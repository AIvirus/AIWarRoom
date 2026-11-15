# 7.2 · Your Gemini key and first call

**Time:** 20 minutes · **Before this:** [7.1](01-what-an-llm-is.md).

## 📖 Read

To use Gemini from a program you need an **API key**: a long secret text that says "this
request is from my account". Google gives free keys with daily limits, which is plenty
for this course.

A key is like a password. Rules:

- It lives **only** in `.env`. Since Part 4, `.gitignore` keeps `.env` out of Git, so it
  never reaches GitHub.
- Never paste it into code, a screenshot, a chat or a lesson question.
- If it leaks, delete it in AI Studio and make a new one.

## ⌨️ Do

### 1. Get a key

1. Open **https://aistudio.google.com** and sign in with a Google account.
2. Find **Get API key** (in the menu on the left), then **Create API key**.
3. Copy the key. It's a long line of letters and numbers.

(Google changes these screens from time to time. If the buttons look different, look for
"API keys".)

### 2. Put it in `.env`

Open `my-warroom/.env` (you made it from `.env.example` in Part 4) and find the line
`GEMINI_API_KEY=`. Paste your key right after the `=`, with no spaces or quotes:

```text
GEMINI_API_KEY=paste-your-key-here
```

Leave `GEMINI_MODEL=gemini-3.5-flash-lite` as it is. Save the file.

Check Git really ignores it:

```bash
git check-ignore .env
```

It must print `.env`. (If it prints nothing, stop and fix `.gitignore` from lesson 4.2
before going on.)

### 3. Your first call

Copy [`practice/hello_gemini.py`](practice/hello_gemini.py) into `my-warroom`:

<!-- source: self-learning-guide/07-ai-with-gemini/practice/hello_gemini.py:1-14 -->
```python
"""Your first call to Gemini. Run it from my-warroom: python hello_gemini.py"""

import os

from dotenv import load_dotenv
from google import genai

load_dotenv()  # reads GEMINI_API_KEY from the .env file in this folder
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
response = client.models.generate_content(
    model=os.environ.get("GEMINI_MODEL") or "gemini-3.5-flash-lite",
    contents="In one short sentence, what does a payment gateway do?",
)
print(response.text)
```

Run it:

```bash
python hello_gemini.py
```

## ✅ Check

After a second or two you get one sentence, something like:

```text
A payment gateway securely authorizes and processes online financial transactions between a customer and a merchant.
```

Your sentence will be a little different. Run it again: it changes again. An LLM's
answer isn't fixed, which is one more reason the **numbers** come from the engine.

When it works, delete `hello_gemini.py` (it was just a test; the real code comes next).

## 🔍 Line by line

- **Line 1** · Docstring.
- **Line 3** · `os`, to read environment variables.
- **Line 5** · `load_dotenv` reads the `.env` file (the same package Django's settings
  use, lesson 4.3).
- **Line 6** · Google's official Gemini package, `google-genai`, installed with the
  requirements in Part 4.
- **Line 8** · Load `.env` into the environment.
- **Line 9** · A client: the object that talks to Gemini, with your key.
  `os.environ["GEMINI_API_KEY"]` crashes with `KeyError` if the key isn't set, which is
  better than a confusing error later.
- **Lines 10–13** · Ask for content: which model, and the text (`contents`). If
  `GEMINI_MODEL` is empty, use `gemini-3.5-flash-lite`.
- **Line 14** · Print the answer's text.

## 🛠️ If it didn't work

| You see | Fix |
|---|---|
| `KeyError: 'GEMINI_API_KEY'` | The line in `.env` is missing or misspelt. Run the script from `my-warroom`, where `.env` is. |
| `400 ... API key not valid` | The key was copied wrong (a missing letter, an extra space). Copy it again. |
| `404 ... models/... is not found` | That model isn't available to your key. In AI Studio, see which models you can use and put one in `GEMINI_MODEL` in `.env`. |
| `429 ... RESOURCE_EXHAUSTED` | You hit the free tier's limit. Wait a minute (or until tomorrow for a daily limit). |
| `UnicodeEncodeError: 'charmap' codec can't encode character '₹'` | Windows' terminal couldn't print a symbol like ₹. Run `set PYTHONIOENCODING=utf-8` (Command Prompt) or `$env:PYTHONIOENCODING="utf-8"` (PowerShell), then try again. |

## ❓ Quiz

1. Where does the key live, and why not in the code?
2. What does `git check-ignore .env` prove?

---

**Next:** [7.3 · The AI tables](03-the-ai-tables.md)

<details><summary>Quiz answers</summary>

1. In `.env`, which Git ignores. Code is shared (GitHub); a key in code would be public.
2. That Git will never add `.env` to a commit.

</details>
