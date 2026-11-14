"""
HTML pages for businesses. Each view: check access, call one service, render or redirect.
Every lookup goes through `for_user()`, so another organization's records are a 404.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.access import organization_for
from decisions.models import Decision
from intelligence.models import AIAnalysis, Alert
from simulation_engine import catalog
from simulations.models import Scenario, SimulationRun
from simulations.services.run_service import SimulationInputError, run_scenario

from .forms import AssumptionsForm, BusinessForm, ComponentForm, ScenarioForm
from .models import BusinessComponent, BusinessProfile
from .services.assumptions import save_assumptions


def _business(request, pk) -> BusinessProfile:
    return get_object_or_404(BusinessProfile.objects.for_user(request.user), pk=pk)


def _latest_completed_runs(field: str, ids) -> dict:
    """
    {business_id or scenario_id: its newest completed run} in ONE query.
    Asking each row for "its latest run" separately would cost a database round trip per
    row (the "N+1" problem), which hurts on a remote database like Neon.
    """
    latest = {}
    runs = SimulationRun.objects.filter(**{f"{field}__in": ids}, status="completed")
    for run in runs.select_related("scenario").order_by("-created_at"):
        latest.setdefault(getattr(run, f"{field}_id"), run)
    return latest


@login_required
def dashboard(request):
    user = request.user
    businesses = list(
        BusinessProfile.objects.for_user(user)
        .active()
        .annotate(open_alerts=Count("alerts", filter=Q(alerts__acknowledged_at__isnull=True)))
    )
    last_runs = _latest_completed_runs("business", [b.pk for b in businesses])
    return render(
        request,
        "businesses/dashboard.html",
        {
            "businesses": [
                {"business": b, "last_run": last_runs.get(b.pk), "open_alerts": b.open_alerts}
                for b in businesses
            ],
            "alerts": Alert.objects.for_user(user)
            .filter(acknowledged_at__isnull=True)
            .select_related("business")[:8],
            "decisions": Decision.objects.for_user(user).select_related("business", "owner")[:8],
        },
    )


@login_required
def business_create(request):
    form = BusinessForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        business = form.save(commit=False)
        business.organization = organization_for(request.user)
        business.created_by = request.user
        business.save()
        messages.success(request, f"{business.name} is on the board. Add its numbers next.")
        return redirect("business-detail", pk=business.pk)
    return render(request, "businesses/create.html", {"form": form})


@login_required
def business_detail(request, pk):
    business = _business(request, pk)
    analyses = business.analyses.filter(status=AIAnalysis.Status.OK)
    available = set(business.assumptions.values_list("key", flat=True))
    scenario_list = list(Scenario.objects.filter(business=business))
    last_runs = _latest_completed_runs("scenario", [s.pk for s in scenario_list])
    scenarios = [
        {
            "scenario": s,
            "last_run": last_runs.get(s.pk),
            "missing": catalog.missing_inputs(s.template_key, available),
        }
        for s in scenario_list
    ]
    return render(
        request,
        "businesses/detail.html",
        {
            "business": business,
            "assumptions_form": AssumptionsForm(business),
            "component_form": ComponentForm(business),
            "components": business.components.prefetch_related("depends_on"),
            "scenario_form": ScenarioForm(business),
            "scenarios": scenarios,
            "runs": SimulationRun.objects.filter(business=business).select_related("scenario")[:8],
            "latest_scan": business.scans.first(),
            "site_profile": analyses.filter(kind=AIAnalysis.Kind.SITE_PROFILE).first(),
            "committee": analyses.filter(kind=AIAnalysis.Kind.COMMITTEE).first(),
            "alerts": business.alerts.filter(acknowledged_at__isnull=True)[:6],
            "decisions": business.decisions.select_related("owner")[:6],
        },
    )


@login_required
@require_POST
def assumptions_update(request, pk):
    business = _business(request, pk)
    form = AssumptionsForm(business, request.POST)
    if form.is_valid():
        save_assumptions(business, form.values())
        messages.success(request, "Assumptions saved. Past runs keep the values they used.")
    else:
        problems = "; ".join(f"{form.fields[k].label}: {v[0]}" for k, v in form.errors.items())
        messages.error(request, f"Nothing saved. {problems}")
    return redirect(reverse("business-detail", args=[pk]) + "#assumptions")


@login_required
@require_POST
def component_create(request, pk):
    business = _business(request, pk)
    form = ComponentForm(business, request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, f"Added {form.instance.name}.")
    else:
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
    return redirect(reverse("business-detail", args=[pk]) + "#components")


@login_required
@require_POST
def component_delete(request, pk, component_pk):
    business = _business(request, pk)
    component = get_object_or_404(BusinessComponent, pk=component_pk, business=business)
    component.delete()
    messages.success(request, f"Removed {component.name}.")
    return redirect(reverse("business-detail", args=[pk]) + "#components")


@login_required
@require_POST
def scenario_create(request, pk):
    """Create a scenario with default parameters and run it straight away."""
    business = _business(request, pk)
    form = ScenarioForm(business, request.POST)
    if not form.is_valid():
        messages.error(request, "Pick what to test and give it a name.")
        return redirect(reverse("business-detail", args=[pk]) + "#scenarios")
    scenario = Scenario.objects.create(
        business=business,
        template_key=form.cleaned_data["template_key"],
        name=form.cleaned_data["name"],
        parameters=catalog.validate_parameters(form.cleaned_data["template_key"], {}),
        created_by=request.user,
    )
    return _run_and_open(request, scenario)


@login_required
@require_POST
def scenario_run(request, pk, scenario_pk):
    business = _business(request, pk)
    scenario = get_object_or_404(Scenario, pk=scenario_pk, business=business)
    return _run_and_open(request, scenario)


def _run_and_open(request, scenario):
    try:
        run = run_scenario(scenario, request.user)
    except SimulationInputError as error:
        messages.error(request, f"Can't run “{scenario.name}” yet. {error}")
        return redirect(reverse("business-detail", args=[scenario.business_id]) + "#assumptions")
    return redirect("run-detail", pk=run.pk)
