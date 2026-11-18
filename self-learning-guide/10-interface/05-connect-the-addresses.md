# 10.5 · Connect the addresses

**Time:** 30 minutes · **Before this:** [10.4](04-run-page-view.md).

## Read

Every page needs an address. Each app lists its own in its `urls.py`, and
`config/urls.py` **includes** them under a prefix:

```text
/                                    → the dashboard (replaces the temporary home page)
/businesses/new/                     → add a business
/businesses/<id>/                    → the business page   (+ its buttons' POST addresses)
/runs/<id>/                          → the run page (bench or board)
/decisions/<id>/brief/               → the brief            (Part 9)
/decisions/from-run/<run id>/        → record a decision from a run (new)
/alerts/<id>/acknowledge/            → mark an alert read   (Part 8's view)
```

After this lesson, `config/urls.py` and `decisions/urls.py` are finished, and the brief's
"← Back" link can go where it was always meant to: the run's page, or the business's page.

## Do

### 1. `businesses/urls.py`

<!-- source: businesses/urls.py:1-21 -->
```python
from django.urls import path

from . import views

urlpatterns = [
    path("new/", views.business_create, name="business-create"),
    path("<uuid:pk>/", views.business_detail, name="business-detail"),
    path("<uuid:pk>/assumptions/", views.assumptions_update, name="business-assumptions"),
    path("<uuid:pk>/components/", views.component_create, name="business-component-create"),
    path(
        "<uuid:pk>/components/<uuid:component_pk>/delete/",
        views.component_delete,
        name="business-component-delete",
    ),
    path("<uuid:pk>/scenarios/", views.scenario_create, name="business-scenario-create"),
    path(
        "<uuid:pk>/scenarios/<uuid:scenario_pk>/run/",
        views.scenario_run,
        name="business-scenario-run",
    ),
]
```

### 2. `simulations/urls.py`

<!-- source: simulations/urls.py:1-7 -->
```python
from django.urls import path

from . import views

urlpatterns = [
    path("<uuid:pk>/", views.run_detail, name="run-detail"),
]
```

### 3. `decisions/urls.py` (finished)

Add line 10:

<!-- source: decisions/urls.py:1-11 -->
```python
from django.urls import path

from . import views

app_name = "decisions"

urlpatterns = [
    path("<uuid:pk>/brief/", views.DecisionBriefView.as_view(), name="brief"),
    path("<uuid:pk>/status/", views.decision_status, name="status"),
    path("from-run/<uuid:run_pk>/", views.decision_create, name="create"),
]
```

### 4. `config/urls.py` (finished)

<!-- source: config/urls.py:1-62 -->
```python
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts import api as accounts_api
from businesses import api as businesses_api
from businesses import views as businesses_views
from decisions import api as decisions_api
from intelligence import api as intelligence_api
from intelligence import views as intelligence_views
from simulations import api as simulations_api

from . import views

# One router for the whole JSON API; each app's ViewSets are registered here.
router = DefaultRouter()
router.register("organizations", accounts_api.OrganizationViewSet, basename="organization")
router.register("businesses", businesses_api.BusinessViewSet, basename="business")
router.register("scenarios", simulations_api.ScenarioViewSet, basename="scenario")
router.register("runs", simulations_api.SimulationRunViewSet, basename="run")
router.register("analyses", intelligence_api.AIAnalysisViewSet, basename="analysis")
router.register("scans", intelligence_api.CompanyScanViewSet, basename="scan")
router.register("alerts", intelligence_api.AlertViewSet, basename="alert")
router.register("decisions", decisions_api.DecisionViewSet, basename="decision")

# Components live under their business: /businesses/<id>/components/. Wired by hand
# (rather than a nested-router package) so the mapping is visible.
components_list = businesses_api.ComponentViewSet.as_view({"get": "list", "post": "create"})
components_detail = businesses_api.ComponentViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

api_v1 = [
    path("me/", accounts_api.me, name="me"),
    path("scenario-templates/", simulations_api.scenario_templates, name="scenario-templates"),
    path("inputs/", simulations_api.input_catalog, name="inputs"),
    path("simulate/preview/", simulations_api.simulate_preview, name="simulate-preview"),
    path("scans/<uuid:pk>/events/", intelligence_views.scan_events, name="scan-events"),
    path("businesses/<uuid:business_pk>/components/", components_list, name="component-list"),
    path(
        "businesses/<uuid:business_pk>/components/<uuid:pk>/",
        components_detail,
        name="component-detail",
    ),
    path("", include(router.urls)),
]

urlpatterns = [
    path("", businesses_views.dashboard, name="home"),
    path("accounts/", include("accounts.urls")),
    path("businesses/", include("businesses.urls")),
    path("runs/", include("simulations.urls")),
    path("decisions/", include("decisions.urls")),
    path(
        "alerts/<uuid:pk>/acknowledge/",
        intelligence_views.alert_acknowledge,
        name="alert-acknowledge",
    ),
    path("api/v1/", include((api_v1, "api"), namespace="api")),
    path("admin/", admin.site.urls),
    path("healthz/", views.healthz, name="healthz"),
]
```

### 5. The brief's "← Back" link (finished)

In `templates/decisions/brief.html`, replace line 13 with:

<!-- source: templates/decisions/brief.html:13-13 -->
```html
    <a href="{% if run %}{% url 'run-detail' run.id %}{% else %}{% url 'business-detail' decision.business_id %}{% endif %}">← Back</a>
```

### 6. Delete the temporary home page

Delete `templates/home.html`. The dashboard replaces it.

## Check

```bash
python manage.py check
```

`System check identified no issues (0 silenced).` Now start the server and open
**http://127.0.0.1:8000/**. You'll see a yellow error page:

```text
TemplateDoesNotExist at /
businesses/dashboard.html
```

That's expected: the address works and the view runs, but its template comes in the next
lesson. Learning to read this page is useful: the title says **what** went wrong, and
the line under it says **which** file Django looked for.

## Line by line

### `businesses/urls.py`

- **Lines 1–3** · `path`, and this app's views.
- **Line 6** · `/businesses/new/`. Note there's no `app_name` here: names like
  `business-detail` are used as they are.
- **Line 7** · `/businesses/<id>/`.
- **Lines 8–9** · POST addresses for saving assumptions and adding a component.
- **Lines 10–14** · Removing a component: two ids in the address.
- **Line 15** · Create a scenario (and run it).
- **Lines 16–20** · Run an existing scenario again.

### `simulations/urls.py`

- **Line 6** · `/runs/<id>/`, named `run-detail`.

### `decisions/urls.py`

- **Line 10** · `/decisions/from-run/<run id>/`, named `decisions:create`.

### `config/urls.py`

Compared with Part 9's version:

- **Line 7** · The business **views** (pages), next to the business API on line 6.
- **Line 49** · The home page is now `businesses_views.dashboard`. The temporary
  `TemplateView` is gone, and so are its two imports (`login_required` and
  `TemplateView`) at the top.
- **Lines 51–53** · The business pages under `/businesses/`, run pages under `/runs/`, and
  the decision pages under `/decisions/`.
- **Lines 54–58** · Part 8's `alert_acknowledge`, finally given an address.

Notice the two `businesses/` prefixes don't clash: `/api/v1/businesses/...` is the API,
`/businesses/...` is the pages.

### `brief.html`, line 13

- With a run: back to `run-detail`. Without: back to the business page.
  `decision.business_id` is the business's id without loading the business.

## If it didn't work

| You see | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'simulations.urls'` | Create `simulations/urls.py` (step 2). |
| `NoReverseMatch: Reverse for 'create' not found` (later, on a run page) | `decisions/urls.py` line 10. |
| The home page still shows the old temporary page | Line 49 of `config/urls.py` must be `businesses_views.dashboard`. |

## Quiz

1. Which file decides that business pages live under `/businesses/`?
2. Why is the yellow `TemplateDoesNotExist` page not a problem right now?

---

**Next:** [10.6 · The board, a form, demo data](06-board-form-demo-data.md)

<details><summary>Quiz answers</summary>

1. `config/urls.py`, line 51: `path("businesses/", include("businesses.urls"))`.
2. The address and view work; only the template is missing, and it's the next lesson.

</details>
