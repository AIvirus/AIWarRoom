# AI WarRoom

Test a business before reality does. A teaching project: Django + DRF, PostgreSQL on Neon,
deterministic simulations and Gemini-written analysis that is labelled as such.

> Status: **Phase 2.1**: project skeleton, Neon connection, sign-up/login and
> organization-level access control. See [docs/PLAN.md](docs/PLAN.md) for the full plan.

## Run it locally

Requires Python 3.12 or newer.

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
```

```bash
pip install -r requirements-dev.txt
```

```bash
copy .env.example .env        # macOS/Linux: cp .env.example .env
```

Fill in `.env`. If `DATABASE_URL` is left empty the app uses a local SQLite file, which
is fine for working offline.

```bash
python manage.py migrate
```

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000, set up an organization, and you land on the operations
board. `http://127.0.0.1:8000/healthz/` reports whether the database is reachable.

## Tests and lint

```bash
pytest
```

```bash
ruff check . && ruff format --check .
```

Tests use in-memory SQLite (fast, offline, no Neon permissions needed). Run `migrate`
against Neon to check the real database.

## Layout so far

| Path | What it is |
|---|---|
| `config/settings/` | `base.py` shared, `local.py` laptop, `production.py` strict, `test.py` |
| `common/` | `BaseModel` (UUID + timestamps) and `OrgScopedQuerySet` |
| `accounts/` | User (email login), Organization, Membership, sign-up service, access mixins |
| `templates/`, `static/css/` | Base layout and design tokens |

## Settings at a glance

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon connection string (`sslmode=require`). Empty means SQLite. |
| `USE_SQLITE` | `True` forces SQLite even if `DATABASE_URL` is set. |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Gemini access; default model `gemini-3.5-flash-lite`. |
| `AI_DAILY_CALL_BUDGET` | Cap on live Gemini calls per day, to protect the free tier. |
