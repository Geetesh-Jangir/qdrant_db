#!/usr/bin/env python3
"""Score insight v2 ask responses against cases_v2.json (needs LLM+Qdrant for full runs)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_rag.eval.v2_scoring import load_cases_v2, score_case


def _run_ask(question: str) -> dict:
    from news_rag.ask_engine import run_ask_engine

    return run_ask_engine(question)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--brief-only", action="store_true", help="Score heuristic brief without full ask")
    args = parser.parse_args()

    cases = load_cases_v2()
    if args.limit > 0:
        cases = cases[: args.limit]

    report: dict = {"cases": [], "summary": {}}
    pass_count = brief_pass = 0

    for case in cases:
        q = case.get("question") or ""
        cid = case.get("id")
        entry: dict = {"id": cid}
        if args.brief_only:
            from news_rag.insight.brief import _heuristic_brief

            brief = _heuristic_brief(q)
            fake = {
                "research": {"evidence_needs": brief.evidence_needs, "ledger": [], "findings": {}},
                "sub_queries": [{"text": a.text} for a in brief.sub_asks],
                "retrieval_window": {"window_days": brief.window_days},
                "insight": "",
            }
            sc = score_case(fake, case)
            entry["brief_score"] = sc
            if sc["passed"]:
                brief_pass += 1
            report["cases"].append(entry)
            continue

        try:
            result = _run_ask(q)
            scored = score_case(result, case)
            entry["score"] = scored
            if scored["passed"]:
                pass_count += 1
        except Exception as exc:
            entry["score"] = {"passed": False, "failures": [str(exc)]}
        report["cases"].append(entry)

    n = len(cases)
    report["summary"] = {
        "count": n,
        "pass": pass_count,
        "brief_pass": brief_pass,
        "mode": "brief-only" if args.brief_only else "insight_v2",
    }
    out = _ROOT / "data" / "rag_eval" / "v2_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
