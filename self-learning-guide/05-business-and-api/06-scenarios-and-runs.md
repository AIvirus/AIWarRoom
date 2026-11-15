# 5.6 · Scenarios and runs

**Time:** 45 minutes · **Before this:** [5.5](05-business-api.md).

## 📖 Read

A **scenario** is a question: *"What if the warehouse shuts for 6 hours, starting at
6 pm?"* It's made of a **template** from the catalogue (`warehouse_shutdown`) plus its
**parameters** (`outage_hours = 6`, `start_hour = 18`...).

A **run** is one answer to that question, worked out by the maths in Part 6. The run keeps
a **frozen copy** of every number it used (the "input snapshot"). Why? If you change the
daily orders tomorrow, yesterday's run must still show what it was based on. A record that
changes after the fact isn't a record.

A run has one **result** per case. For a warehouse shutdown: "wait", "backup",
"queue_retry". For an idea: "expected", "best", "worst" and more.

### `JSONField`

Some data has a shape that varies: a warehouse scenario has different parameters from an
idea scenario. A `JSONField` stores a whole dictionary or list in one column (PostgreSQL
has a fast JSON type for this). We still check the contents, with the catalogue, before
saving.

### Why store parameters as text?

`{"outage_hours": "4"}`, not `{"outage_hours": 4}`. JSON numbers are floats in most
languages, and floats round (`0.1 + 0.2` is `0.30000000000000004`). Text keeps the exact
Decimal value. The catalogue's `validate_parameters` already returns text (lesson 5.2).

## ⌨️ Do

### 1. `simulations/models.py`

Replace the file's contents with:

<!-- source: simulations/models.py:1-110 -->
```python
"""
Scenarios and the record of every simulation run.

Scenario          - "what are we testing?": a template (e.g. warehouse_shutdown) + parameters.
SimulationRun     - one execution. It stores a frozen copy of every input it used, so
                    editing the business tomorrow can never change yesterday's result.
SimulationResult  - one row per case or strategy in a run ("worst", "backup", ...), with
                    its metrics and its hour-by-hour or month-by-month timeline.
"""

from django.conf import settings
from django.db import models

from common.models import BaseModel
from common.querysets import OrgScopedQuerySet
from simulation_engine import catalog


class Scenario(BaseModel):
    class Kind(models.TextChoices):
        IDEA_CASE = "idea_case", "Idea stress test"
        DISRUPTION = "disruption", "Disruption"

    business = models.ForeignKey(
        "businesses.BusinessProfile", on_delete=models.CASCADE, related_name="scenarios"
    )
    template_key = models.CharField(
        max_length=40, choices=[(key, t.name) for key, t in catalog.TEMPLATES.items()]
    )
    kind = models.CharField(max_length=12, choices=Kind.choices, editable=False)
    name = models.CharField(max_length=120)
    # Validated by simulation_engine.catalog.validate_parameters; values stored as strings
    # so decimals stay exact in JSON.
    parameters = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    ORG_PATH = "business__organization"
    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # The kind follows from the template; it is never chosen independently.
        self.kind = catalog.TEMPLATES[self.template_key].kind
        super().save(*args, **kwargs)

    @property
    def template(self):
        return catalog.TEMPLATES[self.template_key]

    def __str__(self):
        return self.name


class SimulationRun(BaseModel):
    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name="runs")
    # Denormalised from scenario.business so runs can be scoped and listed per business
    # with one join instead of two.
    business = models.ForeignKey(
        "businesses.BusinessProfile", on_delete=models.CASCADE, related_name="runs"
    )
    status = models.CharField(max_length=10, choices=Status.choices)
    input_snapshot = models.JSONField()
    # SHA-256 of the snapshot: identical inputs give an identical hash, which lets the AI
    # layer reuse an earlier explanation instead of spending free-tier quota.
    input_hash = models.CharField(max_length=64, db_index=True)
    engine_version = models.CharField(max_length=20)
    # Run-level outputs: sensitivity table, funnel check, strategy comparison.
    summary = models.JSONField(default=dict)
    warnings = models.JSONField(default=list)
    error = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    ORG_PATH = "business__organization"
    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.scenario} @ {self.created_at:%Y-%m-%d %H:%M}"


class SimulationResult(BaseModel):
    run = models.ForeignKey(SimulationRun, on_delete=models.CASCADE, related_name="results")
    case_key = models.CharField(max_length=40)  # "expected", "worst", "wait", "backup"...
    label = models.CharField(max_length=80)
    metrics = models.JSONField()
    timeline = models.JSONField(default=list)

    ORG_PATH = "run__business__organization"
    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        ordering = ["run", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["run", "case_key"], name="unique_case_per_run")
        ]

    def __str__(self):
        return f"{self.run_id}:{self.case_key}"
```

### 2. `simulations/serializers.py`

<!-- source: simulations/serializers.py:1-92 -->
```python
from rest_framework import serializers

from businesses.models import BusinessProfile
from simulation_engine import catalog

from .models import Scenario, SimulationResult, SimulationRun


class ScenarioSerializer(serializers.ModelSerializer):
    # The queryset is narrowed to the user's organization in __init__, so a client can't
    # attach a scenario to someone else's business by guessing its id.
    business = serializers.PrimaryKeyRelatedField(queryset=BusinessProfile.objects.none())
    missing_inputs = serializers.SerializerMethodField()

    class Meta:
        model = Scenario
        fields = [
            "id",
            "business",
            "template_key",
            "kind",
            "name",
            "parameters",
            "missing_inputs",
            "created_at",
        ]
        read_only_fields = ["id", "kind", "created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None:
            self.fields["business"].queryset = BusinessProfile.objects.for_user(
                request.user
            ).active()

    def get_missing_inputs(self, scenario) -> list[str]:
        """Assumptions the business still needs before this scenario can run."""
        available = set(scenario.business.assumptions.values_list("key", flat=True))
        return catalog.missing_inputs(scenario.template_key, available)

    def validate(self, attrs):
        business = attrs.get("business") or self.instance.business
        template_key = attrs.get("template_key") or self.instance.template_key
        if self.instance and template_key != self.instance.template_key:
            raise serializers.ValidationError({"template_key": "can't change after creation"})
        if self.instance and business != self.instance.business:
            raise serializers.ValidationError({"business": "can't change after creation"})

        template = catalog.TEMPLATES[template_key]
        if template.mode != business.mode:
            raise serializers.ValidationError(
                {"template_key": f"'{template.name}' needs a business in '{template.mode}' mode"}
            )
        parameters = attrs.get("parameters", self.instance.parameters if self.instance else {})
        try:
            attrs["parameters"] = catalog.validate_parameters(template_key, parameters)
        except catalog.CatalogError as error:
            raise serializers.ValidationError({"parameters": error.errors}) from None
        return attrs


class SimulationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulationResult
        fields = ["case_key", "label", "metrics", "timeline"]


class SimulationRunSerializer(serializers.ModelSerializer):
    scenario_name = serializers.CharField(source="scenario.name", read_only=True)
    template_key = serializers.CharField(source="scenario.template_key", read_only=True)
    results = SimulationResultSerializer(many=True, read_only=True)

    class Meta:
        model = SimulationRun
        fields = [
            "id",
            "scenario",
            "scenario_name",
            "template_key",
            "business",
            "status",
            "engine_version",
            "input_hash",
            "input_snapshot",
            "summary",
            "warnings",
            "error",
            "results",
            "created_at",
        ]
        read_only_fields = fields
```

### 3. `simulations/admin.py`

Replace the file's contents with:

<!-- source: simulations/admin.py:1-23 -->
```python
from django.contrib import admin

from .models import Scenario, SimulationResult, SimulationRun


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ["name", "template_key", "business", "created_at"]
    list_filter = ["template_key"]


class ResultInline(admin.TabularInline):
    model = SimulationResult
    extra = 0
    readonly_fields = ["case_key", "label", "metrics"]
    exclude = ["timeline"]


@admin.register(SimulationRun)
class SimulationRunAdmin(admin.ModelAdmin):
    list_display = ["scenario", "status", "engine_version", "created_at"]
    readonly_fields = ["input_snapshot", "input_hash", "engine_version"]
    inlines = [ResultInline]
```

### 4. `simulations/api.py` (for now)

The finished file can also **run** a scenario (Part 6) and ask the AI about a run
(Part 7). For now, use the version in [`for-now/simulations/api.py`](for-now/simulations/api.py):

<!-- source: self-learning-guide/05-business-and-api/for-now/simulations/api.py:1-70 -->
```python
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from accounts.access import OrgScopedMixin
from simulation_engine import catalog

from .models import Scenario, SimulationRun
from .serializers import ScenarioSerializer, SimulationRunSerializer


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
```

### 5. Migrate

```bash
python manage.py makemigrations simulations
```

```bash
python manage.py migrate
```

## ✅ Check

```text
Migrations for 'simulations':
  simulations/migrations/0001_initial.py
    + Create model Scenario
    + Create model SimulationRun
    + Create model SimulationResult
```

then `Applying simulations.0001_initial... OK`. In the admin you now see a
**Simulations** section with Scenarios and Simulation runs.

## 🔍 Line by line

### `simulations/models.py`

- **Lines 1–9** · Docstring describing the three models. Read it: it's the whole idea of
  this lesson in five lines.
- **Lines 11–16** · Imports, the same set as in `businesses/models.py`.
- **Line 19** · The scenario table.
- **Lines 20–22** · Two kinds: an idea stress test, or a disruption.
- **Lines 24–26** · Which business it's about. `"businesses.BusinessProfile"` is written
  as **text** (`"app.Model"`) because the model lives in another app; Django finds it.
- **Lines 27–29** · The template key. The allowed choices are built **from the
  catalogue** with a list comprehension: `[(key, name), ...]`. Add a template to the
  catalogue and it becomes a valid choice here too.
- **Line 30** · The kind. `editable=False`: it's never typed (see line 47).
- **Line 31** · A name like "Bhiwandi flood".
- **Lines 32–34** · The parameters, as JSON. `default=dict` (no brackets!) means "a new
  empty dictionary for every row". Writing `default={}` would share **one** dictionary
  between all rows, a classic Python trap.
- **Lines 35–37** · Who made it, like in `BusinessProfile`.
- **Lines 39–40** · Organization path (two steps) and the scoped queryset.
- **Lines 42–43** · Newest first: the `-` in `"-created_at"` means "descending".
- **Lines 45–48** · Before saving, set `kind` from the template, so it can never
  disagree with it.
- **Lines 50–52** · `scenario.template` gives the catalogue `Template` object.
- **Lines 54–55** · Prints its name.
- **Line 58** · One run.
- **Lines 59–61** · It either completed or failed.
- **Line 63** · Which scenario. `related_name="runs"`: `scenario.runs.all()`.
- **Lines 64–68** · Also which business. We could reach it through the scenario, but
  storing it here makes "all runs of this business" a simpler, faster query. Copying a
  value for speed like this is called **denormalising**.
- **Line 69** · Completed or failed.
- **Line 70** · The frozen copy of every input. No default: a run without its inputs is
  meaningless.
- **Lines 71–73** · A **hash** of the snapshot: a 64-character fingerprint. The same
  inputs always give the same fingerprint. Part 7 uses it to reuse an AI explanation
  instead of asking Gemini again. `db_index=True` makes searching by it fast.
- **Line 74** · Which version of the maths produced it (Part 6).
- **Lines 75–76** · Results that belong to the whole run, like the comparison of
  strategies.
- **Line 77** · Warnings, like "your expected orders are higher than the funnel
  supports". `default=list`, for the same reason as `default=dict`.
- **Line 78** · If it failed, why.
- **Lines 79–81** · Who ran it.
- **Lines 83–87** · Organization path, queryset, newest first.
- **Lines 89–90** · Prints like `Bhiwandi flood @ 2026-03-14 18:05`. The `:%Y-%m-%d %H:%M`
  inside the f-string formats the date.
- **Line 93** · One result line of a run.
- **Line 94** · Its run. `run.results.all()` lists them.
- **Line 95** · Which case: `"expected"`, `"backup"`...
- **Line 96** · Its label for people.
- **Line 97** · The numbers (cash at the end, orders lost...), as JSON.
- **Line 98** · Hour by hour (disruptions) or month by month (ideas), for the charts.
- **Line 100** · The path is **three** steps: result → run → business → organization.
- **Lines 103–107** · Sorted by run, then oldest first; and each case only once per run.
- **Lines 109–110** · Prints like `<run id>:backup`. `self.run_id` reads the stored id
  without loading the whole run.

### `simulations/serializers.py`

- **Lines 1–6** · Imports: DRF, the business model, the catalogue, our models.
- **Line 9** · The scenario serializer.
- **Lines 10–12** · `business` is chosen by id, but from **no** businesses at first. We
  open it up in `__init__` (the same safe pattern as `depends_on` in lesson 5.4). So you
  can't attach a scenario to someone else's business by guessing its id.
- **Line 13** · An extra output field whose value comes from a method,
  `get_missing_inputs` (line 37). DRF finds the method by its name: `get_` + field name.
- **Lines 15–27** · Model, fields, and the output-only fields. `kind` is output only
  because `save()` sets it.
- **Line 29** · When the serializer is created...
- **Line 30** · ...do the normal set-up...
- **Line 31** · ...get the request (DRF's ViewSets put it into the context for you)...
- **Lines 32–35** · ...and allow only **my active** businesses.
- **Lines 37–40** · Which numbers does this scenario still need? Get the keys the business
  already has, as a set, and ask the catalogue for the rest. `values_list("key",
  flat=True)` returns just the keys, not whole rows.
- **Line 42** · Checks on all fields together.
- **Lines 43–44** · The business and template. On a PATCH that changes only the name,
  they aren't in `attrs`, so take them from the existing scenario (`self.instance`).
- **Lines 45–48** · Changing the template or business of an existing scenario is
  refused: it would be a different question.
- **Line 50** · The template from the catalogue.
- **Lines 51–54** · A warehouse shutdown needs an **operating** business; the idea stress
  test needs an **idea**.
- **Line 55** · The parameters sent, or the existing ones, or none.
- **Lines 56–59** · Let the catalogue check them and fill in defaults. Errors come back
  under `"parameters"`, one message per bad parameter.
- **Line 60** · Return the clean values.
- **Lines 63–66** · A small serializer for results.
- **Line 69** · The run serializer, for reading only.
- **Lines 70–71** · Two fields taken from the run's scenario (`source="scenario.name"`
  means "follow the scenario link, read its name").
- **Line 72** · The results, nested inside each run, as a list.
- **Lines 74–91** · All the fields.
- **Line 92** · `read_only_fields = fields`: **everything** is output only. A run is a
  record; nobody edits it through the API.

### `simulations/admin.py`

- **Lines 6–9** · Scenarios: columns and a filter by template.
- **Lines 12–16** · Results inside a run's page, read only, **without** the timeline
  (hundreds of numbers would make the page unreadable).
- **Lines 19–23** · Runs: columns, read-only inputs (a record must not be edited, even in
  the admin), and the results inline.

### `simulations/api.py` (for now)

- **Lines 1–9** · Imports. `api_view` turns a plain function into an API view.
- **Line 12** · Scenarios, scoped to my organization by the mixin.
- **Line 13** · Docstring: `?business=<id>` shows only one business's scenarios.
- **Lines 15–17** · Serializer, rows (with `select_related("business")` to fetch each
  scenario's business in the same query), and allowed methods.
- **Lines 19–22** · If the address has `?business=<id>`, filter by it. The line
  `x if condition else y` picks one of two values.
- **Lines 24–25** · Record who created the scenario.
- **Line 28** · Runs: a **ReadOnlyModelViewSet** gives only list and retrieve. There is
  no way to create, change or delete a run through it.
- **Lines 29–32** · Docstring: runs are made by "run this scenario" (Part 6) and never
  edited.
- **Lines 34–35** · Serializer and rows. `prefetch_related("results")` loads all the
  results in one extra query.
- **Lines 37–40** · The same `?business=` filter.
- **Lines 43–44** · A function view that answers GET only.
- **Line 45** · Docstring.
- **Lines 46–59** · Build a list with one dictionary per template: its key, name, kind,
  mode, description, the numbers it needs, and each parameter described by
  `catalog.describe` (lesson 5.2). Part 10's forms are built from this.
- **Lines 62–70** · Every assumption, grouped by mode:
  `{"idea": [...], "operating": [...]}`. A dict comprehension (outside) with a list
  comprehension (inside).

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `KeyError: 'warehouse_shutdown'` on save | The catalogue's `TEMPLATES` is missing it; compare with lesson 5.2. |
| `fields.E010` warning about `default={}` | Use `default=dict` (the function), not `{}`. |
| `makemigrations` says `No changes detected` | Is `"simulations"` in `INSTALLED_APPS` (lesson 4.3)? Did you save `models.py`? |

## ❓ Quiz

1. Why does a run keep a copy of its inputs?
2. What's the difference between `default=dict` and `default={}`?
3. Can you change a run's numbers through the API?
4. A client creates a warehouse shutdown for an **idea** business. What happens?

---

**Next:** [5.7 · Wire it up and try it](07-urls-and-try-it.md)

<details><summary>Quiz answers</summary>

1. So editing the business later never changes what an old run says it was based on.
2. `dict` makes a fresh empty dictionary for each row; `{}` would be one dictionary shared
   by every row.
3. No. `SimulationRunViewSet` is read only, and every serializer field is read only.
4. 400: "'Warehouse shutdown' needs a business in 'operating' mode".

</details>
