"""FastAPI routes for equity fund week insights."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from new.pages import equity_fund_week_page
from new.run import run_equity_fund_week, run_equity_fund_week_by_isin


class EquityFundWeekRequest(BaseModel):
    crn: str | None = Field(default=None, max_length=64)
    isin: str | None = Field(default=None, max_length=24)
    top_n: int | None = Field(default=None, ge=1, le=50)
    dry_run: bool = False

    @model_validator(mode="after")
    def exactly_one_source(self) -> EquityFundWeekRequest:
        crn = (self.crn or "").strip()
        isin = (self.isin or "").strip()
        if bool(crn) == bool(isin):
            raise ValueError("Provide either crn or isin, not both and not neither.")
        if crn and len(crn) < 3:
            raise ValueError("CRN must be at least 3 characters.")
        object.__setattr__(self, "crn", crn or None)
        object.__setattr__(self, "isin", isin or None)
        return self


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
        if body.isin:
            out = run_equity_fund_week_by_isin(body.isin, dry_run=body.dry_run)
        else:
            out = run_equity_fund_week(body.crn or "", top_n=body.top_n, dry_run=body.dry_run)
        return JSONResponse(out, headers={"Cache-Control": "no-store"})

    return router