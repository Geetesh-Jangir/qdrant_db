"""Load investor equity schemes from workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_insight.portfolio_insights.fetch import valid_crn
from news_rag.fund_rating_categories import CATEGORIES, fund_type_for_category, match_scheme_category
from news_rag.portfolio.client import fetch_workspace_raw
from news_rag.portfolio.errors import InvalidCRN, PortfolioNotConfigured, PortfolioUpstreamError
from news_rag.portfolio.normalize import normalize_workspace


@dataclass(frozen=True)
class FundRow:
    isin: str
    scheme_name: str
    scheme_category: str
    aum_inr: float
    portfolio_pct: float


def _is_equity(row: dict[str, Any]) -> bool:
    cat = str(row.get("scheme_category") or "").strip()
    cat_low = cat.casefold()
    equity_cats = {c.casefold() for c in CATEGORIES.get("equity", ())}
    if cat_low in equity_cats:
        return True
    if fund_type_for_category(cat) == "equity":
        return True
    match = match_scheme_category(cat)
    if match and match.fund_type == "equity" and (match.locked or match.category):
        return True
    asset = str(row.get("asset_type") or "").lower()
    return "equity" in asset


def load_equity_holdings(crn: str, *, top_n: int | None = None) -> tuple[list[FundRow], dict[str, Any]]:
    crn = str(crn or "").strip()
    if not valid_crn(crn):
        raise ValueError("bad_crn")
    try:
        raw = fetch_workspace_raw(crn)
    except InvalidCRN:
        raise ValueError("bad_crn") from None
    except PortfolioNotConfigured as exc:
        raise ValueError("portfolio_not_configured") from exc
    except PortfolioUpstreamError as exc:
        raise ValueError(f"upstream:{exc}") from exc

    doc = normalize_workspace(raw)
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    total_aum = float(summary.get("aum_inr") or 0.0)
    holdings = [h for h in (doc.get("holdings") or []) if isinstance(h, dict)]
    equity_rows: list[dict[str, Any]] = []
    for row in holdings:
        if not _is_equity(row):
            continue
        isin = str(row.get("isin") or "").strip().upper()
        if not isin:
            continue
        aum = float(row.get("aum_inr") or 0.0)
        equity_rows.append(row)

    equity_rows.sort(key=lambda r: float(r.get("aum_inr") or 0.0), reverse=True)
    if top_n is not None and top_n > 0:
        equity_rows = equity_rows[:top_n]

    out: list[FundRow] = []
    for row in equity_rows:
        aum = float(row.get("aum_inr") or 0.0)
        pct = round((100.0 * aum / total_aum), 2) if total_aum > 0 else 0.0
        out.append(
            FundRow(
                isin=str(row.get("isin") or "").upper(),
                scheme_name=str(row.get("scheme_name") or ""),
                scheme_category=str(row.get("scheme_category") or ""),
                aum_inr=aum,
                portfolio_pct=pct,
            )
        )
    meta = {
        "crn": crn,
        "total_aum_inr": total_aum,
        "equity_fund_count": len(out),
        "as_of": (doc.get("meta") or {}).get("as_of_date") if isinstance(doc.get("meta"), dict) else None,
    }
    return out, meta