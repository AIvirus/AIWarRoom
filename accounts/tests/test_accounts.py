"""
Auth and organization-isolation tests.

The isolation tests matter most: they prove one organization can never read another's
data. Every later app adds the same kind of test for its own models.
"""

import pytest
from django.urls import reverse

from accounts.access import organization_for
from accounts.models import Membership, Organization, User
from accounts.services import register_owner

pytestmark = pytest.mark.django_db

STRONG_PASSWORD = "harbour-lantern-42"


@pytest.fixture
def alice():
    return register_owner(
        email="alice@kirana.test",
        password=STRONG_PASSWORD,
        full_name="Alice",
        org_name="Kirana Express",
    )


@pytest.fixture
def bob():
    return register_owner(
        email="bob@rival.test", password=STRONG_PASSWORD, full_name="Bob", org_name="Rival Mart"
    )


# --- Registration -----------------------------------------------------------------------


def test_register_owner_creates_user_org_and_owner_membership(alice):
    membership = Membership.objects.get(user=alice)
    assert membership.role == Membership.Role.OWNER
    assert membership.organization.name == "Kirana Express"
    assert membership.organization.slug == "kirana-express"


def test_org_slugs_stay_unique_when_names_repeat(alice):
    other = register_owner(
        email="carol@x.test", password=STRONG_PASSWORD, full_name="Carol", org_name="Kirana Express"
    )
    assert organization_for(other).slug == "kirana-express-2"


def test_email_is_normalised_to_lowercase():
    user = User.objects.create_user(email="Dev@Example.TEST", password=STRONG_PASSWORD)
    assert user.email == "dev@example.test"


def test_signup_page_creates_account_and_logs_in(client):
    response = client.post(
        reverse("accounts:signup"),
        {
            "full_name": "Dana",
            "email": "dana@example.test",
            "org_name": "Dana Foods",
            "password": STRONG_PASSWORD,
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("home")
    assert client.get(reverse("home")).status_code == 200


def test_signup_rejects_weak_password_and_creates_nothing(client):
    response = client.post(
        reverse("accounts:signup"),
        {
            "full_name": "Eve",
            "email": "eve@example.test",
            "org_name": "Eve Co",
            "password": "12345678",
        },
    )
    assert response.status_code == 200  # form re-rendered with errors
    assert not User.objects.filter(email="eve@example.test").exists()
    assert not Organization.objects.filter(name="Eve Co").exists()


def test_signup_rejects_duplicate_email(client, alice):
    response = client.post(
        reverse("accounts:signup"),
        {
            "full_name": "A2",
            "email": "ALICE@kirana.test",
            "org_name": "Dup",
            "password": STRONG_PASSWORD,
        },
    )
    assert response.status_code == 200
    assert "already exists" in response.content.decode()


def test_login_with_email(client, alice):
    response = client.post(
        reverse("accounts:login"), {"username": "alice@kirana.test", "password": STRONG_PASSWORD}
    )
    assert response.status_code == 302


def test_home_requires_login(client):
    response = client.get(reverse("home"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


def test_logout_is_post_only(client, alice):
    client.force_login(alice)
    assert client.get(reverse("accounts:logout")).status_code == 405
    assert client.post(reverse("accounts:logout")).status_code == 302


# --- Organization isolation ----------------------------------------------------------


def test_for_user_returns_only_own_organizations(alice, bob):
    visible = Organization.objects.for_user(alice)
    assert list(visible.values_list("name", flat=True)) == ["Kirana Express"]


def test_for_user_returns_nothing_for_anonymous(alice):
    from django.contrib.auth.models import AnonymousUser

    assert Organization.objects.for_user(AnonymousUser()).count() == 0


def test_api_lists_only_own_organization(client, alice, bob):
    client.force_login(alice)
    response = client.get(reverse("api:organization-list"))
    assert response.status_code == 200
    assert [org["name"] for org in response.json()] == ["Kirana Express"]


def test_api_returns_404_for_another_orgs_record(client, alice, bob):
    """404, not 403: we don't even confirm the other organization exists."""
    client.force_login(alice)
    bobs_org = organization_for(bob)
    response = client.get(reverse("api:organization-detail", args=[bobs_org.id]))
    assert response.status_code == 404


def test_api_requires_authentication(client):
    assert client.get(reverse("api:me")).status_code == 403


def test_me_endpoint_reports_current_organization(client, alice):
    client.force_login(alice)
    body = client.get(reverse("api:me")).json()
    assert body["email"] == "alice@kirana.test"
    assert body["organization"]["name"] == "Kirana Express"


def test_healthz_reports_database(client):
    body = client.get(reverse("healthz")).json()
    assert body == {"status": "ok", "database": "sqlite"}


def test_login_ignores_email_capitals(client):
    # Sign up as "Alice@Kirana.test", then log in typing it exactly the same way.
    client.post(
        reverse("accounts:signup"),
        {
            "full_name": "Alice",
            "email": "Alice@Kirana.test",
            "org_name": "Kirana Express",
            "password": STRONG_PASSWORD,
        },
    )
    client.logout()
    response = client.post(
        reverse("accounts:login"), {"username": "Alice@Kirana.test", "password": STRONG_PASSWORD}
    )
    assert response.status_code == 302
