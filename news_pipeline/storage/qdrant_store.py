"""Single Qdrant collection: one point per canonical URL."""

from __future__ import annotations

import logging
from datetime import timedelta

from qdrant_client import QdrantClient
from qdrant_client.models import (
    DatetimeRange,
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    Range,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
    SearchParams,
    VectorParams,
)

from news_pipeline.config import Settings
from news_pipeline.models import StoredArticle
from news_pipeline.textutil import point_id_for_url, to_iso, utc_now

logger = logging.getLogger(__name__)

_INDEXES = (
    ("published_at", PayloadSchemaType.DATETIME),
    ("scraped_at", PayloadSchemaType.DATETIME),
    ("entity_names", PayloadSchemaType.KEYWORD),
    ("source", PayloadSchemaType.KEYWORD),
    ("max_relevance", PayloadSchemaType.INTEGER),
    ("max_impact", PayloadSchemaType.INTEGER),
    ("direction", PayloadSchemaType.KEYWORD),
    ("event_type", PayloadSchemaType.KEYWORD),
)

_LIST_FIELDS = [
    "url",
    "title",
    "source",
    "published_at",
    "scraped_at",
    "max_impact",
    "max_relevance",
    "direction",
    "event_type",
    "entity_names",
]


class NewsStore:
    def __init__(self, settings: Settings) -> None:
        api_key = settings.qdrant_api_key or None
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=api_key,
            timeout=60,
            check_compatibility=False,
            prefer_grpc=False,
        )
        self._name = settings.collection_name
        self._dim = settings.embedding_dim
        self._upsert_batch = settings.upsert_batch
        self._settings = settings
        self._url = settings.qdrant_url

    def ensure_collection(self) -> None:
        names = {item.name for item in self._client.get_collections().collections}
        if self._name not in names:
            self._create_collection()
            return
        for field, schema in _INDEXES:
            try:
                self._client.create_payload_index(
                    collection_name=self._name,
                    field_name=field,
                    field_schema=schema,
                )
            except Exception as exc:
                message = str(exc).lower()
                if "already exists" in message or "already exist" in message:
                    continue
                raise

    def reset_collection(self) -> None:
        """Drop and recreate the news collection (empty dashboard, no URL skips)."""
        names = {item.name for item in self._client.get_collections().collections}
        if self._name in names:
            self._client.delete_collection(collection_name=self._name)
            logger.info("deleted collection %s", self._name)
        self._create_collection()

    def _create_collection(self) -> None:
        self._client.create_collection(
            collection_name=self._name,
            vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE, on_disk=False),
            on_disk_payload=True,
            quantization_config=ScalarQuantization(
                scalar=ScalarQuantizationConfig(
                    type=ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True,
                )
            ),
        )
        logger.info("created collection %s", self._name)
        for field, schema in _INDEXES:
            try:
                self._client.create_payload_index(
                    collection_name=self._name,
                    field_name=field,
                    field_schema=schema,
                )
            except Exception as exc:
                message = str(exc).lower()
                if "already exists" in message or "already exist" in message:
                    continue
                raise

    def existing_ids(self, urls: list[str]) -> set[str]:
        found: set[str] = set()
        ids = [point_id_for_url(url) for url in urls]
        for start in range(0, len(ids), 256):
            chunk = ids[start : start + 256]
            if not chunk:
                continue
            points = self._client.retrieve(
                collection_name=self._name,
                ids=chunk,
                with_payload=False,
                with_vectors=False,
            )
            for point in points:
                found.add(str(point.id))
        return found

    def recent_titles(self, entity_name: str, hours: int) -> list[str]:
        cutoff = to_iso(utc_now() - timedelta(hours=hours))
        filt = Filter(
            must=[
                FieldCondition(key="entity_names", match=MatchValue(value=entity_name)),
                FieldCondition(key="published_at", range=DatetimeRange(gte=cutoff)),
            ]
        )
        titles: list[str] = []
        offset = None
        while len(titles) < 200:
            points, offset = self._client.scroll(
                collection_name=self._name,
                scroll_filter=filt,
                limit=100,
                offset=offset,
                with_payload=["title"],
                with_vectors=False,
            )
            for point in points:
                title = (point.payload or {}).get("title")
                if title:
                    titles.append(title)
            if offset is None or not points:
                break
        return titles

    def upsert_articles(self, articles: list[StoredArticle], vectors: list[list[float]]) -> int:
        if len(articles) != len(vectors):
            raise ValueError("Each article needs one vector")
        points: list[PointStruct] = []
        for article, vector in zip(articles, vectors):
            if len(vector) != self._dim:
                raise ValueError(f"Expected {self._dim} dimensions, got {len(vector)}")
            points.append(
                PointStruct(
                    id=point_id_for_url(article.url),
                    vector=vector,
                    payload=article.model_dump(),
                )
            )
        written = 0
        for start in range(0, len(points), self._upsert_batch):
            batch = points[start : start + self._upsert_batch]
            self._client.upsert(collection_name=self._name, points=batch, wait=True)
            written += len(batch)
        return written

    def points_count(self) -> int:
        info = self._client.get_collection(collection_name=self._name)
        return int(info.points_count or 0)

    def list_collections(self) -> list[str]:
        return [item.name for item in self._client.get_collections().collections]

    def scroll_points(self, limit: int = 100, include_text: bool = False) -> list[dict]:
        """Return up to `limit` point payloads (no relevance filter)."""
        fields = list(_LIST_FIELDS)
        if include_text:
            fields.extend(["scraped_text", "entities"])
        collected: list[dict] = []
        offset = None
        while len(collected) < limit:
            batch, offset = self._client.scroll(
                collection_name=self._name,
                limit=min(128, limit - len(collected)),
                offset=offset,
                with_payload=fields,
                with_vectors=False,
            )
            for point in batch:
                payload = dict(point.payload or {})
                payload["point_id"] = str(point.id)
                collected.append(payload)
            if offset is None or not batch:
                break
        return collected[:limit]

    def target_label(self) -> str:
        return f"{self._url} collection={self._name}"

    def list_articles(
        self,
        *,
        entity_names: list[str] | None = None,
        published_from: str | None = None,
        published_to: str | None = None,
        scraped_from: str | None = None,
        scraped_to: str | None = None,
        source: str | None = None,
        direction: str | None = None,
        event_type: str | None = None,
        min_relevance: int = 2,
        min_impact: int | None = None,
        limit: int = 20,
        include_text: bool = False,
    ) -> list[dict]:
        filt = self._filter(
            entity_names=entity_names,
            published_from=published_from,
            published_to=published_to,
            scraped_from=scraped_from,
            scraped_to=scraped_to,
            source=source,
            direction=direction,
            event_type=event_type,
            min_relevance=min_relevance,
            min_impact=min_impact,
        )
        fields = list(_LIST_FIELDS)
        if include_text:
            fields.extend(["scraped_text", "entities"])
        points = self._scroll(filt, limit=max(limit, 1), payload_fields=fields)
        rows = [dict(point.payload or {}) for point in points]
        rows.sort(key=lambda row: (row.get("published_at") or "", row.get("max_impact") or 0), reverse=True)
        return rows[:limit]

    def semantic_search(self, query: str, limit: int = 20, **filters: object) -> list[dict]:
        from news_pipeline.embeddings.encoder import get_encoder

        vector = get_encoder(self._settings).embed_query(query)
        filt = self._filter(**filters)  # type: ignore[arg-type]
        response = self._client.query_points(
            collection_name=self._name,
            query=vector,
            query_filter=filt,
            limit=limit,
            with_payload=_LIST_FIELDS,
            search_params=SearchParams(hnsw_ef=128),
        )
        rows = []
        for point in response.points:
            payload = dict(point.payload or {})
            payload["score"] = point.score
            rows.append(payload)
        return rows

    def delete_older_than(self, days: int) -> int:
        if days <= 0:
            return 0
        cutoff = to_iso(utc_now() - timedelta(days=days))
        filt = Filter(must=[FieldCondition(key="published_at", range=DatetimeRange(lt=cutoff))])
        counted = self._client.count(collection_name=self._name, count_filter=filt, exact=True)
        count = int(counted.count)
        if count == 0:
            return 0
        self._client.delete(
            collection_name=self._name,
            points_selector=FilterSelector(filter=filt),
            wait=True,
        )
        return count

    def _scroll(self, filt: Filter, limit: int, payload_fields: list[str]):
        collected = []
        offset = None
        while len(collected) < limit:
            batch, offset = self._client.scroll(
                collection_name=self._name,
                scroll_filter=filt,
                limit=min(128, limit - len(collected)),
                offset=offset,
                with_payload=payload_fields,
                with_vectors=False,
            )
            collected.extend(batch)
            if offset is None or not batch:
                break
        return collected

    def _filter(
        self,
        *,
        entity_names: list[str] | None = None,
        published_from: str | None = None,
        published_to: str | None = None,
        scraped_from: str | None = None,
        scraped_to: str | None = None,
        source: str | None = None,
        direction: str | None = None,
        event_type: str | None = None,
        min_relevance: int = 2,
        min_impact: int | None = None,
    ) -> Filter:
        must: list[FieldCondition] = [
            FieldCondition(key="max_relevance", range=Range(gte=min_relevance)),
        ]
        if entity_names:
            must.append(FieldCondition(key="entity_names", match=MatchAny(any=entity_names)))
        if source:
            must.append(FieldCondition(key="source", match=MatchValue(value=source)))
        if direction:
            must.append(FieldCondition(key="direction", match=MatchValue(value=direction)))
        if event_type:
            must.append(FieldCondition(key="event_type", match=MatchValue(value=event_type)))
        if min_impact is not None:
            must.append(FieldCondition(key="max_impact", range=Range(gte=min_impact)))
        published = _datetime_range(published_from, published_to)
        if published is not None:
            must.append(FieldCondition(key="published_at", range=published))
        scraped = _datetime_range(scraped_from, scraped_to)
        if scraped is not None:
            must.append(FieldCondition(key="scraped_at", range=scraped))
        return Filter(must=must)


def _datetime_range(start: str | None, end: str | None) -> DatetimeRange | None:
    kwargs = {}
    if start is not None:
        kwargs["gte"] = start
    if end is not None:
        kwargs["lte"] = end
    if not kwargs:
        return None
    return DatetimeRange(**kwargs)
