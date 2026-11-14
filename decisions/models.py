"""
Decision - a human choice, recorded with who owns it, why, and which run informed it.

The AI can recommend; only a person creates or approves a Decision.
"""

from django.conf import settings
from django.db import models

from common.models import BaseModel
from common.querysets import OrgScopedQuerySet


class Decision(BaseModel):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        REJECTED = "rejected", "Rejected"

    business = models.ForeignKey(
        "businesses.BusinessProfile", on_delete=models.CASCADE, related_name="decisions"
    )
    # Optional: some decisions follow a run, others don't. If the run is ever deleted the
    # decision stays, without the link.
    run = models.ForeignKey(
        "simulations.SimulationRun",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="decisions",
    )
    title = models.CharField(max_length=160)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_decisions",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROPOSED)
    chosen_strategy = models.CharField(
        max_length=40, blank=True, help_text="Case or strategy key from the run, e.g. 'backup'."
    )
    rationale = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Who approved or rejected it, and when: the human sign-off the brief prints.
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    # Every status change: [{"at", "by", "from", "to", "note"}]. Append-only by convention.
    history = models.JSONField(default=list)

    ORG_PATH = "business__organization"
    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
