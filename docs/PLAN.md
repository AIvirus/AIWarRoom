# AI WarRoom: Phase 1 plan

Status: **built** (phases 2.1 to 2.8). This is the original plan, kept for reference; where the
build differs (e.g. no htmx/Alpine, no Search grounding on the free tier), the README and
`docs/TEACHING_NOTES.md` describe what actually exists.
Decisions locked in Phase 0: Gemini `gemini-3.5-flash-lite` by default (optional `gemini-2.5-flash-lite` for Search-grounded lookups), session auth with one org per user, INR + fictional "Kirana Express" seed, `old_code/` kept out of git, Python 3.12+ (tested on the local 3.14).

---

## 1. Architecture at a glance

```
Browser (Django templates + Alpine.js + htmx + Three.js modules)
   │  HTML pages (session auth)          JSON (/api/v1/, same session + CSRF)
   ▼                                        ▼
Django views (thin) ──────────────► services/  ◄──────────── DRF ViewSets (thin)
                                      │   │   │
              ┌───────────────────────┘   │   └──────────────────────┐
              ▼                           ▼                          ▼
   simulation_engine/            intelligence/services/        businesses/services/
   pure Python, no Django,       ai_client  (Gemini, retry,     snapshot builder,
   Decimal, unit-tested          cache, Pydantic, guardrails)   seed data
                                 url_fetcher (SSRF-safe)
                                 site_extractor, scan_diff
                                      │
                                      ▼
                         PostgreSQL on Neon (SQLite fallback)
```

Rules that every file follows:

- **Views stay thin.** They check access, parse input, call one service and render or serialize the result.
- **`simulation_engine/` never imports Django.** It takes plain dataclasses and returns plain dataclasses. You can run its tests with plain `pytest` and no database.
- **Gemini is called from exactly one module**, `intelligence/services/ai_client.py`. Nothing else imports `google.genai`.
- **Every number on screen comes from somewhere you can name**: the engine, a user input, or a cited source. AI text is labelled "AI analysis", and any number the AI produced that is not in the input data gets flagged.

### Real-time without Redis or Celery

| Need | Mechanism |
|---|---|
| Sliders that react instantly | `POST /api/v1/simulate/preview/` runs the pure engine on the slider values and saves nothing. It takes about 5 ms, so sliders are debounced to around 150 ms. |
| An outage that "plays out" | The engine returns an hour-by-hour **timeline**, and the browser plays it back on the 3D board with a scrubber. There's no server push. |
| Progress of a URL scan or an AI call | **Server-Sent Events.** A generator view does the work step by step and `yield`s progress lines (`fetching robots.txt`, `reading /pricing`, `asking Gemini`, `done`). It's a plain `StreamingHttpResponse` with no extra infrastructure. |
| "Monitoring" a company site | On-demand **Re-scan** button, plus `python manage.py rescan_companies`, which you can schedule with cron or Windows Task Scheduler if you want. The UI calls it *re-scan*, not *live monitoring*. |

---

## 2. Django apps

Four domain apps plus config. Each app owns its models, its services and its pages, so a student can open one folder and see one concept.

| App | Owns | Teaches |
|---|---|---|
| `accounts` | User (custom), Organization, Membership, access helpers, sign-up/login pages | Custom user model, sessions, org-level access control |
| `businesses` | BusinessProfile, FinancialAssumption, BusinessComponent (+ dependencies), seed command | Modelling, provenance, M2M self-relations, serializers |
| `simulations` | Scenario, SimulationRun, SimulationResult, run service, preview API | Snapshots, service layer, calling a pure engine |
| `intelligence` | AIAnalysis, CompanyScan, Alert, Gemini client, URL fetcher, committee | External APIs, Pydantic, guardrails, SSRF, SSE |
| `decisions` | Decision, briefing report page | Workflow and status, printable reports |

`simulation_engine/` is a top-level **plain Python package**, not a Django app. That's deliberate: it shows students that the core logic doesn't need the framework.

---

## 3. Models

All models use UUID primary keys plus `created_at`/`updated_at` from a tiny abstract `TimeStamped` base. Money is `DecimalField(max_digits=14, decimal_places=2)`.

```
User ─┐
      └─< Membership >── Organization ──< BusinessProfile ──< FinancialAssumption
                                                │
                                                ├──< BusinessComponent ⟲ depends_on (M2M self)
                                                ├──< Scenario ──< SimulationRun ──< SimulationResult
                                                │                      │
                                                │                      └──< AIAnalysis (kind=run_explanation)
                                                ├──< CompanyScan ──< Alert
                                                │        └──< AIAnalysis (kind=site_profile)
                                                ├──< AIAnalysis (kind=committee)
                                                └──< Decision ── (optional) SimulationRun, owner → User
```

| Model | Key fields | Notes |
|---|---|---|
| **Organization** | name, slug | Created automatically at sign-up. |
| **Membership** | user, organization, role (`owner`/`member`) | `unique(user, organization)`. Only owners can delete. |
| **BusinessProfile** | organization, mode (`idea`/`operating`), name, industry, description, website_url, currency=`INR`, archived_at | One model serves both modes; `mode` decides which screens appear. |
| **FinancialAssumption** | business, key, value (Decimal), unit, source (`user`/`illustrative`/`derived`/`from_site`), note | `unique(business, key)`. Keys come from a registry in the engine, so a typo can't create a ghost input. |
| **BusinessComponent** | business, key, name, kind (`storefront`/`payment`/`warehouse`/`logistics`/`supplier`/`customers`/`revenue`), criticality 1–5, fallback_note, `depends_on` (M2M self, non-symmetrical) | Validation: a dependency must be in the same business and must not create a cycle. |
| **Scenario** | business, kind (`idea_case`/`disruption`), template_key, name, parameters (JSON) | `parameters` is validated by the template's Pydantic schema before saving. |
| **SimulationRun** | scenario, business, input_snapshot (JSON), input_hash, engine_version, status, created_by | The snapshot is frozen at run time, so editing assumptions later never changes old runs. |
| **SimulationResult** | run, case_key (`expected`, `worst`, `wait`, `backup`…), metrics (JSON), timeline (JSON) | One row per case or strategy. |
| **AIAnalysis** | business, run?, scan?, kind (`run_explanation`/`committee`/`site_profile`), model, prompt_version, input_hash, output (JSON), flagged_numbers (JSON), sources (JSON), status, error | `input_hash` doubles as the **cache key**: same input, prompt version and model means no new Gemini call. |
| **CompanyScan** | business, url, status, robots_allowed, pages (JSON: url, title, text hash, prices, product names), error | One row per scan. Diffing compares a scan with the previous one. |
| **Alert** | business, scan, severity (`info`/`warn`/`critical`), kind (`pricing_change`/`new_product`/`page_removed`/`new_competitor`), summary, detail (JSON), acknowledged_at | Created by deterministic diff rules, not by AI. In-app only. |
| **Decision** | business, run?, title, owner (User in same org), status (`proposed`/`approved`/`in_progress`/`done`/`rejected`), chosen_strategy, rationale | The report is a rendered view of the decision plus its run, analysis and committee. No separate Report model. |

**Org access control.** Every model gets a QuerySet method `.for_user(user)`, which filters by `organization__memberships__user=user` (or the equivalent through `business`). One mixin, `OrgScopedMixin`, used by both the page views and the DRF ViewSets, calls it, so there's only one place where access is decided. Tests prove user A gets a 404 on user B's business, run, scan, alert and decision.

---

## 4. API (`/api/v1/`, session auth + CSRF, DRF)

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `businesses/` | List or create profiles in my org |
| GET/PATCH/DELETE | `businesses/{id}/` | Delete = archive |
| GET/PUT | `businesses/{id}/assumptions/` | Bulk read/upsert with provenance |
| GET/POST/PATCH/DELETE | `businesses/{id}/components/` | Including `depends_on` |
| GET/POST | `scenarios/?business={id}` | Templates are listed at `scenario-templates/` |
| POST | `scenarios/{id}/run/` | Freeze a snapshot, run the engine, persist the results |
| POST | `simulate/preview/` | Run the engine on ad-hoc values, persist nothing (for sliders) |
| GET | `runs/{id}/` | Run, results and timeline |
| POST/GET | `runs/{id}/analysis/` | Ask for or read the Gemini explanation (cached) |
| POST | `businesses/{id}/scans/` | Start a scan and get the SSE URL back |
| GET | `scans/{id}/events/` | SSE progress stream |
| POST/GET | `businesses/{id}/committee/` | Expert-committee review (one Gemini call) |
| GET / POST | `alerts/` / `alerts/{id}/acknowledge/` | Dashboard alerts |
| GET/POST/PATCH | `decisions/` | Decision records |

Errors always come back in one shape: `{"error": {"code": "...", "message": "...", "fields": {...}}}`. A custom exception handler does this, and the same codes are reused in the HTML error states.

---

## 5. Simulation engine (`simulation_engine/`)

Everything uses `Decimal` and is deterministic. Each function is small and has a docstring that states its formula.

### 5.1 Idea Simulator: a monthly model over a 24-month horizon

Inputs (each with a unit and a source label): price per order (AOV), variable cost per order, fixed monthly costs, marketing spend per month, cost per visit, conversion rate, orders per customer per month, monthly retention, initial investment, and *expected monthly orders* (the founder's own estimate).

Formulas:

```
CAC                = cost_per_visit / conversion_rate          (lower conversion ⇒ dearer customers)
new_customers[t]   = marketing_spend / CAC
customers[t]       = customers[t-1] × retention + new_customers[t]
orders[t]          = customers[t] × orders_per_customer
revenue[t]         = orders[t] × price
gross_profit[t]    = revenue[t] − orders[t] × variable_cost
operating[t]       = gross_profit[t] − fixed_costs − marketing_spend
cash[t]            = cash[t-1] + operating[t]                 (cash[0] = initial_investment)
```

Outputs: monthly timeline, break-even month (or "not within 24 months"), cash trough (which is the funding need), runway, and 24-month totals.

**Honesty check.** The model compares *your expected orders* with the orders implied by the funnel. Example: "You expect 3,000 orders/month; your marketing spend and conversion support about 1,840 by month 6."

**Cases**, each defined as explicit, visible shocks on the inputs (labelled *illustrative* unless the user edits them):

| Case | Shock |
|---|---|
| Expected | Inputs as given |
| Best | Conversion +20 %, retention +5 pts |
| Worst | Conversion −30 %, variable cost +15 %, retention −10 pts |
| Reduced demand | Orders per customer −25 % |
| Higher costs | Variable +15 %, fixed +20 % |
| Lower conversion | Conversion −30 % |
| More competition | Cost per visit +40 %, price −5 % |

**Sensitivity analysis:** move one input at a time by ±10 %, record the effect on month-24 cash and on the break-even month, and draw it as a tornado chart.

### 5.2 Resilience Room: an hourly disruption model over a 72-hour horizon

The rule from the blueprint becomes structure here. There are two **loss modes**, because affected orders and lost revenue really are different things:

| Component | Loss mode | What happens to affected orders |
|---|---|---|
| Payment gateway | **At checkout** | Orders fail now. A share of customers come back later (recapture); the rest are lost. |
| Warehouse, logistics partner | **In fulfilment** | Orders are taken but **delayed**. They queue as a backlog. Cancellations grow with the delay (a cancel rate per hour of delay, capped). SLA refunds are an optional cost. |

Inputs: daily orders, AOV, contribution margin %, hourly demand profile (uniform, or a built-in illustrative e-commerce curve), affected share (for example, the share of payments going through the primary gateway), outage duration, recapture rate, cancel rate per delay hour, and normal processing capacity per hour.

**Strategies** (each has its own parameters with defaults):

| Strategy | Parameters | Mechanics |
|---|---|---|
| **Wait** | none | Nothing is served during the outage. Afterwards the backlog clears at spare capacity (fulfilment), or recaptured customers return (checkout). |
| **Backup provider** | switch-over time (h), backup capacity/h, extra cost per order, one-off activation cost | Orders before the switch behave like Wait; after it, orders up to backup capacity get served. |
| **Queue & retry** | retry success rate, retry window (h), cost per retry | Failed or blocked orders are queued and retried when service returns. Only orders inside the window are retried; success is partial. |

Per-strategy outputs, all separate keys:

```
affected_orders, affected_gmv                 ← "what was touched"
recovered_orders, delayed_orders, lost_orders
lost_revenue      = lost_orders × AOV          ← "what didn't happen"
lost_contribution = lost_revenue × margin      ← "what it actually cost the P&L"
mitigation_cost   (fees, activation, retries)
total_financial_impact = lost_contribution + mitigation_cost
time_to_recovery_h (service restored AND backlog cleared)
```

Strategies are compared on **impact, time and extra cost side by side**. The engine does not pick a winner; the UI shows the trade-off.

**Timeline for the 3D board:** each hour gives demand, served, queued, lost, cumulative impact, and a health score from 0 to 1 per component. Propagation is deliberately simple and documented: a failed component passes its served/demand ratio on to its direct dependents only (one hop).

### 5.3 Tests (`simulation_engine/tests/`, plain pytest)

Every formula gets at least one **hand-calculated** case in the test docstring. Example: 2,400 orders/day, uniform, 2 h outage at 100 % share ⇒ 200 affected; recapture 30 % ⇒ 60 recovered, 140 lost; AOV ₹600 ⇒ lost revenue ₹84,000; margin 25 % ⇒ lost contribution ₹21,000.

Edge cases: zero duration, zero orders, capacity bounds (recovered ≤ affected, served ≤ capacity), backup capacity above demand, a switch-over longer than the outage, retention of 0 and 1, conversion of 0 (handled, no division by zero), no break-even, and the same input giving identical output.

---

## 6. Intelligence layer (`intelligence/services/`)

### 6.1 `ai_client.py`, the only module that touches Gemini

```python
result = ai_client.generate(
    task="run_explanation",  # selects a versioned prompt file
    payload=context_dict,  # allowlisted data only
    schema=RunExplanation,  # Pydantic model
    use_search=False,  # grounding only if enabled + supported
)
```

What `generate` does, in order:

1. Hash `(task, prompt_version, model, payload)` and look up AIAnalysis by that hash. If it's there, return it (cache hit).
2. Check the daily budget counter (Django DB cache, so no Redis). If it's exhausted, fail with a clear message instead of burning a 429.
3. Call Gemini with a request timeout and structured output (a JSON schema from the Pydantic model).
4. On 429/503, retry with exponential backoff and jitter (2 retries max), honouring any server `retry-delay`. Errors are classified from the SDK's typed status codes, not by searching message text.
5. Validate with Pydantic. If that fails, retry **once** with the validation error appended. If it fails again, store a `failed` AIAnalysis and show a designed error state ("The analyst returned something we couldn't verify, so we haven't shown it. Simulation results above are unaffected.").
6. **Number guardrail:** extract every number from every string field in the output (handling ₹, commas, Indian lakh/crore, %, k/M) and compare it with the set of numbers in the payload, within a rounding tolerance. Anything unmatched goes into `flagged_numbers`, and the UI underlines it as "not from the simulation".
7. Persist the result with model, prompt version, sources and flags.

Prompts live in `intelligence/prompts/*.md` with a version header. Each one forbids inventing financial figures, requires a metric key for each quantitative claim, and treats business descriptions and fetched web text as untrusted data inside clearly marked blocks.

Tests use a `FakeAIClient`, so CI and classrooms never need a key.

### 6.2 URL analyzer

`url_fetcher.py` is about 100 lines, readable, and fully tested:

- **Allowed URLs:** only `http`/`https`, standard ports 80/443, and no credentials in the URL.
- **SSRF protection:** resolve DNS and reject any address that is private, loopback, link-local, reserved, multicast or IPv6-mapped-private. Redirects are followed **manually** (max 3), and the address check runs again on every hop.
- **robots.txt:** checked with `urllib.robotparser` as `AIWarRoomBot/1.0`. If a path is disallowed, it isn't fetched, and the UI says so.
- **Limits:** 4 s connect / 10 s read, a 1.5 MB streamed cap, `text/html` only, and at most 6 pages (homepage plus same-domain links that look like pricing, products, about, shipping or contact).
- **Known gap:** DNS-rebinding between the check and the connect isn't fully closed with `requests`. That's documented as a teaching point.

`site_extractor.py` uses BeautifulSoup to pull out the title, meta description, headings, visible text (trimmed), prices (₹/Rs/INR/$ patterns), product-like names and the page list. This structured extract is what gets diffed and what gets sent to Gemini.

**Site profile (one Gemini call):** business summary, inferred dependencies (payment providers, couriers and so on named *on the site*), competitors, weaknesses and future scenarios. Every claim carries `source`: a fetched URL, a grounding citation, or `"inference"`. Competitors without a source are shown as **"Unverified, AI inference"** and never in the fact styling.

**Grounding:** if `GEMINI_GROUNDING_MODEL=gemini-2.5-flash-lite` is set (the only free-tier model with Search, 500 req/day), competitor lookup runs as a separate grounded call and its source links are shown. If it isn't set, the feature degrades to inference-only and says so. URL-context tool support on the free tier gets tested live in Phase 5; if it works, it replaces nothing in the fetcher, because we still need our own extract for diffs.

### 6.3 Expert committee

There's **one** structured call. Its Pydantic schema:

```
Committee
  advisors: list[Advisor]           # exactly: finance, operations, market_competition, risk
    role, name ("Finance Desk" …), verdict: proceed | proceed_with_conditions | hold | reconsider
    headline, key_concerns[], drawbacks[], scenarios_to_watch[], recommended_actions[]
    sources: list[{url, title}]     # required for market/competitor claims, else claim labelled inference
  points_of_disagreement: list[str] # disagreement is part of the output, not hidden
```

There is no forced consensus field. The prompt tells each desk to argue from its own mandate.

### 6.4 Re-scan and alerts

`scan_diff.py` is pure and deterministic. It compares this scan with the previous one:

| Change | Severity |
|---|---|
| Page removed | warn |
| New page | info |
| Price changed on the same page | warn if the change is 10 % or more, else info |
| New product name | info |
| New competitor in the AI profile | warn; labelled unverified if it has no source |

Each finding becomes an Alert with a before/after. A management command re-scans every business that has a URL.

---

## 7. Design direction

### Concept: "Operations log", not "AI dashboard"

The reference is the instrument panel and duty log of a real control room: a flight-ops desk, a grid control room, a ship's bridge. Information is **labelled, numbered, timestamped and ruled off**. Nothing floats, glows or blurs. The interface looks like someone who runs operations designed it.

### Palette: two neutrals, one signal, one reserved alarm

| Token | Hex | Use |
|---|---|---|
| `--ink` | `#16150F` | Background (warm graphite, not blue-black) |
| `--panel` | `#1F1E17` | Panels, a one-step lift |
| `--rule` | `#3A382D` | 1 px hairlines, grid |
| `--bone` | `#E9E5D6` | Primary text (warm paper white, AA+ on ink) |
| `--dim` | `#9C9784` | Labels, secondary text (AA on ink) |
| `--signal` | `#F2A900` | **Sodium amber.** Live state, the selected item, "this changed", focus rings |
| `--fault` | `#E5484D` | **Only** for failed components and losses. Never decorative. |

Why: amber is the caution colour in real control rooms and aviation, and it reads warm against warm graphite, which keeps the product away from the blue-purple "AI" look. Red is held back so that when it appears it means something. Colour is never the only carrier of state: failures also get a hatch pattern and a text label (`FAULT`, `DEGRADED`), which keeps them readable for colour-blind users.

The **printable report** flips to paper: a bone background with ink text, and amber used only for a single highlight rule.

### Type: one condensed grotesque, one mono

- **Barlow Semi Condensed** (UI, headings, labels). It comes from the DIN and highway-signage family that real panels use. The condensed width fits dense instrument rows, and in uppercase with +6 % tracking it makes the panel labels (`P-03 · CASH POSITION`).
- **IBM Plex Mono** (every figure, timestamp and key). Tabular figures stop gauges from jittering as they tick, and it signals "this number came from the machine".
- Both are self-hosted in `static/fonts/` so a classroom without internet still renders correctly.

### Visual language

- Square corners (radius 0–2 px), 1 px rules and an 8 px baseline grid.
- Panels carry an ID and a title in a header strip, and corner tick marks instead of shadows.
- A top **status bar** shows org · business · mode (`SIM` vs `SCAN`), a UTC clock and the last-scan age.
- Every value shows a provenance tag in small mono: `USR` user input · `ILL` illustrative · `DRV` derived · `SITE` from site · `AI` AI analysis.
- Icons are a small, custom, single-stroke SVG set (about 10 glyphs). No icon font and no emoji.
- **Microcopy** is written like a duty log: "No disruptions run yet. Pick one from the console to see how Kirana Express absorbs it." / "Gemini quota for today is used up. Simulations still work; analysis resumes after 00:00 UTC."

### Three key screens

**1. Situation Board** (Resilience Room)

```
┌ status bar ─────────────────────────────────────────────────────────────────┐
│ P-01 DISRUPTION CONSOLE │        P-02 SYSTEM VIEW (Three.js)      │ P-03 GAUGES│
│ ○ Payment gateway       │  nodes: storefront, payment, warehouse, │ Revenue/h  │
│ ● Warehouse (Bhiwandi)  │  logistics, suppliers, customers,       │ Orders held│
│ ○ Logistics partner     │  revenue; flows as moving particles;    │ Lost contr.│
│ Duration  [====|---] 6h │  failed node → red hatch + flicker-free │ Mitigation │
│ Strategy  wait/backup/q │  pulse; flows thin with served/demand   │ Recovery h │
├─────────────────────────┴──────────────── timeline scrubber T+0 … T+72h ───┤
│ P-04 STRATEGY COMPARISON (impact · time · cost, side by side)               │
│ P-05 EXPERT COMMITTEE  Finance: HOLD · Ops: PROCEED W/ CONDITIONS · …       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**2. Idea Bench** (Idea Simulator): an assumption ledger on the left (inputs with provenance tags and sliders), a cash fan chart in the centre (seven cases over 24 months, with expected in bone and the others in dim lines plus labels), a tornado sensitivity chart and the "your estimate vs the model" honesty strip on the right, and the AI explanation panel underneath with flagged numbers underlined.

**3. Decision Brief** (report): a paper-style page with a header block (decision, owner, status, date, run ID, engine version), then assumptions with provenance, outcomes table, committee views (including dissent), risks, recommendations and a "What this brief is not" box. Print CSS produces a clean PDF from the browser.

### 3D system view

- Three.js r16x, vendored with a pinned version, ES modules via import map, an orthographic camera at an isometric angle (readable, not cinematic), instanced meshes and fewer than 2k particles.
- Nodes are low plinths labelled in mono. Flows are particle streams whose density is served/demand. A degraded node dims and slows; a failed node turns `--fault` with hatching. Gauges and the scrubber are driven by the same timeline array.
- **2D fallback:** if WebGL is unavailable, the same node and flow data renders as an SVG schematic.
- **Reduced motion:** particles are replaced by static line weights, and the timeline steps instead of tweening.
- Keyboard: Tab through nodes and arrow keys to scrub. Every visual state also appears in a text table for screen readers.

---

## 8. Folder tree

```
AI WarRoom/
├── .env.example  .gitignore  README.md  requirements.txt  requirements-dev.txt  pytest.ini
├── manage.py
├── config/
│   ├── settings/ base.py  local.py  production.py
│   ├── urls.py  wsgi.py  asgi.py
│   └── api_errors.py                 # one error shape for the whole API
├── accounts/        models.py  access.py  forms.py  views.py  urls.py  tests/
├── businesses/      models.py  serializers.py  api.py  views.py  urls.py
│                    services/ snapshot.py  seed_data.py
│                    management/commands/seed_kirana.py  tests/
├── simulations/     models.py  serializers.py  api.py  views.py  urls.py
│                    services/ run_service.py  tests/
├── intelligence/    models.py  serializers.py  api.py  views.py  urls.py
│                    prompts/ run_explanation.md  site_profile.md  committee.md
│                    schemas.py               # Pydantic output models
│                    services/ ai_client.py  guardrails.py  url_fetcher.py
│                              site_extractor.py  scan_service.py  scan_diff.py  committee.py
│                    management/commands/rescan_companies.py  tests/
├── decisions/       models.py  serializers.py  api.py  views.py  urls.py  tests/
├── simulation_engine/                # NO Django imports
│   ├── money.py  inputs.py  idea.py  cases.py  sensitivity.py  disruption.py  strategies.py
│   └── tests/
├── templates/       base.html  partials/  accounts/  businesses/  simulations/  intelligence/  decisions/
├── static/
│   ├── css/ tokens.css  base.css  panels.css  print.css
│   ├── fonts/ (Barlow Semi Condensed, IBM Plex Mono, woff2)
│   ├── icons/ sprite.svg
│   ├── js/ board/ scene.js  nodes.js  flows.js  fallback2d.js  timeline.js
│   │       charts/ fan.js  tornado.js
│   │       bench.js  sse.js
│   └── vendor/ three.module.min.js  alpine.min.js  htmx.min.js   (pinned)
└── docs/  PLAN.md  TEACHING_NOTES.md  DESIGN_NOTE.md  formulas.md  postman_collection.json
```

**Dependencies** (versions pinned at setup after checking that they support Python 3.12–3.14): Django (latest LTS that supports 3.14, otherwise the current stable), djangorestframework, dj-database-url, psycopg[binary] 3, python-dotenv, pydantic 2, google-genai, requests, beautifulsoup4, whitenoise. Dev: pytest, pytest-django, ruff.

**Why Alpine *and* htmx:** htmx loads server-rendered partials (alerts, committee, analysis panels), so students stay in Django templates. Alpine holds local UI state (sliders, tabs). Together they're about 30 KB, and there's no build step.

---

## 9. Build phases (each ends running, tested and committed)

| # | Phase | Done when (verified by me, with output shown) | Commit |
|---|---|---|---|
| 2.1 | **Setup and access.** git init, `.gitignore` (incl. `old_code/`, `.env`), settings split, Neon via `DATABASE_URL` + SSL with SQLite fallback, custom User, Org/Membership, sign-up/login/logout, `OrgScopedMixin`, base template with design tokens | `migrate` against Neon succeeds; `runserver` serves login; isolation tests pass | `feat(setup): project skeleton, Neon, auth, org access` |
| 2.2 | **Models and API.** All models, admin, serializers, ViewSets, validation (dependency cycles, assumption registry), error handler | API tests incl. cross-org 404s pass; browsable API works | `feat(models): business, scenario, run, decision models + API` |
| 2.3 | **Engine.** idea, cases, sensitivity, disruption, strategies; run service + preview endpoint | Hand-calculated engine tests pass; a run persists snapshot + results | `feat(engine): deterministic idea + disruption simulation` |
| 2.4 | **Gemini.** ai_client (timeouts, retries, cache, budget, Pydantic, one repair retry), guardrails, run explanation | Fake-client tests pass; **one live call** with your key succeeds, and the second identical call is served from cache | `feat(ai): Gemini client, guardrails, run explanation` |
| 2.5 | **Company intelligence.** url_fetcher + SSRF tests, extractor, site profile, committee, SSE progress, scan diff, alerts, re-scan command | SSRF tests block 127.0.0.1/10.x/169.254.x/redirect-to-private; a live scan of a public site works; diff tests create the expected alerts | `feat(intel): URL analyzer, committee, alerts` |
| 2.6 | **Decisions and report.** Decision CRUD, Decision Brief page, print CSS | Brief renders from persisted data only; print preview is clean | `feat(decisions): decision records and printable brief` |
| 2.7 | **Frontend.** Situation Board (Three.js + 2D fallback), Idea Bench (sliders → preview, fan, tornado), dashboard with alerts, designed empty/loading/error states | Checked in the browser pane: WebGL and fallback, reduced-motion, keyboard path, phone width | `feat(ui): situation board, idea bench, dashboard` |
| 2.8 | **Polish.** README, `seed_kirana`, Postman collection, TEACHING_NOTES (one-day module map → files), DESIGN_NOTE, formulas.md | Fresh clone → README steps → working demo, verified | `docs: README, seed, Postman, teaching notes` |

### One-day module map (provisional, since there's no outline file)

This gets finalised in TEACHING_NOTES.

| Module | Topic | Phase |
|---|---|---|
| M1 | Django project, settings split, Neon, auth and orgs | 2.1 |
| M2 | Modelling a business: provenance, dependencies, DRF | 2.2 |
| M3 | Pure-Python simulation and testing with hand-calculated values | 2.3 (the core hands-on module) |
| M4 | Calling an LLM responsibly: schemas, retries, caching, guardrails | 2.4 |
| M5 | Reading the web safely: SSRF, robots.txt, SSE | 2.5 (demo + read) |
| M6 | Decisions, reports and human-in-the-loop | 2.6 |
| M7 | Visualising a living system: Three.js, accessibility, reduced motion | 2.7 (demo + read) |

---

## 10. Not being built (stated plainly)

- Monte Carlo
- Celery, Redis or Channels
- Multi-org admin
- Email or push notifications
- Continuous monitoring
- Multi-currency conversion
- Price elasticity of demand (price and demand are independent inputs, and the UI says so)
- Multi-hop cascade failures (one hop only)
- Docker and CI pipelines
- Any claim about real market outcomes
