"""Extract assistant text from DeepSeek / OpenAI-style chat responses."""

from __future__ import annotations

from typing import Any


def extract_assistant_text(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    choice = choices[0]
    message = choice.get("message") or {}
    content = (message.get("content") or "").strip()
    if content:
        return content

    for key in ("reasoning_content", "reasoning"):
        extra = message.get(key)
        if extra and str(extra).strip():
            return _plain_answer_from_reasoning(str(extra).strip())

    text = choice.get("text")
    if text and str(text).strip():
        return str(text).strip()
    return ""


def extract_gemini_text(data: dict[str, Any]) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    chunks: list[str] = []
    for part in parts:
        text = part.get("text")
        if text and str(text).strip():
            chunks.append(str(text).strip())
    return "\n".join(chunks)


def _plain_answer_from_reasoning(text: str) -> str:
    """If only reasoning was returned, use the last non-empty lines as the user-facing answer."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    # Prefer trailing lines that look like final answer bullets or sentences.
    tail = lines[-8:]
    bullet_lines = [line for line in tail if line.startswith(("-", "•", "*"))]
    if bullet_lines:
        headline = ""
        for line in reversed(tail):
            if line.startswith(("-", "•", "*")):
                break
            if len(line) > 40:
                headline = line
                break
    return tail[-1]


def parse_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract and parse the first valid JSON object from LLM response text."""
    import json
    import re

    cleaned = (text or "").strip()
    if not cleaned:
        return None

    # 1. Direct parse attempt
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 2. Extract from markdown code blocks (```json ... ``` or ``` ...)
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if code_block_match:
        try:
            data = json.loads(code_block_match.group(1).strip())
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # 3. Scan for outermost balanced curly brackets { ... }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace : last_brace + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return None

