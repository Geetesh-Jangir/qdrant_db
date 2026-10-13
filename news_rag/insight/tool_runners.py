"""Registry tool adapters.

Each adapter takes the shared gather context (a dict) and returns {"ok": bool, "data": {...}}.
Context keys the adapters read (all optional):
  question, sector_name, sector_keys, drivers, driver_direction, direction, window_days,
  return_window, top_n, fund_names, stock_name, semantic_query, date/impact filters, and the
  evidence collected so far: _articles, _funds, _composition.
"""

from __future__ import annotations

import re
from typing import Any

from news_rag.insight.index_series import index_return_for_sector
from news_rag.insight.registry import ToolSpec, register
from news_rag.query_plan import DataNeed

_IMPACT_RE = re.compile(r"impact\w*|affect\w*|exposed|exposure|heav\w+|highly|most", re.I)


def _s(ctx: dict[str, Any], key: str, default: str = "") -> str:
    return str(ctx.get(key) or default).strip()


def _fail(error: str) -> dict[str, Any]:
    return {"ok": False, "error": error, "data": {}}


def _resolve_fund_detail(ctx: dict[str, Any]) -> dict[str, Any] | None:
    from news_rag.fund_search import get_fund_index

    idx = get_fund_index()
    isin = _s(ctx, "isin").upper()
    if isin:
        detail = idx.get_fund_detail(isin)
        if detail:
            return detail
    names = ctx.get("fund_names") or []
    name = _s(ctx, "fund_name") or (str(names[0]) if names else "")
    if name:
        detail, _ambiguous, _close = idx.lookup_extracted_fund(name=name)
        return detail
    return None


# ---------------------------------------------------------------------------
# News tools
# ---------------------------------------------------------------------------


def _insight_body_char_limit() -> int:
    from news_rag.config import get_settings

    s = get_settings()
    return max(int(getattr(s, "insight_llm_article_chars", 3500)), int(s.snippet_chars))


def run_layered_news_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.tools import run_layered_news

    sector = _s(ctx, "sector_name")
    semantic = _s(ctx, "semantic_query") or sector or _s(ctx, "question")[:200]
    layer = _s(ctx, "layer", "sector_news")
    if layer == "sector":
        layer = "sector_news"
    return run_layered_news(
        layer=layer,
        semantic_query=semantic,
        question=_s(ctx, "question") or semantic,
        entity_filters=[sector] if sector else None,
        window_days=ctx.get("window_days"),
        sentiment=_s(ctx, "sentiment", "any"),
        date_from=ctx.get("date_from"),
        date_to=ctx.get("date_to"),
        min_impact=ctx.get("min_impact"),
        source=ctx.get("source"),
        direction=ctx.get("direction") if ctx.get("direction") in ("positive", "negative") else None,
        body_char_limit=_insight_body_char_limit(),
    )


def run_macro_news_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.macro_news_enhanced import run_macro_news_enhanced

    return run_macro_news_enhanced(
        _s(ctx, "question"),
        semantic_query=_s(ctx, "semantic_query"),
        window_days=ctx.get("window_days"),
    )


def run_market_pulse_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.market_pulse import run_market_pulse

    return run_market_pulse(
        _s(ctx, "question", "market overview"),
        window_days=int(ctx.get("window_days") or 7),
        body_char_limit=_insight_body_char_limit(),
    )


def run_sector_news_signal_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    raw = run_layered_news_adapter(ctx)
    articles: list[dict[str, Any]] = []
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
    return {
        "ok": True,
        "data": {
            "direction": direction,
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count": neu,
            "avg_impact": round(sum(impacts) / len(impacts), 2) if impacts else None,
            "themes": themes,
            "article_count": len(articles),
            "articles": articles,
        },
    }


def run_holding_news_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.holdings_market import fetch_dedicated_holding_news

    name = _s(ctx, "stock_name")
    if not name:
        return _fail("stock_name_missing")
    arts = fetch_dedicated_holding_news(
        name,
        _s(ctx, "question"),
        window_days=int(ctx.get("window_days") or 30),
        limit=6,
    )
    return {"ok": bool(arts), "data": {"articles": arts, "stock": name}, "error": "" if arts else "no_news"}


def run_fund_portfolio_news_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.tools import run_fund_portfolio_news

    detail = _resolve_fund_detail(ctx)
    if not detail:
        return _fail("fund_not_found")
    need = DataNeed(tool="fund_portfolio_news", top_n=8, window_days=int(ctx.get("window_days") or 30))
    return run_fund_portfolio_news(detail, need, question=_s(ctx, "question"))


# ---------------------------------------------------------------------------
# Sector / fund ranking tools
# ---------------------------------------------------------------------------


def run_sector_funds_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.tools import run_sector_funds

    q = _s(ctx, "question")
    sector = _s(ctx, "sector_name")
    keys = list(ctx.get("sector_keys") or [])
    wants_impact = bool(_IMPACT_RE.search(q))
    need = DataNeed(tool="sector_funds", sector_name=sector, semantic_query=q or sector, top_n=int(ctx.get("top_n") or 8))
    # "highly impacted" = meaningful weight in the sector. Step the floor down if the sector is thin.
    floors = (8.0, 5.0, 2.0, 0.0) if wants_impact else (0.0,)
    primary_only = [keys[0]] if (wants_impact and keys) else keys
    result: dict[str, Any] = {}
    for floor in floors:
        result = run_sector_funds(
            need,
            direction=_s(ctx, "direction", "any"),
            question=q,
            return_window=_s(ctx, "return_window"),
            broad_pool=wants_impact,
            sector_keys=primary_only or None,
            min_weight_pct=floor,
        )
        rows = ((result.get("data") or {}).get("rankings")) or []
        if len(rows) >= 3:
            break
    return result


def run_screen_funds_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.tools import run_screen_funds

    return run_screen_funds(
        sector_name=_s(ctx, "sector_name"),
        stock_name=_s(ctx, "stock_name"),
        direction=_s(ctx, "direction", "any"),
        return_window=_s(ctx, "return_window") or None,
        top_n=int(ctx.get("top_n") or 5),
        question=_s(ctx, "question"),
    )


def _rule_sector_picks(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """Sectors the macro rule table expects to gain/lose for the named driver and direction."""
    from news_rag.macro_impact_map import macro_impact_entry
    from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

    idx = get_sector_fund_ranking_index()
    picks: list[dict[str, str]] = []
    for driver in ctx.get("drivers") or []:
        entry = macro_impact_entry(driver, direction=_s(ctx, "driver_direction") or None)
        for row in (entry or {}).get("sectors") or []:
            sign = row.get("expected_sign")
            if sign not in ("positive", "negative") or row.get("impact_type") == "indirect":
                continue
            keys = idx.resolve_sector_keys([str(row.get("sector") or "")])
            if not keys:
                continue
            picks.append(
                {
                    "name": keys[0],
                    "direction": sign,
                    "reason": str(row.get("transmission") or "").strip(),
                    "source": "rule_table",
                }
            )
    return picks


def _infer_driver_direction(ctx: dict[str, Any], articles: list[dict[str, Any]]) -> str:
    """When the question names a driver but not up/down, read the articles."""
    existing = _s(ctx, "driver_direction")
    if existing:
        return existing
    blob = " ".join(
        f"{a.get('title') or ''} {a.get('snippet') or ''} {a.get('body') or ''}"
        for a in (articles or [])[:8]
        if isinstance(a, dict)
    )
    blob = (blob + " " + _s(ctx, "question")).lower()
    if re.search(r"\b(surg\w*|spik\w*|climb\w*|higher|rose|risen|back at \$|above \$|per barrel)\b", blob):
        return "up"
    if re.search(r"\b(oil prices? (?:fall|drop|slump)|crude (?:fell|dropped|slumped)|lower crude)\b", blob):
        return "down"
    return ""


def _merge_sector_picks(
    news: list[dict[str, str]],
    rules: list[dict[str, str]],
    asked: str,
) -> list[dict[str, str]]:
    """Keep the asked side. Rule-table sectors fill gaps the news picker missed."""
    asked = (asked or "any").strip().lower()
    merged: dict[str, dict[str, str]] = {}
    for row in list(rules) + list(news):
        name = str(row.get("name") or "").strip()
        direction = str(row.get("direction") or "").strip().lower()
        if not name or direction not in ("positive", "negative"):
            continue
        if asked in ("positive", "negative") and direction != asked:
            continue
        prev = merged.get(name)
        if prev is None or (row.get("source") != "rule_table" and prev.get("source") == "rule_table"):
            merged[name] = row
    return list(merged.values())


def run_affected_sectors_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    """Which sectors does this news help or hurt? News decides; the rule table fills the other side."""
    from news_rag.affected_sectors import pick_affected_sectors
    from news_rag.tools import _articles_for_affected_question

    articles = ctx.get("_articles") or []
    if not articles:
        return _fail("needs_news_first")
    inferred = _infer_driver_direction(ctx, articles)
    if inferred and not _s(ctx, "driver_direction"):
        ctx["driver_direction"] = inferred
    rules = _rule_sector_picks(ctx)
    hint = ""
    if rules:
        helped = ", ".join(r["name"] for r in rules if r["direction"] == "positive")
        hurt = ", ".join(r["name"] for r in rules if r["direction"] == "negative")
        hint = (
            f"\n\nTypical effect of this driver (rule table, use only if the articles support it): "
            f"helps [{helped or 'none'}]; hurts [{hurt or 'none'}]."
        )
    packed = _articles_for_affected_question(_s(ctx, "question"), articles)
    asked = _s(ctx, "direction", "any")
    picks: list[dict[str, str]] = []
    try:
        picks = pick_affected_sectors(
            question=_s(ctx, "question") + hint,
            articles=packed,
            direction=asked,
        )
    except Exception:
        picks = []
    picks = _merge_sector_picks(picks, rules, asked)
    source = "news+rules" if rules else "news"
    if picks and not any(p.get("source") != "rule_table" for p in picks):
        source = "rule_table"
    return {
        "ok": bool(picks),
        "error": "" if picks else "no_sector_matched",
        "data": {
            "sector_picks": picks,
            "source": source,
            "driver_direction": _s(ctx, "driver_direction"),
            "sectors_positive": [p["name"] for p in picks if p.get("direction") == "positive"],
            "sectors_negative": [p["name"] for p in picks if p.get("direction") == "negative"],
        },
    }


def run_driver_affected_funds_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    """Funds with the most weight in the sectors the news helps/hurts (exposure, not return sign)."""
    from news_rag.tools import run_sector_funds

    picks = ctx.get("_sector_picks") or []
    if not picks:
        return _fail("needs_sector_picks_first")
    q = _s(ctx, "question")
    asked = _s(ctx, "direction", "any")
    chosen: list[dict[str, str]] = []
    for group in ("negative", "positive"):
        if asked in ("positive", "negative") and group != asked:
            continue
        chosen += [p for p in picks if p.get("direction") == group][:2]
    rows_by_isin: dict[str, dict[str, Any]] = {}
    for pick in chosen:
        need = DataNeed(tool="sector_funds", sector_name=pick["name"], semantic_query=q, top_n=4)
        for floor in (8.0, 4.0, 2.0):
            res = run_sector_funds(
                need,
                direction="any",
                question=q,
                return_window=_s(ctx, "return_window"),
                broad_pool=True,
                sector_keys=[pick["name"]],
                min_weight_pct=floor,
            )
            rows = ((res.get("data") or {}).get("rankings")) or []
            if rows:
                break
        for row in rows[:3]:
            isin = str(row.get("isin") or "")
            if not isin:
                continue
            tagged = {
                **row,
                "affected_sector": pick["name"],
                "affected_direction": pick.get("direction") or "any",
                "sector_reason": pick.get("reason") or "",
            }
            prev = rows_by_isin.get(isin)
            if prev is None or float(row.get("sector_weight_pct") or 0) > float(prev.get("sector_weight_pct") or 0):
                rows_by_isin[isin] = tagged
    # Keep both sides visible: the strongest few on each side, then order by exposure.
    by_side: dict[str, list[dict[str, Any]]] = {"negative": [], "positive": []}
    for row in sorted(rows_by_isin.values(), key=lambda r: -float(r.get("sector_weight_pct") or 0)):
        by_side.setdefault(row.get("affected_direction") or "positive", []).append(row)
    per_side = 3 if asked == "any" else 6
    ranked = sorted(
        by_side["negative"][:per_side] + by_side["positive"][:per_side],
        key=lambda r: -float(r.get("sector_weight_pct") or 0),
    )
    cap = int(ctx.get("top_n") or 6)
    return {
        "ok": bool(ranked),
        "error": "" if ranked else "no_funds_in_affected_sectors",
        "data": {
            "rankings": ranked[:cap],
            "sectors": [p["name"] for p in chosen],
            "sector_picks": chosen,
        },
    }


# ---------------------------------------------------------------------------
# Per-fund tools (fan out over shortlisted funds)
# ---------------------------------------------------------------------------


def run_fund_composition_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    detail = _resolve_fund_detail(ctx)
    if not detail:
        return _fail("fund_not_found")
    sectors = detail.get("sectors") or {}
    holdings = detail.get("holdings") or {}
    sector_rows = sorted(
        [{"sector": k, "percentage": float(v)} for k, v in sectors.items()],
        key=lambda x: -x["percentage"],
    )
    holding_rows: list[dict[str, Any]] = []
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

    isin = _s(ctx, "isin").upper()
    if not isin:
        return _fail("missing_isin")
    series = fund_return_series(isin, window_days=int(ctx.get("window_days") or 180))
    return {"ok": bool(series.get("success")), "data": series, "error": "" if series.get("success") else "nav_unavailable"}


def run_fund_nav_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.tools import run_fund_nav

    detail = _resolve_fund_detail(ctx)
    if not detail:
        return _fail("fund_not_found")
    need = DataNeed(tool="fund_nav", fund_ref=detail.get("isin") or "", top_n=5)
    return run_fund_nav(detail, need)


def run_trace_relationships_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.relationships import trace_relationships

    isin = _s(ctx, "isin").upper()
    comp = (ctx.get("_composition") or {}).get(isin) or {}
    driver = (ctx.get("drivers") or [""])[0] or _s(ctx, "sector_name")
    target = _s(ctx, "sector_name")
    if not driver:
        return _fail("driver_missing")
    data = trace_relationships(
        driver=driver.replace("_", " "),
        target=target,
        holdings_rows=comp.get("holdings") or [],
        sector_rows=comp.get("sectors") or [],
        articles=ctx.get("_articles") or [],
        fund_name=_s(ctx, "fund_name"),
    )
    return {"ok": True, "data": {**data, "isin": isin}}


def run_sector_alignment_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.sector_alignment import run_sector_holding_alignment

    detail = _resolve_fund_detail(ctx)
    if not detail:
        return _fail("fund_not_found")
    res = run_sector_holding_alignment(
        detail,
        question=_s(ctx, "question"),
        top_n=5,
        sector_name=_s(ctx, "sector_name"),
        return_window=_s(ctx, "return_window"),
        window_days=int(ctx.get("window_days") or 30),
    )
    if isinstance(res.get("data"), dict):
        res["data"].setdefault("isin", _s(ctx, "isin"))
    return res


def run_compare_funds_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.fund_search import get_fund_index
    from news_rag.tools import run_compare_funds

    idx = get_fund_index()
    details = []
    for name in ctx.get("fund_names") or []:
        d, _ambiguous, _close = idx.lookup_extracted_fund(name=str(name))
        if d:
            details.append(d)
    if len(details) < 2:
        return _fail("need_two_funds")
    return run_compare_funds(details, compare_on="all", return_window=_s(ctx, "return_window", "1M"))


# ---------------------------------------------------------------------------
# Market data tools
# ---------------------------------------------------------------------------


def run_index_series_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    sector = _s(ctx, "sector_name")
    data = index_return_for_sector(sector, window_days=int(ctx.get("window_days") or 180))
    return {
        "ok": data.get("return_pct") is not None or bool(data.get("yfinance_ticker")),
        "data": data,
    }


def run_macro_sector_impact_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.macro_impact_map import run_macro_sector_impact

    entries: list[dict[str, Any]] = []
    for driver in ctx.get("drivers") or []:
        res = run_macro_sector_impact(driver=driver, direction=_s(ctx, "driver_direction"))
        if res.get("ok") and isinstance(res.get("data"), dict):
            entries.append(res["data"])
    if not entries:
        return _fail("unknown_driver")
    return {"ok": True, "data": {"drivers": entries}}


def run_metals_spot_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.tools import run_metals_spot

    return run_metals_spot()


def run_stock_snapshot_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.tools import run_stock_snapshot

    name = _s(ctx, "stock_name")
    if not name:
        return _fail("stock_name_missing")
    return run_stock_snapshot(DataNeed(tool="stock_snapshot", stock_name=name))


def run_stock_holders_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.stock_fund_ranking import funds_holding_stock

    name = _s(ctx, "stock_name")
    if not name:
        return _fail("stock_name_missing")
    payload = funds_holding_stock(name, limit=10)
    return {"ok": bool(payload.get("funds") or payload.get("fund_count")), "data": payload}


def run_sector_holdings_adapter(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.tools import run_sector_holdings_tool

    sector = _s(ctx, "sector_name")
    if not sector:
        return _fail("sector_missing")
    return run_sector_holdings_tool(sector_name=sector, top_n=int(ctx.get("top_n") or 5))


# ---------------------------------------------------------------------------
# Registration — the descriptions below are what the planner reads.
# ---------------------------------------------------------------------------


def _has(key: str):
    return lambda ctx: bool(ctx.get(key))


def _driver_without_sector(ctx: dict[str, Any]) -> bool:
    return bool(ctx.get("drivers")) and not ctx.get("sector_name") and not ctx.get("fund_names")


def _named_fund_no_sector(ctx: dict[str, Any]) -> bool:
    return bool(ctx.get("fund_names")) and not ctx.get("sector_name")


def build_default_registry() -> None:
    register(
        ToolSpec(
            name="layered_news",
            provides=frozenset({"entity_state_over_time", "news_drivers", "forward_view"}),
            description="Ranked news articles for a sector/theme from the news archive: title, cleaned body, direction, impact 1-5, event type.",
            when_to_use="Sector health, what is driving a sector, any question that needs article-level evidence to quote.",
            avoid_when="The question is about one named fund (use fund_portfolio_news) or only about market-wide macro (use macro_news_enhanced / market_pulse).",
            args=(("sector_name", "canonical sector label"), ("window_days", "look-back window")),
            limits="Needs a sector or search phrase. Honors date/impact/source filters from the API request.",
            run=run_layered_news_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="macro_news_enhanced",
            provides=frozenset({"news_drivers"}),
            description="News on one macro driver (RBI, crude, rupee, inflation, FPI flows), clustered into themes with sector tags.",
            when_to_use="The question names a macro driver and no sector, e.g. 'which funds are affected if crude rises'.",
            avoid_when="A sector or a fund is the subject; the driver is only context.",
            args=(("semantic_query", "driver keywords, not the whole sentence"),),
            applies=_driver_without_sector,
            run=run_macro_news_adapter,
            cost=2,
            fallbacks=["layered_news"],
        )
    )
    register(
        ToolSpec(
            name="sector_news_signal",
            provides=frozenset({"news_drivers"}),
            description="Aggregate tone only: positive/negative/mixed counts, average impact, top themes.",
            when_to_use="A cheap tone read when article text will not be quoted.",
            avoid_when="The answer must explain WHY — use layered_news.",
            run=run_sector_news_signal_adapter,
            cost=2,
            fallbacks=["layered_news"],
        )
    )
    register(
        ToolSpec(
            name="fund_portfolio_news",
            provides=frozenset({"news_drivers", "holding_drivers"}),
            description="Layered news for ONE named fund: its top holdings first, then its top sectors, then macro.",
            when_to_use="The user names a specific mutual fund and asks how it is doing or why it moved.",
            avoid_when="The question is about a sector or a driver across many funds.",
            applies=_named_fund_no_sector,
            run=run_fund_portfolio_news_adapter,
            cost=3,
            fallbacks=["layered_news"],
        )
    )
    register(
        ToolSpec(
            name="holding_news",
            provides=frozenset({"holding_drivers"}),
            description="Recent articles explaining one company's share-price move (earnings, orders, management, demand).",
            when_to_use="The user asks about a named stock, or why a holding rose or fell.",
            avoid_when="No company is named.",
            args=(("stock_name", "company name"),),
            applies=_has("stock_name"),
            run=run_holding_news_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="market_pulse",
            provides=frozenset({"market_overview", "news_drivers"}),
            description="Market-wide snapshot: the biggest macro themes in recent news, clustered, with the sectors they touch.",
            when_to_use="'What is happening in the market', 'what should I watch'.",
            avoid_when="The question names a sector, fund, stock or one macro driver.",
            run=run_market_pulse_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="sector_funds",
            provides=frozenset({"exposure_link", "peer_rank"}),
            description="Mutual funds ranked by their weight in a sector, from the holdings aggregate (weights, sector breakdown, latest returns).",
            when_to_use="Which funds are exposed to / impacted by a SECTOR. Seeds the per-fund tools.",
            avoid_when="The user named a driver (rates, crude) with no sector — use driver_affected_funds. Not for AMC/category screens — use screen_funds.",
            args=(("sector_keys", "canonical sector keys"), ("question", "used to detect 'highly impacted'")),
            limits="'Highly impacted' keeps funds with >= 8% in the sector, relaxing to 5/2/0% if too few.",
            run=run_sector_funds_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="driver_affected_funds",
            provides=frozenset({"exposure_link"}),
            requires=frozenset({"sector_impact_direction"}),
            description="Funds with the most weight in the sectors the news helps or hurts (picked by affected_sectors), tagged with the sector and the reason.",
            when_to_use="'Which funds are affected by crude / RBI / rupee / this news' — a driver, not a sector, is the subject.",
            avoid_when="A sector is named — sector_funds is more precise.",
            args=(("direction", "positive = who benefits, negative = who is hurt, any = both"),),
            applies=_driver_without_sector,
            run=run_driver_affected_funds_adapter,
            cost=3,
            fallbacks=["sector_funds"],
        )
    )
    register(
        ToolSpec(
            name="screen_funds",
            provides=frozenset({"fund_screen", "exposure_link"}),
            description="Filter the fund catalog by sector, category, AMC or stock and keep funds whose window return matches the direction.",
            when_to_use="'Best performing large-cap funds', 'funds from AMC X', 'funds holding stock Y with positive returns'.",
            avoid_when="The user wants impact of news on funds (use sector_funds / driver_affected_funds).",
            args=(("question", "category / AMC / stock are parsed from it"), ("direction", "positive|negative|any"), ("return_window", "1W|1M|3M|1Y")),
            run=run_screen_funds_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="affected_sectors",
            provides=frozenset({"sector_impact_direction"}),
            requires=frozenset({"news_drivers"}),
            description="An LLM reads the articles (with the macro rule table as a hint) and names which sectors the news helps and which it hurts, with a one-line reason each. Falls back to the rule table if the news is silent.",
            when_to_use="'Which sectors benefit / are hurt', and the first step of any driver-led 'which funds are affected' question. Needs news first.",
            avoid_when="The sector is already known; the news reader already tags sector direction for it.",
            run=run_affected_sectors_adapter,
            cost=3,
        )
    )
    register(
        ToolSpec(
            name="fund_composition",
            provides=frozenset({"fund_composition", "fund_facts_holdings"}),
            fan_out_over="fund",
            description="Latest sector weights and top holdings for one fund (ISIN).",
            when_to_use="After a fund shortlist exists: shows what ELSE the fund holds, so a sector effect can be separated from other drivers.",
            run=run_fund_composition_adapter,
            cost=1,
        )
    )
    register(
        ToolSpec(
            name="fund_return_series",
            provides=frozenset({"return_series"}),
            fan_out_over="fund",
            description="NAV return over the window and the monthly return series for one fund.",
            when_to_use="'Patterns over the last 6 months', or to check whether a fund moved with the sector news.",
            run=run_fund_return_series_adapter,
            cost=1,
            fallbacks=["fund_nav"],
        )
    )
    register(
        ToolSpec(
            name="trace_relationships",
            provides=frozenset({"relationship_trace"}),
            fan_out_over="fund",
            fan_out_cap=3,
            description="Direct links (the fund holds it / has sector weight) versus indirect links (names that co-occur with the driver in news).",
            when_to_use="'Is the fund really exposed to crude / RBI, or only indirectly?'",
            avoid_when="No driver or sector to trace.",
            run=run_trace_relationships_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="sector_alignment",
            provides=frozenset({"fund_vs_index"}),
            fan_out_over="fund",
            fan_out_cap=3,
            description="Compares a fund's sector holdings' returns with the matching NSE sector index and Nifty 50.",
            when_to_use="'Is the fund moving with the sector or against it?'",
            avoid_when="You only need the sector index return — use index_series.",
            run=run_sector_alignment_adapter,
            cost=3,
        )
    )
    register(
        ToolSpec(
            name="index_series",
            provides=frozenset({"benchmark"}),
            description="Sector index return over the window (NSE sector index via yfinance; Nifty 50 when the sector index has no history).",
            when_to_use="Any sector question: gives the market's own verdict next to the news.",
            limits="Labelled as a proxy when it falls back to Nifty 50.",
            run=run_index_series_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="macro_sector_impact",
            provides=frozenset({"macro_driver_map"}),
            description="Rule table: for a macro driver and direction (e.g. rbi_repo + hike) which sectors usually gain or lose, and why.",
            when_to_use="A macro driver is named. Gives the expected winners/losers to compare with the news.",
            args=(("drivers", "driver ids"), ("driver_direction", "hike|cut|up|down|weaken|...")),
            applies=_has("drivers"),
            run=run_macro_sector_impact_adapter,
            cost=1,
        )
    )
    register(
        ToolSpec(
            name="fund_nav",
            provides=frozenset({"fund_facts_nav", "return_series"}),
            description="Latest NAV, 1W/1M/3M/1Y returns, 52-week range, benchmark and scheme type for one named fund.",
            when_to_use="The user names a fund. Also the fallback when a per-fund return series is missing.",
            avoid_when="You are not sure which fund — do not guess.",
            applies=_has("fund_names"),
            run=run_fund_nav_adapter,
            cost=1,
        )
    )
    register(
        ToolSpec(
            name="compare_funds",
            provides=frozenset({"peer_compare"}),
            description="Side-by-side NAV, sector and holdings comparison for two or more named funds.",
            when_to_use="Only when the user asks to compare and names the funds.",
            applies=lambda ctx: len(ctx.get("fund_names") or []) >= 2,
            run=run_compare_funds_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="stock_holders",
            provides=frozenset({"stock_holders"}),
            description="Mutual funds that hold a given stock, with weights.",
            when_to_use="'Which funds hold HDFC Bank / Maruti?'",
            applies=_has("stock_name"),
            run=run_stock_holders_adapter,
            cost=2,
        )
    )
    register(
        ToolSpec(
            name="stock_snapshot",
            provides=frozenset({"stock_price"}),
            description="Price snapshot and 1W/1M returns for one stock.",
            when_to_use="A company is named and price context helps.",
            applies=_has("stock_name"),
            run=run_stock_snapshot_adapter,
            cost=1,
        )
    )
    register(
        ToolSpec(
            name="sector_holdings",
            provides=frozenset({"sector_holdings"}),
            description="Representative listed companies in a sector.",
            when_to_use="'Name two companies in the banking sector' — no fund is named.",
            applies=_has("sector_name"),
            run=run_sector_holdings_adapter,
            cost=1,
        )
    )
    register(
        ToolSpec(
            name="metals_spot",
            provides=frozenset({"commodity_spot"}),
            description="Latest gold and silver spot prices and recent moves.",
            when_to_use="Gold or silver is the subject.",
            run=run_metals_spot_adapter,
            cost=1,
        )
    )
