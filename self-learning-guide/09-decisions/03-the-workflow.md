# 9.3 · The workflow

**Time:** 35 minutes · **Before this:** [9.2](02-the-decision-table.md).

## Read

The status map from lesson 9.1 becomes a **dictionary**: each status → the set of
statuses allowed next.

```text
proposed     → {approved, rejected}
approved     → {in_progress, rejected}
in_progress  → {done, rejected}
done         → {}            (closed)
rejected     → {proposed}    (re-open)
```

Keeping the rules in **one** small file means the API (lesson 9.7) and the page (lesson
9.6) both ask the same question, "may this move happen?", and get the same answer. If the
rules ever change, they change in one place.

## Do

Make `decisions/services/` with an **empty** `__init__.py`. Then create
`decisions/services/workflow.py`:

<!-- source: decisions/services/workflow.py:1-65 -->
```python
"""
How a decision moves, and the record it leaves.

    proposed ──> approved ──> in_progress ──> done
        │            │              │
        └────────────┴──────────────┴──> rejected ──> proposed (re-opened)

Only people move decisions. The AI can recommend a strategy; it cannot create, approve or
reject anything, because no AI code path calls this module.
"""

from django.utils import timezone

from decisions.models import Decision

S = Decision.Status
TRANSITIONS: dict[str, set[str]] = {
    S.PROPOSED: {S.APPROVED, S.REJECTED},
    S.APPROVED: {S.IN_PROGRESS, S.REJECTED},
    S.IN_PROGRESS: {S.DONE, S.REJECTED},
    S.DONE: set(),
    S.REJECTED: {S.PROPOSED},
}
SIGN_OFF = {S.APPROVED, S.REJECTED}  # the moments someone takes responsibility


class InvalidTransition(ValueError):
    pass


def allowed_next(status: str) -> list[str]:
    return sorted(TRANSITIONS[status])


def check_transition(current: str, new: str) -> None:
    if new != current and new not in TRANSITIONS[current]:
        options = ", ".join(allowed_next(current)) or "none (this decision is closed)"
        raise InvalidTransition(f"A {current} decision can move to: {options}.")


def record_creation(decision: Decision, user) -> None:
    decision.history = [_entry(user, None, decision.status, "Created")]
    decision.save(update_fields=["history"])


def record_status_change(decision: Decision, old: str, user, note: str = "") -> None:
    """Call after the status field has changed and been validated."""
    if decision.status == old:
        return
    decision.history = [*decision.history, _entry(user, old, decision.status, note)]
    if decision.status in SIGN_OFF:
        decision.decided_by, decision.decided_at = user, timezone.now()
    elif decision.status == S.PROPOSED:  # re-opened: the old sign-off no longer applies
        decision.decided_by, decision.decided_at = None, None
    decision.save(update_fields=["history", "decided_by", "decided_at", "updated_at"])


def _entry(user, old, new, note) -> dict:
    return {
        "at": timezone.now().isoformat(),
        "by": str(user) if user else None,
        "from": old,
        "to": new,
        "note": note[:280],
    }
```

## Check

In `python manage.py shell`:

```python
from decisions.services import workflow

workflow.allowed_next("proposed")
```

```text
[Decision.Status.APPROVED, Decision.Status.REJECTED]
```

That's how Python shows the two choices; their stored values are `"approved"` and
`"rejected"`. Now:

```python
workflow.allowed_next("done")
```

`[]`: done is final. And an illegal jump:

```python
workflow.check_transition("proposed", "done")
```

The last line of the error:

```text
decisions.services.workflow.InvalidTransition: A proposed decision can move to: approved, rejected.
```

The message says what **is** allowed, not just "no". Try
`workflow.check_transition("done", "rejected")` too.

## Line by line

- **Lines 1–10** · Docstring: the map, and the promise that no AI code calls this module.
- **Line 12** · `timezone`, for "now".
- **Line 14** · The table.
- **Line 16** · `S` is a short nickname for `Decision.Status`, so the next lines stay
  readable.
- **Lines 17–23** · `TRANSITIONS`: the map. `dict[str, set[str]]` is a **type hint**: "a
  dictionary from text to sets of text". `set()` is an empty set (`{}` would be an empty
  dictionary).
- **Line 24** · The two sign-off statuses.
- **Lines 27–28** · `InvalidTransition`: our own error. It's a kind of `ValueError`, and
  `pass` means "nothing to add".
- **Lines 31–32** · `allowed_next(status)`: the allowed next statuses, sorted so they
  always come in the same order.
- **Line 35** · `check_transition(current, new)`: raise an error if the move isn't
  allowed.
- **Line 36** · "Staying the same" is always fine (`new != current`). Otherwise `new` must
  be in the allowed set.
- **Line 37** · The allowed options as text, or a clear "none (this decision is closed)".
  `or` picks the right side when the left is empty text.
- **Line 38** · Raise it, with a message that helps.
- **Lines 41–43** · `record_creation`: start the history with one entry, "Created", and
  save only that field.
- **Line 46** · `record_status_change(decision, old, user, note)`.
- **Line 47** · Docstring: call it **after** the status was checked and changed.
- **Lines 48–49** · Nothing changed? Nothing to record.
- **Line 50** · **Add** an entry. `[*decision.history, new_entry]` builds a new list: all
  the old entries, then the new one. Old entries are never touched.
- **Lines 51–52** · Approved or rejected: record who and when.
- **Lines 53–54** · Re-opened: clear the old sign-off.
- **Line 55** · Save just those fields.
- **Lines 58–65** · `_entry`: one history entry. The time as text, the person's name (or
  `None`), from, to, and the note cut to 280 characters.

## If it didn't work

| You see | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'decisions.services'` | The folder needs its empty `__init__.py`. |
| `KeyError: 'finished'` | You asked about a status that doesn't exist. The five are on lines 16–20 of `models.py`. |

## Quiz

1. Where would you change the rules if "approved" should also be allowed to go straight
   to "done"?
2. Does editing a decision's title add a history entry?

---

**Next:** [9.4 · The brief](04-the-brief.md)

<details><summary>Quiz answers</summary>

1. In `TRANSITIONS` (line 19): add `S.DONE` to approved's set. Everything else follows.
2. No. Only `record_status_change` adds entries, and only when the status changed.

</details>
