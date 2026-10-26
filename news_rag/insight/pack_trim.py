"""Helpers to trim evidence for the composer prompt."""

from __future__ import annotations

from typing import Any


def trim_news_grouped(news: dict[str, Any], *, max_articles: int = 12) -> dict[str, Any]:
    if not news or max_articles <= 0:
        return news
    flat: list[tuple[str, str, dict[str, Any]]] = []
    for scope, bucket in news.items():
        if isinstance(bucket, dict):
            for entity, arts in bucket.items():
                if isinstance(arts, list):
                    for a in arts:
                        if isinstance(a, dict):
                            flat.append((str(scope), str(entity), a))
        elif isinstance(bucket, list):
            for a in bucket:
                if isinstance(a, dict):
                    flat.append((str(scope), "", a))
    flat.sort(
        key=lambda t: (-int(t[2].get("max_impact") or 0), str(t[2].get("title") or "")),
    )
    kept = flat[:max_articles]
    out: dict[str, Any] = {}
    for scope, entity, art in kept:
        if entity:
            out.setdefault(scope, {}).setdefault(entity, []).append(art)
        else:
            out.setdefault(scope, []).append(art)
    return out
