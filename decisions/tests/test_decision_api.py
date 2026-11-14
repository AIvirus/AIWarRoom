import pytest

from simulations.models import Scenario, SimulationResult, SimulationRun

pytestmark = pytest.mark.django_db


@pytest.fixture
def alice_run(alice_shop):
    scenario = Scenario.objects.create(
        business=alice_shop, template_key="warehouse_shutdown", name="Flood", parameters={}
    )
    run = SimulationRun.objects.create(
        scenario=scenario,
        business=alice_shop,
        status="completed",
        input_snapshot={},
        input_hash="a" * 64,
        engine_version="test",
    )
    for key in ("wait", "backup", "queue_retry"):
        SimulationResult.objects.create(run=run, case_key=key, label=key, metrics={})
    return run


def test_create_decision_linked_to_run(api, alice, alice_shop, alice_run):
    response = api.post(
        "/api/v1/decisions/",
        {
            "business": str(alice_shop.id),
            "run": str(alice_run.id),
            "title": "Contract a backup 3PL",
            "chosen_strategy": "backup",
            "owner": alice.id,
            "rationale": "Lowest total impact.",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["status"] == "proposed"
    assert body["owner_name"] == "Alice"


def test_decision_without_owner_reports_null_owner_name(api, alice_shop):
    response = api.post(
        "/api/v1/decisions/", {"business": str(alice_shop.id), "title": "x"}, format="json"
    )
    assert response.json()["owner"] is None
    assert response.json()["owner_name"] is None


def test_chosen_strategy_must_exist_in_run(api, alice_shop, alice_run):
    response = api.post(
        "/api/v1/decisions/",
        {
            "business": str(alice_shop.id),
            "run": str(alice_run.id),
            "title": "x",
            "chosen_strategy": "pray",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "chosen_strategy" in response.json()["error"]["fields"]


def test_run_must_belong_to_the_same_business(api, alice_idea, alice_run):
    response = api.post(
        "/api/v1/decisions/",
        {"business": str(alice_idea.id), "run": str(alice_run.id), "title": "x"},
        format="json",
    )
    assert response.status_code == 400


def test_status_moves_through_patch(api, alice_shop):
    created = api.post(
        "/api/v1/decisions/", {"business": str(alice_shop.id), "title": "x"}, format="json"
    ).json()
    response = api.patch(
        f"/api/v1/decisions/{created['id']}/", {"status": "approved"}, format="json"
    )
    assert response.json()["status"] == "approved"
    bad = api.patch(f"/api/v1/decisions/{created['id']}/", {"status": "maybe"}, format="json")
    assert bad.json()["error"]["code"] == "validation_error"


def test_unauthenticated_requests_get_the_standard_error_shape(client):
    body = client.get("/api/v1/decisions/").json()
    assert body["error"]["code"] in {"not_authenticated", "permission_denied"}
