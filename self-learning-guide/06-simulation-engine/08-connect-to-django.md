# 6.8 · Connect it to Django

**Time:** 45 minutes · **Before this:** [6.7](07-the-runner.md).

## 📖 Read

The engine knows nothing about databases. Django knows nothing about outages. This
lesson builds the small **bridge** between them:

```text
POST /api/v1/scenarios/<id>/run/
   │
   ▼
build_snapshot()   read the business's numbers and components from the database,
   │               and freeze them into one JSON document
   ▼
runner.run()       the pure engine (lessons 6.2–6.7)
   │
   ▼
save               one SimulationRun (with the snapshot) + one SimulationResult per case
```

### The snapshot and its fingerprint

The **snapshot** is a dictionary with everything the run read: the business, the
template, the parameters, every assumption (with unit and source) and every component.
It's saved inside the run, so the run can always be explained, re-checked or printed
exactly as it was (lesson 5.6).

Its **hash** (SHA-256) is a 64-character fingerprint. Identical snapshots always give
the identical hash; change one digit and the hash is completely different. Part 7 uses it
to avoid asking the AI the same question twice.

To make "identical" reliable, the snapshot is written in a fixed way: keys sorted,
numbers without trailing zeros (`2400`, not `2400.0000`).

### Failed runs are recorded too

If a run can't happen (say, a missing number), the app still saves a run marked
**failed**, with the reason. The history shows every attempt, not only the successes.

### Preview: run without saving

The sliders in Part 10 need answers **while you drag**. `POST /api/v1/simulate/preview/`
runs the engine on "what-if" values and saves **nothing**. Because it uses the same
snapshot and the same `runner.run`, a preview and a saved run with the same inputs always
agree.

## ⌨️ Do

### 1. `businesses/services/snapshot.py`

<!-- source: businesses/services/snapshot.py:1-63 -->
```python
"""
Freeze everything a simulation reads into one JSON document.

A run keeps this snapshot forever. Re-running it, explaining it with AI or printing it
in a report always uses these exact values, even if the business is edited later.
"""

import hashlib
import json


def plain(value) -> str:
    """2400.0000 -> "2400", 22.5000 -> "22.5". normalize() alone gives "2.4E+3"."""
    return format(value.normalize(), "f")


def build_snapshot(business, template_key: str, parameters: dict, overrides=None) -> dict:
    """
    `overrides` ({key: value}) replaces assumption values for one-off what-ifs, such as a
    slider in the preview. Overridden values are marked so nobody mistakes them for the
    saved inputs.
    """
    overrides = overrides or {}
    assumptions = {
        a.key: {"value": plain(a.value), "unit": a.unit, "source": a.source}
        for a in business.assumptions.all()
    }
    for key, value in overrides.items():
        unit = assumptions.get(key, {}).get("unit", "")
        assumptions[key] = {"value": str(value), "unit": unit, "source": "what_if"}

    components = [
        {
            "key": c.key,
            "name": c.name,
            "kind": c.kind,
            "criticality": c.criticality,
            "depends_on": sorted(d.key for d in c.depends_on.all()),
        }
        for c in business.components.prefetch_related("depends_on").order_by("key")
    ]
    return {
        "business": {
            "id": str(business.id),
            "name": business.name,
            "mode": business.mode,
            "currency": business.currency,
        },
        "template_key": template_key,
        "parameters": dict(sorted(parameters.items())),
        "assumptions": dict(sorted(assumptions.items())),
        "components": components,
    }


def snapshot_hash(snapshot: dict) -> str:
    """Same inputs -> same hash, regardless of key order (sort_keys) or whitespace."""
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assumption_values(snapshot: dict) -> dict[str, str]:
    return {key: item["value"] for key, item in snapshot["assumptions"].items()}
```

### 2. `simulations/services/run_service.py`

Make the folder `simulations/services/` with an **empty** `__init__.py`, then:

<!-- source: simulations/services/run_service.py:1-111 -->
```python
"""
The bridge between Django and the pure engine.

    run_scenario(scenario, user)  -> SimulationRun   (saved, with results)
    preview(business, ...)        -> dict            (nothing saved; for sliders)

Both build the same snapshot and call the same engine function, so a preview and a saved
run with identical inputs always agree.
"""

import logging
from dataclasses import asdict

from django.db import transaction

from businesses.services.snapshot import assumption_values, build_snapshot, snapshot_hash
from simulation_engine import catalog, runner
from simulations.models import SimulationResult, SimulationRun

logger = logging.getLogger(__name__)


class SimulationInputError(Exception):
    """The user needs to fix something (missing or invalid inputs) before running."""

    def __init__(self, message: str, fields: dict | None = None):
        super().__init__(message)
        self.fields = fields or {}


def _execute(snapshot: dict) -> runner.EngineResult:
    try:
        return runner.run(
            snapshot["template_key"],
            assumption_values(snapshot),
            snapshot["parameters"],
            snapshot["components"],
        )
    except catalog.CatalogError as error:
        raise SimulationInputError("Some inputs are invalid.", error.errors) from None


def run_scenario(scenario, user) -> SimulationRun:
    """
    Snapshot -> engine -> save run + one result row per case.

    If the engine refuses the inputs (e.g. missing assumptions) a FAILED run is saved with
    the reason, so the history shows the attempt, and the error is raised to the caller.
    """
    snapshot = build_snapshot(scenario.business, scenario.template_key, scenario.parameters)
    run = SimulationRun(
        scenario=scenario,
        business=scenario.business,
        input_snapshot=snapshot,
        input_hash=snapshot_hash(snapshot),
        engine_version=runner.ENGINE_VERSION,
        created_by=user,
    )
    try:
        result = _execute(snapshot)
    except (runner.EngineError, SimulationInputError) as error:
        run.status = SimulationRun.Status.FAILED
        run.error = str(error)
        run.save()
        raise SimulationInputError(str(error), getattr(error, "fields", {})) from None

    # The run and its results are saved together or not at all. (The failed-run save
    # above deliberately sits outside this block, so the attempt is always recorded.)
    with transaction.atomic():
        run.status = SimulationRun.Status.COMPLETED
        run.summary = result.summary
        run.warnings = result.warnings
        run.save()
        SimulationResult.objects.bulk_create(
            SimulationResult(
                run=run,
                case_key=case.case_key,
                label=case.label,
                metrics=case.metrics,
                timeline=case.timeline,
            )
            for case in result.cases
        )
    logger.info("Simulation run %s completed (%s cases)", run.id, len(result.cases))
    return run


def preview(business, template_key: str, parameters: dict | None, overrides: dict | None) -> dict:
    """Run the engine on unsaved what-if values. Nothing touches the database."""
    try:
        clean_params = catalog.validate_parameters(template_key, parameters)
        clean_overrides = {
            key: str(catalog.parse_input(key, value)) for key, value in (overrides or {}).items()
        }
    except catalog.CatalogError as error:
        raise SimulationInputError("Some inputs are invalid.", error.errors) from None

    snapshot = build_snapshot(business, template_key, clean_params, clean_overrides)
    try:
        result = _execute(snapshot)
    except runner.EngineError as error:
        raise SimulationInputError(str(error)) from None
    return {
        "engine_version": result.engine_version,
        "template_key": result.template_key,
        "input_hash": snapshot_hash(snapshot),
        "summary": result.summary,
        "warnings": result.warnings,
        "cases": [asdict(case) for case in result.cases],
        "saved": False,
    }
```

### 3. `simulations/api.py` (for now)

Replace the file with the Part 6 version from
[`for-now/simulations/api.py`](for-now/simulations/api.py). Compared with lesson 5.6 it
has new imports, a `run` action and the preview at the end:

<!-- source: self-learning-guide/06-simulation-engine/for-now/simulations/api.py:1-110 -->
```python
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from accounts.access import OrgScopedMixin
from businesses.api import business_for
from config.api_errors import DomainError
from simulation_engine import catalog

from .models import Scenario, SimulationRun
from .serializers import ScenarioSerializer, SimulationRunSerializer
from .services.run_service import SimulationInputError, preview, run_scenario


class ScenarioViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Scenarios in my organization. Filter one business with ?business=<id>."""

    serializer_class = ScenarioSerializer
    queryset = Scenario.objects.select_related("business")
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        return queryset.filter(business_id=business_id) if business_id else queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        """Freeze the inputs, run the engine, save the run. 201 with the full result."""
        scenario = self.get_object()
        try:
            run = run_scenario(scenario, request.user)
        except SimulationInputError as error:
            raise DomainError(str(error), error.fields, code="simulation_input_error") from None
        return Response(SimulationRunSerializer(run).data, status=status.HTTP_201_CREATED)


class SimulationRunViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    """
    Read-only history. Runs are created by POST /scenarios/<id>/run/ (engine phase) and are
    never edited afterwards: they are the record of what the numbers were.
    """

    serializer_class = SimulationRunSerializer
    queryset = SimulationRun.objects.select_related("scenario").prefetch_related("results")

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        return queryset.filter(business_id=business_id) if business_id else queryset


@api_view(["GET"])
def scenario_templates(request):
    """The scenario types the engine supports, with every parameter's unit and bounds."""
    return Response(
        [
            {
                "key": t.key,
                "name": t.name,
                "kind": t.kind,
                "mode": t.mode,
                "description": t.description,
                "required_inputs": list(t.required_inputs),
                "parameters": [catalog.describe(p) for p in t.parameters],
            }
            for t in catalog.TEMPLATES.values()
        ]
    )


@api_view(["GET"])
def input_catalog(request):
    """Every business assumption the engine understands, grouped by business mode."""
    return Response(
        {
            mode: [catalog.describe(f) for f in catalog.INPUTS.values() if mode in f.modes]
            for mode in (catalog.IDEA, catalog.OPERATING)
        }
    )


class PreviewRequest(serializers.Serializer):
    business = serializers.UUIDField()
    template_key = serializers.ChoiceField(choices=sorted(catalog.TEMPLATES))
    parameters = serializers.DictField(required=False, default=dict)
    # What-if values for assumptions, e.g. {"average_order_value": "650"} from a slider.
    assumptions = serializers.DictField(required=False, default=dict)


@api_view(["POST"])
def simulate_preview(request):
    """
    Run the engine on what-if values WITHOUT saving anything. The sliders call this on
    every change; the engine answers in milliseconds, so this can be "live".
    """
    body = PreviewRequest(data=request.data)
    body.is_valid(raise_exception=True)
    data = body.validated_data
    business = business_for(request.user, data["business"])
    if catalog.TEMPLATES[data["template_key"]].mode != business.mode:
        raise DomainError("This scenario doesn't apply to this kind of business.")
    try:
        result = preview(business, data["template_key"], data["parameters"], data["assumptions"])
    except SimulationInputError as error:
        raise DomainError(str(error), error.fields, code="simulation_input_error") from None
    return Response(result)
```

### 4. `config/urls.py` (for now)

The `api_v1` list gets **one new line**, after the `inputs/` line (line 31 below):

<!-- source: self-learning-guide/06-simulation-engine/for-now/config/urls.py:27-39 -->
```python
api_v1 = [
    path("me/", accounts_api.me, name="me"),
    path("scenario-templates/", simulations_api.scenario_templates, name="scenario-templates"),
    path("inputs/", simulations_api.input_catalog, name="inputs"),
    path("simulate/preview/", simulations_api.simulate_preview, name="simulate-preview"),
    path("businesses/<uuid:business_pk>/components/", components_list, name="component-list"),
    path(
        "businesses/<uuid:business_pk>/components/<uuid:pk>/",
        components_detail,
        name="component-detail",
    ),
    path("", include(router.urls)),
]
```

The whole file is in [`for-now/config/urls.py`](for-now/config/urls.py) if you want to
compare.

```bash
python manage.py check
```

## ✅ Check

`System check identified no issues (0 silenced).` No migration is needed: the tables
for runs and results already exist since lesson 5.6. You'll make a real run in lesson
6.9.

## 🔍 Line by line

### `businesses/services/snapshot.py`

- **Lines 1–6** · Docstring: why freeze the inputs.
- **Lines 8–9** · `hashlib` makes fingerprints; `json` turns data into text.
- **Lines 12–14** · `plain`: `2400.0000` → `"2400"`, `22.5000` → `"22.5"`.
  `.normalize()` drops trailing zeros, but writes 2400 as `2.4E+3`; `format(..., "f")`
  writes it the normal way.
- **Line 17** · `build_snapshot(business, template_key, parameters, overrides)`.
- **Lines 18–22** · Docstring: overrides are what-if values (from a slider), marked so
  nobody mistakes them for saved numbers.
- **Line 23** · No overrides? Use an empty dictionary.
- **Lines 24–27** · Every assumption of the business: `{key: {value, unit, source}}`.
- **Lines 28–30** · Overrides replace values, with `source` = `"what_if"`.
  `.get(key, {}).get("unit", "")` safely reads a unit that might not exist.
- **Lines 32–41** · Every component, sorted by key, with its dependencies' keys sorted
  too. Sorting makes the snapshot the same however the database happens to return rows.
- **Lines 42–53** · The snapshot. `dict(sorted(...items()))` rebuilds a dictionary with
  its keys in alphabetical order.
- **Lines 56–59** · The fingerprint. `json.dumps(..., sort_keys=True, separators=...)`
  writes the snapshot as text in one fixed way (sorted keys, no spaces). `.encode` turns
  text into bytes; `sha256(...).hexdigest()` gives the 64-character fingerprint.
- **Lines 62–63** · Just the values, `{key: "2400"}`, which is what the runner wants.

### `simulations/services/run_service.py`

- **Lines 1–9** · Docstring: the two jobs, run and preview, built the same way.
- **Lines 11–12** · `logging` for a line in the server log; `asdict` turns a dataclass
  into a dictionary.
- **Line 14** · `transaction` for "all or nothing" (lesson 5.4).
- **Lines 16–18** · The snapshot helpers, the engine, the models.
- **Line 20** · A logger named after this file.
- **Lines 23–28** · `SimulationInputError`: "the user must fix something". It carries a
  message and, if known, which fields.
- **Lines 31–40** · `_execute`: call the runner with the snapshot's parts. A catalogue
  error (a bad value) becomes a `SimulationInputError` naming the fields.
- **Line 43** · `run_scenario(scenario, user)`.
- **Lines 44–49** · Docstring, including the failed-run rule.
- **Line 50** · Freeze the inputs.
- **Lines 51–58** · Prepare the run (not saved yet): scenario, business, snapshot, its
  hash, engine version, who ran it.
- **Lines 59–65** · Try the engine. If it refuses: mark the run **failed**, save the
  reason, and raise the error for the API to report. `getattr(error, "fields", {})`
  reads `fields` if the error has it, `{}` otherwise.
- **Lines 67–68** · Comment: the success case is saved inside one transaction; the
  failed save above is outside it on purpose.
- **Lines 69–73** · Mark it completed with its summary and warnings, and save it.
- **Lines 74–83** · Save one result row per case in **one** database query
  (`bulk_create`) instead of seven.
- **Line 84** · Log it. `%s` placeholders are filled in by the logger.
- **Line 85** · Return the saved run.
- **Line 88** · `preview(business, template_key, parameters, overrides)`.
- **Line 89** · Docstring: nothing touches the database.
- **Lines 90–96** · Check the parameters and the what-if values with the catalogue
  first, so a slider value of 180 % is refused with the field named.
- **Line 98** · The same snapshot, with the what-ifs.
- **Lines 99–102** · The same engine.
- **Lines 103–111** · Return the answer as plain data, with `"saved": False` so nobody
  mistakes it for a record.

### `simulations/api.py`: what's new

Lines 15–28 and 41–83 are the same as in lesson 5.6.

- **Line 1** · Also imports `serializers` (for the preview's request) and `status`.
- **Line 2** · Also `action`, for the `run` address.
- **Line 6** · `business_for` (lesson 5.5), to find the business safely in the preview.
- **Line 7** · `DomainError` (lesson 4.7): a **422** answer, "your request is fine, but I
  can't do it as asked".
- **Line 12** · The run service.
- **Lines 30–31** · `POST /scenarios/<id>/run/`.
- **Line 32** · Docstring.
- **Line 33** · Find the scenario through `get_queryset`: another organization's
  scenario is a 404.
- **Lines 34–37** · Run it. If the inputs need fixing, answer 422 with the code
  `simulation_input_error`, the message (e.g. "Missing assumptions: daily_orders.") and
  the fields.
- **Line 38** · Answer **201 Created** with the whole run.
- **Line 43** · The docstring's "engine phase" means this part of the course.
- **Lines 86–91** · `PreviewRequest`: a serializer for the preview's **request body**:
  the business id, the template (one of the catalogue's keys), parameters and what-if
  assumptions (both optional dictionaries).
- **Line 94** · The preview accepts only POST.
- **Lines 95–99** · Docstring.
- **Lines 100–102** · Check the body; 400 if it's malformed.
- **Line 103** · The business, only if it's in the user's organization (404 otherwise).
- **Lines 104–105** · The template must fit the business's mode.
- **Lines 106–109** · Run the preview; report input problems as 422.
- **Line 110** · Send the result.

### `config/urls.py`

- **Line 31** · The preview's address.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'simulations.services'` | Add the empty `simulations/services/__init__.py`. |
| `ImportError: cannot import name 'run_scenario'` | Check the function name on line 43 of `run_service.py`. |
| `ImportError` mentioning `intelligence` | You copied the **finished** `simulations/api.py`. Use the for-now version above. |

## ❓ Quiz

1. What goes into a snapshot, and why is it sorted?
2. A run fails because a number is missing. Is anything saved?
3. What's the difference between `/scenarios/<id>/run/` and `/simulate/preview/`?

---

**Next:** [6.9 · Tests, try it, commit](09-tests-try-it-commit.md)

<details><summary>Quiz answers</summary>

1. The business, template, parameters, every assumption and every component. Sorting
   makes identical inputs produce identical text, so the hash is identical too.
2. Yes: a run marked **failed**, with the reason.
3. `run` saves a run and its results (201). `preview` runs the same engine on what-if
   values and saves nothing (200).

</details>
