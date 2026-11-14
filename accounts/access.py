"""
Organization-level access control for views: the ONE place pages and API endpoints
decide who sees what.

The filter itself is `OrgScopedQuerySet.for_user()` in common/querysets.py. The mixins
below apply it to every class-based view and DRF ViewSet. A record from another
organization is simply absent from the queryset, so views answer 404, not 403. That
way we don't even confirm that the record exists.
"""

from django.contrib.auth.mixins import LoginRequiredMixin

from common.querysets import membership_lookup

from .models import Membership


def organization_for(user):
    """
    The organization a user is working in.

    The MVP gives each user one organization (created at sign-up). If multi-org support
    is added later, this is the function that would read the "current org" from the
    session instead.
    """
    if not user or not user.is_authenticated:
        return None
    membership = (
        Membership.objects.select_related("organization")
        .filter(user=user)
        .order_by("created_at")
        .first()
    )
    return membership.organization if membership else None


class OrgScopedMixin:
    """
    Use in any class-based view or DRF ViewSet that has a `model` or `queryset`.

    It narrows get_queryset() to the user's organizations, so list, detail, update and
    delete are all protected by the same line of code.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**{membership_lookup(queryset.model): self.request.user}).distinct()


class OrgPageMixin(LoginRequiredMixin, OrgScopedMixin):
    """For HTML pages: send anonymous users to login, then scope by organization."""
