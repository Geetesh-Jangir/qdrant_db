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
        parts = [headline] if headline else []
        parts.extend(bullet_lines)
        return "\n".join(parts)
    return tail[-1]
