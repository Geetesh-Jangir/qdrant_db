"""IST session window and the NSE calendar."""

import json
import logging
from datetime import date, datetime

import pytest

from ai_insight.common.config import load_config
from ai_insight.common.time_ist import IST, fmt_ist, session_window, to_ist
from ai_insight.common.trading_calendar import is_trading_day, next_trading_day, prev_trading_day


def _cfg(tmp_path, holidays: dict):
    path = tmp_path / "holidays.json"
    path.write_text(json.dumps(holidays), encoding="utf-8")
    return load_config(
        {
            "INSIGHTS_DATA_DIR": str(tmp_path / "data"),
            "INSIGHTS_HOLIDAYS_PATH": str(path),
            "INSIGHTS_LOG_DIR": str(tmp_path / "logs"),
        }
    )


def test_half_past_midnight_ist_is_previous_utc_day(tmp_path):
    cfg = _cfg(tmp_path, {"2026": ["2026-11-19"]})
    now = datetime(2026, 11, 16, 0, 30, tzinfo=IST)
    start, end = session_window(date(2026, 11, 16), now=now, config=cfg)
    assert start == "2026-11-13T10:00:00Z"
    assert end == "2026-11-15T19:00:00Z"
    assert fmt_ist(now) == "16 Nov 2026, 00:30 IST"


def test_window_caps_at_end_of_trading_date(tmp_path):
    cfg = _cfg(tmp_path, {"2026": ["2026-11-19"]})
    now = datetime(2026, 11, 17, 2, 0, tzinfo=IST)
    _start, end = session_window(date(2026, 11, 16), now=now, config=cfg)
    assert end == "2026-11-16T18:29:59Z"


def test_configured_cutoff_is_the_end(tmp_path):
    cfg = _cfg(tmp_path, {"2026": []})
    cfg = load_config(
        {
            "INSIGHTS_DATA_DIR": str(tmp_path / "data"),
            "INSIGHTS_HOLIDAYS_PATH": str(tmp_path / "holidays.json"),
            "INSIGHTS_LOG_DIR": str(tmp_path / "logs"),
            "INSIGHTS_CUTOFF_IST": "17:10",
        }
    )
    _start, end = session_window(date(2026, 11, 16), now=datetime(2026, 11, 16, 18, 0, tzinfo=IST), config=cfg)
    assert end == "2026-11-16T11:40:00Z"


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError):
        to_ist(datetime(2026, 11, 16, 0, 30))


def test_empty_window_is_rejected(tmp_path):
    cfg = _cfg(tmp_path, {"2026": []})
    with pytest.raises(ValueError):
        session_window(date(2026, 11, 20), now=datetime(2026, 11, 16, 10, 0, tzinfo=IST), config=cfg)


def test_weekends_and_holidays(tmp_path):
    path = tmp_path / "holidays.json"
    path.write_text(json.dumps({"2026": ["2026-11-19"]}), encoding="utf-8")
    assert is_trading_day(date(2026, 11, 14), holidays_path=path) is False
    assert is_trading_day(date(2026, 11, 16), holidays_path=path) is True
    assert is_trading_day(date(2026, 11, 19), holidays_path=path) is False
    assert prev_trading_day(date(2026, 11, 16), holidays_path=path) == date(2026, 11, 13)
    assert next_trading_day(date(2026, 11, 18), holidays_path=path) == date(2026, 11, 20)


def test_unknown_year_warns_and_uses_weekends(tmp_path, caplog):
    path = tmp_path / "holidays.json"
    path.write_text(json.dumps({"2026": ["2026-11-19"]}), encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        assert is_trading_day(date(2027, 11, 16), holidays_path=path) is True
    assert "no entry for 2027" in caplog.text


def test_empty_year_warns(tmp_path, caplog):
    path = tmp_path / "holidays.json"
    path.write_text(json.dumps({"2026": []}), encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        assert is_trading_day(date(2026, 11, 16), holidays_path=path) is True
    assert "empty" in caplog.text


def test_long_holiday_run_is_bounded(tmp_path):
    days = []
    cursor = date(2026, 11, 16)
    while len(days) < 20:
        if cursor.weekday() < 5:
            days.append(cursor.isoformat())
        cursor = date.fromordinal(cursor.toordinal() + 1)
    path = tmp_path / "holidays.json"
    path.write_text(json.dumps({"2026": days}), encoding="utf-8")
    with pytest.raises(ValueError):
        next_trading_day(date(2026, 11, 15), holidays_path=path)
