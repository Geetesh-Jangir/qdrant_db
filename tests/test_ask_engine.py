"""Ask engine wires to insight v2 pipeline."""

from unittest.mock import patch

from news_rag.ask_engine import run_ask_engine


def test_ask_engine_delegates_to_insight_pipeline():
    fake = {
        "insight": "Test headline",
        "insight_summary": "Test headline",
        "insight_bullets": [],
        "sources": [],
        "intent": "insight_v2",
        "outcome": "ok",
        "refused": False,
        "research": {"pipeline": "v2"},
    }
    with patch("news_rag.ask_engine.run_insight_pipeline", return_value=fake) as mock_run:
        out = run_ask_engine("How is the auto sector doing?")
    mock_run.assert_called_once()
    assert out["insight"] == "Test headline"
    assert out["research"]["pipeline"] == "v2"
