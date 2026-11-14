"""
Number guardrail: flag every number in AI text that we didn't give it.

The prompt forbids inventing figures, but a prompt is a request, not a guarantee. So after
every answer we:

  1. collect every number in the data we SENT (metrics, inputs, parameters),
  2. pull every number out of the text we GOT BACK (handling ₹, 1,00,000, 2.5k, 1.2 lakh,
     3 crore, 25 %),
  3. accept a returned number only if it IS a sent number, rounded to the digits the AI
     actually wrote. "₹15k" is fine for 14,700 (two digits written, 14,700 -> 15,000).
     "₹14,550" is not: four digits written, and no sent number rounds to it.

Flagged numbers are stored with the analysis and underlined in the UI as
"not from the simulation". We flag rather than delete: the reader decides.
"""

import re
from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

# Numbers this small are usually counts in prose ("two strategies", "3 options").
SMALL_NUMBER_LIMIT = Decimal("10")

MULTIPLIERS = {
    "k": Decimal("1e3"),
    "thousand": Decimal("1e3"),
    "lakh": Decimal("1e5"),
    "lakhs": Decimal("1e5"),
    "lac": Decimal("1e5"),
    "m": Decimal("1e6"),
    "mn": Decimal("1e6"),
    "million": Decimal("1e6"),
    "cr": Decimal("1e7"),
    "crore": Decimal("1e7"),
    "crores": Decimal("1e7"),
}

NUMBER_PATTERN = re.compile(
    r"""
    (?<![\w.])                     # not glued to a word or another number
    -?\d[\d,]*(?:\.\d+)?           # 1,00,000 or 8514.74 or -2428.8
    (?:\s?(k|thousand|lakhs?|lac|m|mn|million|cr|crores?)\b)?   # optional scale word
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True)
class WrittenNumber:
    literal: str  # exactly as it appears, e.g. "1.2 lakh"
    value: Decimal  # 120000
    significant: int  # how many meaningful digits were written: "1.2" -> 2


def significant_digits(digits: str) -> int:
    """'8514.74' -> 6, '8.5' -> 2, '21000' -> 2 (trailing zeros of a whole number are padding)."""
    digits = digits.lstrip("-")
    if "." in digits:
        return max(1, len(digits.replace(".", "").lstrip("0")))
    return max(1, len(digits.lstrip("0").rstrip("0")))


def numbers_in_text(text: str) -> list[WrittenNumber]:
    found = []
    for match in NUMBER_PATTERN.finditer(text):
        literal = match.group(0).strip()
        digits = re.match(r"-?\d[\d,]*(?:\.\d+)?", literal).group(0).replace(",", "")
        try:
            value = Decimal(digits)
        except InvalidOperation:
            continue
        scale = match.group(1)
        if scale:
            value *= MULTIPLIERS[scale.lower()]
        found.append(WrittenNumber(literal, value, significant_digits(digits)))
    return found


def numbers_in_data(data) -> set[Decimal]:
    """Every number anywhere in a nested dict/list, including numeric strings."""
    values: set[Decimal] = set()

    def walk(node):
        if isinstance(node, dict):
            for item in node.values():
                walk(item)
        elif isinstance(node, list | tuple):
            for item in node:
                walk(item)
        elif isinstance(node, bool):
            return
        elif isinstance(node, int | float | Decimal):
            values.add(Decimal(str(node)))
        elif isinstance(node, str):
            try:
                values.add(Decimal(node.replace(",", "")))
            except InvalidOperation:
                values.update(n.value for n in numbers_in_text(node))

    walk(data)
    return values


def round_to_significant(value: Decimal, digits: int, rounding=ROUND_HALF_UP) -> Decimal:
    """round_to_significant(14700, 2) -> 15000;  (8514.74, 2) -> 8500."""
    if value == 0:
        return value
    quantum = Decimal(1).scaleb(value.adjusted() - digits + 1)
    return value.quantize(quantum, rounding=rounding)


def is_supported(number: WrittenNumber, allowed: set[Decimal]) -> bool:
    if abs(number.value) <= SMALL_NUMBER_LIMIT:
        return True
    for known in allowed:
        # Both rounding ("8.5k" for 8,549) and truncation ("8.5k" for 8,551) are normal
        # ways people shorten a figure; anything else is a different number.
        for rounding in (ROUND_HALF_UP, ROUND_DOWN):
            if round_to_significant(known, number.significant, rounding) == number.value:
                return True
    return False


def flag_unsupported_numbers(answer: dict, sent_data: dict) -> list[dict]:
    """
    Walk every string in the AI answer; return the numbers not backed by `sent_data`.

    Each flag records where it was found, e.g. {"path": "key_findings[1].text",
    "literal": "₹4,000", "value": "4000"}.
    """
    allowed = numbers_in_data(sent_data)
    flags = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, item in node.items():
                walk(item, f"{path}.{key}" if path else key)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")
        elif isinstance(node, str) and not path.endswith("metric_keys"):
            for number in numbers_in_text(node):
                if not is_supported(number, allowed):
                    flags.append(
                        {"path": path, "literal": number.literal, "value": str(number.value)}
                    )

    walk(answer, "")
    return flags
