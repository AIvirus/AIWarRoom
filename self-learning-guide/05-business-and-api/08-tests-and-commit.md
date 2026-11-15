# 5.8 · Tests and commit

**Time:** 40 minutes · **Before this:** [5.7](07-urls-and-try-it.md).

## 📖 Read

In lesson 5.7 you tried the API by hand. Now 36 tests try it automatically, including the
rules you didn't try: Alice can't put her business in Bob's organization, a member can't
archive, a component can't depend on another business's parts, loops are refused...

Two new pytest tools appear:

- **`@pytest.mark.parametrize`** runs one test several times with different values. One
  test function with 5 rows of values = 5 tests.
- **`pytest.raises(SomeError)`** passes only if the code inside **does** raise that error.
  It's how you test that bad input is refused.

### Test data for businesses

`conftest.py`, which you copied in lesson 4.9, already contains the fixtures for this
part. Here they are:

<!-- source: conftest.py:40-70 -->
```python
def make_business(owner, mode, name):
    from businesses.models import BusinessProfile

    return BusinessProfile.objects.create(
        organization=org_of(owner), mode=mode, name=name, created_by=owner
    )


@pytest.fixture
def alice_shop(alice):
    return make_business(alice, "operating", "Kirana Express")


@pytest.fixture
def alice_idea(alice):
    return make_business(alice, "idea", "Kirana Idea")


@pytest.fixture
def bob_shop(bob):
    return make_business(bob, "operating", "Rival Mart")


@pytest.fixture
def api(alice):
    """An API client logged in as alice, with a real session (like the browser)."""
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_login(alice)
    return client
```

- **Lines 40–45** · `make_business` is a plain helper (not a fixture): it creates a
  business in the owner's organization. The import is **inside** the function so the
  pure catalogue tests can run without Django (see below).
- **Lines 48–50** · `alice_shop`: Alice's running shop, "Kirana Express".
- **Lines 53–55** · `alice_idea`: Alice's idea, "Kirana Idea".
- **Lines 58–60** · `bob_shop`: Bob's shop, in **another** organization.
- **Lines 63–70** · `api`: an API client already logged in as Alice. `force_login` logs
  in without a password check, so tests are quick.

## ⌨️ Do

### 1. Copy the three test files

Make the test folders, each with an **empty** `__init__.py`:

```bash
mkdir -p businesses/tests simulations/tests
```

Create `businesses/tests/__init__.py` and `simulations/tests/__init__.py` (both empty).
(`simulation_engine/tests/__init__.py` exists since lesson 5.2.)

Then **copy** these files from the reference project into the same places in
`my-warroom`:

- `simulation_engine/tests/test_catalog.py`
- `businesses/tests/test_business_api.py`
- `simulations/tests/test_scenario_api.py`

Open each one and read it next to the tables below.

### 2. Run them

```bash
pytest
```

The catalogue tests don't need Django at all. You can prove it:

```bash
pytest -p no:django simulation_engine
```

`-p no:django` switches Django's pytest plugin off. It prints `12 passed` and one
harmless warning that the `DJANGO_SETTINGS_MODULE` setting in `pytest.ini` isn't
understood (because the plugin that reads it is off).

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
git commit -m "Part 5: business model and API"
```

## ✅ Check

- `pytest` prints `52 passed` (16 from Part 4 + 36 new).
- `ruff check .` prints `All checks passed!`.
- `git log --oneline` shows two commits.

**Try breaking it on purpose:** in `businesses/api.py`, on line 45, change
`organization=organization` to `organization=None`. Run `pytest`. `test_create_business_uses_the_requesters_organization`
fails, and the terminal shows the database refusing a business with no organization
(`NOT NULL constraint failed`). Put it back. Then, in
`businesses/serializers.py` line 103, change `business.components.all()` to
`BusinessComponent.objects.all()` (every component of every business).
`test_component_cannot_depend_on_another_business` fails: the wall is down. Put it back.

> **The big wall test comes later.** "Alice gets 404 for every one of Bob's records" is
> tested for **all** tables at once in `decisions/tests/test_isolation.py`, in Part 9,
> when every table exists. Until then, the Part 4 ⭐ tests and the ⭐ tests below guard it.

## 🔍 What each test proves

### `simulation_engine/tests/test_catalog.py` (12 tests, no database)

| Lines | Test | Proves |
|---|---|---|
| 10–13 | `test_parse_input_accepts_text_with_commas_and_keeps_exact_decimals` | `"1,250.50"` becomes exactly `1250.50`; a float `0.1` becomes exactly `0.1`. |
| 16–29 | `test_parse_input_rejects_bad_values` | 5 tests in one: over 100 %, negative, not a number, `NaN`, and the misspelt `convertion_rate` are all refused with the right message. |
| 32–37 | `test_validate_parameters_fills_defaults_as_strings` | Missing settings get defaults, and every value is text. |
| 40–46 | `test_validate_parameters_reports_every_bad_field_at_once` | Three bad fields → three errors in **one** answer. |
| 49–51 | `test_unknown_template_is_rejected` | `alien_invasion` isn't a template. |
| 54–58 | `test_missing_inputs_lists_what_a_template_still_needs` | The "still needed" list is right. |
| 61–65 | `test_every_template_requires_only_known_inputs_of_its_own_mode` | A check **on the catalogue itself**: no template needs a number that doesn't exist or belongs to the other mode. |
| 68–70 | `test_every_parameter_default_passes_its_own_validation` | Every default value obeys its own rules. |

The last two test the **data**, not the code. If someone later adds a template with a
typo in it, these tests catch it.

### `businesses/tests/test_business_api.py` (18 tests)

| Lines | Test | Proves |
|---|---|---|
| 13–23 | `test_create_business_uses_the_requesters_organization` | ⭐ Sending Bob's organization id is ignored: the business goes into **Alice's** organization. |
| 26–29 | `test_mode_cannot_change_after_creation` | PATCH `mode` → 400, with the error on the `mode` field. |
| 32–39 | `test_delete_archives_instead_of_deleting` | DELETE → 204; the row still exists with `archived_at`; hidden from the list, shown with `?archived=true`. |
| 42–49 | `test_only_owners_can_archive` | A plain member gets 403 `permission_denied`. |
| 55–73 | `test_put_assumptions_upserts_and_sets_unit_from_catalogue` | Units come from the catalogue; a second PUT updates instead of duplicating. |
| 76–89 | `test_put_assumptions_rejects_invalid_items` | 3 tests: wrong mode, over 100 %, unknown key. And **nothing** is saved. |
| 92–95 | `test_put_assumptions_rejects_duplicate_keys` | The same key twice in one PUT → 400. |
| 101–102 | `make_component` | (A helper, not a test.) |
| 105–120 | `test_create_component_with_dependencies_by_key` | `depends_on: ["payment-gateway"]` works with keys. |
| 123–136 | `test_component_cannot_depend_on_another_business` | ⭐ Even Alice's **other** business's parts can't be used. |
| 139–148 | `test_dependency_cycles_are_rejected` | b needs a, c needs b; "a needs c" would be a loop → 400 mentioning "loop". |
| 151–154 | `test_component_cannot_depend_on_itself` | a needs a → 400. |
| 157–161 | `test_duplicate_component_key_is_rejected` | Two `warehouse` keys → 400. |
| 164–169 | `test_criticality_must_be_1_to_5` | 9 → 400. |
| 175–187 | `test_assumption_form_shows_catalogue_errors_on_its_fields` | 2 tests: the admin's form shows a misspelt key under **Key** and a bad number under **Value**, instead of crashing (lesson 5.3, line 87). |
| 193–201 | `test_user_without_an_organization_gets_403_not_a_crash` | A user with no organization (like a `createsuperuser` account) gets a clear 403, and nothing is created (lesson 5.5, lines 43–44). |

### `simulations/tests/test_scenario_api.py` (6 tests)

| Lines | Test | Proves |
|---|---|---|
| 8–24 | `test_create_scenario_validates_and_fills_defaults` | `kind` is set from the template, defaults are filled in, and `missing_inputs` is listed. |
| 27–34 | `test_missing_inputs_shrinks_as_assumptions_are_added` | Add `daily_orders` and it leaves the "missing" list. |
| 37–44 | `test_template_must_match_business_mode` | A warehouse shutdown on an idea → 400 mentioning "operating". |
| 47–60 | `test_bad_parameters_are_reported_per_field` | Two bad parameters → both reported, under `parameters`. |
| 63–74 | `test_template_cannot_change_after_creation` | PATCH `template_key` → 400. |
| 77–87 | `test_catalogue_endpoints` | The two catalogue addresses answer, and `conversion_rate` is only under `idea`. |

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `fixture 'alice_shop' not found` | Your `conftest.py` is missing lines 40–70. Copy the whole file from the reference project. |
| `ModuleNotFoundError: No module named 'businesses.tests'` | Add the empty `__init__.py` in the `tests` folder. |
| `I001 Import block is un-sorted` from ruff | Run `ruff check --fix .`, and check `pyproject.toml` has the `known-first-party` list from lesson 5.2. |
| A test fails | Read its name: it tells you which rule is broken. Compare that file with the reference project. |

## ❓ Quiz

1. How many tests does one `parametrize` with 3 rows make?
2. Why do the catalogue tests run without Django?
3. Which test would catch a template that needs a misspelt input?

---

**Part 5 done! 🎉** Your app can store businesses, their numbers, their parts and their
"what if?" questions, safely, per organization. Next: the maths that answers those
questions, in [Part 6 · The simulation engine](../06-simulation-engine/README.md).

<details><summary>Quiz answers</summary>

1. Three.
2. `simulation_engine` is plain Python and doesn't import Django; `conftest.py` keeps its
   Django imports inside the fixtures.
3. `test_every_template_requires_only_known_inputs_of_its_own_mode`.

</details>
