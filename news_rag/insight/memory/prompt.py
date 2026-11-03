"""What the planner and the composer are allowed to see. No cached numbers."""

from __future__ import annotations

import json
from typing import Any

from news_rag.insight.memory.state import ENTITY_TTL_TURNS


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
        "turn": state.get("turn_count"),
        "entity_ttl_turns": ENTITY_TTL_TURNS,
        "frame": {
            "subject_kind": frame.get("subject_kind") or "none",
            "subjects": subjects,
            "period": frame.get("period") or "",
            "last_intent": frame.get("last_intent") or "",
            "shown_facts": list(frame.get("shown_facts") or []),
            "shown_facts_note": "Each get_fund_data:module:windows entry is one fetched slice. A new window is not in memory until that tool runs again.",
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
