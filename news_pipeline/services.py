"""Process-wide settings and Qdrant client."""

from __future__ import annotations

import os
from functools import lru_cache

from news_pipeline.config import Settings
from news_pipeline.storage.qdrant_store import NewsStore

_store: NewsStore | None = None


def _cap_daily_cron_settings(settings: Settings) -> Settings:
    """deploy/lightsail/run-daily-pipeline.sh sets NEWS_PIPELINE_DAILY=1."""
    if os.environ.get("NEWS_PIPELINE_DAILY") != "1":
        return settings
    updates: dict[str, int | float] = {}
    if settings.holdings_limit > 250:
        updates["holdings_limit"] = 250
    if settings.sectors_limit > 30:
        updates["sectors_limit"] = 30
    if settings.fetch_workers > 1:
        updates["fetch_workers"] = 1
    if settings.scrape_workers > 2:
        updates["scrape_workers"] = 2
    if settings.scrape_domain_gap_sec < 1.5:
        updates["scrape_domain_gap_sec"] = 1.5
    if not updates:
        return settings
    return settings.model_copy(update=updates)


@lru_cache
def get_settings() -> Settings:
    return _cap_daily_cron_settings(Settings())


def get_store() -> NewsStore:
    global _store
    if _store is None:
        _store = NewsStore(get_settings())
    return _store
