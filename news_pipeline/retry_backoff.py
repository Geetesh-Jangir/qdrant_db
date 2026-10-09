"""Shared exponential backoff delays for scrape and Google resolve."""

from __future__ import annotations

import time


def sleep_before_attempt(attempt_index: int, base_sec: float) -> None:
    """attempt_index is 0-based. No sleep on first attempt; then base, base*2, ..."""
    if attempt_index <= 0:
        return
    delay = base_sec * (2 ** (attempt_index - 1))
    if delay > 0:
        time.sleep(delay)
