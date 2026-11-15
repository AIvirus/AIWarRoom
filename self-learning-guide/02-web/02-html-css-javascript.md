# 2.2 · HTML, CSS and JavaScript

**Time:** 45 minutes · **Before this:** [2.1](01-browser-and-server.md).

## 📖 Read

Every web page is made of three languages. Think of a house:

| Language | Job | House comparison |
|---|---|---|
| **HTML** | What's on the page: headings, text, boxes, buttons | The walls and rooms |
| **CSS** | How it looks: colours, sizes, spacing | The paint and furniture |
| **JavaScript (JS)** | What it does when you interact | The electricity: switches that make things happen |

HTML is written with **tags** in angle brackets. Most come in pairs, an opening tag and a
closing tag with a `/`:

```html
<h1>Raju Chai</h1>
```

Everything between the pair is the tag's content. Tags can have **attributes** that add
details: `<input id="cups" value="120">`.

In AI WarRoom, Django builds the HTML (Part 4), CSS gives it the dark control-room look,
and JavaScript makes the sliders and the 3D view work (Part 10).

## ⌨️ Do

In your `web` folder, make these three files.

**`index.html`** (the walls):

<!-- source: self-learning-guide/02-web/practice/index.html:1-16 -->
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Raju Chai</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <h1>Raju Chai</h1>
  <p>Price per cup: <strong id="price">15</strong> rupees</p>
  <label for="cups">Cups sold today</label>
  <input id="cups" type="number" value="120">
  <p>Money in: <output id="money-in">1800</output> rupees</p>
  <script src="app.js"></script>
</body>
</html>
```

**`style.css`** (the paint):

<!-- source: self-learning-guide/02-web/practice/style.css:1-15 -->
```css
body {
  font-family: sans-serif;
  background: #16150f;
  color: #e9e5d6;
  padding: 24px;
}

h1 {
  color: #f2a900;
}

input {
  font-size: 18px;
  width: 6em;
}
```

**`app.js`** (the electricity):

<!-- source: self-learning-guide/02-web/practice/app.js:1-9 -->
```javascript
// Runs in the browser. Recalculate money in whenever the number changes.
const price = Number(document.getElementById("price").textContent);
const cupsBox = document.getElementById("cups");
const moneyIn = document.getElementById("money-in");

cupsBox.addEventListener("input", () => {
  const cups = Number(cupsBox.value);
  moneyIn.textContent = cups * price;
});
```

Start the server again (`python -m http.server 8765`) and open
http://localhost:8765/index.html. Change the number of cups.

## ✅ Check

- The page is dark with a yellow-orange heading.
- When you change "Cups sold today" to `200`, "Money in" changes to `3000` straight away,
  without reloading the page.
- In the terminal, `style.css` and `app.js` now show `200`.

## 🔍 Line by line

### `index.html`

**Line 1** · `<!doctype html>` tells the browser "this is a modern HTML page".

**Line 2** · `<html lang="en">` is the start of the page; `lang="en"` says it's in
English (screen readers for blind users use this).

**Line 3** · `<head>` holds information **about** the page, which isn't shown in the
page itself.

**Line 4** · `<meta charset="utf-8">`: the text uses UTF-8, which can show every
language and symbols like ₹.

**Line 5** · `<title>` is the text on the browser tab.

**Line 6** · `<link rel="stylesheet" href="style.css">` says "also download `style.css`
and use it for the looks". `href` is the file's address.

**Line 7** · `</head>`: the head ends.

**Line 8** · `<body>`: everything visible goes in here.

**Line 9** · `<h1>` is the biggest heading (h1 to h6 get smaller).

**Line 10** · `<p>` is a paragraph. Inside it, `<strong>` makes text bold, and
`id="price"` gives it a unique name so JavaScript can find it.

**Line 11** · `<label for="cups">` is a caption for the input with `id="cups"`. Clicking
the label puts the cursor in the box, and screen readers read it aloud.

**Line 12** · `<input>` is a box to type in. `type="number"` means numbers only;
`value="120"` is the starting value. `<input>` has no closing tag because it holds no
content.

**Line 13** · `<output id="money-in">` shows a calculated result.

**Line 14** · `<script src="app.js">` downloads and runs the JavaScript. It sits at the
end of `<body>` so the elements above already exist when the script looks for them.

**Lines 15–16** · Close `<body>` and `<html>`.

### `style.css`

A CSS **rule** is: *which elements* (the **selector**) `{` *how they should look* `}`.

**Line 1** · `body {` means the rules below apply to the whole page body.

**Line 2** · `font-family: sans-serif;` uses a plain font without little "feet".

**Line 3** · `background: #16150f;` is the background colour as a **hex code**: `#` then
3 pairs of digits for red, green and blue (`00` = none, `ff` = full). `#16150f` is almost
black.

**Line 4** · `color` is the text colour: `#e9e5d6`, a soft off-white.

**Line 5** · `padding: 24px;` adds 24 pixels of space inside the edges.

**Line 6** · `}` ends the rule. Every line inside ends with `;`.

**Lines 8–10** · `h1 { color: #f2a900; }` makes headings amber. AI WarRoom uses exactly
these three colours.

**Lines 12–15** · Bigger text in the input; `6em` means 6 times the font size wide.

### `app.js`

**Line 1** · In JavaScript, comments start with `//`.

**Line 2** · `const price = Number(document.getElementById("price").textContent);`
- `const` makes a variable whose value won't be replaced (like a frozen jar).
- `document` is the whole page; `getElementById("price")` finds the element with
  `id="price"`.
- `.textContent` is its text, `"15"`.
- `Number(...)` turns the text into the number 15.
- JavaScript lines end with `;`.

**Lines 3–4** · Find the input box and the output.

**Line 6** · `cupsBox.addEventListener("input", () => { ... });`
- "When the user changes the box (the `input` event), run this function."
- `() => { ... }` is a short way to write a function in JavaScript, called an **arrow
  function**.

**Line 7** · Read what's in the box and turn it into a number.

**Line 8** · Put cups × price into the output. The page updates instantly.

**Line 9** · `});` closes the function and the `addEventListener(` call.

> **Compare with Python:** JavaScript uses `{ }` for blocks instead of indentation, and
> `;` at the end of lines, but the ideas (variables, functions, if) are the same.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| Page is white, not dark | `style.css` isn't loading: check the file name and the `href`, and that the terminal shows `200` for it. |
| Changing cups does nothing | Open the browser's **Console** (press F12 → Console) to see JavaScript errors. A wrong `id` gives `Cannot read properties of null`. |

## ❓ Quiz

1. Which language decides colours: HTML, CSS or JS?
2. Why does the `<script>` tag sit at the end of `<body>`?
3. Change the price in `index.html` to `20`. What's "Money in" for 100 cups?

---

**Next:** [2.3 · JSON and APIs](03-json-and-apis.md)

<details><summary>Quiz answers</summary>

1. CSS.
2. So the elements it looks for already exist when it runs.
3. 2000. The JavaScript reads the price from the page, so you don't change the JS.

</details>
