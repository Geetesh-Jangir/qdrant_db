"""In-memory cache of entity labels from Qdrant."""

from __future__ import annotations

import time

from news_rag.config import get_settings
from news_rag.qdrant_reader import QdrantReader

_cache: set[str] = set()
_loaded_at: float = 0.0


def corpus_entity_names(force: bool = False) -> set[str]:
    global _cache, _loaded_at
    settings = get_settings()
    ttl = max(60.0, settings.entity_cache_hours * 3600)
    if not force and _cache and (time.time() - _loaded_at) < ttl:
        return _cache
    reader = QdrantReader()
    _cache = reader.scroll_entity_names()
    _loaded_at = time.time()
    return _cache
