#!/usr/bin/env python3
"""Ask the planner each mapped question and score the tools and news scopes it chose.

  python scripts/eval_tool_mapping.py
  python scripts/eval_tool_mapping.py --limit 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from news_rag.insight.plan import make_plan  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    cases = json.loads((ROOT / "news_rag" / "eval" / "tool_mapping_cases.json").read_text(encoding="utf-8"))
    if args.limit:
        cases = cases[: args.limit]
    tool_hits = tool_total = news_hits = news_total = over = 0
    for case in cases:
        plan = make_plan(case["question"])
        if plan is None:
            print("planner unavailable (no API key)")
            return 1
        got = set(plan.tool_names)
        want = set(case["tools"])
        tool_hits += len(got & want)
        tool_total += len(want)
        scopes = {row["scope"] for row in plan.layer2_news}
        news_hits += len(scopes & set(case["news"]))
        news_total += len(case["news"])
        if not case["news"] and scopes:
            over += 1
            print(f"OVERFETCH {case['id']}: news {sorted(scopes)} for a lookup")
        missing = sorted(want - got)
        if missing:
            print(f"MISS {case['id']}: {missing} got {sorted(got)}")
    precision_base = tool_total or 1
    print(
        f"cases={len(cases)} tool_recall={tool_hits}/{tool_total} ({tool_hits / precision_base:.0%}) "
        f"news_recall={news_hits}/{news_total or 1} lookup_overfetch={over}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
