"""
The exact shapes we accept from Gemini.

Gemini is asked to answer in JSON matching these models, and every answer is validated
here before anyone sees it. Anything that doesn't fit (wrong type, missing field, a metric
key we never sent) counts as a failed answer, not as "close enough".
"""

from typing import Literal

from pydantic import BaseModel, Field


class Finding(BaseModel):
    text: str = Field(max_length=400)
    # Which numbers support this finding, e.g. ["wait.total_impact", "backup.total_impact"].
    metric_keys: list[str] = Field(default_factory=list, max_length=6)


class Recommendation(BaseModel):
    action: str = Field(max_length=200)
    rationale: str = Field(max_length=500)
    metric_keys: list[str] = Field(default_factory=list, max_length=6)
    confidence: Literal["low", "medium", "high"]


class RunExplanation(BaseModel):
    """Gemini's reading of one simulation run."""

    headline: str = Field(max_length=200)
    what_happened: str = Field(max_length=1200)
    key_findings: list[Finding] = Field(min_length=1, max_length=5)
    trade_offs: list[str] = Field(default_factory=list, max_length=5)
    risks: list[str] = Field(default_factory=list, max_length=5)
    opportunities: list[str] = Field(default_factory=list, max_length=5)
    recommendations: list[Recommendation] = Field(min_length=1, max_length=4)
    assumptions_to_check: list[str] = Field(default_factory=list, max_length=5)
    limitations: list[str] = Field(min_length=1, max_length=5)
    next_scenarios: list[str] = Field(default_factory=list, max_length=4)

    def cited_metric_keys(self) -> set[str]:
        keys = {k for f in self.key_findings for k in f.metric_keys}
        return keys | {k for r in self.recommendations for k in r.metric_keys}


# --------------------------------------------------------------------------------------
# Company site profile
# --------------------------------------------------------------------------------------
# Where a claim comes from. "site" and "cited" need a URL we actually have; "inference"
# must NOT carry one, so a guess can never dress itself up as a sourced fact.
Basis = Literal["site", "cited", "inference"]


class Dependency(BaseModel):
    name: str = Field(max_length=80)
    kind: Literal["payment", "logistics", "platform", "supplier", "marketplace", "other"]
    basis: Basis
    source_url: str | None = None


class Competitor(BaseModel):
    name: str = Field(max_length=80)
    reason: str = Field(max_length=300)
    basis: Basis
    source_url: str | None = None


class FutureScenario(BaseModel):
    title: str = Field(max_length=120)
    description: str = Field(max_length=400)
    suggested_template: Literal[
        "payment_gateway_outage", "warehouse_shutdown", "logistics_failure", "none"
    ]


class SiteProfile(BaseModel):
    summary: str = Field(max_length=800)
    offerings: list[str] = Field(default_factory=list, max_length=8)
    customer_segments: list[str] = Field(default_factory=list, max_length=5)
    price_positioning: str = Field(max_length=300)
    dependencies: list[Dependency] = Field(default_factory=list, max_length=10)
    competitors: list[Competitor] = Field(default_factory=list, max_length=6)
    weaknesses: list[str] = Field(default_factory=list, max_length=6)
    future_scenarios: list[FutureScenario] = Field(default_factory=list, max_length=4)
    limitations: list[str] = Field(min_length=1, max_length=5)

    def sourced_items(self):
        return [*self.dependencies, *self.competitors]


# --------------------------------------------------------------------------------------
# Expert committee: four desks, one call, disagreement allowed
# --------------------------------------------------------------------------------------
class Evidence(BaseModel):
    text: str = Field(max_length=300)
    basis: Literal["simulation", "site", "cited", "inference"]
    source_url: str | None = None


class Advisor(BaseModel):
    role: Literal["finance", "operations", "market_competition", "risk"]
    desk_name: str = Field(max_length=60)
    verdict: Literal["proceed", "proceed_with_conditions", "hold", "reconsider"]
    headline: str = Field(max_length=200)
    key_concerns: list[str] = Field(min_length=1, max_length=5)
    drawbacks: list[str] = Field(default_factory=list, max_length=5)
    scenarios_to_watch: list[str] = Field(default_factory=list, max_length=4)
    recommended_actions: list[str] = Field(min_length=1, max_length=5)
    evidence: list[Evidence] = Field(default_factory=list, max_length=6)


class Committee(BaseModel):
    advisors: list[Advisor] = Field(min_length=4, max_length=4)
    # Where the desks disagree. Part of the output on purpose: no forced consensus.
    points_of_disagreement: list[str] = Field(default_factory=list, max_length=5)
    shared_limitations: list[str] = Field(min_length=1, max_length=4)

    def sourced_items(self):
        return [e for advisor in self.advisors for e in advisor.evidence]
