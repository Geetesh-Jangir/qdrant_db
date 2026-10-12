#!/usr/bin/env python3
"""Compare ask v1 vs insight v2 on cases_v2.json (pinned cases need LLM+Qdrant)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_rag.eval.v2_scoring import load_cases_v2, score_case


def _run_v1(question: str) -> dict:
    os.environ["ASK_PIPELINE_V2"] = "0"
    from importlib import reload
    import news_rag.config as cfg
    import news_rag.ask_engine as eng

    reload(cfg)
    reload(eng)
    return eng.run_ask_engine(question)


def _run_v2(question: str) -> dict:
    os.environ["ASK_PIPELINE_V2"] = "1"
    from importlib import reload
    import news_rag.config as cfg
    import news_rag.ask_engine as eng

    reload(cfg)
    reload(eng)
    return eng.run_ask_engine(question)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["v1", "v2", "both"], default="both")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--brief-only", action="store_true", help="Score heuristic brief without full ask")
    args = parser.parse_args()

    cases = load_cases_v2()
    if args.limit > 0:
        cases = cases[: args.limit]

    report: dict = {"cases": [], "summary": {}}
    v1_pass = v2_pass = brief_pass = 0

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

        if args.mode in ("v1", "both"):
            try:
                r1 = _run_v1(q)
                s1 = score_case(r1, case)
                entry["v1"] = s1
                if s1["passed"]:
                    v1_pass += 1
            except Exception as exc:
                entry["v1"] = {"passed": False, "failures": [str(exc)]}
        if args.mode in ("v2", "both"):
            try:
                r2 = _run_v2(q)
                s2 = score_case(r2, case)
                entry["v2"] = s2
                if s2["passed"]:
                    v2_pass += 1
            except Exception as exc:
                entry["v2"] = {"passed": False, "failures": [str(exc)]}
        report["cases"].append(entry)

    n = len(cases)
    report["summary"] = {
        "count": n,
        "v1_pass": v1_pass,
        "v2_pass": v2_pass,
        "brief_pass": brief_pass,
        "mode": "brief-only" if args.brief_only else args.mode,
    }
    out = _ROOT / "data" / "rag_eval" / "v2_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
