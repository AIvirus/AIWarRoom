# 6.7 · The runner

**Time:** 45 minutes · **Before this:** [6.6](06-outages-the-queue.md).

## 📖 Read

You now have the idea model, the cases, sensitivity and both outage modes. The **runner**
is the one front door to all of them:

```python
result = runner.run(template_key, assumptions, parameters, components)
```

You give it plain dictionaries (the scenario's template, the business's numbers, the
scenario's settings, its components). It checks everything with the catalogue, picks the
right model, runs every case or strategy, adds **warnings**, and returns one
`EngineResult`. Django (lesson 6.8), the live sliders (Part 10) and the tests all call
this same function, so they can never disagree.

**Same inputs, same output, every time.** There's no randomness and no clock in the
engine. That's what makes a run a trustworthy record.

### Warnings, not winners

For outages, the runner lays the three responses side by side and **names the
extremes** ("lowest total impact: queue_retry"), but it never declares a winner. Maybe
the cheapest option is too risky for this shop; that's a human decision (Part 9).

## ⌨️ Do

Create `simulation_engine/runner.py` in three pieces.

### Piece 1: the front door (lines 1–68)

<!-- source: simulation_engine/runner.py:1-68 -->
```python
"""
The engine's single entry point.

    result = run(template_key, assumptions, parameters, components)

Inputs are plain dicts (values as Decimal or numeric strings); the output is plain
JSON-ready data. Django calls this to save a run; the preview endpoint calls it to answer
a slider move; tests call it directly. Same inputs always give the same output.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from . import catalog
from .cases import CASES, apply_shocks
from .disruption import (
    DisruptionInputs,
    peak_hourly_load,
    simulate_checkout,
    simulate_fulfilment,
)
from .idea import IdeaInputs, funnel_check, simulate_months, summarise, timeline
from .money import ONE, ZERO, pct
from .sensitivity import sensitivity

ENGINE_VERSION = "1.0.0"


class EngineError(ValueError):
    """The inputs are valid one by one but the scenario can't be simulated as given."""


@dataclass
class CaseResult:
    case_key: str
    label: str
    metrics: dict
    timeline: list
    assumptions: list[str] = field(default_factory=list)  # the shocks this case applied


@dataclass
class EngineResult:
    engine_version: str
    template_key: str
    cases: list[CaseResult]
    summary: dict
    warnings: list[str]


def run(
    template_key: str,
    assumptions: dict[str, Decimal | str],
    parameters: dict[str, str] | None = None,
    components: list[dict] | None = None,
) -> EngineResult:
    template = catalog.TEMPLATES.get(template_key)
    if template is None:
        raise EngineError(f"Unknown scenario template '{template_key}'.")
    values = {key: catalog.parse_input(key, raw) for key, raw in assumptions.items()}
    missing = catalog.missing_inputs(template_key, set(values))
    if missing:
        raise EngineError(f"Missing assumptions: {', '.join(missing)}.")
    params = catalog.validate_parameters(template_key, parameters)

    if template.kind == "idea_case":
        return _run_idea(template, values, params)
    return _run_disruption(template, values, params, components or [])
```

### Piece 2: running an idea (lines 71–124)

<!-- source: simulation_engine/runner.py:71-124 -->
```python
# --------------------------------------------------------------------------------------
# Idea
# --------------------------------------------------------------------------------------
def _run_idea(template, values, params) -> EngineResult:
    horizon = int(Decimal(params["horizon_months"]))
    step = Decimal(params["sensitivity_step"])
    base = IdeaInputs.from_values(values)

    cases = []
    for case in CASES:
        inputs = apply_shocks(base, case.shocks)
        months = simulate_months(inputs, horizon)
        cases.append(
            CaseResult(
                case_key=case.key,
                label=case.label,
                metrics=summarise(inputs, months),
                timeline=timeline(months),
                assumptions=[shock.describe() for shock in case.shocks],
            )
        )

    expected_months = simulate_months(base, horizon)
    warnings = _idea_warnings(base, expected_months)
    summary = {
        "horizon_months": horizon,
        "sensitivity": sensitivity(base, horizon, step),
        "sensitivity_step_pct": str(step),
        "funnel_check": funnel_check(base, expected_months),
        "case_definitions": {c.case_key: c.assumptions for c in cases},
        "note": "Illustrative model built from your assumptions. Not a forecast.",
    }
    return EngineResult(ENGINE_VERSION, template.key, cases, summary, warnings)


def _idea_warnings(inputs: IdeaInputs, months) -> list[str]:
    warnings = []
    if inputs.conversion_rate == ZERO:
        warnings.append("Conversion is 0 %, so marketing wins no customers at all.")
    if inputs.price_per_order <= inputs.variable_cost_per_order:
        warnings.append(
            "Each order costs at least as much as it earns; more sales make losses bigger."
        )
    if inputs.monthly_retention >= Decimal("100"):
        warnings.append(
            "100 % retention means no customer ever leaves; lifetime value isn't shown."
        )
    check = funnel_check(inputs, months)
    if check and check["gap_pct"]["value"] is not None and Decimal(check["gap_pct"]["value"]) > 25:
        warnings.append(
            "Your expected orders are more than 25 % above what your marketing budget and "
            "conversion support. Either the estimate or the funnel inputs need another look."
        )
    return warnings
```

### Piece 3: running an outage (lines 127–247)

<!-- source: simulation_engine/runner.py:127-247 -->
```python
# --------------------------------------------------------------------------------------
# Disruptions
# --------------------------------------------------------------------------------------
def _run_disruption(template, values, params, components) -> EngineResult:
    def dec(key: str) -> Decimal:
        return Decimal(params[key])

    inputs = DisruptionInputs(
        daily_orders=values["daily_orders"],
        average_order_value=values["average_order_value"],
        contribution_margin=values["contribution_margin"],
        affected_share=values[template.share_input],
        hourly_capacity=values.get("hourly_capacity", ZERO),
        recapture_rate=values.get("recapture_rate", ZERO),
        cancel_rate_per_delay_hour=values.get("cancel_rate_per_delay_hour", ZERO),
        max_cancel_rate=values.get("max_cancel_rate", ZERO),
        outage_hours=dec("outage_hours"),
        start_hour=int(dec("start_hour")),
        horizon_hours=int(dec("horizon_hours")),
        demand_profile=params["demand_profile"],
        backup_switch_hours=dec("backup_switch_hours"),
        backup_capacity_per_hour=dec("backup_capacity_per_hour"),
        backup_extra_cost_per_order=dec("backup_extra_cost_per_order"),
        backup_activation_cost=dec("backup_activation_cost"),
        retry_success_rate=dec("retry_success_rate"),
        retry_window_hours=dec("retry_window_hours"),
        retry_cost_per_order=dec("retry_cost_per_order"),
    )
    simulate = simulate_checkout if template.loss_mode == "checkout" else simulate_fulfilment
    failed_node, graph_warning = _failed_node(template.component_kind, components)

    cases = []
    for key, label in template.strategies:
        outcome = simulate(inputs, key)
        _add_component_health(outcome["timeline"], failed_node, components, inputs)
        cases.append(CaseResult(key, label, outcome["metrics"], outcome["timeline"]))

    warnings = _disruption_warnings(template, inputs)
    if graph_warning:
        warnings.append(graph_warning)
    summary = {
        "loss_mode": template.loss_mode,
        "failed_component": failed_node,
        "comparison": _compare(cases),
        "note": (
            "Affected orders are not lost orders, and lost revenue is not lost profit. "
            "Total impact = contribution lost + cost of the response."
        ),
    }
    return EngineResult(ENGINE_VERSION, template.key, cases, summary, warnings)


def _failed_node(kind: str, components: list[dict]) -> tuple[str, str | None]:
    for component in components:
        if component.get("kind") == kind:
            return component["key"], None
    return kind, f"No '{kind}' component is set up for this business; showing a generic node."


def _add_component_health(rows, failed_key, components, inputs) -> None:
    """
    Health per component per hour, 0 (down) to 1 (normal). One hop only: a direct
    dependent loses the share of its traffic that passes through the broken component.
    """
    share = pct(inputs.affected_share)
    dependents = [c["key"] for c in components if failed_key in c.get("depends_on", [])]
    for row in rows:
        health = Decimal(str(row["health"]))
        row["components"] = {failed_key: float(health)}
        for key in dependents:
            row["components"][key] = float(round(ONE - share * (ONE - health), 2))


def _compare(cases: list[CaseResult]) -> dict:
    """Side-by-side facts. It names the extremes but doesn't declare a 'winner'."""

    def value(case, key):
        raw = case.metrics[key]["value"]
        return Decimal(raw) if raw is not None else None

    rows = [
        {
            "case_key": c.case_key,
            "label": c.label,
            "total_impact": c.metrics["total_impact"]["value"],
            "mitigation_cost": c.metrics["mitigation_cost"]["value"],
            "time_to_recovery": c.metrics["time_to_recovery"]["value"],
            "lost_orders": c.metrics["lost_orders"]["value"],
        }
        for c in cases
    ]
    timed = [c for c in cases if value(c, "time_to_recovery") is not None]
    return {
        "rows": rows,
        "lowest_total_impact": min(cases, key=lambda c: value(c, "total_impact")).case_key,
        "lowest_response_cost": min(cases, key=lambda c: value(c, "mitigation_cost")).case_key,
        "fastest_recovery": (
            min(timed, key=lambda c: value(c, "time_to_recovery")).case_key if timed else None
        ),
    }


def _disruption_warnings(template, inputs: DisruptionInputs) -> list[str]:
    warnings = []
    if inputs.demand_profile == "ecommerce_curve":
        warnings.append("Hourly demand uses an illustrative e-commerce day shape, not your data.")
    if inputs.outage_hours == ZERO:
        warnings.append("Outage duration is 0 hours, so nothing is affected.")
    if inputs.affected_share == ZERO:
        warnings.append("None of your orders go through this component, so nothing is affected.")
    if inputs.backup_switch_hours >= inputs.outage_hours > ZERO:
        warnings.append(
            "The backup takes longer to switch on than the outage lasts, so it never helps."
        )
    if template.loss_mode == "fulfilment":
        if inputs.hourly_capacity < peak_hourly_load(inputs):
            warnings.append(
                "Normal capacity is below peak demand, so orders queue even without an outage. "
                "Impact is measured against that normal state."
            )
    return warnings
```

## ✅ Check

Run lesson 6.1's Example 2 through the front door:

```bash
python
```

```python
from simulation_engine import runner

shop = {
    "daily_orders": "2400",
    "average_order_value": "600",
    "contribution_margin": "25",
    "primary_gateway_share": "100",
    "recapture_rate": "30",
}
r = runner.run(
    "payment_gateway_outage",
    shop,
    {"outage_hours": "2", "start_hour": "0", "demand_profile": "uniform"},
)
print(r.warnings)
for case in r.cases:
    print(case.case_key, case.metrics["total_impact"]["value"])
```

(Press **Enter** twice after the last line: the empty line tells Python the loop is
finished.)

You should see:

```text
["No 'payment' component is set up for this business; showing a generic node."]
wait 21000.00
backup 20420.00
queue_retry 10050.00
```

`wait` and `queue_retry` match your paper exactly. (`backup` uses the template's
defaults: switch-over after 1 hour, 60 orders an hour, ₹12 extra each, ₹5,000 to switch
on.) The warning is honest: we passed no components. Type `exit()`.

## 🔍 Line by line

### Piece 1

- **Lines 1–9** · Docstring: one entry point; plain data in, plain data out; same
  inputs, same output.
- **Line 11** · `field` lets a dataclass field have a default that's a new list each
  time (`default_factory=list`, the same trap as `default=dict` in lesson 5.6).
- **Lines 14–24** · Everything the runner uses, from the files you wrote.
- **Line 26** · The engine's version. Every saved run records it, so if the maths ever
  changes, old runs say which maths made them.
- **Lines 29–30** · `EngineError`: the numbers are fine one by one, but the scenario
  can't run (for example, a required number is missing).
- **Lines 33–39** · `CaseResult`: one case or strategy: key, label, metrics, timeline,
  and (for idea cases) the shocks it applied.
- **Lines 42–48** · `EngineResult`: the whole answer.
- **Lines 51–56** · `run(...)` and its four inputs. Parameters and components are
  optional.
- **Lines 57–59** · Unknown template? Stop.
- **Line 60** · Check **every** assumption with the catalogue (lesson 5.2). The result is
  clean Decimals. A bad value raises `CatalogError` here.
- **Lines 61–63** · Anything this template needs that's missing? Stop and **name** it.
- **Line 64** · Check the parameters and fill in defaults.
- **Lines 66–68** · Send ideas to `_run_idea`, outages to `_run_disruption`.

### Piece 2

- **Lines 74–77** · The horizon and sensitivity step as numbers (they arrive as text),
  and the founder's inputs.
- **Lines 79–91** · For each of the seven cases: apply its shocks, play the months, and
  keep the metrics, timeline and a description of its shocks.
- **Lines 93–94** · The expected case's months again (without shocks), for the warnings.
- **Lines 95–102** · Results that belong to the whole run: the horizon, the sensitivity
  table, the funnel check, what each case assumed, and a plain note: "Illustrative model
  built from your assumptions. Not a forecast."
- **Line 103** · Package it all.
- **Lines 106–124** · Warnings in plain words, each for a situation where the numbers
  are technically fine but likely a mistake:
  - **108–109** · Conversion 0 %.
  - **110–113** · Each order loses money.
  - **114–117** · 100 % retention.
  - **118–123** · The founder's estimate is more than 25 % above what their own funnel
    supports.

### Piece 3

- **Lines 130–132** · A tiny function **inside** a function: `dec("outage_hours")` is
  short for `Decimal(params["outage_hours"])`.
- **Lines 134–154** · Build `DisruptionInputs` from the assumptions and parameters.
  - **138** · `affected_share` comes from the assumption the template names: for a
    gateway outage, `primary_gateway_share`.
  - **139–142** · `.get(key, ZERO)`: numbers only some modes have default to 0.
- **Line 155** · Pick the model: a function stored in a variable. Python lets you pass
  functions around like any other value.
- **Line 156** · Which component fails (lines 179–183).
- **Lines 158–162** · For each strategy: simulate it, add per-component health to the
  timeline, keep the result.
- **Lines 164–166** · Warnings.
- **Lines 167–175** · The run's summary: loss mode, the failed component, the comparison,
  and the most important sentence of the Resilience Room as a note.
- **Lines 179–183** · Find the business's component of the right kind (e.g. `payment`).
  None set up? Use a generic node and say so in a warning.
- **Lines 186–197** · Health per component per hour, for the 3D view (Part 10). The
  failed component gets the hour's health. Components that **depend on** it directly
  lose the share of their traffic that goes through it. One hop only, as the docstring in
  lesson 6.5 promised.
- **Lines 200–226** · `_compare`: a table with one row per strategy, plus which one has
  the lowest total impact, the lowest response cost and the fastest recovery. `value()`
  turns the text back into a Decimal for comparing. Strategies that never recover in the
  period are left out of "fastest".
- **Lines 229–247** · Outage warnings: the illustrative day shape, a 0-hour outage, a
  part no orders go through, a backup slower than the outage, and capacity below peak
  demand.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `EngineError: Missing assumptions: ...` | Expected when you leave a number out: add it to the dictionary. |
| `CatalogError: daily_orders: must be a number` | A value in the dictionary isn't a number (e.g. `"2,4OO"` with letter O). |
| `KeyError: 'primary_gateway_share'` | Check line 138 uses `template.share_input`. |

## ❓ Quiz

1. Why does every run record `ENGINE_VERSION`?
2. What does `simulate = simulate_checkout if ... else simulate_fulfilment` store in
   `simulate`?
3. Why doesn't the runner choose the best strategy?

---

**Next:** [6.8 · Connect it to Django](08-connect-to-django.md)

<details><summary>Quiz answers</summary>

1. So an old run always says which version of the maths produced it, even after the
   maths changes.
2. A function. Calling `simulate(inputs, key)` then runs whichever one was chosen.
3. "Best" depends on things the numbers don't know (risk, customers, brand). It shows
   the facts; a person decides.

</details>
