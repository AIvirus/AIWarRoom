"""
Shared test fixtures: two organizations that must never see each other's data.

alice  owns "Kirana Express" (operating company) and "Kirana Idea" (idea).
bob    owns "Rival Mart" (operating company) in a different organization.
"""

import pytest
from rest_framework.test import APIClient

from accounts.models import Membership
from accounts.services import register_owner
from businesses.models import BusinessProfile

PASSWORD = "harbour-lantern-42"


@pytest.fixture
def alice(db):
    return register_owner(
        email="alice@kirana.test", password=PASSWORD, full_name="Alice", org_name="Kirana Co"
    )


@pytest.fixture
def bob(db):
    return register_owner(
        email="bob@rival.test", password=PASSWORD, full_name="Bob", org_name="Rival Co"
    )


def org_of(user):
    return Membership.objects.get(user=user).organization


@pytest.fixture
def alice_shop(alice):
    return BusinessProfile.objects.create(
        organization=org_of(alice), mode="operating", name="Kirana Express", created_by=alice
    )


@pytest.fixture
def alice_idea(alice):
    return BusinessProfile.objects.create(
        organization=org_of(alice), mode="idea", name="Kirana Idea", created_by=alice
    )


@pytest.fixture
def bob_shop(bob):
    return BusinessProfile.objects.create(
        organization=org_of(bob), mode="operating", name="Rival Mart", created_by=bob
    )


@pytest.fixture
def api(alice):
    """An API client logged in as alice."""
    client = APIClient()
    client.force_authenticate(alice)
    return client
