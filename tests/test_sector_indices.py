"""Sector index catalog and the weekly-history health check."""

from datetime import date

from ai_insight.common.sector_indices import fetch_ohlc, load_catalog, series_is_usable, week_stats
from ai_insight.common.sector_indices import IndexSpec, _bars


def _rows(n, start=10):
    return [{"date": f"2026-11-{day:02d}", "open": 100+day, "high": 102+day, "low": 99+day, "close": 100+day} for day in range(start, start+n)]


def test_one_row_is_rejected_and_five_rows_pass():
    assert series_is_usable(_rows(1), date(2026, 11, 10))[0] is False
    ok, reason = series_is_usable(_rows(6, start=10), date(2026, 11, 15))
    assert ok, reason


def test_catalog_skips_weak_and_groups_shared_tickers():
    specs = load_catalog()
    keys = {spec.key for spec in specs}
    assert "bank" in keys
    assert "defence" in keys
    tickers = {ticker for spec in specs for ticker in spec.tickers}
    assert "NIFTY_CONSTRUCTION.NS" not in tickers
    assert "NIFTY_TELECOMMUNICATIONS.NS" not in tickers
    auto = next(spec for spec in specs if spec.key == "auto")
    assert "Automobiles" in auto.news_sectors and "Auto Components" in auto.news_sectors
    assert all("Retailing" not in spec.news_sectors for spec in specs)


def test_fetch_uses_the_first_healthy_ticker():
    def history(ticker):
        if ticker == "BAD":
            return _rows(1)
        return _rows(6, start=10)

    spec = IndexSpec("bank", "Nifty Bank", ["BAD", "^NSEBANK"], "exact", ["Banks"])
    series = fetch_ohlc(spec, date(2026, 11, 15), history=history)
    assert series is not None and series.ticker == "^NSEBANK"
    stats = week_stats(series.bars, None)
    assert stats["week_change_pct"] is not None
    assert _bars(_rows(2))
