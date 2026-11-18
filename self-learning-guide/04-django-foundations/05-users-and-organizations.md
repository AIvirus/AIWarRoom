# 4.5 · Users and organizations

**Time:** 45 minutes · **Before this:** [4.4](04-shared-building-blocks.md).

## Read

AI WarRoom needs three tables to answer "who is this, and what may they see?":

| Table | One row is... |
|---|---|
| **User** | A person who logs in with an email and password |
| **Organization** | A company or founder team. It owns businesses, runs and decisions. |
| **Membership** | "This user belongs to this organization, with this role (owner or member)" |

```text
User ──< Membership >── Organization
```

A Membership row is a **link** between one user and one organization. Every access check
in the whole app goes through these links (lesson 4.6).

### Migrations

When you write or change a model, the database doesn't change by itself. Django makes a
**migration**: a small Python file that describes the change ("create a table with these
columns"). Then **migrate** applies it to the database.

| Command | What it does |
|---|---|
| `python manage.py makemigrations` | Compares your models with the last migration and **writes** a new migration file |
| `python manage.py migrate` | **Runs** all migrations that haven't run yet against the database |

Migration files are saved in Git, so every copy of the project builds the same tables.

## Do

Replace `accounts/models.py` with:

<!-- source: accounts/models.py:1-83 -->
```python
"""
Who is using the platform, and which organization's data they may see.

User          - a person who logs in with an email address.
Organization  - the company or founder team that owns businesses, runs and decisions.
Membership    - links a user to an organization with a role. Every access check in the
                project goes through this table (see accounts/access.py).
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from common.models import BaseModel
from common.querysets import OrgScopedQuerySet


class UserManager(BaseUserManager):
    """Creates users identified by email instead of a username."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """People log in with their email; the inherited username column is removed."""

    username = None
    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=120, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.full_name or self.email


class Organization(BaseModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)

    # Organization is the root of the access tree, so its "path to itself" is empty.
    # Other models set ORG_PATH to e.g. "organization" or "business__organization".
    ORG_PATH = ""

    objects = OrgScopedQuerySet.as_manager()

    def __str__(self):
        return self.name


class Membership(BaseModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MEMBER = "member", "Member"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "organization"], name="unique_membership")
        ]

    def __str__(self):
        return f"{self.user} in {self.organization} ({self.role})"
```

Replace `accounts/admin.py` with:

<!-- source: accounts/admin.py:1-30 -->
```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Membership, Organization, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # Django's default admin expects a username; ours is the email.
    ordering = ["email"]
    list_display = ["email", "full_name", "is_staff", "is_active"]
    search_fields = ["email", "full_name"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Profile", {"fields": ["full_name"]}),
        ("Permissions", {"fields": ["is_active", "is_staff", "is_superuser", "groups"]}),
        ("Dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [(None, {"fields": ["email", "password1", "password2"]})]


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at"]
    inlines = [MembershipInline]
```

Lesson 4.6 needs two more small files before Django can start. Write
`accounts/access.py` and `accounts/context_processors.py` from
[4.6](06-who-sees-what.md) now (copy them; 4.6 explains them), then run:

```bash
python manage.py makemigrations accounts
```

```bash
python manage.py migrate
```

```bash
python manage.py createsuperuser
```

`createsuperuser` asks for an email and a password (typing the password shows nothing;
that's normal). Then start the site:

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/admin/** and log in with that email and password.

## Check

- `makemigrations` printed:

  ```text
  Migrations for 'accounts':
    accounts\migrations\0001_initial.py
      + Create model Organization
      + Create model User
      + Create model Membership
  ```

- `migrate` printed a list of `Applying ... OK` lines.
- In the admin site you see **Users** and **Organizations**. Click **Organizations → Add**,
  create one, and add yourself as a membership at the bottom.
- Stop the server with **Ctrl + C**.

> **Using Neon?** The tables are now in your cloud database. Open Neon's **Tables** page:
> you'll see `accounts_user`, `accounts_organization` and more. Django names each table
> `app_model`.

## Line by line

### `accounts/models.py`

- **Lines 1–8** · Docstring: the three tables, in one sentence each.
- **Line 10** · `AbstractUser` is Django's ready-made user: a password, `is_active`,
  `is_staff`, last login and more. `BaseUserManager` helps us build our own manager.
- **Line 11** · Django's model tools.
- **Lines 13–14** · Our building blocks from lesson 4.4.
- **Line 17** · A **manager** creates and finds rows. Django's default user manager
  expects a username; ours uses email instead.
- **Line 20** · `use_in_migrations = True`: migrations may use this manager too.
- **Line 22** · `create_user` makes a normal user. `**extra_fields` collects any extra
  named values (like `full_name=...`) into a dictionary.
- **Lines 23–24** · No email? Refuse, with a clear message (lesson 1.9).
- **Line 25** · Make a new User object (not saved yet). `normalize_email` tidies the
  email, and `.lower()` makes it lowercase, so `Asha@X.com` and `asha@x.com` count as the
  same person.
- **Line 26** · `set_password` **never** stores the password itself. It stores a
  **hash**: a scrambled fingerprint that can't be turned back into the password. When you
  log in, Django hashes what you type and compares the fingerprints.
- **Line 27** · Save the row to the database.
- **Line 28** · Give back the new user.
- **Lines 30–33** · `create_superuser` (used by `createsuperuser`): the same, but with
  admin powers turned on. `setdefault` sets a value only if it wasn't given.
- **Line 36** · Our User inherits everything from `AbstractUser`.
- **Line 39** · `username = None` removes the inherited username column; we use email.
- **Line 40** · An email column. `unique=True` means no two users may share an email; the
  database enforces it.
- **Line 41** · `full_name`: text up to 120 characters. `blank=True` means it may be left
  empty in forms.
- **Line 43** · `USERNAME_FIELD = "email"`: log in with the email.
- **Line 44** · Nothing else is required when creating a superuser.
- **Line 46** · Use our manager as `User.objects`.
- **Lines 48–49** · `__str__` is how a user is shown as text (in the admin, in
  templates): their full name, or their email if the name is empty.
- **Line 52** · `Organization` inherits from `BaseModel`, so it gets `id`, `created_at`
  and `updated_at` for free.
- **Line 53** · Its name.
- **Line 54** · A **slug** is a URL-friendly version of the name: `Kirana Express` →
  `kirana-express`. `unique=True`: no two organizations share one.
- **Lines 56–58** · `ORG_PATH = ""`: an organization **is** the organization, so the
  path to itself is empty (lesson 4.4).
- **Line 60** · Use our filter as the manager, so `Organization.objects.for_user(user)`
  works.
- **Lines 62–63** · Shown as its name.
- **Line 66** · `Membership` links users to organizations.
- **Lines 67–69** · `TextChoices` is a fixed list of allowed values. Each line is
  `NAME = "stored value", "label shown to people"`.
- **Line 71** · `ForeignKey(User, ...)`: this column points to one User row (lesson 3.1).
  - `on_delete=models.CASCADE`: if the user is deleted, delete their memberships too.
  - `related_name="memberships"`: from a user, `user.memberships` gives all their
    memberships. This name is what makes the `__memberships__user` path in lesson 4.4 work.
- **Lines 72–74** · The same, pointing to an Organization.
- **Line 75** · The role, limited to the choices above; new members are plain members by
  default.
- **Lines 77–80** · A database **constraint**: a rule the database itself enforces. Here,
  the same user can't be in the same organization twice.
- **Lines 82–83** · Shown as e.g. `Alice in Kirana Co (owner)`.

### `accounts/admin.py`

The admin site is a free back office for looking at and editing data.

- **Line 2** · Django's ready-made admin page for users. We import it under the name
  `DjangoUserAdmin` so our own class can be called `UserAdmin`.
- **Line 4** · Our three models. The `.` means "from this same app".
- **Line 7** · `@admin.register(User)` is a decorator (lesson 1.6): "show the User table
  in the admin, using the class below".
- **Line 8** · Start from Django's user admin and adjust it.
- **Line 10** · Sort users by email.
- **Line 11** · Columns shown in the user list.
- **Line 12** · Fields the search box looks in.
- **Lines 13–18** · How the "edit user" page is grouped into sections: login details,
  profile, permissions and dates. Each item is `(section title, {"fields": [...]})`.
- **Line 19** · The fields on the "add user" page. `password1` and `password2` are the
  "type it twice" boxes.
- **Lines 22–24** · An **inline**: show memberships as a small table *inside* the
  organization page. `extra = 0` means no empty extra rows.
- **Lines 27–30** · Show organizations with three columns, and their memberships inline.

## If it didn't work

| You see | Fix |
|---|---|
| `AUTH_USER_MODEL refers to model 'accounts.User' that has not been installed` | `accounts/models.py` isn't saved, or has a typo in `class User`. |
| `ModuleNotFoundError: No module named 'accounts.context_processors'` | You skipped writing the two files from 4.6. |
| `django.db.utils.OperationalError` (with Neon) | Check `DATABASE_URL` in `.env` (lesson 3.3), or leave it empty to use SQLite. |
| `You have ... unapplied migration(s)` when running the server | You forgot `migrate`. |

## Quiz

1. Why does `set_password` store a hash instead of the password?
2. What does `related_name="memberships"` let you write?
3. What's the difference between `makemigrations` and `migrate`?

---

**Next:** [4.6 · Who sees what](06-who-sees-what.md)

<details><summary>Quiz answers</summary>

1. So that even if someone steals the database, they don't get anyone's password.
2. `user.memberships` (all of a user's memberships), and the `__memberships__` path in
   filters.
3. `makemigrations` **writes** a migration file describing your model changes; `migrate`
   **applies** migrations to the database.

</details>
