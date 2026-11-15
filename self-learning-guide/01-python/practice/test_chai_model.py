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
