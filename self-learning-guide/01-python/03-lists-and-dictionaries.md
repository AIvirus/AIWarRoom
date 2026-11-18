# 1.3 · Lists and dictionaries

**Time:** 30 minutes · **Before this:** [1.2](02-values-and-variables.md).

## Read

Sometimes one value isn't enough. Raju wants to remember how many cups he sold on
**each day** of the week. Python has two "containers" for many values.

**A list** keeps values **in order**, in square brackets:

```python
sales = [110, 125, 98]
```

Each item has a position number called an **index**. Counting starts at **0**, not 1:

| Index | 0 | 1 | 2 |
|---|---|---|---|
| Value | 110 | 125 | 98 |

`sales[0]` is `110`. `sales[-1]` means "the last one", which is `98`.

**A dictionary** (`dict`) stores values with **names** (called **keys**), in curly
brackets. It's like a real dictionary: you look up a word (the key) to find its meaning
(the value).

```python
stall = {"name": "Raju Chai", "price_per_cup": 15}
```

`stall["name"]` gives `"Raju Chai"`.

You'll see dictionaries **everywhere** in AI WarRoom: the results of a simulation, the
data sent to the AI and the data the website receives are all dictionaries.

## Do

Make `lists_and_dicts.py`:

<!-- source: self-learning-guide/01-python/practice/lists_and_dicts.py:1-21 -->
```python
# Lists keep things in order. Dictionaries give names to values.
sales_this_week = [110, 125, 98, 140, 160, 210, 190]

print("Monday:", sales_this_week[0])
print("Sunday:", sales_this_week[-1])
print("Days recorded:", len(sales_this_week))
print("Total cups:", sum(sales_this_week))

sales_this_week.append(175)
print("After adding one more day:", sales_this_week)

stall = {
    "name": "Raju Chai",
    "price_per_cup": 15,
    "cost_per_cup": 6.5,
}
print(stall["name"], "sells chai at", stall["price_per_cup"])

stall["city"] = "Pune"
print("Keys:", list(stall.keys()))
print("Has a phone number?", "phone" in stall)
```

```bash
python lists_and_dicts.py
```

## Check

```text
Monday: 110
Sunday: 190
Days recorded: 7
Total cups: 1033
After adding one more day: [110, 125, 98, 140, 160, 210, 190, 175]
Raju Chai sells chai at 15
Keys: ['name', 'price_per_cup', 'cost_per_cup', 'city']
Has a phone number? False
```

## Line by line

**Line 2** · `sales_this_week = [110, 125, ...]`: a list of 7 whole numbers, Monday to
Sunday. Items are separated by commas.

**Line 4** · `sales_this_week[0]`: square brackets after a list mean "give me the item at
this position". Position 0 is the first item (Monday).

**Line 5** · `sales_this_week[-1]`: negative positions count from the end. `-1` is the
last item (Sunday).

**Line 6** · `len(...)`: a built-in function that counts the items (**len**gth): 7.

**Line 7** · `sum(...)`: adds up all the numbers: 1033.

**Line 9** · `sales_this_week.append(175)`: `.append` adds an item to the **end** of the
list. The dot means "use a tool that belongs to this list". Lists have their own tools,
called **methods**.

**Line 10** · Prints the whole list. It now has 8 items.

**Lines 12–16** · A dictionary written over several lines so it's easy to read. Each line
is `"key": value,`. The comma after the last item is allowed, and it makes adding items
later easier.

**Line 17** · `stall["name"]`: look up the value for the key `"name"`.

**Line 19** · `stall["city"] = "Pune"`: putting a new key in square brackets on the left
of `=` **adds** it. If the key already existed, its value would be **replaced**.

**Line 20** · `stall.keys()` gives all the keys; `list(...)` turns them into a normal list
so they print nicely.

**Line 21** · `"phone" in stall`: `in` asks "is this key in the dictionary?" The answer is
`True` or `False`.

## If it didn't work

| You see | It means |
|---|---|
| `IndexError: list index out of range` | You asked for a position that doesn't exist (e.g. `[7]` in a 7-item list: the last is `[6]`). |
| `KeyError: 'Name'` | That key isn't in the dictionary. Check the spelling and capitals: `"name"` ≠ `"Name"`. |

## Quiz

1. In `[5, 10, 15]`, what is `[1]`?
2. How do you add `"phone": "98xxxxxxx"` to `stall`?
3. Print the **average** cups per day. (Hint: `sum` divided by `len`.)

---

**Next:** [1.4 · Decisions and loops](04-decisions-and-loops.md)

<details><summary>Quiz answers</summary>

1. `10`. Counting starts at 0.
2. `stall["phone"] = "98xxxxxxx"`
3. `print(sum(sales_this_week) / len(sales_this_week))`

</details>
