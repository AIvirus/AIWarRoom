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
