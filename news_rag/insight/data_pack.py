"""Turn raw tool output into the compact DATA the answer writer sees.

Numbers are already computed by the tools (or by code, such as holding attribution). The writer is
told to copy them and never to calculate. Identifiers and plumbing fields are removed so the model
has nothing internal to talk about.
"""

from __future__ import annotations

import json
from typing import Any

from news_rag.insight.gather import EvidenceSet

# Plumbing the writer must never see.
_DROP_KEYS = frozenset(
    {
        "isin", "url", "urls", "link", "source", "sources", "provider", "elapsed_ms", "articles",
        "snippet", "scraped_text", "raw", "cache", "fetched_at", "_point_id", "news_url",
        "news_date", "published_at", "date", "ok", "error", "tool", "layer", "query",
        "semantic_query", "entity_key", "entity_names", "doc_id", "id",
    }
)

FACET_LABELS: dict[str, str] = {
    "fund_facts_nav": "nav_and_returns",
    "return_series": "return_history",
    "fund_composition": "holdings_and_sectors",
    "fund_facts_holdings": "holdings_and_sectors",
    "fund_vs_index": "holdings_vs_sector_indexes",
    "peer_compare": "side_by_side_comparison",
    "fund_attribution": "what_moved_the_fund",
    "stock_price": "stock_price",
    "stock_holders": "funds_holding_the_stock",
    "commodity_spot": "gold_and_silver",
    "market_overview": "market_themes",
    "benchmark": "index_return",
    "exposure_link": "funds_by_exposure",
    "fund_screen": "screened_funds",
    "peer_rank": "ranked_funds",
    "sector_impact_direction": "sectors_helped_or_hurt",
    "macro_driver_map": "usual_sector_effects",
    "relationship_trace": "direct_vs_indirect_links",
    "sector_holdings": "companies_in_sector",
    "news_drivers": "news_context",
    "holding_drivers": "news_on_holdings",
    "entity_state_over_time": "recent_trend",
    "forward_view": "outlook_signals",
}

MAX_PACK_CHARS = 16000


def _compact(value: Any, *, depth: int, max_items: int, max_str: int) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, (int,)):
        return value
    if isinstance(value, str):
        text = " ".join(value.split())
        return text if len(text) <= max_str else text[: max_str - 1].rstrip() + "…"
    if depth <= 0:
        return None
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, val in value.items():
            k = str(key)
            if k in _DROP_KEYS or k.startswith("_") or k.endswith("_url"):
                continue
            cleaned = _compact(val, depth=depth - 1, max_items=max_items, max_str=max_str)
            if cleaned in (None, "", [], {}):
                continue
            out[k] = cleaned
        return out
    if isinstance(value, (list, tuple)):
        rows = [_compact(v, depth=depth - 1, max_items=max_items, max_str=max_str) for v in value[:max_items]]
        return [r for r in rows if r not in (None, "", [], {})]
    return str(value)[:max_str]


def build_data_pack(evidence: EvidenceSet, *, max_chars: int = MAX_PACK_CHARS) -> dict[str, Any]:
    """Group evidence by fund (when the item is about one fund) or by topic."""
    isin_to_name: dict[str, str] = {}
    for item in evidence.items:
        data = item.data if isinstance(item.data, dict) else {}
        isin = str(data.get("isin") or item.entity_key or "").upper()
        name = str(data.get("fund_name") or data.get("scheme_name") or "").strip()
        if isin and name:
            isin_to_name.setdefault(isin, name)

    def build(max_items: int, max_str: int) -> dict[str, Any]:
        funds: dict[str, dict[str, Any]] = {}
        topics: dict[str, Any] = {}
        for item in evidence.items:
            data = item.data if isinstance(item.data, dict) else {}
            label = FACET_LABELS.get(item.facet, item.facet)
            if item.facet == "fund_attribution":
                for row in data.get("funds") or []:
                    if not isinstance(row, dict):
                        continue
                    isin = str(row.get("isin") or "").upper()
                    fund = isin_to_name.get(isin) or str(row.get("fund_name") or "fund")
                    funds.setdefault(fund, {})[label] = _compact(
                        row, depth=6, max_items=max_items, max_str=max_str
                    )
                continue
            isin = str(data.get("isin") or item.entity_key or "").upper()
            fund = isin_to_name.get(isin)
            body = _compact(data, depth=5, max_items=max_items, max_str=max_str)
            if body in (None, "", [], {}):
                continue
            if fund:
                funds.setdefault(fund, {})[label] = body
            else:
                existing = topics.get(label)
                if existing is None:
                    topics[label] = body
                elif isinstance(existing, list):
                    existing.append(body)
                else:
                    topics[label] = [existing, body]
        pack: dict[str, Any] = {}
        if funds:
            pack["funds"] = funds
        pack.update(topics)
        return pack

    for max_items, max_str in ((12, 260), (8, 200), (5, 140), (3, 100)):
        pack = build(max_items, max_str)
        if len(json.dumps(pack, ensure_ascii=False, separators=(",", ":"))) <= max_chars:
            return pack
    return pack


def missing_items(evidence: EvidenceSet) -> list[str]:
    out: list[str] = []
    for entry in evidence.ledger:
        if entry.status == "satisfied" or entry.implied:
            continue
        out.append(FACET_LABELS.get(entry.facet, entry.facet).replace("_", " "))
    return list(dict.fromkeys(out))


def select_news(
    evidence: EvidenceSet,
    brief: Any,
    *,
    depth: str,
    question: str,
    detailed_chars: int,
) -> list[dict[str, Any]]:
    """Articles the writer may read. Depth none passes nothing."""
    if depth == "none" or not evidence.articles:
        return []
    from news_rag.insight.news_reader import _body, select_articles

    limit, chars = (4, 380) if depth == "headlines" else (6, detailed_chars)
    arts = select_articles(evidence.articles, limit=limit, brief=brief, evidence=evidence, question=question)
    rows: list[dict[str, Any]] = []
    for art in arts:
        body = _body(art, chars)
        title = str(art.get("title") or "").strip()
        if not (title or body):
            continue
        row: dict[str, Any] = {"headline": title, "text": body}
        if art.get("direction") in ("positive", "negative"):
            row["tone"] = art["direction"]
        row["_article"] = art  # stripped before serialising
        rows.append(row)
    return rows
