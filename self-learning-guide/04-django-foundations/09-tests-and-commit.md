# 4.9 · Tests and your first commit

**Time:** 45 minutes · **Before this:** [4.8](08-pages.md).

## Read

You clicked through the site by hand in 4.8. Tests do the same clicking **automatically**,
in under a second, every time anything changes, including the most important check of
all: **Bob can never see Alice's organization**.

Three small setup files tell the tools how to behave:

| File | Tells... |
|---|---|
| `pytest.ini` | pytest: which settings to use and where tests live |
| `pyproject.toml` | ruff: line length and which checks to run |
| `conftest.py` | pytest: **fixtures**, ready-made test data like "a user called Alice" |

A **fixture** is a function marked `@pytest.fixture`. A test asks for one simply by
having a parameter with the same name: `def test_x(alice):` gets a fresh Alice, created
just for that test.

## Do

### `pytest.ini`

<!-- source: pytest.ini:1-6 -->
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = tests.py test_*.py
# old_code is reference material, not part of this project
norecursedirs = old_code .venv venv .git node_modules staticfiles self-learning-guide
addopts = -q
```

- **Line 1** · The `[pytest]` section header.
- **Line 2** · Use the **test** settings (lesson 4.3): an in-memory database.
- **Line 3** · Test files are named `tests.py` or `test_*.py`.
- **Lines 4–5** · Folders pytest must **not** search. Some of these don't exist in your
  project; that's fine.
- **Line 6** · `-q` (quiet): shorter output.

### `pyproject.toml`

<!-- source: pyproject.toml:1-8 -->
```toml
# Tool configuration only; this project is not packaged.
[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = ["old_code", "*/migrations/*"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "DJ"]
```

- **Line 3** · Lines may be up to 100 characters.
- **Line 4** · Write code for Python 3.12 and newer.
- **Line 5** · Don't check migration files (Django writes those).
- **Line 8** · Which groups of checks to run: **E** style errors, **F** real mistakes
  (like unused imports), **I** import order, **B** likely bugs, **UP** old-fashioned
  Python that has a newer form, **DJ** Django-specific advice.

### `conftest.py` (in the `my-warroom` folder itself)

Copy the whole file from the reference project. These are the lines you use now:

<!-- source: conftest.py:1-37 -->
```python
"""
Shared test fixtures: two organizations that must never see each other's data.

alice  owns "Kirana Express" (operating company) and "Kirana Idea" (idea).
bob    owns "Rival Mart" (operating company) in a different organization.

Django imports live INSIDE the fixtures so `pytest -p no:django simulation_engine` can run
the pure engine tests without Django being configured at all.
"""

import pytest

PASSWORD = "harbour-lantern-42"


@pytest.fixture
def alice(db):
    from accounts.services import register_owner

    return register_owner(
        email="alice@kirana.test", password=PASSWORD, full_name="Alice", org_name="Kirana Co"
    )


@pytest.fixture
def bob(db):
    from accounts.services import register_owner

    return register_owner(
        email="bob@rival.test", password=PASSWORD, full_name="Bob", org_name="Rival Co"
    )


def org_of(user):
    from accounts.models import Membership

    return Membership.objects.get(user=user).organization
```

- **Lines 1–9** · Docstring: two users in two organizations who must never see each
  other's data. The second paragraph explains a trick used in Part 6.
- **Line 13** · A strong test password that passes Django's rules.
- **Line 16** · `@pytest.fixture` marks a fixture.
- **Line 17** · `alice(db)`: asking for the `db` fixture (from pytest-django) gives this
  fixture access to the test database.
- **Line 18** · Import inside the function (the docstring explains why).
- **Lines 20–22** · Create Alice through the real sign-up service, so tests use the same
  code as the real site.
- **Lines 25–31** · Bob, in a **different** organization.
- **Lines 34–37** · A helper (not a fixture): find a user's organization.

The rest of `conftest.py` makes test businesses for Part 5. It won't run until a test
asks for it, so it's fine to have it already.

### `accounts/tests/test_accounts.py`

Make a folder `accounts/tests/` with an empty `__init__.py`, then copy
`test_accounts.py` from the reference project. Here is what each test proves:

| Lines | Test | What it proves |
|---|---|---|
| 8–17 | (setup) | Imports; `pytestmark = pytest.mark.django_db` lets every test in the file use the database; a strong password. |
| 20–34 | `alice`, `bob` fixtures | Local versions of the same two people. |
| 40–44 | `test_register_owner_creates_user_org_and_owner_membership` | Sign-up makes all three rows, with the **owner** role and slug `kirana-express`. |
| 47–51 | `test_org_slugs_stay_unique_when_names_repeat` | A second "Kirana Express" gets `kirana-express-2`. |
| 54–56 | `test_email_is_normalised_to_lowercase` | `Dev@Example.TEST` is stored as `dev@example.test`. |
| 59–71 | `test_signup_page_creates_account_and_logs_in` | `client` is a pretend browser. POSTing the sign-up form redirects (302) to home, and home then opens (200), so the user really is logged in. |
| 74–86 | `test_signup_rejects_weak_password_and_creates_nothing` | `12345678` is refused, and **no** user or organization is left behind. |
| 89–100 | `test_signup_rejects_duplicate_email` | Signing up again with `ALICE@...` (different capitals) shows "already exists". |
| 103–107 | `test_login_with_email` | Logging in with an email works. |
| 110–113 | `test_home_requires_login` | A logged-out visitor is sent to the login page. |
| 116–119 | `test_logout_is_post_only` | GET on logout is refused (405); POST works. |
| 125–127 | `test_for_user_returns_only_own_organizations` | **Key test.** `for_user(alice)` returns only Alice's organization, never Bob's. |
| 130–133 | `test_for_user_returns_nothing_for_anonymous` | A logged-out visitor gets nothing. |
| 136–140 | `test_api_lists_only_own_organization` | **Key test.** The API list shows only Alice's organization. |
| 143–148 | `test_api_returns_404_for_another_orgs_record` | **Key test.** Alice asking for Bob's organization by its id gets **404** (lesson 4.6). |
| 151–152 | `test_api_requires_authentication` | The API refuses visitors who aren't logged in (403). |
| 155–159 | `test_me_endpoint_reports_current_organization` | `/api/v1/me/` returns the right email and organization. |
| 162–164 | `test_healthz_reports_database` | The health check answers `ok` (tests use SQLite). |
| 167–182 | `test_login_ignores_email_capitals` | Sign up as `Alice@Kirana.test`, log out, then log in typing it the **same** way: it works, because log-in lowercases the email like sign-up does (lesson 4.7). |

The tests marked **Key test** are the most important in the whole project: they're the security wall.

### Run everything

```bash
pytest
```

```bash
ruff format .
```

```bash
ruff check .
```

### Save your work with Git

```bash
git add -A
```

```bash
git commit -m "Part 4: Django foundations"
```

## Check

- `pytest` prints `17 passed`.
- `ruff format .` tidies a few files (for example the `apps.py` files `startapp` made with
  single quotes). Then `ruff check .` prints `All checks passed!`.
- `git log --oneline` shows your commit.

**Try breaking it on purpose:** in `accounts/api.py`, remove `OrgScopedMixin, ` from the
`OrganizationViewSet` line, then run `pytest`. The key tests fail, because now Alice can
see Bob's organization. Put it back. That's exactly why these tests exist.

## The commands

| Command | Meaning |
|---|---|
| `pytest` | Run all tests. |
| `ruff format .` | Rewrite files in the standard style (spacing, quotes, line breaks). Safe: it never changes what the code does. |
| `ruff check .` | Look for mistakes and style problems, and report them. |
| `git add -A` | Put **all** changes (new, changed and deleted files) into the next snapshot. |
| `git commit -m "..."` | Save the snapshot with a message describing it. |

## If it didn't work

| You see | Fix |
|---|---|
| `django.core.exceptions.ImproperlyConfigured: Requested setting ...` | `pytest.ini` is missing or not in `my-warroom`. |
| `no tests ran` | The folder must contain `__init__.py`, and the file name must start with `test_`. |
| `Please tell me who you are` from Git | Do Step 4 of lesson 0.2 (`git config --global user.name ...`). |

---

**Part 4 done! ** You have a working, tested, secure login with organizations. Next:
[Part 5 · Business model and API](../05-business-and-api/README.md)
