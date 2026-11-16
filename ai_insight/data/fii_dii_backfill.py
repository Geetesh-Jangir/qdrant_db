"""Best-effort: append the latest NSE FII/DII day. No historical API exists."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_insight.fii_dii_flow_narrative.collector import prefetch_fii_dii
from ai_insight.common.config import load_config
from ai_insight.common.time_ist import ist_now


@dataclass
class BackfillReport:
    added: int = 0
    skipped: int = 0


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