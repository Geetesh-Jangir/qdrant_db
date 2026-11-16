"""Ledger, stale cards, and FII history upsert."""

import json
from pathlib import Path

from ai_insight.common.store import load_best_detail, save
from ai_insight.common.schemas import Envelope, Meta, UsageMeta
from ai_insight.fii_dii_flow_narrative.collector import append_record


def test_load_best_detail_prefers_newest_not_older_ok(tmp_path):
    ok = Envelope(
        insight_id="market_driver_digest",
        trading_date="2026-11-16",
        as_of_ist="2026-11-16T10:00:00+05:30",
        status="ok",
        headline="ok",
        body="body",
        meta=Meta(run_mode="scheduled"),
    )
    bad = ok.model_copy(
        update={
            "as_of_ist": "2026-11-16T18:00:00+05:30",
            "status": "failed",
            "headline": "",
            "body": "",
            "meta": Meta(run_mode="live"),
        }
    )
    save(ok, root=tmp_path, live=False)
    save(bad, root=tmp_path, live=True)
    detail = load_best_detail("market_driver_digest", "2026-11-16", root=tmp_path)
    assert detail.envelope is not None
    assert detail.envelope.status == "failed"
    assert detail.stale is False


def test_fii_history_keeps_revision(tmp_path):
    path = tmp_path / "fii_dii_history.json"
    first = {"date": "2026-11-13", "fii": {"buy": 1, "sell": 0, "net": 1}, "dii": {"buy": 0, "sell": 0, "net": 0}}
    append_record(path, first)
    second = {"date": "2026-11-13", "fii": {"buy": 2, "sell": 0, "net": 2}, "dii": {"buy": 0, "sell": 0, "net": 0}}
    append_record(path, second)
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert rows[-1]["fii"]["net"] == 2
    assert rows[-1].get("revisions")