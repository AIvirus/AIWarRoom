// Number formatting that matches the server's template filters (common/templatetags).
// Intl's "en-IN" locale already groups digits the Indian way: 1,23,45,678.

const whole = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const one = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 });
const two = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const isMissing = (v) => v === null || v === undefined || v === "";

export function money(value) {
  if (isMissing(value)) return "n/a";
  const n = Number(value);
  const isWhole = Number.isInteger(n) || Math.abs(n) >= 1000;
  return `${n < 0 ? "-" : ""}₹${(isWhole ? whole : two).format(Math.abs(n))}`;
}

// Short form for chart labels: ₹4.2L, ₹1.3Cr.
export function moneyShort(value) {
  const n = Number(value);
  const a = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (a >= 1e7) return `${sign}₹${one.format(a / 1e7)}Cr`;
  if (a >= 1e5) return `${sign}₹${one.format(a / 1e5)}L`;
  if (a >= 1e3) return `${sign}₹${one.format(a / 1e3)}k`;
  return `${sign}₹${whole.format(a)}`;
}

export function figure(value, unit = "") {
  if (isMissing(value)) return "n/a";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value).replaceAll("_", " ");
  if (unit.startsWith("INR")) return money(n) + unit.slice(3);
  if (unit === "%") return `${one.format(n)} %`;
  if (unit === "ratio") return `${two.format(n)}×`;
  if (unit === "hour of day") return `${String(Math.trunc(n)).padStart(2, "0")}:00`;
  const text = Number.isInteger(n) || Math.abs(n) >= 100 ? whole.format(n) : one.format(n);
  const u = n === 1 && ["hours", "months", "orders"].includes(unit) ? unit.slice(0, -1) : unit;
  return `${text} ${u}`.trim();
}

// A slider step that the saved value sits on exactly. Range inputs snap their value to
// the step, so step 5 would silently show a saved ₹112 as ₹110. Try the preferred step,
// then finer ones (1, 0.1, 0.01...) until the value lands on the grid.
export function alignedStep(value, preferred) {
  const v = Number(value);
  for (const step of [preferred, 1, 0.5, 0.1, 0.05, 0.01, 0.001]) {
    if (step <= preferred && Math.abs(v / step - Math.round(v / step)) < 1e-9) return step;
  }
  return "any";
}

export const clockLabel = (hour) => `${String(((hour % 24) + 24) % 24).padStart(2, "0")}:00`;
