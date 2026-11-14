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

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
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

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django": {"handlers": ["console"], "level": "WARNING", "propagate": False}},
}
