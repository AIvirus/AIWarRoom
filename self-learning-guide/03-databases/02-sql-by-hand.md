# 3.2 · SQL by hand

**Time:** 45 minutes · **Before this:** [3.1](01-what-is-a-database.md).

## Read

**SQL** (Structured Query Language, said "S-Q-L" or "sequel") is the language for talking
to relational databases. Five commands cover most needs:

| SQL | Meaning |
|---|---|
| `CREATE TABLE` | Make a new table and say what columns it has |
| `INSERT` | Add a row |
| `SELECT` | Find and read rows |
| `UPDATE` | Change rows |
| `DELETE` | Remove rows |

SQL keywords are usually written in CAPITALS so they stand out. That's a habit, not a
rule.

In Part 4 you'll meet Django, which **writes SQL for you** from Python code. You still
need to know what SQL is, because it's what really happens underneath, and error
messages often show it.

We'll practise with **SQLite**, a small database built into Python. No install needed.

## Do

Make a folder `databases` in your `learning` folder, and in it `sql_practice.py`:

<!-- source: self-learning-guide/03-databases/practice/sql_practice.py:1-46 -->
```python
# Learn SQL with SQLite, a small database built into Python.
import sqlite3

db = sqlite3.connect(":memory:")

db.execute("""
    CREATE TABLE stalls (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        city TEXT NOT NULL
    )
""")
db.execute("""
    CREATE TABLE sales (
        id INTEGER PRIMARY KEY,
        stall_id INTEGER NOT NULL REFERENCES stalls(id),
        day TEXT NOT NULL,
        cups INTEGER NOT NULL
    )
""")

db.execute("INSERT INTO stalls (name, city) VALUES ('Raju Chai', 'Pune')")
db.execute("INSERT INTO stalls (name, city) VALUES ('Meena Tea', 'Nashik')")
db.executemany(
    "INSERT INTO sales (stall_id, day, cups) VALUES (?, ?, ?)",
    [(1, "Mon", 110), (1, "Tue", 125), (2, "Mon", 90), (2, "Tue", 140)],
)

print(db.execute("SELECT name, city FROM stalls").fetchall())
print(db.execute("SELECT day, cups FROM sales WHERE cups > 100").fetchall())

db.execute("UPDATE stalls SET city = 'Mumbai' WHERE name = 'Meena Tea'")
print(db.execute("SELECT city FROM stalls WHERE id = 2").fetchone())

rows = db.execute("""
    SELECT stalls.name, SUM(sales.cups)
    FROM sales
    JOIN stalls ON stalls.id = sales.stall_id
    GROUP BY stalls.name
    ORDER BY stalls.name
""").fetchall()
print(rows)

unsafe_name = "x'; DROP TABLE stalls; --"
safe = db.execute("SELECT id FROM stalls WHERE name = ?", (unsafe_name,)).fetchall()
print("Rows matching a tricky name:", safe)
```

```bash
python sql_practice.py
```

## Check

```text
[('Raju Chai', 'Pune'), ('Meena Tea', 'Nashik')]
[('Mon', 110), ('Tue', 125), ('Tue', 140)]
('Mumbai',)
[('Meena Tea', 230), ('Raju Chai', 235)]
Rows matching a tricky name: []
```

## Line by line

**Line 2** · `import sqlite3` loads Python's built-in SQLite tools.

**Line 4** · `sqlite3.connect(":memory:")` opens a database. `":memory:"` is a special
name meaning "keep it in memory only, and throw it away when the program ends", which is
perfect for practice. (A file name like `"shop.db"` would save it on disk.) We call the
connection `db`.

**Line 6** · `db.execute(...)` sends one SQL command to the database. The triple quotes
`"""` let the SQL span several lines.

**Line 7** · `CREATE TABLE stalls (` makes a table called `stalls`.

**Line 8** · `id INTEGER PRIMARY KEY`: a whole-number column that's the primary key.
SQLite fills it in automatically (1, 2, 3...) when we don't give one.

**Line 9** · `name TEXT NOT NULL`: a text column. `NOT NULL` means "must always have a
value"; the database refuses a stall with no name.

**Line 10** · The same for `city`.

**Lines 13–20** · The `sales` table. The key line is **16**:
`stall_id INTEGER NOT NULL REFERENCES stalls(id)` is a **foreign key**: it must be the
`id` of a row in `stalls`.

**Line 22** · `INSERT INTO stalls (name, city) VALUES ('Raju Chai', 'Pune')`: add a row.
First the column names, then the values in the same order. In SQL, text goes in
**single** quotes.

**Line 23** · Add Meena. She gets id 2.

**Lines 24–27** · `executemany` runs one command many times, once per item of the list.
The `?` marks are **placeholders**: SQLite fills them, in order, from each tuple
(`(1, "Mon", 110)` → stall 1, Mon, 110 cups).

**Line 29** · `SELECT name, city FROM stalls` reads those two columns from every row.
`.fetchall()` collects all the results into a list of tuples.

**Line 30** · `WHERE cups > 100` keeps only rows that match the condition. Monday at
Meena's (90) is left out.

**Line 32** · `UPDATE stalls SET city = 'Mumbai' WHERE name = 'Meena Tea'`: change a
value, but **only** in the rows matching `WHERE`. An `UPDATE` without `WHERE` changes
**every** row.

**Line 33** · `.fetchone()` returns just the first result: `('Mumbai',)`. The comma shows
it's a one-item tuple.

**Lines 35–41** · A **JOIN** combines two tables:
- `FROM sales JOIN stalls ON stalls.id = sales.stall_id` pairs each sale with its stall
  by matching the id.
- `SUM(sales.cups)` adds up cups...
- ...`GROUP BY stalls.name`: one total per stall.
- `ORDER BY stalls.name` sorts the results alphabetically.

**Line 42** · Meena 90 + 140 = 230; Raju 110 + 125 = 235.

**Lines 44–46** · **Why placeholders matter (security!).** `unsafe_name` is a nasty piece
of text that *looks like* SQL. If we glued it straight into the command with `+`, the
database might run `DROP TABLE stalls` and delete our data. This attack is called
**SQL injection**. With a `?` placeholder, the database treats the value as plain text,
never as a command: it just finds no stall with that strange name, so we get `[]`.
**Rule: never build SQL by gluing in user text.** Django always uses placeholders for
you.

## If it didn't work

| You see | It means |
|---|---|
| `sqlite3.OperationalError: no such table: stalls` | The `CREATE TABLE` didn't run before the `INSERT`. Check the order. |
| `sqlite3.OperationalError: near "...": syntax error` | A typo in the SQL, often a missing comma between columns. |
| `sqlite3.IntegrityError: NOT NULL constraint failed` | You tried to save a row without a required value. That's the database protecting you. |

## Quiz

1. Which SQL command reads data?
2. What's dangerous about `UPDATE stalls SET city = 'Delhi'` (with no WHERE)?
3. Why use `?` placeholders instead of `+` to put a name into SQL?

---

**Next:** [3.3 · PostgreSQL and your free Neon database](03-postgresql-and-neon.md)

<details><summary>Quiz answers</summary>

1. `SELECT`.
2. It changes **every** stall's city to Delhi.
3. To prevent SQL injection: the value can never be run as a command.

</details>
