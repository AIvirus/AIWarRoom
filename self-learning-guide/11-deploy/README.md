# Part 11 · Deploy: GitHub, Docker, the internet

**Time:** about 3–4 hours · **Before this:** [Part 10](../10-interface/README.md)
(your `my-warroom` passes 266 tests).

Your app works on **your** computer. In this part it goes to three places:

```text
 your computer ──git push──► GitHub ──────────────► Render (a server on the internet)
   (the code)                (a safe copy of the     builds your Docker image, runs it,
                              code + automatic        and gives it an https:// address
                              checks on every push)            │
                                                               ├──► Neon (the database)
                                                               └──► Gemini (the AI)
```

| # | Lesson | You will |
|---|---|---|
| 11.1 | [What "deploying" means](01-what-deploying-means.md) | (Reading only) servers, images, containers, secrets |
| 11.2 | [Your code on GitHub](02-your-code-on-github.md) | Push your project, and check no secret went with it |
| 11.3 | [Ready for production](03-ready-for-production.md) | A real web server (gunicorn), static files, a health check |
| 11.4 | [Docker: the image](04-docker-the-image.md) | A `Dockerfile` and `.dockerignore`; build the image |
| 11.5 | [Docker Compose](05-docker-compose.md) | Run the image with its own PostgreSQL, on your computer |
| 11.6 | [Checks on every push](06-checks-on-every-push.md) | GitHub Actions runs ruff, the tests and a Docker build |
| 11.7 | [On the internet](07-on-the-internet.md) | Render + a production Neon database + your key |
| 11.8 | [Tests, checklist, the end](08-tests-checklist-the-end.md) | 5 tests for the deploy files, a safety checklist, and what's next |

## What you need

- A **GitHub** account (free): https://github.com
- **Docker Desktop** (free for personal and educational use): https://www.docker.com/products/docker-desktop/
- A **Render** account (free tier): https://render.com
- Your **Neon** account from Part 3, and your **Gemini** key from Part 7.

Websites change their buttons from time to time. If a screen looks different from these
lessons, look for the same words (for example "New", "Web Service", "Environment").
