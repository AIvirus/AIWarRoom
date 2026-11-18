# 7.5 · The number guardrail

**Time:** 45 minutes · **Before this:** [7.4](04-schemas-and-the-prompt.md).

## Read

The prompt says "do not invent numbers". A prompt is a request, not a guarantee. So after
every answer, a small piece of plain Python checks **every number** the AI wrote.

### The idea in three steps

1. Collect every number in the data we **sent** (metrics, assumptions, parameters).
2. Find every number in the text we **got back**, however it's written: `₹21,000`,
   `₹1,00,000`, `8.5k`, `1.2 lakh`, `3 crore`, `25 %`.
3. Accept a number only if it **is** a sent number, rounded to the digits the AI actually
   wrote.

### "Rounded to the digits it wrote"

The engine says the backup costs **14,700**. The AI writes:

| AI wrote | Meaningful digits | 14,700 rounded to that many digits | Verdict |
|---|---|---|---|
| `₹15k` | 2 (`1`, `5`) | 15,000 | fair rounding |
| `₹14k` | 2 | 14,000 (rounded down) | fair shortening |
| `₹14,700` | 3 (`1`, `4`, `7`; trailing zeros are padding) | 14,700 | exact |
| `₹14,550` | 4 | 14,700 → no match with any sent number | flagged |
| `₹13,000` | 2 | 15,000 or 14,000 → no match | flagged |

So a writer may round, but can't drift. And a number the AI **calculated itself** (a
difference, a percentage) is flagged too, because we never sent it. That's on purpose:
its calculation might be wrong, and the reader should know it's not from the engine.

### Small counts are fine

"Compare the **3** strategies over **2** days" isn't a claim about money. Numbers of 10
or less are allowed, so the flags aren't full of noise.

### Flag, don't delete

A flagged number stays in the text, underlined in the UI as "not from the simulation".
Deleting it would change what the AI said and hide the problem. The reader decides.

### Regular expressions

To find numbers in text we use a **regular expression** (regex): a small pattern
language for searching text. You met one in lesson 5.7 (`csrftoken=...`). Here are the
pieces this one uses:

| Piece | Means |
|---|---|
| `\d` | one digit |
| `[\d,]*` | any number of digits or commas |
| `(?:\.\d+)?` | optionally, a dot and some digits |
| `\s?` | optionally, one space |
| `(k\|lakh\|crore)` | one of these words |
| `(?<![\w.])` | "not straight after a letter, digit or dot" (so `B2B` isn't a number) |
| `\b` | the edge of a word (so the `m` in `months` isn't "million") |

## Do

Create `intelligence/services/__init__.py` (empty), then
`intelligence/services/guardrails.py` in three pieces.

### Piece 1: rules and the pattern (lines 1–46)

<!-- source: intelligence/services/guardrails.py:1-46 -->
```python
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
```

### Piece 2: reading and comparing numbers (lines 49–122)

<!-- source: intelligence/services/guardrails.py:49-122 -->
```python
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
```

### Piece 3: checking a whole answer (lines 125–150)

<!-- source: intelligence/services/guardrails.py:125-150 -->
```python
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
```

## Check

```bash
python
```

```python
from intelligence.services.guardrails import flag_unsupported_numbers

sent = {"wait.total_impact": "21000.00", "backup.cost": "14700"}
flag_unsupported_numbers(
    {"text": "Waiting loses ₹21,000. Backup about ₹15k. Retrying saves ₹14,550."}, sent
)
```

You get exactly one flag:

```text
[{'path': 'text', 'literal': '14,550', 'value': '14550'}]
```

`₹21,000` is exact and `₹15k` is fair rounding; `₹14,550` isn't a number we sent. Type
`exit()`.

## Line by line

### Piece 1

- **Lines 1–16** · Docstring: the three steps and the "flag, don't delete" rule.
- **Lines 18–20** · `re` for regular expressions; `Decimal` with two rounding modes.
- **Lines 22–23** · Numbers of 10 or less are treated as counts.
- **Lines 25–37** · Scale words and what they multiply by. `Decimal("1e5")` is 1 × 10⁵ =
  1,00,000 (a lakh); `1e7` is a crore.
- **Lines 39–46** · The number pattern, compiled once. `re.VERBOSE` lets the pattern be
  spread over lines with `#` comments; `re.IGNORECASE` matches `Lakh` and `LAKH` too.
  - **41** · Not glued to a word or another number.
  - **42** · An optional minus, a digit, more digits or commas, an optional decimal part.
  - **43** · An optional space and scale word. The round brackets **capture** the word
    so the code can read it (`match.group(1)`).

### Piece 2

- **Lines 49–53** · `WrittenNumber`: the text as written, its value, and how many
  meaningful digits were written.
- **Lines 56–61** · `significant_digits`: count the digits that carry meaning.
  - **58** · Ignore a minus sign.
  - **59–60** · With a decimal point, every digit counts except leading zeros:
    `0.25` → 2.
  - **61** · A whole number's leading **and trailing** zeros are padding: `21000` → 2.
    `max(1, ...)` makes `0` count as 1 digit.
- **Line 64** · `numbers_in_text`: every number in a piece of text.
- **Line 66** · `finditer` gives each match in turn.
- **Line 67** · The matched text, e.g. `"1.2 lakh"`.
- **Line 68** · Just the digits part, without commas: `"1.2"`.
- **Lines 69–72** · Make a Decimal; skip anything odd.
- **Lines 73–75** · Multiply by the scale word, if there was one.
- **Line 76** · Keep it.
- **Line 80** · `numbers_in_data`: every number anywhere inside the data we sent.
- **Line 84** · A function **inside** a function, which calls **itself**: that's
  **recursion**. It's the easy way to walk into dictionaries inside lists inside
  dictionaries, however deep.
- **Lines 85–90** · A dictionary or list: walk into each item. `list | tuple` in
  `isinstance` means "a list or a tuple".
- **Lines 91–92** · `True`/`False` are skipped. (In Python, `True` is secretly the
  number 1, so this check must come **before** the number check.)
- **Lines 93–94** · A number: add it.
- **Lines 95–99** · Text: if the whole text is a number (`"21000.00"`), add it;
  otherwise look for numbers inside it (`"horizon 24 months"` → 24).
- **Lines 101–102** · Start the walk, return the set.
- **Lines 105–110** · `round_to_significant(14700, 2)` → 15000.
  `value.adjusted()` is the position of the first digit (4 for 14,700, meaning 10⁴);
  `scaleb` builds the step to round to (10³ here); `quantize` rounds to that step.
- **Line 113** · `is_supported`: is this written number backed by the data?
- **Lines 114–115** · Small counts are always fine.
- **Lines 116–121** · Try every sent number, rounded half-up **and** rounded down
  (truncated) to the digits written. Any match = supported.
- **Line 122** · No match: not supported.

### Piece 3

- **Line 125** · `flag_unsupported_numbers(answer, sent_data)`: the function the AI
  client calls.
- **Lines 126–131** · Docstring, with an example flag.
- **Line 132** · All the numbers we sent.
- **Line 135** · Another recursive walk, this time keeping track of **where** we are, as
  a path like `key_findings[1].text`.
- **Lines 136–141** · Into dictionaries (adding `.key`) and lists (adding `[index]`).
  `enumerate` gives each item with its position.
- **Line 142** · Check text, but **not** the metric keys themselves
  (`"wait.total_impact"` is a name, not a claim).
- **Lines 143–147** · Every unsupported number becomes a flag with its path, how it was
  written, and its value.
- **Lines 149–150** · Walk the answer and return the flags.

## If it didn't work

| You see | Fix |
|---|---|
| `re.error: ...` when importing | A bracket in the pattern (lines 40–44) is missing. Compare character by character. |
| `₹15k` is flagged | Check lines 59–61 (trailing zeros) and that line 119 tries both roundings. |
| `RecursionError` | `walk` must call itself on the **items**, not on `node` again. |

## Quiz

1. The engine's number is 8,514.74. Which are accepted: "₹8.5k", "₹8,515", "₹8,600"?
2. Why is `True` checked before numbers?
3. Why flag a number instead of deleting it?

---

**Next:** [7.6 · The AI client, part 1](06-ai-client-part-1.md)

<details><summary>Quiz answers</summary>

1. "₹8.5k" (8,500, two digits) and "₹8,515" (four digits, rounded half-up) are accepted.
   "₹8,600" is flagged: two digits written, and 8,514.74 to two digits is 8,500 whether
   you round or cut, never 8,600.
2. In Python `True` counts as the number 1, so it would wrongly add 1 to the sent
   numbers.
3. So the reader sees exactly what the AI said, and knows which part to doubt.

</details>
