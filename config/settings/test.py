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
