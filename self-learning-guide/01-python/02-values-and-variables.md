# 1.2 · Values and variables

**Time:** 30 minutes · **Before this:** [1.1](01-your-first-program.md).

## 📖 Read

A **value** is one piece of information: `120`, `6.5`, `"Raju Chai"`, `True`.

A **variable** is a name for a value, like a labelled jar. You put a value in the jar
with `=`, and later you use the label to get it back.

```python
cups_per_day = 120
```

Read this as **"cups_per_day now holds 120"**. In Python, `=` does not mean "is equal
to". It means **"store the value on the right in the name on the left"**.

### The kinds of values (called *types*)

| Type | Example | Used for |
|---|---|---|
| `int` (integer) | `120`, `-5`, `0` | Whole numbers |
| `float` | `6.5`, `0.1` | Numbers with a decimal point |
| `str` (string) | `"Raju Chai"` | Text |
| `bool` (boolean) | `True`, `False` | Yes/no |
| `None` | `None` | "Nothing here yet" |

### Maths in Python

| Sign | Meaning | Example | Result |
|---|---|---|---|
| `+` | add | `5 + 2` | `7` |
| `-` | subtract | `5 - 2` | `3` |
| `*` | multiply | `5 * 2` | `10` |
| `/` | divide | `5 / 2` | `2.5` |
| `//` | divide, drop the remainder | `5 // 2` | `2` |
| `%` | remainder | `5 % 2` | `1` |
| `**` | power | `5 ** 2` | `25` |

## ⌨️ Do

Make `values.py` in your `python` folder and type:

<!-- source: self-learning-guide/01-python/practice/values.py:1-17 -->
```python
# A tiny chai stall, described with values.
stall_name = "Raju Chai"
cups_per_day = 120
price_per_cup = 15
cost_per_cup = 6.5
is_open_today = True
owner_phone = None

money_in = cups_per_day * price_per_cup
money_out = cups_per_day * cost_per_cup
profit = money_in - money_out

print(stall_name)
print("Money in today:", money_in)
print("Profit today:", profit)
print(f"{stall_name} made {profit} rupees profit from {cups_per_day} cups.")
print(type(cups_per_day), type(cost_per_cup), type(stall_name), type(is_open_today))
```

Run it:

```bash
python values.py
```

## ✅ Check

```text
Raju Chai
Money in today: 1800
Profit today: 1020.0
Raju Chai made 1020.0 rupees profit from 120 cups.
<class 'int'> <class 'float'> <class 'str'> <class 'bool'>
```

## 🔍 Line by line

**Line 1** · A comment saying what the file is about.

**Line 2** · `stall_name = "Raju Chai"`: store the text `Raju Chai` in a variable named
`stall_name`. Names use lowercase words joined by `_` (underscore). This style is called
*snake_case*, and Python programmers always use it for variables.

**Line 3** · `cups_per_day = 120`: a whole number (`int`).

**Line 4** · `price_per_cup = 15`: another `int`. The price is ₹15.

**Line 5** · `cost_per_cup = 6.5`: a number with a decimal point (`float`). Tea, milk and
sugar for one cup cost ₹6.50.

**Line 6** · `is_open_today = True`: a yes/no value (`bool`). `True` and `False` start with
a capital letter.

**Line 7** · `owner_phone = None`: `None` means "we don't have this yet". It isn't zero
and it isn't empty text. It is "nothing".

**Line 8** · An empty line. Python ignores it. It makes the code easier to read, like a
gap between paragraphs.

**Line 9** · `money_in = cups_per_day * price_per_cup`: Python looks up both jars
(120 and 15), multiplies them (1800), and stores the answer in `money_in`.

**Line 10** · `money_out = cups_per_day * cost_per_cup`: 120 × 6.5 = 780.0. Because 6.5
is a float, the answer is a float too.

**Line 11** · `profit = money_in - money_out`: 1800 − 780.0 = 1020.0.

**Line 13** · `print(stall_name)`: prints what's *inside* the jar (`Raju Chai`), not the
word `stall_name`. There are no quotes, so Python treats it as a name.

**Line 14** · `print("Money in today:", money_in)`: text, then the value of a variable.

**Line 15** · The same, for profit.

**Line 16** · `print(f"{stall_name} made {profit} ...")`: an **f-string**. The `f` before
the quote means "fill in the gaps". Anything inside `{ }` is replaced by its value. This
is the easiest way to mix text and values.

**Line 17** · `type(...)` tells you what kind of value something is. You see
`<class 'int'>` and so on. "Class" is Python's word for a type (more in lesson 1.6).

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `NameError: name 'cups_per_day' is not defined` | The spelling is different in two places. Names must match exactly, including `_` and capitals. |
| You see `{stall_name}` printed literally | You forgot the `f` before the quote on line 16. |
| `TypeError: can only concatenate str (not "int") to str` | You wrote something like `"Profit: " + profit`. Use a comma in `print`, or an f-string. |

## ❓ Quiz

1. What type is `"120"` (with quotes)? And `120`?
2. After `cups = 10` and then `cups = cups + 5`, what is in `cups`?
3. Change `cups_per_day` to `200` and run again. What is the profit now?

---

**Next:** [1.3 · Lists and dictionaries](03-lists-and-dictionaries.md)

<details><summary>Quiz answers</summary>

1. `"120"` is a `str` (text). `120` is an `int`.
2. `15`. Python works out the right side first (10 + 5), then stores it.
3. 200 × 15 − 200 × 6.5 = 3000 − 1300 = `1700.0`.

</details>
