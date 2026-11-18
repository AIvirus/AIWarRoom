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

  const { health, flows } = healthAt(row, topology);
  const notes = knockOnAt(rows, topology, data.template.loss_mode, health);
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
$("speed").addEventListener("click", () => {
  state.speed = state.speed === 1 ? 4 : 1;
  $("speed").textContent = `${state.speed}×`;
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
