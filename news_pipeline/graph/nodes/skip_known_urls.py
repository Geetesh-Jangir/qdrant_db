"""Merge hits that share a URL, then drop URLs already stored in Qdrant."""

from __future__ import annotations

import logging

from news_pipeline.graph.state import PipelineState
from news_pipeline.services import get_store
from news_pipeline.textutil import point_id_for_url

logger = logging.getLogger(__name__)


def skip_known_urls(state: PipelineState) -> dict:
    hits = state.get("candidates") or []
    merged = _merge_by_url(hits)
    store = get_store()
    known = store.existing_ids([row["url"] for row in merged])
    fresh = [row for row in merged if point_id_for_url(row["url"]) not in known]
    counts = dict(state.get("counts") or {})
    counts["merged_urls"] = len(merged)
    counts["skipped_existing"] = len(merged) - len(fresh)
    logger.info(
        "skip_known_urls merged=%s skipped_existing=%s remaining=%s",
        len(merged),
        counts["skipped_existing"],
        len(fresh),
    )
    return {"candidates": fresh, "counts": counts}


def _merge_by_url(hits: list[dict]) -> list[dict]:
    by_url: dict[str, dict] = {}
    for hit in hits:
        url = hit["url"]
        match = {
            "name": hit["entity_name"],
            "type": hit["entity_type"],
            "fund_count": hit["fund_count"],
            "total_percentage": hit["total_percentage"],
            "title_relevance": None,
        }
        current = by_url.get(url)
        if current is None:
            by_url[url] = {
                "url": url,
                "title": hit["title"],
                "source": hit["source"],
                "published_at": hit["published_at"],
                "snippet": hit.get("snippet") or "",
                "matches": [match],
                "scraped_text": None,
                "scraped_at": None,
            }
            continue
        if not any(item["name"] == match["name"] for item in current["matches"]):
            current["matches"].append(match)
        if len(hit["title"]) > len(current["title"]):
            current["title"] = hit["title"]
        if not current["published_at"] and hit["published_at"]:
            current["published_at"] = hit["published_at"]
        if len(hit.get("snippet") or "") > len(current["snippet"]):
            current["snippet"] = hit["snippet"]
    return list(by_url.values())
