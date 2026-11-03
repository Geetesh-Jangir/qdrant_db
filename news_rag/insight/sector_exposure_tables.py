"""Deterministic tables for all-holdings returns and sector weights (from tool results)."""

from __future__ import annotations

from typing import Any

from news_rag.insight.contracts import ExecutionPlan
from news_rag.insight.memory.fund_context import owned_holding_names


def _short_fund_name(name: str) -> str:
    text = str(name or "").strip()
    for cut in (" - Regular Plan - Growth", " - Growth", " - Direct Plan - Growth"):
        if cut in text:
            return text.split(cut)[0].strip()
    return text


def _sector_needle(plan: ExecutionPlan) -> str:
    for raw in plan.sectors or []:
        token = str(raw or "").strip().lower()
        if token:
            return token
    for call in plan.tool_calls or []:
        if call.tool == "get_portfolio_data":
            find = str((call.arguments or {}).get("find") or "").strip().lower()
            if find:
                return find
    return ""


def _sector_weight_pct(sectors: list[Any], needle: str) -> float | None:
    if not needle:
        return None
    key = needle.lower()
    bankish = "bank" in key
    total = 0.0
    found = False
    for row in sectors or []:
        if not isinstance(row, dict):
            continue
        label = str(
            row.get("sector")
            or row.get("sector_label")
            or row.get("name")
            or row.get("sector_name")
            or ""
        ).lower()
        if not label:
            continue
        if bankish and "bank" not in label:
            continue
        if not bankish and key not in label and label not in key:
            continue
        try:
            pct = float(
                row.get("percentage")
                or row.get("weight_pct")
                or row.get("allocation_pct")
                or row.get("weight")
                or 0
            )
        except (TypeError, ValueError):
            pct = 0.0
        total += pct
        found = True
    if not found:
        return 0.0
    return round(total, 2)


def render_all_holdings_return_table(
    plan: ExecutionPlan,
    results: list[dict[str, Any]] | None,
    memory: dict[str, Any] | None,
) -> str:
    if str(plan.holding_scope or "") != "all_holdings":
        return ""
    window = "1M"
    for call in plan.tool_calls or []:
        if call.tool == "get_fund_data":
            wins = (call.arguments or {}).get("windows") or []
            if wins:
                window = str(wins[0]).upper()
                break
    by_fund: dict[str, str] = {}
    for row in results or []:
        if not row.get("ok") or row.get("tool") != "get_fund_data":
            continue
        fund = str(row.get("fund") or "").strip()
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        snap = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        rets = snap.get("returns") if isinstance(snap.get("returns"), dict) else {}
        val = rets.get(window) or rets.get(window.lower())
        if val is not None:
            by_fund[fund] = f"{float(val):+.2f}%"
    names = owned_holding_names(memory) or list(plan.funds or [])
    if not names:
        return ""
    lines = [f"| Fund | {window} return |", "| --- | --- |"]
    for name in names:
        val = by_fund.get(name) or "—"
        lines.append(f"| {_short_fund_name(name)} | {val} |")
    return "\n".join(lines)


def render_all_holdings_sector_table(
    plan: ExecutionPlan,
    results: list[dict[str, Any]] | None,
    memory: dict[str, Any] | None,
) -> str:
    needle = _sector_needle(plan)
    if not needle and str(plan.planner_portfolio_slice or "") not in ("sectors", "both"):
        return ""
    if str(plan.holding_scope or "") != "all_holdings" and len(plan.funds or []) < 2:
        return ""
    by_fund: dict[str, float | None] = {}
    for row in results or []:
        if not row.get("ok") or row.get("tool") != "get_portfolio_data":
            continue
        fund = str(row.get("fund") or "").strip()
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        sectors = list(data.get("sectors") or [])
        by_fund[fund] = _sector_weight_pct(sectors, needle or "bank")
    names = owned_holding_names(memory) or list(plan.funds or [])
    if not names:
        return ""
    label = needle.title() if needle else "Sector"
    lines = [f"| Fund | {label} weight (%) |", "| --- | --- |"]
    for name in names:
        weight = by_fund.get(name)
        if weight is None:
            cell = "—"
        else:
            cell = f"{weight:.2f}%" if weight else "0%"
        lines.append(f"| {_short_fund_name(name)} | {cell} |")
    return "\n".join(lines)
