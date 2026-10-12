"""Per-stage scoring for insight pipeline v2 eval cases."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_CASES_PATH = Path(__file__).resolve().parent / "cases_v2.json"


def load_cases_v2() -> list[dict[str, Any]]:
    if not _CASES_PATH.is_file():
        return []
    return json.loads(_CASES_PATH.read_text(encoding="utf-8"))


def _blob(response: dict[str, Any]) -> str:
    parts = [
        str(response.get("insight") or ""),
        str(response.get("insight_headline") or ""),
        str(response.get("insight_narrative") or ""),
    ]
    parts.extend(str(b) for b in (response.get("insight_bullets") or []))
    return "\n".join(parts).lower()


def score_brief(brief_dict: dict[str, Any], expect: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not brief_dict:
        return ["brief:missing"]
    needs = set(brief_dict.get("evidence_needs") or [])
    for facet in expect.get("brief_facets") or []:
        if facet not in needs:
            failures.append(f"brief:missing_facet:{facet}")
    min_sub = int(expect.get("min_sub_asks") or 0)
    sub = brief_dict.get("sub_asks") or []
    if len(sub) < min_sub:
        failures.append(f"brief:sub_asks<{min_sub}")
    min_window = int(expect.get("min_window_days") or 0)
    if min_window and int(brief_dict.get("window_days") or 0) < min_window:
        failures.append(f"brief:window_days<{min_window}")
    return failures


def score_ledger(ledger: list[dict[str, Any]], expect: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    by_facet = {str(e.get("facet")): str(e.get("status")) for e in ledger if isinstance(e, dict)}
    for facet in expect.get("ledger_satisfied") or []:
        if by_facet.get(facet) != "satisfied":
            failures.append(f"ledger:{facet}!={by_facet.get(facet)}")
    return failures


def score_findings(findings: dict[str, Any], expect: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    funds = findings.get("funds") or []
    min_funds = int(expect.get("min_funds") or 0)
    if len(funds) < min_funds:
        failures.append(f"findings:funds<{min_funds}")
    if expect.get("require_other_sectors"):
        if funds and not any((f.get("other_top_sectors") or []) for f in funds):
            failures.append("findings:other_sectors_missing")
    if expect.get("require_verdict"):
        if funds and not any(f.get("verdict") not in (None, "", "unknown") for f in funds):
            failures.append("findings:verdict_missing")
    return failures


def score_answer(response: dict[str, Any], expect: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    text = _blob(response)
    for token in expect.get("must_contain") or []:
        if token.lower() not in text:
            failures.append(f"answer:must_contain:{token}")
    for token in expect.get("must_not_contain") or []:
        if token.lower() in text:
            failures.append(f"answer:must_not_contain:{token}")
    if expect.get("require_direction_words"):
        if not re.search(r"\b(positive|negative|mixed|up|down)\b", text):
            failures.append("answer:direction_words_missing")
    return failures


def score_case(response: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    expect = case.get("expect") or {}
    research = response.get("research") or {}
    brief = {
        "evidence_needs": research.get("evidence_needs"),
        "sub_asks": response.get("sub_queries"),
        "window_days": (response.get("retrieval_window") or {}).get("window_days"),
    }
    failures: list[str] = []
    failures.extend(score_brief(brief, expect))
    failures.extend(score_ledger(research.get("ledger") or [], expect))
    failures.extend(score_findings(research.get("findings") or {}, expect))
    failures.extend(score_answer(response, expect))
    return {
        "id": case.get("id"),
        "passed": len(failures) == 0,
        "failures": failures,
    }
