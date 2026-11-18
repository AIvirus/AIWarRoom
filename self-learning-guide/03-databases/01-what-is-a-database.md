# 3.1 · What a database is

**Time:** 20 minutes · **Before this:** [Part 2](../02-web/README.md).

## Read

A **database** is an organised, permanent store of information. The most common kind,
the kind AI WarRoom uses, is a **relational database**: information is kept in
**tables**, a lot like sheets in Excel.

### Tables, rows and columns

Here is a table called `stalls`:

| id | name | city |
|---|---|---|
| 1 | Raju Chai | Pune |
| 2 | Meena Tea | Nashik |

- The **table** holds one kind of thing (stalls).
- Each **row** is one thing (one stall). Also called a **record**.
- Each **column** is one fact about every thing (its name, its city). Every value in a
  column has the same type: all text, or all numbers.

### Keys: how rows find each other

- A **primary key** is a column whose value is **unique** for every row, like a roll
  number in a school. Here it's `id`. No two stalls ever share an id.
- A **foreign key** is a column that **points to** a row in another table.

Here is a second table, `sales`:

| id | stall_id | day | cups |
|---|---|---|---|
| 1 | 1 | Mon | 110 |
| 2 | 1 | Tue | 125 |
| 3 | 2 | Mon | 90 |

`stall_id` is a foreign key: `1` means "Raju Chai's sale". Instead of writing "Raju Chai"
again on every sale, we store his id. If Raju renames his stall, we change **one** row,
not hundreds.

This kind of link is called a **one-to-many relationship**: one stall has many sales.

### In AI WarRoom

The real app has tables like these:

```text
Organization ──< BusinessProfile ──< FinancialAssumption
                        │
                        ├──< Scenario ──< SimulationRun ──< SimulationResult
                        └──< Decision
```

`──<` means "one to many": one organization has many businesses; one business has many
assumptions; and so on. You'll create every one of these tables yourself in Parts 4–9.

### Why not just save to a file?

| A file | A database |
|---|---|
| Two people saving at once can overwrite each other | Handles many users at once, safely |
| To find one thing you read the whole file | Finds rows fast, even among millions |
| Nothing stops bad data (a price of "hello") | Checks rules: types, "not empty", "must exist" |
| If the program crashes mid-save, the file can break | Changes are all-or-nothing (a **transaction**) |

## Quiz

1. What's the difference between a row and a column?
2. Why does `sales` store `stall_id` instead of the stall's name?
3. In AI WarRoom, one business has many... what? Name two.

---

**Next:** [3.2 · SQL by hand](02-sql-by-hand.md)

<details><summary>Quiz answers</summary>

1. A row is one thing (one stall); a column is one fact about every thing (all the
   cities).
2. So the name lives in one place. Change it once and every sale still points to the
   right stall.
3. Any two of: assumptions, scenarios, runs, decisions, components, scans, alerts.

</details>
