"""
Disruption model tests with hand-calculated values.

All cases use a UNIFORM day (2,400 orders/day = 100 orders every hour), all orders through
the failing component, average order value 600, contribution margin 25 %, and a 2-hour
outage starting at hour 0. Simple numbers so each result can be checked on paper.
"""

from decimal import Decimal as D

import pytest

from simulation_engine.disruption import (
    DisruptionInputs,
    backup_fraction,
    cancel_fraction,
    outage_fraction,
    simulate_checkout,
    simulate_fulfilment,
)

COMMON = dict(
    daily_orders=D("2400"),
    average_order_value=D("600"),
    contribution_margin=D("25"),
    affected_share=D("100"),
    outage_hours=D("2"),
    start_hour=0,
    horizon_hours=24,
    demand_profile="uniform",
    backup_switch_hours=D("0.5"),
    backup_capacity_per_hour=D("60"),
    backup_extra_cost_per_order=D("12"),
    backup_activation_cost=D("5000"),
    retry_success_rate=D("55"),
    retry_window_hours=D("24"),
    retry_cost_per_order=D("3"),
)
PAYMENT = DisruptionInputs(**COMMON, recapture_rate=D("30"))
WAREHOUSE = DisruptionInputs(
    **COMMON,
    hourly_capacity=D("200"),
    cancel_rate_per_delay_hour=D("2"),
    max_cancel_rate=D("30"),
)


def v(outcome, key):
    raw = outcome["metrics"][key]["value"]
    return D(raw) if raw is not None else None


# --- Time slicing ---------------------------------------------------------------------


def test_outage_and_backup_fractions_handle_part_hours():
    half = DisruptionInputs(**{**COMMON, "outage_hours": D("1.5")})
    assert [outage_fraction(half, t) for t in range(3)] == [1, D("0.5"), 0]
    # Backup live from 0.5 h to 1.5 h: half of hour 0, half of hour 1.
    assert [backup_fraction(half, t) for t in range(3)] == [D("0.5"), D("0.5"), 0]


# --- Checkout (payment gateway) -------------------------------------------------------


def test_payment_wait_by_hand():
    """
    Affected: 2 h x 100 = 200 orders. 30 % come back later: 60 recovered, 140 lost.
    Lost revenue 140 x 600 = 84,000. Lost contribution 25 % = 21,000. No response cost.
    """
    out = simulate_checkout(PAYMENT, "wait")
    assert v(out, "affected_orders") == D("200.00")
    assert v(out, "affected_value") == D("120000.00")
    assert v(out, "recovered_orders") == D("60.00")
    assert v(out, "lost_orders") == D("140.00")
    assert v(out, "lost_revenue") == D("84000.00")
    assert v(out, "lost_contribution") == D("21000.00")
    assert v(out, "total_impact") == D("21000.00")
    assert v(out, "hours_without_service") == D("2.00")


def test_affected_value_is_not_lost_revenue_is_not_lost_profit():
    out = simulate_checkout(PAYMENT, "wait")
    assert v(out, "affected_value") > v(out, "lost_revenue") > v(out, "lost_contribution")


def test_payment_backup_by_hand():
    """
    Backup switches on at 0.5 h with 60 orders/hour.
    Hour 0: 100 affected; last half-hour has 50 orders but only 30 capacity -> 30 via backup.
    Hour 1: 100 affected, 60 via backup.  Backup total 90, failed 110.
    Of the 110, 30 % come back: 33. Recovered = 90 + 33 = 123; lost 77.
    Lost contribution = 77 x 600 x 25 % = 11,550.
    Cost = 90 x 12 + 5,000 activation = 6,080.  Total impact 17,630.
    Fully down only for the first half hour.
    """
    out = simulate_checkout(PAYMENT, "backup")
    assert v(out, "orders_via_backup") == D("90.00")
    assert v(out, "recovered_orders") == D("123.00")
    assert v(out, "lost_orders") == D("77.00")
    assert v(out, "mitigation_cost") == D("6080.00")
    assert v(out, "total_impact") == D("17630.00")
    assert v(out, "hours_without_service") == D("0.50")


def test_payment_queue_retry_by_hand():
    """
    All 200 failed payments wait at most 2 h (< 24 h window), so all are queued.
    55 % succeed on retry: 110. The other 90 still get the natural 30 % recapture: 27.
    Recovered 137, lost 63 -> contribution lost 63 x 150 = 9,450. Cost 200 x 3 = 600.
    Total impact 10,050.
    """
    out = simulate_checkout(PAYMENT, "queue_retry")
    assert v(out, "payments_queued") == D("200.00")
    assert v(out, "recovered_orders") == D("137.00")
    assert v(out, "lost_orders") == D("63.00")
    assert v(out, "mitigation_cost") == D("600.00")
    assert v(out, "total_impact") == D("10050.00")


def test_retry_window_excludes_payments_that_waited_too_long():
    """Window 1.5 h: hour 0 waits 2 h (excluded), hour 1 waits 1 h (queued) -> 100 queued."""
    short = DisruptionInputs(**{**COMMON, "retry_window_hours": D("1.5")}, recapture_rate=D("30"))
    assert v(simulate_checkout(short, "queue_retry"), "payments_queued") == D("100.00")


def test_backup_that_switches_after_the_outage_does_nothing_and_costs_nothing():
    late = DisruptionInputs(**{**COMMON, "backup_switch_hours": D("3")}, recapture_rate=D("30"))
    wait, backup = simulate_checkout(late, "wait"), simulate_checkout(late, "backup")
    assert v(backup, "mitigation_cost") == 0
    assert v(backup, "lost_orders") == v(wait, "lost_orders")


def test_backup_never_recovers_more_than_its_capacity():
    tiny = DisruptionInputs(**{**COMMON, "backup_capacity_per_hour": D("5")}, recapture_rate=D("0"))
    out = simulate_checkout(tiny, "backup")
    assert v(out, "orders_via_backup") <= D("5") * 2


@pytest.mark.parametrize("strategy", ["wait", "backup", "queue_retry"])
def test_zero_outage_means_zero_impact(strategy):
    calm = DisruptionInputs(**{**COMMON, "outage_hours": D("0")}, recapture_rate=D("30"))
    out = simulate_checkout(calm, strategy)
    assert v(out, "affected_orders") == 0
    assert v(out, "total_impact") == 0


def test_zero_orders_does_not_divide_by_zero():
    empty = DisruptionInputs(**{**COMMON, "daily_orders": D("0")}, recapture_rate=D("30"))
    for strategy in ("wait", "backup", "queue_retry"):
        out = simulate_checkout(empty, strategy)
        assert v(out, "lost_orders") == 0


@pytest.mark.parametrize("strategy", ["wait", "backup", "queue_retry"])
def test_recovered_plus_lost_equals_affected(strategy):
    out = simulate_checkout(PAYMENT, strategy)
    assert v(out, "recovered_orders") + v(out, "lost_orders") == v(out, "affected_orders")


# --- Fulfilment (warehouse / courier) -------------------------------------------------


def test_cancellation_grows_per_hour_and_caps():
    assert cancel_fraction(WAREHOUSE, 0, "wait") == 0
    assert cancel_fraction(WAREHOUSE, 2, "wait") == D("0.04")
    assert cancel_fraction(WAREHOUSE, 40, "wait") == D("0.30")  # capped at 30 %
    # Notice keeps 55 % of would-be cancellations: 4 % x (1 - 0.55) = 1.8 %.
    assert cancel_fraction(WAREHOUSE, 2, "queue_retry") == D("0.018")


def test_warehouse_wait_by_hand():
    """
    Capacity 200/h, 100 orders/h arrive, warehouse down for hours 0 and 1.
      h0: nothing processed. Queue: [h0:100]
      h1: nothing processed. Queue: [h0:100, h1:100]
      h2: back. h0 orders waited 2 h -> 4 % cancel: 96 shipped, 4 cancelled (uses 96 cap).
          h1 orders waited 1 h -> 2 % cancel: 98 shipped, 2 cancelled (uses 98, 6 left).
          h2 orders: 6 shipped on time, 94 wait.
      h3: h2 leftovers waited 1 h -> 2 %: 92.12 shipped, 1.88 cancelled. h3's 100 ship on time.
          Queue empty at the end of hour 3 -> recovered after 4 hours.
    Delayed: 100 + 100 + 94 = 294.  Cancelled: 4 + 2 + 1.88 = 7.88.
    Lost revenue 7.88 x 600 = 4,728; lost contribution 1,182.
    """
    out = simulate_fulfilment(WAREHOUSE, "wait")
    assert v(out, "delayed_orders") == D("294.00")
    assert v(out, "lost_orders") == D("7.88")
    assert v(out, "recovered_orders") == D("286.12")
    assert v(out, "lost_revenue") == D("4728.00")
    assert v(out, "total_impact") == D("1182.00")
    assert v(out, "time_to_recovery") == 4
    assert v(out, "peak_backlog") == D("200.00")


def test_warehouse_queue_and_notify_by_hand():
    """
    Notice keeps 55 % of would-be cancellations (2 h -> 4 % becomes 1.8 %; 1 h -> 0.9 %).
      h2: h0 cohort 98.2 shipped / 1.8 cancelled; h1 cohort 99.1 / 0.9; capacity left 2.7
          -> 2.7 of h2's orders ship, 97.3 wait.
      h3: 97.3 waited 1 h -> 0.9 %: 0.8757 cancelled. Then h3's 100 ship.
    Cancelled 1.8 + 0.9 + 0.8757 = 3.5757 -> 3.58. Delayed 100 + 100 + 97.3 = 297.3.
    Cost 297.3 x 3 = 891.90. Lost contribution 3.5757 x 150 = 536.355.
    Total 891.90 + 536.355 = 1,428.26 (rounded).
    """
    out = simulate_fulfilment(WAREHOUSE, "queue_retry")
    assert v(out, "delayed_orders") == D("297.30")
    assert v(out, "lost_orders") == D("3.58")
    assert v(out, "mitigation_cost") == D("891.90")
    assert v(out, "total_impact") == D("1428.26")


def test_warehouse_backup_reduces_cancellations_and_charges_for_itself():
    wait = simulate_fulfilment(WAREHOUSE, "wait")
    backup = simulate_fulfilment(WAREHOUSE, "backup")
    assert v(backup, "lost_orders") < v(wait, "lost_orders")
    via_backup = v(backup, "orders_via_backup")
    assert v(backup, "mitigation_cost") == (via_backup * 12 + 5000).quantize(D("0.01"))


def test_capacity_shortfall_without_outage_is_not_blamed_on_the_outage():
    """If capacity is below demand every day, the outage's impact excludes that baseline."""
    strained = DisruptionInputs(
        **{**COMMON, "outage_hours": D("0")},
        hourly_capacity=D("90"),
        cancel_rate_per_delay_hour=D("2"),
        max_cancel_rate=D("30"),
    )
    out = simulate_fulfilment(strained, "wait")
    assert v(out, "lost_orders") == 0
    assert v(out, "time_to_recovery") == 0


def test_backlog_not_cleared_in_horizon_reports_no_recovery_time():
    slow = DisruptionInputs(
        **{**COMMON, "horizon_hours": 24},
        hourly_capacity=D("101"),
        cancel_rate_per_delay_hour=D("0"),
        max_cancel_rate=D("0"),
    )
    out = simulate_fulfilment(slow, "wait")
    assert v(out, "time_to_recovery") is None
    assert v(out, "backlog_at_end") > 0


def test_timeline_has_one_row_per_hour_and_running_impact_matches_total():
    out = simulate_fulfilment(WAREHOUSE, "wait")
    assert len(out["timeline"]) == 24
    assert out["timeline"][0]["health"] == 0.0  # down
    assert out["timeline"][3]["health"] == 1.0  # back
    assert D(str(out["timeline"][-1]["impact_cum"])) == v(out, "total_impact")
