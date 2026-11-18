# 7.7 · The AI client, part 2

**Time:** 50 minutes · **Before this:** [7.6](06-ai-client-part-1.md).

## Read

Now the heart of the file: `generate(...)`. It follows the six steps in the docstring
you typed in lesson 7.6. Here they are as a flow:

```text
generate(business, kind, task, payload, schema, ...)
  │
  1. CACHE   same question asked before for this business? ── yes ──► return the saved answer
  │                                                                  (no call, no quota)
  2. BUDGET  used up today's calls? ── yes ──► "AI budget used up" (simulations still work)
  │
  3. CALL    send it ── 429 / 5xx / timeout? ──► wait 2 s, retry; wait 4 s, retry; then give up
  │
  4. CHECK   matches the schema (and the extra check)?
  │            no ──► ask ONCE more, with the reason ──► still no ──► save as failed, stop
  │
  5. GUARD   flag numbers we didn't send
  │
  6. SAVE    an AIAnalysis row: model, prompt version, answer, flags, sources, attempts
```

### Why "exponential backoff with jitter"?

When Gemini is busy, retrying **immediately** makes it busier. So we wait, and wait
longer each time: about 2 seconds, then about 4 (that's "exponential": 2¹, 2²). The
**jitter** adds a random fraction of a second, so a hundred programs that failed at the
same moment don't all retry at the same moment too. If Google says how long to wait, we
do what it says, unless it's more than 20 seconds; then we stop and tell the user to try
again shortly, instead of freezing their page.

### Why only one repair attempt?

If the answer has the wrong shape, we ask again and include the reason ("confidence:
Input should be 'low', 'medium' or 'high'"). Models usually fix it. If the second answer
is wrong too, something is badly off, and more retries would just spend quota. So we
save a **failed** analysis with the reason and stop.

## Do

Add these two pieces to the **end** of `intelligence/services/ai_client.py`.

### Piece 4: `generate` (lines 224–320)

<!-- source: intelligence/services/ai_client.py:224-320 -->
```python
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
    check=None,  # extra rule: check(parsed_answer, sources_used) raises ValueError
    tools: tuple[str, ...] = (),
    model: str | None = None,
    data_tag: str = "simulation_data",
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
                user=render_user_message(payload, feedback, data_tag), json_schema=json_schema,
                tools=tools,
            )  # fmt: skip
            try:
                parsed = schema.model_validate_json(reply.text)
                if check:
                    check(parsed, reply.sources)
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
```

### Piece 5: retries and helpers (lines 323–354)

<!-- source: intelligence/services/ai_client.py:323-354 -->
```python
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
```

## Check

```bash
python manage.py check
```

`System check identified no issues (0 silenced).` The real test of this file is lesson
7.9: 15 tests that play back good answers, broken answers, rate limits and timeouts with a
fake Gemini.

## Line by line

### Piece 4

- **Lines 224–226** · Section banner.
- **Lines 227–233** · `input_hash`: the fingerprint of a question. It includes the
  **task**, the **prompt version**, the **model** and the **data**. Change any of them (a
  new prompt version, say) and it's a new question, so the old cached answer isn't
  reused.
- **Line 236** · `calls_today()`: how many real calls today.
- **Line 237** · Midnight today, in UTC (the world's reference time zone). Google's
  free-tier day resets at midnight Pacific time, but any fixed midnight works as a fair
  daily limit.
- **Line 238** · Add up `attempts` of every analysis created since midnight.
  `aggregate(n=Sum("attempts"))` asks the database to do the adding and returns
  `{"n": total}`.
- **Line 239** · `None` (no rows yet) becomes 0.
- **Lines 242–256** · `generate(...)`. All arguments are by-name (`*`). The main ones:
  which business and kind, which prompt (`task`), the data (`payload`), the Pydantic
  class (`schema`). Optional: the run or scan it's about, an extra `check` function,
  tools, a different model, the tag name, and a transport (tests pass a fake one).
- **Line 257** · Load the prompt file.
- **Line 258** · Use the model passed in, or the one in settings (`.env`).
- **Line 259** · The question's fingerprint.
- **Lines 261–267** · **Step 1, cache.** A successful answer for this business, this
  kind and this fingerprint? Mark it `from_cache` and return it. No call.
- **Lines 269–275** · **Step 2, budget.** Get a transport first (no key → a clear error
  from lesson 7.6). Then, if today's calls reached the budget, stop politely.
- **Lines 277–280** · Prepare the record (not saved yet). `# fmt: skip` keeps it on
  three lines.
- **Line 281** · The JSON Schema made from the Pydantic class (lesson 7.4).
- **Line 282** · Three variables that start empty.
- **Lines 285–286** · **Steps 3 and 4.** Up to two tries: the first, and one repair.
- **Lines 287–291** · Call (with retries, below). The message includes the rejection
  reason on the second try.
- **Line 293** · **Check the shape.** `model_validate_json` reads the JSON text and
  checks it against the schema in one go.
- **Lines 294–295** · Then the extra rule, if there is one (lesson 7.8's "only known
  metric keys").
- **Line 296** · Both passed: leave the loop.
- **Lines 297–299** · A check failed: forget the answer, keep a short reason for the
  repair message, and log a warning.
- **Lines 300–302** · An `AIError` (rate limit, no connection...): save the record as
  failed with the message, then `raise` the same error again for the API to report.
- **Lines 304–307** · Two invalid answers: save as failed, and raise `AIInvalidOutput`.
  The user sees a calm message, never the broken text.
- **Line 310** · **Step 5.** The answer as a plain dictionary.
- **Lines 311–312** · Mark it OK and store it.
- **Line 313** · **The guardrail** (lesson 7.5): flag numbers not in the payload.
- **Line 314** · Sources the AI used.
- **Line 315** · **Step 6, save.**
- **Lines 316–319** · Log one line: attempts and number of flags.
- **Line 320** · Return the saved analysis.

### Piece 5

- **Line 323** · `_call_with_retries`: one call, retried if needed. `**request` collects
  all the by-name arguments into a dictionary and passes them on.
- **Line 324** · Up to 3 attempts (1 + `MAX_RETRIES`).
- **Line 325** · Count **every** attempt, so the budget is honest.
- **Lines 326–327** · Try; on success, return straight away.
- **Line 328** · A retryable failure...
- **Lines 329–330** · ...was it the last attempt? Or did Google ask us to wait too long?
- **Lines 331–336** · Then give up with a clear message: rate limited ("try again in a
  minute"), or no answer in time.
- **Lines 337–338** · Otherwise wait: Google's suggested delay, or 2, then 4 seconds,
  plus up to half a second of random jitter.
- **Lines 339–340** · Log it and sleep.
- **Line 341** · The loop always returns or raises before here. If it ever didn't, this
  line makes the bug loud instead of silent.
- **Lines 344–348** · `_short_reason`: turn a Pydantic error into a short line like
  `key_findings.0.text: String should have at most 400 characters`, at most five
  problems. Other errors: their text, cut to 500 characters.
- **Lines 351–354** · `_save_failed`: mark failed, store why, save.

## If it didn't work

| You see | Fix |
|---|---|
| `NameError: name 'Sum' is not defined` | Line 37 (in piece 1) imports it. |
| `IndentationError` near line 300 | `except AIError` lines up with the `try:` on line 285, not the inner one on line 292. |

## Quiz

1. You edit the prompt and raise its version. Will old cached answers be reused?
2. What's the longest a user waits on retries before getting an answer or an error?
3. Why is a failed answer saved at all?

---

**Next:** [7.8 · Explain a run](08-explain-a-run.md)

<details><summary>Quiz answers</summary>

1. No. The version is part of the fingerprint, so it's a new question.
2. About 2 + 4 seconds of waiting (plus up to a second of jitter), on top of the calls
   themselves; never more than a 20-second wait suggested by Google.
3. So the history shows every attempt and why it failed, and so its `attempts` still
   count towards the daily budget.

</details>
