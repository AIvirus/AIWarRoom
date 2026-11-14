from rest_framework import serializers

from businesses.models import BusinessProfile
from simulation_engine import catalog

from .models import Scenario, SimulationResult, SimulationRun


class ScenarioSerializer(serializers.ModelSerializer):
    # The queryset is narrowed to the user's organization in __init__, so a client can't
    # attach a scenario to someone else's business by guessing its id.
    business = serializers.PrimaryKeyRelatedField(queryset=BusinessProfile.objects.none())
    missing_inputs = serializers.SerializerMethodField()

    class Meta:
        model = Scenario
        fields = [
            "id",
            "business",
            "template_key",
            "kind",
            "name",
            "parameters",
            "missing_inputs",
            "created_at",
        ]
        read_only_fields = ["id", "kind", "created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None:
            self.fields["business"].queryset = BusinessProfile.objects.for_user(
                request.user
            ).active()

    def get_missing_inputs(self, scenario) -> list[str]:
        """Assumptions the business still needs before this scenario can run."""
        available = set(scenario.business.assumptions.values_list("key", flat=True))
        return catalog.missing_inputs(scenario.template_key, available)

    def validate(self, attrs):
        business = attrs.get("business") or self.instance.business
        template_key = attrs.get("template_key") or self.instance.template_key
        if self.instance and template_key != self.instance.template_key:
            raise serializers.ValidationError({"template_key": "can't change after creation"})
        if self.instance and business != self.instance.business:
            raise serializers.ValidationError({"business": "can't change after creation"})

        template = catalog.TEMPLATES[template_key]
        if template.mode != business.mode:
            raise serializers.ValidationError(
                {"template_key": f"'{template.name}' needs a business in '{template.mode}' mode"}
            )
        parameters = attrs.get("parameters", self.instance.parameters if self.instance else {})
        try:
            attrs["parameters"] = catalog.validate_parameters(template_key, parameters)
        except catalog.CatalogError as error:
            raise serializers.ValidationError({"parameters": error.errors}) from None
        return attrs


class SimulationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulationResult
        fields = ["case_key", "label", "metrics", "timeline"]


class SimulationRunSerializer(serializers.ModelSerializer):
    scenario_name = serializers.CharField(source="scenario.name", read_only=True)
    template_key = serializers.CharField(source="scenario.template_key", read_only=True)
    results = SimulationResultSerializer(many=True, read_only=True)

    class Meta:
        model = SimulationRun
        fields = [
            "id",
            "scenario",
            "scenario_name",
            "template_key",
            "business",
            "status",
            "engine_version",
            "input_hash",
            "input_snapshot",
            "summary",
            "warnings",
            "error",
            "results",
            "created_at",
        ]
        read_only_fields = fields
