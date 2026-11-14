from django.views.generic import DetailView

from accounts.access import OrgPageMixin

from .models import Decision
from .services.brief import build_brief


class DecisionBriefView(OrgPageMixin, DetailView):
    """The printable brief. Same data as GET /api/v1/decisions/<id>/report/."""

    model = Decision
    template_name = "decisions/brief.html"
    context_object_name = "decision"

    def get_queryset(self):
        return super().get_queryset().select_related("business", "run__scenario", "owner")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["brief"] = build_brief(self.object)
        return context
