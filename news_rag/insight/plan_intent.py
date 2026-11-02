"""Follow-up intent from the planner plan — not regex on the user's raw question."""

from __future__ import annotations

from news_rag.insight.contracts import ExecutionPlan

FUND_PICK_VALUES = (
    "none",
    "best_in_category",
    "alternate_in_category",
    "random_in_category",
    "compare_categories",
)

_ALTERNATE_READING_SIGNALS = (
    "another fund",
    "different fund",
    "other fund",
    "alternate fund",
    "new fund in the same category",
    "not the same fund",
    "different scheme",
    "another scheme",
    "one more fund",
)


def plan_wants_better_rated_in_category(plan: ExecutionPlan, question: str = "") -> bool:
    """User wants a better fund in a category — should use RS rating rank, not return screen."""
    pick = str(getattr(plan, "fund_pick", "") or "").strip().lower()
    if pick == "alternate_in_category":
        return False
    blob = f"{question or ''} {plan.goal or ''} {getattr(plan, 'planner_reading', '') or ''}".lower()
    if "better" not in blob and "upgrade" not in blob and "higher rating" not in blob:
        if pick != "best_in_category":
            return False
        if not (plan.funds or []):
            return False
    from news_rag.fund_rating_categories import match_scheme_category

    if match_scheme_category(question or "") or match_scheme_category(plan.planner_reading or ""):
        return True
    if str(plan.scheme_category or "").strip():
        return True
    if pick == "best_in_category" and plan.funds:
        return True
    return False


def plan_wants_alternate_in_category(plan: ExecutionPlan) -> bool:
    pick = str(getattr(plan, "fund_pick", "") or "").strip().lower()
    if pick == "alternate_in_category":
        return True
    for call in plan.tool_calls or []:
        if call.tool != "screen_funds_by_exposure":
            continue
        if (call.arguments or {}).get("pick_alternate"):
            return True
    return False


def normalize_fund_pick_from_planner(plan: ExecutionPlan) -> None:
    """When the planner's goal/reading says alternate but fund_pick was omitted, set it once."""
    if plan_wants_alternate_in_category(plan):
        return
    if str(plan.intent or "").strip().lower() == "compare":
        return
    blob = f"{plan.goal or ''} {getattr(plan, 'planner_reading', '') or ''}".lower()
    if not blob.strip():
        return
    if any(signal in blob for signal in _ALTERNATE_READING_SIGNALS):
        plan.fund_pick = "alternate_in_category"


def plan_wants_compare_categories(plan: ExecutionPlan) -> bool:
    pick = str(getattr(plan, "fund_pick", "") or "").strip().lower()
    if pick == "compare_categories":
        return True
    if str(plan.intent or "").strip().lower() != "compare":
        return False
    cats = [str(c).strip().lower() for c in (getattr(plan, "scheme_categories", None) or []) if str(c).strip()]
    return len(cats) >= 2


def plan_wants_fund_compare(plan: ExecutionPlan) -> bool:
    if str(plan.intent or "").strip().lower() != "compare":
        return False
    return any(call.tool == "compare_funds" for call in plan.tool_calls or [])


def plan_wants_unnamed_category_pair_compare(
    question: str,
    plan: ExecutionPlan,
    memory: dict | None = None,
) -> bool:
    """Compare two funds in one category when the user did not name schemes."""
    import re

    from news_rag.fund_rating_categories import match_scheme_category

    if str(plan.intent or "").strip().lower() != "compare":
        return False
    if plan_wants_compare_categories(plan):
        return False
    ref = str(plan.subject_ref or "none").strip().lower()
    if ref in {"memory_stack", "memory_primary", "list_cursor"}:
        return False
    match = match_scheme_category(question or "")
    if not match or not match.category:
        return False
    category = str(match.category).strip()
    if memory:
        from news_rag.insight.memory.fund_context import memory_funds_for_category

        if len(memory_funds_for_category(memory, category)) >= 2:
            return False
    q = question or ""
    if not re.search(
        r"\bcompare\b|\bcomparison\b|\bversus\b|\bvs\.?\b",
        q,
        re.I,
    ):
        return False
    if re.search(r"\b(?:two|2|both|pair)\b", q, re.I):
        return True
    if re.search(r"\bcompare\s+two\b", q, re.I):
        return True
    return bool(re.search(r"\bfunds?\b", q, re.I) and "compare" in q.lower())


def reconcile_planner_intent(plan: ExecutionPlan, question: str) -> None:
    """Fix conflicting planner fields before deterministic hooks run."""
    from news_rag.fund_rating_categories import match_all_scheme_categories

    if plan_wants_fund_compare(plan):
        plan.intent = "compare"
        if str(plan.data_need or "none").lower() not in ("none", ""):
            plan.data_need = "none"

    if plan_wants_compare_categories(plan):
        plan.intent = "compare"
        plan.data_need = "none"
        if len(plan.scheme_categories or []) < 2:
            cats = match_all_scheme_categories(question or "")
            if len(cats) >= 2:
                plan.scheme_categories = cats[:3]
    if plan_wants_alternate_in_category(plan):
        if str(plan.data_need or "").lower() in ("category_composition", "category_performance"):
            plan.data_need = "none"

    from news_rag.insight.investor_subject import question_refers_deictic_fund

    if question_refers_deictic_fund(question):
        plan.subject_ref = "memory_primary"
