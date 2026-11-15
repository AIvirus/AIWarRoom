# AI WarRoom

**Test a business before reality does.** A teaching project in Django: model a business,
stress-test it with deterministic simulations, have Gemini explain the results under
strict guardrails, and record a human decision with a printable brief.

| Mode | For | What you get |
|---|---|---|
| **Idea Bench** | A business not yet launched | Monthly cash model from price, CAC, conversion, retention and costs; seven cases; sensitivity; a check of your own sales estimate against your funnel |
| **Situation Board** | An operating company | Knock out the payment gateway, warehouse or courier; compare *wait*, *switch to backup* and *queue* on impact, recovery time and cost; watch it play out hour by hour in a 3D system view |

Plus:
- **Company website scans:** a safe crawler, an AI profile, and alerts when something changes.
- **An expert committee:** four AI advisory desks that are allowed to disagree.
- **Decision records:** sign-off by a named person and a print-ready brief.

> **What it is not.** AI WarRoom supports decisions from the numbers *you* enter and the
> assumptions it states. It does not predict markets or guarantee outcomes. Every figure
> comes from the simulation engine or a cited web page. AI text is always labelled, and
> any number in it that we didn't supply is flagged.

---

## Quick start

Requires Python 3.12+. Works offline with SQLite, except for Gemini and site scans.

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

(macOS/Linux: `source .venv/bin/activate`)

```bash
pip install -r requirements-dev.txt
```

```bash
copy .env.example .env
```

(macOS/Linux: `cp .env.example .env`.) Then fill in `.env`; see **Configuration** below.

```bash
python manage.py migrate
```

```bash
python manage.py seed_kirana --email you@example.com
```

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000 and log in.
- If the email you seeded with was new, the seed command printed a one-time password.
- Otherwise use your own password.

You'll find two demo businesses, all figures marked *illustrative*:
- **Kirana Express:** an online grocer with three disruption runs.
- **Tiffin Box Co.:** a meal-subscription idea with a 24-month stress test.

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Any long random string. Required in production |
| `DJANGO_DEBUG` | `True` locally |
| `DATABASE_URL` | Neon connection string (keep `?sslmode=require`). Empty means local SQLite |
| `USE_SQLITE` | `True` forces SQLite even if `DATABASE_URL` is set (offline class) |
| `GEMINI_API_KEY` | From https://aistudio.google.com. Empty means AI features show a clear "off" message; everything else works |
| `GEMINI_MODEL` | Default `gemini-3.5-flash-lite` |
| `GEMINI_GROUNDING_MODEL` | Leave empty on the free tier (Search grounding has no free quota; see below) |
| `AI_DAILY_CALL_BUDGET` | Live Gemini calls per UTC day before the app stops asking (default 200) |
| `AI_TIMEOUT_SECONDS` | Per-request timeout; two retries follow (default 30) |

## Tests

```bash
pytest
```

```bash
pytest -p no:django simulation_engine
```

```bash
ruff check . && ruff format --check .
```

- `pytest` runs the whole suite, about 270 tests in about 5 seconds, on in-memory SQLite.
  Gemini and websites are faked, so no key or network is needed.
- The second command runs only the engine with Django switched off, to show it's pure
  Python.
- Every engine formula has a test with a hand-calculated expected value; see
  `docs/formulas.md`.

## How it fits together

```
Browser: Django templates + small ES modules (Three.js for the 3D view)
   │  pages (session login)                 JSON /api/v1/ (same session + CSRF)
   ▼                                          ▼
thin views ─────────────────────────► services/ ◄─────────────── thin DRF ViewSets
                                   │        │        │
          simulation_engine/  ◄────┘        │        └──► intelligence/services/
          plain Python, Decimal,            │             ai_client (only Gemini caller),
          no Django imports                 │             guardrails, url_fetcher (SSRF-safe),
                                            ▼             scan_service, committee
                                  PostgreSQL on Neon (or SQLite)
```

| App / package | Owns |
|---|---|
| `accounts/` | Email login, organizations, memberships, org-scoped access (`access.py`) |
| `businesses/` | Business profile, assumptions with sources, components and dependencies, seed command |
| `simulations/` | Scenarios, runs (frozen input snapshot), results, preview, run pages |
| `simulation_engine/` | The maths: catalogue, idea model, cases, sensitivity, disruptions, runner |
| `intelligence/` | Gemini client, prompts, guardrails, URL fetcher, scans, committee, alerts |
| `decisions/` | Decision workflow, brief builder, printable page |
| `config/` | Settings split, URLs, one API error shape, health check |

Design rationale: `docs/DESIGN_NOTE.md`. Original plan: `docs/PLAN.md`.
Module-by-module teaching map: `docs/TEACHING_NOTES.md`.

## Screens

| URL | Screen |
|---|---|
| `/` | Operations board: businesses, open alerts, recent decisions |
| `/businesses/new/` | Add an idea or an operating company |
| `/businesses/{id}/` | Dossier: assumption ledger, scenarios, components, site scan with live log, committee, decisions |
| `/runs/{id}/` | Situation Board (disruptions) or Idea Bench (idea stress test) |
| `/decisions/{id}/brief/` | Decision brief with sign-off buttons; print or save as PDF |

How the screens behave:
- Sliders call the preview endpoint, so every number shown still comes from the engine.
  "Save as a new run" freezes the what-if as a new run.
- The 3D view falls back to an SVG schematic with `?view=2d`, without WebGL, or if
  Three.js fails to load.
- With `prefers-reduced-motion`, nothing moves unless you press Play.

## API

All endpoints are under `/api/v1/` and use session login. Import
`docs/postman_collection.json` (30 requests, in order). It logs in, models a business,
simulates, calls the AI, scans a site and records a decision. A test replays the
collection on every run so it can't drift from the API.

| Endpoint | Methods |
|---|---|
| `me/`, `inputs/`, `scenario-templates/` | GET |
| `businesses/` · `{id}/` | GET, POST · GET, PATCH, DELETE (archives; owners only) |
| `businesses/{id}/assumptions/` | GET, PUT (bulk upsert) |
| `businesses/{id}/components/` · `{cid}/` | GET, POST · GET, PATCH, DELETE |
| `businesses/{id}/scans/` | POST → `202` with `events_url` (Server-Sent Events) |
| `businesses/{id}/committee/` | GET, POST |
| `scenarios/` · `{id}/run/` | GET, POST, PATCH, DELETE · POST (runs and saves) |
| `simulate/preview/` | POST (runs, saves nothing) |
| `runs/` · `{id}/analysis/` | GET · GET, POST (201 new, 200 cached) |
| `analyses/`, `scans/` | GET (`?business=`, `?kind=`) |
| `alerts/` · `{id}/acknowledge/` | GET · POST |
| `decisions/` · `{id}/` · `{id}/report/` | GET, POST · GET, PATCH, DELETE · GET |

Errors always look like `{"error": {"code", "message", "fields"}}`. Another
organization's record answers `404`, exactly like a missing one.

## Commands

| Command | Does |
|---|---|
| `python manage.py seed_kirana --email E [--reset]` | Loads the two demo businesses and runs their scenarios (no AI calls) |
| `python manage.py rescan_companies [--business ID]` | Re-scans every business website and raises alerts for changes. Schedule it with cron or Task Scheduler; there's no always-on watcher |

## Docker and deployment

```bash
docker compose up --build
```

Runs the production image (gunicorn, WhiteNoise, `DEBUG` off) with its own PostgreSQL
container at http://localhost:8000. Your Neon database isn't touched.
`config/settings/docker_local.py` relaxes only HTTPS and database SSL, which a laptop
can't provide.

- **`Dockerfile`:** Python 3.12 slim; installs the requirements, runs `collectstatic`,
  and runs as a non-root user. On start it runs `migrate`, then gunicorn on `$PORT`.
- **`.github/workflows/ci.yml`:** on every push it runs ruff, pytest and a Docker build.
- **Hosting (for example Render, Docker runtime):** set these variables:
  - `DJANGO_SECRET_KEY`
  - `DATABASE_URL` (a separate Neon database)
  - `DJANGO_ALLOWED_HOSTS`
  - `DJANGO_CSRF_TRUSTED_ORIGINS`
  - `GEMINI_API_KEY`
  - `AI_DAILY_CALL_BUDGET`

  Step by step: `self-learning-guide/11-deploy/`.

## Gemini: what's real on the free tier

These were checked live with this project's key in November 2026. They change, so
re-check them in Google AI Studio.

- **SDK:** `google-genai` (the old `google-generativeai` is deprecated).
- **Model:** `gemini-3.5-flash-lite` works with JSON-schema output.
- **Google Search grounding returns 429:** there is no free quota for it. The
  `gemini-2.5-flash-lite` fallback is no longer offered to new keys. So competitor claims
  are either named on a fetched page, with its URL, or marked **unverified AI inference**.
- **URL context works,** and is used automatically when a site's HTML has almost no
  text.
- **Privacy:** Google may use free-tier prompts to improve its products. Don't send
  confidential company data on the free tier.

## Known limits

- **Model scope:**
  - Price and demand are independent inputs; there's no price elasticity.
  - Failures spread one step to direct dependents only.
  - In warehouse and courier outages, the backup runs only during the outage.
  - The hourly demand curve is illustrative.
- **The number guardrail flags any figure the AI derived itself,** even a correct
  difference. That's by design: the prompt forbids new calculations.
- **DNS rebinding isn't fully closed** in the URL fetcher (documented in the code).
- **Latency to Neon:** about 67 ms per query from India to `ap-southeast-1`, and
  `runserver` opens a fresh connection per request, so pages take about 1 s. A server
  deployed near the database, or SQLite locally, is much faster.
- **Self-hosted assets:** fonts (`static/fonts/`, SIL Open Font License) and Three.js
  r170 (`static/vendor/three-0.170.0/`, MIT) are served by the app itself, so the
  interface, including the 3D view, works with no internet. A test fails if any page
  links to a CDN again.
- **No Monte Carlo, no background workers, no multi-org admin, no email or push
  notifications.**
