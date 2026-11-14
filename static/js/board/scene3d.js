// Three.js view of the business as a living system.
//
// Each component is a plinth with a column on top: the column's height is its health
// (full = normal, flat = down) and its colour is its state. Small blocks travel along the
// edges: fewer blocks = fewer orders getting through. The camera is orthographic at an
// isometric angle: readable like a drawing, not a cinematic fly-through.

import * as THREE from "three";

import { stateOf } from "./topology.js";

const PARTICLES_PER_FLOW = 14;
const SPEED = 0.12; // edge lengths per second

export function createScene3D(container, topology, { reducedMotion }) {
  const css = getComputedStyle(document.documentElement);
  const colour = (name) => new THREE.Color(css.getPropertyValue(name).trim());
  const palette = {
    normal: colour("--bone"),
    degraded: colour("--signal"),
    failed: colour("--fault"),
    plinth: colour("--panel-2"),
    rule: colour("--rule"),
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
  const flows = topology.flows.map(([a, b]) => {
    const from = topology.nodes.find((n) => n.id === a);
    const to = topology.nodes.find((n) => n.id === b);
    const start = new THREE.Vector3(from.x, 0.06, from.z);
    const end = new THREE.Vector3(to.x, 0.06, to.z);
    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([start, end]),
      new THREE.LineBasicMaterial({ color: palette.rule }),
    );
    const particles = new THREE.InstancedMesh(
      new THREE.BoxGeometry(0.1, 0.1, 0.1),
      new THREE.MeshBasicMaterial({ color: palette.normal }),
      PARTICLES_PER_FLOW,
    );
    particles.count = PARTICLES_PER_FLOW;
    scene.add(line, particles);
    return { start, end, particles, strength: 1 };
  });

  // ---- Sizing: fit the whole layout into the container at any aspect ratio ------------
  function resize() {
    const width = container.clientWidth;
    const height = container.clientHeight;
    // A hidden tab or collapsed panel measures 0x0; fitting to that would give NaN.
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.updateMatrixWorld();
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const { node } of nodes.values()) {
      for (const y of [0, 1.4]) {
        const p = new THREE.Vector3(node.x, y, node.z).applyMatrix4(camera.matrixWorldInverse);
        minX = Math.min(minX, p.x - 0.9); maxX = Math.max(maxX, p.x + 0.9);
        minY = Math.min(minY, p.y - 0.6); maxY = Math.max(maxY, p.y + 0.9);
      }
    }
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
        position.lerpVectors(flow.start, flow.end, s);
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
    update({ health, flows: strengths }) {
      for (const [id, { node, column, label }] of nodes) {
        const h = health[id];
        const state = stateOf(h);
        column.scale.y = 0.08 + 1.1 * h; // never fully vanishes: a flat stub reads as "down"
        column.position.set(node.x, 0.22 + column.scale.y / 2, node.z);
        column.material.color.copy(palette[state]);
        label.className = `node-label ${state}`;
        label.innerHTML = "";
        label.append(node.label);
        const value = document.createElement("b");
        value.textContent = state === "failed" ? "DOWN" : `${Math.round(h * 100)} %`;
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
