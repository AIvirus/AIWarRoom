# 1.7 · Files, modules and packages

**Time:** 40 minutes · **Before this:** [1.6](06-classes-and-dataclasses.md).

## Read

### Modules: code in other files

Big programs are split into many files. Each `.py` file is a **module**. One file can
use the functions of another with `import`. AI WarRoom has about 100 Python files that
import from each other.

```python
from money_tools import rupees
```

means: "open the file `money_tools.py`, and give me its `rupees` function".

### Packages: code other people wrote

A **package** is a bundle of modules someone else wrote and shared, like Django (to build
websites) or pytest (to test code). You download packages with **pip**, Python's package
installer.

### Virtual environments: one toolbox per project

If every project put its packages in one shared place, two projects needing different
versions would fight. So each project gets its own private toolbox, called a **virtual
environment** (venv): a folder (usually `.venv`) holding Python plus that project's
packages.

**Rule:** make a venv once per project, and **activate** it every time you open a new
terminal for that project.

## Do

### Part A · Your own module

Make `money_tools.py`:

<!-- source: self-learning-guide/01-python/practice/money_tools.py:1-13 -->
```python
# A module: a Python file whose functions other files can import.
def rupees(amount):
    """Show an amount the Indian way, like 1,23,456."""
    whole = str(int(round(amount)))
    if len(whole) <= 3:
        return "₹" + whole
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    groups.insert(0, head)
    return "₹" + ",".join(groups) + "," + tail
```

and `use_money_tools.py` **in the same folder**:

<!-- source: self-learning-guide/01-python/practice/use_money_tools.py:1-6 -->
```python
# Using a function from another file.
from money_tools import rupees

print(rupees(450))
print(rupees(123456))
print(rupees(12345678))
```

```bash
python use_money_tools.py
```

You should see:

```text
₹450
₹1,23,456
₹1,23,45,678
```

> On some Windows terminals the ₹ sign shows as `?`. That's only the terminal's display:
> the code is fine. Run `chcp 65001` once to switch the terminal to Unicode.

### Part B · Your first virtual environment and package

In your `python` folder:

```bash
python -m venv .venv
```

Then **activate** it. Pick the line for your terminal:

```bash
.venv\Scripts\activate
```

(Windows PowerShell or Command Prompt.)

```bash
source .venv/Scripts/activate
```

(Windows Git Bash.)

```bash
source .venv/bin/activate
```

(Mac and Linux.)

Your prompt now starts with `(.venv)`. Install pytest, which we need in lesson 1.10:

```bash
pip install pytest
```

Check:

```bash
pip list
```

You should see `pytest` in the list.

## Line by line

### `money_tools.py`

**Line 2** · Define `rupees`, which takes an amount.

**Line 3** · The docstring.

**Line 4** · `str(int(round(amount)))`, read from the inside out:
`round(1234.6)` → `1235`; `int(...)` makes sure it's a whole number; `str(...)` turns
it into **text** (`"1235"`) so we can cut it into pieces.

**Line 5** · `len(whole) <= 3`: three digits or fewer need no commas.

**Line 6** · Return `₹` joined to the digits. `+` between two strings glues them together.

**Line 7** · `head, tail = whole[:-3], whole[-3:]`
- `whole[-3:]` is a **slice**: "from the 3rd-last character to the end", which is the
  last 3 digits.
- `whole[:-3]` is "everything except the last 3".
- Writing `a, b = x, y` stores two values at once.
- For `"123456"`: head = `"123"`, tail = `"456"`.

**Line 8** · An empty list to collect groups of two digits.

**Line 9** · While more than 2 digits are left in `head`...

**Line 10** · ...put the last 2 of them at the **front** of `groups`
(`insert(0, ...)` means "at position 0").

**Line 11** · ...and remove those 2 from `head`.

**Line 12** · Whatever is left (1 or 2 digits) goes at the front.

**Line 13** · `",".join(groups)` glues the groups with commas, then we add the tail.
For 12345678: groups `["1", "23", "45"]` → `"1,23,45"` + `",678"`.

### `use_money_tools.py`

**Line 2** · `from money_tools import rupees`: Python finds `money_tools.py` **in the same
folder** and takes the `rupees` function from it. The `.py` is not written.

**Lines 4–6** · Use it three times.

### The commands

| Command | Meaning |
|---|---|
| `python -m venv .venv` | `-m venv` runs Python's built-in "make a venv" tool; `.venv` is the folder name it creates. |
| `.venv\Scripts\activate` | Switch this terminal to the project's private Python. Lasts until you close the terminal. |
| `pip install pytest` | Download pytest from the internet and put it in the active venv. |
| `pip list` | Show every package in the active venv. |

## If it didn't work

| You see | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'money_tools'` | Both files must be in the same folder, and you must run from that folder. |
| `running scripts is disabled on this system` (PowerShell) | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, then activate again. |
| No `(.venv)` at the start of the prompt | The venv isn't active. Run the activate line again. |
| `pip: command not found` | Use `python -m pip install pytest`. |

## Quiz

1. What's the difference between a module and a package?
2. Why does each project get its own virtual environment?
3. What must you do every time you open a new terminal for a project?

---

**Next:** [1.8 · Money with Decimal](08-money-with-decimal.md)

<details><summary>Quiz answers</summary>

1. A module is one `.py` file. A package is a shared bundle of modules (often someone
   else's) that you install with pip.
2. So projects needing different package versions don't clash.
3. Activate its venv.

</details>
