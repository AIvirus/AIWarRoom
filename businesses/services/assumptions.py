"""Saving assumptions from a form or a slider, validated by the engine's catalogue."""

from django.db import transaction

from businesses.models import FinancialAssumption
from simulation_engine import catalog


@transaction.atomic
def save_assumptions(business, values: dict[str, tuple[object, str]]) -> None:
    """
    values = {key: (value or None, source)}.  A blank value removes that assumption.
    Every value is checked by catalog.parse_input, the same rule the API and engine use.
    """
    for key, (raw, source) in values.items():
        if raw is None or raw == "":
            FinancialAssumption.objects.filter(business=business, key=key).delete()
            continue
        FinancialAssumption.objects.update_or_create(
            business=business,
            key=key,
            defaults={"value": catalog.parse_input(key, raw), "source": source},
        )
