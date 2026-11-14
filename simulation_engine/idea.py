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
