"""Last-chance plan repair so tool calls match holdings / allocation questions."""

from __future__ import annotations

import re

from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.memory.fund_context import primary_fund_name

_HOLDINGS_BREAKDOWN_RE = re.compile(
    r"\b(?:hold(?:s|ing)?|holdings?|portfolio|allocation|composition|made\s+of|"
    r"market\s+cap|sector(?:s)?\s+weights?)\b",
    re.I,
)


def _holdings_breakdown_question(question: str) -> bool:
    return bool(_HOLDINGS_BREAKDOWN_RE.search(question or ""))


def ensure_silver_news_only(plan: ExecutionPlan) -> ExecutionPlan:
    """Silver has no price feed. Drop silver price args and keep a news call."""
    needs_news = False
    kept: list[ToolCall] = []
    for call in plan.tool_calls or []:
        if call.tool != "get_market_snapshot":
            kept.append(call)
            continue
        args = dict(call.arguments or {})
        modules = [str(item) for item in (args.get("modules") or [])]
        series = [str(item).strip().lower() for item in (args.get("series") or [])]
        if str(args.get("metal") or "").strip().lower() == "silver":
            needs_news = True
            modules = [item for item in modules if item != "metals_spot"]
            args.pop("metal", None)
        if "silver" in series:
            needs_news = True
            series = [item for item in series if item != "silver"]
            args["series"] = series
        if not modules:
            continue
        args["modules"] = modules
        call.arguments = args
        kept.append(call)
    plan.tool_calls = kept
    has_silver_news = any(
        call.tool == "search_financial_news"
        and "silver" in [str(topic).strip().lower() for topic in ((call.arguments or {}).get("topics") or [])]
        for call in plan.tool_calls
    )
    if needs_news and not has_silver_news:
        plan.tool_calls.append(
            ToolCall(
                tool="search_financial_news",
                arguments={
                    "scope": "macro",
                    "topics": ["silver"],
                    "top_n": 8,
                    "window_days": min(int(plan.window_days or 14), 30),
                },
                wave=1,
                why="Silver has no price feed; answer from news",
            )
        )
        if plan.answer_mode == AnswerMode.DATA_ONLY:
            plan.answer_mode = AnswerMode.NEWS_ONLY
    return plan


def validate_plan_tools(
    question: str,
    plan: ExecutionPlan,
    memory: dict | None = None,
) -> ExecutionPlan:
    """Ensure risk + full portfolio when the user asked what a fund holds or how it is allocated."""
    from news_rag.insight.category_plan import ensure_fund_holdings_followup_plan

    plan = ensure_silver_news_only(plan)
    plan = ensure_fund_holdings_followup_plan(question, plan, memory)

    if str(getattr(plan, "portfolio_scope", "") or "").lower() in ("investor", "both"):
        return plan
    if any(c.tool == "get_investor_portfolio" for c in plan.tool_calls):
        return plan

    if not _holdings_breakdown_question(question):
        return plan

    fund = primary_fund_name(memory) or (str(plan.funds[0]).strip() if plan.funds else "")
    has_portfolio = any(c.tool == "get_portfolio_data" for c in plan.tool_calls)
    has_fund_data = any(c.tool == "get_fund_data" for c in plan.tool_calls)

    if fund and (has_portfolio or _holdings_breakdown_question(question)):
        if not plan.funds:
            plan.funds = [fund]

    if fund and not has_fund_data and (has_portfolio or "hold" in (question or "").lower()):
        plan.tool_calls = [
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["risk", "snapshot"]},
                wave=1,
            ),
            *plan.tool_calls,
        ]

    for call in plan.tool_calls:
        if call.tool != "get_portfolio_data":
            continue
        args = dict(call.arguments or {})
        sections = [str(s).lower() for s in (args.get("sections") or [])]
        if "holdings" not in sections:
            sections.append("holdings")
        if "sectors" not in sections:
            sections.append("sectors")
        args["sections"] = sections
        args["top_n"] = max(int(args.get("top_n") or 5), 5)
        call.arguments = args

    for call in plan.tool_calls:
        if call.tool != "get_fund_data":
            continue
        args = dict(call.arguments or {})
        modules = [str(m).lower() for m in (args.get("modules") or [])]
        if "risk" not in modules:
            modules.insert(0, "risk")
        args["modules"] = modules
        call.arguments = args

    return plan
