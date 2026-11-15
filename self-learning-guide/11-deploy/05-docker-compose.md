# 11.5 · Docker Compose

**Time:** 45 minutes · **Before this:** [11.4](04-docker-the-image.md).

## 📖 Read

The image needs a PostgreSQL database. You could point it at Neon, but then a test on your
laptop would write into a real database. Instead, **Docker Compose** starts **two**
containers together:

```text
 compose.yaml
 ├── db   postgres:17-alpine     a throwaway PostgreSQL, data kept in a Docker "volume"
 └── web  your warroom image     waits until db is healthy, then migrate + gunicorn
          http://localhost:8000
```

Inside Compose, containers find each other **by name**: the app reaches the database at
the host name `db`.

### One small exception file: `docker_local.py`

Production settings insist on two things a laptop can't give:

- **HTTPS.** `http://localhost` has no certificate. With secure-only cookies, the browser
  would never send your login cookie back, and you could never stay logged in.
- **An encrypted database link.** Neon requires SSL; the little PostgreSQL container
  doesn't offer it.

So `config/settings/docker_local.py` loads **all** the production settings, then switches
off just those two. Everything else stays production: `DEBUG` off, gunicorn, WhiteNoise,
collected static files, a real PostgreSQL. Its docstring says it plainly: never use it on
a server the internet can reach.

## ⌨️ Do

### 1. `config/settings/docker_local.py`

<!-- source: config/settings/docker_local.py:1-23 -->
```python
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
```

### 2. `compose.yaml`

Next to the `Dockerfile`:

<!-- source: compose.yaml:1-41 -->
```yaml
# Run the production image on your own computer, with its own PostgreSQL:
#   docker compose up --build        then open http://localhost:8000
#   docker compose down              stop (add -v to also delete the database)
#
# Your Neon database is not touched: the app talks to the "db" container below.

services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: warroom
      POSTGRES_USER: warroom
      POSTGRES_PASSWORD: warroom-local-only
    volumes:
      - dbdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U warroom -d warroom"]
      interval: 2s
      timeout: 5s
      retries: 15

  web:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - path: .env
        required: false # your Gemini key, if you have one
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.docker_local
      DJANGO_SECRET_KEY: local-docker-only-not-secret
      DATABASE_URL: postgres://warroom:warroom-local-only@db:5432/warroom
      USE_SQLITE: "False"
      DJANGO_ALLOWED_HOSTS: localhost,127.0.0.1
      DJANGO_CSRF_TRUSTED_ORIGINS: http://localhost:8000,http://127.0.0.1:8000
    depends_on:
      db:
        condition: service_healthy

volumes:
  dbdata:
```

### 3. Start it

```bash
docker compose up --build
```

`--build` rebuilds the image first (it now includes `docker_local.py`). Then both
containers start, and their logs appear together, each line starting with `db-1` or
`web-1`. Wait for these from `web-1`:

```text
web-1  | Operations to perform:
web-1  |   Apply all migrations: accounts, admin, auth, businesses, contenttypes, decisions, intelligence, sessions, simulations
...
web-1  | [2026-11-15 17:28:55 +0000] [1] [INFO] Listening at: http://0.0.0.0:8000
```

Leave this terminal running.

## ✅ Check

1. **http://localhost:8000/healthz/** → `{"status": "ok", "database": "postgresql"}`.
   The app is running in Docker and talking to the `db` container.
2. **http://localhost:8000/** → the login page. This is a **new**, empty database, so
   click **Sign up** and make an account (any email; it only exists in this container).
3. **Demo data.** Open a **second** terminal in `my-warroom` and run the seed command
   **inside** the running container, with the email you just signed up with:

   ```bash
   docker compose exec web python manage.py seed_kirana --email you@example.com
   ```

   It prints each business and run, ending with
   `ran "Pune launch, 24 months": /runs/.../`. Reload the board: Kirana Express and Tiffin
   Box Co. are there. Open "Razorpay down at evening peak": the 3D view, sliders and charts
   work, served by gunicorn and WhiteNoise. (Press F12 → Network and look at the CSS file
   names: `app.abc4fb3c4b1b.css`, with the fingerprint from lesson 11.3.)
4. **Production behaviour.** Open **http://localhost:8000/no-such-page/**. A plain "Not
   Found" page, not Django's yellow debug page: `DEBUG` is off.
5. **Stop.** Press **Ctrl+C** in the first terminal, then:

   ```bash
   docker compose down
   ```

   The containers are removed; the database's data stays in its volume for next time.
   (`docker compose down -v` also deletes the data.)

## 🔍 Line by line

### `docker_local.py`

- **Lines 1–13** · Docstring: what it is, the two exceptions and why, and the warning.
- **Lines 15–16** · Every production setting, and the `DATABASES` dictionary by name (to
  change it below). `# noqa: F403` tells ruff the `*` import is on purpose.
- **Lines 18–21** · No HTTPS redirect, cookies allowed over plain HTTP, no HSTS (it would
  make your browser insist on HTTPS for `localhost` for 30 days).
- **Line 23** · Remove the "SSL required" option that `base.py` adds to the database
  connection (lesson 4.3). `.pop("sslmode", None)` removes the key if it's there.

### `compose.yaml`

- **Lines 1–5** · How to use it, and the promise: your Neon database isn't touched.
- **Line 7** · `services:` lists the containers.
- **Lines 8–13** · `db`: the official PostgreSQL 17 image (the small "alpine" build),
  creating a database `warroom` for user `warroom`. The password is only for this local
  container; it's fine in a file because nothing outside your computer can reach it.
- **Lines 14–15** · Keep the database files in a named **volume**, `dbdata`, so they
  survive `docker compose down`.
- **Lines 16–20** · A health check: every 2 seconds, ask `pg_isready` whether PostgreSQL
  accepts connections (up to 15 tries).
- **Lines 22–25** · `web`: build the image from this folder (`.`) and connect your
  computer's port 8000 to the container's port 8000.
- **Lines 26–28** · Read your `.env` if it exists, so your Gemini key works in Docker too.
  `required: false`: fine if there's none.
- **Lines 29–35** · Environment variables, which **win** over `.env`'s: the local
  settings, a throwaway secret key, the `db` container's address (`@db:5432`), no SQLite,
  the allowed host names, and the trusted origins for forms (lesson 4.3).
- **Lines 36–38** · Start `web` only after `db`'s health check passes, so `migrate` never
  finds the database still starting.
- **Lines 40–41** · Declare the `dbdata` volume.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | `runserver` is still running on 8000. Stop it (Ctrl+C) and try again. |
| `connection is insecure (try using sslmode=require)` or an SSL error | `DJANGO_SETTINGS_MODULE` must be `config.settings.docker_local` (line 30). |
| You log in, and the login page comes straight back | The same: production's secure cookies need HTTPS. Check line 30. |
| `CSRF verification failed` on a form | Use `http://localhost:8000` exactly (line 35 lists it). |
| `env file .env not found` | An older Docker Compose. Update Docker Desktop, or create an empty `.env`. |

## ❓ Quiz

1. How does the app find the database inside Compose?
2. Which two production settings does `docker_local.py` relax, and why only those?
3. What's the difference between `docker compose down` and `docker compose down -v`?

---

**Next:** [11.6 · Checks on every push](06-checks-on-every-push.md)

<details><summary>Quiz answers</summary>

1. By the service's name, `db`, used as the host in `DATABASE_URL`.
2. HTTPS (with secure cookies and HSTS) and database SSL. A laptop has neither a
   certificate nor an SSL database; everything else can be exactly like production.
3. `down` removes the containers but keeps the data volume; `-v` deletes the volume too.

</details>
