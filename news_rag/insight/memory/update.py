"""Apply the planner's pointers, then record what a successful tool actually used."""

from __future__ import annotations

from typing import Any

from news_rag.insight.memory.evidence import drop_old_turns
from news_rag.insight.memory.state import add_gist, empty_frame, push_fund, expire_stale_entities
from news_rag.insight.memory.store import get_or_create, save_state

_FUND_TOOLS = {"get_fund_data", "get_portfolio_data", "compare_funds"}
_INVESTOR_TOOL = "get_investor_portfolio"


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
    if name:
        from news_rag.fund_search import get_fund_index

        detail, _amb, _close = get_fund_index().lookup_extracted_fund(name=name)
        isin = str((detail or {}).get("isin") or "").strip()
    return {"id": isin, "name": name, "plan": "", "role": "primary"}


def _facts_from_plan(plan: Any) -> list[str]:
    facts: list[str] = []
    for call in plan.tool_calls or []:
        args = call.arguments or {}
        if call.tool == "get_fund_data":
            modules = [str(item) for item in (args.get("modules") or [])] or ["snapshot"]
            windows = ",".join(str(item) for item in (args.get("windows") or [])) or "-"
            facts.extend(f"get_fund_data:{mod}:{windows}" for mod in modules)
            facts.extend(modules)
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
    question: str = "",
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
        expire_stale_entities(state, turn)
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
        frame["subjects_turn"] = turn
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
        frame["news_turn"] = turn

    listed: list[dict[str, str]] = []
    seen_list_names: set[str] = set()
    screen_args: dict[str, Any] = {}
    for row in ok_rows:
        if row.get("tool") != "screen_funds_by_exposure":
            continue
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        for item in (data.get("rankings") or data.get("funds") or [])[:20]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("fund_name") or item.get("name") or "").strip()
            if not name or name in seen_list_names:
                continue
            seen_list_names.add(name)
            listed.append({"name": name, "id": str(item.get("isin") or "")})
    for call in calls:
        if call.tool == "screen_funds_by_exposure" and not screen_args:
            screen_args = dict(call.arguments or {})
    if listed:
        state["list_cursor"] = {
            "rows": [{"n": index + 1, **item} for index, item in enumerate(listed)],
            "filters": screen_args,
            "turn": turn,
        }

    if (
        not subjects
        and listed
        and str(getattr(plan, "intent", "") or "") == "compare"
    ):
        for item in listed:
            subjects.append(
                {
                    "id": str(item.get("id") or ""),
                    "name": str(item.get("name") or ""),
                    "plan": "",
                    "role": "primary",
                }
            )
        frame["subjects"] = subjects
        frame["subject_kind"] = "comparison" if len(subjects) > 1 else "single_fund"
        frame["subjects_turn"] = turn
        for subject in subjects:
            push_fund(state, subject, period=period, facts=facts, turn=turn)

    investor_row = next(
        (row for row in ok_rows if row.get("tool") == _INVESTOR_TOOL and row.get("ok")),
        None,
    )
    if investor_row:
        inv_data = investor_row.get("data") if isinstance(investor_row.get("data"), dict) else {}
        holdings = inv_data.get("holdings") if isinstance(inv_data.get("holdings"), list) else []
        names_in_chat: list[str] = list(state.get("holdings_in_chat") or [])
        investor_subjects: list[dict[str, str]] = list(frame.get("investor_subjects") or [])
        for row in holdings:
            if not isinstance(row, dict):
                continue
            name = str(row.get("scheme_name") or "").strip()
            if not name:
                continue
            compact = {
                "name": name,
                "isin": str(row.get("isin") or ""),
                "category": str(row.get("scheme_category") or ""),
                "aum_inr": row.get("aum_inr"),
                "xirr_pct": row.get("xirr_pct"),
                "rs_label": str(row.get("rs_label") or ""),
            }
            existing_names = [item.get("name") if isinstance(item, dict) else item for item in names_in_chat]
            if name not in existing_names:
                names_in_chat.append(compact)
            else:
                for index, item in enumerate(list(names_in_chat)):
                    item_name = item.get("name") if isinstance(item, dict) else item
                    if item_name != name:
                        continue
                    if isinstance(item, dict):
                        if not item.get("isin") and compact["isin"]:
                            names_in_chat[index] = {**item, **{k: v for k, v in compact.items() if v not in ("", None)}}
                    else:
                        names_in_chat[index] = compact
            known = next((s for s in investor_subjects if s.get("name") == name), None)
            if known is None:
                investor_subjects.append({
                    "name": name,
                    "isin": compact["isin"],
                    "folio": str(row.get("folio_scheme") or row.get("folio_number") or ""),
                    "category": compact["category"],
                    "rs_label": compact["rs_label"],
                    "role": "primary",
                })
            elif not known.get("isin") and compact["isin"]:
                known["isin"] = compact["isin"]
                known["category"] = compact["category"] or known.get("category")
                known["rs_label"] = compact["rs_label"] or known.get("rs_label")
        if names_in_chat:
            state["holdings_in_chat"] = names_in_chat[-12:]
        if investor_subjects:
            frame["investor_subjects"] = investor_subjects[-8:]
            frame["subject_kind"] = "investor_holding" if len(investor_subjects) == 1 else "investor_portfolio"
            if len(investor_subjects) == 1:
                push_fund(
                    state,
                    {"id": investor_subjects[0].get("isin") or "", "name": investor_subjects[0]["name"], "plan": "", "role": "primary"},
                    period=period,
                    facts=facts,
                    turn=turn,
                )

    compare_row = next(
        (row for row in ok_rows if row.get("tool") == "compare_funds" and row.get("ok")),
        None,
    )
    planned_compare = [
        str(name).strip() for name in (getattr(plan, "funds", None) or []) if str(name).strip()
    ]
    if compare_row and len(planned_compare) >= 2:
        from news_rag.insight.memory.fund_context import (
            compare_payload_matches_funds,
            subjects_from_fund_names,
        )

        data = compare_row.get("data") if isinstance(compare_row.get("data"), dict) else {}
        if not compare_payload_matches_funds(planned_compare[:2], data):
            data = {}
        compare_subjects = subjects_from_fund_names(planned_compare[:2])
        if compare_subjects:
            subjects = compare_subjects
            frame["subjects"] = subjects
            frame["subject_kind"] = "comparison"
            frame["subjects_turn"] = turn
            for subject in subjects:
                push_fund(state, subject, period=period, facts=facts, turn=turn)
            state["list_cursor"] = {
                "rows": [{"n": index + 1, "name": row["name"], "id": row.get("id") or ""} for index, row in enumerate(subjects)],
                "filters": {"compare_pair": True},
                "turn": turn,
            }

    from news_rag.insight.memory.fund_context import fund_name_mentioned_in_memory, push_recent_fund_focus

    focus = str(frame.get("last_fund_focus") or "").strip()
    if question:
        mentioned = fund_name_mentioned_in_memory(question, state)
        if mentioned:
            focus = mentioned
    if len(subjects) == 1 and subjects[0].get("name"):
        focus = str(subjects[0]["name"]).strip()
    elif len(getattr(plan, "funds", None) or []) == 1:
        focus = str(plan.funds[0]).strip()
    if focus:
        push_recent_fund_focus(frame, focus)

    named = subjects or [row for row in (frame.get("subjects") or []) if isinstance(row, dict) and row.get("name")]
    names = ", ".join(str(row.get("name") or "") for row in named) or "no fund"
    fact_text = ", ".join(frame.get("shown_facts") or []) or "a general answer"
    add_gist(state, f"{names}; {frame.get('period') or 'no period'}; {fact_text}", turn)
    state["frame"] = frame
    expire_stale_entities(state, turn)
    save_state(state)
    drop_old_turns(conversation_id, turn)
    return state
