"""Scroll news_articles, explode entities[], and gate each entity on its own scores."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from qdrant_client.models import DatetimeRange, FieldCondition, Filter, MatchAny

logger = logging.getLogger(__name__)

_PAYLOAD = ["url", "title", "source", "published_at", "scraped_at", "scraped_text", "alias_urls", "entities"]
_PAYLOAD_NO_TEXT = ["url", "title", "source", "published_at", "scraped_at", "alias_urls", "entities"]
_SAMPLE_LIMIT = 3
_PAGE = 128
_DROP_REASONS = (
    "wrong_type_or_name",
    "low_relevance",
    "low_impact",
    "low_about",
    "price_recap",
    "opinion_low_impact",
)


@dataclass(frozen=True)
class GateConfig:
    min_relevance: int = 3
    min_impact: int = 2
    min_about: float = 0.7
    drop_event_types: tuple[str, ...] = ("price_recap",)
    opinion_min_impact: int = 3


@dataclass
class GateDiagnostics:
    articles_scanned: int = 0
    entities_scanned: int = 0
    entities_passed: int = 0
    dropped: dict[str, int] = field(default_factory=dict)
    pages: int = 0
    elapsed_ms: float = 0.0
    sample_dropped: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for reason in _DROP_REASONS:
            self.dropped.setdefault(reason, 0)


@dataclass
class EntityRowsResult:
    rows: list[dict[str, Any]]
    diagnostics: GateDiagnostics


def passes_gate(entity: dict[str, Any], gate: GateConfig) -> tuple[bool, str | None]:
    """First failing reason wins, so the drop counts add up to the rows that were rejected."""
    relevance = _int(entity.get("relevance"))
    impact = _int(entity.get("impact"))
    about = _float(entity.get("about_this_name"))
    event_type = str(entity.get("event_type") or "").strip().lower()
    if relevance < gate.min_relevance:
        return False, "low_relevance"
    if impact < gate.min_impact:
        return False, "low_impact"
    if about < gate.min_about:
        return False, "low_about"
    if event_type in gate.drop_event_types:
        return False, "price_recap"
    if event_type == "opinion" and impact < gate.opinion_min_impact:
        return False, "opinion_low_impact"
    return True, None


def fetch_entity_rows(
    entity_type: str,
    window: tuple[str, str],
    names: list[str] | None = None,
    gate: GateConfig | None = None,
    *,
    client: Any = None,
    collection: str | None = None,
    log: Any = None,
    with_text: bool = True,
) -> EntityRowsResult:
    gate = gate or GateConfig()
    wanted = _names(entity_type, names)
    qdrant, collection_name = _client(client, collection)
    started = time.perf_counter()
    diagnostics = GateDiagnostics()
    rows: list[dict[str, Any]] = []
    filt = _filter(entity_type, window, wanted)
    offset = None
    while True:
        batch, offset = qdrant.scroll(
            collection_name=collection_name,
            scroll_filter=filt,
            limit=_PAGE,
            offset=offset,
            with_payload=list(_PAYLOAD if with_text else _PAYLOAD_NO_TEXT),
            with_vectors=False,
        )
        diagnostics.pages += 1
        for point in batch:
            payload = point.payload or {}
            diagnostics.articles_scanned += 1
            rows.extend(_explode(payload, entity_type, wanted, gate, diagnostics, with_text=with_text))
        if offset is None or not batch:
            break
    diagnostics.entities_passed = len(rows)
    diagnostics.elapsed_ms = (time.perf_counter() - started) * 1000
    if log is not None:
        dropped = " ".join(f"{key}={value}" for key, value in diagnostics.dropped.items())
        log.line(
            "QDRANT",
            f"type={entity_type} articles={diagnostics.articles_scanned} "
            f"entities={diagnostics.entities_scanned} passed={diagnostics.entities_passed} "
            f"pages={diagnostics.pages} dropped[{dropped}]",
        )
    logger.info(
        "entity gate %s scanned=%s passed=%s",
        entity_type,
        diagnostics.articles_scanned,
        diagnostics.entities_passed,
    )
    return EntityRowsResult(rows, diagnostics)


def _explode(
    payload: dict[str, Any],
    entity_type: str,
    names: list[str] | None,
    gate: GateConfig,
    diagnostics: GateDiagnostics,
    *,
    with_text: bool = True,
) -> list[dict[str, Any]]:
    text = str(payload.get("scraped_text") or "") if with_text else ""
    article = {
        "url": str(payload.get("url") or ""),
        "title": str(payload.get("title") or ""),
        "source": str(payload.get("source") or ""),
        "published_at": str(payload.get("published_at") or ""),
        "scraped_at": str(payload.get("scraped_at") or ""),
        "scraped_text": text,
        "full_text": text,
        "alias_urls": [str(url) for url in (payload.get("alias_urls") or []) if url],
    }
    kept: list[dict[str, Any]] = []
    for raw in payload.get("entities") or []:
        entity = _as_dict(raw)
        diagnostics.entities_scanned += 1
        if not _name_ok(entity, entity_type, names):
            _drop(diagnostics, "wrong_type_or_name", article, entity)
            continue
        ok, reason = passes_gate(entity, gate)
        if not ok:
            _drop(diagnostics, reason or "low_relevance", article, entity)
            continue
        kept.append({"article": article, "entity": _entity_view(entity)})
    return kept


def _drop(diagnostics: GateDiagnostics, reason: str, article: dict[str, Any], entity: dict[str, Any]) -> None:
    diagnostics.dropped[reason] = diagnostics.dropped.get(reason, 0) + 1
    samples = diagnostics.sample_dropped.setdefault(reason, [])
    if len(samples) < _SAMPLE_LIMIT:
        samples.append(
            {
                "title": str(article.get("title") or ""),
                "url": str(article.get("url") or ""),
                "name": str(entity.get("name") or ""),
            }
        )


def _name_ok(entity: dict[str, Any], entity_type: str, names: list[str] | None) -> bool:
    if str(entity.get("type") or "") != entity_type:
        return False
    if names is None:
        return True
    return str(entity.get("name") or "") in set(names)


def _entity_view(entity: dict[str, Any]) -> dict[str, Any]:
    direction = str(entity.get("direction") or "unclear")
    impact = _int(entity.get("impact"))
    if direction == "positive":
        signed = impact
    elif direction == "negative":
        signed = -impact
    else:
        signed = 0
    return {
        "name": str(entity.get("name") or ""),
        "type": str(entity.get("type") or ""),
        "relevance": _int(entity.get("relevance")),
        "impact": impact,
        "direction": direction,
        "event_type": str(entity.get("event_type") or ""),
        "about_this_name": _float(entity.get("about_this_name")),
        "affects_sector": _float(entity.get("affects_sector")),
        "affects_stock": _float(entity.get("affects_stock")),
        "affects_macro": _float(entity.get("affects_macro")),
        "signed_score": signed,
    }


def _filter(entity_type: str, window: tuple[str, str], names: list[str] | None) -> Filter:
    must: list[Any] = [
        FieldCondition(key="published_at", range=DatetimeRange(gte=window[0], lte=window[1])),
    ]
    if names:
        name_match = MatchAny(any=list(names))
        if entity_type == "sector":
            must.append(
                Filter(
                    should=[
                        FieldCondition(key="entity_names", match=name_match),
                        FieldCondition(key="sector_names", match=name_match),
                    ]
                )
            )
        else:
            must.append(FieldCondition(key="entity_names", match=name_match))
    return Filter(must=must)


def _names(entity_type: str, names: list[str] | None) -> list[str] | None:
    if entity_type not in {"holding", "sector", "macro"}:
        raise ValueError(f"unknown entity_type {entity_type!r}")
    if names:
        return list(names)
    if entity_type == "holding":
        raise ValueError("holding queries need an explicit names list")
    if entity_type == "sector":
        from news_pipeline.config import SECTOR_QUERIES

        return list(SECTOR_QUERIES)
    from news_pipeline.config import MACRO_ENTITIES

    return [str(item["name"]) for item in MACRO_ENTITIES]


def _client(client: Any, collection: str | None) -> tuple[Any, str]:
    if client is not None:
        return client, collection or "news_articles"
    from qdrant_client import QdrantClient

    from news_rag.config import get_settings

    settings = get_settings()
    opened = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
        timeout=60,
        check_compatibility=False,
        prefer_grpc=False,
    )
    return opened, collection or settings.qdrant_collection


def _as_dict(entity: Any) -> dict[str, Any]:
    if isinstance(entity, dict):
        return entity
    if hasattr(entity, "model_dump"):
        return entity.model_dump()
    return dict(entity)


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
