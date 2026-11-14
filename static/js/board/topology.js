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
