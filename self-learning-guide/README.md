# Build AI WarRoom: a self-learning guide

**Start here. Read this page first.**

This guide teaches you to build a real web application called **AI WarRoom**, starting
from nothing. You don't need to know Python, websites, databases or AI before you begin.
If you can use a computer and read English, you can finish this guide.

---

## What you will build

AI WarRoom is a website that helps a business ask "what if?" before something goes wrong.

- **"What if I start a tiffin (lunch box) business?"** You type in your price, your
  costs and how many customers you hope for. The app shows how much money you would
  have each month for two years, in a good case and a bad case.
- **"What if our payment system stops working for 3 hours?"** You describe an online
  shop. The app shows how many orders would be lost, how much money that costs, and
  compares three ways to respond.
- An **AI helper** (Google's Gemini) explains the results in plain words, and the app
  checks that the AI did not make up any numbers.

By the end, you will understand every line of code in the project.

## How to use this guide

1. **Go in order.** Each lesson uses things from the lessons before it. Skipping ahead
   is like starting a story in the middle.
2. **Every lesson has the same parts:**
   - 📖 **Read:** the idea, explained simply.
   - ⌨️ **Do:** what to type and run, exactly.
   - ✅ **Check:** how to know it worked.
   - 🔍 **Line by line:** every line of code explained.
   - 🛠️ **If it didn't work:** the usual mistakes and how to fix them.
   - ❓ **Quiz:** a few questions. Answers are at the bottom of each lesson.
3. **Type the code yourself.** Don't copy-paste unless the lesson says so. Your fingers
   learn too.
4. **When you see an error, don't panic.** Errors are normal. Every programmer sees
   hundreds a day. Each lesson tells you what the common errors mean.
5. **Tick off each lesson** in the checklist at the bottom of this page.

## The map

Do the parts from top to bottom. The times are rough: going slower is fine.

| Part | Folder | What you learn | Time |
|---|---|---|---|
| 0 | [`00-start-here/`](00-start-here/README.md) | How the guide works; install Python, VS Code and Git; use the terminal | 1 hour |
| 1 | [`01-python/`](01-python/README.md) | Python from zero: values, lists, decisions, functions, classes, money maths, errors, tests | 6 hours |
| 2 | [`02-web/`](02-web/README.md) | What happens when you open a website; HTML, CSS, JavaScript; JSON and APIs | 2 hours |
| 3 | [`03-databases/`](03-databases/README.md) | Tables and SQL; PostgreSQL; your own free database on Neon | 2 hours |
| 4 | [`04-django-foundations/`](04-django-foundations/README.md) | Start AI WarRoom: Django, settings, users, organizations, login | 4 hours |
| 5 | [`05-business-and-api/`](05-business-and-api/README.md) | Save a business and its numbers; build an API | 4 hours |
| 6 | [`06-simulation-engine/`](06-simulation-engine/README.md) | The maths: monthly cash, outages, three ways to respond, tests | 5 hours |
| 7 | [`07-ai-with-gemini/`](07-ai-with-gemini/README.md) | What an LLM is; call Gemini safely; catch made-up numbers | 4 hours |
| 8 | [`08-websites-safely/`](08-websites-safely/README.md) | Read a company website without opening a security hole; live progress | 3 hours |
| 9 | [`09-decisions/`](09-decisions/README.md) | Record a human decision; a printable report | 2 hours |
| 10 | [`10-interface/`](10-interface/README.md) | Pages, sliders, charts and the 3D system view | 5 hours |
| 11 | [`11-deploy/`](11-deploy/README.md) | Put it on GitHub, pack it in Docker, put it on the internet | 3 hours |

Stuck on a word? Look it up in the [glossary](glossary.md).

## Two folders, two jobs

When you work through this guide you will have two copies of AI WarRoom:

| Folder | What it is |
|---|---|
| **The reference project** (the folder that contains this guide) | The finished app. Look at it when you're stuck. Don't edit it. |
| **Your project** (`my-warroom`, which you create in Part 4) | The one you build, line by line, by following the lessons. |

If your code doesn't work and you can't see why, compare your file with the same file in
the reference project. The lessons always tell you which file and which lines.

## Your checklist

Copy this into a notebook or tick it here.

- [ ] Part 0: Start here
- [ ] Part 1: Python from zero
- [ ] Part 2: How the web works
- [ ] Part 3: Databases
- [ ] Part 4: Django foundations
- [ ] Part 5: Business model and API
- [ ] Part 6: Simulation engine
- [ ] Part 7: AI with Gemini
- [ ] Part 8: Reading websites safely
- [ ] Part 9: Decisions and reports
- [ ] Part 10: The interface
- [ ] Part 11: GitHub, Docker and deployment

**Ready? Open [`00-start-here/README.md`](00-start-here/README.md).**

---

<sub>For teachers: `python self-learning-guide/tools/check_guide.py` (run from the
project folder) checks that every code block copied from the project still matches the
real file.</sub>
