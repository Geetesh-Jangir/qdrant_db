"""Macro / market-wide Google News query (same RSS filters as entity fetch)."""

from __future__ import annotations

from news_pipeline.config import Settings
from news_pipeline.sources.google_news import fetch_entity_items

MACRO_ENTITY_NAME = "Macro"


def macro_fetch_entity(settings: Settings) -> dict:
    return {
        "name": MACRO_ENTITY_NAME,
        "type": "macro",
        "query": settings.macro_news_query,
        "aliases": [],
        "negative_aliases": [],
        "keywords": [],
        "fund_count": 0,
        "total_percentage": 0.0,
        "industry": "",
    }


def fetch_macro_items(settings: Settings) -> list[dict]:
    if not settings.macro_news_enabled:
        return []
    return fetch_entity_items(macro_fetch_entity(settings), settings)


def is_macro_match(match: dict) -> bool:
    return match.get("type") == "macro" or match.get("name") == MACRO_ENTITY_NAME
