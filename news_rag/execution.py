"""Execute a normalized query plan against resolved fund context."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from news_rag.fund_search import resolve_fund_from_question
from news_rag.macro_plans import skip_scheme_resolution
from news_rag.tools import resolve_fund_for_need
from news_rag.query_analyzer import portfolio_scope_fallback, refine_news_scope
from news_rag.query_plan import DataNeed, QueryPlan, ScopeRefinement, SubQuery
from news_rag.tools import (
    run_fund_holdings,
    run_fund_nav,
    run_fund_portfolio_news,
    run_fund_sectors,
    run_metals_spot,
    run_news_search,
    run_sector_funds,
    run_stock_snapshot,
)

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger


def _is_macro_impact_news(*texts: str) -> bool:
    blob = " ".join(t for t in texts if t).lower()
    return bool(
        re.search(
            r"\b(crude|oil|petroleum|brent|rbi|repo|gold|silver|interest rate|rate hike)\b",
            blob,
        )
    )


def _merge_topic_hints(scope: ScopeRefinement, *texts: str) -> ScopeRefinement:
    """Add crude/RBI/etc. topic filters from the sub-query and semantic query."""
    blob = " ".join(t for t in texts if t).lower()
    extra: list[str] = []
    if re.search(r"\b(crude|oil|petroleum|brent)\b", blob):
        extra.extend(["crude oil", "crude", "oil", "petroleum"])
    if re.search(r"\b(barrel|wti)\b", blob):
        extra.extend(["crude oil", "brent", "barrel"])
    if re.search(r"\b(gold|silver)\b", blob):
        extra.extend(["gold", "silver"])
    if re.search(r"\b(rbi|repo|interest rate|rate hike)\b", blob):
        extra.extend(["rbi", "repo rate", "interest rate"])
    if not extra:
        return scope
    topics = list(scope.news_topics or [])
    for t in extra:
        if t not in topics:
            topics.append(t)
    mode = scope.search_mode
    if mode == "entities_only":
        mode = "event_plus_entities"
    return ScopeRefinement(news_entities=scope.news_entities, news_topics=topics, search_mode=mode)


@dataclass
class FundContext:
    detail: dict[str, Any] | None = None
    ambiguous: bool = False
    close_matches: list[str] = field(default_factory=list)
    by_sub_id: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class SubQueryRun:
    sub_query: SubQuery
    tool_results: dict[str, Any] = field(default_factory=dict)
    fund_detail: dict[str, Any] | None = None
    skipped_ambiguous: bool = False


def build_fund_context(plan: QueryPlan, question: str, *, query_log: QueryLogger | None = None) -> FundContext:
    ctx = FundContext()
    if skip_scheme_resolution(question, plan.source):
        if query_log is not None:
            query_log.write(f"FUND_CTX skip_resolve reason={plan.source or 'market_discovery'}")
        return ctx
    detail, amb, close = resolve_fund_from_question(question)
    ctx.detail = detail
    ctx.ambiguous = amb
    ctx.close_matches = close

    if detail and not amb:
        ctx.by_sub_id["_question"] = detail

    for sq in plan.sub_queries:
        for need in sq.data_needs:
            if need.tool not in ("fund_nav", "fund_holdings", "fund_sectors", "fund_portfolio_news"):
                continue
            if need.tool == "fund_portfolio_news":
                if need.fund_ref and need.fund_ref in ctx.by_sub_id:
                    ctx.by_sub_id[sq.id] = ctx.by_sub_id[need.fund_ref]
                continue
            if sq.id in ctx.by_sub_id:
                continue
            if need.fund_ref and need.fund_ref in ctx.by_sub_id:
                ctx.by_sub_id[sq.id] = ctx.by_sub_id[need.fund_ref]
                continue
            raw = need.fund_raw
            if not raw and ctx.detail:
                raw = str(ctx.detail.get("fund_short_name") or ctx.detail.get("isin") or "")
            if not raw:
                continue
            resolved, r_amb, r_close, _ = resolve_fund_for_need(raw, query_log=query_log)
            if r_amb:
                ctx.ambiguous = True
                ctx.close_matches = r_close
            elif resolved:
                ctx.by_sub_id[sq.id] = resolved
                if not ctx.detail:
                    ctx.detail = resolved

    return ctx


def _detail_for_sub(sq: SubQuery, ctx: FundContext) -> dict[str, Any] | None:
    if sq.id in ctx.by_sub_id:
        return ctx.by_sub_id[sq.id]
    for need in sq.data_needs:
        if need.fund_ref and need.fund_ref in ctx.by_sub_id:
            return ctx.by_sub_id[need.fund_ref]
    return ctx.by_sub_id.get("_question") or ctx.detail


def execute_sub_query(
    sq: SubQuery,
    ctx: FundContext,
    question: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
) -> SubQueryRun:
    run = SubQueryRun(sub_query=sq)
    if ctx.ambiguous:
        run.skipped_ambiguous = True
        return run

    detail = _detail_for_sub(sq, ctx)
    run.fund_detail = detail
    if not detail and any(
        n.tool in ("fund_nav", "fund_holdings", "fund_sectors", "fund_portfolio_news") for n in sq.data_needs
    ):
        return run

    portfolio_holdings: list[dict] = []
    portfolio_sectors: list[dict] = []
    wave1 = [n for n in sq.data_needs if n.tool != "news_search"]
    news_needs = [n for n in sq.data_needs if n.tool == "news_search"]

    for need in wave1:
        if need.tool == "fund_nav" and detail:
            run.tool_results["fund_nav"] = run_fund_nav(detail, need)
        elif need.tool == "fund_holdings" and detail:
            run.tool_results["fund_holdings"] = run_fund_holdings(detail, need)
            portfolio_holdings = (run.tool_results["fund_holdings"].get("data") or {}).get("rows") or []
        elif need.tool == "fund_sectors" and detail:
            run.tool_results["fund_sectors"] = run_fund_sectors(detail, need)
            portfolio_sectors = (run.tool_results["fund_sectors"].get("data") or {}).get("rows") or []
        elif need.tool == "sector_funds":
            run.tool_results["sector_funds"] = run_sector_funds(need)
        elif need.tool == "metals_spot":
            run.tool_results["metals_spot"] = run_metals_spot()
        elif need.tool == "stock_snapshot":
            run.tool_results["stock_snapshot"] = run_stock_snapshot(need)
        elif need.tool == "fund_portfolio_news" and detail:
            run.tool_results["fund_portfolio_news"] = run_fund_portfolio_news(
                detail,
                need,
                question=question,
                query_log=query_log,
            )

    for need in news_needs:
        if need.depends_on_portfolio and detail and not portfolio_holdings:
            h = run_fund_holdings(detail, DataNeed(tool="fund_holdings", top_n=10))
            portfolio_holdings = (h.get("data") or {}).get("rows") or []
        if need.depends_on_portfolio and detail and not portfolio_sectors:
            s = run_fund_sectors(detail, DataNeed(tool="fund_sectors", top_n=10))
            portfolio_sectors = (s.get("data") or {}).get("rows") or []

        macro = _is_macro_impact_news(question, sq.text, need.semantic_query or "")
        if macro:
            scope = _merge_topic_hints(
                ScopeRefinement(search_mode="event_only", news_topics=[]),
                sq.text,
                need.semantic_query or "",
                question,
            )
        elif need.depends_on_portfolio and (portfolio_holdings or portfolio_sectors):
            scope = refine_news_scope(
                sq.text,
                sectors=portfolio_sectors,
                holdings=portfolio_holdings,
                query_log=query_log,
            )
            if not scope.news_entities and portfolio_holdings:
                scope = portfolio_scope_fallback(portfolio_holdings, portfolio_sectors)
            scope = _merge_topic_hints(scope, sq.text, need.semantic_query or "", question)
        elif need.scope == "event_only":
            scope = ScopeRefinement(search_mode="event_only", news_topics=[need.semantic_query or sq.text])
            scope = _merge_topic_hints(scope, sq.text, need.semantic_query or "", question)
        else:
            scope = ScopeRefinement(
                search_mode="event_only",
                news_topics=[need.semantic_query] if need.semantic_query else [],
            )
            scope = _merge_topic_hints(scope, sq.text, need.semantic_query or "", question)
        news_result = run_news_search(
            need,
            scope=scope,
            question=question,
            date_from=date_from,
            date_to=date_to,
            min_impact=min_impact,
            source=source,
            direction=direction,
            query_log=query_log,
        )
        prev = run.tool_results.get("news_search") or {}
        prev_rows = (prev.get("data") or {}).get("articles") or []
        new_rows = (news_result.get("data") or {}).get("articles") or []
        if prev_rows:
            by_url: dict[str, dict] = {}
            for art in prev_rows + new_rows:
                url = str(art.get("url") or "").strip()
                key = url or str(art.get("title") or "")
                if key:
                    by_url[key] = art
            merged = list(by_url.values())
            news_result = {
                **news_result,
                "data": {**(news_result.get("data") or {}), "articles": merged},
            }
        run.tool_results["news_search"] = news_result

    return run


def execute_plan(
    plan: QueryPlan,
    question: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
) -> tuple[FundContext, list[SubQueryRun]]:
    ctx = build_fund_context(plan, question, query_log=query_log)
    runs: list[SubQueryRun] = []
    for sq in plan.sub_queries:
        runs.append(
            execute_sub_query(
                sq,
                ctx,
                question,
                date_from=date_from,
                date_to=date_to,
                min_impact=min_impact,
                source=source,
                direction=direction,
                query_log=query_log,
            )
        )
    return ctx, runs
