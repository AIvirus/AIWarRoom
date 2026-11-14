"""
Read access to AI analyses, scans and alerts. Creating them (calling Gemini, fetching
sites) arrives in the AI and URL-analyzer phases.
"""

from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.access import OrgScopedMixin
from config.api_errors import DomainError

from .models import AIAnalysis, Alert, CompanyScan

# How each AI failure is reported over HTTP.
AI_ERROR_STATUS = {
    "ai_unavailable": 503,
    "ai_rate_limited": 429,
    "ai_invalid_output": 502,
    "ai_provider_error": 502,
}


def ai_error(error) -> DomainError:
    return DomainError(
        error.message, code=error.code, status_code=AI_ERROR_STATUS.get(error.code, 502)
    )


class AIAnalysisSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = AIAnalysis
        fields = [
            "id",
            "business",
            "run",
            "scan",
            "kind",
            "status",
            "label",
            "model_name",
            "prompt_version",
            "output",
            "flagged_numbers",
            "sources",
            "error",
            "created_at",
            "from_cache",
        ]
        read_only_fields = fields

    from_cache = serializers.BooleanField(read_only=True)

    def get_label(self, obj) -> str:
        # Shipped with every payload so no client can forget to show it.
        return "AI analysis. Not a forecast; check flagged numbers against the simulation."


class CompanyScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyScan
        fields = [
            "id",
            "business",
            "url",
            "status",
            "robots_allowed",
            "pages",
            "log",
            "error",
            "created_at",
            "finished_at",
        ]
        read_only_fields = fields


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            "id",
            "business",
            "scan",
            "severity",
            "kind",
            "summary",
            "detail",
            "acknowledged_at",
            "created_at",
        ]
        read_only_fields = fields


class BusinessFilterMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        return queryset.filter(business_id=business_id) if business_id else queryset


class AIAnalysisViewSet(OrgScopedMixin, BusinessFilterMixin, viewsets.ReadOnlyModelViewSet):
    """Filter with ?business=<id>&kind=site_profile|committee|run_explanation."""

    serializer_class = AIAnalysisSerializer
    queryset = AIAnalysis.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        kind = self.request.query_params.get("kind")
        return queryset.filter(kind=kind) if kind else queryset


class CompanyScanViewSet(OrgScopedMixin, BusinessFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = CompanyScanSerializer
    queryset = CompanyScan.objects.all()


class AlertViewSet(OrgScopedMixin, BusinessFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertSerializer
    queryset = Alert.objects.all()

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        if alert.acknowledged_at is None:
            alert.acknowledged_at = timezone.now()
            alert.acknowledged_by = request.user
            alert.save(update_fields=["acknowledged_at", "acknowledged_by", "updated_at"])
        return Response(AlertSerializer(alert).data)
