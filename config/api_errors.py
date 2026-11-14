"""
One error shape for the whole API:

    {"error": {"code": "validation_error", "message": "...", "fields": {...}}}

Clients (our own JS included) check `error.code` instead of parsing English messages.
"""

import logging

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

CODES = {
    exceptions.ValidationError: "validation_error",
    exceptions.NotAuthenticated: "not_authenticated",
    exceptions.AuthenticationFailed: "not_authenticated",
    exceptions.PermissionDenied: "permission_denied",
    exceptions.NotFound: "not_found",
    exceptions.MethodNotAllowed: "method_not_allowed",
    exceptions.ParseError: "parse_error",
    exceptions.UnsupportedMediaType: "unsupported_media_type",
    exceptions.Throttled: "rate_limited",
}


def _code_for(exc) -> str:
    for exc_type, code in CODES.items():
        if isinstance(exc, exc_type):
            return code
    return "error"


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)  # DRF converts Http404 etc. for us

    if response is None:
        # Not an API error DRF knows about: a bug. Log it with the traceback, but never
        # send internals to the client.
        logger.exception("Unhandled API error in %s", context.get("view"))
        return Response(
            {
                "error": {
                    "code": "server_error",
                    "message": "Something went wrong on our side.",
                    "fields": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = "not_found" if response.status_code == 404 else _code_for(exc)
    if isinstance(exc, exceptions.ValidationError):
        detail = response.data
        fields = detail if isinstance(detail, dict) else {"non_field_errors": detail}
        message = "Some fields need attention."
    else:
        fields = {}
        message = str(response.data.get("detail", "")) if isinstance(response.data, dict) else ""
        if code == "not_found":
            message = "Not found."  # same text whether it's missing or someone else's

    response.data = {"error": {"code": code, "message": message, "fields": fields}}
    return response
