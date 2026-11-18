# 7.3 · The AI tables

**Time:** 30 minutes · **Before this:** [7.2](02-key-and-first-call.md).

## Read

The `intelligence` app (made empty in lesson 4.2) holds everything that comes from
**outside** the exact engine: the AI's answers, and (in Part 8) what we read from
company websites. It gets three tables now, so you only need one migration:

| Table | One row is... | Used in |
|---|---|---|
| `AIAnalysis` | one AI answer, with its model, prompt version, flagged numbers and sources | Part 7 and 8 |
| `CompanyScan` | one read of a company's public website | Part 8 |
| `Alert` | one change found between two scans ("price went up") | Part 8 |

An `AIAnalysis` is saved even when it **fails**, with the reason. Like failed runs in
Part 6, the history shows every attempt.

## Do

### 1. `intelligence/models.py`

<!-- source: intelligence/models.py:1-140 -->
```python
"""
Everything that comes from outside the deterministic engine: Gemini's analysis and what we
read from a company's public website.

AIAnalysis   - one Gemini output (run explanation, expert committee or site profile),
               always labelled as AI analysis, with any unverified numbers flagged.
CompanyScan  - one read of a company's public site: which pages, prices and products.
Alert        - a change found by comparing a scan with the previous one.
"""

from django.conf import settings
from django.db import models

from common.models import BaseModel
from common.querysets import OrgScopedQuerySet


class AIAnalysis(BaseModel):
    class Kind(models.TextChoices):
        RUN_EXPLANATION = "run_explanation", "Run explanation"
        COMMITTEE = "committee", "Expert committee"
        SITE_PROFILE = "site_profile", "Company site profile"

    class Status(models.TextChoices):
        OK = "ok", "OK"
        FAILED = "failed", "Failed"

    business = models.ForeignKey(
        "businesses.BusinessProfile", on_delete=models.CASCADE, related_name="analyses"
    )
    run = models.ForeignKey(
        "simulations.SimulationRun",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="analyses",
    )
    scan = models.ForeignKey(
        "intelligence.CompanyScan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="analyses",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=10, choices=Status.choices)
    model_name = models.CharField(max_length=60)
    prompt_version = models.CharField(max_length=20)
    # Hash of (task, prompt version, model, input). Same hash = reuse, no new API call.
    input_hash = models.CharField(max_length=64, db_index=True)
    output = models.JSONField(default=dict)
    # Numbers the AI wrote that don't appear in the data we gave it (see guardrails.py).
    flagged_numbers = models.JSONField(default=list)
    # Links the AI cited: fetched pages or Google Search grounding results.
    sources = models.JSONField(default=list)
    error = models.TextField(blank=True)
    # Live API calls this analysis cost (retries and the repair attempt included).
    # Summed per day to enforce AI_DAILY_CALL_BUDGET.
    attempts = models.PositiveSmallIntegerField(default=0)

    ORG_PATH = "business__organization"
    objects = OrgScopedQuerySet.as_manager()

    # Set (not stored) when an answer is served from cache instead of a new call.
    from_cache = False

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "AI analyses"

    def __str__(self):
        return f"{self.get_kind_display()} ({self.status})"


class CompanyScan(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Waiting to start"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        BLOCKED = "blocked", "Blocked by robots.txt or safety rules"
        FAILED = "failed", "Failed"

    business = models.ForeignKey(
        "businesses.BusinessProfile", on_delete=models.CASCADE, related_name="scans"
    )
    url = models.URLField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    # Human-readable log of what the scan did, also streamed live to the browser.
    log = models.JSONField(default=list)
    robots_allowed = models.BooleanField(null=True)
    # [{url, title, text_hash, prices: [...], products: [...]}] - what we diff next time.
    pages = models.JSONField(default=list)
    error = models.TextField(blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    ORG_PATH = "business__organization"
    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.url} ({self.status})"


class Alert(BaseModel):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARN = "warn", "Warning"
        CRITICAL = "critical", "Critical"

    class Kind(models.TextChoices):
        PRICING_CHANGE = "pricing_change", "Pricing changed"
        NEW_PRODUCT = "new_product", "New product"
        NEW_PAGE = "new_page", "New page"
        PAGE_REMOVED = "page_removed", "Page removed"
        NEW_COMPETITOR = "new_competitor", "New competitor mentioned"

    business = models.ForeignKey(
        "businesses.BusinessProfile", on_delete=models.CASCADE, related_name="alerts"
    )
    scan = models.ForeignKey(CompanyScan, on_delete=models.CASCADE, related_name="alerts")
    severity = models.CharField(max_length=10, choices=Severity.choices)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    summary = models.CharField(max_length=240)
    detail = models.JSONField(default=dict)  # {"before": ..., "after": ..., "url": ...}
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    ORG_PATH = "business__organization"
    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        # Unacknowledged first. Said explicitly: PostgreSQL sorts empty values LAST by default.
        ordering = [models.F("acknowledged_at").asc(nulls_first=True), "-created_at"]

    def __str__(self):
        return self.summary
```

### 2. `intelligence/admin.py`

<!-- source: intelligence/admin.py:1-20 -->
```python
from django.contrib import admin

from .models import AIAnalysis, Alert, CompanyScan


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ["kind", "status", "business", "model_name", "created_at"]
    list_filter = ["kind", "status"]


@admin.register(CompanyScan)
class CompanyScanAdmin(admin.ModelAdmin):
    list_display = ["url", "status", "business", "created_at"]


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["summary", "severity", "kind", "business", "acknowledged_at"]
    list_filter = ["severity", "kind"]
```

### 3. Migrate

```bash
python manage.py makemigrations intelligence
```

```bash
python manage.py migrate
```

## Check

```text
Migrations for 'intelligence':
  intelligence/migrations/0001_initial.py
    + Create model CompanyScan
    + Create model Alert
    + Create model AIAnalysis
```

(`CompanyScan` comes first because `AIAnalysis` and `Alert` point to it; Django orders
the steps for you.) The admin now has an **Intelligence** section.

## Line by line

### `AIAnalysis` (lines 18–72)

- **Lines 1–9** · Docstring naming the three tables.
- **Lines 11–15** · Imports, the same as every other `models.py`.
- **Lines 19–22** · Three kinds of AI answer: explaining a run (this part), the expert
  committee and the website profile (Part 8).
- **Lines 24–26** · It worked, or it failed.
- **Lines 28–30** · Which business. `business.analyses.all()` lists them.
- **Lines 31–37** · Which run it explains, if any (`null=True, blank=True`: optional).
  Delete the run and its explanations go too (`CASCADE`).
- **Lines 38–44** · Which scan it's about, if any. Written as text
  (`"intelligence.CompanyScan"`) because that class comes **later** in this file.
  `SET_NULL`: deleting a scan keeps the analysis.
- **Lines 45–46** · Kind and status.
- **Line 47** · Which Gemini model answered, e.g. `gemini-3.5-flash-lite`.
- **Line 48** · Which version of the prompt was used, e.g. `run-explanation/2`. If we
  improve the prompt, old answers still say which instructions produced them.
- **Lines 49–50** · The fingerprint of the question (task + prompt version + model +
  data). Same fingerprint = we already have this answer, so no new call (lesson 7.7).
- **Line 51** · The AI's answer, as JSON (already checked against the schema).
- **Lines 52–53** · Numbers the guardrail flagged (lesson 7.5).
- **Lines 54–55** · Links the AI cited (Part 8).
- **Line 56** · If it failed, why.
- **Lines 57–59** · How many real calls to Gemini this answer cost, retries included.
  Adding these up per day enforces the daily budget.
- **Lines 61–62** · Organization path and scoped queryset.
- **Lines 64–65** · `from_cache` is a plain class attribute, **not** a database field.
  The client sets it to `True` on an answer it served from the cache, so the API can say
  so. It's never saved.
- **Lines 67–69** · Newest first. `verbose_name_plural` fixes the admin's spelling
  ("AI analyses", not "AI analysiss").
- **Lines 71–72** · Prints like `Run explanation (ok)`. `get_kind_display()` is made by
  Django for every field with choices: it returns the label instead of the stored value.

### `CompanyScan` (lines 75–103)

- **Lines 76–81** · The stages of a scan, including **blocked** (the site said no, or our
  safety rules did).
- **Lines 83–86** · Which business, and which address was read.
- **Line 87** · Status, "pending" at first.
- **Lines 88–89** · A log in plain words ("Reading /pricing..."), shown live (Part 8).
- **Line 90** · Did the site's `robots.txt` allow us? `null=True` on a
  `BooleanField` allows a third answer: "not checked yet".
- **Lines 91–92** · What we found on each page, kept so the next scan can compare.
- **Lines 93–94** · Error, and when it finished.
- **Lines 96–103** · Organization path, queryset, newest first, printing.

### `Alert` (lines 106–140)

- **Lines 107–110** · How serious.
- **Lines 112–117** · What kind of change.
- **Lines 119–122** · Which business, and which scan found it.
- **Lines 123–126** · Severity, kind, a one-line summary, and the details (before, after,
  page).
- **Lines 127–130** · When, and by whom, someone said "seen it".
- **Lines 132–133** · Organization path and queryset.
- **Lines 135–137** · Sort **unread** alerts (empty `acknowledged_at`) first, newest
  first within each group. `models.F("acknowledged_at").asc(nulls_first=True)` says
  "ascending, with empty values first". Why spell it out? SQLite puts empty values first
  anyway, but **PostgreSQL puts them last**. With a plain `"acknowledged_at"`, your
  tests (SQLite) would pass while the real site (Neon) showed unread alerts at the
  bottom. A test in Part 8 checks this.
- **Lines 139–140** · Prints the summary.

### `intelligence/admin.py`

- **Lines 6–9** · AI analyses: columns and filters by kind and status.
- **Lines 12–14** · Scans: columns.
- **Lines 17–20** · Alerts: columns and filters.

## If it didn't work

| You see | Fix |
|---|---|
| `No changes detected` | Is `"intelligence"` in `INSTALLED_APPS` (lesson 4.3)? |
| `fields.E300 ... related model 'intelligence.CompanyScan' cannot be resolved` | Check the spelling on line 39 and that the `CompanyScan` class exists. |

## Quiz

1. Why is `from_cache` not a database field?
2. Why record the prompt version with each answer?
3. Which alerts come first in a list, and why?

---

**Next:** [7.4 · Schemas and the prompt](04-schemas-and-the-prompt.md)

<details><summary>Quiz answers</summary>

1. It describes **this** response ("served from cache just now"), not the saved answer.
2. So you always know which instructions produced an answer, even after the prompt is
   improved.
3. Unacknowledged ones: their `acknowledged_at` is empty, and `nulls_first=True` puts
   empty values first on every database.

</details>
