from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """
    Liveness + database check. Useful right after setting DATABASE_URL: if Neon is
    unreachable this answers 503 with the reason instead of a stack trace.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok", "database": connection.vendor})
    except Exception as error:  # noqa: BLE001  - we report any DB failure the same way
        return JsonResponse(
            {"status": "error", "database": connection.vendor, "detail": type(error).__name__},
            status=503,
        )
