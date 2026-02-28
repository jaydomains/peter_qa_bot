from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class AskLLMError(RuntimeError):
    pass


def ask_openai_responses(*, api_key: str, model: str, system: str, user: str, timeout: int = 90) -> str:
    """Call OpenAI Responses API for text-only QA."""

    if not api_key:
        raise AskLLMError("OPENAI_API_KEY not set")

    body: dict[str, Any] = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user}],
            },
        ],
        # keep it deterministic-ish
        "temperature": float(os.getenv("PETER_QA_TEMPERATURE", "0.2")),
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        details = ""
        try:
            details = e.read().decode("utf-8", errors="replace")
        except Exception:
            details = ""
        raise AskLLMError(f"Ask request failed: HTTP {e.code} {e.reason} {details}".strip()) from e
    except Exception as e:
        raise AskLLMError(f"Ask request failed: {e}") from e

    data = json.loads(raw)

    # Extract first output_text
    for item in data.get("output", []) or []:
        for c in item.get("content", []) or []:
            if c.get("type") in ("output_text", "text") and "text" in c:
                return str(c.get("text"))

    # Fallback: some variants return top-level output_text
    out_text = data.get("output_text")
    if out_text:
        return str(out_text)

    raise AskLLMError(f"No text output found in response. Keys: {list(data.keys())}")
