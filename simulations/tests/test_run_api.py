"""Running scenarios through the API: snapshots, history, failures and live preview."""

from decimal import Decimal as D

import pytest

from businesses.models import BusinessComponent, FinancialAssumption
from simulations.models import Scenario, SimulationRun

pytestmark = pytest.mark.django_db

SHOP_INPUTS = {
    "daily_orders": "2400",
    "average_order_value": "600",
    "contribution_margin": "25",
    "hourly_capacity": "200",
    "primary_gateway_share": "100",
    "recapture_rate": "30",
}


@pytest.fixture
def ready_shop(alice_shop):
    for key, value in SHOP_INPUTS.items():
        FinancialAssumption.objects.create(business=alice_shop, key=key, value=D(value))
    gateway = BusinessComponent.objects.create(
        business=alice_shop, key="payment-gateway", name="Primary PG", kind="payment"
    )
    checkout = BusinessComponent.objects.create(
        business=alice_shop, key="checkout", name="Checkout", kind="storefront"
    )
    checkout.depends_on.add(gateway)
    return alice_shop


@pytest.fixture
def pg_scenario(ready_shop):
    return Scenario.objects.create(
        business=ready_shop,
        template_key="payment_gateway_outage",
        name="PG down",
        parameters={"outage_hours": "2", "demand_profile": "uniform", "start_hour": "0"},
    )


def metric(run_json, case_key, key):
    case = next(r for r in run_json["results"] if r["case_key"] == case_key)
    return D(case["metrics"][key]["value"])


def test_run_saves_snapshot_and_one_result_per_strategy(api, pg_scenario):
    response = api.post(f"/api/v1/scenarios/{pg_scenario.id}/run/")
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["status"] == "completed"
    assert body["engine_version"] == "1.0.0"
    assert [r["case_key"] for r in body["results"]] == ["wait", "backup", "queue_retry"]
    # Same hand-calculated numbers as the engine tests (2 h outage, 100 orders/hour).
    assert metric(body, "wait", "lost_contribution") == D("21000.00")
    assert body["input_snapshot"]["assumptions"]["daily_orders"]["value"] == "2400"
    assert body["summary"]["failed_component"] == "payment-gateway"
    assert body["results"][0]["timeline"][0]["components"]["checkout"] == 0.0


def test_editing_the_business_never_changes_a_past_run(api, ready_shop, pg_scenario):
    first = api.post(f"/api/v1/scenarios/{pg_scenario.id}/run/").json()
    FinancialAssumption.objects.filter(business=ready_shop, key="daily_orders").update(value=4800)
    second = api.post(f"/api/v1/scenarios/{pg_scenario.id}/run/").json()

    old = api.get(f"/api/v1/runs/{first['id']}/").json()
    assert metric(old, "wait", "affected_orders") == D("200.00")
    assert metric(second, "wait", "affected_orders") == D("400.00")
    assert old["input_hash"] != second["input_hash"]


def test_identical_inputs_give_identical_hash(api, pg_scenario):
    a = api.post(f"/api/v1/scenarios/{pg_scenario.id}/run/").json()
    b = api.post(f"/api/v1/scenarios/{pg_scenario.id}/run/").json()
    assert a["input_hash"] == b["input_hash"]
    assert a["id"] != b["id"]  # but each run is its own record


def test_missing_inputs_return_422_and_record_a_failed_run(api, alice_shop):
    scenario = Scenario.objects.create(
        business=alice_shop, template_key="warehouse_shutdown", name="Flood", parameters={}
    )
    response = api.post(f"/api/v1/scenarios/{scenario.id}/run/")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "simulation_input_error"
    assert "daily_orders" in error["message"]
    failed = SimulationRun.objects.get(scenario=scenario)
    assert failed.status == "failed" and "daily_orders" in failed.error


def test_preview_answers_without_saving(api, ready_shop):
    payload = {
        "business": str(ready_shop.id),
        "template_key": "payment_gateway_outage",
        "parameters": {"outage_hours": "2", "demand_profile": "uniform"},
        "assumptions": {"average_order_value": "1200"},  # a slider doubled the AOV
    }
    response = api.post("/api/v1/simulate/preview/", payload, format="json")
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["saved"] is False
    wait = body["cases"][0]
    assert D(wait["metrics"]["lost_revenue"]["value"]) == D("168000.00")  # 140 x 1,200
    assert SimulationRun.objects.count() == 0
    # The saved assumption is untouched.
    assert ready_shop.assumptions.get(key="average_order_value").value == 600


def test_preview_rejects_out_of_range_slider_values(api, ready_shop):
    payload = {
        "business": str(ready_shop.id),
        "template_key": "payment_gateway_outage",
        "assumptions": {"contribution_margin": "180"},
    }
    response = api.post("/api/v1/simulate/preview/", payload, format="json")
    assert response.status_code == 422
    assert "contribution_margin" in response.json()["error"]["fields"]


def test_preview_and_run_are_scoped_to_the_users_org(api, bob_shop):
    payload = {"business": str(bob_shop.id), "template_key": "warehouse_shutdown"}
    assert api.post("/api/v1/simulate/preview/", payload, format="json").status_code == 404
    bobs = Scenario.objects.create(
        business=bob_shop, template_key="warehouse_shutdown", name="x", parameters={}
    )
    assert api.post(f"/api/v1/scenarios/{bobs.id}/run/").status_code == 404


def test_idea_run_includes_sensitivity_and_funnel_check(api, alice_idea):
    inputs = {
        "price_per_order": "500", "variable_cost_per_order": "300",
        "fixed_costs_monthly": "100000", "marketing_spend_monthly": "50000",
        "cost_per_visit": "10", "conversion_rate": "2", "orders_per_customer_monthly": "2",
        "monthly_retention": "80", "initial_investment": "1000000",
        "expected_orders_monthly": "1000",
    }  # fmt: skip
    for key, value in inputs.items():
        FinancialAssumption.objects.create(business=alice_idea, key=key, value=D(value))
    scenario = Scenario.objects.create(
        business=alice_idea, template_key="idea_cases", name="Launch plan", parameters={}
    )
    body = api.post(f"/api/v1/scenarios/{scenario.id}/run/").json()
    assert len(body["results"]) == 7
    assert metric(body, "expected", "first_profitable_month") == 7
    assert body["summary"]["funnel_check"]["gap_pct"]["value"] == "26.21"
    assert len(body["summary"]["sensitivity"]) == 8
