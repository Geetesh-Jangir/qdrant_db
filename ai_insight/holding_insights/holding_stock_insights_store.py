"""Date-keyed holding-stock insight archive (provenance + LLM I/O) for portfolio and audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_insight.common.config import load_config
from ai_insight.holding_insights.atomic_io import atomic_write_json

_TEXT_CAP = 32_000


def _daily_path(trading_date: str) -> Path:
    if len(trading_date) != 10 or trading_date[4] != "-" or trading_date[7] != "-":
        raise ValueError(f"trading_date must be YYYY-MM-DD, got {trading_date!r}")
    return load_config().data_dir / "holding_stock_insights" / f"{trading_date}.json"


def _cap(text: str | None) -> str:
    if not text:
        return ""
    s = str(text)
    return s if len(s) <= _TEXT_CAP else s[:_TEXT_CAP] + "\n…[truncated]"


def _articles(row: dict[str, Any]) -> list[dict[str, str]]:
    sent = ((row.get("logs") or {}).get("news_summary") or {}).get("articles_sent") or []
    by_url = {
        str(a.get("url") or "").strip(): a
        for a in sent
        if isinstance(a, dict) and str(a.get("url") or "").strip()
    }
    out: list[dict[str, str]] = []
    for art in row.get("articles") or []:
        if not isinstance(art, dict):
            continue
        url = str(art.get("url") or "").strip()
        if not url:
            continue
        extra = by_url.get(url) or {}
        out.append(
            {
                "url": url,
                "published_at": str(art.get("published_at") or extra.get("published_at") or ""),
                "headline": str(art.get("headline") or extra.get("headline") or ""),
            }
        )
    return out


def _insight_text(headline: str | None, lines: list[str] | None) -> str:
    if lines:
        return " ".join(str(x) for x in lines if x).strip()
    return str(headline or "").strip()


def _usage(row: dict[str, Any]) -> dict[str, Any]:
    usage = row.get("usage") or {}
    inch = int(usage.get("input_tokens") or 0)
    outch = int(usage.get("output_tokens") or 0)
    return {
        "input_tokens": inch,
        "output_tokens": outch,
        "calls": int(usage.get("llm_calls") or 0),
        "model": usage.get("model") or row.get("model_used"),
    }


def _row_from_record(row: dict[str, Any], *, status: str) -> dict[str, Any]:
    articles = _articles(row)
    if not articles:
        ids = row.get("news_article_ids_used") or []
        articles = [{"url": str(u), "published_at": "", "headline": ""} for u in ids if u]
    insight_lines = row.get("insight_lines")
    headline = row.get("headline")
    llm = row.get("llm") or {}
    logs = row.get("logs") or {}
    return {
        "stock_id": row.get("stock_id"),
        "stock_name": row.get("stock_name"),
        "sector": row.get("sector") or row.get("sector_name"),
        "status": status,
        "created_at": row.get("created_at"),
        "headline": headline,
        "insight": _insight_text(headline, insight_lines),
        "insight_lines": insight_lines,
        **_usage(row),
        "llm": {
            "user_prompt": _cap(llm.get("user_prompt") or logs.get("user_prompt")),
            "output_text": _cap(llm.get("output_text") or logs.get("raw_llm")),
        },
        "articles": articles,
        "price": row.get("price_snapshot") or row.get("price"),
        "log_url": row.get("log_url"),
    }


def build_holding_stock_insights_snapshot(outcome: dict[str, Any]) -> dict[str, Any]:
    trading_date = str(outcome.get("generated_on") or "")
    holdings: list[dict[str, Any]] = []
    stamps: list[str] = []
    for row in outcome.get("insights") or []:
        holdings.append(_row_from_record(row, status="ok"))
        if row.get("created_at"):
            stamps.append(str(row["created_at"]))
    for row in outcome.get("insufficient") or []:
        if not (row.get("price_snapshot") or row.get("price") or row.get("articles") or (row.get("logs") or {}).get("user_prompt")):
            continue
        holdings.append(_row_from_record(row, status="insufficient"))
        if row.get("created_at"):
            stamps.append(str(row["created_at"]))
    holdings.sort(key=lambda r: str(r.get("stock_id") or ""))
    generated_at = max(stamps) if stamps else None
    return {
        "trading_date": trading_date,
        "generated_at": generated_at,
        "job_id": outcome.get("job_id"),
        "counts": outcome.get("counts"),
        "holdings": holdings,
    }


def save_holding_stock_insights(trading_date: str, snapshot: dict[str, Any]) -> Path:
    path = _daily_path(trading_date)
    atomic_write_json(path, snapshot)
    return path


def load_holding_stock_insights(trading_date: str) -> dict[str, Any] | None:
    path = _daily_path(trading_date)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None