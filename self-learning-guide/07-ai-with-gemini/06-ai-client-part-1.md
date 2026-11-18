# 7.6 · The AI client, part 1

**Time:** 50 minutes · **Before this:** [7.5](05-the-number-guardrail.md).

## Read

`intelligence/services/ai_client.py` is **the only file in the whole app that talks to
Gemini**. Every AI feature goes through its one public function, `generate(...)`. That
means the safety layers are written once and can't be skipped by accident.

It's long, so it's split over two lessons:

| Lesson | Lines | What |
|---|---|---|
| 7.6 (this one) | 1–221 | Errors, loading prompt files, wrapping the data, the **transport** |
| 7.7 | 224–354 | `generate`: cache, budget, call, retry, check, repair, guard, save |

### The transport: a swappable plug

The code that actually sends a request to Google is a small class, the **transport**.
Everything else talks to "a transport", not to Google directly. In tests we plug in a
**fake** transport that plays back answers we wrote (lesson 7.9). Then the tests need no
key, no internet, and cost nothing, and we can test hard cases on purpose: a broken
answer, a "too many requests" error, a timeout.

### HTTP status codes from Gemini

| Code | Means | What we do |
|---|---|---|
| 200 | OK | Use the answer |
| 400, 403 | Bad request, bad key | Stop with a clear error (retrying won't help) |
| 429 | Too many requests (rate limit) | Wait and retry |
| 500, 502, 503, 504 | Google's side had a problem | Wait and retry |

### Errors the rest of the app can show

Each kind of failure gets its own error class with a short **code**. The API turns each
code into an HTTP status and a message a person can understand (lesson 7.8). The app
never shows a Python traceback to a user.

## Do

Create `intelligence/services/ai_client.py`. Type these three pieces now; lesson 7.7
adds the rest.

### Piece 1: the plan and the imports (lines 1–50)

<!-- source: intelligence/services/ai_client.py:1-50 -->
```python
"""
The ONLY module that talks to Gemini.

    analysis = generate(business=..., kind=..., task="run_explanation",
                        payload=context, schema=RunExplanation)

What happens on every call, in order:

  1. CACHE   hash(task, prompt version, model, payload). Seen before for this business?
             Return the stored answer: no API call, no quota spent.
  2. BUDGET  stop before AI_DAILY_CALL_BUDGET live calls a day, so the free tier isn't
             burnt by a loop or a demo that runs all afternoon.
  3. CALL    with a timeout; on 429 / 5xx / timeout retry twice with exponential backoff
             plus jitter, honouring the server's own "retry in N s" hint when it sends one.
  4. CHECK   validate the JSON with Pydantic (and an optional extra check, e.g. "only cite
             metric keys we sent"). If it fails, ask ONCE more with the error attached.
             If that fails too, record a failed analysis and stop.
  5. GUARD   flag every number in the answer that isn't in the payload (guardrails.py).
  6. SAVE    an AIAnalysis row with model, prompt version, flags, sources and attempts.

Tests swap the real transport for a fake one, so they never need a key or a network.
"""

import hashlib
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from datetime import time as dtime
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.db.models import Sum
from pydantic import BaseModel, ValidationError

from intelligence.models import AIAnalysis

from .guardrails import flag_unsupported_numbers

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)  # don't log every request URL

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
MAX_RETRIES = 2  # after the first attempt, for 429 / 5xx / timeouts
MAX_SERVER_DELAY_S = 20  # if Google asks us to wait longer than this, give up politely
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
```

### Piece 2: errors and prompts (lines 53–121)

<!-- source: intelligence/services/ai_client.py:53-121 -->
```python
# --------------------------------------------------------------------------------------
# Errors the rest of the app can show to a user
# --------------------------------------------------------------------------------------
class AIError(Exception):
    code = "ai_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AIUnavailable(AIError):
    code = "ai_unavailable"


class AIRateLimited(AIError):
    code = "ai_rate_limited"


class AIInvalidOutput(AIError):
    code = "ai_invalid_output"


class AIProviderError(AIError):
    code = "ai_provider_error"


class _Retryable(Exception):
    def __init__(self, message: str, server_delay: float | None = None, rate_limited=False):
        super().__init__(message)
        self.server_delay = server_delay
        self.rate_limited = rate_limited


# --------------------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Prompt:
    version: str
    text: str


@lru_cache
def load_prompt(task: str) -> Prompt:
    """Prompt files start with 'version: <name>/<n>' and '---'. Bump n on every edit."""
    raw = (PROMPT_DIR / f"{task}.md").read_text(encoding="utf-8")
    header, _, body = raw.partition("---")
    version = header.strip().removeprefix("version:").strip()
    return Prompt(version=version, text=body.strip())


def render_user_message(
    payload: dict, feedback: str | None = None, tag: str = "simulation_data"
) -> str:
    # The data sits inside clearly marked tags; the prompt says text inside is data,
    # never instructions. That's our main defence against prompt injection, whether it
    # hides in a scenario name or in the text of a company's website.
    message = (
        f"<{tag}>\n"
        + json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=True)
        + f"\n</{tag}>"
    )
    if feedback:
        message += (
            "\n\nYour previous answer was rejected for this reason:\n"
            f"{feedback}\nReturn a corrected answer that follows the schema and the rules."
        )
    return message
```

### Piece 3: the transport (lines 124–221)

<!-- source: intelligence/services/ai_client.py:124-221 -->
```python
# --------------------------------------------------------------------------------------
# Transport: the thin layer around the Google SDK
# --------------------------------------------------------------------------------------
@dataclass
class Reply:
    text: str
    sources: list[dict] = field(default_factory=list)


class GeminiTransport:
    def __init__(self, api_key: str, timeout_seconds: int):
        from google import genai
        from google.genai import types

        self._types = types
        self._client = genai.Client(
            api_key=api_key,
            # Timeout is in milliseconds. Retries are ours (below), so the SDK's are off.
            http_options=types.HttpOptions(timeout=timeout_seconds * 1000),
        )

    def generate(self, *, model, system, user, json_schema, tools=()) -> Reply:
        from google.genai import errors

        types = self._types
        tool_objects = [
            types.Tool(google_search=types.GoogleSearch())
            if name == "google_search"
            else types.Tool(url_context=types.UrlContext())
            for name in tools
        ]
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,  # explanations, not creative writing
            response_mime_type="application/json",
            response_json_schema=json_schema,
            tools=tool_objects or None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        try:
            response = self._client.models.generate_content(
                model=model, contents=user, config=config
            )
        except errors.APIError as error:
            if error.code in RETRYABLE_STATUS:
                raise _Retryable(
                    f"Gemini returned {error.code}",
                    server_delay=_server_retry_delay(error),
                    rate_limited=error.code == 429,
                ) from error
            raise AIProviderError(f"Gemini refused the request ({error.code}).") from error
        except Exception as error:  # noqa: BLE001  - network errors and timeouts
            if "timeout" in type(error).__name__.lower() or "timed out" in str(error).lower():
                raise _Retryable("Gemini timed out") from error
            raise AIProviderError("Couldn't reach Gemini.") from error

        if not response.text:
            raise AIProviderError("Gemini returned an empty answer (possibly safety-filtered).")
        return Reply(text=response.text, sources=_grounding_sources(response))


def _server_retry_delay(error) -> float | None:
    """Google's 429s may say how long to wait, e.g. {"retryDelay": "12s"}."""
    match = re.search(r'"?retryDelay"?\s*[:=]\s*"?(\d+(?:\.\d+)?)s', json.dumps(error.details))
    return float(match.group(1)) if match else None


def _grounding_sources(response) -> list[dict]:
    """
    Links Gemini actually used: Google Search results (grounding_metadata) and pages it
    read with the URL-context tool (url_context_metadata, successful retrievals only).
    """
    sources, seen = [], set()

    def add(url, title):
        if url and url not in seen:
            seen.add(url)
            sources.append({"url": url, "title": title or url})

    for candidate in response.candidates or []:
        grounding = getattr(candidate, "grounding_metadata", None)
        for chunk in getattr(grounding, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            if web:
                add(web.uri, web.title)
        url_context = getattr(candidate, "url_context_metadata", None)
        for item in getattr(url_context, "url_metadata", None) or []:
            if "SUCCESS" in str(getattr(item, "url_retrieval_status", "")):
                add(item.retrieved_url, None)
    return sources


def default_transport() -> GeminiTransport:
    if not settings.GEMINI_API_KEY:
        raise AIUnavailable(
            "AI analysis is off: no GEMINI_API_KEY is configured. Simulations still work."
        )
    return GeminiTransport(settings.GEMINI_API_KEY, settings.AI_TIMEOUT_SECONDS)
```

## Check

```bash
python manage.py shell
```

```python
from intelligence.services.ai_client import load_prompt, render_user_message

p = load_prompt("run_explanation")
p.version
print(render_user_message({"business": "Kirana Express", "lost": "21000.00"}))
```

You should see `'run-explanation/2'`, then the data wrapped in tags:

```text
<simulation_data>
{
 "business": "Kirana Express",
 "lost": "21000.00"
}
</simulation_data>
```

Type `exit()`. (We use `manage.py shell` this time because the file imports Django
settings and models.)

## Line by line

### Piece 1

- **Lines 1–22** · The docstring is the plan for the whole file: six steps, in order.
  Read it twice; lesson 7.7 follows it exactly.
- **Lines 24–34** · Standard-library tools: `hashlib` (fingerprints), `json`, `logging`,
  `random` (for "jitter", lesson 7.7), `re`, `time` (to wait), dates, `lru_cache`
  (remember a function's result), `Path` (file paths).
- **Line 32** · `time as dtime`: there are two different things called `time` here (the
  module and the clock-time class), so one gets another name.
- **Lines 36–38** · Django settings, `Sum` for adding up a column in the database, and
  Pydantic.
- **Line 40** · The model from lesson 7.3.
- **Line 42** · The guardrail from lesson 7.5.
- **Line 44** · A logger for this file.
- **Line 45** · The `httpx` library (which Google's package uses) logs a line for every
  request. This hides those lines unless something goes wrong, so the server log stays
  readable.
- **Line 47** · Where the prompt files are: from this file, go up two folders
  (`services` → `intelligence`), then into `prompts`.
- **Lines 48–50** · Retry at most 2 more times; never wait more than 20 seconds; which
  status codes are worth retrying.

### Piece 2

- **Lines 56–61** · `AIError`: the parent of every AI error. Each has a `code` and a
  `message` for people.
- **Lines 64–77** · Four kinds, each with its own code: AI is switched off or the budget
  is used up; rate limited; the answer was invalid; Google refused or couldn't be
  reached.
- **Lines 80–84** · `_Retryable`: used **inside** this file only (the `_` says so), for
  "try again". It may carry how long Google asked us to wait, and whether it was a rate
  limit.
- **Lines 90–93** · A prompt: its version and its text.
- **Line 96** · `@lru_cache`: the first call reads the file; later calls with the same
  `task` return the remembered result without reading the disk again.
- **Line 97** · `load_prompt("run_explanation")` reads `prompts/run_explanation.md`.
- **Line 98** · Docstring: the file format, and the rule to raise the version.
- **Line 99** · Read the whole file as text.
- **Line 100** · `partition("---")` splits it at the **first** `---` into three parts:
  before, the `---` itself, after. `_` is a name for "a value I don't need".
- **Line 101** · `"version: run-explanation/2"` → `"run-explanation/2"`.
- **Line 102** · Return the version and the instructions.
- **Lines 105–107** · `render_user_message`: build the user message from the data, an
  optional reason the last answer was rejected, and the tag name.
- **Lines 108–110** · The comment explains the tags: the main defence against prompt
  injection (lesson 7.1).
- **Lines 111–115** · The data as JSON, inside `<tag>` and `</tag>`.
  `ensure_ascii=False` keeps `₹` as `₹` instead of `₹`; `sort_keys=True` keeps the
  order fixed.
- **Lines 116–120** · On a repair attempt, add the rejection reason and ask for a
  corrected answer.
- **Line 121** · Return the message.

### Piece 3

- **Lines 127–130** · `Reply`: the answer's text and any sources.
- **Line 133** · The real transport.
- **Lines 134–136** · Import Google's library **inside** `__init__`, so the rest of the
  app (and the tests) can load without touching it.
- **Lines 138–143** · Make the client with the key and a timeout. Google wants the
  timeout in **milliseconds**, hence `× 1000`.
- **Line 145** · `generate(...)`: send one request. The `*` makes every argument
  by-name only.
- **Line 146** · Google's error classes.
- **Lines 149–154** · Optional tools (Part 8): Google Search, or reading web pages.
- **Lines 155–162** · The settings for this request:
  - **156** · The system prompt.
  - **157** · Temperature 0.2: steady, not creative (lesson 7.1).
  - **158–159** · Answer in JSON, in this schema's shape.
  - **160** · Tools, or none.
  - **161** · Don't let the model call our Python functions by itself.
- **Lines 163–166** · Send it.
- **Lines 167–174** · Google answered with an error. Retryable codes become
  `_Retryable` (with the wait time Google suggested, if any). Anything else is a
  provider error. `from error` keeps the original error attached for the logs.
- **Lines 175–178** · No answer at all: a timeout is retryable; anything else (no
  internet) is a provider error. The `# noqa: BLE001` comment tells a linter that
  catching **every** exception here is deliberate.
- **Lines 180–181** · An empty answer (for example, blocked by Google's safety filter) is
  an error, not an empty explanation.
- **Line 182** · Return the text and the sources.
- **Lines 185–188** · Google's 429 errors sometimes say `"retryDelay": "12s"`. This regex
  finds the number of seconds, or returns `None`.
- **Lines 191–213** · Collect the links Gemini really used (Part 8), without
  duplicates. `getattr(x, "name", None)` reads an attribute that might not exist.
- **Lines 216–221** · The default transport. **No key → a clear message**: "AI analysis
  is off... Simulations still work." The app runs without AI.

## If it didn't work

| You see | Fix |
|---|---|
| `FileNotFoundError: ...prompts\run_explanation.md` | The prompt file must be in `intelligence/prompts/` (lesson 7.4). |
| `version` shows the whole first paragraph | Line 2 of the prompt file must be exactly `---`. |
| `ImportError: cannot import name 'flag_unsupported_numbers'` | Check lesson 7.5's file name: `intelligence/services/guardrails.py`. |

## Quiz

1. Why is the transport a separate, swappable class?
2. Which status codes are retried, and which aren't?
3. What happens if there's no `GEMINI_API_KEY`?

---

**Next:** [7.7 · The AI client, part 2](07-ai-client-part-2.md)

<details><summary>Quiz answers</summary>

1. So tests can plug in a fake that needs no key or internet, and can play back hard
   cases on purpose.
2. 429 and 500/502/503/504 are retried (the problem may pass). Others, like a bad key,
   aren't: retrying won't fix them.
3. `AIUnavailable` with a clear message. AI features say they're off; simulations keep
   working.

</details>
