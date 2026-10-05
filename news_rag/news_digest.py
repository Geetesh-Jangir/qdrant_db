"""Batch LLM digests per news family (holdings / sector / macro)."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.json_util import safe_json_dumps
from news_rag.llm_client import call_json_llm, contract_model, llm_api_key_configured
from news_rag.llm_text import parse_json_from_text

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

DIGEST_SYSTEM = """You analyze news articles for one topic focus (gold, silver, holding, sector, or macro).
When fund context is provided, explain what the news means for THAT fund's holdings/sectors (not generic market commentary).
When holdings_market is present (check linked_articles per holding), produce digest items that explain WHY the stock moved using snippet/title evidence only.
Each item for a holding must state: price move %, then the news driver in plain language from linked_articles — never invent succession/RBI/crude themes unless an article mentions them.
Return ONLY JSON:
{
  "focus": "label",
  "summary": "2-4 sentences: what happened, cited drivers, and why it matters for the fund or its top holdings/sectors",
  "items": [
    {
      "headline": "short title from article",
      "direction": "positive|negative|neutral|unclear",
      "max_impact": 0,
      "meaning": "cause/effect for the fund investor — tie to a holding or sector when possible",
      "source_title": "original article title"
    }
  ],
  "sectors_positive": ["sector names if any"],
  "sectors_negative": ["sector names if any"]
}
If articles are empty, say no matching news was found. Do not invent macro reasons without article support."""


@dataclass
class LayerDigest:
    layer: str
    focus: str = ""
    summary: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)
    sectors_positive: list[str] = field(default_factory=list)
    sectors_negative: list[str] = field(default_factory=list)
    error: str = ""


def _digest_one_layer(
    layer: str,
    articles: list[dict],
    *,
    focus: str = "",
    fund_context: dict[str, Any],
    holdings_market: list[dict[str, Any]] | None = None,
    sentiment: str,
    question: str,
    query_log: QueryLogger | None,
) -> LayerDigest:
    label = focus or layer
    if not articles:
        return LayerDigest(
            layer=layer,
            focus=label,
            summary=f"No news articles were found in our corpus for {label} in this window.",
        )
    if not llm_api_key_configured(get_settings()):
        return LayerDigest(
            layer=layer,
            focus=label,
            summary=f"{len(articles)} articles (digest skipped — no LLM).",
            items=[
                {
                    "headline": str(a.get("title") or "")[:120],
                    "direction": a.get("direction") or "unclear",
                    "max_impact": a.get("max_impact"),
                    "meaning": str(a.get("snippet") or "")[:200],
                }
                for a in articles[:6]
            ],
        )
    slim = []
    for a in articles[:12]:
        slim.append(
            {
                "title": a.get("title"),
                "snippet": (a.get("snippet") or "")[:400],
                "direction": a.get("direction"),
                "max_impact": a.get("max_impact"),
                "sectors": a.get("sector_names"),
                "entities": a.get("entity_names"),
            }
        )
    ctx = dict(fund_context)
    if holdings_market and (
        layer in ("holding", "holdings_news") or focus in ("holding", "holdings")
    ):
        ctx["holdings_market"] = holdings_market[:6]
    user = (
        f"Question: {question}\nSentiment filter requested: {sentiment}\nFocus: {label}\nLayer: {layer}\n"
        f"Fund context: {safe_json_dumps(ctx, limit=3500)}\n\n"
        f"Articles:\n{json.dumps(slim, ensure_ascii=False)}"
    )
    settings = get_settings()
    try:
        res = call_json_llm(
            system_prompt=DIGEST_SYSTEM,
            user_content=user,
            model_override=contract_model(settings),
            max_tokens=900,
            temperature=0.1,
            query_log=query_log,
        )
        parsed = parse_json_from_text(res.raw_text) or {}
        items = parsed.get("items") if isinstance(parsed.get("items"), list) else []
        return LayerDigest(
            layer=layer,
            focus=str(parsed.get("focus") or label),
            summary=str(parsed.get("summary") or ""),
            items=items,
            sectors_positive=[str(x) for x in (parsed.get("sectors_positive") or [])],
            sectors_negative=[str(x) for x in (parsed.get("sectors_negative") or [])],
        )
    except Exception as exc:
        logger.warning("digest %s failed: %s", layer, exc)
        if query_log is not None:
            query_log.write(f"DIGEST_FAIL layer={layer} error={exc}")
        return LayerDigest(layer=layer, focus=label, error=str(exc), summary=f"Digest failed: {exc}")


def digest_news_parallel(
    articles_by_layer: dict[str, list[dict]],
    articles_by_focus: dict[str, list[dict]] | None = None,
    *,
    fund_nav_data: dict[str, Any] | None,
    holdings_rows: list[dict],
    sector_rows: list[dict],
    holdings_market: list[dict[str, Any]] | None = None,
    sentiment: str,
    question: str,
    query_log: QueryLogger | None = None,
) -> tuple[list[LayerDigest], list[str]]:
    fund_ctx = {
        "nav": fund_nav_data,
        "holdings": holdings_rows[:8],
        "sectors": sector_rows[:8],
    }
    digests: list[LayerDigest] = []
    jobs: list[tuple[str, str, list[dict]]] = []
    if articles_by_focus:
        for focus_key, arts in articles_by_focus.items():
            if not arts:
                continue
            layer = "macro" if focus_key in ("gold", "silver", "macro") else focus_key
            jobs.append((layer, focus_key, arts))
    if not jobs:
        for layer in ("holding", "sector", "macro"):
            arts = articles_by_layer.get(layer) or []
            if arts:
                jobs.append((layer, layer, arts))
    if not jobs:
        return digests, []

    with ThreadPoolExecutor(max_workers=min(6, len(jobs))) as pool:
        futs = {
            pool.submit(
                _digest_one_layer,
                layer,
                arts,
                focus=focus,
                fund_context=fund_ctx,
                holdings_market=holdings_market,
                sentiment=sentiment,
                question=question,
                query_log=query_log,
            ): (layer, focus)
            for layer, focus, arts in jobs
        }
        for fut in as_completed(futs):
            layer, focus = futs[fut]
            try:
                digests.append(fut.result())
            except Exception as exc:
                digests.append(LayerDigest(layer=layer, focus=focus, error=str(exc)))
                if query_log is not None:
                    query_log.write(f"DIGEST_FAIL focus={focus} {exc}")

    sectors_for_funds: list[str] = []
    for d in digests:
        if sentiment == "positive":
            sectors_for_funds.extend(d.sectors_positive)
        elif sentiment == "negative":
            sectors_for_funds.extend(d.sectors_negative)
        else:
            sectors_for_funds.extend(d.sectors_negative + d.sectors_positive)
    seen: set[str] = set()
    unique: list[str] = []
    for s in sectors_for_funds:
        key = s.lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(s)
    return digests, unique
