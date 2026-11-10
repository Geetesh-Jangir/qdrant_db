"""Non-blocking portfolio backend health probe."""

from __future__ import annotations

import threading
import time
from typing import Any

from news_rag.config import get_settings

_probe_lock = threading.Lock()
_probe_cache: dict[str, Any] = {"at": 0.0, "ok": False, "detail": ""}


def portfolio_health_snapshot(*, max_age_sec: float = 60.0) -> dict[str, Any]:
    settings = get_settings()
    configured = bool(settings.portfolio_enabled)
    out: dict[str, Any] = {
        "portfolio_configured": configured,
        "portfolio_backend_ok": False,
    }
    if not configured:
        out["portfolio_backend_ok"] = None
        return out

    now = time.time()
    with _probe_lock:
        if now - float(_probe_cache.get("at") or 0) < max_age_sec:
            out["portfolio_backend_ok"] = bool(_probe_cache.get("ok"))
            out["detail"] = str(_probe_cache.get("detail") or "")
            return out

    ok = False
    detail = ""
    try:
        from news_rag.portfolio.cache import get_active_crn, get_normalized_portfolio

        crn = get_active_crn()
        _, stats = get_normalized_portfolio(crn)
        ok = True
        detail = f"cache={'hit' if stats.get('from_cache') else 'miss'}"
    except Exception as exc:  # noqa: BLE001
        detail = type(exc).__name__

    with _probe_lock:
        _probe_cache["at"] = now
        _probe_cache["ok"] = ok
        _probe_cache["detail"] = detail

    out["portfolio_backend_ok"] = ok
    out["detail"] = detail
    return out
