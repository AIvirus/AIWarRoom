"""
The production settings, run on your own computer with `docker compose up`.

Everything is as strict as on the internet (DEBUG off, a real PostgreSQL database,
collected static files, gunicorn) except two things a laptop can't provide:

  - HTTPS: http://localhost has no certificate, so secure-only cookies would never be
    sent back and you could never stay logged in;
  - an encrypted database link: the PostgreSQL container in compose.yaml doesn't offer
    SSL, while Neon requires it.

Never use these settings on a server that the internet can reach.
"""

from .production import *  # noqa: F403
from .production import DATABASES

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

DATABASES["default"]["OPTIONS"].pop("sslmode", None)
