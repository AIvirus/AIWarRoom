"""
HTML page flows: what a person clicking through the app does, end to end.
Uses Django's test client with a real session, like the browser.
"""

import json
from decimal import Decimal as D

import pytest

from businesses.models import BusinessComponent, BusinessProfile, FinancialAssumption
from decisions.models import Decision
from intelligence.models import Alert, CompanyScan
from simulations.models import Scenario, SimulationRun

pytestmark = pytest.mark.django_db

SHOP = {
    "daily_orders": "2400", "average_order_value": "600", "contribution_margin": "25",
    "primary_gateway_share": "100", "recapture_rate": "30", "hourly_capacity": "200",
}  # fmt: skip
IDEA = {
    "price_per_order": "500", "variable_cost_per_order": "300", "fixed_costs_monthly": "100000",
    "marketing_spend_monthly": "50000", "cost_per_visit": "10", "conversion_rate": "2",
    "orders_per_customer_monthly": "2", "monthly_retention": "80", "initial_investment": "1000000",
    "expected_orders_monthly": "1000",
}  # fmt: skip


@pytest.fixture
def web(client, alice):
    client.force_login(alice)
    return client


def fill(business, values):
    for key, value in values.items():
        FinancialAssumption.objects.create(business=business, key=key, value=D(value))


def page_data(response) -> dict:
    html = response.content.decode()
    tag = html.index('id="page-data"')
    start = html.index(">", tag) + 1
    return json.loads(html[start : html.index("</script>", start)])


# --- Dashboard and business pages -----------------------------------------------------


def test_empty_dashboard_explains_what_to_do(web):
    html = web.get("/").content.decode()
    assert "Nothing on the board yet" in html and "Add a business" in html


def test_create_business_lands_on_its_dossier(web, alice):
    response = web.post(
        "/businesses/new/",
        {"mode": "operating", "name": "Kirana Express", "industry": "Groceries"},
    )
    business = BusinessProfile.objects.get(name="Kirana Express")
    assert response.url == f"/businesses/{business.pk}/"
    assert business.organization.memberships.filter(user=alice).exists()
    assert "Kirana Express" in web.get("/").content.decode()


def test_dossier_shows_mode_specific_inputs(web, alice_shop, alice_idea):
    shop = web.get(f"/businesses/{alice_shop.pk}/").content.decode()
    idea = web.get(f"/businesses/{alice_idea.pk}/").content.decode()
    assert "Daily orders" in shop and "Components and dependencies" in shop
    assert "Visit-to-customer conversion" in idea and "Components and dependencies" not in idea


def test_assumptions_form_saves_with_source_and_blank_removes(web, alice_shop):
    url = f"/businesses/{alice_shop.pk}/assumptions/"
    web.post(
        url,
        {
            "daily_orders": "2400",
            "daily_orders__source": "illustrative",
            "contribution_margin": "22.5",
            "contribution_margin__source": "user",
        },
    )
    saved = {a.key: a for a in alice_shop.assumptions.all()}
    assert saved["daily_orders"].source == "illustrative"
    assert saved["contribution_margin"].value == D("22.5")
    web.post(url, {"daily_orders": "", "daily_orders__source": "user"})
    assert not alice_shop.assumptions.filter(key="daily_orders").exists()


def test_invalid_assumption_saves_nothing_and_says_why(web, alice_shop):
    response = web.post(
        f"/businesses/{alice_shop.pk}/assumptions/",
        {"contribution_margin": "140", "contribution_margin__source": "user"},
        follow=True,
    )
    assert "at most 100" in response.content.decode()
    assert alice_shop.assumptions.count() == 0


def test_add_and_remove_component(web, alice_shop):
    web.post(
        f"/businesses/{alice_shop.pk}/components/",
        {"name": "Razorpay (primary)", "kind": "payment", "criticality": "5"},
    )
    component = BusinessComponent.objects.get(business=alice_shop)
    assert component.key == "razorpay-primary"
    web.post(f"/businesses/{alice_shop.pk}/components/{component.pk}/delete/")
    assert not BusinessComponent.objects.filter(business=alice_shop).exists()


def test_scenario_with_missing_inputs_explains_instead_of_running(web, alice_shop):
    response = web.post(
        f"/businesses/{alice_shop.pk}/scenarios/",
        {"template_key": "payment_gateway_outage", "name": "PG down"},
        follow=True,
    )
    html = response.content.decode()
    assert "yet" in html and "daily_orders" in html
    assert SimulationRun.objects.get().status == "failed"


# --- Run pages ------------------------------------------------------------------------


def test_disruption_scenario_runs_and_opens_the_situation_board(web, alice_shop):
    fill(alice_shop, SHOP)
    BusinessComponent.objects.create(business=alice_shop, key="pg", name="Razorpay", kind="payment")
    response = web.post(
        f"/businesses/{alice_shop.pk}/scenarios/",
        {"template_key": "payment_gateway_outage", "name": "PG down"},
    )
    run = SimulationRun.objects.get(status="completed")
    assert response.url == f"/runs/{run.pk}/"
    page = web.get(response.url)
    html = page.content.decode()
    assert "System view" in html and "Responses compared" in html
    assert "three@0.170.0" in html  # pinned Three.js version
    data = page_data(page)
    assert [r["case_key"] for r in data["run"]["results"]] == ["wait", "backup", "queue_retry"]
    assert data["template"]["loss_mode"] == "checkout"
    # Payment outage: recapture matters; warehouse capacity doesn't, so no slider for it.
    assert {i["key"] for i in data["inputs"]} == {"recapture_rate"}
    assert data["urls"]["run_page"] == "/runs/RUN_ID/"


def test_idea_scenario_opens_the_idea_bench(web, alice_idea):
    fill(alice_idea, IDEA)
    response = web.post(
        f"/businesses/{alice_idea.pk}/scenarios/",
        {"template_key": "idea_cases", "name": "Launch plan"},
    )
    page = web.get(response.url)
    html = page.content.decode()
    assert "Cash position, month by month" in html and "Which assumption matters most" in html
    data = page_data(page)
    assert len(data["run"]["results"]) == 7
    assert data["run"]["summary"]["funnel_check"]["month"] == 6
    assert len(data["inputs"]) == 8


def test_record_decision_from_run_then_sign_off_on_the_brief(web, alice_shop):
    fill(alice_shop, SHOP)
    web.post(
        f"/businesses/{alice_shop.pk}/scenarios/",
        {"template_key": "payment_gateway_outage", "name": "PG down"},
    )
    run = SimulationRun.objects.get(status="completed")
    response = web.post(
        f"/decisions/from-run/{run.pk}/",
        {
            "title": "Add a backup gateway",
            "chosen_strategy": "backup",
            "rationale": "Keeps evening orders flowing.",
        },
    )
    decision = Decision.objects.get()
    assert response.url == f"/decisions/{decision.pk}/brief/"
    assert decision.status == "proposed" and decision.run == run

    brief = web.get(response.url).content.decode()
    assert "Mark approved" in brief and "Mark rejected" in brief
    web.post(f"/decisions/{decision.pk}/status/", {"status": "approved"})
    decision.refresh_from_db()
    assert decision.status == "approved" and decision.decided_by is not None
    # Illegal jump through the page is refused too.
    web.post(f"/decisions/{decision.pk}/status/", {"status": "proposed"})
    decision.refresh_from_db()
    assert decision.status == "approved"


def test_alert_acknowledge_refuses_open_redirects(web, alice_shop):
    scan = CompanyScan.objects.create(business=alice_shop, url="https://k.test/")
    alert = Alert.objects.create(
        business=alice_shop, scan=scan, severity="warn", kind="pricing_change", summary="Prices up"
    )
    response = web.post(f"/alerts/{alert.pk}/acknowledge/", {"next": "https://evil.test/phish"})
    assert response.url == "/"
    alert.refresh_from_db()
    assert alert.acknowledged_at is not None


# --- Isolation ------------------------------------------------------------------------


def test_other_orgs_pages_are_404(web, bob_shop):
    fill(bob_shop, SHOP)
    scenario = Scenario.objects.create(
        business=bob_shop, template_key="payment_gateway_outage", name="x", parameters={}
    )
    run = SimulationRun.objects.create(
        scenario=scenario,
        business=bob_shop,
        status="completed",
        input_snapshot={},
        input_hash="0" * 64,
        engine_version="t",
    )
    decision = Decision.objects.create(business=bob_shop, title="Private")
    for url in [
        f"/businesses/{bob_shop.pk}/",
        f"/runs/{run.pk}/",
        f"/decisions/{decision.pk}/brief/",
    ]:
        assert web.get(url).status_code == 404, url
    for url in [
        f"/businesses/{bob_shop.pk}/assumptions/",
        f"/businesses/{bob_shop.pk}/scenarios/",
        f"/decisions/from-run/{run.pk}/",
        f"/decisions/{decision.pk}/status/",
    ]:
        assert web.post(url, {"status": "approved", "title": "x"}).status_code == 404, url
    decision.refresh_from_db()
    assert decision.status == "proposed"


def test_pages_require_login(client, alice_shop):
    for url in ["/", f"/businesses/{alice_shop.pk}/", "/businesses/new/"]:
        assert client.get(url).status_code == 302


def test_ledger_shows_plain_numbers_not_exponents(web, alice_shop):
    """Decimal.normalize() turns 2400 into '2.4E+3'; the ledger must show 2400."""
    fill(alice_shop, {"daily_orders": "2400", "hourly_capacity": "180"})
    html = web.get(f"/businesses/{alice_shop.pk}/").content.decode()
    assert 'value="2400"' in html and 'value="180"' in html
    assert "E+" not in html
