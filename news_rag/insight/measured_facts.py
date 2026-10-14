"""Numbers gathered before / during insight — news LLM must reconcile with these."""

from __future__ import annotations

from typing import Any

from news_rag.insight.brief import QuestionBrief
from news_rag.insight.gather import EvidenceSet


def measured_facts_block(brief: QuestionBrief, evidence: EvidenceSet | None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "window": brief.window_label,
        "window_days": brief.window_days,
        "funds": [],
    }
    if not evidence:
        return out
    by_isin: dict[str, dict[str, Any]] = {}

    def _merge(isin: str, patch: dict[str, Any]) -> None:
        key = (isin or "").upper()
        if not key:
            return
        by_isin.setdefault(key, {"isin": key})
        by_isin[key].update({k: v for k, v in patch.items() if v is not None})

    for item in evidence.items:
        d = item.data if isinstance(item.data, dict) else {}
        isin = str(d.get("isin") or item.entity_key or "").upper()
        if item.facet == "fund_facts_nav":
            _merge(isin, {
                "fund_name": d.get("fund_name"),
                "nav": d.get("nav"),
                "nav_date": d.get("nav_date"),
                "benchmark_name": d.get("benchmark"),
            })
        elif item.facet == "return_series":
            _merge(isin, {
                "return_window_pct": d.get("window_pct"),
                "monthly": d.get("monthly"),
            })
        elif item.facet in ("fund_composition", "fund_facts_holdings"):
            _merge(isin, {
                "fund_name": d.get("fund_name"),
                "top_sectors": [
                    {"sector": s.get("sector"), "pct": s.get("percentage")}
                    for s in (d.get("sectors") or [])[:8]
                    if isinstance(s, dict)
                ],
                "top_holdings": [
                    {"name": h.get("name"), "pct": h.get("percentage")}
                    for h in (d.get("holdings") or [])[:10]
                    if isinstance(h, dict)
                ],
            })
        elif item.facet == "fund_attribution":
            out["holding_attribution"] = d
            for row in d.get("funds") or []:
                if not isinstance(row, dict):
                    continue
                rid = str(row.get("isin") or "").upper()
                _merge(rid, {
                    "fund_return_pct": row.get("fund_return_pct"),
                    "holding_attribution": row.get("attribution"),
                    "return_notes": row.get("return_notes"),
                })

    out["funds"] = list(by_isin.values())
    return out
