# 10.1 · How the pages fit together

**Time:** 25 minutes · **Before this:** [Part 9](../09-decisions/README.md).
**Reading only.**

## Read

### Two kinds of page

**Server pages.** The dashboard, the forms and the business page are built on the
**server**: a Django view gathers data, a template turns it into HTML, the browser shows
it. Buttons are ordinary forms that POST and then **redirect** back (lesson 9.6). No
JavaScript needed. This is the oldest, sturdiest way to build a website, and it's how
most of AI WarRoom works.

**Live pages.** The two run pages (Idea Bench and Situation Board) need to react **while**
you drag a slider. For that, the server sends the page **plus** a block of data, and a
JavaScript file draws the charts and listens to the sliders.

```text
  Django view ──► template (HTML) ──► browser
       │                                 │
       └── page_data ──► <script id="page-data" type="application/json">{...}</script>
                                         │
                       board/main.js reads it, draws, listens to sliders
                                         │
                slider moves ──► POST /api/v1/simulate/preview/ ──► engine ──► redraw
```

### Handing data to JavaScript: `json_script`

The template writes:

```text
{{ page_data|json_script:"page-data" }}
```

Django turns the `page_data` dictionary into a `<script type="application/json"
id="page-data">` tag, escaped so that no text inside it (a business called
`</script><script>alert(1)`, say) can break out and run as code. The JavaScript reads it
back with one line:

```js
const data = JSON.parse(document.getElementById("page-data").textContent);
```

### JavaScript modules, no build step

Each JS file is a **module**: it `import`s what it needs from other files and `export`s
what others may use.

```js
import { money } from "../lib/format.js";
```

The page loads it with `<script type="module" src="...">`. Modern browsers understand
this directly. So there's **no build step**, no `npm`, no bundler: the files you read are
exactly the files the browser runs.

The 3D view uses one outside library, **Three.js**. A copy lives in
`static/vendor/three-0.170.0/`, so the app works with no internet (a classroom on bad
Wi-Fi, say). An **import map** in the page tells the browser where `"three"` is.

### The rule: the browser never calculates a business number

Every figure on the run pages comes from the engine: the saved run when the page opens,
or the preview endpoint when a slider moves. The JavaScript formats numbers (₹21,000),
draws them, and adds up hour-by-hour rows the engine already returned. It never works out
a loss, a cost or a cash balance itself. One engine, one source of truth.

### Safe text: `textContent`, not `innerHTML`

Component names, business names and website text are typed by people. If JavaScript put
them into the page with `innerHTML`, a name like `<img src=x onerror=alert(1)>` would
**run**. This is called **XSS** (cross-site scripting). So the code puts user text in
with `textContent`, which always shows text as text. You'll see comments saying so.

### For everyone

- Each chart has a hidden **table twin** that screen readers read aloud.
- People who set "reduce motion" in their computer's settings get a still 3D view.
- With no WebGL (old computers), or with `?view=2d` in the address, the system view is a
  flat drawing instead.

## Quiz

1. Why do most pages need no JavaScript?
2. What does `json_script` protect against?
3. A slider moves. Who calculates the new numbers?
4. Why `textContent` and not `innerHTML` for a component's name?

---

**Next:** [10.2 · Forms](02-forms.md)

<details><summary>Quiz answers</summary>

1. The server builds the full HTML, and buttons are ordinary forms that post and redirect.
2. Text in the data breaking out of the `<script>` tag and running as code.
3. The engine, through the preview endpoint. The browser only draws the result.
4. Names are typed by people; `innerHTML` would run any HTML hidden in them (XSS).

</details>
