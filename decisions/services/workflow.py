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
