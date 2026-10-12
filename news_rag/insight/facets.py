"""Evidence facet vocabulary — validated against this set everywhere."""

from __future__ import annotations

EVIDENCE_FACETS: frozenset[str] = frozenset(
    {
        "entity_state_over_time",
        "news_drivers",
        "exposure_link",
        "fund_composition",
        "return_series",
        "benchmark",
        "forward_view",
        "fund_facts_nav",
        "fund_facts_holdings",
        "market_overview",
        "peer_rank",
    }
)

SUB_ASK_KINDS: frozenset[str] = frozenset(
    {
        "describe",
        "measure",
        "compare",
        "explain_cause",
        "predict",
        "list",
    }
)

def validate_facets(facets: list[str]) -> list[str]:
    out: list[str] = []
    for f in facets or []:
        key = str(f).strip()
        if key in EVIDENCE_FACETS and key not in out:
            out.append(key)
    return out
