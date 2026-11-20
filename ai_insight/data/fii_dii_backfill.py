"""Best-effort: append the latest NSE FII/DII day. No historical API exists."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ai_insight.fii_dii_flow_narrative.collector import append_record, history_has_date, prefetch_fii_dii
from ai_insight.common.config import load_config
from ai_insight.common.time_ist import ist_now
from ai_insight.data.stockezee_fii_dii import days_in_range, fetch_stockezee_history, history_record


@dataclass
class BackfillReport:
    added: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)


def backfill_recent(store: Path, *, days: int = 5) -> BackfillReport:
    _ = days
    cfg = load_config()
    report = BackfillReport()
    result = prefetch_fii_dii(ist_now().date(), config=cfg)
    if result.status == "saved":
        report.added = 1
    else:
        report.skipped = 1
    return report


def backfill_stockezee_net(
    store: Path,
    *,
    from_date: date,
    before_date: date,
) -> BackfillReport:
    """Append net-only StockeZee rows for [from_date, before_date). Does not overwrite NSE rows."""
    report = BackfillReport()
    try:
        remote = fetch_stockezee_history()
    except Exception as exc:
        report.warnings.append(f"fetch failed: {type(exc).__name__}: {exc}")
        return report
    picked = days_in_range(remote, from_date=from_date, before_date=before_date)
    if not picked:
        report.warnings.append(f"no stockezee rows in {from_date} .. {before_date}")
    for day in picked:
        if history_has_date(store, day.date):
            report.skipped += 1
            continue
        append_record(store, history_record(day))
        report.added += 1
    return report