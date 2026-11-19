# 10.12 · The system view

**Time:** 75 minutes · **Before this:** [10.11](11-the-situation-board.md). **Reading
lesson:** the files are in `static/js/board/`.

## Read

The system view draws the business as connected parts, customers → storefront → payment
→ revenue, and storefront → warehouse → courier → customers, and shows, hour by hour,
which parts are down and how much flow gets through.

Three files share the work:

| File | Job |
|---|---|
| `topology.js` | **Where** things are (a floor plan), **which** edges connect them, each part's **health** at an hour, and the **knock-on** notes for parts hurt by the outage, all read from the engine's rows. No drawing. |
| `schematic2d.js` | Draws it flat, with SVG. |
| `scene3d.js` | Draws it in 3D, with Three.js. |

Both drawings offer the **same** two functions, `update({health, flows, notes})` and `dispose()`
(the 2D drawing simply ignores `notes`).
`board/main.js` doesn't care which one it got. Programmers call this "the same
**interface**"; it's what makes the 2D fallback a one-line swap.

### 3D in five words

Three.js (and every 3D program) works with the same few things:

| Thing | Meaning |
|---|---|
| **Scene** | The world: everything to draw. |
| **Mesh** | One object = a **geometry** (its shape, e.g. a box) + a **material** (its colour and how light hits it). |
| **Light** | Without lights, most materials are black. We use soft light from everywhere (ambient) plus one "sun". |
| **Camera** | Where you look from. Ours is **orthographic**: far things aren't smaller, so it reads like a technical drawing. |
| **Renderer** | Turns scene + camera into pixels on a `<canvas>`, using the graphics card (WebGL). |

To animate, you change things and ask the renderer to draw again, about 60 times a
second, with `requestAnimationFrame`.

### What the picture means

- Each part is a **plinth** with a **column**. Column height = health (tall = normal, a
  flat stub = down). Colour = state: light (normal), amber (degraded), red (down).
- Small **blocks travel** along the edges: fewer blocks = fewer orders getting through.
- Health comes **only** from the engine's hourly row (`row.components`). A part the
  engine says nothing about is drawn as normal: the picture never invents a failure.

## Do (read)

### `static/js/board/topology.js`

<!-- source: static/js/board/topology.js:1-112 -->
```js
// The business drawn as a system: where each kind of component sits and how orders flow.
// Positions are on a floor grid (x across, z deep); both the 3D and 2D views use them.

export const LAYOUT = {
  customers: { x: 0, z: 0, label: "Customers" },
  storefront: { x: 2.6, z: 0, label: "Storefront" },
  payment: { x: 5.2, z: -1.7, label: "Payment gateway" },
  revenue: { x: 7.8, z: -1.7, label: "Revenue" },
  warehouse: { x: 5.2, z: 1.7, label: "Warehouse" },
  logistics: { x: 7.8, z: 1.7, label: "Courier" },
  supplier: { x: 0, z: 2.6, label: "Suppliers" },
};

// Orders move along these edges: browse -> pay -> revenue, and pick -> ship -> deliver.
// The third value bends an edge: deliveries return to customers as an arc around the
// front of the scene instead of cutting straight through the warehouse.
export const FLOWS = [
  ["customers", "storefront"],
  ["storefront", "payment"],
  ["payment", "revenue"],
  ["storefront", "warehouse"],
  ["supplier", "warehouse"],
  ["warehouse", "logistics"],
  ["logistics", "customers", 4.6],
];

// The control point of an edge's curve on the floor plane (straight edges: the midpoint).
export function controlPoint(from, to, bend = 0) {
  return { x: (from.x + to.x) / 2, z: (from.z + to.z) / 2 + bend };
}

export function buildTopology(components, failedKind) {
  const nodes = Object.entries(LAYOUT).map(([kind, place]) => {
    const own = components.filter((c) => c.kind === kind);
    return {
      id: kind,
      x: place.x,
      z: place.z,
      // Show the business's own names ("Razorpay (primary)") where it has them.
      label: own.length ? own.map((c) => c.name).join(" + ") : place.label,
      keys: own.map((c) => c.key),
    };
  });
  return { nodes, flows: FLOWS, failedKind };
}

// Health per node at one hour, ONLY from what the engine returned for that hour
// (row.components). Nodes the engine says nothing about are drawn as normal.
export function healthAt(row, topology) {
  const health = {};
  for (const node of topology.nodes) {
    const values = node.keys.map((k) => row.components?.[k]).filter((v) => v !== undefined);
    if (node.id === topology.failedKind && row.components?.[node.id] !== undefined) {
      values.push(row.components[node.id]); // generic node when no component was set up
    }
    health[node.id] = values.length ? Math.min(...values) : 1;
  }
  const flows = topology.flows.map(([a, b]) => Math.min(health[a], health[b]));
  // (A bent edge's third value is ignored here: health only depends on the endpoints.)
  return { health, flows };
}

export const stateOf = (h) => (h <= 0.02 ? "failed" : h < 0.98 ? "degraded" : "normal");

// Knock-on effects at one hour: parts that still work but are hurt by the outage.
// Every figure is read from the engine's rows (backlog, served vs demand, revenue lost so
// far); nothing is estimated here. Takes healthAt()'s result and returns it with:
//   notes  { nodeId: { state, text } } for the parts affected right now; a note's state is
//          "affected" unless the part itself is down or degraded
//   flows  edge strengths, lowered after a payment outage: unpaid orders never reach
//          revenue, the warehouse or the courier
export function knockOnAt(rows, topology, lossMode, { health, flows }) {
  const row = rows[rows.length - 1];
  const failed = topology.failedKind;
  const count = (n) => Math.round(n).toLocaleString("en-IN");
  const notes = {};
  const note = (id, text) => {
    const own = stateOf(health[id]);
    notes[id] = { state: own === "normal" ? "affected" : own, text };
  };

  if (lossMode === "fulfilment" && row.backlog >= 0.5) {
    const waiting = count(row.backlog);
    if (failed === "logistics") {
      note("warehouse", `${waiting} parcels stuck`);
      if (stateOf(health.logistics) === "normal") note("logistics", `clearing ${waiting}`);
    } else {
      note("warehouse", stateOf(health.warehouse) === "normal" ? `clearing ${waiting}` : `down · ${waiting} waiting`);
      if (stateOf(health.warehouse) !== "normal") note("logistics", "no parcels to ship");
    }
    note("customers", `${waiting} orders late`);
  }

  let paid = 1; // share of this hour's orders that got through checkout
  if (lossMode === "checkout" && row.demand > 0 && row.served < row.demand * 0.98) {
    paid = row.served / row.demand;
    const failedSoFar = rows.reduce((sum, r) => sum + (r.demand - r.served), 0);
    note("customers", `${count(failedSoFar)} payments failed`);
    note("warehouse", `${count(row.served)} of ${count(row.demand)} orders this hour`);
  }
  const afterPayment = ["payment>revenue", "storefront>warehouse", "warehouse>logistics", "logistics>customers"];
  const strengths = topology.flows.map(([a, b], i) =>
    afterPayment.includes(`${a}>${b}`) ? Math.min(flows[i], paid) : flows[i],
  );

  // Runs saved before the engine added lost_revenue_cum simply show no revenue note.
  if (row.lost_revenue_cum >= 1) {
    const verb = lossMode === "fulfilment" ? "refunded" : "lost";
    notes.revenue = { state: "affected", text: `₹${count(row.lost_revenue_cum)} ${verb}` };
  }
  return { health, flows: strengths, notes };
}
```

### `static/js/board/schematic2d.js`

<!-- source: static/js/board/schematic2d.js:1-96 -->
```js
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
```

### `static/js/board/scene3d.js`

#### Piece 1: scene, lights, camera, floor (lines 1–51)

<!-- source: static/js/board/scene3d.js:1-51 -->
```js
// Three.js view of the business as a living system.
//
// Each component is a plinth with a column on top: the column's height is its health
// (full = normal, flat = down) and its colour is its state. Small blocks travel along the
// edges: fewer blocks = fewer orders getting through. The camera is orthographic at an
// isometric angle: readable like a drawing, not a cinematic fly-through.

import * as THREE from "three";

import { controlPoint, stateOf } from "./topology.js";

const PARTICLES_PER_FLOW = 14;
const SPEED = 0.12; // edge lengths per second

export function createScene3D(container, topology, { reducedMotion }) {
  const css = getComputedStyle(document.documentElement);
  const colour = (name) => new THREE.Color(css.getPropertyValue(name).trim());
  const palette = {
    normal: colour("--bone"),
    degraded: colour("--signal"),
    failed: colour("--fault"),
    // Still working, but hurt by the outage: half-way between normal and degraded.
    affected: colour("--bone").lerp(colour("--signal"), 0.55),
    plinth: colour("--panel-2"),
    rule: colour("--rule"),
    rail: colour("--dim"), // edges: faint, but visible against the graphite floor
  };

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.domElement.setAttribute("aria-hidden", "true");
  container.append(renderer.domElement);

  const scene = new THREE.Scene();
  scene.add(new THREE.AmbientLight(0xffffff, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.4);
  sun.position.set(4, 10, 6);
  scene.add(sun);

  const xs = topology.nodes.map((n) => n.x);
  const zs = topology.nodes.map((n) => n.z);
  const centre = new THREE.Vector3((Math.min(...xs) + Math.max(...xs)) / 2, 0, (Math.min(...zs) + Math.max(...zs)) / 2);
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100);
  camera.position.set(centre.x + 10, 11, centre.z + 10);
  camera.lookAt(centre);

  const grid = new THREE.GridHelper(16, 32, palette.rule, palette.rule);
  grid.position.copy(centre).setY(-0.01);
  grid.material.transparent = true;
  grid.material.opacity = 0.35;
  scene.add(grid);
```

#### Piece 2: parts and flows (lines 53–102)

<!-- source: static/js/board/scene3d.js:53-102 -->
```js
  // ---- Nodes -------------------------------------------------------------------------
  const nodes = new Map();
  for (const node of topology.nodes) {
    const plinth = new THREE.Mesh(
      new THREE.BoxGeometry(1.3, 0.22, 1.3),
      new THREE.MeshLambertMaterial({ color: palette.plinth }),
    );
    plinth.position.set(node.x, 0.11, node.z);
    const outline = new THREE.LineSegments(
      new THREE.EdgesGeometry(plinth.geometry),
      new THREE.LineBasicMaterial({ color: palette.rule }),
    );
    outline.position.copy(plinth.position);
    const column = new THREE.Mesh(
      new THREE.BoxGeometry(0.55, 1, 0.55),
      new THREE.MeshLambertMaterial({ color: palette.normal }),
    );
    scene.add(plinth, outline, column);

    const label = document.createElement("div");
    label.className = "node-label";
    label.setAttribute("aria-hidden", "true");
    container.append(label);
    nodes.set(node.id, { node, column, label });
  }

  // ---- Flows -------------------------------------------------------------------------
  const flows = topology.flows.map(([a, b, bend]) => {
    const from = topology.nodes.find((n) => n.id === a);
    const to = topology.nodes.find((n) => n.id === b);
    const c = controlPoint(from, to, bend);
    // Every edge is a curve; a straight one just has its control point in the middle.
    const curve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(from.x, 0.06, from.z),
      new THREE.Vector3(c.x, 0.06, c.z),
      new THREE.Vector3(to.x, 0.06, to.z),
    );
    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(curve.getPoints(bend ? 40 : 1)),
      new THREE.LineBasicMaterial({ color: palette.rail, transparent: true, opacity: 0.55 }),
    );
    const particles = new THREE.InstancedMesh(
      new THREE.BoxGeometry(0.1, 0.1, 0.1),
      new THREE.MeshBasicMaterial({ color: palette.normal }),
      PARTICLES_PER_FLOW,
    );
    particles.count = PARTICLES_PER_FLOW;
    scene.add(line, particles);
    return { curve, particles, strength: 1 };
  });
```

#### Piece 3: fitting the view, placing labels (lines 104–139)

<!-- source: static/js/board/scene3d.js:104-139 -->
```js
  // ---- Sizing: fit the whole layout into the container at any aspect ratio ------------
  function resize() {
    const width = container.clientWidth;
    const height = container.clientHeight;
    // A hidden tab or collapsed panel measures 0x0; fitting to that would give NaN.
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.updateMatrixWorld();
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    const include = (v, padX, padY) => {
      const p = v.clone().applyMatrix4(camera.matrixWorldInverse);
      minX = Math.min(minX, p.x - padX); maxX = Math.max(maxX, p.x + padX);
      minY = Math.min(minY, p.y - padY); maxY = Math.max(maxY, p.y + padY);
    };
    for (const { node } of nodes.values()) {
      include(new THREE.Vector3(node.x, 0, node.z), 0.9, 0.6);
      include(new THREE.Vector3(node.x, 1.4, node.z), 0.9, 0.9);
    }
    for (const flow of flows) for (const p of flow.curve.getPoints(8)) include(p, 0.3, 0.3);
    const aspect = width / height;
    let w = maxX - minX, h = maxY - minY;
    if (w / h > aspect) h = w / aspect; else w = h * aspect;
    const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
    Object.assign(camera, { left: cx - w / 2, right: cx + w / 2, top: cy + h / 2, bottom: cy - h / 2 });
    camera.updateProjectionMatrix();
    draw();
  }

  function placeLabels() {
    const width = container.clientWidth, height = container.clientHeight;
    for (const { node, column, label } of nodes.values()) {
      const top = new THREE.Vector3(node.x, column.scale.y + 0.35, node.z).project(camera);
      label.style.left = `${((top.x + 1) / 2) * width}px`;
      label.style.top = `${((1 - top.y) / 2) * height}px`;
    }
  }
```

#### Piece 4: animation and updates (lines 141–216)

<!-- source: static/js/board/scene3d.js:141-216 -->
```js
  // ---- Animation ---------------------------------------------------------------------
  const matrix = new THREE.Matrix4();
  const position = new THREE.Vector3();
  let clock = 0, last = performance.now(), frame = null;

  function moveParticles() {
    for (const flow of flows) {
      const visible = Math.round(PARTICLES_PER_FLOW * flow.strength);
      flow.particles.count = visible;
      for (let i = 0; i < visible; i++) {
        const offset = reducedMotion ? 0 : clock * SPEED;
        const s = ((i + 0.5) / PARTICLES_PER_FLOW + offset) % 1;
        flow.curve.getPoint(s, position);
        matrix.makeTranslation(position.x, position.y, position.z);
        flow.particles.setMatrixAt(i, matrix);
      }
      flow.particles.instanceMatrix.needsUpdate = true;
    }
  }

  function draw() {
    moveParticles();
    renderer.render(scene, camera);
    placeLabels();
  }

  function loop(now) {
    clock += (now - last) / 1000;
    last = now;
    draw();
    frame = requestAnimationFrame(loop);
  }
  if (!reducedMotion) frame = requestAnimationFrame(loop);

  const observer = new ResizeObserver(resize);
  observer.observe(container);

  return {
    kind: "3D (WebGL)",
    update({ health, flows: strengths, notes = {} }) {
      for (const [id, { node, column, label }] of nodes) {
        const h = health[id];
        const note = notes[id];
        const state = note?.state ?? stateOf(h);
        column.scale.y = 0.08 + 1.1 * h; // never fully vanishes: a flat stub reads as "down"
        column.position.set(node.x, 0.22 + column.scale.y / 2, node.z);
        column.material.color.copy(palette[state]);
        label.className = `node-label ${state}`;
        label.innerHTML = "";
        label.append(node.label);
        const value = document.createElement("b");
        value.textContent = note?.text ?? (state === "failed" ? "DOWN" : `${Math.round(h * 100)} %`);
        label.append(value);
      }
      strengths.forEach((s, i) => {
        flows[i].strength = s;
        flows[i].particles.material.color.copy(s < 0.98 ? palette.degraded : palette.normal);
      });
      if (reducedMotion) draw(); // no animation loop: draw once per change
    },
    dispose() {
      cancelAnimationFrame(frame);
      observer.disconnect();
      renderer.dispose();
    },
  };
}

export function webglAvailable() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(window.WebGLRenderingContext && (canvas.getContext("webgl2") || canvas.getContext("webgl")));
  } catch {
    return false;
  }
}
```

## Check

On your Kirana Express board:

1. **3D.** Drag the hour slider from T+0 to T+3. At T+0 and T+1 (the outage), the payment
   gateway and checkout are red stubs labelled DOWN (checkout depends on the gateway), and
   the blocks on their edges disappear. Customers, the warehouse and revenue turn **light
   amber** with dashed labels: the number of failed payments so far, how many orders reached
   the warehouse this hour, and the revenue lost. No blocks move on to the warehouse,
   courier or revenue. From T+2, everything stands tall again, except revenue: it stays
   amber, because that money is gone.
2. **Knock-on during a courier outage.** Open the "Delhivery pickups stop for a day" run
   and choose speed 0.25×, then press Play. The courier is red; the warehouse counts the
   parcels stuck, customers count the orders late. When the courier is back, its label says
   "clearing" and the numbers fall hour by hour until everything is normal again.
3. **Your own names.** Kirana's components from lesson 6.9 are called "Payment gateway"
   and "Checkout", so those names appear. The demo businesses show "Razorpay (primary
   gateway)" and so on: the labels come from the business's own components.
4. **2D.** Add `?view=2d` to the address. The same parts, as diamonds on a flat
   "isometric" grid, with dashed lines that march along the edges.
5. **Reduced motion.** In DevTools, press Ctrl+Shift+P (Cmd+Shift+P on a Mac), type
   "reduced motion", choose **Emulate CSS prefers-reduced-motion: reduce**, and reload.
   The subtitle says "3D (WebGL) · reduced motion", and nothing moves on its own: the
   picture only changes when you change the hour.

## Line by line

### `topology.js`

- **Lines 1–2** · Comment: a floor grid, x across and z deep, used by both views.
- **Lines 4–12** · `LAYOUT`: where each **kind** of part sits, and its default label.
- **Lines 14–25** · `FLOWS`: the edges orders move along. The last one has a third value,
  a **bend**, so deliveries curve back to customers around the front instead of cutting
  through the warehouse.
- **Lines 27–30** · `controlPoint(from, to, bend)`: the point a curved edge bends towards
  (for a straight edge, the middle).
- **Lines 32–45** · `buildTopology(components, failedKind)`: one node per kind, labelled
  with the business's **own** component names when it has them ("Razorpay (primary
  gateway)"), joined with `+` if there are several, and remembering their keys.
- **Lines 47–61** · `healthAt(row, topology)`: for each node, the **lowest** health of its
  components in this hour's row (one broken part is enough), or 1 (normal) if the engine
  said nothing. Lines 53–55 handle a business with no components set up: the engine then
  reports the failing **kind** itself. Line 58: each edge's flow is the weaker of its two
  ends.
- **Line 63** · `stateOf(h)`: ≤ 2 % is "failed", under 98 % "degraded", else "normal".
- **Lines 65–71** · Comment: `knockOnAt` finds the parts that **still work** but are hurt by
  the outage. Every number comes from the engine's rows; this file only chooses the words.
  It hands back the health, the flows (lowered after a payment outage) and the notes.
- **Line 72** · It takes the rows **up to now**, the topology, the outage type (`lossMode`:
  `checkout` for payments, `fulfilment` for warehouse and courier) and what `healthAt`
  returned (`{ health, flows }` unpacks it).
- **Lines 73–75** · This hour's row, the broken part's kind, and a helper that rounds a
  number and writes it the Indian way (`1,57,075`).
- **Lines 76–80** · `notes` collects the result. `note(id, text)` adds one: its state is
  "affected" if the part itself is fine, otherwise it keeps its own state (down or degraded).
- **Lines 82–92** · Warehouse or courier outage with orders still waiting (`backlog`):
  - **Lines 84–86** · Courier broken: the parcels are stuck **at the warehouse**. Once the
    courier is back but the backlog isn't cleared yet, the courier shows "clearing 1,153".
  - **Lines 87–90** · Warehouse broken: it says how many orders wait (or "clearing" once it's
    back), and the courier has "no parcels to ship" while the warehouse is down.
  - **Line 91** · Either way, the customers' orders are late.
- **Lines 94–100** · Payment outage. `paid` is the share of this hour's orders that got
  through checkout (served ÷ demand; 1 means all). While payments fail, the customers' note
  counts **every** failed payment so far (demand − served, added up hour by hour), and the
  warehouse shows how many orders reached it this hour ("0 of 159"). Both change every hour.
- **Lines 101–104** · Orders that were never paid never reach revenue, the warehouse, the
  courier or the customer's door. So those four edges carry at most `paid` of their usual
  flow: fewer travelling blocks, or none.
- **Lines 106–110** · Revenue lost so far, straight from the engine's `lost_revenue_cum`:
  "refunded" for cancelled deliveries, "lost" for failed payments. Runs saved before this
  field existed don't have it, so they simply show no revenue note.
- **Line 111** · Return health, the adjusted flows, and the notes.

### `schematic2d.js`

- **Lines 1–3** · Comment: when it's used, and "same update() call".
- **Lines 5–12** · Imports and the SVG element helper (as in `charts.js`).
- **Line 14** · `createSchematic2D(container, topology, { reducedMotion })`: the same
  inputs as the 3D view.
- **Line 16** · `project({x, z})`: turn floor coordinates into flat drawing coordinates,
  tilted so it looks like the 3D view (an "isometric" projection).
- **Lines 17–29** · Work out the drawing's edges from every node and the middle of the
  curved edge, plus padding, so nothing is cut off.
- **Lines 31–50** · The SVG, with a hatch pattern for "down" and its own small
  stylesheet. The marching dashes are a CSS animation (`@keyframes march`) that moves the
  dash pattern along the line.
- **Lines 52–63** · Each edge as a quadratic curve (`M` start, `Q` control point and
  end): a faint rail, and the flow line on top.
- **Lines 65–75** · Each node: a diamond (`polygon`), its name above, its value inside.
  Then the drawing goes on the page.
- **Lines 79–93** · `update`: set each diamond's state and text ("DOWN" or "73 %"). For
  each edge, show strength three ways (opacity, dash spacing, colour), so it doesn't rely
  on colour alone, and only animate when motion is allowed and something flows. The 2D
  view ignores the knock-on `notes`: those labels are drawn in 3D only.
- **Line 94** · `dispose()`: remove the drawing.

### `scene3d.js`, piece 1

- **Lines 1–6** · Comment: plinths, columns, travelling blocks, an isometric camera
  ("readable like a drawing, not a cinematic fly-through").
- **Line 8** · Import all of Three.js as `THREE` (the import map says where it is).
- **Lines 12–13** · 14 blocks per edge; they travel 0.12 of an edge per second.
- **Lines 16–27** · Read the app's colours from its CSS variables (`--bone`, `--signal`,
  `--fault`...), so the 3D view matches the rest of the page. `affected` (line 23) is a
  colour 55 % of the way from normal (`--bone`) to amber (`--signal`): working, but hurt.
- **Lines 29–32** · The renderer: smooth edges, a transparent background, sharp on
  high-resolution screens (but at most 2×, for speed). Its canvas goes into the stage and
  is hidden from screen readers (the table twin speaks instead).
- **Lines 34–38** · The scene, soft light everywhere, and a sun up and to the side.
- **Lines 40–45** · The middle of the layout, and an **orthographic** camera placed up and
  to the side of it, looking at it.
- **Lines 47–51** · A faint floor grid.

### Piece 2

- **Lines 54–77** · For each node: a flat box (the plinth) with its outline, and a tall
  box (the column) on top, added to the scene. Its label is an ordinary HTML `<div>`
  placed over the canvas (text in HTML is sharper and easier than text in 3D).
- **Lines 80–102** · For each edge: a 3D curve (straight edges are curves with the
  control point in the middle), a faint line along it, and an **InstancedMesh**: one
  object that draws 14 copies of a tiny box very cheaply, each at its own position.

### Piece 3

- **Lines 105–130** · `resize()`: make the whole layout fit the box, whatever its shape.
  Skip if the box has no size yet (line 109). Then measure every node (bottom and top of
  its column) and every edge **as the camera sees them**, find the edges of that, widen
  the narrower side to the box's shape, and set the camera's window to it.
- **Lines 132–139** · `placeLabels()`: for each node, find where the top of its column
  lands on the screen (`.project(camera)` gives -1…1), and move its HTML label there.

### Piece 4

- **Lines 142–144** · Reusable objects (made once, not 60 times a second), the clock, and
  the frame handle.
- **Lines 146–159** · `moveParticles()`: per edge, show as many blocks as the flow allows
  (14 × strength), each spread evenly along the curve and moved forward by the clock
  (frozen with reduced motion). `% 1` wraps them back to the start.
- **Lines 161–165** · `draw()`: move blocks, render, place labels.
- **Lines 167–173** · `loop(now)`: advance the clock by the real time since the last frame,
  draw, and ask for the next frame. Only started if motion is allowed.
- **Lines 175–176** · A `ResizeObserver` calls `resize()` whenever the box changes size
  (and once at the start).
- **Lines 180–200** · `update({health, flows, notes})`: per node, take its knock-on note
  if `knockOnAt` gave one (`notes = {}` means "none" when a caller leaves it out). Set the
  column's height (never quite zero: a stub reads as "down"), its position (standing on the
  plinth), its colour (the note's state wins, so "affected" parts turn light amber at full
  height) and its label (the note's text, else "DOWN" or "73 %", built with text nodes). Per edge, store the
  strength and colour the blocks. With reduced motion, draw once now.
- **Lines 201–205** · `dispose()`: stop the loop, the observer and the renderer.
- **Lines 209–216** · `webglAvailable()`: try to get a WebGL drawing context from a
  throwaway canvas; any failure means no.

## If it didn't work

| You see | Fix |
|---|---|
| The stage is empty, no error | The box had no size when the page loaded (a hidden tab). Resize the window: `ResizeObserver` redraws it. |
| Labels are in the top-left corner | `placeLabels` ran before `resize`. Reload; check lines 175–176. |
| Everything is DOWN at every hour | That's the engine's data for this run: check the timeline in `/api/v1/runs/<id>/`. The view only draws it. |

## Quiz

1. Why can `board/main.js` swap the 3D view for the 2D one without other changes?
2. Where does a part's health come from?
3. Why are the node labels HTML and not 3D text?
4. What do the travelling blocks show, and why are there fewer during an outage?
5. The courier is down. Why is the warehouse light amber and not red?

---

**Next:** [10.13 · Tests and commit](13-tests-and-commit.md)

<details><summary>Quiz answers</summary>

1. Both offer the same `update()` and `dispose()` functions (the same interface).
2. Only from the engine's hourly row (`row.components`); unknown parts are drawn normal.
3. HTML text is sharp at any size, easy to style, and simpler than 3D text.
4. Orders getting through on that edge. The count is 14 × the edge's flow strength.
5. The warehouse still works, but parcels pile up there with nowhere to go: it's **affected**
   by the outage (a knock-on effect), not broken itself.

</details>
