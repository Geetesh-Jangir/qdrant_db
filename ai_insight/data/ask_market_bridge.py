"""Numeric market data used by ask-a-question (read-only wrappers; sources stay in news_rag / historical_data)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_insight.data.base import NumericRecord, unavailable

SOURCE_GOLD = "rupeestop:gold_24k"
SOURCE_ASK = "ask_market_bridge"


def fetch_gold_record() -> NumericRecord:
    entity = "Macro - Gold"
    from historical_data.gold_service import get_gold_snapshot

    snap = get_gold_snapshot(windows=["1M"])
    if not snap.get("available"):
        return unavailable(entity, SOURCE_GOLD, str(snap.get("error") or snap.get("message") or "unavailable")[:240])
    latest = snap.get("latest") or {}
    price = latest.get("price_24k_10g")
    if price is None:
        return unavailable(entity, SOURCE_GOLD, "no latest price")
    change = ((snap.get("returns") or {}).get("1M") or {}).get("pct")
    return NumericRecord(
        entity,
        str(latest.get("as_of") or ""),
        float(price),
        float(change) if change is not None else None,
        "inr_per_10g_24k",
        SOURCE_GOLD,
        "ok",
        "India 24K gold; 1M return may be approximate on month-end basis",
    )


def get_ask_market_snapshot(*, window_days: int = 30) -> dict[str, Any]:
    """Structured bundle mirroring get_market_snapshot slices (for ai_insight JSON export)."""
    from news_rag.insight.layer_tools import run_index_return_tool, run_macro_series_tool

    wd = max(1, min(365, int(window_days)))
    macro = run_macro_series_tool({"window_days": wd, "series": ["crude", "wti", "usdinr", "gold", "yield"]})
    series_by_key: dict[str, Any] = {}
    for row in (macro.get("data") or {}).get("series") or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get("series") or "")
        if key == "crude":
            series_by_key["brent"] = row
        elif key == "yield":
            series_by_key["us_10y_yield"] = row
        else:
            series_by_key[key] = row

    indices: dict[str, Any] = {}
    for index, label in (("nifty50", "Nifty 50"), ("sensex", "Sensex"), ("Bank Nifty", "Bank Nifty")):
        res = run_index_return_tool({"index": index, "window_days": wd})
        if res.get("ok"):
            indices[label] = res.get("data")

    try:
        from historical_data.gold_service import get_gold_snapshot

        gold_detail = get_gold_snapshot(windows=["1M", "3M", "1Y"])
    except Exception as exc:  # noqa: BLE001
        gold_detail = {"available": False, "error": str(exc)[:200]}

    return {
        "window_days": wd,
        "macro_series": series_by_key,
        "index_returns": indices,
        "gold": gold_detail,
    }


def fetch_ask_market_records(*, window_days: int = 30) -> list[NumericRecord]:
    """Headline rows for gold plus labeled extras (WTI, US 10Y) not duplicated in yfinance ingest."""
    rows: list[NumericRecord] = [fetch_gold_record()]
    payload = get_ask_market_snapshot(window_days=window_days)
    for key, entity, unit in (
        ("wti", "Market - WTI Crude", "usd"),
        ("us_10y_yield", "Market - US 10Y Treasury Yield", "percent"),
    ):
        row = payload.get("macro_series", {}).get(key)
        if not isinstance(row, dict):
            continue
        pct = row.get("change_pct")
        rows.append(
            NumericRecord(
                entity,
                "",
                None,
                float(pct) if pct is not None else None,
                unit,
                SOURCE_ASK,
                "ok" if pct is not None else "unavailable",
                f"{row.get('label') or key}; {window_days}d change",
            )
        )
    return rows


def write_ask_market_snapshot(root: Path | None = None, *, window_days: int = 30) -> Path:
    from news_pipeline.config import repo_root

    base = root or repo_root()
    path = base / "data" / "ai_insight" / "market_ask_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(get_ask_market_snapshot(window_days=window_days), indent=2), encoding="utf-8")
    return path