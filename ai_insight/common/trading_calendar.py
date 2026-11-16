"""NSE weekdays minus the holiday file. An unknown year uses weekends only."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from ai_insight.common.config import load_config

logger = logging.getLogger(__name__)

_MAX_WALK = 15


def is_trading_day(day: date, *, holidays_path: Path | None = None) -> bool:
    if day.weekday() >= 5:
        return False
    return day.isoformat() not in _closed_dates(day.year, _path(holidays_path))


def prev_trading_day(day: date, *, holidays_path: Path | None = None) -> date:
    return _walk(day, -1, holidays_path=holidays_path)


def next_trading_day(day: date, *, holidays_path: Path | None = None) -> date:
    return _walk(day, 1, holidays_path=holidays_path)


def _walk(day: date, step: int, *, holidays_path: Path | None) -> date:
    path = _path(holidays_path)
    years = {day.year, (day + timedelta(days=step * _MAX_WALK)).year}
    closed = {year: _closed_dates(year, path) for year in years}
    cursor = day
    for _ in range(_MAX_WALK):
        cursor += timedelta(days=step)
        if cursor.year not in closed:
            closed[cursor.year] = _closed_dates(cursor.year, path)
        if cursor.weekday() < 5 and cursor.isoformat() not in closed[cursor.year]:
            return cursor
    direction = "before" if step < 0 else "after"
    raise ValueError(f"no trading day within {_MAX_WALK} days {direction} {day.isoformat()}")


def _path(holidays_path: Path | None) -> Path:
    if holidays_path is not None:
        return Path(holidays_path)
    return load_config().holidays_path


def _closed_dates(year: int, path: Path) -> set[str]:
    book = _read(path)
    key = str(year)
    if key not in book:
        logger.warning("nse holiday list has no entry for %s; using weekends only", year)
        return set()
    days = book.get(key) or []
    if not days:
        logger.warning("nse holiday list for %s is empty; weekends only", year)
    return {str(day) for day in days}


def _read(path: Path) -> dict:
    if not path.is_file():
        logger.warning("nse holiday file missing at %s; using weekends only", path)
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("nse holiday file %s could not be read (%s); using weekends only", path, exc)
        return {}
    if not isinstance(loaded, dict):
        logger.warning("nse holiday file %s is not an object; using weekends only", path)
        return {}
    return loaded
