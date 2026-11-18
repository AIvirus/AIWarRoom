# 1.8 · Money with Decimal

**Time:** 20 minutes · **Before this:** [1.7](07-modules-and-packages.md).

## Read

Try this in your head: 0.1 + 0.2 = 0.3. Now ask Python:

```python
print(0.1 + 0.2)
```

It prints `0.30000000000000004`.

That isn't a bug in Python. Computers store `float` numbers in binary (only 0s and 1s),
and many simple decimals, like 0.1, can't be stored exactly in binary, just as 1/3 can't
be written exactly in decimal (0.3333...). The error is tiny, but with money it adds up
month after month, and a report showing ₹0.30000000000000004 looks broken.

The fix is **`Decimal`**, which does maths the way an accountant does, with decimal digits.
**AI WarRoom uses Decimal for every rupee.**

The one rule: **create a Decimal from text** (`Decimal("0.1")`), not from a float
(`Decimal(0.1)`), or the float's error comes along with it.

## Do

Make `decimal_money.py`:

<!-- source: self-learning-guide/01-python/practice/decimal_money.py:1-16 -->
```python
# Why money needs Decimal, not float.
from decimal import ROUND_HALF_UP, Decimal

print(0.1 + 0.2)
print(Decimal("0.1") + Decimal("0.2"))

price = Decimal("19.99")
cups = 3
total = price * cups
print(total)

tax = total * Decimal("0.18")
print(tax)
print(tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

print(Decimal(0.1))
```

```bash
python decimal_money.py
```

## Check

```text
0.30000000000000004
0.3
59.97
10.7946
10.79
0.1000000000000000055511151231257827021181583404541015625
```

## Line by line

**Line 2** · Import `Decimal` (the number type) and `ROUND_HALF_UP` (a rounding rule) from
Python's built-in `decimal` module.

**Line 4** · Float maths: the tiny binary error shows up.

**Line 5** · Decimal maths: exactly `0.3`. Note the quotes: `"0.1"` is text, so Decimal
reads the digits exactly.

**Line 7** · A price of ₹19.99 as a Decimal.

**Line 8** · An ordinary `int`. A Decimal times an int is fine and stays exact.

**Lines 9–10** · 19.99 × 3 = `59.97`, exact.

**Line 12** · 18% GST: 59.97 × 0.18 = `10.7946`. Decimal keeps every digit; it never
silently rounds.

**Line 14** · `.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` means "round to 2
decimal places, the normal shop way (5 and above rounds up)": `10.79`. AI WarRoom has a
helper called `round2` that does exactly this.

**Line 16** · The mistake to avoid: `Decimal(0.1)` **without quotes** copies the
float's error exactly, all 55 digits of it. Always use quotes.

## If it didn't work

| You see | Fix |
|---|---|
| `TypeError: unsupported operand type(s) for +: 'decimal.Decimal' and 'float'` | Python refuses to mix Decimal with float, to protect you. Make both Decimals: `Decimal("6.5")`. |
| `NameError: name 'Decimal' is not defined` | You forgot line 2's import. |

## Quiz

1. Why does `0.1 + 0.2` not print `0.3`?
2. Which is right: `Decimal(19.99)` or `Decimal("19.99")`?
3. What does `quantize(Decimal("0.01"))` do?

---

**Next:** [1.9 · Errors and exceptions](09-errors-and-exceptions.md)

<details><summary>Quiz answers</summary>

1. Floats are stored in binary, and 0.1 can't be stored exactly in binary.
2. `Decimal("19.99")`, with quotes.
3. Rounds to 2 decimal places (paise).

</details>
