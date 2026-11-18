# 8.8 · The profile and a command

**Time:** 50 minutes · **Before this:** [8.7](07-the-scan-step-by-step.md).

## Read

### The site profile

`build_site_profile` reuses **everything** from Part 7: the AI client's cache, budget,
retries, one repair, number guardrail and saved history. It only has to supply four
things:

| What | For the site profile |
|---|---|
| The payload (what Gemini sees) | Our extracts, trimmed: titles, headings, 2,000 characters of text per page, prices, products, providers |
| The schema | `SiteProfile` (lesson 7.4) |
| The extra check | "Citations must be real" (lesson 8.6) |
| The data tag | `<website_content>`, so the prompt can call it untrusted |

One more idea: **tools**. Some sites are built with JavaScript, and their HTML is nearly
empty until a browser runs the code. Our plain fetcher sees almost no text. In that case
we let Gemini read the page addresses itself with its `url_context` tool (lesson 7.6
explained tools). Google fetches those pages from its own computers, not ours, so our
SSRF rules aren't involved.

### A management command

You've used many Django commands: `runserver`, `migrate`, `shell`... You can write your
own. Put a file in `<app>/management/commands/`, and its name becomes the command name:

```text
intelligence/
└── management/
    ├── __init__.py
    └── commands/
        ├── __init__.py
        └── rescan_companies.py    →   python manage.py rescan_companies
```

Ours re-scans every business that has a website address and prints each step. You could
run it every Monday morning with your computer's scheduler (Task Scheduler on Windows,
`cron` on Mac/Linux). That's the only "monitoring" AI WarRoom does: nothing watches a
site all the time.

## Do

### 1. The profile: the end of `scan_service.py` (lines 165–219)

Add this to the **end** of `intelligence/services/scan_service.py`:

<!-- source: intelligence/services/scan_service.py:165-219 -->
```python
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
```

### 2. The command

Make the folders `intelligence/management/` and `intelligence/management/commands/`,
each with an **empty** `__init__.py`. Then create
`intelligence/management/commands/rescan_companies.py`:

<!-- source: intelligence/management/commands/rescan_companies.py:1-37 -->
```python
"""
Re-scan every active business that has a website URL and print what changed.

    python manage.py rescan_companies
    python manage.py rescan_companies --business <uuid>

Schedule it (cron on Linux/macOS, Task Scheduler on Windows) for periodic checks.
It is the only "monitoring" this project does: there is no always-on watcher.
"""

from django.core.management.base import BaseCommand

from businesses.models import BusinessProfile
from intelligence.models import CompanyScan
from intelligence.services.scan_service import scan_steps


class Command(BaseCommand):
    help = "Re-scan company websites and create alerts for changes since the last scan."

    def add_arguments(self, parser):
        parser.add_argument("--business", help="Only this business id")

    def handle(self, *args, **options):
        businesses = BusinessProfile.objects.active().exclude(website_url="")
        if options["business"]:
            businesses = businesses.filter(pk=options["business"])
        if not businesses:
            self.stdout.write("No active businesses with a website URL.")
            return
        for business in businesses:
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"{business.name}: {business.website_url}")
            )
            scan = CompanyScan.objects.create(business=business, url=business.website_url)
            for step in scan_steps(scan):
                self.stdout.write(f"  [{step['step']}] {step['message']}")
```

## Check

First, with nothing to scan:

```bash
python manage.py rescan_companies
```

`No active businesses with a website URL.`

Now give it something. Start the server (`python manage.py runserver`), log in at
**http://127.0.0.1:8000/**, open the console (F12 → Console) and paste the `api()`
helper (lesson 5.7). Create a business with a website address:

```js
const books = await api("POST", "/api/v1/businesses/", {mode: "operating", name: "Books Corner", website_url: "https://books.toscrape.com/"})
```

→ `201`. Stop the server (**Ctrl+C** in its terminal) and run the command again. Your
Gemini key from Part 7 must be in `.env`:

```bash
python manage.py rescan_companies
```

After a few seconds:

```text
Books Corner: https://books.toscrape.com/
  [check] Checking https://books.toscrape.com/ is a public website
  [robots] robots.txt allows reading this site
  [page] Read the homepage: All products | Books to Scrape - Sandbox
  [page] Read https://books.toscrape.com/catalogue/category/books_1/index.html
  [page] Read https://books.toscrape.com/catalogue/category/books/travel_2/index.html
  [page] Read https://books.toscrape.com/catalogue/category/books/mystery_3/index.html
  [page] Read https://books.toscrape.com/catalogue/category/books/historical-fiction_4/index.html
  [page] Read https://books.toscrape.com/catalogue/category/books/sequential-art_5/index.html
  [ai] Asking Gemini to build a business profile from these pages
  [ai_done] Profile ready; 0 unverified number(s) flagged
  [baseline] First scan of this site: saved as the baseline.
  [done] Scan complete: 6 page(s)
```

You may also see two log lines near the top, `HTTP Request: POST https://generativelanguage...
"HTTP/1.1 200 OK"` and `AI site_profile ok: 1 attempts, 0 flagged numbers`. Those come
from the AI client's logging (lesson 7.7), not from the command.

Each line appeared as it happened: that's the generator at work. Run it **again**:

```text
  [ai_done] Profile ready (from cache); 0 unverified number(s) flagged
  [alerts] 0 change(s) since the last scan
```

Same pages, so the same question: the cache answered (no Gemini call), and nothing
changed. Run it a **third** time: still `0 change(s)` (that's the bug fixed in lesson 8.7).

Finally look at the profile Gemini wrote: **http://127.0.0.1:8000/admin/** (start the
server again) → **AI analyses** → the "Company site profile" row → **Output**. On our test
it noticed, correctly, that this is a demo shop for practising scraping, and it marked its
one competitor guess as `"basis": "inference"`, with no link.

## Line by line

### The profile

- **Lines 165–167** · Section banner.
- **Line 168** · `site_payload(scan)`: what Gemini sees.
- **Line 169** · Docstring: our extract, trimmed, treated as untrusted.
- **Lines 170–186** · A dictionary: the company name, the list of page addresses, and for
  each page only the parts we chose. `[:12]`, `[:2000]` and `[:20]` cut long lists and
  text short, so the prompt stays small (and cheap).
- **Line 189** · `build_site_profile(scan, transport=None)`.
- **Line 190** · Build the payload.
- **Line 191** · The page addresses, as a set: these are the only allowed `site` sources.
- **Line 192** · How much text in total.
- **Lines 194–195** · By default: no tools, the normal model.
- **Lines 196–198** · Very little text? Let Gemini read the pages itself.
- **Lines 199–201** · Only if you set `GEMINI_GROUNDING_MODEL` in `.env` (paid plans):
  also let it search Google, with that model. `(*tools, "google_search")` makes a new
  tuple with everything in `tools` plus one more. The comment says why it's off by
  default: the free tier has no quota for it.
- **Lines 203–205** · The extra check, as a small function **inside** this one. It can
  see `page_urls` from line 191. Allowed sources: our pages, plus any sources the AI's
  tools really used (`sources`, collected by the AI client in lesson 7.6).
- **Lines 207–219** · Ask the AI client: this business and scan, kind "site profile",
  the `site_profile` prompt, our payload, the schema, the check, any tools, and the
  `website_content` tag.

### The command

- **Lines 1–9** · Docstring: how to run it, how to schedule it, and the honest note that
  it's the only "monitoring".
- **Line 11** · `BaseCommand`: every command is a class built on it.
- **Lines 13–15** · Businesses, scans, and our generator.
- **Line 18** · The class **must** be called `Command`. Django looks for that name.
- **Line 19** · `help`: shown by `python manage.py help rescan_companies`.
- **Lines 21–22** · An optional `--business <id>`, to scan just one.
- **Line 24** · `handle`: what runs. `options` holds the arguments.
- **Line 25** · Active businesses (not archived, lesson 5.3) that **have** a website
  address. `.exclude(website_url="")` removes those whose address is empty.
- **Lines 26–27** · Only one, if `--business` was given.
- **Lines 28–30** · None? Say so and stop.
- **Lines 31–34** · For each business, a heading line. `self.stdout.write` is a command's
  `print`; `self.style.MIGRATE_HEADING` makes it look like `migrate`'s headings.
- **Line 35** · A new scan row.
- **Lines 36–37** · Run the generator, printing each step as it arrives.

## If it didn't work

| You see | Fix |
|---|---|
| `Unknown command: 'rescan_companies'` | Check both `__init__.py` files and the folder names: `management` and `commands`, plural. |
| `[ai_skipped] No AI profile this time: ... GEMINI_API_KEY` | No key in `.env`. The scan still completes; add the key (lesson 7.2) and run again. |
| `[done] ... DNS lookup failed` | No internet connection. |
| The lines all appear at once at the end | That's fine on some terminals; the steps still ran in order. |

## Quiz

1. Which Part 7 safety layers does the site profile get for free?
2. When does Gemini get the `url_context` tool?
3. Why is the second scan's profile "from cache"?

---

**Next:** [8.9 · Live progress](09-live-progress.md)

<details><summary>Quiz answers</summary>

1. All of them: the cache, the daily budget, retries, one repair attempt, the number
   guardrail, the saved history, and the label.
2. When all the pages together have under 800 characters of text (probably a JavaScript
   site).
3. Same pages give the same payload, so the same fingerprint (lesson 7.7). The saved
   answer is reused.

</details>
