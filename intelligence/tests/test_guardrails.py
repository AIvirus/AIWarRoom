from decimal import Decimal as D

import pytest

from intelligence.services.guardrails import (
    flag_unsupported_numbers,
    numbers_in_data,
    numbers_in_text,
)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("₹21,000", D("21000")),
        ("₹1,00,000", D("100000")),
        ("8514.74", D("8514.74")),
        ("about ₹8.5k", D("8500")),
        ("₹1.2 lakh", D("120000")),
        ("₹3 crore", D("30000000")),
        ("26.21%", D("26.21")),
        ("-2,428.80", D("-2428.80")),
    ],
)
def test_numbers_are_read_the_way_people_write_them(text, value):
    assert numbers_in_text(text)[0].value == value


def test_month_words_are_not_mistaken_for_millions():
    assert [n.value for n in numbers_in_text("in 10 months")] == [D("10")]


@pytest.mark.parametrize(
    ("written", "digits"),
    [("8514.74", 6), ("8.5", 2), ("21000", 2), ("21,000", 2), ("0.25", 2), ("26", 2)],
)
def test_significant_digits_count_what_was_actually_written(written, digits):
    assert numbers_in_text(written)[0].significant == digits


def test_near_miss_numbers_are_flagged():
    """
    14,700 is real. "₹15k" (rounded) and "₹14k" (truncated) are fair shortenings of it;
    "₹14,550" and "₹13,000" are different numbers.
    """
    sent = {"lost": "14700.00"}
    assert flag_unsupported_numbers({"t": "about ₹15k, at least ₹14k"}, sent) == []
    assert [f["literal"] for f in flag_unsupported_numbers({"t": "₹14,550"}, sent)] == ["14,550"]
    assert [f["literal"] for f in flag_unsupported_numbers({"t": "₹13,000"}, sent)] == ["13,000"]


def test_numbers_in_nested_data_include_numeric_strings():
    data = {"m": {"value": "21000.00", "unit": "INR"}, "list": [7, "horizon 24 months"]}
    assert {D("21000.00"), D("7"), D("24")} <= numbers_in_data(data)


def test_booleans_are_not_numbers():
    assert numbers_in_data({"flag": True}) == set()


SENT = {
    "metrics": {
        "wait.total_impact": {"value": "8514.74"},
        "queue_retry.total_impact": {"value": "6391.02"},
        "wait.time_to_recovery": {"value": "11"},
    },
    "assumptions": {"contribution_margin": {"value": "22"}},
}


def test_rounded_versions_of_sent_numbers_are_accepted():
    answer = {
        "headline": "Waiting costs about ₹8,500; queueing about ₹6.4k.",
        "what_happened": "Recovery takes 11 hours at a 22 % margin.",
    }
    assert flag_unsupported_numbers(answer, SENT) == []


def test_invented_or_derived_numbers_are_flagged_with_their_location():
    answer = {
        "key_findings": [
            {"text": "Queueing saves ₹2,124 versus waiting.", "metric_keys": ["wait.x"]},
            {"text": "Industry average loss is 40 %.", "metric_keys": []},
        ]
    }
    flags = flag_unsupported_numbers(answer, SENT)
    assert [(f["path"], f["literal"]) for f in flags] == [
        ("key_findings[0].text", "2,124"),
        ("key_findings[1].text", "40"),
    ]


def test_small_counts_are_not_flagged():
    assert flag_unsupported_numbers({"t": "Compare the 3 strategies over 2 days."}, SENT) == []
