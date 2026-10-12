#!/usr/bin/env python3
"""Audit insight v2 pipeline stages and tool registry (local, no HTTP required)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

DEFAULT_Q = (
    "How is the automobile sector doing? "
    "Which funds are highly impacted positively or negatively?"
)


def _status_icon(ok: bool) -> str:
    return "ok" if ok else "FAIL"


def audit_registry() -> dict:
    from news_rag.insight.registry import (
        FACET_TOOL_PREFERENCE,
        all_tools,
        ensure_registry,
        pick_tool_for_facet,
    )

    ensure_registry()
    tools = all_tools()
    missing_desc = [t.name for t in tools if not (t.description or "").strip()]
    facet_map = {f: (pick_tool_for_facet(f).name if pick_tool_for_facet(f) else None) for f in FACET_TOOL_PREFERENCE}
    return {
        "tool_count": len(tools),
        "tools_missing_description": missing_desc,
        "facet_tool_pick": facet_map,
        "registry_ok": len(missing_desc) == 0 and all(facet_map.values()),
    }


def audit_stages(question: str, *, fan_out: int = 5, max_rounds: int = 3) -> dict:
    from news_rag.insight.brief import build_question_brief, _heuristic_brief
    from news_rag.insight.gather import GatherContext, gather_evidence
    from news_rag.insight.blocks.compute import compute_findings
    from news_rag.insight.interpret import compose_from_findings
    from news_rag.insight.verify import verify_answer
    from news_rag.config import get_settings
    from news_rag.llm_client import llm_api_key_configured

    settings = get_settings()
    brief = build_question_brief(question) if llm_api_key_configured(settings) else _heuristic_brief(question)
    gctx = GatherContext(question=question, brief=brief, fan_out_cap=fan_out)
    evidence = gather_evidence(gctx, max_rounds=max_rounds)
    findings = compute_findings(brief, evidence)
    composed = compose_from_findings(question, brief, findings, evidence)
    verify = verify_answer(brief, findings, evidence, insight_text=composed.display)

    ledger = [
        {
            "facet": e.facet,
            "status": e.status,
            "tool": e.tool,
            "reason": (e.reason or "")[:120],
        }
        for e in evidence.ledger
    ]
    return {
        "brief": {
            "source": brief.raw.get("source", "llm"),
            "evidence_needs": brief.evidence_needs,
            "sub_asks": [{"kind": a.kind, "text": a.text[:80]} for a in brief.sub_asks],
            "sector": brief.primary_sector(),
            "window": brief.window_label,
        },
        "gather": {
            "ledger": ledger,
            "articles": len(evidence.articles),
            "tool_runs": len(evidence.tool_runs),
            "all_facets_satisfied": all(e.status == "satisfied" for e in evidence.ledger),
        },
        "compute": {
            "funds": len(findings.funds),
            "news_insights": len(findings.sector.news_insights) if findings.sector else 0,
            "index_return_pct": findings.sector.index_return_pct if findings.sector else None,
            "news_direction": findings.sector.news_direction if findings.sector else None,
        },
        "interpret": {"display_chars": len(composed.display or ""), "bullets": len(composed.bullets)},
        "verify": {"passed": verify.passed, "gaps": verify.gaps[:8]},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit insight v2 pipeline")
    parser.add_argument("--question", "-q", default=DEFAULT_Q)
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    args = parser.parse_args()

    reg = audit_registry()
    stages = audit_stages(args.question)

    if args.json:
        print(json.dumps({"registry": reg, "stages": stages}, indent=2))
        return 0

    print("=== Registry ===")
    print(f"tools: {reg['tool_count']}, missing descriptions: {reg['tools_missing_description'] or 'none'}")
    for facet, tool in reg["facet_tool_pick"].items():
        print(f"  {facet} -> {tool}")

    print("\n=== Brief ===")
    for k, v in stages["brief"].items():
        print(f"  {k}: {v}")

    print("\n=== Gather (ledger) ===")
    for row in stages["gather"]["ledger"]:
        mark = _status_icon(row["status"] == "satisfied")
        print(f"  [{mark}] {row['facet']}: {row['status']} via {row['tool'] or '-'} {row['reason']!r}")

    print("\n=== Compute / interpret / verify ===")
    print(f"  articles: {stages['gather']['articles']}")
    print(f"  compute: {stages['compute']}")
    print(f"  interpret: {stages['interpret']}")
    print(f"  verify passed: {stages['verify']['passed']}")
    if stages["verify"]["gaps"]:
        print(f"  gaps: {stages['verify']['gaps']}")

    ok = (
        reg["tool_count"] >= 8
        and not reg["tools_missing_description"]
        and stages["gather"]["articles"] > 0
        and stages["compute"]["funds"] > 0
    )
    print(f"\nOverall: {'PASS' if ok else 'NEEDS ATTENTION'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
