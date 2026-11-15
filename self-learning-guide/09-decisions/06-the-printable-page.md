# 9.6 · The printable page

**Time:** 60 minutes · **Before this:** [9.5](05-numbers-the-indian-way.md).

## 📖 Read

The brief page is built to be **printed** (or saved as a PDF from the print window).
That's why it doesn't use `base.html` from lesson 4.8: no menu, no sidebar. It has its own
small stylesheet, `static/css/brief.css`, which you already copied with the `static`
folder in lesson 4.2. That stylesheet hides the toolbar when printing, so the paper shows
only the brief.

At the top of the page, a toolbar shows one button per **allowed** next status ("Mark
approved", "Mark rejected"...). Each button is a tiny form that POSTs to
`/decisions/<id>/status/`. The view checks the move with `workflow.check_transition` (the
same check the API uses), records it, and sends the browser back to the brief with a
message. This pattern, **post, then redirect back**, means pressing Refresh never sends
the form twice.

### For now: the "Back" link

In the finished app, "← Back" returns to the run's page or the business's page. Those
pages come in Part 10, so for now it goes to the home page. The only difference is line
13 of the template. Part 10 also adds a third view here: recording a decision straight from
a run's page.

## ⌨️ Do

### 1. `decisions/views.py` (for now)

From [`for-now/decisions/views.py`](for-now/decisions/views.py):

<!-- source: self-learning-guide/09-decisions/for-now/decisions/views.py:1-50 -->
```python
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import DetailView

from accounts.access import OrgPageMixin

from .models import Decision
from .services import workflow
from .services.brief import build_brief


class DecisionBriefView(OrgPageMixin, DetailView):
    """The printable brief. Same data as GET /api/v1/decisions/<id>/report/."""

    model = Decision
    template_name = "decisions/brief.html"
    context_object_name = "decision"

    def get_queryset(self):
        return super().get_queryset().select_related("business", "run__scenario", "owner")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["brief"] = build_brief(self.object)
        context["next_statuses"] = [
            (s, Decision.Status(s).label) for s in workflow.allowed_next(self.object.status)
        ]
        return context


@login_required
@require_POST
def decision_status(request, pk):
    decision = get_object_or_404(Decision.objects.for_user(request.user), pk=pk)
    old, new = decision.status, request.POST.get("status", "")
    if new not in Decision.Status.values:
        messages.error(request, "Unknown status.")
        return redirect("decisions:brief", pk=pk)
    try:
        workflow.check_transition(old, new)
    except workflow.InvalidTransition as error:
        messages.error(request, str(error))
        return redirect("decisions:brief", pk=pk)
    decision.status = new
    decision.save(update_fields=["status", "updated_at"])
    workflow.record_status_change(decision, old, request.user, request.POST.get("note", ""))
    messages.success(request, f"Marked {decision.get_status_display().lower()}.")
    return redirect("decisions:brief", pk=pk)
```

### 2. `decisions/urls.py` (for now)

<!-- source: self-learning-guide/09-decisions/for-now/decisions/urls.py:1-10 -->
```python
from django.urls import path

from . import views

app_name = "decisions"

urlpatterns = [
    path("<uuid:pk>/brief/", views.DecisionBriefView.as_view(), name="brief"),
    path("<uuid:pk>/status/", views.decision_status, name="status"),
]
```

### 3. `templates/decisions/brief.html` (for now)

Make the folder `templates/decisions/`, then create `brief.html` from
[`for-now/templates/decisions/brief.html`](for-now/templates/decisions/brief.html). It's
long, but it's eight sections that each follow the same pattern: a heading, then "if
there's data, show it; otherwise say plainly that there isn't".

<!-- source: self-learning-guide/09-decisions/for-now/templates/decisions/brief.html:1-184 -->
```html
{% load static warroom %}<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Brief: {{ brief.decision.title }} · AI WarRoom</title>
  <link rel="stylesheet" href="{% static 'fonts/fonts.css' %}">
  <link rel="stylesheet" href="{% static 'css/brief.css' %}">
</head>
<body>
{% with d=brief.decision run=brief.run out=brief.outcomes %}
  <nav class="toolbar" aria-label="Brief actions">
    <a href="{% url 'home' %}">← Back</a>
    {% if messages %}<span role="status">{% for m in messages %}{{ m }} {% endfor %}</span>{% endif %}
    <span class="toolbar-actions">
      {% for value, label in next_statuses %}
        <form method="post" action="{% url 'decisions:status' decision.pk %}">{% csrf_token %}
          <input type="hidden" name="status" value="{{ value }}">
          <button type="submit" class="{% if value == 'rejected' %}quiet{% endif %}">Mark {{ label|lower }}</button>
        </form>
      {% endfor %}
      <button type="button" onclick="window.print()">Print or save as PDF</button>
    </span>
  </nav>

  <article class="sheet" aria-labelledby="brief-title">
    <header class="masthead">
      <span>AI WarRoom · Decision brief</span>
      <span class="mono">{{ brief.business.name }} · generated {{ brief.generated_at|when }}</span>
    </header>

    <h1 class="title" id="brief-title">{{ d.title }}</h1>
    <p class="subtitle">
      {% if run %}Based on “{{ run.scenario }}” ({{ run.template }}), run {{ run.created_at|when }}.
      {% else %}Not linked to a simulation run.{% endif %}
    </p>

    <dl class="facts">
      <div><dt>Status</dt><dd class="status-{{ d.status }}">{{ d.status_label }}</dd></div>
      <div><dt>Owner</dt><dd>{{ d.owner|default:"Unassigned" }}</dd></div>
      <div><dt>Chosen response</dt><dd>{{ d.chosen_label|default:d.chosen_strategy|default:"Not chosen yet" }}</dd></div>
      <div><dt>Signed off</dt><dd>{% if d.decided_by %}{{ d.decided_by }}, {{ d.decided_at|when }}{% else %}Not yet{% endif %}</dd></div>
      <div><dt>Business</dt><dd>{{ brief.business.name }} <span class="meta-line">({{ brief.business.mode }})</span></dd></div>
      <div><dt>Recorded</dt><dd>{{ d.created_at|when }}</dd></div>
    </dl>

    <section aria-labelledby="s1">
      <h2 id="s1"><span class="n">01</span>Decision and rationale</h2>
      {% if d.rationale %}<p class="rationale">{{ d.rationale|linebreaksbr }}</p>
      {% else %}<p class="empty">No rationale recorded. A brief without a reason is hard to defend later; add one before sign-off.</p>{% endif %}
    </section>

    <section aria-labelledby="s2">
      <h2 id="s2"><span class="n">02</span>What was tested</h2>
      {% if run %}
        <div class="table-wrap"><table>
          <thead><tr><th>Parameter</th><th class="num">Value</th></tr></thead>
          <tbody>
          {% for p in run.parameters %}
            <tr><td>{{ p.label }}</td><td class="num">{{ p.value|figure:p.unit }}</td></tr>
          {% endfor %}
          </tbody>
        </table></div>
        <p class="meta-line">Run <span class="mono">{{ run.id }}</span> · engine <span class="mono">{{ run.engine_version }}</span> · inputs fingerprint <span class="mono">{{ run.input_hash|slice:":12" }}</span></p>
      {% else %}
        <p class="empty">This decision isn't linked to a simulation run, so there are no modelled outcomes. Link a run to show the numbers it was based on.</p>
      {% endif %}
    </section>

    <section aria-labelledby="s3">
      <h2 id="s3"><span class="n">03</span>Assumptions</h2>
      {% if brief.assumptions.rows %}
        <p class="meta-line">
          {% if brief.assumptions.frozen %}As frozen when the run was made; later edits to the business don't change them.
          {% else %}Current values: no run is linked, so these may have changed since the decision.{% endif %}
          Tags: USR user input · ILL illustrative · SITE from company site · WHAT-IF slider value.
        </p>
        <div class="table-wrap"><table>
          <thead><tr><th>Assumption</th><th class="num">Value</th><th>Source</th></tr></thead>
          <tbody>
          {% for a in brief.assumptions.rows %}
            <tr><td>{{ a.label }}</td><td class="num">{{ a.value|figure:a.unit }}</td><td><span class="tag {{ a.source|source_tag }}">{{ a.source|source_tag }}</span></td></tr>
          {% endfor %}
          </tbody>
        </table></div>
      {% else %}<p class="empty">No assumptions recorded.</p>{% endif %}
    </section>

    <section aria-labelledby="s4">
      <h2 id="s4"><span class="n">04</span>Modelled outcomes</h2>
      {% if out %}
        <div class="table-wrap"><table>
          <thead><tr>
            <th scope="col">Measure</th>
            {% for c in out.cases %}<th scope="col" class="num{% if c.key == out.chosen %} chosen{% endif %}">{% if c.key == out.chosen %}<span class="pick">Chosen</span>{% endif %}{{ c.label }}</th>{% endfor %}
          </tr></thead>
          <tbody>
          {% for row in out.rows %}
            <tr><th scope="row">{{ row.label }}</th>
              {% for cell in row.cells %}<td class="num{% if cell.case == out.chosen %} chosen{% endif %}">{{ cell.value|figure:row.unit }}</td>{% endfor %}
            </tr>
          {% endfor %}
          </tbody>
        </table></div>
        {% if run.comparison %}
          <p class="meta-line">Engine comparison (facts, not a recommendation): lowest total impact <span class="mono">{{ run.comparison.lowest_total_impact|humanize_key }}</span> · lowest response cost <span class="mono">{{ run.comparison.lowest_response_cost|humanize_key }}</span> · fastest recovery <span class="mono">{{ run.comparison.fastest_recovery|default:"n/a"|humanize_key }}</span></p>
        {% endif %}
        {% if run.case_definitions %}
          <p class="meta-line">Case definitions:
          {% for key, shocks in run.case_definitions.items %}{% if shocks %}<span class="mono">{{ key }}</span>: {{ shocks|join:", " }}{% if not forloop.last %} · {% endif %}{% endif %}{% endfor %}</p>
        {% endif %}
        {% if brief.warnings %}
          <p class="meta-line"><strong>Engine notes:</strong> {{ brief.warnings|join:" " }}</p>
        {% endif %}
      {% else %}<p class="empty">No modelled outcomes for this decision.</p>{% endif %}
    </section>

    <section aria-labelledby="s5">
      <h2 id="s5"><span class="n">05</span>Analyst reading</h2>
      {% with ai=brief.ai_explanation %}
      {% if ai %}
        <div class="ai">
          <span class="ai-label">AI analysis</span>
          <p class="meta-line">{{ ai.label }} {{ ai.model }} · prompt {{ ai.prompt_version }} · {{ ai.created_at|when }}</p>
          <h3>{{ ai.headline }}</h3>
          <p>{{ ai.what_happened }}</p>
          {% if ai.trade_offs %}<h3>Trade-offs</h3><ul>{% for t in ai.trade_offs %}<li>{{ t }}</li>{% endfor %}</ul>{% endif %}
          {% if ai.risks %}<h3>Risks</h3><ul>{% for r in ai.risks %}<li>{{ r }}</li>{% endfor %}</ul>{% endif %}
          {% if ai.recommendations %}<h3>Suggestions</h3><ul>{% for r in ai.recommendations %}<li>{{ r.action }} <span class="meta-line">({{ r.confidence }} confidence) {{ r.rationale }}</span></li>{% endfor %}</ul>{% endif %}
          {% if ai.assumptions_to_check %}<h3>Check these assumptions</h3><ul>{% for a in ai.assumptions_to_check %}<li>{{ a }}</li>{% endfor %}</ul>{% endif %}
          {% if ai.flagged_numbers %}
            <div class="flags" role="note"><strong>{{ ai.flagged_numbers|length }} number(s) in this text are not from the simulation:</strong>
              {% for f in ai.flagged_numbers %}<span class="mono">{{ f.literal }}</span>{% if not forloop.last %}, {% endif %}{% endfor %}. Treat them as unverified.</div>
          {% endif %}
        </div>
      {% else %}<p class="empty">No AI reading of this run. It's optional: the outcomes above stand on their own.</p>{% endif %}
      {% endwith %}
    </section>

    <section aria-labelledby="s6">
      <h2 id="s6"><span class="n">06</span>Expert committee</h2>
      {% with c=brief.committee %}
      {% if c %}
        <p class="meta-line"><span class="ai-label">AI analysis</span> Four advisory desks, one review, {{ c.created_at|when }}. Desks argue from their own mandates and may disagree.</p>
        <div class="desks">
        {% for a in c.advisors %}
          <div class="desk">
            <span class="meta-line">{{ a.desk_name }}</span> <span class="verdict {{ a.verdict }}">{{ a.verdict|humanize_key }}</span>
            <h3>{{ a.headline }}</h3>
            <ul>{% for k in a.key_concerns %}<li>{{ k }}</li>{% endfor %}{% for r in a.recommended_actions %}<li><em>Do:</em> {{ r }}</li>{% endfor %}</ul>
          </div>
        {% endfor %}
        </div>
        {% if c.points_of_disagreement %}
          <div class="disagree"><strong>Where the desks disagree:</strong> {{ c.points_of_disagreement|join:" " }}</div>
        {% endif %}
        {% if c.flagged_numbers %}<div class="flags">{{ c.flagged_numbers|length }} unverified number(s) in the committee text.</div>{% endif %}
      {% else %}<p class="empty">The committee hasn't reviewed this business yet.</p>{% endif %}
      {% endwith %}
    </section>

    <section aria-labelledby="s7">
      <h2 id="s7"><span class="n">07</span>Decision history</h2>
      <ol class="history">
      {% for h in d.history %}
        <li><span class="mono">{{ h.at|when }}</span> · {{ h.by|default:"system" }} · {% if h.from %}{{ h.from|humanize_key }} → {% endif %}{{ h.to|humanize_key }}{% if h.note %}: “{{ h.note }}”{% endif %}</li>
      {% empty %}<li class="empty">No changes recorded.</li>
      {% endfor %}
      </ol>
    </section>

    <section aria-labelledby="s8">
      <h2 id="s8"><span class="n">08</span>What this brief is not</h2>
      <div class="not-this"><ul>{% for line in brief.what_this_is_not %}<li>{{ line }}</li>{% endfor %}</ul></div>
    </section>

    <footer class="sheet-foot">
      <span>Decision <span class="mono">{{ d.id }}</span></span>
      <span>Built only from saved data; nothing on this page was recalculated.</span>
    </footer>
  </article>
{% endwith %}
</body>
</html>
```

## ✅ Check

```bash
python manage.py check
```

`System check identified no issues (0 silenced).` The page isn't connected to an address
yet: that's one line in `config/urls.py`, in the next lesson, together with the API.

## 🔍 Line by line

### `decisions/views.py`

- **Lines 1–5** · Messages, login-required, `get_object_or_404`, `redirect`, POST-only,
  and Django's `DetailView` (a ready-made "show one record" page).
- **Line 7** · `OrgPageMixin` (lesson 4.6): login required, and only your organization's
  records.
- **Lines 9–11** · The table, the workflow and `build_brief`.
- **Line 14** · `DecisionBriefView`: one decision's brief page.
- **Line 15** · Docstring: the same data as the API.
- **Lines 17–19** · Which table, which template, and the name the template uses
  (`decision`).
- **Lines 21–22** · Load the business, run, scenario and owner in the same query.
  `run__scenario` follows two links.
- **Lines 24–26** · Add the brief to what the template receives.
- **Lines 27–29** · The buttons: each allowed next status with its label, e.g.
  `("approved", "Approved")`. `Decision.Status(s).label` turns a value into its label.
- **Line 30** · Hand it all to the template.
- **Lines 33–35** · `decision_status`: logged in, POST only.
- **Line 36** · The decision, only if it's yours (else 404).
- **Line 37** · The old status, and the one asked for.
- **Lines 38–40** · Not one of the five statuses at all? Say so and go back.
- **Lines 41–45** · Not allowed from here? Show the helpful message and go back.
- **Lines 46–47** · Change and save just the status.
- **Line 48** · Record it in the history (and the sign-off), with the optional note.
- **Lines 49–50** · "Marked approved." and back to the brief.

### `decisions/urls.py`

- **Line 5** · `app_name = "decisions"`: these names are used as `decisions:brief` and
  `decisions:status`, so they can't clash with names in other apps.
- **Line 8** · `/decisions/<id>/brief/`. `.as_view()` turns a class-based view into a
  function Django can call.
- **Line 9** · `/decisions/<id>/status/`.

### `brief.html`

- **Line 1** · Load `static` and **our** filters (`warroom`, lesson 9.5).
- **Lines 2–9** · The page head: title, fonts, and the print stylesheet.
- **Line 11** · `{% with %}` gives short names: `d` for the decision part, `run`,
  `out` for outcomes. Closed on line 182.
- **Lines 12–24** · The toolbar (hidden when printing):
  - **Line 13** · ← Back (to home, for now).
  - **Line 14** · Any messages, like "Marked approved."
  - **Lines 16–21** · One small form per allowed status. `{% csrf_token %}` (lesson 4.3)
    protects it. The "rejected" button gets a quieter style.
  - **Line 22** · `window.print()` opens the browser's print window.
- **Lines 26–30** · The sheet, and its top line with the date (`|when`).
- **Lines 32–36** · The title, and what run it's based on, or that there's none.
- **Lines 38–45** · The facts box: status, owner, chosen response (its label, else its
  key, else "Not chosen yet": `default` filters chained), sign-off, business, recorded.
- **Lines 47–51** · **01 Decision and rationale.** `|linebreaksbr` keeps the writer's line
  breaks. No rationale? A polite nudge.
- **Lines 53–68** · **02 What was tested:** the run's parameters, each with `|figure`,
  then the run id, engine version and the first 12 characters of the input fingerprint.
- **Lines 70–87** · **03 Assumptions,** with a line saying whether they're frozen, a key
  to the tags, and each value with its source tag (`|source_tag`).
- **Lines 89–116** · **04 Modelled outcomes:** a table, one column per case. The chosen
  column gets the `chosen` class and a "Chosen" mark (lines 95 and 100). Below it, the
  engine's comparison (marked "facts, not a recommendation"), what each case means, and
  engine notes.
- **Lines 118–138** · **05 Analyst reading:** the AI explanation. It always shows the
  **"AI analysis"** label, model, prompt version and date (lines 123–124). Lines 131–134:
  if numbers were flagged, a box lists them as "not from the simulation". No explanation?
  "It's optional: the outcomes above stand on their own."
- **Lines 140–160** · **06 Expert committee:** each desk's verdict, headline, concerns
  and "Do:" actions; where they disagree; any flagged numbers.
- **Lines 162–170** · **07 Decision history:** every entry, oldest first, as
  "time · person · from → to: note". `{% empty %}` runs when the list is empty.
- **Lines 172–175** · **08 What this brief is not:** the three sentences.
- **Lines 177–180** · The footer: the decision id, and "nothing on this page was
  recalculated".

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `TemplateSyntaxError: Invalid filter: 'figure'` (in 9.7) | Line 1 must `{% load static warroom %}`, and lesson 9.5's file must exist. Restart `runserver`. |
| `NoReverseMatch: 'run-detail'` (in 9.7) | You copied the finished template. Use the for-now one: line 13 links to `home`. |

## ❓ Quiz

1. Why does the page not extend `base.html`?
2. Why does `decision_status` end with a redirect instead of showing the page directly?
3. Where would a flagged AI number appear on the brief?

---

**Next:** [9.7 · The API, and try it](07-the-api-and-try-it.md)

<details><summary>Quiz answers</summary>

1. It's meant for printing: no menus, just the sheet, with its own print stylesheet.
2. Post, then redirect: refreshing the page then repeats the harmless GET, not the form.
3. In section 05 (or 06 for the committee), in a box saying the numbers are not from the
   simulation.

</details>
