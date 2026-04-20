import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


MODEL = "gpt-5.3-codex" # gpt-5.4, gpt-5.4-mini, gpt-5.2, gpt-5.3-codex
REASONING_EFFORT = "high" # none, low, medium, high, xhigh
PROMPT = "Reply with exactly: ok1"
OPENAI_BASE_URL = "https://api.openai.com/v1"
ROOT_DIR = Path(__file__).resolve().parents[1]


def load_config() -> str:
    load_dotenv(ROOT_DIR / ".env")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set in the root .env file.")

    return api_key


def main() -> None:
    api_key = load_config()
    client = OpenAI(api_key=api_key, base_url=OPENAI_BASE_URL)

    request = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}],
    }
    if REASONING_EFFORT:
        request["reasoning_effort"] = REASONING_EFFORT

    try:
        response = client.chat.completions.create(**request)
    except Exception as exc:
        raise SystemExit(f"Direct OpenAI request failed: {exc}") from exc

    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
