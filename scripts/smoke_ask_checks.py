#!/usr/bin/env python3
"""Quick HTTP smoke against /api/ask using cases_v2 (subset)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_rag.eval.v2_scoring import load_cases_v2, score_case

BASE = "http://127.0.0.1:8080"


def main() -> int:
    cases = load_cases_v2()[:5]
    failures = 0
    for case in cases:
        q = case.get("question") or ""
        r = httpx.post(f"{BASE}/api/ask", json={"question": q}, timeout=600.0)
        r.raise_for_status()
        body = r.json()
        sc = score_case(body, case)
        if not sc["passed"]:
            failures += 1
            print(case.get("id"), sc["failures"])
    print(json.dumps({"checked": len(cases), "failures": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
