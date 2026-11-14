"""
Shared test fixtures: two organizations that must never see each other's data.

alice  owns "Kirana Express" (operating company) and "Kirana Idea" (idea).
bob    owns "Rival Mart" (operating company) in a different organization.

Django imports live INSIDE the fixtures so `pytest -p no:django simulation_engine` can run
the pure engine tests without Django being configured at all.
"""

import pytest

PASSWORD = "harbour-lantern-42"


@pytest.fixture
def alice(db):
    from accounts.services import register_owner

    return register_owner(
        email="alice@kirana.test", password=PASSWORD, full_name="Alice", org_name="Kirana Co"
    )


@pytest.fixture
def bob(db):
    from accounts.services import register_owner

    return register_owner(
        email="bob@rival.test", password=PASSWORD, full_name="Bob", org_name="Rival Co"
    )


def org_of(user):
    from accounts.models import Membership

    return Membership.objects.get(user=user).organization


def make_business(owner, mode, name):
    from businesses.models import BusinessProfile

    return BusinessProfile.objects.create(
        organization=org_of(owner), mode=mode, name=name, created_by=owner
    )


@pytest.fixture
def alice_shop(alice):
    return make_business(alice, "operating", "Kirana Express")


@pytest.fixture
def alice_idea(alice):
    return make_business(alice, "idea", "Kirana Idea")


@pytest.fixture
def bob_shop(bob):
    return make_business(bob, "operating", "Rival Mart")


@pytest.fixture
def api(alice):
    """An API client logged in as alice, with a real session (like the browser)."""
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_login(alice)
    return client
