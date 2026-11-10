"""Unit tests for Ask query log helpers (no network)."""

from __future__ import annotations

from pathlib import Path

from news_rag.parse import ParsedQuery
from news_rag.query_log import (
    QueryLogger,
    attach_query_log_meta,
    find_query_log_file,
    read_query_log,
)


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


def test_query_log_page_reads_only_files_inside_log_dir(tmp_path: Path) -> None:
    query_id = "20261106T080835Z_b1f065"
    log_path = tmp_path / f"ask_{query_id}.log"
    log_path.write_text("USER QUESTION: hello\n", encoding="utf-8")
    log_path.with_suffix(".json").write_text('{"ok": true}\n', encoding="utf-8")

    found = find_query_log_file(query_id, tmp_path)
    assert found == log_path.resolve()
    payload = read_query_log(query_id, tmp_path)
    assert payload is not None
    assert payload["filename"] == log_path.name
    assert "hello" in payload["text"]
    assert payload["summary_filename"].endswith(".json")
    assert '"ok": true' in payload["summary"]

    assert find_query_log_file("../secrets", tmp_path) is None
    assert find_query_log_file("not-a-real-id", tmp_path) is None
    assert read_query_log("20261106T000000Z_abcdef", tmp_path) is None


def test_attach_query_log_meta_adds_page_link() -> None:
    result: dict = {}
    attach_query_log_meta(
        result,
        {
            "query_id": "20261106T080835Z_b1f065",
            "log_file": "data/rag_query_logs/ask_20261106T080835Z_b1f065.log",
            "summary_json": "",
            "llm_calls": 0,
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "deepseek_calls": 0,
            "deepseek_input_tokens": 0,
            "deepseek_output_tokens": 0,
        },
    )
    assert result["query_log_href"] == "log?query_id=20261106T080835Z_b1f065"
    assert result["query_log_file"].endswith(".log")
