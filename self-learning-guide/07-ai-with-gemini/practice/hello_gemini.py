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
