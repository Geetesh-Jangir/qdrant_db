"""When to use sector_to_isin_weights vs per-fund API/allisin paths."""

from __future__ import annotations

import re

from news_rag.query_router import RouterFund, RouterResult

_IMPACT_FUNDS_INTENT = "impact_funds"


def infer_ranking_limit(question: str, default: int = 5) -> int:
    m = re.search(r"\btop\s*(\d{1,2})\b", question, re.I)
    if m:
        return max(1, min(int(m.group(1)), 25))
    m2 = re.search(r"\b(\d{1,2})\s+funds?\b", question, re.I)
    if m2:
        return max(1, min(int(m2.group(1)), 25))
    return default


def infer_direction_filter(question: str, api_direction: str | None = None) -> str:
    if api_direction and api_direction.strip().lower() in ("positive", "negative"):
        return api_direction.strip().lower()
    lower = question.lower()
    if any(w in lower for w in ("benefit", "beneficiary", "positive", "gain", "rally", "boost", "help")):
        if "negative" not in lower and "hurt" not in lower:
            return "positive"
    if any(w in lower for w in ("hurt", "worst", "negative", "fall", "damage", "adversely", "hit hard")):
        return "negative"
    return "any"


def ranking_mode(router: RouterResult) -> str:
    """sector_discovery = use sector JSON; single_fund = API/allisin only."""
    if not router.fund.is_empty():
        return "single_fund"
    if router.intent == _IMPACT_FUNDS_INTENT:
        return "sector_discovery"
    if router.intent == "fund_event_impact":
        return "single_fund"
    return ""


def should_use_sector_ranking_index(router: RouterResult) -> bool:
    return (
        router.intent == _IMPACT_FUNDS_INTENT
        and ranking_mode(router) == "sector_discovery"
        and router.fund.is_empty()
    )


_FUND_EVENT_VERBS = re.compile(
    r"\b(affect|affecting|impact|impacts|impacted|influence|hurt|hits|hit|help|benefit)\b",
    re.I,
)
_FUND_EVENT_TOPICS = re.compile(
    r"\b(crude|oil|petroleum|rbi|repo|rate\s*hike|rate\s*cut|monetary\s*policy|"
    r"inflation|tariff|budget|auto|automobile|banking|bank\s+sector|war|geopolitic|"
    r"election|fed|fii|dii)\b",
    re.I,
)


def _event_focus_from_text(lower: str) -> str:
    if "rbi" in lower or "repo" in lower:
        return "RBI repo rate"
    if "crude" in lower or "oil" in lower or "petroleum" in lower:
        return "crude oil"
    if "auto" in lower or "automobile" in lower:
        return "automotive sector"
    if "bank" in lower:
        return "banking sector"
    if "tariff" in lower:
        return "tariffs"
    if "inflation" in lower:
        return "inflation"
    return ""


_ISIN_IN_TEXT = re.compile(r"\b(INF[A-Z0-9]{9})\b", re.I)


def is_sector_fund_discovery_query(lower: str) -> bool:
    """Market-wide top-N fund queries — not scheme names like 'HDFC Top 100 Fund'."""
    if re.search(r"\b(most\s+affected|highest\s+exposure|worst\s+hit|most\s+impacted)\b", lower):
        return True
    if re.search(r"\b(?:which|what)\s+funds?\b", lower) and re.search(r"\btop\s*\d+", lower):
        return True
    if re.search(r"\btop\s*\d+\s+funds\b", lower):
        return True
    return False


def _extract_fund_phrase(question: str) -> tuple[str, str]:
    from news_rag.fund_search import extract_fund_phrase_from_question

    return extract_fund_phrase_from_question(question)


def try_fast_fund_event_impact_route(question: str) -> RouterResult | None:
    """Named fund + macro/event impact — no LLM router call."""
    q = (question or "").strip()
    if not q:
        return None
    lower = q.lower()
    if is_sector_fund_discovery_query(lower):
        return None
    if not (_FUND_EVENT_VERBS.search(q) or re.search(r"\bhow\s+(?:will|does|would)\b", lower)):
        return None
    if not (_FUND_EVENT_TOPICS.search(q) or re.search(r"\bnews\b", lower)):
        return None
    if not re.search(
        r"\bfund\b|flexi\s*cap|large\s*&?\s*mid|small\s*cap|mid\s*cap|large\s*cap|blue\s*chip|"
        r"ppfas|parag|whiteoak|hdfc|icici|sbi|axis|kotak|nippon|mirae|uti|quant|bandhan",
        lower,
    ):
        if not re.search(r"\bINF[A-Z0-9]{9}\b", q, re.I):
            return None
    isin, fund_name = _extract_fund_phrase(q)
    if not isin and not fund_name:
        return None
    return RouterResult(
        intent="fund_event_impact",
        fund=RouterFund(isin=isin, name=fund_name if not isin else ""),
        companies=[],
        event_focus=_event_focus_from_text(lower),
        window_days=None,
        asked=[q],
        raw_json={"fast_route": True, "fund_event_impact": True},
        duration_sec=0.0,
    )


def try_fast_impact_funds_route(question: str) -> RouterResult | None:
    """Rule-based router for top-N funds by sector/event (no LLM)."""
    q = (question or "").strip()
    if not q:
        return None
    lower = q.lower()
    if not is_sector_fund_discovery_query(lower):
        return None

    limit = infer_ranking_limit(q)
    direction = infer_direction_filter(q)
    event_focus = ""
    if "rbi" in lower or "repo" in lower:
        event_focus = "RBI repo rate"
    elif "crude" in lower or "oil" in lower:
        event_focus = "crude oil"
    elif "auto" in lower or "automobile" in lower:
        event_focus = "automotive sector"
    elif "bank" in lower:
        event_focus = "banking sector"

    return RouterResult(
        intent=_IMPACT_FUNDS_INTENT,
        fund=RouterFund(),
        companies=[],
        event_focus=event_focus,
        window_days=None,
        asked=[q],
        raw_json={
            "fast_route": True,
            "impact_limit": limit,
            "direction_filter": direction,
            "ranking_mode": "sector_discovery",
        },
        duration_sec=0.0,
    )
