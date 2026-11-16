"""FII/DII streak, CSV import, stale rejection, and the no-driver fallback."""

import csv
import json
from datetime import date
from types import SimpleNamespace

from ai_insight.common.config import load_config
from ai_insight.common.flows import FlowDay, history_path
from ai_insight.common.runner import run_insight
from ai_insight.common.time_ist import IST
from ai_insight.data.base import FiiDiiSnapshot, FlowLeg
from ai_insight.data.nse_fii_dii import reset_circuit_for_tests
from ai_insight.fii_dii_flow_narrative.aggregate import compute_flow_facts, fallback_headline, rolling_avg_abs_net, streak_days
from ai_insight.fii_dii_flow_narrative.collector import append_record, collect, import_csv, prefetch_fii_dii
from datetime import datetime


def _day(iso, fii, dii=10):
    return FlowDay(iso, fii, dii, {"net": fii}, {"net": dii})


def test_streak_flip_zero_gap_and_short_history():
    days = [_day("2026-11-12", -1), _day("2026-11-13", -2), _day("2026-11-14", 3)]
    assert streak_days(days).days == 1
    zero = [_day("2026-11-13", -2), _day("2026-11-14", 0)]
    assert streak_days(zero).days == 0
    gapped = [_day("2026-11-12", -1), _day("2026-11-14", -2)]
    assert streak_days(gapped, trading_days={"2026-11-12", "2026-11-13", "2026-11-14"}).days == 1
    short = [_day("2026-11-16", -5)]
    info = streak_days(short)
    assert info.days == 1 and info.history_days == 1
    facts = compute_flow_facts(short, "2026-11-16", min_history=5)
    assert facts["ratio"] is None
    lagged = [_day("2026-11-13", -50, 20)]
    lag_facts = compute_flow_facts(lagged, "2026-11-16", min_history=5)
    assert lag_facts["fii_net_crore"] == -50
    assert lag_facts["flow_trade_date"] == "2026-11-13"
    assert lag_facts["flow_lagged"] is True
    long = [_day(f"2026-11-{day:02d}", -10) for day in range(10, 16)]
    avg, count = rolling_avg_abs_net(long)
    assert count == 5 and avg == 10
    facts = compute_flow_facts(long, "2026-11-15", ratio_high=1.5, min_history=5)
    assert facts["ratio"] == 1.0
    assert "5th" in fallback_headline({"fii_net_crore": -2340, "fii_streak_days": 5})
    assert "straight" not in fallback_headline({"fii_net_crore": -2340, "fii_streak_days": 1})


def test_csv_import_and_stale_rejection(tmp_path):
    path = tmp_path / "hist.json"
    csv_path = tmp_path / "flows.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, ["date", "fii_buy", "fii_sell", "fii_net", "dii_buy", "dii_sell", "dii_net"])
        writer.writeheader()
        writer.writerow({"date": "13-Nov-2026", "fii_buy": 10, "fii_sell": 12, "fii_net": -2, "dii_buy": 8, "dii_sell": 5, "dii_net": 3})
        writer.writerow({"date": "2026-11-14", "fii_buy": 10, "fii_sell": 11, "fii_net": -9, "dii_buy": 1, "dii_sell": 1, "dii_net": 0})
    report = import_csv(csv_path, path)
    assert report.added == 2
    assert any("buy - sell" in warning for warning in report.warnings)
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert [row["date"] for row in rows] == ["2026-11-13", "2026-11-14"]
    append_record(path, rows[0])
    assert len(json.loads(path.read_text(encoding="utf-8"))) == 2

    stale = FiiDiiSnapshot("13-Nov-2026", FlowLeg("FII", 1, 2, -1), FlowLeg("DII", 2, 1, 1), "nse", "ok")
    cfg = load_config({"INSIGHTS_DATA_DIR": str(tmp_path)})
    assert collect(date(2026, 11, 16), history_path=path, fetch=lambda: stale, config=cfg).status == "already_present"
    empty = tmp_path / "lagged.json"
    saved = collect(date(2026, 11, 16), history_path=empty, fetch=lambda: stale, config=cfg)
    assert saved.status == "saved"
    assert json.loads(empty.read_text(encoding="utf-8"))[0]["date"] == "2026-11-13"
    assert collect(date(2026, 11, 16), history_path=empty, fetch=lambda: stale, config=cfg).status == "already_present"
    append_record(path, {"date": "2026-11-16", "fii": {"buy": 1, "sell": 1, "net": 0}, "dii": {"buy": 1, "sell": 1, "net": 0}, "source": "test", "fetched_at_utc": "2026-11-16T00:00:00Z"})
    assert collect(date(2026, 11, 16), history_path=path, fetch=lambda: (_ for _ in ()).throw(AssertionError("no fetch")), config=cfg).status == "already_present"


def test_no_driver_marks_degraded(tmp_path, monkeypatch):
    holidays = tmp_path / "holidays.json"
    holidays.write_text("{}", encoding="utf-8")
    cfg = load_config({"INSIGHTS_DATA_DIR": str(tmp_path / "data"), "INSIGHTS_LOG_DIR": str(tmp_path / "logs"), "INSIGHTS_HOLIDAYS_PATH": str(holidays), "INSIGHTS_CHECK_FRESHNESS": "0"})
    snap = SimpleNamespace(status="ok", data={"trade_date": "2026-11-16", "fii": {"net_inr_crore": -100, "buy_inr_crore": 1, "sell_inr_crore": 2}, "dii": {"net_inr_crore": 50, "buy_inr_crore": 2, "sell_inr_crore": 1}, "source": "nse"}, detail="", source="nse")
    monkeypatch.setattr("ai_insight.fii_dii_flow_narrative.run.get_fii_dii_today", lambda *a, **k: snap)

    class Rows:
        rows = []
        diagnostics = SimpleNamespace(entities_passed=0, dropped={}, sample_dropped={})

    monkeypatch.setattr("ai_insight.fii_dii_flow_narrative.run.fetch_entity_rows", lambda *a, **k: Rows())

    class Reply:
        def __init__(self, data):
            self.data = data
            self.usage = SimpleNamespace(input_tokens=1, output_tokens=1, cached_tokens=0, attempts=1, retries=0, model="claude-haiku-5-5", provider="anthropic")
            self.request = {}
            self.raw_text = "{}"

    draft = {"headline": "FIIs sold today", "body": "News flow doesn't point to one clear driver today.", "chosen_cluster_ids": [], "confidence": "low", "no_clear_driver": True, "implication": None, "observations": []}
    verdict = {"supported": True, "unsupported_claims": [], "too_long": False, "unclear_phrases": [], "revised": {}}

    def build(ctx):
        ctx.llm = lambda *a, **k: Reply(draft if "verifier" not in a[0].lower() and "check" not in a[0].lower() else verdict)
        # The quality loop calls draft then verify. Route by call count.
        calls = {"n": 0}

        def llm(*a, **k):
            calls["n"] += 1
            return Reply(draft if calls["n"] == 1 else verdict)

        ctx.llm = llm
        from ai_insight.fii_dii_flow_narrative.run import build as real

        return real(ctx)

    outcome = run_insight(
        "fii_dii_flow_narrative",
        build,
        date(2026, 11, 16),
        config=cfg,
        now=datetime(2026, 11, 16, 18, 0, tzinfo=IST),
    )
    assert outcome.envelope is not None
    assert outcome.envelope.status == "degraded"
    assert "clear driver" in outcome.envelope.body


def test_prefetch_always_calls_nse_even_when_today_on_file(tmp_path, monkeypatch):
    cfg = load_config({"INSIGHTS_DATA_DIR": str(tmp_path), "INSIGHTS_HOLIDAYS_PATH": str(tmp_path / "holidays.json")})
    (tmp_path / "holidays.json").write_text("{}", encoding="utf-8")
    path = history_path(tmp_path)
    for day in ("2026-11-13", "2026-11-16"):
        append_record(
            path,
            {
                "date": day,
                "fii": {"buy": 1, "sell": 1, "net": 0},
                "dii": {"buy": 1, "sell": 1, "net": 0},
                "source": "test",
                "fetched_at_utc": f"{day}T00:00:00Z",
            },
        )
    calls = {"n": 0}
    stale = FiiDiiSnapshot("13-Nov-2026", FlowLeg("FII", 1, 2, -1), FlowLeg("DII", 2, 1, 1), "nse", "ok")

    def fetch():
        calls["n"] += 1
        return stale

    monkeypatch.setattr("ai_insight.data.nse_fii_dii.fetch_fii_dii_snapshot", fetch)
    monkeypatch.setattr("ai_insight.data.run.write_fii_dii", lambda *_a, **_k: tmp_path / "latest.json")
    result = prefetch_fii_dii(date(2026, 11, 16), config=cfg)
    assert calls["n"] == 1
    assert result.status == "already_present"


def test_prefetch_skips_nse_on_holiday(tmp_path, monkeypatch):
    called = []

    def boom():
        called.append(1)
        raise AssertionError("NSE should not run on a holiday")

    monkeypatch.setattr("ai_insight.data.nse_fii_dii.fetch_fii_dii_snapshot", boom)
    holidays = tmp_path / "holidays.json"
    holidays.write_text(json.dumps({"2026": ["2026-11-16"]}), encoding="utf-8")
    cfg = load_config({"INSIGHTS_DATA_DIR": str(tmp_path), "INSIGHTS_HOLIDAYS_PATH": str(holidays)})
    result = prefetch_fii_dii(date(2026, 11, 16), config=cfg)
    assert result.detail == "not_a_trading_day"
    assert not called


def test_circuit_opens_after_repeated_failures(monkeypatch):
    import ai_insight.data.nse_fii_dii as nse

    reset_circuit_for_tests()
    monkeypatch.setattr(nse, "_httpx_json", lambda *a, **k: (_ for _ in ()).throw(TimeoutError("down")))
    monkeypatch.setattr(nse.time, "sleep", lambda *a, **k: None)
    for _ in range(3):
        try:
            nse._nse_json("https://www.nseindia.com/api/fiidiiTradeReact")
        except RuntimeError:
            pass
    try:
        nse._nse_json("https://www.nseindia.com/api/fiidiiTradeReact")
        raised = False
    except RuntimeError as exc:
        raised = "circuit" in str(exc)
    assert raised
    reset_circuit_for_tests()
