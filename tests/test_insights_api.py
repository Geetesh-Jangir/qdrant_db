"""Insights API hides internals and the live job isolates failures."""

import json
import threading
from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_insight.api import create_router, public_projection
from ai_insight.common.config import load_config
from ai_insight.common.schemas import Chip, Envelope, InsightBundle, Meta, Source, Viz
from ai_insight.common.store import save, save_bundle
from ai_insight.jobs import JobManager


def _env(status="ok", headline="Nifty slips 0.6% today", body="The drop appears tied to crude.", facts=None):
    return Envelope(
        insight_id="market_driver_digest",
        trading_date="2026-11-16",
        as_of_ist="2026-11-16T18:00:00+05:30",
        status=status,
        skip_reason=None if status != "skipped" else "not_a_trading_day",
        headline=headline,
        body=body,
        chips=[Chip(label="Nifty 50", value="-0.61%", tone="negative")],
        sources=[Source(title="Crude", url="https://example.com/a", source="Mint", published_at="2026-11-16T04:00:00Z")],
        facts=facts if facts is not None else {"nifty_change_pct": -0.61, "secret_path": "D:/secret"},
        meta=Meta(model="claude-haiku-5-5", validation={"traceback": "hidden"}),
    )


def test_projection_hides_facts_and_statuses(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("INSIGHTS_PUBLIC", "true")
    save(_env(), root=tmp_path)
    save(_env(status="degraded", body="hidden degraded text"), root=tmp_path)
    shown = public_projection(_env())
    assert "facts" not in shown and "meta" not in shown and "secret" not in json.dumps(shown)
    hidden = public_projection(_env(status="failed"))
    assert hidden["status"] == "failed" and "headline" not in hidden
    app = FastAPI()
    app.include_router(create_router(lambda *_args: None))
    client = TestClient(app)
    daily = client.get("/api/insights/daily")
    assert daily.status_code == 200
    body = daily.json()
    assert body["insights"]["market_driver_digest"]["status"] == "degraded"
    assert "hidden" not in json.dumps(body)
    empty = client.get("/api/insights/daily", params={"date": "2026-01-01"})
    assert empty.json()["insights"]["market_driver_digest"] is None


def test_daily_sees_live_only_files_and_shows_live_degraded(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("INSIGHTS_PUBLIC", "true")
    live = _env(status="degraded", body="Live run text", headline="Live headline")
    live.meta.run_mode = "live"
    save(live, root=tmp_path, live=True)
    app = FastAPI()
    app.include_router(create_router(lambda *_args: None))
    client = TestClient(app)
    daily = client.get("/api/insights/daily")
    assert daily.status_code == 200
    body = daily.json()
    assert body["date"] == "2026-11-16"
    card = body["insights"]["market_driver_digest"]
    assert card["status"] == "degraded"
    assert card["headline"] == "Live headline"


def test_job_isolates_one_failure(tmp_path):
    cfg = load_config({
        "INSIGHTS_DATA_DIR": str(tmp_path),
        "INSIGHTS_LIVE_COOLDOWN_SEC": "0",
        "INSIGHTS_LIVE_PARALLEL": "2",
        "INSIGHTS_LIVE_MAX_MINUTES": "1",
    })
    gate = threading.Event()

    def runner(name, _day, _job, _timeout):
        gate.wait(2)
        return 1 if name == "fii_dii_flow_narrative" else 0

    manager = JobManager(cfg, runner=runner)
    job = manager.start(date(2026, 11, 16), ["market_driver_digest", "fii_dii_flow_narrative", "sector_leaderboard"])
    gate.set()
    for _ in range(50):
        view = manager.get(job.job_id)
        if view.status == "done":
            break
        threading.Event().wait(0.05)
    view = manager.get(job.job_id)
    assert view.results["fii_dii_flow_narrative"] == "failed"
    assert view.results["market_driver_digest"] == "ok"
    assert view.results["sector_leaderboard"] == "ok"
    bundle = InsightBundle(insight_id="additional_insights", trading_date="2026-11-16", as_of_ist="2026-11-16T18:00:00+05:30", status="ok", items=[_env()])
    save_bundle(bundle, root=tmp_path)
