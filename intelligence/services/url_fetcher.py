"""
Fetch a public web page without becoming a tool for attacking our own network.

The danger (SSRF, server-side request forgery): our server will fetch any URL a user types.
Typed "http://169.254.169.254/" it would read a cloud provider's secret metadata; typed
"http://localhost:5432/" it would poke our own database. So before EVERY request, including
every redirect hop, we:

  1. allow only http/https on ports 80/443, with no "user:password@" in the URL;
  2. resolve the host name ourselves and refuse if ANY address is private, loopback,
     link-local, multicast, reserved or otherwise not on the public internet;
  3. follow redirects by hand (max 3) so each new location is checked again;
  4. stream the body and stop at MAX_BYTES; only accept HTML;
  5. respect robots.txt for our user agent.

Known gap, on purpose kept for teaching: between our DNS check and the connection that
`requests` makes, a hostile DNS server could change its answer ("DNS rebinding"). Closing
that fully means connecting to the checked IP ourselves; production systems often route
fetches through an egress proxy that enforces the same rules instead.
"""

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

USER_AGENT = "AIWarRoomBot/1.0 (+on-demand company scan; respects robots.txt)"
CONNECT_TIMEOUT = 4  # seconds
READ_TIMEOUT = 10
MAX_BYTES = 1_500_000  # 1.5 MB is plenty for the text of one page
MAX_REDIRECTS = 3
ALLOWED_PORTS = {None, 80, 443}


class FetchBlocked(Exception):
    """We refused on purpose (unsafe address, robots.txt, wrong content type...)."""


class FetchFailed(Exception):
    """We tried and the site didn't cooperate (timeout, 404, connection refused...)."""


@dataclass
class Page:
    requested_url: str
    final_url: str
    status: int
    html: str


# --------------------------------------------------------------------------------------
# Address checks
# --------------------------------------------------------------------------------------
def is_public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped  # "::ffff:127.0.0.1" is really 127.0.0.1
    return ip.is_global and not ip.is_multicast


def resolve(host: str) -> list[str]:
    """All addresses a host name points to (IPv4 and IPv6)."""
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as error:
        raise FetchFailed(f"Couldn't find {host} (DNS lookup failed).") from error
    return sorted({info[4][0] for info in infos})


def check_url(url: str) -> str:
    """Raise FetchBlocked unless `url` is safe to request. Returns the normalised URL."""
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"}:
        raise FetchBlocked("Only http:// and https:// addresses can be scanned.")
    if not parts.hostname:
        raise FetchBlocked("That address has no host name.")
    if parts.username or parts.password:
        raise FetchBlocked("Addresses with a username or password are not allowed.")
    if parts.port not in ALLOWED_PORTS:
        raise FetchBlocked("Only the standard web ports (80 and 443) are allowed.")
    addresses = resolve(parts.hostname)
    if not addresses or not all(is_public_address(a) for a in addresses):
        raise FetchBlocked(f"{parts.hostname} points to a private or reserved network address.")
    return parts.geturl()


# --------------------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------------------
def _get(url: str, session: requests.Session, accept_html_only: bool) -> Page:
    current = check_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        try:
            response = session.get(
                current,
                allow_redirects=False,  # we follow redirects ourselves, checking each hop
                stream=True,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"},
            )
        except requests.RequestException as error:
            raise FetchFailed(f"Couldn't load {current}: {type(error).__name__}.") from error

        with response:
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                if not location:
                    raise FetchFailed(f"{current} redirected without a destination.")
                current = check_url(urljoin(current, location))
                continue

            content_type = response.headers.get("Content-Type", "").lower()
            if accept_html_only and "html" not in content_type:
                raise FetchBlocked(f"{current} isn't an HTML page ({content_type or 'unknown'}).")
            body = bytearray()
            for chunk in response.iter_content(chunk_size=16_384):
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    break  # keep what we have; one page's text never needs more
            encoding = response.encoding or response.apparent_encoding or "utf-8"
            return Page(url, current, response.status_code, body.decode(encoding, "replace"))
    raise FetchFailed(f"{url} redirected more than {MAX_REDIRECTS} times.")


class SafeFetcher:
    """
    Fetches pages from one site, checking robots.txt once and reusing the connection.

    robots.txt rules (RFC 9309): a 4xx means "no rules", so crawling is allowed; a 5xx or
    an unreachable robots.txt means "assume everything is disallowed".
    """

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self._robots: dict[str, RobotFileParser | None] = {}

    def robots_for(self, url: str) -> RobotFileParser | None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            parser = RobotFileParser()
            try:
                page = _get(f"{origin}/robots.txt", self.session, accept_html_only=False)
            except FetchFailed:
                parser.disallow_all = True
            else:
                if page.status >= 500:
                    parser.disallow_all = True
                elif page.status >= 400:
                    parser.allow_all = True
                else:
                    parser.parse(page.html.splitlines())
            self._robots[origin] = parser
        return self._robots[origin]

    def allowed(self, url: str) -> bool:
        return self.robots_for(url).can_fetch(USER_AGENT, url)

    def fetch(self, url: str) -> Page:
        url = check_url(url)
        if not self.allowed(url):
            raise FetchBlocked(f"robots.txt asks bots not to read {url}.")
        page = _get(url, self.session, accept_html_only=True)
        if page.status >= 400:
            raise FetchFailed(f"{url} answered {page.status}.")
        return page
