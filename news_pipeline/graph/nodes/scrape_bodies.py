"""Scrape article bodies."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from lib.fetch import thread_session
from news_pipeline.entity_funnel import get_entity_funnel
from news_pipeline.failure_ledger import is_source_exhausted, record_source_failure
from news_pipeline.graph.state import PipelineState
from news_pipeline.news_dates import publish_time_for_scrape
from news_pipeline.publisher_stats import get_publisher_stats
from news_pipeline.run_log import clip_log_text, get_run_logger
from news_pipeline.scrape.domain_gap import wait_for_domain
from news_pipeline.scrape.engine import scrape_one
from news_pipeline.services import get_settings
from news_pipeline.textutil import parse_time, to_iso, utc_now

logger = logging.getLogger(__name__)


def scrape_bodies(state: PipelineState) -> dict:
    settings = get_settings()
    candidates = state.get("candidates") or []
    errors = list(state.get("errors") or [])
    now = utc_now()
    scraped_at = to_iso(now)
    funnel = get_entity_funnel()
    stats = get_publisher_stats()

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
        futures = {pool.submit(_scrape, row["url"], settings): row["url"] for row in candidates}
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
        url = candidate["url"]
        source = candidate.get("source") or ""
        entities = _entity_refs(candidate)

        def _drop(reason: str, detail: str = "", retriable: bool = False) -> None:
            for name, etype in entities:
                funnel.bump_scrape_drop(name, etype, reason)
            stats.record_scrape_error(source, url, reason)
            record_source_failure(
                settings,
                url=url,
                drop_reason=reason,
                error=detail or reason,
                retriable=retriable,
                title=candidate.get("title") or "",
                snippet=candidate.get("snippet") or "",
                published_at=candidate.get("published_at"),
                source=source,
                entities=[{"name": n, "type": t} for n, t in entities],
            )

        if is_source_exhausted(url, settings):
            if run_log is not None:
                run_log.write(f"scrape drop url={url} reason=ledger_exhausted")
            for name, etype in entities:
                funnel.bump_scrape_drop(name, etype, "ledger_exhausted")
            stats.record_scrape_error(source, url, "ledger_exhausted")
            continue

        record = results.get(url)
        if not isinstance(record, dict):
            if run_log is not None:
                run_log.write(f"scrape drop url={url} reason=no_record")
            _drop("no_record", retriable=True)
            continue
        if record["status"] in ("fetch_failed", "resolve_failed"):
            if run_log is not None:
                err = clip_log_text(record.get("error") or record["status"])
                run_log.write(
                    f"scrape drop url={url} reason={record['status']} detail={err}"
                )
            _drop(record["status"], detail=record.get("error") or "", retriable=True)
            continue
        text = (record.get("text") or "").strip()

        if len(text) < settings.min_body_chars:
            snippet = (candidate.get("snippet") or "").strip()
            if snippet:
                text = f"{candidate.get('title') or ''}. {snippet}"
            else:
                text = candidate.get("title") or ""

        rss_published = parse_time(candidate.get("published_at"))
        page_published = parse_time(record.get("date"))
        published = publish_time_for_scrape(rss_published, page_published, settings, now)
        if published is None:
            if run_log is not None:
                run_log.write(
                    f"scrape drop url={url} reason=outside_news_window "
                    f"published={candidate.get('published_at') or record.get('date')}"
                )
            _drop("outside_news_window", retriable=False)
            continue
        title = candidate["title"] or (record.get("title") or "").strip()
        if not title:
            if run_log is not None:
                run_log.write(f"scrape drop url={url} reason=empty_title")
            _drop("empty_title", retriable=False)
            continue
        if run_log is not None:
            run_log.write(
                f"scrape keep url={url} chars={len(text)} status={record.get('status')}"
            )
        stats.record_scraped(source, url)
        for name, etype in entities:
            funnel.bump(name, etype, "scraped")
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


def _entity_refs(candidate: dict) -> list[tuple[str, str]]:
    refs = []
    for match in candidate.get("matches") or []:
        if match.get("name"):
            refs.append((match["name"], match.get("type") or ""))
    if not refs and candidate.get("entity_name"):
        refs.append((candidate["entity_name"], candidate.get("entity_type") or ""))
    return refs


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


def _scrape(url: str, settings) -> dict:
    wait_for_domain(url, settings.scrape_domain_gap_sec)
    return scrape_one(thread_session(), url, retries=2)
