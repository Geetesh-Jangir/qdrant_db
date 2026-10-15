#!/usr/bin/env python3
"""Run the ask pipeline once from the command line and print the answer plus node timings.

  python scripts/run_ask_once.py "what is the nav of hdfc large cap fund"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from news_rag.ask_engine import run_ask_engine  # noqa: E402
from news_rag.query_log import new_query_logger  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_ask_once.py <question>")
        return 2
    question = " ".join(sys.argv[1:])
    log = new_query_logger()
    result = run_ask_engine(question, query_log=log)
    meta = log.finish_from_ask_result(result, question=question)
    research = result.get("research") or {}
    print("=" * 70)
    print(result.get("insight"))
    print("=" * 70)
    print("plan:", json.dumps(research.get("plan"), ensure_ascii=False))
    for node in research.get("nodes") or []:
        print(f"  node={node['node']:<8} {node['seconds']:>7}s next={node['next']} why={node['why']}")
    print("log:", (meta or {}).get("log_file") or log.log_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
