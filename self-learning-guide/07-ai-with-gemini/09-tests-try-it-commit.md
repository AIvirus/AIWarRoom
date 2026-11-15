# 7.9 · Tests, try it, commit

**Time:** 50 minutes · **Before this:** [7.8](08-explain-a-run.md).

## 📖 Read

How do you test code that calls an AI whose answers change every time, costs quota, and
needs the internet? You **don't call it**. You plug in a **fake transport** (lesson 7.6)
that plays back a **script** of answers you wrote:

```python
transport = FakeTransport(bad_answer, good_answer)
explain_run(run, transport=transport)
```

The first call gets `bad_answer`, the second `good_answer`. The fake also **records**
every request, so a test can check exactly what we sent (the tags, the allowlist). And
you can script the things that are hard to make happen for real: a rate limit, a
timeout, two broken answers in a row.

A fake like this is called a **test double**. The tests use your settings, but
`config/settings/test.py` sets `GEMINI_API_KEY = ""` (lesson 4.3), so even a mistake
can't reach the real Gemini.

Then, after the tests, you'll try the **real** Gemini once in the browser.

## ⌨️ Do

### 1. The fake, and the tests

Make `intelligence/tests/` with an **empty** `__init__.py`. Then create
`intelligence/tests/fakes.py` from [`for-now/intelligence/tests/fakes.py`](for-now/intelligence/tests/fakes.py)
(Part 8 adds a fake **website** to it):

<!-- source: self-learning-guide/07-ai-with-gemini/for-now/intelligence/tests/fakes.py:1-24 -->
```python
"""Test doubles for the outside world: Gemini and websites. No network, fully scripted."""

import json

from intelligence.services.ai_client import Reply


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
```

- **Line 1** · Docstring.
- **Lines 3–5** · `json`, and the `Reply` class from lesson 7.6.
- **Lines 8–9** · `FakeTransport`: plays back a script.
- **Lines 11–13** · `*script` collects all the arguments into a tuple; we keep them as a
  list, plus an empty list of requests.
- **Line 15** · The same method name and arguments as the real transport, so the client
  can't tell the difference.
- **Line 16** · Remember what was asked.
- **Line 17** · Take the next scripted step (`pop(0)` removes the first item).
- **Lines 18–19** · If the step is an exception (like a rate limit), raise it.
- **Line 20** · Otherwise return it as the answer.
- **Lines 23–24** · `reply(data)`: a quick way to make a `Reply` from a dictionary.

Now **copy** these two test files from the reference project:

- `intelligence/tests/test_guardrails.py`
- `intelligence/tests/test_ai_client.py`

### 2. Run them

```bash
pytest
```

### 3. Try the real Gemini

Start the server, log in, open the console and paste the `api()` helper (lesson 5.7).
Then rebuild lesson 6.9's shop and run (the same lines as in 6.9, up to and including
`const run = ...`). Now ask for an explanation:

```js
const ai = await api("POST", `/api/v1/runs/${run.id}/analysis/`)
```

After a few seconds: `201`. Look at it:

```js
ai.output.headline
```

```js
ai.output.key_findings
```

```js
ai.flagged_numbers
```

```js
ai.label
```

Read the findings. Is every number one from lesson 6.1? Is each finding's
`metric_keys` list pointing at the right metrics? `flagged_numbers` is usually `[]`; if
it isn't, each entry shows exactly which number the AI wrote that wasn't in the data,
and where.

Ask **again**:

```js
const again = await api("POST", `/api/v1/runs/${run.id}/analysis/`)
```

→ `200` immediately, `again.from_cache` is `true`, and `again.id === ai.id`. No second
call to Google, no quota spent.

Finally see it in the admin: **http://127.0.0.1:8000/admin/** → **AI analyses**. One row,
kind "Run explanation", status OK.

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
git commit -m "Part 7: AI with Gemini"
```

Before you commit, check `git status` doesn't list `.env`. (It shouldn't: `.gitignore`.)

## ✅ Check

- `pytest` prints `140 passed` (104 before + 36 new), **without** using your key.
- The real explanation came back with `201`, then `200` from the cache.
- `git log --oneline` shows four commits, and `git show --stat HEAD` doesn't mention
  `.env`.

**Try breaking it on purpose:** in `intelligence/services/ai_client.py` line 313,
change `flag_unsupported_numbers(answer, payload)` to `[]`. Run `pytest`.
`test_invented_number_is_flagged_not_hidden` fails: an AI headline saying "saves
₹14,550 a day" would now go out unflagged. Put it back.

## 🔍 What each test proves

### `intelligence/tests/test_guardrails.py` (21 tests, no AI at all)

| Lines | Test | Proves |
|---|---|---|
| 12–26 | `test_numbers_are_read_the_way_people_write_them` | 8 tests: `₹21,000`, `₹1,00,000`, `8.5k`, `1.2 lakh`, `3 crore`, `26.21%`, negatives. |
| 29–30 | `test_month_words_are_not_mistaken_for_millions` | "10 months" is 10, not 10 million. |
| 33–38 | `test_significant_digits_count_what_was_actually_written` | 6 tests: `21000` has 2 meaningful digits, `8514.74` has 6. |
| 41–49 | `test_near_miss_numbers_are_flagged` | `₹15k` and `₹14k` pass for 14,700; `₹14,550` and `₹13,000` don't. |
| 52–54 | `test_numbers_in_nested_data_include_numeric_strings` | Numbers hidden in text and lists are found. |
| 57–58 | `test_booleans_are_not_numbers` | `True` isn't counted as 1. |
| 71–76 | `test_rounded_versions_of_sent_numbers_are_accepted` | "about ₹8,500" for 8,514.74 is fine. |
| 79–90 | `test_invented_or_derived_numbers_are_flagged_with_their_location` | ⭐ A made-up difference (₹2,124) and a made-up "industry average" (40 %) are flagged, with their exact location. |
| 93–94 | `test_small_counts_are_not_flagged` | "3 strategies over 2 days" is fine. |

### `intelligence/tests/test_ai_client.py` (15 tests, fake Gemini)

| Lines | Test | Proves |
|---|---|---|
| 69–77 | `test_valid_answer_is_saved_with_model_prompt_version_and_no_flags` | A good answer is saved with its model, prompt version and 1 attempt. |
| 80–90 | `test_payload_is_allowlisted_and_wrapped_as_data` | ⭐ The data is inside `<simulation_data>`; an "IGNORE ALL RULES" description is **never sent**; timelines stay out. |
| 93–98 | `test_same_run_twice_is_served_from_cache_without_a_call` | The second ask makes **no** call. |
| 101–105 | `test_invented_number_is_flagged_not_hidden` | ⭐ "₹14,550 a day" is saved **and** flagged. |
| 108–113 | `test_invalid_json_gets_one_repair_attempt_with_the_reason` | A half answer gets one retry, which includes the reason. |
| 116–122 | `test_unknown_metric_key_counts_as_invalid` | Citing `industry.average` triggers the repair. |
| 125–130 | `test_two_invalid_answers_fail_gracefully_and_are_recorded` | Two bad answers → a calm error and a failed row with 2 attempts. |
| 133–139 | `test_rate_limit_is_retried_with_backoff_then_succeeds` | A 429 that says "wait 3 s" is waited for exactly 3 s. |
| 142–146 | `test_persistent_rate_limit_gives_up_after_two_retries` | Three 429s → give up; 3 attempts counted. |
| 149–151 | `test_long_server_delay_fails_fast_instead_of_hanging` | "Wait 600 s" → stop now instead of freezing the page. |
| 154–160 | `test_daily_budget_stops_calls` | With a budget of 1, the second (different) question is refused. |
| 163–166 | `test_missing_api_key_is_a_clear_error` | No key → a message that names `GEMINI_API_KEY`. |
| 172–183 | `test_analysis_endpoint_creates_then_serves_cache` | The API: 404 before, 201 new, 200 from cache, the label is there. |
| 186–190 | `test_analysis_endpoint_reports_missing_key_as_503` | No key → 503 `ai_unavailable`. |
| 193–203 | `test_cannot_analyse_another_orgs_run` | ⭐ Bob's run is 404 for Alice. |

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'intelligence.services.url_fetcher'` | You copied the finished `fakes.py`. Use the for-now version above. |
| `503` `ai_unavailable` in the browser | No key in `.env`, or the server was started before you added it. Stop and restart `runserver`. |
| `429` `ai_rate_limited` | The free tier's per-minute limit. Wait a minute. |
| `502` `ai_invalid_output` | Gemini failed validation twice. Try again; check the failed row's `error` in the admin to see why. |
| The browser waits a long time | A retry is waiting (at most about 20 s). Watch the `runserver` terminal for "Gemini retry in ...". |

## ❓ Quiz

1. How do the tests check what we sent to Gemini?
2. Why does `test_payload_is_allowlisted_and_wrapped_as_data` put "IGNORE ALL RULES" in
   the description?
3. You run the tests with no internet. Do they pass?

---

**Part 7 done! 🎉** AI WarRoom can now explain its numbers in plain words, and it checks
the AI instead of trusting it. Next, the AI gets something much less trustworthy to
read: other people's websites. [Part 8 · Websites, safely](../08-websites-safely/README.md).

<details><summary>Quiz answers</summary>

1. The fake transport records every request in `transport.requests`.
2. To prove that untrusted free text (a classic prompt-injection hiding place) is never
   sent at all.
3. Yes. They use the fake transport; nothing goes to the internet.

</details>
