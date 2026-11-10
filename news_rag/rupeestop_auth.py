"""Bearer token for RupeeStop backend calls (admin routes require auth)."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_REFRESH_SKEW_SEC = 60


def rupeestop_bearer_token(settings: Any | None = None) -> str:
    from news_rag.config import get_settings

    cfg = settings or get_settings()
    for attr in ("rupeestop_auth_token", "rupeestop_admin_token"):
        token = str(getattr(cfg, attr, "") or "").strip()
        if token:
            return token
    return ""


def _jwt_exp_epoch(token: str) -> int | None:
    parts = str(token or "").split(".")
    if len(parts) < 2:
        return None
    payload = parts[1]
    pad = "=" * (-len(payload) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + pad))
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    raw = data.get("exp")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _looks_like_jwt(token: str) -> bool:
    return len(str(token or "").split(".")) >= 3


def token_needs_refresh(token: str, *, now: float | None = None) -> bool:
    """True when the bearer is missing, JWT is expired, or JWT has no exp."""
    cleaned = str(token or "").strip()
    if not cleaned:
        return True
    if not _looks_like_jwt(cleaned):
        return False
    exp = _jwt_exp_epoch(cleaned)
    if exp is None:
        return True
    clock = float(now if now is not None else time.time())
    return exp <= clock + _REFRESH_SKEW_SEC


def _login_url(settings: Any) -> str:
    base = str(getattr(settings, "rupeestop_backend_base", "") or "https://backend.rupeestop.com").rstrip("/")
    return f"{base}/api/v1/user/admin-login"


def _login_credentials(settings: Any) -> tuple[str, str]:
    user = str(getattr(settings, "rupeestop_admin_username", "") or "").strip()
    password = str(getattr(settings, "rupeestop_admin_password", "") or "").strip()
    return user, password


def _fetch_admin_login_token(settings: Any) -> str:
    username, password = _login_credentials(settings)
    if not username or not password:
        return ""
    url = _login_url(settings)
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                url,
                json={"username": username, "password": password},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            logger.warning("admin-login failed status=%s", resp.status_code)
            return ""
        body = resp.json()
        token = ""
        if isinstance(body, dict):
            token = str(body.get("token") or "").strip()
            if not token and isinstance(body.get("data"), dict):
                token = str(body["data"].get("token") or "").strip()
        if not token:
            logger.warning("admin-login response had no token")
            return ""
        return token
    except Exception as exc:
        logger.warning("admin-login request failed: %s", type(exc).__name__)
        return ""


def _env_files_for_token() -> list[Path]:
    from news_rag.config import _ROOT

    return [_ROOT / ".env", _ROOT / "news_rag" / ".env"]


def _rewrite_env_token(env_path: Path, token: str) -> None:
    if not env_path.is_file():
        return
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return
    line = f"RUPEESTOP_AUTH_TOKEN={token}"
    pattern = re.compile(r"^RUPEESTOP_AUTH_TOKEN=.*$", re.M)
    if pattern.search(text):
        new_text = pattern.sub(line, text, count=1)
    else:
        sep = "" if text.endswith("\n") or not text else "\n"
        new_text = f"{text}{sep}{line}\n"
    try:
        env_path.write_text(new_text, encoding="utf-8")
    except OSError as exc:
        logger.info("could not write %s: %s", env_path.name, type(exc).__name__)


def persist_rupeestop_auth_token(token: str) -> None:
    """Process env first so the running server uses the token; .env is best-effort."""
    cleaned = str(token or "").strip()
    if not cleaned:
        return
    os.environ["RUPEESTOP_AUTH_TOKEN"] = cleaned
    for path in _env_files_for_token():
        _rewrite_env_token(path, cleaned)


def refresh_rupeestop_bearer_force(settings: Any | None = None) -> str:
    """Drop the cached bearer and obtain a new JWT via admin-login when credentials exist."""
    from news_rag.config import get_settings

    cfg = settings or get_settings()
    with _lock:
        os.environ.pop("RUPEESTOP_AUTH_TOKEN", None)
        fresh = _fetch_admin_login_token(cfg) if all(_login_credentials(cfg)) else ""
        if fresh and not token_needs_refresh(fresh):
            persist_rupeestop_auth_token(fresh)
            return fresh
        token = rupeestop_bearer_token(cfg)
        if token and token_needs_refresh(token):
            logger.warning(
                "RupeeStop admin JWT is expired; set RUPEESTOP_ADMIN_USERNAME and "
                "RUPEESTOP_ADMIN_PASSWORD for auto-refresh, or update RUPEESTOP_AUTH_TOKEN."
            )
        return token


def ensure_fresh_rupeestop_bearer(settings: Any | None = None) -> str:
    """Return a bearer for admin routes; refresh from admin-login only when JWT is expired."""
    from news_rag.config import get_settings

    def _cfg() -> Any:
        return settings if settings is not None else get_settings()

    def _current() -> str:
        return rupeestop_bearer_token(_cfg())

    token = _current()
    if not token_needs_refresh(token):
        return token
    if not all(_login_credentials(_cfg())):
        return token
    with _lock:
        token = _current()
        if not token_needs_refresh(token):
            return token
        fresh = _fetch_admin_login_token(_cfg())
        if fresh and not token_needs_refresh(fresh):
            persist_rupeestop_auth_token(fresh)
            return fresh
        return token


def rupeestop_admin_request_headers(url: str, *, settings: Any | None = None) -> dict[str, str]:
    """Authorization header for URLs under /api/v1/admin/."""
    headers = {"Accept": "application/json"}
    if "/admin/" not in str(url or ""):
        return headers
    from news_rag.config import get_settings

    cfg = settings or get_settings()
    token = ensure_fresh_rupeestop_bearer(cfg)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
