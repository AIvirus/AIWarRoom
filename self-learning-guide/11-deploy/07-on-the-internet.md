# 11.7 · On the internet

**Time:** 60 minutes · **Before this:** [11.6](06-checks-on-every-push.md).

## Read

Render will read your repository from GitHub, build the `Dockerfile`, and run the image
with **environment variables** you type into its dashboard. Every later `git push` to
`main` builds and deploys again by itself.

You need six values. Write them in a private note as you go (never in a file in your
project):

| Variable | Value | Why |
|---|---|---|
| `DJANGO_SECRET_KEY` | A **new** long random text (step 2) | Signs logins; must not be your laptop's |
| `DATABASE_URL` | Your **production** Neon connection string (step 1) | A separate database from the one you practise on |
| `DJANGO_ALLOWED_HOSTS` | `your-app-name.onrender.com` | Django only answers requests for these host names (lesson 4.3) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://your-app-name.onrender.com` | Forms are only accepted from your own site |
| `GEMINI_API_KEY` | Your key from Part 7 | The AI features |
| `AI_DAILY_CALL_BUDGET` | `50` | A cap on AI calls per day (lesson 7.7): anyone who signs up on a public site uses **your** quota |

`DJANGO_SETTINGS_MODULE` is already set to production inside the image, and `PORT` is set
by Render (to 10000).

## Do

### 1. A production database on Neon

1. Open **https://console.neon.tech** and your project from Part 3.
2. Find **Databases** (in the sidebar or the branch's page) → **New database**. Name it
   `warroom_prod`.
3. Click **Connect**, choose the database `warroom_prod`, and copy the connection string.
   It looks like `postgresql://...@...neon.tech/warroom_prod?sslmode=require`. That's your
   `DATABASE_URL`.

It's empty: the container's start command will create the tables (`migrate`) on the first
deploy.

### 2. A new secret key

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

It prints a line of about 67 random letters, digits, `-` and `_`. That's your
`DJANGO_SECRET_KEY`. (Run it again and you get a different one: that's the point.)

### 3. A web service on Render

1. Go to **https://render.com** and sign up **with GitHub** (it can then see your
   repositories).
2. **New** → **Web Service**. Under "Git Provider", pick `my-warroom`. (If it isn't
   listed, use "Configure account" to give Render access to that repository.)
3. Fill in:
   - **Name:** something unique, for example `warroom-priya`. Your address will be
     `https://warroom-priya.onrender.com`.
   - **Language** (or Runtime): **Docker**. Render finds your `Dockerfile` by itself.
   - **Branch:** `main`.
   - **Region:** the one closest to your users (for India: **Singapore**).
   - **Instance Type:** **Free**.
4. Under **Environment Variables**, add the six from the table above, one by one. For the
   two host lines, use **your** Name.
5. Click **Create Web Service** (or **Deploy Web Service**).

### 4. Watch it deploy

Render shows the **logs** live: the same `#1`, `#2`... build steps as on your computer
(slower the first time), then your container starting:

```text
Operations to perform:
  Apply all migrations: accounts, admin, auth, businesses, contenttypes, decisions, intelligence, sessions, simulations
Running migrations:
  Applying accounts.0001_initial... OK
...
[INFO] Listening at: http://0.0.0.0:10000
```

Then "Your service is live ".

## Check

1. Open `https://your-app-name.onrender.com/healthz/` →
   `{"status": "ok", "database": "postgresql"}`. Your app on the internet, talking to
   Neon.
2. Open `https://your-app-name.onrender.com/` → **Sign up**, make your account, add a
   business. Note the padlock in the address bar: HTTPS, with a certificate Render provides.
3. Try `http://` (without the s): you're sent to `https://` (lesson 11.3, line 16).
4. Ask the analyst for a reading on a run: Gemini works with the key you set.
5. **Demo data (optional).** The free plan has no shell, but you can run the seed command
   from **your computer** against the production database, by setting `DATABASE_URL` for
   that one command (it wins over `.env`, lesson 4.3). Use the email you signed up with.

   Windows PowerShell:

   ```bash
   $env:DATABASE_URL="paste-your-production-url"; python manage.py seed_kirana --email you@example.com; Remove-Item Env:DATABASE_URL
   ```

   Mac or Linux:

   ```bash
   DATABASE_URL="paste-your-production-url" python manage.py seed_kirana --email you@example.com
   ```

   Reload the live site: Kirana Express and Tiffin Box Co. are there.
6. **A new version.** Change something small (the board's empty-state text, say), commit
   and `git push`. GitHub's checks run (lesson 11.6), Render builds and deploys again, and
   a few minutes later the live site shows your change.

The free plan **sleeps** after 15 minutes without visitors. The next visit shows a loading
page for about a minute while it wakes up. That's normal.

## Line by line

| Step | What happens behind it |
|---|---|
| A separate `warroom_prod` database | Your laptop (and its experiments) never touches the real data, and the other way round. |
| A new secret key | If your laptop's `.env` ever leaked, the live site's logins would still be safe. |
| Runtime: Docker | Render runs `docker build` with your `Dockerfile`, exactly as you did in 11.4. |
| Environment variables | Render gives them to the container; `base.py`'s `env_str` reads them (`.env` doesn't exist in the image). |
| The logs | The container's output: `migrate` from the Dockerfile's `CMD`, then gunicorn's lines. |
| `Listening at ...:10000` | Render set `PORT=10000`; the `CMD` binds gunicorn to it. |
| HTTPS | Render's front door holds the certificate and passes requests on with `X-Forwarded-Proto: https` (lesson 11.3, line 15). |

## If it didn't work

| You see | Fix |
|---|---|
| The page says **Bad Request (400)** | `DJANGO_ALLOWED_HOSTS` doesn't match the address. Render may have added letters to a taken name (`warroom-priya-x7k2.onrender.com`): copy the address from the top of the service page into both host variables. Saving them redeploys. |
| **CSRF verification failed** when you sign up | `DJANGO_CSRF_TRUSTED_ORIGINS` must be the address **with** `https://` and nothing after `.com`. |
| Logs: `ImproperlyConfigured: DJANGO_SECRET_KEY must be set` | The variable is missing or misspelt. |
| Logs: `Production needs DATABASE_URL (PostgreSQL), not SQLite.` | `DATABASE_URL` is missing, empty, or you also set `USE_SQLITE=True`. |
| Logs: `connection ... failed` or `password authentication failed` | The Neon URL was copied wrong, or for the wrong database. Copy it again from **Connect**. |
| `/healthz/` says `"status": "error"` | The app runs but can't reach Neon. Same fix as above. |
| "Ask the analyst" says the AI is unavailable | `GEMINI_API_KEY` is missing on Render, or today's budget is used up. |
| The build fails at `pip install` | Open the log: a typo in `requirements.txt`? It must build on your computer first (11.4). |

## Quiz

1. Why a separate production database and a new secret key?
2. Who sets `PORT`, and how does gunicorn know it?
3. Your friend signs up on your live site and asks the AI 200 questions. What stops them
   using up your whole free quota?

---

**Next:** [11.8 · Tests, checklist, the end](08-tests-checklist-the-end.md)

<details><summary>Quiz answers</summary>

1. So practice never touches real data, and a leak of your laptop's `.env` can't affect
   the live site.
2. Render sets it to 10000; the Dockerfile's `CMD` binds to `0.0.0.0:${PORT}`.
3. `AI_DAILY_CALL_BUDGET`: after 50 calls in a day, AI features politely stop until
   tomorrow; simulations keep working (lesson 7.7).

</details>
