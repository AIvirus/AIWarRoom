from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from accounts.access import OrgScopedMixin
from businesses.api import business_for
from config.api_errors import DomainError
from intelligence.api import AIAnalysisSerializer, ai_error
from intelligence.models import AIAnalysis
from intelligence.services import ai_client
from intelligence.services.explain import explain_run
from simulation_engine import catalog

from .models import Scenario, SimulationRun
from .serializers import ScenarioSerializer, SimulationRunSerializer
from .services.run_service import SimulationInputError, preview, run_scenario


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

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        """Freeze the inputs, run the engine, save the run. 201 with the full result."""
        scenario = self.get_object()
        try:
            run = run_scenario(scenario, request.user)
        except SimulationInputError as error:
            raise DomainError(str(error), error.fields, code="simulation_input_error") from None
        return Response(SimulationRunSerializer(run).data, status=status.HTTP_201_CREATED)


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

    @action(detail=True, methods=["get", "post"])
    def analysis(self, request, pk=None):
        """
        GET:  the latest AI explanation of this run (404 if none yet).
        POST: ask Gemini for one. 201 when newly generated, 200 when served from cache.
        """
        run = self.get_object()
        if request.method == "GET":
            latest = run.analyses.filter(
                kind=AIAnalysis.Kind.RUN_EXPLANATION, status=AIAnalysis.Status.OK
            ).first()
            if latest is None:
                raise DomainError("No AI analysis for this run yet.", code="not_found",
                                  status_code=404)  # fmt: skip
            return Response(AIAnalysisSerializer(latest).data)
        try:
            analysis = explain_run(run)
        except ai_client.AIError as error:
            raise ai_error(error) from None
        code = status.HTTP_200_OK if analysis.from_cache else status.HTTP_201_CREATED
        return Response(AIAnalysisSerializer(analysis).data, status=code)


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


class PreviewRequest(serializers.Serializer):
    business = serializers.UUIDField()
    template_key = serializers.ChoiceField(choices=sorted(catalog.TEMPLATES))
    parameters = serializers.DictField(required=False, default=dict)
    # What-if values for assumptions, e.g. {"average_order_value": "650"} from a slider.
    assumptions = serializers.DictField(required=False, default=dict)


@api_view(["POST"])
def simulate_preview(request):
    """
    Run the engine on what-if values WITHOUT saving anything. The sliders call this on
    every change; the engine answers in milliseconds, so this can be "live".
    """
    body = PreviewRequest(data=request.data)
    body.is_valid(raise_exception=True)
    data = body.validated_data
    business = business_for(request.user, data["business"])
    if catalog.TEMPLATES[data["template_key"]].mode != business.mode:
        raise DomainError("This scenario doesn't apply to this kind of business.")
    try:
        result = preview(business, data["template_key"], data["parameters"], data["assumptions"])
    except SimulationInputError as error:
        raise DomainError(str(error), error.fields, code="simulation_input_error") from None
    return Response(result)
