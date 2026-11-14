"""
The run page: a Situation Board for disruptions, an Idea Bench for idea stress tests.

The view hands the browser everything it needs as one JSON blob (via json_script): the
saved run with its timelines, the parameter and input specs for the sliders, and the API
URLs to call. The JavaScript never invents a number; it draws what the engine returned
and asks the preview endpoint when a slider moves.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from decisions.forms import DecisionForm
from intelligence.models import AIAnalysis
from simulation_engine import catalog

from .models import SimulationRun
from .serializers import SimulationRunSerializer

# Inputs the Idea Bench offers as sliders, in the order a founder thinks about them.
IDEA_SLIDERS = [
    "price_per_order",
    "variable_cost_per_order",
    "conversion_rate",
    "cost_per_visit",
    "marketing_spend_monthly",
    "orders_per_customer_monthly",
    "monthly_retention",
    "fixed_costs_monthly",
]
# Business assumptions the Situation Board offers as sliders (parameters come on top).
DISRUPTION_INPUT_SLIDERS = ["recapture_rate", "cancel_rate_per_delay_hour", "hourly_capacity"]


@login_required
def run_detail(request, pk):
    run = get_object_or_404(
        SimulationRun.objects.for_user(request.user).select_related("scenario", "business"),
        pk=pk,
    )
    template = catalog.TEMPLATES[run.scenario.template_key]
    snapshot = run.input_snapshot
    if template.kind == "idea_case":
        slider_keys = IDEA_SLIDERS
    else:
        # Only inputs this disruption actually uses: recapture matters for a payment
        # outage, cancellations and capacity for a warehouse or courier failure.
        slider_keys = [k for k in DISRUPTION_INPUT_SLIDERS if k in template.required_inputs]
    saved = snapshot.get("assumptions", {})
    inputs = [
        {**catalog.describe(catalog.INPUTS[key]), **saved[key]}
        for key in slider_keys
        if key in saved
    ]
    page_data = {
        "run": SimulationRunSerializer(run).data,
        "template": {
            "key": template.key,
            "name": template.name,
            "kind": template.kind,
            "loss_mode": template.loss_mode,
            "component_kind": template.component_kind,
            "strategies": [{"key": k, "label": label} for k, label in template.strategies],
            "parameters": [catalog.describe(p) for p in template.parameters],
        },
        "inputs": inputs,
        "business": {"id": str(run.business_id), "name": run.business.name},
        "urls": {
            "preview": reverse("api:simulate-preview"),
            "analysis": reverse("api:run-analysis", args=[run.pk]),
            "scenario": reverse("api:scenario-detail", args=[run.scenario_id]),
            "scenario_run": reverse("api:scenario-run", args=[run.scenario_id]),
            "assumptions": reverse("api:business-assumptions", args=[run.business_id]),
            "run_page": reverse("run-detail", args=[run.pk]).replace(str(run.pk), "RUN_ID"),
        },
    }
    page = "simulations/bench.html" if template.kind == "idea_case" else "simulations/board.html"
    return render(
        request,
        page,
        {
            "run": run,
            "template": template,
            "page_data": page_data,
            "analysis": run.analyses.filter(
                kind=AIAnalysis.Kind.RUN_EXPLANATION, status=AIAnalysis.Status.OK
            ).first(),
            "committee": run.business.analyses.filter(
                kind=AIAnalysis.Kind.COMMITTEE, status=AIAnalysis.Status.OK
            ).first(),
            "decision_form": DecisionForm(run=run, user=request.user),
            "other_runs": run.scenario.runs.exclude(pk=run.pk)[:5],
        },
    )
