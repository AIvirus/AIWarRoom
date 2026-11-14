from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from accounts.access import OrgScopedMixin
from simulation_engine import catalog

from .models import Scenario, SimulationRun
from .serializers import ScenarioSerializer, SimulationRunSerializer


class ScenarioViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Scenarios in my organization. Filter one business with ?business=<id>."""

    serializer_class = ScenarioSerializer
    queryset = Scenario.objects.select_related("business")
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        return queryset.filter(business_id=business_id) if business_id else queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SimulationRunViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    """
    Read-only history. Runs are created by POST /scenarios/<id>/run/ (engine phase) and are
    never edited afterwards: they are the record of what the numbers were.
    """

    serializer_class = SimulationRunSerializer
    queryset = SimulationRun.objects.select_related("scenario").prefetch_related("results")

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        return queryset.filter(business_id=business_id) if business_id else queryset


@api_view(["GET"])
def scenario_templates(request):
    """The scenario types the engine supports, with every parameter's unit and bounds."""
    return Response(
        [
            {
                "key": t.key,
                "name": t.name,
                "kind": t.kind,
                "mode": t.mode,
                "description": t.description,
                "required_inputs": list(t.required_inputs),
                "parameters": [catalog.describe(p) for p in t.parameters],
            }
            for t in catalog.TEMPLATES.values()
        ]
    )


@api_view(["GET"])
def input_catalog(request):
    """Every business assumption the engine understands, grouped by business mode."""
    return Response(
        {
            mode: [catalog.describe(f) for f in catalog.INPUTS.values() if mode in f.modes]
            for mode in (catalog.IDEA, catalog.OPERATING)
        }
    )
