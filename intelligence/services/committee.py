"""
The expert committee: four advisory desks in ONE Gemini call (not four), to protect the
free-tier quota. Desks may disagree; the schema has a field for it and no consensus field.
"""

from businesses.services.snapshot import plain
from intelligence.models import AIAnalysis, Alert
from intelligence.schemas import Committee
from simulations.models import SimulationRun

from . import ai_client
from .sources import check_citations

ROLES = {"finance", "operations", "market_competition", "risk"}
KEY_METRICS = {
    "total_impact", "lost_contribution", "mitigation_cost", "time_to_recovery", "lost_orders",
    "ending_cash", "funding_gap", "first_profitable_month", "ltv_to_cac", "cac",
}  # fmt: skip


def committee_payload(business) -> dict:
    runs = (
        SimulationRun.objects.filter(business=business, status=SimulationRun.Status.COMPLETED)
        .prefetch_related("results")
        .select_related("scenario")[:3]
    )

    profile = (
        AIAnalysis.objects.filter(
            business=business, kind=AIAnalysis.Kind.SITE_PROFILE, status=AIAnalysis.Status.OK
        )
        .select_related("scan")
        .first()
    )
    allowed_urls = sorted(
        {page["url"] for page in (profile.scan.pages if profile and profile.scan else [])}
        | {source["url"] for source in (profile.sources if profile else [])}
    )
    assumptions = {
        a.key: {"value": plain(a.value), "unit": a.unit, "source": a.source}
        for a in business.assumptions.all()
    }
    return {
        "business": {"name": business.name, "mode": business.mode, "industry": business.industry},
        "assumptions": assumptions,
        "recent_runs": [
            {
                "scenario": run.scenario.name,
                "template": run.scenario.template.name,
                "parameters": run.input_snapshot.get("parameters", {}),
                "results": {
                    result.case_key: {
                        key: item for key, item in result.metrics.items() if key in KEY_METRICS
                    }
                    for result in run.results.all()
                },
                "warnings": run.warnings,
            }
            for run in runs
        ],
        "site_profile": profile.output if profile else None,
        "recent_alerts": [
            alert.summary
            for alert in Alert.objects.filter(business=business, acknowledged_at__isnull=True)[:5]
        ],
        "allowed_source_urls": allowed_urls,
    }


def convene(business, transport=None) -> AIAnalysis:
    payload = committee_payload(business)
    if not payload["recent_runs"] and not payload["site_profile"]:
        raise ai_client.AIUnavailable(
            "The committee needs something to review: run a scenario or scan the website first."
        )

    def one_of_each_desk_and_real_citations(answer: Committee, sources) -> None:
        roles = [advisor.role for advisor in answer.advisors]
        if set(roles) != ROLES or len(roles) != len(ROLES):
            raise ValueError(f"Need exactly one advisor per desk {sorted(ROLES)}; got {roles}.")
        allowed = set(payload["allowed_source_urls"]) | {s["url"] for s in sources}
        check_citations(answer.sourced_items(), allowed)

    return ai_client.generate(
        business=business,
        kind=AIAnalysis.Kind.COMMITTEE,
        task="committee",
        payload=payload,
        schema=Committee,
        check=one_of_each_desk_and_real_citations,
        data_tag="business_data",
        transport=transport,
    )
