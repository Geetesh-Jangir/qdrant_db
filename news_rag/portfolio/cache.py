"""TTL cache and circuit breaker for normalized portfolio documents."""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

from news_rag.config import get_settings
from news_rag.portfolio.client import fetch_workspace_raw
from news_rag.portfolio.errors import PortfolioError, PortfolioNotConfigured
from news_rag.portfolio.normalize import normalize_workspace

logger = logging.getLogger(__name__)

_FAIL_THRESHOLD = 3
_BREAKER_SEC = 60.0


@dataclass
class _CacheEntry:
    doc: dict[str, Any]
    expires_at: float
    fetched_at: float


@dataclass
class _BreakerState:
    failures: int = 0
    open_until: float = 0.0


_lock = threading.Lock()
_cache: dict[str, _CacheEntry] = {}
_breakers: dict[str, _BreakerState] = {}
_last_fetch_ms: dict[str, float] = {}


def crn_log_id(crn: str) -> str:
    raw = str(crn or "").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def get_normalized_portfolio(crn: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (normalized_doc, stats). stats has fetch_ms, from_cache, crn_id."""
    settings = get_settings()
    crn = str(crn or "").strip()
    if not crn:
        raise PortfolioNotConfigured("CLIENT_REF_NO is not set")

    ttl = float(getattr(settings, "portfolio_ttl_sec", 180) or 180)
    now = time.time()
    stats: dict[str, Any] = {"crn_id": crn_log_id(crn), "from_cache": False, "fetch_ms": 0.0}

    with _lock:
        breaker = _breakers.setdefault(crn, _BreakerState())
        if breaker.open_until > now:
            entry = _cache.get(crn)
            if entry:
                stats["from_cache"] = True
                stats["stale"] = True
                return entry.doc, stats
            raise PortfolioError("portfolio circuit open", code="circuit_open")

        entry = _cache.get(crn)
        if entry and entry.expires_at > now:
            stats["from_cache"] = True
            stats["fetch_ms"] = _last_fetch_ms.get(crn, 0.0)
            return entry.doc, stats

    t0 = time.perf_counter()
    try:
        raw = fetch_workspace_raw(crn)
        doc = normalize_workspace(raw)
        fetch_ms = round((time.perf_counter() - t0) * 1000, 1)
        with _lock:
            _cache[crn] = _CacheEntry(doc=doc, expires_at=now + ttl, fetched_at=now)
            _last_fetch_ms[crn] = fetch_ms
            _breakers[crn] = _BreakerState()
        stats["fetch_ms"] = fetch_ms
        return doc, stats
    except PortfolioError:
        with _lock:
            breaker = _breakers.setdefault(crn, _BreakerState())
            breaker.failures += 1
            if breaker.failures >= _FAIL_THRESHOLD:
                breaker.open_until = now + _BREAKER_SEC
            entry = _cache.get(crn)
            if entry:
                stats["from_cache"] = True
                stats["stale"] = True
                stats["fetch_ms"] = _last_fetch_ms.get(crn, 0.0)
                return entry.doc, stats
        raise


def clear_cache_for_tests() -> None:
    with _lock:
        _cache.clear()
        _breakers.clear()
        _last_fetch_ms.clear()
