"""In-memory conversations. A new id starts empty. Idle chats expire after 30 minutes."""

from __future__ import annotations

import threading
import time
from typing import Any

from news_rag.insight.memory.state import IDLE_SEC, empty_state

_lock = threading.Lock()
_states: dict[str, dict[str, Any]] = {}
_sources: dict[str, dict[str, Any]] = {}
_turn_records: dict[str, dict[str, Any]] = {}


def _fresh(conversation_id: str) -> dict[str, Any]:
    current = _states.get(conversation_id)
    if not current:
        return empty_state(conversation_id)
    if time.time() - float(current.get("updated_at") or 0) > IDLE_SEC:
        _states.pop(conversation_id, None)
        return empty_state(conversation_id)
    return current


def get_memory(conversation_id: str) -> dict[str, Any] | None:
    key = str(conversation_id or "").strip()
    if not key:
        return None
    with _lock:
        current = _fresh(key)
        if int(current.get("turn_count") or 0) > 0:
            return current
        return None


def get_or_create(conversation_id: str) -> dict[str, Any]:
    key = str(conversation_id or "").strip()
    with _lock:
        current = _fresh(key)
        _states[key] = current
        return current


def save_state(state: dict[str, Any]) -> None:
    key = str(state.get("conversation_id") or "").strip()
    if not key:
        return
    state["updated_at"] = time.time()
    with _lock:
        _states[key] = state


def reset_memory(conversation_id: str) -> None:
    key = str(conversation_id or "").strip()
    with _lock:
        _states.pop(key, None)


def save_sources(query_id: str, articles: list[dict[str, Any]], *, conversation_id: str) -> None:
    key = str(query_id or "").strip()
    if not key:
        return
    with _lock:
        _sources[key] = {
            "conversation_id": conversation_id,
            "articles": articles,
            "stored_at": time.time(),
        }


def save_turn_record(query_id: str, record: dict[str, Any]) -> None:
    key = str(query_id or "").strip()
    if not key:
        return
    row = dict(record)
    row["stored_at"] = time.time()
    with _lock:
        _turn_records[key] = row


def turn_record(query_id: str) -> dict[str, Any] | None:
    key = str(query_id or "").strip()
    with _lock:
        row = _turn_records.get(key)
        if not row:
            return None
        if time.time() - float(row.get("stored_at") or 0) > IDLE_SEC:
            _turn_records.pop(key, None)
            return None
        return dict(row)


def sources_for(query_id: str) -> list[dict[str, Any]]:
    key = str(query_id or "").strip()
    with _lock:
        row = _sources.get(key) or {}
        if row and time.time() - float(row.get("stored_at") or 0) > IDLE_SEC:
            _sources.pop(key, None)
            return []
        articles = row.get("articles") or []
        return list(articles) if isinstance(articles, list) else []
