"""Haiku JSON wrapper: schema retry, usage, and full article text."""

import time

import pytest

from ai_insight.common.clustering import Cluster
from ai_insight.common.config import load_config
from ai_insight.common.llm import LlmSchemaError, LlmUnavailable, format_articles_block, generate_json
from news_rag.llm_client import LlmCallResult


SCHEMA = {"type": "object", "required": ["headline"], "properties": {"headline": {"type": "string"}}, "additionalProperties": False}


def _result(parsed, provider="anthropic", model="claude-haiku-5-5", in_tok=10, out_tok=4):
    return LlmCallResult(
        raw_text="{}",
        provider=provider,
        model=model,
        input_tokens=in_tok,
        output_tokens=out_tok,
        total_tokens=in_tok + out_tok,
        duration_sec=0.1,
        http_status=200,
        parsed=parsed,
    )


def _cfg(tmp_path, timeout="5"):
    return load_config(
        {
            "INSIGHTS_DATA_DIR": str(tmp_path),
            "INSIGHTS_LLM_TIMEOUT_SEC": timeout,
            "INSIGHTS_LLM_RETRIES": "1",
            "INSIGHTS_LLM_MODEL": "claude-haiku-5-5",
            "INSIGHTS_LLM_PROVIDER": "anthropic",
        }
    )


def test_schema_retry_then_success(tmp_path):
    seen = []

    def call(**kwargs):
        seen.append(kwargs)
        if len(seen) == 1:
            return _result({"headline": 1})
        return _result({"headline": "Banks fell after the policy hold"})

    result = generate_json("system", "user", SCHEMA, config=_cfg(tmp_path), call=call)
    assert result.data["headline"].startswith("Banks")
    assert result.usage.attempts == 2
    assert result.usage.input_tokens == 20
    assert result.usage.model == "claude-haiku-5-5"
    assert seen[0]["model_override"] == "claude-haiku-5-5"
    assert seen[0]["provider_override"] == "anthropic"
    assert "failed validation" in seen[1]["user_content"]


def test_schema_failure_stops_after_one_retry(tmp_path):
    def call(**_kwargs):
        return _result({"headline": 1})

    with pytest.raises(LlmSchemaError):
        generate_json("system", "user", SCHEMA, config=_cfg(tmp_path), call=call)


def test_other_provider_fails_loudly(tmp_path):
    def call(**_kwargs):
        return _result({"headline": "Fine"}, provider="gemini", model="gemini-3.5-flash-lite")

    with pytest.raises(LlmUnavailable):
        generate_json("system", "user", SCHEMA, config=_cfg(tmp_path), call=call)


def test_timeout(tmp_path):
    def call(**_kwargs):
        time.sleep(1)
        return _result({"headline": "late"})

    with pytest.raises(LlmUnavailable, match="timed out"):
        generate_json("system", "user", SCHEMA, config=_cfg(tmp_path, timeout="0.2"), call=call)


def test_articles_are_not_truncated():
    body = "FULL " * 800
    cluster = Cluster(
        cluster_id="c0",
        label="Banks",
        member_urls=["https://a"],
        representative_title="Banks raise lending rates",
        representative_url="https://a",
        weight=1,
        avg_impact=3,
        direction_mix={"positive": 0, "negative": 1, "neutral": 0, "unclear": 0},
        articles=[
            {
                "article": {
                    "title": "Banks raise lending rates",
                    "url": "https://a",
                    "source": "Mint",
                    "published_at": "2026-11-16T06:00:00Z",
                    "scraped_text": body,
                }
            }
        ],
    )
    text = format_articles_block([cluster])
    assert body in text
    assert "c0" in text
