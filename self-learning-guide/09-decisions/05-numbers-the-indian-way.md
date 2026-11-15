# 9.5 · Numbers the Indian way

**Time:** 40 minutes · **Before this:** [9.4](04-the-brief.md).

## 📖 Read

The brief stores money as plain text like `"12345678.40"`. A reader in India expects
**₹1,23,45,678**: the last three digits, then groups of **two** (thousand, lakh, crore).
That's different from the international style, 12,345,678.

| Stored | Unit | Shown |
|---|---|---|
| `21000.00` | `INR` | ₹21,000 |
| `12345678.4` | `INR` | ₹1,23,45,678 |
| `649.50` | `INR/order` | ₹649.50/order |
| `-2428.80` | `INR` | -₹2,429 |
| `22.5` | `%` | 22.5 % |
| `19` | `hour of day` | 19:00 |
| `illustrative` (a source) | | ILL |

Templates show values with **filters**: `{{ value|figure:"INR" }}` means "pass `value` to
the `figure` filter, with `"INR"` as extra information". Django has built-in filters
(`|default`, `|join`, `|linebreaksbr`...). You can write your own: put a file in a
`templatetags` folder of an app, and load it in a template with `{% load warroom %}`.

### How to group the Indian way

Take `12345678`:

1. The last three digits: `678`. The rest: `12345`.
2. Cut the rest into twos from the right: `1`, `23`, `45`.
3. Join with commas: `1,23,45,678`.

## ⌨️ Do

Make the folder `common/templatetags/` with an **empty** `__init__.py`, then create
`common/templatetags/warroom.py`.

### Piece 1: grouping (lines 1–56)

<!-- source: common/templatetags/warroom.py:1-56 -->
```python
"""
Template filters for showing numbers the way an Indian finance team reads them.

    {{ "1234567.5"|indian }}            -> 12,34,568
    {{ "21000.00"|figure:"INR" }}       -> ₹21,000
    {{ "22.5"|figure:"%" }}             -> 22.5 %
    {{ None|figure:"month" }}           -> n/a
    {{ "illustrative"|source_tag }}     -> ILL
"""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()

SOURCE_TAGS = {
    "user": "USR",
    "illustrative": "ILL",
    "derived": "DRV",
    "from_site": "SITE",
    "what_if": "WHAT-IF",
}


def _decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def indian_grouping(number: Decimal, places: int = 0) -> str:
    """12345678 -> '1,23,45,678': last three digits, then groups of two (lakh, crore)."""
    quantum = Decimal(1).scaleb(-places)
    rounded = number.quantize(quantum, rounding=ROUND_HALF_UP)
    sign = "-" if rounded < 0 else ""
    whole, _, fraction = f"{abs(rounded):f}".partition(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    text = ",".join([*groups, tail]) if groups else tail
    return f"{sign}{text}{'.' + fraction if fraction else ''}"


@register.filter
def indian(value, places=0):
    number = _decimal(value)
    return "n/a" if number is None else indian_grouping(number, int(places))
```

### Piece 2: the other filters (lines 59–109)

<!-- source: common/templatetags/warroom.py:59-109 -->
```python
@register.filter
def figure(value, unit=""):
    """Format a metric value with its unit, choosing sensible precision."""
    if value is None or value == "":
        return "n/a"
    number = _decimal(value)
    if number is None:
        return str(value).replace("_", " ")  # a choice such as "ecommerce_curve"
    unit = unit or ""
    whole = number == number.to_integral()
    if unit.startswith("INR"):
        # Paise only where they matter: ₹649.50 yes, ₹640.00 and ₹21,000.40 no.
        places = 0 if whole or abs(number) >= 1000 else 2
        suffix = unit[3:]  # "INR/order" -> "/order"
        sign = "-" if number < 0 else ""  # "-₹2,429", not "₹-2,429"
        return f"{sign}₹{indian_grouping(abs(number), places)}{suffix}"
    if unit == "%":
        return f"{indian_grouping(number, 0 if whole else 1)} %"
    if unit == "ratio":
        return f"{indian_grouping(number, 2)}×"
    if unit == "hour of day":
        return f"{int(number):02d}:00"
    places = 0 if whole or abs(number) >= 100 else 1
    text = indian_grouping(number, places)
    if number == 1 and unit in {"hours", "months", "orders"}:
        unit = unit[:-1]  # "1 hour", not "1 hours"
    return f"{text} {unit}".strip()


@register.filter
def source_tag(source):
    return SOURCE_TAGS.get(source, (source or "").upper())


@register.filter
def when(iso_text):
    """ISO timestamp -> '15 Nov 2026, 19:43 UTC'."""
    if not iso_text:
        return "n/a"
    moment = iso_text if isinstance(iso_text, datetime) else datetime.fromisoformat(str(iso_text))
    return moment.strftime("%d %b %Y, %H:%M UTC")


@register.filter
def humanize_key(value):
    return str(value or "").replace("_", " ")


@register.filter
def get_item(mapping, key):
    return (mapping or {}).get(key)
```

## ✅ Check

In `python manage.py shell`:

```python
from common.templatetags.warroom import figure, indian

figure("21000.00", "INR")
```

`'₹21,000'`. Try the rest of the table above:

```python
figure("12345678.4", "INR")
```

`'₹1,23,45,678'`. Then `figure("649.50", "INR/order")` → `'₹649.50/order'`,
`figure("-2428.80", "INR")` → `'-₹2,429'`, and `indian("100000")` → `'1,00,000'`: one
lakh.

(On Windows, if ₹ gives a `UnicodeEncodeError`, see the fix in lesson 7.2.)

## 🔍 Line by line

### Piece 1

- **Lines 1–9** · Docstring with examples.
- **Line 11** · `datetime`, for the `when` filter.
- **Line 12** · `Decimal` and a rounding rule: `ROUND_HALF_UP` is school rounding (2.5 →
  3).
- **Lines 14–16** · Every filter file needs a `register`: a `template.Library()` that
  filters sign up to.
- **Lines 18–24** · Short tags for where an assumption came from.
- **Lines 27–33** · `_decimal`: turn anything into a `Decimal`, or `None` if it's empty or
  not a number. `str(value)` first, so a float like `0.1` doesn't bring its tiny binary
  errors (lesson 1.8).
- **Line 36** · `indian_grouping(number, places)`.
- **Line 37** · Docstring with the rule.
- **Lines 38–39** · Round to `places` decimals. `Decimal(1).scaleb(-2)` is `0.01`, so
  `places=2` rounds to paise.
- **Line 40** · Remember the minus sign, then work with the number without it.
- **Line 41** · Split `"12345678.40"` into `"12345678"` and `"40"` with `partition(".")`.
  `:f` writes the number plainly, never like `1.2E+7`.
- **Line 42** · `head` = everything but the last three digits, `tail` = the last three.
- **Lines 43–46** · While the head has more than two digits, take its last two to the
  **front** of the groups list.
- **Lines 47–48** · Whatever's left (one or two digits) goes first.
- **Line 49** · Join groups and tail with commas (or just the tail for small numbers).
- **Line 50** · Put back the sign and any decimals.
- **Lines 53–56** · The `indian` filter. `@register.filter` makes it usable in templates.
  Not a number? `"n/a"`.

### Piece 2

- **Lines 59–61** · `figure(value, unit)`: a value with its unit.
- **Lines 62–63** · Nothing? `"n/a"` (for example "first profitable month" when it never
  happens).
- **Lines 64–66** · Not a number? It's a choice like `"ecommerce_curve"`: show it with
  spaces.
- **Line 68** · Is it a whole number?
- **Lines 69–74** · Money (`INR`, `INR/order`...). Show paise only when they matter:
  ₹649.50 yes, ₹21,000.40 no. Keep any `/order` after it. Put the minus **before** the ₹.
- **Lines 75–76** · A percentage: one decimal only if needed.
- **Lines 77–78** · A ratio, like `4.00×`.
- **Lines 79–80** · An hour of the day: `19` → `19:00`. `:02d` pads to two digits, so `7`
  → `07:00`.
- **Lines 81–85** · Anything else: grouped, with its unit, and "1 hour" instead of "1
  hours".
- **Lines 88–90** · `source_tag`: the short tag, or the source in capitals if unknown.
- **Lines 93–99** · `when`: an ISO date text (or a real `datetime`) → `15 Nov 2026, 16:24
  UTC`. `strftime` writes dates with codes: `%d` day, `%b` short month, `%Y` year,
  `%H:%M` time.
- **Lines 102–104** · `humanize_key`: `queue_retry` → `queue retry`.
- **Lines 107–109** · `get_item`: read a dictionary by a key held in a variable. Django
  templates can't write `mapping[key]` themselves. (Part 10 uses it.)

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `'warroom' is not a registered tag library` (in 9.6) | The folder must be `common/templatetags/` with `__init__.py`, and `"common"` must be in `INSTALLED_APPS`. Restart `runserver` after adding a new `templatetags` folder. |
| `figure("21000.00", "INR")` gives `'₹21,000.00'` | Line 71: `places = 0 if whole or abs(number) >= 1000 else 2`. |

## ❓ Quiz

1. Write 2,50,000 the international way.
2. Why does `-2428.80` show as `-₹2,429` and not `₹-2,429`?
3. What does `{{ "illustrative"|source_tag }}` show?

---

**Next:** [9.6 · The printable page](06-the-printable-page.md)

<details><summary>Quiz answers</summary>

1. 250,000 (two lakh fifty thousand).
2. Line 73 puts the sign first, which is how people write it; and ₹2,428.80 is ≥ 1,000,
   so it's shown without paise, rounded to ₹2,429.
3. `ILL`.

</details>
