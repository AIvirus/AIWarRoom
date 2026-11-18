# 0.2 · Install your tools

**Time:** 30 minutes · **Before this:** [0.1](01-how-this-guide-works.md).

## Read

You need three free tools. Every professional programmer uses all three.

| Tool | What it is | Everyday comparison |
|---|---|---|
| **Python** | The programming language we write in, plus the program that runs our code | The language of the recipe, and the cook who follows it |
| **VS Code** | An editor: a notebook made for writing code | A notebook that highlights mistakes and numbers every line |
| **Git** | Saves snapshots of your work so you can go back in time | "Save game" in a video game |

## Do

### Step 1 · Install Python (version 3.12 or newer)

**Windows**

1. Open https://www.python.org/downloads/ and click the big yellow **Download Python**
   button.
2. Open the downloaded file.
3. **Very important:** on the first screen, tick the box **"Add python.exe to PATH"**.
   If you forget this, typing `python` in the terminal won't work.
4. Click **Install Now**. Wait until it says "Setup was successful".

**Mac**

1. Open https://www.python.org/downloads/ and download the macOS installer.
2. Open it and click **Continue** until it finishes.
3. On a Mac, the command is usually `python3` instead of `python`. Wherever this guide
   says `python`, type `python3`.

**Linux (Ubuntu)**

Python 3 is usually already installed. Check in the terminal with `python3 --version`.
If it is older than 3.12, ask your teacher or search "install Python 3.12 Ubuntu".

### Step 2 · Install VS Code

1. Open https://code.visualstudio.com/ and download it for your computer.
2. Install it with the normal options.
3. Open VS Code. On the left side, click the **Extensions** icon (four little squares).
4. Search for **Python** and install the one made by **Microsoft**. It helps VS Code
   understand Python code.

### Step 3 · Install Git

- **Windows:** download from https://git-scm.com/download/win and install with all the
  default options (just keep clicking **Next**). This also gives you **Git Bash**, a
  terminal we can use.
- **Mac:** open the Terminal app and type `git --version`. If Git isn't there, the Mac
  offers to install it. Click **Install**.
- **Linux:** `sudo apt install git`.

### Step 4 · Tell Git your name

Git writes your name on every snapshot you save. Open a terminal (VS Code: menu
**Terminal → New Terminal**) and type these two lines, using your own name and email:

```bash
git config --global user.name "Your Name"
```

```bash
git config --global user.email "you@example.com"
```

## Check

In the VS Code terminal, type each line and press Enter:

```bash
python --version
```

You should see something like `Python 3.12.4` (any number 3.12 or bigger is fine).

```bash
git --version
```

You should see something like `git version 2.43.0`.

## Line by line

| Line | What it means |
|---|---|
| `python --version` | Run the program called `python` and ask only for its version number. `--version` is an **option**: extra words that change what a command does. |
| `git --version` | The same, for Git. |
| `git config --global user.name "Your Name"` | `git config` changes Git's settings. `--global` means "for every project on this computer". `user.name` is the setting's name. The quotes keep your first and last name together as one value. |
| `git config --global user.email "you@example.com"` | The same, for your email. |

## If it didn't work

| You see | It means | Fix |
|---|---|---|
| `'python' is not recognized...` (Windows) | Python isn't on your PATH: the box in Step 1 wasn't ticked | Run the installer again, choose **Modify**, and tick **Add Python to environment variables**. Or try `py --version`. |
| `command not found: python` (Mac) | Macs call it `python3` | Use `python3 --version`. |
| `Python 3.9.x` or older | An old Python is being used | Install 3.12 from python.org, then close and reopen VS Code. |
| VS Code terminal still says "not recognized" after installing | The terminal opened before the install finished | Close VS Code completely and open it again. |

## Quiz

1. Which tool runs our code: Python, VS Code or Git?
2. Which box must you tick when installing Python on Windows?
3. What does `--version` do?

---

**Next:** [0.3 · The terminal](03-the-terminal.md)

<details><summary>Quiz answers</summary>

1. Python. VS Code is where we write; Git saves snapshots.
2. **Add python.exe to PATH**.
3. It's an option that asks a program to print its version number and stop.

</details>
