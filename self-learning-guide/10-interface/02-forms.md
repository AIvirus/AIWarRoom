# 10.2 · Forms

**Time:** 50 minutes · **Before this:** [10.1](01-how-the-pages-fit.md).

## 📖 Read

A Django **form** does three jobs for a page:

1. **Draws** the inputs (`<input>`, `<select>`...) with their labels and help text.
2. **Checks** what was sent back, and keeps a message for each problem.
3. Hands you **clean** values (a `Decimal`, a choice...) once everything is fine.

You met one in Part 4 (the sign-up form). A `ModelForm` builds its fields from a table's
columns; a plain `Form` lists them by hand.

The interesting one here is `AssumptionsForm`. It has **no fixed fields**: it looks at the
engine's catalogue (lesson 5.2) and adds one value field and one "source" field for every
input that applies to this business. An idea gets price and conversion; an operating
company gets daily orders and margins. Add an input to the catalogue, and the form grows
by itself.

The same rule checks a value everywhere: `catalog.parse_input`. The API (Part 5), the
engine (Part 6) and now this form all ask it, so "contribution margin 150 %" is refused
the same way wherever it's typed.

## ⌨️ Do

### 1. `businesses/services/assumptions.py`

<!-- source: businesses/services/assumptions.py:1-23 -->
```python
"""Saving assumptions from a form or a slider, validated by the engine's catalogue."""

from django.db import transaction

from businesses.models import FinancialAssumption
from simulation_engine import catalog


@transaction.atomic
def save_assumptions(business, values: dict[str, tuple[object, str]]) -> None:
    """
    values = {key: (value or None, source)}.  A blank value removes that assumption.
    Every value is checked by catalog.parse_input, the same rule the API and engine use.
    """
    for key, (raw, source) in values.items():
        if raw is None or raw == "":
            FinancialAssumption.objects.filter(business=business, key=key).delete()
            continue
        FinancialAssumption.objects.update_or_create(
            business=business,
            key=key,
            defaults={"value": catalog.parse_input(key, raw), "source": source},
        )
```

### 2. `businesses/forms.py`

#### Piece 1: the business form (lines 1–28)

<!-- source: businesses/forms.py:1-28 -->
```python
from django import forms
from django.utils.text import slugify

from simulation_engine import catalog

from .models import BusinessComponent, BusinessProfile, FinancialAssumption
from .services.snapshot import plain


class BusinessForm(forms.ModelForm):
    # "kirana.example" typed without a scheme means https:// (Django 6's default too).
    website_url = forms.URLField(
        required=False,
        assume_scheme="https",
        label="Public website (optional)",
        help_text="Used for on-demand scans of public pages. Respects robots.txt.",
    )

    class Meta:
        model = BusinessProfile
        fields = ["mode", "name", "industry", "website_url", "description"]
        labels = {"website_url": "Public website (optional)"}
        help_texts = {
            "mode": "An idea is tested with the Idea Bench; an operating company with disruptions.",
            "website_url": "Used for on-demand scans of public pages. Respects robots.txt.",
            "description": "For your own notes. It is never sent to the AI.",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
```

#### Piece 2: the assumptions form (lines 31–87)

<!-- source: businesses/forms.py:31-87 -->
```python
class AssumptionsForm(forms.Form):
    """One value + one source field per catalogue input that applies to this business."""

    def __init__(self, business, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.business = business
        existing = {a.key: a for a in business.assumptions.all()}
        self.rows = []
        for spec in catalog.INPUTS.values():
            if business.mode not in spec.modes:
                continue
            current = existing.get(spec.key)
            self.fields[spec.key] = forms.DecimalField(
                label=spec.label,
                required=False,
                max_digits=16,
                decimal_places=4,
                help_text=spec.help,
                # plain(): 2400.0000 -> "2400". normalize() alone would show "2.4E+3".
                initial=plain(current.value) if current else None,
                widget=forms.NumberInput(attrs={"step": "any", "inputmode": "decimal"}),
            )
            source_key = f"{spec.key}__source"
            self.fields[source_key] = forms.ChoiceField(
                label=f"Source of {spec.label.lower()}",
                choices=FinancialAssumption.Source.choices,
                initial=current.source if current else FinancialAssumption.Source.USER,
                required=False,
            )
            self.rows.append((spec, self[spec.key], self[source_key]))

    def clean(self):
        cleaned = super().clean()
        for spec, _, _ in self.rows:
            value = cleaned.get(spec.key)
            if value is None:
                continue
            try:
                catalog.parse_input(spec.key, value)
            except catalog.CatalogError as error:
                self.add_error(spec.key, error.errors[spec.key])
        return cleaned

    def values(self) -> dict:
        """
        Only fields that were actually submitted. A field posted blank means "remove";
        a field not posted at all means "leave it alone".
        """
        default = FinancialAssumption.Source.USER
        return {
            spec.key: (
                self.cleaned_data.get(spec.key),
                self.cleaned_data.get(f"{spec.key}__source") or default,
            )
            for spec, _, _ in self.rows
            if spec.key in self.data
        }
```

#### Piece 3: components and scenarios (lines 90–135)

<!-- source: businesses/forms.py:90-135 -->
```python
class ComponentForm(forms.ModelForm):
    """
    Adds a component. A brand-new component can't close a dependency loop (nothing
    depends on it yet); editing dependencies later goes through the API, which checks.
    """

    class Meta:
        model = BusinessComponent
        fields = ["name", "kind", "criticality", "depends_on", "fallback_note"]
        labels = {"depends_on": "Depends on", "fallback_note": "Fallback (if any)"}
        help_texts = {"criticality": "1 = nice to have, 5 = the business stops without it."}
        widgets = {"criticality": forms.NumberInput(attrs={"min": 1, "max": 5})}

    def __init__(self, business, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.business = business
        self.fields["depends_on"].queryset = business.components.all()
        self.fields["depends_on"].required = False

    def clean_criticality(self):
        value = self.cleaned_data["criticality"]
        if not 1 <= value <= 5:
            raise forms.ValidationError("Criticality runs from 1 to 5.")
        return value

    def clean(self):
        cleaned = super().clean()
        key = slugify(cleaned.get("name", ""))[:40]
        if not key:
            raise forms.ValidationError("Give the component a name.")
        if self.business.components.filter(key=key).exists():
            self.add_error("name", "This business already has a component with that name.")
        self.instance.key = key
        self.instance.business = self.business
        return cleaned


class ScenarioForm(forms.Form):
    template_key = forms.ChoiceField(label="What to test")
    name = forms.CharField(label="Name it", max_length=120)

    def __init__(self, business, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template_key"].choices = [
            (t.key, t.name) for t in catalog.TEMPLATES.values() if t.mode == business.mode
        ]
```

## ✅ Check

In `python manage.py shell`, build the assumptions form for one of your operating
businesses:

```python
from businesses.forms import AssumptionsForm
from businesses.models import BusinessProfile

shop = BusinessProfile.objects.filter(mode="operating").first()
form = AssumptionsForm(shop)
len(form.rows)
```

`10`: ten inputs apply to an operating company. Now send a bad value:

```python
bad = AssumptionsForm(shop, {"contribution_margin": "150"})
bad.is_valid()
```

`False`. Why?

```python
bad.errors["contribution_margin"]
```

```text
['must be at most 100 %']
```

The catalogue's own message. And a good one:

```python
good = AssumptionsForm(shop, {"contribution_margin": "22", "contribution_margin__source": "user"})
good.is_valid()
good.values()
```

`True`, then `{'contribution_margin': (Decimal('22'), 'user')}`: only the field that was
sent, with its source. (Nothing is saved: we never called `save_assumptions`.)

## 🔍 Line by line

### `assumptions.py`

- **Line 1** · Docstring.
- **Line 3** · `transaction`, for "all or nothing".
- **Lines 5–6** · The assumptions table and the catalogue.
- **Line 9** · `@transaction.atomic`: if anything fails half-way, **none** of the changes
  are kept. You never end up with half the values saved.
- **Line 10** · `save_assumptions(business, values)`. `values` maps each key to a pair:
  the value and its source.
- **Lines 11–14** · Docstring: blank means "remove".
- **Line 15** · For each key, unpack the pair into `raw` and `source`.
- **Lines 16–18** · Blank: delete that assumption, then `continue` to the next key.
- **Lines 19–23** · Otherwise **update or create** the row: if this business already has
  this key, change it; if not, add it. `defaults` are the fields to set. The value goes
  through `catalog.parse_input` one last time.

### Piece 1: `BusinessForm`

- **Lines 1–2** · Django forms, and `slugify` (turns "Bhiwandi DC" into `bhiwandi-dc`).
- **Line 4** · The catalogue.
- **Lines 6–7** · Our tables, and `plain` (lesson 6.8).
- **Line 10** · A form built from the `BusinessProfile` table.
- **Lines 11–17** · The website field, set by hand for one reason: `assume_scheme="https"`
  lets someone type `kirana.example` and get `https://kirana.example`.
- **Lines 19–21** · Which table and which columns appear, in this order.
- **Line 22** · A friendlier label.
- **Lines 23–27** · Help text under three fields. Note the honest one for `description`:
  it's never sent to the AI (lesson 7.8's allowlist).
- **Line 28** · A three-row text box for the description.

### Piece 2: `AssumptionsForm`

- **Line 31** · A plain form: its fields are added in `__init__`.
- **Line 32** · Docstring.
- **Lines 34–36** · Set up as usual, and remember the business.
- **Line 37** · The business's current assumptions, by key.
- **Line 38** · `rows`: what the template will loop over.
- **Lines 39–41** · For every catalogue input... skip those that don't apply to this
  mode.
- **Line 42** · Its current value, if any.
- **Lines 43–52** · A number field with the input's label and help, optional, up to 16
  digits with 4 decimals. `initial` fills in today's value (as `"2400"`, not
  `"2.4E+3"`). The widget lets phones show a number keypad (`inputmode`).
- **Lines 53–59** · A second field, `<key>__source`: a drop-down of sources, starting at
  today's source or "User input".
- **Line 60** · Remember the trio for the template: the catalogue spec, the value field,
  the source field. `self[name]` is the field ready to draw.
- **Lines 62–72** · `clean()`: after Django's own checks, ask the catalogue about each
  value given. A problem is attached to **that** field, with the catalogue's message.
- **Lines 74–87** · `values()`: the `(value, source)` pairs for `save_assumptions`, but
  **only** for fields that were actually sent (`if spec.key in self.data`). That matters:
  a page that sends only one slider's value won't wipe all the others.

### Piece 3: `ComponentForm` and `ScenarioForm`

- **Lines 90–94** · `ComponentForm`, and a docstring about dependency loops: a brand-new
  component can't be in a loop, because nothing depends on it yet. (Changing
  dependencies later goes through the API, which checks loops; lesson 5.3.)
- **Lines 96–101** · Columns, labels and help; criticality is a number box from 1 to 5.
- **Lines 103–107** · Only this business's components can be chosen as dependencies, and
  none are required.
- **Lines 109–113** · `clean_criticality`: Django calls `clean_<field>` for one field.
  `1 <= value <= 5` checks both ends at once.
- **Lines 115–124** · `clean()`: make the component's key from its name (lowercase,
  dashes, at most 40 characters), refuse an empty one or a duplicate, and fill in the key
  and business so `form.save()` has everything.
- **Lines 127–129** · `ScenarioForm`: a template choice and a name.
- **Lines 131–135** · The choices are filled in per business: only templates for its
  mode. An idea can't pick "Payment gateway outage".

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `TypeError: URLField.__init__() got an unexpected keyword argument 'assume_scheme'` | Your Django is older than 5.0. Run `pip install -r requirements.txt` again. |
| `len(form.rows)` is `0` | The business's `mode` didn't match: check line 40 compares `business.mode` with `spec.modes`. |
| `AttributeError: 'NoneType' object has no attribute 'mode'` | You have no operating business. Make one (lesson 6.9's `api()` steps). |

## ❓ Quiz

1. Why does `AssumptionsForm` have no fields written out in the class?
2. A page sends only `contribution_margin`. Does saving remove daily orders?
3. Why `@transaction.atomic` on `save_assumptions`?

---

**Next:** [10.3 · The business views](03-business-views.md)

<details><summary>Quiz answers</summary>

1. It builds them from the catalogue, so it always matches the inputs that exist.
2. No. `values()` only includes fields that were sent (line 86).
3. So a failure half-way through leaves nothing half-saved.

</details>
