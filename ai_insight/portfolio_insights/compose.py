"""Compose personalized insight feed for a CRN."""

from __future__ import annotations

from typing import Any

from ai_insight.portfolio_insights.cards import load_common_cards
from ai_insight.portfolio_insights.catalog import readiness, resolve_trading_date
from ai_insight.portfolio_insights.config import MAX_COMMON
from ai_insight.portfolio_insights.fetch import fetch_portfolio, valid_crn
from ai_insight.portfolio_insights.match import match_holdings, match_sectors, _portfolio_holdings, _portfolio_sectors


MISSING_MESSAGE = (
    "Insights are not created and stored for this trading day. "
    "Run Create insights on Market Insights and Run on Stock Holding Insights, then try again."
)


def compose_portfolio_insights(crn: str, trading_date: str | None = None) -> dict[str, Any]:
    crn = str(crn or "").strip()
    date = resolve_trading_date(trading_date)
    if not date:
        return {
            "status": "missing_insights",
            "trading_date": None,
            "crn": crn,
            "message": MISSING_MESSAGE,
            "missing": ["trading_date"],
        }

    check = readiness(date)
    if not check.ready:
        return {
            "status": "missing_insights",
            "trading_date": date,
            "crn": crn,
            "message": MISSING_MESSAGE,
            "missing": check.missing,
            "details": check.details,
        }

    if not valid_crn(crn):
        return {
            "status": "bad_crn",
            "trading_date": date,
            "crn": crn,
            "message": "Enter a valid CRN (letters, numbers, hyphen, underscore).",
        }

    portfolio_raw = fetch_portfolio(crn)
    if not portfolio_raw or (
        not portfolio_raw.get("top_holdings") and not portfolio_raw.get("sector_allocation")
    ):
        return {
            "status": "bad_crn",
            "trading_date": date,
            "crn": crn,
            "message": "Could not load portfolio for this CRN.",
        }

    common = load_common_cards(date, MAX_COMMON)
    sectors, sectors_unmatched = match_sectors(portfolio_raw, date, crn=crn)
    holdings, holdings_unmatched = match_holdings(portfolio_raw, date, crn=crn)

    return {
        "status": "ok",
        "trading_date": date,
        "crn": crn,
        "portfolio": {
            "as_of_date": portfolio_raw.get("as_of_date"),
            "top_sectors": _portfolio_sectors(portfolio_raw)[:10],
            "top_holdings": _portfolio_holdings(portfolio_raw)[:10],
        },
        "common": common,
        "sectors": sectors,
        "holdings": holdings,
        "gaps": {
            "sectors_unmatched": sectors_unmatched[:15],
            "holdings_unmatched": holdings_unmatched[:15],
        },
    }