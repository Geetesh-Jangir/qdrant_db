import json

from ai_insight.holding_insights.stock_log import load_stock_log, render_markdown, save_stock_log


def test_save_and_load_stock_log(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ai_insight.holding_insights.stock_log.holding_data_dir",
        lambda: tmp_path,
    )
    job_id = "a1b2c3d4e5f6"
    doc = {
        "job_id": job_id,
        "stock_id": "TEST",
        "stock_name": "Test Limited",
        "outcome": "ok",
        "reason": None,
        "timeline": [{"step": "News", "summary": "2 articles sent."}],
        "usage": {"input_tokens": 100, "output_tokens": 20, "llm_calls": 1, "model": "claude-haiku-5-5"},
        "insight_lines": ["One.", "Two.", "Three."],
        "news_summary": {
            "sent_to_llm": 2,
            "articles_sent": [
                {"url": "https://example.com/a", "headline": "Example A", "published_at": "2026-11-17T00:00:00Z"}
            ],
        },
        "price_summary": {"latest_price": 1.0},
        "llm_response_preview": "{}",
    }
    save_stock_log(job_id, "TEST", doc)
    loaded = load_stock_log(job_id, "TEST")
    assert loaded["stock_name"] == "Test Limited"
    md_path = tmp_path / "stock_logs" / job_id / "TEST.md"
    assert md_path.is_file()
    assert "Input tokens: 100" in render_markdown(doc)
    assert "https://example.com/a" in render_markdown(doc)