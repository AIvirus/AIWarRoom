"""
Business endpoints. Every view gets its rows through OrgScopedMixin or business_for(),
so a user can only ever touch businesses in their own organization.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.access import OrgScopedMixin, organization_for
from accounts.models import Membership

from .models import BusinessComponent, BusinessProfile
from .serializers import (
    AssumptionBulkSerializer,
    BusinessComponentSerializer,
    BusinessProfileSerializer,
    FinancialAssumptionSerializer,
)


def business_for(user, business_id) -> BusinessProfile:
    """The business with this id IF the user's organization owns it; otherwise 404."""
    return get_object_or_404(BusinessProfile.objects.for_user(user), pk=business_id)


class BusinessViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = BusinessProfileSerializer
    queryset = BusinessProfile.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list" and self.request.query_params.get("archived") != "true":
            queryset = queryset.active()
        return queryset

    def perform_create(self, serializer):
        # The organization comes from the logged-in user, never from the request body.
        organization = organization_for(self.request.user)
        if organization is None:  # e.g. a superuser made with createsuperuser
            raise PermissionDenied("Your account isn't part of an organization yet.")
        serializer.save(organization=organization, created_by=self.request.user)

    def perform_destroy(self, instance):
        """DELETE archives: past runs and decisions must stay readable. Owners only."""
        is_owner = Membership.objects.filter(
            user=self.request.user, organization=instance.organization, role=Membership.Role.OWNER
        ).exists()
        if not is_owner:
            raise PermissionDenied("Only an organization owner can archive a business.")
        instance.archived_at = timezone.now()
        instance.save(update_fields=["archived_at", "updated_at"])

    @action(detail=True, methods=["get", "put"])
    def assumptions(self, request, pk=None):
        business = self.get_object()
        if request.method == "GET":
            data = FinancialAssumptionSerializer(business.assumptions.all(), many=True).data
            return Response(data)
        serializer = AssumptionBulkSerializer(data=request.data, context={"business": business})
        serializer.is_valid(raise_exception=True)
        saved = serializer.save()
        return Response(FinancialAssumptionSerializer(saved, many=True).data)


class ComponentViewSet(viewsets.ModelViewSet):
    """Components of one business: /api/v1/businesses/<business_pk>/components/."""

    serializer_class = BusinessComponentSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_business(self):
        if not hasattr(self, "_business"):
            self._business = business_for(self.request.user, self.kwargs["business_pk"])
        return self._business

    def get_queryset(self):
        return BusinessComponent.objects.filter(business=self.get_business()).prefetch_related(
            "depends_on"
        )

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "business": self.get_business()}

    def perform_create(self, serializer):
        serializer.save(business=self.get_business())
