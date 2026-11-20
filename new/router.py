"""FastAPI routes for equity fund week insights."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from new.pages import equity_fund_week_page
from new.run import run_equity_fund_week


class EquityFundWeekRequest(BaseModel):
    crn: str = Field(min_length=3, max_length=64)
    top_n: int | None = Field(default=None, ge=1, le=50)
    dry_run: bool = False


def create_equity_fund_week_router(
    check_token: Callable[[str | None, str | None], None],
) -> APIRouter:
    router = APIRouter(tags=["equity-fund-week"])

    @router.get("/equity-fund-week")
    def page() -> Any:
        return equity_fund_week_page()

    @router.post("/api/equity-fund-week/run")
    def run_endpoint(
        body: EquityFundWeekRequest,
        authorization: str | None = Header(default=None),
        x_app_token: str | None = Header(default=None),
    ) -> JSONResponse:
        check_token(authorization, x_app_token)
        out = run_equity_fund_week(body.crn, top_n=body.top_n, dry_run=body.dry_run)
        return JSONResponse(out, headers={"Cache-Control": "no-store"})

    return router