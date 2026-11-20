"""Flow card DATASETS: daily flows, market alignment, macro/sector context (math only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_insight.common.flows import FlowDay, history_path
from ai_insight.fii_dii_flow_narrative.aggregate import flow_period_totals
from ai_insight.market_driver_digest.macro_context import build_digest_datasets


def build_flow_datasets(ctx, history: list[FlowDay], market_facts: dict[str, Any]) -> dict[str, Any]:
    trading = ctx.trading_date.isoformat()
    limits: list[str] = []

    daily = _fii_dii_daily(history, history_path(ctx.config.data_dir), limits)
    aggregates = flow_period_totals(history, trading)
    flow_with_market = _flow_with_market(daily, market_facts.get("aligned_market_flows") or [])
    date_context = _flow_index_date_context(trading, market_facts, flow_with_market)

    macro_pack = build_digest_datasets(ctx)
    limits.extend(macro_pack.get("data_limitations") or [])

    if market_facts.get("flow_lagged"):
        limits.append(
            f"flow_lagged: NSE flow trade_date={market_facts.get('flow_trade_date')} "
            f"vs card trading_date={trading}"
        )
    if not daily:
        limits.append("fii_dii_daily: empty history")

    rank_week = macro_pack.get("sector_rank_week") or []
    indices_7d = macro_pack.get("sector_indices_7d") or []
    flow_history = _flow_history_highlights(daily, aggregates, market_facts)
    sector_ll = _sector_focus(rank_week, indices_7d)
    synthesis_hints = {
        "flow_history": flow_history,
        "sector_leaders_laggards": sector_ll,
        "macro_for_flows": _macro_flow_focus(macro_pack),
        "suggested_tensions": _suggested_tensions(flow_history, sector_ll, market_facts),
    }

    return {
        "fii_dii_net_history": daily,
        "fii_dii_net_note": (
            "Daily FII/DII figures are net purchase/sale in ₹ crore only. "
            "Historical rows do not include buy/sell breakdown; do not infer gross flows."
        ),
        "fii_dii_daily": daily,
        "flow_aggregates": aggregates,
        "flow_with_market": flow_with_market,
        "flow_index_date_context": date_context,
        "sector_indices_7d": indices_7d,
        "sector_rank_week": rank_week,
        "gsec_10y": macro_pack.get("gsec_10y") or {},
        "cpi_ytd": macro_pack.get("cpi_ytd") or {},
        "brent_usd": macro_pack.get("brent_usd") or {},
        "synthesis_hints": synthesis_hints,
        "data_limitations": list(dict.fromkeys(limits)),
    }


def _provisional_by_date(path: Path) -> dict[str, bool]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, bool] = {}
    for row in raw if isinstance(raw, list) else []:
        if not isinstance(row, dict):
            continue
        d = str(row.get("date") or "")
        if d:
            out[d] = bool(row.get("provisional"))
    return out


def _fii_dii_daily(history: list[FlowDay], path: Path, limits: list[str]) -> list[dict[str, Any]]:
    prov = _provisional_by_date(path)
    if prov and all(prov.values()):
        limits.append("fii_dii: all stored rows marked provisional")
    rows = [
        {
            "date": day.date,
            "fii_net_crore": day.fii_net,
            "dii_net_crore": day.dii_net,
            "provisional": prov.get(day.date, False),
        }
        for day in history
        if day.date
    ]
    return rows


def _flow_with_market(
    daily: list[dict[str, Any]],
    aligned: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_date = {str(row.get("date")): row for row in aligned if row.get("date")}
    out: list[dict[str, Any]] = []
    for row in daily:
        d = str(row.get("date"))
        market = by_date.get(d) or {}
        out.append(
            {
                "date": d,
                "fii_net_crore": row.get("fii_net_crore"),
                "dii_net_crore": row.get("dii_net_crore"),
                "nifty_pct": market.get("nifty_pct"),
                "nifty_close": market.get("nifty_close"),
                "banknifty_pct": None,
                "vix_pct": market.get("vix_pct"),
                "crude_pct": market.get("crude_pct"),
                "usdinr": market.get("usdinr"),
            }
        )
    return out


def _flow_index_date_context(
    trading: str,
    market_facts: dict[str, Any],
    flow_with_market: list[dict[str, Any]],
) -> dict[str, Any]:
    """Explicit dates for flow vs index comparisons (LLM must cite these in prose)."""
    flow_date = str(market_facts.get("flow_trade_date") or trading)
    by_date = {str(r.get("date")): r for r in flow_with_market if r.get("date")}

    def _nifty_row(d: str) -> dict[str, Any]:
        row = by_date.get(d) or {}
        return {
            "date": d,
            "nifty_change_pct": row.get("nifty_pct"),
            "nifty_close": row.get("nifty_close"),
            "fii_net_crore": row.get("fii_net_crore"),
            "dii_net_crore": row.get("dii_net_crore"),
        }

    card_nifty = market_facts.get("nifty_change_pct")
    nifty_on_card: dict[str, Any] = _nifty_row(trading)
    if card_nifty is not None and nifty_on_card.get("nifty_change_pct") is None:
        nifty_on_card["nifty_change_pct"] = card_nifty
        nifty_on_card["nifty_close"] = market_facts.get("nifty_close")

    return {
        "card_trading_date": trading,
        "flow_trade_date": flow_date,
        "flow_lagged": bool(market_facts.get("flow_lagged")),
        "nifty_on_card_trading_date": nifty_on_card,
        "nifty_on_flow_trade_date": _nifty_row(flow_date),
        "rule": (
            "When comparing index moves to flows, always name the calendar date (YYYY-MM-DD) "
            "for each figure — especially if flow_trade_date differs from card_trading_date."
        ),
    }


def _sign(value: float | None) -> int:
    if value is None:
        return 0
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _flow_history_highlights(
    daily: list[dict[str, Any]],
    aggregates: dict[str, Any],
    market_facts: dict[str, Any],
) -> dict[str, Any]:
    if not daily:
        return {}
    fii_buy = sum(1 for row in daily if (row.get("fii_net_crore") or 0) > 0)
    fii_sell = sum(1 for row in daily if (row.get("fii_net_crore") or 0) < 0)
    dii_buy = sum(1 for row in daily if (row.get("dii_net_crore") or 0) > 0)
    dii_sell = sum(1 for row in daily if (row.get("dii_net_crore") or 0) < 0)
    offset_sessions = 0
    for row in daily:
        if _sign(row.get("fii_net_crore")) and _sign(row.get("dii_net_crore")) and _sign(row.get("fii_net_crore")) != _sign(row.get("dii_net_crore")):
            offset_sessions += 1
    latest = daily[-1]
    return {
        "history_from": daily[0].get("date"),
        "history_through": latest.get("date"),
        "sessions": len(daily),
        "fii_net_buy_sessions": fii_buy,
        "fii_net_sell_sessions": fii_sell,
        "dii_net_buy_sessions": dii_buy,
        "dii_net_sell_sessions": dii_sell,
        "sessions_dii_offset_fii": offset_sessions,
        "latest_fii_net_crore": latest.get("fii_net_crore"),
        "latest_dii_net_crore": latest.get("dii_net_crore"),
        "latest_flow_date": latest.get("date"),
        "net_5d_fii": aggregates.get("net_5d_fii"),
        "net_5d_dii": aggregates.get("net_5d_dii"),
        "net_20d_fii": aggregates.get("net_20d_fii"),
        "net_20d_dii": aggregates.get("net_20d_dii"),
        "week_fii_net": aggregates.get("week_fii_net"),
        "week_dii_net": aggregates.get("week_dii_net"),
        "fii_streak_days": market_facts.get("fii_streak_days"),
        "dii_offsets_fii_today": market_facts.get("dii_offsets_fii"),
    }


def _sector_focus(rank_week: list[dict[str, Any]], indices_7d: list[dict[str, Any]]) -> dict[str, Any]:
    if not rank_week:
        return {}
    by_display = {str(row.get("display")): row for row in indices_7d if row.get("display")}

    def _with_daily(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for entry in entries:
            display = str(entry.get("display") or "")
            series = by_display.get(display) or {}
            daily = (series.get("daily") or [])[-3:]
            out.append(
                {
                    "display": display,
                    "week_change_pct": entry.get("week_change_pct"),
                    "last_3_sessions_daily": daily,
                }
            )
        return out

    sorted_rank = sorted(rank_week, key=lambda r: r.get("week_change_pct") or -1e9, reverse=True)
    leaders = sorted_rank[:3]
    laggards = list(reversed(sorted_rank[-3:])) if len(sorted_rank) >= 3 else sorted_rank[-3:]
    return {
        "week_leaders": _with_daily(leaders),
        "week_laggards": _with_daily(laggards),
    }


def _suggested_tensions(
    flow_history: dict[str, Any],
    sector_ll: dict[str, Any],
    market_facts: dict[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if flow_history:
        out["fii_dii_offset"] = {
            "fii_streak_days": market_facts.get("fii_streak_days") or flow_history.get("fii_streak_days"),
            "fii_net_buy_sessions": flow_history.get("fii_net_buy_sessions"),
            "fii_net_sell_sessions": flow_history.get("fii_net_sell_sessions"),
            "sessions_dii_offset_fii": flow_history.get("sessions_dii_offset_fii"),
            "net_5d_fii_crore": flow_history.get("net_5d_fii"),
            "net_5d_dii_crore": flow_history.get("net_5d_dii"),
        }
    leaders = sector_ll.get("week_leaders") or []
    laggards = sector_ll.get("week_laggards") or []
    if leaders or laggards:
        top = leaders[0] if leaders else {}
        bottom = laggards[0] if laggards else {}
        if not bottom and len(leaders) > 1:
            bottom = leaders[-1]
        if top.get("display") or bottom.get("display"):
            out["sector_divergence"] = {
                "week_leader_display": top.get("display"),
                "week_leader_pct": top.get("week_change_pct"),
                "week_laggard_display": bottom.get("display"),
                "week_laggard_pct": bottom.get("week_change_pct"),
            }
    return out


def _macro_flow_focus(macro_pack: dict[str, Any]) -> dict[str, Any]:
    gsec = macro_pack.get("gsec_10y") or {}
    brent = macro_pack.get("brent_usd") or {}
    cpi = macro_pack.get("cpi_ytd") or {}
    horizons = brent.get("horizons_pct") or {}
    return {
        "gsec_change_bp_7d": gsec.get("change_bp_7d"),
        "gsec_latest_date": gsec.get("latest_date"),
        "brent_7d_pct": horizons.get("7d"),
        "brent_latest_date": brent.get("latest_date"),
        "cpi_headline_yoy_pct": cpi.get("latest_yoy_pct"),
        "cpi_latest_month": cpi.get("latest_date"),
    }