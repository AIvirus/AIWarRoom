# Tests: small programs that check our code gives the right answers.
import pytest
from chai import is_good_day, profit


def test_profit_by_hand():
    # 100 cups x (15 - 6) = 100 x 9 = 900
    assert profit(100, 15, 6) == 900


def test_no_cups_no_profit():
    assert profit(0, 15, 6) == 0


@pytest.mark.parametrize(("cups", "expected"), [(149, False), (150, True), (300, True)])
def test_good_day_starts_at_150(cups, expected):
    assert is_good_day(cups) == expected
