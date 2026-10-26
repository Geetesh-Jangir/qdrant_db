"""Layered news retrieval for named-fund insights: holdings, sectors, then macro."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _fetch_holding_news(
    row: dict[str, Any],
    *,
    question: str,
    window_days: int,
) -> tuple[str, list[dict]]:
    name = str(row.get("name") or row.get("company_name") or "").strip()
    if not name:
        return name, []
    entity = resolve_corpus_entity(name)
    scope = ScopeRefinement(news_entities=[entity], news_topics=[], search_mode="entities_only")
    hits = retrieve_scoped_news(
        f"{entity} India stock news results earnings",
        scope=scope,
        question=question,
        window_days=window_days,
        query_log=None,
    )
    if not hits:
        scope = ScopeRefinement(search_mode="event_only", news_topics=[])
        hits = retrieve_scoped_news(
            f"{entity} India company news stock",
            scope=scope,
            question=question,
            window_days=window_days,
            query_log=None,
        )
    return name, hits[:3]


def _fetch_sector_news(
    row: dict[str, Any],
    *,
    question: str,
    window_days: int,
) -> tuple[str, list[dict]]:
    sector_label = str(row.get("sector") or "").strip()
    if not sector_label:
        return sector_label, []
    entities = resolve_corpus_entities(_sector_entities(sector_label))
    scope = ScopeRefinement(news_entities=entities, news_topics=[], search_mode="event_plus_entities")
    hits = retrieve_scoped_news(
        f"{sector_label} India sector news",
        scope=scope,
        question=question,
        window_days=window_days,
        query_log=None,
    )
    return sector_label, hits[:3]


def _fetch_macro_news(
    query: str,
    label: str,
    *,
    question: str,
    fund_name: str,
    window_days: int,
) -> tuple[str, list[dict]]:
    scope = ScopeRefinement(search_mode="event_only", news_topics=[])
    hits = retrieve_scoped_news(
        query,
        scope=scope,
        question=question or fund_name,
        window_days=min(window_days, 21),
        query_log=None,
    )
    return label, hits[:3]


def retrieve_layered_fund_news(
    *,
    holdings: list[dict[str, Any]],
    sectors: list[dict[str, Any]],
    question: str,
    fund_name: str = "",
    window_days: int = 30,
    query_log: QueryLogger | None = None,
    layers: frozenset[str] | None = None,
) -> list[dict]:
    """Holdings, sector, and macro news fetched in parallel, then merged and ranked."""
    active = layers or frozenset({"holding", "sector", "macro"})
    pool: dict[str, dict] = {}
    fund_bit = (fund_name or "").strip()

    jobs: list[tuple[str, Any]] = []
    if "holding" in active:
        for row in holdings[:6]:
            jobs.append(("holding", row))
    if "sector" in active:
        for row in sectors[:5]:
            jobs.append(("sector", row))
    if "macro" in active:
        for query, label in _macro_queries_for_sectors(sectors):
            jobs.append(("macro", (query, label)))

    if not jobs:
        return []

    max_workers = min(8, max(2, len(jobs)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool_exec:
        future_map = {}
        for kind, payload in jobs:
            if kind == "holding":
                fut = pool_exec.submit(
                    _fetch_holding_news,
                    payload,
                    question=question,
                    window_days=window_days,
                )
            elif kind == "sector":
                fut = pool_exec.submit(
                    _fetch_sector_news,
                    payload,
                    question=question,
                    window_days=window_days,
                )
            else:
                query, label = payload
                fut = pool_exec.submit(
                    _fetch_macro_news,
                    query,
                    label,
                    question=question,
                    fund_name=fund_bit,
                    window_days=window_days,
                )
            future_map[fut] = kind

        for fut in as_completed(future_map):
            kind = future_map[fut]
            try:
                label, hits = fut.result()
            except Exception:
                continue
            if not label or not hits:
                continue
            _merge_articles(pool, hits, layer=kind, source_label=label)

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
            f"macro={sum(1 for a in ranked if a.get(_LAYER)=='macro')} "
            f"layers={','.join(sorted(active))}"
        )
    return ranked[:24]
