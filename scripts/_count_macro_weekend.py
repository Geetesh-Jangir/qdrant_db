"""One-off: count macro-tagged articles by IST published_at day. Read-only Qdrant."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from qdrant_client import QdrantClient
from qdrant_client.models import DatetimeRange, FieldCondition, Filter, MatchAny

from news_pipeline.config import MACRO_ENTITIES, Settings

IST = timezone(timedelta(hours=5, minutes=30))


def ist_day_bounds(y: int, m: int, d: int) -> tuple[str, str]:
    start = datetime(y, m, d, 0, 0, 0, tzinfo=IST).astimezone(timezone.utc)
    end = datetime(y, m, d, 23, 59, 59, 999000, tzinfo=IST).astimezone(timezone.utc)
    return start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")


def scroll_day(client: QdrantClient, collection: str, names: list[str], gte: str, lte: str):
    filt = Filter(
        must=[
            FieldCondition(key="entity_names", match=MatchAny(any=names)),
            FieldCondition(key="published_at", range=DatetimeRange(gte=gte, lte=lte)),
        ]
    )
    per_entity: dict[str, int] = defaultdict(int)
    urls: set[str] = set()
    macro_link_rows = 0
    offset = None
    while True:
        batch, offset = client.scroll(
            collection_name=collection,
            scroll_filter=filt,
            limit=256,
            offset=offset,
            with_payload=["url", "entities"],
            with_vectors=False,
        )
        for pt in batch:
            p = pt.payload or {}
            urls.add(str(p.get("url") or pt.id))
            for ent in p.get("entities") or []:
                if not isinstance(ent, dict):
                    continue
                ename = ent.get("name")
                if ent.get("type") == "macro" and ename in names:
                    per_entity[str(ename)] += 1
                    macro_link_rows += 1
        if offset is None or not batch:
            break
    return len(urls), macro_link_rows, dict(per_entity)


def main() -> None:
    settings = Settings()
    names = [row["name"] for row in MACRO_ENTITIES]
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
        timeout=120,
        check_compatibility=False,
    )
    total = int(client.get_collection(settings.collection_name).points_count or 0)
    host = settings.qdrant_url.split("/")[2] if "://" in settings.qdrant_url else settings.qdrant_url

    print(f"collection={settings.collection_name} host={host}")
    print(f"total_points_in_collection={total}")
    print(f"macro_entities={len(names)}")
    print()
    print("Filter: published_at IST day; entities[].type=macro and name in MACRO_ENTITIES")
    print()

    days = [
        ("Saturday 14-Nov-2026", 2026, 11, 14),
        ("Sunday 15-Nov-2026", 2026, 11, 15),
        ("Monday 16-Nov-2026", 2026, 11, 16),
    ]
    for label, y, m, d in days:
        gte, lte = ist_day_bounds(y, m, d)
        n_urls, n_links, per = scroll_day(client, settings.collection_name, names, gte, lte)
        print(f"=== {label} ===")
        print(f"  published_at UTC: {gte} .. {lte}")
        print(f"  unique articles: {n_urls}")
        print(f"  macro entity-tags (multi per URL): {n_links}")
        print("  per entity:")
        for name in names:
            print(f"    {per.get(name, 0):4d}  {name}")
        print()


if __name__ == "__main__":
    main()