"""Market-wide and topic-focused news targets for layer-2 fan-out.

Broad questions use the same eight parallel semantic queries as market_pulse.
Focused questions (crude, RBI, FII flows, etc.) use one target per named topic.
"""

from __future__ import annotations

from news_rag.market_pulse import MACRO_QUERY_SPECS, _PULSE_THEME_LABELS

MARKET_PULSE_THEME_COUNT = len(MACRO_QUERY_SPECS)


def market_query_for_topic(topic: str) -> str:
    """Turn a user or planner topic into a retrieval query."""
    t = (topic or "").strip().lower()
    if not t:
        return "India stock market nifty sensex macro news"
    if "crude" in t or "oil" in t or "brent" in t:
        return "crude oil rupee inflation India bond yields macro markets"
    if "rbi" in t or "repo" in t or "liquidity" in t or "mpc" in t:
        return "RBI repo rate rupee liquidity India financial markets"
    if "fii" in t or "dii" in t or "foreign investor" in t or "flow" in t:
        return "FII DII flows India stock market foreign investors"
    if "bank" in t or "nifty bank" in t or "credit" in t:
        return "Nifty Bank index India banking credit lenders asset quality"
    if "earn" in t or "result" in t or "guidance" in t:
        return "India earnings results corporate guidance stock market"
    if "geopolit" in t or "global" in t or "war" in t or "tariff" in t:
        return "global risk geopolitics impact India equity markets"
    if "nifty" in t or "sensex" in t or "equity" in t:
        return "Nifty 50 Sensex India equity markets today drivers"
    if "rupee" in t or "inr" in t or "dollar" in t:
        return "rupee dollar India forex markets RBI impact"
    if "inflation" in t or "cpi" in t or "wpi" in t:
        return "inflation India RBI rates markets impact"
    return f"{topic.strip()} India stock market macro news impact"


def pulse_theme_entities(limit: int) -> list[tuple[str, str]]:
    """(display label, semantic query) for parallel market pulse retrieval."""
    n = max(1, min(int(limit or MARKET_PULSE_THEME_COUNT), MARKET_PULSE_THEME_COUNT))
    out: list[tuple[str, str]] = []
    for semantic, theme_key in MACRO_QUERY_SPECS[:n]:
        label = _PULSE_THEME_LABELS.get(theme_key) or theme_key.replace("_", " ").title()
        out.append((label, semantic))
    return out


def market_scope_entities(
    *,
    source_kind: str,
    topics: list[str],
    top_n: int,
) -> list[tuple[str, str]]:
    """Build entity/query pairs for scope=market."""
    if source_kind == "list" and topics:
        pairs: list[tuple[str, str]] = []
        for topic in topics[: max(1, min(top_n, 8))]:
            pairs.append((topic, market_query_for_topic(topic)))
        return pairs
    return pulse_theme_entities(top_n)
