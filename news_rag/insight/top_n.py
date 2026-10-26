"""Parse 'top N' / 'top six' from natural-language questions."""

from __future__ import annotations

import re

_WORD_TO_INT: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def top_n_from_question(
    question: str,
    *,
    default: int = 3,
    item: str = "any",
) -> int:
    """item: 'sectors' | 'holdings' | 'any' — affects defaults when count omitted."""
    q = (question or "").strip()
    if not q:
        return default

    for pattern in (
        r"\btop\s+(\d+)\b",
        r"\b(\d+)\s+(?:largest|biggest|major)\s+",
        r"\b(?:first|any)\s+(\d+)\s+",
        r"\b(\d+)\s+(?:sectors?|holdings?|stocks?|shares?)\b",
    ):
        m = re.search(pattern, q, re.I)
        if m:
            return max(1, min(20, int(m.group(1))))

    m = re.search(r"\btop\s+([a-z]+)\s+(?:sectors?|holdings?|stocks?)\b", q, re.I)
    if m:
        word = m.group(1).lower()
        if word in _WORD_TO_INT:
            return max(1, min(20, _WORD_TO_INT[word]))

    if item == "sectors":
        if re.search(r"\btop\s+sector(?!s)\b", q, re.I):
            return 1
        if re.search(r"\btop\s+sectors\b", q, re.I):
            return default
        if re.search(r"\bsectors?\b", q, re.I) and re.search(r"\btop\b", q, re.I):
            return default

    if item == "holdings":
        if re.search(r"\btop\s+holdings?\b|\btop\s+stocks?\b", q, re.I):
            return default

    if re.search(r"\btop\b", q, re.I):
        return default
    return default
