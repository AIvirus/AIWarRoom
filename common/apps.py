from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Shared base model, querysets and template filters. Has no tables of its own."""

    name = "common"
