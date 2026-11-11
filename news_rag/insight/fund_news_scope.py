"""Infer which news layers (holdings / sectors / macro) the user wants for a fund ask."""

from __future__ import annotations

import re

_LAYER_HOLDINGS = "holdings"
_LAYER_SECTORS = "sectors"
_LAYER_MACRO = "macro"
_ALL = frozenset({_LAYER_HOLDINGS, _LAYER_SECTORS, _LAYER_MACRO})


def infer_fund_news_layers(question: str) -> frozenset[str]:
    """Return subset of holdings, sectors, macro; all three when unspecified."""
    q = (question or "").strip()
    if not q:
        return _ALL

    want_holdings = bool(
        re.search(
            r"\b(?:holdings?|stocks?|shares?|constituents?|top\s+\d+\s+stocks?)\b",
            q,
            re.I,
        )
    )
    want_sectors = bool(
        re.search(
            r"\b(?:sector|sectors|industry|industries|thematic)\b",
            q,
            re.I,
        )
    )
    want_macro = bool(
        re.search(
            r"\b(?:macro|market\s+level|market-level|market\b|rates?|rbi|inflation|"
            r"crude|oil|rupee|bond|yield|economy|geopolit|nifty|sensex)\b",
            q,
            re.I,
        )
    )

    # Explicit narrow asks: only what they named.
    if want_holdings and not want_sectors and not want_macro:
        return frozenset({_LAYER_HOLDINGS})
    if want_sectors and not want_holdings and not want_macro:
        return frozenset({_LAYER_SECTORS})
    if want_macro and not want_holdings and not want_sectors:
        return frozenset({_LAYER_MACRO})

    picked = set()
    if want_holdings:
        picked.add(_LAYER_HOLDINGS)
    if want_sectors:
        picked.add(_LAYER_SECTORS)
    if want_macro:
        picked.add(_LAYER_MACRO)
    if picked:
        return frozenset(picked)

    # A fund overview is holdings and sectors. Macro only when the question names it.
    if re.search(r"\btell me about\b|\boverview of\b|\bhow is\b", q, re.I):
        return frozenset({_LAYER_HOLDINGS, _LAYER_SECTORS})
    return _ALL


def layers_to_retrieval_keys(layers: frozenset[str]) -> frozenset[str]:
    """Map UI/API layer names to retrieve_layered_fund_news internal keys."""
    out: set[str] = set()
    if _LAYER_HOLDINGS in layers:
        out.add("holding")
    if _LAYER_SECTORS in layers:
        out.add("sector")
    if _LAYER_MACRO in layers:
        out.add("macro")
    return frozenset(out or {"holding", "sector", "macro"})
