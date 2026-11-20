"""Static page for equity fund week UI."""

from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse

_STATIC = Path(__file__).resolve().parent / "static"
_NO_CACHE = {"Cache-Control": "no-cache"}


def equity_fund_week_page() -> FileResponse:
    page = _STATIC / "equity_fund_week.html"
    if not page.is_file():
        raise FileNotFoundError(str(page))
    return FileResponse(page, headers=_NO_CACHE)