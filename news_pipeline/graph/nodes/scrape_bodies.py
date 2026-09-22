"""Scrape article bodies."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from lib.fetch import thread_session
from news_pipeline.graph.state import PipelineState
from news_pipeline.run_log import clip_log_text, get_run_logger
from news_pipeline.scrape.engine import scrape_one
from news_pipeline.services import get_settings
from news_pipeline.textutil import parse_time, to_iso, utc_now, within_news_window

logger = logging.getLogger(__name__)


def scrape_bodies(state: PipelineState) -> dict:
    settings = get_settings()
    candidates = state.get("candidates") or []
    errors = list(state.get("errors") or [])
    now = utc_now()
    scraped_at = to_iso(now)

    if not candidates:
        counts = dict(state.get("counts") or {})
        counts["scraped"] = 0
        run_log = get_run_logger()
        if run_log is not None:
            run_log.write("scrape_bodies skipped reason=no_candidates")
        return {"candidates": [], "counts": counts, "errors": errors}

    run_log = get_run_logger()
    if run_log is not None:
        run_log.write(f"scrape_bodies started urls={len(candidates)} workers={settings.scrape_workers}")

    results: dict[str, dict | None] = {}
    with ThreadPoolExecutor(max_workers=settings.scrape_workers) as pool:
        futures = {pool.submit(_scrape, row["url"]): row["url"] for row in candidates}
        for future in as_completed(futures):
            url = futures[future]
            try:
                record = future.result()
                results[url] = record
                if run_log is not None:
                    _log_scrape_record(run_log, url, record)
            except Exception as exc:
                message = str(exc)
                errors.append({"stage": "scrape_bodies", "url": url, "error": message})
                results[url] = None
                if run_log is not None:
                    run_log.write(f"scrape url={url} FAIL error={clip_log_text(message)}")

    kept = []
    for candidate in candidates:
        record = results.get(candidate["url"])
        if not isinstance(record, dict):
            if run_log is not None:
                run_log.write(f"scrape drop url={candidate['url']} reason=no_record")
            continue
        if record["status"] in ("fetch_failed", "resolve_failed"):
            if run_log is not None:
                err = clip_log_text(record.get("error") or record["status"])
                run_log.write(
                    f"scrape drop url={candidate['url']} reason={record['status']} detail={err}"
                )
            continue
        text = (record.get("text") or "").strip()
        if len(text) < settings.min_body_chars:
            if run_log is not None:
                run_log.write(
                    f"scrape drop url={candidate['url']} reason=short_body "
                    f"chars={len(text)} min={settings.min_body_chars}"
                )
            continue
        published = parse_time(candidate.get("published_at"))
        if published is None:
            published = parse_time(record.get("date"))
        if published is None or not within_news_window(published, settings.news_window_hours, now):
            if run_log is not None:
                run_log.write(
                    f"scrape drop url={candidate['url']} reason=outside_news_window "
                    f"published={candidate.get('published_at') or record.get('date')}"
                )
            continue
        title = candidate["title"] or (record.get("title") or "").strip()
        if not title:
            if run_log is not None:
                run_log.write(f"scrape drop url={candidate['url']} reason=empty_title")
            continue
        if run_log is not None:
            run_log.write(
                f"scrape keep url={candidate['url']} chars={len(text)} status={record.get('status')}"
            )
        kept.append(
            {
                **candidate,
                "title": title,
                "published_at": to_iso(published),
                "scraped_text": text,
                "scraped_at": scraped_at,
            }
        )

    counts = dict(state.get("counts") or {})
    counts["scraped"] = len(kept)
    if run_log is not None:
        run_log.write(f"scrape_bodies finished kept={len(kept)} of={len(candidates)}")
    logger.info("scrape_bodies kept=%s", len(kept))
    return {"candidates": kept, "counts": counts, "errors": errors}


def _log_scrape_record(run_log, url: str, record: dict) -> None:
    status = record.get("status") or "unknown"
    text_len = len((record.get("text") or "").strip())
    err = record.get("error")
    if err:
        run_log.write(
            f"scrape url={url} status={status} chars={text_len} note={clip_log_text(err)}"
        )
    else:
        run_log.write(f"scrape url={url} status={status} chars={text_len}")


def _scrape(url: str) -> dict:
    return scrape_one(thread_session(), url, retries=2)
