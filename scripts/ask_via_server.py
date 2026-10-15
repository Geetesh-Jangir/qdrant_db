#!/usr/bin/env python3
"""POST a question to the running API (warm models) and print answer + per-node timings.

  python scripts/ask_via_server.py "why did parag parikh flexi cap fall this month"
"""

from __future__ import annotations

import json
import sys
import time

import httpx


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: ask_via_server.py <question> [base_url]")
        return 2
    question = sys.argv[1]
    base = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8080"
    started = time.perf_counter()
    resp = httpx.post(f"{base}/api/ask", json={"question": question}, timeout=300)
    wall = time.perf_counter() - started
    resp.raise_for_status()
    data = resp.json()
    research = data.get("research") or {}
    print(data.get("insight"))
    print("-" * 70)
    print("plan:", json.dumps(research.get("plan"), ensure_ascii=False))
    for node in research.get("nodes") or []:
        print(f"  node={node['node']:<8} {node['seconds']:>7}s next={node['next']} why={node['why']}")
    print(f"wall={wall:.1f}s source={data.get('insight_source')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
