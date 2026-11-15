# 11.6 · Checks on every push

**Time:** 25 minutes · **Before this:** [11.5](05-docker-compose.md).

## 📖 Read

Before every commit you've run `ruff check`, `ruff format` and `pytest`. It's easy to
forget once. **GitHub Actions** can run them **for** you, on GitHub's own computers, every
time you push. This is called **CI** (continuous integration).

You describe the job in a **workflow** file written in **YAML** (the same format as
`compose.yaml`: names, colons, and indentation for nesting). GitHub finds it because it
lives in `.github/workflows/`.

On GitHub, each commit then gets a mark:

| Mark | Means |
|---|---|
| 🟡 dot | The checks are running |
| ✅ tick | Everything passed |
| ❌ cross | Something failed: click it to see which step and why |

Free accounts get plenty of Actions minutes for a project like this (public repositories
have no limit).

## ⌨️ Do

Make the folders `.github/workflows/` (note the dot at the start of `.github`), then create
`.github/workflows/ci.yml`:

<!-- source: .github/workflows/ci.yml:1-22 -->
```yaml
# Runs on GitHub's computers for every push and pull request: the same checks you run
# by hand before committing. A red cross on GitHub means one of them failed.
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements-dev.txt
      - run: ruff check .
      - run: ruff format --check .
      - run: pytest
      - run: docker build -t warroom .
```

Commit and push:

```bash
git add -A
```

```bash
git commit -m "Add Docker files and CI"
```

```bash
git push
```

## ✅ Check

1. On your repository's GitHub page, click the **Actions** tab. A run called "Add Docker
   files and CI" appears with a 🟡 dot.
2. Click it, then the **test** job: each step is listed, with its output when you click
   it. After a few minutes every step has a ✅, and so does your commit on the repository's
   front page.
3. **See it fail on purpose** (optional): change a test so it fails, commit, push, and
   watch the ❌ appear, with the failing test's name in the `pytest` step. Then put it back,
   commit and push again.

## 🔍 Line by line

- **Lines 1–2** · Comments: where it runs and what a red cross means.
- **Line 3** · The workflow's name, shown in the Actions tab.
- **Lines 5–7** · `on:` when to run: on every **push**, and on every **pull request** (a
  proposed change, often from someone else).
- **Lines 9–10** · `jobs:` the work. One job here, called `test`.
- **Line 11** · Run it on a fresh Ubuntu Linux machine, created just for this run and
  thrown away afterwards.
- **Line 12** · `steps:` in order. If one fails, the rest are skipped and the run is ❌.
- **Line 13** · `uses:` a ready-made step: download your repository's code.
- **Lines 14–17** · Another ready-made step: install Python 3.12, and remember downloaded
  packages between runs (`cache: pip`) so later runs are quicker.
- **Line 18** · `run:` a command, as in your terminal: install the requirements.
- **Lines 19–21** · The same three checks you run by hand. On GitHub's fresh machine
  there's no `.env` and no Neon, so the tests use their in-memory SQLite (lesson 4.3), and
  the fake Gemini and fake websites (Parts 7–8).
- **Line 22** · Build the Docker image, to prove the `Dockerfile` still works.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| No run appears in the Actions tab | The file must be exactly `.github/workflows/ci.yml`. Check `git ls-files` lists it. |
| `Invalid workflow file` | YAML is strict about indentation: spaces only, two per level, lined up exactly as above. |
| `ruff format --check` fails on GitHub but you didn't notice | You forgot `ruff format .` before committing. Run it, commit, push. |
| A test passes on your computer but fails on GitHub | It may depend on something only your computer has (a file, your `.env`). Tests must not. |

## ❓ Quiz

1. When does this workflow run?
2. Why don't the tests need your Neon database or Gemini key on GitHub?
3. What does a ❌ next to a commit tell you?

---

**Next:** [11.7 · On the internet](07-on-the-internet.md)

<details><summary>Quiz answers</summary>

1. On every push and every pull request.
2. They use an in-memory SQLite database and fake Gemini/website stand-ins.
3. One of the steps failed for that commit; click it to see which and why.

</details>
