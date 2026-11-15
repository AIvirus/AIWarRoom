# 1.6 · Classes and dataclasses

**Time:** 40 minutes · **Before this:** [1.5](05-functions.md).

## 📖 Read

A **class** is a blueprint. From one blueprint you can make many **objects**, each with
its own data.

- **Blueprint:** "a chai stall has a name and a price per cup, and can work out money in".
- **Objects:** Raju's stall (₹15 a cup), Meena's stall (₹12 a cup)...

Data stored on an object is called an **attribute** (`raju.name`). A function that
belongs to a class is called a **method** (`raju.money_in(100)`).

**Why it matters for AI WarRoom:** in Django, every database table is a class. A
`BusinessProfile` class describes a business, and each saved business is an object.

### Dataclasses: classes with less typing

Many classes just *hold data*. Python's `@dataclass` writes the boring parts (like
`__init__`) for you. `frozen=True` makes the object **unchangeable** after it's made,
which is great for things like "the inputs of a simulation": nobody can change them by
accident halfway through.

## ⌨️ Do

Make `classes.py`:

<!-- source: self-learning-guide/01-python/practice/classes.py:1-32 -->
```python
# Classes: a blueprint for things that have data and can do things.
from dataclasses import dataclass, replace


class Stall:
    def __init__(self, name, price_per_cup):
        self.name = name
        self.price_per_cup = price_per_cup

    def money_in(self, cups):
        return cups * self.price_per_cup


raju = Stall("Raju Chai", 15)
print(raju.name, raju.money_in(100))


@dataclass(frozen=True)
class Plan:
    price: int
    cups_per_day: int

    def daily_sales(self):
        return self.price * self.cups_per_day


plan = Plan(price=15, cups_per_day=120)
print(plan)
print(plan.daily_sales())

bigger = replace(plan, cups_per_day=200)
print(bigger.daily_sales(), "versus", plan.daily_sales())
```

```bash
python classes.py
```

## ✅ Check

```text
Raju Chai 1500
Plan(price=15, cups_per_day=120)
1800
3000 versus 1800
```

## 🔍 Line by line

**Line 2** · `from dataclasses import dataclass, replace`: bring in two tools from Python's
built-in `dataclasses` module (lesson 1.7 explains `import`).

**Line 5** · `class Stall:` starts the blueprint. Class names use **CapitalWords**
(PascalCase); variables and functions use snake_case.

**Line 6** · `def __init__(self, name, price_per_cup):`
- `__init__` ("init", short for initialise) is a special method that runs automatically
  when a new object is made.
- `self` is the object being made. Every method gets it as its first parameter.

**Line 7** · `self.name = name` stores the name **on the object**, so it's remembered.

**Line 8** · Same for the price.

**Line 10** · `def money_in(self, cups):` is a method. `self` lets it reach the object's
own data.

**Line 11** · Uses `self.price_per_cup`, this stall's own price.

**Line 14** · `raju = Stall("Raju Chai", 15)` makes an object from the blueprint. Python
calls `__init__` with `name="Raju Chai"` and `price_per_cup=15`.

**Line 15** · `raju.name` reads an attribute; `raju.money_in(100)` calls a method:
100 × 15 = 1500.

**Line 18** · `@dataclass(frozen=True)` is a **decorator**: a line starting with `@` that
adds abilities to the thing right below it. Here it writes `__init__` (and a nice printout)
for us, and makes objects unchangeable.

**Lines 19–21** · The class just *lists* its fields with type hints. No `__init__`
needed: the dataclass creates it.

**Lines 23–24** · Classes made with `@dataclass` can still have methods.

**Line 27** · Make a plan using field names.

**Line 28** · Printing a dataclass shows all its fields. Plain classes just show a
confusing memory address.

**Line 31** · `replace(plan, cups_per_day=200)` makes a **new** Plan that's a copy of
`plan` with one field changed. We can't change `plan` itself because it's frozen. AI
WarRoom uses exactly this to build the "worst case": copy the founder's plan, change a
few numbers.

**Line 32** · The copy sells 3000 a day; the original is untouched at 1800.

## 🛠️ If it didn't work

| You see | It means |
|---|---|
| `TypeError: Stall.__init__() missing 1 required positional argument` | You made a `Stall` without giving both name and price. |
| `FrozenInstanceError: cannot assign to field 'price'` | You tried `plan.price = 20` on a frozen dataclass. Use `replace(...)` instead. |
| `AttributeError: 'Stall' object has no attribute 'Name'` | Spelling or capitals: it's `name`. |

## ❓ Quiz

1. What is `self`?
2. Why might we want a dataclass to be `frozen`?
3. Make `meena = Stall("Meena Tea", 12)` and print `meena.money_in(50)`.

---

**Next:** [1.7 · Files, modules and packages](07-modules-and-packages.md)

<details><summary>Quiz answers</summary>

1. The object itself. Methods use it to reach that object's own data.
2. So nobody can change its data by accident after it's made.
3. `600`.

</details>
