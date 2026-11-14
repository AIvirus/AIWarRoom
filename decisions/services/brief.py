"""
The decision brief: everything a reviewer needs on one page, built ONLY from stored data.

Nothing is recalculated here. Numbers come from the run's frozen snapshot and saved
results; AI text comes from saved analyses, keeps its "AI analysis" label and shows any
flagged numbers. If the business has changed since the run, the brief still shows what
the decision was actually based on.

The JSON API (/decisions/<id>/report/) and the printable page both use build_brief(), so
they can never disagree.
"""

from django.utils import timezone

from businesses.services.snapshot import plain
from intelligence.models import AIAnalysis
from simulation_engine import catalog

# The few metrics a reviewer compares across cases, in reading order.
KEY_METRICS = {
    "disruption": [
        "affected_orders", "lost_orders", "lost_revenue", "lost_contribution",
        "mitigation_cost", "total_impact", "time_to_recovery", "hours_without_service",
    ],
    "idea_case": [
        "revenue_total", "operating_result_total", "first_profitable_month", "lowest_cash",
        "funding_gap", "cash_out_month", "ending_cash", "ltv_to_cac",
    ],
}  # fmt: skip

WHAT_THIS_IS_NOT = [
    "Not a forecast. Every figure follows from the assumptions listed here, and those are "
    "only as good as the people who entered them.",
    "Not market research. Competitor and market statements are either quoted from a "
    "fetched web page (with its address) or marked as AI inference.",
    "Not the AI's decision. The AI explains and advises; the decision, its owner and its "
    "sign-off are human.",
]


def build_brief(decision) -> dict:
    run = decision.run
    business = decision.business
    return {
        "generated_at": timezone.now().isoformat(),
        "decision": _decision(decision, run),
        "business": {
            "name": business.name,
            "mode": business.get_mode_display(),
            "industry": business.industry,
            "website_url": business.website_url,
            "currency": business.currency,
        },
        "run": _run(run),
        "assumptions": _assumptions(run, business),
        "outcomes": _outcomes(run, decision.chosen_strategy),
        "warnings": list(run.warnings) if run else [],
        "ai_explanation": _explanation(run),
        "committee": _committee(business),
        "what_this_is_not": WHAT_THIS_IS_NOT,
    }


def _decision(decision, run) -> dict:
    chosen_label = None
    if run and decision.chosen_strategy:
        result = run.results.filter(case_key=decision.chosen_strategy).first()
        chosen_label = result.label if result else None
    return {
        "id": str(decision.id),
        "title": decision.title,
        "status": decision.status,
        "status_label": decision.get_status_display(),
        "owner": str(decision.owner) if decision.owner else None,
        "chosen_strategy": decision.chosen_strategy or None,
        "chosen_label": chosen_label,
        "rationale": decision.rationale,
        "decided_by": str(decision.decided_by) if decision.decided_by else None,
        "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
        "created_at": decision.created_at.isoformat(),
        "history": decision.history,
    }


def _run(run) -> dict | None:
    if run is None:
        return None
    template = catalog.TEMPLATES[run.scenario.template_key]
    specs = {p.key: p for p in template.parameters}
    parameters = [
        {
            "key": key,
            "label": specs[key].label if key in specs else key,
            "value": value,
            "unit": specs[key].unit if key in specs else "",
        }
        for key, value in run.input_snapshot.get("parameters", {}).items()
    ]
    summary = run.summary or {}
    return {
        "id": str(run.id),
        "scenario": run.scenario.name,
        "template": template.name,
        "kind": template.kind,
        "created_at": run.created_at.isoformat(),
        "engine_version": run.engine_version,
        "input_hash": run.input_hash,
        "parameters": parameters,
        "comparison": {k: v for k, v in summary.get("comparison", {}).items() if k != "rows"},
        "funnel_check": summary.get("funnel_check"),
        "sensitivity": (summary.get("sensitivity") or [])[:5],
        "case_definitions": summary.get("case_definitions", {}),
        "note": summary.get("note"),
    }


def _assumptions(run, business) -> dict:
    """From the run's frozen snapshot when there is a run; otherwise today's values."""
    if run is not None:
        items, frozen = run.input_snapshot.get("assumptions", {}), True
    else:
        items = {
            a.key: {"value": plain(a.value), "unit": a.unit, "source": a.source}
            for a in business.assumptions.all()
        }
        frozen = False
    rows = [
        {
            "key": key,
            "label": catalog.INPUTS[key].label if key in catalog.INPUTS else key,
            "value": item["value"],
            "unit": item["unit"],
            "source": item["source"],
        }
        for key, item in sorted(items.items())
    ]
    return {"frozen": frozen, "rows": rows}


def _outcomes(run, chosen: str) -> dict | None:
    if run is None:
        return None
    results = list(run.results.all())
    if not results:
        return None
    kind = catalog.TEMPLATES[run.scenario.template_key].kind
    rows = []
    for key in KEY_METRICS[kind]:
        sample = next((r.metrics[key] for r in results if key in r.metrics), None)
        if sample is None:
            continue
        rows.append(
            {
                "key": key,
                "label": sample["label"],
                "unit": sample["unit"],
                "cells": [
                    {"case": r.case_key, "value": r.metrics.get(key, {}).get("value")}
                    for r in results
                ],
            }
        )
    return {
        "cases": [{"key": r.case_key, "label": r.label} for r in results],
        "chosen": chosen or None,
        "rows": rows,
    }


def _analysis_block(analysis: AIAnalysis) -> dict:
    return {
        "label": "AI analysis. Advisory only; check flagged numbers against the simulation.",
        "model": analysis.model_name,
        "prompt_version": analysis.prompt_version,
        "created_at": analysis.created_at.isoformat(),
        "flagged_numbers": analysis.flagged_numbers,
        "sources": analysis.sources,
    }


def _explanation(run) -> dict | None:
    if run is None:
        return None
    analysis = run.analyses.filter(
        kind=AIAnalysis.Kind.RUN_EXPLANATION, status=AIAnalysis.Status.OK
    ).first()
    if analysis is None:
        return None
    output = analysis.output
    return {
        **_analysis_block(analysis),
        "headline": output.get("headline"),
        "what_happened": output.get("what_happened"),
        "trade_offs": output.get("trade_offs", []),
        "risks": output.get("risks", []),
        "recommendations": output.get("recommendations", []),
        "assumptions_to_check": output.get("assumptions_to_check", []),
        "limitations": output.get("limitations", []),
    }


def _committee(business) -> dict | None:
    analysis = business.analyses.filter(
        kind=AIAnalysis.Kind.COMMITTEE, status=AIAnalysis.Status.OK
    ).first()
    if analysis is None:
        return None
    output = analysis.output
    return {
        **_analysis_block(analysis),
        "advisors": [
            {
                "role": a["role"],
                "desk_name": a["desk_name"],
                "verdict": a["verdict"],
                "headline": a["headline"],
                "key_concerns": a["key_concerns"][:3],
                "recommended_actions": a["recommended_actions"][:3],
                "evidence": a.get("evidence", [])[:3],
            }
            for a in output.get("advisors", [])
        ],
        "points_of_disagreement": output.get("points_of_disagreement", []),
    }
