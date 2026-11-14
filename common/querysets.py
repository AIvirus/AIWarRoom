"""
The organization filter used by every org-owned model.

Each such model declares ORG_PATH, the ORM path from that model to its Organization:

    Organization        ORG_PATH = ""
    BusinessProfile     ORG_PATH = "organization"
    SimulationRun       ORG_PATH = "business__organization"

and uses `objects = OrgScopedQuerySet.as_manager()`. Then
`Model.objects.for_user(user)` returns only rows in organizations the user belongs to.

This lives in `common/` (not `accounts/`) because models import it, and it must not
import anything from Django's auth views, or app loading becomes circular.
"""

from django.db import models


def membership_lookup(model) -> str:
    """Build the filter keyword that reaches Membership.user from `model`."""
    path = model.ORG_PATH
    return f"{path}__memberships__user" if path else "memberships__user"


class OrgScopedQuerySet(models.QuerySet):
    def for_user(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        return self.filter(**{membership_lookup(self.model): user}).distinct()
