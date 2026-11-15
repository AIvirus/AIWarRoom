# Part 7 · AI with Gemini

**Time:** about 4 hours · **Before this:** [Part 6](../06-simulation-engine/README.md)
(your `my-warroom` passes 104 tests).

The engine from Part 6 gives exact numbers. But a table of 50 numbers is hard to read.
In this part, an **AI** (Google's Gemini) reads a finished run and explains it in plain
words: what happened, the trade-offs, what to check next.

The hard part isn't calling the AI. It's **not trusting it blindly**. An AI can write a
confident sentence with a number that is simply wrong. So AI WarRoom wraps every AI call
in safety layers, and you'll build each one:

| Layer | Protects against |
|---|---|
| An **allowlist** of what we send | Leaking private data; giving the AI things to misuse |
| Data inside clear **tags**, marked "data, not instructions" | **Prompt injection** (text that tries to give the AI orders) |
| A strict **schema** (Pydantic) | Answers in the wrong shape; missing parts |
| One **repair** attempt | A single bad answer stopping everything |
| The **number guardrail** | Made-up numbers (they're flagged for the reader) |
| A **cache** and a **daily budget** | Spending your free quota twice on the same question |
| **Retries** with backoff | Gemini being busy for a moment |
| A clear **label** on every answer | Anyone mistaking AI text for the simulation's maths |

And the app keeps working with **no AI at all**: the simulations never depend on it.

## What you need

A free **Gemini API key** from Google AI Studio. Lesson 7.2 shows you how. The tests in
this part never use your key: they use a **fake** Gemini, so they're free and work
offline.

## Lessons in this part (do them in order)

| # | Lesson | You will build |
|---|---|---|
| 7.1 | [What an LLM is](01-what-an-llm-is.md) | (Reading only) how it works, why it invents things, and our defences |
| 7.2 | [Your Gemini key and first call](02-key-and-first-call.md) | A key in `.env`, and a 10-line script that talks to Gemini |
| 7.3 | [The AI tables](03-the-ai-tables.md) | `intelligence/models.py`: analyses, scans, alerts |
| 7.4 | [Schemas and the prompt](04-schemas-and-the-prompt.md) | `schemas.py` and `prompts/run_explanation.md` |
| 7.5 | [The number guardrail](05-the-number-guardrail.md) | `guardrails.py`: catch numbers the AI made up |
| 7.6 | [The AI client, part 1](06-ai-client-part-1.md) | Errors, prompts, the Gemini transport |
| 7.7 | [The AI client, part 2](07-ai-client-part-2.md) | Cache, budget, retries, repair, save |
| 7.8 | [Explain a run](08-explain-a-run.md) | `context.py`, `explain.py`, the API |
| 7.9 | [Tests, try it, commit](09-tests-try-it-commit.md) | 36 new tests with a fake Gemini, a real explanation, a commit |

When you finish, go to [Part 8 · Websites, safely](../08-websites-safely/README.md).
