"""HTTP client for admin workspace endpoint."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from news_rag.config import get_settings
from news_rag.portfolio.errors import PortfolioNotConfigured, PortfolioUpstreamError

logger = logging.getLogger(__name__)


def _workspace_url(base: str, crn: str) -> str:
    base = base.rstrip("/")
    return f"{base}/api/v1/admin/dashboard/clients/by-crn/{crn}/workspace"


def fetch_workspace_raw(crn: str) -> dict[str, Any]:
    settings = get_settings()
    crn = str(crn or "").strip()
    if not crn:
        raise PortfolioNotConfigured("CLIENT_REF_NO is not set")

    root = Path(__file__).resolve().parents[2]
    fixture = str(getattr(settings, "portfolio_fixture_path", "") or "").strip()
    if fixture:
        path = Path(fixture)
        if not path.is_absolute():
            path = root / path
        if path.is_file():
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}

    # Optional offline copy keyed by CRN (no extra env var required)
    by_crn = root / "data" / "portfolios" / f"{crn}.json"
    if by_crn.is_file():
        with by_crn.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}

    base = str(getattr(settings, "rupeestop_backend_base", "") or "https://backend.rupeestop.com").strip()
    token = str(getattr(settings, "rupeestop_admin_token", "") or "").strip()

    timeout = float(getattr(settings, "portfolio_http_timeout_sec", 15.0) or 15.0)
    retries = int(getattr(settings, "portfolio_http_retries", 1) or 1)
    url = _workspace_url(base, crn)
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_exc: Exception | None = None

    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url, headers=headers)
            if resp.status_code in (502, 503, 504) and attempt < retries:
                continue
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {}
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response is not None and exc.response.status_code in (502, 503, 504) and attempt < retries:
                continue
            raise PortfolioUpstreamError(
                f"workspace HTTP {exc.response.status_code if exc.response else 'error'}"
            ) from exc
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < retries:
                continue
            raise PortfolioUpstreamError(str(exc)[:200]) from exc

    raise PortfolioUpstreamError(str(last_exc or "fetch failed"))
