"""Planner-authoritative path: fill entities, and keep a fund overview on the news path."""

from __future__ import annotations

import re

from news_rag.insight.contracts import AnswerMode, ExecutionPlan, QueryClass, ToolCall, Wave2Policy

_FUND_OVERVIEW_RE = re.compile(
    r"\b(?:tell me about|how is|how has|overview of|what about|update on)\b",
    re.I,
)

# "Right now" / "currently" is one week. A named period in the same question wins.
_NOW_PHRASE_RE = re.compile(
    r"\bright now\b|\bcurrently\b|\bat the moment\b|\bmarket now\b",
    re.I,
)
_EXPLICIT_WINDOW_RE = re.compile(
    r"\b(?:last|past|this)\s+(?:week|month|year)\b"
    r"|\b(?:one|two|three|six|five|\d+)\s*(?:day|days|week|weeks|month|months|year|years)\b"
    r"|\bquarter\b|\bytd\b|\bhalf\s*year\b",
    re.I,
)
_NOW_WINDOW_DAYS = 7
_WINDOW_TOOLS = ("get_market_snapshot", "search_financial_news", "get_fund_data")


def horizon_code(days: int) -> str:
    """Short label the composer must print next to a measured percent."""
    days = int(days or 0)
    if days <= 1:
        return "1D"
    if days <= 7:
        return "1W"
    if 28 <= days <= 32:
        return "1M"
    if 85 <= days <= 100:
        return "3M"
    if 170 <= days <= 190:
        return "6M"
    if 350 <= days <= 380:
        return "1Y"
    return f"{days}D"


def question_uses_now_window(question: str) -> bool:
    """True when the question means the last 7 days and does not name another period."""
    text = question or ""
    if not _NOW_PHRASE_RE.search(text):
        return False
    if _EXPLICIT_WINDOW_RE.search(text):
        return False
    return True


def apply_now_window(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Force price, fund, and news calculations onto 7 days for a 'right now' question."""
    if not question_uses_now_window(question):
        return plan
    plan.window_days = _NOW_WINDOW_DAYS
    plan.window_label = "1W"
    for call in plan.tool_calls:
        if call.tool not in _WINDOW_TOOLS:
            continue
        args = dict(call.arguments or {})
        args["window_days"] = _NOW_WINDOW_DAYS
        if call.tool == "get_fund_data":
            modules = args.get("modules") or []
            if "managers" not in modules:
                args["windows"] = ["1W"]
        call.arguments = args
    note = (
        "Measured moves are for 1 week (1W). "
        "Label every measured percent with its horizon, such as (1W) or (1M)."
    )
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    return plan


def finalize_planner_plan(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Fill missing funds, and attach news when this is an overview of a named fund."""
    if (plan.routed_by or "") != "planner":
        return plan
    from news_rag.tools import asks_sector_overview

    if asks_sector_overview(question):
        return apply_now_window(question, _ensure_sector_overview(question, plan))
    if not plan.tool_calls:
        return apply_now_window(question, plan)

    needs_funds = any(
        c.tool in ("get_portfolio_data", "get_fund_data", "compare_funds") for c in plan.tool_calls
    )
    if needs_funds and not plan.funds:
        from news_rag.insight.slot_router import _extract_fund_names

        funds = _extract_fund_names(question)
        if not funds:
            from news_rag.fund_search import resolve_fund_for_query

            detail, _amb, _close = resolve_fund_for_query(question)
            if detail:
                name = str(
                    detail.get("fund_name") or detail.get("fund_short_name") or ""
                ).strip()
                if name:
                    funds = [name]
        if funds:
            plan.funds = funds
    plan = _ensure_fund_overview_news(question, plan)
    from news_rag.insight.concept_asks import apply_concept_example_to_plan

    plan = apply_concept_example_to_plan(question, plan)
    return apply_now_window(question, plan)


def _ensure_sector_overview(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """A sector question is the sector move plus the news, not a fund sample."""
    from news_rag.sector_fund_ranking import primary_sector_for_question

    canon, _keys = primary_sector_for_question(question)
    sector = canon or "sector"
    kept: list[ToolCall] = []
    snapshot: ToolCall | None = None
    news: ToolCall | None = None
    for call in plan.tool_calls:
        if call.tool == "get_market_snapshot" and snapshot is None:
            snapshot = call
        elif call.tool == "search_financial_news" and news is None:
            news = call
    if snapshot is None:
        snapshot = ToolCall(
            tool="get_market_snapshot",
            arguments={"modules": ["index_return", "sector_ranking"], "index": "nifty50", "top_n": 6},
            wave=1,
        )
    else:
        args = dict(snapshot.arguments or {})
        modules = list(args.get("modules") or [])
        for name in ("index_return", "sector_ranking"):
            if name not in modules:
                modules.append(name)
        args["modules"] = modules
        snapshot.arguments = args
    if news is None:
        news = ToolCall(
            tool="search_financial_news",
            arguments={"scope": "sectors", "topics": [sector], "top_n": 8, "window_days": 30},
            wave=2,
        )
    else:
        args = dict(news.arguments or {})
        topics = [str(t) for t in (args.get("topics") or []) if str(t).strip()]
        if sector.lower() not in {t.lower() for t in topics}:
            topics.append(sector)
        args["topics"] = topics
        args["scope"] = args.get("scope") or "sectors"
        args["top_n"] = max(int(args.get("top_n") or 0), 8)
        news.arguments = args
        news.wave = 2
    kept.extend([snapshot, news])
    plan.tool_calls = kept
    plan.funds = []
    plan.answer_mode = AnswerMode.INSIGHT_FUSION
    plan.query_class = QueryClass.STANDARD
    plan.requires_compose = True
    plan.response_shape = "sections"
    plan.intent = "overview"
    if plan.max_words < 420:
        plan.max_words = 420
    plan.wave_2_policy = Wave2Policy(trigger="always", max_calls=1)
    plan.presentation_notes = (
        f"Sector overview of {sector}. Open with that sector's measured return and the gap versus "
        "the market index, using sector_focus when it is present. Then explain what the sector news "
        "articles report. Also use macro_news: those cached articles are part of the answer, with the "
        "development each one reports. Do not turn this into a fund list, do not call funds examples, "
        "and do not say the sector has no named fund."
    )
    return plan


def _ensure_fund_overview_news(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """A named-fund overview is an insight, so news has to be retrieved with the metrics."""
    if not plan.funds:
        return plan
    overview = plan.intent == "overview" or bool(_FUND_OVERVIEW_RE.search(question or ""))
    if not overview:
        return plan
    if plan.intent == "lookup" and not _FUND_OVERVIEW_RE.search(question or ""):
        return plan
    has_news = any(c.tool == "search_financial_news" for c in plan.tool_calls)
    plan.answer_mode = AnswerMode.INSIGHT_FUSION
    plan.query_class = QueryClass.STANDARD
    plan.requires_compose = True
    plan.response_shape = "sections"
    if plan.max_words < 420:
        plan.max_words = 420
    plan.presentation_notes = (
        "Connect the fund's return and its largest holdings or sectors to the news articles. "
        "The numbers alone are not the answer."
    )
    plan.wave_2_policy = Wave2Policy(trigger="always", max_calls=1)
    if not has_news:
        plan.tool_calls.append(
            ToolCall(
                tool="search_financial_news",
                arguments={
                    "scope": "all",
                    "top_n": 8,
                    "window_days": min(int(plan.window_days or 30), 30),
                },
                wave=2,
            )
        )
    return plan
