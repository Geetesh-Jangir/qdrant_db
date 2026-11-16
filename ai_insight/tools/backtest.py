"""Write one markdown review of recent insight days."""

from __future__ import annotations

import argparse
from datetime import date

from ai_insight.common.config import load_config
from ai_insight.common.time_ist import ist_now
from ai_insight.market_driver_digest.run import backtest as market_backtest
from ai_insight.sector_index_insights.run import _backtest as sector_backtest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_insight.tools.backtest")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--date", default="")
    args = parser.parse_args(argv)
    end = date.fromisoformat(args.date) if args.date else ist_now().date()
    cfg = load_config()
    market = market_backtest(args.days, end=end, config=cfg)
    sector_backtest(args.days, end, cfg)
    report = cfg.data_dir / "_reports" / "insights_backtest.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join([
            "# Insights backtest",
            "",
            f"Days: {args.days}",
            f"Market driver report: {market}",
            "Sector index report: sector_index_insights_backtest.md",
            "",
            "Read each day's headline next to the clusters it cited. A cause that the articles do not support should be degraded, not shown.",
            "",
        ]),
        encoding="utf-8",
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
