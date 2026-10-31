"""Fund manager Q&A — roster focus from natural language and display shaping."""

from __future__ import annotations

import re
from typing import Any

_PAST_ROSTER = re.compile(
    r"\b(?:"
    r"past|former|previous|ex[-\s]?manager|earlier|predecessor|"
    r"who\s+used\s+to\s+manage|used\s+to\s+manage|"
    r"earlier\s+manager|former\s+manager|previous\s+manager|"
    r"who\s+managed\s+before|before\s+(?:the\s+)?current"
    r")\b",
    re.I,
)
_CURRENT_ROSTER = re.compile(
    r"\b(?:"
    r"current|present|(?:who|whom)\s+(?:is|are)\s+(?:the\s+)?(?:fund\s+)?manager|"
    r"who\s+manages|who\s+(?:is|are)\s+managing|managing\s+now|"
    r"manager\s+now|today(?:'s)?\s+manager"
    r")\b",
    re.I,
)
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


_BOTH_ROSTER = re.compile(
    r"\b(?:"
    r"current\s+and\s+(?:past|former|previous)|"
    r"(?:past|former|previous)\s+and\s+current|"
    r"all\s+(?:the\s+)?managers|manager\s+history|"
    r"history\s+of\s+(?:the\s+)?managers"
    r")\b",
    re.I,
)


_MANAGER_ROSTER_ASK = re.compile(
    r"\b(?:"
    r"name\s+of\s+(?:the\s+)?fund\s+managers?|fund\s+manager\s+names?|"
    r"fund\s+manager\s+details?|about\s+(?:the\s+)?fund\s+managers?|"
    r"(?:tell|give)\s+me\s+(?:the\s+)?(?:a\s+)?(?:name\s+of\s+(?:the\s+)?)?fund\s+managers?"
    r")\b",
    re.I,
)


def asks_manager_roster(question: str) -> bool:
    """Human AMC manager names — not the RupeeStop fundManager pillar score."""
    q = (question or "").strip()
    if not q:
        return False
    if _MANAGER_ROSTER_ASK.search(q):
        return True
    if _BOTH_ROSTER.search(q) or _PAST_ROSTER.search(q) or _CURRENT_ROSTER.search(q):
        return True
    if re.search(r"\bfund\s+managers?\b", q, re.I) and re.search(
        r"\b(?:name|names|who|list|detail)\b", q, re.I
    ):
        return True
    return False


def infer_manager_roster_focus(question: str) -> str:
    """Current managers unless the question asks for former ones."""
    q = (question or "").strip()
    if _BOTH_ROSTER.search(q):
        return "all"
    wants_past = bool(_PAST_ROSTER.search(q))
    wants_current = bool(_CURRENT_ROSTER.search(q))
    if wants_past and wants_current:
        return "all"
    if wants_past:
        return "past"
    return "current"


def _parse_iso_date(s: str) -> str:
    t = (s or "").strip()
    if _ISO_DATE.match(t):
        return t
    return ""


def _earliest_on_scheme_dates(
    fund_name: str, managers: list[dict[str, Any]]
) -> list[str]:
    fn = fund_name.lower()
    dates: list[str] = []
    for m in managers:
        ms = _parse_iso_date(str(m.get("managing_since") or ""))
        if ms:
            dates.append(ms)
        for row in m.get("other_schemes") or []:
            if not isinstance(row, dict):
                continue
            sn = str(row.get("scheme_name") or "").lower()
            if fn and fn in sn:
                fd = _parse_iso_date(str(row.get("from_date") or ""))
                if fd:
                    dates.append(fd)
    return dates


def build_roster_note(
    focus: str,
    current: list[dict[str, Any]],
    past: list[dict[str, Any]],
    ctx: dict[str, Any] | None,
    fund_name: str,
) -> str:
    """Short, data-backed note — no scheme marketing copy."""
    ctx = ctx or {}
    inception = _parse_iso_date(str(ctx.get("inception_date") or ""))

    if focus == "past":
        if past:
            return ""
        return "No past managers are listed for this scheme in the available records."

    if focus == "current" and not current:
        if past:
            return (
                "No current managers are listed; only former managers appear "
                "in the records."
            )
        return "No fund manager records were returned for this scheme."

    if not current or past:
        return ""

    dates = _earliest_on_scheme_dates(fund_name, current)
    earliest = min(dates) if dates else ""
    names = ", ".join(str(m.get("name") or "").strip() for m in current if m.get("name"))
    if not names:
        names = "The listed manager(s)"

    if earliest and inception and earliest <= inception:
        return (
            f"No former managers are on record. {names} "
            f"{'are' if len(current) > 1 else 'is'} shown as the current "
            f"manager(s), with tenure on this scheme from {earliest} "
            f"(the scheme inception date is {inception})."
        )
    if earliest:
        return (
            f"No former managers are on record. {names} "
            f"{'are' if len(current) > 1 else 'is'} shown as the current "
            f"manager(s), with the earliest listed tenure on this scheme "
            f"from {earliest}."
        )
    if inception:
        return (
            f"No former managers are on record; only the current manager(s) "
            f"above appear for this scheme (inception {inception})."
        )
    return (
        "No former managers are on record; only the current manager(s) "
        "above are listed for this scheme."
    )


def enrich_manager_payload(mgr: dict[str, Any], question: str) -> dict[str, Any]:
    """Attach roster focus, filtered lists, and an optional note for UI/templates."""
    focus = infer_manager_roster_focus(question)
    current = list(mgr.get("current") or [])
    past = list(mgr.get("past") or [])
    fund_name = str(mgr.get("fund_name") or "").strip()
    ctx = mgr.get("context") if isinstance(mgr.get("context"), dict) else {}

    if focus == "current":
        show_current, show_past = current, []
    elif focus == "past":
        show_current, show_past = [], past
    else:
        show_current, show_past = current, past

    note = "" if focus == "current" else build_roster_note(focus, current, past, ctx, fund_name)

    return {
        **mgr,
        "past": [] if focus == "current" else past,
        "roster_focus": focus,
        "display_current": show_current,
        "display_past": show_past,
        "roster_note": note,
    }


def manager_answer_title(focus: str, fund_name: str) -> str:
    if focus == "current":
        return f"Current fund manager(s) — {fund_name}"
    if focus == "past":
        return f"Past fund manager(s) — {fund_name}"
    return f"Fund managers — {fund_name}"
