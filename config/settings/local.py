"""Developer laptop settings: debug on, browsable API on."""

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK, SECRET_KEY

DEBUG = True

# A missing key should not stop a student from running the project locally.
if not SECRET_KEY:
    SECRET_KEY = "local-dev-only-not-secret"

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
