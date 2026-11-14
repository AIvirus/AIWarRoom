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
