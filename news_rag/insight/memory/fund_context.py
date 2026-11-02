"""Primary fund identity from conversation memory."""

from __future__ import annotations

import re
from typing import Any

_ISIN_RE = re.compile(r"\b(INF[A-Z0-9]{9})\b", re.I)


def _frame_subjects(memory: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(memory, dict):
        return []
    frame = memory.get("frame")
    if not isinstance(frame, dict):
        return []
    return [row for row in (frame.get("subjects") or []) if isinstance(row, dict)]


def primary_fund_subject(memory: dict[str, Any] | None) -> dict[str, Any]:
    for row in _frame_subjects(memory):
        if str(row.get("role") or "") == "primary" and row.get("name"):
            return row
    for row in _frame_subjects(memory):
        if row.get("name"):
            return row
    stack = memory.get("entity_stack") if isinstance(memory, dict) else []
    if isinstance(stack, list):
        for row in stack:
            if isinstance(row, dict) and row.get("name"):
                return {"name": row.get("name"), "id": row.get("id") or ""}
    return {}


def primary_fund_isin(memory: dict[str, Any] | None) -> str:
    subject = primary_fund_subject(memory)
    raw = str(subject.get("id") or "").strip().upper()
    match = _ISIN_RE.search(raw)
    return match.group(1).upper() if match else ""


def list_cursor_fund_name(memory: dict[str, Any] | None) -> str:
    cursor = memory.get("list_cursor") if isinstance(memory, dict) else None
    if not isinstance(cursor, dict):
        return ""
    rows = cursor.get("rows") or []
    if not isinstance(rows, list) or not rows:
        return ""
    first = rows[0] if isinstance(rows[0], dict) else {}
    return str(first.get("name") or "").strip()


def primary_fund_name(memory: dict[str, Any] | None) -> str:
    if isinstance(memory, dict):
        frame = memory.get("frame")
        if isinstance(frame, dict):
            focus = str(frame.get("last_fund_focus") or "").strip()
            if focus:
                return focus
    name = str(primary_fund_subject(memory).get("name") or "").strip()
    if name:
        return name
    return list_cursor_fund_name(memory)


def memory_known_fund_names(memory: dict[str, Any] | None) -> list[str]:
    """Fund names the session already knows (holdings, stack, subjects, cursor) — not planner inventions."""
    if not isinstance(memory, dict):
        return []
    seen: set[str] = set()
    out: list[str] = []
    frame = memory.get("frame") if isinstance(memory.get("frame"), dict) else {}

    def _add(raw: str) -> None:
        name = str(raw or "").strip()
        key = name.lower()
        if not name or key in seen:
            return
        seen.add(key)
        out.append(name)

    for row in frame.get("investor_subjects") or []:
        if isinstance(row, dict):
            _add(str(row.get("name") or ""))
    for row in memory.get("holdings_in_chat") or []:
        if isinstance(row, dict):
            _add(str(row.get("name") or ""))
        else:
            _add(str(row))
    for name in _memory_fund_name_sources(memory):
        _add(name)
    focus = str(frame.get("last_fund_focus") or "").strip()
    if focus:
        _add(focus)
    return out


def fund_name_mentioned_in_memory(question: str, memory: dict[str, Any] | None) -> str:
    """Longest known fund name appearing in the user text (holdings / chat memory)."""
    q = (question or "").lower()
    if not q:
        return ""
    best = ""
    for name in memory_known_fund_names(memory):
        if name.lower() in q and len(name) > len(best):
            best = name
    return best


def last_fund_name_from_gists(memory: dict[str, Any] | None) -> str:
    for row in reversed(memory.get("gists") or [] if isinstance(memory, dict) else []):
        if not isinstance(row, dict):
            continue
        gist = str(row.get("gist") or "").lower()
        if not gist or gist.startswith("no fund"):
            continue
        for name in memory_known_fund_names(memory):
            if name.lower() in gist:
                return name
    return ""


def recent_fund_focus_names(memory: dict[str, Any] | None) -> list[str]:
    if not isinstance(memory, dict):
        return []
    frame = memory.get("frame")
    if not isinstance(frame, dict):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in frame.get("recent_fund_focus") or []:
        name = str(raw or "").strip()
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            out.append(name)
    focus = str(frame.get("last_fund_focus") or "").strip()
    if focus and focus.lower() not in seen:
        out.insert(0, focus)
    return out


def push_recent_fund_focus(frame: dict[str, Any], fund_name: str) -> None:
    name = str(fund_name or "").strip()
    if not name:
        return
    recent = [name] + [
        str(x).strip()
        for x in (frame.get("recent_fund_focus") or [])
        if str(x).strip() and str(x).strip().lower() != name.lower()
    ]
    frame["recent_fund_focus"] = recent[:4]
    frame["last_fund_focus"] = name


def fund_name_matches_category(fund_name: str, category: str) -> bool:
    """True when the fund name resolves to the given scheme category slug."""
    from news_rag.fund_rating_categories import match_scheme_category

    cat = str(category or "").strip().lower()
    name = str(fund_name or "").strip()
    if not cat or not name:
        return False
    match = match_scheme_category(name)
    if match and match.category:
        return match.category.strip().lower() == cat
    lowered = name.lower()
    if cat == "aggressive hybrid":
        return "aggressive hybrid" in lowered and "conservative hybrid" not in lowered
    if cat == "conservative hybrid":
        return "conservative hybrid" in lowered
    return cat in lowered


def _memory_fund_name_sources(memory: dict[str, Any]) -> list[str]:
    names: list[str] = []
    frame = memory.get("frame") if isinstance(memory.get("frame"), dict) else {}
    for row in frame.get("subjects") or []:
        if isinstance(row, dict) and row.get("name"):
            names.append(str(row["name"]).strip())
    for row in memory.get("entity_stack") or []:
        if isinstance(row, dict) and row.get("name"):
            names.append(str(row["name"]).strip())
    cursor = memory.get("list_cursor") if isinstance(memory.get("list_cursor"), dict) else {}
    for row in cursor.get("rows") or []:
        if isinstance(row, dict) and row.get("name"):
            names.append(str(row["name"]).strip())
    return names


def asks_these_equity_funds(question: str) -> bool:
    """Deictic compare of equity funds named earlier in chat (not a hybrid category slug)."""
    q = (question or "").lower()
    if not re.search(r"\b(?:these|those)\b", q):
        return False
    return bool(re.search(r"\bequity\s+funds?\b", q))


def _pure_equity_category_slug(category: str) -> bool:
    from news_rag.fund_rating_categories import CATEGORIES

    cat = str(category or "").strip().lower()
    if not cat:
        return False
    if cat in CATEGORIES.get("hybrid", ()):
        return False
    return cat in CATEGORIES.get("equity", ())


def recent_equity_fund_pair_in_chat(memory: dict[str, Any] | None) -> list[str]:
    """Latest pair of pure-equity category funds in chat (ignores hybrid buckets and alternate picks)."""
    if not isinstance(memory, dict):
        return []
    buckets = memory.get("category_funds_in_chat")
    if isinstance(buckets, list):
        for bucket in reversed(buckets):
            if not isinstance(bucket, dict):
                continue
            cat = str(bucket.get("category") or "").strip().lower()
            names = [
                str(n).strip()
                for n in (bucket.get("fund_names") or [])
                if str(n).strip()
            ]
            if _pure_equity_category_slug(cat) and len(names) >= 2:
                return names[:2]

    cursor = memory.get("list_cursor") if isinstance(memory.get("list_cursor"), dict) else {}
    filters = cursor.get("filters") if isinstance(cursor.get("filters"), dict) else {}
    if not filters.get("pick_alternate"):
        rows = cursor.get("rows") if isinstance(cursor.get("rows"), list) else []
        names = [
            str(row.get("name") or "").strip()
            for row in rows
            if isinstance(row, dict) and row.get("name")
        ]
        if len(names) >= 2:
            from news_rag.fund_rating_categories import match_scheme_category

            if all(
                _pure_equity_category_slug(
                    str(match_scheme_category(n).category or "") if match_scheme_category(n) else ""
                )
                for n in names[:2]
            ):
                return names[:2]

    from news_rag.fund_rating_categories import CATEGORIES

    for cat in reversed(CATEGORIES.get("equity", ())):
        scoped = memory_funds_for_category(memory, cat)
        if len(scoped) >= 2:
            return scoped[:2]
    return []


def memory_funds_for_category(memory: dict[str, Any] | None, category: str) -> list[str]:
    """Distinct fund names in memory that belong to one scheme category (includes list cursor)."""
    if not isinstance(memory, dict) or not str(category or "").strip():
        return []
    out: list[str] = []
    for name in _memory_fund_name_sources(memory):
        if fund_name_matches_category(name, category) and name not in out:
            out.append(name)
    return out


def comparison_fund_names(
    memory: dict[str, Any] | None,
    *,
    category: str = "",
) -> list[str]:
    """Funds from the last in-chat comparison (frame or stack), not the list cursor."""
    if not isinstance(memory, dict):
        return []
    cat = str(category or "").strip()

    def _filter(names: list[str]) -> list[str]:
        if not cat:
            return names
        return [n for n in names if fund_name_matches_category(n, cat)]

    frame = memory.get("frame") if isinstance(memory.get("frame"), dict) else {}
    if str(frame.get("subject_kind") or "").lower() == "comparison":
        names: list[str] = []
        for row in frame.get("subjects") or []:
            if isinstance(row, dict) and row.get("name"):
                names.append(str(row["name"]).strip())
        names = _filter(list(dict.fromkeys(names)))
        if len(names) >= 2:
            return names
        if cat and len(names) == 1:
            scoped = memory_funds_for_category(memory, cat)
            if len(scoped) >= 2:
                return scoped[:2]
    stack = memory.get("entity_stack") if isinstance(memory.get("entity_stack"), list) else []
    from_compare: list[str] = []
    for row in stack:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        facts = row.get("fact_names") or row.get("facts") or []
        if "compare_funds" in facts:
            from_compare.append(str(row["name"]).strip())
    from_compare = _filter(list(dict.fromkeys(from_compare)))
    if len(from_compare) >= 2:
        return from_compare
    if cat:
        scoped = memory_funds_for_category(memory, cat)
        if len(scoped) >= 2:
            return scoped[:2]
    return []


def compare_payload_matches_funds(fund_names: list[str], data: dict[str, Any]) -> bool:
    """True when compare tool payload is for the same fund pair as requested."""
    if not isinstance(data, dict):
        return False
    want = sorted(" ".join(str(n).lower().split()) for n in fund_names if str(n).strip())
    if not want:
        return True

    def _names_from_payload() -> list[str]:
        got: list[str] = []
        for row in data.get("funds") or []:
            if not isinstance(row, dict):
                continue
            fn = str(row.get("fund_name") or row.get("name") or "").strip()
            if fn:
                got.append(" ".join(fn.lower().split()))
        if len(got) == len(want):
            return got
        overlap = data.get("holding_overlap") if isinstance(data.get("holding_overlap"), dict) else {}
        alt = overlap.get("fund_names") or []
        if isinstance(alt, list) and alt:
            return [" ".join(str(x).lower().split()) for x in alt if str(x).strip()]
        return got

    got = _names_from_payload()
    if len(got) != len(want):
        return False
    return sorted(got) == want


def subjects_from_fund_names(names: list[str]) -> list[dict[str, Any]]:
    from news_rag.fund_search import get_fund_index

    idx = get_fund_index()
    out: list[dict[str, Any]] = []
    for raw in names:
        name = str(raw or "").strip()
        if not name:
            continue
        detail, _a, _c = idx.lookup_extracted_fund(name=name)
        isin = str((detail or {}).get("isin") or "").strip()
        canonical = str((detail or {}).get("fund_short_name") or (detail or {}).get("fund_name") or name).strip()
        if canonical not in [row.get("name") for row in out]:
            out.append({"id": isin, "name": canonical, "plan": "", "role": "primary"})
    return out
