#!/usr/bin/env python3
"""Check basic fund, portfolio, and news questions.

  python scripts/eval_basic_queries.py              # regex + tool binding, no LLM
  python scripts/eval_basic_queries.py --live       # also run the planner (one LLM call per turn)
  python scripts/eval_basic_queries.py --full       # full ask pipeline and answer text
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from news_rag.insight.contracts import AnswerMode, ExecutionPlan  # noqa: E402
from news_rag.insight.fields import bind_fields_to_tools, fields_from_question  # noqa: E402


def _cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _turns(case: dict) -> list[str]:
    if case.get("turns"):
        return list(case["turns"])
    return [str(case.get("question") or "")]


def _expects(case: dict) -> list[dict]:
    if case.get("expect_turns"):
        return list(case["expect_turns"])
    return [dict(case.get("expect") or {})]


def _modules(plan: ExecutionPlan, tool: str, key: str) -> list[str]:
    for call in plan.tool_calls:
        if call.tool == tool:
            return [str(item) for item in ((call.arguments or {}).get(key) or [])]
    return []


def _check_plan(plan: ExecutionPlan, expect: dict, failures: list[str]) -> None:
    fields = list(plan.asked_fields or [])
    if "fields" in expect and fields != list(expect["fields"]):
        failures.append(f"fields {fields} != {expect['fields']}")
    if expect.get("modules"):
        got = _modules(plan, "get_fund_data", "modules")
        missing = [name for name in expect["modules"] if name not in got]
        if missing:
            failures.append(f"missing modules {missing} in {got}")
    for name in expect.get("forbid_modules") or []:
        if name in _modules(plan, "get_fund_data", "modules"):
            failures.append(f"module {name} should not be fetched")
    if expect.get("windows"):
        got = _modules(plan, "get_fund_data", "windows")
        if got != list(expect["windows"]):
            failures.append(f"windows {got} != {expect['windows']}")
    if expect.get("sections"):
        got = _modules(plan, "get_portfolio_data", "sections")
        missing = [name for name in expect["sections"] if name not in got]
        if missing:
            failures.append(f"missing sections {missing}")
    if expect.get("investor_modules"):
        got = _modules(plan, "get_investor_portfolio", "modules")
        missing = [name for name in expect["investor_modules"] if name not in got]
        if missing:
            failures.append(f"missing investor modules {missing} in {got}")
    for tool in expect.get("forbid_tools") or []:
        if any(call.tool == tool for call in plan.tool_calls):
            failures.append(f"tool {tool} should not be called")


def _offline_plan(question: str) -> ExecutionPlan:
    plan = ExecutionPlan(intent="lookup", answer_mode=AnswerMode.DATA_ONLY, routed_by="planner")
    return bind_fields_to_tools(question, plan)


def _live_plan(question: str) -> ExecutionPlan | None:
    from news_rag.insight.fund_concentration import ensure_fund_concentration_plan
    from news_rag.insight.multi_fact import ensure_planner_fund_fact_modules
    from news_rag.insight.plan import make_plan
    from news_rag.insight.plan_catalog_bind import enforce_planner_catalog_plan
    from news_rag.insight.plan_enforce import apply_planner_post_hooks
    from news_rag.insight.plan_validate import validate_plan_tools
    from news_rag.insight.planner_policy import align_planned_news_execution

    plan = make_plan(question, prior_context=None)
    if plan is None:
        return None
    plan = apply_planner_post_hooks(question, plan, None)
    plan = enforce_planner_catalog_plan(plan, None)
    plan = align_planned_news_execution(plan)
    plan = validate_plan_tools(question, plan, None)
    plan = ensure_planner_fund_fact_modules(question, plan)
    plan = ensure_fund_concentration_plan(question, plan)
    return bind_fields_to_tools(question, plan)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Call the planner LLM")
    parser.add_argument("--full", action="store_true", help="Run the ask pipeline and check the answer")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--cases", default=str(ROOT / "queries" / "basic_cases.json"))
    args = parser.parse_args()
    cases = _cases(Path(args.cases))
    if args.limit:
        cases = cases[: args.limit]
    failed = 0
    for case in cases:
        started = time.perf_counter()
        problems: list[str] = []
        for question, expect in zip(_turns(case), _expects(case)):
            if args.full:
                from news_rag.ask_engine import run_ask_engine

                result = run_ask_engine(question)
                answer = str(result.get("insight") or "")
                for needle in expect.get("answer_contains") or []:
                    if needle.lower() not in answer.lower():
                        problems.append(f"answer missing {needle!r}")
                for needle in expect.get("answer_not_contains") or []:
                    if needle.lower() in answer.lower():
                        problems.append(f"answer should not contain {needle!r}")
                continue
            regex_fields = fields_from_question(question)
            if "fields" in expect and regex_fields != list(expect["fields"]):
                problems.append(f"regex fields {regex_fields} != {expect['fields']}")
            plan = _live_plan(question) if args.live else _offline_plan(question)
            if plan is None:
                problems.append("planner returned no plan")
                continue
            if expect.get("live_answer_mode") and args.live:
                if plan.answer_mode.value != expect["live_answer_mode"]:
                    problems.append(f"answer_mode {plan.answer_mode.value}")
            if not expect.get("live_answer_mode"):
                _check_plan(plan, expect, problems)
        elapsed = time.perf_counter() - started
        status = "FAIL" if problems else "PASS"
        if problems:
            failed += 1
        print(f"{status} {case.get('id')} {elapsed:.1f}s {'; '.join(problems)}")
    print(f"{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
