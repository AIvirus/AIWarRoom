import pytest
from rest_framework.test import APIClient

from accounts.models import Membership
from businesses.models import BusinessComponent, BusinessProfile

pytestmark = pytest.mark.django_db


# --- Business profiles --------------------------------------------------------------


def test_create_business_uses_the_requesters_organization(api, alice, bob):
    """Even if a client sends someone else's organization id, it is ignored."""
    bobs_org = Membership.objects.get(user=bob).organization
    response = api.post(
        "/api/v1/businesses/",
        {"mode": "operating", "name": "Kirana Express", "organization": str(bobs_org.id)},
        format="json",
    )
    assert response.status_code == 201
    business = BusinessProfile.objects.get(pk=response.json()["id"])
    assert business.organization == Membership.objects.get(user=alice).organization


def test_mode_cannot_change_after_creation(api, alice_shop):
    response = api.patch(f"/api/v1/businesses/{alice_shop.id}/", {"mode": "idea"}, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["fields"]["mode"]


def test_delete_archives_instead_of_deleting(api, alice_shop):
    assert api.delete(f"/api/v1/businesses/{alice_shop.id}/").status_code == 204
    alice_shop.refresh_from_db()
    assert alice_shop.archived_at is not None
    names = [b["name"] for b in api.get("/api/v1/businesses/").json()]
    assert "Kirana Express" not in names
    archived = [b["name"] for b in api.get("/api/v1/businesses/?archived=true").json()]
    assert "Kirana Express" in archived


def test_only_owners_can_archive(alice, alice_shop, django_user_model):
    member = django_user_model.objects.create_user(email="m@kirana.test", password="x")
    Membership.objects.create(user=member, organization=alice_shop.organization, role="member")
    client = APIClient()
    client.force_authenticate(member)
    response = client.delete(f"/api/v1/businesses/{alice_shop.id}/")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


# --- Assumptions --------------------------------------------------------------------


def test_put_assumptions_upserts_and_sets_unit_from_catalogue(api, alice_shop):
    url = f"/api/v1/businesses/{alice_shop.id}/assumptions/"
    payload = {
        "assumptions": [
            {"key": "daily_orders", "value": "2400"},
            {"key": "contribution_margin", "value": "22.5", "source": "illustrative"},
        ]
    }
    response = api.put(url, payload, format="json")
    assert response.status_code == 200, response.json()
    rows = {row["key"]: row for row in response.json()}
    assert rows["daily_orders"]["unit"] == "orders/day"
    assert rows["contribution_margin"]["value"] == "22.5000"
    assert rows["contribution_margin"]["source"] == "illustrative"

    # Second PUT updates in place, it doesn't duplicate.
    api.put(url, {"assumptions": [{"key": "daily_orders", "value": "3000"}]}, format="json")
    assert alice_shop.assumptions.filter(key="daily_orders").get().value == 3000
    assert alice_shop.assumptions.count() == 2


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ({"key": "conversion_rate", "value": "3"}, "doesn't apply"),  # idea-only input
        ({"key": "contribution_margin", "value": "140"}, "at most 100"),
        ({"key": "made_up_key", "value": "1"}, "not a known assumption"),
    ],
)
def test_put_assumptions_rejects_invalid_items(api, alice_shop, item, expected):
    url = f"/api/v1/businesses/{alice_shop.id}/assumptions/"
    response = api.put(url, {"assumptions": [item]}, format="json")
    assert response.status_code == 400
    assert expected in str(response.json()["error"]["fields"])
    assert alice_shop.assumptions.count() == 0


def test_put_assumptions_rejects_duplicate_keys(api, alice_shop):
    url = f"/api/v1/businesses/{alice_shop.id}/assumptions/"
    items = [{"key": "daily_orders", "value": "1"}, {"key": "daily_orders", "value": "2"}]
    assert api.put(url, {"assumptions": items}, format="json").status_code == 400


# --- Components and dependencies ----------------------------------------------------


def make_component(business, key, kind="storefront"):
    return BusinessComponent.objects.create(business=business, key=key, name=key, kind=kind)


def test_create_component_with_dependencies_by_key(api, alice_shop):
    make_component(alice_shop, "payment-gateway", "payment")
    url = f"/api/v1/businesses/{alice_shop.id}/components/"
    response = api.post(
        url,
        {
            "key": "checkout",
            "name": "Checkout",
            "kind": "storefront",
            "criticality": 5,
            "depends_on": ["payment-gateway"],
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["depends_on"] == ["payment-gateway"]


def test_component_cannot_depend_on_another_business(api, alice_shop, alice_idea):
    make_component(alice_idea, "foreign-warehouse", "warehouse")
    url = f"/api/v1/businesses/{alice_shop.id}/components/"
    response = api.post(
        url,
        {
            "key": "checkout",
            "name": "Checkout",
            "kind": "storefront",
            "depends_on": ["foreign-warehouse"],
        },
        format="json",
    )
    assert response.status_code == 400


def test_dependency_cycles_are_rejected(api, alice_shop):
    a = make_component(alice_shop, "a")
    b = make_component(alice_shop, "b")
    c = make_component(alice_shop, "c")
    b.depends_on.add(a)  # b needs a
    c.depends_on.add(b)  # c needs b
    url = f"/api/v1/businesses/{alice_shop.id}/components/{a.id}/"
    response = api.patch(url, {"depends_on": ["c"]}, format="json")  # a needs c -> loop
    assert response.status_code == 400
    assert "loop" in str(response.json()["error"]["fields"])


def test_component_cannot_depend_on_itself(api, alice_shop):
    a = make_component(alice_shop, "a")
    url = f"/api/v1/businesses/{alice_shop.id}/components/{a.id}/"
    assert api.patch(url, {"depends_on": ["a"]}, format="json").status_code == 400


def test_duplicate_component_key_is_rejected(api, alice_shop):
    make_component(alice_shop, "warehouse", "warehouse")
    url = f"/api/v1/businesses/{alice_shop.id}/components/"
    response = api.post(url, {"key": "warehouse", "name": "W2", "kind": "warehouse"}, format="json")
    assert response.status_code == 400


def test_criticality_must_be_1_to_5(api, alice_shop):
    url = f"/api/v1/businesses/{alice_shop.id}/components/"
    response = api.post(
        url, {"key": "x", "name": "X", "kind": "supplier", "criticality": 9}, format="json"
    )
    assert response.status_code == 400
