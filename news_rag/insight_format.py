"""Parse and clean structured insight text (bullets + summary)."""

from __future__ import annotations

import re

_LINE_NO = re.compile(r"^Line\s*\d+\s*:\s*", re.I)
_WORD_COUNT = re.compile(r"\s*~?\d+\s*\.?\s*$")
_QUOTED_BULLET = re.compile(r'^["\'](.+?)["\']\s*$')


def clean_insight_line(line: str) -> str:
    text = line.strip()
    text = _LINE_NO.sub("", text)
    text = re.sub(r"^[-*•]\s+", "", text)
    m = _QUOTED_BULLET.match(text)
    if m:
        text = m.group(1)
    text = _WORD_COUNT.sub("", text).strip()
    return text


def parse_structured_insight(raw: str) -> tuple[list[str], str]:
    """Split model output into bullets and summary paragraph."""
    text = (raw or "").strip()
    if not text:
        return [], ""

    bullets: list[str] = []
    summary = ""

    if re.search(r"(?mi)^BULLETS:\s*$", text) or re.search(r"(?mi)^SUMMARY:\s*$", text):
        parts = re.split(r"(?mi)^SUMMARY:\s*", text, maxsplit=1)
        head = parts[0]
        if len(parts) > 1:
            summary = parts[1].strip()
        head = re.sub(r"(?mi)^BULLETS:\s*", "", head).strip()
        for line in head.splitlines():
            cleaned = clean_insight_line(line)
            if cleaned:
                bullets.append(cleaned)
        summary = " ".join(summary.split())
        return bullets, summary

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullet_lines: list[str] = []
    other_lines: list[str] = []
    for line in lines:
        if re.match(r"^[-*•]\s+", line) or _LINE_NO.match(line):
            cleaned = clean_insight_line(line)
            if cleaned:
                bullet_lines.append(cleaned)
        else:
            other_lines.append(clean_insight_line(line))

    if bullet_lines:
        bullets = bullet_lines
        summary = " ".join(other_lines)
    else:
        summary = " ".join(other_lines) if other_lines else text

    return bullets, summary.strip()


def clamp_bullets(bullets: list[str], *, max_count: int, max_chars: int) -> list[str]:
    trimmed: list[str] = []
    for item in bullets:
        text = " ".join(str(item).split())
        if len(text) > max_chars:
            text = text[: max_chars - 3].rstrip() + "..."
        if text:
            trimmed.append(text)
        if len(trimmed) >= max_count:
            break
    return trimmed


def clamp_summary(text: str, *, max_words: int) -> str:
    words = " ".join((text or "").split()).split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(".,;") + "..."


def format_insight_display(bullets: list[str], summary: str) -> str:
    parts: list[str] = []
    for item in bullets:
        parts.append(f"- {item}")
    if summary:
        parts.append("")
        parts.append(summary)
    return "\n".join(parts)
