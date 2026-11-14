from django import forms

from accounts.models import User

from .models import Decision


class DecisionForm(forms.ModelForm):
    """Record a decision straight from a run page. It always starts as 'proposed'."""

    class Meta:
        model = Decision
        fields = ["title", "chosen_strategy", "owner", "rationale"]
        labels = {"rationale": "Why"}
        widgets = {
            "rationale": forms.Textarea(
                attrs={"rows": 3, "placeholder": "What you chose, what it costs, what you accept."}
            ),
        }

    def __init__(self, *args, run, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.run = run
        cases = [(r.case_key, r.label) for r in run.results.all()]
        self.fields["chosen_strategy"] = forms.ChoiceField(
            label="Chosen response", choices=[("", "Not chosen yet"), *cases], required=False
        )
        self.fields["owner"].queryset = User.objects.filter(
            memberships__organization=run.business.organization
        )
        self.fields["owner"].required = False
        self.fields["owner"].empty_label = "Unassigned"
        self.fields["title"].widget.attrs["placeholder"] = "e.g. Contract a backup payment gateway"

    def save(self, commit=True):
        decision = super().save(commit=False)
        decision.business = self.run.business
        decision.run = self.run
        if commit:
            decision.save()
        return decision
