"""Strip per-holding contribution (pp) from composer-facing evidence while keeping it for reasoning."""

from __future__ import annotations

import copy
from typing import Any

_HOLDING_ATTR_KEYS = ("detractors", "contributors", "rows", "all_priced", "table")


def _display_holding_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": row.get("stock") or row.get("name"),
        "weight_pct": row.get("weight_pct"),
        "return_pct": row.get("return_pct"),
        "sector": row.get("sector") or row.get("industry"),
    }


def _internal_contribution_row(row: dict[str, Any]) -> dict[str, Any]:
    contrib = row.get("contribution_pct")
    if contrib is None:
        contrib = row.get("pct")
    out: dict[str, Any] = {"name": row.get("stock") or row.get("name")}
    if contrib is not None:
        out["contribution_pp"] = contrib
    return out


def split_attribution_for_composer(attr: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """User-visible attribution (weight + return) vs internal pp for ranking."""
    if not isinstance(attr, dict):
        return {}, {}
    display = copy.deepcopy(attr)
    internal: dict[str, Any] = {"detractors": [], "contributors": []}
    for key in _HOLDING_ATTR_KEYS:
        rows = display.get(key)
        if not isinstance(rows, list):
            continue
        cleaned: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            cleaned.append(_display_holding_row(row))
            if key in ("detractors", "contributors"):
                bucket = internal[key]
                bucket.append(_internal_contribution_row(row))
        display[key] = cleaned
    for key in ("fund_return_pct", "fund_return", "top_sector", "top_sector_weight_pct", "sector_weights", "priced_weight_pct"):
        if key in attr:
            display[key] = attr[key]
    if not internal["detractors"] and not internal["contributors"]:
        for row in attr.get("detractors") or []:
            if isinstance(row, dict):
                internal["detractors"].append(_internal_contribution_row(row))
        for row in attr.get("contributors") or []:
            if isinstance(row, dict):
                internal["contributors"].append(_internal_contribution_row(row))
    return display, internal


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _rollup_investor_summary(inv: dict[str, Any]) -> dict[str, Any]:
    """Portfolio totals for composer + grounding (from summary, pnl, or holdings)."""
    summary = inv.get("summary") if isinstance(inv.get("summary"), dict) else {}
    if _num(summary.get("aum_inr")) is not None and _num(summary.get("invested_inr")) is not None:
        return summary

    pnl = inv.get("pnl_summary") if isinstance(inv.get("pnl_summary"), dict) else {}
    if _num(pnl.get("currentValue")) is not None:
        return {
            "invested_inr": _num(pnl.get("netInvestment")),
            "aum_inr": _num(pnl.get("currentValue")),
            "gain_loss_inr": _num(pnl.get("gainLoss")) or _num(pnl.get("gainLossRounded")),
            "absolute_return_pct": _num(pnl.get("absoluteReturnPercent")),
            "portfolio_xirr_pct": _num(pnl.get("portfolioXirrPercent")) or _num(pnl.get("xirrPercent")),
        }

    holdings = [row for row in (inv.get("holdings") or []) if isinstance(row, dict)]
    if not holdings:
        return summary

    invested = aum = gain = 0.0
    have_inv = have_aum = have_gain = False
    for row in holdings:
        inv_amt = _num(row.get("invested_inr"))
        if inv_amt is not None:
            invested += inv_amt
            have_inv = True
        aum_amt = _num(row.get("aum_inr"))
        if aum_amt is not None:
            aum += aum_amt
            have_aum = True
        gl = _num(row.get("gain_loss_inr"))
        if gl is not None:
            gain += gl
            have_gain = True
    rolled: dict[str, Any] = dict(summary)
    if have_inv:
        rolled["invested_inr"] = round(invested, 2)
    if have_aum:
        rolled["aum_inr"] = round(aum, 2)
    if have_gain:
        rolled["gain_loss_inr"] = round(gain, 2)
    if have_inv and have_gain and invested:
        rolled["absolute_return_pct"] = round(100.0 * gain / invested, 2)
    return rolled


INVESTOR_HOLDINGS_DISPLAY_MAX = 8


def scheme_gain_loss_pct(row: dict[str, Any]) -> float | None:
    """Gain on invested from ₹ figures — omit -100% when the scheme has no current value (redeemed)."""
    inv = _num(row.get("invested_inr"))
    gl = _num(row.get("gain_loss_inr"))
    aum = _num(row.get("aum_inr"))
    if inv is None or inv <= 0 or gl is None:
        return None
    aum_val = float(aum or 0)
    if aum_val <= 0:
        # API often sends absolute_return_pct=-100 with aum_inr=0 after redemption; ₹ loss is enough.
        if abs(gl + inv) < max(1.0, 0.001 * inv):
            return None
        raw_abs = _num(row.get("absolute_return_pct"))
        if raw_abs is not None and abs(float(raw_abs) + 100.0) < 0.05:
            return None
    return round(100.0 * gl / inv, 2)


def sort_holdings_weakest_first(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(row: dict[str, Any]) -> tuple[int, float, float]:
        gl = _num(row.get("gain_loss_inr"))
        if gl is not None:
            return (0, gl, float(_num(row.get("xirr_pct")) or 999))
        return (1, float(_num(row.get("xirr_pct")) or 999), 0.0)

    return sorted(holdings, key=key)


def investor_holdings_for_display(
    holdings: list[dict[str, Any]],
    question: str,
    plan: Any,
    *,
    sort_weakest: bool = False,
) -> tuple[list[dict[str, Any]], int, bool]:
    """Table rows (capped), total scheme count, whether the table is truncated."""
    from news_rag.insight.investor_subject import question_asks_all_schemes_in_answer

    total = len(holdings)
    if sort_weakest:
        ordered = sort_holdings_weakest_first(holdings)
    else:
        ordered = sorted(holdings, key=lambda h: float(h.get("aum_inr") or 0), reverse=True)
    if question_asks_all_schemes_in_answer(question, plan) or total <= INVESTOR_HOLDINGS_DISPLAY_MAX:
        return ordered, total, False
    return ordered[:INVESTOR_HOLDINGS_DISPLAY_MAX], total, True


def _enrich_investor_computed_fields(inv: dict[str, Any]) -> None:
    """Pre-compute category weights and per-scheme facts for composer + grounding."""
    summary = inv.get("summary") if isinstance(inv.get("summary"), dict) else {}
    total = _num(summary.get("aum_inr")) or 0.0
    holdings = [row for row in (inv.get("holdings") or []) if isinstance(row, dict)]
    if not holdings or total <= 0:
        return

    by_category: dict[str, float] = {}
    scheme_rows: list[dict[str, Any]] = []
    for row in holdings:
        aum = _num(row.get("aum_inr"))
        if aum is None:
            continue
        weight = round(100.0 * aum / total, 2)
        cat = str(row.get("scheme_category") or "other").strip()
        by_category[cat] = by_category.get(cat, 0.0) + weight
        scheme_rows.append(
            {
                "scheme_name": row.get("scheme_name"),
                "category": cat,
                "weight_pct": weight,
                "value_inr": round(aum, 2),
                "invested_inr": _num(row.get("invested_inr")),
                "gain_loss_inr": _num(row.get("gain_loss_inr")),
                "xirr_pct": _num(row.get("xirr_pct")),
                "gain_on_invested_pct": scheme_gain_loss_pct(row),
            }
        )

    allocation = [
        {"category": name, "weight_pct": round(pct, 2)}
        for name, pct in sorted(by_category.items(), key=lambda item: item[1], reverse=True)
    ]
    inv["computed"] = {
        "total_value_inr": round(total, 2),
        "allocation_by_category": allocation,
        "holdings": scheme_rows,
    }


def sanitize_data_pack_for_composer(data_pack: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (sanitized pack, holding_contribution_pp_internal aggregated across funds)."""
    if not data_pack:
        return {}, {}
    out = copy.deepcopy(data_pack)
    investor = out.get("investor_portfolio")
    if isinstance(investor, dict):
        rolled = _rollup_investor_summary(investor)
        if rolled:
            investor["summary"] = rolled
        _enrich_investor_computed_fields(investor)
    merged_internal: dict[str, Any] = {"funds": []}
    for key, block in out.items():
        if not str(key).startswith("fund:") or not isinstance(block, dict):
            continue
        attr = block.get("attribution")
        if not isinstance(attr, dict):
            continue
        display_attr, internal = split_attribution_for_composer(attr)
        block["attribution"] = display_attr
        if internal.get("detractors") or internal.get("contributors"):
            merged_internal["funds"].append(
                {
                    "fund_key": key,
                    "detractors": internal.get("detractors") or [],
                    "contributors": internal.get("contributors") or [],
                }
            )
    if not merged_internal["funds"]:
        merged_internal = {}
    return out, merged_internal


def merge_holding_pp_into_performance(
    performance: dict[str, Any],
    from_pack: dict[str, Any],
) -> dict[str, Any]:
    perf = dict(performance or {})
    if from_pack:
        existing = perf.get("holding_contribution_pp_internal")
        if existing and isinstance(existing, dict) and "contributors" in existing:
            perf["holding_contribution_pp_internal"] = {
                "digest": existing,
                "attribution_blocks": from_pack,
            }
        else:
            perf["holding_contribution_pp_internal"] = from_pack
    perf.setdefault(
        "_composer_note",
        "holding_contribution_pp_internal is for ranking only — never quote per-holding percentage points; "
        "use DISPLAY holdings_move_table (weight + holding return). Percentage points are OK for vs benchmark and category avg.",
    )
    # Drop legacy digest keys that tempted the model to paste pp per stock.
    for bucket in ("top_contributors", "top_detractors"):
        rows = perf.get(bucket)
        if not isinstance(rows, list):
            continue
        perf[bucket] = [
            _display_holding_row(r) for r in rows if isinstance(r, dict)
        ]
    return perf
