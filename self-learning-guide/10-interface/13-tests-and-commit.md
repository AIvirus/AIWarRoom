# 10.13 · Tests and commit

**Time:** 40 minutes · **Before this:** [10.12](12-the-system-view.md).

## Read

Page tests use Django's **test client**: a pretend browser that logs in, opens pages,
sends forms and follows redirects, all without a real browser or a server. A test reads
like what a person does: "add a component, check it's there, remove it, check it's gone".

They can't run the JavaScript, so they check what the server **hands** to it instead:
the `page-data` JSON. A small helper in the test file reads that block from the page.

## Do

### 1. The tests

**Copy** these two files from the reference project into `businesses/tests/`:

- `businesses/tests/test_pages.py`
- `businesses/tests/test_seed.py`

### 2. Run them

```bash
pytest
```

### 3. Tidy and commit

```bash
ruff format .
```

```bash
ruff check .
```

```bash
git add -A
```

```bash
git commit -m "Part 10: the interface"
```

## Check

- `pytest` prints `268 passed` (248 before + 20 new).
- `git log --oneline` shows seven commits.
- Your project now has every file of the app. Compare: the reference project has a few
  more, for the teacher (`docs/`, the guide itself and its checking tests).

**Try breaking it on purpose:** in `businesses/forms.py` line 50, change
`initial=plain(current.value) if current else None` to
`initial=current.value.normalize() if current else None`. Run `pytest`.
`test_ledger_shows_plain_numbers_not_exponents` fails: the ledger would show daily orders
as `2.4E+3` instead of `2400`. A real bug this project once had. Put it back.

## What each test proves

### `businesses/tests/test_pages.py` (16 tests)

| Lines | Test | Proves |
|---|---|---|
| 30–45 | the `web` fixture, `fill` and `page_data` helpers | A logged-in Alice; quick assumptions; reading the page's JSON. |
| 51–53 | `test_empty_dashboard_explains_what_to_do` | A new user sees what to do, not an empty table. |
| 56–64 | `test_create_business_lands_on_its_dossier` | The form creates a business in Alice's organization and opens its page. |
| 67–71 | `test_dossier_shows_mode_specific_inputs` | An idea and a shop get different ledgers. |
| 74–89 | `test_assumptions_form_saves_with_source_and_blank_removes` | Values save with their source; blank removes. |
| 92–99 | `test_invalid_assumption_saves_nothing_and_says_why` | 140 % is refused with the catalogue's message, and nothing is saved. |
| 102–110 | `test_add_and_remove_component` | "Razorpay (primary)" gets the key `razorpay-primary`; Remove removes it. |
| 113–121 | `test_scenario_with_missing_inputs_explains_instead_of_running` | It says what's missing; the attempt is recorded as a failed run. |
| 127–145 | `test_disruption_scenario_runs_and_opens_the_situation_board` | **Key test.** Create and run → the board, with self-hosted Three.js, three cases, only the **relevant** slider (recapture), and the `RUN_ID` address. |
| 148–160 | `test_idea_scenario_opens_the_idea_bench` | The bench: seven cases, the funnel check at month 6, eight sliders. |
| 163–190 | `test_record_decision_from_run_then_sign_off_on_the_brief` | **Key test.** The full human flow: record, approve on the brief; an illegal jump through the page is refused. |
| 193–204 | `test_alert_acknowledge_refuses_open_redirects` | **Key test.** `next=https://evil.test/phish` sends you home instead. |
| 207–235 | `test_other_orgs_pages_are_404` | **Key test.** Bob's pages are 404 for Alice, and his forms can't be posted to. |
| 238–240 | `test_pages_require_login` | Logged out → the login page. |
| 243–248 | `test_ledger_shows_plain_numbers_not_exponents` | `2400`, never `2.4E+3`. |
| 251–265 | `test_pages_load_no_assets_from_other_hosts` | No page loads anything from Google Fonts or a CDN: the app works offline. |
| 268–273 | `test_create_page_explains_when_the_user_has_no_organization` | A `createsuperuser` account gets a message, not a crash. |

### `businesses/tests/test_seed.py` (4 tests)

| Lines | Test | Proves |
|---|---|---|
| 19–28 | `test_seed_creates_both_demos_with_completed_runs_for_an_existing_user` | Both demos, in Alice's organization, with dependencies, sources and four completed runs. |
| 31–38 | `test_seed_is_idempotent_and_reset_rebuilds` | Running twice changes nothing; `--reset` rebuilds. |
| 41–45 | `test_seed_creates_a_missing_user_and_prints_the_password_once` | The printed password really works. |
| 48–53 | `test_seed_refuses_a_user_without_an_organization` | A clear error instead of a crash. |

("Idempotent" means "doing it twice has the same effect as doing it once".)

## If it didn't work

| You see | Fix |
|---|---|
| `TemplateDoesNotExist` in a page test | One of lesson 10.6–10.8's templates is missing or misnamed. |
| `test_pages_load_no_assets_from_other_hosts` fails | A template links to an outside address (fonts from Google, say). Everything must come from `static/`. |
| `NoReverseMatch` in a page test | Compare your `urls.py` files with lesson 10.5. |

## Quiz

1. How do page tests check JavaScript pages without running JavaScript?
2. What does `test_pages_load_no_assets_from_other_hosts` protect?

---

**Part 10 done! ** AI WarRoom is a complete app: pages, forms, live sliders, charts and
a 3D system view, all drawing numbers only the engine calculated. The last part puts it on
the internet: [Part 11 · Deploy](../11-deploy/README.md).

<details><summary>Quiz answers</summary>

1. They read the `page-data` JSON the server hands to the JavaScript.
2. That the app works with no internet (and doesn't share visitors with outside sites).

</details>
