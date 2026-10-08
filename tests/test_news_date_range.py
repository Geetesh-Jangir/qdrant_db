from datetime import date, datetime, timezone

from news_pipeline.config import Settings
from news_pipeline.news_dates import (
    article_in_fetch_window,
    google_time_query,
    parse_news_date_range,
)


def test_exclusive_end_covers_two_calendar_days():
    start, end = parse_news_date_range("5/10/2026-7/10/2026")
    assert start == date(2026, 10, 5)
    assert end == date(2026, 10, 7)
    assert (end - start).days == 2


def test_two_digit_year_and_iso():
    assert parse_news_date_range("1/10/26-5/10/26") == (date(2026, 10, 1), date(2026, 10, 5))
    assert parse_news_date_range("2026-10-05 to 2026-10-07") == (date(2026, 10, 5), date(2026, 10, 7))


def test_google_query_uses_after_before_when_range_set():
    settings = Settings()
    settings.news_date_range = "5/10/2026-7/10/2026"
    settings.google_news_when = "1d"
    assert google_time_query(settings) == "after:2026-10-05 before:2026-10-07"


def test_google_query_falls_back_to_when_without_range():
    settings = Settings()
    settings.news_date_range = ""
    settings.google_news_when = "1d"
    assert google_time_query(settings) == "when:1d"


def test_publish_filter_exclusive_end():
    settings = Settings()
    settings.news_date_range = "5/10/2026-7/10/2026"
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    fifth = datetime(2026, 10, 5, 15, 0, tzinfo=timezone.utc)
    sixth = datetime(2026, 10, 6, 23, 59, tzinfo=timezone.utc)
    seventh = datetime(2026, 10, 7, 0, 0, tzinfo=timezone.utc)
    assert article_in_fetch_window(fifth, settings, now) is True
    assert article_in_fetch_window(sixth, settings, now) is True
    assert article_in_fetch_window(seventh, settings, now) is False
    assert article_in_fetch_window(None, settings, now) is True
