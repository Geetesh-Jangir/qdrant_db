"""Layer-2 news: one search per holding, sector, macro topic, stock or the market.

Queries that share a window and direction go out in one batched Qdrant call.
No model reads the articles here. The composer gets them grouped by entity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NewsTarget:
    scope: str
    entity: str
    query: str
    window_days: int = 30
    direction: str | None = None
    limit: int = 2
    chars: int = 500
    required: bool = True
    articles: list[dict[str, str]] = field(default_factory=list)


def _body(row: dict[str, Any], chars: int) -> str:
    from news_rag.snippet_clean import article_body_for_llm

    text = article_body_for_llm(row, limit=chars)
    title = str(row.get("title") or "").strip()
    if title and text.lower().startswith(title.lower()[: min(40, len(title))]):
        text = text[len(title):].lstrip(" :-")
    return " ".join(text.split())[:chars]


def search_targets(targets: list[NewsTarget]) -> None:
    """Fill target.articles in place. Failures leave the list empty."""
    if not targets:
        return
    from news_rag.embed import embed_query
    from news_rag.parse import parse_time_window
    from news_rag.qdrant_reader import build_filter, get_qdrant_reader

    groups: dict[tuple[int, str], list[NewsTarget]] = {}
    for target in targets:
        direction = target.direction if target.direction in ("positive", "negative") else ""
        groups.setdefault((int(target.window_days), direction), []).append(target)

    reader = get_qdrant_reader()
    for (window, direction), group in groups.items():
        try:
            published_from, published_to, _label = parse_time_window(
                "", date_from=None, date_to=None, default_days=window
            )
            filt = build_filter(
                entity_names=None,
                published_from=published_from,
                published_to=published_to,
                direction=direction or None,
            )
            vectors = [embed_query(target.query) for target in group]
            batches = reader.query_vectors_batch(vectors, filt, limit=max(t.limit for t in group), with_body=False)
        except Exception:
            continue
        kept: list[dict[str, Any]] = []
        per_target: list[list[dict[str, Any]]] = []
        for target, rows in zip(group, batches):
            chosen = [row for row in rows if isinstance(row, dict)][: target.limit]
            per_target.append(chosen)
            kept.extend(chosen)
        try:
            reader.hydrate_bodies(kept)
        except Exception:
            pass
        for target, chosen in zip(group, per_target):
            articles = []
            for row in chosen:
                title = str(row.get("title") or "").strip()
                text = _body(row, target.chars)
                if not (title or text):
                    continue
                articles.append({"headline": title, "text": text, "url": str(row.get("url") or "")})
            target.articles = articles


def grouped_news(targets: list[NewsTarget]) -> dict[str, dict[str, list[dict[str, str]]]]:
    out: dict[str, dict[str, list[dict[str, str]]]] = {}
    for target in targets:
        out.setdefault(target.scope, {})[target.entity] = list(target.articles)
    return out
