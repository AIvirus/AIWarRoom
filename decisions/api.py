from rest_framework import serializers, viewsets

from accounts.access import OrgScopedMixin
from accounts.models import User
from businesses.models import BusinessProfile
from simulations.models import SimulationRun

from .models import Decision


class DecisionSerializer(serializers.ModelSerializer):
    # All three related fields are narrowed to the user's organization in __init__.
    business = serializers.PrimaryKeyRelatedField(queryset=BusinessProfile.objects.none())
    run = serializers.PrimaryKeyRelatedField(
        queryset=SimulationRun.objects.none(), required=False, allow_null=True
    )
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.none(), required=False, allow_null=True
    )
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Decision
        fields = [
            "id",
            "business",
            "run",
            "title",
            "owner",
            "owner_name",
            "status",
            "chosen_strategy",
            "rationale",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None:
            user = request.user
            self.fields["business"].queryset = BusinessProfile.objects.for_user(user)
            self.fields["run"].queryset = SimulationRun.objects.for_user(user)
            # Owners must be people in the same organization(s) as the requester.
            self.fields["owner"].queryset = User.objects.filter(
                memberships__organization__memberships__user=user
            ).distinct()

    def get_owner_name(self, decision) -> str | None:
        return str(decision.owner) if decision.owner else None

    def validate(self, attrs):
        business = attrs.get("business") or self.instance.business
        if self.instance and business != self.instance.business:
            raise serializers.ValidationError({"business": "can't change after creation"})
        run = attrs.get("run")
        if run is not None and run.business_id != business.id:
            raise serializers.ValidationError({"run": "belongs to a different business"})
        if run is not None and attrs.get("chosen_strategy"):
            case_keys = set(run.results.values_list("case_key", flat=True))
            if case_keys and attrs["chosen_strategy"] not in case_keys:
                raise serializers.ValidationError(
                    {"chosen_strategy": f"must be one of this run's cases: {sorted(case_keys)}"}
                )
        return attrs


class DecisionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = DecisionSerializer
    queryset = Decision.objects.select_related("owner", "business")
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        return queryset.filter(business_id=business_id) if business_id else queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
