"""Bounded research agent: choose tools, observe, then hand evidence to the composer."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, TYPE_CHECKING

from news_rag.article_pool import collect_bundle_articles
from news_rag.ask_execution import ExecutionBundle, PlannedTool, execute_tool_round
from news_rag.ask_plan import AskPlan
from news_rag.config import get_settings
from news_rag.guardrails import check_guardrails
from news_rag.json_util import safe_json_dumps
from news_rag.llm_client import call_json_llm, llm_api_key_configured, router_model
from news_rag.llm_text import parse_json_from_text
from news_rag.name_resolution import ResolvedNames, resolve_plan_names
from news_rag.plan_enrich import enrich_ask_plan
from news_rag.relationships import trace_relationships
from news_rag.snippet_clean import article_body_for_llm
from news_rag.stock_fund_ranking import funds_holding_stock
from news_rag.tools import run_compare_funds, run_fund_universe_discovery

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

AGENT_SYSTEM = """You are the research agent for an Indian mutual-fund and markets app.
You do not write the user-facing answer. You decide what to retrieve.
The user message is a briefing: the question, today's date, the tool catalog, data we actually have, any locally matched names, and observations from earlier rounds.
Return JSON only. Fill every field you can. Use empty arrays or null when something does not apply. Do not drop fields.

{
  "status": "need_tools" or "ready",
  "why": "What is still missing, or why the evidence is enough.",
  "question_reading": {
    "intent": "What the user wants, in your words.",
    "answer_shape": "narrative|bullets|mixed|comparison|figure",
    "must_cover": ["Points the final answer has to hit."],
    "declined_parts": [],
    "sentiment": "positive|negative|any",
    "time_window_days": null
  },
  "entities": [
    {"raw": "", "role": "fund_scheme|amc|holding|sector|macro_driver", "cleaned_phrase": "", "why": ""}
  ],
  "relationships_to_check": [
    {"driver": "", "target": "", "kind_guess": "direct|indirect|unknown", "why": ""}
  ],
  "information_gaps": ["What is still unknown."],
  "tools": [
    {
      "tool": "name",
      "purpose": "Why this call, and which earlier result it uses.",
      "depends_on": "",
      "fund_entity_index": null,
      "semantic_query": "",
      "sector_name": "",
      "stock_name": "",
      "top_n": null,
      "window_days": null,
      "entity_filters": [],
      "search_focus": "",
      "category": "",
      "amc": "",
      "keyword": "",
      "return_window": "1W|1M|3M|1Y",
      "compare_on": "nav|sectors|holdings|all",
      "direction": "positive|negative|any",
      "driver": "",
      "target": "",
      "theme": ""
    }
  ]
}

CHOOSE TOOLS
- Read the question and the observations you already have. Call the smallest set that can answer it.
- A later call should use names the earlier call returned: holdings to news, sectors found in news to fund ranking, a driver plus a fund to trace_relationships.
- Prefer a narrow tool over a market-wide search when the user named a fund, sector, stock, or driver.
- Do not call a tool again for data you already have.
- "Right now" means the recent week. Leave window_days null unless the user named a period. Do not use a one-day window.
- sentiment positive means the user wants to know who benefits. It is not a filter for only upbeat headlines.
- If sector_news returns no articles, do not treat that as "no sector benefits". Read the market articles for the industries they name.
- status=ready when you could explain the mechanism with the evidence in hand, including an honest gap.
- Never request buy/sell advice. Factual performance, news, and exposure are in scope.

TOOL CATALOG
- fund_nav: latest NAV, returns, 52-week high and low, benchmark, scheme type. Needs a fund_scheme entity.
- fund_top_stocks: top holdings and weights. Needs a fund. Later news tools can use those names.
- fund_top_sectors: sector weights. Needs a fund.
- holdings_news: news on named holdings. Set entity_filters from holdings already retrieved.
- sector_news: news on a sector. Set sector_name or entity_filters.
- macro_news: one narrow news search. Set semantic_query to a few search keywords, not the user's full sentence.
- macro_news_enhanced: one macro driver (RBI, oil, inflation, flows) with clustering inside the tool.
- common_market_news: broad Indian market snapshot. Use when the user asks what is happening overall.
- When the user also asks which sectors benefit, are positively affected, or are working well, set sentiment to positive and call sector_news in the same round. Use a short semantic_query such as sectors benefiting from the news, never the full user sentence. common_market_news alone does not answer a sector question.
- Call news tools only when the user asks what is happening in the market or in the news. A question that only names an AMC, a category, a stock, or a performance window does not need a news search.
- screen_funds: which funds match a sector, category, AMC, or stock, and how they moved. Set any of sector_name, category, amc, stock_name. direction is positive, negative, or any. return_window is 1W, 1M, 3M, or 1Y. Use 1M when they ask how funds are performing and do not name a period. Last week is 1W. Last month is 1M. top_n is the count they asked for. A driver written in the question is sector_name. Do not wait for a news theme to invent it. Positive keeps only gains in that window. Negative keeps only declines.
- When the user asks which funds are affected by a driver such as crude, rates, or the news, call a news tool first, then screen_funds. Set direction to positive when they want who benefits, negative when they want who is hurt, and any when they only say affected. Do not set sector_name to the driver. The screen reads the articles and the sector list, then ranks funds in the sectors that match that direction.
- When the user asks which funds are performing, or names an AMC, category, sector, or stock, call screen_funds and set direction and return_window from the question. A named sector such as finance is sector_name. A driver is not.
- sector_funds and affected_funds use the same window and direction. Prefer screen_funds.
- affected_funds: several sectors in one ranking. Set sector_name or pass the sectors already found.
- metals_spot: gold and silver spot moves.
- stock_snapshot: price snapshot for one stock. Set stock_name.
- expand_news: more article bodies for a theme already returned by common_market_news or macro_news_enhanced. Set theme to that label.
- trace_relationships: direct holding or sector weight versus indirect names that co-occur in retrieved articles. Set driver and target.
- fund_universe_search: list regular-growth schemes by category, AMC, or keyword when no return filter is needed. Set category, amc, keyword, top_n. Prefer screen_funds when performance or direction matters.
- compare_funds: only when the user asks to compare. Set entity_filters to the fund names. If they did not name the funds, call screen_funds first and set depends_on to that call. compare_on is nav, sectors, holdings, or all. return_window is the same window as the screen. Fetch only the blocks they asked for.
- funds_holding_stock: schemes that hold a stock, plus the archive count when the scan finds no names. Set stock_name. Prefer screen_funds with stock_name when a return window is also asked.

DATA ON HAND
News archive, fund NAV and holdings, sector-to-fund weights, metals spot, regular-growth fund universe.
Not on hand: expense ratio, AUM, TER, fund manager, riskometer. Do not plan a tool for those.
"""

_STRING = {"type": "string"}

AGENT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": _STRING,
        "why": _STRING,
        "question_reading": {
            "type": "object",
            "properties": {
                "intent": _STRING,
                "answer_shape": _STRING,
                "must_cover": {"type": "array", "items": _STRING},
                "declined_parts": {"type": "array", "items": _STRING},
                "sentiment": _STRING,
                "time_window_days": _STRING,
            },
        },
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "raw": _STRING,
                    "role": _STRING,
                    "cleaned_phrase": _STRING,
                    "why": _STRING,
                },
            },
        },
        "relationships_to_check": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "driver": _STRING,
                    "target": _STRING,
                    "kind_guess": _STRING,
                    "why": _STRING,
                },
            },
        },
        "information_gaps": {"type": "array", "items": _STRING},
        "tools": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": _STRING,
                    "purpose": _STRING,
                    "depends_on": _STRING,
                    "semantic_query": _STRING,
                    "sector_name": _STRING,
                    "stock_name": _STRING,
                    "search_focus": _STRING,
                    "category": _STRING,
                    "amc": _STRING,
                    "keyword": _STRING,
                    "return_window": _STRING,
                    "compare_on": _STRING,
                    "direction": _STRING,
                    "driver": _STRING,
                    "target": _STRING,
                    "theme": _STRING,
                    "entity_filters": {"type": "array", "items": _STRING},
                    "fund_entity_indexes": {"type": "array", "items": _STRING},
                    "fund_entity_index": _STRING,
                    "top_n": _STRING,
                    "window_days": _STRING,
                },
            },
        },
    },
    "required": ["status", "why", "question_reading", "entities", "relationships_to_check", "information_gaps", "tools"],
}

_SPECIAL_TOOLS = frozenset(
    {
        "trace_relationships",
        "expand_news",
        "fund_universe_search",
        "compare_funds",
        "funds_holding_stock",
    }
)


@dataclass
class AgentRun:
    plan: AskPlan
    bundle: ExecutionBundle
    research: dict[str, Any] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)
    rounds: int = 0
    declined: bool = False
    decline_message: str = ""
    ambiguous: bool = False
    close_matches: list[str] = field(default_factory=list)
    finish_reason: str = ""
    repaired: bool = False


def _local_name_matches(question: str) -> list[dict[str, Any]]:
    from news_rag.fund_search import lookup_extracted_fund

    phrases: list[str] = []
    for match in re.finditer(r"\bINF[0-9A-Z]{9}\b", question or "", re.I):
        phrases.append(match.group(0))
    if re.search(r"\bfund\b", question or "", re.I):
        phrases.append(question)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for phrase in phrases[:3]:
        detail, ambiguous, close = lookup_extracted_fund(name=phrase)
        canonical = ""
        if detail and not ambiguous:
            canonical = str(detail.get("fund_short_name") or detail.get("fund_name") or "")
        key = canonical or "|".join(close[:3])
        if not key or key in seen:
            continue
        if not canonical and not close:
            continue
        seen.add(key)
        out.append(
            {
                "phrase": phrase if phrase != question else "",
                "canonical": canonical,
                "ambiguous": bool(ambiguous),
                "close_matches": list(close[:5]),
            }
        )
    return out


def _briefing(
    question: str,
    observations: list[dict[str, Any]],
    reading: dict[str, Any] | None,
    judge_note: str,
) -> list[dict[str, str]]:
    blocks = [
        {"name": "question", "text": question},
        {"name": "today", "text": date.today().isoformat()},
        {"name": "local_name_matches", "text": safe_json_dumps(_local_name_matches(question))},
        {"name": "question_reading", "text": safe_json_dumps(reading or {})},
        {"name": "observations", "text": safe_json_dumps(observations)},
    ]
    if judge_note:
        blocks.append({"name": "grounding_note", "text": judge_note})
    return blocks


def _parse_decision(raw: dict[str, Any]) -> tuple[str, AskPlan]:
    status = str(raw.get("status") or "ready").strip().lower()
    if status not in ("need_tools", "ready"):
        status = "ready" if not raw.get("tools") else "need_tools"
    plan = AskPlan.from_dict(raw)
    return status, plan


def _accumulate(base: AskPlan | None, fresh: AskPlan) -> AskPlan:
    if base is None:
        return fresh
    if fresh.question_reading.get("intent") or fresh.question_reading.get("must_cover"):
        base.question_reading = fresh.question_reading
    if fresh.information_gaps:
        base.information_gaps = fresh.information_gaps
    if fresh.relationships_to_check:
        base.relationships_to_check = fresh.relationships_to_check
    if fresh.entities:
        base.entities = fresh.entities
    if fresh.declined_parts:
        base.declined_parts = fresh.declined_parts
    if fresh.sentiment:
        base.sentiment = fresh.sentiment
    if fresh.answer_parts:
        base.answer_parts = fresh.answer_parts
    seen = {(t.tool, t.semantic_query, t.sector_name, t.stock_name, t.fund_entity_index) for t in base.tools}
    for tool in fresh.tools:
        key = (tool.tool, tool.semantic_query, tool.sector_name, tool.stock_name, tool.fund_entity_index)
        if key not in seen:
            base.tools.append(tool)
            seen.add(key)
    base.raw_json = fresh.raw_json or base.raw_json
    return base


_FUND_NAME_RE = re.compile(r"\bfunds?\b|\bschemes?\b|\bmutual funds?\b", re.I)
_FUND_INTENT_RE = re.compile(
    r"benefit|benefited|affected|working|performing|gain|hurt|positive|negative|compare|which|name|any\b|provided by|from\b",
    re.I,
)


def question_wants_fund_names(question: str) -> bool:
    text = question or ""
    return bool(_FUND_NAME_RE.search(text) and _FUND_INTENT_RE.search(text))


def _has_fund_ranking(bundle: ExecutionBundle | None) -> bool:
    if bundle is None:
        return False
    for key, payload in bundle.tool_results.items():
        if not (
            key.startswith("sector_funds")
            or key.startswith("affected_funds")
            or key.startswith("screen_funds")
        ):
            continue
        data = (payload or {}).get("data") or {}
        rows = data.get("rankings") or data.get("rows") or data.get("funds") or []
        if any(isinstance(row, dict) and (row.get("fund_name") or row.get("isin")) for row in rows):
            return True
    return False


def _sectors_from_observations(observations: list[dict[str, Any]], *, limit: int = 4) -> list[str]:
    names: list[str] = []
    for obs in observations:
        for name in obs.get("entities_found") or []:
            cleaned = str(name).strip()
            if cleaned and cleaned not in names:
                names.append(cleaned)
        for article in obs.get("articles") or []:
            if not isinstance(article, dict):
                continue
            for sector in article.get("sectors") or []:
                cleaned = str(sector).strip()
                if cleaned and cleaned not in names:
                    names.append(cleaned)
    return names[:limit]


def _direction_for_funds(question: str, plan: AskPlan) -> str:
    if plan.sentiment in ("positive", "negative"):
        return plan.sentiment
    low = (question or "").lower()
    if any(word in low for word in ("hurt", "negatively", "losing", "worst")):
        return "negative"
    if any(word in low for word in ("benefit", "positive", "working well", "performing", "gain")):
        return "positive"
    return "any"


def _fill_fund_ranking_gap(
    question: str,
    plan: AskPlan,
    bundle: ExecutionBundle,
    observations: list[dict[str, Any]],
    *,
    date_from: str | None,
    date_to: str | None,
    min_impact: int | None,
    source: str | None,
    direction: str | None,
    query_log: QueryLogger | None,
) -> None:
    """If fund names were asked and no screen rows came back, screen from the question or from sectors the news supports."""
    if not question_wants_fund_names(question) or _has_fund_ranking(bundle):
        return
    from news_rag.affected_sectors import question_needs_affected_sectors
    from news_rag.article_pool import collect_bundle_articles
    from news_rag.tools import (
        explicit_fund_count,
        infer_return_window,
        run_funds_for_affected_question,
        run_screen_funds,
        screen_hints_from_question,
    )

    hints = screen_hints_from_question(question)
    asked = _direction_for_funds(question, plan)
    if question_needs_affected_sectors(question):
        if asked in ("positive", "negative"):
            plan.sentiment = asked
        result = run_funds_for_affected_question(
            question=question,
            direction=asked,
            articles=collect_bundle_articles(bundle),
            top_n=explicit_fund_count(question) or 5,
            return_window=infer_return_window(question),
            query_log=query_log,
        )
        bundle.tool_results[f"affected_sectors_{len(bundle.tool_results)}"] = result
        observations.append(
            _observation(
                PlannedTool(tool="screen_funds", direction=asked, purpose="Sectors from the news, then funds."),
                result,
            )
        )
        return
    if asked in ("positive", "negative"):
        plan.sentiment = asked
    window = infer_return_window(question)
    count = explicit_fund_count(question) or 5
    tool = PlannedTool(
        tool="screen_funds",
        sector_name=hints.get("sector_name") or "",
        category=hints.get("category") or "",
        amc=hints.get("amc") or "",
        stock_name=hints.get("stock_name") or "",
        direction=asked,
        return_window=window,
        top_n=count,
        purpose="Screen funds from the sector, category, or AMC written in the question.",
    )
    plan.tools.append(tool)
    if query_log is not None:
        query_log.write(
            "FUND_GAP "
            f"sector={tool.sector_name} category={tool.category} amc={tool.amc} "
            f"stock={tool.stock_name} direction={asked} window={window}"
        )
    result = run_screen_funds(
        sector_name=tool.sector_name,
        category=tool.category,
        amc=tool.amc,
        stock_name=tool.stock_name,
        direction=asked,
        return_window=window,
        top_n=count,
        question=question,
    )
    bundle.tool_results[f"screen_funds_gap_{len(bundle.tool_results)}"] = result
    observations.append(_observation(tool, result))


def _apply_reading_window(plan: AskPlan, tools: list[PlannedTool]) -> None:
    raw = (plan.question_reading or {}).get("time_window_days")
    try:
        window = int(raw) if raw is not None else None
    except (TypeError, ValueError):
        window = None
    if not window:
        return
    for tool in tools:
        if tool.window_days is None and tool.tool in (
            "holdings_news",
            "sector_news",
            "macro_news",
            "macro_news_enhanced",
            "common_market_news",
            "expand_news",
        ):
            tool.window_days = window


def _slim_articles(articles: list[Any], *, limit: int = 6) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for article in articles:
        if not isinstance(article, dict):
            continue
        rows.append(
            {
                "title": article.get("title"),
                "direction": article.get("direction"),
                "sectors": article.get("sector_names") or article.get("sectors") or [],
                "entities": list(article.get("entity_names") or [])[:6],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _observation(tool: PlannedTool, result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    articles = list(data.get("articles") or []) + list(data.get("representative_articles") or [])
    for cluster in data.get("clusters") or []:
        if isinstance(cluster, dict):
            articles.extend(cluster.get("articles") or [])
    row_source = (
        data.get("rows")
        or data.get("rankings")
        or data.get("funds")
        or data.get("direct")
        or []
    )
    rows = [row for row in row_source if isinstance(row, dict)][:8] if isinstance(row_source, list) else []
    entities: list[str] = []
    for row in rows:
        for key in ("name", "fund_name", "sector", "stock_name"):
            value = str(row.get(key) or "").strip()
            if value and value not in entities:
                entities.append(value)
    numbers: list[str] = []
    for row in rows:
        for key in ("percentage", "weight_pct", "nav", "return_1m_pct", "sector_weight_pct", "fund_count"):
            if row.get(key) is not None:
                numbers.append(f"{key}={row.get(key)}")
    themes: list[str] = []
    for cluster in data.get("clusters") or []:
        if not isinstance(cluster, dict):
            continue
        label = str(cluster.get("label") or "").strip()
        if label and label not in themes:
            themes.append(label)
        for sector in cluster.get("sectors") or []:
            name = str(sector).strip()
            if name and name not in entities:
                entities.append(name)
    summary = str(result.get("error") or data.get("note") or "")
    if not summary and themes:
        summary = f"Themes: {', '.join(themes[:6])} ({len(articles)} articles)."
    if not summary:
        summary = f"{tool.tool} returned {len(articles)} articles and {len(rows)} rows."
    return {
        "tool": tool.tool,
        "ok": bool(result.get("ok")),
        "error": str(result.get("error") or ""),
        "purpose": tool.purpose,
        "summary": summary[:500],
        "entities_found": entities[:12],
        "numbers": numbers[:12],
        "counts": {"articles": len(articles), "rows": len(rows)},
        "rows": rows,
        "articles": _slim_articles(articles),
    }


def _details_for_compare(plan: AskPlan, bundle: ExecutionBundle, tool: PlannedTool) -> list[dict[str, Any]]:
    indexes = list(tool.fund_entity_indexes)
    if tool.fund_entity_index is not None:
        indexes.append(tool.fund_entity_index)
    details: list[dict[str, Any]] = []
    for index in indexes:
        detail = None
        if 0 <= index < len(plan.entities):
            from news_rag.ask_execution import detail_for_tool

            probe = PlannedTool(tool="fund_nav", fund_entity_index=index)
            detail = detail_for_tool(plan, bundle.names, probe)
        if detail:
            details.append(detail)
    if details:
        return details
    from news_rag.fund_search import lookup_extracted_fund

    for phrase in tool.entity_filters:
        detail, ambiguous, _close = lookup_extracted_fund(name=phrase)
        if detail and not ambiguous:
            details.append(detail)
    return details


def _rows_for_compare(bundle: ExecutionBundle, tool: PlannedTool) -> list[dict[str, Any]]:
    """Rows from the screening call this compare depends on, or the latest screen."""
    wanted = (tool.depends_on or "").strip()
    picked: list[dict[str, Any]] = []
    for key, payload in bundle.tool_results.items():
        if wanted and wanted not in key and not key.startswith(wanted):
            continue
        if not (
            key.startswith("screen_funds")
            or key.startswith("sector_funds")
            or key.startswith("affected_funds")
            or (wanted and wanted in key)
        ):
            continue
        data = (payload or {}).get("data") or {}
        rows = data.get("rankings") or data.get("funds") or []
        named = [row for row in rows if isinstance(row, dict) and (row.get("fund_name") or row.get("isin"))]
        if data.get("stock_name") or tool.stock_name:
            named = [row for row in named if row.get("weight_pct") is not None or row.get("holding_name")]
        if named:
            picked = named
            if wanted or data.get("stock_name"):
                break
    limit = tool.top_n or 2
    return picked[: max(2, limit)]


def _expand_news(bundle: ExecutionBundle, tool: PlannedTool) -> dict[str, Any]:
    theme = (tool.theme or tool.semantic_query or tool.search_focus or "").strip().lower()
    extra: list[dict[str, Any]] = []
    for payload in bundle.tool_results.values():
        if not isinstance(payload, dict) or not payload.get("ok"):
            continue
        data = payload.get("data") or {}
        for cluster in data.get("clusters") or []:
            if not isinstance(cluster, dict):
                continue
            label = str(cluster.get("label") or cluster.get("theme_key") or "").lower()
            if theme and theme not in label and label not in theme:
                continue
            for article in cluster.get("articles") or []:
                if not isinstance(article, dict):
                    continue
                extra.append(
                    {
                        **article,
                        "body": article_body_for_llm(article, limit=1000),
                        "theme": cluster.get("label"),
                    }
                )
    return {"ok": True, "data": {"articles": extra, "count": len(extra), "theme": tool.theme}, "error": ""}


def _run_special(
    tool: PlannedTool,
    plan: AskPlan,
    bundle: ExecutionBundle,
) -> dict[str, Any]:
    try:
        if tool.tool == "fund_universe_search":
            return run_fund_universe_discovery(
                category=tool.category or None,
                amc=tool.amc or None,
                keyword=tool.keyword or tool.semantic_query or None,
                limit=tool.top_n or 5,
            )
        if tool.tool == "compare_funds":
            details = _details_for_compare(plan, bundle, tool)
            rows = _rows_for_compare(bundle, tool)
            holders = [row for row in rows if row.get("weight_pct") is not None or row.get("holding_name")]
            if tool.stock_name and len(holders) < 2:
                payload = funds_holding_stock(tool.stock_name, limit=max(tool.top_n or 2, 2))
                bundle.tool_results[f"funds_holding_stock_{len(bundle.tool_results)}"] = {
                    "ok": True,
                    "data": payload,
                    "error": "",
                }
                holders = [
                    row
                    for row in (payload.get("funds") or [])
                    if isinstance(row, dict) and (row.get("weight_pct") is not None or row.get("holding_name"))
                ]
            if tool.stock_name or holders:
                if len(holders) < 2:
                    return {
                        "ok": False,
                        "data": {"funds": holders, "count": len(holders)},
                        "error": "Fewer than two confirmed holders are available to compare.",
                    }
                return run_compare_funds(
                    rows=holders,
                    top_n=tool.top_n or len(holders),
                    compare_on=tool.compare_on or "sectors",
                    return_window=tool.return_window or "1M",
                )
            if len(details) < 2 and len(rows) < 2:
                return {"ok": False, "data": None, "error": "compare_funds needs at least two resolved funds"}
            return run_compare_funds(
                details if len(details) >= 2 else None,
                rows=rows if len(details) < 2 else None,
                top_n=tool.top_n or max(2, len(rows) or 2),
                compare_on=tool.compare_on or "all",
                return_window=tool.return_window or "1M",
            )
        if tool.tool == "funds_holding_stock":
            payload = funds_holding_stock(tool.stock_name or tool.semantic_query, limit=tool.top_n or 10)
            return {"ok": True, "data": payload, "error": ""}
        if tool.tool == "trace_relationships":
            articles = collect_bundle_articles(bundle)
            fund_name = ""
            if bundle.fund_nav_data:
                fund_name = str(bundle.fund_nav_data.get("fund_name") or "")
            payload = trace_relationships(
                driver=tool.driver or tool.semantic_query,
                target=tool.target or tool.sector_name or fund_name,
                holdings_rows=bundle.holdings_rows,
                sector_rows=bundle.sector_rows,
                articles=articles,
                fund_name=fund_name,
            )
            return {"ok": True, "data": payload, "error": ""}
        if tool.tool == "expand_news":
            return _expand_news(bundle, tool)
    except Exception as exc:
        return {"ok": False, "data": None, "error": str(exc)}
    return {"ok": False, "data": None, "error": f"unknown tool {tool.tool}"}


def _research_payload(plan: AskPlan, rounds: int) -> dict[str, Any]:
    return {
        "question_reading": plan.question_reading,
        "entities": [
            {
                "raw": ent.raw,
                "role": ent.role,
                "cleaned_phrase": ent.cleaned_phrase,
                "why": ent.why,
            }
            for ent in plan.entities
        ],
        "relationships_to_check": plan.relationships_to_check,
        "information_gaps": plan.information_gaps,
        "tools": [
            {
                "tool": tool.tool,
                "purpose": tool.purpose,
                "depends_on": tool.depends_on,
                "semantic_query": tool.semantic_query,
                "sector_name": tool.sector_name,
                "stock_name": tool.stock_name,
                "fund_entity_index": tool.fund_entity_index,
            }
            for tool in plan.tools
        ],
        "rounds": rounds,
    }


def run_research_agent(
    question: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
    prior: AgentRun | None = None,
    judge_note: str = "",
) -> AgentRun:
    guard = check_guardrails(question)
    if guard.outcome == "refuse_out_of_domain" and prior is None:
        empty = AskPlan(decline_entirely=True, decline_message=guard.message)
        return AgentRun(
            plan=empty,
            bundle=ExecutionBundle(names=ResolvedNames()),
            declined=True,
            decline_message=guard.message,
        )

    settings = get_settings()
    if not llm_api_key_configured(settings):
        empty = AskPlan(decline_entirely=True, decline_message="LLM API key is not configured.")
        return AgentRun(
            plan=empty,
            bundle=ExecutionBundle(names=ResolvedNames()),
            declined=True,
            decline_message=empty.decline_message,
        )

    plan = prior.plan if prior else None
    bundle = prior.bundle if prior else None
    observations = list(prior.observations) if prior else []
    rounds = prior.rounds if prior else 0
    max_rounds = 1 if prior else max(1, int(settings.ask_agent_max_rounds))
    finish_reason = ""
    repaired = False
    note = judge_note or (plan.judge_note if plan else "")

    for _ in range(max_rounds):
        res = call_json_llm(
            system_prompt=AGENT_SYSTEM,
            user_content="",
            context_blocks=_briefing(
                question,
                observations,
                plan.question_reading if plan else {},
                note,
            ),
            model_override=router_model(settings),
            max_tokens=settings.ask_agent_max_tokens,
            temperature=0.0,
            query_log=query_log,
            response_schema=AGENT_RESPONSE_SCHEMA,
            stage="agent",
        )
        finish_reason = res.finish_reason
        repaired = repaired or bool(res.repaired)
        raw = res.parsed if isinstance(res.parsed, dict) else (parse_json_from_text(res.raw_text) or {})
        if not isinstance(raw, dict):
            raw = {}
        if query_log is not None:
            query_log.log_stage(
                "agent",
                round=rounds + 1,
                finish_reason=res.finish_reason,
                repaired=res.repaired,
                status=raw.get("status"),
                tools=[t.get("tool") for t in (raw.get("tools") or []) if isinstance(t, dict)],
            )
        status, fresh = _parse_decision(raw)
        fresh = enrich_ask_plan(question, fresh)
        plan = _accumulate(plan, fresh)
        if plan.decline_entirely:
            break
        names = resolve_plan_names(plan, query_log=query_log)
        if names.ambiguous:
            return AgentRun(
                plan=plan,
                bundle=ExecutionBundle(names=names),
                research=_research_payload(plan, rounds),
                observations=observations,
                rounds=rounds,
                ambiguous=True,
                close_matches=list(names.close_matches),
                finish_reason=finish_reason,
                repaired=repaired,
            )
        if bundle is None:
            bundle = ExecutionBundle(names=names)
        else:
            bundle.names = names
        tools = list(fresh.tools)
        _apply_reading_window(plan, tools)
        if status != "need_tools" and not tools:
            rounds += 1
            break
        if not tools:
            rounds += 1
            break
        special = [tool for tool in tools if tool.tool in _SPECIAL_TOOLS]
        standard = [tool for tool in tools if tool.tool not in _SPECIAL_TOOLS]
        if standard:
            ran = execute_tool_round(
                plan,
                standard,
                question,
                bundle,
                date_from=date_from,
                date_to=date_to,
                min_impact=min_impact,
                source=source,
                direction=direction,
                query_log=query_log,
            )
            by_tool: dict[str, list[dict[str, Any]]] = {}
            for tr in ran:
                by_tool.setdefault(tr.tool, []).append(tr.result or {"ok": False, "error": tr.error, "data": None})
            for tool in standard:
                bucket = by_tool.get(tool.tool) or []
                result = bucket.pop(0) if bucket else {"ok": False, "error": "no result", "data": None}
                observations.append(_observation(tool, result))
        for tool in special:
            result = _run_special(tool, plan, bundle)
            key = f"{tool.tool}_{rounds}_{len(bundle.tool_results)}"
            bundle.tool_results[key] = result
            observations.append(_observation(tool, result))
        rounds += 1
        if status == "ready":
            break

    if plan is None:
        plan = AskPlan(answer_parts=question)
    if bundle is None:
        bundle = ExecutionBundle(names=ResolvedNames())
    if not plan.decline_entirely:
        _fill_fund_ranking_gap(
            question,
            plan,
            bundle,
            observations,
            date_from=date_from,
            date_to=date_to,
            min_impact=min_impact,
            source=source,
            direction=direction,
            query_log=query_log,
        )
    if note:
        plan.judge_note = note
    return AgentRun(
        plan=plan,
        bundle=bundle,
        research=_research_payload(plan, rounds),
        observations=observations,
        rounds=rounds,
        finish_reason=finish_reason,
        repaired=repaired,
    )
