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
from news_rag.snippet_clean import article_body_for_llm

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

DIGEST_SYSTEM = """You analyze news articles for one topic focus (gold, silver, holding, sector, or macro).
When fund context is provided, explain what the news means for THAT fund's holdings/sectors (not generic market commentary).
When holdings_market is present (check linked_articles per holding), produce digest items that explain WHY the stock moved using the article body, not the title alone.
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
CRITICAL: Be extremely strict about sector assignment. 
- Only add a sector to sectors_positive if the news explicitly states it benefits, rises, or has a positive outlook.
- Only add a sector to sectors_negative if the news explicitly states it faces headwinds, falls, takes a hit, or has a negative outlook.
- Do not list a sector just because it's mentioned. It must have a clear directional impact.

If articles are empty, say no matching news was found. Do not invent macro reasons without article support.

PLAIN LANGUAGE: Write for a reader new to markets. Explain jargon in the same sentence (e.g. Nifty = main Indian stock index).
Use short sentences in summary and meaning fields."""

MARKET_PULSE_DIGEST_ADDENDUM = """
MARKET PULSE theme (many articles on the same topic = important right now).
Summarize ONE event in simple English: what happened, why people care, and which types of mutual funds or sectors feel it (banks, IT, etc.).
Do not repeat other themes. One strong item in items[] is enough. meaning field must be understandable without finance background."""

MARKET_PULSE_BATCH_SYSTEM = """You receive up to 8 MACRO news themes. Each theme has many articles in our database; you get ONE representative article per theme.
Return ONLY JSON:
{
  "focus": "market_pulse",
  "summary": "3-5 sentences: the big picture for Indian markets right now, plain English",
  "items": [
    {
      "theme": "theme label",
      "headline": "short headline (do not copy full URL domain)",
      "direction": "positive|negative|neutral|unclear",
      "max_impact": 0,
      "articles_in_theme": 0,
      "meaning": "2-3 sentences: what happened, market impact, which mutual fund sectors are affected"
    }
  ],
  "sectors_positive": ["names of sectors explicitly stated to benefit or be positively affected, e.g. Information Technology, Banking"],
  "sectors_negative": ["names of sectors explicitly stated to face headwinds or be adversely affected, e.g. Real Estate, Automobiles"]
}
CRITICAL SECTOR ASSIGNMENT:
- sectors_positive: Sectors explicitly stated to rise, gain, benefit from catalysts (like weak rupee for exporters), or demonstrate strong operational resilience/credit growth.
- sectors_negative: Sectors explicitly stated to fall, take a hit, worst affected, face margin squeeze, or face headwinds.
- Do NOT guess or infer impacts without clear evidence in the article body.
- If a sentiment filter is provided, ensure your sector categorizations strictly align with it.

Use only facts from the provided representatives. Identify all beneficiary and negatively affected sectors accurately. One item per theme. No buy/sell advice."""


@dataclass
class LayerDigest:
    layer: str
    focus: str = ""
    summary: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)
    sectors_positive: list[str] = field(default_factory=list)
    sectors_negative: list[str] = field(default_factory=list)
    error: str = ""


def digest_market_pulse_representatives(
    question: str,
    representatives: list[dict[str, Any]],
    *,
    sentiment: str = "",
    query_log: QueryLogger | None = None,
) -> LayerDigest:
    if not representatives:
        return LayerDigest(
            layer="macro",
            focus="market_pulse",
            summary="No macro themes were clustered for this window.",
        )
    if not llm_api_key_configured(get_settings()):
        return LayerDigest(
            layer="macro",
            focus="market_pulse",
            summary=f"{len(representatives)} macro themes (digest skipped — no LLM).",
            items=[
                {
                    "theme": r.get("theme"),
                    "headline": str(r.get("title") or "")[:120],
                    "meaning": str(r.get("snippet") or "")[:240],
                    "direction": r.get("direction") or "unclear",
                    "max_impact": r.get("max_impact"),
                    "articles_in_theme": r.get("articles_in_theme"),
                }
                for r in representatives
            ],
        )
    user = (
        f"Question: {question}\n"
        f"Sentiment filter requested: {sentiment}\n\n"
        f"Representative articles (one per top theme, sorted by coverage):\n"
        f"{json.dumps(representatives, ensure_ascii=False)}"
    )
    settings = get_settings()
    try:
        res = call_json_llm(
            system_prompt=MARKET_PULSE_BATCH_SYSTEM,
            user_content=user,
            model_override=contract_model(settings),
            max_tokens=1200,
            temperature=0.15,
            query_log=query_log,
        )
        parsed = parse_json_from_text(res.raw_text) or {}
        items = parsed.get("items") if isinstance(parsed.get("items"), list) else []
        return LayerDigest(
            layer="macro",
            focus="market_pulse",
            summary=str(parsed.get("summary") or "").strip(),
            items=items,
            sectors_positive=[str(x) for x in (parsed.get("sectors_positive") or [])],
            sectors_negative=[str(x) for x in (parsed.get("sectors_negative") or [])],
        )
    except Exception as exc:
        logger.warning("market_pulse batch digest failed: %s", exc)
        if query_log is not None:
            query_log.write(f"MARKET_PULSE_DIGEST_FAIL {exc}")
        return LayerDigest(layer="macro", focus="market_pulse", error=str(exc))


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
    for a in articles[:8]:
        body = article_body_for_llm(a, limit=1000)
        slim.append(
            {
                "title": a.get("title"),
                "body": body,
                "snippet": body,
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
    system_prompt = DIGEST_SYSTEM
    if (focus or "").startswith("pulse_") or (label or "").startswith("pulse"):
        system_prompt = f"{DIGEST_SYSTEM}\n\n{MARKET_PULSE_DIGEST_ADDENDUM}"
    settings = get_settings()
    try:
        res = call_json_llm(
            system_prompt=system_prompt,
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
    market_pulse_representatives: list[dict[str, Any]] | None = None,
) -> tuple[list[LayerDigest], list[str]]:
    digests: list[LayerDigest] = []
    if market_pulse_representatives:
        batch = digest_market_pulse_representatives(
            question,
            market_pulse_representatives,
            sentiment=sentiment,
            query_log=query_log,
        )
        digests.append(batch)

    fund_ctx = {
        "nav": fund_nav_data,
        "holdings": holdings_rows[:8],
        "sectors": sector_rows[:8],
    }
    jobs: list[tuple[str, str, list[dict]]] = []
    if articles_by_focus:
        pulse_jobs: list[tuple[str, str, list[dict]]] = []
        other_jobs: list[tuple[str, str, list[dict]]] = []
        for focus_key, arts in articles_by_focus.items():
            if not arts:
                continue
            if str(focus_key).startswith("pulse_"):
                if not market_pulse_representatives:
                    pulse_jobs.append(("macro", focus_key, arts))
            else:
                layer = "macro" if focus_key in ("gold", "silver", "macro") else focus_key
                other_jobs.append((layer, focus_key, arts))
        pulse_jobs.sort(key=lambda j: -len(j[2]))
        jobs.extend(pulse_jobs[:5])
        jobs.extend(other_jobs)
    if not jobs and not market_pulse_representatives:
        for layer in ("holding", "sector", "macro"):
            arts = articles_by_layer.get(layer) or []
            if arts:
                jobs.append((layer, layer, arts))
    if not jobs:
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

    with ThreadPoolExecutor(max_workers=max(1, min(6, len(jobs)))) as pool:
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

    sectors_for_funds = []
    for d in digests:
        if sentiment == "positive":
            sectors_for_funds.extend(d.sectors_positive)
        elif sentiment == "negative":
            sectors_for_funds.extend(d.sectors_negative)
        else:
            sectors_for_funds.extend(d.sectors_negative + d.sectors_positive)
    seen = set()
    unique = []
    for s in sectors_for_funds:
        key = s.lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(s)
    return digests, unique
