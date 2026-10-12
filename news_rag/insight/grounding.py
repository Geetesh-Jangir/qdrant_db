"""Number grounding for composed answers (extracted from ask_composer patterns)."""

from __future__ import annotations

import re

_PCT_OR_BPS_RE = re.compile(
    r"(?<![\w.])([+-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:%|bps|bp)(?![\w])",
    re.I,
)
_MONEY_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?)",
    re.I,
)
_DECIMAL_RE = re.compile(r"(?<![\w.])([+-]?\d{1,3}(?:,\d{3})*\.\d+)(?![\w.])")
_ANY_NUMBER_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def numeric_core(raw: str) -> str:
    s = (raw or "").replace(",", "").strip().lstrip("+")
    if not s:
        return ""
    if re.fullmatch(r"-?\d+\.\d+", s):
        s = s.rstrip("0").rstrip(".")
    return s


def number_is_grounded(core: str, allowed: set[str]) -> bool:
    if not core:
        return False
    unsigned = core[1:] if core.startswith("-") else core
    return core in allowed or unsigned in allowed or f"-{unsigned}" in allowed


def cores_in_text(blob: str) -> set[str]:
    cores: set[str] = set()
    for match in _ANY_NUMBER_RE.finditer(blob or ""):
        core = numeric_core(match.group(0))
        if core:
            cores.add(core)
    return cores


def tidy_prose(text: str) -> str:
    text = re.sub(r"(?<!\d)\s*per\s*cent\b", "", text or "", flags=re.I)
    text = re.sub(r"\*{2,}\s*\*{2,}", "", text)
    text = re.sub(r"\bbetween\s+and\b", "", text, flags=re.I)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def strip_ungrounded_numbers(text: str, allowed: set[str]) -> str:
    def drop_pct(match: re.Match[str]) -> str:
        core = numeric_core(match.group(1))
        return match.group(0) if number_is_grounded(core, allowed) else ""

    def drop_money(match: re.Match[str]) -> str:
        core = numeric_core(match.group(1))
        return match.group(0) if number_is_grounded(core, allowed) else ""

    def drop_decimal(match: re.Match[str]) -> str:
        core = numeric_core(match.group(1))
        return match.group(0) if number_is_grounded(core, allowed) else ""

    cleaned = _PCT_OR_BPS_RE.sub(drop_pct, text or "")
    cleaned = _MONEY_RE.sub(drop_money, cleaned)
    cleaned = _DECIMAL_RE.sub(drop_decimal, cleaned)
    return tidy_prose(cleaned)


def finalize_text_fields(
    headline: str,
    narrative: str,
    bullets: list[str],
    closing: str,
    evidence_text: str,
) -> tuple[str, str, list[str], str]:
    allowed = cores_in_text(evidence_text)
    headline = strip_ungrounded_numbers(headline, allowed)
    narrative = strip_ungrounded_numbers(narrative, allowed)
    bullets = [strip_ungrounded_numbers(b, allowed) for b in bullets if b]
    closing = strip_ungrounded_numbers(closing, allowed)
    return headline, narrative, [b for b in bullets if b.strip()], closing
