"""The engine entry point: validation, case/strategy sets, warnings, component health."""

from decimal import Decimal as D

import pytest

from simulation_engine import runner

IDEA = {
    "price_per_order": "500",
    "variable_cost_per_order": "300",
    "fixed_costs_monthly": "100000",
    "marketing_spend_monthly": "50000",
    "cost_per_visit": "10",
    "conversion_rate": "2",
    "orders_per_customer_monthly": "2",
    "monthly_retention": "80",
    "initial_investment": "1000000",
    "expected_orders_monthly": "3000",
}
SHOP = {
    "daily_orders": "2400",
    "average_order_value": "600",
    "contribution_margin": "25",
    "hourly_capacity": "200",
    "primary_gateway_share": "70",
    "main_warehouse_share": "100",
    "recapture_rate": "30",
    "cancel_rate_per_delay_hour": "2",
    "max_cancel_rate": "30",
}
COMPONENTS = [
    {"key": "payment-gateway", "kind": "payment", "depends_on": []},
    {"key": "checkout", "kind": "storefront", "depends_on": ["payment-gateway"]},
    {"key": "revenue", "kind": "revenue", "depends_on": ["checkout"]},
]


def test_idea_run_returns_seven_cases_and_sensitivity():
    result = runner.run("idea_cases", IDEA, {"horizon_months": "12"})
    assert [c.case_key for c in result.cases] == [
        "expected", "best", "worst", "reduced_demand", "higher_costs",
        "lower_conversion", "more_competition",
    ]  # fmt: skip
    assert len(result.cases[0].timeline) == 12
    assert len(result.summary["sensitivity"]) == 8
    assert result.cases[2].assumptions  # worst case says what it assumed


def test_idea_warns_when_estimate_far_exceeds_funnel():
    result = runner.run("idea_cases", IDEA)
    assert any("above what your marketing budget" in w for w in result.warnings)


def test_missing_assumptions_are_named():
    partial = {k: v for k, v in SHOP.items() if k != "contribution_margin"}
    with pytest.raises(runner.EngineError, match="contribution_margin"):
        runner.run("payment_gateway_outage", partial)


def test_payment_run_compares_three_strategies_without_picking_a_winner():
    result = runner.run(
        "payment_gateway_outage", SHOP, {"outage_hours": "3", "demand_profile": "uniform"}
    )
    assert [c.case_key for c in result.cases] == ["wait", "backup", "queue_retry"]
    comparison = result.summary["comparison"]
    assert set(comparison) == {
        "rows", "lowest_total_impact", "lowest_response_cost", "fastest_recovery",
    }  # fmt: skip
    # Waiting costs nothing up front, but it is not the cheapest outcome overall.
    assert comparison["lowest_response_cost"] == "wait"
    impacts = {r["case_key"]: D(r["total_impact"]) for r in comparison["rows"]}
    assert impacts["wait"] > impacts[comparison["lowest_total_impact"]]


def test_component_health_propagates_one_hop_only():
    """70 % of payments use the broken gateway: checkout keeps 30 % health, revenue untouched."""
    result = runner.run(
        "payment_gateway_outage", SHOP, {"outage_hours": "3"}, components=COMPONENTS
    )
    first_hour = result.cases[0].timeline[0]["components"]  # "wait": fully down
    assert first_hour["payment-gateway"] == 0.0
    assert first_hour["checkout"] == 0.3
    assert "revenue" not in first_hour


def test_missing_component_falls_back_to_generic_node_with_warning():
    result = runner.run("warehouse_shutdown", SHOP, {"outage_hours": "2"})
    assert result.summary["failed_component"] == "warehouse"
    assert any("No 'warehouse' component" in w for w in result.warnings)


def test_late_backup_warning():
    result = runner.run(
        "payment_gateway_outage", SHOP, {"outage_hours": "1", "backup_switch_hours": "2"}
    )
    assert any("never helps" in w for w in result.warnings)


def test_runs_are_reproducible():
    a = runner.run("warehouse_shutdown", SHOP, {"outage_hours": "5"}, COMPONENTS)
    b = runner.run("warehouse_shutdown", SHOP, {"outage_hours": "5"}, COMPONENTS)
    assert a == b
