"""Bearer token for RupeeStop backend calls (admin routes require auth)."""

from __future__ import annotations

from typing import Any


def rupeestop_bearer_token(settings: Any | None = None) -> str:
    from news_rag.config import get_settings

    cfg = settings or get_settings()
    for attr in ("rupeestop_auth_token", "rupeestop_admin_token"):
        token = str(getattr(cfg, attr, "") or "").strip()
        if token:
            return token
    return ""


def rupeestop_admin_request_headers(url: str, *, settings: Any | None = None) -> dict[str, str]:
    """Authorization header for URLs under /api/v1/admin/."""
    headers = {"Accept": "application/json"}
    if "/admin/" not in str(url or ""):
        return headers
    token = rupeestop_bearer_token(settings)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
