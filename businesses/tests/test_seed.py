from io import StringIO

import pytest
from django.core.management import call_command

from accounts.models import User
from businesses.models import BusinessProfile
from simulations.models import SimulationRun

pytestmark = pytest.mark.django_db


def seed(*args):
    out = StringIO()
    call_command("seed_kirana", *args, stdout=out)
    return out.getvalue()


def test_seed_creates_both_demos_with_completed_runs_for_an_existing_user(alice):
    seed("--email", "alice@kirana.test")
    kirana = BusinessProfile.objects.get(name="Kirana Express")
    tiffin = BusinessProfile.objects.get(name="Tiffin Box Co.")
    assert kirana.organization == tiffin.organization
    assert kirana.organization.memberships.filter(user=alice).exists()
    assert kirana.components.get(key="delhivery").depends_on.get().key == "bhiwandi"
    assert kirana.assumptions.get(key="recapture_rate").source == "illustrative"
    runs = SimulationRun.objects.all()
    assert runs.count() == 4 and set(runs.values_list("status", flat=True)) == {"completed"}


def test_seed_is_idempotent_and_reset_rebuilds(alice):
    seed("--email", "alice@kirana.test")
    output = seed("--email", "alice@kirana.test")
    assert "already there" in output
    assert BusinessProfile.objects.count() == 2
    seed("--email", "alice@kirana.test", "--reset")
    assert BusinessProfile.objects.count() == 2
    assert SimulationRun.objects.count() == 4  # old runs went with the old businesses


def test_seed_creates_a_missing_user_and_prints_the_password_once():
    output = seed("--email", "Demo@Example.test")
    user = User.objects.get(email="demo@example.test")
    password = output.split("password: ")[1].split()[0]
    assert user.check_password(password)
