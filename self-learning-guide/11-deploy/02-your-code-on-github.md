# 11.2 · Your code on GitHub

**Time:** 30 minutes · **Before this:** [11.1](01-what-deploying-means.md).

## Read

Since Part 4 your project has a Git **history** on your computer: seven commits, one per
part. **GitHub** keeps a copy of that history online. Git calls an online copy a
**remote**, and the usual name for your main remote is `origin`.

- `git push` sends your new commits **to** GitHub.
- `git pull` brings commits **from** GitHub (for example, ones you made on another
  computer).

A repository on GitHub can be **private** (only you, and people you invite) or **public**
(anyone can read it). For a class project, private is a safe default; you can make it
public later to show it off.

## Do

### 1. Check no secret is in your history

In `my-warroom`:

```bash
git check-ignore .env
```

It must print `.env`. Then list every file Git tracks:

```bash
git ls-files
```

Read the list. You should see `.env.example` but **not** `.env`, `db.sqlite3` or anything
in `.venv`. (If `.env` is listed, stop and see "If it didn't work" below.)

### 2. Make an empty repository on GitHub

1. Sign in at **https://github.com** (or create a free account).
2. Click **+** (top right) → **New repository**.
3. **Repository name:** `my-warroom`. Choose **Private**.
4. Leave "Add a README", ".gitignore" and "license" **unticked**: your project already
   has its own files, and an empty repository is easiest to push into.
5. Click **Create repository**. GitHub shows a page of commands; you need its address,
   which looks like `https://github.com/YOUR-NAME/my-warroom.git`.

### 3. Connect and push

Replace `YOUR-NAME` with your GitHub username:

```bash
git remote add origin https://github.com/YOUR-NAME/my-warroom.git
```

```bash
git push -u origin main
```

The first time, Git asks you to sign in:

- **Windows** (Git for Windows): a window opens; choose **Sign in with your browser**
  and approve it in the browser.
- **Mac or Linux:** the simplest way is GitHub's own tool. Install **GitHub CLI** from
  https://cli.github.com, run `gh auth login`, answer its questions (GitHub.com, HTTPS,
  log in with a web browser), then run `git push -u origin main` again.

Never type your GitHub **password** into the terminal: GitHub doesn't accept it for Git
any more.

## Check

The push ends with a line like:

```text
branch 'main' set up to track 'origin/main'.
```

Refresh your repository's page on GitHub. You see your folders (`accounts`,
`businesses`, `config`...), and **Commits** shows your seven commits. Open `.env.example`:
it's there, with placeholders only. Search for `.env` in the file list: there is **no**
`.env`.

From now on, after each commit:

```bash
git push
```

(`-u` the first time remembered that `main` goes to `origin`, so plain `git push` is
enough.)

## Line by line

| Command | What it does |
|---|---|
| `git check-ignore .env` | Asks "would Git ignore this file?" Printing the name means yes. |
| `git ls-files` | Lists every file Git is tracking: exactly what a push uploads. |
| `git remote add origin <address>` | Remember this GitHub address under the name `origin`. Nothing is sent yet. |
| `git push -u origin main` | Send the `main` branch's commits to `origin`. `-u` ("upstream") links your `main` to GitHub's, so later `git push` and `git pull` know where to go. |

## If it didn't work

| You see | Fix |
|---|---|
| `.env` **is** in `git ls-files` | It was committed before `.gitignore` covered it. Run `git rm --cached .env`, commit, and **change every secret in it** (a new Django key, a new Neon password, a new Gemini key), because the old values are in your history. |
| `remote origin already exists` | You ran `remote add` twice. Fix the address with `git remote set-url origin <address>`. |
| `error: src refspec main does not match any` | Your branch has another name. `git branch` shows it; rename it with `git branch -M main`. |
| `Updates were rejected because the remote contains work...` | The GitHub repository wasn't empty (a README was added). Make a new empty one, or ask your teacher about `git pull --rebase`. |
| `Authentication failed` | Sign in again with the browser (Windows) or `gh auth login` (Mac/Linux). |

## Quiz

1. What is `origin`?
2. Why check `git ls-files` before the first push?
3. Why choose a private repository at first?

---

**Next:** [11.3 · Ready for production](03-ready-for-production.md)

<details><summary>Quiz answers</summary>

1. The name of your remote: the GitHub copy of your repository.
2. It's exactly what will be uploaded; a secret listed there would go public (or at least
   online).
3. Nobody else can see it until you decide; making it public later is one click.

</details>
