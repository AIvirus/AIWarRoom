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
// far); nothing is estimated here. Returns { nodeId: { state, text } } for the parts
// affected right now. A note's state is "affected" unless the part itself is down.
export function knockOnAt(rows, topology, lossMode, health) {
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
  if (lossMode === "checkout" && row.demand > 0 && row.served < row.demand * 0.98) {
    const failing = Math.round((1 - row.served / row.demand) * 100);
    note("customers", failing === 100 ? "nobody can pay" : `${failing} % can't pay`);
    note("warehouse", failing === 100 ? "no new orders" : `${failing} % fewer orders`);
  }
  // Runs saved before the engine added lost_revenue_cum simply show no revenue note.
  if (row.lost_revenue_cum >= 1) {
    const verb = lossMode === "fulfilment" ? "refunded" : "lost";
    notes.revenue = { state: "affected", text: `₹${count(row.lost_revenue_cum)} ${verb}` };
  }
  return notes;
}
