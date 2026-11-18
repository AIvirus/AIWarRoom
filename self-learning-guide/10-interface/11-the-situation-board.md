# 10.11 · The Situation Board

**Time:** 60 minutes · **Before this:** [10.10](10-the-idea-bench.md). **Reading
lesson:** the file is `static/js/board/main.js`.

## 📖 Read

The Situation Board uses the same `saved` / `state` / preview pattern as the Idea Bench.
Three things are new:

1. **Strategies.** You pick which response to show (wait, backup, queue and retry), and
   the gauges, timeline and system view follow it.
2. **Time.** An outage run has an hour-by-hour timeline (72 rows). A slider, a Play button
   and a speed menu move through the hours. At each hour the gauges show "so far"
   totals: these are **sums of the engine's hourly rows**, not new calculations.
3. **Two kinds of slider.** The outage's **parameters** (duration, start hour, backup
   speed...) belong to the scenario. The business **inputs** (recapture rate...) belong
   to the business. Saving a what-if saves each where it belongs: a PATCH to the scenario,
   a PUT to the assumptions (with a warning first), then a new run.

## ⌨️ Do (read)

### Piece 1: setup (lines 1–39)

<!-- source: static/js/board/main.js:1-39 -->
```js
// Situation Board controller.
//
// It draws what the engine returned: the saved run first, then preview results while the
// user moves sliders. It never calculates a business number itself; running totals are
// read from the timeline rows the engine produced.

import { api, ApiError, debounce, prefersReducedMotion } from "../lib/api.js";
import { alignedStep, clockLabel, figure, money } from "../lib/format.js";
import { createSchematic2D } from "./schematic2d.js";
import { buildTopology, healthAt, knockOnAt, stateOf } from "./topology.js";

const data = JSON.parse(document.getElementById("page-data").textContent);
const reducedMotion = prefersReducedMotion();
const $ = (id) => document.getElementById(id);

const saved = {
  cases: data.run.results,
  parameters: { ...data.run.input_snapshot.parameters },
  inputs: Object.fromEntries(data.inputs.map((i) => [i.key, i.value])),
  warnings: data.run.warnings,
  summary: data.run.summary,
};
const state = {
  cases: saved.cases,
  warnings: saved.warnings,
  summary: saved.summary,
  parameters: { ...saved.parameters },
  inputs: { ...saved.inputs },
  strategy: saved.cases.find((c) => c.case_key === "wait")?.case_key || saved.cases[0].case_key,
  hour: 0,
  playing: false,
  speed: 1,
};

const currentCase = () => state.cases.find((c) => c.case_key === state.strategy);
const horizon = () => currentCase().timeline.length;
const isWhatIf = () =>
  Object.keys(state.parameters).some((k) => state.parameters[k] !== saved.parameters[k]) ||
  Object.keys(state.inputs).some((k) => state.inputs[k] !== saved.inputs[k]);
```

### Piece 2: the system view, 3D or 2D (lines 41–59)

<!-- source: static/js/board/main.js:41-59 -->
```js
// ---------------------------------------------------------------------------------------
// System view: 3D when WebGL works, otherwise (or with ?view=2d) the SVG schematic.
// ---------------------------------------------------------------------------------------
const topology = buildTopology(data.run.input_snapshot.components, data.template.component_kind);
let view;

async function createView() {
  const stage = $("stage");
  const force2d = new URLSearchParams(location.search).get("view") === "2d";
  if (!force2d) {
    try {
      const { createScene3D, webglAvailable } = await import("./scene3d.js");
      if (webglAvailable()) return createScene3D(stage, topology, { reducedMotion });
    } catch (error) {
      console.warn("3D view unavailable, using the 2D schematic.", error);
    }
  }
  return createSchematic2D(stage, topology, { reducedMotion });
}
```

### Piece 3: drawing (lines 61–189)

<!-- source: static/js/board/main.js:61-188 -->
```js
// ---------------------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------------------
function renderStrategies() {
  const box = $("strategies");
  box.querySelectorAll("label").forEach((n) => n.remove());
  for (const c of state.cases) {
    const label = document.createElement("label");
    label.className = "strategy";
    label.innerHTML = `<input type="radio" name="strategy" value="${c.case_key}"><span></span><span class="figure"></span>`;
    label.querySelector("span").textContent = c.label;
    label.querySelector(".figure").textContent = money(c.metrics.total_impact.value);
    const input = label.querySelector("input");
    input.checked = c.case_key === state.strategy;
    input.addEventListener("change", () => { state.strategy = c.case_key; renderAll(); });
    box.append(label);
  }
}

function gauge(label, value, total, { loss = false, ratio = null } = {}) {
  const share = ratio ?? (Number(total) > 0 ? Math.min(1, Number(value) / Number(total)) : 0);
  return `<div class="gauge"><span class="label">${label}</span>
    <div class="value${loss && Number(value) > 0 ? " loss" : ""}">${value}</div>
    ${total !== null ? `<span class="of">of ${total} by the end</span>` : ""}
    <div class="meter${loss ? " loss" : ""}"><i style="width:${(share * 100).toFixed(1)}%"></i></div></div>`;
}

function renderHour() {
  const c = currentCase();
  const rows = c.timeline.slice(0, state.hour + 1);
  const row = rows[rows.length - 1];
  const m = c.metrics;
  const lostSoFar = rows.reduce((sum, r) => sum + r.lost, 0);
  const costSoFar = rows.reduce((sum, r) => sum + r.cost, 0);
  const through = row.demand > 0 ? row.served / row.demand : 1;

  $("gauge-hour").textContent = `T+${String(state.hour).padStart(2, "0")}`;
  $("clock").innerHTML = `T+${String(state.hour).padStart(2, "0")}<small>${clockLabel(row.clock)} · ${c.label}</small>`;
  $("scrubber").value = state.hour;

  const fulfilment = data.template.loss_mode === "fulfilment";
  $("gauges").innerHTML = [
    gauge("Impact so far", money(row.impact_cum), money(m.total_impact.value), {
      loss: true, ratio: Number(m.total_impact.value) ? row.impact_cum / Number(m.total_impact.value) : 0 }),
    gauge("Orders lost so far", figure(lostSoFar.toFixed(1), "orders"), figure(m.lost_orders.value, "orders"), {
      loss: true, ratio: Number(m.lost_orders.value) ? lostSoFar / Number(m.lost_orders.value) : 0 }),
    gauge(fulfilment ? "Backlog now" : "Orders getting through now",
      fulfilment ? figure(row.backlog.toFixed(0), "orders") : `${Math.round(through * 100)} %`,
      null, { ratio: fulfilment ? Math.min(1, row.backlog / Math.max(1, Number(m.peak_backlog?.value || 1))) : through }),
    gauge("Response cost so far", money(costSoFar), money(m.mitigation_cost.value), {
      ratio: Number(m.mitigation_cost.value) ? costSoFar / Number(m.mitigation_cost.value) : 0 }),
  ].join("");

  const { health, flows, notes } = knockOnAt(rows, topology, data.template.loss_mode, healthAt(row, topology));
  view?.update({ health, flows, notes });
  // Component names are user input: build with text nodes, never innerHTML.
  $("sr-health").replaceChildren(...topology.nodes.map((n) => {
    const tr = document.createElement("tr");
    const th = document.createElement("th");
    const td = document.createElement("td");
    th.textContent = n.label;
    const note = notes[n.id];
    td.textContent = note
      ? `${note.state}, ${note.text}`
      : `${stateOf(health[n.id])}, ${Math.round(health[n.id] * 100)} %`;
    tr.append(th, td);
    return tr;
  }));
}

function renderTimeline() {
  const hours = horizon();
  const scrubber = $("scrubber");
  scrubber.max = hours - 1;
  const outage = Number(state.parameters.outage_hours);
  $("outage-band").style.width = `${Math.min(100, (outage / (hours - 1)) * 100)}%`;
  $("outage-band").title = `Outage: ${outage} hours`;
  const ticks = [];
  for (let h = 0; h < hours; h += 12) ticks.push(`<span>T+${h} ${clockLabel(currentCase().timeline[h].clock)}</span>`);
  $("ticks").innerHTML = ticks.join("");
}

function renderComparison() {
  const maxImpact = Math.max(...state.cases.map((c) => Number(c.metrics.total_impact.value)), 1);
  const head = `<thead><tr><th>Response</th><th>Total impact</th><th class="num">Response cost</th>
    <th class="num">Back to normal</th><th class="num">Orders lost</th></tr></thead>`;
  const body = state.cases.map((c) => {
    const m = c.metrics;
    const share = (Number(m.total_impact.value) / maxImpact) * 100;
    return `<tr data-case="${c.case_key}" class="${c.case_key === state.strategy ? "is-current" : ""}">
      <td class="row-title"><a href="#p-console" data-pick="${c.case_key}">${c.label}</a></td>
      <td><div class="bar-cell"><div class="bar loss"><i style="width:${share.toFixed(1)}%"></i></div>
        <span class="mono">${money(m.total_impact.value)}</span></div></td>
      <td class="num">${money(m.mitigation_cost.value)}</td>
      <td class="num">${figure(m.time_to_recovery.value, "hours")}</td>
      <td class="num">${figure(m.lost_orders.value, "orders")}</td></tr>`;
  }).join("");
  $("comparison").innerHTML = head + `<tbody>${body}</tbody>`;
  $("comparison").querySelectorAll("[data-pick]").forEach((link) =>
    link.addEventListener("click", (event) => {
      event.preventDefault();
      state.strategy = link.dataset.pick;
      renderAll();
    }),
  );
  const cmp = state.summary.comparison || {};
  const name = (key) => state.cases.find((c) => c.case_key === key)?.label || "n/a";
  $("engine-notes").textContent =
    `Lowest total impact: ${name(cmp.lowest_total_impact)}. Lowest response cost: ${name(cmp.lowest_response_cost)}. ` +
    `Fastest back to normal: ${name(cmp.fastest_recovery)}. ${state.warnings.join(" ")}`;
}

function renderMode() {
  const whatIf = isWhatIf();
  const chip = $("mode-chip");
  chip.className = whatIf ? "chip live" : "chip";
  chip.textContent = whatIf ? "What-if · not saved" : chip.dataset.saved;
  $("whatif-actions").hidden = !whatIf;
}

function renderAll() {
  state.hour = Math.min(state.hour, horizon() - 1);
  renderStrategies();
  renderTimeline();
  renderComparison();
  renderHour();
  renderMode();
}
```

### Piece 4: sliders, preview, save (lines 191–327)

<!-- source: static/js/board/main.js:190-326 -->
```js
// ---------------------------------------------------------------------------------------
// Sliders -> preview API
// ---------------------------------------------------------------------------------------
const PARAMETER_SLIDERS = {
  outage_hours: { step: 0.5 },
  start_hour: { step: 1 },
  backup_switch_hours: { step: 0.5, max: 12 },
  backup_capacity_per_hour: { step: 5 },
  retry_success_rate: { step: 1 },
};

function sliderSpec(spec, current, overrides) {
  const value = Number(current);
  const max = overrides.max ?? (spec.maximum !== null ? Number(spec.maximum) : Math.max(200, value * 4));
  const min = spec.minimum !== null ? Number(spec.minimum) : 0;
  const step = alignedStep(value, overrides.step ?? (max - min > 50 ? 1 : 0.5));
  return { min, max, step, value };
}

function addSlider(container, { key, label, unit, help }, range, savedValue, onChange) {
  const id = `ctl-${key}`;
  const wrap = document.createElement("div");
  wrap.className = "control";
  wrap.innerHTML = `<div class="control-top"><label for="${id}"></label><output for="${id}"></output></div>
    <input type="range" id="${id}" min="${range.min}" max="${range.max}" step="${range.step}" value="${range.value}">
    <span class="saved"></span>`;
  wrap.querySelector("label").textContent = label;
  const output = wrap.querySelector("output");
  const saved = wrap.querySelector(".saved");
  const input = wrap.querySelector("input");
  if (help) input.title = help;
  const show = () => {
    output.textContent = figure(input.value, unit);
    const changed = String(Number(input.value)) !== String(Number(savedValue));
    wrap.classList.toggle("changed", changed);
    saved.textContent = changed ? `saved: ${figure(savedValue, unit)}` : "";
  };
  input.addEventListener("input", () => { show(); onChange(key, String(Number(input.value))); });
  show();
  container.append(wrap);
  return { input, show };
}

const sliders = [];
function buildControls() {
  const box = $("controls");
  for (const spec of data.template.parameters) {
    if (!(spec.key in PARAMETER_SLIDERS)) continue;
    const range = sliderSpec(spec, saved.parameters[spec.key], PARAMETER_SLIDERS[spec.key]);
    sliders.push({ kind: "parameter", key: spec.key,
      ...addSlider(box, spec, range, saved.parameters[spec.key], onParameter) });
  }
  for (const input of data.inputs) {
    const range = sliderSpec(input, input.value, input.unit === "%" ? { step: 0.5 } : {});
    sliders.push({ kind: "input", key: input.key,
      ...addSlider(box, { ...input, label: `${input.label} (your input)` }, range, input.value, onInput) });
  }
}

let inFlight = null;
const requestPreview = debounce(async () => {
  inFlight?.abort(); // a newer slider position makes the older request irrelevant
  inFlight = new AbortController();
  const status = $("preview-status");
  status.className = "state busy";
  status.textContent = "Recalculating…";
  const changedInputs = Object.fromEntries(
    Object.entries(state.inputs).filter(([k, v]) => v !== saved.inputs[k]),
  );
  try {
    const result = await api(data.urls.preview, {
      method: "POST",
      signal: inFlight.signal,
      body: {
        business: data.business.id,
        template_key: data.template.key,
        parameters: state.parameters,
        assumptions: changedInputs,
      },
    });
    state.cases = result.cases;
    state.summary = result.summary;
    state.warnings = result.warnings;
    status.className = "state";
    status.textContent = isWhatIf() ? "Showing unsaved what-if results." : "";
    renderAll();
  } catch (error) {
    if (error.name === "AbortError") return;
    status.className = "state error";
    status.textContent = error instanceof ApiError ? error.message : "Couldn't reach the server.";
  }
}, 220);

function onParameter(key, value) { state.parameters[key] = value; renderMode(); requestPreview(); }
function onInput(key, value) { state.inputs[key] = value; renderMode(); requestPreview(); }

$("reset").addEventListener("click", () => {
  state.parameters = { ...saved.parameters };
  state.inputs = { ...saved.inputs };
  state.cases = saved.cases;
  state.summary = saved.summary;
  state.warnings = saved.warnings;
  for (const s of sliders) {
    s.input.value = s.kind === "parameter" ? saved.parameters[s.key] : saved.inputs[s.key];
    s.show();
  }
  $("preview-status").textContent = "";
  renderAll();
});

$("save-run").addEventListener("click", async () => {
  const changedInputs = Object.entries(state.inputs).filter(([k, v]) => v !== saved.inputs[k]);
  if (changedInputs.length && !confirm(
    "Saving also updates this business's saved assumptions " +
    `(${changedInputs.map(([k]) => k.replaceAll("_", " ")).join(", ")}). Past runs keep their values. Continue?`,
  )) return;
  const button = $("save-run");
  button.disabled = true;
  const status = $("preview-status");
  status.className = "state busy";
  status.textContent = "Saving and running…";
  try {
    await api(data.urls.scenario, { method: "PATCH", body: { parameters: state.parameters } });
    if (changedInputs.length) {
      await api(data.urls.assumptions, {
        method: "PUT",
        body: { assumptions: changedInputs.map(([key, value]) => ({ key, value, source: "user", note: "Set on the Situation Board" })) },
      });
    }
    const run = await api(data.urls.scenario_run, { method: "POST" });
    location.href = data.urls.run_page.replace("RUN_ID", run.id);
  } catch (error) {
    button.disabled = false;
    status.className = "state error";
    status.textContent = error.message;
  }
});
```

### Piece 5: playback and start (lines 329–365)

<!-- source: static/js/board/main.js:328-363 -->
```js
// ---------------------------------------------------------------------------------------
// Playback
// ---------------------------------------------------------------------------------------
let timer = null;
function setPlaying(on) {
  state.playing = on;
  $("play").textContent = on ? "Pause" : "Play";
  $("play").setAttribute("aria-pressed", String(on));
  clearInterval(timer);
  if (!on) return;
  if (state.hour >= horizon() - 1) state.hour = 0;
  timer = setInterval(() => {
    if (state.hour >= horizon() - 1) return setPlaying(false);
    state.hour += 1;
    renderHour();
  }, 400 / state.speed);
}
$("play").addEventListener("click", () => setPlaying(!state.playing));
$("speed").addEventListener("change", (event) => {
  state.speed = Number(event.target.value); // 0.25× = 1.6 s per hour, 4× = 0.1 s
  if (state.playing) setPlaying(true);
});
$("scrubber").addEventListener("input", (event) => {
  state.hour = Number(event.target.value);
  renderHour();
});

// ---------------------------------------------------------------------------------------
$("mode-chip").dataset.saved = $("mode-chip").textContent;
buildControls();
renderAll();
createView().then((created) => {
  view = created;
  $("view-kind").textContent = `${view.kind}${reducedMotion ? " · reduced motion" : ""}`;
  renderHour();
});
```

## ✅ Check

Open your Kirana Express run from lesson 6.9 (2-hour gateway outage).

1. **At T+0**, with "Wait for recovery" selected, the gauges read: impact so far
   **₹10,500** of ₹21,000; orders lost so far **70** of 140; orders getting through
   **0 %**; response cost ₹0. The system view's subtitle says **3D (WebGL)** (or "2D
   schematic" on a computer without WebGL), and the payment gateway is drawn as down.
2. **Drag the hour slider to T+1** (or click it and press →). Impact so far: ₹21,000.
   The 2-hour outage covers hours 0 and 1, so the impact stops growing after T+1.
3. **Pick "Queue and retry payments"** in the console. Every panel switches to that
   response.
4. **Press Play**, then pick another speed (try 0.25× to watch slowly, 4× to rush). Press
   Pause.
5. **Drag "Outage duration" to 4 hours.** "What-if · not saved", and the responses become
   about ₹42,000 / ₹30,260 / ₹20,100. Click **Save as a new run**: a new run's page opens,
   showing **exactly** those numbers, now saved. (The preview and the saved run come from
   the same engine, so they always agree.)
6. **Add `?view=2d`** to the address and press Enter: the system view becomes a flat
   drawing, with the same names and states.

## 🔍 Line by line

### Piece 1: setup

- **Lines 1–5** · Comment: draws what the engine returned; running totals are read from
  the engine's rows.
- **Lines 7–10** · Imports: helpers, formatters, the 2D view, and topology (lesson 10.12).
- **Lines 12–14** · Page data, reduced-motion setting, `$`.
- **Lines 16–22** · `saved`: cases, the scenario's parameters, the slider inputs' values,
  warnings, summary.
- **Lines 23–33** · `state`: copies of those, plus the chosen strategy (wait, if there is
  one), the hour, and playback settings.
- **Line 35** · `currentCase()`: the case being shown.
- **Line 36** · `horizon()`: how many hours its timeline has.
- **Lines 37–39** · `isWhatIf()`: any parameter **or** input changed?

### Piece 2: the system view

- **Line 44** · Build the topology once: the run's own components, and which kind fails.
- **Line 45** · `view` will hold the 3D or 2D drawing.
- **Lines 47–59** · `createView()`:
  - **Line 49** · `?view=2d` in the address forces the flat drawing.
  - **Lines 51–53** · Otherwise **load the 3D code only now** (`await import(...)`, a
    "dynamic import"): a page that can't use 3D never downloads Three.js. If WebGL works,
    make the 3D scene.
  - **Lines 54–56** · If anything fails, note it in the console and carry on.
  - **Line 58** · Fall back to the 2D schematic.

### Piece 3: drawing

- **Lines 64–78** · `renderStrategies()`: one radio button per case, labelled with its
  name and total impact. Choosing one changes `state.strategy` and redraws everything.
- **Lines 80–86** · `gauge(...)`: the HTML for one gauge: label, value, "of ₹21,000 by the
  end", and a meter bar whose width is the share so far. A `loss` gauge turns red when
  above zero.
- **Lines 88–129** · `renderHour()`: everything for the selected hour:
  - **Lines 90–91** · The timeline rows from hour 0 up to now, and the current one.
  - **Lines 93–94** · **Sums** of the engine's hourly `lost` and `cost` so far.
  - **Line 95** · Orders getting through now: served ÷ demand, from this hour's row.
  - **Lines 97–99** · The hour labels, the clock (with the time of day and response),
    and the slider's position.
  - **Lines 101–112** · The four gauges. For outages that delay deliveries
    (`fulfilment`), the third gauge is the backlog instead of "getting through".
  - **Lines 114–115** · Each component's health at this hour (from the engine's row),
    passed through `knockOnAt` (lesson 10.12), which adds notes for parts hurt by the
    outage and lowers the flows a payment outage cuts off → update the 3D or 2D view.
  - **Lines 117–128** · The hidden health table for screen readers, built with
    `textContent` because component names are typed by users. A part with a knock-on note
    reads it out ("affected, 1,153 parcels stuck") instead of its plain health.
- **Lines 131–141** · `renderTimeline()`: the slider's range, the red outage band's width
  (outage hours as a share of the timeline), and a tick label every 12 hours.
- **Lines 143–171** · `renderComparison()`: the responses table, each row with a red bar
  sized against the worst impact, cost, recovery time and orders lost. Clicking a name
  picks it. Then the engine's own comparison sentence ("Lowest total impact: Queue and
  retry payments...") and its warnings.
- **Lines 173–179** · `renderMode()`: the chip and the save/reset buttons.
- **Lines 181–188** · `renderAll()`: keep the hour within the (maybe shorter) new
  timeline, then redraw everything.

### Piece 4: sliders, preview, save

- **Lines 193–199** · Which parameters get sliders, with their step (and a maximum for
  the switch time).
- **Lines 201–207** · `sliderSpec(...)`: min, max and an aligned step for one slider,
  from the catalogue's limits or sensible defaults.
- **Lines 209–231** · `addSlider(...)`: the same control as the Idea Bench's (label,
  output, range, "saved:" note), returning the input and its `show` function.
- **Lines 233–247** · `buildControls()`: a slider for each listed parameter, then one for
  each business input, labelled "(your input)" so it's clear which ones belong to the
  business.
- **Lines 249–281** · `requestPreview`, debounced: the same as the Idea Bench's, but it
  sends **all** current parameters plus the changed inputs.
- **Lines 283–284** · What a parameter or input slider does when it moves.
- **Lines 286–298** · "Back to saved run".
- **Lines 300–326** · "Save as a new run":
  - **Lines 301–305** · If business inputs changed, warn that the business's saved
    assumptions will change too (naming them), and stop if the user says no.
  - **Line 312** · PATCH the scenario's parameters.
  - **Lines 313–318** · PUT the changed inputs, if any, as "user" values with a note.
  - **Lines 319–320** · Run it, and open the new run's page.

### Piece 5: playback and start

- **Lines 331–344** · `setPlaying(on)`: switch the button's text and `aria-pressed`
  (so screen readers know it's on), stop any timer, and if playing, start from the
  beginning when at the end. Every `400 / speed` milliseconds, move one hour; stop at the
  end.
- **Lines 345–349** · Play/Pause, and the speed menu (0.25× to 4×: at 0.25× each hour
  lasts 1.6 seconds, at 4× a tenth of a second). A new speed restarts the timer.
- **Lines 350–353** · The hour slider. (Arrow keys work on it too: that's built into
  range sliders.)
- **Lines 356–363** · Start: remember the chip's text, build the sliders, draw, then
  create the system view. When it's ready, say which kind it is and draw the hour on it.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| The subtitle says `2D schematic` without `?view=2d` | Your browser has WebGL turned off, or the console shows why 3D failed. The 2D view shows the same thing. |
| "Save as a new run" shows an error | Read it: usually a parameter out of range. The API's message is shown as-is. |

## ❓ Quiz

1. The "Impact so far" gauge: who calculated it?
2. Why is the 3D code loaded with `await import(...)` instead of at the top?
3. Saving a what-if that changed recapture rate: what three requests are sent?

---

**Next:** [10.12 · The system view](12-the-system-view.md)

<details><summary>Quiz answers</summary>

1. The engine: `impact_cum` is a field of its hourly rows. The page only formats it.
2. So Three.js is only downloaded when it can actually be used.
3. PATCH the scenario's parameters, PUT the assumptions, POST a new run.

</details>
