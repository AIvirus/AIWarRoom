"""Account workflows. Views call these; they never create users or orgs themselves."""

from django.db import transaction
from django.utils.text import slugify

from .models import Membership, Organization, User


def unique_org_slug(name: str) -> str:
    """'Kirana Express' -> 'kirana-express', then 'kirana-express-2' if that's taken."""
    base = slugify(name)[:120] or "org"
    slug, n = base, 2
    while Organization.objects.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


@transaction.atomic
def register_owner(*, email: str, password: str, full_name: str, org_name: str) -> User:
    """
    Create a user, their organization and an owner membership as one unit.

    transaction.atomic means that if any step fails we never end up with a user who has
    no organization: either all three rows are written or none of them are.
    """
    user = User.objects.create_user(email=email, password=password, full_name=full_name)
    organization = Organization.objects.create(name=org_name, slug=unique_org_slug(org_name))
    Membership.objects.create(user=user, organization=organization, role=Membership.Role.OWNER)
    return user
