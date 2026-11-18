# 7.8 · Explain a run

**Time:** 45 minutes · **Before this:** [7.7](07-ai-client-part-2.md).

## Read

Everything is ready; now we use it. Asking for an explanation of a run takes three small
pieces:

| File | Job |
|---|---|
| `context.py` | Build the data we send: an **allowlist**, never "the whole object" |
| `explain.py` | Call `generate` with the run-explanation prompt, schema and an extra rule |
| `simulations/api.py` | `GET`/`POST /api/v1/runs/<id>/analysis/` |

### The allowlist

We **choose** each thing we send, one by one: the business's name, mode and currency;
the assumptions (with their source labels); the scenario's parameters; every metric of
every case; the summary; the engine's warnings. We leave out, on purpose:

- **user details and ids** (they're nobody else's business),
- the free-text **description** (anyone could type anything there, including prompt
  injection, and it isn't needed),
- the **hour-by-hour timelines** (big, and not needed to explain the totals).

Each metric is sent under a key like `"queue_retry.total_impact"`. The AI must cite those
keys. If it cites a key we never sent (`"queue_retry.profit"`), it's pointing at a number
that doesn't exist, so the answer counts as invalid and gets its one repair attempt.

### Errors as HTTP answers

| AI error code | HTTP status | Meaning for the user |
|---|---|---|
| `ai_unavailable` | 503 Service Unavailable | AI is off (no key) or today's budget is used up |
| `ai_rate_limited` | 429 Too Many Requests | Gemini's free tier said "slow down"; try in a minute |
| `ai_invalid_output` | 502 Bad Gateway | Gemini's answer failed validation twice |
| `ai_provider_error` | 502 Bad Gateway | Gemini refused or couldn't be reached |

## Do

### 1. `intelligence/services/context.py`

<!-- source: intelligence/services/context.py:1-51 -->
```python
"""
What we send to Gemini about a run: an ALLOWLIST, never "the whole object".

Included: business name and mode, assumptions with their source labels, scenario
parameters, every case's metrics (keyed "case.metric"), the run summary and warnings.
Left out on purpose: the free-text business description (untrusted and usually not
needed), user details, ids, hour-by-hour timelines (large and not needed to explain).
"""

TOP_SENSITIVITY_ROWS = 5


def run_context(run) -> dict:
    snapshot = run.input_snapshot
    metrics = {}
    for result in run.results.all():
        for key, item in result.metrics.items():
            metrics[f"{result.case_key}.{key}"] = {
                "case": result.label,
                "label": item["label"],
                "value": item["value"],
                "unit": item["unit"],
            }

    summary = dict(run.summary)
    if "sensitivity" in summary:
        summary["sensitivity"] = summary["sensitivity"][:TOP_SENSITIVITY_ROWS]
    if "comparison" in summary:
        summary["comparison"] = {k: v for k, v in summary["comparison"].items() if k != "rows"}

    return {
        "business": {
            "name": snapshot["business"]["name"],
            "mode": snapshot["business"]["mode"],
            "currency": snapshot["business"]["currency"],
        },
        "scenario": {
            "name": run.scenario.name,
            "template": run.scenario.template.name,
            "parameters": snapshot["parameters"],
        },
        "assumptions": snapshot["assumptions"],  # each has value, unit and source label
        "metrics": metrics,
        "run_summary": summary,
        "engine_warnings": run.warnings,
        "engine_version": run.engine_version,
    }


def metric_keys(context: dict) -> set[str]:
    return set(context["metrics"])
```

### 2. `intelligence/services/explain.py`

<!-- source: intelligence/services/explain.py:1-36 -->
```python
"""Ask Gemini to explain one simulation run."""

from intelligence.models import AIAnalysis
from intelligence.schemas import RunExplanation

from . import ai_client
from .context import metric_keys, run_context


def explain_run(run, transport=None) -> AIAnalysis:
    if run.status != run.Status.COMPLETED:
        raise ai_client.AIUnavailable("Only completed runs can be explained.")

    context = run_context(run)
    allowed = metric_keys(context)

    def only_known_metric_keys(answer: RunExplanation, sources) -> None:
        # A cited key we never sent means the model is pointing at a number that doesn't
        # exist. Treat it as an invalid answer, which triggers the one repair attempt.
        unknown = answer.cited_metric_keys() - allowed
        if unknown:
            raise ValueError(
                f"Cited metric keys that are not in the data: {sorted(unknown)}. "
                "Use only keys from simulation_data.metrics."
            )

    return ai_client.generate(
        business=run.business,
        kind=AIAnalysis.Kind.RUN_EXPLANATION,
        task="run_explanation",
        payload=context,
        schema=RunExplanation,
        run=run,
        check=only_known_metric_keys,
        transport=transport,
    )
```

### 3. `intelligence/api.py`

This is the finished file (it also lists scans and alerts, which Part 8 fills):

<!-- source: intelligence/api.py:1-132 -->
```python
"""
Read access to AI analyses, scans and alerts. Creating them (calling Gemini, fetching
sites) arrives in the AI and URL-analyzer phases.
"""

from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.access import OrgScopedMixin
from config.api_errors import DomainError

from .models import AIAnalysis, Alert, CompanyScan

# How each AI failure is reported over HTTP.
AI_ERROR_STATUS = {
    "ai_unavailable": 503,
    "ai_rate_limited": 429,
    "ai_invalid_output": 502,
    "ai_provider_error": 502,
}


def ai_error(error) -> DomainError:
    return DomainError(
        error.message, code=error.code, status_code=AI_ERROR_STATUS.get(error.code, 502)
    )


class AIAnalysisSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = AIAnalysis
        fields = [
            "id",
            "business",
            "run",
            "scan",
            "kind",
            "status",
            "label",
            "model_name",
            "prompt_version",
            "output",
            "flagged_numbers",
            "sources",
            "error",
            "created_at",
            "from_cache",
        ]
        read_only_fields = fields

    from_cache = serializers.BooleanField(read_only=True)

    def get_label(self, obj) -> str:
        # Shipped with every payload so no client can forget to show it.
        return "AI analysis. Not a forecast; check flagged numbers against the simulation."


class CompanyScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyScan
        fields = [
            "id",
            "business",
            "url",
            "status",
            "robots_allowed",
            "pages",
            "log",
            "error",
            "created_at",
            "finished_at",
        ]
        read_only_fields = fields


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            "id",
            "business",
            "scan",
            "severity",
            "kind",
            "summary",
            "detail",
            "acknowledged_at",
            "created_at",
        ]
        read_only_fields = fields


class BusinessFilterMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        return queryset.filter(business_id=business_id) if business_id else queryset


class AIAnalysisViewSet(OrgScopedMixin, BusinessFilterMixin, viewsets.ReadOnlyModelViewSet):
    """Filter with ?business=<id>&kind=site_profile|committee|run_explanation."""

    serializer_class = AIAnalysisSerializer
    queryset = AIAnalysis.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        kind = self.request.query_params.get("kind")
        return queryset.filter(kind=kind) if kind else queryset


class CompanyScanViewSet(OrgScopedMixin, BusinessFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = CompanyScanSerializer
    queryset = CompanyScan.objects.all()


class AlertViewSet(OrgScopedMixin, BusinessFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertSerializer
    queryset = Alert.objects.all()

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        if alert.acknowledged_at is None:
            alert.acknowledged_at = timezone.now()
            alert.acknowledged_by = request.user
            alert.save(update_fields=["acknowledged_at", "acknowledged_by", "updated_at"])
        return Response(AlertSerializer(alert).data)
```

### 4. `simulations/api.py`: the finished version

Replace your file with the **finished** `simulations/api.py` from the reference project
(no more "for now"). Compared with lesson 6.8, it has four new imports and the `analysis`
action:

<!-- source: simulations/api.py:1-16 -->
```python
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from accounts.access import OrgScopedMixin
from businesses.api import business_for
from config.api_errors import DomainError
from intelligence.api import AIAnalysisSerializer, ai_error
from intelligence.models import AIAnalysis
from intelligence.services import ai_client
from intelligence.services.explain import explain_run
from simulation_engine import catalog

from .models import Scenario, SimulationRun
from .serializers import ScenarioSerializer, SimulationRunSerializer
from .services.run_service import SimulationInputError, preview, run_scenario
```

<!-- source: simulations/api.py:45-79 -->
```python
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

    @action(detail=True, methods=["get", "post"])
    def analysis(self, request, pk=None):
        """
        GET:  the latest AI explanation of this run (404 if none yet).
        POST: ask Gemini for one. 201 when newly generated, 200 when served from cache.
        """
        run = self.get_object()
        if request.method == "GET":
            latest = run.analyses.filter(
                kind=AIAnalysis.Kind.RUN_EXPLANATION, status=AIAnalysis.Status.OK
            ).first()
            if latest is None:
                raise DomainError("No AI analysis for this run yet.", code="not_found",
                                  status_code=404)  # fmt: skip
            return Response(AIAnalysisSerializer(latest).data)
        try:
            analysis = explain_run(run)
        except ai_client.AIError as error:
            raise ai_error(error) from None
        code = status.HTTP_200_OK if analysis.from_cache else status.HTTP_201_CREATED
        return Response(AIAnalysisSerializer(analysis).data, status=code)
```

The rest of the file is exactly as in lesson 6.8.

### 5. `config/urls.py` (for now)

Two new lines: the import (line 9) and the router line for analyses (line 20). The whole
file is in [`for-now/config/urls.py`](for-now/config/urls.py).

<!-- source: self-learning-guide/07-ai-with-gemini/for-now/config/urls.py:7-20 -->
```python
from accounts import api as accounts_api
from businesses import api as businesses_api
from intelligence import api as intelligence_api
from simulations import api as simulations_api

from . import views

# One router for the whole JSON API; each app's ViewSets are registered here.
router = DefaultRouter()
router.register("organizations", accounts_api.OrganizationViewSet, basename="organization")
router.register("businesses", businesses_api.BusinessViewSet, basename="business")
router.register("scenarios", simulations_api.ScenarioViewSet, basename="scenario")
router.register("runs", simulations_api.SimulationRunViewSet, basename="run")
router.register("analyses", intelligence_api.AIAnalysisViewSet, basename="analysis")
```

```bash
python manage.py check
```

## Check

`System check identified no issues (0 silenced).` You'll ask Gemini for a real
explanation in lesson 7.9.

## Line by line

### `context.py`

- **Lines 1–8** · Docstring: what's included and what's left out on purpose.
- **Line 10** · Send only the top 5 sensitivity rows (enough to explain; less to read).
- **Line 13** · `run_context(run)`: build the data for one run.
- **Line 14** · The run's frozen snapshot (lesson 6.8). We explain what the run **used**,
  not what the business says today.
- **Lines 15–23** · Every metric of every case, keyed `"case.metric"`, with the case's
  label, the metric's label, value and unit.
- **Line 25** · A **copy** of the summary (`dict(...)`), so changing it doesn't change
  the run.
- **Lines 26–27** · Keep only the top 5 sensitivity rows. `[:5]` means "the first five".
- **Lines 28–29** · Drop the comparison's `rows` (the same numbers are already in
  `metrics`); keep the "lowest impact / fastest" names.
- **Lines 31–47** · The allowlist, built field by field.
- **Lines 50–51** · The metric keys we sent, as a set.

### `explain.py`

- **Line 1** · Docstring.
- **Lines 3–7** · Imports.
- **Line 10** · `explain_run(run, transport=None)`. Tests pass a fake transport.
- **Lines 11–12** · Only completed runs have numbers to explain.
- **Lines 14–15** · The data, and the metric keys in it.
- **Lines 17–25** · The extra rule. It receives the parsed answer (and sources, unused
  here). Any cited key not in `allowed` → `ValueError`, with a message that tells Gemini
  how to fix it. `set - set` = the items in the first set that aren't in the second.
- **Lines 27–36** · Call `generate` with everything: business, kind, prompt name, data,
  schema, the run, the rule and the transport.

### `intelligence/api.py`

- **Lines 1–4** · Docstring. ("Phases" means parts of this course.)
- **Lines 6–14** · Imports.
- **Lines 16–22** · Each AI error code's HTTP status (the table in Read).
- **Lines 25–28** · `ai_error(error)` turns an AI error into our `DomainError`
  (lesson 4.7), so it comes out in the one error shape with the right status.
- **Lines 31–53** · The analysis serializer: everything is output only.
- **Line 55** · `from_cache` as a true/false field. It reads the attribute the client
  set (lesson 7.3).
- **Lines 57–59** · `label`: a sentence sent with **every** analysis: *"AI analysis. Not a
  forecast; check flagged numbers against the simulation."* Because it's in the data,
  no screen can forget to show it.
- **Lines 62–94** · Read-only serializers for scans and alerts (Part 8).
- **Lines 97–101** · A mixin for `?business=<id>` filtering, shared by three ViewSets.
- **Lines 104–113** · Analyses: scoped to my organization, filterable by business and by
  kind. Read only: analyses are created by `generate`, never typed in.
- **Lines 116–118** · Scans, read only.
- **Lines 121–132** · Alerts, read only, plus `POST /alerts/<id>/acknowledge/` to mark
  one as seen. Acknowledging twice changes nothing (the `if`).

### `simulations/api.py`: what's new

- **Lines 8–11** · The error helper and serializer, the model, the client (for its error
  classes) and `explain_run`.
- **Line 59** · `GET` and `POST /runs/<id>/analysis/`.
- **Lines 61–64** · Docstring: GET reads the latest; POST asks Gemini.
- **Line 65** · The run, through the organization filter (another org's run → 404).
- **Lines 66–73** · GET: the newest successful explanation, or a 404 "No AI analysis for
  this run yet."
- **Lines 74–77** · POST: ask. Any AI error becomes the right HTTP answer.
- **Lines 78–79** · **201 Created** for a new answer, **200 OK** for one from the cache.
  The client can tell the difference, and so can you.

### `config/urls.py`

- **Line 9** · Import the intelligence API.
- **Line 20** · `/api/v1/analyses/` lists your organization's AI answers.

## If it didn't work

| You see | Fix |
|---|---|
| `ImportError: cannot import name 'explain_run'` | Check `intelligence/services/explain.py` exists and is spelled right. |
| `ImportError` mentioning `committee` | You copied the finished `businesses/api.py`. Keep the Part 5 version until Part 8. |

## Quiz

1. Name two things deliberately **not** sent to Gemini, and why.
2. Gemini cites `"queue_retry.profit"`. What happens?
3. How does a client know an answer came from the cache?

---

**Next:** [7.9 · Tests, try it, commit](09-tests-try-it-commit.md)

<details><summary>Quiz answers</summary>

1. Any two of: user details and ids (private), the free-text description (untrusted,
   unneeded), hour-by-hour timelines (big, unneeded).
2. The extra rule rejects it; Gemini gets one repair attempt with the reason. If it
   does it again, the analysis is saved as failed and the user gets a 502.
3. Status **200** instead of 201, and `from_cache: true` in the data.

</details>
