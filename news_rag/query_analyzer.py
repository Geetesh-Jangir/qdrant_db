"""Query decomposition and scope refinement — LLM-first, catalog reconciliation after."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from news_rag.config import get_settings
from news_rag.fund_search import lookup_extracted_fund, resolve_fund_from_question
from news_rag.llm_client import call_json_llm, llm_api_key_configured, router_model
from news_rag.llm_text import parse_json_from_text
from news_rag.macro_plans import try_preset_plan
from news_rag.plan_normalize import normalize_query_plan
from news_rag.query_plan import DataNeed, QueryPlan, ScopeRefinement, SubQuery

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

DECOMPOSER_SYSTEM = """You are the query analyzer for an Indian mutual-fund research API.
Decompose the user question into sub_queries. Each sub_query lists ONLY the tools needed to answer that part.

TOOLS (use exact names):
fund_nav, fund_holdings, fund_sectors, sector_funds, news_search, metals_spot, stock_snapshot, concept

answer_style:
one_metric | short_list | short_table | news_brief | exposure_note | performance_summary | multi_block

FIELDS per data_need:
- tool (required)
- fund_raw: scheme name or ISIN as the user meant it (include AMC + category words; fix obvious typos like HFDC→HDFC)
- fund_ref: earlier sub_query id when reusing the same scheme (e.g. Q1)
- scope: latest_only | with_returns | top_n | event_only
- top_n: integer when listing holdings/sectors
- semantic_query: text for news_search
- depends_on_portfolio: true when news must be scoped to a named fund's holdings/sectors
- window_days: integer for news time window (7, 30, 90) from phrases like "last week", "past month"

RULES:
- Split compound questions into separate sub_queries (max 4). Do NOT use answer_style multi_block — use one sub_query per part (e.g. performance_summary then short_list for holdings).
- needs_reasoning=false for factual lookups and lists. needs_reasoning=true for explain/impact/why/news narrative.
- Do NOT add tools the user did not ask for (no news on pure NAV; no holdings on pure NAV).
- Users often drop the word "fund" ("hdfc defence", "parag parikh flexi") — still set fund_raw.
- ISIN in question → put in fund_raw.
- Performance / "how is it working" / "last month" → one sub_query, answer_style performance_summary, fund_nav scope with_returns ONLY (no news_search).
- Named fund + insights / "I invested in X" / "tell me about this fund" → fund_nav with_returns + holdings + sectors + news_search depends_on_portfolio (window 30).
- Macro/event with no named fund → news_search event_only only (never invent a scheme name).
- Gold/silver move (decline, reasons, funds/stocks) — "my portfolio" is hypothetical. metals_spot + news_search + sector_funds. Do not set fund_raw to "gold and silver".
- Barrel/crude/oil prices + sectors/energy/funds → news_search event_only + sector_funds for energy/petroleum/power. No single scheme.
- "What's hot / how's the market / what to focus on" → news_search event_only (market pulse). Recap stored themes; no buy/sell advice.
- Sectors last month positive vs negative → two news_search event_only windows (~30d).
- Fund + external event impact (crude, RBI) → exposure_note with fund_holdings + news_search depends_on_portfolio.

EXAMPLES (follow this shape, adapt to the actual question):

Q: What is the NAV of HDFC Large Cap Fund and what are its top 5 sectors?
{"sub_queries":[
  {"id":"Q1","text":"NAV of HDFC Large Cap","answer_style":"one_metric","needs_reasoning":false,
   "data_needs":[{"tool":"fund_nav","fund_raw":"HDFC Large Cap Fund","scope":"latest_only"}]},
  {"id":"Q2","text":"top 5 sectors","answer_style":"short_table","needs_reasoning":false,
   "data_needs":[{"tool":"fund_sectors","fund_ref":"Q1","scope":"top_n","top_n":5}]}
]}

Q: tell me how hdfc defence fund is working in last one month?
{"sub_queries":[
  {"id":"Q1","text":"HDFC Defence performance last month","answer_style":"performance_summary","needs_reasoning":false,
   "data_needs":[{"tool":"fund_nav","fund_raw":"HDFC Defence Fund","scope":"with_returns"}]}
]}

Q: How has HDFC Defence Fund done over the last one month, and how might crude-oil related news be affecting it given its holdings?
{"sub_queries":[
  {"id":"Q1","text":"HDFC Defence performance last month","answer_style":"performance_summary","needs_reasoning":false,
   "data_needs":[{"tool":"fund_nav","fund_raw":"HDFC Defence Fund","scope":"with_returns"}]},
  {"id":"Q2","text":"crude-oil news impact on holdings","answer_style":"exposure_note","needs_reasoning":true,
   "data_needs":[
     {"tool":"fund_holdings","fund_ref":"Q1","scope":"top_n","top_n":8},
     {"tool":"news_search","semantic_query":"crude oil prices India markets","depends_on_portfolio":true,"window_days":30}
   ]}
]}

Q: how is hdfc defence working in the last month
(Same as above — infer HDFC Defence Fund even without the word "fund".)

Q: RBI increased repo rate 2%. Which sectors would be affected?
{"sub_queries":[
  {"id":"Q1","text":"sectors affected by RBI rate hike","answer_style":"news_brief","needs_reasoning":true,
   "data_needs":[{"tool":"news_search","semantic_query":"RBI repo rate hike sectors India","scope":"event_only","window_days":30}]}
]}

Return ONLY valid JSON: {"sub_queries":[...]}
"""

SCOPE_REFINER_SYSTEM = """Given a fund impact question, pick news search targets from the ACTUAL portfolio.

Return ONLY JSON:
{"news_entities":["Company or sector name max 8"],"news_topics":["topic phrases"],"search_mode":"event_only"|"entities_only"|"event_plus_entities"}

- Pick entities only from the holdings/sectors lists provided.
- Empty news_entities is allowed.
"""


def reconcile_plan_with_catalog(
    plan: QueryPlan,
    question: str,
    *,
    query_log: QueryLogger | None = None,
) -> QueryPlan:
    """Fill or correct fund_raw using the fund catalog (not intent rules)."""
    q = (question or "").strip()
    global_detail, global_amb, _close = resolve_fund_from_question(q)
    resolved_by_id: dict[str, dict[str, Any]] = {}

    for sq in plan.sub_queries:
        for need in sq.data_needs:
            if need.tool not in ("fund_nav", "fund_holdings", "fund_sectors", "fund_portfolio_news"):
                continue
            if need.tool == "fund_portfolio_news" and need.fund_ref:
                if need.fund_ref in resolved_by_id:
                    need.fund_raw = str(
                        resolved_by_id[need.fund_ref].get("fund_short_name")
                        or resolved_by_id[need.fund_ref].get("isin")
                        or ""
                    )
                continue
            if need.fund_ref and need.fund_ref in resolved_by_id:
                need.fund_raw = str(
                    resolved_by_id[need.fund_ref].get("fund_short_name")
                    or resolved_by_id[need.fund_ref].get("isin")
                    or ""
                )
                continue

            candidates: list[str] = []
            if need.fund_raw:
                candidates.append(need.fund_raw)
            if sq.text:
                candidates.append(sq.text)
            if global_detail and not global_amb:
                candidates.append(
                    str(global_detail.get("fund_short_name") or global_detail.get("isin") or "")
                )

            detail = None
            for phrase in candidates:
                phrase = (phrase or "").strip()
                if not phrase:
                    continue
                if phrase.upper().startswith("INF"):
                    detail, amb, _ = lookup_extracted_fund(isin=phrase.upper())
                else:
                    detail, amb, _ = lookup_extracted_fund(name=phrase)
                if detail and not amb:
                    break
                if amb:
                    break

            if detail and not amb:
                need.fund_raw = str(detail.get("fund_short_name") or detail.get("isin") or "")
                resolved_by_id[sq.id] = detail
                if query_log is not None:
                    query_log.write(
                        f"PLAN_RECONCILE {sq.id} -> {need.fund_raw} isin={detail.get('isin')}"
                    )
            elif global_detail and not global_amb and not need.fund_raw:
                need.fund_raw = str(
                    global_detail.get("fund_short_name") or global_detail.get("isin") or ""
                )
                resolved_by_id[sq.id] = global_detail

    return plan


def _llm_decompose(
    question: str,
    *,
    query_log: QueryLogger | None = None,
) -> QueryPlan:
    settings = get_settings()
    started = time.perf_counter()
    res = call_json_llm(
        system_prompt=DECOMPOSER_SYSTEM,
        user_content=f"Question:\n{question.strip()}",
        model_override=router_model(settings),
        max_tokens=max(settings.router_max_tokens, 900),
        temperature=0.0,
        query_log=query_log,
    )
    parsed = parse_json_from_text(res.raw_text) or {}
    plan = QueryPlan.from_dict(parsed, source="llm")
    if query_log is not None:
        query_log.write(
            f"PLAN source=llm sub_queries={len(plan.sub_queries)} "
            f"duration={time.perf_counter() - started:.2f}s"
        )
        for sq in plan.sub_queries:
            tools = ",".join(n.tool for n in sq.data_needs)
            query_log.write(
                f"  {sq.id} {sq.answer_style} needs_llm={sq.needs_reasoning} tools={tools} "
                f"fund_raw={next((n.fund_raw for n in sq.data_needs if n.fund_raw), '')}"
            )
        query_log.note("plan", source="llm", sub_count=len(plan.sub_queries))
    return plan


def _minimal_fallback_plan(question: str) -> QueryPlan:
    """No LLM available: one news search; fund tools filled later via catalog reconcile."""
    q = question.strip()
    return QueryPlan(
        sub_queries=[
            SubQuery(
                id="Q1",
                text=q,
                answer_style="news_brief",
                needs_reasoning=True,
                data_needs=[DataNeed.from_dict({"tool": "news_search", "semantic_query": q})],
            )
        ],
        source="no_llm_fallback",
    )


def decompose_query(
    question: str,
    *,
    query_log: QueryLogger | None = None,
) -> QueryPlan:
    q = (question or "").strip()
    settings = get_settings()

    preset = try_preset_plan(q)
    if preset is not None:
        preset = reconcile_plan_with_catalog(preset, q, query_log=query_log)
        if query_log is not None:
            query_log.write(f"PLAN source={preset.source} preset=true skip_normalize=true")
        return preset

    if llm_api_key_configured(settings):
        try:
            plan = _llm_decompose(q, query_log=query_log)
        except Exception as exc:
            logger.warning("decomposer LLM failed: %s", exc)
            if query_log is not None:
                query_log.write(f"PLAN llm_error={exc}")
            plan = _minimal_fallback_plan(q)
    else:
        if query_log is not None:
            query_log.write("PLAN source=no_llm_fallback reason=no_api_key")
        plan = _minimal_fallback_plan(q)

    if not plan.sub_queries:
        plan = _minimal_fallback_plan(q)

    plan = reconcile_plan_with_catalog(plan, q, query_log=query_log)
    plan = normalize_query_plan(plan, q)
    if query_log is not None:
        query_log.write(f"PLAN normalized sub_queries={len(plan.sub_queries)} source={plan.source}")
        for sq in plan.sub_queries:
            query_log.write(
                f"  {sq.id} {sq.answer_style} tools={','.join(n.tool for n in sq.data_needs)}"
            )

    return plan


def refine_news_scope(
    sub_query_text: str,
    *,
    sectors: list[dict[str, Any]],
    holdings: list[dict[str, Any]],
    query_log: QueryLogger | None = None,
) -> ScopeRefinement:
    """LLM picks entities/topics for portfolio-dependent news."""
    sector_lines = [f"{s.get('sector')}: {s.get('percentage')}%" for s in sectors[:12]]
    holding_lines = [f"{h.get('name')}: {h.get('percentage')}%" for h in holdings[:15]]
    user = (
        f"Sub-query: {sub_query_text}\n\n"
        f"Sectors:\n" + "\n".join(sector_lines) + "\n\n"
        f"Holdings:\n" + "\n".join(holding_lines)
    )
    settings = get_settings()
    if not llm_api_key_configured(settings):
        return portfolio_scope_fallback(holdings, sectors)

    try:
        res = call_json_llm(
            system_prompt=SCOPE_REFINER_SYSTEM,
            user_content=user,
            model_override=router_model(settings),
            max_tokens=400,
            temperature=0.0,
            query_log=query_log,
        )
        parsed = parse_json_from_text(res.raw_text) or {}
        scope = ScopeRefinement.from_dict(parsed)
        if query_log is not None:
            query_log.write(
                f"SCOPE mode={scope.search_mode} entities={scope.news_entities} topics={scope.news_topics}"
            )
        return scope
    except Exception as exc:
        logger.warning("scope refiner failed: %s", exc)
        return portfolio_scope_fallback(holdings, sectors)


def portfolio_scope_fallback(
    holdings: list[dict[str, Any]],
    sectors: list[dict[str, Any]] | None = None,
) -> ScopeRefinement:
    """Deterministic portfolio news scope: top holdings (+ optional sector labels for query text)."""
    entities = [str(h.get("name") or "").strip() for h in holdings[:10] if h.get("name")]
    if entities:
        return ScopeRefinement(news_entities=entities, news_topics=[], search_mode="event_plus_entities")
    return ScopeRefinement(news_entities=[], news_topics=[], search_mode="event_only")


def _fallback_scope_from_portfolio(holdings: list[dict[str, Any]]) -> ScopeRefinement:
    return portfolio_scope_fallback(holdings, None)
