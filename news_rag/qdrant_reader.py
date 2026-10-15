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
    "sector_names",
    "holding_names",
    "primary_industry",
    "max_impact",
    "max_relevance",
    "direction",
    "event_type",
    "scraped_text",
]

# Ranking does not need article bodies. Bodies are fetched only for the rows we keep.
_LIGHT_PAYLOAD_FIELDS = [name for name in _PAYLOAD_FIELDS if name != "scraped_text"]

_PAYLOAD_INDEX_KEYS = (
    "published_at",
    "max_relevance",
    "max_impact",
    "direction",
    "entity_names",
)

_reader_singleton: "QdrantReader | None" = None


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
        *,
        with_body: bool = True,
    ) -> list[dict]:
        response = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            query_filter=filt,
            limit=limit,
            with_payload=_PAYLOAD_FIELDS if with_body else _LIGHT_PAYLOAD_FIELDS,
            search_params=SearchParams(hnsw_ef=128),
        )
        return [_point_row(point) for point in response.points]

    def query_vectors_batch(
        self,
        vectors: list[list[float]],
        filt: Filter,
        limit: int,
        *,
        with_body: bool = False,
    ) -> list[list[dict]]:
        """One HTTP round trip for several vectors that share a filter."""
        from qdrant_client.models import QueryRequest

        if not vectors:
            return []
        payload = _PAYLOAD_FIELDS if with_body else _LIGHT_PAYLOAD_FIELDS
        requests = [
            QueryRequest(
                query=vector,
                filter=filt,
                limit=limit,
                with_payload=payload,
                params=SearchParams(hnsw_ef=128),
            )
            for vector in vectors
        ]
        responses = self._client.query_batch_points(
            collection_name=self._collection,
            requests=requests,
        )
        return [[_point_row(point) for point in response.points] for response in responses]

    def hydrate_bodies(self, rows: list[dict]) -> None:
        """Fill scraped_text for the rows we will actually read."""
        ids = [row.get("_point_id") for row in rows if row.get("_point_id") is not None and not row.get("scraped_text")]
        if not ids:
            return
        points = self._client.retrieve(
            collection_name=self._collection,
            ids=ids,
            with_payload=["scraped_text"],
            with_vectors=False,
        )
        by_id = {point.id: str((point.payload or {}).get("scraped_text") or "") for point in points}
        for row in rows:
            body = by_id.get(row.get("_point_id"))
            if body:
                row["scraped_text"] = body

    def missing_payload_indexes(self) -> list[str]:
        try:
            info = self._client.get_collection(self._collection)
        except Exception:
            return list(_PAYLOAD_INDEX_KEYS)
        schema = getattr(info, "payload_schema", None) or {}
        if hasattr(schema, "keys"):
            present = {str(key) for key in schema.keys()}
        else:
            present = set()
        return [key for key in _PAYLOAD_INDEX_KEYS if key not in present]

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


def _point_row(point: Any) -> dict:
    row = dict(point.payload or {})
    row["score"] = float(point.score or 0.0)
    row["_point_id"] = point.id
    return row


def get_qdrant_reader() -> QdrantReader:
    """Reuse one client (and its HTTP connection) across retrieval calls."""
    global _reader_singleton
    if _reader_singleton is None:
        _reader_singleton = QdrantReader()
    return _reader_singleton
