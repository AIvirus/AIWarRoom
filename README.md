# AI WarRoom

Test a business before reality does. A teaching project: Django + DRF, PostgreSQL on Neon,
deterministic simulations and Gemini-written analysis that is labelled as such.

> Status: **Phase 2.3**: deterministic simulation engine (idea cases, sensitivity,
> payment / warehouse / courier disruptions) with saved runs and a live preview endpoint.
> Gemini analysis arrives in Phase 2.4. See [docs/PLAN.md](docs/PLAN.md).

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

The engine has no Django dependency at all; its tests run with Django switched off:

```bash
pytest -p no:django simulation_engine
```

## The simulation engine

| File | What it models |
|---|---|
| `simulation_engine/idea.py` | Month-by-month funnel: CAC from cost per visit and conversion, customers with retention, cash |
| `simulation_engine/cases.py` | Seven cases (expected, best, worst, reduced demand, higher costs, lower conversion, more competition) as visible input shocks |
| `simulation_engine/sensitivity.py` | One-at-a-time ±step on eight inputs, sorted by effect on ending cash |
| `simulation_engine/disruption.py` | Hour-by-hour outage: checkout failures (payment) or a FIFO backlog with rising cancellations (warehouse, courier); wait / backup / queue strategies |
| `simulation_engine/runner.py` | The single entry point: `run(template_key, assumptions, parameters, components)` |

Every formula is written out in the module docstrings, and the tests check
hand-calculated values.

## Latency against Neon

The engine takes 4–10 ms. Each database query to Neon (ap-southeast-1) costs about
67 ms from a laptop in India, and `runserver` opens a new connection for every request.
Measured preview round trips: about 0.85 s threaded, about 0.43 s with
`runserver --nothreading`. A server deployed in the same region as the database, or
SQLite locally, removes most of this.

## Layout so far

| Path | What it is |
|---|---|
| `config/settings/` | `base.py` shared, `local.py` laptop, `production.py` strict, `test.py` |
| `common/` | `BaseModel` (UUID + timestamps) and `OrgScopedQuerySet` |
| `accounts/` | User (email login), Organization, Membership, sign-up service, access mixins |
| `businesses/` | BusinessProfile, FinancialAssumption, BusinessComponent (+ dependency rules) |
| `simulations/` | Scenario, SimulationRun (frozen input snapshot), SimulationResult |
| `intelligence/` | AIAnalysis, CompanyScan, Alert |
| `decisions/` | Decision |
| `simulation_engine/` | Plain Python, no Django. `catalog.py` defines every input and scenario template |
| `config/api_errors.py` | One error shape for the whole API |
| `templates/`, `static/css/` | Base layout and design tokens |

## API (all under `/api/v1/`, session login)

| Endpoint | Methods |
|---|---|
| `me/` | GET |
| `inputs/`, `scenario-templates/` | GET: what the engine accepts, with units and bounds |
| `businesses/` | GET, POST; `{id}/` GET, PATCH, DELETE (archives; owners only) |
| `businesses/{id}/assumptions/` | GET, PUT (bulk upsert) |
| `businesses/{id}/components/` | GET, POST; `{cid}/` GET, PATCH, DELETE |
| `scenarios/` | GET (`?business=`), POST; `{id}/` GET, PATCH, DELETE |
| `runs/`, `analyses/`, `scans/` | GET (read-only history) |
| `alerts/` | GET; `{id}/acknowledge/` POST |
| `decisions/` | GET, POST; `{id}/` GET, PATCH, DELETE |

Errors always look like `{"error": {"code": "...", "message": "...", "fields": {...}}}`.
Another organization's record answers `404 not_found`, exactly like a missing one.

## Settings at a glance

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon connection string (`sslmode=require`). Empty means SQLite. |
| `USE_SQLITE` | `True` forces SQLite even if `DATABASE_URL` is set. |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Gemini access; default model `gemini-3.5-flash-lite`. |
| `AI_DAILY_CALL_BUDGET` | Cap on live Gemini calls per day, to protect the free tier. |
