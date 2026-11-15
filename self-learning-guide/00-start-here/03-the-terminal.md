# 0.3 · The terminal

**Time:** 20 minutes · **Before this:** [0.2](02-install-your-tools.md).

## 📖 Read

The **terminal** is a window where you type commands instead of clicking. It looks
old-fashioned, but it is fast and exact, and every tool in this guide is started from it.

At any moment the terminal is "standing" in one folder, called the **current folder**
(or **working directory**). Commands work on that folder unless you say otherwise. It's
like being in one room of a house: to work in the kitchen, you first walk to the kitchen.

In VS Code, open a terminal with the menu **Terminal → New Terminal**. It appears at the
bottom of the window.

> **Which terminal?** On Windows, VS Code may open **PowerShell**. The commands in this
> guide work in PowerShell, and also in **Git Bash** (installed with Git). Where they
> differ, the guide shows both.

## ⌨️ Do

Type each command, press **Enter**, and look at what happens.

**1. Where am I?**

```bash
pwd
```

**2. What's in this folder?**

```bash
ls
```

**3. Go into your `learning` folder** (the one you made in lesson 0.1). If it's on your
Desktop:

```bash
cd Desktop/learning
```

**4. Make a new folder for practice, and go into it:**

```bash
mkdir practice
```

```bash
cd practice
```

**5. Go back up one folder:**

```bash
cd ..
```

**6. Run a tiny Python command without making a file:**

```bash
python -c "print(2 + 3)"
```

**7. Clear the screen when it gets messy:**

```bash
clear
```

## ✅ Check

- After `pwd` you saw a path such as `C:\Users\asha\Desktop\learning`.
- After `mkdir practice` and `ls`, `practice` appeared in the list.
- `python -c "print(2 + 3)"` printed `5`.

## 🔍 Line by line

| Command | What it means |
|---|---|
| `pwd` | **P**rint **W**orking **D**irectory: shows the folder you're standing in. |
| `ls` | **L**i**s**t: shows the files and folders here. |
| `cd Desktop/learning` | **C**hange **D**irectory: walk into `Desktop`, then into `learning`. The `/` separates folder names. |
| `mkdir practice` | **M**a**k**e **dir**ectory: create a new folder called `practice`. |
| `cd practice` | Walk into the new folder. |
| `cd ..` | `..` always means "the folder above this one". |
| `python -c "print(2 + 3)"` | Run Python. `-c` means "run the code I give you in quotes". `print(...)` shows the result on the screen. |
| `clear` | Wipe the screen. Your files are not touched. |

**Handy tricks**

- Press **Tab** while typing a folder name: the terminal finishes it for you.
- Press the **↑ (up arrow)** key to bring back the last command.
- Press **Ctrl + C** to stop a program that is running. You'll use this to stop the
  web server later.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `cannot find path` / `No such file or directory` after `cd` | Check the spelling, then run `ls` to see which folders really exist here. |
| A folder name has a space, like `My Files` | Put it in quotes: `cd "My Files"`. |
| `clear` does nothing in old Windows terminals | Use `cls` instead. |

## ❓ Quiz

1. Which command shows the folder you're in?
2. What does `cd ..` do?
3. How do you stop a running program?

---

**Part 0 done! 🎉** Next: [Part 1 · Python from zero](../01-python/README.md)

<details><summary>Quiz answers</summary>

1. `pwd`.
2. Moves you up to the folder above.
3. **Ctrl + C**.

</details>
