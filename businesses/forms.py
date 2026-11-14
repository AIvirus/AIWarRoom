from django import forms
from django.utils.text import slugify

from simulation_engine import catalog

from .models import BusinessComponent, BusinessProfile, FinancialAssumption


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
                initial=current.value.normalize() if current else None,
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
