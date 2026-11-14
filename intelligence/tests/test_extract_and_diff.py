from intelligence.services.scan_diff import compare
from intelligence.services.site_extractor import extract, pick_followup_links

HOME = """
<html><head><title>Kirana Express | Groceries in 30 minutes</title>
<meta name="description" content="Fresh groceries delivered across Pune.">
<script>var tracking = "ignore me";</script></head>
<body>
  <nav><a href="/">Home</a><a href="/pricing">Pricing</a><a href="/about-us">About</a>
       <a href="/shipping-policy">Shipping</a><a href="https://other.test/x">Elsewhere</a>
       <a href="/blog/2026/recipe">Blog</a></nav>
  <h1>Groceries in 30 minutes</h1>
  <div class="product-card"><h3 class="product-title">Basmati Rice 5 kg</h3><span>₹649</span></div>
  <div class="product-card">
    <h3 class="product-title">Toor Dal 1 kg</h3><span>Rs. 1,299.00</span>
  </div>
  <p>Pay with UPI or Razorpay. Delivered by Delhivery and Shadowfax.</p>
</body></html>
"""


def test_extract_reads_title_prices_products_and_providers():
    page = extract("https://kirana.test/", HOME)
    assert page.title == "Kirana Express | Groceries in 30 minutes"
    assert page.description == "Fresh groceries delivered across Pune."
    assert page.prices == ["₹1299.00", "₹649"]  # "Rs. 1,299.00" normalised
    assert page.products == ["Basmati Rice 5 kg", "Toor Dal 1 kg"]
    assert page.providers == {
        "payment": ["Razorpay", "UPI"],
        "logistics": ["Delhivery", "Shadowfax"],
    }
    assert "ignore me" not in page.text  # scripts are stripped


def test_extract_keeps_only_same_site_links():
    page = extract("https://kirana.test/", HOME)
    assert "https://other.test/x" not in page.links
    assert "https://kirana.test/pricing" in page.links


def test_followup_links_prefer_pricing_then_about_then_shipping_and_skip_others():
    page = extract("https://kirana.test/", HOME)
    assert pick_followup_links(page, 5) == [
        "https://kirana.test/pricing",
        "https://kirana.test/about-us",
        "https://kirana.test/shipping-policy",
    ]


def test_same_page_twice_gives_identical_extract():
    assert extract("https://kirana.test/", HOME) == extract("https://kirana.test/", HOME)


# --- Diff ---------------------------------------------------------------------------------


def page(url, prices=(), products=()):
    return {"url": url, "prices": list(prices), "products": list(products)}


def test_no_changes_no_alerts():
    pages = [page("https://k.test/", ["₹649"], ["Rice"])]
    assert compare(pages, pages) == []


def test_removed_and_new_pages():
    before = [page("https://k.test/"), page("https://k.test/offers")]
    after = [page("https://k.test/"), page("https://k.test/careers")]
    kinds = [(c.kind, c.severity) for c in compare(before, after)]
    assert kinds == [("page_removed", "warn"), ("new_page", "info")]


def test_big_price_rise_is_a_warning_with_before_and_after():
    """Typical price 600 -> 700 is +16.7 %: above the 10 % warning line."""
    before = [page("https://k.test/p", ["₹500", "₹600", "₹900"])]
    after = [page("https://k.test/p", ["₹500", "₹700", "₹900"])]
    [change] = compare(before, after)
    assert change.kind == "pricing_change" and change.severity == "warn"
    assert change.detail["removed"] == ["₹600"] and change.detail["added"] == ["₹700"]
    assert "up 17 %" in change.summary


def test_small_price_change_is_info():
    before = [page("https://k.test/p", ["₹600"])]
    after = [page("https://k.test/p", ["₹620"])]
    assert compare(before, after)[0].severity == "info"


def test_new_products_and_new_competitors():
    before = [page("https://k.test/", products=["Rice"])]
    after = [page("https://k.test/", products=["Rice", "Ghee 1 L"])]
    changes = compare(before, after, {"BigBasket"}, {"BigBasket", "Zepto"})
    assert [(c.kind, c.severity) for c in changes] == [
        ("new_product", "info"),
        ("new_competitor", "warn"),
    ]
    assert changes[1].detail["note"].startswith("From AI analysis")
