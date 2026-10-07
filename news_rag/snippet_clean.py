"""Strip scrape boilerplate before synthesis (outlets, datelines, truncation)."""

from __future__ import annotations

import re

_OUTLET_PREFIX = re.compile(
    r"^(?:Livemint|Business\s*Standard|Mint|PTI|Reuters|ANI|Bloomberg|"
    r"Economic\s*Times|Financial\s*Express|Moneycontrol|NDTV|CNBC)[^.\n]{0,80}",
    re.I,
)
_UPDATED_LINE = re.compile(
    r"(?:Updated?\s*\d{1,2}\s+\w{3,9}\s+\d{4}[^.]*(?:IST|GMT|UTC)?|"
    r"\d{1,2}\s+\w{3,9}\s+\d{4},\s*\d{1,2}:\d{2}\s*(?:AM|PM)\s*IST|"
    r"\d{1,2}\s+\w{3,9}\s+\d{4}\s*/\s*\d{1,2}:\d{2}\s*IST)",
    re.I,
)
_AGENCY = re.compile(
    r"\(\s*with inputs from PTI\s*\)|\bPTI\s+repo\b|\binputs from PTI\b",
    re.I,
)
_DOMAIN = re.compile(
    r"\b(?:livemint\.com|business-standard\.com|economictimes\.com|moneycontrol\.com)\b",
    re.I,
)
_ELLIPSIS = re.compile(r"\.{3,}\s*$")
_MIN_READ = re.compile(
    r"\b\d+\s*(?:Min|Mins|min|mins)\s+Read\b",
    re.I,
)
_AD_BANNER = re.compile(
    r"\b\d+\s*Up\s+to\s*₹[\d,.]+\s*(?:lakhs?|crore)?[^|]*\|\s*Starts\s+at\s*[\d.]+%",
    re.I,
)
_AD_LOAN_FRAG = re.compile(
    r"(?:Up\s+to\s*₹[\d,.]+\s*(?:lakhs?|crore)?\s*\|\s*Starts\s+at\s*[\d.]+%)",
    re.I,
)
# Article datelines (not economic calendar months embedded in prose)
_WEEKDAY_DATE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*"
    r"(?:\d{1,2}\s+\w{3,9}|\w{3,9}\s+\d{1,2})(?:,?\s*\d{4})?",
    re.I,
)
_EARLY_TRADING_DATE = re.compile(
    r"\bon\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*"
    r"\d{1,2}\s+\w{3,9}(?:,?\s*\d{4})?",
    re.I,
)
_PUBLISH_TIMESTAMP = re.compile(
    r"\b\w{3,9}\s+\d{1,2},?\s+\d{4}\s*/\s*\d{1,2}:\d{2}\s*IST\b",
    re.I,
)
_INLINE_IST_TIME = re.compile(
    r"\b\d{1,2}\s+\w{3,9}\s+\d{4},?\s*\d{1,2}:\d{2}\s*(?:AM|PM)?\s*IST\b",
    re.I,
)
_BROKEN_END = re.compile(
    r"\b(?:on|the|a|an|to|of|for|and|or|in|at|as|by|with|from|that|which|"
    r"their|its|india'?s?)\s*\.\s*$",
    re.I,
)


def article_body_for_llm(article: dict, limit: int = 1000) -> str:
    """Cleaned article text for an LLM. Prefer the scraped body over the headline."""
    raw = str(
        article.get("scraped_text")
        or article.get("body")
        or article.get("snippet")
        or ""
    )
    text = clean_scraped_snippet(raw)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut


def clean_scraped_snippet(text: str) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ""
    cleaned = _OUTLET_PREFIX.sub("", cleaned).strip()
    cleaned = _MIN_READ.sub(" ", cleaned)
    cleaned = _AD_BANNER.sub(" ", cleaned)
    cleaned = _AD_LOAN_FRAG.sub(" ", cleaned)
    cleaned = _UPDATED_LINE.sub(" ", cleaned)
    cleaned = _PUBLISH_TIMESTAMP.sub(" ", cleaned)
    cleaned = _INLINE_IST_TIME.sub(" ", cleaned)
    cleaned = _WEEKDAY_DATE.sub(" ", cleaned)
    cleaned = _EARLY_TRADING_DATE.sub(" during early trading", cleaned)
    cleaned = _AGENCY.sub(" ", cleaned)
    cleaned = _DOMAIN.sub(" ", cleaned)
    cleaned = " ".join(cleaned.split())
    cleaned = _ELLIPSIS.sub(".", cleaned).strip()
    return cleaned


def is_broken_fragment(text: str) -> bool:
    """True if text looks like a truncated scrape, not a full thought."""
    t = (text or "").strip()
    if not t:
        return True
    if _BROKEN_END.search(t):
        return True
    if t.endswith("...") or t.endswith("…"):
        return True
    # Very short tail after last punctuation
    if len(t) < 55 and not re.search(r"[.!?]$", t):
        return True
    words = t.split()
    if len(words) >= 3 and words[-1].lower() in {
        "the",
        "a",
        "an",
        "on",
        "to",
        "of",
        "for",
        "and",
        "in",
        "at",
        "as",
        "by",
        "with",
        "from",
        "that",
        "which",
    }:
        return True
    return False


def sentence_has_scrape_artifacts(sentence: str) -> bool:
    s = sentence or ""
    if _MIN_READ.search(s):
        return True
    if _AD_BANNER.search(s) or _AD_LOAN_FRAG.search(s):
        return True
    if _UPDATED_LINE.search(s) or _PUBLISH_TIMESTAMP.search(s) or _INLINE_IST_TIME.search(s):
        return True
    if _WEEKDAY_DATE.search(s) and re.search(r"\b\d{4}\b", s):
        return True
    return False


def sanitize_analyst_bullet(text: str) -> str:
    """Final pass on LLM/deterministic bullets: no dates, ads, or paste."""
    cleaned = clean_scraped_snippet(text or "")
    cleaned = re.sub(r"\.{2,}\s*$", ".", cleaned.strip())
    if not cleaned or is_broken_fragment(cleaned):
        return ""
    if looks_like_raw_scrape(cleaned):
        return ""
    return cleaned


def looks_like_raw_scrape(text: str) -> bool:
    """True if text is likely unprocessed Qdrant scrape, not analyst prose."""
    if not text or len(text) < 40:
        return False
    lower = text.lower()
    if _ELLIPSIS.search(text):
        return True
    if _UPDATED_LINE.search(text):
        return True
    if _MIN_READ.search(text):
        return True
    if _AD_BANNER.search(text) or _AD_LOAN_FRAG.search(text):
        return True
    if _PUBLISH_TIMESTAMP.search(text) or _INLINE_IST_TIME.search(text):
        return True
    if is_broken_fragment(text):
        return True
    if "with inputs from pti" in lower or "pti repo" in lower:
        return True
    if re.search(r"livemint\s*\(", lower):
        return True
    if re.search(r"\b\d+\s*min(?:s)?\s+read\b", lower):
        return True
    if re.search(r"starts at \d+\.\d+%", lower) and "up to" in lower:
        return True
    if lower.count("...") >= 1 and len(text) > 120:
        return True
    # Long bullet that still opens like a headline dateline
    if re.match(
        r"^(?:shares of|the domestic|during early trading|\d+\s+up to)",
        lower,
    ) and not text.strip().startswith("**"):
        return True
    return False
