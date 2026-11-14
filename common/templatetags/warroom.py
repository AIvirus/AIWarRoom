"""
Template filters for showing numbers the way an Indian finance team reads them.

    {{ "1234567.5"|indian }}            -> 12,34,568
    {{ "21000.00"|figure:"INR" }}       -> ₹21,000
    {{ "22.5"|figure:"%" }}             -> 22.5 %
    {{ None|figure:"month" }}           -> n/a
    {{ "illustrative"|source_tag }}     -> ILL
"""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()

SOURCE_TAGS = {
    "user": "USR",
    "illustrative": "ILL",
    "derived": "DRV",
    "from_site": "SITE",
    "what_if": "WHAT-IF",
}


def _decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def indian_grouping(number: Decimal, places: int = 0) -> str:
    """12345678 -> '1,23,45,678': last three digits, then groups of two (lakh, crore)."""
    quantum = Decimal(1).scaleb(-places)
    rounded = number.quantize(quantum, rounding=ROUND_HALF_UP)
    sign = "-" if rounded < 0 else ""
    whole, _, fraction = f"{abs(rounded):f}".partition(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    text = ",".join([*groups, tail]) if groups else tail
    return f"{sign}{text}{'.' + fraction if fraction else ''}"


@register.filter
def indian(value, places=0):
    number = _decimal(value)
    return "n/a" if number is None else indian_grouping(number, int(places))


@register.filter
def figure(value, unit=""):
    """Format a metric value with its unit, choosing sensible precision."""
    if value is None or value == "":
        return "n/a"
    number = _decimal(value)
    if number is None:
        return str(value).replace("_", " ")  # a choice such as "ecommerce_curve"
    unit = unit or ""
    whole = number == number.to_integral()
    if unit.startswith("INR"):
        # Paise only where they matter: ₹649.50 yes, ₹640.00 and ₹21,000.40 no.
        places = 0 if whole or abs(number) >= 1000 else 2
        suffix = unit[3:]  # "INR/order" -> "/order"
        sign = "-" if number < 0 else ""  # "-₹2,429", not "₹-2,429"
        return f"{sign}₹{indian_grouping(abs(number), places)}{suffix}"
    if unit == "%":
        return f"{indian_grouping(number, 0 if whole else 1)} %"
    if unit == "ratio":
        return f"{indian_grouping(number, 2)}×"
    if unit == "hour of day":
        return f"{int(number):02d}:00"
    places = 0 if whole or abs(number) >= 100 else 1
    text = indian_grouping(number, places)
    if number == 1 and unit in {"hours", "months", "orders"}:
        unit = unit[:-1]  # "1 hour", not "1 hours"
    return f"{text} {unit}".strip()


@register.filter
def source_tag(source):
    return SOURCE_TAGS.get(source, (source or "").upper())


@register.filter
def when(iso_text):
    """ISO timestamp -> '15 Nov 2026, 19:43 UTC'."""
    if not iso_text:
        return "n/a"
    moment = iso_text if isinstance(iso_text, datetime) else datetime.fromisoformat(str(iso_text))
    return moment.strftime("%d %b %Y, %H:%M UTC")


@register.filter
def humanize_key(value):
    return str(value or "").replace("_", " ")


@register.filter
def get_item(mapping, key):
    return (mapping or {}).get(key)
