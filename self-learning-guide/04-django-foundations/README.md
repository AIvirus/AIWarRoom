# Part 4 · Django foundations: start AI WarRoom

**Time:** about 4 hours · **Before this:** Parts [1](../01-python/README.md),
[2](../02-web/README.md) and [3](../03-databases/README.md).

From now on you build **your own copy of AI WarRoom** in a folder called `my-warroom`.
At the end of this part, people can sign up, log in, and see a home page, and the code
already makes sure that one organization can never see another organization's data.

Every code block in this part is the **real** project code. Where a file will grow
later in the course, you get a "for now" version, kept in the [`for-now/`](for-now/)
folder of this guide.

## Lessons in this part (do them in order)

| # | Lesson | You will build |
|---|---|---|
| 4.1 | [What Django is](01-what-django-is.md) | (Reading only) the journey of one request |
| 4.2 | [Create the project](02-create-the-project.md) | The `my-warroom` folder, venv, packages, Git, Django's skeleton |
| 4.3 | [Settings, line by line](03-settings.md) | `manage.py` and the four settings files |
| 4.4 | [Shared building blocks](04-shared-building-blocks.md) | `common/`: a base model and the "who can see this" filter |
| 4.5 | [Users and organizations](05-users-and-organizations.md) | The first tables, migrations and the admin site |
| 4.6 | [Who sees what](06-who-sees-what.md) | The one place that decides access |
| 4.7 | [Sign up, log in, and the first API](07-signup-login-api.md) | Forms, views, URLs, an API and one error shape |
| 4.8 | [Pages](08-pages.md) | Templates, the project's URL map, running the site |
| 4.9 | [Tests and your first commit](09-tests-and-commit.md) | 16 tests, the formatter, a Git commit |

When you finish, go to [Part 5 · Business model and API](../05-business-and-api/README.md).
