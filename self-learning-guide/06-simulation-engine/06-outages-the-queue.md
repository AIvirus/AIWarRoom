# 6.6 · Outages, part 2: the queue

**Time:** 60 minutes · **Before this:** [6.5](05-outages-checkout.md).

## 📖 Read

When a **warehouse** or **courier** stops, orders aren't refused. Customers still order
and pay; the orders just **wait**. So the question is different: how long is the queue,
how long until it's cleared, and how many customers cancel while they wait?

### First in, first out

The warehouse works like a ticket queue at a counter: the oldest order is served first.
Each hour:

1. This hour's new orders join the **back** of the queue.
2. The warehouse uses its capacity on the **front** of the queue.
3. The longer an order has waited, the more likely its customer has cancelled. A
   cancelled order doesn't use capacity (nobody packs it).

### Cancellations grow, then stop growing

With "2 % per hour of delay, at most 30 %": an order that waited 1 hour has a 2 % chance
of being cancelled, 2 hours 4 %, ... 15 hours 30 %, and 40 hours still 30 % (the cap).

### Work it out by hand (with the test's numbers)

100 orders arrive every hour. The warehouse can process 200 an hour. It's down for hours
0 and 1.

| Hour | What happens | Queue after |
|---|---|---|
| 0 | Down. Nothing processed. | h0: 100 |
| 1 | Down. Nothing processed. | h0: 100, h1: 100 |
| 2 | Back, 200 capacity. **h0's orders** waited 2 h → 4 % cancel: 96 shipped, 4 cancelled (uses 96). **h1's** waited 1 h → 2 %: 98 shipped, 2 cancelled (uses 98). 6 capacity left: 6 of **h2's** ship on time. | h2: 94 |
| 3 | h2's 94 waited 1 h → 2 %: 92.12 shipped, 1.88 cancelled. Then h3's 100 ship on time. | empty |

```text
delayed orders     = 100 + 100 + 94 = 294
cancelled (lost)   = 4 + 2 + 1.88   = 7.88
lost contribution  = 7.88 × ₹600 × 25 % = ₹1,182
recovered after    = 4 hours (the queue is empty at the end of hour 3)
```

### Measured against a normal day

What if the warehouse can't keep up **even on a normal day** (capacity below the evening
peak)? Then some orders wait every evening anyway. Blaming those on the outage would be
unfair. So the engine runs the queue **twice**: once with the outage, once without, and
counts only the **difference**.

## ⌨️ Do

Add these two pieces to the **end** of `simulation_engine/disruption.py`.

### Piece 4: fulfilment mode (lines 169–293)

<!-- source: simulation_engine/disruption.py:169-293 -->
```python
# --------------------------------------------------------------------------------------
# Fulfilment mode (warehouse, courier)
# --------------------------------------------------------------------------------------
def cancel_fraction(inputs: DisruptionInputs, delay_hours: int, strategy: str) -> Decimal:
    """Share of orders cancelled after waiting `delay_hours`: grows per hour, then caps."""
    rate = min(pct(inputs.max_cancel_rate), pct(inputs.cancel_rate_per_delay_hour) * delay_hours)
    if strategy == "queue_retry" and delay_hours <= inputs.retry_window_hours:
        rate = rate * (ONE - pct(inputs.retry_success_rate))
    return rate


def _run_queue(inputs: DisruptionInputs, strategy: str, with_outage: bool) -> dict:
    """
    First-in-first-out order queue, one step per hour.

    Each hour: new orders join the back of the queue; available capacity works from the
    front. An order processed in the hour it arrived has zero delay. Cancelled orders don't
    use capacity (nobody picks a cancelled order).
    """
    share = pct(inputs.affected_share)
    queue: deque[list] = deque()  # [arrival_hour, orders]
    totals = dict(shipped=ZERO, cancelled=ZERO, delayed=ZERO, backup=ZERO)
    peak_backlog, recovery_hours, hours_down = ZERO, None, ZERO
    rows = []

    for t in range(inputs.horizon_hours):
        demand = hourly_demand(inputs, t) * share
        down = outage_fraction(inputs, t) if with_outage else ZERO
        live_backup = backup_fraction(inputs, t) if (with_outage and strategy == "backup") else ZERO
        primary_capacity = inputs.hourly_capacity * (ONE - down)
        backup_capacity = inputs.backup_capacity_per_hour * live_backup
        capacity = primary_capacity + backup_capacity
        hours_down += down - (live_backup if inputs.backup_capacity_per_hour > ZERO else ZERO)

        queue.append([t, demand])
        shipped_now = cancelled_now = ZERO
        while queue and capacity > ZERO:
            arrival, waiting = queue[0]
            delay = t - arrival
            cancel = cancel_fraction(inputs, delay, strategy)
            needed = waiting * (ONE - cancel)
            if needed <= capacity:
                done = waiting
                capacity -= needed
                queue.popleft()
            else:
                done = capacity / (ONE - cancel)
                queue[0][1] = waiting - done
                capacity = ZERO
            shipped_now += done * (ONE - cancel)
            cancelled_now += done * cancel
            if delay > 0:
                totals["delayed"] += done

        backlog = sum((w for _, w in queue), ZERO)
        peak_backlog = max(peak_backlog, backlog)
        total_capacity = primary_capacity + backup_capacity
        if backup_capacity > ZERO and total_capacity > ZERO:
            totals["backup"] += shipped_now * backup_capacity / total_capacity
        totals["shipped"] += shipped_now
        totals["cancelled"] += cancelled_now
        if recovery_hours is None and t + 1 >= inputs.outage_hours and backlog == ZERO:
            recovery_hours = t + 1

        normal = inputs.hourly_capacity
        health = min(ONE, (primary_capacity + backup_capacity) / normal) if normal > 0 else ONE
        rows.append(
            dict(t=t, demand=demand, shipped=shipped_now, backlog=backlog,
                 cancelled=cancelled_now, health=health)
        )  # fmt: skip

    return dict(
        **totals,
        rows=rows,
        peak_backlog=peak_backlog,
        backlog_end=sum((w for _, w in queue), ZERO),
        recovery_hours=recovery_hours,
        hours_down=max(ZERO, hours_down),
    )


def simulate_fulfilment(inputs: DisruptionInputs, strategy: str) -> dict:
    run = _run_queue(inputs, strategy, with_outage=True)
    # The same business with no outage. If normal capacity can't keep up with peak demand,
    # some orders are delayed or cancelled anyway; only the DIFFERENCE is the outage's.
    reference = _run_queue(inputs, "wait", with_outage=False)

    delayed = max(ZERO, run["delayed"] - reference["delayed"])
    lost = max(ZERO, run["cancelled"] - reference["cancelled"])
    cost = ZERO
    if strategy == "backup":
        cost = run["backup"] * inputs.backup_extra_cost_per_order
        if inputs.backup_switch_hours < inputs.outage_hours:
            cost += inputs.backup_activation_cost
    elif strategy == "queue_retry":
        cost = delayed * inputs.retry_cost_per_order

    rows = []
    for row, ref in zip(run["rows"], reference["rows"], strict=True):
        lost_now = max(ZERO, row["cancelled"] - ref["cancelled"])
        cost_now = cost if row["t"] == 0 else ZERO  # the response is paid for up front
        rows.append(
            _row(inputs, row["t"], row["demand"], row["shipped"], row["backlog"], lost_now,
                 cost_now, row["health"])
        )  # fmt: skip

    # With no outage there is nothing to recover from.
    recovery_hours = 0 if inputs.outage_hours == ZERO else run["recovery_hours"]

    return _outcome(
        inputs,
        affected=delayed,
        recovered=delayed - lost,
        lost=lost,
        cost=cost,
        hours_down=run["hours_down"],
        recovery_hours=recovery_hours,
        extra={
            "delayed_orders": metric("Orders delayed", delayed, "orders"),
            "peak_backlog": metric("Largest backlog", run["peak_backlog"], "orders"),
            "backlog_at_end": metric("Backlog left at end of period", run["backlog_end"], "orders"),
            "orders_via_backup": metric("Orders processed via backup", run["backup"], "orders"),
        },
        rows=rows,
    )
```

### Piece 5: the shared output shape (lines 296–349)

<!-- source: simulation_engine/disruption.py:296-349 -->
```python
# --------------------------------------------------------------------------------------
# Shared output shape
# --------------------------------------------------------------------------------------
def _row(inputs, t, demand, served, backlog, lost, cost, health) -> dict:
    return {
        "t": t,
        "clock": (inputs.start_hour + t) % 24,
        "demand": display(demand),
        "served": display(served),
        "backlog": display(backlog),
        "lost": display(lost),
        "cost": display(cost),
        "health": display(health),
    }


def _outcome(inputs, *, affected, recovered, lost, cost, hours_down, recovery_hours, extra, rows):
    aov = inputs.average_order_value
    lost_revenue = lost * aov
    lost_contribution = lost_revenue * pct(inputs.contribution_margin)

    # Running totals for the gauges: lost contribution + cost so far, hour by hour.
    margin = aov * pct(inputs.contribution_margin)
    running = ZERO
    for row in rows:
        running += Decimal(str(row["lost"])) * margin + Decimal(str(row["cost"]))
        row["impact_cum"] = display(running)

    metrics = {
        "affected_orders": metric("Orders affected", affected, "orders"),
        "affected_value": metric("Value of affected orders", affected * aov, "INR"),
        "recovered_orders": metric("Affected orders that still completed", recovered, "orders"),
        "lost_orders": metric("Orders lost", lost, "orders"),
        "lost_revenue": metric("Revenue lost", lost_revenue, "INR"),
        "lost_contribution": metric("Contribution lost", lost_contribution, "INR"),
        "mitigation_cost": metric("Cost of the response", cost, "INR"),
        "total_impact": metric(
            "Total financial impact (contribution lost + response cost)",
            lost_contribution + cost,
            "INR",
        ),
        "hours_without_service": metric("Hours with no service", hours_down, "hours"),
        "time_to_recovery": metric(
            "Hours until service AND backlog are back to normal",
            recovery_hours if recovery_hours is not None else None,
            "hours",
        ),
        **extra,
    }
    return {"metrics": metrics, "timeline": rows}


def peak_hourly_load(inputs: DisruptionInputs) -> Decimal:
    return max(hourly_demand(inputs, t) for t in range(24)) * pct(inputs.affected_share)
```

## ✅ Check

Now both modes work. Try the hand-worked example:

```bash
python
```

```python
from decimal import Decimal as D
from simulation_engine.disruption import DisruptionInputs, simulate_fulfilment

w = DisruptionInputs(
    daily_orders=D("2400"),
    average_order_value=D("600"),
    contribution_margin=D("25"),
    affected_share=D("100"),
    hourly_capacity=D("200"),
    cancel_rate_per_delay_hour=D("2"),
    max_cancel_rate=D("30"),
    outage_hours=D("2"),
    start_hour=0,
    horizon_hours=24,
    demand_profile="uniform",
)
out = simulate_fulfilment(w, "wait")
for key in ("delayed_orders", "lost_orders", "lost_contribution", "time_to_recovery"):
    print(key, out["metrics"][key]["value"])
```

(Press **Enter** twice after the last line: the empty line tells Python the loop is
finished.)

You should see `delayed_orders 294.00`, `lost_orders 7.88`,
`lost_contribution 1182.00` and `time_to_recovery 4`: your table. Type `exit()`.

## 🔍 Line by line

### Piece 4

- **Lines 169–171** · Section banner.
- **Line 172** · `cancel_fraction`: the share of orders cancelled after waiting
  `delay_hours`.
- **Line 174** · Rate per hour × hours, but never above the cap (`min`).
- **Lines 175–176** · With "queue and notify", customers who are told when their order
  will ship cancel less: the rate is reduced by the "kept" share, if the delay is
  within the promise window.
- **Line 177** · Return the rate.
- **Line 180** · `_run_queue`: the queue itself. `with_outage=False` runs a normal day
  for comparison.
- **Lines 181–187** · Docstring: the three rules from 📖 Read.
- **Line 188** · Share of orders through this part.
- **Line 189** · The queue. Each item is a small list `[arrival_hour, orders]`.
  `deque[list]` is a type hint: "a deque of lists".
- **Lines 190–192** · Totals, the biggest backlog seen, the recovery time (unknown yet),
  hours down, and the rows.
- **Line 194** · For each hour...
- **Line 195** · ...new orders...
- **Line 196** · ...how much of this hour the part is down (0 on the normal-day run)...
- **Line 197** · ...how much of it the backup is live (only for "backup", only with an
  outage)...
- **Lines 198–200** · ...capacity: the primary's share of the hour it's up, plus the
  backup's.
- **Line 201** · Hours without service, as in checkout.
- **Line 203** · Rule 1: new orders join the back.
- **Line 204** · Counters for this hour.
- **Line 205** · Rule 2: while there are orders and capacity left...
- **Line 206** · ...look at the **front** group (`queue[0]`): when it arrived, how many.
- **Lines 207–208** · How long it has waited, and its cancel rate.
- **Line 209** · Capacity needed: only for orders **not** cancelled (rule 3).
- **Lines 210–213** · Enough capacity for the whole group? Process it, use the capacity,
  and remove it from the front (`popleft`).
- **Lines 214–217** · Not enough? Process as much as the capacity allows, leave the rest
  at the front, and capacity is used up. `capacity / (1 − cancel)`: because cancelled
  orders don't use capacity, 94 capacity can "handle" 94 ÷ 0.98 orders.
- **Lines 218–219** · Of the orders handled, some ship and some were cancelled.
- **Lines 220–221** · Handled after waiting? They were **delayed**.
- **Lines 223–224** · The backlog left, and the biggest so far. `sum(..., ZERO)` starts
  the sum from a Decimal zero.
- **Lines 225–227** · How many shipped orders the backup handled: its share of this
  hour's capacity.
- **Lines 228–229** · Add to totals.
- **Lines 230–231** · The first hour, after the outage, when the queue is empty: that's
  the recovery time (`t + 1` because hour 3 ends at 4 hours).
- **Lines 233–234** · Health: capacity now ÷ normal capacity, at most 1.
- **Lines 235–238** · Save the hour's numbers.
- **Lines 240–247** · Return everything, including the backlog still left at the end.
- **Line 250** · `simulate_fulfilment`: one strategy for a warehouse or courier outage.
- **Line 251** · Run with the outage...
- **Lines 252–254** · ...and a normal day without it, always with "wait" (the comment
  explains why).
- **Lines 256–257** · Only the **difference** counts: delayed and cancelled orders
  beyond a normal day. `max(ZERO, ...)` stops it going negative.
- **Lines 258–264** · The response cost: backup = extra cost per order it handled, plus
  activation if it switched on; queue and notify = cost per delayed order; wait = 0.
- **Lines 266–273** · Hour-by-hour rows, again as differences. `zip(..., strict=True)`
  walks the two runs side by side and complains if they have different lengths. The
  whole cost is shown in hour 0 (the response is paid for up front).
- **Line 276** · No outage, nothing to recover from: 0 hours.
- **Lines 278–293** · Build the result with the extra fulfilment metrics.

### Piece 5

- **Lines 296–298** · Section banner.
- **Lines 299–309** · `_row`: one hour, in the same shape for both modes, as floats for
  drawing. `clock` is the hour of the day, for the chart's labels.
- **Line 312** · `_outcome`: the final numbers. The `*` means every argument after it
  must be given **by name** (`affected=...`), so they can't be mixed up.
- **Lines 313–315** · The chain from lesson 6.1: lost orders × order value = lost
  revenue; × margin = lost contribution.
- **Lines 317–322** · A running total of the impact, hour by hour, for the gauges:
  lost contribution so far + cost so far.
- **Lines 324–344** · All the metrics, each with a label that says exactly what it is
  (line 333: "contribution lost + response cost"). `**extra` adds the mode's own extra
  metrics.
- **Line 345** · The result: metrics and timeline.
- **Lines 348–349** · The busiest hour's load on this part, for a warning in lesson 6.7
  ("normal capacity is below peak demand").

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `NameError: name '_row' is not defined` | Piece 5 is missing. (It's fine that it comes **after** the functions that use it: Python looks a name up when the function runs, not when it's written.) |
| `lost_orders` isn't `7.88` | Check line 209 multiplies by `(ONE - cancel)` and line 215 divides by it. |
| The program never finishes | Line 217 must set `capacity = ZERO`, or the `while` loop never ends. |

## ❓ Quiz

1. Why are cancelled orders not counted against capacity?
2. Why does the engine run the queue twice?
3. What does `*` in `_outcome(inputs, *, affected, ...)` force?

---

**Next:** [6.7 · The runner](07-the-runner.md)

<details><summary>Quiz answers</summary>

1. Nobody picks and packs an order that has been cancelled.
2. Once with the outage and once without, so only the extra delays and cancellations
   caused by the outage are counted.
3. Every argument after it must be passed by name, which prevents mixing up numbers like
   `affected` and `lost`.

</details>
