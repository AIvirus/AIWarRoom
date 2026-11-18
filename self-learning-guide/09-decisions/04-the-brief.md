# 9.4 · The brief

**Time:** 50 minutes · **Before this:** [9.3](03-the-workflow.md).

## Read

The brief is a single Python **dictionary** with everything a reviewer needs:

```text
{
  "decision":          title, status, owner, chosen response, why, sign-off, history
  "business":          name, mode, industry, website, currency
  "run":               which scenario, its parameters, engine version, input fingerprint
  "assumptions":       every input, its value, its unit and its SOURCE (user, illustrative...)
  "outcomes":          the key metrics for every case, side by side, with the chosen one marked
  "warnings":          the engine's notes
  "ai_explanation":    the AI's reading of the run, labelled, with flagged numbers
  "committee":         the four desks, labelled
  "what_this_is_not":  three honest sentences
}
```

Two things use that dictionary:

1. `GET /api/v1/decisions/<id>/report/` sends it as JSON (lesson 9.7).
2. The printable page fills an HTML template with it (lesson 9.6).

Because both call the **same** function, `build_brief`, the page and the API can never
disagree.

### Only stored data

Look for what this file **doesn't** do: it never calls the engine, never calls Gemini,
never works out a total. Numbers come from the run's saved snapshot and results; AI text
comes from saved analyses. If something isn't saved, the brief says so ("No AI reading of
this run") instead of making it up.

## Do

Create `decisions/services/brief.py`.

### Piece 1: settings and `build_brief` (lines 1–61)

<!-- source: decisions/services/brief.py:1-61 -->
```python
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
```

### Piece 2: decision, run, assumptions, outcomes (lines 64–167)

<!-- source: decisions/services/brief.py:64-167 -->
```python
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
```

### Piece 3: the AI parts (lines 170–224)

<!-- source: decisions/services/brief.py:170-224 -->
```python
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
```

## Check

```bash
python manage.py shell -c "from decisions.services.brief import build_brief; print('ok')"
```

`ok`. You'll see a real brief in lesson 9.7, once you can create a decision.

## Line by line

### Piece 1

- **Lines 1–11** · Docstring: stored data only, and one function for both the API and
  the page.
- **Line 13** · `timezone`, for "generated at".
- **Lines 15–17** · `plain` (lesson 6.8), the AI table, and the engine's catalogue (input
  labels and templates).
- **Lines 19–29** · Which metrics to show, per kind of run, in reading order. Outages
  show lost orders and impact; idea runs show revenue, cash and funding.
- **Lines 31–38** · Three honest sentences printed at the end of every brief. Python
  joins strings written next to each other, so each sentence can span two lines.
- **Line 41** · `build_brief(decision)`.
- **Lines 42–43** · The run (maybe `None`) and the business.
- **Lines 44–61** · The dictionary. Each section is built by a small helper below.
  `get_mode_display()` gives the label ("Operating company"), not the stored value.
  `list(run.warnings) if run else []`: the warnings, or an empty list without a run.

### Piece 2

- **Lines 64–68** · `_decision`: if there's a run and a chosen response, find that
  case's **label** ("Queue and retry payments") in the run's results.
- **Lines 69–82** · The decision as plain values. `str(decision.owner)` is the person's
  name; dates become text with `.isoformat()`, so the dictionary turns into JSON easily.
- **Lines 85–87** · `_run`: nothing without a run.
- **Lines 88–89** · The run's template, and its parameters by key, for their labels and
  units.
- **Lines 90–98** · Each parameter from the run's **frozen snapshot**, with a readable
  label and unit. A key the template doesn't know (an old run) still shows, with the key
  as its label.
- **Line 99** · The run's summary, or an empty dictionary.
- **Lines 100–114** · The run's identity (id, scenario, template, engine version, input
  fingerprint) and its summary parts. Line 109 drops the comparison's `rows`, which are
  already in "outcomes". Line 111: at most 5 sensitivity lines.
- **Lines 117–118** · `_assumptions` and its docstring.
- **Lines 119–120** · With a run: the frozen assumptions, and `frozen = True`.
- **Lines 121–126** · Without a run: today's values from the business, and
  `frozen = False`, so the page can warn that they may have changed.
- **Lines 127–137** · One row per assumption, sorted by key, with its label from the
  catalogue, value, unit and **source**.
- **Lines 140–145** · `_outcomes`: nothing without a run or results.
- **Line 146** · Which kind of run (`disruption` or `idea_case`).
- **Lines 147–151** · For each key metric: take a sample from the first case that has it
  (for its label and unit). `next(..., None)` gives the first match, or `None`. Skip
  metrics no case has.
- **Lines 152–162** · A row: the metric's label and unit, and one cell per case.
- **Lines 163–167** · The cases (key and label), the chosen one, and the rows.

### Piece 3

- **Lines 170–178** · `_analysis_block`: what every AI section carries: its **label**,
  model, prompt version, date, flagged numbers and sources. The label is printed on the
  page, every time.
- **Lines 181–188** · `_explanation`: the run's newest OK explanation, or `None`.
- **Lines 189–199** · The label block (`**` copies one dictionary into another), plus the
  explanation's parts. `.get(..., [])` gives an empty list if a part is missing.
- **Lines 202–207** · `_committee`: the business's newest OK committee review, or `None`.
- **Lines 208–224** · The label block, each desk with only the first three concerns,
  actions and pieces of evidence (a brief is short), and the disagreements.

## If it didn't work

| You see | Fix |
|---|---|
| `ImportError: cannot import name 'plain'` | It's in `businesses/services/snapshot.py` (lesson 6.8). |
| `KeyError: 'disruption'` later, in 9.7 | Check the `KEY_METRICS` keys on lines 21 and 25: `"disruption"` and `"idea_case"`. |

## Quiz

1. Why do the API and the page both call `build_brief`?
2. A decision has no run. Where do its assumptions come from, and how does the brief show
   that?
3. Find one line that would recalculate a number. (Trick question.)

---

**Next:** [9.5 · Numbers the Indian way](05-numbers-the-indian-way.md)

<details><summary>Quiz answers</summary>

1. So they can never show different things.
2. From the business's current values, with `frozen: False`; the page then says they may
   have changed since the decision.
3. There isn't one. Every number is read from saved data.

</details>
