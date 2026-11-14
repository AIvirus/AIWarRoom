"""
SSRF and robots.txt tests. DNS and HTTP are both faked, so these run offline and can
pretend a host resolves to 127.0.0.1 or that a site redirects to the cloud metadata IP.
"""

import pytest

from intelligence.services import url_fetcher
from intelligence.services.url_fetcher import FetchBlocked, FetchFailed, SafeFetcher, check_url

PUBLIC_IP = "93.184.216.34"


@pytest.fixture
def dns(monkeypatch):
    """Map host names to addresses: dns["evil.test"] = ["127.0.0.1"]."""
    table = {"shop.test": [PUBLIC_IP]}

    def fake_resolve(host):
        if host not in table:
            raise FetchFailed(f"Couldn't find {host} (DNS lookup failed).")
        return table[host]

    monkeypatch.setattr(url_fetcher, "resolve", fake_resolve)
    return table


class FakeResponse:
    def __init__(self, status=200, body=b"", headers=None):
        self.status_code = status
        self.headers = {"Content-Type": "text/html; charset=utf-8", **(headers or {})}
        self._body = body
        self.encoding = "utf-8"
        self.apparent_encoding = "utf-8"
        self.is_redirect = status in (301, 302, 303, 307) and "Location" in self.headers
        self.is_permanent_redirect = status == 308 and "Location" in self.headers

    def iter_content(self, chunk_size):
        for start in range(0, len(self._body), chunk_size):
            yield self._body[start : start + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, routes):
        self.routes = routes  # {url: FakeResponse}
        self.requested = []

    def get(self, url, **kwargs):
        assert kwargs["allow_redirects"] is False  # we must follow redirects ourselves
        self.requested.append(url)
        return self.routes.get(url, FakeResponse(404, b"not found"))


# --- URL and address checks -----------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("ftp://shop.test/", "Only http"),
        ("file:///etc/passwd", "Only http"),
        ("https://admin:secret@shop.test/", "username or password"),
        ("https://shop.test:8443/", "standard web ports"),
    ],
)
def test_unsafe_url_shapes_are_refused(dns, url, reason):
    with pytest.raises(FetchBlocked, match=reason):
        check_url(url)


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",  # this server
        "10.0.0.5",  # private network
        "192.168.1.10",  # home/office network
        "172.16.0.1",  # private network
        "169.254.169.254",  # cloud metadata service: the classic SSRF target
        "100.64.0.1",  # carrier-grade NAT, not public
        "0.0.0.0",
        "::1",  # IPv6 loopback
        "fd00::1",  # IPv6 private
        "::ffff:127.0.0.1",  # IPv4 loopback dressed up as IPv6
        "224.0.0.1",  # multicast
    ],
)
def test_private_and_reserved_addresses_are_refused(dns, address):
    dns["sneaky.test"] = [address]
    with pytest.raises(FetchBlocked, match="private or reserved"):
        check_url("https://sneaky.test/")


def test_one_private_address_among_public_ones_is_enough_to_refuse(dns):
    dns["mixed.test"] = [PUBLIC_IP, "127.0.0.1"]
    with pytest.raises(FetchBlocked):
        check_url("http://mixed.test/")


def test_public_address_is_allowed(dns):
    assert check_url("https://shop.test/pricing") == "https://shop.test/pricing"


# --- Fetching ------------------------------------------------------------------------------


def make_fetcher(routes, robots=b"User-agent: *\nAllow: /\n"):
    routes.setdefault(
        "https://shop.test/robots.txt", FakeResponse(200, robots, {"Content-Type": "text/plain"})
    )
    return SafeFetcher(session=FakeSession(routes))


def test_redirect_to_a_private_address_is_refused_before_it_is_requested(dns):
    dns["internal.test"] = ["169.254.169.254"]
    session_routes = {
        "https://shop.test/": FakeResponse(
            302, headers={"Location": "http://internal.test/latest"}
        ),
    }
    fetcher = make_fetcher(session_routes)
    with pytest.raises(FetchBlocked, match="private or reserved"):
        fetcher.fetch("https://shop.test/")
    assert "http://internal.test/latest" not in fetcher.session.requested


def test_same_site_redirect_is_followed(dns):
    routes = {
        "https://shop.test/": FakeResponse(301, headers={"Location": "/home"}),
        "https://shop.test/home": FakeResponse(200, b"<h1>Kirana</h1>"),
    }
    page = make_fetcher(routes).fetch("https://shop.test/")
    assert page.final_url == "https://shop.test/home"
    assert "Kirana" in page.html


def test_redirect_loops_stop(dns):
    routes = {
        "https://shop.test/a": FakeResponse(302, headers={"Location": "/b"}),
        "https://shop.test/b": FakeResponse(302, headers={"Location": "/a"}),
    }
    with pytest.raises(FetchFailed, match="redirected more than"):
        make_fetcher(routes).fetch("https://shop.test/a")


def test_large_pages_are_cut_at_the_size_limit(dns, monkeypatch):
    monkeypatch.setattr(url_fetcher, "MAX_BYTES", 1000)
    routes = {"https://shop.test/": FakeResponse(200, b"x" * 50_000)}
    page = make_fetcher(routes).fetch("https://shop.test/")
    assert len(page.html) < 50_000


def test_non_html_is_refused(dns):
    routes = {"https://shop.test/": FakeResponse(200, b"%PDF", {"Content-Type": "application/pdf"})}
    with pytest.raises(FetchBlocked, match="isn't an HTML page"):
        make_fetcher(routes).fetch("https://shop.test/")


# --- robots.txt ---------------------------------------------------------------------------


def test_robots_disallow_is_respected(dns):
    fetcher = make_fetcher({}, robots=b"User-agent: *\nDisallow: /checkout\n")
    assert fetcher.allowed("https://shop.test/pricing")
    assert not fetcher.allowed("https://shop.test/checkout/step-1")
    with pytest.raises(FetchBlocked, match="robots.txt"):
        fetcher.fetch("https://shop.test/checkout/step-1")


def test_robots_rules_for_our_bot_name_apply(dns):
    fetcher = make_fetcher({}, robots=b"User-agent: AIWarRoomBot\nDisallow: /\n")
    assert not fetcher.allowed("https://shop.test/")


def test_missing_robots_txt_means_allowed(dns):
    routes = {"https://shop.test/robots.txt": FakeResponse(404, b"")}
    assert make_fetcher(routes).allowed("https://shop.test/anything")


def test_robots_txt_server_error_means_stay_out(dns):
    routes = {"https://shop.test/robots.txt": FakeResponse(503, b"")}
    assert not make_fetcher(routes).allowed("https://shop.test/")


def test_robots_txt_is_read_once_per_site(dns):
    fetcher = make_fetcher({})
    fetcher.allowed("https://shop.test/a")
    fetcher.allowed("https://shop.test/b")
    assert fetcher.session.requested.count("https://shop.test/robots.txt") == 1
