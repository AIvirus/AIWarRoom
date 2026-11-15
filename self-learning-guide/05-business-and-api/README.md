# Part 5 · Business model and API

**Time:** about 4 hours · **Before this:** [Part 4](../04-django-foundations/README.md)
(your `my-warroom` passes 16 tests).

In Part 4 people could sign up and log in, but there was nothing to *do*. In this part
you give AI WarRoom its memory:

- a **business** (an idea like "a tiffin service", or a running online shop),
- its **numbers** (price, costs, daily orders...), each with a unit and a source,
- its **parts** (payment gateway, warehouse, courier...) and which part needs which,
- **scenarios** ("what if the warehouse shuts for 6 hours?") and a place to keep
  every **run** of the maths (the maths itself comes in Part 6).

And you build the **API** that lets a program (our own pages in Part 10, or you in the
browser console) create and read all of it, always only inside your own organization.

Every code block is the **real** project code. Two files will grow in later parts, so
you get "for now" versions of them from the [`for-now/`](for-now/) folder:

| File | For now it leaves out | Added back in |
|---|---|---|
| `businesses/api.py` | The website scan and the AI committee | Parts 7 and 8 |
| `simulations/api.py` | Running a scenario and the AI analysis | Parts 6 and 7 |
| `config/urls.py` | Scans, decisions, reports and the real pages | Parts 6–10 |

## Lessons in this part (do them in order)

| # | Lesson | You will build |
|---|---|---|
| 5.1 | [What we are building](01-what-we-build.md) | (Reading only) the six new tables and the new API addresses |
| 5.2 | [The catalogue](02-the-catalogue.md) | `simulation_engine/catalog.py`: every number the app understands |
| 5.3 | [Business tables](03-business-models.md) | `businesses/models.py`, the loop check, migrations, the admin |
| 5.4 | [Serializers](04-serializers.md) | `businesses/serializers.py`: JSON in, checked Python out |
| 5.5 | [The business API](05-business-api.md) | `businesses/api.py`: list, create, archive, numbers, parts |
| 5.6 | [Scenarios and runs](06-scenarios-and-runs.md) | The `simulations` app: tables, serializers, admin, API |
| 5.7 | [Wire it up and try it](07-urls-and-try-it.md) | `config/urls.py`, then real requests from the browser console |
| 5.8 | [Tests and commit](08-tests-and-commit.md) | 36 new tests (52 in total), ruff, a Git commit |

When you finish, go to [Part 6 · The simulation engine](../06-simulation-engine/README.md).
