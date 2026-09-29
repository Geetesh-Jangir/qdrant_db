"""Macro / market-wide Google News query (same RSS filters as entity fetch)."""

from __future__ import annotations

from news_pipeline.config import HIGH_IMPACT_MACRO_KEYWORDS, MACRO_QUERY_CLUSTERS, Settings
from news_pipeline.sources.google_news import fetch_entity_items

MACRO_ENTITY_NAME = "Macro"


def macro_fetch_entities(settings: Settings) -> list[dict]:
    entities = []
    # Primary configured query
    if (settings.macro_news_query or "").strip():
        entities.append(
            {
                "name": MACRO_ENTITY_NAME,
                "type": "macro",
                "query": settings.macro_news_query,
                "aliases": list(HIGH_IMPACT_MACRO_KEYWORDS),
                "negative_aliases": [],
                "keywords": list(HIGH_IMPACT_MACRO_KEYWORDS),
                "fund_count": 0,
                "total_percentage": 0.0,
                "industry": "Macroeconomics",
            }
        )
    # High-impact macro clusters (Commodities, Currency, Rates, Trade)
    for cluster_query in MACRO_QUERY_CLUSTERS:
        entities.append(
            {
                "name": MACRO_ENTITY_NAME,
                "type": "macro",
                "query": cluster_query,
                "aliases": list(HIGH_IMPACT_MACRO_KEYWORDS),
                "negative_aliases": [],
                "keywords": list(HIGH_IMPACT_MACRO_KEYWORDS),
                "fund_count": 0,
                "total_percentage": 0.0,
                "industry": "Macroeconomics",
            }
        )
    return entities


def fetch_macro_items(settings: Settings) -> list[dict]:
    if not settings.macro_news_enabled:
        return []
    items: list[dict] = []
    seen_urls: set[str] = set()
    for ent in macro_fetch_entities(settings):
        for item in fetch_entity_items(ent, settings):
            url = str(item.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            items.append(item)
    return items


def is_macro_match(match: dict) -> bool:
    name = str(match.get("name") or "")
    return match.get("type") == "macro" or name == MACRO_ENTITY_NAME or name.startswith("Macro")

