"""Layered news retrieval for named-fund insights: holdings, sectors, then macro."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from news_rag.news_entity_resolve import resolve_corpus_entity, resolve_corpus_entities
from news_rag.parse import SECTOR_EXPANSIONS
from news_rag.query_plan import ScopeRefinement
from news_rag.scoped_retrieve import retrieve_scoped_news

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

_LAYER = "_news_layer"
_SOURCE = "_news_source_label"


def _merge_articles(
    pool: dict[str, dict],
    rows: list[dict],
    *,
    layer: str,
    source_label: str,
) -> None:
    for row in rows:
        url = str(row.get("url") or "").strip()
        key = url or str(row.get("title") or "")
        if not key:
            continue
        item = {**row, _LAYER: layer, _SOURCE: source_label}
        prev = pool.get(key)
        if prev is None or _layer_rank(layer) < _layer_rank(str(prev.get(_LAYER) or "")):
            pool[key] = item


def _layer_rank(layer: str) -> int:
    return {"holding": 0, "sector": 1, "macro": 2}.get(layer, 3)


def _sector_entities(sector_label: str) -> list[str]:
    label = (sector_label or "").strip()
    if not label:
        return []
    expanded = SECTOR_EXPANSIONS.get(label)
    if expanded:
        return [str(x) for x in expanded[:4]]
    return [label]


def _macro_queries_for_sectors(sectors: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Return (semantic_query, short_label) for macro passes."""
    labels = " ".join(str(s.get("sector") or "") for s in sectors[:6]).lower()
    out: list[tuple[str, str]] = []
    if "bank" in labels or "finance" in labels:
        out.append(
            (
                "RBI repo rate banking credit liquidity FCNR India lenders",
                "Banking & rates",
            )
        )
    if "pharma" in labels or "health" in labels or "biotech" in labels:
        out.append(
            (
                "India pharma USFDA inspections drug pricing healthcare sector",
                "Pharma & healthcare",
            )
        )
    if "software" in labels or "it " in labels or labels.startswith("it "):
        out.append(
            (
                "India IT sector software exports US clients tech spending",
                "IT sector",
            )
        )
    if "consumer" in labels or "fmcg" in labels or "retail" in labels:
        out.append(
            (
                "India consumer demand festive season retail FMCG volumes",
                "Consumer demand",
            )
        )
    if "telecom" in labels or "airtel" in labels:
        out.append(
            (
                "India telecom tariff ARPU Bharti Airtel sector",
                "Telecom",
            )
        )
    out.append(
        (
            "India crude oil rupee RBI inflation bond yields macro markets",
            "Macro backdrop",
        )
    )
    seen: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for q, label in out:
        if q in seen:
            continue
        seen.add(q)
        deduped.append((q, label))
    return deduped[:4]


def retrieve_layered_fund_news(
    *,
    holdings: list[dict[str, Any]],
    sectors: list[dict[str, Any]],
    question: str,
    fund_name: str = "",
    window_days: int = 30,
    query_log: QueryLogger | None = None,
) -> list[dict]:
    """Holdings-first, then sector peers, then macro — merged and ranked."""
    pool: dict[str, dict] = {}
    fund_bit = (fund_name or "").strip()

    for row in holdings[:6]:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        entity = resolve_corpus_entity(name)
        scope = ScopeRefinement(news_entities=[entity], news_topics=[], search_mode="entities_only")
        hits = retrieve_scoped_news(
            f"{entity} India stock news results earnings",
            scope=scope,
            question=question,
            window_days=window_days,
            query_log=query_log,
        )
        if not hits:
            scope = ScopeRefinement(search_mode="event_only", news_topics=[])
            hits = retrieve_scoped_news(
                f"{entity} India company news stock",
                scope=scope,
                question=question,
                window_days=window_days,
                query_log=query_log,
            )
        _merge_articles(pool, hits[:3], layer="holding", source_label=name)

    for row in sectors[:5]:
        sector_label = str(row.get("sector") or "").strip()
        if not sector_label:
            continue
        entities = resolve_corpus_entities(_sector_entities(sector_label))
        scope = ScopeRefinement(news_entities=entities, news_topics=[], search_mode="event_plus_entities")
        hits = retrieve_scoped_news(
            f"{sector_label} India sector news",
            scope=scope,
            question=question,
            window_days=window_days,
            query_log=query_log,
        )
        _merge_articles(pool, hits[:3], layer="sector", source_label=sector_label)

    for query, label in _macro_queries_for_sectors(sectors):
        scope = ScopeRefinement(search_mode="event_only", news_topics=[])
        hits = retrieve_scoped_news(
            query,
            scope=scope,
            question=question or fund_bit,
            window_days=min(window_days, 21),
            query_log=query_log,
        )
        _merge_articles(pool, hits[:3], layer="macro", source_label=label)

    ranked = sorted(
        pool.values(),
        key=lambda a: (
            _layer_rank(str(a.get(_LAYER) or "")),
            -int(a.get("max_impact") or 0),
            -float(a.get("_rrf_score") or 0),
        ),
    )
    if query_log is not None:
        query_log.write(
            f"FUND_PORTFOLIO_NEWS total={len(ranked)} "
            f"holding={sum(1 for a in ranked if a.get(_LAYER)=='holding')} "
            f"sector={sum(1 for a in ranked if a.get(_LAYER)=='sector')} "
            f"macro={sum(1 for a in ranked if a.get(_LAYER)=='macro')}"
        )
    return ranked[:24]
