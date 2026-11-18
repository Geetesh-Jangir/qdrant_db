"""Static page for portfolio insights UI."""

from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse

_STATIC = Path(__file__).resolve().parents[1] / "static"
_NO_CACHE = {"Cache-Control": "no-cache"}


def portfolio_insights_page() -> FileResponse:
    page = _STATIC / "portfolio_insights.html"
    if not page.is_file():
        raise FileNotFoundError(str(page))
    return FileResponse(page, headers=_NO_CACHE)