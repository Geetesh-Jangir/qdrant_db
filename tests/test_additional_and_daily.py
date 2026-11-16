"""Signal detectors and a dry orchestrator run."""

from ai_insight.additional_insights.signals import detect_signals
from ai_insight.common.trends import DayPoint
from ai_insight.tools.run_daily import run_daily


def test_signals_fire_on_extremes_and_a_divergence():
    series = {"Banks": [DayPoint(f"d{i}", n_stories=1, net_signed=-0.1) for i in range(6)]}
    series["Banks"][-1] = DayPoint("d6", n_stories=8, net_signed=-2)
    found = detect_signals(
        series=series,
        prices={"Brent": -4.0},
        flows=[{"fii_net": -100, "nifty_change": 0.4}],
        clusters=[{"label": "rates", "days": 3}],
    )
    kinds = {item.kind for item in found}
    assert "news_surge" in kinds
    assert "price_extreme" in kinds
    assert "divergence" in kinds
    assert "recurring_theme" in kinds


def test_orchestrator_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_DATA_DIR", str(tmp_path))
    assert run_daily(dry_run=True, max_wait_sec=0, poll_sec=0) == 0
    summary = list((tmp_path / "logs").glob("run_*.json"))
    assert summary
