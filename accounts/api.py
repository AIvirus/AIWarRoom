"""JSON endpoints for accounts. Thin: they read through the org-scoped querysets."""

from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .access import OrgScopedMixin, organization_for
from .models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "created_at"]
        read_only_fields = ["id", "slug", "created_at"]


class OrganizationViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Organizations the current user belongs to. Anyone else's org answers 404."""

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


@api_view(["GET"])
def me(request):
    organization = organization_for(request.user)
    return Response(
        {
            "id": request.user.id,
            "email": request.user.email,
            "full_name": request.user.full_name,
            "organization": OrganizationSerializer(organization).data if organization else None,
        }
    )
