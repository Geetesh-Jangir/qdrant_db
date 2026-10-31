"""Project minimal JSON slices for get_investor_portfolio modules."""

from __future__ import annotations

import copy
from typing import Any

from news_rag.portfolio.store import PortfolioStore

ALLOWED_MODULES = frozenset({
    "meta",
    "summary",
    "allocation",
    "holdings",
    "pnl_summary",
    "pnl_scheme",
    "sip",
    "stp",
    "xirr",
    "profile_risk",
})

HOLDINGS_FIELDS = {
    "minimal": ("scheme_name", "aum_inr", "gain_loss_inr", "xirr_pct"),
    "standard": (
        "scheme_name",
        "scheme_category",
        "aum_inr",
        "invested_inr",
        "gain_loss_inr",
        "xirr_pct",
        "current_nav",
        "units",
    ),
    "full": (
        "scheme_name",
        "isin",
        "folio_number",
        "folio_scheme",
        "scheme_category",
        "scheme_type",
        "asset_type",
        "amc_name",
        "invested_inr",
        "aum_inr",
        "gain_loss_inr",
        "absolute_return_pct",
        "xirr_pct",
        "current_nav",
        "nav_date",
        "units",
        "avg_nav",
    ),
}


def _pick_row(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {k: row.get(k) for k in fields if k in row}


def project_modules(doc: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    modules = [m for m in (args.get("modules") or []) if m in ALLOWED_MODULES]
    if not modules:
        return {"ok": False, "error": "no_modules", "data": {}}

    store = PortfolioStore(doc)
    out: dict[str, Any] = {}
    include_meta = bool(args.get("include_meta", True))

    if include_meta and "meta" not in modules:
        out["meta"] = copy.deepcopy(doc.get("meta") or {})
    elif "meta" in modules:
        out["meta"] = copy.deepcopy(doc.get("meta") or {})

    if "summary" in modules:
        out["summary"] = copy.deepcopy(doc.get("summary") or {})

    if "allocation" in modules:
        out["allocation"] = copy.deepcopy(doc.get("allocation") or {})

    if "holdings" in modules:
        preset = str(args.get("holdings_fields") or "minimal").lower()
        fields = HOLDINGS_FIELDS.get(preset, HOLDINGS_FIELDS["minimal"])
        rows = store.holdings(
            scheme_filter=str(args.get("scheme_filter") or ""),
            top_n=int(args.get("top_n") or 10),
            sort_by=str(args.get("sort_by") or "aum"),
        )
        out["holdings"] = [_pick_row(r, fields) for r in rows]

    if "pnl_summary" in modules:
        out["pnl_summary"] = copy.deepcopy(doc.get("pnl_summary") or {})

    if "pnl_scheme" in modules:
        scheme_filter = str(args.get("scheme_filter") or "").strip()
        row = store.pnl_scheme(scheme_filter) if scheme_filter else None
        if row:
            limit = max(1, min(int(args.get("transaction_limit") or 5), 15))
            slim = dict(row)
            txns = list(slim.get("transactions") or [])[:limit]
            slim["transactions"] = txns
            out["pnl_scheme"] = slim
        else:
            out["pnl_scheme"] = {}

    if "sip" in modules:
        sip = copy.deepcopy(doc.get("sip") or {})
        if args.get("live_only", True):
            plans = [p for p in (sip.get("plans") or []) if isinstance(p, dict) and p.get("is_live")]
            sip["plans"] = plans
        out["sip"] = sip

    if "stp" in modules:
        stp = copy.deepcopy(doc.get("stp") or {})
        if args.get("live_only", True):
            plans = [p for p in (stp.get("plans") or []) if isinstance(p, dict) and p.get("is_live")]
            stp["plans"] = plans
        out["stp"] = stp

    if "xirr" in modules:
        xirr = copy.deepcopy(doc.get("xirr") or {})
        scheme_filter = str(args.get("scheme_filter") or "").strip()
        if scheme_filter:
            schemes = [
                s
                for s in (xirr.get("schemes") or [])
                if isinstance(s, dict)
                and _scheme_match(str(s.get("scheme_name") or ""), scheme_filter)
            ]
            xirr["schemes"] = schemes
        out["xirr"] = xirr

    if "profile_risk" in modules:
        out["profile_risk"] = copy.deepcopy(doc.get("profile_risk") or {})

    return {"ok": True, "data": out}


def _scheme_match(name: str, scheme_filter: str) -> bool:
    from news_rag.portfolio.normalize import match_scheme_filter

    return match_scheme_filter(name, scheme_filter)
