"""
Server-Sent Events: the scan streams its progress to the browser while it works.

SSE is plain HTTP: the response stays open and the server writes lines like

    event: page
    data: {"message": "Read https://example.com/pricing"}

followed by a blank line. The browser's built-in EventSource reads them as they arrive.
No WebSockets, no Redis, no Channels: just a Django view that returns a generator.
"""

import json

from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .models import CompanyScan
from .services.scan_service import scan_steps


def sse(event: dict) -> str:
    return f"event: {event['step']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


@login_required
@require_GET
def scan_events(request, pk):
    scan = get_object_or_404(CompanyScan.objects.for_user(request.user), pk=pk)

    # Claim the scan atomically: only the first viewer to arrive runs it. Anyone else (or
    # a page reload later) gets a replay of the log instead of a second scan.
    claimed = CompanyScan.objects.filter(pk=scan.pk, status=CompanyScan.Status.PENDING).update(
        status=CompanyScan.Status.RUNNING
    )
    stream = live(scan) if claimed else replay(scan)

    response = StreamingHttpResponse(stream, content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # tell proxies like nginx not to buffer the stream
    return response


def live(scan):
    try:
        for event in scan_steps(scan):
            yield sse(event)
    finally:
        # Runs even if the browser tab closes mid-scan (the generator is closed early).
        scan.refresh_from_db(fields=["status"])
        if scan.status == CompanyScan.Status.RUNNING:
            scan.status = CompanyScan.Status.FAILED
            scan.error = "Scan interrupted: the page was closed before it finished."
            scan.save(update_fields=["status", "error", "updated_at"])


def replay(scan):
    for event in scan.log:
        yield sse(event)
    if scan.status in {CompanyScan.Status.PENDING, CompanyScan.Status.RUNNING}:
        yield sse({"step": "busy", "message": "This scan is already running in another tab."})
