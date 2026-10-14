"""Number grounding and display polish for composed answers."""

from __future__ import annotations

import re

_MEDIA_OUTLETS = (
    "Economic Times",
    "Financial Express",
    "Business Standard",
    "BusinessLine",
    "The Hindu BusinessLine",
    "Moneycontrol",
    "Livemint",
    "Mint",
    "Reuters",
    "NDTV Profit",
    "CNBC-TV18",
    "CNBC",
    "Bloomberg",
    "PTI",
    "ANI",
    "Business Standard",
)
_OUTLET_CITE_RE = re.compile(
    r"\(\s*(?:"
    + "|".join(re.escape(o) for o in _MEDIA_OUTLETS)
    + r")\s*,\s*[^)]+\)",
    re.I,
)
_OUTLET_BARE_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(o) for o in _MEDIA_OUTLETS)
    + r")\b(?:\s*,\s*\d{1,2}\s+\w{3,9}(?:\s+\d{4})?)?",
    re.I,
)
_ACCORDING_RE = re.compile(r"\baccording to\s+(?:the\s+)?(?:reports?|news|media)\b[,.]?\s*", re.I)

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


def strip_media_attribution(text: str) -> str:
    """Remove newspaper names and inline source parentheses; sources live in the API `sources` list."""
    cleaned = text or ""
    cleaned = _OUTLET_CITE_RE.sub("", cleaned)
    cleaned = _OUTLET_BARE_RE.sub("", cleaned)
    cleaned = _ACCORDING_RE.sub("", cleaned)
    cleaned = re.sub(r"\(\s*\d{1,2}\s+\w{3,9}(?:\s+\d{4})?\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+\(\s*;\s*", " (", cleaned)
    return tidy_prose(cleaned)


def tidy_prose(text: str) -> str:
    text = re.sub(r"(?<!\d)\s*per\s*cent\b", "", text or "", flags=re.I)
    text = re.sub(r"\*{2,}\s*\*{2,}", "", text)
    text = re.sub(r"\broughly\s+\*\*\s*\*\*", "", text)
    text = re.sub(r"\bworth\s+roughly\s+\*\*\s*pp\*\*", "", text, flags=re.I)
    text = re.sub(r"\(\s*approx\.?\s*\)", "", text, flags=re.I)
    text = re.sub(r"\bapprox\.?\s*pp\b", "", text, flags=re.I)
    text = re.sub(r"\s+pp\b(?!\w)", "", text, flags=re.I)
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
    headline = strip_media_attribution(strip_ungrounded_numbers(headline, allowed))
    narrative = strip_media_attribution(strip_ungrounded_numbers(narrative, allowed))
    bullets = [
        strip_media_attribution(strip_ungrounded_numbers(b, allowed)) for b in bullets if b
    ]
    closing = strip_media_attribution(strip_ungrounded_numbers(closing, allowed))
    return headline, narrative, [b for b in bullets if b.strip()], closing
