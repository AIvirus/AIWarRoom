from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import DetailView

from accounts.access import OrgPageMixin
from simulations.models import SimulationRun

from .forms import DecisionForm
from .models import Decision
from .services import workflow
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
        context["next_statuses"] = [
            (s, Decision.Status(s).label) for s in workflow.allowed_next(self.object.status)
        ]
        return context


@login_required
@require_POST
def decision_create(request, run_pk):
    run = get_object_or_404(SimulationRun.objects.for_user(request.user), pk=run_pk)
    form = DecisionForm(request.POST, run=run, user=request.user)
    if not form.is_valid():
        messages.error(request, "The decision needs a title.")
        return redirect("run-detail", pk=run.pk)
    decision = form.save(commit=False)
    decision.created_by = request.user
    decision.save()
    workflow.record_creation(decision, request.user)
    messages.success(request, "Decision recorded as proposed. Sign it off from the brief.")
    return redirect("decisions:brief", pk=decision.pk)


@login_required
@require_POST
def decision_status(request, pk):
    decision = get_object_or_404(Decision.objects.for_user(request.user), pk=pk)
    old, new = decision.status, request.POST.get("status", "")
    if new not in Decision.Status.values:
        messages.error(request, "Unknown status.")
        return redirect("decisions:brief", pk=pk)
    try:
        workflow.check_transition(old, new)
    except workflow.InvalidTransition as error:
        messages.error(request, str(error))
        return redirect("decisions:brief", pk=pk)
    decision.status = new
    decision.save(update_fields=["status", "updated_at"])
    workflow.record_status_change(decision, old, request.user, request.POST.get("note", ""))
    messages.success(request, f"Marked {decision.get_status_display().lower()}.")
    return redirect("decisions:brief", pk=pk)
