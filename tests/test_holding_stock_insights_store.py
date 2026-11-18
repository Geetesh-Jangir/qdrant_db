"""Holding stock insights daily JSON archive."""

from ai_insight.holding_insights.holding_stock_insights_store import (
    build_holding_stock_insights_snapshot,
    load_holding_stock_insights,
    save_holding_stock_insights,
)


def test_holding_stock_insights_snapshot_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_DATA_DIR", str(tmp_path))
    day = "2026-11-18"
    outcome = {
        "job_id": "a1b2c3d4e5f6",
        "generated_on": day,
        "counts": {"ok": 1, "insufficient": 0},
        "insights": [
            {
                "stock_id": "HDFCBANK",
                "stock_name": "HDFC Bank Ltd",
                "sector": "Banks",
                "created_at": "2026-11-18T14:00:00+05:30",
                "headline": "HDFC Bank up 1.2% on loan growth",
                "insight_lines": ["Loan growth continues.", "Margins stable.", "Outlook steady."],
                "usage": {"input_tokens": 800, "output_tokens": 120, "llm_calls": 1, "model": "claude-haiku-5-5"},
                "articles": [
                    {
                        "url": "https://example.com/n1",
                        "headline": "Loan book expands",
                        "published_at": "2026-11-17T04:00:00Z",
                    }
                ],
                "llm": {"user_prompt": "User prompt body", "output_text": '{"headline":"..."}'},
                "price_snapshot": {"latest_price": 100.0, "bars": [{"date": "2026-11-18", "close": 100.0}]},
            }
        ],
        "insufficient": [],
    }
    snap = build_holding_stock_insights_snapshot(outcome)
    assert snap["trading_date"] == day
    row = snap["holdings"][0]
    assert row["stock_name"] == "HDFC Bank Ltd"
    assert row["sector"] == "Banks"
    assert row["articles"][0]["url"] == "https://example.com/n1"
    assert row["llm"]["user_prompt"] == "User prompt body"
    assert row["price"]["latest_price"] == 100.0
    assert "Loan growth" in row["insight"]

    save_holding_stock_insights(day, snap)
    loaded = load_holding_stock_insights(day)
    assert loaded is not None
    assert loaded["holdings"][0]["input_tokens"] == 800