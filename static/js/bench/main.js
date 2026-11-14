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
