"""Evidence facet vocabulary — validated against this set everywhere."""

from __future__ import annotations

EVIDENCE_FACETS: frozenset[str] = frozenset(
    {
        # core news + sector
        "entity_state_over_time",
        "news_drivers",
        "benchmark",
        "forward_view",
        "market_overview",
        # fund exposure and per-fund data
        "exposure_link",
        "fund_composition",
        "return_series",
        "fund_facts_nav",
        "fund_facts_holdings",
        "peer_rank",
        # added from the legacy tool set
        "sector_impact_direction",  # which sectors the news helps / hurts (LLM picker over article bodies)
        "relationship_trace",  # direct holding/sector weight vs indirect news co-occurrence
        "macro_driver_map",  # rule-based macro driver -> sector winners/losers
        "fund_vs_index",  # fund holdings return vs sector index
        "holding_drivers",  # news explaining a specific stock's move
        "stock_holders",  # funds that hold a stock
        "peer_compare",  # side-by-side comparison of named funds
        "commodity_spot",  # gold / silver spot
        "stock_price",  # price snapshot for one stock
        "sector_holdings",  # representative companies in a sector
        "fund_screen",  # catalog screen by category / AMC / stock / performance
        "fund_attribution",  # holding weight times stock return, computed in code
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

FACET_ALIASES: dict[str, str] = {
    "fund_facts_holdings": "fund_composition",
    "fund_holdings": "fund_composition",
    "fund_facts_nav": "return_series",
}


def canonical_facet(facet: str) -> str:
    key = str(facet).strip()
    return FACET_ALIASES.get(key, key)


def validate_facets(facets: list[str]) -> list[str]:
    out: list[str] = []
    for f in facets or []:
        key = str(f).strip()
        canon = canonical_facet(key)
        if (key in EVIDENCE_FACETS or canon in EVIDENCE_FACETS) and key not in out:
            out.append(key)
    return out

