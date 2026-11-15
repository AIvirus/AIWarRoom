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
