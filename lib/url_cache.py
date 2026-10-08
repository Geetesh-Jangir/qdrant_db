"""Persistent cache for Google News wrapper URL → publisher URL."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

FAIL_TTL_SEC = 6 * 3600
_LOCK = threading.Lock()
_DB: sqlite3.Connection | None = None


def _db_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    path = root / "data" / "news_scrape_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path / "google_resolve.db"


def _connection() -> sqlite3.Connection:
    global _DB
    if _DB is None:
        _DB = sqlite3.connect(str(_db_path()), check_same_thread=False)
        _DB.execute(
            "CREATE TABLE IF NOT EXISTS resolve_cache (k TEXT PRIMARY KEY, v TEXT NOT NULL, ts REAL NOT NULL)"
        )
        _DB.commit()
    return _DB


def get_resolved(wrapper_url: str, *, fail_ttl: float = FAIL_TTL_SEC) -> str | None:
    """Return publisher URL, empty string if cached failure (within TTL), or None on miss."""
    with _LOCK:
        row = _connection().execute(
            "SELECT v, ts FROM resolve_cache WHERE k = ?", (wrapper_url,)
        ).fetchone()
    if not row:
        return None
    value, ts = row[0], float(row[1])
    if value:
        return value
    if time.time() - ts < fail_ttl:
        return ""
    return None


def put_resolved(wrapper_url: str, publisher_url: str) -> None:
    with _LOCK:
        _connection().execute(
            "INSERT OR REPLACE INTO resolve_cache VALUES (?,?,?)",
            (wrapper_url, publisher_url, time.time()),
        )
        _connection().commit()


def put_failure(wrapper_url: str) -> None:
    with _LOCK:
        _connection().execute(
            "INSERT OR REPLACE INTO resolve_cache VALUES (?,?,?)",
            (wrapper_url, "", time.time()),
        )
        _connection().commit()


def reset_cache_db() -> None:
    """Close the SQLite handle (for tests)."""
    global _DB
    with _LOCK:
        if _DB is not None:
            _DB.close()
            _DB = None
