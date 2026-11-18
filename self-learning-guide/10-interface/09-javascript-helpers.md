# 10.9 · JavaScript helpers

**Time:** 50 minutes · **Before this:** [10.8](08-the-run-pages.md). **Reading lesson:**
the files are already in `static/js/lib/`.

## Read

### JavaScript you'll meet in the next lessons

Part 2 taught the basics. These lessons also use some newer, shorter ways of writing
things. Here they are once, side by side with Python:

| JavaScript | Means | Python equivalent |
|---|---|---|
| `const x = 5` / `let y = 1` | A name that can't / can be given a new value | `x = 5` |
| `(a, b) => a + b` | A small function (an **arrow function**) | `lambda a, b: a + b` |
| `` `Total ${money(x)}` `` | Text with values inside (a **template literal**, with backticks) | `f"Total {money(x)}"` |
| `const { a, b } = obj` | Take `obj.a` and `obj.b` into two names (**destructuring**) | `a, b = obj["a"], obj["b"]` |
| `{ ...old, key: 1 }` | A copy of `old` with `key` changed (**spread**) | `{**old, "key": 1}` |
| `obj?.name` | `obj.name`, or `undefined` if `obj` is missing (**optional chaining**) | `obj.name if obj else None` |
| `a ?? b` | `a`, unless it's `null` or `undefined`, then `b` | `a if a is not None else b` |
| `async function f()` / `await x` | A function that can wait for slow things (the network) | `async def` / `await` |
| `import { x } from "./y.js"` | Use `x` from another file | `from y import x` |
| `export function x()` | Let other files import `x` | (everything is importable in Python) |

### Two small files used everywhere

- **`lib/api.js`**: `api(url, options)` calls our JSON API with the CSRF token
  (lesson 4.3), and turns our standard error shape (lesson 4.7) into an `ApiError` the
  page can show. Plus `debounce` (wait until the user stops moving a slider) and a check
  for "reduce motion".
- **`lib/format.js`**: the browser's twin of lesson 9.5's template filters, so a number
  looks the same whether the server or the browser drew it: `₹1,23,45,678`.

## Do (read)

### `static/js/lib/api.js`

<!-- source: static/js/lib/api.js:1-48 -->
```js
// Tiny fetch wrapper for our own JSON API.
// Every API error has one shape: {"error": {"code", "message", "fields"}}; we turn it into
// an ApiError the page can show as-is.

export class ApiError extends Error {
  constructor(status, body) {
    const error = (body && body.error) || {};
    super(error.message || `Request failed (${status})`);
    this.status = status;
    this.code = error.code || "error";
    this.fields = error.fields || {};
  }
}

function csrfToken() {
  // Django puts the CSRF token in a cookie; unsafe requests must echo it in a header.
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export async function api(url, { method = "GET", body, signal } = {}) {
  const response = await fetch(url, {
    method,
    signal,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(method !== "GET" ? { "X-CSRFToken": csrfToken() } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, data);
  return data;
}

// Call `fn` only after the user has stopped changing things for `ms` milliseconds.
export function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

export const prefersReducedMotion = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;
```

### `static/js/lib/format.js`

<!-- source: static/js/lib/format.js:1-52 -->
```js
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
```

## Check

Open any page of the app (logged in), press F12 → **Console**, and load the modules
directly. `await import(...)` loads a module and gives you everything it exports:

```js
const f = await import("/static/js/lib/format.js")
```

```js
f.money("1234567.8")
```

`'₹12,34,568'`: Indian grouping, no paise over ₹1,000, the same as the server's `figure`
filter. Try these too:

| Type | You get |
|---|---|
| `f.money("649.5")` | `'₹649.50'` |
| `f.moneyShort(4200000)` | `'₹42L'` (42 lakh) |
| `f.moneyShort(13000000)` | `'₹1.3Cr'` (1.3 crore) |
| `f.figure("1", "hours")` | `'1 hour'` |
| `f.alignedStep(112, 5)` | `1` (see the comment on lines 41–43) |
| `f.clockLabel(26)` | `'02:00'` (hour 26 is 2 a.m. the next day) |

Now the API helper, with a run that doesn't exist:

```js
const a = await import("/static/js/lib/api.js")
```

```js
try { await a.api("/api/v1/runs/00000000-0000-0000-0000-000000000000/") } catch (e) { console.log(e.message, e.status, e.code) }
```

`Not found. 404 not_found`: our error shape, turned into a JavaScript error with the
message, the status and the code.

## Line by line

### `api.js`

- **Lines 1–3** · Comments: one error shape, turned into an `ApiError`.
- **Line 5** · `ApiError` is a kind of `Error` (`extends`), exported for other files.
- **Line 6** · Its `constructor` (like Python's `__init__`) takes the status and body.
- **Line 7** · The `error` part of our shape, or an empty object if the body isn't ours
  (`(a && a.b) || {}`).
- **Line 8** · `super(...)` sets the message: ours, or "Request failed (500)".
- **Lines 9–11** · Keep the status, code and per-field messages.
- **Lines 15–19** · `csrfToken()`: find the `csrftoken` cookie with a regular expression
  and return its value (`decodeURIComponent` undoes any `%` encoding), or `""`.
- **Line 21** · `api(url, options)`. `{ method = "GET", body, signal } = {}` takes three
  named options with a default for `method`, and works with no options at all.
- **Lines 22–32** · `fetch` (the browser's way to make a request, Part 2):
  - `signal` lets a caller cancel it (lesson 10.10).
  - `credentials: "same-origin"`: send our login cookie.
  - `Accept`: we want JSON back.
  - Line 28: add `Content-Type: application/json` only when there is a body. `...( cond ?
    {...} : {} )` spreads either a header or nothing.
  - Line 29: send the CSRF header for anything but GET.
  - Line 31: the body as JSON text.
- **Line 33** · Read the answer as JSON. A 204 ("no content") has none; broken JSON
  becomes `null` (`.catch(() => null)`) instead of a second error.
- **Line 34** · Not a 2xx status? Throw our `ApiError`.
- **Line 35** · Otherwise return the data.
- **Lines 38–45** · `debounce(fn, ms)`: returns a new function. Each call **cancels** the
  previous timer and starts a new one, so `fn` only runs once the calls stop for `ms`
  milliseconds. Dragging a slider fires dozens of events a second; the preview request is
  sent once, when you pause.
- **Lines 47–48** · `prefersReducedMotion()`: has the user asked their computer for less
  animation? `matchMedia` asks the browser.

### `format.js`

- **Lines 1–2** · Comments: matches the server's filters. The browser's built-in
  `Intl.NumberFormat` with the `"en-IN"` locale already groups the Indian way.
- **Lines 4–6** · Three ready-made formatters: whole numbers, one decimal, exactly two
  decimals.
- **Line 8** · `isMissing`: null, undefined or empty text.
- **Lines 10–15** · `money(value)`: `"n/a"` if missing; whole numbers (or anything ₹1,000
  and over) with no paise, otherwise two decimals; the minus sign before the ₹. The same
  rule as lesson 9.5's filter.
- **Lines 17–26** · `moneyShort`: for chart labels where space is tight: crore (`1e7` is
  10,000,000), lakh (`1e5`), thousand (`k`), or the plain number.
- **Lines 28–39** · `figure(value, unit)`: the twin of the server's `figure` filter:
  money with its `/order`, percentages, ratios, hours of the day, and "1 hour" not "1
  hours". `String(value).replaceAll("_", " ")` for choices like `ecommerce_curve`.
- **Lines 41–50** · `alignedStep(value, preferred)`: a browser slider snaps its value to
  its step. With step 5, a saved ₹112 would silently show as ₹110, a wrong number on
  screen. So try the preferred step, then finer ones, until the saved value sits exactly
  on the grid. `Math.abs(v / step - Math.round(v / step)) < 1e-9` means "v divided by step
  is a whole number" (allowing for tiny rounding errors).
- **Line 52** · `clockLabel(hour)`: hour 26 → `"02:00"`. `((h % 24) + 24) % 24` keeps the
  answer between 0 and 23, even for negative hours.

## If it didn't work

| You see | Fix |
|---|---|
| `Failed to fetch dynamically imported module` | The address must start with `/static/`. Is the server running? |
| `await is only valid in async functions` | Use the browser console (it allows top-level `await`), not a file. |

## Quiz

1. Why does `api()` send `X-CSRFToken` for POST but not GET?
2. What would happen without `debounce` while dragging a slider?
3. Why does `alignedStep` exist?

---

**Next:** [10.10 · The Idea Bench](10-the-idea-bench.md)

<details><summary>Quiz answers</summary>

1. GET only reads. Django's CSRF check guards requests that change things (lesson 4.3).
2. A preview request for every tiny movement: dozens per second, mostly wasted.
3. So a slider never shows a saved value rounded to its step (₹112 shown as ₹110).

</details>
