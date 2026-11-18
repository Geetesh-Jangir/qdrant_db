"""Backfill market / holding daily JSON from on-disk runs (one-off repair)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai_insight.common.market_daily_store import build_market_daily_snapshot, save_market_daily
from ai_insight.holding_insights.config import holding_data_dir
from ai_insight.holding_insights.daily_store import save_daily
from ai_insight.holding_insights.holding_stock_insights_store import (
    build_holding_stock_insights_snapshot,
    save_holding_stock_insights,
)


def _latest_holding_run(trading_date: str) -> dict | None:
    root = holding_data_dir() / "runs"
    if not root.is_dir():
        return None
    best: tuple[float, dict] | None = None
    for path in root.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if str(payload.get("generated_on") or "") != trading_date:
            continue
        if int((payload.get("counts") or {}).get("ok") or 0) < 1:
            continue
        mtime = path.stat().st_mtime
        if best is None or mtime > best[0]:
            best = (mtime, payload)
    return best[1] if best else None


def backfill(trading_date: str) -> dict[str, str]:
    out: dict[str, str] = {}
    snap = build_market_daily_snapshot(trading_date)
    if snap.get("common") or snap.get("sectors"):
        save_market_daily(trading_date, snap)
        out["market_daily"] = "ok"
    else:
        out["market_daily"] = "skip"

    run = _latest_holding_run(trading_date)
    if run:
        save_daily(trading_date, run)
        save_holding_stock_insights(trading_date, build_holding_stock_insights_snapshot(run))
        out["holding_archive"] = "ok"
    else:
        out["holding_archive"] = "skip"
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_insight.tools.backfill_portfolio_stores")
    parser.add_argument("--date", required=True, help="Trading date YYYY-MM-DD")
    args = parser.parse_args(argv)
    print(backfill(args.date))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())