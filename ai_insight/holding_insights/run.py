"""Batch runner: one LLM call per stock, parallel 5."""

from __future__ import annotations

import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import date
from typing import Any, Callable

from ai_insight.common.time_ist import ist_now
from ai_insight.holding_insights.config import (
    HOLDING_INSIGHT_GATE,
    HOLDING_LOOKBACK_DAYS,
    HOLDING_NEWS_EXTENDED_DAYS,
    HOLDING_NEWS_MIN_ARTICLES,
    HOLDING_NEWS_TOP_K,
    HOLDING_PARALLEL,
    holding_data_dir,
)
from ai_insight.holding_insights.llm import call_holding_llm
from ai_insight.holding_insights.news import NewsArticle, get_top_news, news_window
from ai_insight.holding_insights.price import get_price_snapshot
from ai_insight.holding_insights.prompt import build_user_prompt
from ai_insight.holding_insights.stock_log import build_log_document, log_page_path, save_stock_log
from ai_insight.holding_insights.universe import StockRow, load_top_stocks

logger = logging.getLogger(__name__)

ProgressFn = Callable[[int, int, str, str], None]


def _articles_for_log(articles: list[NewsArticle]) -> list[dict[str, Any]]:
    return [
        {
            "url": a.article_id,
            "headline": a.headline,
            "published_at": a.published_at,
            "relevance": a.relevancy_score,
            "impact": a.nav_impact_display,
            "sentiment": a.sentiment,
        }
        for a in articles
    ]


def _news_summary_block(stock: StockRow, news: Any, window: tuple[str, str]) -> dict[str, Any]:
    return {
        "entity": stock.qdrant_entity_name,
        "scanned": news.scanned,
        "after_gate": news.after_gate,
        "sent_to_llm": len(news.articles),
        "window": list(window),
        "articles_sent": _articles_for_log(news.articles),
        "filters": {
            "lookback_days": HOLDING_LOOKBACK_DAYS,
            "news_extended_days": HOLDING_NEWS_EXTENDED_DAYS,
            "news_min_articles": HOLDING_NEWS_MIN_ARTICLES,
            "top_k": HOLDING_NEWS_TOP_K,
            "qdrant_entity_type": "holding",
            "entity_gate": asdict(HOLDING_INSIGHT_GATE),
        },
    }


def _week_change_pct(price: dict[str, Any] | None) -> float | None:
    if not price:
        return None
    hints = price.get("pattern_hints") or {}
    val = hints.get("week_change_pct")
    return float(val) if val is not None else None


def _write_stock_log(
    job_id: str | None,
    stock: StockRow,
    *,
    outcome: str,
    reason: str | None,
    timeline: list[dict[str, str]],
    usage: dict[str, Any] | None,
    insight_lines: list[str] | None,
    news_summary: dict[str, Any] | None,
    price: dict[str, Any] | None,
    llm_preview: str,
) -> str | None:
    if not job_id:
        return None
    doc = build_log_document(
        job_id=job_id,
        stock_id=stock.stock_id,
        stock_name=stock.instrument_name,
        outcome=outcome,
        reason=reason,
        timeline=timeline,
        usage=usage,
        insight_lines=insight_lines,
        news=news_summary,
        price=price,
        llm_response_preview=llm_preview,
    )
    save_stock_log(job_id, stock.stock_id, doc)
    return log_page_path(job_id, stock.stock_id)


def _process_stock(
    stock: StockRow,
    trading_date: date,
    *,
    dry_run: bool,
    job_id: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (insight_record, insufficient_record)."""
    timeline: list[dict[str, str]] = []
    logs: dict[str, Any] = {}
    price = get_price_snapshot(stock.yfinance_ticker, trading_date=trading_date)
    if price is None:
        timeline.append({"step": "Price", "summary": "Yahoo price data was not available."})
        log_url = _write_stock_log(
            job_id,
            stock,
            outcome="insufficient",
            reason="price_unavailable",
            timeline=timeline,
            usage=None,
            insight_lines=None,
            news_summary=None,
            price=None,
            llm_preview="",
        )
        return None, {
            "stock_id": stock.stock_id,
            "stock_name": stock.instrument_name,
            "reason": "price_unavailable",
            "log_url": log_url,
        }

    timeline.append(
        {
            "step": "Price",
            "summary": (
                f"Loaded 7 session days (OHLCV each); latest {price.get('latest_price')} ({price.get('session_state')}) "
                f"as of {price.get('price_as_of')}."
            ),
        }
    )

    window = news_window(trading_date)
    news = get_top_news(stock.qdrant_entity_name, window, trading_date=trading_date)
    logs["articles_scanned"] = news.scanned
    logs["articles_after_gate"] = news.after_gate
    logs["news_window"] = list(window)
    news_summary = _news_summary_block(stock, news, window)

    timeline.append(
        {
            "step": "News",
            "summary": (
                f"Scanned {news.scanned} articles; {news.after_gate} passed filter; "
                f"sending {len(news.articles)} to the model."
            ),
        }
    )

    if not news.articles:
        logs["article_ids_sent"] = []
        log_url = _write_stock_log(
            job_id,
            stock,
            outcome="insufficient",
            reason="no_news_after_filter",
            timeline=timeline,
            usage={"input_tokens": 0, "output_tokens": 0, "llm_calls": 0},
            insight_lines=None,
            news_summary=news_summary,
            price=price,
            llm_preview="(LLM not called — no news after filter)",
        )
        return None, {
            "stock_id": stock.stock_id,
            "stock_name": stock.instrument_name,
            "reason": "no_news_after_filter",
            "logs": logs,
            "log_url": log_url,
            "usage": {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0},
        }

    logs["article_ids_sent"] = [a.article_id for a in news.articles]
    user_prompt = build_user_prompt(stock.instrument_name, stock.sector_name, price, news.articles)
    logs["prompt_chars"] = len(user_prompt)
    llm_out = call_holding_llm(user_prompt, dry_run=dry_run)
    usage = llm_out.get("usage") or {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0}
    logs["raw_llm"] = llm_out.get("raw_text", "")[:4000]
    logs["retries"] = llm_out.get("retries", 0)
    logs["skip_reason"] = llm_out.get("reason_if_skipped")
    logs["usage"] = usage

    timeline.append(
        {
            "step": "LLM",
            "summary": (
                f"Calls: {usage.get('llm_calls', 0)}; "
                f"in {usage.get('input_tokens', 0)} / out {usage.get('output_tokens', 0)} tokens; "
                f"model {usage.get('model') or llm_out.get('model_used')}."
            ),
        }
    )

    if llm_out.get("skip") or not llm_out.get("insight_lines"):
        reason = llm_out.get("error") or "llm_skip"
        if llm_out.get("reason_if_skipped"):
            reason = "llm_skip"
        timeline.append({"step": "Result", "summary": f"No insight shown: {reason}."})
        log_url = _write_stock_log(
            job_id,
            stock,
            outcome="insufficient",
            reason=reason,
            timeline=timeline,
            usage=usage,
            insight_lines=None,
            news_summary=news_summary,
            price=price,
            llm_preview=str(llm_out.get("raw_text") or ""),
        )
        return None, {
            "stock_id": stock.stock_id,
            "stock_name": stock.instrument_name,
            "reason": reason,
            "detail": llm_out.get("reason_if_skipped"),
            "logs": logs,
            "log_url": log_url,
            "usage": usage,
            "week_change_pct": _week_change_pct(price),
        }

    timeline.append({"step": "Result", "summary": "Compressed insight generated (one short paragraph)."})
    log_url = _write_stock_log(
        job_id,
        stock,
        outcome="ok",
        reason=None,
        timeline=timeline,
        usage=usage,
        insight_lines=llm_out["insight_lines"],
        news_summary=news_summary,
        price=price,
        llm_preview=str(llm_out.get("raw_text") or ""),
    )

    record = {
        "stock_id": stock.stock_id,
        "stock_name": stock.instrument_name,
        "sector": stock.sector_name,
        "generated_on": trading_date.isoformat(),
        "skip": False,
        "insight_lines": llm_out["insight_lines"],
        "model_used": llm_out.get("model_used"),
        "news_article_ids_used": logs["article_ids_sent"],
        "price_snapshot": price,
        "week_change_pct": _week_change_pct(price),
        "logs": logs,
        "usage": usage,
        "log_url": log_url,
    }
    logger.info(
        "holding_insight ok %s lines=%s articles=%s",
        stock.stock_id,
        len(record["insight_lines"]),
        len(news.articles),
    )
    return record, None


def _build_batch_outcome(
    *,
    job_id: str | None,
    trading_date: date,
    limit: int,
    total: int,
    insights: list[dict[str, Any]],
    insufficient: list[dict[str, Any]],
) -> dict[str, Any]:
    token_in = sum(int((r.get("usage") or {}).get("input_tokens") or 0) for r in insights)
    token_in += sum(int((r.get("usage") or {}).get("input_tokens") or 0) for r in insufficient)
    token_out = sum(int((r.get("usage") or {}).get("output_tokens") or 0) for r in insights)
    token_out += sum(int((r.get("usage") or {}).get("output_tokens") or 0) for r in insufficient)
    return {
        "job_id": job_id,
        "generated_on": trading_date.isoformat(),
        "limit": limit,
        "total": total,
        "insights": insights,
        "insufficient": insufficient,
        "counts": {
            "ok": len(insights),
            "insufficient": len(insufficient),
        },
        "usage_total": {
            "input_tokens": token_in,
            "output_tokens": token_out,
            "stocks_with_llm": sum(
                1 for r in insights + insufficient if (r.get("usage") or {}).get("llm_calls")
            ),
        },
    }


def _persist_run_snapshot(job_id: str | None, snapshot: dict[str, Any]) -> None:
    if not job_id:
        return
    root = holding_data_dir() / "runs"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{job_id}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def run_batch(
    limit: int,
    *,
    dry_run: bool = False,
    job_id: str | None = None,
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    trading_date = ist_now().date()
    stocks = load_top_stocks(limit)
    total = len(stocks)
    insights: list[dict[str, Any]] = []
    insufficient: list[dict[str, Any]] = []
    done = 0

    def report(stock_id: str, phase: str) -> None:
        if on_progress:
            on_progress(done, total, stock_id, phase)

    report("", "start")

    with ThreadPoolExecutor(max_workers=HOLDING_PARALLEL) as pool:
        futures = {
            pool.submit(_process_stock, stock, trading_date, dry_run=dry_run, job_id=job_id): stock
            for stock in stocks
        }
        for future in as_completed(futures):
            stock = futures[future]
            try:
                insight, insuff = future.result()
                if insight:
                    insights.append(insight)
                if insuff:
                    insufficient.append(insuff)
            except Exception as exc:
                logger.exception("holding insight failed %s", stock.stock_id)
                insufficient.append(
                    {
                        "stock_id": stock.stock_id,
                        "stock_name": stock.instrument_name,
                        "reason": "processing_error",
                        "detail": str(exc)[:200],
                    }
                )
            done += 1
            report(stock.stock_id, "done")
            _persist_run_snapshot(
                job_id,
                _build_batch_outcome(
                    job_id=job_id,
                    trading_date=trading_date,
                    limit=limit,
                    total=total,
                    insights=list(insights),
                    insufficient=list(insufficient),
                ),
            )

    insights.sort(key=lambda r: r.get("stock_id", ""))
    insufficient.sort(key=lambda r: r.get("stock_id", ""))
    outcome = _build_batch_outcome(
        job_id=job_id,
        trading_date=trading_date,
        limit=limit,
        total=total,
        insights=insights,
        insufficient=insufficient,
    )
    _persist_run_snapshot(job_id, outcome)
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_insight.holding_insights.run")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = run_batch(args.limit, dry_run=args.dry_run)
    print(f"ok={result['counts']['ok']} insufficient={result['counts']['insufficient']}")
    for row in result["insufficient"][:10]:
        print(f"  insufficient: {row.get('stock_name')} ({row.get('reason')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())