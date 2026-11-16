"""IST session windows. Storage stays UTC with a Z suffix."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from news_pipeline.textutil import to_iso

from ai_insight.common.config import CommonConfig, load_config

IST = ZoneInfo("Asia/Kolkata")
_SESSION_OPEN = time(15, 30)
_DAY_END = time(23, 59, 59)


def ist_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(IST)
    return to_ist(now)


def to_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware; IST and UTC are not guessed")
    return dt.astimezone(IST)


def fmt_ist(dt: datetime) -> str:
    local = to_ist(dt)
    return f"{local.day} {local.strftime('%b %Y, %H:%M')} IST"


def rolling_window(
    trading_date: date,
    days: int = 7,
    *,
    now: datetime | None = None,
    config: CommonConfig | None = None,
) -> tuple[str, str]:
    """Calendar window: start midnight IST (days-1) before trading_date, end at live now or day end."""
    cfg = config or load_config()
    end = _resolve_end(trading_date, cutoff=None, now=now, config=cfg)
    cap = datetime.combine(trading_date, _DAY_END, tzinfo=IST)
    if end > cap:
        end = cap
    start_day = trading_date - timedelta(days=max(days - 1, 0))
    start = datetime.combine(start_day, time(0, 0), tzinfo=IST)
    return to_iso(start), to_iso(end)


def week_window(trading_date: date, sessions: int = 5, *, now: datetime | None = None, config: CommonConfig | None = None) -> tuple[str, str]:
    """15:30 IST before the first of the last `sessions` sessions, through the cutoff."""
    from ai_insight.common.trading_calendar import prev_trading_day

    cfg = config or load_config()
    cursor = trading_date
    for _ in range(max(sessions - 1, 0)):
        cursor = prev_trading_day(cursor, holidays_path=cfg.holidays_path)
    start_day = prev_trading_day(cursor, holidays_path=cfg.holidays_path)
    start = datetime.combine(start_day, _SESSION_OPEN, tzinfo=IST)
    end = _resolve_end(trading_date, cutoff=None, now=now, config=cfg)
    cap = datetime.combine(trading_date, _DAY_END, tzinfo=IST)
    if end > cap:
        end = cap
    return to_iso(start), to_iso(end)


def session_window(
    trading_date: date,
    *,
    cutoff: datetime | None = None,
    now: datetime | None = None,
    holidays_path=None,
    config: CommonConfig | None = None,
) -> tuple[str, str]:
    """Previous trading day 15:30 IST through the cutoff, capped at 23:59 IST that date.

    Both ends are UTC ISO strings. A clock time of 00:30 IST is still the previous UTC date.
    """
    from ai_insight.common.trading_calendar import prev_trading_day

    cfg = config or load_config()
    previous = prev_trading_day(trading_date, holidays_path=holidays_path or cfg.holidays_path)
    start = datetime.combine(previous, _SESSION_OPEN, tzinfo=IST)
    end = _resolve_end(trading_date, cutoff=cutoff, now=now, config=cfg)
    cap = datetime.combine(trading_date, _DAY_END, tzinfo=IST)
    if end > cap:
        end = cap
    if start >= end:
        raise ValueError(
            f"session window is empty for {trading_date.isoformat()}: "
            f"{fmt_ist(start)} is not before {fmt_ist(end)}"
        )
    return to_iso(start), to_iso(end)


def _resolve_end(
    trading_date: date,
    *,
    cutoff: datetime | None,
    now: datetime | None,
    config: CommonConfig,
) -> datetime:
    if cutoff is not None:
        return to_ist(cutoff)
    if config.cutoff_ist:
        hour, minute = (int(part) for part in config.cutoff_ist.split(":"))
        return datetime.combine(trading_date, time(hour, minute), tzinfo=IST)
    return ist_now(now)
