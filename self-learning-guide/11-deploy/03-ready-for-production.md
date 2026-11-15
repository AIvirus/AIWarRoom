# 11.3 · Ready for production

**Time:** 30 minutes · **Before this:** [11.2](02-your-code-on-github.md).

## 📖 Read

Four pieces make the app ready for real visitors. Three are already in your project; one
is new.

| Piece | Job | Where |
|---|---|---|
| **gunicorn** | A production web server: several "workers" answer requests side by side, and a stuck one is restarted | **New:** one line in `requirements.txt` |
| **Production settings** | `DEBUG` off, HTTPS only, secure cookies, refuse to start without a secret key or a real database | `config/settings/production.py` (lesson 4.3) |
| **WhiteNoise** | Serves CSS, JS, fonts and Three.js from the app itself, compressed, with long cache times | `requirements.txt` and settings (lesson 4.3) |
| **A health check** | `/healthz/` answers `{"status": "ok"}` if the database answers; the host asks it to know the app is alive | `config/views.py` (lesson 4.8) |

### `collectstatic`

During development, Django finds static files in `static/` as they're asked for. In
production, `python manage.py collectstatic` copies them all **once** into `staticfiles/`,
giving each a name with a fingerprint (`app.3f2a9c.css`). Browsers can then keep them
for a year: when a file changes, its name changes, so nobody gets an old copy. The
Dockerfile (next lesson) runs this while building the image.

### gunicorn doesn't run on Windows

gunicorn uses features only Linux and macOS have. That's fine: it runs **inside** the
Docker container, which is Linux, on any computer. On Windows you keep using `runserver`
for development.

## ⌨️ Do

Add this line at the **end** of `requirements.txt` (it becomes line 12):

<!-- source: requirements.txt:12-12 -->
```text
gunicorn==27.0.1            # production web server (Linux; used inside Docker)
```

Then install it into your virtual environment, so your `requirements.txt` and your
environment agree:

```bash
pip install -r requirements.txt
```

## ✅ Check

```bash
pip show gunicorn
```

The second line says `Version: 27.0.1`. (Don't try to **run** gunicorn on Windows: it
stops with `No module named 'fcntl'`. You'll run it in Docker in lesson 11.5.)

Now look at `config/settings/production.py` again, with the internet in mind:

<!-- source: config/settings/production.py:8-25 -->
```python
DEBUG = False

if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")
if USING_SQLITE_FALLBACK:
    raise ImproperlyConfigured("Production needs DATABASE_URL (PostgreSQL), not SQLite.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_CONTENT_TYPE_NOSNIFF = True

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
```

## 🔍 Line by line

### `requirements.txt`, line 12

- `gunicorn==27.0.1`: the exact version, like every other line (lesson 4.2), so the
  server builds exactly what you tested.

### `production.py`, revisited

- **Line 8** · Never show debug pages to visitors.
- **Lines 10–13** · Refuse to start without a secret key, or on SQLite. A server that
  starts with a missing secret is worse than one that doesn't start.
- **Line 15** · Hosts like Render answer the visitor's HTTPS themselves, then pass the
  request on to your app over plain HTTP with a header `X-Forwarded-Proto: https`. This
  line tells Django to trust that header, so it knows the visitor used HTTPS.
- **Line 16** · Anyone arriving on `http://` is redirected to `https://`.
- **Lines 17–18** · The login and CSRF cookies are only ever sent over HTTPS.
- **Line 19** · **HSTS:** tell browsers "for the next 30 days, only ever use HTTPS for
  this site", even if someone types `http://`.
- **Line 20** · Browsers must trust the declared file type (a script can't be disguised
  as an image).
- **Lines 22–25** · Static files are served by WhiteNoise, compressed, with fingerprinted
  names.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `ERROR: No matching distribution found for gunicorn==27.0.1` | A typo in the line, or no internet. Copy the line again. |
| `pip show gunicorn` prints `WARNING: Package(s) not found` | The virtual environment wasn't active when you ran `pip install`. Activate it and run it again. |

## ❓ Quiz

1. Why can't you use `runserver` on the internet?
2. What does `SECURE_PROXY_SSL_HEADER` let Django know?
3. Why do collected static files get a fingerprint in their name?

---

**Next:** [11.4 · Docker: the image](04-docker-the-image.md)

<details><summary>Quiz answers</summary>

1. It's built for one developer: not for many visitors, not hardened, and it may show
   debug information.
2. That the visitor's connection was HTTPS, even though the host forwards it to the app
   over plain HTTP.
3. So browsers can cache them for a long time, and still get the new file when it
   changes (the name changes).

</details>
