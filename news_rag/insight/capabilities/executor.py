"""Capability executor — runs six capability tools in parallel with deadline enforcement.

Each capability delegates to existing layer_tools / tool_runners adapters.
The executor validates args, respects fan-out caps, and uses the TTL cache.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from news_rag.config import get_settings
from news_rag.insight.capabilities.cache import get_capability_cache
from news_rag.insight.capabilities.catalog import validate_capability_args
from news_rag.insight.contracts import ToolCall, RequestTelemetry

logger = logging.getLogger(__name__)


def _capability_cache_key(
    tool: str,
    fund_name: str,
    args: dict[str, Any],
    ctx: dict[str, Any],
) -> str:
    """Cache keys must reflect modules, portfolio shape, and manager question focus."""
    if tool == "get_portfolio_data":
        sections = ",".join(sorted(args.get("sections") or ["holdings", "sectors"]))
        top_n = int(args.get("top_n") or 3)
        find = str(args.get("find") or "").strip()
        return f"{fund_name}|sections={sections}|top_n={top_n}|find={find}"
    modules = ",".join(args.get("modules") or [])
    key = f"{fund_name}|{modules}"
    if "managers" in (args.get("modules") or []):
        from news_rag.insight.manager_view import infer_manager_roster_focus

        focus = infer_manager_roster_focus(str(ctx.get("question") or ""))
        key = f"{key}|mgr_focus={focus}"
    if "attribution" in (args.get("modules") or []):
        key = f"{key}|attr_w={args.get('window_days', 30)}|attr_n={args.get('top_n', 3)}"
    if "return_series" in (args.get("modules") or []):
        key = f"{key}|series_w={args.get('window_days', 180)}"
    if "drawdown" in (args.get("modules") or []):
        periods = ",".join(args.get("periods") or [])
        key = f"{key}|dd={periods}|cat={bool(args.get('include_category'))}"
    if "risk" in (args.get("modules") or []):
        key = f"{key}|risk=1"
    return key


def _run_get_fund_data(fund_name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Delegate to existing fund snapshot / return_series / attribution tools."""
    from news_rag.insight.registry import ensure_registry

    ensure_registry()
    results: dict[str, Any] = {"fund_name": fund_name}
    modules = args.get("modules", ["snapshot"])

    if "snapshot" in modules:
        from news_rag.insight.layer_tools import run_fund_snapshot
        snap_ctx = {
            **ctx,
            "fund_name": fund_name,
            "fund_names": [fund_name],
            "windows": args.get("windows") or ["1W", "1M", "3M", "6M", "1Y"],
        }
        snap = run_fund_snapshot(snap_ctx)
        if snap.get("ok"):
            results["snapshot"] = snap.get("data", {})

    if "return_series" in modules:
        from news_rag.insight.tool_runners import _resolve_fund_detail
        detail = _resolve_fund_detail({**ctx, "fund_name": fund_name, "fund_names": [fund_name]})
        if detail:
            from news_rag.insight.tool_runners import run_fund_return_series_adapter
            series_ctx = {**ctx, "fund_name": fund_name, "fund_names": [fund_name], "window_days": args.get("window_days", 180)}
            series = run_fund_return_series_adapter(series_ctx)
            if series.get("ok"):
                results["return_series"] = series.get("data", {})

    if "attribution" in modules:
        from news_rag.insight.layer_tools import run_fund_attribution_tool
        attr_ctx = {**ctx, "fund_name": fund_name, "fund_names": [fund_name],
                    "window_days": args.get("window_days", 30), "top_n": args.get("top_n", 3)}
        attr = run_fund_attribution_tool(attr_ctx)
        if attr.get("ok"):
            results["attribution"] = attr.get("data", {})

    if "snapshot" in modules or "vs_benchmark" in modules:
        from news_rag.fund_search import resolve_fund_for_query
        from news_rag.fund_rupeestop_metrics import (
            fetch_vs_benchmark,
            merge_fund_insight_metrics,
        )

        detail, _amb, _close = resolve_fund_for_query(fund_name)
        isin = str((detail or {}).get("isin") or "").strip()
        vs = fetch_vs_benchmark(isin) if isin else None
        insights = merge_fund_insight_metrics(detail, vs_benchmark=vs)
        if insights:
            results["fund_insights"] = insights
            if vs:
                results["vs_benchmark"] = vs

    if "drawdown" in modules:
        from news_rag.fund_drawdown import load_fund_drawdown

        try:
            results["drawdown"] = load_fund_drawdown(
                fund_name,
                list(args.get("periods") or []),
                str(ctx.get("question") or ""),
                include_category=bool(args.get("include_category")),
            )
        except Exception as exc:
            logger.warning("drawdown load failed for %s: %s", fund_name, exc)

    if "risk" in modules:
        from news_rag.fund_risk import load_fund_risk

        try:
            results["risk"] = load_fund_risk(fund_name, str(ctx.get("question") or ""))
        except Exception as exc:
            logger.warning("risk load failed for %s: %s", fund_name, exc)

    if "managers" in modules:
        from news_rag.fund_search import fetch_fund_managers_for_query

        mgr = fetch_fund_managers_for_query(fund_name)
        if not mgr:
            mgr = fetch_fund_managers_for_query(str(ctx.get("question") or ""))
        if mgr:
            from news_rag.insight.manager_view import enrich_manager_payload

            results["managers"] = enrich_manager_payload(
                mgr, str(ctx.get("question") or fund_name)
            )

    return {"ok": bool(results.keys() - {"fund_name"}), "data": results}


def _run_get_portfolio_data(fund_name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.insight.layer_tools import run_fund_portfolio
    top_n = args.get("top_n", 3)
    find = args.get("find", "")
    include_count = "count" in args.get("sections", [])
    sections = list(args.get("sections") or ["holdings", "sectors"])
    portfolio_ctx = {
        **ctx,
        "fund_name": fund_name,
        "fund_names": [fund_name],
        "top_n_holdings": top_n,
        "top_n_sectors": min(top_n, 10),
        "portfolio_sections": sections,
        "include_count": include_count,
        "find": find,
    }
    return run_fund_portfolio(portfolio_ctx)


def _run_compare_funds(fund_names: list[str], args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.insight.tool_runners import run_compare_funds_adapter
    compare_ctx = {
        **ctx,
        "fund_names": fund_names,
        "overlap": args.get("mode") in ("overlap", "both"),
        "drawdown_periods": args.get("drawdown_periods") or [],
    }
    return run_compare_funds_adapter(compare_ctx)


def _portfolio_for_fund_news(ctx: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Holdings/sectors from Wave 1 or a quick portfolio fetch for layered fund news."""
    holdings: list[dict[str, Any]] = []
    sectors: list[dict[str, Any]] = []
    fund_name = ""
    for r in ctx.get("wave1_results") or []:
        if r.get("tool") != "get_portfolio_data" or not r.get("ok"):
            continue
        data = r.get("data") if isinstance(r.get("data"), dict) else {}
        holdings = list(data.get("holdings") or [])
        sectors = list(data.get("sectors") or [])
        fund_name = str(r.get("fund") or data.get("fund_name") or "").strip()
        break

    names = list(ctx.get("fund_names") or [])
    if not fund_name and names:
        fund_name = str(names[0]).strip()

    if holdings or sectors:
        return holdings, sectors, fund_name

    if not fund_name:
        return [], [], ""

    from news_rag.fund_search import extract_top_holdings, extract_top_sectors, resolve_fund_for_query

    detail, _amb, _close = resolve_fund_for_query(fund_name)
    if not detail:
        return [], [], fund_name
    fund_name = str(
        detail.get("fund_short_name") or detail.get("fund_name") or fund_name
    ).strip()
    holdings = extract_top_holdings(detail, limit=10)
    sectors = extract_top_sectors(detail, limit=8)
    return holdings, sectors, fund_name


def _group_layered_articles(articles: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, str]]]]:
    layer_map = {"holding": "holdings", "sector": "sectors", "macro": "macro"}
    grouped: dict[str, dict[str, list[dict[str, str]]]] = {}
    for row in articles:
        if not isinstance(row, dict):
            continue
        scope = layer_map.get(str(row.get("_news_layer") or ""), "macro")
        entity = str(row.get("_news_source_label") or row.get("source") or "general").strip()
        title = str(row.get("title") or "").strip()
        text = str(row.get("text") or row.get("summary") or "")[:900]
        grouped.setdefault(scope, {}).setdefault(entity, []).append(
            {
                "title": title,
                "headline": title,
                "text": text,
                "summary": text,
                "url": str(row.get("url") or ""),
                "source": str(row.get("source") or ""),
                "published_at": str(row.get("published_at") or ""),
                "sentiment": str(row.get("sentiment") or ""),
                "max_impact": row.get("max_impact"),
                "direction": row.get("direction"),
            }
        )
    return grouped


def _run_search_financial_news(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Market/stock news fanout, or layered holdings+sectors+macro for named funds."""
    from news_rag.insight.fund_news_scope import infer_fund_news_layers, layers_to_retrieval_keys
    from news_rag.insight.news_fanout import NewsTarget, grouped_news, search_targets

    scope = str(args.get("scope") or "market").lower()
    question = str(ctx.get("question") or "")
    topics = [str(t).strip() for t in (args.get("topics") or []) if str(t).strip()]
    subject = _news_subject(question) if scope == "market" and not topics else ""
    if subject:
        topics = [subject]
    top_n = int(args.get("top_n") or 3)
    if subject:
        top_n = max(top_n, 8)
    window_days = int(args.get("window_days") or ctx.get("window_days") or 14)
    direction = args.get("direction")
    if direction == "any":
        direction = None

    use_fund_layers = scope in ("all", "fund", "portfolio") or (
        scope in ("holdings", "sectors", "macro")
        and bool(ctx.get("fund_names"))
    )
    if use_fund_layers:
        holdings, sectors, fund_name = _portfolio_for_fund_news(ctx)
        if holdings or sectors:
            from news_rag.fund_portfolio_news import retrieve_layered_fund_news

            if scope in ("all", "fund", "portfolio"):
                layers = layers_to_retrieval_keys(infer_fund_news_layers(question))
            elif scope == "holdings":
                layers = frozenset({"holding"})
            elif scope == "sectors":
                layers = frozenset({"sector"})
            else:
                layers = frozenset({"macro"})

            articles = retrieve_layered_fund_news(
                holdings=holdings,
                sectors=sectors,
                question=question,
                fund_name=fund_name,
                window_days=window_days,
                query_log=ctx.get("query_log"),
                layers=layers,
            )
            grouped = _group_layered_articles(articles)
            return {
                "ok": bool(articles),
                "scope": scope if scope != "fund" else "all",
                "data": {
                    "grouped": grouped,
                    "articles": articles,
                    "article_count": len(articles),
                    "fund_name": fund_name,
                    "layers": sorted(layers),
                },
            }

    targets = _news_search_targets(
        topics,
        scope=scope,
        top_n=top_n,
        window_days=window_days,
        direction=direction,
    )

    search_targets(targets)
    grouped = grouped_news(targets)
    articles = [art for t in targets for art in (t.articles or [])]
    return {
        "ok": bool(articles),
        "scope": scope,
        "data": {"grouped": grouped, "articles": articles, "article_count": len(articles)},
    }


_GENERIC_NEWS_SUBJECTS = frozenset(
    {
        "market",
        "the market",
        "markets",
        "the markets",
        "stock market",
        "the stock market",
        "india",
        "indian market",
    }
)


def _news_subject(question: str) -> str:
    """The named subject in 'news about HDFC Bank', or empty for a market-wide question."""
    import re

    match = re.search(
        r"\b(?:news|headlines?)\s+(?:about|on|regarding|for)\s+(.+)",
        question or "",
        re.I,
    )
    if not match:
        return ""
    subject = match.group(1).strip(" ?.!")
    subject = re.sub(r"\s+in\s+the\s+market$", "", subject, flags=re.I).strip()
    if len(subject) < 2 or subject.lower() in _GENERIC_NEWS_SUBJECTS:
        return ""
    return subject


_TOPIC_KEYS = {
    "bank": "banks",
    "banks": "banks",
    "banking": "banks",
}


def _news_search_targets(
    topics: list[Any],
    *,
    scope: str,
    top_n: int,
    window_days: int,
    direction: str | None,
) -> list[Any]:
    """One search per distinct topic. Banking and Banks are the same search, with the asked count."""
    from news_rag.insight.news_fanout import NewsTarget

    if scope == "market" and not topics:
        from news_rag.insight.market_news import market_scope_entities

        entities = market_scope_entities(source_kind="layer1", topics=[], top_n=top_n)
    elif topics:
        entities = []
        seen: set[str] = set()
        for topic in topics:
            name = str(topic).strip()
            if not name:
                continue
            key = _TOPIC_KEYS.get(name.lower(), name.lower())
            if key in seen:
                continue
            seen.add(key)
            entities.append((name, f"{name} India market news"))
    else:
        entities = [(scope, f"{scope} India financial news")]

    limit = max(int(top_n or 8), 1)
    return [
        NewsTarget(
            scope=scope,
            entity=entity,
            query=query,
            window_days=window_days,
            direction=direction,
            limit=limit,
            chars=2500,
            required=True,
        )
        for entity, query in entities
    ]


def _run_get_macro_news(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Two fresh articles for every named macro topic. No cache."""
    from news_pipeline.config import MACRO_ENTITIES
    from news_rag.insight.fund_display import complete_sentences, strip_publisher
    from news_rag.macro_news_cache import _article_text, _search_macro_parameters

    window_days = int(args.get("window_days") or ctx.get("window_days") or 30)
    specs = [(str(row["name"]), str(row["query"])) for row in MACRO_ENTITIES]
    clusters: list[dict[str, Any]] = []
    for group in _search_macro_parameters(specs, window_days):
        articles: list[dict[str, str]] = []
        for art in list(group.get("articles") or [])[:2]:
            if not isinstance(art, dict):
                continue
            body = complete_sentences(_article_text(art))
            title = strip_publisher(str(art.get("title") or art.get("headline") or ""))
            if not title or not body:
                continue
            articles.append(
                {
                    "title": title,
                    "summary": body,
                    "published_at": str(art.get("published_at") or art.get("date") or ""),
                }
            )
        if articles:
            clusters.append({"label": group.get("label") or "", "articles": articles})
    total = sum(len(cluster["articles"]) for cluster in clusters)
    return {
        "ok": bool(clusters),
        "data": {"window_days": window_days, "clusters": clusters, "article_total": total},
    }


def _run_screen_funds_by_exposure(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Delegate to sector_funds / driver_affected_funds / screen_funds."""
    question = str(ctx.get("question") or "")
    from news_rag.fund_rating_screen import asks_rating_list, run_rating_list

    rating_question = question if asks_rating_list(question) else ""
    if not rating_question:
        focus = str(args.get("focus_question") or "").strip()
        if focus and asks_rating_list(focus):
            rating_question = focus
    if args.get("rating_screen") or rating_question:
        result = run_rating_list(rating_question or question)
        return {"ok": bool(result.get("success")), "data": result}

    from news_rag.insight.registry import ensure_registry, get_tool

    ensure_registry()
    sector = args.get("sector", "")
    driver = args.get("driver", "")
    direction = args.get("direction", "any")

    if driver:
        from news_rag.insight.tool_runners import (
            infer_exposure_direction,
            resolve_driver_direction,
            _rule_sector_picks,
            run_driver_affected_funds_adapter,
        )

        driver_id = str(driver).strip()
        plan_drivers = ctx.get("drivers") or []
        if not plan_drivers:
            plan_drivers = [driver_id]

        screen_ctx = {
            **ctx,
            "drivers": plan_drivers if isinstance(plan_drivers, list) else [driver_id],
            "driver_direction": str(ctx.get("driver_direction") or "").strip(),
            "direction": direction if direction in ("positive", "negative") else str(ctx.get("direction") or "any"),
            "top_n": args.get("top_n", 5),
        }
        # Allow planner/slot_router to pass macro move separately from exposure side.
        move_arg = str(args.get("driver_move") or args.get("driver_direction") or "").strip().lower()
        if move_arg in ("up", "down", "tighten", "ease", "weaken", "strengthen"):
            screen_ctx["driver_direction"] = move_arg
        elif str(direction).lower() in ("up", "down", "tighten", "ease", "weaken", "strengthen"):
            screen_ctx["driver_direction"] = str(direction).lower()

        resolved_move = resolve_driver_direction(screen_ctx, ctx.get("_articles") or [])
        if resolved_move:
            screen_ctx["driver_direction"] = resolved_move

        screen_ctx["direction"] = infer_exposure_direction(screen_ctx)

        picks = _rule_sector_picks(screen_ctx)
        if not picks:
            macro_spec = get_tool("macro_sector_impact")
            if macro_spec and macro_spec.run:
                macro_res = macro_spec.run(screen_ctx)
                if macro_res.get("ok"):
                    picks = _rule_sector_picks(screen_ctx)
        if not picks and resolved_move:
            # Re-apply canonical move after macro_sector_impact may have filled driver_direction.
            screen_ctx["driver_direction"] = resolved_move
            picks = _rule_sector_picks(screen_ctx)
        if not picks:
            from news_rag.macro_impact_map import macro_impact_entry, normalize_driver

            diag = macro_impact_entry(
                normalize_driver(driver_id),
                direction=resolved_move or None,
            )
            sectors_n = len((diag or {}).get("sectors") or [])
            return {
                "ok": False,
                "error": "no_sectors_for_driver",
                "data": {
                    "driver": driver_id,
                    "driver_direction": resolved_move,
                    "macro_sectors_in_map": sectors_n,
                },
            }

        screen_ctx["_sector_picks"] = picks
        return run_driver_affected_funds_adapter(screen_ctx)
    if sector:
        from news_rag.tools import screen_hints_from_question

        q = str(ctx.get("question") or "")
        # "Banking funds" and "large cap funds" are scheme categories. Keep the
        # sector-weight tool for exposure asks that do not name a category.
        if not screen_hints_from_question(q).get("category"):
            spec = get_tool("sector_funds")
            if spec and spec.run:
                screen_ctx = {
                    **ctx,
                    "sector_name": sector,
                    "sector_keys": [sector],
                    "top_n": args.get("top_n", 5),
                }
                return spec.run(screen_ctx)
    spec = get_tool("screen_funds")
    if spec and spec.run:
        from news_rag.tools import infer_return_window

        q = str(args.get("focus_question") or ctx.get("question") or "")
        screen_ctx = {
            **ctx,
            "sector_name": sector or ctx.get("sector_name") or "",
            "top_n": args.get("top_n", 5),
            "direction": args.get("direction") or ctx.get("direction") or "any",
            "return_window": args.get("return_window") or infer_return_window(q),
            "random_sample": bool(args.get("random_sample")),
            "require_positive_1y": bool(args.get("require_positive_1y")),
        }
        return spec.run(screen_ctx)
    return {"ok": False, "error": "no_screen_tool", "data": {}}


def _run_get_market_snapshot(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Delegate to index_return / sector_ranking / macro_series / metals_spot."""
    from news_rag.insight.layer_tools import (
        run_index_return_tool,
        run_macro_series_tool,
        run_sector_ranking_tool,
    )
    from news_rag.insight.registry import ensure_registry, get_tool

    ensure_registry()
    modules = args.get("modules", ["index_return"])
    combined: dict[str, Any] = {}

    if "index_return" in modules:
        idx_ctx = {**ctx, "index": args.get("index", "nifty50"), "window_days": args.get("window_days", 30)}
        res = run_index_return_tool(idx_ctx)
        if res.get("ok"):
            combined["index_return"] = res.get("data", {})

    if "sector_ranking" in modules:
        rank_ctx = {**ctx, "window_days": args.get("window_days", 30), "top_n": args.get("top_n", 6)}
        res = run_sector_ranking_tool(rank_ctx)
        if res.get("ok"):
            combined["sector_ranking"] = res.get("data", {})

    if "macro_series" in modules:
        macro_ctx = {**ctx, "series": args.get("series", ["crude", "usdinr"]), "window_days": args.get("window_days", 30)}
        res = run_macro_series_tool(macro_ctx)
        if res.get("ok"):
            combined["macro_series"] = res.get("data", {})

    if "metals_spot" in modules:
        spec = get_tool("metals_spot")
        if spec and spec.run:
            res = spec.run(ctx)
            if res.get("ok"):
                combined["metals_spot"] = res.get("data", {})

    if "stock_quote" in modules:
        stock_name = str(args.get("stock") or ctx.get("stock_name") or "").strip()
        if stock_name:
            from news_rag.insight.tool_runners import run_stock_snapshot_adapter

            snap = run_stock_snapshot_adapter({**ctx, "stock_name": stock_name})
            if snap.get("ok"):
                combined["stock_quote"] = snap.get("data", {})

    return {"ok": bool(combined), "data": combined}


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

_RUNNERS = {
    "get_fund_data": _run_get_fund_data,
    "get_portfolio_data": _run_get_portfolio_data,
    "compare_funds": _run_compare_funds,
    "search_financial_news": _run_search_financial_news,
    "get_macro_news": _run_get_macro_news,
    "screen_funds_by_exposure": _run_screen_funds_by_exposure,
    "get_market_snapshot": _run_get_market_snapshot,
}


def execute_capability(
    call: ToolCall,
    *,
    fund_names: list[str] | None = None,
    ctx: dict[str, Any] | None = None,
    telemetry: RequestTelemetry | None = None,
) -> list[dict[str, Any]]:
    """Run one capability, possibly fanning out over funds.

    Returns a list of result dicts [{ok, data, tool, fund, elapsed_ms}].
    """
    from news_rag.insight.capabilities.catalog import CAPABILITIES

    cap = CAPABILITIES.get(call.tool)
    if cap is None:
        return [{"ok": False, "tool": call.tool, "fund": "", "error": f"unknown_capability:{call.tool}", "data": {}, "elapsed_ms": 0}]

    args = validate_capability_args(call.tool, call.arguments)
    base_ctx = dict(ctx or {})
    cache = get_capability_cache()
    results: list[dict[str, Any]] = []

    runner = _RUNNERS.get(call.tool)
    if runner is None:
        return [{"ok": False, "tool": call.tool, "fund": "", "error": "no_runner", "data": {}, "elapsed_ms": 0}]

    if cap.get("per_fund"):
        target_funds = list(fund_names or [])
        arg_fund = str(call.arguments.get("fund") or call.arguments.get("fund_name") or "").strip()
        if arg_fund and arg_fund not in target_funds:
            target_funds.append(arg_fund)
        if not target_funds:
            return [{"ok": False, "tool": call.tool, "fund": "", "error": "no_funds_resolved", "data": {}, "elapsed_ms": 0}]
        for name in target_funds:
            cache_key = _capability_cache_key(call.tool, name, args, base_ctx)
            cached = cache.get(call.tool, cache_key)
            if cached is not None:
                results.append({"ok": True, "tool": call.tool, "fund": name, "data": cached, "elapsed_ms": 0, "cached": True})
                continue
            t0 = time.perf_counter()
            try:
                out = runner(name, args, base_ctx)
            except Exception as exc:
                out = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "data": {}}
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            row = {"ok": bool(out.get("ok")), "tool": call.tool, "fund": name,
                   "data": out.get("data", {}), "elapsed_ms": elapsed,
                   "error": out.get("error", "")}
            if row["ok"]:
                cache.set(call.tool, cache_key, row["data"])
            results.append(row)
            if telemetry:
                telemetry.add_tool(call.tool, wave=call.wave, ok=row["ok"],
                                   duration_ms=elapsed, fund=name)
    else:
        # Non-per-fund capabilities
        if call.tool == "compare_funds":
            t0 = time.perf_counter()
            try:
                out = runner(fund_names or [], args, base_ctx)
            except Exception as exc:
                out = {"ok": False, "error": str(exc), "data": {}}
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
        else:
            t0 = time.perf_counter()
            try:
                out = runner(args, base_ctx)
            except Exception as exc:
                out = {"ok": False, "error": str(exc), "data": {}}
            elapsed = round((time.perf_counter() - t0) * 1000, 1)

        row = {"ok": bool(out.get("ok")), "tool": call.tool, "fund": "",
               "data": out.get("data", {}), "elapsed_ms": elapsed,
               "error": out.get("error", "")}
        results.append(row)
        if telemetry:
            telemetry.add_tool(call.tool, wave=call.wave, ok=row["ok"], duration_ms=elapsed)

    return results


def execute_wave(
    calls: list[ToolCall],
    ctx: dict[str, Any] | None = None,
    *,
    fund_names: list[str] | None = None,
    telemetry: RequestTelemetry | None = None,
    deadline_at: float | None = None,
    deadline_ms: float | None = None,
    query_log: Any = None,
) -> list[dict[str, Any]]:
    """Execute all tool calls in a wave in parallel, respecting the deadline.

    Returns flat list of result dicts.
    """
    if ctx is not None and fund_names is None:
        fund_names = ctx.get("fund_names")
    if deadline_at is None and deadline_ms is not None:
        deadline_at = time.time() + (float(deadline_ms) / 1000.0)

    settings = get_settings()
    max_workers = min(getattr(settings, "max_concurrent_tools", 4), len(calls) or 1)
    all_results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures: list[tuple[Future, ToolCall]] = []
        for call in calls:
            fut = pool.submit(
                execute_capability, call,
                fund_names=fund_names, ctx=ctx, telemetry=telemetry,
            )
            futures.append((fut, call))

        for fut, call in futures:
            # Enforce deadline: if we've passed it, cancel remaining futures
            if deadline_at and time.time() > deadline_at:
                fut.cancel()
                all_results.append({
                    "ok": False, "tool": call.tool, "fund": "",
                    "error": "deadline_exceeded", "data": {}, "elapsed_ms": 0,
                })
                continue
            try:
                remaining = None
                if deadline_at:
                    remaining = max(0.5, deadline_at - time.time())
                results = fut.result(timeout=remaining)
                all_results.extend(results)
            except Exception as exc:
                all_results.append({
                    "ok": False, "tool": call.tool, "fund": "",
                    "error": f"{type(exc).__name__}: {exc}", "data": {}, "elapsed_ms": 0,
                })

    return all_results
