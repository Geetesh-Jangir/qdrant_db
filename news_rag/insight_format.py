"""Parse and clean structured insight text (bullets + summary)."""

from __future__ import annotations

import re

_LINE_NO = re.compile(r"^Line\s*\d+\s*:\s*", re.I)
_BULLET_LABEL = re.compile(r"^(?:Bullet|Point)\s*\d+\s*(?:\([^)]*\))?\s*:\s*", re.I)
_WORD_COUNT = re.compile(r"\s*~?\d+\s*\.?\s*$")
_QUOTED_BULLET = re.compile(r'^["\'](.+?)["\']\s*$')


def clean_insight_line(line: str) -> str:
    text = line.strip()
    text = _LINE_NO.sub("", text)
    text = re.sub(r"^[-*•]\s+", "", text)
    text = _BULLET_LABEL.sub("", text)
    m = _QUOTED_BULLET.match(text)
    if m:
        text = m.group(1)

    # Strip outer square brackets if the entire line was enclosed e.g. [Live NAV Trajectory: ...]
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()

    # Strip any lingering prompt template labels or instruction phrases at the beginning of the bullet
    text = re.sub(
        r"^(?:\[?\s*(?:Live NAV Trajectory|Sector Breakdown|Sector Allocations|Key Holdings News|Growth Initiatives|Portfolio Transmission|Portfolio Impact|Direct Impact|Transmission to|Portfolio Cushion|Spot Price|30-Day Context|Investor & Economic|Core Catalyst|Direct answer addressing Question \d+|Explain the fund's latest value story|Explain the industry climate|Tell the story of [^:]*|Connect the big picture[^:]*|Fund NAV & Macro Backdrop|Primary Portfolio Mover & Catalysts|Major Deals & Corporate Actions|Sector Champions[^:]*|Investor Takeaway & Portfolio Resilience)[^:]*:\s*\]?)\s*",
        "",
        text,
        flags=re.I,
    )

    text = _WORD_COUNT.sub("", text).strip()
    text = re.sub(r"\s*\[\s*\d+-\d+\s+complete\s+sentences[^\]]*\]", "", text, flags=re.I).strip()
    text = re.sub(r"\s*\(\s*~?\d+\s*words?\s*\)\s*$", "", text, flags=re.I).strip()
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


def trim_chars_at_word(text: str, max_chars: int) -> str:
    text = " ".join(str(text).split())
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    cut = cut.rstrip(".,;-")
    if cut.count("**") % 2 != 0:
        cut += "**"
    return cut


def clamp_bullets(bullets: list[str], *, max_count: int, max_chars: int) -> list[str]:
    trimmed: list[str] = []
    for item in bullets:
        text = trim_chars_at_word(item, max_chars)
        if text:
            trimmed.append(text)
        if max_count > 0 and len(trimmed) >= max_count:
            break
    return trimmed


def clamp_summary(text: str, *, max_words: int) -> str:
    words = " ".join((text or "").split()).split()
    if max_words <= 0 or len(words) <= max_words:
        return " ".join(words)
    cut = " ".join(words[:max_words]).rstrip(".,;")
    if cut.count("**") % 2 != 0:
        cut += "**"
    return cut


def format_insight_display(bullets: list[str], summary: str) -> str:
    parts: list[str] = []
    for item in bullets:
        parts.append(f"- {item}")
    if summary:
        parts.append("")
        parts.append(summary)
    return "\n".join(parts)


def format_insight_sections_display(
    sections: list[dict],
    summary: str = "",
) -> str:
    parts: list[str] = []
    for sec in sections:
        heading = (sec.get("heading") or "").strip()
        if heading:
            parts.append(f"## {heading}")
        for item in sec.get("bullets") or []:
            if item:
                parts.append(f"- {item}")
        parts.append("")
    if summary:
        parts.append(summary.strip())
    return "\n".join(parts).strip()
