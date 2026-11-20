"""Load a single fund by ISIN for equity fund week (no portfolio)."""

from __future__ import annotations

import re
from typing import Any

from news_rag.fund_search import get_fund_index, resolve_canonical_isin

from new.portfolio_equity import FundRow

_ISIN_RE = re.compile(r"^INF[A-Z0-9]{9}$", re.I)


def normalize_isin(raw: str) -> str:
    return resolve_canonical_isin(str(raw or "").strip())


def is_valid_isin_shape(isin: str) -> bool:
    return bool(_ISIN_RE.match(isin))


def fetch_fund_detail_for_week(isin: str) -> dict[str, Any] | None:
    index = get_fund_index()
    return index.fetch_fund_detail_from_api(isin)


def is_equity_scheme_type(detail: dict[str, Any]) -> bool:
    stype = str(detail.get("scheme_type") or "").strip().casefold()
    return stype == "equity"


def scheme_type_label(detail: dict[str, Any]) -> str:
    return str(detail.get("scheme_type") or "unknown").strip() or "unknown"


def fund_row_from_detail(detail: dict[str, Any]) -> FundRow:
    isin = str(detail.get("isin") or "").strip().upper()
    name = str(detail.get("fund_name") or detail.get("fund_short_name") or isin).strip()
    category = str(detail.get("category") or "").strip()
    return FundRow(
        isin=isin,
        scheme_name=name,
        scheme_category=category,
        aum_inr=0.0,
        portfolio_pct=0.0,
    )


def load_equity_fund_by_isin(raw_isin: str) -> tuple[FundRow, dict[str, Any]]:
    """Validate ISIN, fetch detail, require equity scheme_type."""
    cleaned = normalize_isin(raw_isin)
    if not cleaned or not is_valid_isin_shape(cleaned):
        raise ValueError("bad_isin")
    detail = fetch_fund_detail_for_week(cleaned)
    if not detail:
        raise ValueError("fund_not_found")
    if not is_equity_scheme_type(detail):
        raise ValueError(f"not_equity:{scheme_type_label(detail)}")
    fund = fund_row_from_detail(detail)
    meta = {
        "mode": "isin",
        "isin": fund.isin,
        "scheme_name": fund.scheme_name,
        "scheme_type": scheme_type_label(detail),
    }
    return fund, meta