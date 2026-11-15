# 10.6 · The board, a form, demo data

**Time:** 50 minutes · **Before this:** [10.5](05-connect-the-addresses.md).

## 📖 Read

Two templates and a command.

**The operations board** (`dashboard.html`) is the home page: a table of businesses on
the left, open alerts and recent decisions on the right. It **extends** `base.html`
(lesson 4.8), so it gets the status bar and messages for free, and only fills the
`content` block.

**Add a business** (`create.html`) is a form page. It doesn't draw each field by hand: it
loops over the form and includes `accounts/_field.html` (lesson 4.8) for each one, which
draws the label, the input, the help text and any error the same way everywhere.

**`seed_kirana`** is a management command (like `rescan_companies` in lesson 8.8) that
loads demo data for class: an operating company, **Kirana Express**, with components and
three outages already run; and an idea, **Tiffin Box Co.**, with its stress test run.
Every invented number is tagged **illustrative**, and it makes no AI calls.

## ⌨️ Do

### 1. `templates/businesses/dashboard.html`

Make the folder `templates/businesses/`, then:

<!-- source: templates/businesses/dashboard.html:1-76 -->
```html
{% extends "base.html" %}
{% load warroom %}
{% block title %}Operations board · AI WarRoom{% endblock %}
{% block content %}
<div class="page">
  <header class="page-head">
    <h1>Operations board</h1>
    <span class="chip">{{ businesses|length }} on the board</span>
    <div class="spacer"></div>
    <a class="btn btn-primary" href="{% url 'business-create' %}">Add a business</a>
  </header>

  <div class="cols-main-side">
    <section class="panel ticked" aria-labelledby="p-biz">
      <div class="panel-head"><span class="panel-id">D-01</span><h2 id="p-biz">Businesses</h2></div>
      {% if businesses %}
      <div class="table-scroll"><table class="ledger">
        <thead><tr><th>Name</th><th>Mode</th><th>Last run</th><th class="num">Open alerts</th></tr></thead>
        <tbody>
        {% for row in businesses %}
          <tr>
            <td><a class="row-title" href="{% url 'business-detail' row.business.pk %}">{{ row.business.name }}</a>
              <span class="help">{{ row.business.industry }}</span></td>
            <td>{% if row.business.mode == "idea" %}<span class="tag idea">Idea</span>{% else %}<span class="tag ops">Operating</span>{% endif %}</td>
            <td>{% if row.last_run %}<a href="{% url 'run-detail' row.last_run.pk %}">{{ row.last_run.scenario.name }}</a>
              <span class="help mono">{{ row.last_run.created_at|date:"d M, H:i" }} UTC</span>{% else %}<span class="unit">No runs yet</span>{% endif %}</td>
            <td class="num">{{ row.open_alerts|default:"·" }}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table></div>
      {% else %}
      <div class="empty">
        <span class="label">Nothing on the board yet</span>
        <h2>Start with one business.</h2>
        <p>An idea you haven't launched gets the Idea Bench: price, demand, CAC and costs under seven cases. An operating company gets the Situation Board: knock out the payment gateway, warehouse or courier and compare responses.</p>
        <a class="btn btn-primary" href="{% url 'business-create' %}">Add a business</a>
      </div>
      {% endif %}
    </section>

    <div class="stack">
      <section class="panel ticked" aria-labelledby="p-alerts">
        <div class="panel-head"><span class="panel-id">D-02</span><h2 id="p-alerts">Alerts</h2><span class="aside">from site re-scans</span></div>
        {% for alert in alerts %}
          <div class="alert-row">
            <span class="sev {{ alert.severity }}" aria-hidden="true"></span>
            <div><p>{{ alert.summary }}</p>
              <span class="meta">{{ alert.get_severity_display|upper }} · {{ alert.business.name }} · {{ alert.created_at|date:"d M, H:i" }} UTC</span></div>
            <form class="inline-form" method="post" action="{% url 'alert-acknowledge' alert.pk %}">{% csrf_token %}
              <input type="hidden" name="next" value="{{ request.path }}">
              <button class="btn btn-sm" type="submit" aria-label="Acknowledge: {{ alert.summary }}">Ack</button>
            </form>
          </div>
        {% empty %}
          <p class="state">No open alerts. Alerts appear when a re-scan of a company website finds new prices, products, pages or competitors.</p>
        {% endfor %}
      </section>

      <section class="panel ticked" aria-labelledby="p-dec">
        <div class="panel-head"><span class="panel-id">D-03</span><h2 id="p-dec">Decisions</h2></div>
        {% for d in decisions %}
          <div class="alert-row">
            <span class="sev {% if d.status == 'rejected' %}critical{% elif d.status == 'proposed' %}warn{% endif %}" aria-hidden="true"></span>
            <div><p><a href="{% url 'decisions:brief' d.pk %}">{{ d.title }}</a></p>
              <span class="meta">{{ d.get_status_display|upper }} · {{ d.business.name }} · {{ d.owner|default:"unassigned" }}</span></div>
            <span></span>
          </div>
        {% empty %}
          <p class="state">No decisions recorded. Record one from any run once you've compared the responses.</p>
        {% endfor %}
      </section>
    </div>
  </div>
</div>
{% endblock %}
```

### 2. `templates/businesses/create.html`

<!-- source: templates/businesses/create.html:1-21 -->
```html
{% extends "base.html" %}
{% block title %}Add a business · AI WarRoom{% endblock %}
{% block content %}
<div class="page" style="max-width: 760px">
  <header class="page-head">
    <p class="crumbs"><a href="{% url 'home' %}">Operations board</a> /</p>
    <h1>Add a business</h1>
  </header>
  <section class="panel ticked" aria-labelledby="p-new">
    <div class="panel-head"><span class="panel-id">B-00</span><h2 id="p-new">Profile</h2></div>
    <form class="panel-body" method="post" novalidate>
      {% csrf_token %}
      {% for field in form %}{% include "accounts/_field.html" %}{% endfor %}
      <div class="btn-row">
        <button class="btn btn-primary" type="submit">Add to the board</button>
        <a class="btn-link" href="{% url 'home' %}">Cancel</a>
      </div>
    </form>
  </section>
</div>
{% endblock %}
```

### 3. The demo data command

Make `businesses/management/` and `businesses/management/commands/`, each with an empty
`__init__.py`, then create `businesses/management/commands/seed_kirana.py`.

#### Piece 1: the demo data (lines 1–89)

<!-- source: businesses/management/commands/seed_kirana.py:1-89 -->
```python
"""
Load the demo data used in class: one operating e-commerce company and one idea.

    python manage.py seed_kirana --email you@example.com
    python manage.py seed_kirana --email you@example.com --reset

The businesses go into that user's organization. If the user doesn't exist yet, it is
created with a random password that is printed ONCE in your terminal (local use only).
Every invented number is tagged "illustrative" so nobody mistakes it for real data, and
no AI call is made: seeding costs no Gemini quota.
"""

import secrets

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.access import organization_for
from accounts.models import User
from accounts.services import register_owner
from businesses.models import BusinessComponent, BusinessProfile
from businesses.services.assumptions import save_assumptions
from simulation_engine import catalog
from simulations.models import Scenario
from simulations.services.run_service import run_scenario

DEMO_NOTE = "Demo data for teaching. All figures are illustrative, not a real company."

KIRANA = {
    "name": "Kirana Express",
    "mode": "operating",
    "industry": "Online groceries",
    "website_url": "https://books.toscrape.com/",  # a public scraping sandbox, safe to scan
    "assumptions": {
        # key: (value, source)
        "daily_orders": ("2400", "illustrative"),
        "average_order_value": ("640", "illustrative"),
        "contribution_margin": ("22", "illustrative"),
        "hourly_capacity": ("180", "illustrative"),
        "primary_gateway_share": ("85", "illustrative"),
        "main_warehouse_share": ("80", "illustrative"),
        "logistics_partner_share": ("70", "illustrative"),
        "recapture_rate": ("30", "illustrative"),
        "cancel_rate_per_delay_hour": ("1.5", "illustrative"),
        "max_cancel_rate": ("35", "illustrative"),
    },
    # (key, name, kind, criticality, depends_on keys, fallback)
    "components": [
        ("razorpay", "Razorpay (primary gateway)", "payment", 5, [], "Cashfree account, not live"),
        ("storefront", "kiranaexpress.in", "storefront", 5, ["razorpay"], ""),
        ("bhiwandi", "Bhiwandi DC", "warehouse", 5, [], "Thane dark store, 20 % capacity"),
        ("delhivery", "Delhivery", "logistics", 4, ["bhiwandi"], "Shadowfax for metro pin codes"),
        ("growers", "Nashik growers", "supplier", 3, [], ""),
    ],
    "scenarios": [
        (
            "Razorpay down at evening peak",
            "payment_gateway_outage",
            {"outage_hours": "3", "start_hour": "19"},
        ),
        ("Bhiwandi flood, 6 h from 18:00", "warehouse_shutdown", {"outage_hours": "6"}),
        (
            "Delhivery pickups stop for a day",
            "logistics_failure",
            {"outage_hours": "24", "start_hour": "9", "backup_switch_hours": "4"},
        ),
    ],  # fmt: skip
}

TIFFIN = {
    "name": "Tiffin Box Co.",
    "mode": "idea",
    "industry": "Meal subscriptions",
    "website_url": "",
    "assumptions": {
        "price_per_order": ("180", "user"),
        "variable_cost_per_order": ("112", "illustrative"),
        "fixed_costs_monthly": ("260000", "user"),
        "marketing_spend_monthly": ("120000", "user"),
        "cost_per_visit": ("9", "illustrative"),
        "conversion_rate": ("2.2", "illustrative"),
        "orders_per_customer_monthly": ("9", "illustrative"),
        "monthly_retention": ("78", "illustrative"),
        "initial_investment": ("2500000", "user"),
        "expected_orders_monthly": ("6000", "user"),
    },
    "components": [],
    "scenarios": [("Pune launch, 24 months", "idea_cases", {})],
}
```

#### Piece 2: the command (lines 92–153)

<!-- source: businesses/management/commands/seed_kirana.py:92-153 -->
```python
class Command(BaseCommand):
    help = "Create the Kirana Express (operating) and Tiffin Box Co. (idea) demo businesses."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Owner account (created if missing)")
        parser.add_argument("--reset", action="store_true", help="Delete and recreate the demos")

    @transaction.atomic
    def handle(self, *args, email, reset, **options):
        user = User.objects.filter(email=email.lower()).first()
        if user is None:
            password = secrets.token_urlsafe(12)
            user = register_owner(
                email=email, password=password, full_name="Demo operator", org_name="Demo Org"
            )
            self.stdout.write(self.style.WARNING(f"Created {email} with password: {password}"))
            self.stdout.write("  (shown once; change it after logging in if you keep the account)")
        organization = organization_for(user)
        if organization is None:
            raise CommandError(f"{email} isn't part of an organization; use another email.")

        for spec in (KIRANA, TIFFIN):
            existing = BusinessProfile.objects.filter(organization=organization, name=spec["name"])
            if existing.exists():
                if not reset:
                    self.stdout.write(f"{spec['name']}: already there (use --reset to rebuild)")
                    continue
                existing.delete()
            self._create(spec, organization, user)

    def _create(self, spec, organization, user):
        business = BusinessProfile.objects.create(
            organization=organization,
            created_by=user,
            name=spec["name"],
            mode=spec["mode"],
            industry=spec["industry"],
            website_url=spec["website_url"],
            description=DEMO_NOTE,
        )
        save_assumptions(business, spec["assumptions"])

        by_key = {}
        for key, name, kind, criticality, _, fallback in spec["components"]:
            by_key[key] = BusinessComponent.objects.create(
                business=business, key=key, name=name, kind=kind,
                criticality=criticality, fallback_note=fallback,
            )  # fmt: skip
        for key, *_, depends_on, _ in spec["components"]:
            by_key[key].depends_on.set([by_key[d] for d in depends_on])

        self.stdout.write(self.style.SUCCESS(f"{business.name} ({business.mode})"))
        for name, template_key, parameters in spec["scenarios"]:
            scenario = Scenario.objects.create(
                business=business,
                name=name,
                template_key=template_key,
                parameters=catalog.validate_parameters(template_key, parameters),
                created_by=user,
            )
            run = run_scenario(scenario, user)
            self.stdout.write(f'  ran "{name}": /runs/{run.pk}/')
```

## ✅ Check

### The board

Start the server and open **http://127.0.0.1:8000/**. The operations board lists your
businesses from Parts 5–8 (Kirana Express, Books Corner...), each with its last run and a
link to it. On the right: alerts (probably none) and the decision you recorded in Part 9.

### The demo data

Stop the server (Ctrl+C) and run the command with **your own** login email:

```bash
python manage.py seed_kirana --email you@example.com
```

You already have a "Kirana Express" from lesson 6.9, so it's kept, and only the idea is
added:

```text
Kirana Express: already there (use --reset to rebuild)
Tiffin Box Co. (idea)
  ran "Pune launch, 24 months": /runs/7bb49a10-5589-4301-8abd-a54aebe028d2/
```

(Your run id will differ, and a log line like `Simulation run ... completed (7 cases)` may
appear too.) **Don't** add `--reset` now: it would delete your Kirana Express with its
runs and your Part 9 decision, and rebuild the demo one.

Start the server again: the board now shows **Tiffin Box Co.** with an "Idea" tag.

### The form

Click **Add a business**. Choose "Idea", name it "Chai Cart", industry "Food stall", and
click **Add to the board**. You land on a yellow `TemplateDoesNotExist` page for
`businesses/detail.html`: the business **was** saved (go back to the board and you'll see
it), and its page comes in the next lesson.

Try sending the form with no name: the page comes back with "This field is required."
under the name box.

## 🔍 Line by line

### `dashboard.html`

- **Line 1** · Use `base.html` as the frame.
- **Line 2** · Our filters (not used much here, but every app page loads them).
- **Line 3** · The browser tab's title.
- **Lines 4–11** · The page header: a title, "3 on the board" (`|length` counts a list),
  and the "Add a business" button.
- **Lines 13–15** · Two columns; the left one is a panel. `aria-labelledby` ties the
  panel to its heading for screen readers. `D-01` is just a panel number, like on a
  control-room screen.
- **Lines 16–31** · The businesses table. For each row: the name (a link to its page) and
  industry; an Idea/Operating tag; the last run (a link, with its time) or "No runs yet";
  the open alerts, or `·` when there are none (`|default:"·"`).
- **Lines 32–39** · No businesses? An empty state that explains what each mode gets, with
  the button again.
- **Lines 42–58** · Alerts: each with its severity mark, summary and details, and an
  **Ack** button. The hidden `next` field is the page to return to: `alert_acknowledge`
  only follows it if it's on our own site (lesson 8.9). `{% empty %}` explains where
  alerts come from.
- **Lines 60–72** · Recent decisions, each linking to its brief, coloured by status.

### `create.html`

- **Lines 1–3** · Frame and title.
- **Line 4** · A narrower page.
- **Lines 6–9** · A "breadcrumb" link back to the board, and the heading.
- **Line 11** · `novalidate` turns off the browser's own pop-up checks, so Django's
  messages (clearer, and the same on every browser) are shown instead.
- **Line 12** · `{% csrf_token %}` (lesson 4.3).
- **Line 13** · Draw every field with the shared `_field.html`.
- **Lines 14–17** · Submit, or cancel back to the board.

### `seed_kirana.py`, piece 1

- **Lines 1–11** · Docstring: how to run it, where the data goes, and two promises:
  illustrative tags, no AI calls.
- **Line 13** · `secrets`: makes passwords that can't be guessed.
- **Lines 15–16** · The command base, its error, and transactions.
- **Lines 18–25** · Everything needed to create users, businesses, assumptions,
  components, scenarios and runs, all through the same services the app uses.
- **Line 27** · The description put on each demo business.
- **Lines 29–68** · Kirana Express: name, mode, industry, a website (the practice site
  from Part 8, safe to scan), ten assumptions **each with its source**, five components
  (key, name, kind, criticality, dependencies, fallback), and three scenarios with their
  parameters.
- **Lines 70–89** · Tiffin Box Co.: an idea with ten inputs (some "user", some
  "illustrative"), no components, and one stress test.

### Piece 2

- **Lines 92–93** · The command and its help text.
- **Lines 95–97** · `--email` (required) and `--reset` (a switch: present or not).
- **Lines 99–100** · `@transaction.atomic`: all of it, or none of it. `email` and `reset`
  arrive as named arguments.
- **Line 101** · Find the user (emails are stored lowercase).
- **Lines 102–108** · No such user? Create one with a random password and print it
  **once**, in yellow, with a reminder.
- **Lines 109–111** · The user's organization, or a clear error.
- **Lines 113–120** · For each demo: if one with that name exists, skip it, or delete it
  first with `--reset`. Then create it.
- **Lines 122–132** · `_create`: the business, then its assumptions through
  `save_assumptions` (lesson 10.2), so they're checked by the catalogue too.
- **Lines 134–139** · Create each component and remember it by key.
- **Lines 140–141** · Then set dependencies (a second loop, because a component can only
  depend on one that already exists). `key, *_, depends_on, _` takes the first and the
  second-to-last items and ignores the rest.
- **Lines 143–153** · Print the business, then create and run each scenario, printing
  the run's address.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `TemplateDoesNotExist: accounts/_field.html` | It's from lesson 4.8, in `templates/accounts/`. |
| `Unknown command: 'seed_kirana'` | Both `__init__.py` files, and the folder names `management/commands`. |
| `CommandError: ... isn't part of an organization` | That email belongs to a `createsuperuser` account. Use the account you signed up with. |
| `Created you@example.com with password: ...` | You typed an email with no account, so the command made a new one. Use your real login email, or log in with the printed password. |

## ❓ Quiz

1. Why does `create.html` include `_field.html` instead of writing each input?
2. What would `--reset` do to your own Kirana Express?
3. Why are dependencies set in a second loop?

---

**Next:** [10.7 · The business page](07-the-business-page.md)

<details><summary>Quiz answers</summary>

1. So every form draws labels, help and errors the same way, from one file.
2. Delete it (with its runs and decisions) and build the demo one instead.
3. A component can only point at components that already exist; after the first loop,
   they all do.

</details>
