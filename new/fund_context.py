"""Per-fund facts: holdings, NAV, drivers, cushioners."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from historical_data.nav_service import fetch_raw_nav_history
from news_rag.fund_search import get_fund_index
from new.sector_clusters import detect_sector_clusters
from new.sector_news import news_for_sector_clusters
from new.stock_news import news_for_movers

from new.nav_settled import nav_change_1w_settled, nav_daily_week_settled
from new.portfolio_equity import FundRow
from new.security_master import lookup_instrument
from new.week_window import EQUITY_WEEK_DAYS
from new.yf_week import stock_change_1w_settled, stock_daily_week_settled

TOP_MOVER_COUNT = 5


def holding_impact_1w(weight_pct: float, change_1w_pct: float | None) -> float | None:
    if change_1w_pct is None:
        return None
    return round(float(weight_pct) * float(change_1w_pct) / 100.0, 3)


def _fmt_signed_pct(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def attribution_summary(
    holdings: list[dict[str, Any]],
    nav_1w_pct: float | None,
) -> dict[str, Any]:
    explained = round(
        sum(float(h["impact_1w_pct"]) for h in holdings if h.get("impact_1w_pct") is not None),
        3,
    )
    priced_weight = round(
        sum(float(h.get("percentage") or 0.0) for h in holdings if h.get("impact_1w_pct") is not None),
        2,
    )
    positive = round(
        sum(float(h["impact_1w_pct"]) for h in holdings if (h.get("impact_1w_pct") or 0) > 0),
        3,
    )
    negative = round(
        sum(float(h["impact_1w_pct"]) for h in holdings if (h.get("impact_1w_pct") or 0) < 0),
        3,
    )
    residual: float | None = None
    justification_pct: float | None = None
    unaccounted_pct: float | None = None
    summary_line = ""
    if nav_1w_pct is not None:
        residual = round(float(nav_1w_pct) - explained, 3)
        if abs(float(nav_1w_pct)) >= 0.01:
            justification_pct = round(100.0 * explained / float(nav_1w_pct), 1)
        unaccounted_pct = round(100.0 - (justification_pct or 0.0), 1) if justification_pct is not None else None
        summary_line = (
            f"Fund NAV moved {_fmt_signed_pct(float(nav_1w_pct))} over the last week; "
            f"top gainers & losers account for {_fmt_signed_pct(explained)} net impact "
            f"({justification_pct or 0}% of the NAV move, "
            f"{_fmt_signed_pct(residual)} still unaccounted)."
        )
    return {
        "nav_1w_pct": nav_1w_pct,
        "total_stock_impact_1w_pct": explained,
        "explained_1w_pct": explained,
        "residual_1w_pct": residual,
        "unaccounted_nav_move_pct": unaccounted_pct,
        "justification_pct": justification_pct,
        "positive_impact_sum_pct": positive,
        "negative_impact_sum_pct": negative,
        "priced_holdings_weight_pct": priced_weight,
        "summary_line": summary_line,
    }


def split_gainers_losers(
    holdings: list[dict[str, Any]],
    *,
    limit: int = TOP_MOVER_COUNT,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    priced = [h for h in holdings if h.get("impact_1w_pct") is not None]
    gainers = sorted(
        [h for h in priced if float(h["impact_1w_pct"]) > 0],
        key=lambda r: -float(r["impact_1w_pct"]),
    )
    losers = sorted(
        [h for h in priced if float(h["impact_1w_pct"]) < 0],
        key=lambda r: float(r["impact_1w_pct"]),
    )
    cap = max(1, min(int(limit or TOP_MOVER_COUNT), 20))
    return gainers[:cap], losers[:cap]


def _equity_holdings_from_detail(detail: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not detail:
        return []
    raw = detail.get("holdings")
    rows: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for name, meta in raw.items():
            if not isinstance(meta, dict):
                continue
            rating = str(meta.get("rating") or "").strip().lower()
            if rating != "equity":
                continue
            pct = float(meta.get("percentage") or 0.0)
            if pct <= 1.0:
                continue
            rows.append(
                {
                    "instrument_name": str(name).strip(),
                    "percentage": pct,
                    "industry": str(meta.get("industry") or "").strip(),
                }
            )
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            rating = str(item.get("rating") or "").strip().lower()
            if rating != "equity":
                continue
            pct = float(item.get("percentage") or 0.0)
            if pct <= 1.0:
                continue
            name = str(
                item.get("instrument_name") or item.get("company_name") or item.get("name") or ""
            ).strip()
            if name:
                rows.append(
                    {
                        "instrument_name": name,
                        "percentage": pct,
                        "industry": str(item.get("industry") or "").strip(),
                    }
                )
    rows.sort(key=lambda r: -float(r.get("percentage") or 0))
    return rows


def _fund_return_1w_api(detail: dict[str, Any] | None) -> float | None:
    if not detail:
        return None
    rets = detail.get("returns") if isinstance(detail.get("returns"), dict) else {}
    raw = rets.get("1w")
    try:
        return round(float(raw), 2) if raw is not None else None
    except (TypeError, ValueError):
        return None


@dataclass
class FundFacts:
    isin: str
    scheme_name: str
    portfolio_pct: float
    nav_1w_pct: float | None
    nav_sentiment: str
    fund_api_1w_pct: float | None
    holdings: list[dict[str, Any]] = field(default_factory=list)
    drivers: list[dict[str, Any]] = field(default_factory=list)
    cushioned_by: list[dict[str, Any]] = field(default_factory=list)
    stock_news: list[dict[str, Any]] = field(default_factory=list)
    sector_clusters: list[dict[str, Any]] = field(default_factory=list)
    sector_news: list[dict[str, Any]] = field(default_factory=list)
    limits: list[str] = field(default_factory=list)
    attribution: dict[str, Any] = field(default_factory=dict)
    gainers: list[dict[str, Any]] = field(default_factory=list)
    losers: list[dict[str, Any]] = field(default_factory=list)
    nav_daily: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "isin": self.isin,
            "scheme_name": self.scheme_name,
            "portfolio_pct": self.portfolio_pct,
            "nav_1w_pct": self.nav_1w_pct,
            "nav_sentiment": self.nav_sentiment,
            "fund_api_1w_pct": self.fund_api_1w_pct,
            "holdings": self.holdings,
            "attribution": self.attribution,
            "gainers": self.gainers,
            "losers": self.losers,
            "drivers": self.drivers,
            "cushioned_by": self.cushioned_by,
            "stock_news": self.stock_news,
            "sector_clusters": self.sector_clusters,
            "sector_news": self.sector_news,
            "nav_daily": self.nav_daily,
            "limits": self.limits,
        }


def _daily_prices_for_holding(row: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    name = str(row.get("instrument_name") or "")
    ticker = row.get("ticker")
    if not ticker:
        return name, []
    return name, stock_daily_week_settled(str(ticker))


def _attach_daily_bars(holdings: list[dict[str, Any]]) -> None:
    if not holdings:
        return
    workers = min(6, len(holdings))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_daily_prices_for_holding, h): h for h in holdings}
        for fut in as_completed(futs):
            row = futs[fut]
            try:
                _, daily = fut.result()
            except Exception:
                daily = []
            row["daily_prices"] = daily


def nav_1w_for_isin(isin: str) -> float | None:
    records = fetch_raw_nav_history(isin)
    stats = nav_change_1w_settled(records)
    if not stats:
        return None
    return float(stats.get("change_pct"))


def cushion_funds(
    current: FundRow,
    nav_by_isin: dict[str, float | None],
    all_funds: list[FundRow],
    current_nav_1w: float | None,
) -> list[dict[str, Any]]:
    others: list[dict[str, Any]] = []
    for row in all_funds:
        if row.isin == current.isin:
            continue
        nav = nav_by_isin.get(row.isin)
        if nav is None or nav <= 0:
            continue
        others.append(
            {
                "scheme_name": row.scheme_name,
                "isin": row.isin,
                "nav_1w_pct": nav,
                "portfolio_pct": row.portfolio_pct,
            }
        )
    others.sort(key=lambda r: -float(r["nav_1w_pct"]))
    if current_nav_1w is not None and current_nav_1w < 0:
        return others
    return others[:5]


def select_drivers(
    gainers: list[dict[str, Any]],
    losers: list[dict[str, Any]],
    sentiment: str,
) -> list[dict[str, Any]]:
    if sentiment == "positive":
        return list(gainers)
    return list(losers)


def build_fund_facts(
    fund: FundRow,
    all_funds: list[FundRow],
    nav_by_isin: dict[str, float | None],
    *,
    fetch_news: bool = True,
    dry_run: bool = False,
) -> FundFacts:
    limits: list[str] = []
    index = get_fund_index()
    detail = index.fetch_fund_detail_from_api(fund.isin)
    if not detail:
        limits.append(f"fund_api:{fund.isin}")

    nav_records = fetch_raw_nav_history(fund.isin)
    nav_daily = nav_daily_week_settled(nav_records)
    nav_stats = nav_change_1w_settled(nav_records)
    nav_1w = nav_by_isin.get(fund.isin)
    if nav_1w is None and nav_stats:
        nav_1w = float(nav_stats["change_pct"])
    elif nav_1w is None:
        nav_1w = nav_1w_for_isin(fund.isin)
    sentiment = "positive" if (nav_1w is not None and nav_1w >= 0) else "negative"

    holding_rows = _equity_holdings_from_detail(detail)
    enriched: list[dict[str, Any]] = []
    for h in holding_rows:
        name = h["instrument_name"]
        mapped = lookup_instrument(name)
        change: float | None = None
        ticker_used: str | None = None
        if mapped and mapped.get("tickers"):
            for t in mapped["tickers"]:
                change = stock_change_1w_settled(t)
                if change is not None:
                    ticker_used = t
                    break
        else:
            limits.append(f"no_master:{name}")
        impact = holding_impact_1w(h["percentage"], change)
        enriched.append(
            {
                **h,
                "change_1w_pct": change,
                "impact_1w_pct": impact,
                "ticker": ticker_used,
                "symbol": (mapped or {}).get("symbol"),
            }
        )

    _attach_daily_bars(enriched)
    gainers, losers = split_gainers_losers(enriched, limit=TOP_MOVER_COUNT)
    top_movers = gainers + losers
    clusters, cluster_limits = detect_sector_clusters(gainers, losers)
    limits.extend(cluster_limits)
    sector_clusters_serialized = [c.to_dict() for c in clusters]
    attribution = attribution_summary(top_movers, nav_1w)
    drivers = select_drivers(gainers, losers, sentiment)
    stock_news: list[dict[str, Any]] = []
    sector_news: list[dict[str, Any]] = []
    if fetch_news and not dry_run:
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_stock = pool.submit(
                news_for_movers,
                gainers,
                losers,
                fund_name=fund.scheme_name,
                window_days=EQUITY_WEEK_DAYS,
                per_stock=8,
            )
            fut_sector = pool.submit(
                news_for_sector_clusters,
                clusters,
                fund_name=fund.scheme_name,
                window_days=EQUITY_WEEK_DAYS,
                allow_extended_window=False,
            )
            try:
                stock_news = fut_stock.result()
            except Exception:
                stock_news = []
                limits.append("stock_news_failed")
            try:
                sector_news = fut_sector.result()
            except Exception:
                sector_news = []
                limits.append("sector_news_failed")
        for block in sector_news:
            if not block.get("usable_news"):
                sk = block.get("sector_key") or "unknown"
                limits.append(f"sector_news_empty:{sk}")
        movers_daily = [
            {
                "instrument_name": h["instrument_name"],
                "change_1w_pct": h.get("change_1w_pct"),
                "move": "up" if float(h.get("change_1w_pct") or 0) >= 0 else "down",
                "daily_prices": h.get("daily_prices") or [],
            }
            for h in top_movers
        ]
        by_name = {h["instrument_name"]: h for h in top_movers}
        for block in stock_news:
            block["fund_nav_daily"] = nav_daily
            block["movers_daily"] = movers_daily
            row = by_name.get(block.get("instrument_name") or "")
            if row:
                block["daily_prices"] = row.get("daily_prices") or []

    cushioned = cushion_funds(fund, nav_by_isin, all_funds, nav_1w)

    return FundFacts(
        isin=fund.isin,
        scheme_name=fund.scheme_name,
        portfolio_pct=fund.portfolio_pct,
        nav_1w_pct=nav_1w,
        nav_sentiment=sentiment,
        fund_api_1w_pct=_fund_return_1w_api(detail),
        holdings=top_movers,
        attribution=attribution,
        gainers=gainers,
        losers=losers,
        drivers=drivers,
        cushioned_by=cushioned,
        stock_news=stock_news,
        sector_clusters=sector_clusters_serialized,
        sector_news=sector_news,
        nav_daily=nav_daily,
        limits=limits,
    )