# 1.11 · Mini project: chai stall cash, month by month

**Time:** 45 minutes · **Before this:** lessons 1.1–1.10.

## 📖 Read

Meena wants to open a chai stall. She has **₹20,000** saved. She asks:
*"If I sell 1,500 cups a month and rent is ₹15,000, how long will my money last?"*

You'll build a tiny **simulation**: a program that steps through time, month by month,
using exact rules:

```
profit this month = cups × (price − cost) − rent
cash at end of month = cash last month + profit this month
```

This is the **same idea** as the real AI WarRoom Idea Simulator (Part 6), just smaller.
You'll use dataclasses (1.6), Decimal (1.8), loops (1.4), functions (1.5) and tests
(1.10) together.

**Work it out by hand first** (always!):
- Each cup earns 15 − 6.50 = **₹8.50**.
- 1,500 cups × 8.50 = **₹12,750** a month.
- Minus rent 15,000 = **−₹2,250** a month. Meena loses money every month.
- ₹20,000 ÷ 2,250 = 8.9 months, so she runs out of cash in **month 9**.

## ⌨️ Do

Make `chai_model.py`:

<!-- source: self-learning-guide/01-python/practice/chai_model.py:1-52 -->
```python
# Mini project: how much cash will a new chai stall have, month by month?
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StallPlan:
    price_per_cup: Decimal
    cost_per_cup: Decimal
    cups_per_month: Decimal
    rent_per_month: Decimal
    starting_cash: Decimal


@dataclass(frozen=True)
class Month:
    number: int
    profit: Decimal
    cash: Decimal


def simulate(plan: StallPlan, months: int) -> list[Month]:
    """Cash at the end of each month: last month's cash + this month's profit."""
    results = []
    cash = plan.starting_cash
    for number in range(1, months + 1):
        profit = (
            plan.cups_per_month * (plan.price_per_cup - plan.cost_per_cup) - plan.rent_per_month
        )
        cash = cash + profit
        results.append(Month(number, profit, cash))
    return results


def first_month_out_of_cash(months: list[Month]) -> int | None:
    for month in months:
        if month.cash < 0:
            return month.number
    return None


if __name__ == "__main__":
    plan = StallPlan(
        price_per_cup=Decimal("15"),
        cost_per_cup=Decimal("6.5"),
        cups_per_month=Decimal("1500"),
        rent_per_month=Decimal("15000"),
        starting_cash=Decimal("20000"),
    )
    for month in simulate(plan, 6):
        print(f"Month {month.number}: profit {month.profit}, cash {month.cash}")
    print("Runs out of cash in month:", first_month_out_of_cash(simulate(plan, 24)))
```

```bash
python chai_model.py
```

✅ You should see:

```text
Month 1: profit -2250.0, cash 17750.0
Month 2: profit -2250.0, cash 15500.0
Month 3: profit -2250.0, cash 13250.0
Month 4: profit -2250.0, cash 11000.0
Month 5: profit -2250.0, cash 8750.0
Month 6: profit -2250.0, cash 6500.0
Runs out of cash in month: 9
```

These match the hand calculation. Now make `test_chai_model.py` so the computer keeps
checking it:

<!-- source: self-learning-guide/01-python/practice/test_chai_model.py:1-29 -->
```python
# Tests with answers worked out by hand first.
from decimal import Decimal

from chai_model import StallPlan, first_month_out_of_cash, simulate

PLAN = StallPlan(
    price_per_cup=Decimal("15"),
    cost_per_cup=Decimal("6.5"),
    cups_per_month=Decimal("1500"),
    rent_per_month=Decimal("15000"),
    starting_cash=Decimal("20000"),
)


def test_profit_by_hand():
    # Each cup earns 15 - 6.5 = 8.5. 1500 cups x 8.5 = 12,750. Minus rent 15,000 = -2,250.
    first = simulate(PLAN, 1)[0]
    assert first.profit == Decimal("-2250")
    assert first.cash == Decimal("17750")


def test_cash_runs_out_in_month_9():
    # 20,000 - 2,250 x 9 = -250, the first month below zero.
    assert first_month_out_of_cash(simulate(PLAN, 24)) == 9


def test_more_cups_means_never_out_of_cash():
    busy = StallPlan(Decimal("15"), Decimal("6.5"), Decimal("2000"), Decimal("15000"), Decimal("0"))
    assert first_month_out_of_cash(simulate(busy, 24)) is None
```

```bash
pytest test_chai_model.py
```

✅ `3 passed`.

## 🔍 Line by line

### `chai_model.py`

**Lines 2–3** · Imports: `dataclass` for our blueprints, `Decimal` for exact money.

**Lines 6–12** · `StallPlan` holds Meena's inputs: five numbers, all Decimal. It's
frozen, so a simulation can't change her plan by accident.

**Lines 15–19** · `Month` holds the result for one month: its number, profit and cash.

**Line 22** · `simulate` takes a plan and how many months to simulate, and returns a
**list of Months** (`-> list[Month]`).

**Line 23** · The docstring states the rule in words.

**Line 24** · An empty list to collect each month's result.

**Line 25** · Cash starts at Meena's savings.

**Line 26** · `range(1, months + 1)` counts 1, 2, 3 ... up to `months`. `range` stops
**before** its second number, which is why we write `months + 1`.

**Lines 27–29** · This month's profit. The round brackets let one long sum continue over
several lines.

**Line 30** · The key line of any simulation: new cash = old cash + this month's profit.
Next time round the loop, `cash` already holds this month's ending cash.

**Line 31** · Make a `Month` result and add it to the list.

**Line 32** · After the loop, return all the months.

**Line 35** · `-> int | None` means "returns a whole number, **or** None".

**Lines 36–38** · Go through the months in order; at the first one with negative cash,
return its number. `return` stops the function immediately.

**Line 39** · If the loop finished without finding one, cash never ran out, so return
`None`.

**Line 42** · `if __name__ == "__main__":` means "only run the lines below when this file
is run **directly** (`python chai_model.py`), not when another file imports it". Without
it, running the tests would also print the table. AI WarRoom's `manage.py` uses the same
line.

**Lines 43–49** · Meena's plan. Every number is `Decimal("...")` with quotes.

**Lines 50–51** · Simulate 6 months and print each one with an f-string.

**Line 52** · Simulate 24 months and ask when cash runs out.

### `test_chai_model.py`

**Line 4** · Import the things we test.

**Lines 6–12** · One plan shared by the tests. A name in ALL CAPITALS means "a fixed
value, don't change it" (a **constant**).

**Lines 15–19** · Check month 1 against the hand calculation (the comment shows the
working). `[0]` takes the first (only) month from the list.

**Lines 22–24** · Check the "runs out in month 9" answer.

**Lines 27–29** · A different plan with 2,000 cups: each month earns 17,000 − 15,000 =
+2,000, so cash never goes below zero. Here the fields are passed **by position** (in the
order they're listed in the class) instead of by name.

## 🎯 Challenge (optional)

1. Meena could sell 1,800 cups a month. Does she ever run out of cash?
2. Add a field `price_rise_after_month_6` and use it inside the loop. (Hint: `if number > 6:`.)
3. Write a test for your change **before** you change the code.

## ❓ Quiz

1. Why is `StallPlan` frozen?
2. What does `range(1, 4)` count?
3. Why do the tests have the hand calculation in a comment?

---

**Part 1 done! 🎉 You can now read most of the Python in AI WarRoom.**
Next: [Part 2 · How the web works](../02-web/README.md)

<details><summary>Quiz answers</summary>

1. So no code can change the founder's inputs during a simulation.
2. 1, 2, 3 (it stops before 4).
3. So a reader can check that the expected value is really right, not just copied from
   the program's output.

</details>
