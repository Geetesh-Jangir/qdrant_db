"""LLM-facing chat transcript and legacy pointer view for internal tooling."""

from __future__ import annotations

import json
from typing import Any

from news_rag.insight.memory.state import ENTITY_TTL_TURNS, MAX_CHAT_TURNS
from news_rag.insight.greeting import ASSISTANT_MAIN_MEMORY


def _chat_turn_rows(state: dict[str, Any] | None) -> list[dict[str, str]]:
    if not state:
        return []
    rows: list[dict[str, str]] = []
    for row in state.get("chat_turns") or []:
        if not isinstance(row, dict):
            continue
        user = str(row.get("user") or "").strip()
        assistant = str(row.get("assistant") or "").strip()
        if not user and not assistant:
            continue
        rows.append({"user": user, "assistant": assistant})
    return rows[-MAX_CHAT_TURNS:]


def chat_history_view(state: dict[str, Any] | None) -> dict[str, Any]:
    """Prior turns sent to the planner and composer (user + assistant text only)."""
    return {"turns": _chat_turn_rows(state)}


def format_chat_history_block(state: dict[str, Any] | None) -> str:
    turns = _chat_turn_rows(state)
    if not turns:
        return ""
    lines = [f"Conversation history (oldest first, at most {MAX_CHAT_TURNS} turns):"]
    for row in turns:
        lines.append(f"User: {row['user']}")
        lines.append(f"Assistant: {row['assistant']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def memory_json_tokens(payload: dict[str, Any] | None) -> int:
    """Estimated tokens for the chat history payload. Empty is zero."""
    if not payload or not isinstance(payload, dict):
        return 0
    turns = payload.get("turns")
    if not isinstance(turns, list) or not turns:
        return 0
    fake = {
        "chat_turns": [
            {"user": t.get("user"), "assistant": t.get("assistant")}
            for t in turns
            if isinstance(t, dict)
        ]
    }
    block = format_chat_history_block(fake)
    return max(1, (len(block) + 3) // 4) if block else 0


def format_chat_history_from_view(view: dict[str, Any] | None) -> str:
    if not view or not isinstance(view, dict):
        return ""
    turns = view.get("turns")
    if not isinstance(turns, list) or not turns:
        return ""
    fake: dict[str, Any] = {
        "chat_turns": [
            {"user": t.get("user"), "assistant": t.get("assistant")}
            for t in turns
            if isinstance(t, dict)
        ]
    }
    return format_chat_history_block(fake)


def prompt_view(state: dict[str, Any] | None) -> dict[str, Any]:
    identity = {"assistant_main_memory": dict(ASSISTANT_MAIN_MEMORY)}
    if not state or not state.get("turn_count"):
        return identity
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
            "facts": list(row.get("fact_names") or row.get("facts") or []),
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
    from news_rag.insight.memory.fund_context import memory_funds_for_category

    category_funds: list[dict[str, Any]] = []
    seen_cats: set[str] = set()
    for row in subjects + [{"name": r.get("name")} for r in stack]:
        name = str((row or {}).get("name") or "").strip()
        if not name:
            continue
        from news_rag.fund_rating_categories import match_scheme_category

        match = match_scheme_category(name)
        cat = str(match.category or "").strip().lower() if match else ""
        if not cat or cat in seen_cats:
            continue
        seen_cats.add(cat)
        funds = memory_funds_for_category(state, cat)
        if funds:
            category_funds.append({"category": cat, "fund_names": funds})

    cursor_filters = (listed or {}).get("filters") if isinstance(listed, dict) else {}
    list_note = ""
    if isinstance(cursor_filters, dict) and cursor_filters.get("pick_alternate"):
        focus = str(cursor_filters.get("focus_question") or "").strip()
        if focus and listed and listed.get("rows"):
            list_note = (
                f"Latest screen in '{focus}' (alternate pick): "
                + ", ".join(str(r.get("name") or "") for r in listed["rows"])
            )

    out: dict[str, Any] = {
        **identity,
        "turn": state.get("turn_count"),
        "entity_ttl_turns": ENTITY_TTL_TURNS,
        "frame": {
            "subject_kind": frame.get("subject_kind") or "none",
            "subjects": subjects,
            "period": frame.get("period") or "",
            "last_intent": frame.get("last_intent") or "",
            "shown_facts": list(frame.get("shown_facts") or []),
            "shown_facts_note": (
                "ALREADY FETCHED: each tool:module:window entry is data already in hand. Do not fetch it again. "
                "A different window, module or section is NOT fetched yet: call the tool for it."
            ),
            "depth": frame.get("depth") or "short",
            "open_part": frame.get("open_part") or {"answered": [], "pending": []},
            "news_topic": news_view,
            "last_fund_focus": str(frame.get("last_fund_focus") or "").strip(),
            "recent_fund_focus": [
                str(x).strip()
                for x in (frame.get("recent_fund_focus") or [])
                if str(x).strip()
            ][:4],
        },
        "entity_stack": stack,
        "list_cursor": listed,
        "recent": [row.get("gist") for row in (state.get("gists") or []) if isinstance(row, dict)],
    }
    if category_funds:
        out["category_funds_in_chat"] = category_funds
        out["memory_hint"] = (
            "frame.subjects may be from an older cross-category compare. "
            f"Catalog entities in entity_stack and list_cursor older than {ENTITY_TTL_TURNS} turns are dropped automatically. "
            "For 'both funds in [category]', use category_funds_in_chat for that slug "
            "(includes list_cursor). Do not pair conservative hybrid with aggressive hybrid. "
            "For 'compare these/those equity funds', use the latest pure-equity category pair "
            "in category_funds_in_chat (e.g. large cap), not hybrid funds or a single alternate pick."
        )
    if list_note:
        out["list_cursor_note"] = list_note

    holdings_chat = state.get("holdings_in_chat") if isinstance(state.get("holdings_in_chat"), list) else []
    if holdings_chat:
        out["holdings_in_chat"] = holdings_chat
        frame_inv = frame.get("investor_subjects") if isinstance(frame.get("investor_subjects"), list) else []
        if frame_inv:
            out["frame"]["investor_subjects"] = frame_inv
        hint = out.get("memory_hint") or ""
        inv_hint = (
            "For the user's own book: use holdings_in_chat and frame.investor_subjects for "
            "'that fund', 'my second fund', 'my contra fund', 'my small cap fund', or similar — "
            "match the category word to holdings_in_chat, not list_cursor or category_funds_in_chat. "
            "portfolio_scope investor + get_investor_portfolio. "
            "Do not use category_funds_in_chat for 'my fund' unless they mean a catalog compare."
        )
        out["memory_hint"] = f"{hint} {inv_hint}".strip()

    return out
