"""Persistent Google vs publisher failure records with retry counts."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from news_pipeline.config import Settings
from news_pipeline.run_context import get_run_context

logger = logging.getLogger(__name__)

_GOOGLE = "google"
_SOURCE = "source"
_MAX_ATTEMPTS = 3

_google_items: dict[str, dict] = {}
_source_items: dict[str, dict] = {}
_day_google: list[dict] = []
_day_source: list[dict] = []
_loaded = False


def reset_run_buffers() -> None:
    global _day_google, _day_source
    _day_google = []
    _day_source = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _failures_dir(settings: Settings) -> Path:
    path = settings.path(settings.news_failures_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_file(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return {}
    by_url: dict[str, dict] = {}
    for row in items:
        if isinstance(row, dict) and row.get("url"):
            by_url[str(row["url"])] = row
    return by_url


def ensure_loaded(settings: Settings) -> None:
    global _loaded, _google_items, _source_items
    if _loaded:
        return
    root = _failures_dir(settings)
    _google_items = _load_file(root / "google.json")
    _source_items = _load_file(root / "source.json")
    _loaded = True


def _atomic_write(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def flush(settings: Settings) -> None:
    ensure_loaded(settings)
    root = _failures_dir(settings)
    _atomic_write(root / "google.json", {"items": list(_google_items.values())})
    _atomic_write(root / "source.json", {"items": list(_source_items.values())})


def is_google_exhausted(wrapper_url: str, settings: Settings) -> bool:
    ensure_loaded(settings)
    row = _google_items.get(wrapper_url)
    return bool(row and row.get("exhausted"))


def is_source_exhausted(publisher_url: str, settings: Settings) -> bool:
    ensure_loaded(settings)
    row = _source_items.get(publisher_url)
    return bool(row and row.get("exhausted"))


def _merge_entities(existing: list, new: list[dict]) -> list[dict]:
    by_name = {e["name"]: e for e in existing if isinstance(e, dict) and e.get("name")}
    for ent in new:
        if ent.get("name"):
            by_name[ent["name"]] = ent
    return list(by_name.values())


def record_google_failure(
    settings: Settings,
    *,
    url: str,
    kind: str,
    error: str,
    title: str = "",
    snippet: str = "",
    published_at: str | None = None,
    source_name: str = "",
    entities: list[dict] | None = None,
    entity_query: str = "",
) -> dict:
    ensure_loaded(settings)
    ctx = get_run_context()
    entities = entities or []
    now = _now_iso()
    row = _google_items.get(url)
    if row is None:
        row = {
            "url": url,
            "kind": kind,
            "title": title,
            "snippet": snippet,
            "published_at": published_at,
            "source_name": source_name,
            "entity_query": entity_query,
            "entities": entities,
            "attempts": 1,
            "exhausted": False,
            "pending": True,
            "first_failed_at": now,
            "last_failed_at": now,
            "last_run_id": ctx.run_id,
            "last_error": error,
            "news_date_range": ctx.news_date_range,
            "calendar_day": ctx.calendar_day,
        }
        _google_items[url] = row
    else:
        if row.get("attempts", 0) < _MAX_ATTEMPTS:
            row["attempts"] = int(row.get("attempts") or 0) + 1
        row["last_failed_at"] = now
        row["last_run_id"] = ctx.run_id
        row["last_error"] = error
        row["calendar_day"] = ctx.calendar_day
        row["entities"] = _merge_entities(row.get("entities") or [], entities)
        if title:
            row["title"] = title
    if int(row.get("attempts") or 0) >= _MAX_ATTEMPTS:
        row["exhausted"] = True
    _day_google.append(deepcopy(row))
    return row


def record_source_failure(
    settings: Settings,
    *,
    url: str,
    drop_reason: str,
    error: str = "",
    retriable: bool,
    title: str = "",
    snippet: str = "",
    published_at: str | None = None,
    source: str = "",
    entities: list[dict] | None = None,
) -> dict:
    ensure_loaded(settings)
    ctx = get_run_context()
    entities = entities or []
    now = _now_iso()
    row = _source_items.get(url)
    if row is None:
        attempts = 1 if retriable else 1
        exhausted = retriable and attempts >= _MAX_ATTEMPTS
        row = {
            "url": url,
            "title": title,
            "snippet": snippet,
            "published_at": published_at,
            "source": source,
            "entities": entities,
            "drop_reason": drop_reason,
            "retriable": retriable,
            "attempts": attempts,
            "exhausted": exhausted,
            "pending": retriable,
            "first_failed_at": now,
            "last_failed_at": now,
            "last_run_id": ctx.run_id,
            "last_error": error or drop_reason,
            "news_date_range": ctx.news_date_range,
            "calendar_day": ctx.calendar_day,
        }
        _source_items[url] = row
    else:
        if retriable and int(row.get("attempts") or 0) < _MAX_ATTEMPTS:
            row["attempts"] = int(row.get("attempts") or 0) + 1
        row["last_failed_at"] = now
        row["last_run_id"] = ctx.run_id
        row["last_error"] = error or drop_reason
        row["drop_reason"] = drop_reason
        row["calendar_day"] = ctx.calendar_day
        row["entities"] = _merge_entities(row.get("entities") or [], entities)
        if retriable and int(row.get("attempts") or 0) >= _MAX_ATTEMPTS:
            row["exhausted"] = True
    _day_source.append(deepcopy(row))
    return row


def mark_source_resolved(settings: Settings, url: str) -> None:
    ensure_loaded(settings)
    row = _source_items.get(url)
    if row is None:
        return
    row["pending"] = False
    row["exhausted"] = False
    row["resolved_at"] = _now_iso()


def day_failure_slices_for_run() -> tuple[list[dict], list[dict]]:
    day = get_run_context().calendar_day
    google_slice = [r for r in _day_google if r.get("calendar_day") == day]
    source_slice = [r for r in _day_source if r.get("calendar_day") == day]
    return google_slice, source_slice


def write_day_slices(settings: Settings, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    google_slice, source_slice = day_failure_slices_for_run()
    (out_dir / "failed_google.json").write_text(
        json.dumps({"items": google_slice}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "failed_source.json").write_text(
        json.dumps({"items": source_slice}, indent=2),
        encoding="utf-8",
    )
