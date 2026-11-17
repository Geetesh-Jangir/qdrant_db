"""Per-stock holding insight logs (separate from Tier 1 insight logs)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ai_insight.holding_insights.config import holding_data_dir

_STOCK_ID = re.compile(r"^[A-Z0-9][A-Z0-9&._-]{0,31}$")
_JOB_ID = re.compile(r"^[a-f0-9]{12}$")


def stock_logs_dir(job_id: str) -> Path:
    if not _JOB_ID.match(job_id):
        raise ValueError("bad job_id")
    root = holding_data_dir() / "stock_logs" / job_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def log_page_path(job_id: str, stock_id: str) -> str:
    return f"/holding-insights/log/{job_id}/{stock_id}"


def save_stock_log(job_id: str, stock_id: str, payload: dict[str, Any]) -> Path:
    if not _STOCK_ID.match(stock_id):
        raise ValueError("bad stock_id")
    path = stock_logs_dir(job_id) / f"{stock_id}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    md = stock_logs_dir(job_id) / f"{stock_id}.md"
    md.write_text(render_markdown(payload), encoding="utf-8")
    return path


def load_stock_log(job_id: str, stock_id: str) -> dict[str, Any] | None:
    if not _JOB_ID.match(job_id) or not _STOCK_ID.match(stock_id):
        return None
    path = holding_data_dir() / "stock_logs" / job_id / f"{stock_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def render_markdown(doc: dict[str, Any]) -> str:
    lines = [
        f"# {doc.get('stock_name') or doc.get('stock_id')} — holding insight log",
        "",
        f"- Job: `{doc.get('job_id')}`",
        f"- Outcome: **{doc.get('outcome')}**",
    ]
    if doc.get("reason"):
        lines.append(f"- Reason: {doc.get('reason')}")
    lines.extend(["", "## What happened"])
    for step in doc.get("timeline") or []:
        lines.append(f"- **{step.get('step')}**: {step.get('summary')}")
    usage = doc.get("usage") or {}
    if usage:
        lines.extend(
            [
                "",
                "## LLM usage",
                f"- Input tokens: {usage.get('input_tokens', 0)}",
                f"- Output tokens: {usage.get('output_tokens', 0)}",
                f"- LLM calls: {usage.get('llm_calls', 0)}",
                f"- Model: {usage.get('model') or '—'}",
            ]
        )
    if doc.get("headline"):
        lines.extend(["", "## Headline", str(doc["headline"])])
    if doc.get("insight_lines"):
        lines.extend(["", "## Insight", " ".join(doc["insight_lines"])])
    articles = (doc.get("news_summary") or {}).get("articles_sent") or doc.get("articles_sent") or []
    if articles:
        lines.extend(["", "## Articles sent to the LLM"])
        for i, art in enumerate(articles, start=1):
            headline = art.get("headline") or art.get("url") or "Article"
            url = art.get("url") or ""
            when = art.get("published_at") or ""
            lines.append(f"{i}. [{headline}]({url}) ({when})")
    if doc.get("llm_response_preview"):
        lines.extend(["", "## LLM response (preview)", "```", doc["llm_response_preview"], "```"])
    return "\n".join(lines) + "\n"


def build_log_document(
    *,
    job_id: str,
    stock_id: str,
    stock_name: str,
    outcome: str,
    reason: str | None,
    timeline: list[dict[str, str]],
    usage: dict[str, Any] | None,
    insight_lines: list[str] | None,
    headline: str | None = None,
    news: dict[str, Any] | None,
    price: dict[str, Any] | None,
    llm_response_preview: str,
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "stock_id": stock_id,
        "stock_name": stock_name,
        "outcome": outcome,
        "reason": reason,
        "timeline": timeline,
        "usage": usage or {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0},
        "headline": headline,
        "insight_lines": insight_lines,
        "news_summary": news,
        "price_summary": _price_summary(price),
        "llm_response_preview": llm_response_preview[:2000],
    }


def _price_summary(price: dict[str, Any] | None) -> dict[str, Any] | None:
    if not price:
        return None
    return {
        "latest_price": price.get("latest_price"),
        "price_as_of": price.get("price_as_of"),
        "session_state": price.get("session_state"),
        "pct_from_52w_high": price.get("pct_from_52w_high"),
        "pct_from_52w_low": price.get("pct_from_52w_low"),
        "pattern_hints": price.get("pattern_hints"),
        "days_in_prompt": len(price.get("bars") or []),
    }