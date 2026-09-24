"""Merge hits that share a URL. Known URLs go to entity-merge queue instead of full re-ingest."""

from __future__ import annotations

import logging

from news_pipeline.graph.state import PipelineState
from news_pipeline.run_log import get_run_logger
from news_pipeline.services import get_store
from news_pipeline.textutil import point_id_for_url

logger = logging.getLogger(__name__)


def skip_known_urls(state: PipelineState) -> dict:
    hits = state.get("candidates") or []
    run_log = get_run_logger()
    if run_log is not None:
        run_log.write(f"skip_known_urls started raw_hits={len(hits)}")

    merged = _merge_by_url(hits)
    multi = sum(1 for row in merged if len(row.get("matches") or []) > 1)
    store = get_store()
    known = store.existing_ids([row["url"] for row in merged])
    fresh: list[dict] = []
    known_merges: list[dict] = []
    for row in merged:
        if point_id_for_url(row["url"]) in known:
            known_merges.append(row)
        else:
            fresh.append(row)

    if run_log is not None:
        run_log.write(
            f"skip_known_urls merged unique_urls={len(merged)} multi_entity_urls={multi} "
            f"known_url_merges={len(known_merges)} new_urls={len(fresh)}"
        )
        for row in known_merges:
            names = ", ".join(m["name"] for m in row.get("matches") or [])
            run_log.write(
                f"skip_known_urls queue_entity_merge url={row['url']} matches=[{names}]"
            )

    counts = dict(state.get("counts") or {})
    counts["merged_urls"] = len(merged)
    counts["skipped_existing"] = len(known_merges)
    counts["new_urls"] = len(fresh)
    logger.info(
        "skip_known_urls merged=%s known_merges=%s fresh=%s",
        len(merged),
        len(known_merges),
        len(fresh),
    )
    return {"candidates": fresh, "known_merges": known_merges, "counts": counts}


def _merge_by_url(hits: list[dict]) -> list[dict]:
    by_url: dict[str, dict] = {}
    for hit in hits:
        url = hit["url"]
        match = {
            "name": hit["entity_name"],
            "type": hit["entity_type"],
            "industry": hit.get("entity_industry") or "",
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
