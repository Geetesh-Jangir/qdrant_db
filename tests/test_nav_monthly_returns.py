from historical_data.nav_service import monthly_returns_from_records


def test_monthly_returns_from_records():
    records = [
        {"nav_date": "2026-08-01", "nav_value": 100.0},
        {"nav_date": "2026-08-15", "nav_value": 102.0},
        {"nav_date": "2026-09-01", "nav_value": 102.0},
        {"nav_date": "2026-09-20", "nav_value": 101.0},
    ]
    monthly = monthly_returns_from_records(records, months=6)
    assert len(monthly) == 2
    assert monthly[0]["month"] == "2026-08"
    assert monthly[0]["return_pct"] == 2.0
