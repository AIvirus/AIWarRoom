from decimal import Decimal as D

import pytest

from businesses.models import FinancialAssumption
from common.templatetags.warroom import figure, indian, source_tag
from decisions.models import Decision
from intelligence.models import AIAnalysis
from simulations.models import Scenario
from simulations.services.run_service import run_scenario

pytestmark = pytest.mark.django_db


@pytest.fixture
def run(alice_shop):
    inputs = {
        "daily_orders": "2400", "average_order_value": "600", "contribution_margin": "25",
        "primary_gateway_share": "100", "recapture_rate": "30",
    }  # fmt: skip
    for key, value in inputs.items():
        FinancialAssumption.objects.create(
            business=alice_shop, key=key, value=D(value),
            source="illustrative" if key == "recapture_rate" else "user",
        )  # fmt: skip
    scenario = Scenario.objects.create(
        business=alice_shop, template_key="payment_gateway_outage", name="PG down at peak",
        parameters={"outage_hours": "2", "demand_profile": "uniform"},
    )  # fmt: skip
    return run_scenario(scenario, alice_shop.created_by)


def create(api, business, **extra):
    body = {"business": str(business.id), "title": "Sign a backup payment gateway", **extra}
    response = api.post("/api/v1/decisions/", body, format="json")
    assert response.status_code == 201, response.json()
    return response.json()


# --- Workflow ---------------------------------------------------------------------------


def test_new_decision_starts_proposed_with_history(api, alice_shop):
    body = create(api, alice_shop)
    assert body["status"] == "proposed"
    assert body["allowed_next_status"] == ["approved", "rejected"]
    assert [h["to"] for h in body["history"]] == ["proposed"]


def test_cannot_create_a_pre_approved_decision(api, alice_shop):
    response = api.post(
        "/api/v1/decisions/",
        {"business": str(alice_shop.id), "title": "x", "status": "approved"},
        format="json",
    )
    assert response.status_code == 400


def test_approval_records_who_and_when_and_the_note(api, alice, alice_shop):
    body = create(api, alice_shop)
    url = f"/api/v1/decisions/{body['id']}/"
    approved = api.patch(url, {"status": "approved", "note": "Board agreed"}, format="json").json()
    assert approved["decided_by_name"] == "Alice" and approved["decided_at"]
    assert approved["history"][-1] == {
        **approved["history"][-1], "from": "proposed", "to": "approved", "note": "Board agreed"
    }  # fmt: skip


def test_illegal_jump_is_refused_with_the_allowed_options(api, alice_shop):
    body = create(api, alice_shop)
    response = api.patch(f"/api/v1/decisions/{body['id']}/", {"status": "done"}, format="json")
    assert response.status_code == 400
    assert "approved, rejected" in str(response.json()["error"]["fields"]["status"])


def test_done_is_final_and_rejected_can_be_reopened(api, alice_shop):
    body = create(api, alice_shop)
    url = f"/api/v1/decisions/{body['id']}/"
    for step in ("approved", "in_progress", "done"):
        assert api.patch(url, {"status": step}, format="json").status_code == 200
    assert api.patch(url, {"status": "rejected"}, format="json").status_code == 400

    other = create(api, alice_shop)
    url = f"/api/v1/decisions/{other['id']}/"
    api.patch(url, {"status": "rejected"}, format="json")
    reopened = api.patch(url, {"status": "proposed"}, format="json").json()
    assert reopened["decided_by_name"] is None  # old sign-off no longer applies
    assert [h["to"] for h in reopened["history"]] == ["proposed", "rejected", "proposed"]


def test_editing_text_does_not_add_history(api, alice_shop):
    body = create(api, alice_shop)
    edited = api.patch(
        f"/api/v1/decisions/{body['id']}/", {"rationale": "Cheaper overall."}, format="json"
    ).json()
    assert len(edited["history"]) == 1


def test_chosen_strategy_checked_on_patch_against_linked_run(api, alice_shop, run):
    body = create(api, alice_shop, run=str(run.id))
    response = api.patch(
        f"/api/v1/decisions/{body['id']}/", {"chosen_strategy": "pray"}, format="json"
    )
    assert response.status_code == 400


# --- Brief --------------------------------------------------------------------------------


def test_brief_uses_the_frozen_snapshot_not_todays_values(api, alice_shop, run):
    body = create(api, alice_shop, run=str(run.id), chosen_strategy="queue_retry")
    FinancialAssumption.objects.filter(business=alice_shop, key="daily_orders").update(value=9999)

    brief = api.get(f"/api/v1/decisions/{body['id']}/report/").json()
    rows = {r["key"]: r for r in brief["assumptions"]["rows"]}
    assert brief["assumptions"]["frozen"] is True
    assert rows["daily_orders"]["value"] == "2400"
    assert rows["recapture_rate"]["source"] == "illustrative"

    outcomes = brief["outcomes"]
    assert outcomes["chosen"] == "queue_retry"
    impact = next(r for r in outcomes["rows"] if r["key"] == "total_impact")
    assert impact["cells"] == [
        {"case": "wait", "value": "21000.00"},
        {"case": "backup", "value": impact["cells"][1]["value"]},
        {"case": "queue_retry", "value": impact["cells"][2]["value"]},
    ]
    assert brief["decision"]["chosen_label"] == "Queue and retry payments"
    assert brief["ai_explanation"] is None and brief["committee"] is None


def test_brief_without_a_run_says_so(api, alice_shop):
    body = create(api, alice_shop)
    brief = api.get(f"/api/v1/decisions/{body['id']}/report/").json()
    assert brief["run"] is None and brief["outcomes"] is None
    assert brief["assumptions"]["frozen"] is False


def test_brief_page_renders_labelled_ai_and_flagged_numbers(api, alice_shop, run):
    AIAnalysis.objects.create(
        business=alice_shop, run=run, kind="run_explanation", status="ok", model_name="m",
        prompt_version="run-explanation/1", input_hash="x" * 64,
        output={"headline": "Queueing has the lowest impact", "what_happened": "…",
                "recommendations": [{"action": "Pilot a retry queue", "rationale": "r",
                                     "metric_keys": [], "confidence": "medium"}]},
        flagged_numbers=[{"path": "headline", "literal": "14,550", "value": "14550"}],
    )  # fmt: skip
    body = create(api, alice_shop, run=str(run.id), chosen_strategy="backup",
                  rationale="Fastest recovery.")  # fmt: skip
    page = api.get(f"/decisions/{body['id']}/brief/")
    assert page.status_code == 200
    html = page.content.decode()
    assert "AI analysis" in html and "Queueing has the lowest impact" in html
    assert "not from the simulation" in html and "14,550" in html
    assert "₹21,000" in html  # Indian formatting of the wait case's total impact
    assert 'class="num chosen"' in html  # the chosen column is marked
    assert "What this brief is not" in html
    assert "Print or save as PDF" in html


def test_brief_page_is_org_scoped(client, bob, alice_shop):
    decision = Decision.objects.create(business=alice_shop, title="Private")
    client.force_login(bob)
    assert client.get(f"/decisions/{decision.id}/brief/").status_code == 404
    client.logout()
    assert client.get(f"/decisions/{decision.id}/brief/").status_code == 302  # to login


# --- Number formatting --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        ("21000.00", "INR", "₹21,000"),
        ("12345678.4", "INR", "₹1,23,45,678"),
        ("-2428.80", "INR", "-₹2,429"),
        ("649.50", "INR/order", "₹649.50/order"),
        ("640.00", "INR/order", "₹640/order"),
        ("0.00", "INR", "₹0"),
        ("19", "hour of day", "19:00"),
        ("1.00", "hours", "1 hour"),
        ("ecommerce_curve", "", "ecommerce curve"),
        ("22.5", "%", "22.5 %"),
        ("25", "%", "25 %"),
        ("4.00", "ratio", "4.00×"),
        ("7", "month", "7 month"),
        (None, "month", "n/a"),
        ("2400", "orders/day", "2,400 orders/day"),
    ],
)
def test_figure_formats_like_an_indian_finance_team(value, unit, expected):
    assert figure(value, unit) == expected


def test_indian_grouping_and_source_tags():
    assert indian("100000") == "1,00,000"
    assert indian("999") == "999"
    assert source_tag("illustrative") == "ILL" and source_tag("what_if") == "WHAT-IF"
