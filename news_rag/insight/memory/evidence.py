"""Per-conversation tool slices. A new period is stored beside the old one."""

from __future__ import annotations

import threading
import time
from typing import Any

from news_rag.insight.memory.state import IDLE_SEC, MAX_TURNS

_lock = threading.Lock()
# conversation -> slot key -> {data, turn, stored_at, label}
_slices: dict[str, dict[str, dict[str, Any]]] = {}
_events: dict[str, list[dict[str, str]]] = {}


def slice_slot(tool: str, args: dict[str, Any] | None) -> str:
    """The exact slot the planner asked for. 1M and 1Y are different keys."""
    args = args or {}
    if tool == "get_fund_data":
        modules = ",".join(str(item) for item in (args.get("modules") or []))
        windows = ",".join(str(item) for item in (args.get("windows") or []))
        periods = ",".join(str(item) for item in (args.get("periods") or []))
        from news_rag.fund_risk import rating_needs_pillars

        pillars = "1" if rating_needs_pillars(args) else "0"
        return f"fund|{modules}|w={windows}|p={periods}|pillars={pillars}"
    if tool == "get_portfolio_data":
        sections = ",".join(str(item) for item in (args.get("sections") or []))
        return f"portfolio|{sections}|n={args.get('top_n')}"
    if tool == "search_financial_news":
        topics = ",".join(str(item) for item in (args.get("topics") or []))
        return f"news|{args.get('scope')}|d={args.get('window_days')}|t={topics}"
    if tool == "screen_funds_by_exposure":
        question = " ".join(str(args.get("focus_question") or "").lower().split())[:180]
        return (
            f"screen|{question or args.get('sector') or ''}|"
            f"w={args.get('return_window')}|n={args.get('top_n')}|"
            f"rating={bool(args.get('rating_screen'))}|random={bool(args.get('random_sample'))}|"
            f"compare_pair={bool(args.get('compare_pair'))}|alternate={bool(args.get('pick_alternate'))}"
        )
    if tool == "compare_funds":
        return f"compare|mode={str(args.get('mode') or 'both').lower()}"
    if tool == "get_investor_portfolio":
        modules = ",".join(str(item) for item in (args.get("modules") or []))
        scheme = str(args.get("scheme_filter") or "").strip().lower()[:80]
        fields = str(args.get("holdings_fields") or "minimal").lower()
        return f"investor|{modules}|scheme={scheme}|hf={fields}"
    return tool


def slice_key(fund: str, tool: str, args: dict[str, Any] | None) -> str:
    name = " ".join(str(fund or "").lower().split())
    return f"{name}|{slice_slot(tool, args)}"


def note_cache(conversation_id: str, status: str, key: str, beside: str = "") -> None:
    conv = str(conversation_id or "").strip()
    if not conv:
        return
    with _lock:
        _events.setdefault(conv, []).append({"status": status, "key": key, "beside": beside})


def drain_cache_events(conversation_id: str) -> list[dict[str, str]]:
    conv = str(conversation_id or "").strip()
    with _lock:
        return list(_events.pop(conv, []))


def beside_keys(conversation_id: str, key: str) -> str:
    conv = str(conversation_id or "").strip()
    with _lock:
        bucket = _slices.get(conv) or {}
        others = [item for item in bucket if item != key]
    return ", ".join(others)


def recall_slice(conversation_id: str, fund: str, tool: str, args: dict[str, Any] | None) -> Any | None:
    conv = str(conversation_id or "").strip()
    if not conv or not fund:
        return None
    key = slice_key(fund, tool, args)
    now = time.time()
    with _lock:
        bucket = _slices.get(conv) or {}
        row = bucket.get(key)
        if not row:
            return None
        if now - float(row.get("stored_at") or 0) > IDLE_SEC:
            bucket.pop(key, None)
            return None
        return row.get("data")


def recall_wider_portfolio(conversation_id: str, fund: str, args: dict[str, Any] | None) -> Any | None:
    """A larger holdings or sectors slice can answer a smaller one. A smaller slice cannot."""
    conv = str(conversation_id or "").strip()
    name = " ".join(str(fund or "").lower().split())
    if not conv or not name:
        return None
    args = args or {}
    needed = [str(item).lower() for item in (args.get("sections") or ["holdings", "sectors"])]
    try:
        need_n = int(args.get("top_n") or 0)
    except (TypeError, ValueError):
        need_n = 0
    prefix = f"{name}|portfolio|"
    now = time.time()
    best: dict[str, Any] | None = None
    best_n = -1
    with _lock:
        bucket = _slices.get(conv) or {}
        for key, row in bucket.items():
            if not key.startswith(prefix):
                continue
            if now - float(row.get("stored_at") or 0) > IDLE_SEC:
                continue
            slot = str(row.get("slot") or "")
            parts = slot.split("|")
            if len(parts) < 3 or not parts[2].startswith("n="):
                continue
            have = [item for item in parts[1].split(",") if item]
            if any(section not in have for section in needed):
                continue
            try:
                have_n = int(parts[2][2:])
            except ValueError:
                continue
            if have_n < need_n or have_n <= best_n:
                continue
            best = row
            best_n = have_n
    if not best or not isinstance(best.get("data"), dict):
        return None
    data = dict(best["data"])
    for section in ("holdings", "sectors"):
        rows = data.get(section)
        if section not in needed:
            data[section] = []
        elif isinstance(rows, list):
            data[section] = rows[:need_n] if need_n else rows
    return data


def remember_slice(
    conversation_id: str,
    fund: str,
    tool: str,
    args: dict[str, Any] | None,
    data: Any,
    *,
    turn: int,
) -> str:
    conv = str(conversation_id or "").strip()
    key = slice_key(fund, tool, args)
    if not conv or not fund:
        return key
    with _lock:
        bucket = _slices.setdefault(conv, {})
        bucket[key] = {
            "data": data,
            "turn": turn,
            "stored_at": time.time(),
            "slot": slice_slot(tool, args),
        }
    return key


def drop_old_turns(conversation_id: str, current_turn: int) -> None:
    conv = str(conversation_id or "").strip()
    if not conv:
        return
    floor = current_turn - MAX_TURNS
    with _lock:
        bucket = _slices.get(conv) or {}
        stale = [key for key, row in bucket.items() if int(row.get("turn") or 0) <= floor]
        for key in stale:
            bucket.pop(key, None)


def clear_conversation(conversation_id: str) -> None:
    with _lock:
        _slices.pop(str(conversation_id or "").strip(), None)
