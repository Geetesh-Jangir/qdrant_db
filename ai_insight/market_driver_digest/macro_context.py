"""Load local _data files and sector 7d series for market_driver_digest. Math only."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from ai_insight.common.flows import cumulative, history_path, load_flow_history
from ai_insight.common.sector_indices import fetch_ohlc, load_catalog
from ai_insight.data.twelve_data_brent import history_path as brent_history_path


GSEC_CSV_NAME = "India 10-Year Bond Yield Historical Data.csv"
CPI_XLSX_NAME = "cpi_inflation_data.xlsx"


def build_digest_datasets(ctx) -> dict[str, Any]:
    root = ctx.config.data_dir / "_data"
    trading = ctx.trading_date.isoformat()
    year = ctx.trading_date.year
    limits: list[str] = []

    sector_indices_7d = _sector_indices_7d(ctx)
    if not sector_indices_7d:
        limits.append("sector_indices_7d: no usable index series")

    fii_dii = _fii_dii_7d(ctx, limits)
    gsec_10y = _gsec_7d(root, limits)
    cpi_ytd = _cpi_ytd(root, year, limits)
    brent_usd = _brent_usd(ctx.config.data_dir, trading, limits)

    sector_rank_week = sorted(
        [row for row in sector_indices_7d if row.get("week_change_pct") is not None],
        key=lambda r: r.get("week_change_pct") or 0,
        reverse=True,
    )

    return {
        "sector_indices_7d": sector_indices_7d,
        "sector_rank_week": [
            {
                "display": row.get("display"),
                "ticker": row.get("ticker"),
                "week_change_pct": row.get("week_change_pct"),
            }
            for row in sector_rank_week
        ],
        "fii_dii": fii_dii,
        "gsec_10y": gsec_10y,
        "cpi_ytd": cpi_ytd,
        "brent_usd": brent_usd,
        "data_limitations": limits,
    }


def _sector_indices_7d(ctx) -> list[dict[str, Any]]:
    specs = load_catalog(include_weak=ctx.config.include_weak_index)
    out: list[dict[str, Any]] = []
    for spec in specs:
        series = fetch_ohlc(spec, ctx.trading_date, sessions=7)
        if series is None:
            continue
        daily = [bar.as_dict() for bar in series.bars]
        out.append(
            {
                "display": spec.display,
                "ticker": series.ticker,
                "fit": spec.fit,
                "scope_note": spec.scope_note or "",
                "week_change_pct": series.week_change_pct,
                "today_change_pct": series.today_change_pct,
                "daily": daily,
            }
        )
    return out


def _fii_dii_7d(ctx, limits: list[str]) -> dict[str, Any]:
    path = history_path(ctx.config.data_dir)
    history = load_flow_history(path)
    if not path.is_file():
        limits.append("fii_dii: history file missing")
        return {"rows": [], "sum_7d_fii": None, "sum_7d_dii": None, "provisional": False}
    rows_raw = _read_fii_rows(path)
    provisional = any(r.get("provisional") for r in rows_raw)
    if provisional:
        limits.append("fii_dii: rows marked provisional")
    last_7 = history[-7:] if len(history) > 7 else list(history)
    rows = [
        {
            "date": day.date,
            "fii_net": day.fii_net,
            "dii_net": day.dii_net,
            "source": day.source,
        }
        for day in last_7
    ]
    sum_fii = cumulative(history, min(7, len(history)), "fii_net") if history else None
    sum_dii = cumulative(history, min(7, len(history)), "dii_net") if history else None
    if len(last_7) < 7:
        limits.append(f"fii_dii: only {len(last_7)} dates in history (requested 7)")
    return {
        "rows": rows,
        "sum_7d_fii": sum_fii,
        "sum_7d_dii": sum_dii,
        "provisional": provisional,
        "source": str(path),
    }


def _read_fii_rows(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, dict)]


def _gsec_7d(root: Path, limits: list[str]) -> dict[str, Any]:
    path = root / GSEC_CSV_NAME
    if not path.is_file():
        limits.append("gsec_10y: CSV missing")
        return {"daily": [], "change_bp_7d": None, "source": ""}
    rows = _parse_gsec_csv(path)
    if not rows:
        limits.append("gsec_10y: no rows parsed")
        return {"daily": [], "change_bp_7d": None, "source": str(path)}
    daily = rows[:7]
    daily.reverse()
    change_bp = None
    if len(daily) >= 2:
        change_bp = round((daily[-1]["yield_pct"] - daily[0]["yield_pct"]) * 100, 1)
    return {
        "daily": daily,
        "change_bp_7d": change_bp,
        "latest_yield_pct": daily[-1]["yield_pct"] if daily else None,
        "latest_date": daily[-1]["date"] if daily else None,
        "source": str(path),
        "unit": "percent_yield",
    }


def _parse_gsec_csv(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw_date = (row.get("Date") or "").strip().strip('"')
            price = _num(row.get("Price"))
            if not raw_date or price is None:
                continue
            iso = _ddmmyyyy_to_iso(raw_date)
            if not iso:
                continue
            out.append({"date": iso, "yield_pct": price})
    out.sort(key=lambda r: r["date"], reverse=True)
    return out


def _ddmmyyyy_to_iso(raw: str) -> str:
    try:
        return datetime.strptime(raw, "%d-%m-%Y").date().isoformat()
    except ValueError:
        return ""


def _cpi_ytd(root: Path, year: int, limits: list[str]) -> dict[str, Any]:
    path = root / CPI_XLSX_NAME
    if not path.is_file():
        limits.append("cpi_ytd: xlsx missing")
        return {"rows": [], "change_pp_latest": None}
    try:
        import pandas as pd

        df = pd.read_excel(path)
    except Exception as exc:
        limits.append(f"cpi_ytd: read failed ({type(exc).__name__})")
        return {"rows": [], "change_pp_latest": None}
    date_col = "Date" if "Date" in df.columns else df.columns[0]
    val_col = "cpi headline inflation" if "cpi headline inflation" in df.columns else df.columns[1]
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        ts = row.get(date_col)
        if ts is None or (hasattr(ts, "year") and ts.year != year):
            continue
        yoy = _num(row.get(val_col))
        if yoy is None:
            continue
        month_date = ts.date().isoformat()[:10] if hasattr(ts, "date") else str(ts)[:10]
        rows.append({"date": month_date, "headline_yoy_pct": yoy})
    rows.sort(key=lambda r: r["date"])
    change_pp = None
    if len(rows) >= 2:
        change_pp = round(rows[-1]["headline_yoy_pct"] - rows[-2]["headline_yoy_pct"], 2)
    if not rows:
        limits.append(f"cpi_ytd: no rows for calendar year {year}")
    return {
        "rows": rows,
        "latest_yoy_pct": rows[-1]["headline_yoy_pct"] if rows else None,
        "latest_date": rows[-1]["date"] if rows else None,
        "change_pp_latest": change_pp,
        "source": str(path),
        "frequency": "monthly",
    }


def _brent_usd(data_dir: Path, trading: str, limits: list[str]) -> dict[str, Any]:
    path = brent_history_path(data_dir)
    root = data_dir / "_data"
    if not path.is_file():
        path = root / "xbr_usd_history.json"
    if not path.is_file():
        limits.append("brent_usd: history json missing")
        return {"horizons": {}, "daily_tail": []}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        limits.append("brent_usd: invalid json shape")
        return {"horizons": {}, "daily_tail": []}
    series = sorted(
        [r for r in raw if isinstance(r, dict) and r.get("date") and _num(r.get("close")) is not None],
        key=lambda r: str(r["date"]),
    )
    if not series:
        limits.append("brent_usd: empty series")
        return {"horizons": {}, "daily_tail": []}
    last = series[-1]
    latest_close = _num(last.get("close"))
    latest_date = str(last["date"])
    if latest_date < trading:
        limits.append(f"brent_usd: last observation {latest_date} before trading_date {trading}")
    horizons = _brent_horizons(series, latest_close, latest_date)
    daily_tail = [
        {"date": str(r["date"]), "close_usd": _num(r.get("close"))}
        for r in series[-7:]
    ]
    meta = series[-1]
    return {
        "benchmark": meta.get("requested_symbol") or "XBR/USD",
        "symbol_used": meta.get("symbol"),
        "unit": meta.get("unit") or "usd",
        "latest_close_usd": latest_close,
        "latest_date": latest_date,
        "horizons_pct": horizons,
        "daily_tail": daily_tail,
        "source": str(path),
    }


def _brent_horizons(series: list[dict], latest_close: float | None, latest_date: str) -> dict[str, float | None]:
    if latest_close is None or not latest_date:
        return {}
    end = date.fromisoformat(latest_date[:10])
    anchors = {"7d": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365}
    out: dict[str, float | None] = {}
    by_date = {str(r["date"])[:10]: _num(r.get("close")) for r in series}
    dates_sorted = sorted(by_date.keys())
    for label, days_back in anchors.items():
        target = (end - timedelta(days=days_back)).isoformat()
        ref_close = _closest_close_on_or_before(dates_sorted, by_date, target)
        if ref_close is None or ref_close == 0:
            out[label] = None
        else:
            out[label] = round((latest_close - ref_close) / ref_close * 100.0, 2)
    return out


def _closest_close_on_or_before(dates_sorted: list[str], by_date: dict[str, float | None], target: str) -> float | None:
    chosen = None
    for d in dates_sorted:
        if d <= target:
            chosen = d
        else:
            break
    if chosen is None and dates_sorted:
        chosen = dates_sorted[0]
    return None if chosen is None else by_date.get(chosen)


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, str):
            value = value.replace("%", "").strip()
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None