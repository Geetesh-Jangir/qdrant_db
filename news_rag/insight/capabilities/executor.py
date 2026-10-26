"""Capability executor — runs six capability tools in parallel with deadline enforcement.

Each capability delegates to existing layer_tools / tool_runners adapters.
The executor validates args, respects fan-out caps, and uses the TTL cache.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Any

from news_rag.config import get_settings
from news_rag.insight.capabilities.cache import get_capability_cache
from news_rag.insight.capabilities.catalog import validate_capability_args
from news_rag.insight.contracts import ToolCall, RequestTelemetry


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
    return key


def _run_get_fund_data(fund_name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Delegate to existing fund snapshot / return_series / attribution tools."""
    from news_rag.insight.registry import ensure_registry

    ensure_registry()
    results: dict[str, Any] = {"fund_name": fund_name}
    modules = args.get("modules", ["snapshot"])

    if "snapshot" in modules:
        from news_rag.insight.layer_tools import run_fund_snapshot
        snap_ctx = {**ctx, "fund_name": fund_name, "fund_names": [fund_name], "windows": args.get("windows", ["1M"])}
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
    compare_ctx = {**ctx, "fund_names": fund_names, "overlap": args.get("mode") in ("overlap", "both")}
    return run_compare_funds_adapter(compare_ctx)


def _run_search_financial_news(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Delegate to the news fanout system."""
    from news_rag.insight.news_fanout import NewsTarget, search_targets, grouped_news

    scope = args.get("scope", "market")
    topics = args.get("topics", [])
    top_n = args.get("top_n", 3)
    window_days = args.get("window_days", 14)
    direction = args.get("direction")
    if direction == "any":
        direction = None

    targets: list[NewsTarget] = []
    if scope == "market" and not topics:
        from news_rag.insight.market_news import market_scope_entities
        entities = market_scope_entities(source_kind="layer1", topics=[], top_n=top_n)
    elif topics:
        entities = [(t, f"{t} India market news") for t in topics[:top_n]]
    else:
        entities = [(scope, f"{scope} India financial news")]

    for entity, query in entities:
        targets.append(NewsTarget(
            scope=scope, entity=entity, query=query, window_days=window_days,
            direction=direction, limit=3, chars=900, required=True,
        ))

    search_targets(targets)
    grouped = grouped_news(targets)
    articles = [art for t in targets for art in (t.articles or [])]
    return {"ok": bool(articles), "data": {"grouped": grouped, "articles": articles, "article_count": len(articles)}}


def _run_screen_funds_by_exposure(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Delegate to sector_funds / driver_affected_funds / screen_funds."""
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
        spec = get_tool("sector_funds")
        if spec and spec.run:
            screen_ctx = {
                **ctx,
                "sector_name": sector,
                "sector_keys": [sector],
                "top_n": args.get("top_n", 5),
            }
            return spec.run(screen_ctx)
    # Catalog performance / random fund screen (no sector or driver)
    spec = get_tool("screen_funds")
    if spec and spec.run:
        from news_rag.tools import infer_return_window

        q = str(ctx.get("question") or "")
        screen_ctx = {
            **ctx,
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
