# 8.7 · The scan, step by step

**Time:** 55 minutes · **Before this:** [8.6](06-real-citations.md).

## Read

A scan takes several seconds: robots.txt, six pages, one Gemini call. We'd like the user
to **see** each step as it happens ("Read /pricing...") instead of staring at a spinner.
And we'd like the same scan code to work from a terminal command and from tests.

The tool for that is a Python **generator**.

### Generators: a function that hands things over one at a time

A normal function `return`s once and is finished. A generator uses `yield` instead: it
hands over one value, **pauses**, and carries on from the same place when asked for the
next one. Try it in `python`:

```python
def countdown():
    yield "three"
    yield "two"
    yield "one"
```

(Press Enter twice to finish the function.)

```python
steps = countdown()
next(steps)
```

`'three'`. Type `next(steps)` again: `'two'`. Then `'one'`. One more time gives a
`StopIteration` error: the generator has finished. A `for` loop calls `next` for you and
stops at the end by itself:

```python
for word in countdown():
    print(word)
```

(Enter twice.) It prints all three. Type `exit()`.

`scan_steps(scan)` works the same way: it does one step of the scan, `yield`s a little
progress dictionary, then does the next step. Three different callers use it:

| Caller | What it does with each step |
|---|---|
| The live page (lesson 8.9) | Sends it to the browser straight away |
| The `rescan_companies` command (lesson 8.8) | Prints it in the terminal |
| `run_scan` (tests) | Ignores it, and just runs to the end |

### The four steps

```text
1. CHECK    is it a public address? does robots.txt allow us?   ── no ──► BLOCKED, stop
2. PAGES    homepage, then up to 5 interesting pages            ── homepage fails ──► FAILED
3. AI       a business profile from Gemini                      ── unavailable? carry on
4. COMPARE  with the last completed scan → Alert rows   (first scan: it becomes the baseline)
```

Step 3 is **optional**: if there's no key, or the daily budget is used up, the scan still
reads pages and still finds price changes. The AI makes the scan better, never required.

## Do

Create `intelligence/services/scan_service.py`. This lesson types the first three
pieces; lesson 8.8 adds the last one.

### Piece 1: imports and `event` (lines 1–38)

<!-- source: intelligence/services/scan_service.py:1-38 -->
```python
"""
Scan a company's public website, profile it with Gemini, and raise alerts on changes.

`scan_steps()` is a GENERATOR: it does one step, yields a progress event, does the next
step, yields again. That single design serves three callers:

  - the SSE view streams each event to the browser as it happens,
  - the `rescan_companies` command prints each event to the terminal,
  - `run_scan()` (tests, scripts) just runs it to the end.

"Real-time" here means on-demand: a scan runs when someone clicks Re-scan or when the
re-scan command is scheduled. Nothing watches the site continuously.
"""

import logging

from django.conf import settings
from django.utils import timezone

from intelligence.models import AIAnalysis, Alert, CompanyScan
from intelligence.schemas import SiteProfile

from . import ai_client, scan_diff
from .site_extractor import extract, pick_followup_links
from .sources import check_citations
from .url_fetcher import FetchBlocked, FetchFailed, SafeFetcher

logger = logging.getLogger(__name__)

MAX_EXTRA_PAGES = 5
AI_TEXT_PER_PAGE = 2000  # characters of page text sent to Gemini per page
THIN_TEXT = 800  # below this much text in total, also let Gemini read the URLs itself


def event(scan: CompanyScan, step: str, message: str, **extra) -> dict:
    entry = {"step": step, "message": message, "at": timezone.now().isoformat(), **extra}
    scan.log.append(entry)
    return entry
```

### Piece 2: `scan_steps` (lines 41–128)

<!-- source: intelligence/services/scan_service.py:41-128 -->
```python
def scan_steps(scan: CompanyScan, fetcher: SafeFetcher | None = None, transport=None):
    fetcher = fetcher or SafeFetcher()
    scan.status = CompanyScan.Status.RUNNING
    scan.save(update_fields=["status", "updated_at"])

    # 1. Safety and robots.txt ------------------------------------------------------
    yield event(scan, "check", f"Checking {scan.url} is a public website")
    try:
        allowed = fetcher.allowed(scan.url)
    except FetchBlocked as error:  # e.g. the address is on a private network
        yield from _finish(scan, CompanyScan.Status.BLOCKED, str(error))
        return
    except FetchFailed as error:  # e.g. DNS lookup failed
        yield from _finish(scan, CompanyScan.Status.FAILED, str(error))
        return
    scan.robots_allowed = allowed
    if not allowed:
        message = "robots.txt asks bots not to read this site, so we stopped."
        yield from _finish(scan, CompanyScan.Status.BLOCKED, message)
        return
    yield event(scan, "robots", "robots.txt allows reading this site")

    # 2. Pages -------------------------------------------------------------------------
    try:
        home = extract(scan.url, fetcher.fetch(scan.url).html)
    except (FetchBlocked, FetchFailed) as error:
        yield from _finish(scan, CompanyScan.Status.FAILED, str(error))
        return
    extracts = [home]
    yield event(scan, "page", f"Read the homepage: {home.title or scan.url}", url=scan.url)

    for link in pick_followup_links(home, MAX_EXTRA_PAGES):
        try:
            page = fetcher.fetch(link)
        except (FetchBlocked, FetchFailed) as error:
            yield event(scan, "skip", f"Skipped {link}: {error}", url=link)
            continue
        extracts.append(extract(link, page.html))
        yield event(scan, "page", f"Read {link}", url=link)

    scan.pages = [e.to_dict() for e in extracts]
    scan.save(update_fields=["pages", "log", "robots_allowed", "updated_at"])

    # 3. AI profile (optional: a scan is still useful without it) ------------------------
    profile = None
    yield event(scan, "ai", "Asking Gemini to build a business profile from these pages")
    try:
        profile = build_site_profile(scan, transport=transport)
        note = " (from cache)" if profile.from_cache else ""
        flags = len(profile.flagged_numbers)
        yield event(scan, "ai_done", f"Profile ready{note}; {flags} unverified number(s) flagged")
    except ai_client.AIError as error:
        yield event(scan, "ai_skipped", f"No AI profile this time: {error.message}")

    # 4. Compare with the previous scan ---------------------------------------------
    previous = (
        CompanyScan.objects.filter(business=scan.business, status=CompanyScan.Status.COMPLETED)
        .exclude(pk=scan.pk)
        .order_by("-created_at")
        .first()
    )
    if previous is None:
        yield event(scan, "baseline", "First scan of this site: saved as the baseline.")
    else:
        changes = scan_diff.compare(
            previous.pages,
            scan.pages,
            _competitor_names(previous),
            # No new profile (AI unavailable) -> assume competitors unchanged, no false alerts.
            {c["name"] for c in profile.output.get("competitors", [])}
            if profile
            else _competitor_names(previous),
        )
        for change in changes:
            Alert.objects.create(
                business=scan.business,
                scan=scan,
                severity=change.severity,
                kind=change.kind,
                summary=change.summary[:240],
                detail=change.detail,
            )
        message = f"{len(changes)} change(s) since the last scan"
        yield event(scan, "alerts", message, count=len(changes))

    yield from _finish(
        scan, CompanyScan.Status.COMPLETED, f"Scan complete: {len(extracts)} page(s)"
    )
```

### Piece 3: the helpers (lines 131–162)

<!-- source: intelligence/services/scan_service.py:131-162 -->
```python
def _finish(scan, status, message):
    scan.status = status
    if status != CompanyScan.Status.COMPLETED:
        scan.error = message
    scan.finished_at = timezone.now()
    final = event(scan, "done", message, status=status)
    scan.save()
    yield final


def run_scan(scan, **kwargs) -> CompanyScan:
    for _ in scan_steps(scan, **kwargs):
        pass
    return scan


def _competitor_names(scan) -> set[str]:
    # The profile in force when that scan finished. Not `scan.analyses`: a scan whose
    # profile came from the cache shares an earlier scan's row and has none of its own.
    analysis = (
        AIAnalysis.objects.filter(
            business=scan.business,
            kind=AIAnalysis.Kind.SITE_PROFILE,
            status=AIAnalysis.Status.OK,
            created_at__lte=scan.finished_at,
        )
        .order_by("-created_at")
        .first()
    )
    if not analysis:
        return set()
    return {c["name"] for c in analysis.output.get("competitors", [])}
```

## Check

```bash
python manage.py check
```

`System check identified no issues (0 silenced).` Then make sure the file imports
cleanly:

```bash
python manage.py shell -c "from intelligence.services import scan_service; print('ok')"
```

`ok`. (`build_site_profile`, used on line 88, comes in the next lesson. Python only looks
for it when that line actually runs, so importing works already.)

## Line by line

### Piece 1

- **Lines 1–13** · Docstring: one generator, three callers, and an honest note that
  "real-time" means **on demand**.
- **Line 15** · `logging`.
- **Lines 17–18** · Django's settings and `timezone` (for "now", with a time zone).
- **Lines 20–21** · The tables from lesson 7.3, and the `SiteProfile` schema.
- **Lines 23–26** · Everything built in this part, plus the AI client. The `.` means
  "from this same `services` folder".
- **Line 28** · A logger for this file.
- **Line 30** · Read at most 5 extra pages.
- **Line 31** · Send at most 2,000 characters per page to Gemini.
- **Line 32** · If all pages together have under 800 characters of text, the site is
  probably built with JavaScript (the text appears only in a browser). Lesson 8.8 uses
  this.
- **Lines 35–38** · `event(scan, step, message, **extra)`: make one progress entry (step
  name, message, time, and any extras like `url=`), **add it to the scan's log**, and
  return it. The log is saved, so the steps can be replayed later.

### Piece 2: `scan_steps`

- **Line 41** · The generator. A fetcher and a transport can be passed in, so tests can
  use fakes (lesson 8.11).
- **Line 42** · No fetcher given? Use the real `SafeFetcher`.
- **Lines 43–44** · Mark the scan "running" and save just that field (and the updated
  time). `update_fields` saves only what we name: quicker, and it can't overwrite other
  fields by accident.

**Step 1: safety and robots.txt**

- **Line 47** · First progress message: `yield` hands it to the caller and pauses here.
- **Line 49** · `fetcher.allowed(...)` runs `check_url` and reads robots.txt.
- **Lines 50–52** · A private address: finish as **blocked**. `yield from` passes on
  every value of another generator (here, `_finish`'s one final event). Then `return`
  ends this generator.
- **Lines 53–55** · The name doesn't exist (or similar): finish as **failed**.
- **Lines 56–60** · Remember robots.txt's answer. If it says no, finish as blocked, with
  a clear reason.
- **Line 61** · All clear.

**Step 2: pages**

- **Lines 64–68** · Fetch and extract the homepage. If **that** fails, the scan fails:
  without a homepage there's nothing to work with.
- **Line 69** · A list of extracts, starting with the homepage.
- **Line 70** · Progress: the homepage's title (or its address if it has no title).
- **Lines 72–79** · The interesting pages. If one fails, **skip** it with a message and
  `continue` to the next: one missing page doesn't spoil the scan.
- **Lines 81–82** · Save the extracts (as dictionaries) and the log so far.

**Step 3: the AI profile**

- **Line 85** · No profile yet.
- **Line 86** · Progress: asking Gemini.
- **Lines 87–91** · Build the profile (next lesson). Report whether it came from the
  cache and how many numbers were flagged.
- **Lines 92–93** · Any AI error (no key, budget, rate limit...) becomes a message, and
  the scan **carries on**.

**Step 4: compare**

- **Lines 96–101** · The last **completed** scan of this business, not counting this one
  (`exclude(pk=scan.pk)`), newest first.
- **Lines 102–103** · None? This scan is the baseline: nothing to compare yet.
- **Lines 105–113** · Compare pages and competitors. The new competitor names come from
  the new profile. If there's **no** new profile (AI unavailable), we pretend the
  competitors didn't change, so we don't raise a false "new competitor" alert for every
  competitor we already knew.
- **Lines 114–122** · One `Alert` row per change. `[:240]` keeps the summary within the
  column's length.
- **Lines 123–124** · Progress: how many changes, with `count=` as an extra.
- **Lines 126–128** · Finish as completed.

### Piece 3

- **Lines 131–138** · `_finish`: set the status, record the error (only for a scan that
  didn't complete), the finish time, a final `done` event with the status, save
  **everything**, and yield that event.
- **Lines 141–144** · `run_scan`: run every step and ignore the messages. `for _ in ...:
  pass` is how you say "just run it to the end". `_` is a name for "a value I don't
  need".
- **Line 147** · `_competitor_names(scan)`: the competitors the AI named at that scan.
- **Lines 148–149** · Why not just "that scan's own profile"? Because a profile that came
  from the **cache** stays linked to the earlier scan that created it. The scan that
  reused it has no profile of its own.
- **Lines 150–159** · So: the newest OK site profile of this business that existed when
  that scan **finished** (`created_at__lte`, "created at or before"). That's the profile
  the scan really used.
- **Lines 160–162** · No profile: an empty set. Otherwise, every competitor's name.

> **A real bug, found while writing this guide.** The first version of line 148 used
> "that scan's own profile". Scan the same unchanged site three times, and the third
> scan raised a "new competitor" alert for a competitor the app already knew, because the
> second scan (served from the cache) had no profile of its own. A test in lesson 8.11
> scans three times to make sure it never comes back.

## If it didn't work

| You see | Fix |
|---|---|
| `ImportError: cannot import name 'pick_followup_links'` | It's in `site_extractor.py`, lines 144–159 (lesson 8.4). |
| `IndentationError` in piece 2 | Every `yield` and `try` inside `scan_steps` is indented 4 spaces; lines inside `try`, `except` and `for` another 4. |

## Quiz

1. What's the difference between `return` and `yield`?
2. Gemini is unavailable during a scan. Does the scan fail?
3. Why are skipped pages not a reason to fail the scan?

---

**Next:** [8.8 · The profile and a command](08-profile-and-command.md)

<details><summary>Quiz answers</summary>

1. `return` gives back one value and ends the function. `yield` gives back a value and
   pauses; the function continues from there when the next value is asked for.
2. No. It records an `ai_skipped` step and carries on: pages are read and compared.
3. A site often has a broken link or a page robots.txt keeps us from. One missing page
   still leaves a useful scan.

</details>
