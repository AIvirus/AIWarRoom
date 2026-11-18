# 3.3 · PostgreSQL and your free Neon database

**Time:** 40 minutes · **Before this:** [3.2](02-sql-by-hand.md).

## Read

SQLite is great for practice, but real websites use a **database server**: a separate
program that many users and many copies of the website can use at once. AI WarRoom uses
**PostgreSQL** (said "post-gres-Q-L", or just "Postgres"), a free and very popular one.

Running Postgres yourself is work. **Neon** is a company that runs Postgres for you **in
the cloud**, with a free plan:

- 1 GB of storage per project, which is plenty for this course.
- No credit card needed.
- It **"scales to zero"**: when nobody uses it for 5 minutes it goes to sleep, and the
  next request wakes it up (the first one takes a second or two longer).

### The connection string, and keeping secrets

To connect, your program needs one long line called a **connection string**:

```text
postgresql://alex:AbC123dEf@ep-cool-darkness-a1b2c3d4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

| Part | Meaning |
|---|---|
| `postgresql://` | It's a Postgres database |
| `alex:AbC123dEf` | Username and **password** |
| `ep-cool-darkness-...neon.tech` | The server's address |
| `/neondb` | Which database on that server |
| `?sslmode=require&...` | Settings: always encrypt the connection |

**This string contains your password. It is a secret.**

- **Never** paste it into your code.
- **Never** put it on GitHub. People run robots that search GitHub for leaked passwords
  within minutes.
- Instead, put it in a file called **`.env`**, and tell Git to ignore that file (Part 4
  shows how). Your code reads it from there.

## Do

### Step 1 · Make your Neon database

1. Go to **https://neon.com** and click **Sign up**. Signing up with your Google or GitHub
   account is easiest.
2. Create a **project**:
   - **Project name:** `my-warroom`.
   - **Region:** pick the one closest to you. In India, choose **AWS Asia Pacific
     (Singapore)**. A nearer region makes every page faster.
   - Leave the Postgres version as it is.
3. Click the **Connect** button in the Console. A box called **Connect to your branch**
   opens.
4. Leave everything as it is and **copy the connection string**.

### Step 2 · Save it in `.env`

In your `databases` folder, create a file named exactly **`.env`** (dot, then env, no
other extension) containing one line:

```text
DATABASE_URL=postgresql://...paste your whole string here...
```

### Step 3 · Connect from Python

Activate your venv from lesson 1.7, or make a new one in this folder, then install two
packages:

```bash
pip install "psycopg[binary]" python-dotenv
```

Make `neon_check.py`:

<!-- source: self-learning-guide/03-databases/practice/neon_check.py:1-16 -->
```python
# Check that Python can reach your PostgreSQL database on Neon.
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is missing. Put it in a file called .env (see lesson 3.3).")

with psycopg.connect(url) as connection:
    row = connection.execute("SELECT version()").fetchone()
    print("Connected! The database says:")
    print(row[0])
```

```bash
python neon_check.py
```

## Check

```text
Connected! The database says:
PostgreSQL 18.7 on aarch64-unknown-linux-gnu, compiled by gcc ...
```

The version number may be different. Any "Connected!" means it works. If it took a few
seconds, the database was asleep and just woke up.

## Line by line

**Line 2** · `import os` gives access to the operating system, including **environment
variables**: named settings a program can read.

**Line 4** · `psycopg` is the package that lets Python talk to Postgres. Django uses it
too.

**Line 5** · `load_dotenv` comes from the `python-dotenv` package.

**Line 7** · `load_dotenv()` reads the `.env` file in the current folder and turns each
`NAME=value` line into an environment variable.

**Line 8** · `os.environ.get("DATABASE_URL")` reads the variable. `.get` gives `None`
instead of crashing if it's missing.

**Lines 9–10** · If it's missing, stop with a clear message. `raise SystemExit("...")`
ends the program and prints the message.

**Line 12** · `with psycopg.connect(url) as connection:`
- Opens a connection to Neon.
- `with` means "when the indented block finishes, close the connection automatically,
  even if an error happens". Always use `with` for things that must be closed.

**Line 13** · Run the SQL `SELECT version()` (ask Postgres its version) and fetch the one
row it returns.

**Lines 14–15** · Print it. `row[0]` is the first (and only) column of that row.

**The install command** · `pip install "psycopg[binary]" python-dotenv`: `[binary]` asks
for a ready-built version, so nothing needs compiling. The quotes stop some terminals
from misreading the square brackets.

## If it didn't work

| You see | Fix |
|---|---|
| `DATABASE_URL is missing` | The file must be named exactly `.env` (Windows may secretly add `.txt`: in VS Code check the name in the Explorer), it must be in the folder you run from, and the line must start `DATABASE_URL=`. |
| `password authentication failed` | The string was copied incompletely. Copy it again from **Connect**. |
| `could not translate host name` | Check your internet, and that no space or line break got into the string. |
| `connection timeout` on a school/office network | Some networks block database ports. Try a phone hotspot. |

## Quiz

1. Why do we use Neon instead of SQLite for the real app?
2. Where must the connection string **never** go?
3. What does `with` do on line 12?

---

**Part 3 done! ** Next: [Part 4 · Django foundations](../04-django-foundations/README.md)

<details><summary>Quiz answers</summary>

1. Neon runs a real Postgres server that many users and copies of the site can share,
   and it lives online, not just on your laptop.
2. Into your code, or anywhere on GitHub.
3. Closes the connection automatically when the block ends, even after an error.

</details>
