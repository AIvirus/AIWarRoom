# 1.4 · Decisions and loops

**Time:** 30 minutes · **Before this:** [1.3](03-lists-and-dictionaries.md).

## Read

### Decisions: `if`, `elif`, `else`

Programs often need to choose: *if it's raining, take an umbrella, otherwise don't.*

```python
if cups >= 180:
    note = "busy"
else:
    note = "slow"
```

- After `if` comes a **condition**: a question with a True/False answer.
- The line ends with a colon `:`.
- The lines that belong to the `if` are pushed right by **4 spaces**. This push is
  called **indentation**, and in Python it isn't decoration: it decides which lines
  belong together. VS Code adds the 4 spaces for you when you press Enter after a `:`.

Comparison signs: `==` equal, `!=` not equal, `<`, `>`, `<=` (less or equal),
`>=` (more or equal).

Careful: `=` stores a value; `==` **asks** whether two values are equal.

### Loops: doing something many times

- **`for`** goes through every item of a list, one at a time.
- **`while`** keeps going **as long as** a condition is True.

## Do

Make `decisions_and_loops.py`:

<!-- source: self-learning-guide/01-python/practice/decisions_and_loops.py:1-19 -->
```python
# Making decisions with if, and repeating work with for and while.
cups_sold = [110, 125, 98, 140, 160, 210, 190]
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

for day, cups in zip(days, cups_sold, strict=True):
    if cups >= 180:
        note = "busy"
    elif cups >= 120:
        note = "normal"
    else:
        note = "slow"
    print(day, cups, note)

savings = 0
months = 0
while savings < 50000:
    savings = savings + 12000
    months = months + 1
print("Months to save 50,000:", months)
```

```bash
python decisions_and_loops.py
```

## Check

```text
Mon 110 slow
Tue 125 normal
Wed 98 slow
Thu 140 normal
Fri 160 normal
Sat 210 busy
Sun 190 busy
Months to save 50,000: 5
```

## Line by line

**Lines 2–3** · Two lists of the same length: cups sold, and the day names.

**Line 5** · `for day, cups in zip(days, cups_sold, strict=True):`
- `zip` pairs up two lists like a zip on a jacket: ("Mon", 110), ("Tue", 125)…
- `for day, cups in ...` takes one pair at a time and puts its two parts in the
  variables `day` and `cups`.
- `strict=True` makes Python complain if the two lists have different lengths. That's a
  safety check: a missing day would otherwise go unnoticed.
- The colon `:` starts the block of lines to repeat. Lines 6–12 are indented, so they
  run once for **each** day.

**Line 6** · `if cups >= 180:`: is this day's number 180 or more?

**Line 7** · If yes, `note` becomes `"busy"`. This line is indented again because it
belongs to the `if`.

**Line 8** · `elif cups >= 120:`: `elif` means "else, if". It's only checked when the
`if` above was False.

**Line 9** · If this one is true, `note` becomes `"normal"`.

**Line 10** · `else:` catches everything left over. No condition is needed.

**Line 11** · `note` becomes `"slow"`.

**Line 12** · `print(day, cups, note)` is indented **once** (4 spaces), so it belongs to
the `for`, not the `if`. It runs every day, whichever branch ran.

**Lines 14–15** · Start two counters at zero.

**Line 16** · `while savings < 50000:`: repeat the block below **as long as** savings are
under 50,000.

**Line 17** · Add 12,000 to savings. The right side is worked out first, then stored
back in the same variable.

**Line 18** · Count one more month.

**Line 19** · Not indented, so it runs once, **after** the loop finishes. After 5 months
savings are 60,000, which is no longer under 50,000, so the loop stops.

## If it didn't work

| You see | Fix |
|---|---|
| `IndentationError: expected an indented block` | The line after a `:` must be pushed right by 4 spaces. |
| `IndentationError: unindent does not match` | You mixed 3 and 4 spaces, or tabs and spaces. Select the lines and let VS Code fix the spacing, or retype the spaces. |
| The program never stops | A `while` whose condition never becomes False. Press **Ctrl + C**, then check that the loop changes the variable it tests. |

## Quiz

1. What's the difference between `=` and `==`?
2. If `cups` is 120, which note is chosen, and why not `"busy"`?
3. Change the `while` loop to save 15,000 a month. How many months does it take now?

---

**Next:** [1.5 · Functions](05-functions.md)

<details><summary>Quiz answers</summary>

1. `=` stores a value in a name; `==` asks whether two values are equal (True/False).
2. `"normal"`. 120 is not ≥ 180, so the `if` is False; 120 ≥ 120, so the `elif` is True.
3. 4 months (15,000 × 4 = 60,000).

</details>
