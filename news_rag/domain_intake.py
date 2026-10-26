"""Domain intake: decide if a question is in our finance scope using indexes, not keyword length.

Resolves stocks, sectors, funds, and macro drivers from the question text before
guardrails or routing refuse vague phrasing like "tell me about HDFC Bank".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Wording that usually means the user wants a company overview (not a mutual fund).
_STOCK_OVERVIEW_RE = re.compile(
    r"\b(?:tell\s+me\s+about|what\s+about|overview\s+of|how\s+is|how\s+are|"
    r"what(?:'s| is)\s+happening|happening\s+with|update\s+on|brief\s+on)\b",
    re.I,
)
_FUND_SCHEME_RE = re.compile(
    r"\b(?:mutual\s+fund|mf\b|scheme|nav\b|folio|sip\b|amc\b|"
    r"(?:large|mid|small|flexi|multi)\s*cap|elss|index\s+fund|etf\b|"
    r"absl|ppfas|parag\s+parikh|aditya\s+birla|angel\s+one)\b",
    re.I,
)

_NEWS_INTENT_RE = re.compile(
    r"\b(?:news|headlines?|updates?|articles?|stories|reports?|coverage)\b",
    re.I,
)
_CORPORATE_MARKET_EVENT_RE = re.compile(
    r"\b(?:ipo|fpo|listing|delisting|qip|merger|acquisition|takeover|"
    r"earnings|results?|dividend|buyback|rights\s+issue|offer\s+for\s+sale|ofs)\b",
    re.I,
)
_INDIA_MARKET_CONTEXT_RE = re.compile(
    r"\b(?:india|indian|nse|bse|nifty|sensex|markets?|stocks?|shares?|rupee|sebi|rbi)\b",
    re.I,
)

_NEWS_TOPIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:tell\s+me\s+)?(?:the\s+)?(?:latest\s+)?news\s+(?:about|on|for|regarding)\s+(.+)",
        re.I,
    ),
    re.compile(r"headlines?\s+(?:about|on|for|regarding)\s+(.+)", re.I),
    re.compile(r"what(?:'s| is)\s+(?:the\s+)?(?:latest|news)(?:\s+on|\s+about)?\s+(.+)", re.I),
    re.compile(r"any\s+(?:news|updates?)\s+(?:on|about)\s+(.+)", re.I),
)

# Expand common names for Qdrant semantic search (not hardcoded Q&A pairs).
_NEWS_SEARCH_ALIASES: dict[str, str] = {
    "jio": "Reliance Jio IPO India",
    "jio ipo": "Jio IPO Reliance Industries India",
    "reliance jio": "Reliance Jio IPO India",
}


@dataclass
class DomainScan:
    stocks: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    funds: list[str] = field(default_factory=list)
    drivers: list[str] = field(default_factory=list)
    news_topics: list[str] = field(default_factory=list)
    market_briefing: bool = False
    metals: bool = False
    reasons: list[str] = field(default_factory=list)

    @property
    def has_entity(self) -> bool:
        return bool(self.stocks or self.sectors or self.funds or self.drivers or self.news_topics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stocks": self.stocks,
            "sectors": self.sectors,
            "funds": self.funds,
            "drivers": self.drivers,
            "news_topics": self.news_topics,
            "market_briefing": self.market_briefing,
            "metals": self.metals,
            "reasons": self.reasons,
        }


def _detect_stocks(question: str) -> list[str]:
    from news_rag.insight.brief import _detect_stocks

    return list(_detect_stocks(question))


def _detect_sectors(question: str) -> list[str]:
    from news_rag.insight.brief import _detect_sector

    _label, keys = _detect_sector(question)
    if keys:
        return list(keys)
    try:
        from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

        idx = get_sector_fund_ranking_index()
        from_q = idx.resolve_from_question(question) if hasattr(idx, "resolve_from_question") else []
        if from_q:
            return list(from_q)[:3]
        return [k for k in idx.resolve_sector_keys([question]) if k][:3]
    except Exception:
        return []


def _detect_drivers(question: str) -> list[str]:
    from news_rag.insight.brief import _detect_drivers

    drivers, _direction = _detect_drivers(question)
    return list(drivers)


def _detect_funds(question: str) -> list[str]:
    from news_rag.fund_search import collect_fund_phrase_candidates, get_fund_index, resolve_fund_for_query

    names: list[str] = []
    detail, _amb, _close = resolve_fund_for_query(question)
    if detail:
        n = str(detail.get("fund_short_name") or detail.get("fund_name") or "").strip()
        if n:
            names.append(n)
    if not names:
        idx = get_fund_index()
        for phrase in collect_fund_phrase_candidates(question):
            hits = idx.search(phrase, limit=2)
            for h in hits:
                hn = str(h.get("fund_short_name") or h.get("fund_name") or "").strip()
                if hn and hn not in names:
                    names.append(hn)
    return names[:3]


def enrich_news_search_topic(topic: str) -> str:
    """Optional query expansion for known corporate names (search only)."""
    key = re.sub(r"\s+", " ", (topic or "").strip().lower())
    return _NEWS_SEARCH_ALIASES.get(key, (topic or "").strip())


def extract_news_topics(question: str) -> list[str]:
    """Topic phrase from 'news about X' style questions."""
    q = (question or "").strip().rstrip("?")
    for pat in _NEWS_TOPIC_PATTERNS:
        match = pat.search(q)
        if not match:
            continue
        topic = re.sub(r"\s+", " ", match.group(1).strip()).strip("?. ")
        if len(topic) >= 2:
            return [enrich_news_search_topic(topic)]
    return []


def asks_financial_news(question: str) -> bool:
    """User wants headlines/updates on a market or corporate topic."""
    q = question or ""
    if not _NEWS_INTENT_RE.search(q):
        return False
    if extract_news_topics(q):
        return True
    if _CORPORATE_MARKET_EVENT_RE.search(q):
        return True
    if _INDIA_MARKET_CONTEXT_RE.search(q):
        return True
    return bool(_detect_stocks(q) or _detect_sectors(q) or _detect_drivers(q))


def question_mentions_fund_scheme(question: str) -> bool:
    """True only when the user is clearly asking about a mutual fund scheme."""
    q = question or ""
    if _FUND_SCHEME_RE.search(q):
        return True
    if re.search(r"\b(?:nav|folio|sip|amc|scheme)\b", q, re.I):
        return True
    return bool(re.search(r"\b(?:mutual\s+)?funds?\b", q, re.I))


def is_macro_or_commodity_focus(question: str) -> bool:
    """Crude, rates, FX, etc. — not a named fund question unless they also said 'fund'."""
    q = question or ""
    if _detect_drivers(q):
        return True
    return bool(
        re.search(
            r"\b(crude|oil|brent|petrol|diesel|gold|silver|commodit|rupee|dollar|"
            r"yield|bond|g-?sec|inflation|forex|gas)\b",
            q,
            re.I,
        )
    )


def asks_macro_explanation(question: str) -> bool:
    """Why / how come / reason for a macro or commodity move."""
    q = question or ""
    if not is_macro_or_commodity_focus(q):
        return False
    if question_mentions_fund_scheme(q):
        return False
    return bool(
        re.search(
            r"\b(?:why|how\s+come|reason|cause|what\s+(?:is|are)\s+driving|"
            r"explain)\b",
            q,
            re.I,
        )
        or re.search(
            r"\b(?:ris\w*|increas\w*|decreas\w*|fall\w*|surge|spike|climb\w*|"
            r"drop\w*|declin\w*|going\s+up|going\s+down)\b",
            q,
            re.I,
        )
    )


def _question_targets_stock_not_fund(question: str, stocks: list[str]) -> bool:
    """True when indexed stocks match and wording is not clearly about a mutual fund."""
    if not stocks:
        return False
    if _FUND_SCHEME_RE.search(question or ""):
        return False
    q = (question or "").lower()
    for stock in stocks:
        sl = stock.lower()
        if sl in q and "fund" not in q[max(0, q.find(sl) - 15) : q.find(sl) + len(sl) + 20]:
            return True
    return bool(stocks) and not re.search(r"\bfunds?\b", q)


def scan_question_domain(question: str) -> DomainScan:
    """Resolve entities from catalogs; used by guardrails and slot router."""
    q = (question or "").strip()
    scan = DomainScan()
    if not q:
        return scan

    from news_rag.insight.brief import _METAL_RE, asks_market_briefing

    scan.stocks = _detect_stocks(q)
    scan.sectors = _detect_sectors(q)
    scan.drivers = _detect_drivers(q)
    scan.market_briefing = asks_market_briefing(q)
    scan.metals = bool(_METAL_RE.search(q))

    stock_first = _question_targets_stock_not_fund(q, scan.stocks)
    if stock_first:
        scan.reasons.append("stock_entity")
    elif question_mentions_fund_scheme(q) or not is_macro_or_commodity_focus(q):
        scan.funds = _detect_funds(q)
        if scan.funds:
            scan.reasons.append("fund_entity")
    if asks_macro_explanation(q):
        scan.reasons.append("macro_explain")

    if scan.sectors:
        scan.reasons.append("sector_entity")
    if scan.drivers:
        scan.reasons.append("macro_driver")
    if scan.market_briefing:
        scan.reasons.append("market_briefing")
    if scan.metals:
        scan.reasons.append("metals")

    scan.news_topics = extract_news_topics(q)
    if scan.news_topics:
        scan.reasons.append("news_topic")
    elif asks_financial_news(q) and _CORPORATE_MARKET_EVENT_RE.search(q):
        # e.g. "Jio IPO updates" without the word "news"
        blob = re.sub(r"\b(ipo|fpo|listing|tell me|about|the|latest)\b", " ", q, flags=re.I)
        topic = re.sub(r"\s+", " ", blob).strip()
        if len(topic) >= 2:
            scan.news_topics = [enrich_news_search_topic(topic)]

    return scan


def question_in_finance_scope(question: str) -> tuple[bool, DomainScan]:
    """Whether the question should pass domain guardrails (before advice checks)."""
    from news_rag.guardrails import financial_keyword_signal

    q = (question or "").strip()
    scan = scan_question_domain(q)
    if scan.has_entity or scan.market_briefing or scan.metals:
        return True, scan
    if financial_keyword_signal(q):
        return True, scan
    if re.match(r"^\s*what\s+is\s+\w+", q, re.I) and len(q) < 160:
        return True, scan
    return False, scan
