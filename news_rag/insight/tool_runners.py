"""Registry tool adapters wrapping existing news_rag.tools and new insight fetchers."""

from __future__ import annotations

from typing import Any

from news_rag.insight.index_series import index_return_for_sector
from news_rag.insight.registry import ToolSpec, register
from news_rag.query_plan import DataNeed


def _ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    return ctx if isinstance(ctx, dict) else {}


def run_layered_news_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.tools import run_layered_news

    need = DataNeed(
        tool="sector_news",
        sector_name=str(ctx.get("sector_name") or ctx.get("subject") or ""),
        semantic_query=str(ctx.get("semantic_query") or ctx.get("subject") or ""),
        window_days=ctx.get("window_days"),
    )
    layer = str(ctx.get("layer") or "sector_news")
    if layer == "sector":
        layer = "sector_news"
    return run_layered_news(
        layer=layer,
        semantic_query=need.semantic_query or need.sector_name,
        question=str(ctx.get("question") or need.semantic_query or ""),
        entity_filters=[need.sector_name] if need.sector_name else None,
        window_days=ctx.get("window_days"),
        sentiment=str(ctx.get("sentiment") or "any"),
        date_from=ctx.get("date_from"),
        date_to=ctx.get("date_to"),
        min_impact=ctx.get("min_impact"),
        source=ctx.get("source"),
        direction=ctx.get("direction"),
    )


def run_sector_funds_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.tools import run_sector_funds

    q = str(ctx.get("question") or "")
    sector = str(ctx.get("sector_name") or ctx.get("subject") or "")
    need = DataNeed(
        tool="sector_funds",
        sector_name=sector,
        semantic_query=q or sector,
        top_n=int(ctx.get("top_n") or 8),
    )
    broad = bool(ctx.get("broad_sector_funds"))
    q_lower = q.lower()
    sector_keys = None
    min_w = 0.0
    if any(w in q_lower for w in ("highly", "impacted", "affected", "exposure")):
        broad = True
    if any(w in q_lower for w in ("automobile", "automotive", " auto ")):
        from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

        sector_keys = get_sector_fund_ranking_index().resolve_sector_keys(["Automobiles"])
        min_w = 8.0
        broad = True
    return run_sector_funds(
        need,
        direction=str(ctx.get("direction") or "any"),
        question=q,
        return_window=str(ctx.get("return_window") or ""),
        broad_pool=broad,
        sector_keys=sector_keys,
        min_weight_pct=min_w,
    )


def run_fund_composition_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.fund_search import get_fund_index

    isin = str(ctx.get("isin") or "").strip().upper()
    name = str(ctx.get("fund_name") or "").strip()
    idx = get_fund_index()
    detail = None
    if isin:
        detail = idx.get_fund_detail(isin)
    elif name:
        detail = idx.lookup_extracted_fund(name)
    if not detail:
        return {"ok": False, "error": "fund_not_found", "data": {}}
    sectors = detail.get("sectors") or {}
    holdings = detail.get("holdings") or {}
    sector_rows = sorted(
        [{"sector": k, "percentage": float(v)} for k, v in sectors.items()],
        key=lambda x: -x["percentage"],
    )
    holding_rows = []
    if isinstance(holdings, dict):
        for hname, meta in holdings.items():
            if isinstance(meta, dict):
                holding_rows.append(
                    {
                        "name": hname,
                        "percentage": float(meta.get("percentage") or 0),
                        "industry": meta.get("industry") or "",
                    }
                )
        holding_rows.sort(key=lambda x: -x["percentage"])
    return {
        "ok": True,
        "data": {
            "isin": detail.get("isin"),
            "fund_name": detail.get("fund_short_name") or detail.get("fund_name"),
            "category": detail.get("category"),
            "sectors": sector_rows,
            "holdings": holding_rows[:25],
            "as_on": detail.get("as_on"),
        },
    }


def run_fund_return_series_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from historical_data.nav_service import fund_return_series

    isin = str(ctx.get("isin") or "").strip().upper()
    window = int(ctx.get("window_days") or 180)
    if not isin:
        return {"ok": False, "error": "missing_isin", "data": {}}
    series = fund_return_series(isin, window_days=window)
    return {"ok": bool(series.get("success")), "data": series}


def run_index_series_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    sector = str(ctx.get("sector_name") or ctx.get("subject") or "")
    window = int(ctx.get("window_days") or 180)
    data = index_return_for_sector(sector, window_days=window)
    has_ticker = bool(data.get("yfinance_ticker"))
    has_pct = data.get("return_pct") is not None
    return {"ok": has_pct or has_ticker, "data": data}


def run_sector_news_signal_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    raw = run_layered_news_adapter(ctx)
    articles = []
    if raw.get("ok"):
        data = raw.get("data") or {}
        articles = data.get("articles") or data.get("rows") or []
    pos = neg = neu = 0
    impacts: list[float] = []
    themes: list[str] = []
    for art in articles:
        if not isinstance(art, dict):
            continue
        d = str(art.get("direction") or "").lower()
        if d == "positive":
            pos += 1
        elif d == "negative":
            neg += 1
        else:
            neu += 1
        try:
            impacts.append(float(art.get("max_impact") or art.get("impact") or 0))
        except (TypeError, ValueError):
            pass
        title = str(art.get("title") or "").strip()
        if title and len(themes) < 8:
            themes.append(title[:120])
    direction = "unknown"
    if pos > neg * 1.2:
        direction = "positive"
    elif neg > pos * 1.2:
        direction = "negative"
    elif pos or neg:
        direction = "mixed"
    avg_impact = round(sum(impacts) / len(impacts), 2) if impacts else None
    return {
        "ok": True,
        "data": {
            "direction": direction,
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count": neu,
            "avg_impact": avg_impact,
            "themes": themes,
            "article_count": len(articles),
            "articles": articles,
        },
    }


def run_fund_nav_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.fund_search import get_fund_index
    from news_rag.tools import run_fund_nav

    name = str(ctx.get("fund_name") or ctx.get("subject") or "")
    idx = get_fund_index()
    detail = idx.lookup_extracted_fund(name) if name else None
    if not detail and ctx.get("isin"):
        detail = idx.get_fund_detail(str(ctx["isin"]))
    if not detail:
        return {"ok": False, "error": "fund_not_found", "data": {}}
    need = DataNeed(tool="fund_nav", fund_ref=detail.get("isin") or "", top_n=5)
    return run_fund_nav(detail, need)


def run_market_pulse_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.market_pulse import run_market_pulse

    return run_market_pulse(
        str(ctx.get("question") or "market overview"),
        window_days=int(ctx.get("window_days") or 7),
    )


def build_default_registry() -> None:
    register(
        ToolSpec(
            name="layered_news",
            provides=frozenset({"entity_state_over_time", "news_drivers"}),
            description="Retrieve ranked news articles for a sector/theme from Qdrant (titles, scores, scraped text).",
            when_to_use="Sector health, drivers, or any question needing article-level evidence and quotes.",
            limits="Needs sector_name or semantic_query in context; respects date/impact filters from the ask API.",
            run=run_layered_news_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="sector_news_signal",
            provides=frozenset({"news_drivers"}),
            requires=frozenset(),
            description="Aggregate news direction (positive/negative/mixed), impact averages, and themes from layered news.",
            when_to_use="Lightweight news tone only; prefer layered_news when the answer must cite article text.",
            run=run_sector_news_signal_adapter,
            cost=2,
            fallbacks=["layered_news"],
        )
    )
    register(
        ToolSpec(
            name="sector_funds",
            provides=frozenset({"exposure_link", "peer_rank"}),
            description="Rank mutual funds by sector weight from holdings aggregate; optional NAV return window filter.",
            when_to_use="Which funds are exposed to a sector; impacted/affected/high weight questions. Sets fan-out fund list.",
            limits="For automobiles use Automobiles sector keys and min_weight_pct when question mentions impact/exposure.",
            run=run_sector_funds_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="fund_composition",
            provides=frozenset({"fund_composition", "fund_facts_holdings"}),
            requires=frozenset({"exposure_link"}),
            fan_out_over="fund",
            description="Latest sector and holding breakdown for one fund (ISIN) from extracted portfolio data.",
            when_to_use="Other top sectors, concentration, and attribution vs the topic sector.",
            run=run_fund_composition_adapter,
            cost=1,
        )
    )
    register(
        ToolSpec(
            name="fund_return_series",
            provides=frozenset({"return_series"}),
            requires=frozenset({"exposure_link"}),
            fan_out_over="fund",
            description="NAV return over window_days and monthly return series for one fund ISIN.",
            when_to_use="6-month patterns, positive/negative fund performance vs sector news.",
            run=run_fund_return_series_adapter,
            cost=1,
            fallbacks=["fund_nav"],
        )
    )
    register(
        ToolSpec(
            name="index_series",
            provides=frozenset({"benchmark"}),
            description="Sector NSE index total return via yfinance (nse_sector_indices_yfinance.json); Nifty 50 fallback.",
            when_to_use="benchmark facet — sector index performance over the brief window.",
            limits="May substitute broad index if sector ticker missing; short history tickers use max period.",
            run=run_index_series_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="fund_nav",
            provides=frozenset({"fund_facts_nav", "return_series"}),
            description="Point-in-time NAV facts and short return stats for a named fund.",
            when_to_use="Single-fund NAV questions or fallback when fund_return_series lacks ISIN.",
            run=run_fund_nav_adapter,
            cost=1,
        )
    )
    register(
        ToolSpec(
            name="market_pulse",
            provides=frozenset({"market_overview", "news_drivers"}),
            description="Broad market pulse summary across recent news layers.",
            when_to_use="Whole-market questions without a single sector subject.",
            run=run_market_pulse_adapter,
            cost=2,
        )
    )
