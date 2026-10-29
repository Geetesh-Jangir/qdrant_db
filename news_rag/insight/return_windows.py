"""Return windows of any length, measured from NAV history."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_CODE = re.compile(r"^(\d+)([DWMY])$")
_FIXED_DAYS = {
    "1D": 1,
    "1W": 7,
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    "2Y": 730,
    "3Y": 1095,
    "5Y": 1825,
    "10Y": 3650,
}
_UNIT_DAYS = {"D": 1, "W": 7, "M": 30, "Y": 365}


def normalize_window_code(raw: str) -> str:
    text = re.sub(r"[^A-Z0-9]", "", str(raw or "").upper())
    if text in ("YTD", "YEARTILLDATE", "YEARTONOW"):
        return "YTD"
    if text in _FIXED_DAYS or _CODE.match(text):
        return text
    return ""


def window_to_days(code: str) -> int | None:
    """Calendar length. YTD is not a fixed number of days."""
    cleaned = normalize_window_code(code)
    if not cleaned or cleaned == "YTD":
        return _FIXED_DAYS.get(cleaned)
    if cleaned in _FIXED_DAYS:
        return _FIXED_DAYS[cleaned]
    match = _CODE.match(cleaned)
    if not match:
        return None
    count = int(match.group(1))
    if count <= 0 or count > 40:
        return None
    return count * _UNIT_DAYS[match.group(2)]


def window_label(code: str) -> str:
    cleaned = normalize_window_code(code)
    if cleaned == "YTD":
        return "year to date"
    days = window_to_days(cleaned)
    if days is None:
        return cleaned or "that period"
    if cleaned.endswith("D"):
        n = int(cleaned[:-1])
        return "1 day" if n == 1 else f"{n} days"
    if cleaned.endswith("W"):
        n = int(cleaned[:-1])
        return "1 week" if n == 1 else f"{n} weeks"
    if cleaned.endswith("M"):
        n = int(cleaned[:-1])
        return "1 month" if n == 1 else f"{n} months"
    if cleaned.endswith("Y"):
        n = int(cleaned[:-1])
        return "1 year" if n == 1 else f"{n} years"
    return cleaned


def _parse_date(value: str) -> datetime | None:
    text = str(value or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _pretty_date(value: datetime) -> str:
    return f"{value.day} {value.strftime('%B %Y')}"


def _age_phrase(start: datetime, end: datetime) -> str:
    days = max(0, (end.date() - start.date()).days)
    years, rem = divmod(days, 365)
    months = rem // 30
    parts: list[str] = []
    if years:
        parts.append("1 year" if years == 1 else f"{years} years")
    if months:
        parts.append("1 month" if months == 1 else f"{months} months")
    if not parts:
        parts.append("1 day" if days == 1 else f"{days} days")
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return parts[0]


def _ytd_days(latest: datetime) -> int:
    return max(1, (latest.date() - latest.date().replace(month=1, day=1)).days)


def returns_for_windows(
    isin: str,
    windows: list[str],
    *,
    inception_date: str = "",
) -> tuple[dict[str, float], list[dict[str, str]]]:
    """NAV-history return for each asked window. A missing window is a limit, not another period."""
    from historical_data.nav_service import _calculate_window_stats, fetch_raw_nav_history

    codes = []
    for raw in windows:
        code = normalize_window_code(str(raw))
        if code and code not in codes:
            codes.append(code)
    if not isin or not codes:
        return {}, []

    records = fetch_raw_nav_history(isin)
    if not records:
        limits = [
            {
                "window": code,
                "note": f"The {window_label(code)} return is not available because no NAV history was found.",
            }
            for code in codes
        ]
        return {}, limits

    latest = _parse_date(str(records[-1].get("nav_date") or ""))
    first = _parse_date(str(records[0].get("nav_date") or ""))
    started = _parse_date(inception_date) or first
    found: dict[str, float] = {}
    limits: list[dict[str, str]] = []
    for code in codes:
        if latest is None:
            break
        days = _ytd_days(latest) if code == "YTD" else window_to_days(code)
        stats = _calculate_window_stats(records, days=days) if days is not None else None
        pct = stats.get("change_pct") if isinstance(stats, dict) else None
        if pct is None:
            label = window_label(code)
            if started is not None and latest is not None:
                note = (
                    f"The fund's inception date is {_pretty_date(started)}. "
                    f"It has been {_age_phrase(started, latest)} till now, "
                    f"so the {label} return is not available."
                )
            else:
                note = f"The {label} return is not available for this fund."
            limits.append({"window": code, "note": note})
            continue
        found[code] = float(pct)
    return found, limits


def align_plan_windows(plan: Any) -> None:
    """If the planner named windows but left the default 1-month clock, follow the windows."""
    codes: list[str] = []
    for call in getattr(plan, "tool_calls", None) or []:
        if getattr(call, "tool", "") != "get_fund_data":
            continue
        for raw in (call.arguments or {}).get("windows") or []:
            code = normalize_window_code(str(raw))
            if code and code not in codes:
                codes.append(code)
    if not codes:
        return
    label = str(getattr(plan, "window_label", "") or "")
    days = int(getattr(plan, "window_days", 0) or 0)
    left_the_default = label in ("", "1 month") and days in (0, 30)
    if not left_the_default or codes == ["1M"]:
        return
    plan.window_label = " and ".join(window_label(code) for code in codes)
    lengths = [window_to_days(code) for code in codes]
    known = [item for item in lengths if item]
    if codes == ["YTD"]:
        plan.window_days = _ytd_days(datetime.now())
    elif len(codes) == 1 and known:
        plan.window_days = known[0]
    elif known:
        plan.window_days = max(known)
