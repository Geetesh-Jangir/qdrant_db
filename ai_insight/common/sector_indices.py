"""Sector index catalog and a health check that rejects one-day Yahoo history."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Literal

from ai_insight.common.config import load_config

Fit = Literal["exact", "proxy", "thematic", "weak"]


@dataclass
class IndexSpec:
    key: str
    display: str
    tickers: list[str]
    fit: Fit
    news_sectors: list[str]
    scope_note: str = ""


@dataclass
class OhlcBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    prev_close: float | None = None
    change_pct: float | None = None
    range_pct: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "prev_close": self.prev_close,
            "change_pct": self.change_pct,
            "range_pct": self.range_pct,
        }


@dataclass
class IndexSeries:
    spec: IndexSpec
    ticker: str
    bars: list[OhlcBar]
    week_change_pct: float | None = None
    today_change_pct: float | None = None
    stats: dict[str, Any] = field(default_factory=dict)


def catalog_path(root: Path | None = None) -> Path:
    data = root or load_config().data_dir
    return Path(data) / "_data" / "sector_index_catalog.json"


def load_catalog(path: Path | None = None, *, include_weak: bool = False) -> list[IndexSpec]:
    file = path or catalog_path()
    if not file.is_file():
        payload = DEFAULT_CATALOG
    else:
        payload = json.loads(file.read_text(encoding="utf-8"))
    grouped: dict[str, IndexSpec] = {}
    for row in payload["sectors"]:
        fit = row.get("fit") or "exact"
        if fit == "weak" and not include_weak:
            continue
        ticker = (row.get("tickers") or ["?"])[0]
        display = row.get("display") or row.get("group") or ticker
        # One card per index ticker (e.g. merge infra/cement/defence → single Nifty Infrastructure).
        key = f"{display}|{ticker}"
        current = grouped.get(key)
        if current is None:
            grouped[key] = IndexSpec(
                key=display.lower().replace(" ", "_"),
                display=display,
                tickers=list(row.get("tickers") or []),
                fit=fit,
                news_sectors=[row["sector"]],
                scope_note=row.get("scope_note") or "",
            )
        else:
            row_fit = row.get("fit") or "exact"
            if row_fit == "exact":
                if current.fit != "exact":
                    current.news_sectors = [row["sector"]]
                elif row["sector"] not in current.news_sectors:
                    current.news_sectors.insert(0, row["sector"])
                current.fit = "exact"  # type: ignore[misc]
                continue
            if current.fit == "exact" and row_fit != "exact":
                continue
            if row["sector"] not in current.news_sectors:
                current.news_sectors.append(row["sector"])
    return list(grouped.values())


def news_sectors_for_index(spec: IndexSpec) -> list[str]:
    """Qdrant sector entity names used for retrieval (proxies dropped in load_catalog)."""
    if spec.display == "Nifty IT":
        return ["It - Software"]
    return list(spec.news_sectors)


def series_is_usable(rows: list[dict[str, Any]], trading_date: date) -> tuple[bool, str]:
    closes = [row for row in rows if row.get("close") is not None]
    if len(closes) < 5:
        return False, f"{len(closes)} closes"
    last = str(closes[-1].get("date") or "")
    allowed = {trading_date.isoformat(), (trading_date - timedelta(days=1)).isoformat(), (trading_date - timedelta(days=3)).isoformat()}
    if last not in allowed:
        return False, f"last bar {last}"
    if len({round(float(row["close"]), 4) for row in closes[-5:]}) == 1:
        return False, "flat closes"
    return True, "ok"


def fetch_ohlc(spec: IndexSpec, end: date, sessions: int = 7, *, history: Callable[[str], list[dict[str, Any]]] | None = None) -> IndexSeries | None:
    loader = history or _yahoo
    chosen = None
    rows: list[dict[str, Any]] = []
    for ticker in spec.tickers:
        rows = loader(ticker)
        ok, _reason = series_is_usable(rows, end)
        if ok:
            chosen = ticker
            break
    if chosen is None:
        return None
    bars = _bars(rows)[-sessions:]
    if len(bars) < 2:
        return None
    week = round((bars[-1].close - bars[0].prev_close if bars[0].prev_close else bars[-1].close - bars[0].open) / (bars[0].prev_close or bars[0].open) * 100.0, 2)
    return IndexSeries(spec, chosen, bars, week_change_pct=week, today_change_pct=bars[-1].change_pct, stats=week_stats(bars, None))


def week_stats(bars: list[OhlcBar], benchmark: list[OhlcBar] | None) -> dict[str, Any]:
    if not bars:
        return {}
    changes = [(bar.date, bar.change_pct) for bar in bars if bar.change_pct is not None]
    best = max(changes, key=lambda item: item[1]) if changes else None
    worst = min(changes, key=lambda item: item[1]) if changes else None
    high = max(bar.high for bar in bars)
    low = min(bar.low for bar in bars)
    week = None
    base = bars[0].prev_close or bars[0].open
    if base:
        week = round((bars[-1].close - base) / base * 100.0, 2)
    relative = None
    if benchmark and benchmark[0].prev_close and week is not None:
        bench = round((benchmark[-1].close - (benchmark[0].prev_close or benchmark[0].open)) / (benchmark[0].prev_close or benchmark[0].open) * 100.0, 2)
        relative = round(week - bench, 2)
    return {
        "week_change_pct": week,
        "today_change_pct": bars[-1].change_pct,
        "best_day": None if best is None else {"date": best[0], "change_pct": best[1]},
        "worst_day": None if worst is None else {"date": worst[0], "change_pct": worst[1]},
        "week_high": high,
        "week_low": low,
        "vs_nifty_pp": relative,
    }


def _bars(rows: list[dict[str, Any]]) -> list[OhlcBar]:
    ordered = sorted(rows, key=lambda row: str(row.get("date")))
    bars: list[OhlcBar] = []
    prev = None
    for row in ordered:
        close = float(row["close"])
        change = None if not prev else round((close - prev) / prev * 100.0, 2)
        high = float(row.get("high") or close)
        low = float(row.get("low") or close)
        bars.append(OhlcBar(str(row["date"]), float(row.get("open") or close), high, low, close, prev, change, None if not close else round((high - low) / close * 100.0, 2)))
        prev = close
    return bars


def _yahoo(ticker: str) -> list[dict[str, Any]]:
    from ai_insight.common.yahoo_live import history_closes

    return history_closes(ticker, period="1mo")


DEFAULT_CATALOG: dict[str, Any] = {
    "sectors": [
        {"sector": "Banks", "tickers": ["^NSEBANK"], "fit": "exact", "group": "bank", "display": "Nifty Bank"},
        {"sector": "It - Software", "tickers": ["^CNXIT"], "fit": "exact", "group": "it", "display": "Nifty IT"},
        {"sector": "Automobiles", "tickers": ["^CNXAUTO"], "fit": "exact", "group": "auto", "display": "Nifty Auto"},
        {"sector": "Auto Components", "tickers": ["^CNXAUTO"], "fit": "proxy", "group": "auto", "display": "Nifty Auto"},
        {"sector": "Agricultural, Commercial & Construction Vehicles", "tickers": ["^CNXAUTO"], "fit": "proxy", "group": "auto", "display": "Nifty Auto"},
        {"sector": "Diversified Fmcg", "tickers": ["^CNXFMCG"], "fit": "exact", "group": "fmcg", "display": "Nifty FMCG"},
        {"sector": "Food Products", "tickers": ["^CNXFMCG"], "fit": "proxy", "group": "fmcg", "display": "Nifty FMCG"},
        {"sector": "Beverages", "tickers": ["^CNXFMCG"], "fit": "proxy", "group": "fmcg", "display": "Nifty FMCG"},
        {"sector": "Retailing", "tickers": ["^CNXFMCG"], "fit": "weak", "group": "fmcg", "display": "Nifty FMCG", "scope_note": "FMCG proxy; Nifty Retail not on Yahoo."},
        {"sector": "Pharmaceuticals & Biotechnology", "tickers": ["^CNXPHARMA"], "fit": "exact", "group": "pharma", "display": "Nifty Pharma"},
        {"sector": "Healthcare Services", "tickers": ["^CNXPHARMA"], "fit": "proxy", "group": "pharma", "display": "Nifty Pharma", "scope_note": "Pharma index proxy for hospital operators."},
        {"sector": "Ferrous Metals", "tickers": ["^CNXMETAL"], "fit": "exact", "group": "metal", "display": "Nifty Metal"},
        {"sector": "Non - Ferrous Metals", "tickers": ["^CNXMETAL"], "fit": "exact", "group": "metal", "display": "Nifty Metal"},
        {"sector": "Realty", "tickers": ["^CNXREALTY"], "fit": "exact", "group": "realty", "display": "Nifty Realty"},
        {"sector": "Petroleum Products", "tickers": ["^CNXENERGY"], "fit": "thematic", "group": "energy", "display": "Nifty Energy"},
        {"sector": "Power", "tickers": ["^CNXENERGY"], "fit": "thematic", "group": "energy", "display": "Nifty Energy", "scope_note": "Energy index proxy for power utilities."},
        {"sector": "Construction", "tickers": ["^CNXINFRA"], "fit": "thematic", "group": "infra", "display": "Nifty Infrastructure"},
        {"sector": "Cement & Cement Products", "tickers": ["^CNXINFRA"], "fit": "thematic", "group": "cement", "display": "Nifty Infrastructure", "scope_note": "Infrastructure proxy; Nifty Cement not on Yahoo."},
        {"sector": "Industrial Products", "tickers": ["^CNXINFRA"], "fit": "thematic", "group": "infra", "display": "Nifty Infrastructure", "scope_note": "Infrastructure / capital-goods proxy."},
        {"sector": "Electrical Equipment", "tickers": ["^CNXINFRA"], "fit": "thematic", "group": "infra", "display": "Nifty Infrastructure"},
        {"sector": "Transport Services", "tickers": ["^CNXINFRA"], "fit": "thematic", "group": "infra", "display": "Nifty Infrastructure", "scope_note": "Infrastructure / logistics proxy."},
        {"sector": "Finance", "tickers": ["NIFTY_FIN_SERVICE.NS"], "fit": "exact", "group": "financials", "display": "Nifty Financial Services"},
        {"sector": "Capital Markets", "tickers": ["NIFTY_FIN_SERVICE.NS"], "fit": "proxy", "group": "financials", "display": "Nifty Financial Services"},
        {"sector": "Insurance", "tickers": ["NIFTY_FIN_SERVICE.NS"], "fit": "proxy", "group": "financials", "display": "Nifty Financial Services", "scope_note": "Financial services index includes listed insurers."},
        {"sector": "Financial Technology (fintech)", "tickers": ["NIFTY_FIN_SERVICE.NS"], "fit": "proxy", "group": "financials", "display": "Nifty Financial Services"},
        {"sector": "Consumer Durables", "tickers": ["^CNXFMCG"], "fit": "weak", "group": "durables", "display": "Nifty FMCG", "scope_note": "FMCG proxy; consumer durables index not on Yahoo."},
        {"sector": "Chemicals & Petrochemicals", "tickers": ["^CNXCMDT", "^CNXFMCG"], "fit": "weak", "group": "chemicals", "display": "Nifty Commodities", "scope_note": "Commodities index when available; else FMCG proxy."},
        {"sector": "Telecom - Services", "tickers": ["^CNXIT"], "fit": "proxy", "group": "telecom", "display": "Nifty IT", "scope_note": "IT index proxy; Nifty Telecommunications not on Yahoo."},
        {"sector": "Aerospace & Defense", "tickers": ["^CNXINFRA"], "fit": "thematic", "group": "defence", "display": "Nifty Infrastructure", "scope_note": "Infrastructure proxy; Nifty India Defence not on Yahoo."},
        {"sector": "Leisure Services", "tickers": ["^CNXFMCG"], "fit": "weak", "group": "leisure", "display": "Nifty FMCG", "scope_note": "FMCG proxy; Nifty Consumer Services not on Yahoo."},
    ]
}
