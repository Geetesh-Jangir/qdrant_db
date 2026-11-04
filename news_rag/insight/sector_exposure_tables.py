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
    asked = {str(x).lower() for x in (plan.asked_facts or [])}
    has_return = "returns" in asked or any(x.startswith("return:") for x in asked)
    if asked and not has_return:
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
    if not by_fund:
        return ""
    lines = [f"| Fund | {window} return |", "| --- | --- |"]
    for name in names:
        val = by_fund.get(name) or "not available"
        lines.append(f"| {_short_fund_name(name)} | {val} |")
    return "\n".join(lines)


def _fund_data_from_results(
    results: list[dict[str, Any]] | None,
    data_pack: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    by_fund: dict[str, dict[str, Any]] = {}
    for row in results or []:
        if not row.get("ok") or row.get("tool") != "get_fund_data":
            continue
        fund = str(row.get("fund") or "").strip()
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        if fund and data:
            by_fund[fund] = data
    if isinstance(data_pack, dict):
        for key, val in data_pack.items():
            if not str(key).startswith("fund:") or not isinstance(val, dict):
                continue
            name = str(val.get("fund_name") or val.get("fund_short_name") or key.split(":", 1)[-1]).strip()
            if name:
                by_fund[name] = val
    return by_fund


def _investor_holdings_rating_rows(data_pack: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """RS label/score from get_investor_portfolio when get_fund_data was not fan-out."""
    pack = data_pack or {}
    investor = pack.get("investor_portfolio") if isinstance(pack.get("investor_portfolio"), dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for row in investor.get("holdings") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("scheme_name") or "").strip()
        if not name:
            continue
        out[name] = {
            "rs_rating": {
                "label": row.get("rs_label"),
                "final_score": row.get("rs_score"),
            }
        }
    return out


def _all_holdings_metric_spec(plan: ExecutionPlan) -> tuple[str, str]:
    asked = [str(x) for x in (plan.asked_facts or [])]
    fields = {str(x) for x in (plan.asked_fields or [])}
    if "holding_rs_labels" in fields:
        return "rs_rating", ""
    for pref in ("rs_rating", "nav", "aum", "expense", "exit_load"):
        if pref in asked:
            return pref, ""
    for token in asked:
        if token.startswith("return:"):
            return "return", token.split(":", 1)[1].upper()
    if "returns" in asked:
        window = "1M"
        for call in plan.tool_calls or []:
            if call.tool == "get_fund_data":
                wins = (call.arguments or {}).get("windows") or []
                if wins:
                    window = str(wins[0]).upper()
                    break
        return "return", window
    return "", ""


def _metric_cell(data: dict[str, Any], metric: str, window: str) -> str:
    snap = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
    if metric == "rs_rating":
        rating = data.get("rs_rating") if isinstance(data.get("rs_rating"), dict) else {}
        label = rating.get("label") or rating.get("rs_label") or snap.get("rs_label")
        score = rating.get("final_score")
        if score is None:
            score = rating.get("score") or rating.get("rs_score") or snap.get("rs_score")
        if label or score is not None:
            parts = [str(part) for part in (label, score) if part not in (None, "")]
            return " ".join(parts)
        return "not available"
    if metric == "nav":
        nav = snap.get("nav")
        if nav is not None:
            return f"₹{float(nav):,.2f}" if isinstance(nav, (int, float)) else str(nav)
        return "not available"
    if metric == "aum":
        if snap.get("aum") is not None:
            return f"Rs {float(snap['aum']):,.2f} crore"
        return "not available"
    if metric == "expense":
        expense = snap.get("expense_ratio") if isinstance(snap.get("expense_ratio"), dict) else {}
        if expense.get("regular") is not None:
            return f"{float(expense['regular']):.2f}%"
        return "not available"
    if metric == "exit_load":
        summary = str(snap.get("exit_load_summary") or "").strip()
        return summary or "not available"
    if metric == "return" and window:
        rets = snap.get("returns") if isinstance(snap.get("returns"), dict) else {}
        val = rets.get(window) or rets.get(window.lower())
        if val is not None:
            return f"{float(val):+.2f}%"
        return "not available"
    return "not available"


def render_all_holdings_metric_table(
    plan: ExecutionPlan,
    results: list[dict[str, Any]] | None = None,
    memory: dict[str, Any] | None = None,
    *,
    data_pack: dict[str, Any] | None = None,
) -> str:
    if str(plan.holding_scope or "") != "all_holdings":
        return ""
    metric, window = _all_holdings_metric_spec(plan)
    if not metric:
        return ""
    headers = {
        "rs_rating": "RS rating",
        "nav": "NAV",
        "aum": "AUM",
        "expense": "Expense ratio",
        "exit_load": "Exit load",
        "return": f"{window} return" if window else "Return",
    }
    col = headers.get(metric, metric)
    by_fund = _fund_data_from_results(results, data_pack)
    if metric == "rs_rating":
        for name, payload in _investor_holdings_rating_rows(data_pack).items():
            merged = dict(by_fund.get(name) or {})
            merged.update(payload)
            by_fund[name] = merged
    names = owned_holding_names(memory) or list(plan.funds or [])
    if not names:
        return ""
    lines = [f"| Fund | {col} |", "| --- | --- |"]
    for name in names:
        data = by_fund.get(name)
        if not data:
            for key, val in by_fund.items():
                if key.lower() == name.lower() or name.lower() in key.lower() or key.lower() in name.lower():
                    data = val
                    break
        cell = _metric_cell(data or {}, metric, window) if data else "not available"
        lines.append(f"| {_short_fund_name(name)} | {cell} |")
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
