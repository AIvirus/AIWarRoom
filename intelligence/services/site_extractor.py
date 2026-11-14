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
