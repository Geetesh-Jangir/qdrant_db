"""Optional failure webhook. Off unless INSIGHTS_FAILURE_WEBHOOK_URL is set."""

from __future__ import annotations

import os

import httpx


def notify_failure(text: str) -> None:
    url = os.environ.get("INSIGHTS_FAILURE_WEBHOOK_URL", "").strip()
    if not url:
        return
    try:
        httpx.post(url, json={"text": text[:500]}, timeout=5.0)
    except Exception:
        return
