"""Parse GitHub Actions date ranges and apply them to Google News + publish-time filters.

Range is inclusive of the start date and exclusive of the end date.
Example: 5/10/2026-7/10/2026 covers 5 Oct and 6 Oct (not 7 Oct).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from news_pipeline.textutil import within_news_window

_RANGE_RE = re.compile(
    r"^\s*(?P<start>\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4})\s*"
    r"(?:-|–|to|/)\s*"
    r"(?P<end>\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4})\s*$",
    re.I,
)
_ISO_RANGE_RE = re.compile(
    r"^\s*(?P<start>\d{4}-\d{2}-\d{2})\s*(?:-|–|to)\s*(?P<end>\d{4}-\d{2}-\d{2})\s*$"
)


class NewsDateRangeError(ValueError):
    pass


def parse_one_date(raw: str) -> date:
    text = (raw or "").strip()
    if not text:
        raise NewsDateRangeError("empty date")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return date.fromisoformat(text)
    parts = re.split(r"[/\-.]", text)
    if len(parts) != 3:
        raise NewsDateRangeError(f"unrecognised date {raw!r}")
    a, b, c = (int(p) for p in parts)
    # ISO-like Y-M-D when first token is a 4-digit year
    if a >= 1000:
        year, month, day = a, b, c
    else:
        day, month, year = a, b, c
        if year < 100:
            year += 2000
    return date(year, month, day)


def parse_news_date_range(raw: str | None) -> tuple[date, date] | None:
    """Return (start_inclusive, end_exclusive) or None if unset."""
    text = (raw or "").strip()
    if not text:
        return None
    match = _ISO_RANGE_RE.match(text) or _RANGE_RE.match(text)
    if not match:
        raise NewsDateRangeError(
            f"date range must look like 5/10/2026-7/10/2026 (end exclusive), got {raw!r}"
        )
    start = parse_one_date(match.group("start"))
    end = parse_one_date(match.group("end"))
    if end <= start:
        raise NewsDateRangeError(f"end date must be after start date: {start.isoformat()} → {end.isoformat()}")
    return start, end


def range_bounds_utc(start: date, end_exclusive: date) -> tuple[datetime, datetime]:
    start_dt = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    end_dt = datetime(end_exclusive.year, end_exclusive.month, end_exclusive.day, tzinfo=timezone.utc)
    return start_dt, end_dt


def google_time_query(settings) -> str:
    """Clause appended to the Google News RSS q= search."""
    parsed = parse_news_date_range(getattr(settings, "news_date_range", "") or "")
    if parsed is not None:
        start, end = parsed
        return f"after:{start.isoformat()} before:{end.isoformat()}"
    raw = (getattr(settings, "google_news_when", None) or "1d").strip().lower()
    if raw.startswith("when:"):
        raw = raw[5:].strip()
    return f"when:{raw or '1d'}"


def article_in_fetch_window(published: datetime | None, settings, now: datetime) -> bool:
    """Keep articles in the configured window. Missing times stay until scrape fills them."""
    parsed = parse_news_date_range(getattr(settings, "news_date_range", "") or "")
    if parsed is None:
        return within_news_window(published, settings.news_window_hours, now)
    if published is None:
        return True
    start_dt, end_dt = range_bounds_utc(*parsed)
    return start_dt <= published < end_dt


def covered_calendar_days(settings) -> list[str]:
    """ISO dates actually requested (exclusive end omitted). Empty if using relative when:."""
    parsed = parse_news_date_range(getattr(settings, "news_date_range", "") or "")
    if parsed is None:
        return []
    start, end = parsed
    return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days)]


def describe_fetch_window(settings) -> str:
    parsed = parse_news_date_range(getattr(settings, "news_date_range", "") or "")
    if parsed is None:
        return (
            f"google={google_time_query(settings)} "
            f"news_window_hours={settings.news_window_hours}"
        )
    start, end = parsed
    days = (end - start).days
    covered = ", ".join((start + timedelta(days=i)).isoformat() for i in range(days))
    return (
        f"google={google_time_query(settings)} "
        f"inclusive_days={covered} exclusive_end={end.isoformat()}"
    )
