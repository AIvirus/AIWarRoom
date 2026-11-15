# Part 10 · The interface

**Time:** about 5–6 hours · **Before this:** [Part 9](../09-decisions/README.md)
(your `my-warroom` passes 246 tests).

Everything works already: you've driven it from the browser console. Now it gets real
**pages** that anyone can use without typing code:

| Page | Address | What it shows |
|---|---|---|
| Operations board | `/` | Every business, open alerts, recent decisions |
| Add a business | `/businesses/new/` | A form |
| Business page | `/businesses/<id>/` | Assumption ledger, scenarios, components, committee, runs, website scan, decisions |
| Idea Bench | `/runs/<id>/` (idea runs) | Sliders, a month-by-month cash chart, seven cases, "which assumption matters most" |
| Situation Board | `/runs/<id>/` (outage runs) | Sliders, a 3D system view, an hour-by-hour timeline, the responses compared |
| Decision brief | `/decisions/<id>/brief/` | Part 9's printable page, now linked from everywhere |

This part has two halves:

1. **Python and templates** (lessons 10.2–10.8): forms, views, addresses, and the HTML
   for each page. You type these, as usual.
2. **JavaScript** (lessons 10.9–10.12): the sliders, charts and the 3D view. These files
   are already in your `static/js/` folder: you copied them with `static/` in lesson 4.2.
   Now you **read** them, line by line, and see how they work.

One rule runs through all the JavaScript: **the browser never calculates a business
number.** When you move a slider, the page asks the server's preview endpoint (Part 6),
and draws whatever the engine returns.

## Lessons in this part (do them in order)

| # | Lesson | You will build or read |
|---|---|---|
| 10.1 | [How the pages fit together](01-how-the-pages-fit.md) | (Reading only) server pages, small JS modules, page data |
| 10.2 | [Forms](02-forms.md) | `businesses/forms.py` and saving assumptions |
| 10.3 | [The business views](03-business-views.md) | `businesses/views.py` |
| 10.4 | [The run page view](04-run-page-view.md) | `simulations/views.py`; recording a decision from a run |
| 10.5 | [Connect the addresses](05-connect-the-addresses.md) | Every page's URL, in its final form |
| 10.6 | [The board, a form, demo data](06-board-form-demo-data.md) | Dashboard and "add a business" pages; `seed_kirana` |
| 10.7 | [The business page](07-the-business-page.md) | `detail.html`, plus `ai-actions.js` and `scan.js` |
| 10.8 | [The run pages](08-the-run-pages.md) | `board.html`, `bench.html` and three shared pieces |
| 10.9 | [JavaScript helpers](09-javascript-helpers.md) | (Read) `lib/api.js` and `lib/format.js` |
| 10.10 | [The Idea Bench](10-the-idea-bench.md) | (Read) `bench/main.js` and `bench/charts.js` |
| 10.11 | [The Situation Board](11-the-situation-board.md) | (Read) `board/main.js` |
| 10.12 | [The system view](12-the-system-view.md) | (Read) `topology.js`, the 2D schematic and the 3D scene |
| 10.13 | [Tests and commit](13-tests-and-commit.md) | 20 new tests, and a commit |

When you finish, go to [Part 11 · Deploy](../11-deploy/README.md).
