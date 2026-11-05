"""Live planner evaluation: routing accuracy and token use over tests/eval/planner_cases.py.

    python scripts/eval_planner.py [--workers 4] [--out data/eval_results/planner.json]

Calls the configured planner model, so it needs ANTHROPIC_API_KEY. Not part of the unit tests.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "eval"))

from planner_cases import CASES  # noqa: E402


class _Usage:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add_llm_usage(self, **kw) -> None:  # matches RequestTelemetry.add_llm_usage
        self.rows.append(kw)


def run_case(case: dict) -> dict:
    from news_rag.insight.plan import make_plan
    from news_rag.insight.plan_enforce import apply_planner_post_hooks

    usage = _Usage()
    plan = make_plan(case["q"], telemetry=usage)
    if plan is None:
        return {"q": case["q"], "fail": ["no plan"], "tools": [], "usage": usage.rows}
    planned = [c.tool for c in plan.tool_calls]
    try:
        plan = apply_planner_post_hooks(case["q"], plan, None)
    except Exception as exc:  # noqa: BLE001
        return {"q": case["q"], "fail": [f"hooks error {exc}"], "tools": planned, "usage": usage.rows}
    return {"q": case["q"], "fail": check(case, plan), "tools": [c.tool for c in plan.tool_calls], "planned": planned, "usage": usage.rows}


def check(case: dict, plan) -> list[str]:
    fails: list[str] = []
    calls = plan.tool_calls
    names = [c.tool for c in calls]
    if "tools_exact" in case and sorted(set(names)) != sorted(case["tools_exact"]):
        fails.append(f"tools {names} != {case['tools_exact']}")
    for t in case.get("tools_include", []):
        if t not in names:
            fails.append(f"missing {t}")
    for t in case.get("tools_exclude", []):
        if t in names:
            fails.append(f"unexpected {t}")
    if len(calls) > case.get("max_tools", 3):
        fails.append(f"{len(calls)} tool calls")

    def first(tool: str):
        return next((c for c in calls if c.tool == tool), None)

    fund = first("get_fund_data")
    inv = first("get_investor_portfolio")
    want_modules = case.get("modules")
    if want_modules is not None:
        call = fund or inv
        got = sorted((call.arguments or {}).get("modules") or []) if call else []
        if got != sorted(want_modules):
            fails.append(f"modules {got} != {want_modules}")
    for m in case.get("modules_include", []):
        got = (fund.arguments or {}).get("modules") or [] if fund else []
        if m not in got:
            fails.append(f"module {m} missing")
    if "windows" in case:
        got = [str(w).upper() for w in ((fund.arguments or {}).get("windows") or [])] if fund else []
        if got != case["windows"]:
            fails.append(f"windows {got} != {case['windows']}")
    if "windows_if_fund_data" in case and fund:
        got = [str(w).upper() for w in ((fund.arguments or {}).get("windows") or [])]
        if got != case["windows_if_fund_data"]:
            fails.append(f"windows {got}")
    port = first("get_portfolio_data")
    if "sections" in case:
        got = sorted((port.arguments or {}).get("sections") or []) if port else []
        if got != sorted(case["sections"]):
            fails.append(f"sections {got}")
    if "top_n" in case and port and (port.arguments or {}).get("top_n") != case["top_n"]:
        fails.append(f"top_n {(port.arguments or {}).get('top_n')}")
    screen = first("screen_funds_by_exposure")
    if "top_n_screen" in case and screen and (screen.arguments or {}).get("top_n") != case["top_n_screen"]:
        fails.append(f"screen top_n {(screen.arguments or {}).get('top_n')}")
    if "scope" in case and (plan.portfolio_scope or "none") not in case["scope"]:
        fails.append(f"scope {plan.portfolio_scope}")
    if "advice" in case and bool(plan.asks_for_advice) != case["advice"]:
        fails.append(f"advice {plan.asks_for_advice}")
    return fails


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="data/eval_results/planner.json")
    args = ap.parse_args()
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(run_case, CASES))
    passed = sum(1 for r in results if not r["fail"])
    usage = [u for r in results for u in r["usage"]]
    totals = {k: sum(int(u.get(k) or 0) for u in usage) for k in ("input_tokens", "output_tokens", "cached_input_tokens")}
    tool_counts = [len(r["tools"]) for r in results]
    summary = {
        "passed": passed,
        "total": len(results),
        "avg_tools": round(sum(tool_counts) / max(1, len(tool_counts)), 2),
        "avg_latency_ms": round(sum(float(u.get("total_ms") or 0) for u in usage) / max(1, len(usage))),
        **totals,
    }
    for r in results:
        if r["fail"]:
            print("FAIL", r["q"][:70], "->", r["fail"], r["tools"])
    print(json.dumps(summary))
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "results": results}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
