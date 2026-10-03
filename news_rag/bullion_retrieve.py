"""Retrieve news tagged Macro - Gold / Macro - Silver (plus vector supplement)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.embed import embed_query
from news_rag.parse import parse_time_window
from news_rag.qdrant_reader import QdrantReader, build_filter

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

MACRO_GOLD = "Macro - Gold"
MACRO_SILVER = "Macro - Silver"
MACRO_BULLION_ENTITIES = (MACRO_GOLD, MACRO_SILVER)


def _trim_snippet(text: str, limit: int) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _pack_row(row: dict, settings, *, vector_score: float = 0.0) -> dict:
    raw_text = str(row.get("scraped_text") or row.get("snippet") or "")
    snippet = _trim_snippet(raw_text, settings.snippet_chars)
    return {
        "url": row.get("url"),
        "title": row.get("title"),
        "source": row.get("source"),
        "published_at": row.get("published_at"),
        "entity_names": row.get("entity_names") or [],
        "sector_names": row.get("sector_names") or [],
        "snippet": snippet,
        "max_impact": int(row.get("max_impact") or 0),
        "_vector_score": vector_score,
    }


def retrieve_bullion_macro_news(
    semantic_query: str,
    *,
    question: str = "",
    window_days: int | None = None,
    query_log: QueryLogger | None = None,
) -> list[dict]:
    settings = get_settings()
    effective_days = window_days if window_days else settings.default_window_days
    published_from, published_to, _label = parse_time_window(
        question or semantic_query,
        date_from=None,
        date_to=None,
        default_days=effective_days,
    )
    reader = QdrantReader()
    query_text = (semantic_query or question).strip()
    t_embed = time.perf_counter()
    vector = embed_query(query_text)
    if query_log is not None:
        query_log.log_step("embed_query_bullion", time.perf_counter() - t_embed, vector_dim=len(vector))

    k = 60.0
    rrf_scores: dict[str, float] = {}
    by_url: dict[str, dict] = {}
    macro_urls: set[str] = set()

    base = {
        "published_from": published_from,
        "published_to": published_to,
        "min_relevance": settings.min_relevance,
    }

    for macro_name in MACRO_BULLION_ENTITIES:
        filt = build_filter(entity_names=[macro_name], **base)
        t_scroll = time.perf_counter()
        scroll_rows = reader.scroll_filtered(filt, 15)
        if query_log is not None:
            query_log.log_step(
                f"qdrant_scroll_{macro_name}",
                time.perf_counter() - t_scroll,
                hits=len(scroll_rows),
            )
        for rank, row in enumerate(scroll_rows):
            packed = _pack_row(row, settings)
            url = str(packed.get("url") or "")
            if not url:
                continue
            macro_urls.add(url)
            rrf_scores[url] = rrf_scores.get(url, 0.0) + (1.4 / (k + rank + 1))
            by_url[url] = packed

        t_vec = time.perf_counter()
        vec_rows = reader.query_vector(vector, filt, 12)
        if query_log is not None:
            query_log.log_step(
                f"qdrant_vector_{macro_name}",
                time.perf_counter() - t_vec,
                hits=len(vec_rows),
            )
        min_score = settings.retrieve_min_vector_score
        for rank, row in enumerate(vec_rows):
            if float(row.get("score") or 0) < min_score:
                continue
            packed = _pack_row(row, settings, vector_score=float(row.get("score") or 0.0))
            url = str(packed.get("url") or "")
            if not url:
                continue
            macro_urls.add(url)
            rrf_scores[url] = rrf_scores.get(url, 0.0) + (1.2 / (k + rank + 1))
            if url not in by_url:
                by_url[url] = packed

    if len(by_url) < 4:
        broad_filt = build_filter(entity_names=None, **base)
        vec_rows = reader.query_vector(vector, broad_filt, settings.retrieve_vector_limit)
        for rank, row in enumerate(vec_rows):
            if float(row.get("score") or 0) < settings.retrieve_min_vector_score:
                continue
            packed = _pack_row(row, settings, vector_score=float(row.get("score") or 0.0))
            url = str(packed.get("url") or "")
            if not url or url in by_url:
                continue
            blob = f"{packed.get('title')} {packed.get('snippet')}".lower()
            if "gold" not in blob and "silver" not in blob and "bullion" not in blob:
                continue
            rrf_scores[url] = rrf_scores.get(url, 0.0) + (0.6 / (k + rank + 1))
            by_url[url] = packed

    ranked: list[dict] = []
    for url, row in by_url.items():
        impact = int(row.get("max_impact") or 0)
        macro_boost = 0.12 if url in macro_urls else 0.0
        combined = rrf_scores.get(url, 0.0) + macro_boost + (0.01 * impact)
        ranked.append({**row, "_rrf_score": combined, "_macro_tagged": url in macro_urls})

    ranked.sort(
        key=lambda item: (
            item.get("_macro_tagged"),
            item["_rrf_score"],
            item["max_impact"],
        ),
        reverse=True,
    )
    final = ranked[:8]
    if query_log is not None:
        query_log.write(
            f"BULLION_RETRIEVE macro_tagged={sum(1 for x in final if x.get('_macro_tagged'))} "
            f"kept={len(final)}"
        )
        query_log.log_articles_block("bullion_macro_news", final, snippet_limit=400)
    return final
