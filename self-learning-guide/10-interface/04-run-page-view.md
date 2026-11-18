# 10.4 · The run page view

**Time:** 45 minutes · **Before this:** [10.3](03-business-views.md).

## Read

One address, `/runs/<id>/`, shows two different pages:

| The run's template kind | Page | Sliders offered |
|---|---|---|
| `idea_case` | **Idea Bench** (`bench.html`) | Price, costs, conversion, marketing, retention... |
| `disruption` | **Situation Board** (`board.html`) | The outage's parameters, plus the business inputs **this** outage uses |

The view's main job is to build `page_data`: everything the JavaScript needs, in one
dictionary. The saved run (with its timelines), the slider specs, and the **addresses**
of the API endpoints to call. The addresses are made with `reverse(...)` from their
names, so the JavaScript never has a hard-coded `/api/v1/...` that could go out of date.

The run page also has a "Record a decision" form, so this lesson adds `DecisionForm` and
the view that saves it (the one Part 9 left for later).

## Do

### 1. `simulations/views.py`

#### Piece 1: slider lists (lines 1–33)

<!-- source: simulations/views.py:1-33 -->
```python
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
```

#### Piece 2: `run_detail` (lines 36–95)

<!-- source: simulations/views.py:36-95 -->
```python
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
```

### 2. `decisions/forms.py`

<!-- source: decisions/forms.py:1-41 -->
```python
from django import forms

from accounts.models import User

from .models import Decision


class DecisionForm(forms.ModelForm):
    """Record a decision straight from a run page. It always starts as 'proposed'."""

    class Meta:
        model = Decision
        fields = ["title", "chosen_strategy", "owner", "rationale"]
        labels = {"rationale": "Why"}
        widgets = {
            "rationale": forms.Textarea(
                attrs={"rows": 3, "placeholder": "What you chose, what it costs, what you accept."}
            ),
        }

    def __init__(self, *args, run, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.run = run
        cases = [(r.case_key, r.label) for r in run.results.all()]
        self.fields["chosen_strategy"] = forms.ChoiceField(
            label="Chosen response", choices=[("", "Not chosen yet"), *cases], required=False
        )
        self.fields["owner"].queryset = User.objects.filter(
            memberships__organization=run.business.organization
        )
        self.fields["owner"].required = False
        self.fields["owner"].empty_label = "Unassigned"
        self.fields["title"].widget.attrs["placeholder"] = "e.g. Contract a backup payment gateway"

    def save(self, commit=True):
        decision = super().save(commit=False)
        decision.business = self.run.business
        decision.run = self.run
        if commit:
            decision.save()
        return decision
```

### 3. Finish `decisions/views.py`

Add two imports at the top, so lines 1–13 look like this (lines 8 and 10 are new):

<!-- source: decisions/views.py:1-13 -->
```python
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
```

Then add this view **between** `DecisionBriefView` and `decision_status`:

<!-- source: decisions/views.py:35-48 -->
```python
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
```

Your `decisions/views.py` is now the same as the reference project's.

## Check

```bash
python manage.py check
```

`System check identified no issues (0 silenced).`

## Line by line

### `simulations/views.py`, piece 1

- **Lines 1–8** · Docstring: one JSON blob for the browser, and the promise that the
  JavaScript never invents a number.
- **Lines 10–12** · Login, shortcuts and `reverse`.
- **Lines 14–16** · The decision form, the AI table and the catalogue.
- **Lines 18–19** · Runs, and the run serializer from Part 6 (it includes results and
  timelines).
- **Lines 21–31** · The Idea Bench sliders, in the order a founder thinks: price and cost
  first, then winning customers, then keeping them, then fixed costs.
- **Lines 32–33** · Business inputs the Situation Board may offer. The outage's own
  parameters (duration, start hour...) come on top.

### Piece 2: `run_detail`

- **Lines 36–41** · The run, only if it's yours, with its scenario and business loaded in
  the same query.
- **Lines 42–43** · Its template and its frozen inputs.
- **Lines 44–49** · Which sliders: the idea list, or only the disruption inputs this
  template actually uses (recapture matters for a payment outage; capacity for a
  warehouse).
- **Line 50** · The assumptions the run was made with.
- **Lines 51–55** · For each slider: the catalogue's description of the input (label,
  unit, min, max, help) merged with the run's saved value and source. `{**a, **b}` makes
  one dictionary from two. Inputs the run didn't have are skipped.
- **Lines 56–77** · `page_data`:
  - **Line 57** · The whole saved run, as the API would send it.
  - **Lines 58–66** · The template: name, kind, how losses work, which component kind
    fails, the response strategies, and each parameter's description.
  - **Lines 67–68** · The sliders and the business.
  - **Lines 69–76** · Addresses for the JavaScript: preview, AI analysis, the scenario
    (to save new parameters), "run it again", the assumptions, and this page's own
    address with the run id swapped for `RUN_ID`, so the JavaScript can open a **new**
    run's page by replacing it.
- **Line 78** · Bench or board.
- **Lines 79–95** · Render it with the run, the template, `page_data`, the run's latest
  AI explanation, the business's latest committee review, an empty decision form, and up
  to five other runs of the same scenario.

### `decisions/forms.py`

- **Lines 1–5** · Forms, users, and the Decision table.
- **Lines 8–9** · A ModelForm, and its docstring: always starts as proposed.
- **Lines 11–19** · Four fields only (status isn't one of them: nobody can create an
  approved decision here either). "Why" as the rationale's label, with a hint.
- **Lines 21–23** · `run` and `user` must be given by name (`*args, run, user`).
- **Lines 24–27** · The chosen response is a drop-down of **this run's** cases, plus "Not
  chosen yet".
- **Lines 28–32** · The owner can only be someone in the business's organization, or
  nobody ("Unassigned").
- **Line 33** · A placeholder example title.
- **Lines 35–41** · `save`: fill in the business and run from the run, then save.

### `decisions/views.py`

- **Line 8** · Runs, to find the one the form was posted from.
- **Line 10** · The new form.
- **Lines 35–37** · `decision_create`: logged in, POST only, from one run.
- **Line 38** · The run, only if it's yours.
- **Line 39** · The form with what was sent.
- **Lines 40–42** · Not valid (the title is the only required field): say so, back to the
  run page.
- **Lines 43–46** · Save it with its creator, and start its history (lesson 9.3).
- **Lines 47–48** · "Recorded as proposed. Sign it off from the brief." and open the
  brief.

## If it didn't work

| You see | Fix |
|---|---|
| `ImportError: cannot import name 'DecisionForm'` | Create `decisions/forms.py` (step 2) before checking. |
| `ImportError: cannot import name 'SimulationRunSerializer'` | It's in `simulations/serializers.py` (Part 6). |

## Quiz

1. Why does `page_data` contain addresses instead of the JavaScript writing them?
2. What does `RUN_ID` in `run_page` let the JavaScript do?
3. Can the run page's form create an already-approved decision?

---

**Next:** [10.5 · Connect the addresses](05-connect-the-addresses.md)

<details><summary>Quiz answers</summary>

1. They come from `reverse()`, so if an address ever changes in `urls.py`, the page
   follows automatically.
2. Open the page of a **new** run after saving, by replacing `RUN_ID` with its id.
3. No. Status isn't a form field; the model's default is "proposed".

</details>
