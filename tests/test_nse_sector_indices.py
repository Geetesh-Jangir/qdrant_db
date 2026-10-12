"""NSE sector index JSON aligns with SECTOR_QUERIES and supports O(1) lookup."""

from __future__ import annotations

import os

import pytest

from lib.nse_sector_indices import (
    NIFTY_50_KEY,
    benchmark_entry,
    clear_sector_index_cache,
    sector_index_entry,
    sector_yfinance_ticker,
)
from news_pipeline.config import SECTOR_QUERIES


@pytest.fixture(autouse=True)
def _clear_index_cache():
    clear_sector_index_cache()
    yield
    clear_sector_index_cache()


def test_by_sector_keys_match_sector_queries_exactly():
    from lib.nse_sector_indices import _document

    by_sector = _document()["by_sector"]
    assert set(by_sector) == set(SECTOR_QUERIES)
    assert _document()["metadata"]["schema_version"] == "2.0.0"


def test_nifty_50_benchmark_present():
    row = benchmark_entry(NIFTY_50_KEY)
    assert row is not None
    assert row["yfinance_ticker"] == "^NSEI"
    assert row["nse_index_name"] == NIFTY_50_KEY
    assert benchmark_entry("India VIX") is None


def test_o1_lookup_returns_ticker():
    assert sector_yfinance_ticker("Banks") == "^NSEBANK"
    assert sector_index_entry("Unknown Sector") is None
    assert sector_yfinance_ticker("Unknown Sector") is None


def test_every_sector_has_verified_ticker_field():
    from lib.nse_sector_indices import _document

    for name, row in _document()["by_sector"].items():
        assert row.get("yfinance_ticker"), name
        assert row.get("ticker_status") == "yfinance_verified", name


@pytest.mark.skipif(
    os.environ.get("RUN_YFINANCE_SECTOR_CHECK") != "1",
    reason="set RUN_YFINANCE_SECTOR_CHECK=1 to hit Yahoo Finance",
)
def test_yfinance_history_not_empty_for_all_mapped_symbols():
    yfinance = pytest.importorskip("yfinance")

    from lib.nse_sector_indices import _document

    doc = _document()
    symbols: set[str] = set()
    symbols.add(doc["benchmarks"][NIFTY_50_KEY]["yfinance_ticker"])
    for row in doc["by_sector"].values():
        symbols.add(row["yfinance_ticker"])

    for symbol in sorted(symbols):
        frame = yfinance.Ticker(symbol).history(period="5d")
        assert frame is not None and not frame.empty, symbol
