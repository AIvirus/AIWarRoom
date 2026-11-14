// The same system as a flat SVG schematic: used when WebGL isn't available, when the
// user asks for it (?view=2d), or as a lighter option on low-end machines. Same layout,
// same data, same update() call as the 3D view.

import { controlPoint, stateOf } from "./topology.js";

const NS = "http://www.w3.org/2000/svg";
const el = (name, attrs = {}) => {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
};

export function createSchematic2D(container, topology, { reducedMotion }) {
  // Isometric-style projection so the 2D view reads like the 3D one.
  const project = ({ x, z }) => ({ px: (x - z) * 46, py: (x + z) * 23 });
  const arcPoints = topology.flows.filter((f) => f[2]).map(([a, b, bend]) => {
    const from = topology.nodes.find((n) => n.id === a);
    const to = topology.nodes.find((n) => n.id === b);
    const c = controlPoint(from, to, bend);
    // The curve's midpoint is halfway between the chord's midpoint and the control point.
    return project({ x: (from.x + to.x) / 4 + c.x / 2, z: (from.z + to.z) / 4 + c.z / 2 });
  });
  const points = [...topology.nodes.map(project), ...arcPoints];
  const pad = 80;
  const minX = Math.min(...points.map((p) => p.px)) - pad;
  const minY = Math.min(...points.map((p) => p.py)) - pad;
  const width = Math.max(...points.map((p) => p.px)) - minX + pad;
  const height = Math.max(...points.map((p) => p.py)) - minY + pad;

  const svg = el("svg", { viewBox: `${minX} ${minY} ${width} ${height}`, "aria-hidden": "true" });
  svg.innerHTML = `
    <defs>
      <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="6" stroke="var(--fault)" stroke-width="2"/>
      </pattern>
    </defs>
    <style>
      .flow { stroke: var(--bone); stroke-width: 2; stroke-dasharray: 2 10; fill: none; }
      .flow.degraded { stroke: var(--signal); }
      .flow.moving { animation: march 1.2s linear infinite; }
      @keyframes march { to { stroke-dashoffset: -24; } }
      .rail { stroke: var(--dim); stroke-width: 1; opacity: .45; fill: none; }
      .tile { fill: var(--panel-2); stroke: var(--rule); }
      .tile.degraded { stroke: var(--signal); stroke-width: 2; }
      .tile.failed { fill: url(#hatch); stroke: var(--fault); stroke-width: 2; }
      .name { fill: var(--bone); font: 600 12px var(--font-ui); text-transform: uppercase; letter-spacing: .04em; }
      .value { fill: var(--dim); font: 11px var(--font-data); }
      .value.degraded { fill: var(--signal); } .value.failed { fill: var(--fault); }
    </style>`;

  const flows = topology.flows.map(([a, b, bend]) => {
    const fromNode = topology.nodes.find((n) => n.id === a);
    const toNode = topology.nodes.find((n) => n.id === b);
    const from = project(fromNode);
    const to = project(toNode);
    const c = project(controlPoint(fromNode, toNode, bend));
    const d = `M${from.px},${from.py} Q${c.px},${c.py} ${to.px},${to.py}`;
    svg.append(el("path", { d, class: "rail" }));
    const line = el("path", { d, class: "flow" });
    svg.append(line);
    return line;
  });

  const tiles = new Map();
  for (const node of topology.nodes) {
    const { px, py } = project(node);
    const tile = el("polygon", { points: `${px},${py - 22} ${px + 44},${py} ${px},${py + 22} ${px - 44},${py}`, class: "tile" });
    const name = el("text", { x: px, y: py - 30, "text-anchor": "middle", class: "name" });
    name.textContent = node.label;
    const value = el("text", { x: px, y: py + 4, "text-anchor": "middle", class: "value" });
    svg.append(tile, name, value);
    tiles.set(node.id, { tile, value });
  }
  container.append(svg);

  return {
    kind: "2D schematic",
    update({ health, flows: strengths }) {
      for (const [id, { tile, value }] of tiles) {
        const state = stateOf(health[id]);
        tile.setAttribute("class", `tile ${state}`);
        value.setAttribute("class", `value ${state}`);
        value.textContent = state === "failed" ? "DOWN" : `${Math.round(health[id] * 100)} %`;
      }
      strengths.forEach((s, i) => {
        const line = flows[i];
        // Flow strength shown three ways: opacity, dash density and colour.
        line.style.opacity = String(0.15 + 0.85 * s);
        line.style.strokeDasharray = `2 ${Math.round(6 + (1 - s) * 30)}`;
        line.setAttribute("class", `flow${s < 0.98 ? " degraded" : ""}${!reducedMotion && s > 0.02 ? " moving" : ""}`);
      });
    },
    dispose() { svg.remove(); },
  };
}
