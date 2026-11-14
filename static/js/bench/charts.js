// Two small hand-written SVG charts. No chart library: each is ~80 lines a student can read.

import { figure, money, moneyShort } from "../lib/format.js";

const NS = "http://www.w3.org/2000/svg";
const el = (name, attrs = {}, text) => {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) if (v !== undefined) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
};

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
  for (let i = 0; i <= 4; i++) {
    const v = yMin + ((yMax - yMin) * i) / 4;
    grid.append(el("line", { x1: m.left, x2: W - m.right, y1: y(v), y2: y(v), opacity: 0.4 }));
    grid.append(el("text", { x: m.left - 8, y: y(v) + 4, "text-anchor": "end" }, moneyShort(v)));
  }
  for (let month = 1; month <= months; month += months > 24 ? 6 : 3) {
    grid.append(el("text", { x: x(month), y: H - 8, "text-anchor": "middle" }, `M${month}`));
  }
  svg.append(grid);

  // Zero cash is where the business can't pay its bills: marked in the alarm colour.
  svg.append(el("line", { class: "zero", x1: m.left, x2: W - m.right, y1: y(0), y2: y(0) }));
  svg.append(el("text", { x: W - m.right + 6, y: y(0) + 4, fill: "var(--fault)" }, "₹0 cash"));
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
