"""Catalogue rules. Plain pytest: no Django, no database."""

from decimal import Decimal

import pytest

from simulation_engine import catalog


def test_parse_input_accepts_text_with_commas_and_keeps_exact_decimals():
    assert catalog.parse_input("average_order_value", "1,250.50") == Decimal("1250.50")
    # A float 0.1 must become exactly 0.1, not 0.1000000000000000055...
    assert catalog.parse_input("conversion_rate", 0.1) == Decimal("0.1")


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("conversion_rate", "120", "at most 100"),
        ("daily_orders", "-5", "at least 0"),
        ("daily_orders", "lots", "must be a number"),
        ("daily_orders", "NaN", "finite"),
        ("convertion_rate", "2", "not a known assumption"),
    ],
)
def test_parse_input_rejects_bad_values(key, value, message):
    with pytest.raises(catalog.CatalogError) as caught:
        catalog.parse_input(key, value)
    assert message in caught.value.errors[key]


def test_validate_parameters_fills_defaults_as_strings():
    params = catalog.validate_parameters("warehouse_shutdown", {"outage_hours": 6})
    assert params["outage_hours"] == "6"
    assert params["horizon_hours"] == "72"  # default
    assert params["demand_profile"] == "ecommerce_curve"
    assert all(isinstance(v, str) for v in params.values())


def test_validate_parameters_reports_every_bad_field_at_once():
    with pytest.raises(catalog.CatalogError) as caught:
        catalog.validate_parameters(
            "payment_gateway_outage",
            {"outage_hours": 100, "demand_profile": "random", "surprise": 1},
        )
    assert set(caught.value.errors) == {"outage_hours", "demand_profile", "surprise"}


def test_unknown_template_is_rejected():
    with pytest.raises(catalog.CatalogError):
        catalog.validate_parameters("alien_invasion", {})


def test_missing_inputs_lists_what_a_template_still_needs():
    have = {"daily_orders", "average_order_value"}
    missing = catalog.missing_inputs("payment_gateway_outage", have)
    assert "contribution_margin" in missing
    assert "daily_orders" not in missing


def test_every_template_requires_only_known_inputs_of_its_own_mode():
    for template in catalog.TEMPLATES.values():
        for key in template.required_inputs:
            assert key in catalog.INPUTS, key
            assert template.mode in catalog.INPUTS[key].modes, (template.key, key)


def test_every_parameter_default_passes_its_own_validation():
    for template in catalog.TEMPLATES.values():
        catalog.validate_parameters(template.key, {})  # raises if any default is invalid
