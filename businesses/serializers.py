from django.db import transaction
from rest_framework import serializers

from simulation_engine import catalog

from .models import BusinessComponent, BusinessProfile, FinancialAssumption
from .services.dependencies import creates_cycle


class BusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = [
            "id",
            "mode",
            "name",
            "industry",
            "description",
            "website_url",
            "currency",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "archived_at", "created_at", "updated_at"]

    def validate_mode(self, value):
        # Switching mode would orphan assumptions that only make sense in the other mode.
        if self.instance and value != self.instance.mode:
            raise serializers.ValidationError("A business can't change mode after creation.")
        return value


class FinancialAssumptionSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)
    # Decimals travel as strings so 0.1 never turns into 0.1000000000000000055.
    value = serializers.DecimalField(max_digits=16, decimal_places=4, coerce_to_string=True)

    class Meta:
        model = FinancialAssumption
        fields = ["key", "label", "value", "unit", "source", "note", "updated_at"]
        read_only_fields = ["unit", "updated_at"]

    def validate(self, attrs):
        key = attrs["key"]
        try:
            attrs["value"] = catalog.parse_input(key, attrs["value"])
        except catalog.CatalogError as error:
            raise serializers.ValidationError(error.errors) from None
        business = self.context["business"]
        if business.mode not in catalog.INPUTS[key].modes:
            raise serializers.ValidationError(
                {key: f"doesn't apply to a business in '{business.mode}' mode"}
            )
        return attrs


class AssumptionBulkSerializer(serializers.Serializer):
    """PUT a list of assumptions; each is created or updated by key."""

    assumptions = FinancialAssumptionSerializer(many=True)

    def validate_assumptions(self, items):
        keys = [item["key"] for item in items]
        duplicates = {key for key in keys if keys.count(key) > 1}
        if duplicates:
            raise serializers.ValidationError(f"Duplicate keys: {', '.join(sorted(duplicates))}")
        return items

    @transaction.atomic
    def save(self):
        business = self.context["business"]
        for item in self.validated_data["assumptions"]:
            FinancialAssumption.objects.update_or_create(
                business=business,
                key=item["key"],
                defaults={
                    "value": item["value"],
                    "source": item.get("source", FinancialAssumption.Source.USER),
                    "note": item.get("note", ""),
                },
            )
        return business.assumptions.all()


class BusinessComponentSerializer(serializers.ModelSerializer):
    # Dependencies are referenced by component key ("payment-gateway"), which reads better
    # in requests and seed files than UUIDs.
    depends_on = serializers.SlugRelatedField(
        slug_field="key", many=True, required=False, queryset=BusinessComponent.objects.none()
    )

    class Meta:
        model = BusinessComponent
        fields = ["id", "key", "name", "kind", "criticality", "fallback_note", "depends_on"]
        read_only_fields = ["id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        business = self.context.get("business")
        if business is not None:
            # Only components of the SAME business can be dependencies.
            self.fields["depends_on"].child_relation.queryset = business.components.all()

    def validate_criticality(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Criticality runs from 1 (minor) to 5 (critical).")
        return value

    def validate_key(self, value):
        business = self.context["business"]
        clash = business.components.filter(key=value)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                "This business already has a component with that key."
            )
        return value

    def validate_depends_on(self, value):
        if self.instance:
            if self.instance in value:
                raise serializers.ValidationError("A component can't depend on itself.")
            if creates_cycle(self.instance, value):
                raise serializers.ValidationError(
                    "That would create a loop (A needs B needs A). Remove one direction."
                )
        return value
