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
