# 4.6 · Who sees what

**Time:** 25 minutes · **Before this:** [4.5](05-users-and-organizations.md).

## Read

AI WarRoom holds private business numbers. The most important security rule is:

> **A user may only ever see their own organization's data.**

The easy way to get this wrong is to check it in 50 different places and forget one.
So AI WarRoom decides it in **one place**, and every page and every API endpoint uses
that one place.

### The 404 rule

What should happen when Alice asks for Bob's business, `/businesses/41/`?

- Wrong: **403 "Forbidden"** would tell Alice "that business exists, you just can't see it".
- Right: **404 "Not found"**: Alice's search simply doesn't contain Bob's rows, so for her
  the business doesn't exist. She learns nothing at all.

## Do

Create `accounts/access.py`:

<!-- source: accounts/access.py:1-51 -->
```python
"""
Organization-level access control for views: the ONE place pages and API endpoints
decide who sees what.

The filter itself is `OrgScopedQuerySet.for_user()` in common/querysets.py. The mixins
below apply it to every class-based view and DRF ViewSet. A record from another
organization is simply absent from the queryset, so views answer 404, not 403. That
way we don't even confirm that the record exists.
"""

from django.contrib.auth.mixins import LoginRequiredMixin

from common.querysets import membership_lookup

from .models import Membership


def organization_for(user):
    """
    The organization a user is working in.

    The MVP gives each user one organization (created at sign-up). If multi-org support
    is added later, this is the function that would read the "current org" from the
    session instead.
    """
    if not user or not user.is_authenticated:
        return None
    membership = (
        Membership.objects.select_related("organization")
        .filter(user=user)
        .order_by("created_at")
        .first()
    )
    return membership.organization if membership else None


class OrgScopedMixin:
    """
    Use in any class-based view or DRF ViewSet that has a `model` or `queryset`.

    It narrows get_queryset() to the user's organizations, so list, detail, update and
    delete are all protected by the same line of code.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**{membership_lookup(queryset.model): self.request.user}).distinct()


class OrgPageMixin(LoginRequiredMixin, OrgScopedMixin):
    """For HTML pages: send anonymous users to login, then scope by organization."""
```

and `accounts/context_processors.py`:

<!-- source: accounts/context_processors.py:1-8 -->
```python
from .access import organization_for


def current_organization(request):
    """Makes {{ current_org }} available in every template (used by the status bar)."""
    if not request.user.is_authenticated:
        return {}
    return {"current_org": organization_for(request.user)}
```

## Line by line

### `accounts/access.py`

- **Lines 1–9** · Docstring: this is *the* place access is decided, and why the answer
  is 404.
- **Line 11** · `LoginRequiredMixin`: a ready-made Django piece that sends logged-out
  visitors to the login page.
- **Line 13** · The path builder from lesson 4.4.
- **Line 15** · The Membership model.
- **Line 18** · `organization_for(user)`: "which organization is this person working
  in?"
- **Lines 19–25** · Docstring: for now each person has one organization, made at sign-up.
- **Lines 26–27** · Logged-out visitors have no organization.
- **Lines 28–33** · Find the user's first membership. One query, read like a sentence:
  - **29** `select_related("organization")`: fetch the organization in the **same**
    database trip (one query instead of two).
  - **30** `.filter(user=user)`: only this user's memberships.
  - **31** `.order_by("created_at")`: oldest first.
  - **32** `.first()`: just one, or `None` if there isn't any.
  - The round brackets around the chain let it continue over several lines.
- **Line 34** · Return that membership's organization, or `None`.
- **Line 37** · A **mixin**: a small class you add to *other* classes to give them an
  extra ability. Here the ability is "only show my organization's rows".
- **Lines 38–43** · Docstring: how to use it.
- **Line 45** · Django views and DRF ViewSets get their rows from a method called
  `get_queryset`. We **override** it, which means we write our own version of a method
  the parent class already has.
- **Line 46** · `super().get_queryset()` first gets the normal rows from the parent class.
- **Line 47** · Then narrows them with the same `**{path: user}` trick as `for_user`.
  Every list, detail, edit and delete in the app goes through this one line.
- **Line 50** · `OrgPageMixin` = "must be logged in" **plus** "only my organization", for
  web pages. A class can inherit from several parents at once.
- **Line 51** · Its docstring is its whole body: it needs nothing else.

### `accounts/context_processors.py`

- **Line 1** · Import the function above.
- **Line 4** · A context processor receives the request (lesson 4.3 registered it in
  `TEMPLATES`).
- **Line 5** · Docstring: what it's for.
- **Lines 6–7** · Logged out? Add nothing to the page.
- **Line 8** · Return a dictionary. Every template can now use `{{ current_org }}`; the
  status bar at the top of every page shows its name.

## Check

Now run the commands in [lesson 4.5](05-users-and-organizations.md#-do) if you haven't
yet. `python manage.py check` should print:

```text
System check identified no issues (0 silenced).
```

## Quiz

1. Why answer 404 instead of 403 for another organization's record?
2. What does `select_related` save?
3. Where is the organization rule applied for **every** page and API list?

---

**Next:** [4.7 · Sign up, log in, and the first API](07-signup-login-api.md)

<details><summary>Quiz answers</summary>

1. 403 confirms the record exists; 404 reveals nothing.
2. A second trip to the database: the organization comes back with the membership.
3. `OrgScopedMixin.get_queryset` (line 47), which every view and ViewSet uses.

</details>
