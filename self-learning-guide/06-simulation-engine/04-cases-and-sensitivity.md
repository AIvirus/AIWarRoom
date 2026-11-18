# 6.4 · Cases and sensitivity

**Time:** 35 minutes · **Before this:** [6.3](03-the-idea-model.md).

## Read

Priya's numbers are guesses. Two tools show what happens if the guesses are wrong.

### Cases: "what if several things go badly at once?"

A **case** is a named set of changes (**shocks**) to her inputs. The "worst case" is:
conversion × 0.7, variable cost × 1.15, retention −10 points. Each case **prints** its
shocks next to its result, so nobody has to wonder what "worst" assumed. These sizes are
illustrative, not market research, and the code says so.

There are two kinds of shock:

| Kind | Example | Means |
|---|---|---|
| `scale` | conversion × 0.7 | multiply: 2 % → 1.4 % |
| `add` | retention −10 pts | add **percentage points**: 80 % → 70 % |

"Points" matter: retention −10 % would be 80 × 0.9 = 72 %, but −10 **points** is 70 %.

### Sensitivity: "which single guess matters most?"

Take one input, move it 10 % down and 10 % up, keep everything else the same, and see how
much the cash at the end changes. Do that for each of 8 inputs. The input with the
biggest **swing** is the one Priya most needs to get right. Sorted from biggest to
smallest, these bars make a **tornado chart** (it looks like a tornado: wide at the top).

## Do

Create `simulation_engine/cases.py`:

<!-- source: simulation_engine/cases.py:1-81 -->
```python
"""
The seven idea cases, defined as explicit, visible changes to the founder's inputs.

A "worst case" is only meaningful if you can see what it assumed. Each shock below is
data the UI prints next to the case, e.g. "conversion x0.7, variable cost x1.15,
retention -10 pts". These sizes are illustrative defaults, not market research.
"""

from dataclasses import dataclass
from decimal import Decimal

from .idea import IdeaInputs
from .money import HUNDRED, ZERO, clamp

PERCENT_FIELDS = {"conversion_rate", "monthly_retention"}


@dataclass(frozen=True)
class Shock:
    field: str
    op: str  # "scale" multiplies the input; "add" adds percentage points
    amount: Decimal

    def describe(self) -> str:
        if self.op == "scale":
            return f"{self.field} x{self.amount}"
        sign = "+" if self.amount >= 0 else ""
        return f"{self.field} {sign}{self.amount} pts"


@dataclass(frozen=True)
class Case:
    key: str
    label: str
    shocks: tuple[Shock, ...] = ()


def _s(field: str, factor: str) -> Shock:
    return Shock(field, "scale", Decimal(factor))


def _pts(field: str, points: str) -> Shock:
    return Shock(field, "add", Decimal(points))


CASES: tuple[Case, ...] = (
    Case("expected", "Expected (your inputs)"),
    Case("best", "Best case", (_s("conversion_rate", "1.2"), _pts("monthly_retention", "5"))),
    Case(
        "worst",
        "Worst case",
        (
            _s("conversion_rate", "0.7"),
            _s("variable_cost_per_order", "1.15"),
            _pts("monthly_retention", "-10"),
        ),
    ),
    Case("reduced_demand", "Reduced demand", (_s("orders_per_customer_monthly", "0.75"),)),
    Case(
        "higher_costs",
        "Higher costs",
        (_s("variable_cost_per_order", "1.15"), _s("fixed_costs_monthly", "1.2")),
    ),
    Case("lower_conversion", "Lower conversion", (_s("conversion_rate", "0.7"),)),
    Case(
        "more_competition",
        "More competition",
        (_s("cost_per_visit", "1.4"), _s("price_per_order", "0.95")),
    ),
)


def apply_shocks(inputs: IdeaInputs, shocks: tuple[Shock, ...]) -> IdeaInputs:
    changes = {}
    for shock in shocks:
        value = changes.get(shock.field, getattr(inputs, shock.field))
        value = value * shock.amount if shock.op == "scale" else value + shock.amount
        if shock.field in PERCENT_FIELDS:
            value = clamp(value, ZERO, HUNDRED)  # a rate can't go below 0 % or above 100 %
        changes[shock.field] = max(ZERO, value)
    return inputs.changed(**changes)
```

Create `simulation_engine/sensitivity.py`:

<!-- source: simulation_engine/sensitivity.py:1-62 -->
```python
"""
One-at-a-time sensitivity: which single assumption moves the outcome most?

For each input we nudge it down and up by the same percentage (default 10 %), keep every
other input as entered, and record cash at the end of the horizon. The bigger the gap
("swing") between the two results, the more the business depends on getting that number
right. Sorted by swing, this is the data behind the tornado chart.

It ignores interactions (two inputs moving together); that's the price of being simple
enough to read.
"""

from decimal import Decimal

from .cases import PERCENT_FIELDS
from .catalog import INPUTS
from .idea import IdeaInputs, simulate_months
from .money import HUNDRED, ONE, ZERO, clamp, round2

SENSITIVE_FIELDS = (
    "price_per_order",
    "variable_cost_per_order",
    "fixed_costs_monthly",
    "marketing_spend_monthly",
    "cost_per_visit",
    "conversion_rate",
    "orders_per_customer_monthly",
    "monthly_retention",
)


def _nudged(value: Decimal, factor: Decimal, field: str) -> Decimal:
    nudged = value * factor
    return clamp(nudged, ZERO, HUNDRED) if field in PERCENT_FIELDS else max(ZERO, nudged)


def sensitivity(inputs: IdeaInputs, horizon: int, step_pct: Decimal) -> list[dict]:
    base_cash = simulate_months(inputs, horizon)[-1].cash
    down, up = ONE - step_pct / HUNDRED, ONE + step_pct / HUNDRED
    rows = []
    for field in SENSITIVE_FIELDS:
        value = getattr(inputs, field)
        low_input = _nudged(value, down, field)
        high_input = _nudged(value, up, field)
        cash_low = simulate_months(inputs.changed(**{field: low_input}), horizon)[-1].cash
        cash_high = simulate_months(inputs.changed(**{field: high_input}), horizon)[-1].cash
        rows.append(
            {
                "input": field,
                "label": INPUTS[field].label,
                "unit": INPUTS[field].unit,
                "value": str(value),
                "low_value": str(round2(low_input)),
                "high_value": str(round2(high_input)),
                "ending_cash_low": str(round2(cash_low)),
                "ending_cash_high": str(round2(cash_high)),
                "ending_cash_base": str(round2(base_cash)),
                "swing": str(round2(abs(cash_high - cash_low))),
            }
        )
    rows.sort(key=lambda row: Decimal(row["swing"]), reverse=True)
    return rows
```

## Check

```bash
python
```

```python
from decimal import Decimal as D
from simulation_engine.idea import IdeaInputs
from simulation_engine.sensitivity import sensitivity

priya = IdeaInputs(
    D("500"), D("300"), D("100000"), D("50000"), D("10"), D("2"), D("2"), D("80"), D("1000000")
)
for row in sensitivity(priya, 24, D("10")):
    print(row["label"], row["swing"])
```

(Press **Enter** twice after the last line: the empty line tells Python the loop is
finished.)

You should see:

```text
Monthly customer retention 2607893.70
Average order value 2001888.95
Variable cost per order 1201133.37
Cost per visit 808844.02
Visit-to-customer conversion 800755.58
Orders per customer 800755.58
Marketing spend 560755.58
Fixed costs 480000.00
```

So for Priya, **retention** matters most: 10 % more or fewer customers staying each month
changes her cash after two years by about ₹26 lakh. Her price comes next. Fixed costs,
the thing founders often worry about first, matter least. Type `exit()`.

## Line by line

### `cases.py`

- **Lines 1–7** · Docstring: a worst case is only meaningful if you can see it.
- **Lines 9–13** · Imports. `IdeaInputs` from the last lesson; helpers from `money`.
- **Line 15** · The inputs that are percentages. A **set** (curly brackets) because we
  only ever ask "is this field in it?".
- **Lines 18–22** · A `Shock`: which field, which operation, how much.
- **Lines 24–28** · `describe()` writes the shock as text: `conversion_rate x0.7` or
  `monthly_retention -10 pts`. For `add`, a `+` is added for positive amounts (negative
  numbers already print their `-`).
- **Lines 31–35** · A `Case`: key, label, and its shocks (none for "expected").
- **Lines 38–43** · Two tiny helpers so the table below stays short: `_s` makes a scale
  shock, `_pts` an add shock.
- **Lines 46–70** · The seven cases. Read them like a table: "best" = conversion × 1.2
  and retention +5 points, and so on. A tuple with one shock needs a trailing comma, like
  line 58: `(_s(...),)`.
- **Line 73** · `apply_shocks` returns **new** inputs with the shocks applied.
- **Line 74** · The changes so far, as a dictionary.
- **Lines 75–76** · For each shock, start from the value already changed by an earlier
  shock, or else the original. `getattr(inputs, "conversion_rate")` reads a field by its
  **name as text**.
- **Line 77** · Multiply or add.
- **Lines 78–79** · A rate can't go below 0 % or above 100 %: 98 % + 5 points is 100 %,
  not 103 %.
- **Line 80** · And nothing goes below 0.
- **Line 81** · A copy of the inputs with all the changes.

### `sensitivity.py`

- **Lines 1–11** · Docstring: what it does, and its limit (it moves one input at a time,
  so it misses two inputs moving together).
- **Lines 13–18** · Imports.
- **Lines 20–29** · The eight inputs we test. (Initial investment and the founder's
  estimate are left out: they don't drive the business.)
- **Lines 32–34** · Nudge one value by a factor, then keep it in range (0–100 for
  percentages, at least 0 for everything else).
- **Line 37** · `sensitivity(inputs, horizon, step_pct)`.
- **Line 38** · Cash at the end with the inputs unchanged: `[-1]` is the last month.
- **Line 39** · With a step of 10: `down` = 0.9 and `up` = 1.1. Two values on one line.
- **Line 41** · For each input...
- **Lines 42–44** · ...its value, nudged down and up...
- **Lines 45–46** · ...and the ending cash for each. `**{field: low_input}` passes a
  keyword argument whose **name** is in a variable.
- **Lines 47–60** · One row for the table: the input, its values, the three ending cash
  amounts, and the swing (`abs` makes it positive).
- **Line 61** · Sort by swing, biggest first. `key=lambda row: Decimal(row["swing"])`
  sorts by the swing **as a number**. (Sorting the text would put "9" after "10000".)
- **Line 62** · Return the rows.

## If it didn't work

| You see | Fix |
|---|---|
| `ImportError: cannot import name 'IdeaInputs'` | Check `idea.py` from lesson 6.3 is saved. |
| `TypeError: 'Shock' object is not iterable` | A one-shock case is missing its trailing comma: `(_s(...),)`. |

## Quiz

1. Retention is 80 %. What is it after a `-10 pts` shock? After a `scale 0.9` shock?
2. Why does line 61 convert the swing back to a `Decimal` before sorting?
3. What does sensitivity **not** tell you?

---

**Next:** [6.5 · Outages, part 1: checkout](05-outages-checkout.md)

<details><summary>Quiz answers</summary>

1. 70 % and 72 %.
2. The swing is stored as text; text sorts letter by letter, which puts numbers in the
   wrong order.
3. What happens when two inputs change together.

</details>
