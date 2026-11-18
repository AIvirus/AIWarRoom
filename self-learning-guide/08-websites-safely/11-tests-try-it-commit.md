# 8.11 · Tests, try it, commit

**Time:** 50 minutes · **Before this:** [8.10](10-the-expert-committee.md).

## Read

How do you test a fetcher that must refuse `127.0.0.1`, without a hostile server? Or a
redirect to the cloud's secret address, without a cloud? You **fake** the outside world,
just as Part 7 faked Gemini:

| Real thing | Fake in the tests | Where |
|---|---|---|
| DNS (name → address) | A dictionary: `dns["sneaky.test"] = ["127.0.0.1"]` | `test_url_fetcher.py`, the `dns` fixture |
| The internet (`requests`) | `FakeSession` with `FakeResponse`s you script: a 302, a PDF, a 50 KB page | `test_url_fetcher.py` |
| A whole website | `FakeFetcher({url: html})` | `fakes.py` |
| Gemini | `FakeTransport` (Part 7) | `fakes.py` |

The `.test` ending in the fake addresses is reserved for testing: it can never be a real
website.

**monkeypatch** (a pytest fixture) swaps something for the length of one test and puts it
back afterwards. The `dns` fixture uses it to replace `url_fetcher.resolve` with the
dictionary lookup, so a test can make any name point anywhere, with no internet at all.

## Do

### 1. The finished `fakes.py`

Replace `intelligence/tests/fakes.py` with the finished version. Line 6 and lines 28–51
are new:

<!-- source: intelligence/tests/fakes.py:1-51 -->
```python
"""Test doubles for the outside world: Gemini and websites. No network, fully scripted."""

import json

from intelligence.services.ai_client import Reply
from intelligence.services.url_fetcher import FetchBlocked, FetchFailed, Page


class FakeTransport:
    """Plays back a script of Gemini replies (or exceptions), one per call."""

    def __init__(self, *script):
        self.script = list(script)
        self.requests = []

    def generate(self, **request):
        self.requests.append(request)
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def reply(data: dict, sources=()) -> Reply:
    return Reply(text=json.dumps(data), sources=list(sources))


class FakeFetcher:
    """
    A pretend website: {url: html}. URLs in `disallowed` are refused by "robots.txt";
    URLs missing from `pages` fail like a 404.
    """

    def __init__(self, pages: dict[str, str], disallowed=(), blocked_site=None):
        self.pages = pages
        self.disallowed = set(disallowed)
        self.blocked_site = blocked_site
        self.fetched = []

    def allowed(self, url):
        if self.blocked_site:
            raise FetchBlocked(self.blocked_site)
        return url not in self.disallowed

    def fetch(self, url):
        if url in self.disallowed:
            raise FetchBlocked(f"robots.txt asks bots not to read {url}.")
        if url not in self.pages:
            raise FetchFailed(f"{url} answered 404.")
        self.fetched.append(url)
        return Page(url, url, 200, self.pages[url])
```

### 2. The tests

**Copy** these three files from the reference project into `intelligence/tests/`:

- `test_url_fetcher.py`
- `test_extract_and_diff.py`
- `test_scan_and_committee.py`

### 3. Run them

```bash
pytest
```

### 4. Tidy and commit

```bash
ruff format .
```

```bash
ruff check .
```

```bash
git add -A
```

```bash
git commit -m "Part 8: websites, safely"
```

## Check

- `pytest` prints `195 passed` (141 before + 54 new), with no internet needed.
- `git log --oneline` shows five commits.

**Try breaking it on purpose:** in `intelligence/services/url_fetcher.py` line 112, change

```text
current = check_url(urljoin(current, location))
```

to `current = urljoin(current, location)`, so redirects are no longer checked. Run
`pytest`. `test_redirect_to_a_private_address_is_refused_before_it_is_requested` fails: a
public page could now send our server to `169.254.169.254`. Every other test still passes,
which is exactly why that test exists. Put the line back.

## Line by line: the new parts of `fakes.py`

- **Line 6** · The fetcher's errors and its `Page`, so the fake behaves like the real one.
- **Line 28** · `FakeFetcher`: a pretend website.
- **Lines 29–32** · Docstring: pages are a dictionary; some can be "disallowed".
- **Line 34** · `pages` (`{url: html}`), addresses robots.txt "disallows", and
  `blocked_site`: a message, if the whole site should count as a private address.
- **Lines 35–38** · Keep them, plus `fetched`, a list of every address actually fetched
  (so a test can prove a replay fetched nothing).
- **Lines 40–43** · `allowed`: raise `FetchBlocked` if the whole site is blocked;
  otherwise "allowed unless disallowed".
- **Lines 45–51** · `fetch`: disallowed → `FetchBlocked`; unknown address → `FetchFailed`
  like a 404; otherwise remember it and return a `Page` with status 200.

## What each test proves

### `intelligence/tests/test_url_fetcher.py` (27 tests, fake DNS and fake internet)

| Lines | Test | Proves |
|---|---|---|
| 14–25 | the `dns` fixture | Names point wherever a test says. |
| 63–74 | `test_unsafe_url_shapes_are_refused` | 4 tests: `ftp://`, `file://`, a password in the address, port 8443. |
| 77–96 | `test_private_and_reserved_addresses_are_refused` | **Key test.** 11 tests: this computer, private networks, the cloud metadata address, IPv6, and `::ffff:127.0.0.1` in disguise. |
| 99–102 | `test_one_private_address_among_public_ones_is_enough_to_refuse` | One bad address among good ones: refused. |
| 105–106 | `test_public_address_is_allowed` | A normal site passes. |
| 119–129 | `test_redirect_to_a_private_address_is_refused_before_it_is_requested` | **Key test.** A redirect to `169.254.169.254` is refused, and **never requested**. |
| 132–139 | `test_same_site_redirect_is_followed` | Normal redirects still work. |
| 142–148 | `test_redirect_loops_stop` | A → B → A... stops. |
| 151–155 | `test_large_pages_are_cut_at_the_size_limit` | A 50 KB page with a 1 KB limit is cut. |
| 158–161 | `test_non_html_is_refused` | A PDF is refused. |
| 167–172 | `test_robots_disallow_is_respected` | `Disallow: /checkout` keeps us out of `/checkout/...` only. |
| 175–177 | `test_robots_rules_for_our_bot_name_apply` | Rules written for `AIWarRoomBot` apply to us. |
| 180–182 | `test_missing_robots_txt_means_allowed` | 404 → no rules. |
| 185–187 | `test_robots_txt_server_error_means_stay_out` | 503 → stay out. |
| 190–194 | `test_robots_txt_is_read_once_per_site` | robots.txt is fetched once, not per page. |

### `intelligence/tests/test_extract_and_diff.py` (9 tests, no fakes needed)

| Lines | Test | Proves |
|---|---|---|
| 22–32 | `test_extract_reads_title_prices_products_and_providers` | Title, description, prices (`Rs. 1,299.00` → `₹1299.00`), products, providers; script text is gone. |
| 35–38 | `test_extract_keeps_only_same_site_links` | Links to other sites are dropped. |
| 41–47 | `test_followup_links_prefer_pricing_then_about_then_shipping_and_skip_others` | Pricing first; the blog isn't read. |
| 50–51 | `test_same_page_twice_gives_identical_extract` | Plain code: same page, same extract. |
| 61–63 | `test_no_changes_no_alerts` | Nothing changed → no alerts. |
| 66–70 | `test_removed_and_new_pages` | A removed page warns; a new one informs. |
| 73–80 | `test_big_price_rise_is_a_warning_with_before_and_after` | ₹600 → ₹700 is "up 17 %", a warning, with before and after. |
| 83–86 | `test_small_price_change_is_info` | ₹600 → ₹620 is only info. |
| 89–97 | `test_new_products_and_new_competitors` | New products inform; a new competitor warns, with its note. |

### `intelligence/tests/test_scan_and_committee.py` (18 tests, fake website and fake Gemini)

| Lines | Test | Proves |
|---|---|---|
| 67–79 | `test_first_scan_reads_pages_builds_profile_and_sets_baseline` | The whole pipeline: pages, a skipped 404, the profile, a baseline, no alerts. |
| 82–101 | `test_rescan_raises_alerts_for_what_changed` | **Key test.** Price up, page gone, new competitor: three alerts. |
| 104–111 | `test_unchanged_site_scanned_three_times_raises_no_alerts` | **Key test.** The bug from lesson 8.7 stays fixed. |
| 114–117 | `test_robots_disallow_stops_the_scan` | robots.txt says no → blocked, nothing read. |
| 120–123 | `test_private_address_blocks_the_scan` | A private address → blocked. |
| 126–130 | `test_scan_still_completes_when_ai_is_unavailable` | No key → the scan still completes. |
| 133–140 | `test_profile_citing_a_page_we_never_fetched_is_repaired` | **Key test.** A made-up citation triggers the repair, with the reason. |
| 143–150 | `test_inference_may_not_carry_a_url` | A guess with a link triggers the repair. |
| 153–160 | `test_website_text_is_sent_as_untrusted_data` | **Key test.** "SYSTEM: ignore your rules" arrives **inside** `<website_content>`, and the prompt says to ignore instructions there. |
| 163–166 | `test_thin_js_site_lets_gemini_read_the_urls` | An almost empty page → the `url_context` tool. |
| 172–190 | `test_start_scan_returns_events_url_and_stream_runs_it` | 202, then the stream runs it; opening it again replays without fetching. |
| 193–196 | `test_scan_needs_a_website_url` | No address → 422 naming `url`. |
| 199–202 | `test_another_orgs_scan_stream_is_404` | **Key test.** Bob's scan: 404 for Alice, and it's **not** started. |
| 250–259 | `test_committee_is_one_call_with_four_desks_that_may_disagree` | One call; four desks; disagreement kept. |
| 262–269 | `test_committee_missing_a_desk_is_repaired` | Two `risk` desks → the repair. |
| 272–274 | `test_committee_needs_something_to_review` | Nothing to review → a clear error, no call. |
| 277–283 | `test_committee_endpoint` | 404 before, 201 new, 200 cached. |
| 286–288 | `test_unread_alerts_sort_first_on_every_database` | Unread alerts sort first on PostgreSQL too. |

## If it didn't work

| You see | Fix |
|---|---|
| `ImportError: cannot import name 'FakeFetcher'` | You still have Part 7's `fakes.py`. Replace it (step 1). |
| `fixture 'alice_shop' not found` | `conftest.py` (Part 5) must be in the `my-warroom` folder itself. |
| A test fails with a real network error | Something calls the real fetcher. Compare that file with the reference project. |

## Quiz

1. How can a test check that `127.0.0.1` is refused without asking a real DNS server?
2. What does `test_another_orgs_scan_stream_is_404` check besides the 404?
3. Why does the test in the "break it" exercise matter so much, when 26 other fetcher
   tests still passed?

---

**Part 8 done! ** AI WarRoom can now read a website without becoming a weapon against
its own network, notice what changed, and gather four AI opinions without hiding their
disagreements. Next, a **human** makes the call:
[Part 9 · Decisions](../09-decisions/README.md).

<details><summary>Quiz answers</summary>

1. The `dns` fixture uses monkeypatch to replace `resolve` with a dictionary lookup, so
   `sneaky.test` can "point to" `127.0.0.1`.
2. That the scan's status is still `pending`: opening someone else's stream must not run
   their scan.
3. Without it, nothing would notice that redirects were no longer checked, and that's
   exactly how a real SSRF attack gets through.

</details>
