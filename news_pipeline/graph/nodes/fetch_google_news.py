"""Fetch Google News for each holding and sector. One failure does not stop the run."""

from __future__ import annotations

import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from news_pipeline.graph.state import PipelineState
from news_pipeline.run_log import clip_log_text, get_run_logger
from news_pipeline.services import get_settings
from news_pipeline.sources.google_news import fetch_entity_items
from news_pipeline.sources.macro_news import fetch_macro_items

logger = logging.getLogger(__name__)


def fetch_google_news(state: PipelineState) -> dict:
    settings = get_settings()
    entities = state.get("entities") or []
    errors = list(state.get("errors") or [])
    hits: list[dict] = []
    fetch_failures: list[tuple[str, str]] = []
    total = len(entities)
    done = 0

    run_log = get_run_logger()
    if run_log is not None:
        run_log.write(f"fetch_google_news started entities={total} workers={settings.fetch_workers}")

    with ThreadPoolExecutor(max_workers=settings.fetch_workers) as pool:
        futures = {pool.submit(fetch_entity_items, entity, settings): entity for entity in entities}
        for future in as_completed(futures):
            entity = futures[future]
            done += 1
            try:
                items = future.result()
                hits.extend(items)
                if run_log is not None:
                    run_log.write(
                        f"fetch entity={entity['name']} type={entity['type']} ok items={len(items)}"
                    )
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

    macro_items: list[dict] = []
    try:
        macro_items = fetch_macro_items(settings)
        hits.extend(macro_items)
        if run_log is not None:
            run_log.write(f"fetch macro_news ok items={len(macro_items)} query={settings.macro_news_query!r}")
    except Exception as exc:
        message = str(exc)
        if run_log is not None:
            run_log.write(f"fetch macro_news FAIL error={clip_log_text(message)}")
        errors.append({"stage": "fetch_google_news", "error": message, "query": "macro_news"})

    if run_log is not None:
        run_log.write(
            f"fetch_google_news finished items={len(hits)} macro_items={len(macro_items)} "
            f"entity_failures={len(fetch_failures)}"
        )

    errors.extend(_compact_fetch_errors(fetch_failures))

    counts = dict(state.get("counts") or {})
    counts["google_items"] = len(hits)
    counts["macro_items"] = len(macro_items)
    logger.info("fetch_google_news items=%s errors=%s", len(hits), len(errors))
    return {"candidates": hits, "counts": counts, "errors": errors}


def _compact_fetch_errors(failures: list[tuple[str, str]]) -> list[dict]:
    if not failures:
        return []
    by_message: dict[str, list[str]] = defaultdict(list)
    for name, message in failures:
        key = message.split("\n", maxsplit=1)[0].strip()
        by_message[key].append(name)
    compact: list[dict] = []
    for message, names in by_message.items():
        entry: dict = {
            "stage": "fetch_google_news",
            "error": message,
            "count": len(names),
        }
        if len(names) <= 8:
            entry["entities"] = names
        else:
            entry["entities_sample"] = names[:8]
        compact.append(entry)
    return compact
