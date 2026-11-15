# 11.1 · What "deploying" means

**Time:** 25 minutes · **Before this:** [Part 10](../10-interface/README.md).
**Reading only.**

## 📖 Read

### From "works on my computer" to "works for everyone"

`python manage.py runserver` is a **development** server: one person, one computer,
helpful error pages. On the internet you need:

| On your computer | On the internet |
|---|---|
| `runserver` | **gunicorn**, a web server built for many visitors at once |
| `DEBUG=True`: yellow error pages with your code inside | `DEBUG=False`: a plain error page; details only in the logs |
| http://127.0.0.1:8000 | **https://** with a certificate, so passwords travel encrypted |
| `.env` file | **Environment variables** set in the host's dashboard |
| Django serves CSS and JS for you | Files collected once (`collectstatic`), served by WhiteNoise |

Your project already has `config/settings/production.py` (lesson 4.3), which switches
all of this on and **refuses to start** without a secret key and a real database.

### Docker: ship the whole box

"It works on my computer" fails on servers for silly reasons: a different Python, a
missing system library, a different operating system. **Docker** solves this by shipping
the computer's **contents** along with your code.

| Word | Meaning | Like... |
|---|---|---|
| **Dockerfile** | A recipe: start from Python 3.12 on Linux, install the requirements, copy the code, collect static files | A recipe card |
| **Image** | The result of following the recipe once: a frozen box with everything inside | A cake in a tin |
| **Container** | An image **running**. You can run many containers from one image | A slice being eaten |
| **Docker Compose** | Start several containers together (the app and a database) with one command | A meal: several dishes, served together |

The same image runs on your laptop and on the server. If it works in Docker on your
computer, it will very likely work on the internet.

### Secrets never travel with the code

Your `.env` holds your secret key, database password and Gemini key. It must **never**
reach GitHub or a Docker image:

- `.gitignore` keeps it out of Git (since Part 4).
- `.dockerignore` keeps it out of the image (this part).
- On the server, you type each secret into the host's dashboard as an **environment
  variable**. Django reads them the same way it reads `.env` (lesson 4.3).

If a secret ever leaks (pasted in a chat, pushed by mistake), **change it**: make a new
key, a new database password. Deleting the file afterwards isn't enough, because Git and
GitHub remember history.

### Where we'll put it

- **GitHub** stores your code, shows it to others (or keeps it private), and runs
  automatic checks on every change ("CI", continuous integration).
- **Render** reads your code from GitHub, builds the Docker image, runs it, and gives you
  an `https://...onrender.com` address. Its free plan is fine for a class: the app sleeps
  after 15 minutes without visitors and takes about a minute to wake up.
- **Neon** is your database, as before, but a **separate** one for production, so testing
  on your laptop never touches real data.

## ❓ Quiz

1. What is the difference between an image and a container?
2. Why is `DEBUG=False` important on the internet?
3. Your Gemini key was pushed to GitHub by mistake. Is deleting the file enough?

---

**Next:** [11.2 · Your code on GitHub](02-your-code-on-github.md)

<details><summary>Quiz answers</summary>

1. An image is the frozen box; a container is that box running.
2. Debug pages show your code, settings and data to anyone who causes an error.
3. No. It stays in Git's history. Make a new key in AI Studio and delete the old one.

</details>
