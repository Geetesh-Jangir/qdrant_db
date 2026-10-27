from datetime import datetime, timedelta

from historical_data.nav_service import _calculate_window_stats
from news_rag.tools import screen_hints_from_question


def test_category_beats_a_shorter_cap_phrase():
    hints = screen_hints_from_question(
        "compare any two large and mid cap funds which are performing well in last 1 year?"
    )
    assert hints["category"] == "Large & Mid Cap"
    assert hints["sector_name"] == ""


def test_banking_and_defence_funds_are_categories_not_sectors():
    banking = screen_hints_from_question(
        "compare any two banking funds which are performing well in last 1 year?"
    )
    defence = screen_hints_from_question(
        "compare any two defense funds which are performing well in last 1 year?"
    )
    assert banking["category"] == "Banking & Financial Services"
    assert banking["sector_name"] == ""
    assert defence["category"] == "Defense & Aerospace"
    assert defence["sector_name"] == ""


def test_sector_exposure_stays_a_sector_screen():
    hints = screen_hints_from_question("what are the 5 funds that are invested in banking sector?")
    assert hints["sector_name"]
    assert hints["category"] == ""


def test_stock_holding_is_not_a_bank_sector_screen():
    hints = screen_hints_from_question("2 equity funds which are invested in hdfc bank")
    assert hints["stock_name"].lower().startswith("hdfc")
    assert hints["sector_name"] == ""


def test_short_history_is_not_a_five_year_return():
    latest = datetime(2026, 10, 26)
    start = latest - timedelta(days=40)
    records = [
        {"nav_date": start.strftime("%Y-%m-%d"), "nav_value": 10.0},
        {"nav_date": latest.strftime("%Y-%m-%d"), "nav_value": 11.0},
    ]
    assert _calculate_window_stats(records, days=30) is not None
    assert _calculate_window_stats(records, days=365) is None
    assert _calculate_window_stats(records, days=1825) is None
