"""Merge retrieved articles from execution bundle pools and tool payloads."""

from __future__ import annotations

from typing import Any


def article_dedupe_key(article: dict[str, Any]) -> str:
    url = str(article.get("url") or "").strip()
    if url:
        return url
    title = str(article.get("title") or "").strip().lower()
    return f"title:{title}" if title else ""


def merge_article(pool: list[dict[str, Any]], seen: set[str], article: dict[str, Any]) -> None:
    if not isinstance(article, dict):
        return
    key = article_dedupe_key(article)
    if not key or key in seen:
        return
    seen.add(key)
    pool.append(article)


def collect_bundle_articles(bundle: Any) -> list[dict[str, Any]]:
    arts: list[dict[str, Any]] = []
    seen: set[str] = set()
    pools = list(bundle.articles_by_focus.values()) + list(bundle.articles_by_layer.values())
    for layer_arts in pools:
        for a in layer_arts:
            merge_article(arts, seen, a)

    for _key, val in (bundle.tool_results or {}).items():
        if not isinstance(val, dict) or not val.get("ok"):
            continue
        data = val.get("data") or {}
        for a in data.get("articles") or []:
            merge_article(arts, seen, a)
        for cl in data.get("clusters") or []:
            if not isinstance(cl, dict):
                continue
            for a in cl.get("articles") or []:
                merge_article(arts, seen, a)
    return arts


def sources_from_articles(articles: list[dict[str, Any]], limit: int = 40) -> list[dict[str, Any]]:
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for a in articles:
        key = article_dedupe_key(a)
        if not key or key in seen:
            continue
        seen.add(key)
        url = str(a.get("url") or "").strip()
        rows.append(
            {
                "title": a.get("title"),
                "url": url or None,
                "source": a.get("source"),
                "published_at": a.get("published_at"),
                "direction": a.get("direction"),
                "max_impact": a.get("max_impact"),
            }
        )
    rows.sort(key=lambda r: (-int(r.get("max_impact") or 0), str(r.get("published_at") or "")))
    return rows[:limit]
