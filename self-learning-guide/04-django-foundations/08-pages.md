# 4.8 · Pages

**Time:** 50 minutes · **Before this:** [4.7](07-signup-login-api.md).

## 📖 Read

A **template** is an HTML file with gaps that Django fills in. The template language
has two kinds of markers:

| Marker | Meaning | Example |
|---|---|---|
| `{{ ... }}` | Print a value | `{{ user }}` → `Asha Rao` |
| `{% ... %}` | Do something: if, for, include another file, and so on | `{% if user.is_authenticated %}` |
| `{# ... #}` | A comment (never sent to the browser) | `{# note #}` |

**Template inheritance** stops repetition. `base.html` holds what every page shares (the
status bar, fonts and CSS) and leaves **blocks** for other pages to fill:

```text
base.html:   <title>{% block title %}AI WarRoom{% endblock %}</title> ... {% block content %}{% endblock %}
login.html:  {% extends "base.html" %}  {% block content %} the login form {% endblock %}
```

Django also **escapes** every `{{ value }}` automatically: if someone names their
organization `<script>...`, it's shown as text, never run as code. That blocks an attack
called **XSS** (cross-site scripting).

## ⌨️ Do

Create a `templates` folder in `my-warroom`, and `templates/accounts` inside it.

### `templates/base.html` (shared by every page)

<!-- source: templates/base.html:1-55 -->
```html
{% load static %}<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}AI WarRoom{% endblock %}</title>
  {# Fonts are self-hosted: the app works in a classroom with no internet. #}
  <link rel="stylesheet" href="{% static 'fonts/fonts.css' %}">
  <link rel="stylesheet" href="{% static 'css/tokens.css' %}">
  <link rel="stylesheet" href="{% static 'css/base.css' %}">
  <link rel="stylesheet" href="{% static 'css/app.css' %}">
  {% block head %}{% endblock %}
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="statusbar" role="banner">
    <a class="brand" href="{% url 'home' %}">AI WarRoom</a>
    {% if user.is_authenticated %}
      <div class="cell"><span class="label">Org</span><span>{{ current_org.name|default:"none" }}</span></div>
      {% block status_extra %}{% endblock %}
      <div class="spacer"></div>
      <div class="cell hide-sm"><span class="label">Operator</span><span>{{ user }}</span></div>
      <div class="cell hide-sm"><span class="label">UTC</span><span class="mono" data-utc-clock>{% now "H:i" %}</span></div>
      <form method="post" action="{% url 'accounts:logout' %}">{% csrf_token %}
        <button class="btn-link" type="submit">Log out</button>
      </form>
    {% else %}
      <div class="spacer"></div>
      <div class="cell hide-sm"><span class="label">UTC</span><span class="mono" data-utc-clock>{% now "H:i" %}</span></div>
    {% endif %}
  </header>

  {% if messages %}
    <div class="flash" role="status">
      {% for message in messages %}<p class="{{ message.tags }}">{{ message }}</p>{% endfor %}
    </div>
  {% endif %}

  <main id="main">{% block content %}{% endblock %}</main>

  <script>
    // Keep the status-bar clock honest without a library.
    (function () {
      const cells = document.querySelectorAll("[data-utc-clock]");
      const tick = () => {
        const hhmm = new Date().toISOString().slice(11, 16);
        cells.forEach((cell) => { cell.textContent = hhmm; });
      };
      tick();
      setInterval(tick, 30000);
    })();
  </script>
  {% block scripts %}{% endblock %}
</body>
</html>
```

- **Line 1** · `{% load static %}` enables the `{% static %}` tag. Then the usual
  `<!doctype html>` (lesson 2.2).
- **Line 5** · The **viewport** tag makes phones show the page at their real width
  instead of a tiny zoomed-out desktop page.
- **Line 6** · The title is a **block** with a default; each page can replace it.
- **Line 7** · A template comment.
- **Lines 8–11** · Load four CSS files. `{% static 'css/base.css' %}` becomes the right
  address (`/static/css/base.css`).
- **Line 12** · An empty block where a page can add extra things to `<head>` (the 3D page
  uses it in Part 10).
- **Line 15** · A **skip link**: invisible until a keyboard user presses Tab, then lets
  them jump past the status bar to the content. Good for accessibility.
- **Line 16** · The status bar. `role="banner"` tells screen readers what it is.
- **Line 17** · The logo links home. `{% url 'home' %}` looks the address up **by name**.
- **Line 18** · Only if someone is logged in...
- **Line 19** · ...show the organization's name (from our context processor, lesson
  4.6). `|default:"none"` is a **filter**: show "none" if the value is empty.
- **Line 20** · A block other pages may fill with extra status-bar items.
- **Line 21** · An empty element that pushes the following items to the right edge (the
  CSS does this).
- **Line 22** · The logged-in user, shown with `__str__` from lesson 4.5. `hide-sm`
  hides it on small phone screens.
- **Line 23** · The time in UTC. `{% now "H:i" %}` prints the current hour and minute;
  the script below keeps it updated.
- **Lines 24–26** · Logout is a tiny **form** that POSTs (lesson 4.7). `{% csrf_token %}`
  adds the hidden CSRF token (lesson 4.3) that proves the request came from our own page.
- **Lines 27–30** · Logged out: just the clock.
- **Lines 33–37** · One-time **messages** ("Assumptions saved."), if there are any.
  `role="status"` makes screen readers announce them.
- **Line 39** · The main area. Each page fills the `content` block. `id="main"` is where
  the skip link jumps to.
- **Lines 41–52** · A small script that updates the clock:
  - **43** `(function () { ... })();` creates a function and runs it straight away, so
    its variables don't leak into the rest of the page.
  - **44** Find every element marked `data-utc-clock`.
  - **45–48** A function that writes the current UTC time. `toISOString()` gives
    `"2026-11-15T11:21:54.000Z"`; `.slice(11, 16)` cuts out `"11:21"`.
  - **49** Run it now...
  - **50** ...and every 30,000 milliseconds (30 seconds).
- **Line 53** · A block for page-specific scripts.

### The account templates

`templates/accounts/_field.html`: one form field, with its label, help and errors.
A leading `_` in a template name means "a piece used inside other templates":

<!-- source: templates/accounts/_field.html:1-7 -->
```html
{# Renders one form field with label, help text and errors wired up for screen readers. #}
<div class="field{% if field.errors %} has-error{% endif %}">
  <label for="{{ field.id_for_label }}">{{ field.label }}</label>
  {{ field }}
  {% if field.help_text %}<span class="help" id="{{ field.id_for_label }}-help">{{ field.help_text }}</span>{% endif %}
  {% for error in field.errors %}<span class="error" role="alert">{{ error }}</span>{% endfor %}
</div>
```

- **Line 2** · A box for one field. If it has errors, add the CSS class `has-error`
  (red border).
- **Line 3** · The label, linked to the input by its id (lesson 2.2).
- **Line 4** · `{{ field }}` prints the input box itself; Django writes the HTML.
- **Line 5** · The help text, if any.
- **Line 6** · Each error message. `role="alert"` makes screen readers read it out.

`templates/accounts/_brief.html`: the left-hand column on the login and sign-up pages:

<!-- source: templates/accounts/_brief.html:1-11 -->
```html
{# Shared left-hand column of the login and sign-up screens. #}
<section class="auth-brief" aria-labelledby="brief-title">
  <span class="label">Decision rehearsal for operators and founders</span>
  <h1 id="brief-title">Test the business before reality does.</h1>
  <ol class="log">
    <li><span class="mono">IDEA</span><span>Stress-test pricing, demand, CAC and costs across best, expected and worst cases, and see which assumption moves the outcome most.</span></li>
    <li><span class="mono">OPS</span><span>Knock out the payment gateway, the warehouse or the courier, and compare waiting it out against switching over or queueing the backlog.</span></li>
    <li><span class="mono">BRIEF</span><span>Record who decided what, on which numbers, and print the brief.</span></li>
  </ol>
  <p class="disclaimer">Every figure comes from your own inputs and a deterministic model you can inspect. AI analysis is labelled as such. Nothing here predicts the market or guarantees an outcome.</p>
</section>
```

- **Line 2** · A `<section>` labelled by its heading (`aria-labelledby`), for screen
  readers.
- **Lines 3–4** · A small label and the big headline.
- **Lines 5–9** · An ordered list (`<ol>`) of the three things the app does.
- **Line 10** · The honest disclaimer: the app doesn't predict the future.

`templates/accounts/login.html`:

<!-- source: templates/accounts/login.html:1-23 -->
```html
{% extends "base.html" %}
{% block title %}Log in · AI WarRoom{% endblock %}
{% block content %}
<div class="auth">
  {% include "accounts/_brief.html" %}
  <section class="panel ticked" aria-labelledby="login-title">
    <div class="panel-head"><span class="panel-id">A-01</span><h1 id="login-title">Operator log in</h1></div>
    <div class="panel-body">
      {% if form.non_field_errors %}
        <div class="notice" role="alert">{% for e in form.non_field_errors %}{{ e }}{% endfor %}</div>
      {% endif %}
      <form method="post" novalidate>
        {% csrf_token %}
        {% include "accounts/_field.html" with field=form.username %}
        {% include "accounts/_field.html" with field=form.password %}
        <input type="hidden" name="next" value="{{ next }}">
        <button class="btn btn-primary" type="submit">Log in</button>
      </form>
      <p class="auth-switch">New here? <a href="{% url 'accounts:signup' %}">Set up an organization</a>.</p>
    </div>
  </section>
</div>
{% endblock %}
```

- **Line 1** · Start from `base.html`.
- **Line 2** · Replace the title block.
- **Lines 3–23** · Fill the content block.
- **Line 5** · `{% include %}` drops another template in here: the brief column.
- **Lines 6–7** · A panel with an ID (`A-01`) and a title, in the app's control-room style.
- **Lines 9–11** · Errors not tied to one box, like "That email and password don't match"
  (lesson 4.7).
- **Line 12** · The form POSTs to the same address. `novalidate` turns off the browser's
  own pop-up checks, so Django's clearer messages are shown instead.
- **Line 13** · The CSRF token. **Every** POST form needs it.
- **Lines 14–15** · Include `_field.html` twice, once per field. `with field=...` sets
  the `field` variable inside it.
- **Line 16** · A hidden value: after logging in, go back to the page you originally
  wanted (`next`).
- **Line 17** · The submit button.
- **Line 19** · A link to sign-up, found by its URL name.

`templates/accounts/signup.html` works the same way, with four fields:

<!-- source: templates/accounts/signup.html:1-21 -->
```html
{% extends "base.html" %}
{% block title %}Set up an organization · AI WarRoom{% endblock %}
{% block content %}
<div class="auth">
  {% include "accounts/_brief.html" %}
  <section class="panel ticked" aria-labelledby="signup-title">
    <div class="panel-head"><span class="panel-id">A-02</span><h1 id="signup-title">Set up an organization</h1></div>
    <div class="panel-body">
      <form method="post" novalidate>
        {% csrf_token %}
        {% include "accounts/_field.html" with field=form.full_name %}
        {% include "accounts/_field.html" with field=form.email %}
        {% include "accounts/_field.html" with field=form.org_name %}
        {% include "accounts/_field.html" with field=form.password %}
        <button class="btn btn-primary" type="submit">Create organization</button>
      </form>
      <p class="auth-switch">Already have an account? <a href="{% url 'accounts:login' %}">Log in</a>.</p>
    </div>
  </section>
</div>
{% endblock %}
```

Lines 11–14 include one field each; everything else matches `login.html`.

### A temporary home page: `templates/home.html`

<!-- source: self-learning-guide/04-django-foundations/for-now/templates/home.html:1-14 -->
```html
{% extends "base.html" %}
{% block title %}Operations · {{ current_org.name }} · AI WarRoom{% endblock %}
{% block content %}
<div class="page">
  <section class="panel ticked" aria-labelledby="ops-title">
    <div class="panel-head"><span class="panel-id">D-01</span><h1 id="ops-title">Operations board</h1></div>
    <div class="empty">
      <span class="label">No businesses on the board</span>
      <h2>{{ current_org.name }} has nothing to simulate yet.</h2>
      <p>You are logged in, and your organization exists. Businesses arrive in Part 5.</p>
    </div>
  </section>
</div>
{% endblock %}
```

A simple page showing your organization's name (line 9). Part 10 replaces it with the real
operations board.

### `config/views.py`: a health check

<!-- source: config/views.py:1-18 -->
```python
from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """
    Liveness + database check. Useful right after setting DATABASE_URL: if Neon is
    unreachable this answers 503 with the reason instead of a stack trace.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok", "database": connection.vendor})
    except Exception as error:  # noqa: BLE001  - we report any DB failure the same way
        return JsonResponse(
            {"status": "error", "database": connection.vendor, "detail": type(error).__name__},
            status=503,
        )
```

- **Line 1** · `connection` is Django's connection to the database.
- **Line 2** · `JsonResponse` sends a dictionary back as JSON.
- **Line 5** · A view to answer "is the site alive, and can it reach the database?".
  Hosting companies call addresses like this to check the site is up.
- **Lines 10–12** · Try the smallest possible SQL, `SELECT 1`.
- **Line 13** · It worked: answer `ok`, and which database (`sqlite` or `postgresql`).
- **Lines 14–18** · Any failure: answer **503** ("service unavailable") with only the
  error's **type** name, never details. `# noqa: BLE001` tells the linter that catching
  every kind of error is deliberate here.

### `config/urls.py`: the project's URL map (for now)

Replace the file Django generated with:

<!-- source: self-learning-guide/04-django-foundations/for-now/config/urls.py:1-27 -->
```python
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from accounts import api as accounts_api

from . import views

# One router for the whole JSON API; each app's ViewSets are registered here.
router = DefaultRouter()
router.register("organizations", accounts_api.OrganizationViewSet, basename="organization")

api_v1 = [
    path("me/", accounts_api.me, name="me"),
    path("", include(router.urls)),
]

urlpatterns = [
    # A temporary home page. Part 10 replaces it with the real operations board.
    path("", login_required(TemplateView.as_view(template_name="home.html")), name="home"),
    path("accounts/", include("accounts.urls")),
    path("api/v1/", include((api_v1, "api"), namespace="api")),
    path("admin/", admin.site.urls),
    path("healthz/", views.healthz, name="healthz"),
]
```

- **Line 2** · `login_required` wraps a view so logged-out visitors go to the login page.
- **Line 3** · `include` plugs in another URL list.
- **Line 4** · `TemplateView` is a ready-made view that just shows one template.
- **Line 5** · A DRF **router** creates the URLs for a ViewSet automatically.
- **Line 7** · Our API module, imported under a short name.
- **Line 9** · Our `views.py` from this same folder.
- **Lines 12–13** · Make a router and register the organizations ViewSet. That creates
  `organizations/` (the list) and `organizations/<id>/` (one), named
  `organization-list` and `organization-detail`.
- **Lines 15–18** · The API's URL list: `me/`, plus everything the router made.
- **Line 22** · The home page: `TemplateView` showing `home.html`, wrapped in
  `login_required`.
- **Line 23** · Everything starting `accounts/` is handled by `accounts/urls.py` (4.7).
- **Line 24** · Everything starting `api/v1/` uses `api_v1`, with the family name `api`,
  so code writes `api:me`. `v1` means version 1, so a future version 2 could live beside it.
- **Line 25** · The admin site.
- **Line 26** · The health check.

## ✅ Check

```bash
python manage.py runserver
```

Then in the browser:

1. **http://127.0.0.1:8000/healthz/** → `{"status": "ok", "database": "postgresql"}` (or
   `"sqlite"` if you're offline).
2. **http://127.0.0.1:8000/** → you're sent to the login page, because you're not
   logged in.
3. Click **Set up an organization**. Try the password `12345678` first: you should see
   "This password is too common" and "This password is entirely numeric". Then use a
   strong password.
4. You land on the home page: "*Your Org* has nothing to simulate yet."
5. **http://127.0.0.1:8000/api/v1/me/** → your user and organization as JSON, in the
   browsable API.
6. Click **Log out** in the status bar.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `TemplateDoesNotExist: accounts/login.html` | The file must be at `my-warroom/templates/accounts/login.html`. |
| `NoReverseMatch: 'accounts' is not a registered namespace` | `app_name = "accounts"` is missing from `accounts/urls.py`, or line 23 is missing. |
| The page has no colours | The `static` folder wasn't copied into `my-warroom` (lesson 4.2, Step 6). |
| `CSRF verification failed` | A form is missing `{% csrf_token %}`. |

## ❓ Quiz

1. What's the difference between `{{ }}` and `{% %}`?
2. Why is logout a form with a button, not a plain link?
3. What would someone see at `/healthz/` if Neon was down?

---

**Next:** [4.9 · Tests and your first commit](09-tests-and-commit.md)

<details><summary>Quiz answers</summary>

1. `{{ }}` prints a value; `{% %}` does something (if, for, include, url...).
2. Logout only accepts POST, so another site can't log you out with a hidden link or
   image.
3. `{"status": "error", "database": "postgresql", "detail": "OperationalError"}` with
   status 503.

</details>
