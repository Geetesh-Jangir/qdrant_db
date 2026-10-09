"""Minimum gap between HTTP requests to the same publisher host."""

from __future__ import annotations

import threading
import time

from lib.google_guard import is_google_host
from news_pipeline.textutil import host_of

_lock = threading.Lock()
_last_by_host: dict[str, float] = {}


def wait_for_domain(url: str, gap_sec: float) -> None:
    if gap_sec <= 0:
        return
    host = host_of(url)
    if not host or is_google_host(url):
        return
    with _lock:
        now = time.monotonic()
        last = _last_by_host.get(host, 0.0)
        wait = gap_sec - (now - last)
        if wait > 0:
            time.sleep(wait)
        _last_by_host[host] = time.monotonic()
