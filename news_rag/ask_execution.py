"""Parallel tool execution for LLM ask plans."""

from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from news_rag.ask_plan import AskPlan, PlannedTool
from news_rag.fund_search import extract_top_holdings, extract_top_sectors

_NEWS_TOOL_NAMES = frozenset({"holdings_news", "sector_news", "macro_news"})


def _is_driver_macro_tool(tool: PlannedTool) -> bool:
    return tool.tool == "macro_news" and bool((tool.search_focus or "").strip())


def _split_news_tools(news_tools: list[PlannedTool]) -> tuple[list[PlannedTool], list[PlannedTool]]:
    driver = [t for t in news_tools if _is_driver_macro_tool(t)]
    other = [t for t in news_tools if not _is_driver_macro_tool(t)]
    return driver, other
from news_rag.name_resolution import ResolvedNames, resolve_plan_names
from news_rag.query_plan import DataNeed
from news_rag.macro_news_enhanced import run_macro_news_enhanced
from news_rag.market_pulse import CLUSTERED_MACRO_TOOL_NAMES, run_market_pulse
from news_rag.tools import (
    run_affected_funds,
    run_fund_holdings,
    run_fund_nav,
    run_fund_sectors,
    run_layered_news,
    run_metals_spot,
    run_sector_funds,
    run_stock_snapshot,
)
from news_rag.fund_portfolio_news import retrieve_layered_fund_news

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger


@dataclass
class PipelineError:
    stage: str
    tool: str
    message: str


@dataclass
class ToolRunResult:
    tool: str
    key: str
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class ExecutionBundle:
    names: ResolvedNames
    tool_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    holdings_rows: list[dict[str, Any]] = field(default_factory=list)
    sector_rows: list[dict[str, Any]] = field(default_factory=list)
    articles_by_layer: dict[str, list[dict]] = field(default_factory=dict)
    articles_by_focus: dict[str, list[dict]] = field(default_factory=dict)
    pipeline_errors: list[PipelineError] = field(default_factory=list)
    fund_nav_data: dict[str, Any] | None = None


def _tool_key(tool: PlannedTool, index: int) -> str:
    return f"{tool.tool}_{index}"


def _run_one_tool(
    tool: PlannedTool,
    index: int,
    plan: AskPlan,
    names: ResolvedNames,
    question: str,
    *,
    date_from: str | None,
    date_to: str | None,
    min_impact: int | None,
    source: str | None,
    direction: str | None,
    query_log: QueryLogger | None,
) -> ToolRunResult:
    key = _tool_key(tool, index)
    detail = names.scheme_detail(tool.fund_entity_index)
    filter_kwargs = {
        "date_from": date_from,
        "date_to": date_to,
        "min_impact": min_impact,
        "source": source,
        "direction": direction,
    }
    try:
        if tool.tool == "fund_nav" and detail:
            need = DataNeed(tool="fund_nav", scope="with_returns")
            return ToolRunResult(tool.tool, key, run_fund_nav(detail, need))
        if tool.tool == "fund_top_stocks" and detail:
            need = DataNeed(tool="fund_holdings", top_n=tool.top_n)
            return ToolRunResult(tool.tool, key, run_fund_holdings(detail, need))
        if tool.tool == "fund_top_sectors" and detail:
            need = DataNeed(tool="fund_sectors", top_n=tool.top_n)
            return ToolRunResult(tool.tool, key, run_fund_sectors(detail, need))
        if tool.tool in ("holdings_news", "sector_news", "macro_news"):
            entities = list(tool.entity_filters)
            if tool.tool == "holdings_news" and detail and not entities:
                entities = [str(r.get("name") or "") for r in extract_top_holdings(detail, 8)]
            if tool.tool == "sector_news" and detail and not entities:
                entities = [str(r.get("sector") or "") for r in extract_top_sectors(detail, 6)]
            if not entities and names.holdings and tool.tool == "holdings_news":
                entities = names.holdings
            if not entities and names.sectors and tool.tool == "sector_news":
                entities = names.sectors
            layer = tool.tool
            return ToolRunResult(
                tool.tool,
                key,
                run_layered_news(
                    layer=layer,
                    semantic_query=tool.semantic_query or question,
                    question=question,
                    entity_filters=entities,
                    window_days=tool.window_days,
                    sentiment=plan.sentiment,
                    search_focus=tool.search_focus,
                    query_log=query_log,
                    **filter_kwargs,
                ),
            )
        if tool.tool == "sector_funds":
            need = DataNeed(
                tool="sector_funds",
                sector_name=tool.sector_name,
                semantic_query=tool.semantic_query,
                top_n=tool.top_n,
            )
            return ToolRunResult(
                tool.tool,
                key,
                run_sector_funds(
                    need,
                    direction=direction or plan.sentiment or "any",
                    question=question,
                ),
            )
        if tool.tool == "metals_spot":
            return ToolRunResult(tool.tool, key, run_metals_spot())
        if tool.tool == "stock_snapshot":
            need = DataNeed(tool="stock_snapshot", stock_name=tool.stock_name, semantic_query=tool.semantic_query)
            return ToolRunResult(tool.tool, key, run_stock_snapshot(need))
        if tool.tool == "affected_funds":
            sectors = plan.affected_funds_sectors or names.sectors
            return ToolRunResult(
                tool.tool,
                key,
                run_affected_funds(
                    sector_names=sectors,
                    top_n=plan.affected_funds_top_n,
                    semantic_query=tool.semantic_query,
                    direction=direction or plan.sentiment or "any",
                ),
            )
        if tool.tool in ("common_market_news", "market_pulse"):
            return ToolRunResult(
                tool.tool,
                key,
                run_market_pulse(
                    question,
                    window_days=tool.window_days,
                    query_log=query_log,
                    **filter_kwargs,
                ),
            )
        if tool.tool == "macro_news_enhanced":
            return ToolRunResult(
                tool.tool,
                key,
                run_macro_news_enhanced(
                    question,
                    semantic_query=tool.semantic_query,
                    window_days=tool.window_days,
                    query_log=query_log,
                    **filter_kwargs,
                ),
            )
        return ToolRunResult(tool.tool, key, {"ok": False, "error": f"unknown tool {tool.tool}", "data": None})
    except Exception as exc:
        return ToolRunResult(tool.tool, key, {"ok": False, "error": str(exc), "data": None}, error=str(exc))


def _news_window_days(news_tools: list[PlannedTool], default: int = 30) -> int:
    for tool in news_tools:
        if tool.window_days:
            return int(tool.window_days)
    return default


def _run_fund_portfolio_news(
    bundle: ExecutionBundle,
    question: str,
    news_tools: list[PlannedTool],
    *,
    query_log: QueryLogger | None,
) -> None:
    """Layered Qdrant search with corpus-resolved entities (holdings → sectors → macro)."""
    detail = bundle.names.primary_scheme
    if not detail:
        return
    _hydrate_names_from_scheme(bundle)
    nav = bundle.fund_nav_data if isinstance(bundle.fund_nav_data, dict) else {}
    fund_name = str(
        detail.get("fund_short_name") or detail.get("fund_name") or nav.get("fund_name") or ""
    )
    window = _news_window_days(news_tools)
    started_articles = sum(len(v) for v in bundle.articles_by_layer.values())
    articles = retrieve_layered_fund_news(
        holdings=bundle.holdings_rows,
        sectors=bundle.sector_rows,
        question=question,
        fund_name=fund_name,
        window_days=window,
        query_log=query_log,
    )
    bundle.tool_results["fund_portfolio_news"] = {
        "ok": True,
        "data": {"articles": articles, "count": len(articles)},
        "error": "",
    }
    by_layer: dict[str, list[dict]] = {}
    for art in articles:
        layer = str(art.get("_news_layer") or "macro")
        by_layer.setdefault(layer, []).append(art)
    for layer, arts in by_layer.items():
        _merge_articles_into(bundle.articles_by_layer, layer, arts)
        _merge_articles_into(bundle.articles_by_focus, layer, arts)
    if query_log is not None:
        query_log.log_stage(
            "fund_portfolio_news",
            articles=len(articles),
            layers=list(by_layer.keys()),
            prior_articles=started_articles,
        )


def _hydrate_names_from_scheme(bundle: ExecutionBundle) -> None:
    """After fund facts run, seed holding/sector names for news vector search."""
    detail = bundle.names.primary_scheme
    if not detail:
        return
    if not bundle.holdings_rows:
        bundle.holdings_rows = extract_top_holdings(detail, 10)
    if not bundle.sector_rows:
        bundle.sector_rows = extract_top_sectors(detail, 8)
    if not bundle.names.holdings and bundle.holdings_rows:
        bundle.names.holdings = [
            str(r.get("name") or "") for r in bundle.holdings_rows[:10] if r.get("name")
        ]
    if not bundle.names.sectors and bundle.sector_rows:
        bundle.names.sectors = [
            str(r.get("sector") or "") for r in bundle.sector_rows[:8] if r.get("sector")
        ]


def _apply_tool_result(bundle: ExecutionBundle, tr: ToolRunResult) -> None:
    data = tr.result.get("data") or {}
    if tr.tool == "fund_top_stocks" and tr.result.get("ok"):
        bundle.holdings_rows = data.get("rows") or []
    if tr.tool == "fund_top_sectors" and tr.result.get("ok"):
        bundle.sector_rows = data.get("rows") or []
    if tr.tool == "fund_nav" and tr.result.get("ok"):
        bundle.fund_nav_data = data
    if tr.tool in CLUSTERED_MACRO_TOOL_NAMES and tr.result.get("ok"):
        prefix = "pulse" if tr.tool in ("common_market_news", "market_pulse") else "macro_enh"
        for cl in data.get("clusters") or []:
            focus = f"{prefix}_{cl.get('theme_key') or cl.get('id')}"
            arts = cl.get("articles") or []
            _merge_articles_into(bundle.articles_by_focus, focus, arts)
            _merge_articles_into(bundle.articles_by_layer, "macro", arts)
        for art in data.get("articles") or []:
            _merge_articles_into(bundle.articles_by_layer, "macro", [art])
        return
    if tr.tool in _NEWS_TOOL_NAMES and tr.result.get("ok"):
        layer = tr.tool.replace("_news", "")
        arts = data.get("articles") or []
        focus = str(data.get("search_focus") or "")
        if not focus and arts:
            focus = str(arts[0].get("_search_focus") or "")
        focus_key = focus or layer
        _merge_articles_into(bundle.articles_by_layer, layer, arts)
        _merge_articles_into(bundle.articles_by_focus, focus_key, arts)


def _run_tools_parallel(
    tools_to_run: list[PlannedTool],
    plan: AskPlan,
    bundle: ExecutionBundle,
    question: str,
    *,
    date_from: str | None,
    date_to: str | None,
    min_impact: int | None,
    source: str | None,
    direction: str | None,
    query_log: QueryLogger | None,
) -> list[ToolRunResult]:
    results: list[ToolRunResult] = []
    if not tools_to_run:
        return results
    max_workers = min(8, max(1, len(tools_to_run)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                _run_one_tool,
                tool,
                i,
                plan,
                bundle.names,
                question,
                date_from=date_from,
                date_to=date_to,
                min_impact=min_impact,
                source=source,
                direction=direction,
                query_log=query_log,
            ): (tool, i)
            for i, tool in enumerate(tools_to_run)
        }
        for fut in as_completed(futures):
            tool, i = futures[fut]
            try:
                tr = fut.result()
            except Exception as exc:
                tr = ToolRunResult(tool.tool, _tool_key(tool, i), error=str(exc))
                if query_log is not None:
                    query_log.write(f"TOOL_FAIL {tool.tool} {exc}\n{traceback.format_exc()}")
            results.append(tr)
            if tr.error or not tr.result.get("ok", True):
                msg = tr.error or str(tr.result.get("error") or "tool failed")
                bundle.pipeline_errors.append(PipelineError(stage="tool", tool=tr.tool, message=msg))
            else:
                bundle.tool_results[tr.key] = tr.result
                _apply_tool_result(bundle, tr)
                if query_log is not None:
                    elapsed = tr.result.get("elapsed_ms", 0)
                    query_log.log_stage("tool_done", tool=tr.tool, key=tr.key, elapsed_ms=elapsed)
    return results


def _merge_articles_into(pool: dict[str, list[dict]], key: str, articles: list[dict]) -> None:
    if not articles:
        return
    seen = {str(a.get("url") or "") for a in pool.get(key, [])}
    bucket = pool.setdefault(key, [])
    for art in articles:
        url = str(art.get("url") or "").strip()
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        bucket.append(art)


def execute_ask_plan(
    plan: AskPlan,
    question: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
) -> ExecutionBundle:
    bundle = ExecutionBundle(names=resolve_plan_names(plan, query_log=query_log))

    if bundle.names.ambiguous:
        return bundle

    tools_to_run = [t for t in plan.tools if t.tool != "affected_funds" or plan.affected_funds == "now"]
    clustered_macro = [t for t in tools_to_run if t.tool in CLUSTERED_MACRO_TOOL_NAMES]
    pulse_mode = any(t.tool in ("common_market_news", "market_pulse") for t in clustered_macro)
    fact_tools = [
        t
        for t in tools_to_run
        if t.tool not in _NEWS_TOOL_NAMES and t.tool not in CLUSTERED_MACRO_TOOL_NAMES
    ]
    news_tools = [t for t in tools_to_run if t.tool in _NEWS_TOOL_NAMES]
    if pulse_mode:
        news_tools = [t for t in news_tools if t.tool != "macro_news"]

    if query_log is not None:
        query_log.write(
            f"EXEC phase1_facts={len(fact_tools)} phase2_news={len(news_tools)}"
        )

    _hydrate_names_from_scheme(bundle)
    _run_tools_parallel(
        fact_tools,
        plan,
        bundle,
        question,
        date_from=date_from,
        date_to=date_to,
        min_impact=min_impact,
        source=source,
        direction=direction,
        query_log=query_log,
    )
    if clustered_macro:
        _run_tools_parallel(
            clustered_macro,
            plan,
            bundle,
            question,
            date_from=date_from,
            date_to=date_to,
            min_impact=min_impact,
            source=source,
            direction=direction,
            query_log=query_log,
        )
    _hydrate_names_from_scheme(bundle)
    driver_news, other_news = _split_news_tools(news_tools)
    if news_tools and bundle.names.primary_scheme:
        _run_fund_portfolio_news(bundle, question, news_tools, query_log=query_log)
        if driver_news:
            _run_tools_parallel(
                driver_news,
                plan,
                bundle,
                question,
                date_from=date_from,
                date_to=date_to,
                min_impact=min_impact,
                source=source,
                direction=direction,
                query_log=query_log,
            )
        elif other_news:
            _run_tools_parallel(
                other_news,
                plan,
                bundle,
                question,
                date_from=date_from,
                date_to=date_to,
                min_impact=min_impact,
                source=source,
                direction=direction,
                query_log=query_log,
            )
    elif news_tools:
        _run_tools_parallel(
            news_tools,
            plan,
            bundle,
            question,
            date_from=date_from,
            date_to=date_to,
            min_impact=min_impact,
            source=source,
            direction=direction,
            query_log=query_log,
        )

    return bundle


def run_affected_funds_after_news(
    plan: AskPlan,
    bundle: ExecutionBundle,
    digest_sectors: list[str],
    *,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
) -> None:
    if plan.affected_funds != "after_news":
        return
    sectors = [s for s in (digest_sectors or plan.affected_funds_sectors or []) if str(s).strip()][:3]
    target_dir = direction or plan.sentiment or "any"
    try:
        res = run_affected_funds(
            sector_names=sectors,
            top_n=plan.affected_funds_top_n,
            semantic_query=plan.answer_parts,
            direction=target_dir,
        )
        bundle.tool_results["affected_funds_post"] = res
        if query_log is not None:
            query_log.log_stage(
                "affected_funds_after_news",
                sectors=sectors[:8],
                direction=target_dir,
            )
    except Exception as exc:
        bundle.pipeline_errors.append(
            PipelineError(stage="affected_funds", tool="affected_funds", message=str(exc))
        )
        if query_log is not None:
            query_log.write(f"AFFECTED_FUNDS_FAIL {exc}")
