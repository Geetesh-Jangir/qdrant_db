"""When one named fund question asks for several facts, fetch and keep all of them."""

from __future__ import annotations

import re

from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall, Wave2Policy
from news_rag.insight.top_n import top_n_from_question

_SNAPSHOT_FACTS = frozenset({"nav", "aum", "expense", "exit_load", "returns"})


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
    if re.search(r"\bfund[\s_]+managers?\b|\bmanagers?\b", q, re.I):
        facts.add("managers")
    if re.search(r"\bsectors?\b", q, re.I):
        facts.add("sectors")
    if re.search(r"\bholdings?\b", q, re.I):
        facts.add("holdings")
    return facts


def ensure_multi_fact_tools(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Add the snapshot, manager, and portfolio calls a multi-fact fund question needs."""
    facts = requested_fund_facts(question)
    if len(facts) < 2 or not plan.funds:
        return plan
    if re.search(r"\b(?:news|why|headline)\b", question or "", re.I):
        return plan

    modules: list[str] = []
    if facts & _SNAPSHOT_FACTS:
        modules.append("snapshot")
    if "managers" in facts:
        modules.append("managers")

    fund_call = next((c for c in plan.tool_calls if c.tool == "get_fund_data"), None)
    if modules:
        if fund_call is None:
            plan.tool_calls.insert(
                0,
                ToolCall(tool="get_fund_data", arguments={"modules": modules}, wave=1),
            )
        else:
            existing = [str(m) for m in (fund_call.arguments or {}).get("modules") or []]
            merged = list(dict.fromkeys(existing + modules))
            fund_call.arguments = {**(fund_call.arguments or {}), "modules": merged}

    sections: list[str] = []
    if "sectors" in facts:
        sections.append("sectors")
    if "holdings" in facts:
        sections.append("holdings")
    if sections:
        top_n = top_n_from_question(
            question,
            default=5,
            item="sectors" if sections == ["sectors"] else "holdings" if sections == ["holdings"] else "any",
        )
        port_call = next((c for c in plan.tool_calls if c.tool == "get_portfolio_data"), None)
        if port_call is None:
            plan.tool_calls.append(
                ToolCall(
                    tool="get_portfolio_data",
                    arguments={"sections": sections, "top_n": top_n},
                    wave=1,
                )
            )
        else:
            have = [str(s) for s in (port_call.arguments or {}).get("sections") or []]
            port_call.arguments = {
                **(port_call.arguments or {}),
                "sections": list(dict.fromkeys(have + sections)),
                "top_n": top_n,
            }

    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.wave_2_policy = Wave2Policy(trigger="none")
    plan.tool_calls = [c for c in plan.tool_calls if c.tool != "search_financial_news"]
    return plan


def ensure_compare_template(plan: ExecutionPlan) -> ExecutionPlan:
    """A fund comparison answer is the facts table plus the holdings overlap table."""
    if not any(call.tool == "compare_funds" for call in plan.tool_calls):
        return plan
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.requires_compose = False
    plan.wave_2_policy = Wave2Policy(trigger="none")
    return plan
