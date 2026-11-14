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


def render_user_message(payload: dict, feedback: str | None = None) -> str:
    # The data sits inside clearly marked tags; the prompt says text inside is data,
    # never instructions. That's our main defence against prompt injection via names.
    message = (
        "<simulation_data>\n"
        + json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=True)
        + "\n</simulation_data>"
    )
    if feedback:
        message += (
            "\n\nYour previous answer was rejected for this reason:\n"
            f"{feedback}\nReturn a corrected answer that follows the schema and the rules."
        )
    return message


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
    """Links Gemini used via Google Search / URL context, if any."""
    sources = []
    for candidate in response.candidates or []:
        metadata = getattr(candidate, "grounding_metadata", None)
        for chunk in getattr(metadata, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            if web and web.uri:
                sources.append({"url": web.uri, "title": web.title or web.uri})
    return sources


def default_transport() -> GeminiTransport:
    if not settings.GEMINI_API_KEY:
        raise AIUnavailable(
            "AI analysis is off: no GEMINI_API_KEY is configured. Simulations still work."
        )
    return GeminiTransport(settings.GEMINI_API_KEY, settings.AI_TIMEOUT_SECONDS)


# --------------------------------------------------------------------------------------
# The public function
# --------------------------------------------------------------------------------------
def input_hash(task: str, prompt_version: str, model: str, payload: dict) -> str:
    canonical = json.dumps(
        {"task": task, "prompt": prompt_version, "model": model, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def calls_today() -> int:
    midnight = datetime.combine(datetime.now(UTC).date(), dtime.min, UTC)
    total = AIAnalysis.objects.filter(created_at__gte=midnight).aggregate(n=Sum("attempts"))["n"]
    return total or 0


def generate(
    *,
    business,
    kind: str,
    task: str,
    payload: dict,
    schema: type[BaseModel],
    run=None,
    scan=None,
    check=None,
    tools: tuple[str, ...] = (),
    model: str | None = None,
    transport=None,
) -> AIAnalysis:
    prompt = load_prompt(task)
    model = model or settings.GEMINI_MODEL
    digest = input_hash(task, prompt.version, model, payload)

    # 1. Cache: same business, same question, same model, same prompt version.
    cached = AIAnalysis.objects.filter(
        business=business, kind=kind, input_hash=digest, status=AIAnalysis.Status.OK
    ).first()
    if cached:
        cached.from_cache = True
        return cached

    # 2. Budget
    transport = transport or default_transport()
    if calls_today() >= settings.AI_DAILY_CALL_BUDGET:
        raise AIUnavailable(
            "Today's AI budget is used up. Simulations still work; analysis resumes after "
            "00:00 UTC."
        )

    record = AIAnalysis(
        business=business, run=run, scan=scan, kind=kind, model_name=model,
        prompt_version=prompt.version, input_hash=digest,
    )  # fmt: skip
    json_schema = schema.model_json_schema()
    feedback, parsed, reply = None, None, None

    # 3 + 4. Call, validate, and allow one repair attempt.
    try:
        for _ in range(2):
            reply = _call_with_retries(
                transport, record, model=model, system=prompt.text,
                user=render_user_message(payload, feedback), json_schema=json_schema,
                tools=tools,
            )  # fmt: skip
            try:
                parsed = schema.model_validate_json(reply.text)
                if check:
                    check(parsed)
                break
            except (ValidationError, ValueError) as error:
                parsed, feedback = None, _short_reason(error)
                logger.warning("AI answer rejected (%s): %s", task, feedback)
    except AIError as error:
        _save_failed(record, error.message)
        raise

    if parsed is None:
        message = "The analyst's answer didn't pass validation twice, so it isn't shown."
        _save_failed(record, f"{message} Last reason: {feedback}")
        raise AIInvalidOutput(message)

    # 5 + 6. Guardrail, then save.
    answer = parsed.model_dump()
    record.status = AIAnalysis.Status.OK
    record.output = answer
    record.flagged_numbers = flag_unsupported_numbers(answer, payload)
    record.sources = reply.sources
    record.save()
    logger.info(
        "AI %s ok: %s attempts, %s flagged numbers", task, record.attempts,
        len(record.flagged_numbers),
    )  # fmt: skip
    return record


def _call_with_retries(transport, record, **request) -> Reply:
    for attempt in range(MAX_RETRIES + 1):
        record.attempts += 1
        try:
            return transport.generate(**request)
        except _Retryable as error:
            last_attempt = attempt == MAX_RETRIES
            too_long = error.server_delay is not None and error.server_delay > MAX_SERVER_DELAY_S
            if last_attempt or too_long:
                if error.rate_limited:
                    raise AIRateLimited(
                        "Gemini's free-tier rate limit was hit. Try again in a minute."
                    ) from error
                raise AIProviderError("Gemini didn't answer in time. Try again shortly.") from error
            # Exponential backoff with jitter: about 2 s, then 4 s, unless told otherwise.
            delay = error.server_delay or (2 ** (attempt + 1)) + random.uniform(0, 0.5)
            logger.info("Gemini retry in %.1fs (%s)", delay, error)
            time.sleep(delay)
    raise AssertionError("unreachable")


def _short_reason(error: Exception) -> str:
    if isinstance(error, ValidationError):
        problems = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors()[:5]]
        return "; ".join(problems)
    return str(error)[:500]


def _save_failed(record: AIAnalysis, message: str) -> None:
    record.status = AIAnalysis.Status.FAILED
    record.error = message
    record.save()
