"""Fetch Google News for each holding and sector. One failure does not stop the run."""

from __future__ import annotations

import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from lib.google_guard import GoogleBlockedError
from news_pipeline.error_summary import fetch_window_fields
from news_pipeline.graph.state import PipelineState
from news_pipeline.news_dates import describe_fetch_window
from news_pipeline.run_log import clip_log_text, get_run_logger
from news_pipeline.services import get_settings
from news_pipeline.sources.google_news import fetch_entity_items

logger = logging.getLogger(__name__)


def fetch_google_news(state: PipelineState) -> dict:
    settings = get_settings()
    entities = state.get("entities") or []
    errors = list(state.get("errors") or [])
    hits: list[dict] = []
    fetch_failures: list[tuple[str, str]] = []
    google_blocked = False
    total = len(entities)
    done = 0

    run_log = get_run_logger()
    if run_log is not None:
        run_log.write(
            f"fetch_google_news started entities={total} workers={settings.fetch_workers} "
            f"{describe_fetch_window(settings)}"
        )

    with ThreadPoolExecutor(max_workers=settings.fetch_workers) as pool:
        futures = {pool.submit(fetch_entity_items, entity, settings): entity for entity in entities}
        for future in as_completed(futures):
            if google_blocked:
                future.cancel()
                continue
            entity = futures[future]
            done += 1
            try:
                items = future.result()
                hits.extend(items)
                if run_log is not None:
                    run_log.write(
                        f"fetch entity={entity['name']} type={entity['type']} ok items={len(items)}"
                    )
            except GoogleBlockedError as exc:
                google_blocked = True
                message = str(exc)
                fetch_failures.append((entity["name"], message))
                if run_log is not None:
                    run_log.write(f"fetch_google_news google_blocked=true error={clip_log_text(message)}")
                for pending in futures:
                    pending.cancel()
            except Exception as exc:
                message = str(exc)
                fetch_failures.append((entity["name"], message))
                if run_log is not None:
                    run_log.write(
                        f"fetch entity={entity['name']} type={entity['type']} FAIL "
                        f"error={clip_log_text(message)}"
                    )
            if run_log is not None and (done == total or done % 5 == 0):
                run_log.write(
                    f"fetch_google_news progress done={done}/{total} "
                    f"items_so_far={len(hits)} failures={len(fetch_failures)}"
                )

    if run_log is not None:
        run_log.write(
            f"fetch_google_news finished items={len(hits)} entity_failures={len(fetch_failures)} "
            f"google_blocked={google_blocked}"
        )

    errors.extend(_compact_fetch_errors(fetch_failures, settings))
    if google_blocked:
        window = fetch_window_fields(settings)
        failed_names = [name for name, _ in fetch_failures]
        errors.append(
            {
                "source": "google_news",
                "stage": "fetch_google_news",
                "error": "google_blocked",
                "google_blocked": True,
                "entities": failed_names,
                "dates": window["dates"],
                "window": window["window"],
            }
        )
        if run_log is not None:
            run_log.write(
                f"ERROR SUMMARY source=google_news count={len(fetch_failures)} "
                f"entities=[{', '.join(failed_names)}] dates={window['dates'] or 'relative_window'}"
            )

    counts = dict(state.get("counts") or {})
    counts["google_items"] = len(hits)
    if google_blocked:
        counts["google_blocked"] = True
    logger.info("fetch_google_news items=%s errors=%s blocked=%s", len(hits), len(errors), google_blocked)
    return {"candidates": hits, "counts": counts, "errors": errors}


def _compact_fetch_errors(failures: list[tuple[str, str]], settings) -> list[dict]:
    if not failures:
        return []
    window = fetch_window_fields(settings)
    by_message: dict[str, list[str]] = defaultdict(list)
    for name, message in failures:
        key = message.split("\n", maxsplit=1)[0].strip()
        by_message[key].append(name)
    compact: list[dict] = []
    for message, names in by_message.items():
        compact.append(
            {
                "source": "google_news",
                "stage": "fetch_google_news",
                "error": message,
                "count": len(names),
                "entities": names,
                "dates": window["dates"],
                "window": window["window"],
            }
        )
    return compact
