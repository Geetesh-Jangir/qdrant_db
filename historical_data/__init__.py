"""Historical market, NAV, and commodity data services."""

from historical_data.metals_service import (
    fetch_snapdata_metals,
    format_metals_context_for_llm,
    get_latest_metals_spot,
    load_metals_history,
    save_metals_history,
)
from historical_data.nav_service import get_fund_nav_history
from historical_data.stocks_service import (
    format_holdings_stock_context,
    format_single_stock_context,
    get_stock_profile,
    resolve_stock_ticker,
)

__all__ = [
    "get_fund_nav_history",
    "fetch_snapdata_metals",
    "get_latest_metals_spot",
    "load_metals_history",
    "save_metals_history",
    "format_metals_context_for_llm",
    "get_stock_profile",
    "resolve_stock_ticker",
    "format_holdings_stock_context",
    "format_single_stock_context",
]

