"""Evaluation runner for Smart Ask agents (Query Router and Answer Contract).

Usage:
    python scripts/eval_ask_agents.py --mode router
    python scripts/eval_ask_agents.py --mode pinned
    python scripts/eval_ask_agents.py --mode all
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from news_rag.answer import generate_answer
from news_rag.fund_search import lookup_extracted_fund
from news_rag.query_router import route_query
from news_rag.retrieve import retrieve_for_question

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_ask_agents")

CASES_FILE = ROOT / "news_rag" / "eval" / "cases.json"
REPORT_DIR = ROOT / "data" / "rag_eval"
REPORT_FILE = REPORT_DIR / "last_report.json"


def load_cases(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Cases file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_router_case(case: dict[str, Any]) -> dict[str, Any]:
    question = case["question"]
    expected_intent = case.get("expected_intent")
    expected_isin = case.get("expected_fund_isin", "")
    expected_name = case.get("expected_fund_name", "")

    t0 = time.perf_counter()
    router_res = route_query(question)
    duration = time.perf_counter() - t0

    # 1. Intent Match
    intent_match = False
    if isinstance(expected_intent, list):
        intent_match = router_res.intent in expected_intent
    elif isinstance(expected_intent, str):
        intent_match = router_res.intent == expected_intent

    # 2. Fund / ISIN Extraction Match
    fund_match = True
    fund_detail = None
    if expected_isin or expected_name:
        detail, is_ambiguous, close = lookup_extracted_fund(
            isin=router_res.fund.isin,
            name=router_res.fund.name,
        )
        fund_detail = detail
        if expected_isin and not expected_name:
            fund_match = bool(
                router_res.fund.isin.strip().upper() == expected_isin.strip().upper()
                or (detail and detail.get("isin", "").upper() == expected_isin.upper())
            )
        elif expected_name:
            fund_name_lower = (detail.get("fund_short_name", "") or detail.get("fund_name", "")).lower() if detail else ""
            fund_match = bool(
                (detail and expected_name.lower() in fund_name_lower)
                or (expected_name.lower() in router_res.fund.name.lower())
                or (expected_isin and router_res.fund.isin.strip().upper() == expected_isin.strip().upper())
                or (expected_isin and detail and detail.get("isin", "").upper() == expected_isin.upper())
            )
    else:
        # Non-fund case: fund should not resolve
        if router_res.fund.isin or router_res.fund.name:
            detail, _, _ = lookup_extracted_fund(isin=router_res.fund.isin, name=router_res.fund.name)
            if detail:
                fund_match = False

    passed = intent_match and fund_match

    return {
        "id": case["id"],
        "question": question,
        "expected_intent": expected_intent,
        "actual_intent": router_res.intent,
        "intent_match": intent_match,
        "expected_isin": expected_isin,
        "actual_isin": router_res.fund.isin,
        "expected_fund_name": expected_name,
        "actual_fund_name": router_res.fund.name,
        "resolved_isin": fund_detail.get("isin") if fund_detail else None,
        "fund_match": fund_match,
        "passed": passed,
        "duration_sec": round(duration, 3),
    }


def evaluate_pinned_answer_case(case: dict[str, Any]) -> dict[str, Any]:
    question = case["question"]
    must_contain = case.get("must_contain", [])
    must_not_contain = case.get("must_not_contain", [])

    t0 = time.perf_counter()
    parsed, articles = retrieve_for_question(question)
    result = generate_answer(parsed, articles)
    duration = time.perf_counter() - t0

    answer_text = result.get("insight") or (
        " ".join(result.get("insight_bullets") or []) + " " + (result.get("insight_summary") or "")
    )
    answer_lower = answer_text.lower()

    # Check Must Contain
    missing_must_contain: list[str] = []
    for item in must_contain:
        if item.lower() not in answer_lower:
            missing_must_contain.append(item)

    # Check Must NOT Contain (Strict forbidden content check)
    found_forbidden: list[str] = []
    for item in must_not_contain:
        if item.lower() in answer_lower:
            found_forbidden.append(item)

    contract_info = result.get("contract") or {}
    clean_forbidden = len(found_forbidden) == 0
    passed = len(missing_must_contain) == 0 and clean_forbidden

    return {
        "id": case["id"],
        "question": question,
        "intent": parsed.intent,
        "articles_retrieved": len(articles),
        "articles_used": contract_info.get("use_articles_count", 0),
        "contract": contract_info,
        "missing_must_contain": missing_must_contain,
        "found_forbidden": found_forbidden,
        "clean_forbidden": clean_forbidden,
        "passed": passed,
        "insight_source": result.get("insight_source"),
        "answer_preview": answer_text[:250],
        "duration_sec": round(duration, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Smart Ask Query Router and Answer Contract")
    parser.add_argument("--mode", choices=["router", "pinned", "all"], default="all", help="Evaluation mode")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of cases to test")
    args = parser.parse_args()

    cases = load_cases(CASES_FILE)
    if args.limit > 0:
        cases = cases[: args.limit]

    logger.info("Loaded %d test cases from %s", len(cases), CASES_FILE.name)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_cases": len(cases),
        "router": {},
        "pinned_answers": {},
    }

    # 1. Router Evaluation
    if args.mode in ("router", "all"):
        logger.info("Running Router Evaluation on %d cases...", len(cases))
        router_results = []
        router_passes = 0

        for idx, case in enumerate(cases, 1):
            res = evaluate_router_case(case)
            router_results.append(res)
            if res["passed"]:
                router_passes += 1
                logger.info("[%d/%d] PASS: %s (intent=%s, fund=%s)", idx, len(cases), case["id"], res["actual_intent"], res["actual_fund_name"] or res["actual_isin"])
            else:
                logger.warning("[%d/%d] FAIL: %s (expected=%s got=%s, fund_match=%s)", idx, len(cases), case["id"], case.get("expected_intent"), res["actual_intent"], res["fund_match"])
            time.sleep(1.0)

        router_acc = (router_passes / len(cases)) * 100.0 if cases else 0.0
        report["router"] = {
            "total": len(cases),
            "passed": router_passes,
            "accuracy_pct": round(router_acc, 2),
            "target_met": router_acc >= 90.0,
            "details": router_results,
        }
        logger.info("ROUTER RESULTS: %d/%d passed (%.2f%%) - Target >= 90%%: %s", router_passes, len(cases), router_acc, "MET" if router_acc >= 90.0 else "NOT MET")

    # 2. Pinned Answer Evaluation
    if args.mode in ("pinned", "all"):
        pinned_cases = [c for c in cases if c.get("pinned_answer_eval")]
        logger.info("Running Pinned Answer Evaluation on %d cases...", len(pinned_cases))
        answer_results = []
        answer_passes = 0
        forbidden_clean_count = 0

        for idx, case in enumerate(pinned_cases, 1):
            res = evaluate_pinned_answer_case(case)
            answer_results.append(res)
            if res["clean_forbidden"]:
                forbidden_clean_count += 1
            if res["passed"]:
                answer_passes += 1
                logger.info("[%d/%d] PASS: %s (source=%s, forbidden_clean=%s)", idx, len(pinned_cases), case["id"], res["insight_source"], res["clean_forbidden"])
            else:
                logger.warning("[%d/%d] FAIL: %s (missing=%s, forbidden_found=%s)", idx, len(pinned_cases), case["id"], res["missing_must_contain"], res["found_forbidden"])
            time.sleep(1.5)

        answer_acc = (answer_passes / len(pinned_cases)) * 100.0 if pinned_cases else 0.0
        forbidden_acc = (forbidden_clean_count / len(pinned_cases)) * 100.0 if pinned_cases else 0.0

        report["pinned_answers"] = {
            "total": len(pinned_cases),
            "passed": answer_passes,
            "accuracy_pct": round(answer_acc, 2),
            "forbidden_clean_pct": round(forbidden_acc, 2),
            "forbidden_target_met": forbidden_clean_count == len(pinned_cases),
            "details": answer_results,
        }
        logger.info("PINNED ANSWER RESULTS: %d/%d passed (%.2f%%) | Forbidden Clean: %d/%d (%.2f%%)", answer_passes, len(pinned_cases), answer_acc, forbidden_clean_count, len(pinned_cases), forbidden_acc)

    with REPORT_FILE.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info("Report saved to %s", REPORT_FILE)


if __name__ == "__main__":
    main()
