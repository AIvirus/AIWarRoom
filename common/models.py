"""Abstract base model shared by every app."""

import uuid

from django.db import models


class BaseModel(models.Model):
    """
    UUID primary key plus timestamps.

    UUIDs mean a URL like /businesses/<id>/ doesn't reveal how many records exist, and
    nobody can guess a neighbour's id by adding one.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
