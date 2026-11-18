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
    # Revenue lost so far feeds the System View's knock-on labels ("₹48,000 refunded").
    margin = aov * pct(inputs.contribution_margin)
    running = revenue_running = ZERO
    for row in rows:
        lost_now = Decimal(str(row["lost"]))
        running += lost_now * margin + Decimal(str(row["cost"]))
        revenue_running += lost_now * aov
        row["impact_cum"] = display(running)
        row["lost_revenue_cum"] = display(revenue_running)

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
