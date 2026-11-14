"""Ask Gemini to explain one simulation run."""

from intelligence.models import AIAnalysis
from intelligence.schemas import RunExplanation

from . import ai_client
from .context import metric_keys, run_context


def explain_run(run, transport=None) -> AIAnalysis:
    if run.status != run.Status.COMPLETED:
        raise ai_client.AIUnavailable("Only completed runs can be explained.")

    context = run_context(run)
    allowed = metric_keys(context)

    def only_known_metric_keys(answer: RunExplanation) -> None:
        # A cited key we never sent means the model is pointing at a number that doesn't
        # exist. Treat it as an invalid answer, which triggers the one repair attempt.
        unknown = answer.cited_metric_keys() - allowed
        if unknown:
            raise ValueError(
                f"Cited metric keys that are not in the data: {sorted(unknown)}. "
                "Use only keys from simulation_data.metrics."
            )

    return ai_client.generate(
        business=run.business,
        kind=AIAnalysis.Kind.RUN_EXPLANATION,
        task="run_explanation",
        payload=context,
        schema=RunExplanation,
        run=run,
        check=only_known_metric_keys,
        transport=transport,
    )
