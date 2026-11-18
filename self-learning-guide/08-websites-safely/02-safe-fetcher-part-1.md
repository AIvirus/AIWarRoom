# 8.2 · The safe fetcher, part 1: check the address

**Time:** 45 minutes · **Before this:** [8.1](01-the-dangers.md).

## Read

Before our server requests **any** address, `check_url` asks four questions:

1. Is it `http` or `https`? (Not `ftp://`, not `file:///etc/passwd`.)
2. Does it have a host name, and **no** `username:password@` part?
3. Is the port the normal web port (80 or 443), or none?
4. Does the name point **only** to public internet addresses?

Python can answer all four with its built-in tools. Try them first. Open a Python prompt
from `my-warroom` (with the virtual environment active):

```bash
python
```

```python
import ipaddress

ipaddress.ip_address("8.8.8.8").is_global
```

`True`: 8.8.8.8 (one of Google's public servers) is on the public internet ("global").

```python
ipaddress.ip_address("127.0.0.1").is_global
```

`False`. So are `"192.168.1.10"` and `"169.254.169.254"`: try them.

Now split an address into its parts:

```python
from urllib.parse import urlsplit

parts = urlsplit("https://admin:secret@shop.example:8443/pricing?x=1")
parts.scheme, parts.hostname, parts.port, parts.username, parts.path
```

```text
('https', 'shop.example', 8443, 'admin', '/pricing')
```

Finally, ask "what addresses does this name point to?":

```python
import socket

socket.getaddrinfo("localhost", None, proto=socket.IPPROTO_TCP)
```

You get a list. Inside it you'll see `'::1'` and `'127.0.0.1'`: `localhost` is this
computer, in the new (IPv6) and old (IPv4) styles. Type `exit()` to leave.

Those three tools are the whole idea. The file below wraps them up carefully.

## Do

Create `intelligence/services/url_fetcher.py` and type in the first half:

<!-- source: intelligence/services/url_fetcher.py:1-87 -->
```python
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
```

## Check

Open the Django shell (you first used it in lesson 7.6):

```bash
python manage.py shell
```

```python
from intelligence.services.url_fetcher import check_url

check_url("https://example.com/")
```

```text
'https://example.com/'
```

A public site: allowed (this needs the internet). Now the dangerous one:

```python
check_url("http://localhost/")
```

The last line of the error:

```text
intelligence.services.url_fetcher.FetchBlocked: localhost points to a private or reserved network address.
```

Try a few more and read each message: `"http://169.254.169.254/"`,
`"file:///etc/passwd"`, `"http://localhost:8000/"`, `"https://nosuchsite.invalid/"`. The
last one is a `FetchFailed` (the name doesn't exist), not a `FetchBlocked`. Type `exit()`
when you're done.

## Line by line

- **Lines 1–20** · The docstring explains the danger and the five rules. Lines 16–19 are
  honest about a gap the file doesn't close (see the box below).
- **Line 22** · `ipaddress`: Python's tool for IP addresses.
- **Line 23** · `socket`: low-level networking; we use it to look names up.
- **Line 24** · `dataclass`, for the `Page` result.
- **Line 25** · `urljoin` (turn `/pricing` into a full address) and `urlsplit` (split an
  address into parts).
- **Line 26** · `RobotFileParser`: Python's built-in `robots.txt` reader (next lesson).
- **Line 28** · `requests`: the popular package for downloading web pages. It's in
  `requirements.txt` since Part 4.
- **Line 30** · Our **User-Agent**: the name we give every site, so they know who's
  visiting and why.
- **Lines 31–32** · Give up if connecting takes over 4 seconds, or if the page stops
  sending for 10.
- **Line 33** · Read at most 1.5 million bytes (1.5 MB) of a page. The `_` is just for
  reading: `1_500_000` is `1500000`.
- **Line 34** · Follow at most 3 redirects.
- **Line 35** · Allowed ports. `None` means "not written in the address", so the normal
  one is used.
- **Lines 38–39** · `FetchBlocked`: **we** refused on purpose.
- **Lines 42–43** · `FetchFailed`: **the site** didn't work (no answer, a 404...). Two
  different errors, so a scan can say which happened.
- **Lines 46–51** · `Page`: what a fetch returns. The address asked for, the address we
  ended at (after redirects), the status code (200, 404...), and the page's HTML.
- **Lines 54–56** · A section banner.
- **Line 57** · `is_public_address`: is this one IP address on the public internet?
- **Line 58** · Turn the text into an address object.
- **Lines 59–60** · A trick to watch for: `::ffff:127.0.0.1` is the IPv4 address
  `127.0.0.1` written in IPv6 style. `ipv4_mapped` unwraps it, so the check below sees
  the real address.
- **Line 61** · Public means `is_global` and not **multicast** (an address that sends to
  many machines at once).
- **Line 64** · `resolve(host)`: every address a name points to.
- **Line 67** · `getaddrinfo` asks the computer's DNS (the internet's phone book). One
  name can have several addresses.
- **Lines 68–69** · The name doesn't exist: `FetchFailed` with a clear message.
- **Line 70** · Each result's address is at `info[4][0]`. The `{...}` set removes
  duplicates; `sorted` puts them in a fixed order.
- **Line 73** · `check_url`: the gatekeeper.
- **Line 75** · Split the address (after removing spaces at the ends).
- **Lines 76–77** · Question 1: only `http` and `https`.
- **Lines 78–79** · Question 2a: there must be a host name.
- **Lines 80–81** · Question 2b: no `user:password@`. (Such addresses are a common trick
  to make a link look like it goes somewhere it doesn't.)
- **Lines 82–83** · Question 3: ports 80/443 only. `localhost:8000` (your own Django!)
  fails here.
- **Line 84** · Look the name up.
- **Lines 85–86** · Question 4: refuse if there are no addresses, or if **any one** of
  them isn't public. "All must be public" matters: a name with one public and one private
  address could send us to the private one.
- **Line 87** · Safe. Return the address, tidied up.

> **The honest gap (lines 16–19).** We look the name up, then `requests` looks it up
> **again** when it connects. A hostile name server could answer "public" the first time
> and "private" the second ("DNS rebinding"). Closing that completely means connecting
> to the checked address ourselves. Big companies often send all such requests through
> a separate "egress proxy" with the same rules. For this course, knowing the gap exists
> is the lesson.

## If it didn't work

| You see | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'requests'` | Your virtual environment isn't active, or Part 4's `pip install -r requirements.txt` was skipped. |
| `check_url("https://example.com/")` says `DNS lookup failed` | No internet connection. The tests in 8.11 don't need it. |
| `localhost` is **allowed** | Check line 85: `not all(...)` with `is_public_address(a)`, and line 61. |

## Quiz

1. Why does `check_url` refuse `http://localhost:8000/` before even looking the name up?
2. A name points to `93.184.216.34` **and** `127.0.0.1`. Allowed?
3. What's the difference between `FetchBlocked` and `FetchFailed`?

---

**Next:** [8.3 · The safe fetcher, part 2](03-safe-fetcher-part-2.md)

<details><summary>Quiz answers</summary>

1. Port 8000 isn't 80 or 443 (lines 82–83 come before the lookup on line 84).
2. No. Every address must be public (line 85).
3. `FetchBlocked`: we refused on purpose (unsafe, robots.txt, not HTML).
   `FetchFailed`: we tried and the site didn't work (no such name, timeout, 404).

</details>
