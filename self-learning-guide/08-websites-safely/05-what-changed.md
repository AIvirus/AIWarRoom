# 8.5 · What changed?

**Time:** 35 minutes · **Before this:** [8.4](04-reading-a-page.md).

## Read

Every scan saves its pages' extracts. When a site is scanned again, we compare the new
extracts with the last scan's, using plain rules:

| Rule | Alert kind | Severity |
|---|---|---|
| A page we read last time is gone | `page_removed` | warn |
| A page we didn't have before | `new_page` | info |
| Prices on a page changed, typical price moved **10 % or more** | `pricing_change` | warn |
| Prices changed, but by less | `pricing_change` | info |
| New product names on a page | `new_product` | info |
| The AI profile names a competitor it didn't name before | `new_competitor` | warn |

The last one comes from the AI, so its alert says "From AI analysis; check the source
before acting."

### "Typical" price: the median

A page with prices ₹500, ₹600, ₹900 has a **median** (the middle one, once sorted) of
₹600. If it becomes ₹500, ₹700, ₹900, the median is ₹700: a move of
(700 − 600) ÷ 600 = **+16.7 %**, so a warning. The median ignores one strange very
cheap or very expensive item, which an average wouldn't.

## Do

Create `intelligence/services/scan_diff.py`:

<!-- source: intelligence/services/scan_diff.py:1-98 -->
```python
"""
What changed between two scans of the same site? Plain rules, no AI.

Input: the `pages` lists of the previous and the new CompanyScan, plus the competitor
names each scan's AI profile mentioned. Output: a list of Change objects that become Alert
rows. Keeping this deterministic means an alert can always be explained by pointing at a
before and an after.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

BIG_PRICE_MOVE = Decimal("0.10")  # a 10 % or larger move counts as a warning


@dataclass
class Change:
    kind: str  # matches Alert.Kind
    severity: str  # matches Alert.Severity
    summary: str
    detail: dict = field(default_factory=dict)


def _price_value(price: str) -> Decimal | None:
    try:
        return Decimal(re.sub(r"[^\d.]", "", price))
    except InvalidOperation:
        return None


def _price_change(url: str, before: list[str], after: list[str]) -> Change | None:
    if sorted(before) == sorted(after):
        return None
    removed, added = sorted(set(before) - set(after)), sorted(set(after) - set(before))
    # Compare typical (median-ish) prices to judge how big the move is.
    old = sorted(v for v in map(_price_value, before) if v)
    new = sorted(v for v in map(_price_value, after) if v)
    severity = "info"
    move = None
    if old and new:
        old_mid, new_mid = old[len(old) // 2], new[len(new) // 2]
        move = (new_mid - old_mid) / old_mid if old_mid else None
        if move is not None and abs(move) >= BIG_PRICE_MOVE:
            severity = "warn"
    summary = f"Prices changed on {url}"
    if move is not None and move != 0:
        summary += f" (typical price {'up' if move > 0 else 'down'} {abs(move) * 100:.0f} %)"
    return Change(
        "pricing_change",
        severity,
        summary,
        {"url": url, "removed": removed[:20], "added": added[:20],
         "typical_move_pct": f"{move * 100:.1f}" if move is not None else None},
    )  # fmt: skip


def compare(
    previous_pages: list[dict],
    new_pages: list[dict],
    previous_competitors: set[str] = frozenset(),
    new_competitors: set[str] = frozenset(),
) -> list[Change]:
    before = {page["url"]: page for page in previous_pages}
    after = {page["url"]: page for page in new_pages}
    changes: list[Change] = []

    for url in sorted(before.keys() - after.keys()):
        changes.append(Change("page_removed", "warn", f"Page no longer found: {url}", {"url": url}))
    for url in sorted(after.keys() - before.keys()):
        changes.append(Change("new_page", "info", f"New page found: {url}", {"url": url}))

    for url in sorted(before.keys() & after.keys()):
        old, new = before[url], after[url]
        price_change = _price_change(url, old.get("prices", []), new.get("prices", []))
        if price_change:
            changes.append(price_change)
        added_products = sorted(set(new.get("products", [])) - set(old.get("products", [])))
        if added_products:
            changes.append(
                Change(
                    "new_product",
                    "info",
                    f"{len(added_products)} new product(s) on {url}",
                    {"url": url, "products": added_products[:20]},
                )
            )

    for name in sorted(set(new_competitors) - set(previous_competitors)):
        changes.append(
            Change(
                "new_competitor",
                "warn",
                f"New competitor mentioned in the AI profile: {name}",
                {"name": name, "note": "From AI analysis; check the source before acting."},
            )
        )
    return changes
```

## Check

In `python manage.py shell`:

```python
from intelligence.services.scan_diff import compare

before = [{"url": "https://k.test/", "prices": ["₹600"], "products": ["Rice"]}]
after = [{"url": "https://k.test/", "prices": ["₹700"], "products": ["Rice", "Ghee"]}]
for change in compare(before, after):
    print(change.severity, change.summary)
```

(Type the `print` line with its 4 spaces in front, then press Enter twice.)

```text
warn Prices changed on https://k.test/ (typical price up 17 %)
info 1 new product(s) on https://k.test/
```

Now try `compare(before, before)`. It's `[]`: nothing changed, no alerts.

## Line by line

- **Lines 1–8** · Docstring: two scans in, a list of changes out, no AI.
- **Line 10** · `re`, to strip a price down to its digits.
- **Line 11** · `dataclass` and `field`.
- **Line 12** · `Decimal` for exact money (Part 1), and `InvalidOperation`, the error
  `Decimal` raises for text that isn't a number.
- **Line 14** · The warning line: a 10 % move.
- **Lines 17–22** · `Change`: one difference. `kind` and `severity` use the same words as
  the `Alert` table (lesson 7.3), so a `Change` becomes an `Alert` row directly.
- **Lines 25–29** · `_price_value`: `"₹1299.50"` → `Decimal("1299.50")`. If that fails,
  `None`.
- **Line 32** · `_price_change(url, before, after)`: compare one page's price lists.
- **Lines 33–34** · Same prices (in any order)? No change.
- **Line 35** · Prices that disappeared, and prices that appeared, using set
  subtraction (`a - b`: in `a` but not in `b`).
- **Lines 36–38** · Every price as a number, sorted, dropping any that failed.
- **Lines 39–40** · Start as "info", with no measured move.
- **Lines 41–45** · If both scans have prices: take the middle one of each (`len // 2` is
  the middle position), work out the move as a fraction, and if it's 10 % or more either
  way (`abs`), make it a warning.
- **Lines 46–48** · The summary, adding "(typical price up 17 %)" when there's a move.
  `:.0f` prints a number with no decimals.
- **Lines 49–55** · Build the change. `detail` keeps up to 20 removed and added prices,
  and the move as text like `"16.7"`.
- **Lines 58–63** · `compare(...)`. The competitor sets are optional; `frozenset()` is an
  empty set that can't be changed by accident.
- **Lines 64–65** · Turn each list of pages into a dictionary `{url: page}`, so we can
  find a page by its address.
- **Line 66** · The list we'll fill.
- **Lines 68–69** · Addresses before but not after: removed pages. `.keys()` of two
  dictionaries can be subtracted like sets.
- **Lines 70–71** · After but not before: new pages.
- **Line 73** · Addresses in **both** (`&` is "in both").
- **Lines 74–77** · Price changes on that page. `.get("prices", [])`: an empty list if a
  saved page has no `prices` key.
- **Lines 78–87** · New product names on that page.
- **Lines 89–97** · New competitor names, with the "check the source" note.
- **Line 98** · Return every change.

## If it didn't work

| You see | Fix |
|---|---|
| `TypeError: unsupported operand type(s) for -: 'dict_keys' and 'list'` | Lines 63–64 must build dictionaries, `{page["url"]: page for page in ...}`. |
| The price change is `info`, not `warn` | Line 43: `abs(move) >= BIG_PRICE_MOVE`. |

## Quiz

1. Prices go from ₹600 to ₹620. Alert? Which severity?
2. Why use the median price, not the average?
3. Why does the `new_competitor` alert carry a note?

---

**Next:** [8.6 · Real citations](06-real-citations.md)

<details><summary>Quiz answers</summary>

1. Yes, a `pricing_change`, but only `info`: +3.3 % is under 10 %.
2. One very cheap or very expensive item would drag an average around; the median
   ignores it.
3. Competitors come from the AI profile, not from the page itself, so the reader should
   check before acting.

</details>
