"""What the planner and the composer are allowed to see. No cached numbers."""

from __future__ import annotations

import json
from typing import Any


def memory_json_tokens(payload: dict[str, Any] | None) -> int:
    """Estimated tokens for the memory JSON only. Empty memory is zero.

    This is not the API's input-token total. It is len(json) / 4, the usual
    stand-in when the provider does not count one field on its own.
    """
    if not payload:
        return 0
    text = json.dumps(payload, ensure_ascii=False)
    return max(1, (len(text) + 3) // 4)


def prompt_view(state: dict[str, Any] | None) -> dict[str, Any]:
    if not state or not state.get("turn_count"):
        return {}
    frame = state.get("frame") if isinstance(state.get("frame"), dict) else {}
    subjects = []
    for row in frame.get("subjects") or []:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        subjects.append({
            "id": row.get("id") or "",
            "name": row.get("name") or "",
            "plan": row.get("plan") or "",
            "role": row.get("role") or "primary",
        })
    stack = []
    for index, row in enumerate(state.get("entity_stack") or [], start=1):
        if not isinstance(row, dict) or not row.get("name"):
            continue
        stack.append({
            "ref": index,
            "name": row.get("name"),
            "plan": row.get("plan") or "",
            "period": row.get("period") or "",
            "facts": list(row.get("fact_names") or []),
        })
    cursor = state.get("list_cursor") if isinstance(state.get("list_cursor"), dict) else None
    listed = None
    if cursor and cursor.get("rows"):
        listed = {
            "rows": [
                {"n": index, "name": row.get("name") or ""}
                for index, row in enumerate(cursor.get("rows") or [], start=1)
                if isinstance(row, dict)
            ],
            "filters": cursor.get("filters") or {},
        }
    news = frame.get("news_topic") if isinstance(frame.get("news_topic"), dict) else None
    news_view = None
    if news and news.get("phrase"):
        news_view = {
            "phrase": news.get("phrase"),
            "window_days": news.get("window_days"),
            "tied_to_fund": bool(news.get("tied_to_fund")),
        }
    return {
        "turn": state.get("turn_count"),
        "frame": {
            "subject_kind": frame.get("subject_kind") or "none",
            "subjects": subjects,
            "period": frame.get("period") or "",
            "last_intent": frame.get("last_intent") or "",
            "shown_facts": list(frame.get("shown_facts") or []),
            "depth": frame.get("depth") or "short",
            "open_part": frame.get("open_part") or {"answered": [], "pending": []},
            "news_topic": news_view,
        },
        "entity_stack": stack,
        "list_cursor": listed,
        "recent": [row.get("gist") for row in (state.get("gists") or []) if isinstance(row, dict)],
    }
