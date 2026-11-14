"""
The bridge between Django and the pure engine.

    run_scenario(scenario, user)  -> SimulationRun   (saved, with results)
    preview(business, ...)        -> dict            (nothing saved; for sliders)

Both build the same snapshot and call the same engine function, so a preview and a saved
run with identical inputs always agree.
"""

import logging
from dataclasses import asdict

from django.db import transaction

from businesses.services.snapshot import assumption_values, build_snapshot, snapshot_hash
from simulation_engine import catalog, runner
from simulations.models import SimulationResult, SimulationRun

logger = logging.getLogger(__name__)


class SimulationInputError(Exception):
    """The user needs to fix something (missing or invalid inputs) before running."""

    def __init__(self, message: str, fields: dict | None = None):
        super().__init__(message)
        self.fields = fields or {}


def _execute(snapshot: dict) -> runner.EngineResult:
    try:
        return runner.run(
            snapshot["template_key"],
            assumption_values(snapshot),
            snapshot["parameters"],
            snapshot["components"],
        )
    except catalog.CatalogError as error:
        raise SimulationInputError("Some inputs are invalid.", error.errors) from None


def run_scenario(scenario, user) -> SimulationRun:
    """
    Snapshot -> engine -> save run + one result row per case.

    If the engine refuses the inputs (e.g. missing assumptions) a FAILED run is saved with
    the reason, so the history shows the attempt, and the error is raised to the caller.
    """
    snapshot = build_snapshot(scenario.business, scenario.template_key, scenario.parameters)
    run = SimulationRun(
        scenario=scenario,
        business=scenario.business,
        input_snapshot=snapshot,
        input_hash=snapshot_hash(snapshot),
        engine_version=runner.ENGINE_VERSION,
        created_by=user,
    )
    try:
        result = _execute(snapshot)
    except (runner.EngineError, SimulationInputError) as error:
        run.status = SimulationRun.Status.FAILED
        run.error = str(error)
        run.save()
        raise SimulationInputError(str(error), getattr(error, "fields", {})) from None

    # The run and its results are saved together or not at all. (The failed-run save
    # above deliberately sits outside this block, so the attempt is always recorded.)
    with transaction.atomic():
        run.status = SimulationRun.Status.COMPLETED
        run.summary = result.summary
        run.warnings = result.warnings
        run.save()
        SimulationResult.objects.bulk_create(
            SimulationResult(
                run=run,
                case_key=case.case_key,
                label=case.label,
                metrics=case.metrics,
                timeline=case.timeline,
            )
            for case in result.cases
        )
    logger.info("Simulation run %s completed (%s cases)", run.id, len(result.cases))
    return run


def preview(business, template_key: str, parameters: dict | None, overrides: dict | None) -> dict:
    """Run the engine on unsaved what-if values. Nothing touches the database."""
    try:
        clean_params = catalog.validate_parameters(template_key, parameters)
        clean_overrides = {
            key: str(catalog.parse_input(key, value)) for key, value in (overrides or {}).items()
        }
    except catalog.CatalogError as error:
        raise SimulationInputError("Some inputs are invalid.", error.errors) from None

    snapshot = build_snapshot(business, template_key, clean_params, clean_overrides)
    try:
        result = _execute(snapshot)
    except runner.EngineError as error:
        raise SimulationInputError(str(error)) from None
    return {
        "engine_version": result.engine_version,
        "template_key": result.template_key,
        "input_hash": snapshot_hash(snapshot),
        "summary": result.summary,
        "warnings": result.warnings,
        "cases": [asdict(case) for case in result.cases],
        "saved": False,
    }
