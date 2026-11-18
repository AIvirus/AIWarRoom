# 1.5 · Functions

**Time:** 30 minutes · **Before this:** [1.4](04-decisions-and-loops.md).

## Read

A **function** is a recipe with a name. You write the steps once, and then you can
"cook" it as many times as you like, with different ingredients.

```python
def profit_for_day(cups):
    return cups * 9
```

- `def` means "**def**ine a new function".
- `cups` is a **parameter**: an empty slot that gets filled each time the function is
  used.
- `return` sends an answer back to whoever used the function.

Using a function is called **calling** it: `profit_for_day(120)` fills the slot `cups`
with 120 and gives back the answer.

Why bother? Almost all of AI WarRoom is functions: one works out the money lost in an
outage, another checks a number the AI wrote, and so on. Small named functions are easy
to read, easy to test and easy to reuse.

## Do

Make `functions.py`:

<!-- source: self-learning-guide/01-python/practice/functions.py:1-23 -->
```python
# Functions: give a name to a recipe so you can use it again.
def profit_for_day(cups, price=15, cost=6.5):
    """Money left after paying for the tea, milk and sugar."""
    money_in = cups * price
    money_out = cups * cost
    return money_in - money_out


print(profit_for_day(120))
print(profit_for_day(120, price=20))
print(profit_for_day(cups=50, cost=8))


def best_day(sales: dict[str, int]) -> str:
    """The day with the most cups sold."""
    best = None
    for day, cups in sales.items():
        if best is None or cups > sales[best]:
            best = day
    return best


print(best_day({"Mon": 110, "Sat": 210, "Sun": 190}))
```

```bash
python functions.py
```

## Check

```text
1020.0
1620.0
350
Sat
```

## Line by line

**Line 2** · `def profit_for_day(cups, price=15, cost=6.5):`
- `def` starts a new function called `profit_for_day`.
- It has three parameters. `price=15` and `cost=6.5` have **default values**: if you
  don't give a price, 15 is used.
- The colon `:` says "the recipe's steps come next, indented".

**Line 3** · `"""Money left after..."""` is a **docstring**: a sentence (in triple quotes)
saying what the function does. VS Code shows it when you point at the function's name.
AI WarRoom has one on almost every function.

**Lines 4–5** · Work out money in and money out. These variables only exist **inside**
the function, and disappear when it finishes.

**Line 6** · `return money_in - money_out`: send the answer back. The function stops here.

**Lines 7–8** · Two empty lines after a function: a style rule that makes files easier to
read.

**Line 9** · `profit_for_day(120)`: `cups` becomes 120; price and cost use their defaults.
120 × 15 − 120 × 6.5 = 1020.0.

**Line 10** · `price=20` overrides the default **by name**: 120 × 20 − 780 = 1620.0.

**Line 11** · Every value given by name, in any order: 50 × 15 − 50 × 8 = 750 − 400 = 350.
Using names makes calls easy to read: you can see which number is which.

**Line 14** · `def best_day(sales: dict[str, int]) -> str:`
- `: dict[str, int]` is a **type hint**: a note saying "sales should be a dictionary with
  text keys and whole-number values".
- `-> str` says "this function returns text".
- Python doesn't enforce type hints; they help humans and VS Code catch mistakes.

**Line 16** · Start with "no best day found yet".

**Line 17** · `sales.items()` gives each (key, value) pair. Here that's each (day, cups).

**Line 18** · `if best is None or cups > sales[best]:`
- `best is None` is True only the first time round.
- `or` means "either side being True is enough".
- `cups > sales[best]` asks: did this day sell more than the best day so far?

**Line 19** · If so, this day becomes the new best.

**Line 20** · After checking every day, return the best one.

**Line 23** · Call it with a small dictionary. Saturday (210) wins.

## If it didn't work

| You see | It means |
|---|---|
| Your function prints nothing | Calling a function doesn't print. Wrap it: `print(profit_for_day(120))`. |
| `TypeError: profit_for_day() missing 1 required positional argument: 'cups'` | You called it without the value that has no default. |
| `None` is printed | The function has no `return` line, so it gives back `None`. |

## Quiz

1. What's the difference between a parameter and a value you pass in?
2. What does `profit_for_day(10, cost=10)` return?
3. Write a function `money_in(cups, price)` that returns `cups * price`, and print
   `money_in(30, 15)`.

---

**Next:** [1.6 · Classes and dataclasses](06-classes-and-dataclasses.md)

<details><summary>Quiz answers</summary>

1. A parameter is the named slot in the definition (`cups`); the value is what fills it
   when you call (`120`).
2. `50`: 10 × 15 − 10 × 10 = 150 − 100.
3. `def money_in(cups, price): return cups * price`, then `print(money_in(30, 15))` → `450`.

</details>
