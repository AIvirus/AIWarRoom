# 2.3 · JSON and APIs

**Time:** 30 minutes · **Before this:** [2.2](02-html-css-javascript.md).

## 📖 Read

Web pages are for **people**. But programs also need to talk to programs: the AI WarRoom
page asks the server "recalculate with outage = 12 hours", and the server talks to
Google's Gemini. They don't send pretty pages; they send **data**.

### JSON

**JSON** (said "jay-son") is a text format for data. It looks almost exactly like a
Python dictionary:

```json
{"name": "Raju Chai", "price_per_cup": 15, "open": true, "phone": null}
```

Small differences from Python: JSON writes `true`/`false`/`null` where Python writes
`True`/`False`/`None`, and always uses double quotes.

Because JSON is **text**, any language can read and write it: Python, JavaScript, Java...
That's why the whole web uses it.

### APIs

An **API** (Application Programming Interface) is a set of addresses on a server that
answer with JSON instead of web pages. It's a door made for programs.

AI WarRoom has an API at `/api/v1/...`. For example:

| Request | What happens |
|---|---|
| `GET /api/v1/businesses/` | Answers with a JSON list of your businesses |
| `POST /api/v1/scenarios/5/run/` | Runs a simulation and answers with the results as JSON |

The sliders on the AI WarRoom page call this API in the background, so the page can
update without reloading, just like your `app.js` in 2.2, but asking the server.

## ⌨️ Do

Make `json_practice.py` in your `web` folder:

<!-- source: self-learning-guide/02-web/practice/json_practice.py:1-12 -->
```python
# JSON: the text format websites and APIs use to send data.
import json

stall = {"name": "Raju Chai", "price_per_cup": 15, "open": True, "phone": None}

text = json.dumps(stall)
print(text)
print(type(text))

back = json.loads('{"name": "Meena Tea", "cups": [110, 125, 98]}')
print(back["name"], sum(back["cups"]))
print(type(back))
```

```bash
python json_practice.py
```

## ✅ Check

```text
{"name": "Raju Chai", "price_per_cup": 15, "open": true, "phone": null}
<class 'str'>
Meena Tea 333
<class 'dict'>
```

## 🔍 Line by line

**Line 2** · `import json` loads Python's built-in JSON tools.

**Line 4** · An ordinary Python dictionary, with `True` and `None`.

**Line 6** · `json.dumps(stall)`: "**dump** to **s**tring". It turns the dictionary into
JSON **text**, ready to send over the internet.

**Line 7** · Look at the output: `True` became `true` and `None` became `null`.

**Line 8** · Proof that it's text now (`str`), not a dictionary.

**Line 10** · `json.loads('...')`: "**load** from **s**tring". It reads JSON text (here
written by hand, inside single quotes) and turns it back into a Python dictionary. This is
what Python does when JSON **arrives**, for example Gemini's answer in Part 7.

**Line 11** · It's a real dictionary again, so we can use `["name"]` and `sum` on the list.

**Line 12** · Proof: `dict`.

## 🛠️ If it didn't work

| You see | It means |
|---|---|
| `json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes` | JSON needs **double** quotes around keys and text. `{'name': 'x'}` isn't valid JSON. |
| `TypeError: Object of type Decimal is not JSON serializable` | JSON doesn't know Decimal. AI WarRoom sends money as text, like `"1250.00"`, which is exact and safe. You'll see this in Part 5. |

## ❓ Quiz

1. What is `True` in JSON?
2. Which function turns a dictionary into JSON text: `dumps` or `loads`?
3. Why do APIs send JSON instead of HTML?

---

**Part 2 done! 🎉** Next: [Part 3 · Databases](../03-databases/README.md)

<details><summary>Quiz answers</summary>

1. `true` (lowercase).
2. `dumps` (dump **to** a string).
3. Because the reader is a program, not a person: it needs clean data it can use, not a
   page layout.

</details>
