"""Runner: skip, retry, degrade, fail, and dry-run."""

import json
from datetime import date, datetime

from ai_insight.common.config import load_config
from ai_insight.common.runner import cli_main, run_insight
from ai_insight.common.schemas import Chip, Envelope, Meta, Source
from ai_insight.common.store import load, save
from ai_insight.common.time_ist import IST


def _cfg(tmp_path):
    holidays = tmp_path / "holidays.json"
    holidays.write_text(json.dumps({"2026": ["2026-11-19"]}), encoding="utf-8")
    return load_config(
        {
            "INSIGHTS_DATA_DIR": str(tmp_path / "data"),
            "INSIGHTS_LOG_DIR": str(tmp_path / "logs"),
            "INSIGHTS_HOLIDAYS_PATH": str(holidays),
        }
    )


def _good(headline="Banks fell after the policy hold"):
    return Envelope(
        insight_id="market_driver_digest",
        trading_date="2026-11-16",
        as_of_ist="2026-11-16T17:10:00+05:30",
        status="ok",
        headline=headline,
        body="Lenders fell 0.61% after the central bank held rates.",
        chips=[Chip(label="Nifty 50", value="-0.61%", tone="negative")],
        sources=[Source(title="Mint", url="https://example.com/a", source="Mint", published_at="2026-11-16T04:00:00Z")],
        facts={"nifty_change_pct": -0.61},
        meta=Meta(cluster_ids=[]),
    )


NOW = datetime(2026, 11, 16, 17, 10, tzinfo=IST)
DAY = date(2026, 11, 16)


def test_non_trading_day_is_skipped(tmp_path):
    called = []
    outcome = run_insight(
        "market_driver_digest",
        lambda ctx: called.append(ctx) or _good(),
        date(2026, 11, 14),
        config=_cfg(tmp_path),
        now=NOW,
    )
    assert called == []
    assert outcome.status == "skipped"
    assert outcome.exit_code == 0
    saved = load("market_driver_digest", "2026-11-14", root=tmp_path / "data")
    assert saved is not None and saved.skip_reason == "not_a_trading_day"
    text = open(outcome.log_path, encoding="utf-8").read()
    assert "RUN_SUMMARY" in text and "status=skipped" in text


def test_existing_ok_is_kept_unless_forced(tmp_path):
    cfg = _cfg(tmp_path)
    save(_good("Original headline stays"), root=cfg.data_dir)
    calls = []
    skipped = run_insight("market_driver_digest", lambda ctx: calls.append(1) or _good(), DAY, config=cfg, now=NOW)
    assert calls == []
    assert skipped.status == "skipped"
    forced = run_insight(
        "market_driver_digest",
        lambda ctx: calls.append(1) or _good("Forced headline stays"),
        DAY,
        force=True,
        config=cfg,
        now=NOW,
    )
    assert calls == [1]
    assert forced.status == "ok"
    assert load("market_driver_digest", "2026-11-16", root=cfg.data_dir).headline == "Forced headline stays"


def test_exception_is_saved_as_failed(tmp_path):
    def boom(_ctx):
        raise RuntimeError("feed broke")

    outcome = run_insight("market_driver_digest", boom, DAY, config=_cfg(tmp_path), now=NOW)
    assert outcome.exit_code == 1
    assert outcome.status == "failed"
    saved = load("market_driver_digest", "2026-11-16", root=tmp_path / "data")
    assert "RuntimeError" in saved.meta.validation["traceback"]
    assert "feed broke" in saved.meta.validation["traceback"]


def test_validation_retries_once_then_degrades_or_accepts(tmp_path):
    cfg = _cfg(tmp_path)
    state = {"n": 0}

    def flaky(_ctx):
        state["n"] += 1
        if state["n"] == 1:
            return _good("one two three four five six seven eight nine ten eleven twelve thirteen")
        return _good()

    recovered = run_insight("market_driver_digest", flaky, DAY, config=cfg, now=NOW)
    assert recovered.status == "ok"
    assert state["n"] == 2

    def always_bad(_ctx):
        return _good("one two three four five six seven eight nine ten eleven twelve thirteen")

    degraded = run_insight("market_driver_digest", always_bad, DAY, force=True, config=cfg, now=NOW)
    assert degraded.status == "degraded"
    assert degraded.exit_code == 0
    assert load("market_driver_digest", "2026-11-16", root=cfg.data_dir).status == "degraded"


def test_dry_run_prints_prompts_and_does_not_save(tmp_path, capsys):
    cfg = _cfg(tmp_path)

    def build(ctx):
        ctx.emit_facts({"nifty_change_pct": -0.61})
        ctx.llm("Be brief.", "Write the digest.", {"type": "object"})
        return _good()

    outcome = run_insight("market_driver_digest", build, DAY, dry_run=True, config=cfg, now=NOW)
    printed = capsys.readouterr().out
    assert outcome.exit_code == 0
    assert "FACTS" in printed and "-0.61" in printed
    assert "Be brief." in printed
    assert load("market_driver_digest", "2026-11-16", root=cfg.data_dir) is None
    prompt = open(outcome.log_path, encoding="utf-8").read()
    assert "dry run" in prompt
    assert "Be brief." in open(str(outcome.log_path).replace(".log", ".prompt.txt"), encoding="utf-8").read()


def test_cli_dry_run(tmp_path, monkeypatch, capsys):
    holidays = tmp_path / "holidays.json"
    holidays.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("INSIGHTS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("INSIGHTS_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("INSIGHTS_HOLIDAYS_PATH", str(holidays))
    code = cli_main(
        "market_driver_digest",
        lambda ctx: (_ for _ in ()).throw(AssertionError("should not build")),
        ["--date", "2026-11-14", "--dry-run"],
    )
    assert code == 0
    assert "skipped" in capsys.readouterr().out
