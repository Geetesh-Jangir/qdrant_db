"""Event-focus helpers for fund-level and discovery impact answers."""

from __future__ import annotations

import re
from typing import Any

# Sectors in a flexi/large-cap fund most sensitive to crude oil moves (portfolio lens).
_CRUDE_SENSITIVE_SECTOR_KEYS = frozenset(
    {
        "petroleum products",
        "automobiles",
        "auto components",
        "transport services",
        "airlines",
        "chemicals & petrochemicals",
    }
)

_EVENT_TEXT_ALIASES: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (re.compile(r"\bcrude\b|\boil price|\bpetroleum\b", re.I), ("crude", "oil", "petroleum")),
    (re.compile(r"\brbi\b|\brepo\s*rate|\brate\s*hike|\bmonetary\s*policy", re.I), ("rbi", "repo", "rate")),
)


def event_search_tokens(question: str, event_focus: str = "") -> list[str]:
    blob = f"{question} {event_focus}".strip()
    tokens: list[str] = []
    for pat, words in _EVENT_TEXT_ALIASES:
        if pat.search(blob):
            tokens.extend(words)
    return tokens


def article_matches_event(article: dict[str, Any], tokens: list[str]) -> bool:
    if not tokens:
        return True
    hay = " ".join(
        [
            str(article.get("title") or ""),
            str(article.get("snippet") or ""),
            " ".join(str(e) for e in (article.get("entity_names") or [])),
            " ".join(str(i) for i in (article.get("industry_names") or [])),
        ]
    ).lower()
    return any(t in hay for t in tokens)


def filter_articles_for_event(
    articles: list[dict[str, Any]],
    question: str,
    event_focus: str = "",
) -> list[dict[str, Any]]:
    tokens = event_search_tokens(question, event_focus)
    if not tokens:
        return articles
    matched = [a for a in articles if article_matches_event(a, tokens)]
    return matched if matched else articles[:3]


def is_crude_oil_event(tokens: list[str]) -> bool:
    return any(t in ("crude", "oil", "petroleum") for t in tokens)


def crude_oil_price_rising(question: str, event_focus: str = "") -> bool:
    blob = f"{question} {event_focus}".lower()
    if any(w in blob for w in ("surge", "spike", "rise", "rally", "higher", "jump", "soar", "increase")):
        return True
    if any(w in blob for w in ("fall", "drop", "decline", "lower", "slide", "crash")):
        return False
    return True  # default: user asked about shock; treat as higher crude unless stated


def crude_sector_channel_note(sector: str, *, oil_rising: bool) -> str:
    key = str(sector).strip().lower()
    if key == "automobiles" or key == "auto components":
        if oil_rising:
            return "Higher fuel and input costs can pressure margins and demand for autos."
        return "Cheaper oil can ease cost pressure and support auto sentiment."
    if key == "petroleum products":
        if oil_rising:
            return "Small direct weight; refiner/marketing names can see mixed margin effects when crude moves."
        return "Lower crude can help marketing margins; upstream names may see less support."
    if key == "transport services" or key == "airlines":
        if oil_rising:
            return "Fuel is a major cost line — transport names are sensitive to oil spikes."
        return "Lower fuel costs tend to help transport profitability."
    if key == "chemicals & petrochemicals":
        if oil_rising:
            return "Feedstock costs can squeeze petrochemical margins."
        return "Cheaper feedstock can support chemical margins."
    if oil_rising:
        return "Energy-linked sector — earnings can move with crude."
    return "Sector can react when oil prices shift."


_RBI_SENSITIVE_SECTOR_KEYS = frozenset(
    {
        "banks",
        "finance",
        "capital markets",
    }
)


def is_rbi_rate_event(tokens: list[str]) -> bool:
    return any(t in ("rbi", "repo", "rate") for t in tokens)


def rbi_rate_tightening(question: str, event_focus: str = "") -> bool:
    blob = f"{question} {event_focus}".lower()
    if any(w in blob for w in ("hike", "increase", "tighten", "tightening", "higher", "raise", "raised")):
        return True
    if any(w in blob for w in ("cut", "lower", "ease", "easing", "reduction", "reduced")):
        return False
    if "change" in blob or "impact" in blob:
        return True
    return True


def rbi_sector_channel_note(sector: str, *, tightening: bool) -> str:
    key = str(sector).strip().lower()
    if key == "banks":
        if tightening:
            return "Higher rates can lift NIMs initially but may slow loan growth and pressure valuations."
        return "Rate cuts can support credit demand and bank sentiment, with mixed NIM effects."
    if key == "finance":
        if tightening:
            return "NBFCs and lenders often face higher funding costs when policy rates move up."
        return "Easier policy can lower funding costs for finance names."
    if key == "capital markets":
        if tightening:
            return "Risk-off and higher discount rates can weigh on brokers and asset managers."
        return "Easier liquidity can support capital-markets earnings."
    if tightening:
        return "Financials-heavy slices tend to move with rate and liquidity expectations."
    return "Financials-heavy slices tend to move with rate-cut and liquidity headlines."


def rbi_sensitive_sectors(detail: dict[str, Any], limit: int = 6) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    raw = detail.get("sectors") or {}
    if isinstance(raw, dict):
        for sec, pct in raw.items():
            if str(sec).strip().lower() in _RBI_SENSITIVE_SECTOR_KEYS:
                try:
                    rows.append((str(sec), float(pct)))
                except (TypeError, ValueError):
                    pass
    rows.sort(key=lambda x: -x[1])
    return rows[:limit]


def crude_sensitive_sectors(detail: dict[str, Any], limit: int = 6) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    raw = detail.get("sectors") or {}
    if isinstance(raw, dict):
        for sec, pct in raw.items():
            if str(sec).strip().lower() in _CRUDE_SENSITIVE_SECTOR_KEYS:
                try:
                    rows.append((str(sec), float(pct)))
                except (TypeError, ValueError):
                    pass
    rows.sort(key=lambda x: -x[1])
    return rows[:limit]
