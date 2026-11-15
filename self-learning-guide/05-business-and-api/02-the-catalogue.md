# 5.2 · The catalogue

**Time:** 45 minutes · **Before this:** [5.1](01-what-we-build.md).

## 📖 Read

The catalogue is a **list of every number the app understands**, with its unit and its
allowed range. It answers questions like:

- Is `conversion_rate` a real assumption? *Yes, a percentage from 0 to 100.*
- Is `"1,250.50"` a valid order value? *Yes: it means 1250.50 rupees.*
- What settings does a "warehouse shutdown" scenario have, and what are the defaults?

It lives in a new folder, `simulation_engine/`, which is **plain Python, not a Django
app**. Part 6 puts the maths in the same folder. Keeping it free of Django means it can be
tested in a split second, and the rules can't get mixed up with database details.

Two Python tools you haven't used yet:

- **`@dataclass`** writes the boring parts of a class for you. You list the fields, and
  Python makes `__init__` (and a nice printout) automatically. `frozen=True` means an
  object can't be changed after it is made, so nobody can accidentally edit a rule.
- **`**PERCENT`** "unpacks" a dictionary into keyword arguments.
  `Field("x", "X", **PERCENT)` is the same as
  `Field("x", "X", unit="%", minimum=D("0"), maximum=D("100"))`.

## ⌨️ Do

In `my-warroom`, make the folder and its empty package files:

```bash
mkdir -p simulation_engine/tests
```

Then create two **empty** files: `simulation_engine/__init__.py` and
`simulation_engine/tests/__init__.py` (in VS Code: right-click the folder → New File).
An `__init__.py` file tells Python "this folder is a package you can import from".

Now create `simulation_engine/catalog.py`. It is long (410 lines), so we go through it in
four pieces. Type each piece in order, into the same file. Leave empty lines between the
pieces (one after piece 1, two after pieces 2 and 3); `ruff format` in lesson 5.8 fixes
the spacing if you get it slightly wrong.

### Piece 1: the basic building blocks (lines 1–67)

<!-- source: simulation_engine/catalog.py:1-67 -->
```python
"""
The catalogue of everything a simulation can be fed.

INPUTS     - business assumptions (price, conversion, daily orders...), with units and bounds.
TEMPLATES  - scenario types (the idea case set, three disruptions) and their parameters.

Django stores assumptions and scenario parameters; this module decides what a valid
value is. Keeping the rules here (plain Python, no Django) means the engine, the API and
the tests all agree on one definition, and a typo like "convertion_rate" is rejected
instead of silently becoming a new input nobody reads.

Percentages are written as people say them: 2.5 means 2.5 %, not 0.025.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

IDEA = "idea"
OPERATING = "operating"


class CatalogError(ValueError):
    """Raised with a {field: message} dict so the API can point at the exact field."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{key}: {msg}" for key, msg in errors.items()))
        self.errors = errors


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    unit: str
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    default: str | None = None  # stored as text so Decimals survive JSON exactly
    choices: tuple[str, ...] = ()
    help: str = ""
    modes: tuple[str, ...] = (IDEA, OPERATING)

    def parse(self, raw) -> Decimal | str:
        """Turn user input into a checked value, or raise ValueError with a readable reason."""
        if self.choices:
            value = str(raw).strip()
            if value not in self.choices:
                raise ValueError(f"must be one of: {', '.join(self.choices)}")
            return value
        try:
            # str() first: Decimal(0.1) would carry binary-float noise, Decimal("0.1") does not.
            value = Decimal(str(raw).strip().replace(",", ""))
        except (InvalidOperation, AttributeError):
            raise ValueError("must be a number") from None
        if not value.is_finite():
            raise ValueError("must be a finite number")
        if self.minimum is not None and value < self.minimum:
            raise ValueError(f"must be at least {self.minimum} {self.unit}".rstrip())
        if self.maximum is not None and value > self.maximum:
            raise ValueError(f"must be at most {self.maximum} {self.unit}".rstrip())
        return value


def D(text: str) -> Decimal:  # noqa: N802  - short alias keeps the tables below readable
    return Decimal(text)


PERCENT = dict(unit="%", minimum=D("0"), maximum=D("100"))
```

### Piece 2: the business assumptions (lines 69–195)

<!-- source: simulation_engine/catalog.py:69-195 -->
```python
# --------------------------------------------------------------------------------------
# Business assumptions
# --------------------------------------------------------------------------------------
_INPUT_LIST = [
    # Idea Simulator: unit economics and the acquisition funnel.
    Field(
        "price_per_order",
        "Average order value",
        "INR/order",
        D("0"),
        help="What a customer pays per order, before refunds.",
        modes=(IDEA,),
    ),
    Field(
        "variable_cost_per_order",
        "Variable cost per order",
        "INR/order",
        D("0"),
        help="Goods, packaging, payment fees and delivery for one order.",
        modes=(IDEA,),
    ),
    Field(
        "fixed_costs_monthly",
        "Fixed costs",
        "INR/month",
        D("0"),
        help="Salaries, rent, software: costs that don't move with orders.",
        modes=(IDEA,),
    ),
    Field("marketing_spend_monthly", "Marketing spend", "INR/month", D("0"), modes=(IDEA,)),
    Field(
        "cost_per_visit",
        "Cost per visit",
        "INR/visit",
        D("0"),
        help="Average paid cost to bring one visitor to the store.",
        modes=(IDEA,),
    ),
    Field(
        "conversion_rate",
        "Visit-to-customer conversion",
        **PERCENT,
        help="Share of visitors who become customers.",
        modes=(IDEA,),
    ),
    Field(
        "orders_per_customer_monthly",
        "Orders per customer",
        "orders/customer/month",
        D("0"),
        D("100"),
        modes=(IDEA,),
    ),
    Field(
        "monthly_retention",
        "Monthly customer retention",
        **PERCENT,
        help="Share of last month's customers who order again this month.",
        modes=(IDEA,),
    ),
    Field("initial_investment", "Initial investment", "INR", D("0"), modes=(IDEA,)),
    Field(
        "expected_orders_monthly",
        "Your expected orders",
        "orders/month",
        D("0"),
        help="Your own estimate. The model checks it against what the funnel supports.",
        modes=(IDEA,),
    ),
    # Resilience Room: an operating business and its dependencies.
    Field("daily_orders", "Daily orders", "orders/day", D("0"), modes=(OPERATING,)),
    Field("average_order_value", "Average order value", "INR/order", D("0"), modes=(OPERATING,)),
    Field(
        "contribution_margin",
        "Contribution margin",
        **PERCENT,
        help="What's left of each rupee of revenue after variable costs.",
        modes=(OPERATING,),
    ),
    Field(
        "hourly_capacity",
        "Normal processing capacity",
        "orders/hour",
        D("0"),
        help="Most orders the operation can process in an hour; spare capacity clears backlogs.",
        modes=(OPERATING,),
    ),
    Field("primary_gateway_share", "Payments via primary gateway", **PERCENT, modes=(OPERATING,)),
    Field(
        "main_warehouse_share", "Orders fulfilled by main warehouse", **PERCENT, modes=(OPERATING,)
    ),
    Field(
        "logistics_partner_share", "Orders shipped by main courier", **PERCENT, modes=(OPERATING,)
    ),
    Field(
        "recapture_rate",
        "Customers who retry after a failed checkout",
        **PERCENT,
        modes=(OPERATING,),
    ),
    Field(
        "cancel_rate_per_delay_hour",
        "Cancellations per hour of delay",
        **PERCENT,
        help="Extra share of delayed orders cancelled for each hour they wait.",
        modes=(OPERATING,),
    ),
    Field(
        "max_cancel_rate",
        "Cancellation ceiling",
        **PERCENT,
        help="Delayed orders never cancel beyond this share.",
        modes=(OPERATING,),
    ),
]
INPUTS: dict[str, Field] = {f.key: f for f in _INPUT_LIST}


def parse_input(key: str, raw) -> Decimal:
    """Validate one business assumption. Raises CatalogError naming the field."""
    spec = INPUTS.get(key)
    if spec is None:
        raise CatalogError({key: "is not a known assumption"})
    try:
        return spec.parse(raw)
    except ValueError as error:
        raise CatalogError({key: str(error)}) from None
```

### Piece 3: the scenario templates (lines 198–348)

<!-- source: simulation_engine/catalog.py:198-348 -->
```python
# --------------------------------------------------------------------------------------
# Scenario templates
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Template:
    key: str
    name: str
    kind: str  # "idea_case" | "disruption"
    mode: str  # which business mode it applies to
    description: str
    parameters: tuple[Field, ...] = ()
    required_inputs: tuple[str, ...] = ()
    component_kind: str = ""  # for disruptions: which component fails
    share_input: str = ""  # for disruptions: which assumption says how much traffic it carries
    loss_mode: str = ""  # "checkout" (orders fail now) or "fulfilment" (orders wait)
    strategies: tuple[tuple[str, str], ...] = ()  # (key, label) of response strategies


_DISRUPTION_COMMON = (
    Field("outage_hours", "Outage duration", "hours", D("0"), D("72"), "4"),
    Field("start_hour", "Outage starts at", "hour of day", D("0"), D("23"), "18"),
    Field("horizon_hours", "Simulated period", "hours", D("24"), D("168"), "72"),
    Field(
        "demand_profile",
        "Order pattern",
        "",
        default="ecommerce_curve",
        choices=("uniform", "ecommerce_curve"),
        help="ecommerce_curve is an illustrative day shape with an evening peak.",
    ),
)
_BACKUP = (
    Field("backup_switch_hours", "Time to switch to backup", "hours", D("0"), D("48"), "1"),
    Field("backup_capacity_per_hour", "Backup capacity", "orders/hour", D("0"), default="60"),
    Field("backup_extra_cost_per_order", "Backup extra cost", "INR/order", D("0"), default="12"),
    Field(
        "backup_activation_cost", "Backup one-off activation cost", "INR", D("0"), default="5000"
    ),
)
# Same parameter keys, different meaning per loss mode, so the labels say what they do.
_RETRY_CHECKOUT = (
    Field("retry_success_rate", "Queued payments that succeed on retry", **PERCENT, default="55"),
    Field(
        "retry_window_hours",
        "Retry window",
        "hours",
        D("0"),
        D("72"),
        "24",
        help="Payments older than this are dropped from the queue.",
    ),
    Field("retry_cost_per_order", "Retry cost", "INR/order", D("0"), default="3"),
)
_QUEUE_FULFILMENT = (
    Field(
        "retry_success_rate",
        "Would-be cancellations kept by proactive notice",
        **PERCENT,
        default="55",
        help="Customers told 'your order ships by X' who wait instead of cancelling.",
    ),
    Field(
        "retry_window_hours",
        "Promise window",
        "hours",
        D("0"),
        D("72"),
        "24",
        help="Notice only helps for delays up to this long.",
    ),
    Field("retry_cost_per_order", "Notice and handling cost", "INR/order", D("0"), default="3"),
)
_CHECKOUT_STRATEGIES = (
    ("wait", "Wait for recovery"),
    ("backup", "Switch to backup gateway"),
    ("queue_retry", "Queue and retry payments"),
)
_FULFILMENT_STRATEGIES = (
    ("wait", "Wait and clear the backlog"),
    ("backup", "Switch to backup provider"),
    ("queue_retry", "Queue and notify customers"),
)
_CHECKOUT_CORE = ("daily_orders", "average_order_value", "contribution_margin")
_FULFILMENT_CORE = _CHECKOUT_CORE + ("hourly_capacity",)

_TEMPLATE_LIST = [
    Template(
        key="idea_cases",
        name="Idea stress test",
        kind="idea_case",
        mode=IDEA,
        description="Best, expected and worst cases plus reduced demand, higher costs, lower conversion and more competition, with one-at-a-time sensitivity.",
        parameters=(
            Field("horizon_months", "Horizon", "months", D("6"), D("60"), "24"),
            Field("sensitivity_step", "Sensitivity step", "%", D("1"), D("50"), "10"),
        ),
        required_inputs=(
            "price_per_order",
            "variable_cost_per_order",
            "fixed_costs_monthly",
            "marketing_spend_monthly",
            "cost_per_visit",
            "conversion_rate",
            "orders_per_customer_monthly",
            "monthly_retention",
            "initial_investment",
        ),
    ),
    Template(
        key="payment_gateway_outage",
        name="Payment gateway outage",
        kind="disruption",
        mode=OPERATING,
        description="The primary payment gateway stops authorising payments. Checkouts fail; some customers come back later.",
        parameters=_DISRUPTION_COMMON + _BACKUP + _RETRY_CHECKOUT,
        required_inputs=_CHECKOUT_CORE + ("primary_gateway_share", "recapture_rate"),
        component_kind="payment",
        share_input="primary_gateway_share",
        loss_mode="checkout",
        strategies=_CHECKOUT_STRATEGIES,
    ),
    Template(
        key="warehouse_shutdown",
        name="Warehouse shutdown",
        kind="disruption",
        mode=OPERATING,
        description="The main warehouse stops picking and packing. Orders keep arriving and wait; the longer they wait, the more get cancelled.",
        parameters=_DISRUPTION_COMMON + _BACKUP + _QUEUE_FULFILMENT,
        required_inputs=_FULFILMENT_CORE
        + ("main_warehouse_share", "cancel_rate_per_delay_hour", "max_cancel_rate"),
        component_kind="warehouse",
        share_input="main_warehouse_share",
        loss_mode="fulfilment",
        strategies=_FULFILMENT_STRATEGIES,
    ),
    Template(
        key="logistics_failure",
        name="Courier partner failure",
        kind="disruption",
        mode=OPERATING,
        description="The main courier stops collecting parcels. Packed orders pile up and customers cancel as delays grow.",
        parameters=_DISRUPTION_COMMON + _BACKUP + _QUEUE_FULFILMENT,
        required_inputs=_FULFILMENT_CORE
        + ("logistics_partner_share", "cancel_rate_per_delay_hour", "max_cancel_rate"),
        component_kind="logistics",
        share_input="logistics_partner_share",
        loss_mode="fulfilment",
        strategies=_FULFILMENT_STRATEGIES,
    ),
]
TEMPLATES: dict[str, Template] = {t.key: t for t in _TEMPLATE_LIST}
```

### Piece 4: the helper functions (lines 351–410)

<!-- source: simulation_engine/catalog.py:351-410 -->
```python
def validate_parameters(template_key: str, raw: dict | None) -> dict[str, str]:
    """
    Check scenario parameters against the template and fill in defaults.

    Returns plain strings (e.g. {"outage_hours": "4"}) so the result can be stored in a
    JSON column without float rounding. Raises CatalogError listing every bad field.
    """
    template = TEMPLATES.get(template_key)
    if template is None:
        raise CatalogError({"template_key": "is not a known scenario template"})
    raw = raw or {}
    known = {p.key: p for p in template.parameters}
    errors = {key: "is not a parameter of this scenario" for key in raw if key not in known}
    clean: dict[str, str] = {}
    for key, spec in known.items():
        value = raw.get(key, spec.default)
        if value is None or value == "":
            errors[key] = "is required"
            continue
        try:
            clean[key] = str(spec.parse(value))
        except ValueError as error:
            errors[key] = str(error)
    if errors:
        raise CatalogError(errors)
    return clean


def missing_inputs(template_key: str, available: set[str]) -> list[str]:
    """Assumptions a template needs that the business hasn't provided yet."""
    return [key for key in TEMPLATES[template_key].required_inputs if key not in available]


def describe(field_spec: Field) -> dict:
    """JSON-friendly description, used by the API and the input forms."""
    return {
        "key": field_spec.key,
        "label": field_spec.label,
        "unit": field_spec.unit,
        "minimum": str(field_spec.minimum) if field_spec.minimum is not None else None,
        "maximum": str(field_spec.maximum) if field_spec.maximum is not None else None,
        "default": field_spec.default,
        "choices": list(field_spec.choices),
        "help": field_spec.help,
    }


__all__ = [
    "IDEA",
    "OPERATING",
    "INPUTS",
    "TEMPLATES",
    "CatalogError",
    "Field",
    "Template",
    "parse_input",
    "validate_parameters",
    "missing_inputs",
    "describe",
]
```

### Tell ruff about this file

The tables above keep each field on one line where they can, and some descriptions are
longer than 100 characters. Open `pyproject.toml` and make sure it ends with these lines
(if you copied the whole file in lesson 4.9, they are already there):

<!-- source: pyproject.toml:10-20 -->
```toml
[tool.ruff.lint.isort]
# Our own packages, named so imports are grouped the same way even in a half-built copy
# of the project (the self-learning guide builds it one app at a time).
known-first-party = [
    "accounts", "businesses", "common", "config", "decisions", "intelligence",
    "simulation_engine", "simulations",
]

[tool.ruff.lint.per-file-ignores]
# Catalogue tables keep one input per line so they read like a spec sheet.
"simulation_engine/catalog.py" = ["E501"]
```

## ✅ Check

In the terminal (venv active, inside `my-warroom`), start Python and try the rules:

```bash
python
```

```python
from simulation_engine import catalog

catalog.parse_input("average_order_value", "1,250.50")
catalog.parse_input("conversion_rate", "120")
```

The first line prints `Decimal('1250.50')`. The second raises
`CatalogError: conversion_rate: must be at most 100 %`. That's the rule doing its job.
Try one more:

```python
catalog.validate_parameters("warehouse_shutdown", {"outage_hours": 6})
```

You get a dictionary with **all** the settings, your `'6'` plus the defaults
(`'start_hour': '18'`, `'horizon_hours': '72'`...), every value as text. Type `exit()` to
leave Python.

## 🔍 Line by line

### Piece 1

- **Lines 1–13** · The docstring. It names the two big tables (`INPUTS`, `TEMPLATES`)
  and gives the most important rule of the file: percentages are written the way people
  say them, so `2.5` means 2.5 %, not 0.025.
- **Line 15** · `dataclass`, the class-writing helper from 📖 Read.
- **Line 16** · `Decimal` for exact money (you met it in lesson 1.9).
  `InvalidOperation` is the error `Decimal` raises for text like `"lots"`.
- **Lines 18–19** · The two modes as named constants. Writing `IDEA` instead of `"idea"`
  everywhere means a typo becomes an error you see immediately (`IDAE` doesn't exist),
  not a silent bug.
- **Line 22** · Our own error type. It **inherits** from `ValueError`, so any code that
  catches `ValueError` also catches it.
- **Line 23** · Docstring: it carries a dictionary like `{"conversion_rate": "must be at
  most 100 %"}`, so the API can point at the exact field that is wrong.
- **Line 25** · `__init__` receives that dictionary. `dict[str, str]` is a **type hint**:
  "a dictionary from text to text". Python doesn't enforce hints; they help readers and
  editors.
- **Line 26** · Builds one readable message for the parent `ValueError`, like
  `"conversion_rate: must be at most 100 %"`. If there are several errors they are joined
  with `"; "`.
- **Line 27** · Keeps the dictionary too, on `self.errors`, for code that wants details.
- **Line 30** · `@dataclass(frozen=True)`: make the boring parts of the class below, and
  forbid changes after creation.
- **Line 31** · A `Field` describes **one** number: its rules, not its value.
- **Lines 32–34** · Three required pieces of text: `key` (the code name, like
  `daily_orders`), `label` (the human name) and `unit` (like `orders/day`).
- **Lines 35–36** · The smallest and biggest allowed values. `Decimal | None = None`
  means "a Decimal, or nothing; nothing by default" (no limit).
- **Line 37** · A default value, stored as **text** (the comment says why: text survives
  being saved as JSON exactly, while a float could become `0.30000000000000004`).
- **Line 38** · For fields that aren't numbers: a list of allowed words.
  `tuple[str, ...]` means "a tuple of any number of strings". `()` is an empty tuple.
- **Line 39** · Help text for forms.
- **Line 40** · Which modes the field belongs to. By default, both.
- **Line 42** · `parse` turns whatever the user typed into a checked value. The `->`
  hint says it returns a Decimal or a string.
- **Line 43** · Docstring.
- **Lines 44–48** · If the field has `choices`: clean the text (`strip()` removes spaces
  at the ends), refuse anything not in the list, otherwise return it.
- **Lines 49–51** · Try to make a Decimal. `str(raw)` first (the comment explains: a
  float `0.1` is really `0.1000000000000000055...` inside the computer; going through text
  gives exactly `0.1`). `.replace(",", "")` lets people type `1,250.50`.
- **Lines 52–53** · If that failed, raise a friendly `ValueError`. `from None` hides the
  confusing original error from the message.
- **Lines 54–55** · Decimal accepts `"NaN"` ("not a number") and `"Infinity"`. Neither
  makes sense as money, so refuse them.
- **Lines 56–57** · Below the minimum? Say so, with the unit:
  `"must be at least 0 orders/day"`. `.rstrip()` removes the trailing space when the unit
  is empty.
- **Lines 58–59** · Same for the maximum.
- **Line 60** · All checks passed: return the clean Decimal.
- **Lines 63–64** · `D("0")` is a short name for `Decimal("0")`, so the tables below are
  easier to read. The `# noqa: N802` comment tells a linter "yes, I know the name is
  capitalised; it's on purpose".
- **Line 67** · The settings every percentage shares. Used with `**PERCENT` below.

### Piece 2

- **Lines 69–71** · A comment "banner" to make the big sections easy to spot.
- **Line 72** · `_INPUT_LIST` is a list of `Field`s. The `_` at the start says "private
  to this file; other files should use `INPUTS`".
- **Line 73** · Comment: the first fields are for the **Idea** mode.
- **Lines 74–81** · The first field, written over several lines for readability:
  - **75** key `price_per_order`, **76** label, **77** unit `INR/order`,
  - **78** minimum `D("0")` (a price can't be negative). These four are given **by
    position**, in the same order as lines 32–35.
  - **79** `help=` and **80** `modes=` are given **by name**, because we skip `maximum`
    and `default`.
  - `modes=(IDEA,)` is a tuple with one item. The comma matters: `(IDEA)` would just be
    the text `"idea"`.
- **Lines 82–129** · More Idea fields in exactly the same pattern. Notice:
  - **Line 98** · A short field fits on one line.
  - **Line 110** · `**PERCENT` fills in unit, minimum and maximum for a percentage.
  - **Lines 118–119** · Orders per customer: between 0 and 100 a month.
- **Lines 130–137** · `expected_orders_monthly`: the founder's own guess. Part 6 checks it
  against what the funnel (visits × conversion) can really produce.
- **Line 138** · Comment: now the fields for the **Operating** mode (the "Resilience
  Room").
- **Lines 139–182** · Same pattern again: daily orders, order value, contribution margin,
  hourly capacity, and the share of orders each main supplier handles (gateway, warehouse,
  courier), plus how customers behave when things go wrong (retry, cancel).
- **Line 183** · End of the list.
- **Line 184** · Turn the list into a **dictionary** keyed by `key`, so code can ask
  `INPUTS["daily_orders"]` directly. `{f.key: f for f in _INPUT_LIST}` is a **dict
  comprehension**: a one-line loop that builds a dictionary.
- **Line 187** · `parse_input` checks **one** business number by its key.
- **Line 188** · Docstring.
- **Line 189** · `.get(key)` returns `None` instead of crashing when the key is unknown.
- **Lines 190–191** · Unknown key? Refuse it, naming the key. This is what catches
  `convertion_rate`.
- **Lines 192–195** · Ask the field to parse the value. If it raises `ValueError`, turn it
  into a `CatalogError` that names the field.

### Piece 3

- **Lines 198–200** · Section banner.
- **Lines 201–213** · A `Template` describes one **kind** of scenario:
  - **203–206** · Its key, name, kind (`idea_case` or `disruption`) and the mode of
    business it works for.
  - **207** · A sentence describing it.
  - **208** · Its settings (a tuple of `Field`s, the same class as before).
  - **209** · The business numbers it **needs** before it can run.
  - **210–212** · For disruptions only: which kind of part fails, which assumption says
    how much of the traffic that part carries, and whether lost orders fail at checkout or
    wait to be shipped.
  - **213** · The three ways to respond, as `(key, label)` pairs.
- **Lines 216–228** · Settings **every** disruption has: how long the outage lasts (0–72
  hours, default 4), what hour it starts (default 18 = 6 pm), how many hours to simulate,
  and the shape of the day's orders (only two words allowed).
  These lines give `minimum, maximum, default` **by position**, after the unit.
- **Lines 229–236** · Settings for the "switch to a backup" strategy: how long switching
  takes, how much the backup can handle, and what it costs.
- **Line 237** · Comment: the next two groups use the **same keys** with different
  meanings, so each has its own labels.
- **Lines 238–250** · For **checkout** failures (payments): retry queued payments.
- **Lines 251–269** · For **fulfilment** failures (warehouse, courier): tell waiting
  customers when their order will ship, so fewer cancel.
- **Lines 270–279** · The three strategies, with labels that fit each kind of failure.
- **Line 280** · The numbers every checkout scenario needs.
- **Line 281** · Fulfilment scenarios need those **plus** `hourly_capacity`. Adding two
  tuples with `+` joins them.
- **Lines 283–305** · The Idea template: horizon in months, the sensitivity step, and the
  nine numbers it needs.
- **Lines 306–346** · The three disruption templates. Each one combines the shared
  settings with `+` (line 312: common + backup + retry) and says which part fails and
  which numbers it needs.
- **Line 348** · The dictionary version, like line 184.

### Piece 4

- **Line 351** · `validate_parameters` checks a scenario's settings against its template.
  `dict | None` means you may pass nothing at all.
- **Lines 352–357** · Docstring. Values come back **as text** (`"4"`), safe for a JSON
  column, and **every** bad field is reported at once (not just the first).
- **Lines 358–360** · Unknown template? Refuse.
- **Line 361** · `raw or {}`: if nothing was passed, use an empty dictionary.
- **Line 362** · The template's settings, keyed by name.
- **Line 363** · Start the error list with every key the user sent that this template
  doesn't have (like `"colour"`).
- **Line 364** · The clean result starts empty.
- **Line 365** · Go through every setting the template **does** have.
- **Line 366** · Use the user's value, or the default if they didn't send one.
- **Lines 367–369** · Still nothing? It's required. `continue` jumps to the next setting.
- **Lines 370–373** · Parse it. Store the clean value as text; or store the error and
  carry on.
- **Lines 374–375** · Any errors at all? Raise them **together**.
- **Line 376** · All good: return the clean settings.
- **Lines 379–381** · `missing_inputs`: which numbers does this template need that the
  business doesn't have yet? A list comprehension keeps the ones not in `available`.
- **Lines 384–395** · `describe` turns a `Field` into a plain dictionary that can be sent
  as JSON. Decimals become text (`str(...)`), and `None` stays `None` (JSON's `null`).
- **Lines 398–410** · `__all__` lists the names this module offers to other files. It's a
  polite "this is the public part".

### `pyproject.toml`

- **Line 10** · Settings for ruff's import sorter (the **I** checks from lesson 4.9).
- **Lines 11–12** · A comment explaining why.
- **Lines 13–16** · "These names are **our own** packages." Ruff puts our own imports in
  a separate group after the libraries. Without this list ruff guesses, and while your
  project is half-built (no `intelligence` code yet) it can guess differently from the
  finished project.
- **Line 18** · Rules that apply only to certain files.
- **Lines 19–20** · In `catalog.py`, allow lines longer than 100 characters (rule
  **E501**): the long scenario descriptions read better on one line.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'simulation_engine'` | Run `python` from inside `my-warroom`, and check `simulation_engine/__init__.py` exists. |
| `TypeError: non-default argument follows default argument` | In `Field`, the four fields without `=` (lines 32–34) must come first. |
| `SyntaxError` near `**PERCENT` | Check the commas: `"Contribution margin",` then `**PERCENT,` on its own line. |
| `FrozenInstanceError` | You tried to change a field of a `Field` or `Template`. They are frozen on purpose. |

## ❓ Quiz

1. What does `conversion_rate = 2.5` mean: 2.5 % or 250 %?
2. Why does `parse` call `str(raw)` before `Decimal(...)`?
3. What happens if you send `{"outage_hours": 100, "colour": "red"}` to a warehouse
   shutdown?
4. Why is `simulation_engine` not a Django app?

---

**Next:** [5.3 · Business tables](03-business-models.md)

<details><summary>Quiz answers</summary>

1. 2.5 % (line 12: percentages are written the way people say them).
2. A float like `0.1` is not exactly 0.1 inside the computer; going through text gives an
   exact Decimal.
3. You get one `CatalogError` listing **both**: `outage_hours` (at most 72) and `colour`
   (not a parameter of this scenario).
4. It's pure rules and maths. Without Django it's simpler, faster to test, and usable from
   anywhere.

</details>
