"""Read-only Qdrant access for RAG."""

from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    DatetimeRange,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    Range,
    SearchParams,
)

from news_rag.config import get_settings

_PAYLOAD_FIELDS = [
    "url",
    "title",
    "source",
    "published_at",
    "entity_names",
    "holding_names",
    "primary_industry",
    "max_impact",
    "max_relevance",
    "direction",
    "event_type",
    "scraped_text",
]


def filter_spec(
    *,
    entity_names: list[str] | None,
    published_from: str,
    published_to: str | None = None,
    min_relevance: int = 2,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
) -> dict[str, Any]:
    """Human-readable filter description for query logs."""
    spec: dict[str, Any] = {
        "max_relevance_gte": min_relevance,
        "published_at_gte": published_from,
    }
    if published_to:
        spec["published_at_lte"] = published_to
    if entity_names:
        spec["entity_names_any"] = entity_names
    else:
        spec["entity_names_any"] = None
    if min_impact is not None:
        spec["max_impact_gte"] = min_impact
    if source:
        spec["source_eq"] = source
    if direction:
        spec["direction_eq"] = direction
    return spec


def describe_filters_for_log(
    spec: dict[str, Any],
    *,
    collection: str,
    post_filters: dict[str, Any],
) -> list[str]:
    """Plain-English lines for RAG query logs."""
    lines = [f"collection={collection}"]
    lines.append(f"max_relevance >= {spec.get('max_relevance_gte')}")
    gte = spec.get("published_at_gte")
    lte = spec.get("published_at_lte")
    if lte:
        lines.append(f"published_at from {gte} through {lte}")
    else:
        lines.append(f"published_at >= {gte}")

    entities = spec.get("entity_names_any")
    if entities:
        lines.append(f"entity_names must include any of {entities}")
    else:
        lines.append("entity_names filter: not applied (broad corpus search)")

    if spec.get("max_impact_gte") is not None:
        lines.append(f"max_impact >= {spec['max_impact_gte']}")
    else:
        lines.append("max_impact filter: not applied")

    if spec.get("source_eq"):
        lines.append(f"source equals {spec['source_eq']!r}")
    else:
        lines.append("source filter: not applied")

    if spec.get("direction_eq"):
        lines.append(f"direction equals {spec['direction_eq']!r}")
    else:
        lines.append("direction filter: not applied")

    if post_filters.get("exclude_event_type_price_recap"):
        lines.append("post-filter: exclude event_type=price_recap unless question asks for price/recap")
    lines.append(
        f"retrieval limits: vector_top={post_filters.get('retrieve_vector_limit')} "
        f"scroll_top={post_filters.get('retrieve_impact_limit')} "
        f"max_to_llm={post_filters.get('retrieve_max_articles')}"
    )
    return lines


def build_filter(
    *,
    entity_names: list[str] | None,
    published_from: str,
    published_to: str | None = None,
    min_relevance: int = 2,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
) -> Filter:
    published_range = DatetimeRange(gte=published_from)
    if published_to:
        published_range = DatetimeRange(gte=published_from, lte=published_to)
    must: list[FieldCondition] = [
        FieldCondition(key="max_relevance", range=Range(gte=min_relevance)),
        FieldCondition(key="published_at", range=published_range),
    ]
    if entity_names:
        must.append(FieldCondition(key="entity_names", match=MatchAny(any=entity_names)))
    if min_impact is not None:
        must.append(FieldCondition(key="max_impact", range=Range(gte=min_impact)))
    if source:
        must.append(FieldCondition(key="source", match=MatchValue(value=source)))
    if direction:
        must.append(FieldCondition(key="direction", match=MatchValue(value=direction)))
    return Filter(must=must)


class QdrantReader:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=60,
            check_compatibility=False,
            prefer_grpc=False,
        )
        self._collection = settings.qdrant_collection

    def scroll_entity_names(self) -> set[str]:
        names: set[str] = set()
        offset = None
        while True:
            batch, offset = self._client.scroll(
                collection_name=self._collection,
                limit=128,
                offset=offset,
                with_payload=["entity_names", "holding_names", "primary_industry"],
                with_vectors=False,
            )
            for point in batch:
                payload = point.payload or {}
                for key in ("entity_names", "holding_names"):
                    for name in payload.get(key) or []:
                        if name:
                            names.add(str(name))
                industry = payload.get("primary_industry")
                if industry:
                    names.add(str(industry))
            if offset is None or not batch:
                break
        return names

    def query_vector(
        self,
        vector: list[float],
        filt: Filter,
        limit: int,
    ) -> list[dict]:
        response = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            query_filter=filt,
            limit=limit,
            with_payload=_PAYLOAD_FIELDS,
            search_params=SearchParams(hnsw_ef=128),
        )
        rows = []
        for point in response.points:
            row = dict(point.payload or {})
            row["score"] = float(point.score or 0.0)
            rows.append(row)
        return rows

    def scroll_filtered(self, filt: Filter, limit: int) -> list[dict]:
        collected: list[dict] = []
        offset = None
        while len(collected) < limit:
            batch, offset = self._client.scroll(
                collection_name=self._collection,
                scroll_filter=filt,
                limit=min(128, limit - len(collected)),
                offset=offset,
                with_payload=_PAYLOAD_FIELDS,
                with_vectors=False,
            )
            for point in batch:
                collected.append(dict(point.payload or {}))
            if offset is None or not batch:
                break
        return collected[:limit]
