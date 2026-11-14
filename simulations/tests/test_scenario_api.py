import pytest

from businesses.models import FinancialAssumption

pytestmark = pytest.mark.django_db


def test_create_scenario_validates_and_fills_defaults(api, alice_shop):
    response = api.post(
        "/api/v1/scenarios/",
        {
            "business": str(alice_shop.id),
            "template_key": "warehouse_shutdown",
            "name": "Bhiwandi flood",
            "parameters": {"outage_hours": "6"},
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["kind"] == "disruption"
    assert body["parameters"]["outage_hours"] == "6"
    assert body["parameters"]["retry_window_hours"] == "24"
    assert "daily_orders" in body["missing_inputs"]


def test_missing_inputs_shrinks_as_assumptions_are_added(api, alice_shop):
    FinancialAssumption.objects.create(business=alice_shop, key="daily_orders", value=2400)
    response = api.post(
        "/api/v1/scenarios/",
        {"business": str(alice_shop.id), "template_key": "payment_gateway_outage", "name": "PG"},
        format="json",
    )
    assert "daily_orders" not in response.json()["missing_inputs"]


def test_template_must_match_business_mode(api, alice_idea):
    response = api.post(
        "/api/v1/scenarios/",
        {"business": str(alice_idea.id), "template_key": "warehouse_shutdown", "name": "x"},
        format="json",
    )
    assert response.status_code == 400
    assert "operating" in str(response.json()["error"]["fields"]["template_key"])


def test_bad_parameters_are_reported_per_field(api, alice_shop):
    response = api.post(
        "/api/v1/scenarios/",
        {
            "business": str(alice_shop.id),
            "template_key": "logistics_failure",
            "name": "x",
            "parameters": {"outage_hours": "500", "colour": "red"},
        },
        format="json",
    )
    assert response.status_code == 400
    fields = response.json()["error"]["fields"]["parameters"]
    assert set(fields) == {"outage_hours", "colour"}


def test_template_cannot_change_after_creation(api, alice_shop):
    created = api.post(
        "/api/v1/scenarios/",
        {"business": str(alice_shop.id), "template_key": "logistics_failure", "name": "x"},
        format="json",
    ).json()
    response = api.patch(
        f"/api/v1/scenarios/{created['id']}/",
        {"template_key": "warehouse_shutdown"},
        format="json",
    )
    assert response.status_code == 400


def test_catalogue_endpoints(api):
    templates = api.get("/api/v1/scenario-templates/").json()
    assert {t["key"] for t in templates} == {
        "idea_cases",
        "payment_gateway_outage",
        "warehouse_shutdown",
        "logistics_failure",
    }
    inputs = api.get("/api/v1/inputs/").json()
    assert any(f["key"] == "conversion_rate" for f in inputs["idea"])
    assert not any(f["key"] == "conversion_rate" for f in inputs["operating"])
