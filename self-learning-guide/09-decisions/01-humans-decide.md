# 9.1 · Humans decide

**Time:** 20 minutes · **Before this:** [Part 8](../08-websites-safely/README.md).
**Reading only.**

## 📖 Read

### Why record a decision at all?

Imagine three months from now. The payment gateway goes down again, and someone asks:
*"Why did we choose to queue payments instead of paying for a backup gateway? Who agreed
to that?"*

If the answer is "it was in a chat somewhere", nobody can check it. A **decision record**
answers it in one place:

| Field | Example |
|---|---|
| Title | Queue and retry payments during outages |
| Linked run | "Gateway down 2h", run on 15 Nov |
| Chosen response | `queue_retry` (one of the run's cases) |
| Owner | Priya (the person responsible) |
| Rationale ("why") | Lowest total impact in the model, cheap to set up. We accept slower recovery. |
| Status | approved |
| Signed off by | Priya, 15 Nov 2026, 16:24 UTC |
| History | every status change: who, when, from, to, note |

### Only people decide

The AI explains runs and gives advice. It never creates, approves or rejects a decision.
That's not a rule we hope the AI follows; it's how the code is built: **no AI code path
calls the decisions code at all**. You'll see the comment saying so in lesson 9.3.

### The status map

A decision moves through a few statuses, like a parcel's tracking: proposed, approved, in
progress, done. Not every move makes sense. "Proposed" can't jump straight to "done" (who
approved it?). "Done" is final.

```text
    proposed ──> approved ──> in_progress ──> done
        │            │              │
        └────────────┴──────────────┴──> rejected ──> proposed (re-opened)
```

A map like this, where each status lists the statuses that may come next, is called a
**state machine**. Two moments are special: **approved** and **rejected**. That's when
someone takes responsibility, so the app records **who** and **when** (the "sign-off").
Re-opening a rejected decision clears the old sign-off: it no longer applies.

### The history is append-only

Every status change **adds** an entry to the decision's history. Entries are never edited
or deleted. Editing the title or rationale doesn't add history; only status changes do.

### The brief never recalculates

When the brief shows "Daily orders: 2,400", that's the value **frozen inside the run**
when it was made (Part 6's input snapshot), not today's value. If someone later changes
daily orders to 3,000, the brief still shows what the decision was **actually** based on.
That's the whole point of a record.

## ❓ Quiz

1. Can a decision go from "proposed" straight to "done"?
2. Which two statuses record a sign-off, and why those two?
3. Someone edits a business's daily orders after a decision. What does the brief show?

---

**Next:** [9.2 · The Decision table](02-the-decision-table.md)

<details><summary>Quiz answers</summary>

1. No. Proposed can only become approved or rejected.
2. Approved and rejected: those are the moments someone takes responsibility.
3. The old value, frozen in the run the decision was linked to.

</details>
