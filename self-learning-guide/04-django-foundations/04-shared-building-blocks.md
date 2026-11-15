# 4.4 · Shared building blocks

**Time:** 30 minutes · **Before this:** [4.3](03-settings.md).

## 📖 Read

Two small pieces are used by **every** table in AI WarRoom, so they live in a shared
folder called `common`:

1. **`BaseModel`**: every table gets three columns for free: a random `id`, a
   `created_at` time and an `updated_at` time.
2. **`OrgScopedQuerySet`**: the "who can see this?" filter. Every table that belongs to
   an organization uses it, so a user only ever gets rows from **their own**
   organization.

### Why random ids (UUIDs)?

Normally ids count up: 1, 2, 3... Then a URL like `/businesses/41/` tells everyone you
have about 41 businesses, and a curious person might try `/businesses/42/` to peek at
someone else's. A **UUID** is a long random id like
`8eeeee08-1000-41c9-99d0-891849672f56`, which is impossible to guess.

### What's a QuerySet?

In Django you don't write SQL yourself (lesson 3.2). You write Python, and Django turns it
into SQL:

| Python (Django) | SQL Django writes for you |
|---|---|
| `Organization.objects.all()` | `SELECT * FROM organization` |
| `Organization.objects.filter(name="Kirana Co")` | `... WHERE name = 'Kirana Co'` |
| `.first()` | `... LIMIT 1` |

`Organization.objects` is the table's **manager**, and what it returns is a **QuerySet**:
a list-like set of rows that you can keep narrowing down. Our `OrgScopedQuerySet` adds
one extra method, `for_user(user)`, which narrows the rows to the user's organization.

## ⌨️ Do

Create a folder `common` in `my-warroom`, with an empty `__init__.py` file and these
three files.

### `common/models.py`

<!-- source: common/models.py:1-21 -->
```python
"""Abstract base model shared by every app."""

import uuid

from django.db import models


class BaseModel(models.Model):
    """
    UUID primary key plus timestamps.

    UUIDs mean a URL like /businesses/<id>/ doesn't reveal how many records exist, and
    nobody can guess a neighbour's id by adding one.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

### `common/querysets.py`

<!-- source: common/querysets.py:1-30 -->
```python
"""
The organization filter used by every org-owned model.

Each such model declares ORG_PATH, the ORM path from that model to its Organization:

    Organization        ORG_PATH = ""
    BusinessProfile     ORG_PATH = "organization"
    SimulationRun       ORG_PATH = "business__organization"

and uses `objects = OrgScopedQuerySet.as_manager()`. Then
`Model.objects.for_user(user)` returns only rows in organizations the user belongs to.

This lives in `common/` (not `accounts/`) because models import it, and it must not
import anything from Django's auth views, or app loading becomes circular.
"""

from django.db import models


def membership_lookup(model) -> str:
    """Build the filter keyword that reaches Membership.user from `model`."""
    path = model.ORG_PATH
    return f"{path}__memberships__user" if path else "memberships__user"


class OrgScopedQuerySet(models.QuerySet):
    def for_user(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        return self.filter(**{membership_lookup(self.model): user}).distinct()
```

### `common/apps.py`

<!-- source: common/apps.py:1-7 -->
```python
from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Shared base model, querysets and template filters. Has no tables of its own."""

    name = "common"
```

## 🔍 Line by line

### `common/models.py`

- **Line 3** · `uuid` is Python's built-in tool for making random ids.
- **Line 5** · Django's `models` module: the tools for describing tables.
- **Line 8** · `class BaseModel(models.Model):`. A Django model is a **class** (lesson 1.6)
  that **inherits** from `models.Model`. **Inherit** means "starts with everything the
  parent class has", like a child inheriting a family recipe book and adding new pages.
- **Lines 9–14** · Docstring: what it adds, and why UUIDs.
- **Line 16** · `id = models.UUIDField(...)`: a column that holds a UUID.
  - `primary_key=True`: this is the table's primary key (lesson 3.1).
  - `default=uuid.uuid4`: when a row is created, call `uuid.uuid4()` to make a new random
    id. Note: **no brackets** after `uuid4`. We give Django the function itself, to call
    fresh for every new row. With brackets, every row would get the same id!
  - `editable=False`: nobody can change it in forms.
- **Line 17** · `created_at`: a date-and-time column. `auto_now_add=True` sets it
  automatically when the row is first created.
- **Line 18** · `updated_at`: `auto_now=True` updates it automatically on every save.
- **Lines 20–21** · `class Meta:` holds settings **about** the model.
  `abstract = True` means "don't make a table called BaseModel; this is only a blueprint
  for other models to inherit from".

### `common/querysets.py`

- **Lines 1–15** · Docstring explaining the idea:
  - Every model that belongs to an organization says how to reach it, in a variable
    called `ORG_PATH`.
  - In Django, a double underscore `__` means "follow this link to the next table".
  - So `"business__organization"` reads as "this row's business, then that business's
    organization".
- **Line 20** · `membership_lookup(model)` builds the text for a filter.
- **Line 22** · Read the model's `ORG_PATH`.
- **Line 23** · Add the last part of the path: from an organization to its memberships to
  each membership's user. For a business that gives
  `"organization__memberships__user"`. For Organization itself (empty path) it's just
  `"memberships__user"`. The `x if condition else y` form is a one-line if/else.
- **Line 26** · Our own QuerySet type, inheriting everything a normal one can do.
- **Line 27** · A new method, `for_user(user)`.
- **Lines 28–29** · A logged-out visitor sees **nothing**. `self.none()` is an empty
  QuerySet.
- **Line 30** · `self.filter(**{...: user})`:
  - `{membership_lookup(self.model): user}` makes a dictionary, for example
    `{"organization__memberships__user": alice}`.
  - `**` unpacks a dictionary into named arguments. So this is the same as writing
    `self.filter(organization__memberships__user=alice)`, but the name can be chosen while
    the program runs.
  - In plain words: "only rows whose organization has a membership for this user".
  - `.distinct()` removes duplicates, in case one path matches a row twice.

### `common/apps.py`

- **Line 4** · An `AppConfig` describes an app to Django.
- **Line 7** · `name = "common"` must match the folder name and the entry in
  `INSTALLED_APPS`.

## ✅ Check

Nothing to run yet. Check that `common/` has four files: `__init__.py`, `models.py`,
`querysets.py`, `apps.py`.

## ❓ Quiz

1. What three columns does every table get from `BaseModel`?
2. Why is it `default=uuid.uuid4` and not `default=uuid.uuid4()`?
3. For `ORG_PATH = "business__organization"`, what filter does `for_user` build?

---

**Next:** [4.5 · Users and organizations](05-users-and-organizations.md)

<details><summary>Quiz answers</summary>

1. `id` (a UUID), `created_at`, `updated_at`.
2. Django must call the function **for every new row**. With brackets it would be called
   once, and every row would share that one id.
3. `business__organization__memberships__user=user`.

</details>
