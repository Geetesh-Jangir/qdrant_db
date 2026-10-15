#!/usr/bin/env python3
"""Compare two ask runs (summary JSON) on latency, tokens and answer overlap.

Capture a baseline with the speed flags off, then a candidate with them on:

  INSIGHT_BRIEF_TIERING=0 INSIGHT_PRUNE_MARKET_FACETS=0 INSIGHT_ANALYST_MODE=always \\
  INSIGHT_USE_NEWS_DIGEST=0 INSIGHT_JSON_TOOL_USE=0 \\
  python scripts/run_ask_once.py "question"

  python scripts/compare_ask_speed.py baseline.json candidate.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _load(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "summary" in data and "total_seconds" not in data:
        return data["summary"]
    return data


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text or ""))


def compare(baseline: dict, candidate: dict) -> dict:
    base_text = str(baseline.get("insight") or baseline.get("question") or "")
    cand_text = str(candidate.get("insight") or "")
    # Summary sidecars store the question, not the insight body. Prefer research when present.
    base_research = baseline.get("research_summary") or {}
    cand_research = candidate.get("research_summary") or {}
    return {
        "baseline_seconds": baseline.get("total_seconds"),
        "candidate_seconds": candidate.get("total_seconds"),
        "baseline_llm_calls": baseline.get("llm_calls"),
        "candidate_llm_calls": candidate.get("llm_calls"),
        "baseline_input_tokens": baseline.get("llm_input_tokens"),
        "candidate_input_tokens": candidate.get("llm_input_tokens"),
        "baseline_facets": base_research.get("evidence_needs"),
        "candidate_facets": cand_research.get("evidence_needs"),
        "baseline_verify_gaps": base_research.get("verify_gaps"),
        "candidate_verify_gaps": cand_research.get("verify_gaps"),
        "number_overlap": sorted(_numbers(base_text) & _numbers(cand_text)),
        "stage_summary": candidate.get("stage_summary"),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: compare_ask_speed.py baseline.json candidate.json")
        return 2
    report = compare(_load(sys.argv[1]), _load(sys.argv[2]))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
