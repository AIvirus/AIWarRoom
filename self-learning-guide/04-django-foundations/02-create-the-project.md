# 4.2 · Create the project

**Time:** 40 minutes · **Before this:** [4.1](01-what-django-is.md).

## Read

In this lesson you set up the empty project: a folder, a virtual environment, the
packages, Git, and Django's starting skeleton. It's like preparing a kitchen before
cooking: lots of small steps, each one simple.

## Do

### Step 1 · Make the folder and virtual environment

In the terminal, go to your `learning` folder, then:

```bash
mkdir my-warroom
```

```bash
cd my-warroom
```

```bash
python -m venv .venv
```

Activate it (pick your terminal; see lesson 1.7):

```bash
.venv\Scripts\activate
```

(Windows PowerShell/Command Prompt. Git Bash: `source .venv/Scripts/activate`. Mac/Linux:
`source .venv/bin/activate`.)

Open the folder in VS Code (**File → Open Folder → my-warroom**). From now on, use the
terminal inside VS Code.

### Step 2 · List the packages

Create `requirements.txt` (the packages the app needs to run):

<!-- source: requirements.txt:1-11 -->
```text
# Runtime dependencies, pinned. Checked on Python 3.12 and 3.14 (2026-11-15).
Django==5.2.19              # LTS (supported to April 2028)
djangorestframework==3.18.3
dj-database-url==3.1.2      # parses DATABASE_URL (Neon) into Django settings
psycopg[binary]==3.3.9      # PostgreSQL driver
python-dotenv==1.2.4        # loads .env in development
pydantic==2.14.3            # validates every LLM response
google-genai==3.3.0         # official Gemini SDK (replaces deprecated google-generativeai)
requests==2.34.2            # URL analyzer HTTP client
beautifulsoup4==4.15.0      # readable-text extraction from HTML
whitenoise==6.12.0          # serves static files without a separate web server
```

and `requirements-dev.txt` (extra tools only developers need):

<!-- source: requirements-dev.txt:1-4 -->
```text
-r requirements.txt
pytest==9.2.0
pytest-django==4.14.0
ruff==0.17.5
```

Install everything:

```bash
pip install -r requirements-dev.txt
```

This takes a minute or two.

### Step 3 · Tell Git what to ignore

Create `.gitignore`:

<!-- source: .gitignore:1-4 -->
```text
# Secrets: never commit. Copy .env.example to .env instead.
.env
.env.*
!.env.example
```

then, in the **same file** below it, add:

<!-- source: .gitignore:9-30 -->
```text
# Python
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/

# Django
db.sqlite3
db.sqlite3-journal
staticfiles/
media/
*.log

# Editors / OS
.vscode/
.idea/
.DS_Store
Thumbs.db
```

and create `.gitattributes`:

<!-- source: .gitattributes:1-2 -->
```text
* text=auto eol=lf
*.docx binary
```

### Step 4 · Settings that change per computer: `.env`

Create `.env.example`. This is a **template** that is safe to share: no real secrets.

<!-- source: .env.example:1-26 -->
```text
# Copy to .env and fill in. Never commit .env.

# --- Django ---
DJANGO_SECRET_KEY=change-me-to-a-long-random-string
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
# Only needed in production behind HTTPS, e.g. https://warroom.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=

# --- Database ---
# Neon: copy the connection string from the Neon dashboard (keep ?sslmode=require).
# Leave empty to use a local SQLite file instead.
DATABASE_URL=
# Set to True to force SQLite even when DATABASE_URL is set (e.g. offline classroom).
USE_SQLITE=False

# --- Gemini (key from https://aistudio.google.com) ---
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
# Optional, paid plans only: a model with Google Search grounding for competitor lookups.
# On the free tier (Nov 2026) Search grounding has no quota; leave this empty.
GEMINI_GROUNDING_MODEL=
# Max live Gemini calls per day from this app (protects the free tier).
AI_DAILY_CALL_BUDGET=200
# Seconds before a Gemini request is abandoned (then retried up to twice).
AI_TIMEOUT_SECONDS=30
```

Now make your own private copy:

```bash
copy .env.example .env
```

(Mac/Linux/Git Bash: `cp .env.example .env`.)

Open `.env` and paste your Neon connection string from lesson 3.3 after `DATABASE_URL=`.
**Leave it empty if you want to work offline**: the app then uses a local SQLite file.

### Step 5 · Start Git

```bash
git init -b main
```

### Step 6 · Django's skeleton

```bash
django-admin startproject config .
```

Don't forget the dot at the end.

Now create the five apps:

```bash
django-admin startapp accounts
```

```bash
django-admin startapp businesses
```

```bash
django-admin startapp simulations
```

```bash
django-admin startapp intelligence
```

```bash
django-admin startapp decisions
```

Tidy up the files we won't use or will write later:
- Delete `tests.py` in **all five** app folders (we keep tests in a `tests/` folder instead).
- In `businesses`, `simulations`, `intelligence` and `decisions`, also delete `admin.py`,
  `models.py` and `views.py`. We'll write them ourselves in Parts 5–10. (Keep
  `__init__.py`, `apps.py` and `migrations/`.)

Finally, copy the **`static`** folder from the reference project into `my-warroom`. It
holds the fonts, the CSS (the look) and the JavaScript (the interactive parts). You'll
study the CSS and JavaScript in Part 10, and they don't change how the Python works.

## Check

Your folder should now look like this (VS Code's Explorer on the left):

```text
my-warroom/
├── .venv/
├── accounts/            ← admin.py, apps.py, models.py, views.py, migrations/
├── businesses/          ← apps.py, migrations/
├── config/              ← settings.py, urls.py, asgi.py, wsgi.py
├── decisions/
├── intelligence/
├── simulations/
├── static/              ← css/, fonts/, js/, vendor/
├── .env
├── .env.example
├── .gitattributes
├── .gitignore
├── manage.py
├── requirements-dev.txt
└── requirements.txt
```

Run `git status`. You should **not** see `.env` or `.venv` listed: Git is ignoring them.
That proves your secret is safe.

## Line by line

### `requirements.txt`

Each line is `package==version`. The `==` **pins** an exact version, so everyone who
installs gets the same code, and nothing changes behind your back.

| Line | Package | Why AI WarRoom needs it |
|---|---|---|
| 1 | (comment) | Says the versions were checked on Python 3.12 and 3.14. |
| 2 | `Django` | The web framework. 5.2 is an **LTS** (Long Term Support) version: it gets security fixes until April 2028. |
| 3 | `djangorestframework` | Builds the JSON API (lesson 4.1). |
| 4 | `dj-database-url` | Turns the one-line `DATABASE_URL` into Django's database settings. |
| 5 | `psycopg[binary]` | Talks to PostgreSQL (you used it in 3.3). |
| 6 | `python-dotenv` | Reads `.env` (you used it in 3.3). |
| 7 | `pydantic` | Checks that the AI's answers have exactly the right shape (Part 7). |
| 8 | `google-genai` | Google's official package for Gemini (Part 7). |
| 9 | `requests` | Downloads web pages (Part 8). |
| 10 | `beautifulsoup4` | Pulls readable text out of web pages (Part 8). |
| 11 | `whitenoise` | Lets Django serve the CSS, fonts and JS files itself. |

Text after `#` on a line is a comment, just as in Python.

### `requirements-dev.txt`

| Line | Meaning |
|---|---|
| 1 | `-r requirements.txt`: "first install everything in that file". |
| 2 | `pytest`: runs tests (lesson 1.10). |
| 3 | `pytest-django`: teaches pytest about Django (a test database, a test browser). |
| 4 | `ruff`: checks code style and catches common mistakes, and can fix formatting. |

### `.gitignore`

Each line is a pattern for files Git must **never** save.

| Lines | Meaning |
|---|---|
| 1 | Comment. |
| 2 | `.env`: your secrets file. The most important line in the file. |
| 3 | `.env.*`: any variation, like `.env.production`. |
| 4 | `!.env.example`: `!` means "except this one": the template is safe to share. |
| 9–17 | Python's temporary files: `__pycache__/` (compiled code), `*.py[cod]` (files ending `.pyc`, `.pyo`, `.pyd`), your venvs, and the caches pytest and ruff make. A `/` at the end means "a folder". |
| 19–24 | Django's local files: the SQLite database, collected static files, uploads, logs. |
| 26–30 | Editor and operating-system clutter, such as macOS's `.DS_Store` and Windows' `Thumbs.db`. |

### `.gitattributes`

| Line | Meaning |
|---|---|
| 1 | `* text=auto eol=lf`: store text files with Unix-style line endings (LF). Windows uses CRLF; without this line Git prints dozens of "LF will be replaced by CRLF" warnings. |
| 2 | Word documents are binary: never touch their bytes. |

### `.env.example`

Each line is `NAME=value`. Lines starting with `#` are comments.

| Lines | Setting | Meaning |
|---|---|---|
| 4 | `DJANGO_SECRET_KEY` | A long secret Django uses to sign cookies, so nobody can forge a login. In production it **must** be a real random string. |
| 5 | `DJANGO_DEBUG` | `True` shows detailed error pages, which is helpful on your laptop and dangerous on the internet. |
| 6 | `DJANGO_ALLOWED_HOSTS` | Which addresses this site answers to. |
| 8 | `DJANGO_CSRF_TRUSTED_ORIGINS` | Needed later when the site runs on a real `https://` address. |
| 13 | `DATABASE_URL` | Your Neon string, or empty for SQLite. |
| 15 | `USE_SQLITE` | `True` forces SQLite even if a URL is set, for offline days. |
| 18–26 | Gemini settings | Used in Part 7. Leave them as they are for now. |

### The commands

| Command | Meaning |
|---|---|
| `pip install -r requirements-dev.txt` | `-r` means "read the list from this file". |
| `copy .env.example .env` | Copy the template to your private file. |
| `git init -b main` | Start a Git history in this folder; name the main branch `main`. |
| `django-admin startproject config .` | Create Django's starting files. `config` is the folder name for settings; `.` means "put `manage.py` here, not in a new folder". |
| `django-admin startapp accounts` | Create an app folder with starter files. |

## If it didn't work

| You see | Fix |
|---|---|
| `django-admin: command not found` | Activate the venv first: `(.venv)` must show in the prompt. |
| `CommandError: ... conflicts with the name of an existing Python module` | Check the spelling; app names must be new words like `accounts`. |
| You made `my-warroom/config/config/` (folders inside each other) | You forgot the `.` in `startproject`. Delete `config` and the inner `manage.py`, and run it again with the dot. |
| `git status` lists `.env` | The `.gitignore` has a typo, or isn't saved, or is named `gitignore` (missing the dot). |

## Quiz

1. Why do we pin versions with `==`?
2. What's the difference between `.env` and `.env.example`?
3. Why do we delete `models.py` in four apps for now?

---

**Next:** [4.3 · Settings, line by line](03-settings.md)

<details><summary>Quiz answers</summary>

1. So everyone gets exactly the same package code, and nothing changes unexpectedly.
2. `.env` holds **your** real values and secrets and is never shared; `.env.example` is a
   safe template that shows which settings exist.
3. They'd be empty files with an unused import (the linter complains). We write the real
   ones later.

</details>
