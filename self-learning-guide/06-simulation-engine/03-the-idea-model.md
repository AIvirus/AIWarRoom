# 6.3 · The idea model

**Time:** 45 minutes · **Before this:** [6.2](02-money-helpers.md).

## Read

This file is lesson 6.1's Example 1, written in Python. Read its docstring (lines 4–13)
side by side with your paper: it's the same chain of steps.

New Python in this lesson:

| Code | Means |
|---|---|
| `@classmethod` | A method you call on the **class**, not on one object: `IdeaInputs.from_values(...)`. Often used to build objects in a special way. |
| `dataclasses.replace(obj, x=1)` | A **copy** of a frozen object with one field changed. The original is untouched. |
| `lambda m: m.cash` | A tiny function with no name: "given `m`, return `m.cash`". |
| `next(generator, None)` | The first item a loop produces, or `None` if it produces nothing. |
| `min(items, key=...)` | The item with the smallest key, e.g. the month with the least cash. |

## Do

Create `simulation_engine/idea.py` in three pieces.

### Piece 1: inputs and months (lines 1–58)

<!-- source: simulation_engine/idea.py:1-58 -->
```python
"""
Idea Simulator: a month-by-month model of a business that hasn't launched yet.

The chain of cause and effect, one line per month:

    CAC             = cost_per_visit / conversion        (lower conversion => dearer customers)
    new customers   = marketing_spend / CAC
    customers       = last month's customers x retention + new customers
    orders          = customers x orders_per_customer
    revenue         = orders x price
    gross profit    = revenue - orders x variable_cost
    operating result= gross profit - fixed costs - marketing spend
    cash            = last month's cash + operating result   (month 0 cash = investment)

Everything is an expected value, so "customers" can be fractional; screens round it.
What's deliberately NOT modelled: price elasticity (price and demand are independent
inputs), taxes, payment timing, seasonality.
"""

from dataclasses import dataclass, fields, replace
from decimal import Decimal

from .money import HUNDRED, ONE, ZERO, display, metric, pct


@dataclass(frozen=True)
class IdeaInputs:
    price_per_order: Decimal
    variable_cost_per_order: Decimal
    fixed_costs_monthly: Decimal
    marketing_spend_monthly: Decimal
    cost_per_visit: Decimal
    conversion_rate: Decimal  # percent, e.g. 2.5
    orders_per_customer_monthly: Decimal
    monthly_retention: Decimal  # percent, e.g. 80
    initial_investment: Decimal
    expected_orders_monthly: Decimal | None = None  # the founder's own estimate

    @classmethod
    def from_values(cls, values: dict[str, Decimal]) -> "IdeaInputs":
        """Build from assumption values keyed like the catalogue."""
        kwargs = {f.name: values.get(f.name) for f in fields(cls)}
        return cls(**kwargs)

    def changed(self, **changes) -> "IdeaInputs":
        return replace(self, **changes)


@dataclass(frozen=True)
class Month:
    month: int
    new_customers: Decimal
    customers: Decimal
    orders: Decimal
    revenue: Decimal
    gross_profit: Decimal
    operating_result: Decimal
    cash: Decimal
```

### Piece 2: playing the months forward (lines 61–97)

<!-- source: simulation_engine/idea.py:61-97 -->
```python
def customer_acquisition_cost(inputs: IdeaInputs) -> Decimal | None:
    """Rupees spent to win one customer. None when conversion is 0 (nobody converts)."""
    if inputs.conversion_rate <= ZERO:
        return None
    return inputs.cost_per_visit / pct(inputs.conversion_rate)


def new_customers_per_month(inputs: IdeaInputs) -> Decimal:
    cac = customer_acquisition_cost(inputs)
    if cac is None:
        return ZERO
    if cac == ZERO:
        # Free traffic that converts is a modelling error, not infinite customers.
        return ZERO
    return inputs.marketing_spend_monthly / cac


def simulate_months(inputs: IdeaInputs, horizon: int) -> list[Month]:
    retention = pct(inputs.monthly_retention)
    unit_margin = inputs.price_per_order - inputs.variable_cost_per_order
    new = new_customers_per_month(inputs)

    months = []
    customers, cash = ZERO, inputs.initial_investment
    for month in range(1, horizon + 1):
        customers = customers * retention + new
        orders = customers * inputs.orders_per_customer_monthly
        revenue = orders * inputs.price_per_order
        gross_profit = orders * unit_margin
        operating = gross_profit - inputs.fixed_costs_monthly - inputs.marketing_spend_monthly
        cash = cash + operating
        months.append(Month(month, new, customers, orders, revenue, gross_profit, operating, cash))
    return months


def first_month(months: list[Month], condition) -> int | None:
    return next((m.month for m in months if condition(m)), None)
```

### Piece 3: the headline numbers (lines 100–194)

<!-- source: simulation_engine/idea.py:100-194 -->
```python
def summarise(inputs: IdeaInputs, months: list[Month]) -> dict[str, dict]:
    """The headline numbers for one case, in the shared metric() shape."""
    cac = customer_acquisition_cost(inputs)
    unit_margin = inputs.price_per_order - inputs.variable_cost_per_order
    retention = pct(inputs.monthly_retention)

    # Lifetime: a customer who stays with probability r each month stays 1/(1-r) months
    # on average. At 100 % retention the lifetime (and so LTV) is unbounded: not shown.
    lifetime = ONE / (ONE - retention) if retention < ONE else None
    ltv = (
        unit_margin * inputs.orders_per_customer_monthly * lifetime
        if lifetime is not None
        else None
    )
    ltv_to_cac = ltv / cac if (ltv is not None and cac) else None

    lowest = min(months, key=lambda m: m.cash)
    last = months[-1]
    new = new_customers_per_month(inputs)
    steady_orders = (
        new / (ONE - retention) * inputs.orders_per_customer_monthly if retention < ONE else None
    )

    return {
        "cac": metric("Customer acquisition cost", cac, "INR/customer"),
        "new_customers_monthly": metric("New customers per month", new, "customers/month"),
        "contribution_per_order": metric("Contribution per order", unit_margin, "INR/order"),
        "customer_lifetime_value": metric("Customer lifetime value", ltv, "INR/customer"),
        "ltv_to_cac": metric("Lifetime value to CAC", ltv_to_cac, "ratio"),
        "steady_state_orders": metric(
            "Orders/month once growth levels off", steady_orders, "orders/month"
        ),
        "final_month_orders": metric("Orders in final month", last.orders, "orders/month"),
        "revenue_total": metric("Revenue over horizon", sum(m.revenue for m in months), "INR"),
        "operating_result_total": metric(
            "Operating result over horizon", sum(m.operating_result for m in months), "INR"
        ),
        "first_profitable_month": metric(
            "First month with an operating profit",
            first_month(months, lambda m: m.operating_result >= ZERO),
            "month",
        ),
        "payback_month": metric(
            "Month cash is back to the initial investment",
            first_month(months, lambda m: m.cash >= inputs.initial_investment),
            "month",
        ),
        "lowest_cash": metric("Lowest cash balance", lowest.cash, "INR"),
        "lowest_cash_month": metric("Month of lowest cash", lowest.month, "month"),
        "funding_gap": metric(
            "Extra funding needed beyond the investment", max(ZERO, -lowest.cash), "INR"
        ),
        "cash_out_month": metric(
            "Month cash runs out", first_month(months, lambda m: m.cash < ZERO), "month"
        ),
        "ending_cash": metric("Cash at end of horizon", last.cash, "INR"),
    }


def timeline(months: list[Month]) -> list[dict]:
    return [
        {
            "month": m.month,
            "customers": display(m.customers),
            "orders": display(m.orders),
            "revenue": display(m.revenue),
            "gross_profit": display(m.gross_profit),
            "operating_result": display(m.operating_result),
            "cash": display(m.cash),
        }
        for m in months
    ]


def funnel_check(inputs: IdeaInputs, months: list[Month]) -> dict | None:
    """
    Compare the founder's expected orders with what their own funnel numbers support.

    It's the most useful honesty check in the model: "you expect 3,000 orders a month;
    your marketing budget and conversion support about 1,840."
    """
    if inputs.expected_orders_monthly is None or not months:
        return None
    at_month = min(6, len(months))
    modelled = months[at_month - 1].orders
    expected = inputs.expected_orders_monthly
    gap = (expected - modelled) / expected * HUNDRED if expected > ZERO else None
    return {
        "expected_orders": metric("Your expected orders", expected, "orders/month"),
        "modelled_orders": metric(
            f"Orders the funnel supports by month {at_month}", modelled, "orders/month"
        ),
        "gap_pct": metric("How far your estimate is above the model", gap, "%"),
        "month": at_month,
    }
```

## Check

Check the code against your paper from lesson 6.1:

```bash
python
```

```python
from decimal import Decimal as D
from simulation_engine.idea import IdeaInputs, simulate_months

priya = IdeaInputs(
    D("500"), D("300"), D("100000"), D("50000"), D("10"), D("2"), D("2"), D("80"), D("1000000")
)
for m in simulate_months(priya, 4):
    print(m.month, m.customers, m.orders, m.operating_result, m.cash)
```

(Press **Enter** twice after the `print` line.) You should see:

```text
1 100.00 200.00 -110000.00 890000.00
2 180.000 360.000 -78000.000 812000.000
3 244.0000 488.0000 -52400.0000 759600.0000
4 295.20000 590.40000 -31920.00000 727680.00000
```

The same numbers as your paper. The extra zeros grow because Decimal remembers how many
decimals went into each multiplication (× 0.80 adds two each month); the **value** is
identical: 244.0000 is 244. Type `exit()`.

## Line by line

### Piece 1

- **Lines 1–18** · The docstring: the model in eight lines, plus what it deliberately
  **doesn't** model (price changes don't change demand, no taxes, no seasons). Being
  open about limits is part of being honest.
- **Line 20** · `dataclass`, `fields` (lists a dataclass's fields) and `replace`.
- **Line 23** · Our money helpers. The `.` in `.money` means "from this same package".
- **Lines 26–37** · `IdeaInputs`: the ten numbers of Priya's table, each a Decimal. The
  comments remind you that percentages are written like `2.5`.
  `expected_orders_monthly` is optional (`= None`): only the funnel check uses it.
- **Lines 39–43** · `from_values` builds `IdeaInputs` from a dictionary like
  `{"price_per_order": Decimal("500"), ...}`. Line 42 loops over the class's fields and
  picks each one from the dictionary (`None` if missing); line 43 passes them all as
  keyword arguments with `**`.
- **Lines 45–46** · `changed(...)`: a copy with some values changed. Cases and
  sensitivity (lesson 6.4) use it to try "what if conversion were lower?".
- **Lines 49–58** · `Month`: one row of your paper table.

### Piece 2

- **Lines 61–65** · CAC = cost per visit ÷ conversion. If conversion is 0, nobody ever
  converts: there's no CAC, so return `None` instead of dividing by zero (which would
  crash).
- **Lines 68–75** · New customers per month = marketing ÷ CAC. If there's no CAC, or
  the CAC is 0 (free visits that convert, which can't really happen), return 0.
- **Line 78** · `simulate_months(inputs, horizon)`: play `horizon` months forward.
- **Lines 79–81** · Things that are the same every month: retention as a fraction, the
  contribution per order, the new customers.
- **Line 83** · An empty list for the months.
- **Line 84** · Start with 0 customers and the initial investment as cash. Two variables
  set on one line.
- **Line 85** · `range(1, horizon + 1)` counts 1, 2, ... horizon.
- **Lines 86–91** · Exactly your paper's columns: customers, orders, revenue, gross
  profit, the month's result, and cash.
- **Line 92** · Save the month.
- **Line 93** · Return them all.
- **Lines 96–97** · `first_month(months, condition)`: the first month for which
  `condition` is true, or `None`. For example
  `first_month(months, lambda m: m.cash < ZERO)` = "when does cash run out?".

### Piece 3

- **Line 100** · `summarise`: all the headline numbers for one case.
- **Lines 102–104** · CAC, contribution per order, retention as a fraction.
- **Lines 106–108** · Average lifetime = 1 ÷ (1 − retention) (lesson 6.1, Step 5). At
  100 % retention nobody ever leaves; the lifetime is endless, so `None`.
- **Lines 109–113** · LTV = contribution × orders per month × lifetime, if there is a
  lifetime.
- **Line 114** · LTV ÷ CAC, only if both exist (`cac` is "truthy" only when it's not
  `None` and not 0).
- **Line 116** · The month with the lowest cash.
- **Line 117** · `months[-1]` is the last month (negative positions count from the end).
- **Lines 118–121** · The level customers settle at (Step 4), times orders per customer.
- **Lines 123–156** · The result dictionary. Each value is a `metric(label, value, unit)`.
  Read the labels: they're the sentences the screens show. Some to notice:
  - **133** · `sum(m.revenue for m in months)` adds up a column.
  - **137–141** · First month with a profit: `>= ZERO`.
  - **142–146** · **Payback**: the month cash is back to what you started with.
  - **149–151** · **Funding gap**: if cash goes below zero, by how much. `-lowest.cash`
    turns −50,000 into 50,000; `max(ZERO, ...)` keeps it at 0 when cash never goes
    negative.
- **Lines 159–171** · `timeline`: one small dictionary per month for the charts, using
  `display` (floats are fine for drawing).
- **Lines 174–180** · `funnel_check` and its docstring: "you expect 3,000 orders; your
  marketing supports about 1,840". A gentle reality check.
- **Lines 181–182** · No estimate, or no months? Nothing to compare.
- **Line 183** · Compare at month 6 (or earlier if the horizon is shorter).
- **Line 184** · Orders the model gives for that month. `at_month - 1` because lists
  count from 0.
- **Lines 185–186** · How far the estimate is above the model, in %. If the estimate
  is 0, there's nothing to divide by: `None`.
- **Lines 187–194** · Return the comparison.

## If it didn't work

| You see | Fix |
|---|---|
| `TypeError: IdeaInputs.__init__() missing 1 required positional argument` | You gave fewer than the 9 required numbers in the Check step. |
| Month 3 shows 244 but cash is wrong | Line 91 must add `operating` to the **previous** cash. |
| `ImportError: attempted relative import with no known parent package` | Run `python` from `my-warroom` and import `simulation_engine.idea`, not `idea`. |

## Quiz

1. Why does `customer_acquisition_cost` return `None` when conversion is 0?
2. What does `months[-1]` mean?
3. What's the difference between "first profitable month" and "payback month"?

---

**Next:** [6.4 · Cases and sensitivity](04-cases-and-sensitivity.md)

<details><summary>Quiz answers</summary>

1. Dividing by zero would crash, and "the cost of a customer you can never win" has no
   honest number.
2. The last item in the list.
3. First profitable month: one month's result is ≥ 0. Payback: all the money lost so far
   has been earned back (cash ≥ the initial investment).

</details>
