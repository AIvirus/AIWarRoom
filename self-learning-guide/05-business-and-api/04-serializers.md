# 5.4 · Serializers

**Time:** 40 minutes · **Before this:** [5.3](03-business-models.md).

## 📖 Read

The API speaks **JSON** (Part 2). The database speaks **Python objects**. Between them
sits a **serializer**, from Django REST Framework (DRF). It works in both directions:

```text
  request JSON  ──►  serializer  ──►  checked Python values  ──►  saved to the database
 {"name": "..."}     (validates)        {"name": "..."}

 database row   ──►  serializer  ──►  response JSON
 BusinessProfile     (.data)           {"id": "...", "name": "..."}
```

A `ModelSerializer` reads your model and builds most of this by itself. You only add the
rules the model doesn't know.

Validation happens in three layers, and you'll see all three below:

| Method | Checks | Example |
|---|---|---|
| `validate_<field>(self, value)` | One field on its own | "criticality must be 1–5" |
| `validate(self, attrs)` | Several fields together | "this key doesn't apply to this mode" |
| The database constraints (5.3) | The last line of defence | "only one `daily_orders` per business" |

When a check fails, raise `serializers.ValidationError("message")`. Our error handler
from lesson 4.7 turns it into the one API error shape:

```json
{"error": {"code": "validation_error", "message": "...", "fields": {"criticality": ["..."]}}}
```

### Context

A serializer sometimes needs to know more than the JSON it was given. For example: "which
business are these assumptions for?" The view passes that in a dictionary called
`context`, and the serializer reads `self.context["business"]`.

## ⌨️ Do

Create `businesses/serializers.py`:

<!-- source: businesses/serializers.py:1-129 -->
```python
from django.db import transaction
from rest_framework import serializers

from simulation_engine import catalog

from .models import BusinessComponent, BusinessProfile, FinancialAssumption
from .services.dependencies import creates_cycle


class BusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = [
            "id",
            "mode",
            "name",
            "industry",
            "description",
            "website_url",
            "currency",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "archived_at", "created_at", "updated_at"]

    def validate_mode(self, value):
        # Switching mode would orphan assumptions that only make sense in the other mode.
        if self.instance and value != self.instance.mode:
            raise serializers.ValidationError("A business can't change mode after creation.")
        return value


class FinancialAssumptionSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)
    # Decimals travel as strings so 0.1 never turns into 0.1000000000000000055.
    value = serializers.DecimalField(max_digits=16, decimal_places=4, coerce_to_string=True)

    class Meta:
        model = FinancialAssumption
        fields = ["key", "label", "value", "unit", "source", "note", "updated_at"]
        read_only_fields = ["unit", "updated_at"]

    def validate(self, attrs):
        key = attrs["key"]
        try:
            attrs["value"] = catalog.parse_input(key, attrs["value"])
        except catalog.CatalogError as error:
            raise serializers.ValidationError(error.errors) from None
        business = self.context["business"]
        if business.mode not in catalog.INPUTS[key].modes:
            raise serializers.ValidationError(
                {key: f"doesn't apply to a business in '{business.mode}' mode"}
            )
        return attrs


class AssumptionBulkSerializer(serializers.Serializer):
    """PUT a list of assumptions; each is created or updated by key."""

    assumptions = FinancialAssumptionSerializer(many=True)

    def validate_assumptions(self, items):
        keys = [item["key"] for item in items]
        duplicates = {key for key in keys if keys.count(key) > 1}
        if duplicates:
            raise serializers.ValidationError(f"Duplicate keys: {', '.join(sorted(duplicates))}")
        return items

    @transaction.atomic
    def save(self):
        business = self.context["business"]
        for item in self.validated_data["assumptions"]:
            FinancialAssumption.objects.update_or_create(
                business=business,
                key=item["key"],
                defaults={
                    "value": item["value"],
                    "source": item.get("source", FinancialAssumption.Source.USER),
                    "note": item.get("note", ""),
                },
            )
        return business.assumptions.all()


class BusinessComponentSerializer(serializers.ModelSerializer):
    # Dependencies are referenced by component key ("payment-gateway"), which reads better
    # in requests and seed files than UUIDs.
    depends_on = serializers.SlugRelatedField(
        slug_field="key", many=True, required=False, queryset=BusinessComponent.objects.none()
    )

    class Meta:
        model = BusinessComponent
        fields = ["id", "key", "name", "kind", "criticality", "fallback_note", "depends_on"]
        read_only_fields = ["id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        business = self.context.get("business")
        if business is not None:
            # Only components of the SAME business can be dependencies.
            self.fields["depends_on"].child_relation.queryset = business.components.all()

    def validate_criticality(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Criticality runs from 1 (minor) to 5 (critical).")
        return value

    def validate_key(self, value):
        business = self.context["business"]
        clash = business.components.filter(key=value)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                "This business already has a component with that key."
            )
        return value

    def validate_depends_on(self, value):
        if self.instance:
            if self.instance in value:
                raise serializers.ValidationError("A component can't depend on itself.")
            if creates_cycle(self.instance, value):
                raise serializers.ValidationError(
                    "That would create a loop (A needs B needs A). Remove one direction."
                )
        return value
```

There's nothing to run yet: a serializer is used by the API, which comes next lesson.
Just check Django can still load everything:

```bash
python manage.py check
```

## ✅ Check

`System check identified no issues (0 silenced).`

## 🔍 Line by line

### Imports (lines 1–7)

- **Line 1** · `transaction`, to make several saves happen "all or nothing".
- **Line 2** · DRF's serializer tools.
- **Line 4** · The catalogue.
- **Line 6** · Our three models.
- **Line 7** · The loop check from lesson 5.3.

### `BusinessProfileSerializer` (lines 10–31)

- **Line 10** · A `ModelSerializer` for businesses.
- **Lines 11–12** · `class Meta` holds the settings: which model...
- **Lines 13–24** · ...and which fields to send and accept. A field **not** in this list
  can't be read or written through the API. That's why `organization` is missing: a
  client must never choose the organization (the view sets it in lesson 5.5).
- **Line 25** · These are sent out but **ignored** if a client sends them. A client can't
  set the id, or pretend a business was archived or created last year.
- **Line 27** · A rule for one field, `mode`. DRF finds it by its name
  (`validate_` + `mode`).
- **Line 28** · The comment says why.
- **Line 29** · `self.instance` is the business being **changed**; it's `None` when
  creating. So: "if we're changing an existing business and the mode is different..."
- **Line 30** · ...refuse.
- **Line 31** · Otherwise return the value unchanged. A `validate_` method **must**
  return the value.

### `FinancialAssumptionSerializer` (lines 34–55)

- **Line 35** · An extra field the model doesn't store: `label` comes from the `@property`
  in lesson 5.3. `read_only=True` means it's only sent out.
- **Lines 36–37** · The value as a **DecimalField** that goes out as text (`"22.5000"`),
  never as a JSON number, so no rounding ever happens on the way.
- **Lines 39–42** · The fields, and which are output only: the unit (from the catalogue)
  and the time it was last changed.
- **Line 44** · `validate(attrs)` sees all fields together. `attrs` is a dictionary of
  values that already passed the per-field checks.
- **Line 45** · The key, like `"daily_orders"`.
- **Lines 46–49** · Ask the catalogue. On success, replace the value with the clean
  Decimal. On failure, raise its `{key: message}` dictionary as a `ValidationError`.
- **Line 50** · The business, from the **context** (see 📖 Read).
- **Lines 51–54** · Does this number belong to this business's mode? `conversion_rate` is
  for ideas only, so an operating shop is refused.
- **Line 55** · All good: return the cleaned values.

### `AssumptionBulkSerializer` (lines 58–83)

Saving numbers one request at a time would be slow and messy. This serializer accepts a
whole list at once: `{"assumptions": [{...}, {...}]}`.

- **Line 58** · A plain `Serializer` (not tied to one model).
- **Line 59** · Docstring. "Created or updated by key" is often called an **upsert**.
- **Line 61** · One field, `assumptions`: a list (`many=True`) where **each item** is
  checked by the serializer above.
- **Line 63** · An extra rule for the list.
- **Line 64** · All the keys in the list.
- **Line 65** · Keys that appear more than once. `{... for ...}` is a **set**
  comprehension; a set never holds the same thing twice.
- **Lines 66–67** · Duplicates? Refuse, naming them in alphabetical order (`sorted`).
- **Line 68** · Return the list.
- **Line 70** · `@transaction.atomic`: everything inside happens completely, or not at all.
  If the third save fails, the first two are undone. No half-saved lists.
- **Line 71** · We write our own `save()`.
- **Line 72** · Which business, from the context.
- **Line 73** · For every checked item...
- **Lines 74–82** · ...`update_or_create`: find the row with this business **and** this
  key; if it exists, update it with the `defaults`, otherwise create it.
  `item.get("source", ...)` uses "user" when the client didn't say.
- **Line 83** · Return all the business's numbers, now saved.

### `BusinessComponentSerializer` (lines 86–129)

- **Lines 87–88** · Comment: dependencies are written by **key** (`"payment-gateway"`),
  which is much easier to read than a long id.
- **Lines 89–91** · A `SlugRelatedField` turns keys into components and back.
  `many=True`: a list of them. `required=False`: you may leave it out.
  `queryset=...objects.none()`: by default **no** component is allowed. We open it up,
  safely, in `__init__`.
- **Lines 93–96** · The fields, and `id` is output only.
- **Line 98** · `__init__` runs when the serializer is created.
- **Line 99** · Do the normal set-up first.
- **Line 100** · Which business, if the view told us.
- **Lines 101–103** · Allow only components of **this** business as dependencies. A
  component of another business (even one of yours) simply isn't found, so the request
  is refused.
- **Lines 105–108** · Criticality 1 to 5. Python lets you write `1 <= value <= 5`, just
  like in maths. The database checks this too (lesson 5.3); checking here as well gives a
  friendly message instead of a database error.
- **Lines 110–119** · No two components of a business may share a key:
  - **112** · Look for components of this business with this key.
  - **113–114** · When **changing** a component, don't count the component itself.
  - **115–118** · Found one? Refuse.
- **Lines 121–129** · Rules for `depends_on`, only when changing an existing component:
  - **123–124** · It can't depend on itself.
  - **125–128** · It can't close a loop (the walk from lesson 5.3).
  - **129** · Return the list.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `ImportError: cannot import name 'creates_cycle'` | Check the file name `businesses/services/dependencies.py` and the empty `__init__.py` beside it. |
| `AttributeError: 'BusinessProfile' object has no attribute 'components'` | `related_name="components"` is missing in `models.py` (lesson 5.3). |
| `IndentationError` | `class Meta:` and the `def`s must be indented 4 spaces inside their class. |

## ❓ Quiz

1. Why is `organization` not in `BusinessProfileSerializer`'s fields?
2. What does `@transaction.atomic` protect against?
3. Why does `depends_on` start with `objects.none()`?
4. Which method runs for one field, and which for all fields together?

---

**Next:** [5.5 · The business API](05-business-api.md)

<details><summary>Quiz answers</summary>

1. So a client can never choose (or fake) the organization. The view sets it from the
   logged-in user.
2. Half-finished saves: if one item fails, none are kept.
3. Safe by default: nothing is allowed until `__init__` allows exactly this business's
   components.
4. `validate_<field>` for one field; `validate` for all of them together.

</details>
