"""Compare fund holdings in a sector to the mapped Nifty index and Nifty 50."""

from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

from lib.nse_sector_indices import nifty50_ticker, sector_index_entry, sector_yfinance_ticker
from lib.portfolio_scope import sector_query_for_label
from news_rag.fund_search import extract_top_holdings, extract_top_sectors
from news_rag.holdings_market import fetch_dedicated_holding_news, _slim_article

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

FLAT_THRESHOLD_PCT = 0.3


def return_sign(pct: float | None, *, threshold: float = FLAT_THRESHOLD_PCT) -> str:
    if pct is None:
        return "unknown"
    if abs(pct) < threshold:
        return "flat"
    return "up" if pct > 0 else "down"


def signs_opposite(a: str, b: str) -> bool:
    if a in ("unknown", "flat") or b in ("unknown", "flat"):
        return False
    return a != b


def index_return_pct(ticker: str, window: str = "5d") -> float | None:
    """Percent change for an index symbol (^NSEI, ^CNXAUTO, ...)."""
    if not ticker:
        return None
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        hist = yf.Ticker(ticker).history(period="3mo")
        if hist is None or hist.empty or len(hist) < 2:
            return None
        cmp_price = float(hist["Close"].iloc[-1])
        window_key = (window or "5d").strip().lower()
        if window_key in ("1m", "1mo", "1month", "30d"):
            lookback = 21 if len(hist) >= 21 else len(hist) - 1
        else:
            lookback = 5 if len(hist) >= 5 else len(hist) - 1
        prior = float(hist["Close"].iloc[-1 - lookback])
        if prior == 0:
            return None
        return round(((cmp_price - prior) / prior) * 100.0, 2)
    except Exception:
        return None


def holding_return_pct(holding_name: str, window: str = "5d") -> tuple[float | None, str]:
    from historical_data.stocks_service import get_stock_profile

    profile = get_stock_profile(holding_name)
    if not profile:
        return None, "price_unavailable"
    window_key = (window or "5d").strip().lower()
    if window_key in ("1m", "1mo", "1month", "30d"):
        val = profile.get("return_1m")
    else:
        val = profile.get("return_1w")
    if val is None:
        return None, "price_unavailable"
    return float(val), "ok"


def canonical_sector_for_holding(industry: str) -> str | None:
    mapped = sector_query_for_label(industry)
    if mapped:
        return mapped[0]
    return None


def holdings_in_sector(
    sector_name: str,
    holdings: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    target = sector_name.casefold()
    matched: list[dict[str, Any]] = []
    for row in holdings:
        industry = str(row.get("industry") or row.get("sector") or "").strip()
        canon = canonical_sector_for_holding(industry)
        if canon and canon.casefold() == target:
            matched.append(row)
            continue
        if industry.casefold() == target:
            matched.append(row)
    matched.sort(key=lambda r: float(r.get("percentage") or 0.0), reverse=True)
    return matched[: max(1, limit)]


def _sector_news(
    sector_name: str,
    question: str,
    *,
    window_days: int,
    query_log: QueryLogger | None,
) -> list[dict[str, Any]]:
    from news_rag.tools import run_layered_news

    result = run_layered_news(
        layer="sector_news",
        semantic_query=f"{sector_name} India sector earnings outlook",
        question=question,
        entity_filters=[sector_name],
        window_days=window_days,
        query_log=query_log,
    )
    if not result.get("ok"):
        return []
    articles = (result.get("data") or {}).get("articles") or []
    return [_slim_article(a) for a in articles[:5] if isinstance(a, dict)]


def analyze_sector_block(
    sector_name: str,
    holdings: list[dict[str, Any]],
    *,
    question: str,
    window: str,
    window_days: int,
    holdings_per_sector: int,
    query_log: QueryLogger | None,
) -> dict[str, Any]:
    meta = sector_index_entry(sector_name) or {}
    index_ticker = sector_yfinance_ticker(sector_name) or ""
    index_ret = index_return_pct(index_ticker, window) if index_ticker else None
    index_sign = return_sign(index_ret)
    nifty_ret = index_return_pct(nifty50_ticker(), window)
    sector_rows = holdings_in_sector(sector_name, holdings, limit=holdings_per_sector)
    sector_news = _sector_news(sector_name, question, window_days=window_days, query_log=query_log)

    aligned: list[dict[str, Any]] = []
    divergent: list[dict[str, Any]] = []

    for row in sector_rows:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        ret, status = holding_return_pct(name, window)
        h_sign = return_sign(ret) if status == "ok" else "unknown"
        entry: dict[str, Any] = {
            "holding": name,
            "weight_pct": row.get("percentage"),
            "return_pct": ret,
            "return_sign": h_sign,
            "price_status": status,
        }
        if signs_opposite(h_sign, index_sign):
            entry["news"] = fetch_dedicated_holding_news(
                name,
                question,
                window_days=window_days,
                query_log=query_log,
                limit=5,
            )
            divergent.append(entry)
        else:
            aligned.append(entry)

    return {
        "sector": sector_name,
        "nse_index_name": meta.get("nse_index_name"),
        "index_ticker": index_ticker,
        "index_return_pct": index_ret,
        "index_return_sign": index_sign,
        "nifty50_return_pct": nifty_ret,
        "proxy_note": meta.get("proxy_note"),
        "sector_news": sector_news,
        "aligned": aligned,
        "divergent": divergent,
    }


def run_sector_holding_alignment(
    detail: dict[str, Any],
    *,
    question: str,
    top_n: int = 5,
    sector_name: str = "",
    return_window: str = "",
    window_days: int | None = None,
    query_log: QueryLogger | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    if not detail:
        elapsed = (time.perf_counter() - started) * 1000
        return {"ok": False, "data": None, "error": "fund detail required", "elapsed_ms": elapsed}

    window = (return_window or "5d").strip() or "5d"
    wd = int(window_days or 30)
    holdings = extract_top_holdings(detail, limit=max(top_n * 4, 20))
    sectors = extract_top_sectors(detail, limit=top_n)
    sector_names: list[str] = []
    if sector_name.strip():
        mapped = sector_query_for_label(sector_name)
        sector_names.append(mapped[0] if mapped else sector_name.strip())
    else:
        for s in sectors:
            label = str(s.get("sector") or "").strip()
            if not label:
                continue
            mapped = sector_query_for_label(label)
            if mapped and sector_yfinance_ticker(mapped[0]):
                sector_names.append(mapped[0])
            if len(sector_names) >= top_n:
                break

    blocks: list[dict[str, Any]] = []
    for sec in sector_names:
        blocks.append(
            analyze_sector_block(
                sec,
                holdings,
                question=question,
                window=window,
                window_days=wd,
                holdings_per_sector=max(3, top_n),
                query_log=query_log,
            )
        )

    fund_name = str(detail.get("fund_short_name") or detail.get("fund_name") or "")
    elapsed = (time.perf_counter() - started) * 1000
    return {
        "ok": True,
        "data": {
            "fund_name": fund_name,
            "return_window": window,
            "window_days": wd,
            "sectors": blocks,
        },
        "error": "",
        "elapsed_ms": elapsed,
    }


SECTOR_ALIGNMENT_COMPOSER_ADDENDUM = """
SECTOR HOLDING ALIGNMENT (when Context includes sector_holding_alignment):
- Mention a sector index move only if the question is about that sector or the fund's main exposure.
- If proxy_note is present, say the index is a proxy in one clause.
- Skip aligned holdings unless the question asks who moved with the sector. One sentence can cover the group.
- Explain divergent holdings: name, return, and the news reason. Skip a divergent name that has no news and no return.
- Do not invent price moves; use only return_pct and signs from Context.
- For macro_sector_impact, use expected_sign and transmission. Say the effect depends when impact_type is mixed. Do not list every sector in the map — only sectors in the fund or named in the question.
"""
