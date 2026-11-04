"""TTL cache and circuit breaker for normalized portfolio documents.

The snapshot is loaded at process start and refreshed in the background.
A request reads the in-memory document and does not wait on the upstream call
once a snapshot exists.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from news_rag.config import get_settings
from news_rag.portfolio.client import fetch_workspace_raw
from news_rag.portfolio.errors import PortfolioError, PortfolioNotConfigured
from news_rag.portfolio.normalize import normalize_workspace
from news_rag.portfolio.views import build_derived_views

logger = logging.getLogger(__name__)

_FAIL_THRESHOLD = 3
_BREAKER_SEC = 60.0


@dataclass
class _CacheEntry:
    doc: dict[str, Any]
    expires_at: float
    fetched_at: float
    derived: dict[str, Any] = field(default_factory=dict)


@dataclass
class _BreakerState:
    failures: int = 0
    open_until: float = 0.0


_lock = threading.Lock()
_cache: dict[str, _CacheEntry] = {}
_breakers: dict[str, _BreakerState] = {}
_last_fetch_ms: dict[str, float] = {}
_refreshing: set[str] = set()
_refresh_thread_started = False


def crn_log_id(crn: str) -> str:
    raw = str(crn or "").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def _stats(crn: str, *, from_cache: bool, stale: bool = False) -> dict[str, Any]:
    return {
        "crn_id": crn_log_id(crn),
        "from_cache": from_cache,
        "stale": stale,
        "fetch_ms": _last_fetch_ms.get(crn, 0.0),
    }


def _remember(crn: str, doc: dict[str, Any], now: float, ttl: float, fetch_ms: float) -> None:
    derived = build_derived_views(doc)
    with _lock:
        _cache[crn] = _CacheEntry(
            doc=doc,
            derived=derived,
            expires_at=now + ttl,
            fetched_at=now,
        )
        _last_fetch_ms[crn] = fetch_ms
        _breakers[crn] = _BreakerState()


def _fetch_and_store(crn: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Upstream fetch. On failure, keep and return the previous snapshot."""
    settings = get_settings()
    ttl = float(getattr(settings, "portfolio_ttl_sec", 900) or 900)
    now = time.time()
    t0 = time.perf_counter()
    try:
        raw = fetch_workspace_raw(crn)
        doc = normalize_workspace(raw)
        fetch_ms = round((time.perf_counter() - t0) * 1000, 1)
        _remember(crn, doc, now, ttl, fetch_ms)
        stats = _stats(crn, from_cache=False)
        stats["fetch_ms"] = fetch_ms
        return doc, stats
    except PortfolioError:
        with _lock:
            breaker = _breakers.setdefault(crn, _BreakerState())
            breaker.failures += 1
            if breaker.failures >= _FAIL_THRESHOLD:
                breaker.open_until = now + _BREAKER_SEC
            entry = _cache.get(crn)
        if entry is not None:
            stats = _stats(crn, from_cache=True, stale=True)
            return entry.doc, stats
        raise


def _schedule_refresh(crn: str) -> None:
    with _lock:
        if crn in _refreshing:
            return
        _refreshing.add(crn)

    def _run() -> None:
        try:
            _fetch_and_store(crn)
        except Exception:
            logger.info("portfolio refresh kept the previous snapshot crn_id=%s", crn_log_id(crn))
        finally:
            with _lock:
                _refreshing.discard(crn)

    threading.Thread(target=_run, name="portfolio-refresh-once", daemon=True).start()


def get_normalized_portfolio(crn: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (normalized_doc, stats). stats has fetch_ms, from_cache, crn_id, stale."""
    crn = str(crn or "").strip()
    if not crn:
        raise PortfolioNotConfigured("CLIENT_REF_NO is not set")

    now = time.time()
    with _lock:
        breaker = _breakers.setdefault(crn, _BreakerState())
        entry = _cache.get(crn)
        breaker_open = breaker.open_until > now
        if entry is not None:
            fresh = entry.expires_at > now and not breaker_open
            stats = _stats(crn, from_cache=True, stale=not fresh)
            doc = entry.doc
            should_refresh = not fresh and not breaker_open
        else:
            doc = None
            stats = None
            should_refresh = False
            if breaker_open:
                raise PortfolioError("portfolio circuit open", code="circuit_open")

    if doc is not None and stats is not None:
        if should_refresh:
            _schedule_refresh(crn)
        return doc, stats
    return _fetch_and_store(crn)


def peek_portfolio(crn: str | None = None) -> dict[str, Any] | None:
    """In-memory snapshot only. Never fetches."""
    crn = str(crn or get_settings().client_ref_no or "").strip()
    if not crn:
        return None
    with _lock:
        entry = _cache.get(crn)
        return entry.doc if entry is not None else None


def peek_derived(crn: str | None = None) -> dict[str, Any]:
    crn = str(crn or get_settings().client_ref_no or "").strip()
    if not crn:
        return {}
    with _lock:
        entry = _cache.get(crn)
        return dict(entry.derived) if entry is not None else {}


def find_cached_holdings(question: str, crn: str | None = None) -> list[dict[str, Any]]:
    """Holdings whose category or name the question points at. Never fetches."""
    doc = peek_portfolio(crn)
    if not doc:
        return []
    holdings = [row for row in (doc.get("holdings") or []) if isinstance(row, dict)]
    if not holdings:
        return []
    category = ""
    try:
        from news_rag.insight.investor_subject import _category_slug_from_question

        category = _category_slug_from_question(question or "")
    except Exception:
        category = ""
    if category:
        try:
            from news_rag.insight.category_plan import _categories_equivalent
        except Exception:
            _categories_equivalent = None  # type: ignore[assignment]
        matched: list[dict[str, Any]] = []
        needle = category.strip().lower()
        for row in holdings:
            row_cat = str(row.get("scheme_category") or "").strip().lower()
            name = str(row.get("scheme_name") or "").lower()
            if _categories_equivalent and _categories_equivalent(row_cat, needle):
                matched.append(row)
            elif needle and (needle in row_cat or needle in name):
                matched.append(row)
        return matched

    generic = {"fund", "plan", "growth", "regular", "direct", "cap", "scheme"}
    q = (question or "").lower()
    name_hits: list[dict[str, Any]] = []
    for row in holdings:
        name = str(row.get("scheme_name") or "")
        tokens = [tok for tok in name.lower().replace("-", " ").split() if len(tok) >= 4 and tok not in generic]
        if tokens and any(tok in q for tok in tokens):
            name_hits.append(row)
    if len(name_hits) == 1:
        return name_hits
    return []


def seed_portfolio_cache_for_tests(
    crn: str,
    doc: dict[str, Any],
    *,
    ttl_sec: float = 900,
    expired: bool = False,
) -> None:
    now = time.time()
    expires = now - 1 if expired else now + ttl_sec
    with _lock:
        _cache[crn] = _CacheEntry(
            doc=doc,
            derived=build_derived_views(doc),
            expires_at=expires,
            fetched_at=now,
        )
        _breakers.pop(crn, None)


def preload_configured_portfolio(timeout_sec: float | None = None) -> bool:
    """Load the configured book before serving. Failure logs and returns False."""
    settings = get_settings()
    crn = str(settings.client_ref_no or "").strip()
    if not crn:
        return False
    timeout = float(
        timeout_sec if timeout_sec is not None else (float(settings.portfolio_http_timeout_sec or 15) + 5)
    )
    box: dict[str, Any] = {}

    def _run() -> None:
        try:
            get_normalized_portfolio(crn)
            box["ok"] = True
        except Exception as exc:
            box["error"] = exc
            logger.warning("portfolio preload failed: %s", exc)

    thread = threading.Thread(target=_run, name="portfolio-preload", daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        logger.warning("portfolio preload timed out after %.1fs", timeout)
        return False
    if not box.get("ok"):
        return False
    start_background_refresh()
    logger.info("portfolio preload finished crn_id=%s", crn_log_id(crn))
    return True


def start_background_refresh() -> None:
    """Refresh the configured book on the TTL interval. Does not block requests."""
    global _refresh_thread_started
    with _lock:
        if _refresh_thread_started:
            return
        _refresh_thread_started = True

    def _loop() -> None:
        while True:
            settings = get_settings()
            interval = max(60.0, float(getattr(settings, "portfolio_ttl_sec", 900) or 900))
            time.sleep(interval)
            crn = str(settings.client_ref_no or "").strip()
            if not crn or crn not in _cache:
                continue
            try:
                _fetch_and_store(crn)
            except Exception:
                logger.warning("portfolio background refresh failed crn_id=%s", crn_log_id(crn))

    threading.Thread(target=_loop, name="portfolio-refresh", daemon=True).start()


def clear_cache_for_tests() -> None:
    with _lock:
        _cache.clear()
        _breakers.clear()
        _last_fetch_ms.clear()
        _refreshing.clear()
