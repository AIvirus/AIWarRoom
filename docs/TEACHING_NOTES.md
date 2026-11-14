# Teaching notes: one day with AI WarRoom

> **Provisional module map.** The course outline (`docs/day5_outline.*`) wasn't available
> when this was built, so the modules below come from the project blueprint and brief.
> Rename or reorder them to match your outline. The file references stay valid.

**Format.** About 6½ hours of teaching. Students get the finished repository: each module is
a guided read of working code plus one small hands-on change. Nobody builds the whole
thing in a day. Modules 3 and 4 are the hands-on core; 5 and 7 are demo-and-read.

**Before class:**
- Copy `.env.example` to `.env`.
- Run `python manage.py migrate` and `python manage.py seed_kirana --email you@example.com`.
- Open http://127.0.0.1:8000.
- Without internet, set `USE_SQLITE=True`. Everything except Gemini and site scans works
  offline, though fonts and Three.js come from CDNs (see README).

---

## M1 · Project, settings, Neon, auth and organizations (45 min)

| Concept | Where |
|---|---|
| Settings split: shared, laptop, production, tests | `config/settings/base.py`, `local.py`, `production.py`, `test.py` |
| `DATABASE_URL` → Neon with SSL; SQLite fallback | `config/settings/base.py` (Database section) |
| Custom user (email login), created before the first migration | `accounts/models.py` |
| Sign-up creates user + org + owner membership atomically | `accounts/services.py` (`register_owner`) |
| One place decides who sees what | `common/querysets.py` (`for_user`), `accounts/access.py` (`OrgScopedMixin`) |
| 404, not 403, for other orgs' records | `decisions/tests/test_isolation.py` |

**Demo:** sign up two users in two browsers, then try to open the other user's business
URL (404).
**Exercise:** add `ORG_PATH` and `OrgScopedQuerySet` to a new model and write the
isolation test first.

## M2 · Modelling a business: provenance, dependencies, an API (60 min)

| Concept | Where |
|---|---|
| A catalogue of valid inputs, with units and bounds, in plain Python | `simulation_engine/catalog.py` |
| Assumptions carry value + unit + source (user / illustrative / site / what-if) | `businesses/models.py` (`FinancialAssumption`) |
| Self-referencing many-to-many plus a cycle check | `businesses/models.py` (`depends_on`), `businesses/services/dependencies.py` |
| Thin ViewSets, org-narrowed related fields | `businesses/api.py`, `simulations/serializers.py`, `decisions/api.py` |
| One error shape for the whole API | `config/api_errors.py` |
| Archive instead of delete; owner-only | `businesses/api.py` (`perform_destroy`) |

**Demo:** Postman folders 1–2 (`docs/postman_collection.json`).
**Exercise:** add a new input to the catalogue (e.g. `refund_rate`) and see the API and
the ledger form pick it up with no other change.

## M3 · Pure-Python simulation, tested by hand (90 min) ★ hands-on core

| Concept | Where |
|---|---|
| Engine has no Django imports; runs with Django switched off | `simulation_engine/` · `pytest -p no:django simulation_engine` |
| Decimal, not float, for money | `simulation_engine/money.py` |
| Funnel model: CAC from conversion | `simulation_engine/idea.py` |
| Cases as visible shocks; one-at-a-time sensitivity | `simulation_engine/cases.py`, `sensitivity.py` |
| Affected ≠ lost ≠ lost profit; two loss modes; three strategies | `simulation_engine/disruption.py` |
| Single entry point | `simulation_engine/runner.py` |
| Frozen snapshot + hash per run | `businesses/services/snapshot.py`, `simulations/services/run_service.py` |
| Hand-calculated tests | `simulation_engine/tests/test_idea.py`, `test_disruption.py` |

All formulas, with worked examples: `docs/formulas.md`.

**Demo:** the payment-outage table in `formulas.md`, then the same numbers from the API
(Postman "Run it" checks ₹21,000 automatically).
**Exercise (pairs):** work out on paper the Backup strategy with a 1-hour switch-over, then
write the test before running it. Answer: 60 via backup, 140 failed, 42 recaptured,
98 lost, cost ₹5,720, total impact ₹20,420.

## M4 · Calling an LLM responsibly (75 min) ★ hands-on core

| Concept | Where |
|---|---|
| One module talks to Gemini (`google-genai`) | `intelligence/services/ai_client.py` |
| Cache by input hash; daily call budget | `ai_client.generate` steps 1–2 |
| Timeouts, retries, backoff with jitter, honouring `retryDelay` | `_call_with_retries` |
| Pydantic schemas; one repair attempt; recorded failure | `intelligence/schemas.py`, `ai_client.generate` steps 3–4 |
| Allowlisted context; untrusted text wrapped as data | `intelligence/services/context.py`, `render_user_message` |
| Versioned prompts | `intelligence/prompts/*.md` |
| Number guardrail | `intelligence/services/guardrails.py` |
| Tests with a fake transport (no key, no network) | `intelligence/tests/fakes.py`, `test_ai_client.py` |

**Demo:** "Ask the analyst" on a run, then ask again: the second answer comes from the
cache instantly.
**Exercise:** make Gemini say "₹14,550" in a fake answer and watch it get flagged. Then
change the prompt and notice the version bump forces a fresh call.

## M5 · Reading the web safely (40 min, demo and read)

| Concept | Where |
|---|---|
| SSRF: check every DNS answer and every redirect hop; ports; credentials | `intelligence/services/url_fetcher.py` |
| robots.txt per RFC 9309 | `SafeFetcher.robots_for` |
| Deterministic extraction and diffing | `site_extractor.py`, `scan_diff.py` |
| A generator powering SSE, a CLI command and tests | `scan_service.py` (`scan_steps`), `intelligence/views.py`, `rescan_companies` |
| Citations must be real; inference must not have a URL | `intelligence/services/sources.py` |
| One-call committee that may disagree | `intelligence/services/committee.py`, `prompts/committee.md` |

**Demo:**
- Scan `http://169.254.169.254/` (refused).
- Scan the seeded site: the log streams live.
- Run `python manage.py rescan_companies`.

**Discuss:** the DNS-rebinding gap documented at the top of `url_fetcher.py`.

## M6 · Decisions and human sign-off (30 min)

| Concept | Where |
|---|---|
| Status workflow in one module; append-only history | `decisions/services/workflow.py` |
| Brief built only from stored data | `decisions/services/brief.py` |
| Printable page | `templates/decisions/brief.html`, `static/css/brief.css` |

**Demo:** record a decision that disagrees with the AI's suggestion and write why, then
print the brief to PDF.

## M7 · Showing a living system (40 min, demo and read)

| Concept | Where |
|---|---|
| Server hands the page one JSON blob (`json_script`) | `simulations/views.py` |
| Live sliders call the preview API, debounced, with older requests aborted | `static/js/board/main.js`, `static/js/bench/main.js` |
| Three.js scene; 2D SVG fallback with the same API | `static/js/board/scene3d.js`, `schematic2d.js`, `topology.js` |
| Hand-written SVG charts | `static/js/bench/charts.js` |
| Accessibility: reduced motion, screen-reader tables, labels | `board.html`, `bench.html`, `app.css` |

**Demo:**
- Bhiwandi flood: press Play, drag the outage slider to 12 h, switch strategy.
- Append `?view=2d` to the URL.

---

## Real bugs from building this, worth showing

| Bug | Lesson | Where it's fixed |
|---|---|---|
| `Decimal("2400").normalize()` prints `2.4E+3` | Format for humans explicitly | `businesses/services/snapshot.py` (`plain`) |
| A failed run saved inside `transaction.atomic` vanished on the rollback | Decide what must survive a failure | `simulations/services/run_service.py` |
| "Within 2 %" let an invented ₹14,550 pass next to a real ₹14,700 | Define tolerance by what was written, not a percentage | `guardrails.py` |
| Range sliders snap: a saved ₹112 displayed as ₹110 | UI widgets can change data silently | `static/js/lib/format.js` (`alignedStep`) |
| One query per business on the dashboard | N+1 queries hurt on a remote database (67 ms each to Neon) | `businesses/views.py` (`_latest_completed_runs`) |
| Fake AI answers cited a page never fetched, and the guardrail rejected them | Guardrails catch your own mistakes too | `config/tests/test_postman_collection.py` |

## Questions to ask the class

1. Why is "affected value" never shown as "lost revenue"?
2. What would break if the engine imported Django?
3. Why does a scan alert come from a plain diff and not from the AI?
4. The AI recommended queueing; the decision chose the backup. Is that a bug?
