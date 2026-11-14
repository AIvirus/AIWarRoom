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
        ordering = ["acknowledged_at", "-created_at"]  # unacknowledged first

    def __str__(self):
        return self.summary
