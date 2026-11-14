"""
Small Decimal helpers shared by every model.

Why Decimal and not float? 0.1 + 0.2 == 0.30000000000000004 in float. For money that
error compounds month after month; Decimal does arithmetic the way an accountant does.
"""

from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")
CENT = Decimal("0.01")


def pct(value: Decimal) -> Decimal:
    """22.5 (as people write a percentage) -> 0.225 (as a fraction used in maths)."""
    return value / HUNDRED


def round2(value: Decimal) -> Decimal:
    """Round half-up to 2 places: the rounding people expect on an invoice."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return max(low, min(high, value))


def metric(label: str, value: Decimal | int | None, unit: str) -> dict:
    """
    One output number in the shape every layer (API, UI, AI context) uses.

    Values are strings so they survive JSON exactly. None means "not applicable", for
    example a break-even month that never arrives inside the horizon.
    """
    if value is None:
        text = None
    elif isinstance(value, int):
        text = str(value)
    else:
        text = str(round2(value))
    return {"label": label, "value": text, "unit": unit}


def display(value: Decimal) -> float:
    """Timelines are for drawing, not accounting: a rounded float keeps them small."""
    return float(round2(value))
