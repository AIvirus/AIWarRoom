"""
What we send to Gemini about a run: an ALLOWLIST, never "the whole object".

Included: business name and mode, assumptions with their source labels, scenario
parameters, every case's metrics (keyed "case.metric"), the run summary and warnings.
Left out on purpose: the free-text business description (untrusted and usually not
needed), user details, ids, hour-by-hour timelines (large and not needed to explain).
"""

TOP_SENSITIVITY_ROWS = 5


def run_context(run) -> dict:
    snapshot = run.input_snapshot
    metrics = {}
    for result in run.results.all():
        for key, item in result.metrics.items():
            metrics[f"{result.case_key}.{key}"] = {
                "case": result.label,
                "label": item["label"],
                "value": item["value"],
                "unit": item["unit"],
            }

    summary = dict(run.summary)
    if "sensitivity" in summary:
        summary["sensitivity"] = summary["sensitivity"][:TOP_SENSITIVITY_ROWS]
    if "comparison" in summary:
        summary["comparison"] = {k: v for k, v in summary["comparison"].items() if k != "rows"}

    return {
        "business": {
            "name": snapshot["business"]["name"],
            "mode": snapshot["business"]["mode"],
            "currency": snapshot["business"]["currency"],
        },
        "scenario": {
            "name": run.scenario.name,
            "template": run.scenario.template.name,
            "parameters": snapshot["parameters"],
        },
        "assumptions": snapshot["assumptions"],  # each has value, unit and source label
        "metrics": metrics,
        "run_summary": summary,
        "engine_warnings": run.warnings,
        "engine_version": run.engine_version,
    }


def metric_keys(context: dict) -> set[str]:
    return set(context["metrics"])
