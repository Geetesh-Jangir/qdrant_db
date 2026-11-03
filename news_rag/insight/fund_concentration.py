"""Catalog-fund concentration asks — tools and deterministic answers."""

from __future__ import annotations

from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.investor_drawback import plan_wants_fund_concentration


def ensure_fund_concentration_plan(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Fetch holdings, sectors, and scheme-level concentration stats for one fund."""
    if not plan_wants_fund_concentration(plan, question):
        return plan

    want_n = max(5, int(plan.planner_count or 0) or 10)
    for call in plan.tool_calls or []:
        if call.tool == "get_portfolio_data":
            args = dict(call.arguments or {})
            sections = [str(s).lower() for s in (args.get("sections") or [])]
            if "holdings" not in sections:
                sections.append("holdings")
            if "sectors" not in sections:
                sections.append("sectors")
            args["sections"] = sections
            args["top_n"] = max(int(args.get("top_n") or 0), want_n)
            call.arguments = args
        elif call.tool == "get_fund_data":
            args = dict(call.arguments or {})
            modules = [str(m) for m in (args.get("modules") or [])]
            for mod in ("risk", "composition"):
                if mod not in modules:
                    modules.append(mod)
            args["modules"] = modules
            windows = args.get("windows")
            if windows:
                args.pop("windows", None)
            call.arguments = args

    has_portfolio = any(c.tool == "get_portfolio_data" for c in plan.tool_calls or [])
    if not has_portfolio and plan.funds:
        plan.tool_calls.append(
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": ["holdings", "sectors"], "top_n": want_n},
                wave=1,
            )
        )

    plan.requires_compose = False
    plan.answer_mode = plan.answer_mode
    return plan
