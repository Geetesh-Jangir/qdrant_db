"""DeepSeek — structured insight (bullets + summary) from retrieved articles."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx

from news_rag.config import get_settings
from news_rag.insight_format import (
    clamp_bullets,
    clamp_summary,
    format_insight_display,
    parse_structured_insight,
)
from news_rag.insights import build_structured_insight_from_articles
from news_rag.llm_text import extract_assistant_text
from news_rag.parse import ParsedQuery
from news_rag.query_log import clip_log_text

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

SYSTEM_PROMPT = """You help Indian investors understand recent Indian market news in clear, simple English.

You receive a user question and numbered article excerpts. Use ONLY facts from those excerpts.

Write your reply in exactly this structure (plain text, no markdown headers other than the labels below):

BULLETS:
- Exactly 2 or 3 bullet lines (no more). Each line starts with "- ".
- Each bullet is ONE sentence (about 20–28 words): a concrete fact FROM the excerpt (number, date, who did what) PLUS a brief "so what" for investors. Example style: "RBI drained surplus liquidity via swaps while banks may still need ₹1.5L cr capital by 2028 largely to refinance AT-1 bonds."
- Do NOT copy or lightly rephrase article titles. Do not write headline-style bullets with no detail.
- Do NOT use "Line1", line numbers, word counts, or cut-off sentences.

SUMMARY:
One short paragraph of about 40–55 words (2–4 sentences). Tie the bullets to the user's question in plain prose. No bullet characters. No buy/sell advice. No URLs. Do not mention impact scores or internal labels.
"""


def _format_context(articles: list[dict]) -> str:
    blocks = []
    for index, row in enumerate(articles, start=1):
        blocks.append(
            f"[{index}] title={row.get('title')!r}\n"
            f"    source={row.get('source')} published={row.get('published_at')}\n"
            f"    direction={row.get('direction')} event={row.get('event_type')} "
            f"entities={row.get('entity_names')}\n"
            f"    text={row.get('snippet')!r}"
        )
    return "\n\n".join(blocks)


def _insight_payload(
    bullets: list[str],
    summary: str,
    *,
    insight_source: str,
    parsed: ParsedQuery,
    sources: list[dict],
) -> dict:
    display = format_insight_display(bullets, summary)
    return {
        "answer": display,
        "insight": display,
        "insight_bullets": bullets,
        "insight_summary": summary,
        "insight_source": insight_source,
        "sources": sources,
        "window": parsed.window_label,
        "entities": parsed.entity_resolved,
        "entity_match_note": parsed.entity_match_note,
    }


def empty_answer(parsed: ParsedQuery) -> dict:
    window = parsed.window_label
    entity_bit = ""
    if parsed.entity_match_note == "not_in_corpus" and parsed.stock_hint:
        entity_bit = f" We could not match “{parsed.stock_hint}” to a name in the news store."
    text = (
        f"No matching news was found for {window}.{entity_bit} "
        "Try a wider date range or a different company name."
    )
    return {
        "answer": text,
        "insight": text,
        "insight_bullets": [],
        "insight_summary": text,
        "sources": [],
        "window": parsed.window_label,
        "entities": parsed.entity_resolved,
        "entity_match_note": parsed.entity_match_note,
        "insight_source": "no_articles",
    }


def generate_answer(
    parsed: ParsedQuery,
    articles: list[dict],
    *,
    query_log: QueryLogger | None = None,
) -> dict:
    if not articles:
        return empty_answer(parsed)

    settings = get_settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("Set DEEPSEEK_API_KEY in .env")

    user_content = (
        f"Question: {parsed.question}\n"
        f"Time window: {parsed.window_label}\n"
        f"Resolved entities: {', '.join(parsed.entity_resolved) or '(none — searched broadly)'}\n\n"
        f"Articles:\n{_format_context(articles)}\n\n"
        "For BULLETS, use facts from each article's text= excerpt (numbers, actions, dates). "
        "Do not rewrite title= lines as bullets."
    )

    url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": settings.deepseek_max_tokens,
        "temperature": 0.25,
    }
    if query_log is not None:
        query_log.write(
            f"deepseek request url={url} model={settings.deepseek_model} "
            f"max_tokens={settings.deepseek_max_tokens} "
            f"system_chars={len(SYSTEM_PROMPT)} user_chars={len(user_content)}"
        )

    started = time.perf_counter()
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        duration = time.perf_counter() - started
        if query_log is not None and response.status_code >= 400:
            query_log.log_error(
                "deepseek",
                f"http_status={response.status_code} body={response.text[:500]}",
            )
        response.raise_for_status()
        data = response.json()

    usage = data.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = usage.get("total_tokens")
    if query_log is not None:
        query_log.record_deepseek(
            model=settings.deepseek_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=int(total_tokens) if total_tokens is not None else None,
            duration_sec=duration,
            http_status=response.status_code,
        )

    raw = extract_assistant_text(data)
    if query_log is not None:
        query_log.write(f"deepseek raw_preview={clip_log_text(raw, 500)}")

    bullets, summary = parse_structured_insight(raw)
    insight_source = "deepseek"

    if not bullets and not summary:
        bullets, summary = build_structured_insight_from_articles(parsed, articles)
        insight_source = "articles_fallback"
        if query_log is not None:
            query_log.write("insight llm_empty=true reason=empty_llm_content")
    elif not summary and bullets:
        summary = "These are the main themes from recent news in your store for this question."

    bullets = clamp_bullets(
        bullets,
        max_count=settings.insight_max_bullets,
        max_chars=settings.insight_bullet_max_chars,
    )
    summary = clamp_summary(summary, max_words=settings.insight_summary_max_words)

    sources = [
        {
            "title": row.get("title"),
            "url": row.get("url"),
            "source": row.get("source"),
            "published_at": row.get("published_at"),
        }
        for row in articles
    ]

    display = format_insight_display(bullets, summary)
    if query_log is not None:
        query_log.log_insight_output(
            insight_source=insight_source,
            char_count=len(display),
            preview=display,
        )
        query_log.write(f"insight_bullets_count={len(bullets)} summary_words={len(summary.split())}")

    return _insight_payload(
        bullets,
        summary,
        insight_source=insight_source,
        parsed=parsed,
        sources=sources,
    )
