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
