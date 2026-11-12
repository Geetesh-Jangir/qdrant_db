"""PII-safe normalization of admin workspace JSON into a compact indexed document."""

from __future__ import annotations

import re
from typing import Any

_PII_KEYS = frozenset({
    "pan",
    "guardianpan",
    "email",
    "mobile",
    "phone",
    "pekrn",
    "clientidtoken",
    "accountno",
    "bankaccount",
    "emailrelationship",
    "addressline1",
    "addressline2",
    "addressline3",
    "pincode",
    "dob",
    "city",
    "state",
    "country",
    "occupation",
    "guardianname",
})


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _str(value: Any) -> str:
    return str(value or "").strip()


def strip_pii_tree(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, val in obj.items():
            if str(key).lower().replace("_", "") in _PII_KEYS:
                continue
            if str(key).lower() in ("clientrefno",) and isinstance(val, str):
                continue
            out[key] = strip_pii_tree(val)
        return out
    if isinstance(obj, list):
        return [strip_pii_tree(item) for item in obj]
    return obj


def _first(*values: Any) -> Any:
    for v in values:
        if v is not None and v != "":
            return v
    return None


def _holding_from_scheme(row: dict[str, Any]) -> dict[str, Any]:
    name = _str(_first(row.get("schemeName"), row.get("fundName"), row.get("bseName")))
    return {
        "scheme_name": name,
        "isin": _str(row.get("isin")).upper(),
        "folio_number": _str(row.get("folioNumber")),
        "folio_scheme": _str(row.get("folioScheme")),
        "scheme_category": _str(row.get("schemeCategory")),
        "scheme_type": _str(row.get("schemeType")),
        "asset_type": _str(row.get("assetType")),
        "amc_name": _str(_first(row.get("amcName"), row.get("amc"))),
        "invested_inr": _num(_first(row.get("investedInr"), row.get("investedAmount"), row.get("totalInvested"))),
        "aum_inr": _num(_first(row.get("aumInr"), row.get("marketValue"), row.get("currentValue"))),
        "gain_loss_inr": _num(_first(row.get("gainLossInr"), row.get("gainLoss"))),
        "absolute_return_pct": _num(row.get("absoluteReturnPercent")),
        "xirr_pct": _num(_first(row.get("liveXirrPercent"), row.get("xirrPercent"))),
        "current_nav": _num(_first(row.get("currentNav"), row.get("nav"))),
        "nav_date": _str(_first(row.get("currentNavDate"), row.get("navDate"))),
        "units": _num(_first(row.get("availableUnits"), row.get("currentUnits"), row.get("closingUnits"))),
        "avg_nav": _num(_first(row.get("avgNav"), row.get("avgPrice"))),
    }


def _prefer_xirr(*values: Any) -> float | None:
    """Prefer a non-zero XIRR. portfolioXirrPercent is often 0 while liveXirrPercent is set."""
    parsed: list[float] = []
    for value in values:
        number = _num(value)
        if number is None:
            continue
        parsed.append(number)
    for number in parsed:
        if number != 0:
            return number
    return parsed[0] if parsed else None


def _resolve_isin(scheme_name: str) -> str:
    name = _str(scheme_name)
    if not name:
        return ""
    try:
        from news_rag.fund_search import get_fund_index

        detail, _amb, _close = get_fund_index().lookup_extracted_fund(name=name)
        return _str((detail or {}).get("isin")).upper()
    except Exception:
        return ""


def _apply_holding_values(holdings: list[dict[str, Any]], xirr_rows: list[dict[str, Any]]) -> None:
    by_folio = {str(row.get("folio_scheme") or ""): row for row in xirr_rows if row.get("folio_scheme")}
    for holding in holdings:
        matched = by_folio.get(str(holding.get("folio_scheme") or ""))
        if matched:
            if holding.get("aum_inr") is None and matched.get("market_value_at_to") is not None:
                holding["aum_inr"] = matched["market_value_at_to"]
            if holding.get("xirr_pct") is None and matched.get("xirr_pct") is not None:
                holding["xirr_pct"] = matched["xirr_pct"]
        if holding.get("aum_inr") is None and holding.get("units") and holding.get("current_nav"):
            holding["aum_inr"] = round(float(holding["units"]) * float(holding["current_nav"]), 2)
        invested = holding.get("invested_inr")
        aum = holding.get("aum_inr")
        if aum is not None and invested is not None and holding.get("gain_loss_inr") is None:
            holding["gain_loss_inr"] = round(float(aum) - float(invested), 2)
        gain = holding.get("gain_loss_inr")
        if holding.get("absolute_return_pct") is None and gain is not None and invested:
            holding["absolute_return_pct"] = round(100.0 * float(gain) / float(invested), 2)
        if not holding.get("isin"):
            holding["isin"] = _resolve_isin(str(holding.get("scheme_name") or ""))


def _allocation_block(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key in ("investedByCategory", "aumByCategory", "investedBySchemeType", "aumBySchemeType"):
        block = raw.get(key)
        if isinstance(block, dict):
            out[key] = {str(name): _num(value) for name, value in block.items()}
    for key in ("schemeTypeShare", "categoryShare"):
        rows = raw.get(key)
        if not isinstance(rows, list):
            continue
        slim = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            slim.append({
                "name": _str(row.get("name") or row.get("category") or row.get("schemeType")),
                "aum_inr": _num(_first(row.get("aumInr"), row.get("marketValue"))),
                "aum_pct": _num(_first(row.get("aumPct"), row.get("percentage"))),
            })
        out[key] = [r for r in slim if r.get("name")]
    return out


def _pnl_summary_row(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    keys = (
        "purchase", "switchIn", "switchOut", "redemption", "divPayout", "divReinvestment",
        "netInvestment", "inflow", "currentValue", "gainLoss", "gainLossRounded",
        "absoluteReturnPercent", "portfolioXirrPercent", "xirrPercent",
    )
    out: dict[str, Any] = {}
    for key in keys:
        val = raw.get(key)
        if isinstance(val, (int, float)):
            out[key] = val
        elif val is not None and val != "":
            n = _num(val)
            if n is not None:
                out[key] = n
            else:
                out[key] = val
    return out


def aggregate_term_gains(schemes: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    """Sum unrealised gain_loss by holding period from scheme transaction rows."""
    short = 0.0
    long = 0.0
    seen = False
    for scheme in schemes:
        if not isinstance(scheme, dict):
            continue
        for txn in scheme.get("transactions") or []:
            if not isinstance(txn, dict):
                continue
            gain = _num(txn.get("gain_loss"))
            term = txn.get("term")
            if gain is None or term not in ("short_term", "long_term"):
                continue
            seen = True
            if term == "long_term":
                long += gain
            else:
                short += gain
    if not seen:
        return None, None
    return round(short, 2), round(long, 2)


def _sip_plan(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "scheme_name": _str(row.get("schemeName")),
        "amount": _num(row.get("amount")),
        "monthly_amount": _num(_first(row.get("monthlyAmount"), row.get("amount"))),
        "frequency": _str(_first(row.get("frequencyLabel"), row.get("frequency"))),
        "status": _str(row.get("status")),
        "is_live": bool(row.get("isLive")),
        "start_date": _str(_first(row.get("startDate"), row.get("registerDate"))),
        "end_date": _str(row.get("endDate")),
        "next_due_date": _str(row.get("nextDueDate")),
        "last_installment_date": _str(row.get("lastInstallmentDate")),
        "installment_count": row.get("installmentCount"),
        "missed_installments": row.get("missedInstallments"),
        "folio_scheme": _str(row.get("folioScheme")),
        "bank_name": _str(row.get("bankName")),
        "systematic_reg_id": _str(row.get("systematicRegId")),
    }


def normalize_workspace(raw: dict[str, Any]) -> dict[str, Any]:
    """Build the internal normalized document used by store and project."""
    raw = strip_pii_tree(raw)
    meta_in = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
    sections = raw.get("sections") if isinstance(raw.get("sections"), dict) else {}

    def sec(name: str) -> dict[str, Any]:
        block = sections.get(name) or {}
        data = block.get("data") if isinstance(block, dict) else {}
        return data if isinstance(data, dict) else {}

    book = sec("book")
    live = sec("live")
    pnl = sec("pnl")
    sip = sec("sip")
    stp = sec("stp")
    profile = sec("profile")
    xirr_sec = sec("xirr")

    user = profile.get("user") if isinstance(profile.get("user"), dict) else {}
    live_summary = live.get("liveSummary") if isinstance(live.get("liveSummary"), dict) else {}
    book_total = (book.get("books") or {}).get("total") if isinstance(book.get("books"), dict) else {}
    if not isinstance(book_total, dict):
        book_total = {}

    live_schemes = live.get("schemes") if isinstance(live.get("schemes"), list) else []
    book_schemes = book_total.get("schemes") if isinstance(book_total.get("schemes"), list) else []
    scheme_rows = live_schemes or book_schemes
    holdings = [_holding_from_scheme(r) for r in scheme_rows if isinstance(r, dict)]
    holdings = [h for h in holdings if h.get("scheme_name")]

    ps = book.get("portfolioSummary") if isinstance(book.get("portfolioSummary"), dict) else {}
    summary = {
        "invested_inr": _num(_first(
            book_total.get("investedInr"),
            live_summary.get("totalInvestedAmount"),
            ps.get("totalInvested"),
        )),
        "aum_inr": _num(_first(
            book_total.get("aumInr"),
            live_summary.get("totalMarketValue"),
            ps.get("totalMarketValue"),
        )),
        "gain_loss_inr": _num(_first(
            book_total.get("gainLossInr"),
            live_summary.get("gainLoss"),
            ps.get("gainLossValue"),
        )),
        "absolute_return_pct": _num(_first(
            book_total.get("absoluteReturnPercent"),
            live_summary.get("gainLossPercentage"),
            ps.get("absoluteReturnPercent"),
        )),
        "portfolio_xirr_pct": _prefer_xirr(
            live_summary.get("liveXirrPercent"),
            live_summary.get("xirrPercent"),
            book_total.get("portfolioXirrPercent"),
            live_summary.get("portfolioXirrPercent"),
        ),
        "scheme_count": int(_first(book_total.get("schemeCount"), len(holdings)) or 0),
    }

    pnl_schemes = []
    for row in pnl.get("schemes") or []:
        if not isinstance(row, dict):
            continue
        pnl_schemes.append({
            "scheme_name": _str(row.get("schemeName")),
            "folio_scheme": _str(row.get("folioScheme")),
            "scheme_category": _str(row.get("schemeCategory")),
            "invested_since": _str(row.get("investedSince")),
            "fully_redeemed": bool(row.get("fullyRedeemed")),
            "current_value": _num(row.get("currentValue")),
            "gain_loss": _num(row.get("gainLoss")),
            "xirr_pct": _num(row.get("xirrPercent")),
            "transactions": [
                {
                    "date": _str(t.get("date")),
                    "amount": _num(t.get("amount")),
                    "nav": _num(t.get("nav")),
                    "units": _num(t.get("units")),
                    "transaction_type": _str(t.get("transactionType")),
                    "nature": _str(t.get("nature")),
                    "current_value": _num(t.get("currentValue")),
                    "days": t.get("days"),
                    "gain_loss": (
                        round(float(t["currentValue"]) - float(t["amount"]), 2)
                        if _num(t.get("currentValue")) is not None and _num(t.get("amount")) is not None
                        else None
                    ),
                    "term": (
                        "long_term"
                        if isinstance(t.get("days"), (int, float)) and float(t["days"]) >= 365
                        else "short_term"
                        if isinstance(t.get("days"), (int, float))
                        else ""
                    ),
                }
                for t in (row.get("transactions") or [])[:40]
                if isinstance(t, dict)
            ],
        })

    xirr_rows = []
    xirr_data = xirr_sec.get("data") if isinstance(xirr_sec.get("data"), list) else []
    for row in xirr_data:
        if not isinstance(row, dict):
            continue
        xirr_rows.append({
            "scheme_name": _str(row.get("schemeName")),
            "folio_scheme": _str(row.get("folioScheme")),
            "xirr_pct": _prefer_xirr(row.get("xirr"), row.get("xirrPercent")),
            "market_value_at_to": _num(row.get("marketValueAtTo")),
            "invested_at_to": _num(row.get("investedAmountAtTo")),
            "gain_loss": _num(row.get("gainLoss")),
            "absolute_return": _num(row.get("absoluteReturn")),
        })

    _apply_holding_values(holdings, xirr_rows)
    holdings, sold_count = _drop_sold(holdings)

    meta = {
        "sold_scheme_count": sold_count,
        "as_of_date": _str(_first(meta_in.get("asOfDate"), live.get("asOfDate"), ps.get("asOfDate"))),
        "financial_year": _str(meta_in.get("financialYear")),
        "generated_at": _str(meta_in.get("generatedAt")),
        "xirr_window": meta_in.get("xirrWindow") if isinstance(meta_in.get("xirrWindow"), dict) else {},
        "transaction_report_window": meta_in.get("transactionReportWindow")
        if isinstance(meta_in.get("transactionReportWindow"), dict)
        else {},
    }

    profile_risk = {
        "investor_name": _str(user.get("investorName")).split()[0] if user.get("investorName") else "",
        "book_type": _str(user.get("bookType")),
        "book_type_label": _str(user.get("bookTypeLabel")),
        "risk_profiler_category": _str(user.get("riskProfilerCategory")),
        "active_profiler_category": _str(user.get("activeProfilerCategory")),
        "investment_style": _str(user.get("investmentStyle")),
        "is_hybrid": bool(user.get("isHybrid")),
        "is_mfc": bool(user.get("isMFC")),
    }

    sip_plans = [_sip_plan(p) for p in (sip.get("plans") or []) if isinstance(p, dict)]
    stp_plans = [_sip_plan(p) for p in (stp.get("plans") or []) if isinstance(p, dict)]

    pnl_summary = _pnl_summary_row(pnl.get("summary") if isinstance(pnl.get("summary"), dict) else {})
    st_gain, lt_gain = aggregate_term_gains(pnl_schemes)
    if st_gain is not None:
        pnl_summary["short_term_gain_inr"] = st_gain
    if lt_gain is not None:
        pnl_summary["long_term_gain_inr"] = lt_gain

    doc = {
        "meta": meta,
        "profile_risk": profile_risk,
        "summary": summary,
        "allocation": _allocation_block(book_total.get("allocation") if isinstance(book_total.get("allocation"), dict) else {}),
        "holdings": holdings,
        "pnl_summary": pnl_summary,
        "pnl_schemes": pnl_schemes,
        "sip": {
            "summary": sip.get("summary") if isinstance(sip.get("summary"), dict) else {},
            "plans": sip_plans,
            "count": sip.get("count"),
        },
        "stp": {
            "summary": stp.get("summary") if isinstance(stp.get("summary"), dict) else {},
            "plans": stp_plans,
            "count": stp.get("count"),
        },
        "xirr": {"portfolio_xirr_pct": summary.get("portfolio_xirr_pct"), "schemes": xirr_rows},
    }
    return doc


def _drop_sold(holdings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """A holding with no current value has been sold. Totals stay on the API summary."""
    live: list[dict[str, Any]] = []
    sold = 0
    for row in holdings:
        aum = row.get("aum_inr")
        if aum is None or float(aum) == 0:
            sold += 1
            continue
        live.append(row)
    return live, sold


def match_scheme_filter(name: str, scheme_filter: str) -> bool:
    """Case-insensitive substring match for planner-provided scheme_filter."""
    needle = " ".join(str(scheme_filter or "").lower().split())
    if needle in ("", "any", "all", "none", "*"):
        return True
    hay = " ".join(str(name or "").lower().split())
    if needle in hay:
        return True
    tokens = [t for t in re.split(r"\W+", needle) if len(t) > 2]
    return bool(tokens) and all(t in hay for t in tokens)
