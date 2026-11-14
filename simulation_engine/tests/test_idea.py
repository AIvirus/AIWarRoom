"""
Idea model tests. Every expected number is worked out by hand in the docstring, so a
student can check the maths on paper before trusting the code.

Reference business used throughout:
    price 500, variable cost 300  -> 200 contribution per order
    fixed 1,00,000/month, marketing 50,000/month
    cost per visit 10, conversion 2 %  -> CAC = 10 / 0.02 = 500
    new customers = 50,000 / 500 = 100 per month
    retention 80 %, 2 orders per customer per month
    initial investment 10,00,000
"""

from decimal import Decimal as D

import pytest

from simulation_engine.cases import CASES, apply_shocks
from simulation_engine.idea import IdeaInputs, funnel_check, simulate_months, summarise
from simulation_engine.sensitivity import sensitivity

BASE = IdeaInputs(
    price_per_order=D("500"),
    variable_cost_per_order=D("300"),
    fixed_costs_monthly=D("100000"),
    marketing_spend_monthly=D("50000"),
    cost_per_visit=D("10"),
    conversion_rate=D("2"),
    orders_per_customer_monthly=D("2"),
    monthly_retention=D("80"),
    initial_investment=D("1000000"),
    expected_orders_monthly=D("1000"),
)


def value(metrics, key):
    raw = metrics[key]["value"]
    return D(raw) if raw is not None else None


def test_first_three_months_by_hand():
    """
    Month 1: customers 100           orders 200  GP 40,000  result 40,000-150,000 = -110,000
    Month 2: customers 80+100 = 180  orders 360  GP 72,000  result -78,000
    Month 3: customers 144+100 = 244 orders 488  GP 97,600  result -52,400
    Cash after month 3: 10,00,000 - 110,000 - 78,000 - 52,400 = 7,59,600
    """
    m1, m2, m3 = simulate_months(BASE, 3)
    assert (m1.customers, m1.orders, m1.operating_result) == (D("100"), D("200"), D("-110000"))
    assert (m2.customers, m2.orders, m2.operating_result) == (D("180"), D("360"), D("-78000"))
    assert (m3.customers, m3.orders, m3.operating_result) == (D("244"), D("488"), D("-52400"))
    assert m3.cash == D("759600")


def test_unit_economics_by_hand():
    """
    CAC 500. Contribution per customer-month = 2 x 200 = 400.
    Average lifetime = 1 / (1 - 0.8) = 5 months -> LTV = 2,000 -> LTV/CAC = 4.
    Steady state: 100 / 0.2 = 500 customers -> 1,000 orders/month.
    """
    metrics = summarise(BASE, simulate_months(BASE, 24))
    assert value(metrics, "cac") == D("500.00")
    assert value(metrics, "customer_lifetime_value") == D("2000.00")
    assert value(metrics, "ltv_to_cac") == D("4.00")
    assert value(metrics, "steady_state_orders") == D("1000.00")


def test_first_profitable_month_by_hand():
    """
    Customers in month t = 500 x (1 - 0.8^t). Break-even needs GP >= 150,000, i.e. 750
    orders, i.e. 375 customers: 1 - 0.8^t >= 0.75  ->  t >= 6.2  ->  month 7.
    Month 6: 368.93 customers -> result -2,428.80.  Month 7: 395.14 -> result +8,056.96.
    """
    months = simulate_months(BASE, 24)
    assert months[5].operating_result == D("-2428.800")
    assert months[6].operating_result.quantize(D("0.01")) == D("8056.96")
    assert value(summarise(BASE, months), "first_profitable_month") == 7


def test_lowest_cash_and_funding_gap():
    """Cash falls until month 6 (last loss-making month), then rises. Investment covers it."""
    metrics = summarise(BASE, simulate_months(BASE, 24))
    assert value(metrics, "lowest_cash_month") == 6
    assert value(metrics, "funding_gap") == D("0.00")
    assert metrics["cash_out_month"]["value"] is None


def test_funding_gap_when_investment_is_too_small():
    small = BASE.changed(initial_investment=D("100000"))
    metrics = summarise(small, simulate_months(small, 24))
    assert value(metrics, "cash_out_month") == 1  # 1,00,000 - 1,10,000 < 0 in month 1
    assert value(metrics, "funding_gap") > 0


def test_zero_conversion_means_no_customers_not_a_crash():
    dead = BASE.changed(conversion_rate=D("0"))
    months = simulate_months(dead, 12)
    assert all(m.orders == 0 for m in months)
    metrics = summarise(dead, months)
    assert metrics["cac"]["value"] is None
    assert metrics["ltv_to_cac"]["value"] is None


def test_full_retention_has_no_lifetime_value():
    loyal = BASE.changed(monthly_retention=D("100"))
    metrics = summarise(loyal, simulate_months(loyal, 12))
    assert metrics["customer_lifetime_value"]["value"] is None
    assert metrics["steady_state_orders"]["value"] is None


def test_funnel_check_compares_estimate_with_model():
    """Expected 1,000/month vs month-6 model 737.856: (1000 - 737.856) / 1000 = 26.21 %."""
    check = funnel_check(BASE, simulate_months(BASE, 24))
    assert check["month"] == 6
    assert D(check["modelled_orders"]["value"]) == D("737.86")
    assert D(check["gap_pct"]["value"]) == D("26.21")


def test_cases_apply_their_shocks():
    by_key = {case.key: case for case in CASES}
    worst = apply_shocks(BASE, by_key["worst"].shocks)
    assert worst.conversion_rate == D("1.4")  # 2 x 0.7
    assert worst.variable_cost_per_order == D("345.00")  # 300 x 1.15
    assert worst.monthly_retention == D("70")  # 80 - 10 pts
    best = apply_shocks(BASE.changed(monthly_retention=D("98")), by_key["best"].shocks)
    assert best.monthly_retention == D("100")  # capped, never 103 %


def test_worst_case_is_worse_than_expected_which_is_worse_than_best():
    def ending(key):
        case = next(c for c in CASES if c.key == key)
        return simulate_months(apply_shocks(BASE, case.shocks), 24)[-1].cash

    assert ending("worst") < ending("expected") < ending("best")


def test_sensitivity_is_sorted_by_swing_and_symmetric_inputs_move_cash_both_ways():
    rows = sensitivity(BASE, 24, D("10"))
    swings = [D(r["swing"]) for r in rows]
    assert swings == sorted(swings, reverse=True)
    price = next(r for r in rows if r["input"] == "price_per_order")
    assert D(price["ending_cash_high"]) > D(price["ending_cash_base"]) > D(price["ending_cash_low"])
    assert price["low_value"] == "450.00" and price["high_value"] == "550.00"


@pytest.mark.parametrize("horizon", [1, 6, 60])
def test_same_inputs_same_output(horizon):
    assert simulate_months(BASE, horizon) == simulate_months(BASE, horizon)
