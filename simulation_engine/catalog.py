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
