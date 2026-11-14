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
    analysis = scan.analyses.filter(
        kind=AIAnalysis.Kind.SITE_PROFILE, status=AIAnalysis.Status.OK
    ).first()
    if not analysis:
        return set()
    return {c["name"] for c in analysis.output.get("competitors", [])}


# --------------------------------------------------------------------------------------
# Gemini site profile
# --------------------------------------------------------------------------------------
def site_payload(scan) -> dict:
    """What Gemini sees: our extract, trimmed. Untrusted text, wrapped as data."""
    return {
        "company_name": scan.business.name,
        "page_urls": [page["url"] for page in scan.pages],
        "pages": [
            {
                "url": page["url"],
                "title": page["title"],
                "description": page["description"],
                "headings": page["headings"][:12],
                "text": page["text"][:AI_TEXT_PER_PAGE],
                "prices_seen": page["prices"][:20],
                "products_seen": page["products"][:20],
                "providers_named": page["providers"],
            }
            for page in scan.pages
        ],
    }


def build_site_profile(scan, transport=None) -> AIAnalysis:
    payload = site_payload(scan)
    page_urls = set(payload["page_urls"])
    total_text = sum(len(page["text"]) for page in payload["pages"])

    tools: tuple[str, ...] = ()
    model = None
    if total_text < THIN_TEXT:
        # Probably a JavaScript-rendered site: let Gemini read the pages itself.
        tools = ("url_context",)
    if settings.GEMINI_GROUNDING_MODEL:
        # Only with a key/plan that has Search grounding (not this free tier, as of Nov 2026).
        tools, model = (*tools, "google_search"), settings.GEMINI_GROUNDING_MODEL

    def citations_must_be_real(profile: SiteProfile, sources) -> None:
        allowed = page_urls | {s["url"] for s in sources}
        check_citations(profile.sourced_items(), allowed)

    return ai_client.generate(
        business=scan.business,
        kind=AIAnalysis.Kind.SITE_PROFILE,
        task="site_profile",
        payload=payload,
        schema=SiteProfile,
        scan=scan,
        check=citations_must_be_real,
        tools=tools,
        model=model,
        data_tag="website_content",
        transport=transport,
    )
