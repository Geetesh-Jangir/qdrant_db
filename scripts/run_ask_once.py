"""Run the insight pipeline once, in-process, with a query log. Usage: python scripts/run_ask_once.py "question" """

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from news_rag.insight.pipeline import run_insight_pipeline  # noqa: E402
from news_rag.query_log import new_query_logger  # noqa: E402

DEFAULT_Q = "How is the automobile sector doing? Which funds are highly impacted — positively or negatively?"


def main() -> None:
    q = " ".join(sys.argv[1:]).strip() or DEFAULT_Q
    log = new_query_logger()
    t0 = time.perf_counter()
    out = run_insight_pipeline(q, query_log=log)
    log.finish(outcome=str(out.get("outcome") or ""), article_count=len(out.get("sources") or []))
    print(f"\n=== {round(time.perf_counter() - t0, 1)}s | log: {log.log_path} ===\n")
    print(out.get("insight") or "(no insight)")
    print("\n--- gaps:", (out.get("research") or {}).get("verify_gaps"))
    print("--- scores:", out.get("output_scores"))
    print("--- errors:", out.get("pipeline_errors"))


if __name__ == "__main__":
    main()
