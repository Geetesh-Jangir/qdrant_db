"""Facts blocks for prompts: market history, flows, news map."""

from __future__ import annotations

from typing import Any

from ai_insight.common.flows import cumulative, history_path, load_flow_history
from ai_insight.common.market_data import build_aligned_table, get_index_history
from ai_insight.fii_dii_flow_narrative.aggregate import flow_period_totals


def editorial_context(ctx) -> dict[str, Any]:
    """How to read prices vs news timing for prompts."""
    trading = ctx.trading_date.isoformat()
    return {
        "trading_date": trading,
        "news_note": (
            "News ingest usually completes after the cash close (around 17:10 IST). "
            "Articles cover the rolling week — not every story is dated trading_date. "
            "Use article dates and themes to explain moves. "
            "Never say the feed is empty if ARTICLES are attached."
        ),
        "article_count_hint": "See article_count in facts when present.",
        "flow_note": (
            "NSE FII/DII figures can lag the trading_date by one or more sessions. "
            "When flow_lagged is true, state the flow_trade_date once, then discuss themes from the articles."
        ),
    }


def market_numbers(ctx) -> dict[str, Any]:
    from ai_insight.common.market_data import get_nifty, get_series

    trading = ctx.trading_date.isoformat()
    nifty = get_nifty(trading, config=ctx.config)
    facts: dict[str, Any] = {}
    if nifty.status == "ok" and nifty.data:
        facts.update(nifty.data)
        facts["nifty_change_pct"] = nifty.data.get("change_pct")
    vix = get_series("Macro - India VIX", trading)
    if vix.status == "ok" and vix.data:
        facts["vix_change_pct"] = vix.data.get("change_pct")
        facts["vix_close"] = vix.data.get("close")
    usd = get_series("Macro - Rupee / USD", trading)
    if usd.status == "ok" and usd.data:
        facts["usdinr"] = usd.data.get("close")
    crude = get_series("Macro - Crude Oil", trading)
    if crude.status == "ok" and crude.data:
        facts["crude_change_pct"] = crude.data.get("change_pct")
    hist = get_index_history("Macro - Nifty 50", days=20, config=ctx.config)
    if hist.get("status") == "ok":
        facts["nifty_history"] = hist
        facts["range_5d"] = [row.get("close") for row in (hist.get("daily") or [])[-5:]]
    bank = get_index_history("Macro - Bank Nifty", days=7, config=ctx.config)
    if bank.get("status") == "ok":
        facts["banknifty_history"] = bank
    path = history_path(ctx.config.data_dir)
    flows = load_flow_history(path)
    facts["flow_totals"] = flow_period_totals(flows, trading)
    facts["fii_net_5d"] = cumulative(flows, 5, "fii_net")
    facts["dii_net_5d"] = cumulative(flows, 5, "dii_net")
    facts["aligned_market_flows"] = build_aligned_table(trading, flows, config=ctx.config)
    facts.update(editorial_context(ctx))
    return facts


def news_map_block(clusters: list[Any]) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    for cluster in clusters:
        entities: dict[str, dict[str, Any]] = {}
        for row in cluster.articles:
            entity = row.get("entity") or {}
            name = str(entity.get("name") or "")
            if not name:
                continue
            bucket = entities.setdefault(
                name,
                {"name": name, "type": entity.get("type"), "direction": entity.get("direction"), "impact": entity.get("impact"), "count": 0},
            )
            bucket["count"] += 1
        mapped.append(
            {
                "cluster_id": cluster.cluster_id,
                "label": cluster.label,
                "weight": cluster.weight,
                "avg_impact": cluster.avg_impact,
                "entities": list(entities.values()),
            }
        )
    return mapped