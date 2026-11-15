# 9.2 · The Decision table

**Time:** 30 minutes · **Before this:** [9.1](01-humans-decide.md).

## 📖 Read

The `decisions` app has existed since Part 4 (you made it empty, with the others). Now it
gets its one table, `Decision`. Most fields you know by now: text, a choice list, links to
other tables. Two are new ideas:

- **`on_delete=models.SET_NULL`** on the run: if a run is ever deleted, the decision
  **stays**, just without the link. A decision is too important to vanish with its run.
- **`history = models.JSONField(default=list)`**: a list of dictionaries stored in one
  column, like the scan log in Part 8.

## ⌨️ Do

### 1. `decisions/models.py`

<!-- source: decisions/models.py:1-69 -->
```python
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
```

### 2. `decisions/admin.py`

<!-- source: decisions/admin.py:1-9 -->
```python
from django.contrib import admin

from .models import Decision


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "owner", "business", "created_at"]
    list_filter = ["status"]
```

### 3. Make and run the migration

```bash
python manage.py makemigrations decisions
```

```text
Migrations for 'decisions':
  decisions\migrations\0001_initial.py
    + Create model Decision
```

```bash
python manage.py migrate
```

## ✅ Check

Open **http://127.0.0.1:8000/admin/** (start the server first). There's a new
**Decisions** section. Click **Add**: you'll see every field, with "Proposed" already
chosen as the status.

## 🔍 Line by line

### `decisions/models.py`

- **Lines 1–5** · Docstring: a human choice with an owner, a reason and a run. Line 4
  says the important rule.
- **Lines 7–8** · `settings` (for the user table's name) and `models`.
- **Lines 10–11** · `BaseModel` (a UUID `id`, `created_at`, `updated_at`; lesson 4.4) and
  the organization filter (lesson 4.6).
- **Line 14** · The table.
- **Lines 15–20** · The five statuses. Each has a stored value (`"in_progress"`) and a
  label people read (`"In progress"`).
- **Lines 22–24** · The business it belongs to. If the business is deleted, its decisions
  go too (`CASCADE`). `related_name="decisions"` lets you write `business.decisions.all()`.
- **Lines 25–33** · The run, optional (`null=True, blank=True`). `SET_NULL`: deleting the
  run keeps the decision, without the link.
- **Line 34** · A title, up to 160 characters.
- **Lines 35–41** · The owner: a user, optional. If the user is deleted, the decision
  stays, unowned.
- **Line 42** · The status, starting as "proposed". `max_length=12` fits `in_progress`.
- **Lines 43–45** · The chosen response: a case key from the run, like `queue_retry`.
  `help_text` is shown under the field in the admin.
- **Line 46** · The reason, as long as needed. `blank=True`: allowed to be empty (the
  brief will nag, politely).
- **Lines 47–49** · Who created it. `related_name="+"` means "no reverse name needed".
- **Lines 50–58** · Who signed it off (approved or rejected) and when.
- **Lines 59–60** · The history: a list. The comment shows what each entry holds.
  `default=list` gives each new decision its **own** empty list.
- **Lines 62–63** · How to filter by organization: through the business (lesson 4.6).
- **Lines 65–66** · Newest first.
- **Lines 68–69** · In the admin and the shell, a decision shows as its title.

### `decisions/admin.py`

- **Lines 1–3** · The admin, and our table.
- **Lines 6–9** · Register it, with useful columns and a filter by status.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `No changes detected in app 'decisions'` | Is the file saved? Is `"decisions"` in `INSTALLED_APPS` (lesson 4.3)? |
| `fields.E304 Reverse accessor ... clashes` | `created_by` and `decided_by` need `related_name="+"` (lines 48 and 56). |

## ❓ Quiz

1. A run is deleted. What happens to a decision linked to it?
2. Why `default=list` and not `default=[]`?

---

**Next:** [9.3 · The workflow](03-the-workflow.md)

<details><summary>Quiz answers</summary>

1. The decision stays; its `run` becomes empty (`SET_NULL`).
2. `default=list` makes a **new** empty list for every decision. One shared `[]` would be
   the same list for all of them, so one decision's history would leak into others.
   (Django warns about this.)

</details>
