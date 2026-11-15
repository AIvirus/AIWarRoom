# 5.3 · Business tables

**Time:** 45 minutes · **Before this:** [5.2](02-the-catalogue.md).

## 📖 Read

You made the `businesses` app in lesson 4.2 (with `startapp`) but left it empty. Now it
gets three tables. Remember from lesson 4.5: a **model** is a Python class, and Django
turns it into a database table with a **migration**.

New kinds of model field in this lesson:

| Field | Stores | Example |
|---|---|---|
| `DecimalField` | An exact number with a fixed number of decimals | `2400.0000` |
| `URLField` | Text that must look like a web address | `https://kirana.example` |
| `SlugField` | Short text with only letters, numbers, `-` and `_` | `payment-gateway` |
| `PositiveSmallIntegerField` | A small whole number, 0 or more | `5` |
| `ManyToManyField` | Links between rows, many on each side | "checkout needs payment-gateway **and** storefront" |

Two new ideas about **rules in the database itself**:

- A **unique constraint** says "no two rows may have the same values here". One business
  can't have two `daily_orders` numbers.
- A **check constraint** says "every row must pass this test". Criticality must be 1–5.

Even if some code forgets to check, the database refuses bad data. That's the last line
of defence.

### Archive, don't delete

If you delete a business, every past run and decision about it would vanish too. So
AI WarRoom **archives** instead: it writes the time into `archived_at`, and lists simply
hide archived businesses. Nothing is lost.

## ⌨️ Do

### 1. `businesses/models.py`

Replace the file's contents with:

<!-- source: businesses/models.py:1-146 -->
```python
"""
The business being simulated.

BusinessProfile      - one business idea or operating company, owned by an organization.
FinancialAssumption  - one number the simulation uses, with its unit and where it came from.
BusinessComponent    - a part of the operation (payment gateway, warehouse, courier...) and
                       which other components it depends on.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import BaseModel
from common.querysets import OrgScopedQuerySet
from simulation_engine import catalog


class BusinessQuerySet(OrgScopedQuerySet):
    def active(self):
        return self.filter(archived_at__isnull=True)


class BusinessProfile(BaseModel):
    class Mode(models.TextChoices):
        IDEA = catalog.IDEA, "Idea (not launched)"
        OPERATING = catalog.OPERATING, "Operating company"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="businesses"
    )
    mode = models.CharField(max_length=10, choices=Mode.choices)
    name = models.CharField(max_length=120)
    industry = models.CharField(max_length=80, default="E-commerce")
    description = models.TextField(blank=True)
    website_url = models.URLField(blank=True)
    # One currency per business; the MVP supports INR only so amounts are never mixed.
    currency = models.CharField(max_length=3, default="INR", choices=[("INR", "Indian rupee")])
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Archive instead of delete: past runs and decisions must stay readable.
    archived_at = models.DateTimeField(null=True, blank=True)

    ORG_PATH = "organization"
    objects = BusinessQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class FinancialAssumption(BaseModel):
    class Source(models.TextChoices):
        USER = "user", "User input"
        ILLUSTRATIVE = "illustrative", "Illustrative"
        DERIVED = "derived", "Derived"
        FROM_SITE = "from_site", "From company site"

    business = models.ForeignKey(
        BusinessProfile, on_delete=models.CASCADE, related_name="assumptions"
    )
    key = models.CharField(max_length=60)
    # 16 digits with 4 decimals covers rupee amounts in crores and rates like 2.5 %.
    value = models.DecimalField(max_digits=16, decimal_places=4)
    unit = models.CharField(max_length=40, editable=False)
    source = models.CharField(max_length=15, choices=Source.choices, default=Source.USER)
    note = models.CharField(max_length=240, blank=True)

    ORG_PATH = "business__organization"
    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(fields=["business", "key"], name="unique_assumption_key")
        ]

    def clean(self):
        try:
            self.value = catalog.parse_input(self.key, self.value)
        except catalog.CatalogError as error:
            # Name a real form field (the admin crashes on any other name): the key if it's
            # unknown, otherwise the value.
            field = "value" if self.key in catalog.INPUTS else "key"
            raise ValidationError({field: error.errors[self.key]}) from None

    def save(self, *args, **kwargs):
        # The unit always comes from the catalogue, never from the client.
        spec = catalog.INPUTS.get(self.key)
        self.unit = spec.unit if spec else ""
        super().save(*args, **kwargs)

    @property
    def label(self):
        spec = catalog.INPUTS.get(self.key)
        return spec.label if spec else self.key

    def __str__(self):
        return f"{self.key} = {self.value} {self.unit}"


class BusinessComponent(BaseModel):
    class Kind(models.TextChoices):
        STOREFRONT = "storefront", "Storefront"
        PAYMENT = "payment", "Payment gateway"
        WAREHOUSE = "warehouse", "Warehouse"
        LOGISTICS = "logistics", "Logistics partner"
        SUPPLIER = "supplier", "Supplier"
        CUSTOMERS = "customers", "Customers"
        REVENUE = "revenue", "Revenue"

    business = models.ForeignKey(
        BusinessProfile, on_delete=models.CASCADE, related_name="components"
    )
    key = models.SlugField(max_length=40)
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    criticality = models.PositiveSmallIntegerField(
        default=3, help_text="1 = nice to have, 5 = business stops without it"
    )
    fallback_note = models.CharField(max_length=240, blank=True)
    # "Checkout depends on the payment gateway" is stored as
    # checkout.depends_on = [payment_gateway]. Not symmetrical: the gateway doesn't
    # depend on checkout.
    depends_on = models.ManyToManyField(
        "self", symmetrical=False, related_name="dependents", blank=True
    )

    ORG_PATH = "business__organization"
    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(fields=["business", "key"], name="unique_component_key"),
            models.CheckConstraint(
                condition=models.Q(criticality__gte=1, criticality__lte=5),
                name="criticality_1_to_5",
            ),
        ]

    def __str__(self):
        return self.name
```

### 2. The loop check: `businesses/services/dependencies.py`

Make a folder `businesses/services/` with an **empty** `__init__.py` inside, then create
`businesses/services/dependencies.py`:

<!-- source: businesses/services/dependencies.py:1-30 -->
```python
"""Rules for the component dependency graph."""


def creates_cycle(component, proposed_dependencies) -> bool:
    """
    Would `component` depending on `proposed_dependencies` create a loop?

    A loop (A needs B, B needs C, C needs A) makes failure propagation meaningless, so we
    refuse it. We walk "downhill" from each proposed dependency through what *it* depends
    on; if we ever reach `component` again, the new edge would close a circle.
    """
    target_id = component.pk
    to_visit = [dep.pk for dep in proposed_dependencies]
    seen = set()
    # Imported here so this module stays importable without app loading (tests, shell).
    from businesses.models import BusinessComponent

    while to_visit:
        current = to_visit.pop()
        if current == target_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        to_visit.extend(
            BusinessComponent.depends_on.through.objects.filter(
                from_businesscomponent_id=current
            ).values_list("to_businesscomponent_id", flat=True)
        )
    return False
```

### 3. `businesses/admin.py`

Replace the file's contents with:

<!-- source: businesses/admin.py:1-22 -->
```python
from django.contrib import admin

from .models import BusinessComponent, BusinessProfile, FinancialAssumption


class AssumptionInline(admin.TabularInline):
    model = FinancialAssumption
    extra = 0
    readonly_fields = ["unit"]


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "mode", "organization", "archived_at"]
    list_filter = ["mode"]
    inlines = [AssumptionInline]


@admin.register(BusinessComponent)
class BusinessComponentAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "business", "criticality"]
    filter_horizontal = ["depends_on"]
```

### 4. Make and apply the migration

```bash
python manage.py makemigrations businesses
```

```bash
python manage.py migrate
```

## ✅ Check

`makemigrations` prints:

```text
Migrations for 'businesses':
  businesses/migrations/0001_initial.py
    + Create model BusinessProfile
    + Create model BusinessComponent
    + Create model FinancialAssumption
```

and `migrate` ends with `Applying businesses.0001_initial... OK`.

Now start the server (`python manage.py runserver`), log in to
**http://127.0.0.1:8000/admin/** with the superuser from lesson 4.5, and you'll see a new
**Businesses** section. Click **Business profiles → Add**. Pick an **Organization** (the
one you made when you signed up in Part 4), mode "Operating company", a name, and
yourself as **Created by**. At the bottom, click **Add another Financial assumption** and
type key `daily_orders` and value `2400`. Click **Save and continue editing**. The
**Unit** column fills itself in: `orders/day`.

Now add another assumption with key `daily_ordrs` (spelt wrong) and save: the admin shows
"is not a known assumption" next to the **Key** box. Fix the key to `average_order_value`
and try value `-5`: "must be at least 0 INR/order" appears next to **Value**. Delete that
row (tick **Delete?**) and save. Stop the server with **Ctrl + C**.

## 🔍 Line by line

### `businesses/models.py`

- **Lines 1–8** · Docstring naming the three models.
- **Line 10** · `settings`, to point at the user model (as in lesson 4.5).
- **Line 11** · `ValidationError`, the error Django forms and the admin know how to show
  next to a field.
- **Line 12** · `models`, Django's model tools.
- **Lines 14–15** · Our building blocks from lesson 4.4: `BaseModel` (id, created_at,
  updated_at) and `OrgScopedQuerySet` (the `for_user` filter).
- **Line 16** · The catalogue from lesson 5.2.
- **Line 19** · A queryset just for businesses, built **on top of** `OrgScopedQuerySet`,
  so it keeps `for_user` and adds one more method.
- **Lines 20–21** · `active()` = "not archived". `archived_at__isnull=True` means "the
  archive date is empty". The double underscore `__` adds a test to a field name.
- **Line 24** · The business table.
- **Lines 25–27** · The two modes. `TextChoices` (lesson 4.5) gives each choice a stored
  value and a human label. The values come from the catalogue, so they can never differ.
- **Lines 29–31** · Which organization owns the business. `on_delete=models.CASCADE`:
  delete the organization and its businesses go too. `related_name="businesses"` lets
  you write `organization.businesses.all()`.
- **Line 32** · The mode, at most 10 letters, one of the two choices.
- **Line 33** · The name, at most 120 letters.
- **Line 34** · Industry, "E-commerce" unless told otherwise.
- **Line 35** · A longer description. `blank=True` means forms may leave it empty.
- **Line 36** · The company website (Part 8 reads it). Optional.
- **Lines 37–38** · The currency. Only Indian rupees for now, so amounts are never mixed
  up (₹100 + $100 is not 200 of anything).
- **Lines 39–41** · Who created it. `null=True, on_delete=models.SET_NULL`: if that user
  is deleted, keep the business and just empty this field. `related_name="+"` means "I
  don't need a reverse link from the user".
- **Lines 42–43** · The archive date. Empty (`null`) means "active".
- **Line 45** · `ORG_PATH` tells the `for_user` filter (lesson 4.4) how to get from this
  row to its organization: just one step, `organization`.
- **Line 46** · Use our queryset, so `BusinessProfile.objects.for_user(user).active()`
  works.
- **Lines 48–49** · Lists come out sorted by name.
- **Lines 51–52** · How a business prints: its name.
- **Line 55** · One business number.
- **Lines 56–60** · Where the number came from. This matters for honesty: the app always
  shows whether a number was typed by the user, is an illustrative example, was worked
  out from other numbers, or was read from the company's site.
- **Lines 62–64** · Which business it belongs to. `business.assumptions.all()` lists them.
- **Line 65** · The catalogue key, like `daily_orders`.
- **Lines 66–67** · The value: up to 16 digits, 4 of them after the decimal point.
- **Line 68** · The unit. `editable=False` hides it from forms: it is never typed.
- **Line 69** · The source, "user" by default.
- **Line 70** · An optional short note ("from last month's report").
- **Lines 72–73** · The path to the organization is two steps this time:
  `business__organization` (from the assumption to its business, then to its
  organization).
- **Lines 75–79** · Sorted by key. The **unique constraint**: each business can have each
  key only once.
- **Line 81** · `clean()` is Django's hook for checks. The admin and model forms call it
  before saving.
- **Lines 82–83** · Ask the catalogue to check the value (and get back a clean Decimal).
- **Line 84** · If the catalogue refuses...
- **Lines 85–86** · ...a comment explains the next two lines.
- **Line 87** · ...pick which form field to blame. A form only has fields called `key`,
  `value`, `source` and `note`. If the key itself is unknown, blame `key`; otherwise the
  value is the problem.
- **Line 88** · Raise a `ValidationError` as `{field: message}`, so the admin shows the
  message right next to that field. (If we named a field the form doesn't have, like
  `daily_orders`, Django would crash instead. A test in lesson 5.8 guards this.)
- **Line 90** · We override `save()` (lesson 4.6 explained overriding).
- **Lines 91–93** · Look the key up in the catalogue and copy its unit. The unit can
  **never** come from the user.
- **Line 94** · Then do the normal save.
- **Lines 96–99** · `@property` makes a method look like a field: `assumption.label`
  (no brackets) gives the human name from the catalogue.
- **Lines 101–102** · Prints like `daily_orders = 2400.0000 orders/day`.
- **Line 105** · One part of the operation.
- **Lines 106–113** · The kinds of part.
- **Lines 115–117** · Its business.
- **Line 118** · A short code name like `payment-gateway`.
- **Line 119** · The display name, like "Razorpay".
- **Line 120** · Its kind, from the list above.
- **Lines 121–123** · How important it is, 3 by default. `help_text` appears under the
  field in forms.
- **Line 124** · What the business can do if it fails ("switch to Cashfree").
- **Lines 125–127** · Comment explaining direction: "checkout depends on the gateway" is
  stored on checkout. It's one-way.
- **Lines 128–130** · The many-to-many link **to the same table** (`"self"`).
  `symmetrical=False` makes it one-way. `related_name="dependents"` gives the other
  direction: `gateway.dependents.all()` = "who needs the gateway?".
- **Lines 132–133** · Organization path and queryset, as before.
- **Lines 135–143** · Sorted by key; key unique per business; and a **check constraint**:
  `models.Q(criticality__gte=1, criticality__lte=5)` means "greater than or equal to 1
  and less than or equal to 5".
- **Lines 145–146** · Prints its name.

### `businesses/services/dependencies.py`

A **loop** is when A needs B, B needs C, and C needs A. Then "what fails when A fails?"
never ends, so we refuse it.

- **Line 1** · Docstring.
- **Line 4** · The question: if `component` were to depend on `proposed_dependencies`,
  would that close a loop? Returns `True` or `False`.
- **Lines 5–11** · Docstring explaining the idea: walk "downhill" from each proposed
  dependency; if you ever arrive back at `component`, it's a loop.
- **Line 12** · The id we're looking out for.
- **Line 13** · A to-do list of ids to visit, starting with the proposed dependencies.
- **Line 14** · Ids we've already visited (so we never visit one twice).
- **Lines 15–16** · Import the model **inside** the function. The comment says why: the
  file can then be imported before Django has loaded the apps.
- **Line 18** · Keep going while the to-do list isn't empty.
- **Line 19** · `pop()` takes the last id off the list.
- **Lines 20–21** · Arrived back at the start? Loop found.
- **Lines 22–24** · Already visited? Skip it. Otherwise remember it.
- **Lines 25–29** · Add everything **this** one depends on to the to-do list. A
  many-to-many field is stored in a hidden **link table** (`through`), with one row per
  arrow: `from_businesscomponent_id` → `to_businesscomponent_id`. We ask that table
  directly for the ids, which is one quick query.
- **Line 30** · Visited everything and never came back: no loop.

This walk is called a **depth-first search**. You'll see the same idea in Part 6, when
a failure spreads through the parts.

### `businesses/admin.py`

- **Line 1** · The admin tools.
- **Line 3** · Our three models.
- **Lines 6–9** · An **inline**: assumptions appear as a little table **inside** the
  business page. `extra = 0` shows no empty rows until you click "Add another". `unit`
  is shown but can't be edited.
- **Lines 12–16** · The business admin page: which columns the list shows, a filter by
  mode in the side bar, and the assumptions inline.
- **Lines 19–22** · The component admin page. `filter_horizontal` shows `depends_on` as
  two boxes with arrows, which is much easier than a long multi-select list.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `No changes detected` | Is `"businesses"` in `INSTALLED_APPS` (lesson 4.3)? Did you save `models.py`? |
| `ImportError: cannot import name 'OrgScopedQuerySet'` | Check `common/querysets.py` from lesson 4.4. |
| `fields.E304` / "clashes with reverse accessor" | A `related_name` is mistyped; compare with lines 30, 63, 116, 129. |
| The unit stays empty in the admin | The key isn't in the catalogue, or line 93 is mistyped. |

## ❓ Quiz

1. What does `archived_at = None` mean?
2. Why is `unit` set in `save()` instead of being typed by the user?
3. A business already has `daily_orders`. What stops a second `daily_orders` row?
4. Checkout depends on the gateway. Does the gateway depend on checkout?

---

**Next:** [5.4 · Serializers](04-serializers.md)

<details><summary>Quiz answers</summary>

1. The business is active (not archived).
2. So it always matches the catalogue. A user could type the wrong unit; the code can't.
3. The unique constraint `unique_assumption_key` (line 78): the database itself refuses.
4. No. `symmetrical=False` (line 129) makes the link one-way.

</details>
