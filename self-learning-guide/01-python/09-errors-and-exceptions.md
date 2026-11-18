# 1.9 · Errors and exceptions

**Time:** 30 minutes · **Before this:** [1.8](08-money-with-decimal.md).

## Read

When Python can't do something (divide by zero, read "fifteen" as a number, find a
missing file) it **raises an exception**: it stops and prints an error. That printout is
called a **traceback**.

### How to read a traceback

```text
Traceback (most recent call last):
  File "errors.py", line 10, in <module>
    print(price_per_cup(1800, 0))
  File "errors.py", line 5, in price_per_cup
    return total_money / cups
ZeroDivisionError: division by zero
```

- **Read the last line first.** It names the error (`ZeroDivisionError`) and says why
  (`division by zero`).
- The lines above show **where**: file, line number, and the code on that line. The
  bottom-most location is where it actually broke.

### Catching exceptions: `try` / `except`

Sometimes we expect an error and want to handle it nicely instead of crashing:

```python
try:
    risky thing
except SomeError:
    what to do instead
```

### Raising your own: `raise`

When **your** function gets bad input, you can raise an error with a clear message.
AI WarRoom does this everywhere. For example, if someone says the profit margin is 140%,
it raises an error saying "must be at most 100 %".

## Do

Make `errors.py`:

<!-- source: self-learning-guide/01-python/practice/errors.py:1-22 -->
```python
# Errors happen. We can catch them and explain what went wrong.
def price_per_cup(total_money, cups):
    if cups < 0:
        raise ValueError("cups can't be negative")
    return total_money / cups


try:
    print(price_per_cup(1800, 120))
    print(price_per_cup(1800, 0))
except ZeroDivisionError:
    print("No cups sold, so there is no price per cup.")

try:
    price_per_cup(1800, -5)
except ValueError as error:
    print("Problem:", error)

try:
    int("fifteen")
except ValueError as error:
    print("Couldn't read the number:", error)
```

```bash
python errors.py
```

## Check

```text
15.0
No cups sold, so there is no price per cup.
Problem: cups can't be negative
Couldn't read the number: invalid literal for int() with base 10: 'fifteen'
```

## Line by line

**Line 2** · A function that divides money by cups.

**Lines 3–4** · `raise ValueError("...")`: if cups is negative, **stop** and raise an
error with our own message. `ValueError` is Python's standard error for "the type is
right but the value makes no sense".

**Line 5** · The normal case.

**Line 8** · `try:` means "attempt the indented lines below".

**Line 9** · Works fine: 1800 / 120 = 15.0.

**Line 10** · Dividing by 0 raises `ZeroDivisionError`. Python **jumps straight** to the
matching `except`; nothing else in the `try` block runs.

**Line 11** · `except ZeroDivisionError:` catches only that kind of error.

**Line 12** · Our friendly message instead of a crash.

**Lines 14–15** · Call with −5: our own `raise` on line 4 fires.

**Line 16** · `except ValueError as error:` catches it, and puts the error in a variable
called `error` so we can read its message.

**Line 17** · Printing the error shows our message: "cups can't be negative".

**Lines 19–22** · `int("fifteen")` can't turn words into a number, so Python raises a
`ValueError` with its own message, which we catch and print.

## If it didn't work

| You see | Fix |
|---|---|
| The program crashes with `ZeroDivisionError` | Check `except` is spelled `ZeroDivisionError` exactly, and is at the same indentation as `try`. |
| `SyntaxError: expected 'except' or 'finally' block` | Every `try:` needs an `except` (at the same indentation). |

> **Good habit:** catch **specific** errors (`except ValueError`), never everything
> (`except:` alone). Catching everything hides bugs you'd want to know about.

## Quiz

1. In a traceback, which line do you read first?
2. What happens to the rest of a `try` block after an error?
3. Why did we raise our own `ValueError` for negative cups instead of letting the
   function return a negative price?

---

**Next:** [1.10 · Testing with pytest](10-testing-with-pytest.md)

<details><summary>Quiz answers</summary>

1. The last line: the error's name and message.
2. It's skipped. Python jumps to the matching `except`.
3. A negative price is nonsense. Failing loudly with a clear message is better than
   quietly giving a wrong answer.

</details>
