"""Evidence budget, quality loop, artifacts, trends, and flow history."""

import json
import os
from datetime import date

import pytest

from ai_insight.common.clustering import Cluster
from ai_insight.common.config import load_config
from ai_insight.common.evidence import EvidenceArticle, enforce_prompt_budget, format_evidence_block, pick_evidence
from ai_insight.common.flows import FlowDay, cumulative, load_flow_history
from ai_insight.common.logging import RunArtifacts
from ai_insight.common.market_data import get_nifty
from ai_insight.common.quality import LoopSpec, run_quality_loop
from ai_insight.common.runner import RunContext
from ai_insight.common.run_log import RunLog
from ai_insight.common.schemas import Chip, Envelope, Meta, Source
from ai_insight.common.trends import DayPoint, price_trend_from_closes, trend_stats
from ai_insight.common.validate import validate_insight


def _article(text="Brent touched 91 dollars."):
    return EvidenceArticle("c0", "Oil rises", "Mint", "2026-11-16T04:00:00Z", "https://a", text, 1.0, "Macro - Crude Oil", "negative", 3)


def test_budget_drops_whole_articles_only():
    articles = [
        EvidenceArticle("c0", "A", "M", "t", "https://a", "x" * 50, 1, "E", "negative", 2),
        EvidenceArticle("c1", "B", "M", "t", "https://b", "y" * 50, 5, "E", "negative", 2),
    ]
    kept, dropped = enforce_prompt_budget(articles, max_chars=200)
    assert len(kept) == 1 and kept[0].url == "https://b"
    assert dropped[0].url == "https://a"
    assert "y" * 50 in format_evidence_block(kept)


def test_pick_evidence_keeps_top_by_weight():
    cluster = Cluster("c0", "Oil", ["https://a", "https://b"], "A", "https://a", 2, 3, {}, [
        {"article": {"title": "A", "url": "https://a", "source": "M", "published_at": "t", "scraped_text": "full a"}, "entity": {"name": "Oil", "relevance": 4, "impact": 3, "about_this_name": 0.9, "direction": "negative"}},
        {"article": {"title": "B", "url": "https://b", "source": "M", "published_at": "t", "scraped_text": "full b"}, "entity": {"name": "Oil", "relevance": 2, "impact": 1, "about_this_name": 0.8, "direction": "negative"}},
    ])
    picked = pick_evidence([cluster], per_cluster=1)
    assert picked[0].url == "https://a"
    assert picked[0].full_text == "full a"


def test_validator_accepts_multiparagraph_narrative():
    beats = {
        "what_happened": "Nifty edged up today.",
        "why": "Crude cooled a little earlier this week.",
        "impacted": "Energy names saw fewer negative headlines.",
        "investor_meaning": "Volatility may ease slightly.",
    }
    body = "\n\n".join(beats.values())
    env = Envelope(
        insight_id="market_driver_digest",
        trading_date="2026-11-16",
        as_of_ist="2026-11-16T18:00:00+05:30",
        status="ok",
        headline="Nifty up today",
        body=body,
        chips=[Chip(label="Nifty 50", value="25000 (+0.5%)", tone="positive")],
        sources=[Source(title="Oil", url="https://a", source="Mint", published_at="t")],
        facts={"nifty_change_pct": 0.5, "narrative_beats": beats},
        meta=Meta(),
    )
    result = validate_insight(env, "Crude cooled to 91 dollars.")
    assert result.ok, result.errors


def test_validator_accepts_numbers_from_evidence():
    env = Envelope(
        insight_id="fii_dii_flow_narrative",
        trading_date="2026-11-16",
        as_of_ist="2026-11-16T18:00:00+05:30",
        status="ok",
        headline="Crude move is linked to the selling",
        body="The selling appears tied to Brent at 91.",
        chips=[Chip(label="FII", value="-100", tone="negative")],
        sources=[Source(title="Oil", url="https://a", source="Mint", published_at="t")],
        facts={"fii_net_crore": -100},
        meta=Meta(),
    )
    assert not validate_insight(env).ok
    assert validate_insight(env, "Brent touched 91 dollars.").ok


def test_trend_stats_do_not_outrun_history():
    series = [DayPoint("d1", net_signed=-1), DayPoint("d2", net_signed=-2), DayPoint("d3", net_signed=3)]
    stats = trend_stats(series)
    assert stats.streak_days == 1
    assert stats.history_days == 3
    prices = price_trend_from_closes([(f"2026-01-{day:02d}", 100 + day) for day in range(1, 25)], end=date(2026, 1, 24))
    assert prices.history_days == 24
    assert prices.change_5d is not None


def test_flow_history_and_cumulative(tmp_path):
    path = tmp_path / "fii_dii_history.json"
    path.write_text(json.dumps([
        {"date": "2026-11-14", "fii": {"buy": 1, "sell": 3, "net": -2}, "dii": {"buy": 4, "sell": 1, "net": 3}},
        {"date": "2026-11-13", "fii": {"net": -1}, "dii": {"net": 1}},
    ]), encoding="utf-8")
    days = load_flow_history(path)
    assert [day.date for day in days] == ["2026-11-13", "2026-11-14"]
    assert cumulative(days, 2) == -3


def test_artifacts_redact_and_prune(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secretvalue")
    artifacts = RunArtifacts("fii_dii_flow_narrative", "2026-11-16", "abc123", tmp_path, retention_days=60)
    artifacts.info("key sk-ant-secretvalue and Bearer abc.def")
    text = (artifacts.dir / "run.log").read_text(encoding="utf-8")
    assert "sk-ant-secretvalue" not in text
    assert "[redacted]" in text
    record = json.loads((artifacts.dir / "run.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert record["run_id"] == "abc123" and record["ts_ist"].endswith("+05:30")
    old = tmp_path / "2020-01-01" / "x"
    old.mkdir(parents=True)
    (old / "run.log").write_text("old", encoding="utf-8")
    artifacts2 = RunArtifacts("fii_dii_flow_narrative", "2026-11-16", "bbb", tmp_path, retention_days=30)
    assert not (tmp_path / "2020-01-01").exists()
    artifacts.close()
    artifacts2.close()


def test_quality_loop_revise_then_degraded(tmp_path):
    replies = [
        {"headline": "FIIs sold again", "body": "Selling appears tied to oil."},
        {"supported": False, "unsupported_claims": ["oil"], "too_long": False, "unclear_phrases": [], "revised": {}},
        {"headline": "FIIs sold again", "body": "Selling appears tied to oil."},
        {"supported": False, "unsupported_claims": ["oil"], "too_long": True, "unclear_phrases": ["fuzzy"], "revised": {}},
    ]

    class Result:
        def __init__(self, data):
            self.data = data

    def llm(*_a, **_k):
        return Result(replies.pop(0))

    ctx = RunContext(
        insight_id="fii_dii_flow_narrative",
        trading_date=date(2026, 11, 16),
        window=("a", "b"),
        dry_run=False,
        config=load_config(
            {"INSIGHTS_DATA_DIR": str(tmp_path), "INSIGHTS_LLM_VERIFY": "true", "INSIGHTS_REVERIFY": "true"}
        ),
        log=RunLog(insight_id="fii_dii_flow_narrative", trading_date="2026-11-16", run_id="r", log_dir=tmp_path),
        llm=llm,
    )

    def compose(data):
        return Envelope(
            insight_id="fii_dii_flow_narrative",
            trading_date="2026-11-16",
            as_of_ist="2026-11-16T18:00:00+05:30",
            status="ok",
            headline=data["headline"],
            body=data["body"],
            sources=[Source(title="Oil", url="https://a", source="Mint", published_at="t")],
            facts={},
            meta=Meta(),
        )

    spec = LoopSpec("d", "v", "r", "user", {"type": "object"}, compose)
    outcome = run_quality_loop(ctx, spec=spec, facts={}, evidence=[_article()])
    assert outcome.status == "degraded"
    assert outcome.revised is not None


def test_nifty_history_serves_a_past_date(tmp_path):
    rows = [("2026-11-13", 100.0), ("2026-11-16", 99.0)]
    result = get_nifty("2026-11-16", history=rows, config=load_config({"INSIGHTS_DATA_DIR": str(tmp_path)}))
    assert result.status == "ok"
    assert result.data["close"] == 99.0
    assert result.data["change_pct"] == -1.0
    missing = get_nifty("2026-11-12", history=rows, config=load_config({"INSIGHTS_DATA_DIR": str(tmp_path)}))
    assert missing.status == "stale"
