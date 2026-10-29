"""Apply the planner's pointers, then record what a successful tool actually used."""

from __future__ import annotations

from typing import Any

from news_rag.insight.memory.evidence import drop_old_turns
from news_rag.insight.memory.state import add_gist, empty_frame, push_fund
from news_rag.insight.memory.store import get_or_create, save_state

_FUND_TOOLS = {"get_fund_data", "get_portfolio_data", "compare_funds"}


def apply_planner_refs(memory: dict[str, Any] | None, plan: Any) -> None:
    """Fill funds from a stack or list ref the planner already named."""
    if memory is None or plan is None:
        return
    funds = list(plan.funds or [])
    for ref in list(getattr(plan, "stack_refs", None) or []):
        try:
            index = int(ref) - 1
        except (TypeError, ValueError):
            continue
        stack = list(memory.get("entity_stack") or [])
        if index < 0 or index >= len(stack):
            continue
        name = str(stack[index].get("name") or "").strip()
        if name and name not in funds:
            funds.append(name)
    cursor = memory.get("list_cursor") if isinstance(memory.get("list_cursor"), dict) else None
    rows = list((cursor or {}).get("rows") or [])
    for ordinal in list(getattr(plan, "list_ordinals", None) or []):
        try:
            index = int(ordinal) - 1
        except (TypeError, ValueError):
            continue
        if index < 0 or index >= len(rows):
            continue
        name = str(rows[index].get("name") or "").strip()
        if name and name not in funds:
            funds.append(name)
    plan.funds = funds

    depth = str(getattr(plan, "answer_depth", "") or "")
    frame = memory.get("frame") if isinstance(memory.get("frame"), dict) else {}
    last_call = frame.get("last_call") if isinstance(frame.get("last_call"), dict) else None
    if depth == "more" and not plan.tool_calls and last_call and last_call.get("tool"):
        from news_rag.insight.contracts import ToolCall

        plan.tool_calls = [
            ToolCall(tool=str(last_call["tool"]), arguments=dict(last_call.get("arguments") or {}), wave=1)
        ]
        plan.requires_compose = True
        plan.max_words = max(int(plan.max_words or 0), 220)
        note = "Explain the same facts more plainly. Do not stop at the previous sentence."
        plan.presentation_notes = f"{plan.presentation_notes} {note}".strip()
        if not funds:
            for row in frame.get("subjects") or []:
                name = str((row or {}).get("name") or "").strip()
                if name:
                    funds.append(name)
            plan.funds = funds


def _subject_from_row(row: dict[str, Any]) -> dict[str, Any]:
    data = row.get("data") if isinstance(row.get("data"), dict) else {}
    name = str(row.get("fund") or data.get("fund_name") or "").strip()
    isin = ""
    for block in data.values():
        if isinstance(block, dict) and block.get("isin"):
            isin = str(block.get("isin") or "").strip()
            break
    return {"id": isin, "name": name, "plan": "", "role": "primary"}


def _facts_from_plan(plan: Any) -> list[str]:
    facts: list[str] = []
    for call in plan.tool_calls or []:
        args = call.arguments or {}
        if call.tool == "get_fund_data":
            facts.extend(str(item) for item in (args.get("modules") or []))
            facts.extend(str(item) for item in (args.get("windows") or []))
        elif call.tool == "get_portfolio_data":
            facts.extend(str(item) for item in (args.get("sections") or []))
        elif call.tool == "search_financial_news":
            facts.append("news")
        elif call.tool:
            facts.append(call.tool)
    return list(dict.fromkeys(item for item in facts if item))


def _changed(frame: dict[str, Any], subjects: list[dict[str, Any]], period: str) -> bool:
    old_names = [str(row.get("name") or "") for row in (frame.get("subjects") or [])]
    new_names = [row["name"] for row in subjects]
    return old_names != new_names or str(frame.get("period") or "") != period


def _news_topic(plan: Any, tied_to_fund: bool) -> dict[str, Any] | None:
    for call in getattr(plan, "tool_calls", None) or []:
        if call.tool != "search_financial_news":
            continue
        args = dict(call.arguments or {})
        topics = args.get("topics")
        if isinstance(topics, list) and topics:
            phrase = ", ".join(str(item) for item in topics)
        else:
            phrase = str(args.get("scope") or "the news")
        return {
            "phrase": phrase,
            "query": phrase,
            "window_days": args.get("window_days"),
            "tied_to_fund": tied_to_fund,
        }
    return None


def commit_turn(
    conversation_id: str,
    plan: Any,
    results: list[dict[str, Any]],
    *,
    query_id: str = "",
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    del query_id, sources  # Articles are stored by the graph, not inside the frame.
    state = get_or_create(conversation_id)
    state["turn_count"] = int(state.get("turn_count") or 0) + 1
    turn = state["turn_count"]
    frame = dict(state.get("frame") or empty_frame())
    relation = str(getattr(plan, "turn_relation", "") or "")
    ok_rows = [row for row in results if row.get("ok") and isinstance(row.get("data"), dict) and row.get("data")]
    asked_tools = bool(getattr(plan, "tool_calls", None))

    if asked_tools and not ok_rows:
        frame["subjects"] = []
        frame["subject_kind"] = "none"
        frame["shown_facts"] = []
        frame["last_call"] = None
        state["frame"] = frame
        add_gist(state, "The last lookup did not return data.", turn)
        save_state(state)
        drop_old_turns(conversation_id, turn)
        return state

    subjects = []
    for row in ok_rows:
        if row.get("tool") not in _FUND_TOOLS:
            continue
        subject = _subject_from_row(row)
        if subject["name"] and subject["name"] not in [item["name"] for item in subjects]:
            subjects.append(subject)
    fund_tool_ok = any(row.get("tool") in _FUND_TOOLS for row in ok_rows)
    if fund_tool_ok and not subjects:
        for name in list(getattr(plan, "funds", None) or []):
            cleaned = str(name or "").strip()
            if cleaned:
                subjects.append({"id": "", "name": cleaned, "plan": "", "role": "primary"})

    period = str(getattr(plan, "window_label", "") or "")
    facts = _facts_from_plan(plan)
    if relation == "reset":
        for old in frame.get("subjects") or []:
            if isinstance(old, dict) and old.get("name"):
                push_fund(
                    state,
                    old,
                    period=str(frame.get("period") or ""),
                    facts=list(frame.get("shown_facts") or []),
                    turn=turn,
                )
        kept_topic = frame.get("news_topic")
        frame = empty_frame()
        frame["news_topic"] = kept_topic
    elif subjects and _changed(frame, subjects, period):
        for old in frame.get("subjects") or []:
            if isinstance(old, dict) and old.get("name"):
                push_fund(
                    state,
                    old,
                    period=str(frame.get("period") or ""),
                    facts=list(frame.get("shown_facts") or []),
                    turn=turn,
                )
        frame["shown_facts"] = []

    if subjects:
        frame["subjects"] = subjects
        frame["subject_kind"] = "comparison" if len(subjects) > 1 else "single_fund"
        for subject in subjects:
            push_fund(state, subject, period=period, facts=facts, turn=turn)
    elif relation == "reset":
        frame["subjects"] = []
        frame["subject_kind"] = "none"
    elif not asked_tools:
        frame["subject_kind"] = frame.get("subject_kind") or "definition"

    if subjects or asked_tools:
        frame["period"] = period
        frame["shown_facts"] = facts
    frame["last_intent"] = str(getattr(plan, "intent", "") or frame.get("last_intent") or "")
    frame["depth"] = str(getattr(plan, "answer_depth", "") or "short")
    calls = list(getattr(plan, "tool_calls", None) or [])
    if calls and ok_rows:
        first = calls[0]
        frame["last_call"] = {"tool": first.tool, "arguments": dict(first.arguments or {})}

    topic = _news_topic(plan, tied_to_fund=bool(frame.get("subjects")))
    if topic and any(row.get("tool") == "search_financial_news" for row in ok_rows):
        frame["news_topic"] = topic

    for row in ok_rows:
        if row.get("tool") != "screen_funds_by_exposure":
            continue
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        listed = []
        for item in (data.get("rankings") or data.get("funds") or [])[:20]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("fund_name") or item.get("name") or "").strip()
            if name:
                listed.append({"name": name, "id": str(item.get("isin") or "")})
        screen_args = {}
        for call in calls:
            if call.tool == "screen_funds_by_exposure":
                screen_args = dict(call.arguments or {})
        if listed:
            state["list_cursor"] = {"rows": listed, "filters": screen_args, "turn": turn}

    named = subjects or [row for row in (frame.get("subjects") or []) if isinstance(row, dict) and row.get("name")]
    names = ", ".join(str(row.get("name") or "") for row in named) or "no fund"
    fact_text = ", ".join(frame.get("shown_facts") or []) or "a general answer"
    add_gist(state, f"{names}; {frame.get('period') or 'no period'}; {fact_text}", turn)
    state["frame"] = frame
    save_state(state)
    drop_old_turns(conversation_id, turn)
    return state
