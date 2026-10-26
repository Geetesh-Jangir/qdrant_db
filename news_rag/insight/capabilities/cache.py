"""TTL cache for capability results.

Keyed by (capability_name, entity_key, module) — not user-specific.
Thread-safe via a threading Lock.
"""

from __future__ import annotations

import threading
import time
from typing import Any


class _Entry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: int) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl


class CapabilityCache:
    """Simple in-process TTL cache. Not meant for persistence."""

    def __init__(self, default_ttl: int = 300) -> None:
        self._store: dict[str, _Entry] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    def _key(self, capability: str, entity: Any, module: str = "") -> str:
        return f"{capability}:{str(entity)}:{module}"

    def get(self, capability: str, entity: Any, module: str = "") -> Any | None:
        key = self._key(capability, entity, module)
        with self._lock:
            entry = self._store.get(key)
            if entry is None or time.monotonic() > entry.expires_at:
                self._store.pop(key, None)
                return None
            return entry.value

    def set(
        self,
        capability: str,
        entity: Any,
        value: Any,
        module: str = "",
        ttl: int | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        key = self._key(capability, entity, module)
        effective_ttl = ttl or ttl_seconds or self._default_ttl
        with self._lock:
            self._store[key] = _Entry(value, effective_ttl)


    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def evict_expired(self) -> int:
        now = time.monotonic()
        removed = 0
        with self._lock:
            expired = [k for k, v in self._store.items() if now > v.expires_at]
            for k in expired:
                del self._store[k]
                removed += 1
        return removed

    @property
    def size(self) -> int:
        return len(self._store)


# Module-level singleton
_cache: CapabilityCache | None = None


def get_capability_cache() -> CapabilityCache:
    global _cache
    if _cache is None:
        from news_rag.config import get_settings
        settings = get_settings()
        _cache = CapabilityCache(default_ttl=settings.fund_cache_ttl)
    return _cache
