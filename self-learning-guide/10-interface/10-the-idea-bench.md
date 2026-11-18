# 10.10 · The Idea Bench

**Time:** 60 minutes · **Before this:** [10.9](09-javascript-helpers.md). **Reading
lesson:** the files are already in `static/js/bench/`.

## Read

The Idea Bench answers "what if my price, costs or retention were different?" while you
drag a slider. Its JavaScript has one pattern you'll see again on the Situation Board:

```text
saved  = what the server sent (the saved run)          never changes
state  = what's on screen now (starts as a copy of saved)

slider moves ──► state.inputs changes ──► "What-if · not saved"
            └──► (after 220 ms of quiet) POST /api/v1/simulate/preview/
                     ──► state.cases = engine's answer ──► renderAll()

"Back to saved run" ──► state = saved again ──► renderAll()
"Save and run again" ──► PUT assumptions, POST run ──► open the new run's page
```

Every `render...` function **redraws from `state`**. Nothing is patched piece by piece,
so the screen can't drift out of step with the data.

The charts are hand-written **SVG** (the drawing language inside web pages: lines,
rectangles, text, with coordinates). No chart library: each chart is about 50 lines you
can read.

## Do (read)

### `static/js/bench/main.js`

#### Piece 1: setup (lines 1–20)

<!-- source: static/js/bench/main.js:1-20 -->
```js
// Idea Bench controller: sliders on the founder's assumptions, live results from the
// engine's preview endpoint, nothing calculated in the browser.

import { api, ApiError, debounce } from "../lib/api.js";
import { alignedStep, figure, money } from "../lib/format.js";
import { cashChart, tornadoChart } from "./charts.js";

const data = JSON.parse(document.getElementById("page-data").textContent);
const $ = (id) => document.getElementById(id);

const saved = {
  cases: data.run.results,
  summary: data.run.summary,
  warnings: data.run.warnings,
  inputs: Object.fromEntries(data.inputs.map((i) => [i.key, i.value])),
};
const state = { ...saved, inputs: { ...saved.inputs }, focus: "worst", month: null };
const investment = Number(data.run.input_snapshot.assumptions.initial_investment?.value || 0);
const isWhatIf = () => Object.keys(state.inputs).some((k) => state.inputs[k] !== saved.inputs[k]);
const expected = () => state.cases.find((c) => c.case_key === "expected");
```

#### Piece 2: drawing (lines 22–140)

<!-- source: static/js/bench/main.js:22-140 -->
```js
// ---------------------------------------------------------------------------------------
function renderChart() {
  const months = expected().timeline.length;
  const range = $("inspect-month");
  range.max = months;
  if (state.month === null) state.month = months;
  state.month = Math.min(state.month, months);
  range.value = state.month;
  cashChart($("cash-chart"), state.cases, { focus: state.focus, cursor: state.month, investment });
  $("inspect-label").textContent = `Month ${state.month}`;
  $("inspect-values").replaceChildren(...state.cases.map((c) => {
    const li = document.createElement("li");
    li.append(`${c.label}: `);
    const b = document.createElement("b");
    b.textContent = money(c.timeline[state.month - 1].cash);
    li.append(b);
    return li;
  }));
  // Table twin of the chart for screen readers.
  $("cash-table").innerHTML = `<caption>Cash at month ${state.month}</caption><tbody>${state.cases
    .map((c) => `<tr><th>${c.label}</th><td>${money(c.timeline[state.month - 1].cash)}</td></tr>`).join("")}</tbody>`;
}

const READOUT = [
  ["cac", "Cost to win a customer"],
  ["ltv_to_cac", "Lifetime value / CAC"],
  ["first_profitable_month", "First profitable month"],
  ["payback_month", "Cash back to investment"],
  ["lowest_cash", "Lowest cash"],
  ["funding_gap", "Extra funding needed"],
  ["cash_out_month", "Cash runs out"],
  ["ending_cash", "Cash at the end"],
];

function renderReadout() {
  const m = expected().metrics;
  $("readout").replaceChildren(...READOUT.map(([key, label]) => {
    const row = document.createElement("div");
    row.className = "row";
    const value = document.createElement("b");
    const metric = m[key];
    let text = figure(metric.value, metric.unit);
    if (metric.value === null && key === "first_profitable_month") text = "Not within horizon";
    if (metric.value === null && key === "cash_out_month") text = "Never";
    if (metric.unit === "month" && metric.value !== null) text = `Month ${metric.value}`;
    value.textContent = text;
    const bad = (key === "funding_gap" && Number(metric.value) > 0) || (key === "cash_out_month" && metric.value !== null);
    if (bad) value.className = "loss";
    row.append(label, value);
    return row;
  }));

  const check = state.summary.funnel_check;
  const box = $("honesty");
  if (!check) {
    box.className = "honesty ok";
    box.textContent = "Add your own expected orders per month to compare your estimate with what the funnel supports.";
    return;
  }
  const gap = Number(check.gap_pct.value);
  box.className = Math.abs(gap) > 25 ? "honesty" : "honesty ok";
  const verdict = gap > 0
    ? `: your estimate is ${figure(gap.toFixed(0), "%")} higher than the funnel supports.`
    : gap < -25
      ? ". Your estimate is cautious; check the conversion and retention inputs are realistic."
      : ".";
  box.textContent =
    `You expect ${figure(check.expected_orders.value, "orders/month")}. ` +
    `Your marketing spend and conversion support about ${figure(check.modelled_orders.value, "orders/month")} by month ${check.month}${verdict}`;
}

function renderCases() {
  const head = `<thead><tr><th>Case</th><th>What it changes</th><th class="num">Cash at the end</th>
    <th class="num">First profit</th><th class="num">Extra funding</th></tr></thead>`;
  const defs = state.summary.case_definitions || {};
  const body = state.cases.map((c) => {
    const m = c.metrics;
    const shocks = (defs[c.case_key] || []).join(", ").replaceAll("_", " ") || "your inputs as entered";
    return `<tr class="${c.case_key === state.focus ? "is-current" : ""}">
      <td class="row-title"><a href="#cash-chart" data-focus="${c.case_key}">${c.label}</a></td>
      <td><span class="unit">${shocks}</span></td>
      <td class="num">${money(m.ending_cash.value)}</td>
      <td class="num">${m.first_profitable_month.value ? `M${m.first_profitable_month.value}` : "none"}</td>
      <td class="num">${money(m.funding_gap.value)}</td></tr>`;
  }).join("");
  $("cases").innerHTML = head + `<tbody>${body}</tbody>`;
  $("cases").querySelectorAll("[data-focus]").forEach((a) => a.addEventListener("click", (event) => {
    event.preventDefault();
    state.focus = a.dataset.focus;
    renderChart();
    renderCases();
  }));
}

function renderSensitivity() {
  const rows = state.summary.sensitivity || [];
  tornadoChart($("tornado"), rows);
  const top = rows[0];
  $("tornado-note").textContent = top
    ? `${top.label} moves ending cash the most: ${money(top.ending_cash_low)} to ${money(top.ending_cash_high)} ` +
      `for a ±${state.summary.sensitivity_step_pct} % change. Get that number right first.`
    : "";
}

function renderMode() {
  const chip = $("mode-chip");
  chip.className = isWhatIf() ? "chip live" : "chip";
  chip.textContent = isWhatIf() ? "What-if · not saved" : chip.dataset.saved;
  $("whatif-actions").hidden = !isWhatIf();
  $("warnings").textContent = state.warnings.join(" ");
}

function renderAll() {
  renderChart();
  renderReadout();
  renderCases();
  renderSensitivity();
  renderMode();
}
```

#### Piece 3: sliders, preview, save (lines 142–243)

<!-- source: static/js/bench/main.js:142-243 -->
```js
// ---------------------------------------------------------------------------------------
// Sliders
// ---------------------------------------------------------------------------------------
function niceStep(value, max) {
  if (max <= 100) return 0.5;
  const raw = Math.max(1, value / 50);
  const p = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 5, 10].map((k) => k * p).find((s) => s >= raw);
}

const sliders = [];
for (const input of data.inputs) {
  const value = Number(input.value);
  const max = input.maximum !== null ? Number(input.maximum) : Math.max(10, value * 3);
  const step = alignedStep(value, niceStep(value, max));
  const id = `ctl-${input.key}`;
  const wrap = document.createElement("div");
  wrap.className = "control";
  wrap.innerHTML = `<div class="control-top"><label for="${id}"></label><output for="${id}"></output></div>
    <input type="range" id="${id}" min="0" max="${max}" step="${step}" value="${value}">
    <span class="saved"></span>`;
  wrap.querySelector("label").textContent = input.label;
  const slider = wrap.querySelector("input");
  const output = wrap.querySelector("output");
  const savedNote = wrap.querySelector(".saved");
  if (input.help) slider.title = input.help;
  const show = () => {
    output.textContent = figure(slider.value, input.unit);
    const changed = Number(slider.value) !== value;
    wrap.classList.toggle("changed", changed);
    savedNote.textContent = changed ? `saved: ${figure(value, input.unit)} (${input.source})` : "";
  };
  slider.addEventListener("input", () => {
    state.inputs[input.key] = String(Number(slider.value));
    show();
    renderMode();
    requestPreview();
  });
  show();
  $("controls").append(wrap);
  sliders.push({ key: input.key, slider, show });
}

let inFlight = null;
const requestPreview = debounce(async () => {
  inFlight?.abort();
  inFlight = new AbortController();
  const status = $("preview-status");
  status.className = "state busy";
  status.textContent = "Recalculating…";
  const changed = Object.fromEntries(Object.entries(state.inputs).filter(([k, v]) => v !== saved.inputs[k]));
  try {
    const result = await api(data.urls.preview, {
      method: "POST",
      signal: inFlight.signal,
      body: { business: data.business.id, template_key: data.template.key,
        parameters: data.run.input_snapshot.parameters, assumptions: changed },
    });
    Object.assign(state, { cases: result.cases, summary: result.summary, warnings: result.warnings });
    status.className = "state";
    status.textContent = isWhatIf() ? "Showing unsaved what-if results." : "";
    renderAll();
  } catch (error) {
    if (error.name === "AbortError") return;
    status.className = "state error";
    status.textContent = error instanceof ApiError ? error.message : "Couldn't reach the server.";
  }
}, 220);

$("reset").addEventListener("click", () => {
  Object.assign(state, { cases: saved.cases, summary: saved.summary, warnings: saved.warnings, inputs: { ...saved.inputs } });
  for (const s of sliders) { s.slider.value = saved.inputs[s.key]; s.show(); }
  $("preview-status").textContent = "";
  renderAll();
});

$("save-run").addEventListener("click", async () => {
  const changed = Object.entries(state.inputs).filter(([k, v]) => v !== saved.inputs[k]);
  if (!confirm("Save these values as the business's assumptions and run the stress test again? Past runs keep their values.")) return;
  const button = $("save-run");
  button.disabled = true;
  $("preview-status").className = "state busy";
  $("preview-status").textContent = "Saving and running…";
  try {
    await api(data.urls.assumptions, { method: "PUT", body: {
      assumptions: changed.map(([key, value]) => ({ key, value, source: "user", note: "Set on the Idea Bench" })) } });
    const run = await api(data.urls.scenario_run, { method: "POST" });
    location.href = data.urls.run_page.replace("RUN_ID", run.id);
  } catch (error) {
    button.disabled = false;
    $("preview-status").className = "state error";
    $("preview-status").textContent = error.message;
  }
});

$("inspect-month").addEventListener("input", (event) => {
  state.month = Number(event.target.value);
  renderChart();
});

$("mode-chip").dataset.saved = $("mode-chip").textContent;
renderAll();
```

### `static/js/bench/charts.js`

<!-- source: static/js/bench/charts.js:1-106 -->
```js
// Two small hand-written SVG charts. No chart library: each is ~80 lines a student can read.

import { figure, money, moneyShort } from "../lib/format.js";

const NS = "http://www.w3.org/2000/svg";
const el = (name, attrs = {}, text) => {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) if (v !== undefined) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
};

// Round tick values (₹10L, ₹20L... not ₹37.7L) that cover [lo, hi] in about `count` steps.
function niceTicks(lo, hi, count) {
  const raw = (hi - lo) / count;
  const power = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((k) => k * power).find((s) => s >= raw);
  const ticks = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push(v);
  return ticks;
}

// ---------------------------------------------------------------------------------------
// Cash position over time, one line per case. Expected is heavy; the focused case is amber.
// ---------------------------------------------------------------------------------------
export function cashChart(container, cases, { focus, cursor, investment }) {
  const W = 760, H = 330, m = { top: 16, right: 150, bottom: 30, left: 64 };
  const months = cases[0].timeline.length;
  const values = cases.flatMap((c) => c.timeline.map((r) => r.cash)).concat([0, investment]);
  const lo = Math.min(...values), hi = Math.max(...values);
  const pad = (hi - lo) * 0.06 || 1;
  const yMin = lo - pad, yMax = hi + pad;
  const x = (month) => m.left + ((month - 1) / Math.max(1, months - 1)) * (W - m.left - m.right);
  const y = (cash) => m.top + (1 - (cash - yMin) / (yMax - yMin)) * (H - m.top - m.bottom);

  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "Cash at the end of each month for every case. A table version follows." });

  const grid = el("g", { class: "grid" });
  for (const v of niceTicks(yMin, yMax, 5)) {
    grid.append(el("line", { x1: m.left, x2: W - m.right, y1: y(v), y2: y(v), opacity: 0.4 }));
    grid.append(el("text", { x: m.left - 8, y: y(v) + 4, "text-anchor": "end" }, moneyShort(v)));
  }
  for (let month = 1; month <= months; month += months > 24 ? 6 : 3) {
    grid.append(el("text", { x: x(month), y: H - 8, "text-anchor": "middle" }, `M${month}`));
  }
  svg.append(grid);

  // Zero cash is where the business can't pay its bills: marked in the alarm colour.
  svg.append(el("line", { class: "zero", x1: m.left, x2: W - m.right, y1: y(0), y2: y(0) }));
  // Label sits just inside the plot's left edge, where it can't collide with case labels.
  svg.append(el("text", { x: m.left + 6, y: y(0) - 5, fill: "var(--fault)" }, "₹0 cash"));
  svg.append(el("line", { class: "invest", x1: m.left, x2: W - m.right, y1: y(investment), y2: y(investment) }));

  // Draw others first so the expected and focused lines sit on top.
  const order = [...cases].sort((a, b) => rank(a) - rank(b));
  function rank(c) { return c.case_key === "expected" ? 2 : c.case_key === focus ? 1 : 0; }
  for (const c of order) {
    const d = c.timeline.map((r, i) => `${i ? "L" : "M"}${x(r.month).toFixed(1)},${y(r.cash).toFixed(1)}`).join("");
    const cls = c.case_key === "expected" ? "series expected" : c.case_key === focus ? "series focus" : "series";
    svg.append(el("path", { d, class: cls }));
  }

  // End labels, nudged apart so they never overlap.
  const ends = cases.map((c) => ({ c, y: y(c.timeline.at(-1).cash) })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + 13);
  for (const { c, y: ly } of ends) {
    const cls = c.case_key === "expected" ? "end-label expected" : "end-label";
    svg.append(el("text", { x: W - m.right + 6, y: ly + 4, class: cls,
      fill: c.case_key === focus && c.case_key !== "expected" ? "var(--signal)" : undefined }, c.label));
  }

  if (cursor) svg.append(el("line", { class: "cursor", x1: x(cursor), x2: x(cursor), y1: m.top, y2: H - m.bottom }));
  container.replaceChildren(svg);
}

// ---------------------------------------------------------------------------------------
// Tornado: how far ending cash moves when ONE input moves down/up by the step.
// ---------------------------------------------------------------------------------------
export function tornadoChart(container, rows) {
  const W = 760, rowH = 30, m = { top: 22, right: 110, bottom: 8, left: 230 };
  const H = m.top + rows.length * rowH + m.bottom;
  const base = Number(rows[0]?.ending_cash_base ?? 0);
  const reach = Math.max(1, ...rows.flatMap((r) => [Math.abs(r.ending_cash_low - base), Math.abs(r.ending_cash_high - base)]));
  const mid = m.left + (W - m.left - m.right) / 2;
  const scale = (W - m.left - m.right) / 2 / reach;

  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "How much ending cash moves when each input changes on its own. A table version follows." });
  svg.append(el("text", { x: mid, y: 12, "text-anchor": "middle" }, `Ending cash as entered: ${money(base)}`));
  rows.forEach((r, i) => {
    const top = m.top + i * rowH;
    svg.append(el("text", { x: m.left - 10, y: top + 18, "text-anchor": "end", fill: "var(--bone)" }, r.label));
    for (const [value, input, down] of [[r.ending_cash_low, r.low_value, true], [r.ending_cash_high, r.high_value, false]]) {
      const delta = Number(value) - base;
      const x0 = delta < 0 ? mid + delta * scale : mid;
      svg.append(el("rect", { x: x0, y: top + 6, width: Math.max(1, Math.abs(delta) * scale), height: rowH - 12,
        class: down ? "tornado-bar down" : "tornado-bar" }, undefined));
      const labelX = delta < 0 ? x0 - 6 : mid + Math.abs(delta) * scale + 6;
      svg.append(el("text", { x: labelX, y: top + 19, "text-anchor": delta < 0 ? "end" : "start" },
        `${delta >= 0 ? "+" : ""}${moneyShort(delta)} at ${figure(input, r.unit)}`));
    }
  });
  svg.append(el("line", { class: "tornado-base", x1: mid, x2: mid, y1: m.top, y2: H - m.bottom }));
  container.replaceChildren(svg);
}
```

## Check

Open **Tiffin Box Co.**'s run (from the board). On our test, the "Expected case" readout
said:

```text
Cost to win a customer      ₹409.09/customer
Lifetime value / CAC        6.80×
First profitable month      Month 3
Cash back to investment     Month 5
Lowest cash                 ₹22,39,066
Extra funding needed        ₹0
Cash runs out               Never
Cash at the end             ₹1,00,78,350
```

and the tornado note: "Monthly customer retention moves ending cash the most: ₹64,19,163
to ₹1,62,76,155 for a ±10 % change. Get that number right first."

1. **Drag "Average order value"** from ₹180 to about ₹200. Watch: "Recalculating…" for a
   moment, then the chip says **What-if · not saved**, the slider shows "saved: ₹180/order
   (user)" under it, and "Cash at the end" jumps (to ₹1,49,89,630 at exactly ₹200).
   Open the Network tab (F12): each pause sent one `preview/` request, not one per pixel.
2. **Click "Back to saved run".** Everything returns to the saved numbers.
3. **Click a case's name** in "Seven cases" (say "Reduced demand"): its line in the cash
   chart turns amber.
4. **Drag the month slider** under the chart: the list shows every case's cash at that
   month, and a cursor line moves on the chart.

(Don't click "Save and run again" unless you want to change Tiffin's saved assumptions:
it asks first, then saves the slider values as "user" inputs and makes a new run.)

## Line by line

### `main.js`, piece 1: setup

- **Lines 1–2** · Comment: sliders in, engine results out, nothing calculated here.
- **Lines 4–6** · Imports from lesson 10.9 and the charts file.
- **Line 8** · Read `page-data` (lesson 10.1).
- **Line 9** · `$("id")`: a short name for `document.getElementById("id")`.
- **Lines 11–16** · `saved`: the run's cases, summary, warnings, and each slider input's
  saved value (`Object.fromEntries` turns `[[key, value], ...]` into an object).
- **Line 17** · `state`: a **copy** of `saved` (with its own copy of `inputs`, so changing
  one doesn't change the other), plus which case is focused (worst first) and which month
  to inspect.
- **Line 18** · The initial investment, for the dashed line on the chart.
  `?.value || 0`: zero if there isn't one.
- **Line 19** · `isWhatIf()`: is any input different from its saved value?
- **Line 20** · `expected()`: the "expected" case.

### Piece 2: drawing

- **Lines 23–43** · `renderChart()`: set the month slider's range (24 months, say), keep
  the inspected month in range, draw the cash chart, and fill the "Month 12" list with
  each case's cash. Lines 41–42 fill the hidden table twin for screen readers (only our
  own labels and formatted numbers go in, so `innerHTML` is safe here).
- **Lines 45–54** · `READOUT`: the eight readout rows, metric key and label.
- **Lines 56–72** · `renderReadout()`: one row per metric. Missing values get honest
  words ("Not within horizon", "Never"); months show as "Month 5"; a funding gap or a
  cash-out month is coloured as a loss.
- **Lines 74–90** · The "honesty" box. No estimate of your own? Ask for one. Otherwise
  compare: if your expected orders are more than 25 % above what the funnel supports, the
  box warns; far below, it says you're cautious. The numbers in the sentence come from
  the engine's `funnel_check`.
- **Lines 93–114** · `renderCases()`: the seven-case table. Each row: the case name as a
  link, what it changes ("conversion rate, cost per visit", from the engine's
  `case_definitions`), cash at the end, first profitable month, extra funding. Clicking a
  name focuses that case and redraws. `event.preventDefault()` stops the link jumping.
- **Lines 116–124** · `renderSensitivity()`: the tornado chart, and a sentence about the
  input that matters most (the engine sorted them, so it's `rows[0]`).
- **Lines 126–132** · `renderMode()`: the chip ("What-if · not saved" or the saved
  text), show or hide the save/reset buttons, and the engine's warnings.
- **Lines 134–140** · `renderAll()`: redraw everything from `state`.

### Piece 3: sliders, preview, save

- **Lines 145–150** · `niceStep(value, max)`: a sensible slider step. Small ranges: 0.5.
  Otherwise about a fiftieth of the value, rounded to a "nice" 1, 2, 5 or 10 times a power
  of ten (₹180 → step 5; ₹2,60,000 → 10,000).
- **Lines 152–183** · Build one slider per input:
  - **Lines 154–156** · Its value, its maximum (the catalogue's, or three times the
    value), and a step the saved value sits on exactly (lesson 10.9).
  - **Lines 158–162** · A box with a label, an `<output>` showing the value, the range
    slider, and a "saved" note.
  - **Line 163** · The label goes in with `textContent` (safe text).
  - **Lines 168–173** · `show()`: write the formatted value; if it differs from the
    saved one, mark the control as changed and show "saved: ₹180/order (user)".
  - **Lines 174–179** · On every movement: store the new value as text, update the
    control and the chip, and **ask for a preview** (debounced).
- **Lines 185–209** · `requestPreview`, debounced by 220 ms:
  - **Lines 187–188** · Cancel the previous request if it's still waiting (its answer
    would be out of date), and make a new `AbortController` to be able to cancel this
    one.
  - **Lines 189–191** · "Recalculating…".
  - **Line 192** · Only the inputs that **changed**.
  - **Lines 194–199** · POST to the preview endpoint (Part 6): this business, this
    template, the run's own parameters, and the changed inputs.
  - **Lines 200–203** · Put the engine's answer into `state` and redraw.
  - **Lines 204–208** · A cancelled request: ignore it. Any other error: show it.
- **Lines 211–216** · "Back to saved run": copy `saved` back into `state`, move every
  slider back, redraw.
- **Lines 218–235** · "Save and run again": ask first (`confirm`), then PUT the changed
  inputs as **user** assumptions with a note, POST a new run of the scenario, and open
  the new run's page (the `RUN_ID` trick from lesson 10.4).
- **Lines 237–240** · The month slider redraws the chart.
- **Lines 242–243** · Remember the chip's saved text, and draw everything once.

### `charts.js`

- **Line 1** · No chart library.
- **Line 3** · Formatters.
- **Lines 5–11** · `el(name, attrs, text)`: make an SVG element. SVG elements must be
  created with their "namespace" (`createElementNS`), unlike normal HTML ones.
- **Lines 13–21** · `niceTicks(lo, hi, count)`: round axis values (₹10L, ₹20L... not
  ₹37.7L), the same "nice number" idea as `niceStep`.
- **Lines 26–75** · `cashChart(container, cases, {focus, cursor, investment})`:
  - **Line 27** · Drawing size and margins (room on the right for case names).
  - **Lines 28–32** · The lowest and highest cash across every case (and ₹0 and the
    investment, which must be visible), with a little padding.
  - **Lines 33–34** · `x(month)` and `y(cash)`: turn a month and an amount into drawing
    coordinates. SVG's y grows **downwards**, hence `1 - ...`.
  - **Lines 36–37** · The SVG, described for screen readers.
  - **Lines 39–47** · Grid lines with money labels, and month labels along the bottom.
  - **Lines 49–53** · The ₹0 line in the alarm colour (labelled "₹0 cash"), and the
    dashed investment line.
  - **Lines 55–62** · One path per case. A path is a string like `M10,20L30,40L50,35`:
    **M**ove to the first point, then **L**ine to each next one. Drawn in an order that
    puts "expected" and the focused case on top.
  - **Lines 64–71** · Case names at the right end of each line, pushed apart by at least
    13 units so they never overlap.
  - **Lines 73–74** · The inspect cursor, then swap the new drawing in.
- **Lines 80–106** · `tornadoChart(container, rows)`: for each input, two bars from the
  middle: how far ending cash moves when that input goes **down** (left) or **up**
  (right) by the step, each labelled "+₹48L at ₹198/order". The biggest bar sets the
  scale. The middle line is ending cash as entered.

## If it didn't work

| You see | Fix |
|---|---|
| A red error in the status line: `Couldn't reach the server.` | Is `runserver` still running? |
| Sliders move but nothing changes | F12 → Network: is there a `preview/` request? Its response shows the API's error. |
| The chart is blank | F12 → Console. A typo in `bench.html`'s ids (`cash-chart`) is the usual cause. |

## Quiz

1. What's the difference between `saved` and `state`?
2. You drag a slider for two seconds. Roughly how many preview requests are sent?
3. Why does the code cancel the previous request before sending a new one?

---

**Next:** [10.11 · The Situation Board](11-the-situation-board.md)

<details><summary>Quiz answers</summary>

1. `saved` is the run as stored, and never changes; `state` is what's on screen, changed
   by sliders and previews.
2. Usually one: the debounce waits for 220 ms of quiet. If you pause along the way, one
   per pause.
3. An older answer arriving late would overwrite the newer one with out-of-date numbers.

</details>
