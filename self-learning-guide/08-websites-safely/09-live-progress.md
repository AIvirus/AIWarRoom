# 8.9 · Live progress

**Time:** 60 minutes · **Before this:** [8.8](08-profile-and-command.md).

## 📖 Read

The terminal command printed each step as it happened. Now the browser should too.

Normally a web request works like a letter: the browser asks, the server writes the whole
answer, sends it, done. For a scan we want something more like a **radio**: the browser
tunes in, and the server keeps talking until it's finished.

The simplest way is **Server-Sent Events (SSE)**. It's ordinary HTTP, where the server
just doesn't close the answer straight away. It writes small blocks like this, each ended
by an empty line:

```text
event: page
data: {"step": "page", "message": "Read https://books.toscrape.com/catalogue/..."}

```

Browsers have a built-in reader for it, called `EventSource`. Django can send it with a
`StreamingHttpResponse` fed by a generator, and our scan **is** a generator (lesson 8.7).
So the view is short.

### Two API calls, on purpose

1. `POST /api/v1/businesses/<id>/scans/` **creates** a scan row ("pending") and answers
   **202 Accepted** ("I've got it; it hasn't happened yet") with the address of its
   event stream.
2. Opening that **events** address is what actually **runs** the scan, streaming each
   step.

What if two browser tabs open the same events address? Only the **first** may run the
scan. The view "claims" it with one database command that says "set status to running,
**only if** it's still pending". The database does that as one indivisible step, so only
one tab can win. Every other tab (or a reload later) gets a **replay** of the saved log
instead of a second scan.

## ⌨️ Do

### 1. `intelligence/views.py`

<!-- source: intelligence/views.py:1-81 -->
```python
"""
Server-Sent Events: the scan streams its progress to the browser while it works.

SSE is plain HTTP: the response stays open and the server writes lines like

    event: page
    data: {"message": "Read https://example.com/pricing"}

followed by a blank line. The browser's built-in EventSource reads them as they arrive.
No WebSockets, no Redis, no Channels: just a Django view that returns a generator.
"""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from .models import Alert, CompanyScan
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


@login_required
@require_POST
def alert_acknowledge(request, pk):
    alert = get_object_or_404(Alert.objects.for_user(request.user), pk=pk)
    if alert.acknowledged_at is None:
        alert.acknowledged_at, alert.acknowledged_by = timezone.now(), request.user
        alert.save(update_fields=["acknowledged_at", "acknowledged_by", "updated_at"])
        messages.success(request, "Alert acknowledged.")
    target = request.POST.get("next", "")
    # Only go back to a page on this site: an open redirect is a phishing tool.
    if not url_has_allowed_host_and_scheme(target, {request.get_host()}):
        target = "home"
    return redirect(target)
```

### 2. `config/urls.py` (for now)

Three additions: import the views (line 10), list scans and alerts in the API (lines
22–23), and add the events address (line 37). The whole file is in
[`for-now/config/urls.py`](for-now/config/urls.py):

<!-- source: self-learning-guide/08-websites-safely/for-now/config/urls.py:7-45 -->
```python
from accounts import api as accounts_api
from businesses import api as businesses_api
from intelligence import api as intelligence_api
from intelligence import views as intelligence_views
from simulations import api as simulations_api

from . import views

# One router for the whole JSON API; each app's ViewSets are registered here.
router = DefaultRouter()
router.register("organizations", accounts_api.OrganizationViewSet, basename="organization")
router.register("businesses", businesses_api.BusinessViewSet, basename="business")
router.register("scenarios", simulations_api.ScenarioViewSet, basename="scenario")
router.register("runs", simulations_api.SimulationRunViewSet, basename="run")
router.register("analyses", intelligence_api.AIAnalysisViewSet, basename="analysis")
router.register("scans", intelligence_api.CompanyScanViewSet, basename="scan")
router.register("alerts", intelligence_api.AlertViewSet, basename="alert")

# Components live under their business: /businesses/<id>/components/. Wired by hand
# (rather than a nested-router package) so the mapping is visible.
components_list = businesses_api.ComponentViewSet.as_view({"get": "list", "post": "create"})
components_detail = businesses_api.ComponentViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

api_v1 = [
    path("me/", accounts_api.me, name="me"),
    path("scenario-templates/", simulations_api.scenario_templates, name="scenario-templates"),
    path("inputs/", simulations_api.input_catalog, name="inputs"),
    path("simulate/preview/", simulations_api.simulate_preview, name="simulate-preview"),
    path("scans/<uuid:pk>/events/", intelligence_views.scan_events, name="scan-events"),
    path("businesses/<uuid:business_pk>/components/", components_list, name="component-list"),
    path(
        "businesses/<uuid:business_pk>/components/<uuid:pk>/",
        components_detail,
        name="component-detail",
    ),
    path("", include(router.urls)),
]
```

### 3. The "start a scan" action in `businesses/api.py`

At the top of `businesses/api.py`, change two imports so they match lines 6–15 here
(`status` is new on line 8, and line 15 is new):

<!-- source: businesses/api.py:6-15 -->
```python
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.access import OrgScopedMixin, organization_for
from accounts.models import Membership
from config.api_errors import DomainError
```

Then add this action **inside** the `BusinessViewSet` class, after the `assumptions`
action (so it's indented by 4 spaces, like the other actions):

<!-- fmt:off -->
<!-- source: businesses/api.py:69-88 -->
```python
    @action(detail=True, methods=["post"])
    def scans(self, request, pk=None):
        """
        Create a scan of the business website. Returns 202 with the URL of its event
        stream; opening that stream is what actually runs the scan.
        """
        from django.urls import reverse

        from intelligence.models import CompanyScan

        business = self.get_object()
        url = (request.data.get("url") or business.website_url or "").strip()
        if not url:
            raise DomainError("Add the company's website URL first.", {"url": ["required"]})
        scan = CompanyScan.objects.create(business=business, url=url)
        events_url = reverse("api:scan-events", args=[scan.id])
        return Response(
            {"scan": str(scan.id), "status": scan.status, "events_url": events_url},
            status=status.HTTP_202_ACCEPTED,
        )
```
<!-- fmt:on -->

## ✅ Check

```bash
python manage.py check
```

Then try it. Start the server, log in, open the console and paste the `api()` helper.
Then paste the `watch()` helper from [`practice/watch_scan.js`](practice/watch_scan.js):

<!-- source: self-learning-guide/08-websites-safely/practice/watch_scan.js:1-16 -->
```js
// Paste into the browser console (after the api() helper) to watch a scan live.
function watch(eventsUrl) {
  const stream = new EventSource(eventsUrl);
  const steps = ["check", "robots", "page", "skip", "ai", "ai_done", "ai_skipped",
    "baseline", "alerts", "busy", "done"];
  for (const step of steps) {
    stream.addEventListener(step, (message) => {
      const event = JSON.parse(message.data);
      console.log(`[${step}] ${event.message}`);
      if (step === "done" || step === "busy") stream.close();
    });
  }
  stream.onerror = () => stream.close();
}

console.log("watch() ready");
```

Find Books Corner and start a scan:

```js
const books = (await api("GET", "/api/v1/businesses/")).find((b) => b.name === "Books Corner")
```

```js
const started = await api("POST", `/api/v1/businesses/${books.id}/scans/`)
```

→ `202`, with `status: "pending"` and an `events_url`. Nothing has been fetched yet. Now
tune in:

```js
watch(started.events_url)
```

The lines appear one by one, from `[check]` to `[done] Scan complete: 6 page(s)`, with
`(from cache)` and `0 change(s)` as in lesson 8.8. Watch it **again**:

```js
watch(started.events_url)
```

The same lines appear instantly: that's the **replay** of the saved log. Nothing was
fetched twice.

Now the important one. Ask for a scan of your own computer:

```js
const bad = await api("POST", `/api/v1/businesses/${books.id}/scans/`, {url: "http://localhost/admin/"})
```

```js
watch(bad.events_url)
```

```text
[check] Checking http://localhost/admin/ is a public website
[done] localhost points to a private or reserved network address.
```

The server refused to visit itself. 🎉

**See the stream itself:** open DevTools' **Network** tab, run another
`watch(started.events_url)`, click the `events/` request, then its **EventStream** tab:
each event, as it arrived.

## 🔍 Line by line

### `intelligence/views.py`

- **Lines 1–11** · Docstring: what SSE looks like, and why no extra tools are needed.
- **Line 13** · `json`.
- **Lines 15–21** · Django tools: messages, login required, the streaming response,
  `get_object_or_404`, `redirect`, `timezone`, a URL safety check, and decorators that
  allow only GET or only POST.
- **Lines 23–24** · Our tables and the generator.
- **Lines 27–28** · `sse(event)`: one event as SSE text: `event:` line, `data:` line with
  the JSON, then `\n\n` (the empty line that ends an event). `ensure_ascii=False` keeps ₹
  as ₹ instead of `₹`.
- **Lines 31–32** · Must be logged in; GET only.
- **Line 33** · `scan_events(request, pk)`: `pk` is the scan id from the address.
- **Line 34** · The scan, **only if** it belongs to the user's organization; otherwise
  404 (lesson 4.6). `for_user` comes from the `CompanyScan` table's manager (lesson 7.3).
- **Lines 36–40** · ⭐ The claim. `.filter(pk=..., status=PENDING).update(status=RUNNING)`
  is one database command that changes the row **only if** it's still pending, and
  returns how many rows it changed: 1 (we won) or 0 (someone else did, or it's done).
- **Line 41** · Won: run it live. Lost: replay.
- **Lines 43–46** · Stream it with the SSE content type. `no-cache`: don't save a copy.
  `X-Accel-Buffering: no`: asks a proxy server (like nginx, in Part 11) not to hold the
  events back.
- **Lines 49–52** · `live(scan)`: run the scan, sending each step as SSE.
- **Lines 53–59** · `finally:` runs even if the user **closes the tab** mid-scan (Django
  then stops the generator early). If the scan was left "running", mark it failed with a
  clear reason, so it doesn't stay "running" forever.
- **Lines 62–66** · `replay(scan)`: send the saved log. If the scan isn't finished yet
  (another tab is running it), add a `busy` event.
- **Lines 69–81** · `alert_acknowledge`: marks an alert as read (who and when), then
  goes back to the page the user came from. **Part 10** puts a button on the page for
  it, so we don't connect it to an address yet. Lines 77–80 matter: the "go back to"
  address comes from the browser, so we only follow it if it's on **our** site. A login
  page that redirects to any address it's given is an **open redirect**, a favourite
  tool for fake "log in again" emails.

### `config/urls.py`

- **Line 10** · Import the views.
- **Lines 22–23** · `/api/v1/scans/` and `/api/v1/alerts/`: read-only lists (the
  ViewSets from lesson 7.8), plus `POST /api/v1/alerts/<id>/acknowledge/`.
- **Line 37** · The events address. `<uuid:pk>` only matches a real UUID.

### `businesses/api.py`

- **Line 8** · `status` gives names for codes, like `status.HTTP_202_ACCEPTED`.
- **Line 15** · `DomainError`, our friendly error with a code and fields (lesson 4.7).
- **Line 69** · An extra action, POST only: `/businesses/<id>/scans/`.
- **Lines 71–74** · Docstring: creating isn't running.
- **Lines 75–77** · These imports sit **inside** the function. The businesses app then
  doesn't load the intelligence app until someone actually starts a scan, which keeps
  the two apps loosely tied together.
- **Line 79** · The business (only if it's yours).
- **Line 80** · The address to scan: one sent in the request, or the business's
  `website_url`, or nothing.
- **Lines 81–82** · No address: a 422 error naming the `url` field.
- **Line 83** · Create the scan row. It starts as pending.
- **Line 84** · Build the events address from its name (`api:scan-events`), never by
  gluing text together.
- **Lines 85–88** · Answer 202 with the scan id, its status and the events address.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `NoReverseMatch: 'scan-events' not found` | The events path (line 37 of `urls.py`) is missing or misspelt. |
| `NameError: name 'status' is not defined` | Line 8 of `businesses/api.py`: `from rest_framework import status, viewsets`. |
| `watch()` prints nothing at all | Did you paste `watch_scan.js`? Is `started.events_url` set? Look in the Network tab for the `events/` request. |
| `[busy] This scan is already running in another tab.` | Another tab is running that scan. Wait, then `watch` again to see the replay. |

## ❓ Quiz

1. Why does starting a scan answer 202, not 201?
2. Two tabs open the same events address at the same moment. How many scans run?
3. Why does `alert_acknowledge` check the "go back to" address?

---

**Next:** [8.10 · The expert committee](10-the-expert-committee.md)

<details><summary>Quiz answers</summary>

1. 202 means "accepted, not done yet". The scan only runs when the events address is
   opened.
2. One. The `update(...)` claim lets only one tab change "pending" to "running"; the
   other gets a replay.
3. It comes from the browser, so anyone could put any address there. Following it
   blindly would be an open redirect.

</details>
