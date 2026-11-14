# AI WarRoom

Test a business before reality does. A teaching project: Django + DRF, PostgreSQL on Neon,
deterministic simulations and Gemini-written analysis that is labelled as such.

> Status: **Phase 2.5**: simulation engine, Gemini run explanations, SSRF-safe company
> website scans with live progress (SSE), AI site profiles, the expert committee and
> change alerts. Decisions and the printable brief arrive in Phase 2.6.
> See [docs/PLAN.md](docs/PLAN.md).

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

## Gemini analysis

`POST /api/v1/runs/{id}/analysis/` asks Gemini to explain a saved run; `GET` returns the
latest one. Everything goes through `intelligence/services/ai_client.py`:

| Step | What it does |
|---|---|
| Cache | Same business + run inputs + prompt version + model: the stored answer comes back (HTTP 200, `from_cache: true`), no API call |
| Budget | Live calls per UTC day are capped by `AI_DAILY_CALL_BUDGET` |
| Retries | 429 / 5xx / timeout: two retries, exponential backoff with jitter, honouring Google's retry hint |
| Validation | Pydantic schema (`intelligence/schemas.py`) plus "only cite metric keys we sent"; one repair attempt, then a recorded failure |
| Guardrail | Every number in the answer must be a sent number rounded to the digits written; others are stored in `flagged_numbers` |

Prompts live in `intelligence/prompts/` with a version header; change the text, bump the
version. Tests use a fake transport and never call Google.

Free-tier note: Google may use free-tier prompts to improve its products. Don't send real
confidential company data while on the free tier.

## Company scans, committee and alerts

| Endpoint | What it does |
|---|---|
| `POST businesses/{id}/scans/` | Creates a scan (optional `{"url": ...}`), returns `202` with `events_url` |
| `GET scans/{id}/events/` | Server-Sent Events: runs the scan and streams each step; reopening replays the log |
| `GET analyses/?business={id}&kind=site_profile` | The AI profile built from the scanned pages |
| `POST/GET businesses/{id}/committee/` | Four advisory desks (finance, operations, market and competition, risk) in one Gemini call |
| `GET alerts/`, `POST alerts/{id}/acknowledge/` | Changes found by comparing a scan with the previous one |

Fetching is in `intelligence/services/url_fetcher.py`: http/https on ports 80 and 443
only, every DNS answer and every redirect hop must be a public address, robots.txt is
respected, and pages are capped at 1.5 MB. Extraction and diffing are plain code (no AI),
so the same page always gives the same result.

Every claim about dependencies, competitors or the market carries a basis: `site` (with
a URL we fetched), `cited` (with a URL a search tool returned) or `inference` (no URL
allowed). Answers that break this rule get one repair attempt, then fail.

"Real-time" means on demand: a scan runs when someone asks for it, or on a schedule with

```bash
python manage.py rescan_companies
```

Nothing watches sites continuously.

**Free-tier findings (checked 15 Nov 2026 with this project's key):** Google Search
grounding returns 429 (no free quota) and `gemini-2.5-flash-lite` is no longer offered to
new keys, so competitor claims here are either named on the site or marked as unverified
inference. URL context works on `gemini-3.5-flash-lite` and is used automatically when a
site's own HTML has almost no text (JavaScript-rendered pages). Set
`GEMINI_GROUNDING_MODEL` only with a plan that includes Search grounding.

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
