# 11.4 · Docker: the image

**Time:** 50 minutes (plus download time) · **Before this:** [11.3](03-ready-for-production.md).

## Read

A `Dockerfile` is a recipe, read top to bottom. Each instruction makes a **layer** (a
saved step). When you build again, Docker **reuses** every layer whose inputs haven't
changed, which is why the recipe installs the requirements **before** copying your code:
change a Python file, and the slow "install everything" step is reused; only the quick
"copy the code" step runs again.

| Instruction | Means |
|---|---|
| `FROM` | Start from this ready-made image (here: Linux with Python 3.12) |
| `ENV` | Set an environment variable inside the image |
| `WORKDIR` | "cd" into this folder (create it if needed) |
| `COPY a b` | Copy files from your project into the image |
| `RUN` | Run a command while **building** |
| `USER` | Run everything after this as this user |
| `EXPOSE` | Note which port the app listens on |
| `CMD` | The command to run when a **container starts** |

`.dockerignore` is like `.gitignore`, for `COPY . .`: what **never** goes into the
image. Your `.env` above all.

## Do

### 1. Install Docker Desktop

Download it from **https://www.docker.com/products/docker-desktop/**, install it, and
start it. (On Windows it may ask to install or update **WSL**, Windows' Linux layer: say
yes, and restart if asked.) Wait until it says the engine is running. Then, in a terminal:

```bash
docker --version
```

`Docker version 29.3.1, build ...` (any recent version is fine).

### 2. `Dockerfile`

In `my-warroom` (next to `manage.py`), create a file called exactly `Dockerfile`, with no
extension:

<!-- source: Dockerfile:1-42 -->
```text
# AI WarRoom as a container image: the same box runs on a laptop and on a server.
#   docker build -t warroom .
#   docker compose up --build        (with a local PostgreSQL, see compose.yaml)

FROM python:3.12-slim

# Print logs straight away, don't write .pyc files, keep pip quiet and the image small,
# and be patient with slow networks (a classroom's Wi-Fi, say).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Dependencies first: this layer is reused until requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Then the code (.dockerignore keeps out .env, the virtual environment, the database...).
COPY . .

# Gather every static file into /app/staticfiles for WhiteNoise. Production settings
# insist on a secret key and a database URL, so give throwaway ones for this one command;
# collectstatic never connects to the database, and these values don't stay in the image.
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_SECRET_KEY=build-only-not-secret \
    DATABASE_URL=postgres://build:build@localhost:5432/build \
    python manage.py collectstatic --noinput

# Don't run as root: if the app were ever broken into, the intruder gets little.
RUN useradd --create-home --uid 10001 warroom
USER warroom

ENV DJANGO_SETTINGS_MODULE=config.settings.production \
    PORT=8000
EXPOSE 8000

# Bring the database up to date, then serve. Hosts like Render set PORT themselves.
# A long timeout because a website scan or an AI call can take 20 seconds or more.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi --bind 0.0.0.0:${PORT} --workers 2 --timeout 120 --access-logfile -"]
```

### 3. `.dockerignore`

<!-- source: .dockerignore:1-24 -->
```text
# Never copied into the image. Secrets above all: the host provides real ones.
.env
.env.*
!.env.example

# Local-only things the image doesn't need (and would only make it bigger)
.git
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
db.sqlite3
staticfiles/
media/
*.log
.vscode/
.idea/
.claude/
old_code/
self-learning-guide/
docs/
*.pdf
```

### 4. Build the image

```bash
docker build -t warroom .
```

The first build downloads Python's image and every package: a few minutes (much longer on
slow Wi-Fi: on our test, a very slow connection took about 15 minutes). Lines scroll past,
numbered `#1`, `#2`... Near the end you'll see a line with:

```text
naming to docker.io/library/warroom:latest
```

## Check

### The image exists

```bash
docker images warroom
```

One line: `warroom`, tag `latest`, and its size (about 360 MB on disk on our test).

### Your secrets are not inside

Run a throwaway container that just lists the app folder:

```bash
docker run --rm warroom ls -a
```

You see `manage.py`, `accounts`, `staticfiles`, `.env.example`... and **no** `.env`.
(`--rm` deletes the container when the command ends.)

### Django's own deploy check

Django has a checklist for production settings. Run it inside the image, giving it a
made-up key and database address just for the check:

```bash
docker run --rm -e DJANGO_SECRET_KEY=just-for-the-check -e DATABASE_URL=postgres://u:p@db.example:5432/app warroom python manage.py check --deploy
```

You get three warnings:

- **W009** says the secret key is too short and simple. True: `just-for-the-check` is a
  made-up key. The real one you'll make in lesson 11.7 is long and random, and this
  warning goes away.
- **W005** and **W021** are about HSTS "subdomains" and "preload". Leaving them off is on
  purpose: they promise browsers that **every** subdomain of your site will always use
  HTTPS, which isn't yours to promise on a shared address like `onrender.com`.

Everything else passes.

### Build again

Run `docker build -t warroom .` once more. It takes a second or two: every step says
`CACHED`. Change any `.py` file and build again: only the steps from `COPY . .` onwards
run.

## Line by line

- **Lines 1–3** · Comments: what this is and how to use it.
- **Line 5** · Start from the official Python 3.12 image, "slim" variant (Debian Linux
  without extras: smaller and with less to attack).
- **Lines 7–13** · Settings for Python and pip: print logs at once (so the host's log
  viewer shows them live), no `.pyc` files, don't keep pip's download cache (a smaller
  image), no "new pip version" notices, and wait up to 100 seconds for slow downloads.
  The `\` at a line's end continues the instruction on the next line.
- **Line 15** · Work in `/app`.
- **Lines 17–19** · Copy **only** `requirements.txt`, then install. This layer is reused
  until that file changes.
- **Lines 21–22** · Copy the project (minus `.dockerignore`'s list).
- **Lines 24–30** · Collect static files (lesson 11.3) with production settings.
  `production.py` refuses to load without a secret key and a database address, so this
  one command gets throwaway values. They exist only for that command: they're not saved
  in the image's settings, and `collectstatic` never connects to a database.
- **Lines 32–34** · Make an ordinary user and switch to it. The app then can't change
  system files, even if someone found a way to make it try.
- **Lines 36–37** · Use production settings, and port 8000 unless the host says
  otherwise (Render sets `PORT=10000`).
- **Line 38** · Document the port.
- **Lines 40–42** · When a container starts: apply any new migrations, **then**
  (`&&`: only if that worked) start gunicorn. `exec` makes gunicorn the main process, so
  stop signals reach it. `--bind 0.0.0.0:${PORT}`: listen on every network address (a
  container must, for traffic from outside to reach it). Two workers; up to 120 seconds
  per request (scans and AI calls are slow); log each request to the output.

### `.dockerignore`

- **Lines 1–4** · Secrets first: `.env` and any `.env.something`, but `.env.example` may
  go in (`!` means "except").
- **Lines 6–24** · Things the image doesn't need: Git's history, virtual environments
  (the image installs its own), caches, your local database and collected files, editor
  folders, and teaching material.

## If it didn't work

| You see | Fix |
|---|---|
| `failed to connect to the docker API` / `Is the docker daemon running?` | Start Docker Desktop and wait until it says the engine is running. |
| `Read timed out` or `No matching distribution found` during `pip install` | A slow or interrupted connection (it happened while we wrote this lesson). Run the build again: finished layers are reused. |
| `ImproperlyConfigured: DJANGO_SECRET_KEY must be set` during the build | Lines 27–30 must be **one** `RUN` instruction (each line but the last ends with `\`). |
| `.env` appears in `ls -a` | `.dockerignore` must sit next to the `Dockerfile` and its first lines must be `.env` and `.env.*`. Build again. |

## Quiz

1. Why is `requirements.txt` copied before the rest of the code?
2. What would happen without `.dockerignore`?
3. Why does the container run `migrate` before gunicorn?

---

**Next:** [11.5 · Docker Compose](05-docker-compose.md)

<details><summary>Quiz answers</summary>

1. So the slow install layer is reused when only code changes.
2. Your `.env` (with your secrets) and your local database would be copied into the
   image, and anyone with the image could read them.
3. So the database always matches the code before the first visitor arrives. The free
   Render plan has no shell to run it by hand.

</details>
