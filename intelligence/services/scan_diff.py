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
