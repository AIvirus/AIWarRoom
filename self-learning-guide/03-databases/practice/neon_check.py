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
