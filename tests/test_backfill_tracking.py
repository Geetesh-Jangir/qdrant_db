from datetime import date, datetime, timezone

from news_pipeline.config import Settings
from news_pipeline.news_dates import (
    iter_inclusive_days,
    parse_one_date,
    publish_time_for_scrape,
    single_day_news_date_range,
)
from news_pipeline.publisher_stats import PublisherStats
from unittest.mock import patch

from news_pipeline.backfill_days import _checkpoint_path
from news_pipeline.retry_backoff import sleep_before_attempt


def test_publish_time_trusts_rss_when_in_range():
    settings = Settings()
    settings.news_date_range = "5/10/2026-7/10/2026"
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    rss = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
    page = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
    chosen = publish_time_for_scrape(rss, page, settings, now)
    assert chosen == rss


def test_publish_time_drops_when_rss_outside_range():
    settings = Settings()
    settings.news_date_range = "5/10/2026-7/10/2026"
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    rss = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    chosen = publish_time_for_scrape(rss, None, settings, now)
    assert chosen is None


def test_single_day_range_format():
    assert single_day_news_date_range(date(2026, 10, 1)) == "1/10/2026-2/10/2026"


def test_iter_inclusive_days_three():
    start = parse_one_date("1/10/2026")
    end = parse_one_date("3/10/2026")
    days = iter_inclusive_days(start, end)
    assert [d.isoformat() for d in days] == ["2026-10-01", "2026-10-02", "2026-10-03"]


def test_backoff_sleep_schedule():
    sleeps: list[float] = []

    def capture(sec: float) -> None:
        sleeps.append(sec)

    with patch("news_pipeline.retry_backoff.time.sleep", side_effect=capture):
        for attempt in range(3):
            sleep_before_attempt(attempt, 2.0)
    assert sleeps == [2.0, 4.0]


def test_checkpoint_paths_differ_by_range():
    a = _checkpoint_path(date(2026, 10, 1), date(2026, 10, 3))
    b = _checkpoint_path(date(2026, 10, 4), date(2026, 10, 6))
    assert a != b
    assert a.name == "checkpoint_2026-10-01_2026-10-03.json"


def test_publisher_stats_unique_urls(tmp_path):
    from news_pipeline.run_context import set_run_context

    set_run_context("run_test", "2026-10-01", "1/10/2026-2/10/2026")
    stats = PublisherStats()
    stats.record_received("moneycontrol.com", "https://moneycontrol.com/a")
    stats.record_received("moneycontrol.com", "https://moneycontrol.com/a")
    stats.record_scraped("moneycontrol.com", "https://moneycontrol.com/a")
    stats.record_scrape_error("moneycontrol.com", "https://moneycontrol.com/b", "fetch_failed")
    path = tmp_path / "publisher_stats.json"
    stats.write(path)
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    row = data["publishers"][0]
    assert row["received"] == 1
    assert row["scraped"] == 1
    assert row["scrape_errors"] == 1
    assert data["totals"]["urls_received"] == 1
    assert data["totals"]["urls_scraped"] == 1
    assert data["totals"]["urls_scrape_errors"] == 1


def test_failure_ledger_attempts_cap(tmp_path):
    import news_pipeline.failure_ledger as ledger

    from news_pipeline.run_context import set_run_context

    settings = Settings()
    settings.news_failures_dir = str(tmp_path / "failures")
    ledger._loaded = False
    ledger._source_items = {}
    ledger._google_items = {}
    set_run_context("run1", "2026-10-01", "1/10/2026-2/10/2026")
    reset_run_buffers = ledger.reset_run_buffers
    reset_run_buffers()
    for _ in range(3):
        ledger.record_source_failure(
            settings,
            url="https://example.com/story",
            drop_reason="fetch_failed",
            retriable=True,
            source="example.com",
        )
    ledger.flush(settings)
    assert ledger.is_source_exhausted("https://example.com/story", settings)
