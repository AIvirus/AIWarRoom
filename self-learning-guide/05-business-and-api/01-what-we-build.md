# 5.1 · What we are building

**Time:** 20 minutes · **Before this:** [Part 4](../04-django-foundations/README.md).
**Reading only:** no typing in this lesson.

## Read

### Two kinds of business

AI WarRoom helps two kinds of people. The app calls them **modes**:

| Mode | Who | Example question |
|---|---|---|
| `idea` | Someone who hasn't started yet | "If I sell tiffins at ₹120, will I run out of money?" |
| `operating` | A shop that is already running | "If our courier stops for 6 hours, how much do we lose?" |

A business picks its mode when it is created and **never changes it**. The numbers an
idea needs (conversion rate, retention...) are different from the numbers a running
shop needs (daily orders, warehouse share...), so changing mode would leave nonsense
behind.

### The six new tables

```text
Organization (Part 4)
  └── BusinessProfile          "Kirana Express", mode = operating
        ├── FinancialAssumption    daily_orders = 2400 orders/day (source: user)
        ├── BusinessComponent      "Warehouse", criticality 5, depends on ...
        └── Scenario               "Bhiwandi flood" = warehouse_shutdown, outage_hours = 6
              └── SimulationRun        one run of the maths, with a frozen copy of the inputs
                    └── SimulationResult   one row per case: "wait", "backup", ...
```

Read the arrows as "has many". An organization has many businesses; a business has many
assumptions; and so on. Every row hangs off an organization somewhere up the tree, which
is exactly how the "who sees what" rule from lesson 4.6 finds its owner.

| Table | One row is... | App |
|---|---|---|
| `BusinessProfile` | one business | `businesses` |
| `FinancialAssumption` | one number about it, like `daily_orders = 2400` | `businesses` |
| `BusinessComponent` | one part of the operation, like "Payment gateway" | `businesses` |
| `Scenario` | one "what if?" question | `simulations` |
| `SimulationRun` | one time the maths answered that question | `simulations` |
| `SimulationResult` | one line of that answer ("if we wait", "if we switch") | `simulations` |

### The catalogue: one rulebook for every number

What is a valid conversion rate? 2.5 is fine (it means 2.5 %). 120 is not (more than
100 %). What about `convertion_rate` (spelt wrong)? It must be **refused**, otherwise it
quietly becomes a number nobody ever reads.

These rules live in **one plain Python file**, `simulation_engine/catalog.py`, with no
Django in it. The database, the API, the maths and the tests all ask that one file. That
is lesson 5.2.

### The new API addresses

By the end of this part your app answers all of these (always only for your own
organization):

| Method and address | Does |
|---|---|
| `GET /api/v1/businesses/` | List my businesses |
| `POST /api/v1/businesses/` | Create a business |
| `GET` · `PATCH` · `DELETE /api/v1/businesses/<id>/` | Read, change, archive one |
| `GET` · `PUT /api/v1/businesses/<id>/assumptions/` | Read or save its numbers |
| `GET` · `POST /api/v1/businesses/<id>/components/` | List or add its parts |
| `GET` · `PATCH` · `DELETE /api/v1/businesses/<id>/components/<id>/` | One part |
| `GET` · `POST /api/v1/scenarios/` | List or create scenarios |
| `GET` · `PATCH` · `DELETE /api/v1/scenarios/<id>/` | One scenario |
| `GET /api/v1/runs/` and `/api/v1/runs/<id>/` | Past runs (read only) |
| `GET /api/v1/scenario-templates/` | The kinds of scenario, with their settings |
| `GET /api/v1/inputs/` | Every number the app understands |

Remember the HTTP methods from Part 2: **GET** reads, **POST** creates, **PUT** replaces,
**PATCH** changes some fields, **DELETE** removes (here it *archives*, as you'll see).

### Four new ideas you'll meet

| Idea | In one line |
|---|---|
| **Serializer** | Turns JSON from the internet into checked Python values, and Python objects back into JSON. |
| **ViewSet** | One class that answers list, create, read, change and delete for a table. |
| **Router** | Makes the URL addresses for a ViewSet automatically. |
| **Many-to-many** | A link where each side can have many of the other: a part can depend on many parts, and be needed by many. |

## Quiz

1. Why can't a business change its mode?
2. Which table holds "warehouse shutdown for 6 hours"?
3. Why is `convertion_rate` refused instead of saved?

---

**Next:** [5.2 · The catalogue](02-the-catalogue.md)

<details><summary>Quiz answers</summary>

1. Each mode uses different numbers; switching would leave numbers that make no sense.
2. `Scenario` (template `warehouse_shutdown`, parameter `outage_hours = 6`).
3. It's not in the catalogue. Saving it would create a number the maths never reads,
   and you'd think you had set the conversion rate when you hadn't.

</details>
