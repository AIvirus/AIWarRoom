"""
Business endpoints. Every view gets its rows through OrgScopedMixin or business_for(),
so a user can only ever touch businesses in their own organization.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.access import OrgScopedMixin, organization_for
from accounts.models import Membership
from config.api_errors import DomainError

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
        serializer.save(
            organization=organization_for(self.request.user), created_by=self.request.user
        )

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

    @action(detail=True, methods=["post"])
    def scans(self, request, pk=None):
        """
        Create a scan of the business website. Returns 202 with the URL of its event
        stream; opening that stream is what actually runs the scan.
        """
        from django.urls import reverse

        from intelligence.models import CompanyScan

        business = self.get_object()
        url = (request.data.get("url") or business.website_url or "").strip()
        if not url:
            raise DomainError("Add the company's website URL first.", {"url": ["required"]})
        scan = CompanyScan.objects.create(business=business, url=url)
        events_url = reverse("api:scan-events", args=[scan.id])
        return Response(
            {"scan": str(scan.id), "status": scan.status, "events_url": events_url},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get", "post"])
    def committee(self, request, pk=None):
        """GET the latest committee review; POST convenes a new one (one Gemini call)."""
        from intelligence.api import AIAnalysisSerializer, ai_error
        from intelligence.models import AIAnalysis
        from intelligence.services import ai_client
        from intelligence.services.committee import convene

        business = self.get_object()
        if request.method == "GET":
            latest = business.analyses.filter(
                kind=AIAnalysis.Kind.COMMITTEE, status=AIAnalysis.Status.OK
            ).first()
            if latest is None:
                raise DomainError(
                    "The committee hasn't met yet.", code="not_found", status_code=404
                )
            return Response(AIAnalysisSerializer(latest).data)
        try:
            analysis = convene(business)
        except ai_client.AIError as error:
            raise ai_error(error) from None
        code = status.HTTP_200_OK if analysis.from_cache else status.HTTP_201_CREATED
        return Response(AIAnalysisSerializer(analysis).data, status=code)


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

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(status=status.HTTP_204_NO_CONTENT)
