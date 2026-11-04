"""Derived portfolio views and balance sentences, built once per refresh."""

from __future__ import annotations

from typing import Any

# One place for the mix and concentration cutoffs the composer is allowed to say.
BALANCE_THRESHOLDS = {
    "equity_heavy_pct": 80.0,
    "debt_balances_min_pct": 10.0,
    "little_debt_pct": 5.0,
    "sector_concentration_pct": 40.0,
    "single_fund_pct": 50.0,
}

# First match wins. Gold and hybrid are checked before equity so "gold" is not equity.
_ASSET_BUCKETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("gold", ("gold", "silver", "commodity", "commodities")),
    ("hybrid", ("hybrid", "balanced", "arbitrage")),
    ("debt", ("debt", "liquid", "gilt", "bond", "money market", "overnight", "floater")),
    ("equity", (
        "equity", "large cap", "mid cap", "small cap", "flexi", "multi cap",
        "elss", "value", "contra", "focused", "dividend", "sectoral", "thematic",
    )),
)


def _aum(row: dict[str, Any]) -> float:
    try:
        value = row.get("aum_inr")
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _pct(part: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * part / total, 1)


def asset_bucket(holding: dict[str, Any]) -> str:
    blob = " ".join(
        str(holding.get(key) or "")
        for key in ("scheme_type", "asset_type", "scheme_category", "scheme_name")
    ).lower()
    for bucket, keys in _ASSET_BUCKETS:
        if any(key in blob for key in keys):
            return bucket
    return "other"


def _split_from_allocation(allocation: dict[str, Any], total: float) -> dict[str, dict[str, float]]:
    """Scheme-type shares when holdings do not carry amounts."""
    split = {name: {"aum_inr": 0.0, "aum_pct": 0.0} for name in ("equity", "debt", "hybrid", "gold", "other")}
    rows = allocation.get("schemeTypeShare") if isinstance(allocation.get("schemeTypeShare"), list) else []
    if rows:
        for row in rows:
            if not isinstance(row, dict):
                continue
            bucket = asset_bucket({"scheme_type": row.get("name"), "scheme_category": row.get("name")})
            pct = row.get("aum_pct")
            try:
                pct_f = float(pct) if pct is not None else 0.0
            except (TypeError, ValueError):
                pct_f = 0.0
            split[bucket]["aum_pct"] = round(split[bucket]["aum_pct"] + pct_f, 1)
            if total > 0:
                split[bucket]["aum_inr"] = round(split[bucket]["aum_inr"] + total * pct_f / 100.0, 2)
        return split
    by_type = allocation.get("aumBySchemeType") if isinstance(allocation.get("aumBySchemeType"), dict) else {}
    if not by_type:
        return split
    typed = {asset_bucket({"scheme_type": name}): float(value or 0) for name, value in by_type.items()}
    type_total = sum(typed.values()) or total
    for bucket, amount in typed.items():
        split[bucket]["aum_inr"] = round(amount, 2)
        split[bucket]["aum_pct"] = _pct(amount, type_total)
    return split


def build_derived_views(doc: dict[str, Any] | None) -> dict[str, Any]:
    """Holdings by category, asset split, top categories, XIRR, and rating labels."""
    doc = doc if isinstance(doc, dict) else {}
    holdings = [row for row in (doc.get("holdings") or []) if isinstance(row, dict)]
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    allocation = doc.get("allocation") if isinstance(doc.get("allocation"), dict) else {}

    total = sum(_aum(row) for row in holdings)
    if total <= 0:
        try:
            total = float(summary.get("aum_inr") or 0)
        except (TypeError, ValueError):
            total = 0.0

    by_category: dict[str, dict[str, Any]] = {}
    asset_amounts = {name: 0.0 for name in ("equity", "debt", "hybrid", "gold", "other")}
    slim_rows: list[dict[str, Any]] = []
    for row in holdings:
        amount = _aum(row)
        category = str(row.get("scheme_category") or "unknown").strip().lower() or "unknown"
        bucket = asset_bucket(row)
        asset_amounts[bucket] += amount
        block = by_category.setdefault(category, {"aum_inr": 0.0, "holdings": []})
        block["aum_inr"] = round(block["aum_inr"] + amount, 2)
        slim = {
            "scheme_name": str(row.get("scheme_name") or ""),
            "isin": str(row.get("isin") or ""),
            "scheme_category": category,
            "aum_inr": round(amount, 2),
            "aum_pct": _pct(amount, total),
            "xirr_pct": row.get("xirr_pct"),
            "rs_label": str(row.get("rs_label") or ""),
        }
        block["holdings"].append(slim)
        slim_rows.append(slim)

    if any(asset_amounts.values()):
        asset_split = {
            name: {"aum_inr": round(amount, 2), "aum_pct": _pct(amount, total)}
            for name, amount in asset_amounts.items()
        }
    else:
        asset_split = _split_from_allocation(allocation, total)

    for block in by_category.values():
        block["aum_pct"] = _pct(float(block["aum_inr"]), total)

    top_categories = sorted(
        (
            {"name": name, "aum_inr": block["aum_inr"], "aum_pct": block["aum_pct"]}
            for name, block in by_category.items()
        ),
        key=lambda row: float(row["aum_pct"]),
        reverse=True,
    )[:8]
    largest = sorted(slim_rows, key=lambda row: float(row["aum_pct"]), reverse=True)[:5]
    ratings = [
        {"scheme_name": row["scheme_name"], "isin": row["isin"], "rs_label": row["rs_label"]}
        for row in slim_rows
        if row.get("rs_label")
    ]
    return {
        "total_aum_inr": round(total, 2),
        "by_category": by_category,
        "asset_split": asset_split,
        "top_categories": top_categories,
        "largest_holdings": largest,
        "xirr_pct": summary.get("portfolio_xirr_pct"),
        "ratings": ratings,
    }


def balance_verdicts(derived: dict[str, Any] | None) -> list[str]:
    """Sentences the composer must use. Computed here so the model does not invent the mix."""
    derived = derived if isinstance(derived, dict) else {}
    split = derived.get("asset_split") if isinstance(derived.get("asset_split"), dict) else {}

    def pct(name: str) -> float:
        block = split.get(name) if isinstance(split.get(name), dict) else {}
        try:
            return float(block.get("aum_pct") or 0)
        except (TypeError, ValueError):
            return 0.0

    equity = pct("equity")
    debt = pct("debt")
    lines: list[str] = []
    if equity >= BALANCE_THRESHOLDS["equity_heavy_pct"] and debt < BALANCE_THRESHOLDS["little_debt_pct"]:
        lines.append(
            f"Equity is {equity:.0f}% of the book, so most of the result follows equity markets. "
            "That is a normal growth-leaning mix."
        )
    elif equity > 0 and debt >= BALANCE_THRESHOLDS["debt_balances_min_pct"]:
        lines.append(
            f"Equity is {equity:.0f}% of the book, which is the growth side. "
            f"Debt at {debt:.0f}% sits beside it and balances that."
        )

    for sector in derived.get("top_categories") or []:
        if not isinstance(sector, dict):
            continue
        try:
            share = float(sector.get("aum_pct") or 0)
        except (TypeError, ValueError):
            share = 0.0
        if share >= BALANCE_THRESHOLDS["sector_concentration_pct"]:
            name = str(sector.get("name") or "One category")
            lines.append(
                f"{name} is {share:.0f}% of the book. That is the main theme, "
                "and the rest is spread across the other categories."
            )
            break

    for row in derived.get("largest_holdings") or []:
        if not isinstance(row, dict):
            continue
        try:
            share = float(row.get("aum_pct") or 0)
        except (TypeError, ValueError):
            share = 0.0
        if share >= BALANCE_THRESHOLDS["single_fund_pct"]:
            name = str(row.get("scheme_name") or "One fund")
            lines.append(
                f"{name} is {share:.0f}% of the book, so this scheme carries most of the result. "
                "The other schemes still add a second line."
            )
            break
    return lines


def balance_verdicts_for_payload(data: dict[str, Any] | None) -> list[str]:
    data = data if isinstance(data, dict) else {}
    doc = {
        "holdings": data.get("holdings") or [],
        "summary": data.get("summary") or {},
        "allocation": data.get("allocation") or {},
    }
    return balance_verdicts(build_derived_views(doc))
