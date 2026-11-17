"""Build top-100 holdings JSON and yfinance availability report."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
AGG_CSV = ROOT / "aggregated_holdings.csv"
MASTER_JSON = ROOT / "security-master-list.json"
OUT_HOLDINGS = ROOT / "top_100_holdings.json"
OUT_YF_REPORT = ROOT / "top_100_holdings_yfinance_report.json"


def normalize_name(name: str) -> str:
    s = (name or "").lower()
    s = re.sub(r"\[.*?\]", " ", s)
    s = s.replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\bthe\b", "", s)
    s = re.sub(r"\benterprises\b", "enterprise", s)
    s = re.sub(r"\b(limited|ltd|ltd\.|co\.?|company|corporation|corp)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_master_index(items: list[dict]) -> dict[str, list[dict]]:
    by_norm: dict[str, list[dict]] = {}
    for row in items:
        key = normalize_name(row.get("companyName") or "")
        if not key:
            continue
        by_norm.setdefault(key, []).append(row)
    return by_norm


def lookup_master(by_norm: dict[str, list[dict]], instrument_name: str) -> dict | None:
    norm = normalize_name(instrument_name)
    if norm in by_norm:
        return pick_best_master(by_norm[norm])
    candidates: list[tuple[int, dict]] = []
    for key, rows in by_norm.items():
        if norm in key or key in norm:
            candidates.append((max(len(norm), len(key)), pick_best_master(rows) or {}))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1] or None


def pick_best_master(rows: list[dict]) -> dict | None:
    if not rows:
        return None

    def score(r: dict) -> tuple:
        sym = (r.get("symbol") or "").upper()
        st = (r.get("status") or "").lower()
        active = 1 if st == "active" else 0
        no_pp = 1 if not sym.endswith("PP") else 0
        has_idx = 1 if r.get("indiceName") else 0
        return (active, no_pp, has_idx)

    return max(rows, key=score)


def resolve_yf_ticker(symbol: str | None, scrip_code: str | None) -> list[str]:
    tickers: list[str] = []
    if symbol and str(symbol).strip():
        sym = str(symbol).strip().upper()
        if sym.endswith(".NS") or sym.endswith(".BO"):
            tickers.append(sym)
        else:
            tickers.append(f"{sym}.NS")
            tickers.append(f"{sym}.BO")
    # Yahoo does not take NSE numeric scrip; keep as last resort only if it looks like a bare symbol
    if scrip_code and str(scrip_code).strip() and not tickers:
        sc = str(scrip_code).strip()
        if sc.isalpha():
            tickers.append(f"{sc.upper()}.NS")
    return tickers


def check_yfinance(tickers: list[str]) -> dict:
    try:
        import yfinance as yf
    except ImportError:
        return {"ok": False, "error": "yfinance not installed", "ticker_used": None, "fields": {}}

    for t in tickers:
        try:
            ticker = yf.Ticker(t)
            hist = ticker.history(period="5d")
            if hist is None or hist.empty:
                continue
            info = {}
            try:
                raw = ticker.info or {}
            except Exception:
                raw = {}
            for k in (
                "symbol",
                "shortName",
                "longName",
                "sector",
                "industry",
                "currency",
                "exchange",
                "marketCap",
                "regularMarketPrice",
                "regularMarketPreviousClose",
                "fiftyTwoWeekHigh",
                "fiftyTwoWeekLow",
                "trailingPE",
                "priceToBook",
                "dividendYield",
                "beta",
            ):
                if k in raw and raw[k] is not None:
                    info[k] = raw[k]
            close = hist["Close"].dropna()
            if not close.empty:
                info["latestClose"] = float(close.iloc[-1])
                info["latestCloseDate"] = str(close.index[-1].date())
            return {
                "ok": True,
                "ticker_used": t,
                "history_bars": int(len(hist)),
                "fields": info,
            }
        except Exception as exc:
            last_err = str(exc)[:200]
            continue
    return {"ok": False, "error": last_err if "last_err" in dir() else "no data", "ticker_used": None, "fields": {}}


def main() -> int:
    df = pd.read_csv(AGG_CSV)
    df["norm"] = df["instrument_name"].map(normalize_name)
    df = df.groupby("norm", as_index=False).agg(
        instrument_name=("instrument_name", "first"),
        industry=("industry", "first"),
        fund_count=("fund_count", "sum"),
    )
    df = df.sort_values("fund_count", ascending=False).head(100)
    top = df

    with MASTER_JSON.open(encoding="utf-8") as f:
        master = json.load(f)
    by_norm = load_master_index(master["items"])

    holdings: list[dict] = []
    yf_rows: list[dict] = []

    for _, row in top.iterrows():
        instrument_name = str(row["instrument_name"]).strip()
        sector_name = str(row["industry"]).strip() if pd.notna(row["industry"]) else None
        master_row = lookup_master(by_norm, instrument_name)

        entry = {
            "instrument_name": instrument_name,
            "sector_name": sector_name,
            "indiceName": master_row.get("indiceName") if master_row else None,
            "scripCode": master_row.get("scripCode") if master_row else None,
            "symbol": master_row.get("symbol") if master_row else None,
            "status": master_row.get("status") if master_row else None,
        }
        holdings.append(entry)

        tickers = resolve_yf_ticker(entry["symbol"], entry["scripCode"])
        yf = check_yfinance(tickers)
        yf_rows.append(
            {
                "instrument_name": instrument_name,
                "symbol": entry["symbol"],
                "scripCode": entry["scripCode"],
                "tickers_tried": tickers,
                "yfinance_available": yf["ok"],
                "yfinance_ticker": yf.get("ticker_used"),
                "yfinance_error": None if yf["ok"] else yf.get("error"),
                "yfinance_fields": yf.get("fields") or {},
            }
        )
        print(f"{'OK' if yf['ok'] else 'MISS'} {instrument_name} -> {yf.get('ticker_used') or tickers}")

    payload = {
        "source": str(AGG_CSV.name),
        "security_master": str(MASTER_JSON.name),
        "count": len(holdings),
        "items": holdings,
    }
    OUT_HOLDINGS.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    ok = [r for r in yf_rows if r["yfinance_available"]]
    miss = [r for r in yf_rows if not r["yfinance_available"]]
    sample_fields = sorted({k for r in ok for k in r["yfinance_fields"]})

    report = {
        "summary": {
            "total": len(yf_rows),
            "yfinance_ok": len(ok),
            "yfinance_missing": len(miss),
            "field_keys_seen_when_ok": sample_fields,
        },
        "yfinance_ok": [
            {
                "instrument_name": r["instrument_name"],
                "symbol": r["symbol"],
                "yfinance_ticker": r["yfinance_ticker"],
            }
            for r in ok
        ],
        "yfinance_missing": [
            {
                "instrument_name": r["instrument_name"],
                "symbol": r["symbol"],
                "scripCode": r["scripCode"],
                "tickers_tried": r["tickers_tried"],
                "error": r["yfinance_error"],
            }
            for r in miss
        ],
        "details": yf_rows,
    }
    OUT_YF_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUT_HOLDINGS} and {OUT_YF_REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())