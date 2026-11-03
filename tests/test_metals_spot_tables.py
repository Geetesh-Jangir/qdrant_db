"""Gold window table: then vs now prices from metals_spot returns."""

from news_rag.insight.metals_spot_tables import (
    render_gold_returns_table,
    strip_gold_window_table,
)


def test_render_gold_returns_table_shows_then_and_now():
    results = [
        {
            "ok": True,
            "tool": "get_market_snapshot",
            "data": {
                "metals_spot": {
                    "available": True,
                    "metal": "gold",
                    "returns": {
                        "1D": {
                            "pct": -1.15,
                            "from_date": "2026-11-02",
                            "from_price": 139260.0,
                            "to_date": "2026-11-03",
                            "to_price": 137660.0,
                        },
                        "1W": {
                            "pct": -3.7,
                            "from_date": "2026-10-27",
                            "from_price": 142950.0,
                            "to_date": "2026-11-03",
                            "to_price": 137660.0,
                        },
                    },
                }
            },
        }
    ]
    table = render_gold_returns_table(results)
    assert "1,39,260 (2 Nov)" in table
    assert "1,37,660 (3 Nov)" in table
    assert "1,42,950 (27 Oct)" in table
    assert "-1.15%" in table
    assert "-3.70%" in table
    assert "Then (₹ per 10g)" in table
    assert "Now (₹ per 10g)" in table


def test_strip_gold_window_table():
    body = (
        "Gold is falling.\n\n"
        "| Window | Price (₹ per 10g) | Change |\n"
        "|---|---|---|\n"
        "| 1D (from 2 Nov) | 1,37,660 | -1.15% |\n"
    )
    assert "Price (₹ per 10g)" not in strip_gold_window_table(body)
    assert "Gold is falling." in strip_gold_window_table(body)
