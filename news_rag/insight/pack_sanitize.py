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
    for key in ("explained_pct", "unexplained_pct", "fund_return_pct", "fund_return", "top_sector", "top_sector_weight_pct", "sector_weights", "priced_weight_pct", "missing_price"):
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


def sanitize_data_pack_for_composer(data_pack: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (sanitized pack, holding_contribution_pp_internal aggregated across funds)."""
    if not data_pack:
        return {}, {}
    out = copy.deepcopy(data_pack)
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
