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
