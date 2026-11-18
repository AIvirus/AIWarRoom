# 1.10 · Testing with pytest

**Time:** 30 minutes · **Before this:** [1.9](09-errors-and-exceptions.md) (and pytest
installed in lesson [1.7](07-modules-and-packages.md)).

## Read

How do you know your code gives the right answer? You could run it and check by eye,
every time you change anything. Or you can write **tests**: small functions that check
answers **automatically**.

The method used all through AI WarRoom:

1. **Work out the answer by hand first**, on paper (100 cups × ₹9 = ₹900).
2. Write a test saying "the code must give 900".
3. Run the tests. Green means correct; red means something is wrong.

AI WarRoom has about 260 tests. Every time anyone changes the code, all of them run in
about 5 seconds. That's how we know a change didn't break something else.

**pytest rules:**
- Test files are named `test_something.py`.
- Test functions are named `test_something`.
- Inside, `assert` checks that something is True.

## Do

Make `chai.py` (the code to test):

<!-- source: self-learning-guide/01-python/practice/chai.py:1-7 -->
```python
# Code we want to test.
def profit(cups, price, cost):
    return cups * (price - cost)


def is_good_day(cups):
    return cups >= 150
```

and `test_chai.py` (the tests), in the same folder:

<!-- source: self-learning-guide/01-python/practice/test_chai.py:1-17 -->
```python
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
```

With your venv **active** (`(.venv)` in the prompt), run:

```bash
pytest
```

## Check

```text
test_chai.py .....                                                       [100%]
5 passed in 0.05s
```

Each dot is one passing test. There are 5 because the last test runs 3 times (see
line 15).

**Now break it on purpose:** in `chai.py`, change `>= 150` to `> 150`, save and run
`pytest` again. You'll see `1 failed` and pytest shows exactly which case (150) failed.
Change it back.

## Line by line

### `chai.py`

**Lines 2–3** · Profit = cups × (price − cost).

**Lines 6–7** · `cups >= 150` is already True or False, so we return it directly.

### `test_chai.py`

**Line 2** · `import pytest` loads the testing package.

**Line 3** · Import the two functions we want to test from `chai.py`.

**Line 6** · A test is a normal function whose name starts with `test_`. pytest finds it
by that name.

**Line 7** · The comment shows the hand calculation. Always write it down: it tells the
next reader *why* 900 is right.

**Line 8** · `assert profit(100, 15, 6) == 900`: "it must be true that this gives 900".
If it isn't, the test fails and pytest shows both numbers.

**Lines 11–12** · An **edge case**: zero cups. Edge cases (zero, empty, the exact border)
are where bugs hide.

**Line 15** · `@pytest.mark.parametrize(...)` runs the test below once for **each** pair:
(149 → False), (150 → True), (300 → True). One test, three checks. 149 and 150 sit on
the border, which is the most important place to test.

**Line 16** · `cups` and `expected` are filled from each pair in turn.

**Line 17** · Check that the answer matches what we expected.

## If it didn't work

| You see | Fix |
|---|---|
| `pytest: command not found` | Activate the venv, or run `python -m pytest`. |
| `no tests ran` | The file must start with `test_`, and functions with `test_`. |
| `ModuleNotFoundError: No module named 'chai'` | Run `pytest` from the folder that contains both files. |

## Quiz

1. Why do we work out the answer by hand **before** writing the test?
2. Why test 149 and 150, not just 100 and 300?
3. Add a test that `profit(10, 15, 15) == 0` (selling at cost). Does it pass?

---

**Next:** [1.11 · Mini project: chai stall cash](11-mini-project.md)

<details><summary>Quiz answers</summary>

1. So the test checks the code against the truth, not against whatever the code happens
   to output.
2. Bugs hide at borders: `>` versus `>=` only differs at exactly 150.
3. Yes: 10 × (15 − 15) = 0.

</details>
