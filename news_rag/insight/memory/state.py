"""Compact session state. Pointers only. Numbers stay in the tool cache."""

from __future__ import annotations

import time
from typing import Any

IDLE_SEC = 30 * 60
MAX_STACK = 5
MAX_GISTS = 2
MAX_TURNS = 12


def _subject(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    return {
        "id": str(raw.get("id") or "").strip(),
        "name": str(raw.get("name") or "").strip(),
        "plan": str(raw.get("plan") or "").strip(),
        "role": str(raw.get("role") or "primary").strip() or "primary",
    }


def empty_frame() -> dict[str, Any]:
    return {
        "subject_kind": "none",
        "subjects": [],
        "period": "",
        "last_intent": "",
        "shown_facts": [],
        "depth": "short",
        "open_part": {"answered": [], "pending": []},
        "news_topic": None,
        "last_call": None,
    }


def empty_state(conversation_id: str) -> dict[str, Any]:
    now = time.time()
    return {
        "conversation_id": conversation_id,
        "turn_count": 0,
        "frame": empty_frame(),
        "entity_stack": [],
        "list_cursor": None,
        "gists": [],
        "updated_at": now,
        "cache_events": [],
    }


def stack_entry(ref: int, state: dict[str, Any]) -> dict[str, Any] | None:
    """1 is the newest fund. The prompt numbers the stack the same way."""
    rows = list(state.get("entity_stack") or [])
    if ref < 1 or ref > len(rows):
        return None
    row = rows[ref - 1]
    return row if isinstance(row, dict) else None


def push_fund(state: dict[str, Any], subject: dict[str, Any], *, period: str, facts: list[str], turn: int) -> None:
    name = str(subject.get("name") or "").strip()
    if not name:
        return
    row = {
        "id": str(subject.get("id") or "").strip(),
        "name": name,
        "plan": str(subject.get("plan") or "").strip(),
        "period": period,
        "fact_names": list(facts),
        "turn": turn,
    }
    stack = [item for item in (state.get("entity_stack") or []) if str(item.get("name") or "") != name]
    stack.insert(0, row)
    state["entity_stack"] = stack[:MAX_STACK]


def add_gist(state: dict[str, Any], text: str, turn: int) -> None:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return
    gists = list(state.get("gists") or [])
    gists.append({"turn": turn, "gist": cleaned})
    state["gists"] = gists[-MAX_GISTS:]
