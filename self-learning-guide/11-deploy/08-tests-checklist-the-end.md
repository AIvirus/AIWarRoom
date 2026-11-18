# 11.8 · Tests, checklist, the end

**Time:** 40 minutes · **Before this:** [11.7](07-on-the-internet.md).

## Read

Deploy files are code too, and their mistakes are the expensive kind: a secret copied into
an image, a server that never migrates, an unsafe setting that slipped through. Five small
tests guard them. Two of them load `production.py` and `docker_local.py` **for real**,
with made-up environment variables, and check their switches.

## Do

### 1. The tests

**Copy** this file from the reference project into `config/tests/` (make the folder with
an empty `__init__.py` if you don't have it):

<!-- source: config/tests/test_deploy_files.py:1-64 -->
```python
"""
The deploy files are code too. These checks catch the mistakes that hurt most once the
app is on the internet: a secret copied into the image, or an unsafe setting.
"""

import importlib
import runpy
import sys
from pathlib import Path

import pytest
from django.conf import settings

ROOT = Path(settings.BASE_DIR)


def lines(name: str) -> list[str]:
    return [line.strip() for line in (ROOT / name).read_text(encoding="utf-8").splitlines()]


def test_secrets_never_go_into_the_image_or_the_repository():
    for name in (".dockerignore", ".gitignore"):
        assert ".env" in lines(name), f"{name} must exclude .env"
    assert "COPY .env" not in (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_image_runs_as_a_normal_user_and_migrates_before_serving():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "\nUSER " in dockerfile
    assert "migrate --noinput && exec gunicorn" in dockerfile
    assert "0.0.0.0:${PORT}" in dockerfile  # hosts such as Render choose the port


def test_production_server_is_installed():
    assert any(line.startswith("gunicorn==") for line in lines("requirements.txt"))


@pytest.fixture
def production_env(monkeypatch):
    """Made-up production values, whatever your own .env says; put everything back after."""
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@db.example:5432/app")
    monkeypatch.setenv("USE_SQLITE", "False")
    base = importlib.import_module("config.settings.base")
    importlib.reload(base)  # base.py reads the environment when it runs, so run it again
    sys.modules.pop("config.settings.production", None)
    yield
    monkeypatch.undo()
    importlib.reload(base)
    sys.modules.pop("config.settings.production", None)


def test_production_settings_stay_strict(production_env):
    production = runpy.run_module("config.settings.production")
    assert production["DEBUG"] is False
    assert production["SECURE_SSL_REDIRECT"] and production["SESSION_COOKIE_SECURE"]
    assert production["DATABASES"]["default"]["OPTIONS"]["sslmode"] == "require"


def test_local_docker_settings_only_relax_https_and_database_ssl(production_env):
    local = runpy.run_module("config.settings.docker_local")
    assert local["DEBUG"] is False  # still production in every other way
    assert local["SECURE_SSL_REDIRECT"] is False and local["SESSION_COOKIE_SECURE"] is False
    assert "sslmode" not in local["DATABASES"]["default"]["OPTIONS"]
```

### 2. Run, tidy, commit, push

```bash
pytest
```

```bash
ruff format .
```

```bash
ruff check .
```

```bash
git add -A
```

```bash
git commit -m "Part 11: deploy"
```

```bash
git push
```

## Check

- `pytest` prints `272 passed` (267 + 5).
- GitHub shows a green tick for the commit, and Render deploys it.

**Try breaking it on purpose:** delete the `.env` line (line 2) from `.dockerignore` and
run `pytest`. `test_secrets_never_go_into_the_image_or_the_repository` fails with
".dockerignore must exclude .env". Put it back.

## Line by line

- **Lines 1–4** · Docstring: why test deploy files.
- **Lines 6–12** · `importlib` (run a module again), `runpy` (run a module fresh and get
  its names), `sys` (the list of loaded modules), `Path`, pytest, and Django's settings
  (for `BASE_DIR`, the project folder).
- **Lines 17–18** · `lines(name)`: a file's lines, with spaces trimmed.
- **Lines 21–24** · `.env` must be in both `.dockerignore` and `.gitignore`, and the
  Dockerfile must never copy it on purpose.
- **Lines 27–31** · The image switches to a normal user, migrates before serving, and
  binds to the host's `PORT`.
- **Lines 34–35** · gunicorn is in the requirements.
- **Lines 38–50** · A fixture that sets made-up production values (`monkeypatch.setenv`,
  for this test only), then runs `base.py` again so it reads them, and forgets any loaded
  `production.py`. After the test (`yield`), it puts everything back. Without this, the
  result would depend on **your** `.env`, and the test could pass on your computer but
  fail on GitHub.
- **Lines 53–57** · Run `production.py` fresh and check: `DEBUG` off, HTTPS redirect,
  secure cookies, and SSL required for the database.
- **Lines 60–64** · The same for `docker_local.py`: still `DEBUG` off, but no HTTPS
  redirect, plain-HTTP cookies, and no database SSL; nothing else relaxed.

## The safety checklist

Before you share your live address, check each line:

- [ ] `.env` is in `.gitignore` **and** `.dockerignore`, and `git ls-files` doesn't list it.
- [ ] The live site uses its **own** secret key and its **own** database.
- [ ] `/no-such-page/` on the live site shows a plain "Not Found" (debug is off).
- [ ] `http://` redirects to `https://`.
- [ ] `AI_DAILY_CALL_BUDGET` is set to a number you're happy to spend.
- [ ] GitHub shows a green tick for your latest commit.
- [ ] If any secret ever leaked: you made a new one and deleted the old one.

## You've finished

Look at what you built, starting from "what is a variable?":

- A **Django** app with users, organizations and data that never leaks between them.
- A **PostgreSQL** database on Neon, changed only through migrations.
- A **simulation engine** in plain Python with exact money maths, and over 100 tests.
- **Gemini**, used carefully: data as data, strict schemas, one repair, flagged numbers,
  a cache and a budget, and a label on every answer.
- A **website reader** that won't be turned against its own network.
- **Human decisions** with a history and a printable brief.
- **Pages**, sliders, charts and a 3D system view, drawing only the engine's numbers.
- **Docker**, **CI** and a live **https://** address.

Almost every line of it is explained in this guide, and you typed most of them.

### Where to go next

- **Make it yours.** Add a new disruption template to the catalogue (a power cut? a
  supplier price rise?), with tests first.
- **Read the docs** you now understand: https://docs.djangoproject.com,
  https://www.django-rest-framework.org, https://threejs.org/manual/.
- **Read the reference project's `docs/` folder**: the design notes explain decisions the
  lessons only touched on.
- **Show someone.** Make your GitHub repository public, put the live address in its README,
  and explain one design choice you'd defend.

When something breaks (it will), do what you learned here: read the last line of the
error, find the file and line it names, change one thing, run the tests.
