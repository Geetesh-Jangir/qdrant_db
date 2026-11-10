"""HTTP client for admin workspace endpoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from news_rag.config import get_settings
from news_rag.rupeestop_auth import rupeestop_admin_request_headers
from news_rag.portfolio.errors import InvalidCRN, PortfolioNotConfigured, PortfolioUpstreamError


def _load_json_file(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


def _resolve_fixture_path(settings: Any, root: Path, crn: str) -> Path | None:
    """Per-CRN file, or an explicit fixture path. Never a shared sample for an unknown CRN."""
    by_crn = root / "data" / "portfolios" / f"{crn}.json"
    if by_crn.is_file():
        return by_crn
    explicit = str(getattr(settings, "portfolio_fixture_path", "") or "").strip()
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = root / path
        return path if path.is_file() else None
    return None


def _workspace_url(base: str, crn: str) -> str:
    base = base.rstrip("/")
    return f"{base}/api/v1/admin/dashboard/clients/by-crn/{crn}/workspace"


def fetch_workspace_raw(crn: str) -> dict[str, Any]:
    settings = get_settings()
    crn = str(crn or "").strip()
    if not crn:
        raise PortfolioNotConfigured("CLIENT_REF_NO is not set")

    root = Path(__file__).resolve().parents[2]
    fixture_path = _resolve_fixture_path(settings, root, crn)
    if fixture_path is not None:
        return _load_json_file(fixture_path)

    base = str(getattr(settings, "rupeestop_backend_base", "") or "https://backend.rupeestop.com").strip()

    # The workspace often sends its first byte after about a minute.
    read_timeout = max(float(getattr(settings, "portfolio_http_timeout_sec", 120.0) or 120.0), 90.0)
    retries = int(getattr(settings, "portfolio_http_retries", 1) or 1)
    url = _workspace_url(base, crn)
    headers = rupeestop_admin_request_headers(url, settings=settings)
    last_exc: Exception | None = None
    timeout = httpx.Timeout(connect=10.0, read=read_timeout, write=30.0, pool=10.0)

    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url, headers=headers)
            if resp.status_code in (502, 503, 504) and attempt < retries:
                continue
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {}
        except httpx.TimeoutException as exc:
            raise PortfolioUpstreamError(
                "The portfolio service did not respond in time. The CRN was accepted; try again."
            ) from exc
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            status = exc.response.status_code if exc.response is not None else 0
            if status in (502, 503, 504) and attempt < retries:
                continue
            if status == 404:
                raise InvalidCRN(f"wrong CRN: {crn}") from exc
            if status in (401, 403):
                raise PortfolioUpstreamError(
                    "workspace auth failed — set RUPEESTOP_AUTH_TOKEN (or RUPEESTOP_ADMIN_TOKEN) or "
                    f"PORTFOLIO_FIXTURE_PATH (or add data/portfolios/{crn}.json)",
                ) from exc
            raise PortfolioUpstreamError(f"workspace HTTP {status or 'error'}") from exc
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < retries:
                continue
            raise PortfolioUpstreamError(str(exc)[:200]) from exc

    raise PortfolioUpstreamError(str(last_exc or "fetch failed"))
