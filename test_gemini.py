"""Standalone Gemini diagnostic. Run:  python3 test_gemini.py

It uses the SAME call your bot makes, but prints the full error/response
so we can see exactly why answers come back empty.
"""
import os
import asyncio
import traceback

from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY")
print("GEMINI_API_KEY present:", bool(API_KEY),
      "(length:", len(API_KEY) if API_KEY else 0, ")")

if not API_KEY:
    raise SystemExit("❌ GEMINI_API_KEY is not set in this environment.")

client = genai.Client(api_key=API_KEY)


async def main():
    try:
        resp = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents="What is 1+1?",
            config=types.GenerateContentConfig(
                system_instruction="You are a helpful study assistant.",
                max_output_tokens=1024,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
    except Exception:
        print("❌ EXCEPTION during the API call:")
        traceback.print_exc()
        return

    print("\n--- RAW RESULT ---")
    print("response.text:", repr(resp.text))
    if resp.candidates:
        c = resp.candidates[0]
        print("finish_reason:", c.finish_reason)
        print("content:", c.content)
    print("prompt_feedback:", resp.prompt_feedback)
    print("usage:", resp.usage_metadata)


asyncio.run(main())
