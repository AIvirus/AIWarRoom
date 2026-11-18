# 8.4 · Reading a page

**Time:** 50 minutes · **Before this:** [8.3](03-safe-fetcher-part-2.md).

## Read

A web page's HTML is mostly **wrapping**: menus, scripts, styles, tracking code. We want
a few things from it:

| We keep | Example |
|---|---|
| Title and description | "Kirana Express \| Groceries in 30 minutes" |
| Headings (`h1`, `h2`, `h3`) | "Groceries in 30 minutes" |
| Readable text (first 4,000 characters) | for the AI to summarise |
| Prices | `₹649`, `₹1299.00` |
| Product names | "Basmati Rice 5 kg" |
| Providers the site **names** | `{"payment": ["Razorpay"], "logistics": ["Delhivery"]}` |
| Same-site links | to pick the next pages to read |

The tool is **Beautiful Soup** (`bs4`, installed in Part 4): it reads messy HTML and lets
you ask "give me every `h1`" or "the `<title>`".

### Regular expressions, briefly

To find prices in text we use a **regular expression** ("regex"): a tiny pattern
language. You met one in lesson 7.5. This one:

```text
(?:₹|rs\.?|inr|\$|£|€)\s?\d[\d,]*(?:\.\d{1,2})?
```

reads as: a currency sign (`₹`, `rs`, `rs.`, `inr`, `$`, `£` or `€`), maybe a space, a
digit, then more digits or commas, then maybe a dot and one or two digits. It matches
`₹649`, `Rs. 1,299`, `INR 2,000`, `£51.77`. You don't need to write regexes like this
yet; you need to be able to read one with the help of a comment.

### "Names", not "uses"

If a page says "Pay with Razorpay", we record that the site **names** Razorpay. That's
all. It doesn't prove they use it today. The code's comment says so, and so will the AI
profile ("basis: site").

## Do

Create `intelligence/services/site_extractor.py`.

### Piece 1: the settings and `extract` (lines 1–94)

<!-- source: intelligence/services/site_extractor.py:1-94 -->
```python
"""
Turn raw HTML into the few things we care about, deterministically (no AI):

  title, description, headings, readable text, prices, product names, same-site links,
  and providers the site itself names (payment gateways, couriers).

Because this step is plain code, the same page always gives the same extract, so the
next scan can be compared with this one fairly. The AI only sees what we extracted.
"""

import hashlib
import re
from dataclasses import asdict, dataclass, field
from urllib.parse import urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup

MAX_TEXT_CHARS = 4000  # per page, enough for an AI summary; keeps prompts small
MAX_PRODUCTS = 40

PRICE_PATTERN = re.compile(
    r"(?:₹|rs\.?|inr|\$|£|€)\s?\d[\d,]*(?:\.\d{1,2})?", re.IGNORECASE
)  # "₹1,299", "Rs. 499", "INR 2,000", "$19.99", "£51.77"

# Names a site might mention on checkout, shipping or FAQ pages. Matching is literal, so a
# "dependency" here means "the site names it", nothing more.
KNOWN_PROVIDERS = {
    "payment": [
        "Razorpay", "Paytm", "PhonePe", "Cashfree", "PayU", "CCAvenue", "Stripe", "PayPal",
        "Google Pay", "BillDesk", "Juspay", "Simpl", "LazyPay", "UPI",
    ],
    "logistics": [
        "Shiprocket", "Delhivery", "Blue Dart", "BlueDart", "Ekart", "DTDC", "Xpressbees",
        "Ecom Express", "Shadowfax", "India Post", "FedEx", "DHL", "Dunzo", "Porter",
    ],
    "platform": ["Shopify", "WooCommerce", "Magento", "BigCommerce", "Wix", "Dukaan"],
}  # fmt: skip

# Links worth following from the homepage, best first.
INTERESTING_LINK_WORDS = [
    "pricing", "price", "plans", "shop", "products", "collections", "catalogue", "catalog",
    "about", "shipping", "delivery", "returns", "faq", "contact",
]  # fmt: skip


@dataclass
class PageExtract:
    url: str
    title: str
    description: str
    headings: list[str]
    text: str
    text_hash: str
    prices: list[str]
    products: list[str]
    providers: dict[str, list[str]]
    links: list[str] = field(default_factory=list)

    def to_dict(self, include_links=False) -> dict:
        data = asdict(self)
        if not include_links:
            data.pop("links")
        return data


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract(url: str, html: str) -> PageExtract:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "template"]):
        tag.decompose()

    title = _clean(soup.title.get_text()) if soup.title else ""
    meta = soup.find("meta", attrs={"name": "description"})
    description = _clean(meta.get("content", "")) if meta else ""
    headings = [_clean(h.get_text()) for h in soup.find_all(["h1", "h2", "h3"])]
    headings = [h for h in headings if h][:30]
    text = _clean(soup.get_text(" "))

    return PageExtract(
        url=url,
        title=title[:200],
        description=description[:400],
        headings=headings,
        text=text[:MAX_TEXT_CHARS],
        # Hash of the FULL text: a change anywhere on the page changes it.
        text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        prices=sorted(set(_normalise_price(p) for p in PRICE_PATTERN.findall(text))),
        products=_product_names(soup),
        providers=_providers(text),
        links=_same_site_links(url, soup),
    )
```

### Piece 2: the helpers (lines 97–159)

<!-- source: intelligence/services/site_extractor.py:97-159 -->
```python
def _normalise_price(raw: str) -> str:
    """'Rs. 1,299' and '₹1299' are the same price: both become '₹1299'."""
    symbol = "₹" if re.match(r"(?i)rs|inr|₹", raw) else raw.strip()[0]
    digits = re.sub(r"[^\d.]", "", raw).strip(".")  # "Rs. 1,299.50" -> "1299.50"
    return f"{symbol}{digits}"


def _product_names(soup) -> list[str]:
    """
    Product names, from the markup shops commonly use: schema.org itemprop="name" inside a
    Product, or elements whose class mentions product title/name, or links inside
    product cards. Heuristic by nature; it only needs to be stable between scans.
    """
    names = []
    selectors = [
        "[itemtype*='Product'] [itemprop='name']",
        "[class*='product-title']", "[class*='product-name']", "[class*='product_title']",
        "[class*='product'] h2", "[class*='product'] h3", "article.product_pod h3 a",
    ]  # fmt: skip
    for selector in selectors:
        for element in soup.select(selector):
            name = _clean(element.get("title") or element.get_text())
            if 2 < len(name) < 120 and name not in names:
                names.append(name)
    return names[:MAX_PRODUCTS]


def _providers(text: str) -> dict[str, list[str]]:
    found = {}
    for kind, names in KNOWN_PROVIDERS.items():
        hits = [name for name in names if re.search(rf"\b{re.escape(name)}\b", text, re.I)]
        if hits:
            found[kind] = hits
    return found


def _same_site_links(base_url: str, soup) -> list[str]:
    host = urlsplit(base_url).hostname
    links = []
    for anchor in soup.find_all("a", href=True):
        absolute, _ = urldefrag(urljoin(base_url, anchor["href"]))
        parts = urlsplit(absolute)
        if parts.scheme in {"http", "https"} and parts.hostname == host and absolute not in links:
            links.append(absolute)
    return links


def pick_followup_links(homepage: PageExtract, limit: int) -> list[str]:
    """The most informative same-site pages to read next (pricing, products, shipping...)."""

    def score(link: str) -> int:
        path = urlsplit(link).path.lower()
        for rank, word in enumerate(INTERESTING_LINK_WORDS):
            if word in path:
                return rank
        return len(INTERESTING_LINK_WORDS)

    candidates = [
        link for link in homepage.links
        if urlsplit(link).path not in {"", "/"} and link.rstrip("/") != homepage.url.rstrip("/")
    ]  # fmt: skip
    interesting = [link for link in candidates if score(link) < len(INTERESTING_LINK_WORDS)]
    return sorted(interesting, key=score)[:limit]
```

## Check

First, a tiny page you write yourself. In `python manage.py shell` (the `extract(`
call spans four lines; Python waits with `...` until the closing `)`):

```python
from intelligence.services.site_extractor import extract

mini = extract(
    "https://kirana.example/",
    "<title>Kirana</title><h1>Fresh food</h1><p>Rice Rs. 1,299 or ₹649. Pay with Razorpay.</p><a href='/pricing'>Prices</a>",
)
mini.prices
```

```text
['₹1299', '₹649']
```

"Rs. 1,299" became `₹1299`: the same price always looks the same. Now:

```python
mini.providers
```

```text
{'payment': ['Razorpay']}
```

```python
mini.links
```

```text
['https://kirana.example/pricing']
```

The relative link `/pricing` became a full address. Now the real practice site. If you
closed the shell from 8.3, fetch it again first
(`from intelligence.services.url_fetcher import SafeFetcher` and
`page = SafeFetcher().fetch("https://books.toscrape.com/")`):

```python
from intelligence.services.site_extractor import pick_followup_links

books = extract(page.final_url, page.html)
books.title
```

```text
'All products | Books to Scrape - Sandbox'
```

```python
books.prices[:3]
```

```text
['£13.99', '£17.46', '£17.93']
```

```python
books.products[:3]
```

```text
['A Light in the ...', 'Tipping the Velvet', 'Soumission']
```

The first name is cut short because the site itself shortens it on the page. (Further
down the list you'll find the full name too, from the link's `title`. Finding product
names is guesswork by nature; what matters is that it's the **same** guess every time.)

```python
pick_followup_links(books, 2)
```

Two category pages of the shop (their addresses contain `catalogue`, a word on our
"interesting" list).

## Line by line

### Piece 1

- **Lines 1–9** · Docstring: plain code, no AI, same page → same extract.
- **Line 11** · `hashlib`, to make a fingerprint of the text (as in lesson 7.7).
- **Line 12** · `re`, regular expressions.
- **Line 13** · `asdict` turns a dataclass into a dictionary; `field` sets defaults.
- **Line 14** · Address tools. `urldefrag` removes the `#section` part of an address.
- **Line 16** · Beautiful Soup.
- **Lines 18–19** · Limits: 4,000 characters of text per page, 40 products.
- **Lines 21–23** · The price pattern from the Read section. `re.IGNORECASE` makes `RS`,
  `Rs` and `rs` all match. The comment shows examples.
- **Lines 25–37** · Names to look for, in three groups. `# fmt: skip` tells `ruff format`
  to leave this hand-arranged list alone.
- **Lines 39–43** · Words that make a link worth reading, **best first**: pricing pages
  beat "about" pages.
- **Lines 46–57** · `PageExtract`: everything we keep from one page. `text_hash` is a
  fingerprint of the full text. `links` defaults to an empty list
  (`field(default_factory=list)`: each extract gets its **own** new list).
- **Lines 59–63** · `to_dict`: as a dictionary, for saving in the database. Links are
  left out unless asked for: they're only needed during the scan.
- **Lines 66–67** · `_clean`: squash every run of spaces, tabs and new lines into one
  space, and trim the ends.
- **Line 70** · `extract(url, html)`.
- **Line 71** · Let Beautiful Soup read the HTML.
- **Lines 72–73** · Throw away tags that never hold readable text: scripts, styles,
  drawings, embedded frames. `decompose()` deletes a tag and everything inside it.
- **Line 75** · The `<title>`'s text, if there is one; otherwise empty.
- **Lines 76–77** · The `<meta name="description" content="...">` tag's `content`.
- **Lines 78–79** · The text of every `h1`, `h2` and `h3`, dropping empty ones, at most
  30.
- **Line 80** · All the remaining text. `get_text(" ")` puts a space between tags, so
  words from different tags don't stick together.
- **Lines 82–94** · Build the result. Title and description are cut to sensible lengths.
  - **Lines 88–89** · The fingerprint uses the **full** text, so a change anywhere
    changes it.
  - **Line 90** · Find all prices, normalise each, remove duplicates (`set`), sort.

### Piece 2

- **Lines 97–101** · `_normalise_price`. If it starts with `rs`, `inr` or `₹`, the symbol
  is `₹`; otherwise the first character (`$`, `£`, `€`). Then keep only digits and dots.
  `"Rs. 1,299.50"` → `"₹1299.50"`.
- **Lines 104–109** · `_product_names` and a docstring admitting it's guesswork.
- **Lines 111–115** · CSS selectors (the same patterns CSS uses to style things), in
  order. `[class*='product-title']` means "any element whose class **contains**
  `product-title`". The last one fits books.toscrape.com's layout.
- **Lines 116–120** · For each match, use its `title` attribute if it has one, else its
  text. Keep names of a sensible length that we haven't seen yet.
- **Line 121** · At most 40.
- **Lines 124–130** · `_providers`: for each group, which names appear in the text?
  `\b` means "a word edge", so "UPI" doesn't match inside "CUPID". `re.escape` makes a
  name like "Blue Dart" safe to put in a pattern. `re.I`: any capitals.
- **Lines 133–141** · `_same_site_links`: every `<a href=...>`, made into a full address
  without the `#part`, kept only if it's `http(s)` on **the same host** and not already
  listed.
- **Line 144** · `pick_followup_links(homepage, limit)`.
- **Lines 147–152** · `score(link)`: the position of the first interesting word in the
  link's path (0 = "pricing", best). No interesting word: a score past the end.
- **Lines 154–157** · Candidates: links that aren't the homepage itself.
- **Line 158** · Keep only links with an interesting word.
- **Line 159** · Best first, at most `limit`.

## If it didn't work

| You see | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'bs4'` | Activate the virtual environment. The package is `beautifulsoup4`, imported as `bs4`. |
| `mini.prices` is `['₹1,299', '₹649']` | Line 100: `re.sub(r"[^\d.]", "", raw)` removes everything except digits and dots. |
| `NameError: name 'urldefrag' is not defined` | Line 14 imports three things: `urldefrag, urljoin, urlsplit`. |

## Quiz

1. Why are `<script>` tags removed before reading the text?
2. A page says "Pay with Razorpay". Does that prove the shop uses Razorpay?
3. Why does `text_hash` use the full text, not the first 4,000 characters?

---

**Next:** [8.5 · What changed?](05-what-changed.md)

<details><summary>Quiz answers</summary>

1. Scripts are code, not words for people. They'd fill the text with noise (and could
   hide text meant to trick the AI).
2. No, only that the site **names** it. It could be old text.
3. So a change anywhere on the page, even past the first 4,000 characters, changes the
   fingerprint.

</details>
