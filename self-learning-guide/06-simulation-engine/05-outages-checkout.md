# 6.5 · Outages, part 1: checkout

**Time:** 50 minutes · **Before this:** [6.4](04-cases-and-sensitivity.md).

## Read

Now the second half of the app, the **Resilience Room**: what does an outage cost a
running shop? `disruption.py` is long, so it's split over two lessons. This one covers
the shared set-up and the **payment gateway** (lesson 6.1, Example 2).

### Hours, not days

The engine steps through time **one hour at a time**, starting at the moment the outage
begins (hour `t = 0`). Two things make that realistic:

- **The day has a shape.** People order more at 8 pm than at 4 am. The **e-commerce
  curve** says what share of a day's orders arrive in each clock hour (in thousandths,
  adding up to 1000). It's an illustrative shape, and the engine always warns that it
  isn't the shop's own data. `uniform` (the same every hour) is the other choice.
- **Outages don't end on the hour.** A 1.5-hour outage takes all of hour 0 and **half**
  of hour 1. So the engine works with fractions of hours.

### The three responses for a payment outage

| Strategy | What happens |
|---|---|
| `wait` | Payments fail. Some customers (recapture) come back later and pay. |
| `backup` | After a switch-over delay, a backup gateway takes payments, up to its hourly capacity, at an extra cost per order plus a one-off activation cost. |
| `queue_retry` | Failed payments are queued and retried when the gateway returns, if they haven't waited longer than the retry window. |

## Do

Create `simulation_engine/disruption.py`. Type these three pieces now; lesson 6.6 adds
the rest to the **same file**.

### Piece 1: the idea and the inputs (lines 1–74)

<!-- source: simulation_engine/disruption.py:1-74 -->
```python
"""
Resilience Room: what an outage costs, hour by hour, under three responses.

The key idea: AFFECTED orders are not LOST orders, and lost revenue is not lost profit.

    affected orders     orders that hit the broken component
    lost orders         affected orders that never complete
    lost revenue        lost orders x average order value
    lost contribution   lost revenue x contribution margin   <- what the P&L actually loses
    total impact        lost contribution + what the response itself cost

Two ways a component can fail ("loss modes"):

  checkout    (payment gateway) An order fails at the moment of payment. Some customers
              come back later on their own (recapture); the rest are gone.
  fulfilment  (warehouse, courier) Orders are taken but can't be processed. They queue
              (first in, first out) and the queue clears with spare capacity once service
              returns. Each hour an order waits raises its chance of being cancelled.

Three responses ("strategies"), each with its own parameters:

  wait         do nothing special
  backup       after a switch-over delay, route traffic to a backup with limited capacity
               and a per-order extra cost (plus a one-off activation cost)
  queue_retry  checkout: queue failed payments and retry them when the gateway returns
               fulfilment: keep customers informed so fewer delayed orders are cancelled

Simplifications, stated so nobody mistakes them for features:
- Demand within one hour is spread evenly; the day shape comes from the demand profile.
- Customers who fail at checkout but come back are assumed to succeed when service returns.
- In fulfilment mode, the backup only runs during the outage; the primary clears the
  backlog afterwards.
- Failure spreads ONE hop: direct dependents of the broken component degrade in
  proportion to the traffic that goes through it; nothing further down is touched.
"""

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from .money import ONE, ZERO, clamp, display, metric, pct

# Share of a day's orders placed in each hour, in thousandths (sums to 1000).
# Illustrative Indian e-commerce shape: quiet nights, a lunchtime bump, an evening peak.
ECOMMERCE_CURVE = (
    20, 12, 8, 6, 6, 10, 20, 32, 42, 48, 52, 54,
    56, 52, 48, 46, 48, 56, 66, 74, 78, 72, 56, 38,
)  # fmt: skip
assert sum(ECOMMERCE_CURVE) == 1000


@dataclass(frozen=True)
class DisruptionInputs:
    # Business assumptions
    daily_orders: Decimal
    average_order_value: Decimal
    contribution_margin: Decimal  # percent
    affected_share: Decimal  # percent of orders that go through the failing component
    hourly_capacity: Decimal = ZERO  # fulfilment only: normal processing capacity
    recapture_rate: Decimal = ZERO  # checkout only, percent
    cancel_rate_per_delay_hour: Decimal = ZERO  # fulfilment only, percent
    max_cancel_rate: Decimal = ZERO  # fulfilment only, percent
    # Scenario parameters
    outage_hours: Decimal = Decimal("4")
    start_hour: int = 18
    horizon_hours: int = 72
    demand_profile: str = "ecommerce_curve"
    backup_switch_hours: Decimal = Decimal("1")
    backup_capacity_per_hour: Decimal = ZERO
    backup_extra_cost_per_order: Decimal = ZERO
    backup_activation_cost: Decimal = ZERO
    retry_success_rate: Decimal = ZERO  # percent
    retry_window_hours: Decimal = ZERO
    retry_cost_per_order: Decimal = ZERO
```

### Piece 2: time helpers (lines 77–97)

<!-- source: simulation_engine/disruption.py:77-97 -->
```python
# --------------------------------------------------------------------------------------
# Time helpers
# --------------------------------------------------------------------------------------
def hourly_demand(inputs: DisruptionInputs, t: int) -> Decimal:
    """Orders placed in simulation hour t (hour 0 is when the outage starts)."""
    clock = (inputs.start_hour + t) % 24
    if inputs.demand_profile == "uniform":
        return inputs.daily_orders / 24
    return inputs.daily_orders * ECOMMERCE_CURVE[clock] / 1000


def outage_fraction(inputs: DisruptionInputs, t: int) -> Decimal:
    """How much of hour t the component is down: 1 inside the outage, 0.5 for half an hour."""
    return clamp(inputs.outage_hours - t, ZERO, ONE)


def backup_fraction(inputs: DisruptionInputs, t: int) -> Decimal:
    """How much of hour t the backup is live: after the switch-over AND during the outage."""
    start = max(Decimal(t), inputs.backup_switch_hours)
    end = min(Decimal(t + 1), inputs.outage_hours)
    return clamp(end - start, ZERO, ONE)
```

### Piece 3: checkout mode (lines 100–166)

<!-- source: simulation_engine/disruption.py:100-166 -->
```python
# --------------------------------------------------------------------------------------
# Checkout mode (payment gateway)
# --------------------------------------------------------------------------------------
def simulate_checkout(inputs: DisruptionInputs, strategy: str) -> dict:
    share = pct(inputs.affected_share)
    recapture = pct(inputs.recapture_rate)
    retry_ok = pct(inputs.retry_success_rate)

    totals = dict(affected=ZERO, backup=ZERO, recovered=ZERO, lost=ZERO, cost=ZERO, queued=ZERO)
    hours_down = ZERO
    rows = []
    for t in range(inputs.horizon_hours):
        demand = hourly_demand(inputs, t) * share
        down = outage_fraction(inputs, t)
        affected = demand * down

        served_by_backup = ZERO
        live_backup = ZERO
        if strategy == "backup":
            live_backup = backup_fraction(inputs, t)
            capacity = inputs.backup_capacity_per_hour * live_backup
            served_by_backup = min(demand * live_backup, capacity)
        failed = affected - served_by_backup

        # Which of this hour's failed checkouts complete in the end?
        if strategy == "queue_retry":
            waits = inputs.outage_hours - t  # hours until the gateway is back
            queued = failed if waits <= inputs.retry_window_hours else ZERO
            retried = queued * retry_ok
            # Payments that still fail (or were never queued) fall back to the same natural
            # recapture as "wait". Every strategy gets it, so the comparison is fair.
            recovered = retried + (failed - retried) * recapture
            cost = queued * inputs.retry_cost_per_order
            totals["queued"] += queued
        else:
            recovered = failed * recapture
            cost = served_by_backup * inputs.backup_extra_cost_per_order
        lost = failed - recovered

        totals["affected"] += affected
        totals["backup"] += served_by_backup
        totals["recovered"] += recovered + served_by_backup
        totals["lost"] += lost
        totals["cost"] += cost
        hours_down += down - (live_backup if inputs.backup_capacity_per_hour > ZERO else ZERO)
        health = ONE - (failed / demand if demand > ZERO else ZERO)
        rows.append(_row(inputs, t, demand, demand - failed, ZERO, lost, cost, health))

    activated = strategy == "backup" and inputs.backup_switch_hours < inputs.outage_hours
    if activated:
        totals["cost"] += inputs.backup_activation_cost
        rows[0]["cost"] += display(inputs.backup_activation_cost)

    return _outcome(
        inputs,
        affected=totals["affected"],
        recovered=totals["recovered"],
        lost=totals["lost"],
        cost=totals["cost"],
        hours_down=max(ZERO, hours_down),
        recovery_hours=inputs.outage_hours,
        extra={
            "orders_via_backup": metric("Orders completed via backup", totals["backup"], "orders"),
            "payments_queued": metric("Payments queued for retry", totals["queued"], "orders"),
        },
        rows=rows,
    )
```

There's nothing to run yet: `simulate_checkout` calls `_row` and `_outcome`, which you
write in lesson 6.6.

## Line by line

### Piece 1

- **Lines 1–35** · The docstring is the whole model in words. Read it slowly; it has
  the most important idea of Part 6 (lines 4–10): affected ≠ lost, and lost revenue ≠
  lost profit. Lines 28–34 list the **simplifications**, "so nobody mistakes them for
  features".
- **Line 37** · `deque` ("deck"): a list that's fast to add to at the back and remove
  from at the front. Perfect for a queue (lesson 6.6).
- **Lines 38–41** · Imports.
- **Lines 43–48** · The e-commerce curve: 24 numbers, one per clock hour from midnight.
  `# fmt: skip` tells ruff not to reformat it, so it stays as two neat rows of 12.
- **Line 49** · `assert` checks something is true **when the file loads**. If someone
  edits the curve and it no longer adds up to 1000, the program stops immediately
  instead of quietly losing orders.
- **Lines 52–74** · `DisruptionInputs`: everything one outage needs. Business numbers
  first (lines 55–62), then scenario settings (lines 64–74). `affected_share` is the
  share of orders that go through the broken part (e.g. "100 % of payments use the
  primary gateway"). Fields with `= ...` have defaults, so tests can leave them out.

### Piece 2

- **Lines 77–79** · Section banner.
- **Line 80** · `hourly_demand(inputs, t)`: orders placed in simulation hour `t`.
- **Line 81** · Docstring: hour 0 is when the outage starts.
- **Line 82** · Which **clock** hour is that? If the outage starts at 18:00, `t = 7` is
  18 + 7 = 25, and `% 24` ("the remainder after dividing by 24") makes it 1, i.e. 1 am.
- **Lines 83–84** · Uniform: a day's orders ÷ 24.
- **Line 85** · Curve: a day's orders × that hour's share ÷ 1000.
- **Lines 88–90** · `outage_fraction`: how much of hour `t` the part is down. With a
  1.5-hour outage: hour 0 → 1.5 − 0 = 1.5, clamped to 1 (all of it). Hour 1 → 0.5
  (half). Hour 2 → −0.5, clamped to 0 (none).
- **Lines 93–97** · `backup_fraction`: how much of hour `t` the backup is live. It's live
  from the switch-over time until the outage ends. The overlap of "this hour" (`t` to
  `t + 1`) with "backup live" is from the **later** start to the **earlier** end; if
  that's negative there's no overlap, so clamp to 0–1.

  Example: switch at 0.5 h, outage 1.5 h. Hour 0: from max(0, 0.5) = 0.5 to
  min(1, 1.5) = 1 → 0.5 of the hour. Hour 1: from 1 to 1.5 → 0.5. Hour 2: from 2 to
  1.5 → negative → 0.

### Piece 3

- **Line 103** · `simulate_checkout(inputs, strategy)`: one strategy for a payment
  outage.
- **Lines 104–106** · The percentages as fractions.
- **Line 108** · Running totals, all starting at 0. `dict(a=1)` is another way to write
  `{"a": 1}`.
- **Lines 109–110** · Hours without service, and the hour-by-hour rows.
- **Line 111** · For each hour of the simulated period...
- **Line 112** · ...orders this hour that go through the gateway...
- **Lines 113–114** · ...and how many of them hit the outage (**affected**).
- **Lines 116–121** · Backup: live for part of the hour? Then its capacity for that part
  is `capacity × fraction`. It serves the orders arriving while it's live, but never
  more than its capacity (`min`).
- **Line 122** · **Failed** = affected minus what the backup saved.
- **Lines 124–133** · Queue and retry:
  - **126** · How long would this hour's payments wait for the gateway to return?
  - **127** · Queue them only if that's within the retry window.
  - **128** · Retries that succeed.
  - **129–131** · Those that still fail get the same natural recapture as everyone
    else (the comment explains: otherwise the comparison wouldn't be fair).
  - **132–133** · Pay for every queued retry, and count the queue.
- **Lines 134–136** · Wait or backup: only the natural recapture comes back. The cost is
  the backup's extra cost per order it served (0 for wait).
- **Line 137** · **Lost** = failed − recovered.
- **Lines 139–143** · Add this hour to the totals. Orders the backup served count as
  recovered.
- **Line 144** · Hours fully without service: the outage time minus backup time (if
  there is a backup).
- **Line 145** · **Health** for the 3D view: 1 = all payments work, 0 = none. The
  `if demand > ZERO` avoids dividing by zero in an hour with no orders.
- **Line 146** · Save the row (`_row`, lesson 6.6).
- **Lines 148–151** · If the backup really switched on (before the outage ended), add
  its one-off activation cost, to the total and to hour 0 of the timeline.
- **Lines 153–166** · Build the final result with `_outcome` (lesson 6.6), adding two
  extra metrics only checkout has.

Compare lines 112–137 with lesson 6.1, Example 2. For "wait": affected 200, recovered
30 % = 60, lost 140. Same steps, hour by hour.

## If it didn't work

| You see | Fix |
|---|---|
| `AssertionError` on line 49 when importing | A number in the curve is mistyped; the 24 numbers must add up to 1000. |
| `IndentationError` around line 134 | `else:` must line up with the `if strategy == "queue_retry":` on line 125. |

## Quiz

1. An outage starts at 22:00. Which clock hour is `t = 3`?
2. A 2.25-hour outage: what is `outage_fraction` for hours 0, 1, 2, 3?
3. Why does every strategy get the natural recapture?

---

**Next:** [6.6 · Outages, part 2: the queue](06-outages-the-queue.md)

<details><summary>Quiz answers</summary>

1. (22 + 3) % 24 = 1, so 1 am.
2. 1, 1, 0.25, 0.
3. Some customers come back on their own whatever the shop does. Giving that to only one
   strategy would make the others look worse than they are.

</details>
