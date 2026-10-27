"""When one named fund question asks for several facts, fetch and keep all of them."""

from __future__ import annotations

import re

from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall, Wave2Policy
from news_rag.insight.top_n import top_n_from_question

_SNAPSHOT_FACTS = frozenset(
    {"nav", "aum", "expense", "exit_load", "returns", "benchmark", "risk", "inception"}
)


def requested_fund_facts(question: str) -> set[str]:
    """Facts named in one question. Empty when the question is not a fact list."""
    q = question or ""
    facts: set[str] = set()
    if re.search(r"\b(?:nav|net\s+asset\s+value)\b", q, re.I):
        facts.add("nav")
    if re.search(r"\baum\b|assets?\s+under\s+management", q, re.I):
        facts.add("aum")
    if re.search(r"\bexpense\s+ratio\b|\bter\b", q, re.I):
        facts.add("expense")
    if re.search(r"\bexit\s+load\b", q, re.I):
        facts.add("exit_load")
    if re.search(r"\bhistorical\s+performance\b|\breturns?\b", q, re.I):
        facts.add("returns")
    if re.search(
        r"\bfund[\s_]*managers?\b|\bmanagers?\b|\bwho\s+manages\b|\bmanaged\s+by\b",
        q,
        re.I,
    ):
        facts.add("managers")
    if re.search(r"\bbenchmark\b", q, re.I):
        facts.add("benchmark")
    if re.search(r"\brisk(?:ometer)?\b", q, re.I):
        facts.add("risk")
    if re.search(r"\b(?:inception|launch\s+date|fund\s+age)\b", q, re.I):
        facts.add("inception")
    if re.search(r"\bsectors?\b", q, re.I):
        facts.add("sectors")
    if re.search(r"\bholdings?\b", q, re.I):
        facts.add("holdings")
    return facts


def screen_fact_names(question: str) -> list[str]:
    """Facts to add onto a fund screen. The word sector alone is the screen, not a column."""
    facts = set(requested_fund_facts(question))
    if "sectors" in facts and not re.search(
        r"\b(?:top\s+(?:\d+\s+)?sectors?|sector\s+allocation|their\s+sectors)\b",
        question or "",
        re.I,
    ):
        facts.discard("sectors")
    if "holdings" in facts and not re.search(
        r"\b(?:their\s+holdings|top\s+(?:\d+\s+)?holdings|stock\s+holdings)\b",
        question or "",
        re.I,
    ):
        facts.discard("holdings")
    if "managers" in facts:
        asks_name = bool(re.search(r"\bnames?\b", question or "", re.I))
        asks_experience = bool(re.search(r"\b(?:experienc\w*|tenure|managing\s+since)\b", question or "", re.I))
        if asks_name or not asks_experience:
            facts.add("manager_name")
        if asks_experience or not asks_name:
            facts.add("manager_experience")
        facts.discard("managers")
    order = [
        "nav",
        "aum",
        "expense",
        "exit_load",
        "category",
        "benchmark",
        "risk",
        "inception",
        "returns",
        "manager_name",
        "manager_experience",
        "sectors",
        "holdings",
    ]
    return [name for name in order if name in facts]


def ensure_screen_facts(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """A sector screen plus extra facts stays a screen. Do not swap in one other fund."""
    if not any(call.tool == "screen_funds_by_exposure" for call in plan.tool_calls):
        return plan
    if not screen_fact_names(question):
        return plan
    plan.tool_calls = [
        call for call in plan.tool_calls if call.tool not in ("get_fund_data", "get_portfolio_data")
    ]
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.requires_compose = False
    question_l = (question or "").lower()
    kept: list[str] = []
    for fund in plan.funds:
        words = [
            word
            for word in re.findall(r"[a-z0-9]+", fund.lower())
            if len(word) > 3 and word not in {"fund", "regular", "plan", "growth", "direct"}
        ]
        if words and all(word in question_l for word in words[:2]):
            kept.append(fund)
    plan.funds = kept
    return plan


def ensure_multi_fact_tools(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """A named fact uses one call and a data answer. A fund overview is left alone."""
    facts = requested_fund_facts(question)
    if not plan.funds or not facts:
        return plan
    if re.search(r"\b(?:news|why|headline)\b", question or "", re.I):
        return plan
    if any(call.tool in ("screen_funds_by_exposure", "compare_funds") for call in plan.tool_calls):
        return plan

    modules: list[str] = []
    if facts & _SNAPSHOT_FACTS:
        modules.append("snapshot")
    if "managers" in facts:
        modules.append("managers")

    sections: list[str] = []
    if "sectors" in facts:
        sections.append("sectors")
    if "holdings" in facts:
        sections.append("holdings")

    calls: list[ToolCall] = []
    if modules:
        calls.append(ToolCall(tool="get_fund_data", arguments={"modules": modules}, wave=1))
    if sections:
        top_n = top_n_from_question(
            question,
            default=5,
            item="sectors" if sections == ["sectors"] else "holdings" if sections == ["holdings"] else "any",
        )
        calls.append(
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": sections, "top_n": top_n},
                wave=1,
            )
        )
    if not calls:
        return plan

    plan.tool_calls = calls
    plan.asked_facts = sorted(facts)
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.requires_compose = False
    plan.wave_2_policy = Wave2Policy(trigger="none")
    return plan


def ensure_compare_template(plan: ExecutionPlan) -> ExecutionPlan:
    """A fund comparison answer is the facts table plus the holdings overlap table."""
    if not any(call.tool == "compare_funds" for call in plan.tool_calls):
        return plan
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.requires_compose = False
    plan.wave_2_policy = Wave2Policy(trigger="none")
    return plan
