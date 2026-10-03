"""Agent 1: Query Router — rules first, optional LLM (set RAG_USE_LLM_ROUTER=true).

Pipeline order:
  1. Fast paths (fund facts, named-fund event impact, sector top-N discovery) — no LLM.
  2. Cheap JSON LLM router (gemini-3.5-flash-lite or RAG_ROUTER_MODEL) when RAG_USE_LLM_ROUTER=true.
  3. Heuristic fallback if LLM off, no API key, or call fails.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from news_rag.config import get_settings
from news_rag.fund_search import extract_fund_phrase_from_question, lookup_extracted_fund, resolve_fund_for_query
from news_rag.llm_client import call_json_llm, llm_api_key_configured, router_model
from news_rag.parse import classify_query_intent
from news_rag.llm_text import parse_json_from_text
from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are a fast, highly accurate financial query parser and router for an Indian investment research platform.
Your job is to classify the user's question into one structured JSON object.

SUPPORTED INTENTS:
- "fund_nav": User asks specifically about the NAV (Net Asset Value), current price, or return history of a mutual fund scheme (e.g., "What is the latest NAV of Parag Parikh Flexi Cap?", "NAV for INF879O01027", "How has WhiteOak Mid Cap fund NAV performed in the last 7 days?").
- "fund_holdings": User asks specifically for the top holdings, underlying stocks, or equity portfolio of a mutual fund (e.g., "What are the top holdings of HDFC Top 100?", "Which companies does Nippon India Growth fund own?").
- "fund_sectors": User asks specifically for the sector allocation, sector breakdown, or industry exposure of a mutual fund (e.g., "What is the sector allocation of Axis Bluechip?", "Sector breakdown for Mirae Large Cap").
- "fund_event_impact": User asks how a specific external event, policy, interest rate hike, crude price surge, tariff, or macro trend impacts a **named** mutual fund (e.g., "How does rising crude oil impact Parag Parikh Flexi Cap?", "Will RBI repo rate cut help SBI Bluechip fund?"). The fund name or ISIN must be present.
- "impact_funds": User asks which mutual funds are **most affected / top N funds** by an event or sector **without** naming one fund (e.g., "Top 5 funds affected by RBI rate hike", "Which funds are worst hit by automotive sector news?", "Top 10 funds exposed to banking after repo cut"). NOT for scheme names like "HDFC Top 100 Fund" — that is a single fund name, use fund_event_impact or fund_news instead.
- "fund_news": User asks general questions about recent news, overall performance, or what is happening with a specific mutual fund (e.g., "What is the latest news on Parag Parikh Flexi Cap?", "Why is Nippon Growth fund underperforming?").
- "single_stock": User asks about a specific company or stock (e.g., "Why is Infosys falling?", "Latest news on HDFC Bank", "What did Tata Motors announce today?").
- "sector": User asks about an entire industry or sector (e.g., "How is the Indian IT sector performing?", "Auto sales numbers in India this month", "Pharma sector USFDA inspection updates").
- "macro": User asks about macroeconomic indicators, monetary policy, currency, bond yields, or trade (e.g., "RBI repo rate decision", "India CPI retail inflation", "10-year G-sec bond yields", "USD/INR rupee exchange rate", "Union Budget capital gains tax").
- "bullion": User asks about gold, silver, or precious metals prices and market trends in India (e.g., "Gold price today in India", "Why is silver rallying?", "MCX bullion rates").
- "concept": User asks to define, explain, or understand a financial term, ratio, metric, or general investing concept (e.g., "What is NAV in mutual funds?", "Explain expense ratio", "What is EBITDA margin?", "How does an SIP work?"). Note: if asking about a general concept, fund should be empty.
- "multi": User asks multiple distinct questions combining different assets or topics in one prompt (e.g., "What is the NAV of HDFC Top 100 and why did TCS drop today?").
- "general": Broad market questions that do not fit into the specific categories above.

EXTRACTION INSTRUCTIONS:
1. "fund": If the user mentions a mutual fund name or ISIN, extract it EXACTLY as written into "name" or "isin". If the user mentions an ISIN (like INF179K01BE2), put it in "isin". If no mutual fund is asked about (e.g., a stock like "TCS", a commodity like "Gold", or a concept like "What is NAV?"), "name" and "isin" MUST be empty strings "".
2. "companies": Extract specific company or stock names mentioned (e.g., ["Infosys", "HDFC Bank"]). If none, [].
3. "event_focus": If the question is about a specific event or catalyst (e.g., "crude oil surge", "RBI repo rate hike", "USFDA warning letter", "Q3 results", "CEO resignation"), state it briefly. Else "".
4. "window_days": If a time window is specified in the prompt (e.g., "last 30 days" -> 30, "past week" -> 7, "last 3 months" -> 90, "today" / "yesterday" -> 1), extract the number of days as an integer. Otherwise null.
5. "asked": A list of 1 to 3 short phrases capturing what the user actually wants answered.

OUTPUT FORMAT: Return ONLY valid JSON matching this schema:
{
  "intent": "fund_nav" | "fund_holdings" | "fund_sectors" | "fund_event_impact" | "impact_funds" | "fund_news" | "single_stock" | "sector" | "macro" | "bullion" | "concept" | "multi" | "general",
  "fund": {
    "isin": "INF...",
    "name": "..."
  },
  "companies": ["..."],
  "event_focus": "...",
  "window_days": 7 | null,
  "asked": ["..."]
}"""

VALID_INTENTS = frozenset({
    "fund_nav",
    "fund_holdings",
    "fund_sectors",
    "fund_event_impact",
    "impact_funds",
    "fund_news",
    "single_stock",
    "sector",
    "macro",
    "bullion",
    "concept",
    "multi",
    "general",
})


@dataclass
class RouterFund:
    isin: str = ""
    name: str = ""

    def is_empty(self) -> bool:
        return not bool(self.isin.strip() or self.name.strip())


@dataclass
class RouterResult:
    intent: str
    fund: RouterFund
    companies: list[str] = field(default_factory=list)
    event_focus: str = ""
    window_days: int | None = None
    asked: list[str] = field(default_factory=list)
    raw_json: dict[str, Any] = field(default_factory=dict)
    duration_sec: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, duration_sec: float = 0.0) -> RouterResult:
        raw_intent = str(data.get("intent") or "general").strip().lower()
        if raw_intent not in VALID_INTENTS:
            raw_intent = "general"

        fund_dict = data.get("fund")
        if isinstance(fund_dict, dict):
            isin = str(fund_dict.get("isin") or "").strip()
            name = str(fund_dict.get("name") or "").strip()
        elif isinstance(fund_dict, str) and fund_dict.strip():
            if fund_dict.strip().upper().startswith("INF"):
                isin = fund_dict.strip().upper()
                name = ""
            else:
                isin = ""
                name = fund_dict.strip()
        else:
            isin = ""
            name = ""

        companies_raw = data.get("companies") or []
        companies = [str(c).strip() for c in companies_raw if str(c).strip()] if isinstance(companies_raw, list) else []

        event_focus = str(data.get("event_focus") or "").strip()

        window_days_raw = data.get("window_days")
        window_days = None
        if window_days_raw is not None:
            try:
                window_days = int(window_days_raw)
            except (ValueError, TypeError):
                window_days = None

        asked_raw = data.get("asked") or []
        asked = [str(a).strip() for a in asked_raw if str(a).strip()] if isinstance(asked_raw, list) else []

        return cls(
            intent=raw_intent,
            fund=RouterFund(isin=isin, name=name),
            companies=companies,
            event_focus=event_focus,
            window_days=window_days,
            asked=asked,
            raw_json=data,
            duration_sec=duration_sec,
        )


_ISIN_IN_TEXT = re.compile(r"\b(INF[A-Z0-9]{9})\b", re.I)


_SCHEME_SHAPE = re.compile(
    r"\b(flexi|large|mid|small|multi|micro|cap|elss|index|etf|ppfas|parag|blue\s*chip|"
    r"hdfc|icici|sbi|axis|kotak|nippon|mirae|uti|whiteoak|quant|bandhan)\b",
    re.I,
)


def try_fast_fund_fact_route(question: str) -> RouterResult | None:
    """Rule-based router for fund NAV / holdings / sectors — no LLM."""
    q = (question or "").strip()
    if not q:
        return None
    lower = q.lower()
    if "mutual fund" in lower and "what is" in lower:
        return None

    isin_m = _ISIN_IN_TEXT.search(q)
    isin = isin_m.group(1).upper() if isin_m else ""
    ext_isin, ext_name = extract_fund_phrase_from_question(q)
    if not isin and ext_isin:
        isin = ext_isin

    intent: str | None = None
    sector_terms = ("sector allocation", "sector breakdown", "sector exposure", "sectors", "sector")
    holdings_terms = ("holdings", "holding", "stocks held", "portfolio stocks", "top stocks", "underlying stocks")
    nav_terms = ("nav", "net asset value")

    if any(t in lower for t in sector_terms):
        intent = "fund_sectors"
    elif any(t in lower for t in holdings_terms):
        intent = "fund_holdings"
    elif any(re.search(rf"\b{re.escape(t)}\b", lower) for t in nav_terms):
        intent = "fund_nav"

    if not intent:
        return None

    fund_name = ext_name
    if not fund_name and not isin:
        m2 = re.search(r"\b(in|of|for)\s+(.+?)(?:\?|$)", q, re.I)
        if m2:
            fund_name = m2.group(2).strip().rstrip("?")

    has_scheme = bool(isin) or bool(fund_name) or _SCHEME_SHAPE.search(q)
    if not has_scheme:
        return None

    if not fund_name and not isin:
        return None

    return RouterResult(
        intent=intent,
        fund=RouterFund(isin=isin, name=fund_name if not isin else ""),
        companies=[],
        event_focus="",
        window_days=None,
        asked=[q],
        raw_json={"fast_route": True},
        duration_sec=0.0,
    )


def _enrich_router_fund_from_question(result: RouterResult, question: str) -> RouterResult:
    """Fill missing/wrong fund fields using question text + index lookup."""
    detail, amb, _close = resolve_fund_for_query(
        question,
        isin=result.fund.isin,
        name=result.fund.name,
    )
    if not detail or amb:
        ext_isin, ext_name = extract_fund_phrase_from_question(question)
        if not result.fund.isin and ext_isin:
            result.fund.isin = ext_isin
        if not result.fund.name and ext_name:
            result.fund.name = ext_name
        return result
    result.fund.isin = str(detail.get("isin") or result.fund.isin or "")
    result.fund.name = str(
        detail.get("fund_short_name") or detail.get("fund_name") or result.fund.name or ""
    )
    return result


def heuristic_router_fallback(question: str) -> RouterResult:
    """Rule-based router when LLM router is off or Gemini is unavailable."""
    from news_rag.impact_gating import (
        _event_focus_from_text,
        _extract_fund_phrase,
        try_fast_fund_event_impact_route,
        try_fast_impact_funds_route,
    )

    q = (question or "").strip()
    for factory in (
        try_fast_fund_fact_route,
        try_fast_fund_event_impact_route,
        try_fast_impact_funds_route,
    ):
        hit = factory(q)
        if hit is not None:
            return hit

    isin, fund_name = _extract_fund_phrase(q)
    fund_detail, ambiguous, _close = lookup_extracted_fund(isin=isin, name=fund_name)
    intent = classify_query_intent(
        q,
        "",
        [],
        fund_detail if fund_detail and not ambiguous else None,
    )
    fund = RouterFund()
    if fund_detail and not ambiguous:
        fund = RouterFund(
            isin=str(fund_detail.get("isin") or isin or ""),
            name=str(fund_detail.get("fund_short_name") or fund_detail.get("fund_name") or fund_name),
        )
    elif isin or fund_name:
        fund = RouterFund(isin=isin, name=fund_name)

    return RouterResult(
        intent=intent,
        fund=fund,
        companies=[],
        event_focus=_event_focus_from_text(q.lower()),
        window_days=None,
        asked=[q],
        raw_json={"heuristic_router": True},
        duration_sec=0.0,
    )


def route_query(
    question: str,
    *,
    query_log: QueryLogger | None = None,
) -> RouterResult:
    """Invokes the cheap-LLM query router to extract intent, fund, companies, event focus, and time window."""
    fast = try_fast_fund_fact_route(question)
    if fast is not None:
        if query_log is not None:
            query_log.write(
                f"router_fast_path intent={fast.intent} fund_isin={fast.fund.isin} "
                f"fund_name={fast.fund.name!r}"
            )
        return fast

    from news_rag.impact_gating import try_fast_fund_event_impact_route, try_fast_impact_funds_route

    fund_event_fast = try_fast_fund_event_impact_route(question)
    if fund_event_fast is not None:
        if query_log is not None:
            query_log.write(
                f"router_fast_path intent={fund_event_fast.intent} "
                f"event_focus={fund_event_fast.event_focus!r} "
                f"fund_isin={fund_event_fast.fund.isin} fund_name={fund_event_fast.fund.name!r}"
            )
        return fund_event_fast

    impact_fast = try_fast_impact_funds_route(question)
    if impact_fast is not None:
        if query_log is not None:
            query_log.write(
                f"router_fast_path intent={impact_fast.intent} event_focus={impact_fast.event_focus!r} "
                f"ranking_mode=sector_discovery"
            )
        return impact_fast

    settings = get_settings()
    if not settings.rag_use_llm_router or not llm_api_key_configured(settings):
        result = heuristic_router_fallback(question)
        if query_log is not None:
            query_log.write(
                f"router_heuristic intent={result.intent} fund_isin={result.fund.isin} "
                f"fund_name={result.fund.name!r} event_focus={result.event_focus!r} "
                f"llm_router_skipped=true rag_use_llm_router={settings.rag_use_llm_router} "
                f"llm_key_configured={llm_api_key_configured(settings)}"
            )
        return result

    user_content = f"User Question: {question.strip()}"
    chosen_router_model = router_model(settings)
    if query_log is not None:
        query_log.write(f"router_llm_start model={chosen_router_model}")

    try:
        res = call_json_llm(
            system_prompt=ROUTER_SYSTEM_PROMPT,
            user_content=user_content,
            model_override=chosen_router_model,
            max_tokens=settings.router_max_tokens,
            temperature=0.0,
            query_log=query_log,
        )
    except Exception as exc:
        if query_log is not None:
            query_log.write(f"router_llm_failed fallback=heuristic error={exc}")
        return heuristic_router_fallback(question)

    parsed_json = parse_json_from_text(res.raw_text)
    if not parsed_json:
        logger.warning("Query router returned unparseable JSON: %r", res.raw_text)
        if query_log is not None:
            query_log.write(f"router_error unparseable_json text={res.raw_text[:300]}")
        return heuristic_router_fallback(question)

    result = RouterResult.from_dict(parsed_json, duration_sec=res.duration_sec)
    result = _enrich_router_fund_from_question(result, question.strip())
    result.raw_json = {**(result.raw_json or {}), "llm_router": True, "router_model": chosen_router_model}
    if query_log is not None:
        query_log.write(
            f"router_llm_result intent={result.intent} model={chosen_router_model} "
            f"fund_isin={result.fund.isin} fund_name={result.fund.name} "
            f"companies={result.companies} event_focus={result.event_focus} "
            f"window_days={result.window_days} duration={result.duration_sec:.2f}s"
        )
    return result
