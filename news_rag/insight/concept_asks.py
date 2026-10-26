"""Concept explanation + catalog example (e.g. what is FoF and name one)."""

from __future__ import annotations

import re

from news_rag.insight.contracts import (
    AnswerMode,
    ExecutionPlan,
    QueryClass,
    ScopeKind,
    ToolCall,
    Wave2Policy,
)

FOF_CONCEPT_BRIEF = (
    "A **Fund of Funds (FoF)** is a mutual fund that invests mainly in other mutual fund schemes "
    "(across equity, debt, hybrid, etc.) instead of buying stocks or bonds directly. "
    "It gives one NAV and one folio while spreading across multiple underlying funds."
)

_WANTS_EXAMPLE_RE = re.compile(
    r"\b(?:"
    r"(?:you\s+)?name|give|show|tell|list|suggest|pick|share"
    r")\s+(?:me\s+)?(?:any\s+)?(?:one|an?\s+example|a\s+scheme|a\s+fund)"
    r"\b|\bname\s+any\s+one\b|\bone\s+of\s+them\b|\bany\s+one\s+of\s+them\b",
    re.I,
)


def asks_wants_named_example(question: str) -> bool:
    return bool(_WANTS_EXAMPLE_RE.search(question or ""))


def concept_brief_for_question(question: str) -> str | None:
    from news_rag.tools import asks_fof_funds

    if asks_fof_funds(question or ""):
        return FOF_CONCEPT_BRIEF
    return None


def asks_concept_with_catalog_example(question: str) -> bool:
    q = question or ""
    if not asks_wants_named_example(q):
        return False
    return concept_brief_for_question(q) is not None


def build_concept_example_plan(
    question: str,
    *,
    routed_by: str = "slot_router",
) -> ExecutionPlan | None:
    brief = concept_brief_for_question(question)
    if not brief or not asks_wants_named_example(question):
        return None
    from news_rag.tools import asks_fof_funds

    goal = (
        "Explain what a Fund of Funds (FoF) is and name one example scheme from the catalog"
        if asks_fof_funds(question)
        else "Explain the concept and name one matching example scheme from the catalog"
    )
    return ExecutionPlan(
        scope_kind=ScopeKind.IN_SCOPE,
        intent="lookup",
        goal=goal,
        answer_mode=AnswerMode.DATA_ONLY,
        query_class=QueryClass.SIMPLE,
        concept_brief=brief,
        requires_compose=True,
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={
                    "direction": "any",
                    "top_n": 1,
                    "return_window": "1M",
                },
                wave=1,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        response_shape="sections",
        max_words=130,
        presentation_notes=(
            "Use concept_brief for the definition (1–3 sentences). Then name exactly one example "
            "fund from DATA screen rankings (fund name; add category or ISIN if present). "
            "Do not invent scheme names."
        ),
        routed_by=routed_by,
        confidence=0.97,
    )


def apply_concept_example_to_plan(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Planner path: attach concept brief + ensure catalog screen for FoF-style asks."""
    if not asks_concept_with_catalog_example(question):
        return plan
    brief = concept_brief_for_question(question)
    if not brief:
        return plan
    if not plan.tool_calls:
        ref = build_concept_example_plan(question, routed_by=plan.routed_by or "planner")
        if ref:
            plan.tool_calls = list(ref.tool_calls)
            plan.goal = ref.goal
            plan.answer_mode = ref.answer_mode
            plan.response_shape = ref.response_shape
    plan.concept_brief = brief
    plan.requires_compose = True
    plan.max_words = max(int(plan.max_words or 0), 130)
    if not plan.goal:
        plan.goal = build_concept_example_plan(question, routed_by=plan.routed_by or "planner").goal
    notes = (
        "Use concept_brief for the definition. Name one example from DATA screen rankings only."
    )
    plan.presentation_notes = (plan.presentation_notes + " " + notes).strip() if plan.presentation_notes else notes

    screen_calls = [c for c in plan.tool_calls if c.tool == "screen_funds_by_exposure"]
    if not screen_calls:
        plan.tool_calls = [
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"direction": "any", "top_n": 1, "return_window": "1M"},
                wave=1,
            ),
        ]
    else:
        for call in screen_calls:
            args = dict(call.arguments or {})
            args["top_n"] = 1
            args.setdefault("direction", "any")
            args.setdefault("return_window", "1M")
            call.arguments = args
    return plan
