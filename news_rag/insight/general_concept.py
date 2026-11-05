"""Detect general/concept asks that should not call catalog tools."""

from __future__ import annotations

import re

from news_rag.insight.contracts import ExecutionPlan

_CONCEPT_RE = re.compile(
    r"\b(?:"
    r"what\s+is|what\s+are|what\s+do\s+you\s+mean|"
    r"difference\s+between|different\s+from|how\s+is\s+.+\s+different|"
    r"how\s+does\s+.+\s+work|explain\s+(?:what|how)|"
    r"different\s+from|how\s+.+\s+different|"
    r"meaning\s+of|tell\s+me\s+about\s+(?:large|mid|small|multi|flexi|hybrid|debt|equity)\b"
    r")\b",
    re.I,
)
_VERSUS_RE = re.compile(
    r"\b(?:vs\.?|versus)\b|"
    r"\b(?:large|mid|small|multi)\s+cap\b.+\b(?:large|mid|small|multi)\s+cap\b",
    re.I,
)
_MY_BOOK_RE = re.compile(r"\b(?:my|mine|i\s+hold|our\s+portfolio)\b", re.I)
_CATALOG_LIST_RE = re.compile(
    r"\b(?:"
    r"all\s+(?:\w+\s+){0,4}funds?|every\s+fund|list\s+(?:all\s+)?(?:\w+\s+){0,3}funds?|"
    r"top\s+\d+\s+(?:\w+\s+){0,3}funds?|show\s+me\s+\d+\s+(?:\w+\s+){0,3}funds?"
    r")\b",
    re.I,
)
_NUMBERED_LIST_RE = re.compile(r"\b(?:top|best|worst)\s+\d+\b|\b\d+\s+(?:\w+\s+){0,2}funds?\b", re.I)
_CATEGORY_CONCEPT_RE = re.compile(
    r"\b(?:large|mid|small|multi|flexi|large\s*&\s*mid)\s+cap\b|"
    r"\b(?:debt|equity|hybrid|index|sectoral|thematic)\s+funds?\b",
    re.I,
)
# An AMC or scheme name means the user wants that fund, not a category definition.
_NAMED_SCHEME_RE = re.compile(
    r"\b(?:hdfc|icici|sbi|axis|kotak|bandhan|parag|quant|invesco|nippon|mirae|"
    r"dsp|motilal|uti|tata|canara|aditya|birla|edelweiss|franklin|hsbc|idfc|"
    r"lic|mahindra|navi|pgim|ppfas|whiteoak)\b",
    re.I,
)
_SCHEME_FIGURE_RE = re.compile(
    r"\b(?:nav|aum|expense|exit\s+load|ter|returns?|holdings?|sectors?|"
    r"managers?|benchmark|inception)\b",
    re.I,
)


def question_is_pure_general_concept(question: str) -> bool:
    q = (question or "").strip()
    if not q:
        return False
    from news_rag.insight.concept_asks import asks_concept_with_catalog_example
    from news_rag.insight.computed_answers import asks_computed_illustration
    from news_rag.insight.glossary import asks_precise_definition

    if asks_concept_with_catalog_example(q) or asks_computed_illustration(q):
        return False
    if _MY_BOOK_RE.search(q):
        return False
    if _CATALOG_LIST_RE.search(q) and not re.search(r"\bwhat\s+(?:is|are)\b", q, re.I):
        return False
    if _NUMBERED_LIST_RE.search(q) and not _CONCEPT_RE.search(q):
        return False
    try:
        from news_rag.domain_intake import question_mentions_fund_scheme

        mentions_scheme = question_mentions_fund_scheme(q)
    except Exception:
        mentions_scheme = False
    category_concept = bool(_CATEGORY_CONCEPT_RE.search(q)) and (
        _CONCEPT_RE.search(q) or _VERSUS_RE.search(q)
    )
    if mentions_scheme and not category_concept:
        return False
    # "what is the aum of hdfc large cap" names a scheme. The category word is part of the name.
    if _NAMED_SCHEME_RE.search(q) and (
        _SCHEME_FIGURE_RE.search(q) or re.search(r"\bfunds?\b", q, re.I)
    ):
        if not re.search(r"\b(?:different|difference|versus|\bvs\.?\b)\b", q, re.I):
            return False
    if asks_precise_definition(q):
        return True
    if _CONCEPT_RE.search(q) or _VERSUS_RE.search(q):
        return True
    return False


def apply_pure_concept_plan(plan: ExecutionPlan, question: str) -> ExecutionPlan:
    from news_rag.insight.brief import question_is_standalone_macro

    if question_is_standalone_macro(question):
        return plan
    task = str(getattr(plan, "planner_task", None) or "").lower()
    # A resolved scheme is a data question even when its name contains "large cap" or "hybrid".
    if plan.funds and task != "explain":
        return plan
    if task == "data" and plan.tool_calls:
        return plan
    if not question_is_pure_general_concept(question):
        return plan
    plan.tool_calls = []
    plan.portfolio_scope = "none"
    plan.direct_reply = ""
    plan.requires_compose = True
    plan.max_words = max(int(plan.max_words or 0), 180)
    if str(plan.response_shape or "") == "short_answer" and plan.max_words >= 180:
        plan.response_shape = "sections"
    return plan
