"""Global throttle and circuit breaker for news.google.com requests."""

from __future__ import annotations

import logging
import random
import threading
import time
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_GOOGLE_HOSTS = frozenset({"news.google.com", "www.news.google.com"})


class GoogleBlockedError(RuntimeError):
    """Raised when Google rate-limits this IP and the circuit breaker is open."""


class GoogleCircuitBreaker:
    def __init__(self, *, fail_threshold: int = 3, cool_down_sec: float = 15 * 60) -> None:
        self.fail_threshold = fail_threshold
        self.cool_down_sec = cool_down_sec
        self._fails = 0
        self._until = 0.0
        self._lock = threading.Lock()

    def blocked(self) -> bool:
        with self._lock:
            return time.time() < self._until

    def assert_allowed(self) -> None:
        if self.blocked():
            remaining = max(0, int(self._until - time.time()))
            raise GoogleBlockedError(
                f"Google News circuit open; retry after ~{remaining}s cool-down"
            )

    def record_success(self) -> None:
        with self._lock:
            self._fails = 0

    def record_block(self) -> None:
        with self._lock:
            self._fails += 1
            if self._fails >= self.fail_threshold:
                self._until = time.time() + self.cool_down_sec
                logger.warning(
                    "GOOGLE circuit open fails=%s cool_down_sec=%s",
                    self._fails,
                    self.cool_down_sec,
                )


google_breaker = GoogleCircuitBreaker()

_g_lock = threading.Lock()
_g_last = 0.0


def is_google_host(url: str) -> bool:
    try:
        return urlparse(url).netloc.lower() in _GOOGLE_HOSTS
    except Exception:
        return False


def google_throttle(min_gap: float = 1.5, jitter: float = 1.0) -> None:
    global _g_last
    with _g_lock:
        wait = min_gap + random.random() * jitter - (time.monotonic() - _g_last)
        if wait > 0:
            time.sleep(wait)
        _g_last = time.monotonic()


def looks_like_google_block(status_code: int, final_url: str, body: str) -> bool:
    if status_code >= 400:
        return True
    url_l = (final_url or "").lower()
    if "/sorry/" in url_l or "google.com/sorry" in url_l:
        return True
    snippet = (body or "")[:3000].lower()
    return "unusual traffic" in snippet or "detected unusual traffic" in snippet


def log_google_block(status_code: int, url: str) -> None:
    logger.warning("GOOGLE BLOCK status=%s url=%s", status_code, (url or "")[:120])
