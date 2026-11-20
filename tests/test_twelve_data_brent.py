from datetime import date
from ai_insight.data import twelve_data_brent as td


def test_row_parses_twelve_data_value():
    row = td._row_from_value(
        {"datetime": "2026-11-18", "open": "90", "high": "91", "low": "89", "close": "90.5", "volume": "0"},
        symbol="BCO",
        requested="XBR/USD",
    )
    assert row
    assert row["date"] == "2026-11-18"
    assert row["close"] == 90.5
    assert row["symbol"] == "BCO"
    assert row["requested_symbol"] == "XBR/USD"


def test_sync_backfills_when_history_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(td, "_api_key", lambda: "test-key")
    monkeypatch.setattr(td, "resolve_fetch_symbol", lambda _key: ("BCO", "fallback"))
    rows = [
        {
            "date": "2026-11-17",
            "close": 90.0,
            "open": 89.0,
            "high": 91.0,
            "low": 88.0,
            "volume": 0,
            "unit": "usd",
            "symbol": "BCO",
            "requested_symbol": "XBR/USD",
            "source": "twelvedata:time_series",
            "fetched_at_utc": "2026-11-19T00:00:00Z",
        }
    ]
    monkeypatch.setattr(td, "fetch_days", lambda *a, **k: rows)

    result = td.sync_brent_history(date(2026, 11, 19), data_dir=tmp_path)
    assert result.status == "backfilled"
    assert result.rows_added == 1
    stored = (tmp_path / "_data" / td.HISTORY_NAME).read_text(encoding="utf-8")
    assert "2026-11-17" in stored


def test_sync_appends_single_day(tmp_path, monkeypatch):
    history = tmp_path / "_data" / td.HISTORY_NAME
    history.parent.mkdir(parents=True)
    history.write_text('[{"date":"2026-11-17","close":90}]', encoding="utf-8")

    monkeypatch.setattr(td, "_api_key", lambda: "test-key")
    monkeypatch.setattr(td, "resolve_fetch_symbol", lambda _key: ("BCO", ""))
    monkeypatch.setattr(
        td,
        "fetch_day",
        lambda *a, **k: {
            "date": "2026-11-18",
            "close": 91.0,
            "unit": "usd",
            "symbol": "BCO",
            "requested_symbol": "XBR/USD",
            "source": "twelvedata:time_series",
            "fetched_at_utc": "2026-11-19T00:00:00Z",
        },
    )

    result = td.sync_brent_history(date(2026, 11, 18), data_dir=tmp_path)
    assert result.status == "saved"
    assert result.rows_added == 1