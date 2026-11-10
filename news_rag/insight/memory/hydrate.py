"""Rebuild in-process memory from client chat when the server process restarted."""

from __future__ import annotations

from typing import Any

from news_rag.insight.memory.state import MAX_CHAT_TURNS, append_chat_turn
from news_rag.insight.memory.store import get_memory, get_or_create, save_state


def normalize_prior_turns(turns: list[Any] | None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in turns or []:
        if not isinstance(row, dict):
            continue
        user = str(row.get("user") or row.get("question") or "").strip()
        assistant = str(
            row.get("assistant") or row.get("answer") or row.get("insight") or ""
        ).strip()
        if not user and not assistant:
            continue
        if not assistant:
            continue
        out.append({"user": user, "assistant": assistant})
    return out[-MAX_CHAT_TURNS:]


def hydrate_memory_from_prior_turns(
    conversation_id: str,
    prior_turns: list[Any] | None,
) -> tuple[dict[str, Any] | None, bool]:
    """If server memory is empty, seed chat turns from the UI. Do not guess a fund."""
    rows = normalize_prior_turns(prior_turns)
    key = str(conversation_id or "").strip()
    if not key or not rows:
        return None, False
    if get_memory(key):
        return get_memory(key), False

    state = get_or_create(key)
    turn = 0
    for row in rows:
        turn += 1
        append_chat_turn(
            state,
            user=row["user"],
            assistant=row["assistant"],
            turn=turn,
        )
    state["turn_count"] = turn
    save_state(state)
    return state, True
