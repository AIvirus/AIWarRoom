from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.access import OrgScopedMixin
from accounts.models import User
from businesses.models import BusinessProfile
from simulations.models import SimulationRun

from .models import Decision
from .services import workflow
from .services.brief import build_brief


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
    decided_by_name = serializers.SerializerMethodField()
    allowed_next_status = serializers.SerializerMethodField()
    # Optional reason recorded in the history when the status changes.
    note = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=280)

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
            "allowed_next_status",
            "chosen_strategy",
            "rationale",
            "note",
            "decided_by_name",
            "decided_at",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "decided_at", "history", "created_at", "updated_at"]

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

    def get_decided_by_name(self, decision) -> str | None:
        return str(decision.decided_by) if decision.decided_by else None

    def get_allowed_next_status(self, decision) -> list[str]:
        return workflow.allowed_next(decision.status)

    def validate_status(self, value):
        if self.instance is None:
            if value != Decision.Status.PROPOSED:
                raise serializers.ValidationError("New decisions start as 'proposed'.")
            return value
        try:
            workflow.check_transition(self.instance.status, value)
        except workflow.InvalidTransition as error:
            raise serializers.ValidationError(str(error)) from None
        return value

    def validate(self, attrs):
        business = attrs.get("business") or self.instance.business
        if self.instance and business != self.instance.business:
            raise serializers.ValidationError({"business": "can't change after creation"})
        run = attrs.get("run", self.instance.run if self.instance else None)
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
        serializer.validated_data.pop("note", None)
        decision = serializer.save(created_by=self.request.user)
        workflow.record_creation(decision, self.request.user)

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        note = serializer.validated_data.pop("note", "")
        decision = serializer.save()
        workflow.record_status_change(decision, old_status, self.request.user, note)

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        """The decision brief as structured JSON (the printable page renders the same data)."""
        return Response(build_brief(self.get_object()))
