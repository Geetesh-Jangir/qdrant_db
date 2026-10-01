"""Unit tests for Ask query log helpers (no network)."""

from __future__ import annotations

from pathlib import Path

from news_rag.parse import ParsedQuery
from news_rag.query_log import QueryLogger


def test_log_parsed_includes_intent_and_fund(tmp_path: Path) -> None:
    log_path = tmp_path / "ask_test.log"
    logger = QueryLogger("test_id", log_path, kind="ask")
    parsed = ParsedQuery(
        question="What is the NAV of Test Fund?",
        published_from="2026-01-01T00:00:00Z",
        published_to="2026-01-08T00:00:00Z",
        window_label="last 7 days",
        stock_hint="",
        entity_resolved=[],
        entity_match_note="no_stock_hint",
        intent="fund_nav",
        fund_resolved={"isin": "INF000000001", "fund_short_name": "Test Fund"},
        fund_ambiguous=False,
    )
    logger.log_parsed(parsed)
    text = log_path.read_text(encoding="utf-8")
    assert "intent=fund_nav" in text or 'intent="fund_nav"' in text
    assert "INF000000001" in text


def test_finish_writes_json_sidecar(tmp_path: Path) -> None:
    log_path = tmp_path / "ask_sidecar.log"
    logger = QueryLogger("sid", log_path, kind="ask")
    logger.note("test_event", ok=True)
    meta = logger.finish(outcome="ok", article_count=3, insight_source="gemini")
    assert meta["summary_json"]
    json_path = Path(meta["summary_json"])
    assert json_path.is_file()
    assert "test_event" in json_path.read_text(encoding="utf-8")
