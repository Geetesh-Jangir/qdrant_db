"""Planner-authoritative path: execution helpers only (no regex intent overrides)."""

from __future__ import annotations

from news_rag.insight.contracts import ExecutionPlan


def finalize_planner_plan(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Fill missing entity fields so the planner's tool_calls can run — never swap tools or answer_mode."""
    if (plan.routed_by or "") != "planner":
        return plan
    if not plan.tool_calls:
        return plan

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

    return apply_concept_example_to_plan(question, plan)
