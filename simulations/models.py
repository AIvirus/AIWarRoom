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
