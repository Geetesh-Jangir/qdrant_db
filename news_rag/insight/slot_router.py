"""Generalized slot router — deterministic fast path for common question patterns.

Infers structured slots from the question using existing helpers in brief.py
(question_tier, entity detection, sub-ask split) — NOT string equality on
sample questions.

If confidence >= threshold → builds ExecutionPlan deterministically.
Else → falls through to the structured planner LLM.
"""

from __future__ import annotations

import re
from typing import Any

from news_rag.config import get_settings
from news_rag.insight.brief import (
    QuestionBrief,
    asks_market_briefing,
    asks_sector_lists,
    asks_weak_sector,
    question_tier,
    random_fund_count,
    _COMPARE_RE,
    _DRIVER_PATTERNS,
    _DRIVER_DIRECTION_PATTERNS,
    _FUND_WORD_RE,
    _HOLDERS_RE,
    _IMPACT_WORD_RE,
    _MARKET_RE,
    _METAL_RE,
    _NEGATIVE_RE,
    _POSITIVE_RE,
    _SCREEN_RE,
)
from news_rag.insight.contracts import (
    AnswerMode,
    ExecutionPlan,
    QueryClass,
    ScopeKind,
    ToolCall,
    Wave2Policy,
)
from news_rag.guardrails import check_guardrails


# ---------------------------------------------------------------------------
# Slot inference
# ---------------------------------------------------------------------------

_NAV_RE = re.compile(
    r"\b(?:nav|price|current\s+(?:value|nav|price)|latest\s+nav)\b",
    re.I,
)
_HOLDINGS_RE = re.compile(
    r"\b(?:holdings?|top\s+\d+\s+(?:holdings?|stocks?|shares?)|portfolio|"
    r"what\s+does\s+.+\s+hold|composition|stocks?\s+in|"
    r"stocks?\s+(?:that\s+are\s+)?invested\s+in)\b",
    re.I,
)
_SECTORS_OF_FUND_RE = re.compile(
    r"\b(?:top\s+\d+\s+sectors?|sectors?\s+of|sector\s+(?:allocation|breakdown|mix|weights?)|"
    r"what\s+(?:are\s+)?(?:the\s+)?top\s+\d+\s+sectors?)\b",
    re.I,
)
_CATEGORY_RE = re.compile(
    r"\b(?:category|type\s+of\s+fund|what\s+kind|classification)\b",
    re.I,
)
_ABOUT_RE = re.compile(
    r"\b(?:how\s+is|tell\s+me\s+about|what\s+about|overview\s+of|brief\s+on|"
    r"summarize|summarise)\b",
    re.I,
)
_WHY_MOVE_RE = re.compile(
    r"\b(?:why\s+(?:did|has|is)|reason|cause|what\s+(?:happened|caused|drove|made))\b",
    re.I,
)
_RETURN_RE = re.compile(
    r"\b(?:return|performance|how\s+(?:much|well)|yield|growth)\b",
    re.I,
)
_MANAGER_RE = re.compile(
    r"\b(?:fund\s+manager|portfolio\s+manager|who\s+manages|managed\s+by|"
    r"manager\s+of\s+(?:the\s+)?(?:fund|scheme))\b",
    re.I,
)
_TOP_N_RE = re.compile(r"\btop\s+(\d+)\b", re.I)


def _extract_fund_names(question: str) -> list[str]:
    """Extract fund name candidates from the question text."""
    from news_rag.fund_search import (
        collect_fund_phrase_candidates,
        get_fund_index,
        resolve_fund_for_query,
    )

    names: list[str] = []
    detail, _amb, _close = resolve_fund_for_query(question)
    if detail:
        n = str(detail.get("fund_short_name") or detail.get("fund_name") or "")
        if n:
            names.append(n)

    if not names:
        idx = get_fund_index()
        for phrase in collect_fund_phrase_candidates(question):
            detail, ambiguous, _close = idx.lookup_extracted_fund(name=phrase)
            if detail and not ambiguous:
                hn = str(detail.get("fund_short_name") or detail.get("fund_name") or "")
                if hn and hn not in names:
                    names.append(hn)
    return names[:3]


def _extract_drivers(question: str) -> list[dict[str, str]]:
    """Extract macro drivers and their direction from the question."""
    drivers: list[dict[str, str]] = []
    q = question or ""
    for driver_id, pattern in _DRIVER_PATTERNS:
        if re.search(pattern, q, re.I):
            direction = ""
            for dir_name, dir_pattern in _DRIVER_DIRECTION_PATTERNS:
                if re.search(dir_pattern, q, re.I):
                    direction = dir_name
                    break
            drivers.append({"id": driver_id, "direction": direction})
    return drivers


def _extract_stocks(question: str) -> list[str]:
    """Indexed company names (NSE map), not regex-only phrases."""
    from news_rag.domain_intake import _detect_stocks

    return _detect_stocks(question)


def _infer_window_days(question: str) -> tuple[int, str]:
    """Infer time window from question text."""
    q = (question or "").lower()
    if re.search(r"\btoday\b|\bright now\b|\bcurrently\b|\bcurrent\b|\blatest\b|\bat the moment\b", q):
        return 7, "1 week"
    if re.search(r"\bthis week\b|\bpast week\b|\blast week\b", q):
        return 7, "1 week"
    if re.search(r"\bthis month\b|\blast month\b|\bpast month\b|\bone month\b", q):
        return 30, "1 month"
    if re.search(r"\b(?:3|three)\s*months?\b|\bquarter\b", q):
        return 90, "3 months"
    if re.search(r"\b(?:6|six)\s*months?\b|\bhalf\s*year\b", q):
        return 180, "6 months"
    if re.search(r"\b5\s*years?\b|\bfive\s+years?\b", q):
        return 1825, "5 years"
    if re.search(r"\b3\s*years?\b|\bthree\s+years?\b", q):
        return 1095, "3 years"
    if re.search(r"\b2\s*years?\b|\btwo\s+years?\b", q):
        return 730, "2 years"
    if re.search(r"\b(?:1|one)\s*year\b|\bthis year\b", q):
        return 365, "1 year"
    # Default based on question type
    if asks_market_briefing(q):
        return 7, "1 week"
    return 30, "1 month"


def _get_top_n(question: str, default: int = 3, *, item: str = "any") -> int:
    from news_rag.insight.top_n import top_n_from_question

    q = question or ""
    if re.search(r"\bpick\s+(?:a\s+)?fund\b|\bchoose\s+(?:a\s+)?fund\b", q, re.I):
        return 1
    return top_n_from_question(q, default=default, item=item)


# ---------------------------------------------------------------------------
# Slot-based plan builders
# ---------------------------------------------------------------------------


def _plan_nav_lookup(funds: list[str], window_days: int, window_label: str) -> ExecutionPlan:
    """Single fund NAV lookup — DATA_ONLY, no Wave 2."""
    return ExecutionPlan(
        intent="lookup",
        goal=f"NAV and returns for {', '.join(funds)}",
        answer_mode=AnswerMode.DATA_ONLY,
        query_class=QueryClass.SIMPLE,
        funds=funds,
        window_days=window_days,
        window_label=window_label,
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        response_shape="short_answer",
        max_words=80,
        routed_by="slot_router",
        confidence=0.95,
    )


def _plan_holdings_lookup(
    funds: list[str],
    top_n: int,
    *,
    sections: list[str] | None = None,
    question: str = "",
) -> ExecutionPlan:
    """Holdings list — DATA_ONLY, no Wave 2."""
    from news_rag.tools import portfolio_sections_for_question

    sec = list(sections or portfolio_sections_for_question(question) or ["holdings", "sectors"])
    if sec == ["sectors"]:
        goal = f"Top {top_n} sectors of {', '.join(funds)}"
    elif sec == ["holdings"]:
        goal = f"Top {top_n} holdings of {', '.join(funds)}"
    else:
        goal = f"Top {top_n} portfolio slice of {', '.join(funds)}"
    return ExecutionPlan(
        intent="lookup",
        goal=goal,
        answer_mode=AnswerMode.DATA_ONLY,
        query_class=QueryClass.SIMPLE,
        funds=funds,
        window_days=30,
        window_label="1 month",
        tool_calls=[
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": sec, "top_n": top_n},
                wave=1,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        response_shape="table",
        max_words=100 if sec == ["sectors"] else 120,
        presentation_notes="List only what was asked (sectors or holdings table). No news, NAV, or returns unless asked.",
        routed_by="slot_router",
        confidence=0.98,
    )


def _asks_fund_manager(question: str) -> bool:
    return bool(_MANAGER_RE.search(question or ""))


def _extract_fund_targets_for_manager(question: str) -> list[str]:
    """Fund name, scheme phrase, or ISIN for manager lookup."""
    from news_rag.fund_search import _ISIN_IN_TEXT, fetch_fund_managers_for_isin

    q = question or ""
    isin_m = _ISIN_IN_TEXT.search(q)
    if isin_m:
        isin = isin_m.group(1).upper()
        payload = fetch_fund_managers_for_isin(isin)
        if payload and payload.get("fund_name"):
            return [str(payload["fund_name"])]
        return [isin]
    return _extract_fund_names(q)[:1]


def _plan_fund_managers(funds: list[str]) -> ExecutionPlan:
    """Fund manager bios from RupeeStop fund detail API — DATA_ONLY."""
    return ExecutionPlan(
        intent="lookup",
        goal=f"Fund manager(s) for {', '.join(funds)}",
        answer_mode=AnswerMode.DATA_ONLY,
        query_class=QueryClass.SIMPLE,
        funds=funds,
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["managers"]}, wave=1),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        response_shape="short_answer",
        max_words=380,
        routed_by="slot_router",
        confidence=0.94,
    )


def _plan_fund_overview(funds: list[str], window_days: int, window_label: str) -> ExecutionPlan:
    """How is this fund doing — INSIGHT_FUSION with Wave 2 news."""
    return ExecutionPlan(
        intent="explain_cause",
        goal=f"Overview of {', '.join(funds)} — performance, why it moved, and what it means",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        query_class=QueryClass.STANDARD,
        funds=funds,
        window_days=window_days,
        window_label=window_label,
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot", "attribution"], "top_n": 3}, wave=1),
            ToolCall(tool="get_portfolio_data", arguments={"sections": ["holdings", "sectors"], "top_n": 3}, wave=1),
            ToolCall(tool="get_market_snapshot", arguments={"modules": ["index_return"], "index": "benchmark"}, wave=1),
            ToolCall(
                tool="search_financial_news",
                arguments={"scope": "all", "top_n": 8, "window_days": min(window_days, 30)},
                wave=2,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="always", max_calls=1),
        response_shape="sections",
        max_words=480,
        routed_by="slot_router",
        confidence=0.85,
    )


def _plan_fund_category_average(funds: list[str], window_days: int, window_label: str) -> ExecutionPlan:
    label = ", ".join(funds)
    return ExecutionPlan(
        intent="lookup",
        goal=f"Category average returns for {label}",
        answer_mode=AnswerMode.DATA_ONLY,
        query_class=QueryClass.SIMPLE,
        funds=funds,
        window_days=window_days,
        window_label=window_label,
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1M", "3M", "6M", "1Y", "3Y", "5Y"]},
                wave=1,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        response_shape="table",
        max_words=120,
        routed_by="slot_router",
        confidence=0.96,
    )


def _plan_fund_news(funds: list[str], window_days: int, window_label: str, *, question: str = "") -> ExecutionPlan:
    """News about a named fund — portfolio first, then parallel holdings/sectors/macro news."""
    from news_rag.insight.fund_news_scope import infer_fund_news_layers

    layers = sorted(infer_fund_news_layers(question))
    scope = "all" if len(layers) >= 2 else (layers[0] if layers else "all")
    return ExecutionPlan(
        intent="overview",
        goal=f"Recent news relevant to {', '.join(funds)} — holdings, sectors, and macro as needed",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        query_class=QueryClass.STANDARD,
        funds=funds,
        window_days=window_days,
        window_label=window_label,
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={
                    "modules": ["snapshot", "return_series", "attribution"],
                    "windows": ["1W", "1M", "3M", "6M", "1Y"],
                    "top_n": 3,
                    "window_days": min(window_days, 30),
                },
                wave=1,
            ),
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": ["holdings", "sectors"], "top_n": 5},
                wave=1,
            ),
            ToolCall(
                tool="search_financial_news",
                arguments={
                    "scope": scope,
                    "top_n": 8,
                    "window_days": min(window_days, 30),
                },
                wave=2,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="always", max_calls=1),
        response_shape="sections",
        max_words=480,
        routed_by="slot_router",
        confidence=0.98,
    )


def _plan_why_moved(funds: list[str], window_days: int, window_label: str) -> ExecutionPlan:
    """Why did the fund fall/rise — INSIGHT_FUSION with news."""
    return ExecutionPlan(
        intent="explain_cause",
        goal=f"Why {', '.join(funds)} moved — attribution and news context",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        query_class=QueryClass.STANDARD,
        funds=funds,
        window_days=window_days,
        window_label=window_label,
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot", "return_series", "attribution"], "top_n": 3}, wave=1),
            ToolCall(tool="get_portfolio_data", arguments={"sections": ["holdings", "sectors"], "top_n": 3}, wave=1),
            ToolCall(tool="get_market_snapshot", arguments={"modules": ["index_return"], "index": "benchmark"}, wave=1),
            ToolCall(
                tool="search_financial_news",
                arguments={"scope": "all", "top_n": 8, "window_days": min(window_days, 30)},
                wave=2,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="always", max_calls=1),
        response_shape="sections",
        max_words=480,
        routed_by="slot_router",
        confidence=0.85,
    )


def _plan_market_overview(window_days: int, window_label: str) -> ExecutionPlan:
    """Market overview — what is happening in the market."""
    return ExecutionPlan(
        intent="overview",
        goal="Market overview — index moves, sector rotation, key themes",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        query_class=QueryClass.STANDARD,
        window_days=window_days,
        window_label=window_label,
        tool_calls=[
            ToolCall(tool="get_market_snapshot", arguments={
                "modules": ["index_return", "sector_ranking"],
                "index": "nifty50",
                "window_days": window_days,
                "top_n": 6,
            }, wave=1),
            ToolCall(tool="search_financial_news", arguments={
                "scope": "market",
                "top_n": 8,
                "window_days": min(window_days, 14),
            }, wave=2),
        ],
        wave_2_policy=Wave2Policy(trigger="always", max_calls=1),
        response_shape="sections",
        max_words=480,
        routed_by="slot_router",
        confidence=0.9,
    )


def _plan_fund_compare(funds: list[str], window_days: int, window_label: str) -> ExecutionPlan:
    """Compare two or more funds."""
    return ExecutionPlan(
        intent="compare",
        goal=f"Compare {', '.join(funds)}",
        answer_mode=AnswerMode.DATA_ONLY,
        query_class=QueryClass.STANDARD,
        funds=funds,
        window_days=window_days,
        window_label=window_label,
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(tool="get_portfolio_data", arguments={"sections": ["holdings", "sectors"], "top_n": 5}, wave=1),
            ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        response_shape="table",
        max_words=300,
        routed_by="slot_router",
        confidence=0.85,
    )


def _plan_stock_lookup(stocks: list[str]) -> ExecutionPlan:
    """Stock price lookup."""
    name = stocks[0] if stocks else ""
    return ExecutionPlan(
        intent="lookup",
        goal=f"Price of {', '.join(stocks)}",
        answer_mode=AnswerMode.DATA_ONLY,
        query_class=QueryClass.SIMPLE,
        stocks=stocks,
        window_days=7,
        window_label="1 week",
        tool_calls=[
            ToolCall(
                tool="get_market_snapshot",
                arguments={"modules": ["stock_quote"], "stock": name},
                wave=1,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        response_shape="short_answer",
        max_words=60,
        routed_by="slot_router",
        confidence=0.85,
    )


def _plan_stock_overview(stocks: list[str], window_days: int, window_label: str) -> ExecutionPlan:
    """Company overview — quote plus recent news."""
    name = stocks[0] if stocks else ""
    return ExecutionPlan(
        intent="overview",
        goal=f"Overview of {name} — price move and what is in the news",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        query_class=QueryClass.STANDARD,
        stocks=stocks,
        window_days=window_days,
        window_label=window_label,
        tool_calls=[
            ToolCall(
                tool="get_market_snapshot",
                arguments={"modules": ["stock_quote"], "stock": name, "window_days": window_days},
                wave=1,
            ),
            ToolCall(
                tool="search_financial_news",
                arguments={
                    "scope": "stock",
                    "topics": [name],
                    "top_n": 3,
                    "window_days": min(window_days, 14),
                },
                wave=2,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="always", max_calls=1),
        response_shape="sections",
        max_words=400,
        routed_by="slot_router",
        confidence=0.88,
    )


def _plan_news_topics(topics: list[str], window_days: int, window_label: str) -> ExecutionPlan:
    """Headlines on a specific theme (IPO, company, macro topic) — NEWS_ONLY."""
    label = ", ".join(topics)
    return ExecutionPlan(
        intent="lookup",
        goal=f"Recent news on {label}",
        answer_mode=AnswerMode.NEWS_ONLY,
        query_class=QueryClass.STANDARD,
        window_days=min(window_days, 30),
        window_label=window_label,
        tool_calls=[
            ToolCall(
                tool="search_financial_news",
                arguments={
                    "scope": "market",
                    "topics": topics[:4],
                    "top_n": min(8, len(topics) * 3 or 6),
                    "window_days": min(window_days, 30),
                },
                wave=1,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        response_shape="bullets",
        max_words=400,
        routed_by="slot_router",
        confidence=0.9,
    )


def _macro_series_for_driver(driver_id: str, question: str = "") -> list[str]:
    from news_rag.macro_impact_map import macro_series_for_driver

    q = (question or "").lower()
    if re.search(r"\bwti\b", q):
        return ["wti"]
    if re.search(r"\bbrent\b", q):
        return ["brent"]
    return macro_series_for_driver(driver_id or "")


def _plan_macro_explain(
    drivers: list[dict[str, str]],
    window_days: int,
    window_label: str,
    question: str = "",
) -> ExecutionPlan:
    """Why is crude/rates/FX moving — prices from macro_series + explanatory news."""
    driver_id = drivers[0]["id"] if drivers else "crude_oil"
    topic = driver_id.replace("_", " ")
    series = _macro_series_for_driver(driver_id, question)
    return ExecutionPlan(
        intent="explain_cause",
        goal=f"Explain recent moves in {topic} and what the news points to",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        query_class=QueryClass.STANDARD,
        drivers=drivers,
        window_days=window_days,
        window_label=window_label,
        tool_calls=[
            ToolCall(
                tool="get_market_snapshot",
                arguments={
                    "modules": ["macro_series", "index_return"],
                    "series": series,
                    "index": "nifty50",
                    "window_days": window_days,
                },
                wave=1,
            ),
            ToolCall(
                tool="search_financial_news",
                arguments={
                    "scope": "macro",
                    "topics": [topic],
                    "top_n": 6,
                    "window_days": min(window_days, 21),
                },
                wave=2,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="always", max_calls=1),
        response_shape="sections",
        max_words=450,
        routed_by="slot_router",
        confidence=0.88,
    )


def _asks_catalog_fund_performance(question: str) -> bool:
    """Unnamed fund list by return window (random sample or top performers)."""
    from news_rag.tools import (
        _return_direction_in_question,
        asks_funds_holding_stock,
        explicit_fund_count,
        infer_return_window,
    )

    if asks_funds_holding_stock(question):
        return False
    if random_fund_count(question) > 0:
        return True
    if not _FUND_WORD_RE.search(question) and not _SCREEN_RE.search(question):
        return False
    if _extract_fund_names(question):
        return False
    window = infer_return_window(question)
    direction = _return_direction_in_question(question)
    if direction and window in ("1W", "1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y"):
        return True
    if explicit_fund_count(question) and (_RETURN_RE.search(question) or _POSITIVE_RE.search(question)):
        return True
    return False


def _plan_fund_performance_screen(
    question: str,
    window_days: int,
    window_label: str,
) -> ExecutionPlan:
    from news_rag.tools import (
        _return_direction_in_question,
        explicit_fund_count,
        infer_return_window,
        return_window_days,
        return_window_label,
    )

    n = random_fund_count(question) or explicit_fund_count(question) or _get_top_n(question, 5)
    window = infer_return_window(question)
    window_days = return_window_days(window)
    window_label = return_window_label(window)
    direction = "negative" if _NEGATIVE_RE.search(question) else (
        "positive"
        if _POSITIVE_RE.search(question) or _return_direction_in_question(question) == "positive"
        else "any"
    )
    random_sample = random_fund_count(question) > 0
    require_1y = direction == "positive"
    return ExecutionPlan(
        intent="rank",
        goal=f"List {n} funds with {direction} {window} returns from the catalog",
        answer_mode=AnswerMode.DATA_ONLY,
        query_class=QueryClass.SIMPLE,
        window_days=window_days,
        window_label=window_label,
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={
                    "direction": direction,
                    "top_n": n,
                    "return_window": window,
                    "random_sample": random_sample,
                    "require_positive_1y": require_1y,
                },
                wave=1,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        response_shape="table",
        max_words=200,
        routed_by="slot_router",
        confidence=0.92,
    )


def _asks_driver_sector_or_fund_impact(question: str) -> bool:
    """Sectors/funds hurt or helped by a macro driver (not only NAV lookups)."""
    q = question or ""
    if not re.search(r"\b(?:sectors?|funds?)\b", q, re.I):
        return False
    return bool(
        re.search(r"\baffected\b|\bexposed\b|\bexposure\b", q, re.I) or _IMPACT_WORD_RE.search(q)
    )


def _plan_driver_impact(
    drivers: list[dict[str, str]],
    window_days: int,
    window_label: str,
    question: str = "",
) -> ExecutionPlan:
    """Why a driver moved, which sectors it hits, and which funds have the most exposure."""
    from news_rag.insight.brief import _NEGATIVE_RE, _POSITIVE_RE

    driver_move = next((d.get("direction", "") for d in drivers if d.get("direction")), "")
    exposure = "any"
    if _NEGATIVE_RE.search(question or ""):
        exposure = "negative"
    elif _POSITIVE_RE.search(question or ""):
        exposure = "positive"
    driver_id = drivers[0]["id"] if drivers else "crude_oil"
    series = _macro_series_for_driver(driver_id)
    return ExecutionPlan(
        intent="explain_cause",
        goal=(
            f"Explain recent {driver_id.replace('_', ' ')} moves, list affected sectors, "
            "and funds with the highest exposure on the hurt/help side"
        ),
        answer_mode=AnswerMode.INSIGHT_FUSION,
        query_class=QueryClass.STANDARD,
        drivers=drivers,
        window_days=window_days,
        window_label=window_label,
        tool_calls=[
            ToolCall(
                tool="get_market_snapshot",
                arguments={
                    "modules": ["macro_series", "index_return"],
                    "series": series,
                    "index": "nifty50",
                    "window_days": window_days,
                },
                wave=1,
            ),
            ToolCall(tool="screen_funds_by_exposure", arguments={
                "driver": driver_id,
                "direction": exposure,
                "driver_move": driver_move,
                "top_n": 5,
            }, wave=1),
            ToolCall(tool="search_financial_news", arguments={
                "scope": "macro",
                "topics": [d["id"].replace("_", " ") for d in drivers[:3]],
                "window_days": min(window_days, 14),
            }, wave=2),
        ],
        wave_2_policy=Wave2Policy(trigger="always", max_calls=1),
        response_shape="sections",
        max_words=400,
        routed_by="slot_router",
        confidence=0.8,
    )


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------


def slot_route(
    question: str,
    *,
    prior_context: dict[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> ExecutionPlan | None:
    """Try to build an ExecutionPlan deterministically.

    Returns None when the question is too ambiguous — the caller should
    fall through to the structured planner LLM.
    """
    q = (question or "").strip()
    if not q:
        return None

    from news_rag.fund_rating_screen import asks_rating_list, rating_list_plan
    from news_rag.fund_risk import asks_rating_concept, rating_concept_plan

    if asks_rating_list(q):
        return rating_list_plan(q)

    if asks_rating_concept(q):
        return rating_concept_plan(q)

    from news_rag.insight.glossary import glossary_execution_plan

    gplan = glossary_execution_plan(q)
    if gplan is not None:
        return gplan

    from news_rag.insight.concept_asks import build_concept_example_plan

    cplan = build_concept_example_plan(q, routed_by="slot_router")
    if cplan is not None:
        return cplan

    settings = get_settings()
    if confidence_threshold is None:
        confidence_threshold = getattr(settings, "slot_router_confidence", 0.8)


    # --- Guardrails ---
    guard = check_guardrails(q)
    if guard.outcome == "refuse_out_of_domain":
        return ExecutionPlan(
            guardrail_passed=False,
            scope_kind=ScopeKind.OUT_OF_SCOPE,
            direct_reply=guard.message,
            routed_by="slot_router",
            confidence=1.0,
        )
    if guard.outcome == "refuse_advice":
        # Still plan the facts (the plan notes asks_for_advice=True)
        pass

    # --- Extract entities (indexes: stocks, sectors, funds) ---
    from news_rag.domain_intake import (
        _STOCK_OVERVIEW_RE,
        _question_targets_stock_not_fund,
        asks_macro_explanation,
        question_mentions_fund_scheme,
        scan_question_domain,
    )

    window_days, window_label = _infer_window_days(q)
    domain = scan_question_domain(q)
    drivers = _extract_drivers(q)
    stocks = domain.stocks or _extract_stocks(q)
    stock_first = _question_targets_stock_not_fund(q, stocks)

    # --- Pattern matching → plan ---

    if domain.news_topics:
        plan = _plan_news_topics(domain.news_topics, window_days, window_label)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    # What a named fund holds (stocks/sectors) — before "funds holding a stock"
    from news_rag.tools import (
        asks_fund_portfolio_holdings,
        asks_funds_holding_stock,
        asks_funds_with_sector_exposure,
    )

    if asks_funds_with_sector_exposure(q):
        plan = _plan_fund_performance_screen(q, window_days, window_label)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    if asks_fund_portfolio_holdings(q):
        funds = _extract_fund_names(q)
        if not funds:
            from news_rag.fund_search import resolve_fund_for_query

            detail, _amb, _close = resolve_fund_for_query(q)
            if detail:
                funds = [
                    str(
                        detail.get("fund_name")
                        or detail.get("fund_short_name")
                        or ""
                    ).strip()
                ]
                funds = [f for f in funds if f]
        if funds:
            from news_rag.tools import portfolio_sections_for_question

            sec = portfolio_sections_for_question(q)
            kind = (
                "sectors"
                if sec == ["sectors"]
                else "holdings"
                if sec == ["holdings"]
                else "any"
            )
            plan = _plan_holdings_lookup(
                funds,
                _get_top_n(q, item=kind),
                sections=sec if sec != ["holdings", "sectors"] else None,
                question=q,
            )
            if guard.outcome == "refuse_advice":
                plan.asks_for_advice = True
            return plan

    if asks_funds_holding_stock(q) and _FUND_WORD_RE.search(q):
        plan = _plan_fund_performance_screen(q, window_days, window_label)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    # Fund manager (RupeeStop fund API) — supports ISIN or scheme name
    if _asks_fund_manager(q):
        mgr_funds = _extract_fund_targets_for_manager(q)
        if mgr_funds:
            plan = _plan_fund_managers(mgr_funds)
            if guard.outcome == "refuse_advice":
                plan.asks_for_advice = True
            return plan

    # Random / performance fund screens (catalog, 1Y positive, etc.)
    if _asks_catalog_fund_performance(q):
        plan = _plan_fund_performance_screen(q, window_days, window_label)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    # Listed company (e.g. HDFC Bank) before mutual-fund heuristics
    if stocks and stock_first:
        if _STOCK_OVERVIEW_RE.search(q) or _ABOUT_RE.search(q):
            plan = _plan_stock_overview(stocks, window_days, window_label)
            if guard.outcome == "refuse_advice":
                plan.asks_for_advice = True
            return plan
        if not _FUND_WORD_RE.search(q):
            return _plan_stock_lookup(stocks)

    # Market overview
    if asks_market_briefing(q) and not _extract_fund_names(q):
        plan = _plan_market_overview(window_days, window_label)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    # Driver + sectors/funds impact (compound or exposure-only)
    if drivers and _asks_driver_sector_or_fund_impact(q):
        plan = _plan_driver_impact(drivers, window_days, window_label, q)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    # Macro / commodity "why is X rising" (no sector/fund impact ask)
    if drivers and asks_macro_explanation(q):
        plan = _plan_macro_explain(drivers, window_days, window_label, q)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    # Driver impact on funds (explicit fund/scheme wording)
    if drivers and question_mentions_fund_scheme(q) and (
        _FUND_WORD_RE.search(q) or _IMPACT_WORD_RE.search(q)
    ):
        plan = _plan_driver_impact(drivers, window_days, window_label, q)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    # --- Fund-centric patterns ---
    # These require fund name extraction which hits the fund index
    funds = _extract_fund_names(q) if question_mentions_fund_scheme(q) else []
    if not funds:
        # Can't route deterministically without a fund — fall through to planner
        return None

    top_n = _get_top_n(q, default=3)

    from news_rag.fund_rupeestop_metrics import asks_fund_category_average
    from news_rag.tools import asks_fund_related_news

    if asks_fund_category_average(q):
        plan = _plan_fund_category_average(funds, window_days, window_label)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    if asks_fund_related_news(q):
        plan = _plan_fund_news(funds, window_days, window_label, question=q)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    # Compare funds
    if _COMPARE_RE.search(q) and len(funds) >= 2:
        plan = _plan_fund_compare(funds, window_days, window_label)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    if _asks_fund_manager(q) and funds:
        plan = _plan_fund_managers(funds)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    # NAV / price lookup
    if _NAV_RE.search(q) and not _ABOUT_RE.search(q) and not _WHY_MOVE_RE.search(q):
        return _plan_nav_lookup(funds, window_days, window_label)

    # Sector allocation of a named scheme (before generic holdings / overview)
    if (
        (_SECTORS_OF_FUND_RE.search(q) or (re.search(r"\bsectors?\b", q, re.I) and _TOP_N_RE.search(q)))
        and not _ABOUT_RE.search(q)
        and not _WHY_MOVE_RE.search(q)
    ):
        return _plan_holdings_lookup(
            funds,
            _get_top_n(q, default=3, item="sectors"),
            sections=["sectors"],
            question=q,
        )

    # Holdings lookup
    if _HOLDINGS_RE.search(q) and not _ABOUT_RE.search(q) and not _WHY_MOVE_RE.search(q):
        return _plan_holdings_lookup(funds, top_n, question=q)

    # Why did fund move
    if _WHY_MOVE_RE.search(q):
        plan = _plan_why_moved(funds, window_days, window_label)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    # Fund overview ("how is it doing", "tell me about")
    if _ABOUT_RE.search(q) or _RETURN_RE.search(q):
        plan = _plan_fund_overview(funds, window_days, window_label)
        if guard.outcome == "refuse_advice":
            plan.asks_for_advice = True
        return plan

    # Weak default only when the router explicitly allows low-confidence plans (not planner fallback).
    if len(funds) == 1 and confidence_threshold < 0.8:
        plan = _plan_fund_overview(funds, window_days, window_label)
        plan.confidence = 0.7
        return plan

    return None
