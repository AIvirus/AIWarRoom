# 10.8 · The run pages

**Time:** 50 minutes · **Before this:** [10.7](07-the-business-page.md).

## Read

The two run pages are **skeletons**. The templates draw the frame: panel headings, empty
boxes with ids like `controls`, `gauges`, `stage`, `cash-chart`. Then a JavaScript module
reads `page-data` and fills the boxes in (lessons 10.10 and 10.11).

```text
board.html                               board/main.js fills in
┌ S-01 Response console ─┐┌ S-02 System view ─────┐┌ S-03 At T+0 ─┐
│ #strategies #controls  ││ #stage (3D or 2D)     ││ #gauges      │
└────────────────────────┘└───────────────────────┘└──────────────┘
┌ S-04 Timeline: #play  #scrubber  #speed ───────────────────────────┐
┌ S-05 Responses compared: #comparison ┐┌ S-06 Analyst reading ──────┐
┌ S-07 Expert committee ───────────────┐┌ S-08 Record a decision ────┐
```

The **server** draws the parts that don't change with sliders: the AI reading, the
committee and the decision form. They come from three small shared pieces, used by both
pages: `_analysis.html`, `_committee.html` (lesson 10.7) and `_decision.html`.

Notice the AI panel's note: *"explains the saved run, not unsaved slider changes"*. A
what-if is never sent to the AI; only a saved run is.

## Do

Create these four files in `templates/simulations/`.

### 1. `board.html` (the Situation Board)

<!-- source: templates/simulations/board.html:1-98 -->
```html
{% extends "base.html" %}
{% load static warroom %}
{% block title %}Situation board · {{ run.scenario.name }} · AI WarRoom{% endblock %}
{% block head %}
  {# Three.js r170, self-hosted (MIT, see static/vendor/three-0.170.0/LICENSE.txt). #}
  {# Only the 3D view imports it, so the 2D schematic never downloads it. #}
  <script type="importmap">{"imports": {"three": "{% static 'vendor/three-0.170.0/three.module.min.js' %}"}}</script>
{% endblock %}
{% block content %}
<div class="page" style="max-width: 1480px">
  <header class="page-head">
    <p class="crumbs"><a href="{% url 'home' %}">Operations board</a> / <a href="{% url 'business-detail' run.business.pk %}">{{ run.business.name }}</a> /</p>
    <h1>{{ run.scenario.name }}</h1>
    <span class="chip">{{ template.name }}</span>
    <span class="chip" id="mode-chip">Saved run · {{ run.created_at|date:"d M, H:i" }} UTC</span>
    <div class="spacer"></div>
    <span class="unit mono">engine {{ run.engine_version }} · inputs {{ run.input_hash|slice:":8" }}</span>
  </header>

  <div class="board">
    {# ---------------- Console ---------------- #}
    <section class="panel ticked" aria-labelledby="p-console">
      <div class="panel-head"><span class="panel-id">S-01</span><h2 id="p-console">Response console</h2></div>
      <div class="panel-body">
        <fieldset class="strategies" id="strategies">
          <legend>Response to show</legend>
        </fieldset>
        <div id="controls" style="margin-top: var(--s3)"></div>
        <p class="state" id="preview-status" aria-live="polite"></p>
        <div class="btn-row" id="whatif-actions" hidden>
          <button class="btn btn-sm btn-primary" type="button" id="save-run">Save as a new run</button>
          <button class="btn btn-sm" type="button" id="reset">Back to saved run</button>
        </div>
      </div>
    </section>

    {# ---------------- System view ---------------- #}
    <section class="panel ticked stage-panel" aria-labelledby="p-stage">
      <div class="panel-head"><span class="panel-id">S-02</span><h2 id="p-stage">System view</h2>
        <span class="aside" id="view-kind">loading</span></div>
      <div class="stage" id="stage" role="img" aria-label="Diagram of the business as connected components; a text table follows for screen readers."></div>
      <div class="stage-legend" aria-hidden="true">
        <span>Normal</span><span class="l-degraded">Degraded</span><span class="l-failed">Down</span>
        <em>Moving dots: orders getting through. Fewer dots, less flow.</em>
      </div>
      <table class="sr-only" aria-live="polite"><caption>Component health at the selected hour</caption><tbody id="sr-health"></tbody></table>
    </section>

    {# ---------------- Gauges ---------------- #}
    <section class="panel ticked gauges-panel" aria-labelledby="p-gauges">
      <div class="panel-head"><span class="panel-id">S-03</span><h2 id="p-gauges">At <span id="gauge-hour">T+0</span></h2></div>
      <div class="gauges" id="gauges" aria-live="polite"></div>
    </section>
  </div>

  {# ---------------- Timeline ---------------- #}
  <section class="panel ticked" style="margin-top: var(--s3)" aria-labelledby="p-time">
    <div class="panel-head"><span class="panel-id">S-04</span><h2 id="p-time">Timeline</h2>
      <span class="aside">hour 0 = outage starts · ← → to step</span></div>
    <div class="timeline">
      <button class="btn btn-sm" type="button" id="play" aria-pressed="false">Play</button>
      <div class="clock" id="clock">T+00<small>18:00</small></div>
      <div class="track">
        <div class="outage" id="outage-band" aria-hidden="true"></div>
        <label class="sr-only" for="scrubber">Hour of the simulation</label>
        <input type="range" id="scrubber" min="0" max="71" value="0" step="1">
        <div class="ticks" id="ticks" aria-hidden="true"></div>
      </div>
      <button class="btn btn-sm" type="button" id="speed" aria-label="Playback speed">1×</button>
    </div>
  </section>

  <div class="cols-2" style="margin-top: var(--s3)">
    {# ---------------- Comparison ---------------- #}
    <section class="panel ticked" aria-labelledby="p-cmp">
      <div class="panel-head"><span class="panel-id">S-05</span><h2 id="p-cmp">Responses compared</h2>
        <span class="aside">engine facts, no winner declared</span></div>
      <div class="table-scroll"><table class="ledger" id="comparison"></table></div>
      <p class="panel-foot" id="engine-notes"></p>
    </section>
    {% include "simulations/_analysis.html" with panel_id="S-06" %}
  </div>

  <div class="cols-2" style="margin-top: var(--s3)">
    <section class="panel ticked" aria-labelledby="p-com">
      <div class="panel-head"><span class="panel-id">S-07</span><h2 id="p-com">Expert committee</h2></div>
      {% if committee %}{% include "simulations/_committee.html" with c=committee %}
      {% else %}<p class="state">No committee review yet. Convene it from the <a href="{% url 'business-detail' run.business.pk %}#committee">business page</a>.</p>{% endif %}
    </section>
    {% include "simulations/_decision.html" with panel_id="S-08" %}
  </div>
</div>
{{ page_data|json_script:"page-data" }}
{% endblock %}
{% block scripts %}
<script type="module" src="{% static 'js/ai-actions.js' %}"></script>
<script type="module" src="{% static 'js/board/main.js' %}"></script>
{% endblock %}
```

### 2. `bench.html` (the Idea Bench)

<!-- source: templates/simulations/bench.html:1-74 -->
```html
{% extends "base.html" %}
{% load static warroom %}
{% block title %}Idea bench · {{ run.scenario.name }} · AI WarRoom{% endblock %}
{% block content %}
<div class="page" style="max-width: 1480px">
  <header class="page-head">
    <p class="crumbs"><a href="{% url 'home' %}">Operations board</a> / <a href="{% url 'business-detail' run.business.pk %}">{{ run.business.name }}</a> /</p>
    <h1>{{ run.scenario.name }}</h1>
    <span class="chip">{{ template.name }}</span>
    <span class="chip" id="mode-chip">Saved run · {{ run.created_at|date:"d M, H:i" }} UTC</span>
    <div class="spacer"></div>
    <span class="unit mono">engine {{ run.engine_version }} · inputs {{ run.input_hash|slice:":8" }}</span>
  </header>

  <div class="bench">
    <section class="panel ticked" aria-labelledby="p-ledger">
      <div class="panel-head"><span class="panel-id">I-01</span><h2 id="p-ledger">Assumption ledger</h2></div>
      <div class="panel-body">
        <p class="unit" style="margin-top: 0">Move a value to see every case respond. Nothing is saved until you choose to.</p>
        <div id="controls"></div>
        <p class="state" id="preview-status" aria-live="polite"></p>
        <div class="btn-row" id="whatif-actions" hidden>
          <button class="btn btn-sm btn-primary" type="button" id="save-run">Save and run again</button>
          <button class="btn btn-sm" type="button" id="reset">Back to saved run</button>
        </div>
      </div>
    </section>

    <section class="panel ticked" aria-labelledby="p-cash">
      <div class="panel-head"><span class="panel-id">I-02</span><h2 id="p-cash">Cash position, month by month</h2>
        <span class="aside">dashed: your investment · red: ₹0</span></div>
      <div class="chart" id="cash-chart"></div>
      <div class="inspect">
        <label for="inspect-month" id="inspect-label">Month</label>
        <input type="range" id="inspect-month" min="1" max="24" value="24" step="1">
        <ul id="inspect-values" aria-live="polite"></ul>
      </div>
      <table class="sr-only" id="cash-table"></table>
    </section>

    <section class="panel ticked readout-panel" aria-labelledby="p-read">
      <div class="panel-head"><span class="panel-id">I-03</span><h2 id="p-read">Expected case</h2></div>
      <div class="readout" id="readout" aria-live="polite"></div>
      <div class="honesty" id="honesty" style="margin: var(--s3)"></div>
      <p class="panel-foot" id="warnings"></p>
    </section>
  </div>

  <div class="cols-2" style="margin-top: var(--s3)">
    <section class="panel ticked" aria-labelledby="p-sens">
      <div class="panel-head"><span class="panel-id">I-04</span><h2 id="p-sens">Which assumption matters most</h2>
        <span class="aside">one input at a time</span></div>
      <div class="chart" id="tornado"></div>
      <p class="panel-foot" id="tornado-note"></p>
    </section>
    <section class="panel ticked" aria-labelledby="p-cases">
      <div class="panel-head"><span class="panel-id">I-05</span><h2 id="p-cases">Seven cases</h2>
        <span class="aside">select one to highlight it</span></div>
      <div class="table-scroll"><table class="ledger" id="cases"></table></div>
      <p class="panel-foot">Case sizes are illustrative defaults, not market research. Price and demand move independently in this model.</p>
    </section>
  </div>

  <div class="cols-2" style="margin-top: var(--s3)">
    {% include "simulations/_analysis.html" with panel_id="I-06" %}
    {% include "simulations/_decision.html" with panel_id="I-07" %}
  </div>
</div>
{{ page_data|json_script:"page-data" }}
{% endblock %}
{% block scripts %}
<script type="module" src="{% static 'js/ai-actions.js' %}"></script>
<script type="module" src="{% static 'js/bench/main.js' %}"></script>
{% endblock %}
```

### 3. `_analysis.html`

<!-- source: templates/simulations/_analysis.html:1-29 -->
```html
{% load warroom %}
{# Gemini's reading of the SAVED run. Always labelled; flagged numbers listed. #}
<section class="panel ticked" id="analyst" aria-labelledby="p-ai">
  <div class="panel-head"><span class="panel-id">{{ panel_id }}</span><h2 id="p-ai">Analyst reading</h2>
    <span class="aside">explains the saved run, not unsaved slider changes</span></div>
  {% if analysis %}
    {% with o=analysis.output %}
    <div class="panel-body ai-block" style="margin: var(--s3)">
      <span class="ai-label">AI analysis</span><span class="meta">{{ analysis.model_name }} · prompt {{ analysis.prompt_version }} · {{ analysis.created_at|date:"d M, H:i" }} UTC</span>
      <h3>{{ o.headline }}</h3>
      <p>{{ o.what_happened }}</p>
      {% if o.trade_offs %}<h4>Trade-offs</h4><ul>{% for t in o.trade_offs %}<li>{{ t }}</li>{% endfor %}</ul>{% endif %}
      {% if o.risks %}<h4>Risks</h4><ul>{% for t in o.risks %}<li>{{ t }}</li>{% endfor %}</ul>{% endif %}
      {% if o.recommendations %}<h4>Suggestions</h4><ul>{% for r in o.recommendations %}<li>{{ r.action }} <span class="unit">({{ r.confidence }} confidence)</span></li>{% endfor %}</ul>{% endif %}
      {% if o.assumptions_to_check %}<h4>Check these assumptions</h4><ul>{% for a in o.assumptions_to_check %}<li>{{ a }}</li>{% endfor %}</ul>{% endif %}
      {% if analysis.flagged_numbers %}
        <div class="flagged" role="note"><strong>{{ analysis.flagged_numbers|length }} number(s) above are not from the simulation:</strong>
          {% for f in analysis.flagged_numbers %}<span class="mono">{{ f.literal }}</span>{% if not forloop.last %}, {% endif %}{% endfor %}. Treat them as unverified.</div>
      {% endif %}
    </div>
    {% endwith %}
  {% else %}
    <p class="state">No reading yet. The analyst explains what the engine calculated in plain language. It can't change the numbers, and any figure it writes that isn't in the run is flagged.</p>
  {% endif %}
  <div class="panel-foot btn-row">
    <button class="btn btn-sm" type="button" data-ai-action="{% url 'api:run-analysis' run.pk %}" data-status="ai-status" data-anchor="analyst" data-busy="Asking the analyst. Usually 5–10 seconds.">{% if analysis %}Ask again{% else %}Ask the analyst{% endif %}</button>
    <span id="ai-status"></span>
  </div>
</section>
```

### 4. `_decision.html`

<!-- source: templates/simulations/_decision.html:1-15 -->
```html
{# Record a human decision from this run. It starts as "proposed"; sign-off happens on the brief. #}
<section class="panel ticked" id="decide" aria-labelledby="p-decide">
  <div class="panel-head"><span class="panel-id">{{ panel_id }}</span><h2 id="p-decide">Record a decision</h2>
    <span class="aside">you decide; the AI only advises</span></div>
  <form class="panel-body" method="post" action="{% url 'decisions:create' run.pk %}">
    {% csrf_token %}
    <div class="form-grid">
      {% with field=decision_form.title %}{% include "accounts/_field.html" %}{% endwith %}
      {% with field=decision_form.chosen_strategy %}{% include "accounts/_field.html" %}{% endwith %}
      {% with field=decision_form.owner %}{% include "accounts/_field.html" %}{% endwith %}
    </div>
    {% with field=decision_form.rationale %}{% include "accounts/_field.html" %}{% endwith %}
    <button class="btn btn-primary" type="submit">Record as proposed</button>
  </form>
</section>
```

## Check

1. **The Idea Bench.** Open Chai Cart and click **Run** (or **Create and run** with a name
   like "First try"). You land on `/runs/<id>/`: the cash chart, seven cases, the
   "Expected case" readout and "Which assumption matters most". Then open **Tiffin Box
   Co.**'s run from the board, too.
2. **The Situation Board.** Open your Kirana Express run from lesson 6.9. The response
   console lists the three responses with their total impact (₹21,000, ₹20,420,
   ₹10,050), the system view draws the business, and the analyst reading from lesson 7.9
   is there, with its **AI analysis** label.
3. **Record a decision.** At the bottom, fill in "Record a decision" (title, chosen
   response, why) and click **Record as proposed**. You land on the brief, with "Decision
   recorded as proposed. Sign it off from the brief." Its **← Back** link now returns to
   the run.

The sliders and the 3D view are the JavaScript's job: the next four lessons read it.

## Line by line

### `board.html`

- **Lines 1–3** · Frame, filters, title.
- **Lines 4–8** · The `head` block: an **import map** (lesson 10.1). It tells the browser
  that `import ... from "three"` means our copy of Three.js. The comments say why it's
  self-hosted, and that only the 3D view loads it.
- **Lines 11–18** · Header: breadcrumbs, scenario name, template, a chip saying "Saved
  run" (the JavaScript changes it to "What-if" when sliders move), and the engine version
  and input fingerprint.
- **Lines 22–35** · **S-01 Response console:** an empty group for the strategy choices,
  an empty `controls` box for sliders, a status line, and hidden "Save as a new run" and
  "Back to saved run" buttons.
- **Lines 38–47** · **S-02 System view:** the `stage` box the 3D or 2D drawing goes in,
  described for screen readers (`role="img"` and `aria-label`), a legend, and a hidden
  table (`sr-only`) the JavaScript fills with each component's health.
- **Lines 50–53** · **S-03 Gauges** at the selected hour.
- **Lines 57–71** · **S-04 Timeline:** Play, a clock, the outage band, the hour slider
  (`scrubber`, hours 0–71) with a label for screen readers, tick marks, and a speed
  button.
- **Lines 75–81** · **S-05 Responses compared** (an empty table) with the engine's notes,
  and **S-06**, the analyst reading. `{% include ... with panel_id="S-06" %}` passes a
  value into the piece.
- **Lines 85–90** · **S-07 Committee** (the shared piece, or a link to convene it), and
  **S-08 Record a decision**.
- **Line 93** · `page_data` as a JSON script (lesson 10.1).
- **Lines 95–98** · The two scripts.

### `bench.html`

- **Lines 1–13** · Frame, title and the same header. No import map: no 3D here.
- **Lines 16–27** · **I-01 Assumption ledger:** a `controls` box for sliders, a status
  line, and the hidden save/reset buttons. "Nothing is saved until you choose to."
- **Lines 29–39** · **I-02 Cash chart:** a box for the chart, a month slider to inspect
  any month, a list of each case's cash at that month, and a hidden table twin.
- **Lines 41–46** · **I-03 Expected case:** the readout, the "honesty" box (your
  estimate against the funnel), and engine warnings.
- **Lines 50–61** · **I-04 Which assumption matters most** (the "tornado" chart), and
  **I-05 Seven cases**, with an honest footnote: case sizes are illustrative defaults.
- **Lines 64–66** · The analyst reading and the decision form.
- **Lines 69–74** · Page data and scripts.

### `_analysis.html`

- **Lines 1–2** · Filters, and a comment: always labelled, flags listed.
- **Lines 3–5** · The panel, with its id passed in, and the "saved run only" note.
- **Lines 6–21** · With an analysis: the label, model, prompt version and date; the
  headline and summary; trade-offs, risks, suggestions (each with its confidence), and
  assumptions to check; and the flagged-numbers box.
- **Lines 22–24** · Without: what the analyst does, and that it can't change numbers.
- **Lines 25–28** · "Ask the analyst" (or "Ask again"): an `ai-actions.js` button pointing
  at this run's analysis API.

### `_decision.html`

- **Line 1** · A comment: starts as proposed; sign-off happens on the brief.
- **Lines 2–4** · The panel: "you decide; the AI only advises".
- **Lines 5–14** · A normal form to `decisions:create` for this run: title, chosen
  response and owner in a grid, then "Why", then the button.

## If it didn't work

| You see | Fix |
|---|---|
| The page shows but every panel is empty | The JavaScript failed. Press F12 → Console and read the red line. |
| `Failed to resolve module specifier "three"` in the console | The import map (lines 4–8 of `board.html`) is missing or mistyped. |
| `TemplateDoesNotExist: simulations/_decision.html` | All four files go in `templates/simulations/`. |

## Quiz

1. What draws the strategies and gauges: the template or the JavaScript?
2. Why does the AI panel say it explains the saved run only?
3. What does the import map do?

---

**Next:** [10.9 · JavaScript helpers](09-javascript-helpers.md)

<details><summary>Quiz answers</summary>

1. The JavaScript, into the empty boxes the template leaves (`#strategies`, `#gauges`).
2. Slider changes aren't saved and are never sent to Gemini; only saved runs are
   explained.
3. It tells the browser where the module named `"three"` is (our self-hosted copy).

</details>
