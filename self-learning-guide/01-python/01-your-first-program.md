# 1.1 · Your first program

**Time:** 15 minutes · **Before this:** [Part 0](../00-start-here/README.md).

## Read

A Python program is a **text file** whose name ends in `.py`. Inside are instructions,
one per line. When you **run** the file, Python reads it from the top line to the bottom
line and does each instruction in turn.

The most useful first instruction is `print`. It shows something on the screen.

## Do

1. Open VS Code. Choose **File → Open Folder** and open your `learning` folder.
2. Make a new folder inside it called `python` (we'll keep all Part 1 files there).
3. In VS Code, right-click the `python` folder → **New File** → name it `hello.py`.
4. Type these three lines exactly:

<!-- source: self-learning-guide/01-python/practice/hello.py:1-3 -->
```python
# My first Python program.
print("Hello, AI WarRoom!")
print("2 + 3 =", 2 + 3)
```

5. Save the file (**Ctrl + S**, or **Cmd + S** on a Mac).
6. Open the terminal (**Terminal → New Terminal**), go into the folder and run the file:

```bash
cd python
```

```bash
python hello.py
```

## Check

You should see exactly:

```text
Hello, AI WarRoom!
2 + 3 = 5
```

## Line by line

**Line 1** · `# My first Python program.`
A line that starts with `#` is a **comment**. Python ignores it completely. Comments are
notes for humans: they explain *why* the code is there.

**Line 2** · `print("Hello, AI WarRoom!")`
- `print` is a **function**: a ready-made command that does a job. Its job is to show
  things on the screen.
- The round brackets `( )` hold what we give to the function.
- `"Hello, AI WarRoom!"` is **text**. Text always goes inside quotes, so Python knows it
  is words to show and not code to run. Programmers call text a **string**.

**Line 3** · `print("2 + 3 =", 2 + 3)`
- We give `print` **two** things, separated by a comma.
- The first, `"2 + 3 ="`, is text in quotes, so it is shown exactly as written.
- The second, `2 + 3`, has no quotes, so Python **calculates** it and gets `5`.
- `print` puts a space between the things it shows. That's why you see `2 + 3 = 5`.

## If it didn't work

| You see | It means | Fix |
|---|---|---|
| `can't open file 'hello.py': No such file` | The terminal is in a different folder | Run `ls`. If you don't see `hello.py`, `cd` into the right folder. |
| `SyntaxError: unterminated string literal` | A quote is missing | Every `"` needs a partner `"` on the same line. |
| `NameError: name 'Print' is not defined` | You typed a capital P | Python cares about capital letters. Use `print`. |
| Nothing happens | The file wasn't saved | Press Ctrl + S, then run again. A white dot on the file's tab means "not saved". |

## Quiz

1. What does Python do with a line starting with `#`?
2. What will `print("5 + 5")` show? And `print(5 + 5)`?
3. Add a fourth line that prints your own name. Run it.

---

**Next:** [1.2 · Values and variables](02-values-and-variables.md)

<details><summary>Quiz answers</summary>

1. Ignores it. It's a comment for humans.
2. `5 + 5` (it's text in quotes) and `10` (it's a sum).
3. For example `print("Asha")`.

</details>
