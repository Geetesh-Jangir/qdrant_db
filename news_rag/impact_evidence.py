"""Event news retrieval and sector channel extraction for impact queries."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from news_rag.config import get_settings
from news_rag.entity_index import corpus_entity_names
from news_rag.impact_gating import infer_direction_filter
from news_rag.qdrant_reader import QdrantReader, build_filter
from news_rag.query_router import RouterResult
from news_rag.sector_fund_ranking import get_sector_fund_ranking_index, sectors_from_article_industries

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger


@dataclass
class EventEvidence:
    sector_keys: list[str] = field(default_factory=list)
    clusters: list[list[dict]] = field(default_factory=list)
    articles: list[dict] = field(default_factory=list)
    severity: float = 1.0
    direction: str = "neutral"
    direction_filter: str = "any"
    mixed_direction: bool = False


def _direction_sign(direction: str) -> float:
    d = (direction or "").strip().lower()
    if d == "negative":
        return -1.0
    if d == "positive":
        return 1.0
    return 0.0


def _cluster_severity(cluster: list[dict]) -> float:
    if not cluster:
        return 1.0
    impacts = [int(a.get("max_impact") or 0) for a in cluster]
    base = max(impacts) if impacts else 1
    return max(1.0, min(5.0, float(base)))


def _filter_clusters_by_direction(
    clusters: list[list[dict]],
    direction_filter: str,
) -> list[list[dict]]:
    if direction_filter == "any":
        return clusters
    out: list[list[dict]] = []
    for cluster in clusters:
        dirs = {str(a.get("direction") or "").lower() for a in cluster}
        if direction_filter in dirs:
            out.append(cluster)
    return out


def gather_impact_evidence(
    question: str,
    router: RouterResult,
    *,
    published_from: str,
    published_to: str,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
) -> EventEvidence:
    settings = get_settings()
    direction_filter = infer_direction_filter(question, direction)
    idx = get_sector_fund_ranking_index()

    sector_keys = idx.resolve_from_question(question, router.event_focus)
    corpus = corpus_entity_names()
    entity_filter: list[str] = []
    for sk in sector_keys:
        if sk in corpus:
            entity_filter.append(sk)
        else:
            for name in idx.sector_names:
                if name.casefold() == sk.casefold() and name in corpus:
                    entity_filter.append(name)
                    break

    if not entity_filter and sector_keys:
        entity_filter = sector_keys[:4]

    # Macro/RBI news often tags "Banks" — add when question mentions policy rates.
    lower_q = f"{question} {router.event_focus}".lower()
    if any(t in lower_q for t in ("rbi", "repo rate", "rate hike", "monetary policy")):
        for macro_ent in ("Banks", "Macro - RBI"):
            if macro_ent in corpus and macro_ent not in entity_filter:
                entity_filter.append(macro_ent)
        if not sector_keys:
            sector_keys = idx.resolve_sector_keys(["Banks", "Finance"])

    filter_kwargs = {
        "entity_names": entity_filter if entity_filter else None,
        "published_from": published_from,
        "published_to": published_to,
        "min_relevance": settings.min_relevance,
        "min_impact": min_impact if min_impact is not None else 1,
        "source": source or None,
        "direction": direction if direction_filter == "any" else direction_filter,
    }
    filt = build_filter(**filter_kwargs)
    reader = QdrantReader()

    vector_query = f"{question.strip()} {router.event_focus}".strip()
    vector_rows: list[dict] = []
    if vector_query:
        t0 = time.perf_counter()
        try:
            from news_rag.embed import embed_query

            vector = embed_query(vector_query)
            vector_rows = reader.query_vector(vector, filt, settings.retrieve_vector_limit)
            if query_log is not None:
                query_log.log_step(
                    "impact_embed_query",
                    time.perf_counter() - t0,
                    hits=len(vector_rows),
                )
        except Exception:
            vector_rows = []

    scroll_rows = reader.scroll_filtered(filt, settings.retrieve_impact_limit)
    by_url: dict[str, dict] = {}
    for row in vector_rows + scroll_rows:
        url = str(row.get("url") or "").strip()
        if url and url not in by_url:
            by_url[url] = row
    articles = list(by_url.values())

    if query_log is not None:
        query_log.write(
            f"impact_evidence sector_keys={sector_keys!r} entity_filter={entity_filter!r} "
            f"articles={len(articles)} direction_filter={direction_filter}"
        )

    if not sector_keys and articles:
        sector_keys = sectors_from_article_industries(articles)

    from news_rag.fund_brief import cluster_articles

    clusters = cluster_articles(articles)
    clusters = _filter_clusters_by_direction(clusters, direction_filter)

    severities = [_cluster_severity(c) for c in clusters] if clusters else [1.0]
    severity = sum(severities) / len(severities) if severities else 1.0

    all_dirs: set[str] = set()
    for c in clusters:
        for a in c:
            d = str(a.get("direction") or "").lower()
            if d in ("positive", "negative"):
                all_dirs.add(d)
    lead_dir = "neutral"
    if len(all_dirs) == 1:
        lead_dir = next(iter(all_dirs))
    elif len(all_dirs) > 1:
        lead_dir = "mixed"

    if direction_filter != "any" and clusters:
        sign = _direction_sign(direction_filter)
        severity = severity * abs(sign if sign else 1.0)

    return EventEvidence(
        sector_keys=sector_keys,
        clusters=clusters,
        articles=articles,
        severity=severity,
        direction=lead_dir,
        direction_filter=direction_filter,
        mixed_direction=len(all_dirs) > 1,
    )
