"""Has the news ingest written anything new inside this session window?"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from qdrant_client.models import DatetimeRange, Direction, FieldCondition, Filter, OrderBy

from news_pipeline.textutil import parse_time

from ai_insight.common.config import CommonConfig, load_config
from ai_insight.common.qdrant_access import _client


def newest_scraped_at(
    window: tuple[str, str],
    *,
    client: Any = None,
    collection: str | None = None,
    config: CommonConfig | None = None,
) -> datetime | None:
    del config
    qdrant, collection_name = _client(client, collection)
    filt = Filter(
        must=[FieldCondition(key="scraped_at", range=DatetimeRange(gte=window[0], lte=window[1]))]
    )
    batch, _offset = qdrant.scroll(
        collection_name=collection_name,
        scroll_filter=filt,
        limit=1,
        order_by=OrderBy(key="scraped_at", direction=Direction.DESC),
        with_payload=["scraped_at"],
        with_vectors=False,
    )
    if not batch:
        return None
    return parse_time(str((batch[0].payload or {}).get("scraped_at") or ""))


def is_stale(
    window: tuple[str, str],
    max_hours: float | None = None,
    *,
    now: datetime | None = None,
    client: Any = None,
    collection: str | None = None,
    config: CommonConfig | None = None,
) -> bool:
    cfg = config or load_config()
    limit = cfg.max_ingest_age_hours if max_hours is None else max_hours
    newest = newest_scraped_at(window, client=client, collection=collection, config=cfg)
    if newest is None:
        return True
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    age_hours = (clock.astimezone(timezone.utc) - newest.astimezone(timezone.utc)).total_seconds() / 3600
    return age_hours > limit
