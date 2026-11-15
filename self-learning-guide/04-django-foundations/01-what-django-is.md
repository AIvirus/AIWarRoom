# 4.1 · What Django is

**Time:** 20 minutes · **Before this:** Parts 1–3. Reading only, no typing.

## 📖 Read

**Django** is a Python package for building websites. It's called a **framework**: a
ready-made skeleton, with the hard, boring, risky parts already solved, such as
passwords, sessions, security, talking to the database, and forms. You fill in the parts
that make **your** site special.

Big sites have used Django for years, including Instagram's early versions and many
government and newspaper sites.

### The journey of one request

When someone opens `http://127.0.0.1:8000/accounts/login/`, this happens:

```text
Browser ──request──▶ Django
                        │
                        ▼
                 1. urls.py      "Which code handles /accounts/login/?"
                        │
                        ▼
                 2. a view       A Python function or class that decides what to do
                        │   ╲
                        │    ╲──▶ 3. models   Read or save data in the database
                        ▼
                 4. a template   An HTML file with gaps for the data
                        │
Browser ◀──response── HTML page
```

| Piece | File | Job | Restaurant comparison |
|---|---|---|---|
| **URLs** | `urls.py` | A map from addresses to views | The menu: "dosa → kitchen station 3" |
| **View** | `views.py` | Handles one kind of request | The cook at that station |
| **Model** | `models.py` | One Python class = one database table | The store room |
| **Template** | `templates/*.html` | HTML with gaps to fill in | The plate it's served on |

### Projects and apps

- A Django **project** is the whole website (`my-warroom`).
- A project is split into **apps**: folders that each own one area. AI WarRoom has:

| App | Owns |
|---|---|
| `accounts` | People, organizations, login (this part) |
| `businesses` | A business and its numbers (Part 5) |
| `simulations` | Scenarios and runs (Part 6) |
| `intelligence` | The AI, website scans and alerts (Parts 7–8) |
| `decisions` | Decisions and reports (Part 9) |

Plus two folders that aren't apps in the usual sense:
- `config`: settings and the main URL map.
- `common`: small building blocks shared by every app.

### Django REST Framework (DRF)

Django builds web **pages**. **DRF** is an extra package that builds **APIs** (lesson 2.3):
URLs that answer with JSON. AI WarRoom uses both: pages for people, and an API for the
sliders, the 3D view and tools like Postman.

## ❓ Quiz

1. In the request journey, which piece decides which view runs?
2. What does a model represent?
3. Which app will hold the login code?

---

**Next:** [4.2 · Create the project](02-create-the-project.md)

<details><summary>Quiz answers</summary>

1. `urls.py`, the URL map.
2. One database table (each object is one row).
3. `accounts`.

</details>
