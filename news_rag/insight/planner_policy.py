"""Planner-authoritative path: fill entities, and leave the planner's tools in place."""

from __future__ import annotations

import re
from typing import Any

from news_rag.insight.contracts import AnswerMode, ExecutionPlan, QueryClass, ToolCall, Wave2Policy

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


def planner_owns(plan: Any) -> bool:
    """A planner plan is not rewritten by later phrase matches."""
    return (getattr(plan, "routed_by", "") or "") == "planner"


def restore_dropped_planner_tools(plan: ExecutionPlan, original: list[ToolCall]) -> ExecutionPlan:
    """Hooks may add tools; they must not drop ones the planner already chose."""
    from news_rag.insight.contracts import ScopeKind

    if not planner_owns(plan) or not original:
        return plan
    if plan.scope_kind in (ScopeKind.NEEDS_CLARIFICATION, ScopeKind.OUT_OF_SCOPE):
        return plan
    if any((c.arguments or {}).get("compare_pair") for c in plan.tool_calls or []):
        return plan
    if not plan.tool_calls:
        plan.tool_calls = [call.model_copy(deep=True) for call in original]
        return plan
    have = {call.tool: i for i, call in enumerate(plan.tool_calls)}
    for call in original:
        idx = have.get(call.tool)
        if idx is None:
            plan.tool_calls.append(call.model_copy(deep=True))
            have[call.tool] = len(plan.tool_calls) - 1
            continue
        if call.tool != "get_fund_data":
            continue
        cur = plan.tool_calls[idx]
        args = dict(cur.arguments or {})
        mods = [str(m).lower() for m in (args.get("modules") or [])]
        for mod in (call.arguments or {}).get("modules") or []:
            name = str(mod).lower()
            if name and name not in mods:
                mods.append(name)
        if mods:
            args["modules"] = mods
        windows = [str(w) for w in (args.get("windows") or [])]
        for window in (call.arguments or {}).get("windows") or []:
            label = str(window)
            if label and label not in windows:
                windows.append(label)
        if windows:
            args["windows"] = windows
        cur.arguments = args
    return plan


_RISK_ASK_RE = re.compile(r"\b(?:riskometer|how risky|risk)\b", re.I)


def drop_unasked_fund_modules(question: str, plan: ExecutionPlan) -> None:
    """Managers and the risk module only when the question asks for them."""
    from news_rag.insight.slot_router import _asks_fund_manager

    wants_mgr = _asks_fund_manager(question)
    wants_risk = bool(_RISK_ASK_RE.search(question or ""))
    for call in plan.tool_calls or []:
        if call.tool != "get_fund_data":
            continue
        args = dict(call.arguments or {})
        modules = [str(m) for m in (args.get("modules") or [])]
        if not wants_mgr:
            modules = [m for m in modules if m.lower() != "managers"]
        if not wants_risk:
            modules = [m for m in modules if m.lower() != "risk"]
        if not modules:
            modules = ["snapshot"]
        args["modules"] = modules
        call.arguments = args
    if not wants_mgr:
        plan.asked_facts = [
            fact
            for fact in (plan.asked_facts or [])
            if str(fact).lower() not in ("fund_manager", "managers")
        ]


def trim_named_fund_overview(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """A 'tell me about this fund' ask is snapshot, rating, holdings and sectors."""
    if str(plan.intent or "") != "overview" or len(plan.funds or []) != 1:
        return plan
    drop_unasked_fund_modules(question, plan)
    for call in plan.tool_calls or []:
        if call.tool != "get_fund_data":
            continue
        args = dict(call.arguments or {})
        modules = [str(m).lower() for m in (args.get("modules") or [])]
        for name in ("snapshot", "rating"):
            if name not in modules:
                modules.append(name)
        args["modules"] = modules
        call.arguments = args
    return plan


def narrow_deictic_follow_up(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> ExecutionPlan:
    """A follow-up on the last fund fetches only the new slice, or nothing if already answered."""
    from news_rag.fund_rupeestop_metrics import periods_requested_in_question
    from news_rag.insight.investor_subject import question_refers_deictic_fund

    refers = question_refers_deictic_fund(question) or bool(
        re.search(r"\b(?:it|its|that fund|this fund)\b", question or "", re.I)
    )
    if not refers or len(plan.funds or []) != 1:
        return plan
    drop_unasked_fund_modules(question, plan)
    periods = periods_requested_in_question(question)
    why = bool(re.search(r"\bwhy\b", question or "", re.I))
    if why:
        kept: list[ToolCall] = []
        for call in plan.tool_calls or []:
            if call.tool == "get_fund_data":
                args = dict(call.arguments or {})
                args["modules"] = ["snapshot"]
                args["windows"] = periods or ["1M"]
                call.arguments = args
                kept.append(call)
            elif call.tool in ("get_portfolio_data", "search_financial_news"):
                kept.append(call)
        if not any(call.tool == "search_financial_news" for call in kept):
            kept.append(
                ToolCall(
                    tool="search_financial_news",
                    arguments={"scope": "all", "top_n": 8, "window_days": 30},
                    wave=1,
                )
            )
        if not any(call.tool == "get_fund_data" for call in kept):
            kept.insert(
                0,
                ToolCall(
                    tool="get_fund_data",
                    arguments={"modules": ["snapshot"], "windows": periods or ["1M"]},
                    wave=1,
                ),
            )
        plan.tool_calls = kept
        plan.answer_mode = AnswerMode.INSIGHT_FUSION
        return plan
    if len(periods) != 1:
        return plan
    # "tell me more about it and its 1M" is still an overview, not a single-figure follow-up.
    if re.search(
        r"\b(?:tell me more|more about|overview|also)\b|\band\s+(?:its|the|about)\b",
        question or "",
        re.I,
    ):
        for call in plan.tool_calls or []:
            if call.tool != "get_fund_data":
                continue
            args = dict(call.arguments or {})
            args["windows"] = periods
            call.arguments = args
        return plan
    turns = (memory or {}).get("chat_turns") if isinstance(memory, dict) else None
    last = ""
    if isinstance(turns, list) and turns and isinstance(turns[-1], dict):
        last = str(turns[-1].get("assistant") or "")
    label = periods[0]
    shown = {
        "1Y": r"\b1\s*year\b|\b1Y\b",
        "3Y": r"\b3\s*years?\b|\b3Y\b",
        "5Y": r"\b5\s*years?\b|\b5Y\b",
        "1M": r"\b1\s*month\b|\b1M\b",
        "6M": r"\b6\s*months?\b|\b6M\b",
    }.get(label, re.escape(label))
    if last and re.search(shown, last, re.I):
        plan.tool_calls = []
        plan.answer_mode = AnswerMode.DATA_ONLY
        plan.wave_2_policy = Wave2Policy(trigger="none")
        return plan
    plan.tool_calls = [
        ToolCall(
            tool="get_fund_data",
            arguments={"modules": ["snapshot"], "windows": [label]},
            wave=1,
        )
    ]
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.wave_2_policy = Wave2Policy(trigger="none")
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
    from news_rag.insight.concept_asks import apply_concept_example_to_plan

    plan = apply_concept_example_to_plan(question, plan)
    from news_rag.insight.return_windows import align_plan_windows

    align_plan_windows(plan)
    plan = trim_named_fund_overview(question, plan)
    return apply_now_window(question, plan)


def align_planned_news_execution(plan: ExecutionPlan) -> ExecutionPlan:
    """Planned wave-2 news with trigger=none never runs; move it to wave 1 for fusion.

    A DATA_ONLY plan is a figure, a list, or a comparison. It does not fetch news.
    """
    if plan.answer_mode == AnswerMode.DATA_ONLY and str(
        getattr(plan, "portfolio_news_mode", "") or "none"
    ) == "none":
        plan.tool_calls = [
            call
            for call in plan.tool_calls
            if call.tool not in ("search_financial_news", "get_macro_news")
        ]
        if (plan.wave_2_policy.trigger or "none").lower() != "none":
            plan.wave_2_policy.trigger = "none"
        return plan
    trigger = (plan.wave_2_policy.trigger or "none").lower()
    if trigger == "none":
        for call in plan.tool_calls:
            if call.tool == "search_financial_news" and call.wave == 2:
                call.wave = 1
    for call in plan.tool_calls:
        if call.tool != "search_financial_news":
            continue
        args = dict(call.arguments or {})
        scope = str(args.get("scope") or "").lower()
        if scope in ("fund", "market") and (plan.funds or str(plan.intent or "") == "overview"):
            args["scope"] = "all"
        wd = int(args.get("window_days") or 0)
        if wd <= 0 or wd > 90:
            args["window_days"] = min(int(plan.window_days or 30), 30)
        args["top_n"] = max(int(args.get("top_n") or 0), 8)
        call.arguments = args
    return plan


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
