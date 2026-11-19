# 4.3 · Settings, line by line

**Time:** 45 minutes · **Before this:** [4.2](02-create-the-project.md).

## Read

**Settings** are the switches and dials of a Django project: which database, which apps,
where templates live, how passwords are checked, and so on.

AI WarRoom runs in three places, which need slightly different settings:

| Where | File | What's special |
|---|---|---|
| Your laptop | `local.py` | Helpful error pages; the API has a clickable web view |
| The internet | `production.py` | Strict: HTTPS only, and refuses to start if a secret is missing |
| Tests | `test.py` | A fast throwaway database in memory |

All three start from `base.py`, the settings shared by everyone, and change only what's
different. So instead of Django's single `settings.py`, we make a **folder** of settings.

## Do

1. Delete `config/settings.py`.
2. Make a folder `config/settings/` with an empty file `__init__.py` inside. (An
   `__init__.py` file turns a folder into a Python **package**, so `config.settings.base`
   can be imported.)
3. Create the four settings files. Their full code is further down this page, each under
   its own heading: `config/settings/base.py`, `local.py`, `production.py` and
   `test.py`. `base.py` is long, so it comes in **four code blocks**. Type all four, in
   order, into the **same** file. After each block there is a "Line N" explanation; read
   it, but don't type it.
4. Replace `manage.py`, `config/wsgi.py` and `config/asgi.py` with the versions under the
   headings `manage.py` and `config/wsgi.py and config/asgi.py`, at the end of this page.

All of these files go in **your own** `my-warroom` folder, the one you made in lesson 4.2.
The code shown here is copied from the finished reference project, so you can compare
your file with the real one.

### `config/settings/base.py`

<!-- source: config/settings/base.py:1-37 -->
```python
"""
Settings shared by every environment.

local.py, production.py and test.py import this file and override only what differs.
Every secret comes from the environment (.env in development); nothing secret lives here.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# In development the values come from .env. In production the host sets real environment
# variables, and load_dotenv never overrides those.
load_dotenv(BASE_DIR / ".env")


def env_str(name: str, default: str = "") -> str:
    # Tolerate values pasted with surrounding quotes or spaces, a common .env mistake.
    return os.environ.get(name, default).strip().strip('"').strip("'").strip()


def env_bool(name: str, default: bool = False) -> bool:
    return env_str(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env_str(name, default).split(",") if item.strip()]


SECRET_KEY = env_str("DJANGO_SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
```

#### Lines 1–37

- **Lines 1–6** · The file's docstring: what this file is for, and the rule that no
  secret is ever written here.
- **Line 8** · `import os` gives access to environment variables (lesson 3.3).
- **Line 9** · `Path` is a tool for working with file and folder paths that works on
  Windows and Mac alike.
- **Line 11** · `dj_database_url` turns `DATABASE_URL` into database settings (used at
  line 100).
- **Line 12** · `load_dotenv` reads `.env` (lesson 3.3).
- **Line 14** · `BASE_DIR = Path(__file__).resolve().parent.parent.parent`
  - `__file__` is the path of **this** file: `my-warroom/config/settings/base.py`.
  - `.resolve()` turns it into a full, exact path.
  - Each `.parent` goes up one folder: `settings` → `config` → `my-warroom`.
  - So `BASE_DIR` is your project folder. Other settings use it to find `templates`,
    `static` and `.env`.
- **Lines 16–17** · Comment: on your laptop values come from `.env`; on a real server
  they're set by the hosting company, and `load_dotenv` never overwrites those.
- **Line 18** · `BASE_DIR / ".env"`: with `Path`, `/` joins folder and file names.
- **Line 21** · `env_str` reads one setting as text, with a default if it's missing.
- **Line 22** · Comment: why the next line removes quotes and spaces.
- **Line 23** · Read the variable, then `.strip()` spaces, `.strip('"')` double quotes and
  `.strip("'")` single quotes from both ends. People often paste `KEY="value"`; this makes
  it still work.
- **Line 26** · `env_bool` reads a yes/no setting.
- **Line 27** · `.lower()` makes `TRUE` and `True` both `true`; `in {"1", "true", "yes",
  "on"}` asks whether it's one of those words. `{ }` with plain values is a **set**: a
  collection made for fast "is it in here?" questions.
- **Line 30** · `env_list` reads a comma-separated setting as a list.
- **Line 31** · A **list comprehension**: a one-line loop that builds a list. Read it as
  "for each `item` in the text split at commas, keep `item.strip()`, but only if it isn't
  empty". `"localhost,127.0.0.1"` → `["localhost", "127.0.0.1"]`.
- **Line 34** · The secret key (see lesson 4.2).
- **Line 35** · Debug mode, **off** by default. Safe defaults matter: if someone forgets
  the setting on a real server, debug stays off.
- **Line 36** · Which host names this site accepts. Django refuses requests for other
  names, to stop a kind of attack where someone points their own domain at your server.
- **Line 37** · Trusted origins for forms on HTTPS sites (used in Part 11).

<!-- source: config/settings/base.py:39-83 -->
```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "common",
    "accounts",
    "businesses",
    "simulations",
    "intelligence",
    "decisions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.current_organization",
            ],
        },
    },
]
```

#### Lines 39–83

- **Lines 39–53** · `INSTALLED_APPS`: every app Django should load, in order.
  - **40** `admin`: a ready-made admin website to look at your data (lesson 4.5).
  - **41** `auth`: users, passwords, permissions.
  - **42** `contenttypes`: lets Django keep track of all your models (admin and auth
    need it).
  - **43** `sessions`: remembers who's logged in between page loads.
  - **44** `messages`: one-time notices like "Assumptions saved."
  - **45** `staticfiles`: serves CSS, fonts and JavaScript.
  - **46** `rest_framework`: DRF, for the API.
  - **47–52** Our own apps: `common` plus the five you created.
- **Lines 55–64** · `MIDDLEWARE`: code that runs on **every** request and response, in
  this order, like security guards at a gate.
  - **56** Adds security headers to every response.
  - **57** WhiteNoise: sends static files quickly.
  - **58** Reads and saves the session (who's logged in).
  - **59** Small common fixes, such as adding a missing `/` at the end of a URL.
  - **60** **CSRF** protection: stops other websites from submitting forms *as you*.
    Every form we write includes a hidden `{% csrf_token %}`.
  - **61** Works out `request.user` from the session.
  - **62** Makes one-time messages work.
  - **63** Stops other sites from showing our pages inside a hidden frame (an attack
    called **clickjacking**).
- **Line 66** · `ROOT_URLCONF`: the main URL map is in `config/urls.py`.
- **Line 67** · Where the web server finds the app (see `wsgi.py` below).
- **Lines 69–83** · `TEMPLATES`: how HTML pages are built.
  - **71** Use Django's own template language.
  - **72** Look for templates in `my-warroom/templates/`.
  - **73** Also look inside each app's own `templates/` folder.
  - **75–80** **Context processors**: functions that add values to *every* page. **79**
    is ours: it adds `current_org`, so every page can show your organization's name.
    You'll write it in lesson 4.6.

<!-- source: config/settings/base.py:85-131 -->
```python
# --- Database -------------------------------------------------------------------------
# DATABASE_URL (Neon) wins when present; otherwise fall back to a local SQLite file so the
# project still runs on a laptop with no internet. USE_SQLITE=True forces the fallback.
DATABASE_URL = env_str("DATABASE_URL")
USING_SQLITE_FALLBACK = not DATABASE_URL or env_bool("USE_SQLITE")

if USING_SQLITE_FALLBACK:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=60,  # reuse connections: Neon's TLS handshake is not free
            conn_health_checks=True,  # Neon suspends idle computes, so check before reuse
            ssl_require=True,  # never talk to the database in plain text
        )
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Auth -----------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"  # custom from day one: swapping it later is painful

# Sessions are read from an in-memory cache first and only fall back to the database.
# Against a remote database (Neon) that saves one network round trip on every request.
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalisation -------------------------------------------------------------
LANGUAGE_CODE = "en-in"
TIME_ZONE = "UTC"  # store and display UTC; the status bar labels it explicitly
USE_I18N = True
USE_TZ = True
```

#### Lines 85–131

- **Lines 85–87** · Comment: Neon if a URL is given, otherwise a local SQLite file.
- **Line 88** · Read `DATABASE_URL`.
- **Line 89** · Use SQLite if there's no URL, **or** if `USE_SQLITE` is true. `not` flips
  True/False; an empty string counts as False, so `not ""` is True.
- **Lines 91–97** · The SQLite settings: the engine (which database type) and the file
  name `db.sqlite3` in your project folder.
- **Lines 98–106** · The Neon settings, made from the URL by `dj_database_url.parse`:
  - **102** `conn_max_age=60`: keep a connection open for 60 seconds and reuse it. Opening
    an encrypted connection to Neon takes time, so reusing saves it.
  - **103** `conn_health_checks=True`: test a reused connection first, because Neon may
    have gone to sleep (lesson 3.3).
  - **104** `ssl_require=True`: always encrypt.
- **Line 108** · The type of automatic id column for tables that don't choose their own
  (ours mostly use UUIDs; lesson 4.4).
- **Line 111** · `AUTH_USER_MODEL = "accounts.User"`: use **our own** User model
  (lesson 4.5) instead of Django's built-in one. This must be decided **before** the
  first migration; changing it later is very painful.
- **Lines 113–115** · Store sessions in fast memory first, with the database as backup.
  That saves one trip to Neon on every page.
- **Line 116** · Where to send someone who isn't logged in: the URL named `login` in the
  `accounts` app.
- **Line 117** · Where to go after logging in: the URL named `home`.
- **Line 118** · Where to go after logging out.
- **Lines 120–125** · Password rules Django checks at sign-up:
  - not too similar to your name or email;
  - a minimum length (8 by default);
  - not a common password like `password123`;
  - not only numbers.
- **Line 128** · Language: English (India).
- **Line 129** · Store all times in **UTC** (world time). The screen labels times "UTC",
  so nobody gets confused by time zones.
- **Line 130** · Turn on translation support.
- **Line 131** · Store times with their time zone.

<!-- source: config/settings/base.py:133-168 -->
```python
# --- Static files ---------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Django REST Framework ------------------------------------------------------------
# Browser pages and the JSON API share one login: the Django session (+ CSRF token).
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "config.api_errors.api_exception_handler",
    # Decimals go out as strings ("1250.00"): exact, and JS won't round them silently.
    "COERCE_DECIMAL_TO_STRING": True,
}

# --- Gemini ---------------------------------------------------------------------------
GEMINI_API_KEY = env_str("GEMINI_API_KEY")
GEMINI_MODEL = env_str("GEMINI_MODEL") or "gemini-3.5-flash-lite"
GEMINI_GROUNDING_MODEL = env_str("GEMINI_GROUNDING_MODEL")
AI_DAILY_CALL_BUDGET = int(env_str("AI_DAILY_CALL_BUDGET", "200") or 200)
AI_TIMEOUT_SECONDS = int(env_str("AI_TIMEOUT_SECONDS", "30") or 30)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django": {"handlers": ["console"], "level": "WARNING", "propagate": False}},
}
```

#### Lines 133–168

- **Line 134** · Static files are served under addresses starting `/static/`.
- **Line 135** · They live in `my-warroom/static/`.
- **Line 136** · When publishing the site (Part 11), Django copies all static files into
  `staticfiles/`.
- **Lines 140–153** · Settings for the API (DRF):
  - **141–143** Who is calling? Use the same login **session** as the web pages.
  - **144–146** Only logged-in users may use the API.
  - **147–149** Answer in JSON.
  - **150** When an API error happens, use **our** function to format it (lesson 4.7).
  - **151–152** Send Decimal money values as text, like `"1250.00"`, which is exact
    (lesson 2.3).
- **Lines 156–160** · Gemini settings, used in Part 7.
  - **157** `or` gives a default: if the setting is empty, use `"gemini-3.5-flash-lite"`.
  - **159–160** `int(...)` turns text into a whole number; `or 200` catches an empty value.
- **Lines 162–168** · Logging: where messages from the app go. Here, to the terminal
  (`StreamHandler`). Our own messages show at INFO level; Django's own only when they're
  warnings or worse, to keep the terminal quiet.

### `config/settings/local.py`

<!-- source: config/settings/local.py:1-15 -->
```python
"""Developer laptop settings: debug on, browsable API on."""

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK, SECRET_KEY

DEBUG = True

# A missing key should not stop a student from running the project locally.
if not SECRET_KEY:
    SECRET_KEY = "local-dev-only-not-secret"

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
```

- **Line 3** · `from .base import *` copies **every** setting from `base.py` into this
  file. The `.` means "from this same folder". `# noqa: F403` tells the linter "I know
  `*` imports are usually a bad idea, and this is the one place they're the normal way".
- **Line 4** · Name two settings directly, because we change them below.
- **Line 6** · On your laptop, always show detailed errors.
- **Lines 8–10** · If you didn't set a secret key, use a harmless placeholder, so you can
  start learning without generating one.
- **Lines 12–15** · Add the **browsable API**: when you open an API URL in the browser,
  you get a readable web page instead of raw JSON.

### `config/settings/production.py`

<!-- source: config/settings/production.py:1-25 -->
```python
"""Production settings: refuse to start with an unsafe configuration."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import SECRET_KEY, USING_SQLITE_FALLBACK

DEBUG = False

if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")
if USING_SQLITE_FALLBACK:
    raise ImproperlyConfigured("Production needs DATABASE_URL (PostgreSQL), not SQLite.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_CONTENT_TYPE_NOSNIFF = True

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
```

- **Line 3** · `ImproperlyConfigured` is Django's error for "the settings are wrong".
- **Line 8** · Never show detailed errors to the public: they reveal how the code works.
- **Lines 10–13** · **Refuse to start** without a secret key or a real database. It's
  far better to fail loudly at startup than to run unsafely.
- **Line 15** · The hosting company's front server handles HTTPS and tells Django so in
  a header; trust it.
- **Line 16** · Send anyone using `http://` to `https://`.
- **Lines 17–18** · Only send the login and CSRF cookies over HTTPS.
- **Line 19** · **HSTS**: tell browsers "only ever use HTTPS for this site" for 30 days
  (60 seconds × 60 × 24 × 30).
- **Line 20** · Stop browsers from guessing a file's type (a known attack trick).
- **Lines 22–25** · Store uploaded files on disk, and serve static files compressed, with
  a fingerprint in the name (like `app.3f2a9c.css`) so browsers can cache them safely.

### `config/settings/test.py`

<!-- source: config/settings/test.py:1-16 -->
```python
"""
Test settings: in-memory SQLite and a fixed key.

Why not Neon for tests? pytest creates and drops a whole database on every run; over the
internet that is slow and needs CREATEDB rights. Migrations are checked against Neon
separately (`python manage.py migrate`), and nothing in the code is SQLite-specific.
"""

from .base import *  # noqa: F403

SECRET_KEY = "test-only"
DEBUG = False
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast; tests only
GEMINI_API_KEY = ""  # tests must never call the real API
WHITENOISE_AUTOREFRESH = True  # don't require a collectstatic'd folder during tests
```

- **Lines 1–7** · Why tests use a throwaway in-memory database: a fresh database is made
  for every test run, and doing that over the internet would be slow.
- **Line 11** · A fixed, fake secret key: fine for tests.
- **Line 13** · `":memory:"` is the same trick as lesson 3.2.
- **Line 14** · Real password hashing is slow **on purpose** (to slow down attackers).
  Tests make many users, so they use a fast, weak method. Never use this outside tests.
- **Line 15** · An empty key, so no test can ever call the real Gemini by mistake.
- **Line 16** · Let WhiteNoise find static files directly while testing.

### `manage.py`

<!-- source: manage.py:1-16 -->
```python
#!/usr/bin/env python
"""Django's command-line utility. Defaults to local settings."""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

- **Line 1** · On Mac/Linux, this "shebang" line lets the file run as a program. Windows
  ignores it.
- **Line 5** · `sys` gives access to the words you typed after `python manage.py`.
- **Line 9** · `setdefault` means "use local settings, **unless** something else was
  already chosen". Production sets its own.
- **Line 10** · Import Django's command runner. It's imported inside the function, only
  after the settings are chosen.
- **Line 12** · `sys.argv` is the list of words you typed, e.g. `["manage.py", "migrate"]`;
  Django runs that command.
- **Lines 15–16** · Run `main()` only when this file is run directly (lesson 1.11).

### `config/wsgi.py` and `config/asgi.py`

<!-- source: config/wsgi.py:1-6 -->
```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
application = get_wsgi_application()
```

<!-- source: config/asgi.py:1-6 -->
```python
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
application = get_asgi_application()
```

These are the doors a **real web server** uses to run your app on the internet
(Part 11). **WSGI** and **ASGI** are two standard ways for a web server to talk to Python.
Line 5 picks **production** settings by default, because these files are only used on
real servers; line 6 creates the app object the server calls.

## Check

You can't run anything yet: `AUTH_USER_MODEL` points to `accounts.User`, which you write
in lesson 4.5. That's expected. Make sure all seven files are saved, then move on.

## Quiz

1. Why are the settings split into four files?
2. What does line 89 of `base.py` decide?
3. Why does `production.py` refuse to start without a secret key, instead of using a
   default?

---

**Next:** [4.4 · Shared building blocks](04-shared-building-blocks.md)

<details><summary>Quiz answers</summary>

1. Laptop, internet and tests need slightly different settings; `base.py` holds what they
   share, so nothing is repeated.
2. Whether to use the local SQLite file (no URL, or `USE_SQLITE=True`) or Neon.
3. A default key would be public (it's in the code on GitHub), so anyone could forge
   logins. Failing loudly is safer.

</details>
