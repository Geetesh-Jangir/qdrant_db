"""LLM-only query planner — guardrails, tools, sentiment, and entities in one JSON call."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from news_rag.ask_plan import AskPlan
from news_rag.config import get_settings
from news_rag.llm_client import call_json_llm, llm_api_key_configured, router_model
from news_rag.llm_text import parse_json_from_text

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

ADVICE_NOTE = (
    "We provide fund data and news context only — not buy/sell/hold advice, "
    "target prices, or predictions."
)

PLANNER_SYSTEM = """You are the planner for an Indian mutual-fund and market-news API.
Return ONLY valid JSON matching the schema below. No markdown.

SCHEMA:
{
  "decline_entirely": false,
  "decline_message": "",
  "answer_parts": "factual parts to answer",
  "declined_parts": ["buy/sell advice phrases we will not answer"],
  "sentiment": "positive|negative|any",
  "entities": [
    {"raw": "user text", "role": "fund_scheme|amc|holding|sector", "cleaned_phrase": "normalized name"}
  ],
  "tools": [
    {
      "tool": "<name>",
      "fund_entity_index": 0,
      "top_n": 5,
      "semantic_query": "short embedding query for news tools",
      "sector_name": "",
      "stock_name": "",
      "window_days": 30,
      "entity_filters": ["optional holding or sector names for news"]
    }
  ],
  "affected_funds": "none|now|after_news",
  "affected_funds_sectors": ["sector labels when known"],
  "affected_funds_top_n": 10
}

TOOLS (exact names):
fund_nav, fund_top_stocks, fund_top_sectors, holdings_news, sector_news, macro_news,
common_market_news, macro_news_enhanced,
affected_funds, sector_funds, metals_spot, stock_snapshot

MARKET & MACRO TOOLS (planner must choose — no keyword guessing in code):
- common_market_news: User wants a broad read on Indian markets right now / today / overall backdrop.
  No named mutual fund required. entities[] can be empty. Sets window_days 30 (or from question).
  Do NOT also add macro_news for the same broad question.
- macro_news_enhanced: User asks about a specific macro driver or theme (RBI, rates, oil, FII flows,
  inflation, bond yields, rupee, earnings season, geopolitics) without needing full market snapshot.
  Provide a strong semantic_query (India + topic keywords). Can combine with sector_news for sector angle.
- macro_news: Single focused vector search — narrow follow-up or one headline topic only.

GUARDRAILS:
- decline_entirely=true ONLY for non-finance (poems, code, recipes) or empty meaning.
- If the user also asks "should I buy", target price, predict, recommend: put that in declined_parts.
  Still set answer_parts to the factual question and run tools for the factual part.
- Never refuse the whole question only because of buy/sell wording.

SENTIMENT (this value is the fund-direction filter — do not leave it to later code):
- positive: the user wants funds or sectors that are working well, performing well, doing well, benefiting, or are gainers. Affected-fund and sector-fund ranking will keep only positive 1-month NAV.
- negative: the user wants worst hit, adversely affected, under pressure, falling, or losing funds or sectors. Ranking keeps the weakest 1-month NAV.
- any: the user did not ask for a winning or losing side. Ranking uses the strongest 1-month results without a sign filter.
- "which mutual funds are working well" and "sectors performing well" are positive, even in a combined market question.

ENTITIES (critical):
- fund_scheme: a specific mutual fund (fix typos: HFDC→HDFC, defense→defence in cleaned_phrase).
- hdfc large cap without "fund" → HDFC Large Cap Fund scheme.
- amc: fund house only (HDFC AMC) — do NOT bind fund_nav to a random HDFC scheme.
- holding: a stock (HDFC Bank is a holding, not the AMC).
- sector: industry name.
- One question can mix roles (HDFC Defence Fund + HDFC Bank holding).

TOOLS RULES:
- Fund performance / how is X working → fund_nav (with_returns) + fund_top_stocks + fund_top_sectors +
  holdings_news + sector_news + macro_news as needed for a rich answer (window_days 30 for "last month").
- "Tell me about X fund", overview, profile, composition, or general fund questions → ALWAYS include
  fund_nav + fund_top_stocks + fund_top_sectors + holdings_news + sector_news + macro_news (vector news is required).
- "How are top holdings working" / top N holdings performance → fund_nav + fund_top_stocks (top_n from question, often 3)
  + holdings_news with semantic_query naming those companies and earnings/results.
- Pure NAV (only asking for latest NAV number) → fund_nav only.
- Top holdings/sectors → fund_top_stocks / fund_top_sectors with top_n from question.
- Macro/sector impact without a named fund → sector_news + macro_news; sector_funds or affected_funds as needed.
- User asks for sector mutual funds (banking funds, IT funds, pharma funds, best funds in X sector):
  sector_funds with sector_name set to that sector + top_n from question (default 5–10).
  For "best performing" / "performed best" / "working well": sentiment=positive so only funds with a positive 1-month NAV are returned.
  For worst hit / adversely affected funds: sentiment=negative (largest declines).
  If the user does not ask for gainers or losers: sentiment=any.
  affected_funds is NOT required when they name the sector explicitly — use sector_funds directly.
- RBI / macro + banking impact + best banking mutual funds: macro_news_enhanced (RBI, rates) + sector_news
  (banking credit, NIM) + sector_funds (sector_name banking and financial services, top_n 5).
- Broad "what is happening in the market now/today" (no named fund) → common_market_news ONLY (not macro_news).
- Combined market + sector beneficiaries (no named fund), e.g. "what's happening in the market now and which sectors will be positively affected":
  sentiment=positive (or negative if user asks who is hurt), answer_parts must list BOTH sub-questions explicitly.
  tools: common_market_news (window_days 30) + sector_news with semantic_query like
  "India sector gainers beneficiaries export IT banking pharma PSU banks macro" — NOT the user's full sentence.
  entities[] may be empty. Do NOT add macro_news alongside common_market_news.
- Combined market + sector + mutual funds (e.g. "tell me what's happening in the market right now and what are the sectors performing well and then which mutual funds are working well"):
  sentiment=positive (or negative if asked about worst hit/falling, any if neutral).
  answer_parts must mention market conditions, performing sectors, and corresponding top mutual funds.
  tools: common_market_news (window_days 30) + sector_news.
  affected_funds=after_news, affected_funds_top_n=6.
- "How is RBI / oil / inflation affecting markets?" with no fund → macro_news_enhanced (+ sector_news if sector named).
- Crude/oil/RBI → macro_news + sector_news with strong semantic_query (India markets, sectors).
- semantic_query: dense keywords for vector search, NOT the user's full sentence.
- affected_funds=after_news when sectors must be inferred from news first; now when sectors listed in question.

CROSS-IMPACT (macro driver × named fund):
- "Is gold/oil/rates affecting [Fund]?" → fund_nav + fund_top_stocks + fund_top_sectors + metals_spot (if gold/silver)
  + macro_news with search_focus per driver (e.g. gold) + portfolio news via holdings/sector layers.
- Answer indirect channels via the fund's sectors/holdings; do not stop at "fund does not hold gold".

GOLD / SILVER / BULLION (multi-entity):
- User asks why gold AND silver moved → TWO separate macro_news tools:
  one search_focus "gold" with semantic_query about gold drivers in India;
  one search_focus "silver" with semantic_query about silver drivers.
- Always add metals_spot and sector_funds (precious metals exposure) when they ask about mutual funds affected.
- "reason" / "why" questions MUST include macro_news per metal mentioned — never answer why from spot prices alone.

EXAMPLE declined_parts:
Q: How is HDFC Defence performing, should I buy?
answer_parts: "HDFC Defence Fund recent performance and context"
declined_parts: ["should I buy"]
tools: fund_nav, fund_top_stocks, holdings_news, ...
"""


def plan_query(
    question: str,
    *,
    query_log: QueryLogger | None = None,
) -> AskPlan:
    q = (question or "").strip()
    if not q:
        return AskPlan(
            decline_entirely=True,
            decline_message="Please enter a question about funds, sectors, or market news.",
        )

    settings = get_settings()
    if not llm_api_key_configured(settings):
        if query_log is not None:
            query_log.write("PLANNER error=no_llm_api_key")
        return AskPlan(
            decline_entirely=True,
            decline_message="LLM API key is not configured. Cannot run the ask pipeline.",
        )

    started = time.perf_counter()
    try:
        res = call_json_llm(
            system_prompt=PLANNER_SYSTEM,
            user_content=f"Question:\n{q}",
            model_override=router_model(settings),
            max_tokens=max(settings.router_max_tokens, 1200),
            temperature=0.0,
            query_log=query_log,
        )
        parsed = res.parsed if isinstance(getattr(res, "parsed", None), dict) else None
        if not isinstance(parsed, dict):
            parsed = parse_json_from_text(res.raw_text) or {}
        if not parsed:
            raise ValueError("planner returned no JSON object")
        plan = AskPlan.from_dict(parsed)
        if not plan.answer_parts:
            plan.answer_parts = q
        if not plan.tools and not plan.decline_entirely:
            res2 = call_json_llm(
                system_prompt=PLANNER_SYSTEM,
                user_content=(
                    f"Question:\n{q}\n\n"
                    "Your previous response had no tools array or it was empty. "
                    "Return valid JSON with at least one appropriate tool."
                ),
                model_override=router_model(settings),
                max_tokens=max(settings.router_max_tokens, 1200),
                temperature=0.0,
                query_log=query_log,
            )
            parsed2 = res2.parsed if isinstance(getattr(res2, "parsed", None), dict) else None
            if not isinstance(parsed2, dict):
                parsed2 = parse_json_from_text(res2.raw_text) or {}
            if parsed2:
                plan = AskPlan.from_dict(parsed2)
                if not plan.answer_parts:
                    plan.answer_parts = q
        if query_log is not None:
            query_log.write(
                f"PLANNER ok duration={time.perf_counter() - started:.2f}s "
                f"sentiment={plan.sentiment} tools={len(plan.tools)} entities={len(plan.entities)}"
            )
            query_log.log_stage("planner", raw_json=parsed, sentiment=plan.sentiment)
        return plan
    except Exception as exc:
        logger.warning("planner LLM failed: %s", exc)
        if query_log is not None:
            query_log.write(f"PLANNER error={exc}")
        return AskPlan(
            decline_entirely=True,
            decline_message=f"Query planning failed: {exc}",
        )


# Legacy import shim — old tests/modules may import decompose_query
def decompose_query(question: str, *, query_log: QueryLogger | None = None):
    """Deprecated: use plan_query. Maps AskPlan to legacy QueryPlan for transitional imports."""
    from news_rag.query_plan import DataNeed, QueryPlan, SubQuery

    plan = plan_query(question, query_log=query_log)
    if plan.decline_entirely:
        return QueryPlan(sub_queries=[], source="planner_decline")
    needs = []
    for t in plan.tools:
        tool = t.tool
        if tool == "fund_top_stocks":
            tool = "fund_holdings"
        elif tool == "fund_top_sectors":
            tool = "fund_sectors"
        elif tool in ("holdings_news", "sector_news", "macro_news"):
            tool = "news_search"
        need = DataNeed(
            tool=tool,
            top_n=t.top_n,
            semantic_query=t.semantic_query,
            window_days=t.window_days,
            sector_name=t.sector_name,
            stock_name=t.stock_name,
        )
        if plan.entities and t.fund_entity_index is not None:
            ent = plan.entities[t.fund_entity_index] if t.fund_entity_index < len(plan.entities) else None
            if ent:
                need.fund_raw = ent.cleaned_phrase or ent.raw
        needs.append(need)
    sq = SubQuery(
        id="Q1",
        text=plan.answer_parts or question,
        answer_style="news_brief",
        needs_reasoning=True,
        data_needs=needs,
    )
    return QueryPlan(sub_queries=[sq], source="llm", raw_json=plan.raw_json)


def reconcile_plan_with_catalog(plan, question: str, *, query_log: QueryLogger | None = None):
    """Deprecated shim."""
    return plan


SCOPE_REFINER_SYSTEM = """Given a fund impact question, pick news search targets from the ACTUAL portfolio.
Return ONLY JSON:
{"news_entities":["Company or sector name max 8"],"news_topics":["topic phrases"],"search_mode":"event_only"|"entities_only"|"event_plus_entities"}
"""


def portfolio_scope_fallback(
    holdings: list,
    sectors: list | None = None,
):
    from news_rag.query_plan import ScopeRefinement

    entities = [str(h.get("name") or "").strip() for h in holdings[:10] if h.get("name")]
    if entities:
        return ScopeRefinement(news_entities=entities, news_topics=[], search_mode="event_plus_entities")
    return ScopeRefinement(news_entities=[], news_topics=[], search_mode="event_only")


def refine_news_scope(
    sub_query_text: str,
    *,
    sectors: list,
    holdings: list,
    query_log: QueryLogger | None = None,
):
    from news_rag.query_plan import ScopeRefinement

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
        return ScopeRefinement.from_dict(parsed)
    except Exception as exc:
        logger.warning("scope refiner failed: %s", exc)
        return portfolio_scope_fallback(holdings, sectors)
