# 9.7 · The API, and try it

**Time:** 60 minutes · **Before this:** [9.6](06-the-printable-page.md).

## Read

The decisions API is a normal `ModelViewSet` (lesson 5.5) with a few careful rules in
its serializer:

| Rule | Why |
|---|---|
| `business`, `run` and `owner` can only be **yours** | You can't attach a decision to someone else's run, or give it to someone outside your organization |
| A new decision must start as `proposed` | Nobody can create one that's "already approved" |
| A status change must follow the workflow | The same check as the page (lesson 9.3) |
| The run must belong to the same business | No mixing up two businesses |
| `chosen_strategy` must be one of the run's cases | You can't "choose" `pray` |
| A `note` can be sent with a status change | It goes into the history, not into a column |

Plus one extra address: `GET /api/v1/decisions/<id>/report/` returns the brief as JSON.

## Do

### 1. `decisions/api.py`

#### Piece 1: the serializer (lines 1–97)

<!-- source: decisions/api.py:1-97 -->
```python
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.access import OrgScopedMixin
from accounts.models import User
from businesses.models import BusinessProfile
from simulations.models import SimulationRun

from .models import Decision
from .services import workflow
from .services.brief import build_brief


class DecisionSerializer(serializers.ModelSerializer):
    # All three related fields are narrowed to the user's organization in __init__.
    business = serializers.PrimaryKeyRelatedField(queryset=BusinessProfile.objects.none())
    run = serializers.PrimaryKeyRelatedField(
        queryset=SimulationRun.objects.none(), required=False, allow_null=True
    )
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.none(), required=False, allow_null=True
    )
    owner_name = serializers.SerializerMethodField()
    decided_by_name = serializers.SerializerMethodField()
    allowed_next_status = serializers.SerializerMethodField()
    # Optional reason recorded in the history when the status changes.
    note = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=280)

    class Meta:
        model = Decision
        fields = [
            "id",
            "business",
            "run",
            "title",
            "owner",
            "owner_name",
            "status",
            "allowed_next_status",
            "chosen_strategy",
            "rationale",
            "note",
            "decided_by_name",
            "decided_at",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "decided_at", "history", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None:
            user = request.user
            self.fields["business"].queryset = BusinessProfile.objects.for_user(user)
            self.fields["run"].queryset = SimulationRun.objects.for_user(user)
            # Owners must be people in the same organization(s) as the requester.
            self.fields["owner"].queryset = User.objects.filter(
                memberships__organization__memberships__user=user
            ).distinct()

    def get_owner_name(self, decision) -> str | None:
        return str(decision.owner) if decision.owner else None

    def get_decided_by_name(self, decision) -> str | None:
        return str(decision.decided_by) if decision.decided_by else None

    def get_allowed_next_status(self, decision) -> list[str]:
        return workflow.allowed_next(decision.status)

    def validate_status(self, value):
        if self.instance is None:
            if value != Decision.Status.PROPOSED:
                raise serializers.ValidationError("New decisions start as 'proposed'.")
            return value
        try:
            workflow.check_transition(self.instance.status, value)
        except workflow.InvalidTransition as error:
            raise serializers.ValidationError(str(error)) from None
        return value

    def validate(self, attrs):
        business = attrs.get("business") or self.instance.business
        if self.instance and business != self.instance.business:
            raise serializers.ValidationError({"business": "can't change after creation"})
        run = attrs.get("run", self.instance.run if self.instance else None)
        if run is not None and run.business_id != business.id:
            raise serializers.ValidationError({"run": "belongs to a different business"})
        if run is not None and attrs.get("chosen_strategy"):
            case_keys = set(run.results.values_list("case_key", flat=True))
            if case_keys and attrs["chosen_strategy"] not in case_keys:
                raise serializers.ValidationError(
                    {"chosen_strategy": f"must be one of this run's cases: {sorted(case_keys)}"}
                )
        return attrs
```

#### Piece 2: the ViewSet (lines 100–124)

<!-- source: decisions/api.py:100-124 -->
```python
class DecisionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = DecisionSerializer
    queryset = Decision.objects.select_related("owner", "business")
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        return queryset.filter(business_id=business_id) if business_id else queryset

    def perform_create(self, serializer):
        serializer.validated_data.pop("note", None)
        decision = serializer.save(created_by=self.request.user)
        workflow.record_creation(decision, self.request.user)

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        note = serializer.validated_data.pop("note", "")
        decision = serializer.save()
        workflow.record_status_change(decision, old_status, self.request.user, note)

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        """The decision brief as structured JSON (the printable page renders the same data)."""
        return Response(build_brief(self.get_object()))
```

### 2. `config/urls.py` (for now)

Three more lines: import the decisions API (line 9), register it (line 25), and include
the page addresses (line 53). The whole file is in
[`for-now/config/urls.py`](for-now/config/urls.py):

<!-- source: self-learning-guide/09-decisions/for-now/config/urls.py:7-25 -->
```python
from accounts import api as accounts_api
from businesses import api as businesses_api
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
```

<!-- source: self-learning-guide/09-decisions/for-now/config/urls.py:49-57 -->
```python
urlpatterns = [
    # A temporary home page. Part 10 replaces it with the real operations board.
    path("", login_required(TemplateView.as_view(template_name="home.html")), name="home"),
    path("accounts/", include("accounts.urls")),
    path("decisions/", include("decisions.urls")),
    path("api/v1/", include((api_v1, "api"), namespace="api")),
    path("admin/", admin.site.urls),
    path("healthz/", views.healthz, name="healthz"),
]
```

## Check: try it

```bash
python manage.py check
```

Start the server, log in, open the console and paste the `api()` helper (lesson 5.7).

### 1. Find the run Gemini explained in lesson 7.9

```js
const [explained] = await api("GET", "/api/v1/analyses/?kind=run_explanation")
```

The newest explanation comes first. `explained.run` is that run's id, and
`explained.business` is Kirana Express. (`const [explained] = ...` takes the **first**
item of the list.)

### 2. Record a decision

```js
const me = await api("GET", "/api/v1/me/")
```

```js
const d = await api("POST", "/api/v1/decisions/", {business: explained.business, run: explained.run, title: "Queue and retry payments during outages", chosen_strategy: "queue_retry", owner: me.id, rationale: "Lowest total impact in the model, and cheap to set up. We accept slower recovery."})
```

→ `201`. Look at `d.status` (`"proposed"`), `d.allowed_next_status`
(`["approved", "rejected"]`) and `d.history` (one entry, "Created").

### 3. Try to break the rules

```js
await api("POST", "/api/v1/decisions/", {business: explained.business, run: explained.run, title: "x", chosen_strategy: "pray"})
```

→ `400`: `chosen_strategy: must be one of this run's cases: ['backup', 'queue_retry', 'wait']`.

```js
await api("PATCH", `/api/v1/decisions/${d.id}/`, {status: "done"})
```

→ `400`: `status: A proposed decision can move to: approved, rejected.`

### 4. Sign it off

```js
const ok = await api("PATCH", `/api/v1/decisions/${d.id}/`, {status: "approved", note: "Agreed with the ops lead"})
```

→ `200`. `ok.decided_by_name` is your name, `ok.decided_at` is now, and the last history
entry says `proposed` → `approved` with your note.

### 5. The brief, as JSON

```js
const report = await api("GET", `/api/v1/decisions/${d.id}/report/`)
```

Open it in the console. `report.assumptions.frozen` is `true`. In
`report.outcomes.rows`, find "Total financial impact": `21000.00`, `20420.00` and
`10050.00` for wait, backup and queue (the same numbers as lesson 6.1).

### 6. The brief, as a page

```js
location.href = `/decisions/${d.id}/brief/`
```

Read it from top to bottom. The chosen column is highlighted. Section 05 carries the
"AI analysis" label. Then:

1. Click **Mark in progress**. The status changes, "Marked in progress." appears in the
   toolbar, and the history gets a third line.
2. Click **Print or save as PDF**. In the print preview the toolbar has gone: only the
   sheet is printed. (Choose "Save as PDF" as the printer to keep a copy.)

> **A real catch.** When we tested this lesson, Gemini wrote "the lowest total financial
> impact of about **₹10,50**": a typo for ₹10,050. The brief showed, in section 05:
> *"1 number(s) in this text are not from the simulation: 10,50. Treat them as
> unverified."* That's Part 7's guardrail doing its job on a real slip, all the way into
> the printed page. Your AI text will be different; look for the box anyway.

## Line by line

### Piece 1: the serializer

- **Lines 1–3** · DRF's serializers, ViewSets, extra actions and responses.
- **Lines 5–8** · The org filter, and the three tables a decision can point to.
- **Lines 10–12** · Our table, the workflow and the brief.
- **Line 15** · `DecisionSerializer`.
- **Line 16** · The comment explains the next lines.
- **Lines 17–23** · The three links, each starting with an **empty** list of allowed
  choices (`.none()`). They're filled in for the person asking in `__init__` (below), so
  by default nothing is allowed.
- **Lines 24–26** · Three read-only extras worked out by methods below: the owner's
  name, the signer's name, and the allowed next statuses.
- **Lines 27–28** · `note`: accepted on input (`write_only`), never stored in a column.
- **Lines 30–50** · Which fields, and which are read-only (the id, the sign-off time, the
  history and the dates can't be sent by a client).
- **Lines 52–53** · `__init__`: set up as usual, then...
- **Lines 54–62** · ...if we know who's asking, allow only **their** businesses and runs,
  and owners who share an organization with them. That last query reads: users who have
  a membership in an organization that has a membership for this user. `.distinct()`
  removes repeats.
- **Lines 64–71** · The three extra fields' methods.
- **Lines 73–77** · `validate_status`, for a **new** decision: it must be "proposed".
- **Lines 78–82** · For an existing one: the workflow decides. Its error becomes a normal
  validation error (a 400 naming `status`).
- **Line 84** · `validate(attrs)`: checks that need several fields at once.
- **Lines 85–87** · The business, from the request or the existing decision. It can't be
  changed later.
- **Lines 88–90** · The run (new, or the one already linked) must belong to that
  business.
- **Lines 91–96** · A chosen strategy must be one of the run's case keys.
  `values_list("case_key", flat=True)` asks the database for just that column.
- **Line 97** · All good.

### Piece 2: the ViewSet

- **Lines 100–103** · A ViewSet limited to your organization (lesson 4.6), loading owner
  and business in the same query. `http_method_names` leaves out `PUT`: changes go
  through `PATCH`.
- **Lines 105–108** · Optional `?business=<id>` filter.
- **Lines 110–113** · Creating: drop the `note` (there's no column for it), save with
  `created_by`, start the history.
- **Lines 115–119** · Updating: remember the old status, take out the note, save, then
  record the change (which does nothing if the status didn't change).
- **Lines 121–124** · The `report` action: the brief, as JSON.

### `config/urls.py`

- **Line 9** · Import the decisions API.
- **Line 25** · `/api/v1/decisions/`.
- **Line 53** · `/decisions/...`: the brief and status pages from lesson 9.6.

## If it didn't work

| You see | Fix |
|---|---|
| `explained` is `undefined` | No AI explanation yet. Do lesson 7.9's "Try the real Gemini" first, or use any run: `(await api("GET", "/api/v1/runs/"))[0]`. |
| `400` `owner: Invalid pk` | `me.id` must be **your** user id; owners must share your organization. |
| `404` on the brief page | The id is wrong, or the decision belongs to another organization. |

## Quiz

1. Why do the serializer's three links start with `.none()`?
2. You `PATCH` only the rationale. Does the history change?
3. Where does the `note` you send end up?

---

**Next:** [9.8 · Tests and commit](08-tests-and-commit.md)

<details><summary>Quiz answers</summary>

1. Safe by default: if `__init__` didn't know the user, nothing could be linked at all.
2. No. Only status changes add history.
3. In the history entry for that status change.

</details>
