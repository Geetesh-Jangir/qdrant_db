"""Last-chance plan repair so tool calls match holdings / allocation questions."""

from __future__ import annotations

import re

from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.memory.fund_context import primary_fund_name

_HOLDINGS_BREAKDOWN_RE = re.compile(
    r"\b(?:hold(?:s|ing)?|holdings?|portfolio|allocation|composition|made\s+of|"
    r"market\s+cap|sector(?:s)?\s+weights?)\b",
    re.I,
)


def _holdings_breakdown_question(question: str) -> bool:
    return bool(_HOLDINGS_BREAKDOWN_RE.search(question or ""))


def validate_plan_tools(
    question: str,
    plan: ExecutionPlan,
    memory: dict | None = None,
) -> ExecutionPlan:
    """Ensure risk + full portfolio when the user asked what a fund holds or how it is allocated."""
    from news_rag.insight.category_plan import ensure_fund_holdings_followup_plan

    plan = ensure_fund_holdings_followup_plan(question, plan, memory)

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
