from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import User


class SignUpForm(forms.Form):
    full_name = forms.CharField(label="Your name", max_length=120)
    email = forms.EmailField(label="Work email")
    org_name = forms.CharField(
        label="Organization",
        max_length=120,
        help_text="The company or founding team. You can rename it later.",
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="At least 8 characters, not only numbers, not a common password.",
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. Log in instead."
            )
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        if password:
            # Run Django's validators against a throwaway user so "too similar to your
            # email" checks work before the real user exists.
            candidate = User(email=cleaned.get("email", ""), full_name=cleaned.get("full_name", ""))
            try:
                password_validation.validate_password(password, candidate)
            except forms.ValidationError as error:
                self.add_error("password", error)
        return cleaned


class EmailLoginForm(AuthenticationForm):
    """Django's login form, relabelled: our USERNAME_FIELD is the email address."""

    error_messages = {
        "invalid_login": "That email and password don't match an account.",
        "inactive": "This account has been deactivated.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email"
        self.fields["username"].widget.attrs.update({"autocomplete": "email", "autofocus": True})
