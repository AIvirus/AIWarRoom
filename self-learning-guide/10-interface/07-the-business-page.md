# 10.7 · The business page

**Time:** 60 minutes · **Before this:** [10.6](06-board-form-demo-data.md).

## Read

The business page is the biggest server page. Left column: the **assumption ledger**,
**scenarios**, **components** (operating businesses only) and the **expert committee**.
Right column: **run history**, the **company site** (operating only) and **decisions**.

Almost everything is plain forms that POST to the views from lesson 10.3. Two buttons need
a little JavaScript, because they wait for something slow:

| Button | Script | What it does |
|---|---|---|
| "Convene the committee" | `static/js/ai-actions.js` | POSTs to the committee API, shows "Usually 5–10 seconds", then reloads the page to show the saved, labelled result (or shows the API's error message) |
| "Scan the site" | `static/js/scan.js` | Starts a scan and shows each step live from the SSE stream (Part 8), then reloads |

Both scripts are already in `static/js/` (copied in lesson 4.2). Here you read them.

The same `ai-actions.js` also drives "Ask the analyst" on the run pages (next lesson):
each button says **which** API address to call in a `data-ai-action` attribute, so one
script serves them all.

## Do

### 1. `templates/businesses/detail.html`

<!-- source: templates/businesses/detail.html:1-185 -->
```html
{% extends "base.html" %}
{% load static warroom %}
{% block title %}{{ business.name }} · AI WarRoom{% endblock %}
{% block content %}
<div class="page">
  <header class="page-head">
    <p class="crumbs"><a href="{% url 'home' %}">Operations board</a> /</p>
    <h1>{{ business.name }}</h1>
    {% if business.mode == "idea" %}<span class="tag idea">Idea</span>{% else %}<span class="tag ops">Operating</span>{% endif %}
    <span class="chip">{{ business.industry }}</span>
    {% if business.website_url %}<a class="chip" href="{{ business.website_url }}" rel="noopener" target="_blank">{{ business.website_url }}</a>{% endif %}
  </header>

  <div class="cols-main-side">
    <div class="stack">
      {# ---------------- Assumptions ---------------- #}
      <section class="panel ticked" id="assumptions" aria-labelledby="p-assume">
        <div class="panel-head"><span class="panel-id">B-01</span><h2 id="p-assume">Assumption ledger</h2>
          <span class="aside">every value carries its source</span></div>
        <form method="post" action="{% url 'business-assumptions' business.pk %}">
          {% csrf_token %}
          <div class="table-scroll"><table class="ledger">
            <thead><tr><th>Input</th><th class="num">Value</th><th>Unit</th><th>Source</th></tr></thead>
            <tbody>
            {% for spec, value, source in assumptions_form.rows %}
              <tr>
                <td><label for="{{ value.id_for_label }}">{{ spec.label }}</label>{% if spec.help %}<span class="help">{{ spec.help }}</span>{% endif %}</td>
                <td class="num" style="width: 11rem">{{ value }}</td>
                <td><span class="unit">{{ spec.unit }}</span></td>
                <td style="width: 12.5rem"><label class="sr-only" for="{{ source.id_for_label }}">{{ source.label }}</label>{{ source }}</td>
              </tr>
            {% endfor %}
            </tbody>
          </table></div>
          <div class="panel-foot btn-row">
            <button class="btn btn-primary btn-sm" type="submit">Save assumptions</button>
            <span>Leave a value blank to remove it. Saved runs keep the values they were run with.</span>
          </div>
        </form>
      </section>

      {# ---------------- Scenarios ---------------- #}
      <section class="panel ticked" id="scenarios" aria-labelledby="p-scen">
        <div class="panel-head"><span class="panel-id">B-02</span><h2 id="p-scen">Scenarios</h2></div>
        <div class="table-scroll"><table class="ledger">
          <thead><tr><th>Scenario</th><th>Type</th><th>Last run</th><th></th></tr></thead>
          <tbody>
          {% for row in scenarios %}
            <tr>
              <td class="row-title">{{ row.scenario.name }}</td>
              <td>{{ row.scenario.template.name }}</td>
              <td>{% if row.last_run %}<a href="{% url 'run-detail' row.last_run.pk %}">Open {% if business.mode == "idea" %}bench{% else %}board{% endif %}</a>
                  <span class="help mono">{{ row.last_run.created_at|date:"d M, H:i" }} UTC</span>
                {% elif row.missing %}<span class="help">Needs: {% for k in row.missing %}{{ k|humanize_key }}{% if not forloop.last %}, {% endif %}{% endfor %}</span>
                {% else %}<span class="unit">Not run</span>{% endif %}</td>
              <td class="num"><form class="inline-form" method="post" action="{% url 'business-scenario-run' business.pk row.scenario.pk %}">{% csrf_token %}
                <button class="btn btn-sm" type="submit" {% if row.missing %}disabled title="Add the missing assumptions first"{% endif %}>Run</button></form></td>
            </tr>
          {% empty %}
            <tr class="empty-row"><td colspan="4">No scenarios yet. {% if business.mode == "idea" %}Add an idea stress test below to see best, expected and worst cases.{% else %}Add a disruption below: payment gateway, warehouse or courier.{% endif %}</td></tr>
          {% endfor %}
          </tbody>
        </table></div>
        <form class="panel-body form-grid" method="post" action="{% url 'business-scenario-create' business.pk %}">
          {% csrf_token %}
          {% with field=scenario_form.template_key %}{% include "accounts/_field.html" %}{% endwith %}
          {% with field=scenario_form.name %}{% include "accounts/_field.html" %}{% endwith %}
          <div class="field"><button class="btn btn-primary" type="submit">Create and run</button></div>
        </form>
      </section>

      {# ---------------- Components (operating only) ---------------- #}
      {% if business.mode == "operating" %}
      <section class="panel ticked" id="components" aria-labelledby="p-comp">
        <div class="panel-head"><span class="panel-id">B-03</span><h2 id="p-comp">Components and dependencies</h2></div>
        <div class="table-scroll"><table class="ledger">
          <thead><tr><th>Component</th><th>Kind</th><th class="num">Criticality</th><th>Depends on</th><th></th></tr></thead>
          <tbody>
          {% for c in components %}
            <tr>
              <td class="row-title">{{ c.name }}{% if c.fallback_note %}<span class="help">Fallback: {{ c.fallback_note }}</span>{% endif %}</td>
              <td>{{ c.get_kind_display }}</td>
              <td class="num">{{ c.criticality }}/5</td>
              <td>{% for d in c.depends_on.all %}{{ d.name }}{% if not forloop.last %}, {% endif %}{% empty %}<span class="unit">nothing</span>{% endfor %}</td>
              <td class="num"><form class="inline-form" method="post" action="{% url 'business-component-delete' business.pk c.pk %}">{% csrf_token %}
                <button class="btn-link" type="submit" aria-label="Remove {{ c.name }}">Remove</button></form></td>
            </tr>
          {% empty %}
            <tr class="empty-row"><td colspan="5">No components yet. Add the payment gateway, warehouse and courier so the system view shows your real names.</td></tr>
          {% endfor %}
          </tbody>
        </table></div>
        <form class="panel-body form-grid" method="post" action="{% url 'business-component-create' business.pk %}">
          {% csrf_token %}
          {% for field in component_form %}{% include "accounts/_field.html" %}{% endfor %}
          <div class="field"><button class="btn" type="submit">Add component</button></div>
        </form>
      </section>
      {% endif %}

      {# ---------------- Committee ---------------- #}
      <section class="panel ticked" id="committee" aria-labelledby="p-com">
        <div class="panel-head"><span class="panel-id">B-04</span><h2 id="p-com">Expert committee</h2>
          <span class="aside">four desks · one AI call</span></div>
        {% if committee %}
          {% include "simulations/_committee.html" with c=committee %}
        {% else %}
          <p class="state">The committee hasn't met. It reviews your latest runs and site profile from four angles (finance, operations, market and competition, risk) and is allowed to disagree.</p>
        {% endif %}
        <div class="panel-foot btn-row">
          <button class="btn btn-sm" type="button" data-ai-action="{% url 'api:business-committee' business.pk %}" data-status="committee-status" data-anchor="committee" data-busy="Convening the committee. Usually 5–10 seconds.">{% if committee %}Reconvene{% else %}Convene the committee{% endif %}</button>
          <span id="committee-status"></span>
        </div>
      </section>
    </div>

    <div class="stack">
      {# ---------------- Runs ---------------- #}
      <section class="panel ticked" aria-labelledby="p-runs">
        <div class="panel-head"><span class="panel-id">B-05</span><h2 id="p-runs">Run history</h2></div>
        {% for run in runs %}
          <div class="alert-row">
            <span class="sev {% if run.status == 'failed' %}critical{% endif %}" aria-hidden="true"></span>
            <div><p>{% if run.status == "completed" %}<a href="{% url 'run-detail' run.pk %}">{{ run.scenario.name }}</a>{% else %}{{ run.scenario.name }}{% endif %}</p>
              <span class="meta">{{ run.get_status_display|upper }} · {{ run.created_at|date:"d M, H:i" }} UTC · {{ run.input_hash|slice:":8" }}</span>
              {% if run.error %}<span class="meta" style="color: var(--fault)">{{ run.error }}</span>{% endif %}</div>
            <span></span>
          </div>
        {% empty %}<p class="state">No runs yet.</p>{% endfor %}
      </section>

      {# ---------------- Company site ---------------- #}
      {% if business.mode == "operating" %}
      <section class="panel ticked" id="site" aria-labelledby="p-site">
        <div class="panel-head"><span class="panel-id">B-06</span><h2 id="p-site">Company site</h2>
          {% if latest_scan %}<span class="aside">last scan {{ latest_scan.created_at|date:"d M, H:i" }} UTC · {{ latest_scan.get_status_display|lower }}</span>{% endif %}</div>
        {% if business.website_url %}
          <div class="panel-body">
            <p class="unit" style="margin-top: 0">On-demand read of public pages. Respects robots.txt; private network addresses are refused. Nothing watches the site between scans.</p>
            <div class="btn-row"><button class="btn btn-sm" type="button" data-scan-start="{% url 'api:business-scans' business.pk %}">{% if latest_scan %}Re-scan now{% else %}Scan the site{% endif %}</button>
              <span id="scan-status"></span></div>
          </div>
          <ol class="log" id="scan-log" aria-live="polite" hidden></ol>
          {% for alert in alerts %}
            <div class="alert-row">
              <span class="sev {{ alert.severity }}" aria-hidden="true"></span>
              <div><p>{{ alert.summary }}</p><span class="meta">{{ alert.get_kind_display|upper }}</span></div>
              <form class="inline-form" method="post" action="{% url 'alert-acknowledge' alert.pk %}">{% csrf_token %}
                <input type="hidden" name="next" value="{{ request.path }}#site"><button class="btn btn-sm" type="submit">Ack</button></form>
            </div>
          {% endfor %}
          {% if site_profile %}
            {% with p=site_profile.output %}
            <div class="panel-body ai-block" style="margin: var(--s3)">
              <span class="ai-label">AI analysis</span><span class="meta">site profile · {{ site_profile.created_at|date:"d M, H:i" }} UTC</span>
              <p>{{ p.summary }}</p>
              {% if p.dependencies %}<h4>Dependencies it names</h4><ul>{% for d in p.dependencies %}<li>{{ d.name }} <span class="basis {{ d.basis }}">{{ d.basis }}</span></li>{% endfor %}</ul>{% endif %}
              {% if p.competitors %}<h4>Competitors</h4><ul>{% for c in p.competitors %}<li>{{ c.name }} <span class="basis {{ c.basis }}">{% if c.basis == "inference" %}unverified inference{% else %}{{ c.basis }}{% endif %}</span>{% if c.source_url %} · <a href="{{ c.source_url }}" rel="noopener" target="_blank">source</a>{% endif %}<br><span class="unit">{{ c.reason }}</span></li>{% endfor %}</ul>{% endif %}
              {% if p.future_scenarios %}<h4>Scenarios worth testing</h4><ul>{% for s in p.future_scenarios %}<li>{{ s.title }}{% if s.suggested_template != "none" %} <span class="unit">→ {{ s.suggested_template|humanize_key }}</span>{% endif %}</li>{% endfor %}</ul>{% endif %}
              {% if site_profile.flagged_numbers %}<div class="flagged">{{ site_profile.flagged_numbers|length }} number(s) here are not from the site extract.</div>{% endif %}
            </div>
            {% endwith %}
          {% endif %}
        {% else %}
          <p class="state">No website on file. Add a public URL to the profile to read pricing, products and named providers on demand.</p>
        {% endif %}
      </section>
      {% endif %}

      {# ---------------- Decisions ---------------- #}
      <section class="panel ticked" aria-labelledby="p-dec">
        <div class="panel-head"><span class="panel-id">B-07</span><h2 id="p-dec">Decisions</h2></div>
        {% for d in decisions %}
          <div class="alert-row"><span class="sev {% if d.status == 'proposed' %}warn{% elif d.status == 'rejected' %}critical{% endif %}" aria-hidden="true"></span>
            <div><p><a href="{% url 'decisions:brief' d.pk %}">{{ d.title }}</a></p><span class="meta">{{ d.get_status_display|upper }} · {{ d.owner|default:"unassigned" }}</span></div><span></span></div>
        {% empty %}<p class="state">None yet. Record one from a run after comparing the responses.</p>{% endfor %}
      </section>
    </div>
  </div>
</div>
{% endblock %}
{% block scripts %}
<script type="module" src="{% static 'js/ai-actions.js' %}"></script>
<script type="module" src="{% static 'js/scan.js' %}"></script>
{% endblock %}
```

### 2. `templates/simulations/_committee.html`

A small shared piece: the committee review. The business page shows it, and so does the
Situation Board (next lesson). Make the folder `templates/simulations/`, then:

<!-- source: templates/simulations/_committee.html:1-21 -->
```html
{% load warroom %}
{# The committee review: four desks, each with its own verdict. Disagreement is shown, not hidden. #}
<div class="panel-body" style="padding-bottom: 0">
  <span class="ai-label">AI analysis</span><span class="meta mono">{{ c.created_at|date:"d M, H:i" }} UTC · {{ c.model_name }}</span>
</div>
<div class="desks">
{% for a in c.output.advisors %}
  <div class="desk">
    <span class="label">{{ a.desk_name }}</span> <span class="verdict {{ a.verdict }}">{{ a.verdict|humanize_key }}</span>
    <h4>{{ a.headline }}</h4>
    <ul>
      {% for k in a.key_concerns|slice:":2" %}<li>{{ k }}</li>{% endfor %}
      {% for r in a.recommended_actions|slice:":2" %}<li><em>Do:</em> {{ r }}</li>{% endfor %}
    </ul>
  </div>
{% endfor %}
</div>
{% if c.output.points_of_disagreement %}
  <div class="honesty" style="margin: var(--s3)"><strong>Where the desks disagree:</strong> {{ c.output.points_of_disagreement|join:" " }}</div>
{% endif %}
{% if c.flagged_numbers %}<div class="flagged" style="margin: var(--s3)">{{ c.flagged_numbers|length }} number(s) in the committee's text are not from the data it was given: {% for f in c.flagged_numbers %}<span class="mono">{{ f.literal }}</span>{% if not forloop.last %}, {% endif %}{% endfor %}.</div>{% endif %}
```

### 3. Read `static/js/ai-actions.js`

<!-- source: static/js/ai-actions.js:1-28 -->
```js
// Buttons that ask Gemini for something (run explanation, committee review).
// <button data-ai-action="/api/v1/..." data-busy="Asking the analyst…">
// On success the page reloads to show the stored, labelled analysis; on failure the API's
// own message is shown next to the button (quota used up, no key, rate limited...).

import { api } from "./lib/api.js";

document.querySelectorAll("[data-ai-action]").forEach((button) => {
  const status = document.getElementById(button.dataset.status);
  button.addEventListener("click", async () => {
    button.disabled = true;
    if (status) {
      status.className = "state busy";
      status.textContent = button.dataset.busy || "Working…";
    }
    try {
      await api(button.dataset.aiAction, { method: "POST" });
      window.location.hash = button.dataset.anchor || "";
      window.location.reload();
    } catch (error) {
      button.disabled = false;
      if (status) {
        status.className = "state error";
        status.textContent = error.message;
      }
    }
  });
});
```

### 4. Read `static/js/scan.js`

<!-- source: static/js/scan.js:1-59 -->
```js
// Live company scan: start it, then read the Server-Sent Events stream as it runs.

import { api } from "./lib/api.js";

const button = document.querySelector("[data-scan-start]");
const log = document.getElementById("scan-log");
const status = document.getElementById("scan-status");

function addLine(event) {
  const item = document.createElement("li");
  item.className = event.status || event.step;
  const step = document.createElement("span");
  step.className = "step";
  step.textContent = event.step.replace("_", " ");
  const message = document.createElement("span");
  message.textContent = event.message; // textContent, never innerHTML: it's site text
  item.append(step, message);
  log.append(item);
  log.scrollTop = log.scrollHeight;
}

button?.addEventListener("click", async () => {
  button.disabled = true;
  log.replaceChildren();
  log.hidden = false;
  status.className = "state busy";
  status.textContent = "Scanning. Each step appears below as it happens.";
  try {
    const { events_url: eventsUrl } = await api(button.dataset.scanStart, { method: "POST" });
    const stream = new EventSource(eventsUrl);
    const steps = ["check", "robots", "page", "skip", "ai", "ai_done", "ai_skipped",
      "baseline", "alerts", "busy", "done"];
    steps.forEach((step) =>
      stream.addEventListener(step, (message) => {
        const event = JSON.parse(message.data);
        addLine(event);
        if (step === "done" || step === "busy") {
          stream.close();
          status.className = event.status === "completed" ? "state" : "state error";
          status.textContent = event.status === "completed"
            ? "Done. Reloading to show the profile and any alerts…"
            : event.message;
          if (event.status === "completed") setTimeout(() => window.location.reload(), 900);
          else button.disabled = false;
        }
      }),
    );
    stream.onerror = () => {
      stream.close();
      status.className = "state error";
      status.textContent = "Lost the connection to the scan. Reload to see where it got to.";
      button.disabled = false;
    };
  } catch (error) {
    status.className = "state error";
    status.textContent = error.message;
    button.disabled = false;
  }
});
```

## Check

Open the board and click **Chai Cart** (the idea you added in 10.6).

1. **The ledger.** Type `150` for "Visit-to-customer conversion" and click **Save
   assumptions**. The message says "Nothing saved. Visit-to-customer conversion: must be
   at most 100 %". Put `8` instead, fill in the rest (price `30`, variable cost `12`, fixed
   costs `40000`, marketing `10000`, cost per visit `5`, orders per customer `12`,
   retention `70`, investment `150000`) and save: "Assumptions saved. Past runs keep the
   values they used."
2. **A scenario that can't run.** Before saving the ledger, a scenario shows "Needs: ..."
   and its **Run** button is greyed out. (If you saved already, try it on a new idea.)

Now open **Kirana Express**:

3. **A component.** In "Components and dependencies", add "Delhivery", kind "Logistics",
   criticality `4`, depends on nothing. It appears in the table. **Remove** takes it away
   again.

Now open **Books Corner** (from Part 8):

4. **Scan the site.** Click **Re-scan now**. The steps appear one by one under the button
   (`CHECK`, `ROBOTS`, `PAGE`...), then "Done. Reloading..." and the page reloads with the
   site profile. Its competitor carries the **unverified inference** tag.
5. **The committee.** Click **Reconvene**. It's answered from the cache (nothing changed
   since 8.10), so the page reloads almost at once, with the four desks.

Don't click **Run** or **Create and run** yet: the run pages are the next lesson.

## Line by line

### `detail.html`

- **Lines 1–3** · Frame, `static` and our filters, title.
- **Lines 5–12** · Header: breadcrumb, name, mode tag, industry, and the website as a
  link. `rel="noopener"` stops the opened site from controlling this tab.
- **Line 14** · Two columns.
- **Lines 17–40** · **Assumption ledger.** One form for all inputs. For each row of
  `assumptions_form.rows` (lesson 10.2): the label (tied to its input with `for`) and
  help, the value box, the unit, and the source drop-down with a label only screen
  readers see (`sr-only`). A save button and a reminder that blank removes.
- **Lines 43–70** · **Scenarios.** For each: name, template, and either a link to its last
  run, the inputs it still **needs**, or "Not run". Its Run button is `disabled` while
  inputs are missing. Below: the "Create and run" form, drawn with `_field.html`.
- **Lines 73–99** · **Components** (operating only): each with its fallback, kind,
  criticality "4/5", what it depends on, and a Remove button. Then the add form.
- **Lines 102–114** · **Committee.** The latest review (the shared piece below), or an
  explanation. The button carries its instructions in `data-` attributes: which API to
  POST to, which element shows the status, where to scroll after reloading, and what to
  say while waiting.
- **Lines 119–130** · **Run history:** each run (a link if it completed), its status,
  time and the first 8 characters of its input fingerprint, and its error if it failed.
- **Lines 133–168** · **Company site** (operating only):
  - **Lines 137–143** · With a website: an honest note (robots.txt, private addresses
    refused, nothing watches between scans), the scan button with its API address in
    `data-scan-start`, a status line, and an empty, hidden log list. `aria-live` makes
    screen readers announce new lines.
  - **Lines 144–151** · Unread alerts, each with an Ack button that returns to `#site`.
  - **Lines 152–163** · The latest site profile: the **AI analysis** label, summary,
    dependencies and competitors **each with its basis** ("unverified inference" for
    guesses, with a source link only when there is one), suggested scenarios, and any
    flagged numbers.
  - **Line 165** · No website: what adding one would give you.
- **Lines 171–177** · **Decisions**, each linking to its brief.
- **Lines 182–185** · The two scripts, as modules.

### `_committee.html`

- **Line 1** · Our filters (an included piece loads its own).
- **Line 2** · A comment: disagreement is shown, not hidden.
- **Lines 3–5** · The **AI analysis** label, date and model.
- **Lines 6–17** · One box per desk: its name, its verdict (`proceed_with_conditions` →
  "proceed with conditions"), headline, the first two concerns (`|slice:":2"`) and the
  first two actions.
- **Lines 18–20** · Where the desks disagree.
- **Line 21** · Any numbers not found in the data the committee was given.

### `ai-actions.js`

- **Lines 1–4** · Comments: what the buttons look like and what happens.
- **Line 6** · Import our `api()` helper (lesson 10.9).
- **Line 8** · For every element with a `data-ai-action` attribute...
- **Line 9** · ...find its status element. `button.dataset.status` reads `data-status`.
- **Line 10** · When it's clicked (`async`: it will wait for the server):
- **Lines 11–15** · Disable the button (no double clicks) and show the "busy" message.
- **Line 17** · POST to the address in `data-ai-action` (`dataset.aiAction`: dashes in
  the HTML become capital letters in JavaScript). `await` waits for the answer.
- **Lines 18–19** · Success: set the address's `#anchor` and reload, so the page shows
  the saved result where it belongs.
- **Lines 20–26** · Failure (no key, budget, rate limit...): re-enable the button and
  show the API's own message.

### `scan.js`

- **Lines 1–3** · Comment and import.
- **Lines 5–7** · Find the button, the log list and the status line.
- **Lines 9–20** · `addLine(event)`: a list item with the step name (`ai_done` →
  `ai done`) and the message. Line 16 is the safety line from lesson 10.1: website text
  goes in with `textContent`, never `innerHTML`. Then scroll the log to the bottom.
- **Line 22** · `button?.addEventListener`: the `?.` means "only if there is a button".
  A business with no website has none, and this line then does nothing instead of
  crashing.
- **Lines 23–27** · Disable, clear and show the log, "Scanning...".
- **Line 29** · Start the scan; take `events_url` from the answer and call it `eventsUrl`.
- **Line 30** · Tune in to the stream (lesson 8.9).
- **Lines 31–47** · Listen for each step name. Each event becomes a line. On `done` or
  `busy`: close the stream, and either reload (completed) or show why it stopped and
  re-enable the button.
- **Lines 48–53** · The connection broke: say so, honestly.
- **Lines 54–58** · Starting failed (for example, no website): show the API's message.

## If it didn't work

| You see | Fix |
|---|---|
| `TemplateDoesNotExist: simulations/_committee.html` | Step 2: the file goes in `templates/simulations/`. |
| Clicking "Re-scan now" does nothing | Open the console (F12): an error there names the file. Is `{% block scripts %}` at the end (lines 182–185)? |
| `NoReverseMatch: 'business-committee'` | The committee action must be in `businesses/api.py` (lesson 8.10). |

## Quiz

1. How does one `ai-actions.js` serve several different buttons?
2. Why does `scan.js` use `button?.addEventListener`?
3. Why is the Run button sometimes greyed out?

---

**Next:** [10.8 · The run pages](08-the-run-pages.md)

<details><summary>Quiz answers</summary>

1. Each button carries its own API address and messages in `data-` attributes.
2. Pages without a website have no scan button; `?.` skips the line instead of crashing.
3. The scenario is missing inputs (the view lists them); you can't run it until they're
   saved.

</details>
