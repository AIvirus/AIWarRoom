"""
Cross-organization isolation for EVERY org-owned resource.

Alice must get 404 (not 403, not data) for each of Bob's records, must not see them in
lists, and must not be able to attach her records to his.
"""

import pytest

from businesses.models import BusinessComponent
from decisions.models import Decision
from intelligence.models import AIAnalysis, Alert, CompanyScan
from simulations.models import Scenario, SimulationResult, SimulationRun

pytestmark = pytest.mark.django_db


@pytest.fixture
def bobs_world(bob, bob_shop):
    """One of every org-owned record, all belonging to Bob."""
    component = BusinessComponent.objects.create(
        business=bob_shop, key="pg", name="PG", kind="payment"
    )
    scenario = Scenario.objects.create(
        business=bob_shop, template_key="payment_gateway_outage", name="PG down", parameters={}
    )
    run = SimulationRun.objects.create(
        scenario=scenario,
        business=bob_shop,
        status="completed",
        input_snapshot={},
        input_hash="0" * 64,
        engine_version="test",
    )
    SimulationResult.objects.create(run=run, case_key="wait", label="Wait", metrics={})
    analysis = AIAnalysis.objects.create(
        business=bob_shop,
        run=run,
        kind="run_explanation",
        status="ok",
        model_name="test",
        prompt_version="v1",
        input_hash="1" * 64,
    )
    scan = CompanyScan.objects.create(business=bob_shop, url="https://rival.test/")
    alert = Alert.objects.create(
        business=bob_shop, scan=scan, severity="warn", kind="pricing_change", summary="Price up"
    )
    decision = Decision.objects.create(business=bob_shop, run=run, title="Add backup PG")
    return {
        "business": bob_shop,
        "component": component,
        "scenario": scenario,
        "run": run,
        "analysis": analysis,
        "scan": scan,
        "alert": alert,
        "decision": decision,
    }


DETAIL_URLS = {
    "business": "/api/v1/businesses/{id}/",
    "scenario": "/api/v1/scenarios/{id}/",
    "run": "/api/v1/runs/{id}/",
    "analysis": "/api/v1/analyses/{id}/",
    "scan": "/api/v1/scans/{id}/",
    "alert": "/api/v1/alerts/{id}/",
    "decision": "/api/v1/decisions/{id}/",
}


@pytest.mark.parametrize("resource", sorted(DETAIL_URLS))
def test_other_orgs_records_answer_404(api, bobs_world, resource):
    url = DETAIL_URLS[resource].format(id=bobs_world[resource].id)
    response = api.get(url)
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Not found.", "fields": {}}
    }


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/businesses/",
        "/api/v1/scenarios/",
        "/api/v1/runs/",
        "/api/v1/analyses/",
        "/api/v1/scans/",
        "/api/v1/alerts/",
        "/api/v1/decisions/",
    ],
)
def test_other_orgs_records_never_appear_in_lists(api, bobs_world, url):
    assert api.get(url).json() == []


def test_other_orgs_records_cannot_be_changed_or_deleted(api, bobs_world):
    biz = bobs_world["business"]
    assert (
        api.patch(f"/api/v1/businesses/{biz.id}/", {"name": "x"}, format="json").status_code == 404
    )
    assert api.delete(f"/api/v1/businesses/{biz.id}/").status_code == 404
    assert api.post(f"/api/v1/alerts/{bobs_world['alert'].id}/acknowledge/").status_code == 404
    biz.refresh_from_db()
    assert biz.name == "Rival Mart" and biz.archived_at is None


def test_other_orgs_nested_components_answer_404(api, bobs_world):
    biz, comp = bobs_world["business"], bobs_world["component"]
    assert api.get(f"/api/v1/businesses/{biz.id}/components/").status_code == 404
    assert api.get(f"/api/v1/businesses/{biz.id}/components/{comp.id}/").status_code == 404
    assert api.get(f"/api/v1/businesses/{biz.id}/assumptions/").status_code == 404


def test_cannot_attach_records_to_another_orgs_business(api, bobs_world):
    response = api.post(
        "/api/v1/scenarios/",
        {
            "business": str(bobs_world["business"].id),
            "template_key": "warehouse_shutdown",
            "name": "sneaky",
        },
        format="json",
    )
    assert response.status_code == 400
    response = api.post(
        "/api/v1/decisions/",
        {"business": str(bobs_world["business"].id), "title": "sneaky"},
        format="json",
    )
    assert response.status_code == 400


def test_cannot_link_own_decision_to_another_orgs_run(api, alice_shop, bobs_world):
    response = api.post(
        "/api/v1/decisions/",
        {"business": str(alice_shop.id), "run": str(bobs_world["run"].id), "title": "x"},
        format="json",
    )
    assert response.status_code == 400


def test_cannot_assign_decision_to_user_outside_org(api, alice_shop, bob):
    response = api.post(
        "/api/v1/decisions/",
        {"business": str(alice_shop.id), "title": "x", "owner": bob.id},
        format="json",
    )
    assert response.status_code == 400
