# 4.7 · Sign up, log in, and the first API

**Time:** 50 minutes · **Before this:** [4.6](06-who-sees-what.md).

## 📖 Read

To let people in, we need:

| Piece | File | Job |
|---|---|---|
| A **service** | `accounts/services.py` | Creates a user, their organization and their membership, all together |
| **Forms** | `accounts/forms.py` | Describe the sign-up and login boxes, and check what people type |
| **Views** | `accounts/views.py` | Handle the sign-up and login requests |
| **URLs** | `accounts/urls.py` | Map `/accounts/login/` and friends to the views |
| An **API** | `accounts/api.py` | `/api/v1/me/` answers "who am I?" in JSON |
| **One error shape** | `config/api_errors.py` | Every API error looks the same |

### Why a separate "service"?

Views should be **thin**: read the request, call one function that does the real work,
send a response. The real work lives in **services**. That keeps the important rules in
one place, easy to test, and usable from a page, the API or a command.

### Transactions: all or nothing

Signing up writes **three** rows (user, organization, membership). If the third fails,
we must not be left with a user who has no organization. A **transaction** groups writes
so either **all** happen or **none** do.

## ⌨️ Do

Create or replace these six files.

### `accounts/services.py`

<!-- source: accounts/services.py:1-29 -->
```python
"""Account workflows. Views call these; they never create users or orgs themselves."""

from django.db import transaction
from django.utils.text import slugify

from .models import Membership, Organization, User


def unique_org_slug(name: str) -> str:
    """'Kirana Express' -> 'kirana-express', then 'kirana-express-2' if that's taken."""
    base = slugify(name)[:120] or "org"
    slug, n = base, 2
    while Organization.objects.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


@transaction.atomic
def register_owner(*, email: str, password: str, full_name: str, org_name: str) -> User:
    """
    Create a user, their organization and an owner membership as one unit.

    transaction.atomic means that if any step fails we never end up with a user who has
    no organization: either all three rows are written or none of them are.
    """
    user = User.objects.create_user(email=email, password=password, full_name=full_name)
    organization = Organization.objects.create(name=org_name, slug=unique_org_slug(org_name))
    Membership.objects.create(user=user, organization=organization, role=Membership.Role.OWNER)
    return user
```

- **Line 3** · `transaction` gives us all-or-nothing database writes.
- **Line 4** · `slugify` turns `"Kirana Express"` into `"kirana-express"`.
- **Line 9** · Make a slug that no other organization has.
- **Line 10** · Docstring with an example.
- **Line 11** · Slugify the name and keep at most 120 characters (`[:120]`, a slice). If
  the name had no usable letters (say, only emoji), slugify gives `""`, and `or "org"`
  uses `"org"` instead.
- **Line 12** · Start with the plain slug, and the number 2 ready for the first clash.
- **Line 13** · While a row with this slug already exists...
- **Line 14** · ...try `kirana-express-2`, then `-3`, and so on.
- **Line 15** · Return the first free slug.
- **Line 18** · `@transaction.atomic`: everything inside this function is one
  transaction. If any line raises an error, all its database writes are undone.
- **Line 19** · The `*` at the start means "all values after this **must** be given by
  name": `register_owner(email=..., password=...)`. That stops anyone mixing up email and
  name by position.
- **Lines 20–25** · Docstring explaining the all-or-nothing rule.
- **Line 26** · Create the user (lesson 4.5's manager hashes the password).
- **Line 27** · Create the organization with a unique slug.
- **Line 28** · Link them: this user **owns** this organization.
- **Line 29** · Return the new user.

### `accounts/forms.py`

<!-- source: accounts/forms.py:1-55 -->
```python
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
```

A Django **form** describes input boxes **and** checks what people type. If anything is
wrong, the form collects friendly error messages to show next to each box.

- **Lines 1–3** · Django's form tools; its password checker; its ready-made login form.
- **Line 8** · The sign-up form: a plain form with four fields.
- **Line 9** · A text box labelled "Your name", up to 120 characters.
- **Line 10** · An email box: Django checks it looks like an email.
- **Lines 11–15** · The organization name, with a **help text** shown under the box.
- **Lines 16–20** · The password box. `widget=forms.PasswordInput` shows dots instead of
  letters. `autocomplete: new-password` tells password managers to suggest a new strong
  password.
- **Line 22** · A method named `clean_<field>` runs automatically to check that field.
- **Line 23** · `cleaned_data` holds the values that already passed the basic checks.
  Lowercase the email.
- **Lines 24–27** · Someone already has this email? Raise `ValidationError`; Django shows
  the message under the email box.
- **Line 28** · A `clean_` method must return the (possibly tidied) value.
- **Line 30** · `clean()` checks things involving **several** fields together.
- **Line 31** · First let the parent class do its normal checks.
- **Line 32** · Get the password, if it got this far.
- **Lines 33–36** · The password rules (lesson 4.3) want a user to compare against ("too
  similar to your email"), but the user doesn't exist yet. So we make a **throwaway**
  User object, never saved, just for the check.
- **Lines 37–40** · Run Django's password checks. If they fail, attach the errors to the
  password box.
- **Line 41** · Return everything.
- **Line 44** · Our login form starts from Django's own `AuthenticationForm`.
- **Lines 47–50** · Friendlier error messages.
- **Line 52** · `__init__` runs when the form is created (lesson 1.6).
- **Line 53** · First let the parent set everything up.
- **Line 54** · Django's login form calls its box `username`; ours holds an email, so
  relabel it.
- **Line 55** · Help the browser autofill the email, and put the cursor there when the
  page opens.

### `accounts/views.py`

<!-- source: accounts/views.py:1-25 -->
```python
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import EmailLoginForm, SignUpForm
from .services import register_owner


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = register_owner(**form.cleaned_data)
        login(request, user)
        return redirect("home")
    return render(request, "accounts/signup.html", {"form": form})
```

- **Line 1** · `login(request, user)` marks someone as logged in for this browser.
- **Line 2** · Django's ready-made login and logout views.
- **Line 3** · `redirect` sends the browser to another page; `render` builds a page from
  a template.
- **Line 4** · A decorator that limits which HTTP methods a view accepts.
- **Lines 10–13** · Our login page is Django's, with three settings changed: our template,
  our email form, and "if you're already logged in, go straight to home".
- **Line 16** · Accept only GET (show the form) and POST (submit it). Anything else gets
  `405 Method Not Allowed`.
- **Line 17** · A **function view** receives the request and must return a response.
- **Lines 18–19** · Already logged in? Go home.
- **Line 20** · `SignUpForm(request.POST or None)`: on a POST, fill the form with what
  was typed; on a GET, `request.POST` is empty, so `or None` makes an empty form.
- **Line 21** · Only on a POST, and only if every check passes...
- **Line 22** · ...create everything. `**form.cleaned_data` unpacks the dictionary into
  named values (`email=...`, `password=...`), which match `register_owner`'s names
  exactly.
- **Line 23** · Log the new user in.
- **Line 24** · Go home. Sending a redirect after a successful POST means pressing
  "refresh" won't submit the form twice.
- **Line 25** · Otherwise (a GET, or invalid input), show the page with the form and its
  errors.

### `accounts/urls.py`

<!-- source: accounts/urls.py:1-13 -->
```python
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("signup/", views.signup, name="signup"),
    # Django only accepts POST for logout, so a stray link or image can't log you out.
    path("logout/", LogoutView.as_view(), name="logout"),
]
```

- **Line 6** · `app_name` gives these URLs a family name, so elsewhere we write
  `accounts:login`.
- **Line 8** · `urlpatterns` is the list Django reads.
- **Line 9** · `path("login/", ...)`: the address, the view, and a **name**.
  `.as_view()` turns a class view into something Django can call. Code refers to URLs by
  name, never by typing the address, so addresses can change safely.
- **Line 10** · A function view needs no `.as_view()`.
- **Lines 11–12** · Django's own logout view. It only accepts POST, so a sneaky link
  can't log you out.

### `accounts/api.py`

<!-- source: accounts/api.py:1-35 -->
```python
"""JSON endpoints for accounts. Thin: they read through the org-scoped querysets."""

from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .access import OrgScopedMixin, organization_for
from .models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "created_at"]
        read_only_fields = ["id", "slug", "created_at"]


class OrganizationViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Organizations the current user belongs to. Anyone else's org answers 404."""

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


@api_view(["GET"])
def me(request):
    organization = organization_for(request.user)
    return Response(
        {
            "id": request.user.id,
            "email": request.user.email,
            "full_name": request.user.full_name,
            "organization": OrganizationSerializer(organization).data if organization else None,
        }
    )
```

- **Line 3** · DRF tools: **serializers** turn database rows into JSON (and check incoming
  JSON); **viewsets** are API views that handle a whole table.
- **Lines 4–5** · `api_view` makes a function into an API view; `Response` sends JSON.
- **Line 11** · A `ModelSerializer` builds itself from a model.
- **Lines 12–15** · Which model, which fields go into the JSON, and which can't be changed
  through the API.
- **Line 18** · A ViewSet that can only **read** (list and detail). `OrgScopedMixin` comes
  **first**, so its `get_queryset` (lesson 4.6) narrows the rows. Without it, everyone
  would see every organization!
- **Line 21** · Start from all organizations; the mixin narrows them.
- **Line 22** · Use the serializer above for the JSON.
- **Line 25** · `/api/v1/me/` accepts GET only.
- **Line 27** · Look up the user's organization.
- **Lines 28–35** · Answer with a dictionary, which DRF turns into JSON. The organization
  is serialized if there is one, otherwise `None` (`null` in JSON).

### `config/api_errors.py`

<!-- source: config/api_errors.py:1-92 -->
```python
"""
One error shape for the whole API:

    {"error": {"code": "validation_error", "message": "...", "fields": {...}}}

Clients (our own JS included) check `error.code` instead of parsing English messages.
"""

import logging

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

CODES = {
    exceptions.ValidationError: "validation_error",
    exceptions.NotAuthenticated: "not_authenticated",
    exceptions.AuthenticationFailed: "not_authenticated",
    exceptions.PermissionDenied: "permission_denied",
    exceptions.NotFound: "not_found",
    exceptions.MethodNotAllowed: "method_not_allowed",
    exceptions.ParseError: "parse_error",
    exceptions.UnsupportedMediaType: "unsupported_media_type",
    exceptions.Throttled: "rate_limited",
}


class DomainError(exceptions.APIException):
    """
    A request that is well-formed but can't be carried out as asked, e.g. "this scenario
    needs a contribution margin first". Raise with a message and optional per-field hints.
    """

    status_code = 422
    default_code = "unprocessable"

    def __init__(
        self,
        message: str,
        fields: dict | None = None,
        code: str | None = None,
        status_code: int | None = None,
    ):
        super().__init__(detail=message, code=code or self.default_code)
        self.fields = fields or {}
        self.error_code = code or self.default_code
        if status_code:
            self.status_code = status_code


def _code_for(exc) -> str:
    if isinstance(exc, DomainError):
        return exc.error_code
    for exc_type, code in CODES.items():
        if isinstance(exc, exc_type):
            return code
    return "error"


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)  # DRF converts Http404 etc. for us

    if response is None:
        # Not an API error DRF knows about: a bug. Log it with the traceback, but never
        # send internals to the client.
        logger.exception("Unhandled API error in %s", context.get("view"))
        return Response(
            {
                "error": {
                    "code": "server_error",
                    "message": "Something went wrong on our side.",
                    "fields": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = "not_found" if response.status_code == 404 else _code_for(exc)
    if isinstance(exc, exceptions.ValidationError):
        detail = response.data
        fields = detail if isinstance(detail, dict) else {"non_field_errors": detail}
        message = "Some fields need attention."
    else:
        fields = getattr(exc, "fields", {})
        message = str(response.data.get("detail", "")) if isinstance(response.data, dict) else ""
        if code == "not_found":
            message = "Not found."  # same text whether it's missing or someone else's

    response.data = {"error": {"code": code, "message": message, "fields": fields}}
    return response
```

Every API error, whatever went wrong, is sent in **one shape**, so the JavaScript (and
Postman, and students) only learn one pattern.

- **Lines 1–7** · The shape, as an example.
- **Line 9** · `logging` writes messages to the terminal (or files on a real server).
- **Line 11** · DRF's error classes and status codes.
- **Line 13** · DRF's own error handler. We start from what it does, then reshape it.
- **Line 15** · A logger named after this file (`config.api_errors`).
- **Lines 17–27** · A dictionary from DRF error **classes** to short code words. For
  example, a `NotFound` error gets the code `"not_found"`.
- **Line 30** · `DomainError`: our own error for "your request is valid JSON, but we can't
  do it", such as "add a contribution margin first". It inherits from DRF's base API error.
- **Lines 31–34** · Docstring.
- **Line 36** · By default it answers **422** ("Unprocessable", meaning "I understood
  you, but can't do it").
- **Line 37** · Its default code word.
- **Lines 39–45** · It takes a message, plus optional field hints, code and status. The
  `| None = None` means "may be left out".
- **Line 46** · Pass the message to DRF's parent class.
- **Lines 47–50** · Remember the extras; replace the status only if one was given.
- **Line 53** · `_code_for` picks the code word for an error. A leading `_` in a name means
  "for use inside this file".
- **Lines 54–55** · Our own error carries its code.
- **Lines 56–58** · Otherwise look through `CODES`. `isinstance(exc, exc_type)` asks "is
  this error that kind of error (or a more specific version of it)?"
- **Line 59** · Unknown kinds get `"error"`.
- **Line 62** · DRF calls this function (lesson 4.3, line 150 of `base.py`) whenever an
  API view raises an error. `exc` is the error; `context` says which view.
- **Line 63** · Let DRF build its normal response first.
- **Line 65** · `None` means DRF didn't recognise it: a real bug in our code.
- **Lines 66–68** · Write the full details to the log for developers...
- **Lines 69–78** · ...but send the user only a calm, generic message. **Never** show
  code details to the public: they help attackers.
- **Line 80** · Every 404 gets the code `not_found`.
- **Lines 81–84** · Validation errors (bad input): put DRF's per-field messages under
  `fields`. If they came as a list instead of a dictionary, wrap them.
- **Lines 85–89** · Other errors:
  - **86** Use the error's own `fields` if it has some (our `DomainError` does). `getattr`
    with a default avoids crashing if it doesn't.
  - **87** Use DRF's message.
  - **88–89** For 404s, always say just "Not found.", the same text whether the record is
    missing **or** belongs to someone else (lesson 4.6).
- **Lines 91–92** · Swap in our shape and return.

## ✅ Check

Nothing to see in the browser yet: the pages need templates and the project's URL map,
which come in the next lesson.

## ❓ Quiz

1. Why does `signup` call `register_owner` instead of creating the rows itself?
2. What would go wrong without `@transaction.atomic`?
3. Why does `OrgScopedMixin` come first in `OrganizationViewSet`?

---

**Next:** [4.8 · Pages](08-pages.md)

<details><summary>Quiz answers</summary>

1. Views stay thin; the rule "user + org + owner membership, together" lives in one
   testable place that the page, API and commands can all share.
2. If creating the membership failed, you could be left with a user and organization that
   aren't linked: a user who can't see anything.
3. So its `get_queryset` runs and narrows rows to the user's organization.

</details>
