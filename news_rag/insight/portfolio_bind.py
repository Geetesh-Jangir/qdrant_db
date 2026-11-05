"""Bind an own-book question to the cached portfolio before tools run."""

from __future__ import annotations

import logging
import re
from typing import Any

from news_rag.insight.contracts import ExecutionPlan, ToolCall

logger = logging.getLogger(__name__)

_OWN_BOOK_RE = re.compile(
    r"\b(?:my|mine)\b|\bportfolio\b|\bholdings?\b|\binvested\b",
    re.I,
)
_CONCEPT_ONLY_RE = re.compile(
    r"\bwhat is (?:a |an )?(?:portfolio|holding|mutual fund)\b",
    re.I,
)
_DATA_INTENTS = frozenset({"lookup", "compare", "rank", "overview", "explain_cause", "measure"})

_CATALOG_FUND_HOLDINGS_RE = re.compile(
    r"\b(?:top|largest)\s+\d+\s+holdings?\s+of\b|\bholdings?\s+of\b|\bholdings?\s+in\b",
    re.I,
)


def _catalog_fund_holdings_question(question: str) -> bool:
    """Stock/scheme holdings inside a named mutual fund — not the investor's book."""
    q = (question or "").strip()
    if not q or not re.search(r"\bholdings?\b", q, re.I):
        return False
    if re.search(r"\b(?:my|mine|our)\b", q, re.I):
        return False
    if re.search(r"\bportfolio\b", q, re.I):
        return False
    if _CATALOG_FUND_HOLDINGS_RE.search(q):
        return True
    from news_rag.fund_search import resolve_fund_from_question
    from news_rag.insight.investor_subject import user_explicitly_named_scheme

    detail, ambiguous, _close = resolve_fund_from_question(q)
    if not detail or ambiguous:
        return False
    name = str(detail.get("scheme_name") or detail.get("fund_name") or "").strip()
    return bool(name and user_explicitly_named_scheme(q, name))


def question_mentions_own_book(question: str) -> bool:
    if _CONCEPT_ONLY_RE.search(question or ""):
        return False
    if _catalog_fund_holdings_question(question):
        return False
    return bool(_OWN_BOOK_RE.search(question or ""))


def _investor_args(plan: ExecutionPlan) -> dict[str, Any]:
    from news_rag.insight.portfolio_scope import _modules_for_investor_plan

    modules = _modules_for_investor_plan(plan, "") or ["summary", "allocation", "holdings"]
    for name in ("summary", "allocation", "holdings"):
        if name not in modules:
            modules.append(name)
    return {
        "modules": modules,
        "include_meta": True,
        "holdings_fields": "standard",
        "top_n": 20,
        "sort_by": "aum",
    }


def _merge_fund(plan: ExecutionPlan, name: str) -> None:
    name = str(name or "").strip()
    if not name:
        return
    current = [str(item).strip() for item in (plan.funds or []) if str(item).strip()]
    if name.lower() not in {item.lower() for item in current}:
        current.append(name)
    plan.funds = current


def bind_cached_portfolio(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """Force the book tool and attach the cached holding the question names."""
    if not question_mentions_own_book(question):
        return plan
    if (plan.concept_brief or "").strip() and not plan.tool_calls and str(plan.data_need or "") in ("", "none"):
        return plan
    from news_rag.config import get_settings

    if not get_settings().portfolio_enabled:
        return plan

    from news_rag.insight.investor_subject import (
        _category_slug_from_question,
        question_asks_category_book_share,
        question_asks_whole_investor_portfolio,
        resolve_investor_holding_fund_name,
    )
    from news_rag.portfolio.cache import find_cached_holdings

    comparing = any(call.tool == "compare_funds" for call in plan.tool_calls)
    hits = find_cached_holdings(question)
    if not hits and memory is not None:
        remembered = resolve_investor_holding_fund_name(question, memory)
        if remembered:
            hits = [{"scheme_name": remembered}]
    # A compare keeps the catalog fund in plan.funds. The book tool's scheme_filter
    # and the compare adapter supply the holding. Other asks can take the cached name.
    if hits and not comparing:
        for row in hits:
            _merge_fund(plan, str(row.get("scheme_name") or row.get("name") or ""))

    has_catalog = any(
        call.tool in ("get_fund_data", "compare_funds", "get_portfolio_data") for call in plan.tool_calls
    )
    if (hits or comparing) and str(plan.portfolio_scope or "").lower().strip() in ("none", "", "catalog"):
        plan.portfolio_scope = "both" if has_catalog else "investor"

    if not any(call.tool == "get_investor_portfolio" for call in plan.tool_calls):
        plan.tool_calls = [
            ToolCall(
                tool="get_investor_portfolio",
                arguments=_investor_args(plan),
                wave=1,
                why="Own-book question uses the cached portfolio",
            ),
            *list(plan.tool_calls or []),
        ]
        if str(plan.portfolio_scope or "").lower().strip() in ("none", "", "catalog"):
            plan.portfolio_scope = "investor"
        logger.info("PLAN_PORTFOLIO_TOOL_FORCED funds=%s", plan.funds)

    category = _category_slug_from_question(question)
    if (
        category
        and not question_asks_category_book_share(question)
        and not question_asks_whole_investor_portfolio(question, plan)
    ):
        for call in plan.tool_calls:
            if call.tool != "get_investor_portfolio":
                continue
            args = dict(call.arguments or {})
            if not str(args.get("scheme_filter") or "").strip():
                args["scheme_filter"] = category
                call.arguments = args

    investor_present = any(call.tool == "get_investor_portfolio" for call in plan.tool_calls)
    if comparing and len(plan.funds or []) < 2 and not investor_present and not hits:
        plan.tool_calls = [call for call in plan.tool_calls if call.tool != "compare_funds"]
        if plan.funds and not any(call.tool == "get_fund_data" for call in plan.tool_calls):
            plan.tool_calls.append(
                ToolCall(
                    tool="get_fund_data",
                    arguments={"modules": ["snapshot"], "windows": ["1M"]},
                    wave=1,
                    why="Compare needs two funds; one side is missing",
                )
            )
        logger.info("COMPARE_FUNDS_DROPPED_ONE_FUND funds=%s", plan.funds)
    return plan


def ensure_tools_for_data_question(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """A data question with an empty tool list still fetches. A pure concept does not."""
    if plan.tool_calls:
        return plan
    if (plan.concept_brief or "").strip():
        return plan
    need = str(plan.data_need or "none").lower().strip()
    intent = str(plan.intent or "").lower().strip()
    if need in ("", "none") and intent not in _DATA_INTENTS and not plan.funds:
        return plan
    from news_rag.config import get_settings

    if question_mentions_own_book(question) and get_settings().portfolio_enabled:
        plan.portfolio_scope = "investor"
        plan.tool_calls = [
            ToolCall(
                tool="get_investor_portfolio",
                arguments=_investor_args(plan),
                wave=1,
                why="Planner returned no tools for an own-book question",
            )
        ]
    elif plan.funds:
        plan.tool_calls = [
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"]},
                wave=1,
                why="Planner returned no tools for a fund question",
            )
        ]
    else:
        return plan
    logger.info(
        "PLAN_EMPTY_TOOLS_OVERRIDDEN intent=%s tools=%s",
        intent,
        [call.tool for call in plan.tool_calls],
    )
    return plan


def finish_portfolio_plan_bind(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    plan = bind_cached_portfolio(question, plan, memory)
    return ensure_tools_for_data_question(question, plan)
