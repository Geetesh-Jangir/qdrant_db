"""Rule-based time and hint parsing from user questions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

TIME_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"\blast\s+(\d+)\s+days?\b", re.I), 0),
    (re.compile(r"\bpast\s+(\d+)\s+days?\b", re.I), 0),
    (re.compile(r"\blast\s+one\s+week\b|\blast\s+1\s+week\b|\bpast\s+week\b|\blast\s+week\b", re.I), 7),
    (re.compile(r"\blast\s+(\d+)\s+weeks?\b", re.I), 0),
    (re.compile(r"\blast\s+month\b|\bpast\s+month\b|\blast\s+one\s+month\b", re.I), 30),
    (re.compile(r"\blast\s+(\d+)\s+months?\b", re.I), 0),
    (re.compile(r"\byesterday\b", re.I), 1),
    (re.compile(r"\btoday\b", re.I), 1),
]

STOPWORDS = {
    "why",
    "what",
    "how",
    "when",
    "where",
    "who",
    "the",
    "is",
    "are",
    "was",
    "were",
    "for",
    "in",
    "on",
    "at",
    "to",
    "a",
    "an",
    "and",
    "or",
    "of",
    "last",
    "past",
    "one",
    "week",
    "weeks",
    "day",
    "days",
    "month",
    "months",
    "news",
    "about",
    "stock",
    "shares",
    "share",
    "price",
    "underperforming",
    "performing",
    "performance",
    "market",
    "india",
    "indian",
    "whats",
    "what's",
    "happening",
    "happened",
    "sector",
    "industry",
    "going",
    "with",
    "tell",
    "me",
    "give",
    "update",
    "updates",
    "latest",
}

# Map phrases in the question to corpus entity_names (same labels as the ingest universe).
TOPIC_ENTITY_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bbanking\b|\bbank\s+sector\b|\bbanks\b", re.I), "Banks"),
    (re.compile(r"\bit\s+sector\b|\bsoftware\b|\bit\s+services\b", re.I), "It - Software"),
    (re.compile(r"\bpharma\b|\bbiotech\b|\bpharmaceutical", re.I), "Pharmaceuticals & Biotechnology"),
    (re.compile(r"\bretail\b|\bretailing\b", re.I), "Retailing"),
    (re.compile(r"\bauto\b|\bautomobile\b|\bcarmaker\b", re.I), "Automobiles"),
    (re.compile(r"\bcapital\s+market\b|\bstock\s+market\b|\bsebi\b", re.I), "Capital Markets"),
    (re.compile(r"\bnbfc\b|\bfinance\s+sector\b", re.I), "Finance"),
    (re.compile(r"\bpower\b|\belectricity\b|\benergy\s+sector\b", re.I), "Power"),
)


@dataclass
class ParsedQuery:
    question: str
    published_from: str
    published_to: str
    window_label: str
    stock_hint: str
    entity_resolved: list[str]
    entity_match_note: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_date_field(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    if len(text) == 10:
        text = text + "T00:00:00Z"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_time_window(
    question: str,
    *,
    date_from: str | None,
    date_to: str | None,
    default_days: int,
) -> tuple[str, str, str]:
    now = utc_now()
    start = parse_date_field(date_from)
    end = parse_date_field(date_to)
    if start or end:
        if not start:
            start = now - timedelta(days=default_days)
        if not end:
            end = now
        label = f"{start.date().isoformat()} to {end.date().isoformat()}"
        return to_iso(start), to_iso(end), label

    days = default_days
    for pattern, fixed_days in TIME_PATTERNS:
        match = pattern.search(question)
        if not match:
            continue
        if fixed_days > 0:
            days = fixed_days
            break
        groups = match.groups()
        if groups and groups[0].isdigit():
            n = int(groups[0])
            if "week" in match.group(0).lower():
                days = n * 7
            elif "month" in match.group(0).lower():
                days = n * 30
            else:
                days = n
            break

    start = now - timedelta(days=days)
    label = f"last {days} days"
    return to_iso(start), to_iso(now), label


def extract_stock_hint(question: str, explicit: str | None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    for pattern, entity_label in TOPIC_ENTITY_HINTS:
        if pattern.search(question):
            return entity_label
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9&.\-]{1,}", question)
    for token in tokens:
        lower = token.lower()
        if lower in STOPWORDS or len(lower) < 2:
            continue
        return token
    return ""


def resolve_entities(hint: str, corpus_names: set[str]) -> tuple[list[str], str]:
    if not hint:
        return [], "no_stock_hint"
    hint_lower = hint.lower()
    matches = []
    for name in sorted(corpus_names):
        if hint_lower in name.lower():
            matches.append(name)
    if matches:
        return matches, "matched"
    token = hint_lower
    for name in sorted(corpus_names):
        parts = name.lower().split()
        if any(token in part or part.startswith(token) for part in parts if len(part) >= 3):
            matches.append(name)
    if matches:
        return matches[:5], "fuzzy_matched"
    return [], "not_in_corpus"
