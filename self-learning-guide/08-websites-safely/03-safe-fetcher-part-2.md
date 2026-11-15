# 8.3 · The safe fetcher, part 2: fetch carefully

**Time:** 45 minutes · **Before this:** [8.2](02-safe-fetcher-part-1.md).

## 📖 Read

Now the actual download. Three new ideas.

### Redirects, by hand

Ask for `http://shop.example/` and the server may answer **301** or **302** ("moved") with
a header `Location: https://shop.example/home`. Normally `requests` follows that by
itself. We **switch that off** (`allow_redirects=False`) and follow it ourselves, so we
can run `check_url` on the new address **before** going there. Otherwise a public page
could redirect us to `http://169.254.169.254/`, and we'd never notice.

### Streaming, with a size limit

`stream=True` means "don't download the whole page at once; give it to me in pieces".
We add up the pieces and stop at 1.5 MB. A page that never ends can't fill our memory.

### robots.txt rules, exactly

The rules for robots.txt (a standard called RFC 9309) say:

| Asking for `/robots.txt` gives | Meaning |
|---|---|
| 200 and a file | Follow the file's rules |
| 404 (or another 4xx) | There are no rules: reading is allowed |
| 500 (or another 5xx), or no answer | Something's wrong: assume **nothing** is allowed |

We read each site's robots.txt **once** and remember it.

## ⌨️ Do

Add the second half to the **end** of `intelligence/services/url_fetcher.py`:

<!-- source: intelligence/services/url_fetcher.py:90-169 -->
```python
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
```

## ✅ Check

```bash
python manage.py shell
```

```python
from intelligence.services.url_fetcher import SafeFetcher

f = SafeFetcher()
f.allowed("https://books.toscrape.com/")
```

`True`. (This practice site has no robots.txt at all: a 404, which means "no rules".)

```python
page = f.fetch("https://books.toscrape.com/")
page.status
```

`200`. And how much HTML did we get?

```python
len(page.html)
```

About `51294` characters (it may change a little if the site changes). Now a page that
doesn't exist:

```python
f.fetch("https://books.toscrape.com/no-such-page")
```

```text
intelligence.services.url_fetcher.FetchFailed: https://books.toscrape.com/no-such-page answered 404.
```

Keep this shell open: the next lesson uses `page`.

## 🔍 Line by line

### `_get`: one careful request

- **Lines 90–92** · Section banner.
- **Line 93** · `_get(url, session, accept_html_only)`. The `_` at the start means
  "private to this file". `session` is a `requests.Session`, which reuses the connection
  for several requests to the same site.
- **Line 94** · Check the first address before anything else.
- **Line 95** · At most `MAX_REDIRECTS + 1` requests: the first, plus 3 redirects.
- **Lines 96–103** · The request:
  - `allow_redirects=False`: we follow redirects ourselves (line 99 says so).
  - `stream=True`: give us the body in pieces.
  - `timeout=(4, 10)`: the two limits from the top of the file.
  - `headers`: our User-Agent, and "I'd like HTML, or plain text".
- **Lines 104–105** · Any network problem (`requests.RequestException` covers timeouts,
  refused connections...) becomes a `FetchFailed` naming the kind of error. `from error`
  keeps the original error attached, for the log.
- **Line 107** · `with response:` makes sure the connection is closed when we're done,
  even if something goes wrong.
- **Line 108** · Is this a redirect?
- **Lines 109–111** · Where to? A redirect with no `Location` is broken.
- **Line 112** · ⭐ The key line. `urljoin` turns a relative `Location` like `/home` into a
  full address. Then **`check_url` again**: a redirect to a private address stops here,
  before it's ever requested.
- **Line 113** · `continue`: go round the loop again, with the new address.
- **Lines 115–117** · Not a redirect. For normal pages, refuse anything that isn't HTML
  (a PDF, an image, a 2 GB video...).
- **Line 118** · `bytearray()`: an empty, growable box of bytes.
- **Lines 119–122** · Take the body 16 KB at a time. Stop once we're over the limit, but
  keep what we have.
- **Line 123** · Which text encoding (how bytes become letters)? The one the server
  declared, or the one `requests` guesses, or UTF-8.
- **Line 124** · Turn the bytes into text (`"replace"` puts a `�` for any byte that makes
  no sense, instead of crashing) and return a `Page`.
- **Line 125** · The loop ran out: more than 3 redirects (maybe a loop: A → B → A...).

### `SafeFetcher`: one site, politely

- **Lines 128–134** · The class and its docstring, with the robots.txt rules from the
  table above.
- **Lines 136–138** · Use the session we're given (tests pass a fake one) or a new real
  one. `_robots` remembers each site's rules.
- **Line 140** · `robots_for(url)`: the rules for this address's site.
- **Lines 141–142** · The **origin**: scheme and host, like `https://books.toscrape.com`.
- **Line 143** · Only fetch robots.txt the first time we see this origin.
- **Line 144** · An empty rules reader.
- **Line 146** · Fetch `/robots.txt` with the same safe `_get`. It's plain text, so
  `accept_html_only=False`.
- **Lines 147–148** · Couldn't reach it: assume nothing is allowed.
- **Lines 149–151** · `else:` runs only if there was no error. A 5xx: nothing allowed.
- **Lines 152–153** · A 4xx: no rules, everything allowed.
- **Lines 154–155** · Otherwise read the file's rules, line by line.
- **Lines 156–157** · Remember the rules, and return them.
- **Lines 159–160** · `allowed(url)`: may **our** bot (by its User-Agent) read this
  address?
- **Line 162** · `fetch(url)`: what the scan calls.
- **Line 163** · Check the address.
- **Lines 164–165** · Check robots.txt.
- **Line 166** · Download it, HTML only.
- **Lines 167–168** · A 404 or a 500 is a failure for a scan.
- **Line 169** · Return the page.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `FetchFailed: Couldn't load ...: ConnectTimeout.` | No internet, or a firewall. The tests don't need the internet. |
| `FetchBlocked: ... isn't an HTML page` | You asked for a PDF or image. That's the rule working. |
| `AttributeError: 'NoneType' object has no attribute 'can_fetch'` | `robots_for` must `return self._robots[origin]` (line 157), outside the `if`. |

## ❓ Quiz

1. Why `allow_redirects=False`?
2. A site's robots.txt answers 503. May we read the site?
3. A page is 20 MB of HTML. What happens?

---

**Next:** [8.4 · Reading a page](04-reading-a-page.md)

<details><summary>Quiz answers</summary>

1. So we can check each redirect's address (line 112) before requesting it.
2. No. A 5xx means "assume everything is disallowed" (lines 150–151).
3. We read the first 1.5 MB or so and stop (lines 119–122). One page's text never needs
   more.

</details>
