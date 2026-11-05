"""Deterministic entity candidates (funds, sectors, own holdings) handed to the planner.

The planner still decides; code only offers catalog-checked names so a typo or short form
does not become an invented entity.
"""

from __future__ import annotations

import difflib
import re
from typing import Any

_MIN_ALIAS_LEN = 3  # "it" and similar two-letter aliases are too ambiguous to match on their own


def _sector_candidates(question: str) -> list[str]:
    from news_rag.sector_aliases import SECTOR_ALIAS_MAP

    q = (question or "").lower()
    words = re.findall(r"[a-z&]+", q)
    found: list[str] = []
    for alias in sorted(SECTOR_ALIAS_MAP, key=len, reverse=True):
        if len(alias) < _MIN_ALIAS_LEN:
            continue
        hit = re.search(rf"\b{re.escape(alias.lower())}\b", q) is not None
        if not hit and len(alias) >= 5 and " " not in alias:
            hit = bool(difflib.get_close_matches(alias.lower(), words, n=1, cutoff=0.86))
        if hit:
            for key in SECTOR_ALIAS_MAP[alias]:
                if key not in found:
                    found.append(key)
    return found[:4]


def _holding_candidates(question: str, memory: dict[str, Any] | None) -> list[str]:
    rows = (memory or {}).get("holdings_in_chat") or []
    q_words = set(re.findall(r"[a-z0-9]+", (question or "").lower()))
    out: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("scheme_name") or row.get("fund_name") or "").strip()
        if not name:
            continue
        tokens = {t for t in re.findall(r"[a-z0-9]+", name.lower()) if len(t) > 2 and t not in {"fund", "plan", "growth", "direct", "regular"}}
        category = str(row.get("category") or "").lower()
        cat_hit = bool(category) and all(w in q_words for w in re.findall(r"[a-z]+", category) if len(w) > 2)
        if len(tokens & q_words) >= 2 or (cat_hit and "my" in q_words):
            out.append(name)
    return out[:5]


def entity_candidates(question: str, memory: dict[str, Any] | None = None) -> dict[str, Any]:
    """{"funds", "sectors", "holdings", "amc_notes"} — planner still decides."""
    funds: list[dict[str, str]] = []
    amc_notes: list[str] = []
    try:
        from news_rag.fund_search import _amc_hints_from_tokens, resolve_fund_for_query

        detail, ambiguous, close = resolve_fund_for_query(question)
        if detail:
            funds.append(
                {
                    "name": str(detail.get("fund_name") or detail.get("fund_short_name") or "").strip(),
                    "isin": str(detail.get("isin") or "").strip(),
                    "match": "ambiguous" if ambiguous else "likely",
                }
            )
        elif ambiguous and close:
            funds.extend({"name": str(n), "isin": "", "match": "ambiguous"} for n in close[:4])
        q_tokens = re.findall(r"[a-z0-9]+", (question or "").lower())
        hints = _amc_hints_from_tokens([t for t in q_tokens if len(t) >= 2])
        if hints:
            from news_rag.fund_catalog import amc_planner_lines

            amc_notes = amc_planner_lines(hints)
    except Exception:  # noqa: BLE001
        pass
    try:
        sectors = _sector_candidates(question)
    except Exception:  # noqa: BLE001
        sectors = []
    return {
        "funds": [f for f in funds if f["name"]],
        "sectors": sectors,
        "holdings": _holding_candidates(question, memory),
        "amc_notes": amc_notes,
    }


def candidates_block(question: str, memory: dict[str, Any] | None = None) -> str:
    """Text for the planner message. Empty when there is nothing to offer."""
    got = entity_candidates(question, memory)
    lines: list[str] = []
    for f in got["funds"]:
        lines.append(f"- fund ({f['match']}): {f['name']}" + (f" [{f['isin']}]" if f["isin"] else ""))
    if got["sectors"]:
        lines.append("- sector: " + ", ".join(got["sectors"]))
    for name in got["holdings"]:
        lines.append(f"- user's own holding: {name}")
    for note in got.get("amc_notes") or []:
        lines.append(note)
    if not lines:
        return ""
    return (
        "CANDIDATES (catalog-checked names for typos and short forms; pick or correct them, never invent others):\n"
        + "\n".join(lines)
    )
