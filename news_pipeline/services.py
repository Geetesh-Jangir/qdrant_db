"""Process-wide settings and Qdrant client."""

from __future__ import annotations

from functools import lru_cache

from news_pipeline.config import Settings
from news_pipeline.storage.qdrant_store import NewsStore

_store: NewsStore | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_store() -> NewsStore:
    global _store
    if _store is None:
        _store = NewsStore(get_settings())
    return _store
