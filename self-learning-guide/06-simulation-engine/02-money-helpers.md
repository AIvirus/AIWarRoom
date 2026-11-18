# 6.2 · Money helpers

**Time:** 20 minutes · **Before this:** [6.1](01-the-maths-on-paper.md).

## Read

Every part of the engine needs the same few small tools: turn `22.5` (%) into `0.225`,
round money to paise, keep a number between two limits, and package one result as
`{"label": ..., "value": ..., "unit": ...}`. They live in one small file so every model
does them **the same way**.

Two words you'll meet:

- **Rounding half-up**: 2.345 → 2.35, and 2.344 → 2.34. That's the rounding people
  expect on a bill. (Python's normal `round()` uses "banker's rounding", where 2.345 can
  become 2.34. Surprising on an invoice.)
- **Clamp**: keep a value inside limits. Clamp 120 to 0–100 → 100. Clamp −5 → 0.

## Do

Create `simulation_engine/money.py`:

<!-- source: simulation_engine/money.py:1-48 -->
```python
"""
Small Decimal helpers shared by every model.

Why Decimal and not float? 0.1 + 0.2 == 0.30000000000000004 in float. For money that
error compounds month after month; Decimal does arithmetic the way an accountant does.
"""

from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")
CENT = Decimal("0.01")


def pct(value: Decimal) -> Decimal:
    """22.5 (as people write a percentage) -> 0.225 (as a fraction used in maths)."""
    return value / HUNDRED


def round2(value: Decimal) -> Decimal:
    """Round half-up to 2 places: the rounding people expect on an invoice."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return max(low, min(high, value))


def metric(label: str, value: Decimal | int | None, unit: str) -> dict:
    """
    One output number in the shape every layer (API, UI, AI context) uses.

    Values are strings so they survive JSON exactly. None means "not applicable", for
    example a break-even month that never arrives inside the horizon.
    """
    if value is None:
        text = None
    elif isinstance(value, int):
        text = str(value)
    else:
        text = str(round2(value))
    return {"label": label, "value": text, "unit": unit}


def display(value: Decimal) -> float:
    """Timelines are for drawing, not accounting: a rounded float keeps them small."""
    return float(round2(value))
```

## Check

```bash
python
```

```python
from decimal import Decimal
from simulation_engine.money import pct, round2, clamp, metric

pct(Decimal("22.5"))
round2(Decimal("2.345"))
clamp(Decimal("120"), Decimal("0"), Decimal("100"))
metric("Lost revenue", Decimal("84000"), "INR")
```

You should see `Decimal('0.225')`, `Decimal('2.35')`, `Decimal('100')` and
`{'label': 'Lost revenue', 'value': '84000.00', 'unit': 'INR'}`. Type `exit()`.

## Line by line

- **Lines 1–6** · Docstring: why Decimal (lesson 1.9 showed the float problem).
- **Line 8** · `ROUND_HALF_UP` names the rounding rule; `Decimal` the number type.
- **Lines 10–13** · Named constants. `ZERO` reads better than `Decimal("0")` everywhere,
  and `CENT` (0.01) is "two decimal places".
- **Lines 16–18** · `pct`: a percentage as people write it → a fraction for maths.
  22.5 → 0.225.
- **Lines 21–23** · `round2`: `.quantize(CENT, ...)` means "round to the same number of
  decimals as 0.01", using half-up.
- **Lines 26–27** · `clamp`: `min(high, value)` caps it at the top, then
  `max(low, ...)` lifts it to the bottom limit.
- **Line 30** · `metric(label, value, unit)`: every output number in the whole app has
  this shape. The value may be a Decimal, a whole number (`int`), or `None`.
- **Lines 31–36** · Docstring: values become **text** so they survive JSON exactly, and
  `None` means "doesn't apply" (like a break-even month that never comes).
- **Lines 37–38** · `None` stays `None` (`null` in JSON).
- **Lines 39–40** · `isinstance(value, int)` asks "is this a whole number?". Months like
  `7` stay `"7"`, not `"7.00"`.
- **Lines 41–42** · Everything else is money-like: round to 2 decimals, then text.
- **Line 43** · Build the dictionary.
- **Lines 46–48** · `display`: for **charts** only. A chart doesn't need exact paise,
  and a list of 72 small floats is much smaller than 72 long texts. Never used for totals.

## If it didn't work

| You see | Fix |
|---|---|
| `TypeError: unsupported operand type(s) for /: 'float' and 'decimal.Decimal'` | You passed a float like `22.5`. Use `Decimal("22.5")`. Decimals and floats don't mix. |
| `round2` gives `2.34` | Check line 23 says `ROUND_HALF_UP`. |

## Quiz

1. What does `metric("Month", 7, "month")` put in `value`?
2. Why are chart numbers floats but totals Decimals?

---

**Next:** [6.3 · The idea model](03-the-idea-model.md)

<details><summary>Quiz answers</summary>

1. `"7"` (text, no decimals, because 7 is an `int`).
2. Charts only need to look right; totals must be exact. Floats are smaller and fine for
   drawing.

</details>
