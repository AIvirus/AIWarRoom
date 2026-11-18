# 10.3 · The business views

**Time:** 50 minutes · **Before this:** [10.2](02-forms.md).

## Read

Every view in this file follows the same three steps:

1. **Check access.** Find the business through `for_user()`, so someone else's is a 404.
2. **Call one service.** Save assumptions, run a scenario...: the real work lives in the
   services you already wrote.
3. **Render or redirect.** Show a template, or (after a POST) go back to the page with a
   message.

### The "N+1" problem

The dashboard shows each business with **its latest run**. The easy way is a loop that
asks the database "latest run for this business?" once per business. Ten businesses, ten
questions, plus the first one for the list: **N+1** queries. On a database far away (Neon
is in another city), each question takes a few hundredths of a second, and it adds up.

`_latest_completed_runs` asks **once** for the completed runs of all those businesses,
newest first, and keeps the first one it sees for each. One query, whatever the number of
businesses.

## Do

Create `businesses/views.py`.

### Piece 1: helpers and the dashboard (lines 1–64)

<!-- source: businesses/views.py:1-64 -->
```python
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
```

### Piece 2: create, and the business page (lines 67–116)

<!-- source: businesses/views.py:67-116 -->
```python
@login_required
def business_create(request):
    organization = organization_for(request.user)
    if organization is None:  # e.g. a superuser made with createsuperuser
        messages.error(request, "Your account isn't part of an organization yet.")
        return redirect("home")
    form = BusinessForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        business = form.save(commit=False)
        business.organization = organization
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
```

### Piece 3: the buttons (lines 119–189)

<!-- source: businesses/views.py:119-189 -->
```python
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
```

## Check

```bash
python manage.py check
```

`System check identified no issues (0 silenced).` These views get addresses in lesson
10.5 and templates in 10.6–10.7.

## Line by line

### Piece 1

- **Lines 1–4** · Docstring: check access, call one service, render or redirect.
- **Lines 6–11** · Django tools: messages, login, `Count` and `Q` (for counting with a
  condition), shortcuts, `reverse` (build an address from its name), POST-only.
- **Lines 13–18** · Our pieces: who's in which organization, decisions, AI tables, the
  catalogue, scenarios and runs, and the run service with its error.
- **Lines 20–22** · The forms, tables and `save_assumptions`.
- **Lines 25–26** · `_business`: the business with this id, only if it's yours.
- **Lines 29–34** · `_latest_completed_runs(field, ids)` and a docstring explaining N+1.
- **Line 35** · An empty dictionary to fill.
- **Line 36** · One query: completed runs whose `business` (or `scenario`) is in the list.
  `**{f"{field}__in": ids}` builds the filter's name from text: `business__in=ids`.
- **Lines 37–38** · Newest first; `setdefault` only stores the **first** run seen for each
  id, which is the newest. `getattr(run, "business_id")` reads `run.business_id`.
- **Line 39** · Return `{id: run}`.
- **Lines 42–43** · The dashboard, for logged-in users.
- **Lines 45–49** · Your active businesses, each with a count of **unread** alerts.
  `annotate(open_alerts=Count(...))` asks the database to count, in the same query.
  `list(...)` runs the query now, so we can use the ids next.
- **Line 50** · Their latest runs, in one query.
- **Lines 51–64** · Render the dashboard with three lists: businesses (each with its last
  run and alert count), up to 8 unread alerts, and up to 8 recent decisions.

### Piece 2

- **Lines 67–72** · Adding a business: no organization (a superuser made with
  `createsuperuser`)? Explain and go home, instead of crashing.
- **Line 73** · `request.POST or None`: on a POST, the form gets the sent data; on a GET,
  `None`, an empty form.
- **Lines 74–78** · Valid? Save without writing yet (`commit=False`), fill in the
  organization and creator, then save.
- **Lines 79–80** · A message, and on to the new business's page.
- **Line 81** · A GET, or a form with errors: show the page (with the errors).
- **Lines 84–86** · The business page.
- **Line 87** · Its successful AI analyses.
- **Line 88** · Which assumption keys it has.
- **Lines 89–90** · Its scenarios, and their latest runs in one query.
- **Lines 91–98** · Each scenario with its last run and the inputs it's **missing**
  (`catalog.missing_inputs`), so the page can say "Needs: price per order..." and grey out
  the Run button.
- **Lines 99–116** · Render the page with everything it shows: the forms, components,
  scenarios, last 8 runs, latest scan, site profile, committee, 6 unread alerts and 6
  decisions.

### Piece 3

- **Lines 119–130** · Save the assumptions form. Valid: save and say so ("Past runs keep
  the values they used", Part 6's snapshot). Not valid: list each problem in one message.
  Either way, back to the page at `#assumptions`, so it scrolls to the right place.
- **Lines 133–143** · Add a component, then back to `#components`. Errors are joined into
  one message.
- **Lines 146–153** · Remove a component (only one of **this** business's), then back.
- **Lines 156–172** · Create a scenario: check the form, create it with the template's
  **default** parameters (`validate_parameters(key, {})` fills them in), and run it.
- **Lines 175–180** · Run an existing scenario again.
- **Lines 183–189** · `_run_and_open`: run it and open the run's page. If inputs are
  missing, say which, and go back to `#assumptions` so they can be added.

## If it didn't work

| You see | Fix |
|---|---|
| `ImportError: cannot import name 'SimulationInputError'` | It's in `simulations/services/run_service.py` (Part 6). |
| `ImportError: cannot import name 'save_assumptions'` | Lesson 10.2's `businesses/services/assumptions.py`. |

## Quiz

1. What is the "N+1" problem, and how does `_latest_completed_runs` avoid it?
2. Why does every POST view end with a redirect?
3. What does the business page do when a scenario is missing inputs?

---

**Next:** [10.4 · The run page view](04-run-page-view.md)

<details><summary>Quiz answers</summary>

1. One query for the list plus one per row. It fetches all the runs in one query and
   keeps the newest per id.
2. Post, then redirect (lesson 9.6): a refresh won't send the form again.
3. It lists the missing inputs and disables the Run button.

</details>
