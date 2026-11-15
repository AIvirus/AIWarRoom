# 5.5 · The business API

**Time:** 40 minutes · **Before this:** [5.4](04-serializers.md).

## 📖 Read

In lesson 4.7 you wrote a small API with a **function** (`me`) and one **ViewSet**
(`OrganizationViewSet`, read only). Now you'll use a full `ModelViewSet`. One class gives
you five actions for free:

| HTTP request | ViewSet action | Does |
|---|---|---|
| `GET /businesses/` | `list` | All rows |
| `POST /businesses/` | `create` | Make one |
| `GET /businesses/<id>/` | `retrieve` | One row |
| `PATCH /businesses/<id>/` | `partial_update` | Change some fields |
| `DELETE /businesses/<id>/` | `destroy` | Remove one |

You change the behaviour by overriding small **hook** methods, such as:

| Hook | Called... | We use it to... |
|---|---|---|
| `get_queryset()` | to find rows, for every action | hide other organizations' rows, and archived ones |
| `perform_create(serializer)` | to save a new row | set the organization from the logged-in user |
| `perform_destroy(instance)` | to delete a row | archive instead, and only for owners |

And `@action` adds **extra** addresses to a ViewSet: here
`/businesses/<id>/assumptions/`.

### The "for now" version

The finished `businesses/api.py` also has two actions that need Parts 7 and 8 (reading
the company's website and the AI committee). For now, use the version in
[`for-now/businesses/api.py`](for-now/businesses/api.py), which leaves them out.

## ⌨️ Do

Create `businesses/api.py`:

<!-- source: self-learning-guide/05-business-and-api/for-now/businesses/api.py:1-89 -->
```python
"""
Business endpoints. Every view gets its rows through OrgScopedMixin or business_for(),
so a user can only ever touch businesses in their own organization.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.access import OrgScopedMixin, organization_for
from accounts.models import Membership

from .models import BusinessComponent, BusinessProfile
from .serializers import (
    AssumptionBulkSerializer,
    BusinessComponentSerializer,
    BusinessProfileSerializer,
    FinancialAssumptionSerializer,
)


def business_for(user, business_id) -> BusinessProfile:
    """The business with this id IF the user's organization owns it; otherwise 404."""
    return get_object_or_404(BusinessProfile.objects.for_user(user), pk=business_id)


class BusinessViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = BusinessProfileSerializer
    queryset = BusinessProfile.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list" and self.request.query_params.get("archived") != "true":
            queryset = queryset.active()
        return queryset

    def perform_create(self, serializer):
        # The organization comes from the logged-in user, never from the request body.
        organization = organization_for(self.request.user)
        if organization is None:  # e.g. a superuser made with createsuperuser
            raise PermissionDenied("Your account isn't part of an organization yet.")
        serializer.save(organization=organization, created_by=self.request.user)

    def perform_destroy(self, instance):
        """DELETE archives: past runs and decisions must stay readable. Owners only."""
        is_owner = Membership.objects.filter(
            user=self.request.user, organization=instance.organization, role=Membership.Role.OWNER
        ).exists()
        if not is_owner:
            raise PermissionDenied("Only an organization owner can archive a business.")
        instance.archived_at = timezone.now()
        instance.save(update_fields=["archived_at", "updated_at"])

    @action(detail=True, methods=["get", "put"])
    def assumptions(self, request, pk=None):
        business = self.get_object()
        if request.method == "GET":
            data = FinancialAssumptionSerializer(business.assumptions.all(), many=True).data
            return Response(data)
        serializer = AssumptionBulkSerializer(data=request.data, context={"business": business})
        serializer.is_valid(raise_exception=True)
        saved = serializer.save()
        return Response(FinancialAssumptionSerializer(saved, many=True).data)


class ComponentViewSet(viewsets.ModelViewSet):
    """Components of one business: /api/v1/businesses/<business_pk>/components/."""

    serializer_class = BusinessComponentSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_business(self):
        if not hasattr(self, "_business"):
            self._business = business_for(self.request.user, self.kwargs["business_pk"])
        return self._business

    def get_queryset(self):
        return BusinessComponent.objects.filter(business=self.get_business()).prefetch_related(
            "depends_on"
        )

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "business": self.get_business()}

    def perform_create(self, serializer):
        serializer.save(business=self.get_business())
```

## ✅ Check

```bash
python manage.py check
```

prints `System check identified no issues (0 silenced).` You can't visit the addresses
yet: lesson 5.7 adds them to `config/urls.py`.

## 🔍 Line by line

### Imports (lines 1–22)

- **Lines 1–4** · Docstring: every view gets its rows through one of two safe paths.
- **Line 6** · `get_object_or_404`: "find this row, or answer 404".
- **Line 7** · `timezone.now()` gives the current time with its time zone.
- **Line 8** · DRF's `viewsets`.
- **Line 9** · `action`, to add extra addresses to a ViewSet.
- **Line 10** · `PermissionDenied` → a **403** answer ("you may not do this").
- **Line 11** · `Response`, a reply that DRF turns into JSON.
- **Lines 13–14** · From lesson 4.6: the organization filter and "which organization is
  this user in?", plus the Membership model (to check roles).
- **Lines 16–22** · Our models and serializers. The round brackets let an import list go
  over several lines.

### `business_for` (lines 25–27)

- **Line 25** · A helper: given a user and a business id, return the business.
- **Line 26** · Docstring.
- **Line 27** · Search **only** the user's businesses (`for_user`, lesson 4.4). Bob's
  business isn't in Alice's search, so for Alice it's a 404, exactly the rule from
  lesson 4.6.

### `BusinessViewSet` (lines 30–66)

- **Line 30** · `OrgScopedMixin` first, then `ModelViewSet`. Python looks for methods in
  the classes from **left to right**, so the mixin's `get_queryset` runs first and then
  calls the ViewSet's with `super()`.
- **Line 31** · Use the serializer from lesson 5.4.
- **Line 32** · Start from all businesses; the mixin narrows them to "mine".
- **Line 34** · Override `get_queryset` once more, on top of the mixin's.
- **Line 35** · Get the mixin's result: only my organization's businesses.
- **Lines 36–37** · For the **list**, hide archived businesses, unless the address ends
  with `?archived=true`. `query_params` holds the part of the address after `?`.
  A single business (retrieve) is still found even when archived, so old links keep
  working.
- **Line 38** · Return the rows.
- **Line 40** · When a new business is created...
- **Line 41** · (comment: the key security rule)...
- **Line 42** · ...find the organization of the **logged-in user**.
- **Lines 43–44** · A user with **no** organization (the superuser you made with
  `createsuperuser` in lesson 4.5 is one: only sign-up creates an organization) gets a
  clear 403 instead of a crash.
- **Line 45** · Save the business with that organization and `created_by` = that user.
  Anything a client sends as `organization` was already thrown away, because it isn't in
  the serializer's fields (lesson 5.4).
- **Line 47** · DELETE calls this.
- **Line 48** · Docstring.
- **Lines 49–51** · Is the user an **owner** of this business's organization? `.exists()`
  asks the database "is there at least one such row?", which is faster than loading it.
- **Lines 52–53** · Not an owner: answer 403 with a clear message.
- **Line 54** · Archive: write the current time.
- **Line 55** · Save **only** these two fields (`update_fields`). Quicker, and it can't
  accidentally overwrite another field someone just changed. DRF then answers **204 No
  Content** ("done, nothing to show").
- **Line 57** · `@action(detail=True, ...)` adds `/businesses/<id>/assumptions/`.
  `detail=True` means "on one business" (the address has an id). It accepts GET and PUT.
- **Line 58** · DRF passes the id as `pk` ("primary key").
- **Line 59** · `self.get_object()` finds the business **through `get_queryset`**, so it
  is already protected: another organization's id gives 404.
- **Lines 60–62** · GET: send all its numbers, using the one-item serializer with
  `many=True` for a list.
- **Line 63** · PUT: build the bulk serializer with the request's JSON, and put the
  business into its **context** (lesson 5.4).
- **Line 64** · Check everything. `raise_exception=True` means: if anything is wrong, stop
  here and answer **400** with the error shape.
- **Line 65** · Save (inside one transaction, lesson 5.4).
- **Line 66** · Reply with the saved numbers.

### `ComponentViewSet` (lines 69–89)

Components live **under** a business: `/businesses/<business_pk>/components/`. So this
ViewSet first finds the business, safely, and then works only inside it.

- **Line 69** · A `ModelViewSet` **without** the mixin: the protection comes from
  `business_for` instead (line 77).
- **Line 70** · Docstring with the address.
- **Line 72** · The serializer from lesson 5.4.
- **Line 73** · Only these methods are allowed. There's no PUT (replace everything);
  PATCH (change some fields) is enough.
- **Line 75** · A helper that finds the business from the address.
- **Line 76** · `hasattr` checks "have I already found it?". The ViewSet asks for the
  business several times per request; this way the database is asked only once.
- **Line 77** · Find it with `business_for`: another organization's business id gives
  404. `self.kwargs` holds the values taken from the address, like `business_pk`.
- **Line 78** · Return it.
- **Lines 80–83** · The rows: only this business's components. `prefetch_related` loads
  all their `depends_on` links in **one** extra query, instead of one query per
  component.
- **Lines 85–86** · Add the business to the serializer's context (lesson 5.4 needs it to
  check keys and dependencies). `{**a, "business": ...}` makes a new dictionary with
  everything in `a` plus one more entry.
- **Lines 88–89** · A new component always belongs to the business in the address.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `ImportError: cannot import name 'organization_for'` | Check `accounts/access.py` from lesson 4.6. |
| `AttributeError: 'OrgScopedQuerySet' object has no attribute 'active'` | `BusinessProfile.objects` must use `BusinessQuerySet` (models.py line 46). |
| `ImproperlyConfigured: ... 'queryset' attribute` | `BusinessViewSet` needs line 32. |

## ❓ Quiz

1. Alice sends `DELETE` for Bob's business. What answer does she get, and why?
2. A member (not an owner) sends `DELETE` for their own organization's business. What
   happens?
3. Why does `ComponentViewSet` not need `OrgScopedMixin`?
4. What does `?archived=true` change?

---

**Next:** [5.6 · Scenarios and runs](06-scenarios-and-runs.md)

<details><summary>Quiz answers</summary>

1. **404**. Bob's business isn't in her `get_queryset`, so `get_object` doesn't find it.
2. **403** "Only an organization owner can archive a business." Nothing changes.
3. Every request goes through `get_business`, which uses `business_for`, which only
   searches the user's own businesses.
4. The list includes archived businesses too.

</details>
