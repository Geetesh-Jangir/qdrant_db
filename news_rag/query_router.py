"""Agent 1: Query Router — fast cheap-LLM query parser and intent classifier."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from news_rag.config import get_settings
from news_rag.llm_client import call_json_llm, router_model
from news_rag.llm_text import parse_json_from_text
from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are a fast, highly accurate financial query parser and router for an Indian investment research platform.
Your job is to classify the user's question into one structured JSON object.

SUPPORTED INTENTS:
- "fund_nav": User asks specifically about the NAV (Net Asset Value), current price, or return history of a mutual fund scheme (e.g., "What is the latest NAV of Parag Parikh Flexi Cap?", "NAV for INF879O01027", "How has WhiteOak Mid Cap fund NAV performed in the last 7 days?").
- "fund_holdings": User asks specifically for the top holdings, underlying stocks, or equity portfolio of a mutual fund (e.g., "What are the top holdings of HDFC Top 100?", "Which companies does Nippon India Growth fund own?").
- "fund_sectors": User asks specifically for the sector allocation, sector breakdown, or industry exposure of a mutual fund (e.g., "What is the sector allocation of Axis Bluechip?", "Sector breakdown for Mirae Large Cap").
- "fund_event_impact": User asks how a specific external event, policy, interest rate hike, crude price surge, tariff, or macro trend impacts a mutual fund (e.g., "How does rising crude oil impact Parag Parikh Flexi Cap?", "Will RBI repo rate cut help SBI Bluechip fund?").
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
  "intent": "fund_nav" | "fund_holdings" | "fund_sectors" | "fund_event_impact" | "fund_news" | "single_stock" | "sector" | "macro" | "bullion" | "concept" | "multi" | "general",
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

    fund_name = ""
    intent: str | None = None

    if re.search(r"\b(sector|sectors)\b", lower) and re.search(r"\bfund\b", lower):
        intent = "fund_sectors"
        m = re.search(
            r"(?:sectors?\s+(?:in|of|for)\s+|allocation\s+(?:of|for)\s+)(.+?)(?:\?|$)",
            q,
            re.I,
        )
        if m:
            fund_name = m.group(1).strip().rstrip("?")
    elif re.search(r"\b(holdings?|stocks held|portfolio stocks)\b", lower) and re.search(
        r"\bfund\b", lower
    ):
        intent = "fund_holdings"
        m = re.search(r"(?:holdings?\s+(?:of|in|for)\s+|(?:of|in|for)\s+)(.+?fund.*?)(?:\?|$)", q, re.I)
        if m:
            fund_name = m.group(1).strip().rstrip("?")
    elif re.search(r"\bnav\b", lower) and re.search(r"\bfund\b", lower):
        intent = "fund_nav"
        m = re.search(r"(?:nav\s+(?:of|for)\s+|(?:of|for)\s+)(.+?)(?:\?|$)", q, re.I)
        if m:
            fund_name = m.group(1).strip().rstrip("?")

    if not intent:
        return None

    if not fund_name and not isin:
        m2 = re.search(r"\b(in|of)\s+(.+?fund)\b", q, re.I)
        if m2:
            fund_name = m2.group(2).strip().rstrip("?")

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

    settings = get_settings()
    user_content = f"User Question: {question.strip()}"

    res = call_json_llm(
        system_prompt=ROUTER_SYSTEM_PROMPT,
        user_content=user_content,
        model_override=router_model(settings),
        max_tokens=settings.router_max_tokens,
        temperature=0.0,
        query_log=query_log,
    )

    parsed_json = parse_json_from_text(res.raw_text)
    if not parsed_json:
        logger.warning("Query router returned unparseable JSON: %r", res.raw_text)
        if query_log is not None:
            query_log.write(f"router_error unparseable_json text={res.raw_text[:300]}")
        # Default fallback without full sentence fund scoring
        return RouterResult(
            intent="general",
            fund=RouterFund(),
            companies=[],
            event_focus="",
            window_days=None,
            asked=[question.strip()],
            raw_json={},
            duration_sec=res.duration_sec,
        )

    result = RouterResult.from_dict(parsed_json, duration_sec=res.duration_sec)
    if query_log is not None:
        query_log.write(
            f"router_result intent={result.intent} fund_isin={result.fund.isin} "
            f"fund_name={result.fund.name} companies={result.companies} "
            f"event_focus={result.event_focus} window_days={result.window_days} "
            f"duration={result.duration_sec:.2f}s"
        )
    return result
