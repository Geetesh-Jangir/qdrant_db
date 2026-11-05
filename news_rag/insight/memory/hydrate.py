"""Rebuild in-process memory from client chat when the server process restarted."""

from __future__ import annotations

from typing import Any

from news_rag.insight.memory.state import MAX_CHAT_TURNS, append_chat_turn, empty_frame
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


def _infer_fund_focus_from_chat(state: dict[str, Any]) -> str:
    from news_rag.fund_search import resolve_fund_from_question

    for row in reversed(state.get("chat_turns") or []):
        if not isinstance(row, dict):
            continue
        for key in ("user", "assistant"):
            text = str(row.get(key) or "").strip()
            if not text:
                continue
            detail, ambiguous, _close = resolve_fund_from_question(text)
            if detail and not ambiguous:
                name = str(
                    detail.get("scheme_name") or detail.get("name") or detail.get("fund_name") or ""
                ).strip()
                if name:
                    return name
    return ""


def hydrate_memory_from_prior_turns(
    conversation_id: str,
    prior_turns: list[Any] | None,
) -> tuple[dict[str, Any] | None, bool]:
    """If server memory is empty, seed chat_turns (+ best-effort fund focus) from the UI."""
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
    focus = _infer_fund_focus_from_chat(state)
    if focus:
        from news_rag.insight.memory.fund_context import push_recent_fund_focus
        from news_rag.insight.memory.state import push_fund

        frame = dict(state.get("frame") or empty_frame())
        frame["subject_kind"] = "single"
        frame["subjects"] = [{"id": "", "name": focus, "plan": "", "role": "primary"}]
        frame["last_fund_focus"] = focus
        frame["last_fund_focus_turn"] = turn
        push_recent_fund_focus(frame, focus, turn=turn)
        push_fund(state, {"name": focus}, period="", facts=[], turn=turn)
        state["frame"] = frame
    save_state(state)
    return state, True
