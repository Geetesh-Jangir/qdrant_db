"""Probe every catalog ticker and write which ones have a usable week."""

from __future__ import annotations

from datetime import date

from ai_insight.common.config import load_config
from ai_insight.common.sector_indices import load_catalog, series_is_usable
from ai_insight.common.sector_indices import _yahoo
from ai_insight.common.store import save_json
from ai_insight.common.time_ist import ist_now


def main() -> int:
    cfg = load_config()
    day = ist_now().date()
    rows = []
    for spec in load_catalog(include_weak=True):
        for ticker in spec.tickers:
            history = _yahoo(ticker)
            ok, reason = series_is_usable(history, day)
            rows.append({"sector_group": spec.key, "ticker": ticker, "rows": len(history), "usable": ok, "reason": reason})
            if ok:
                break
    path = cfg.data_dir / "_data" / "sector_index_health.json"
    save_json(path, {"date": day.isoformat(), "tickers": rows})
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
