"""Per-stock narrative from full news articles (fund week flow)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Literal

from ai_insight.common.prose_guard import split_sentences
from news_rag.llm_client import LlmCallResult, call_json_llm

Move = Literal["up", "down"]
_MAX_WHY_WORDS = 80

_SYSTEM = """You explain in very simple words why an Indian stock went up or down this past week.

Output JSON only: {"why": string, "skip": boolean}

When skip is false:
- why is ONE short paragraph: 2–3 sentences, 45–75 words. No lists, no jargon.
- Pick only the 1–2 news facts that best match the week's direction (up vs down). Drop the rest.
- For each fact you keep, spell out the link: what happened in the news, and why that would make buyers happy or sellers nervous (plain cause → effect on the share price).
- If news is mixed, say so in one line: good X but worrying Y, and which side likely won this week.
- Use everyday words (profit, loans, fuel cost, court case, big investor selling). Skip broker names unless essential.
- No buy/sell advice. Only use facts from the articles.

Set skip true only when articles are not about this company. why must be "" when skip is true.

Never mention missing news."""


def clamp_why_paragraph(text: str, *, max_words: int = _MAX_WHY_WORDS) -> str:
    words = 0
    kept: list[str] = []
    for sentence in split_sentences(text):
        w = len(sentence.split())
        if words + w > max_words and kept:
            break
        kept.append(sentence)
        words += w
    return " ".join(kept) if kept else text.strip()


def _short_name(name: str) -> str:
    import re

    return re.sub(r"\s+(Limited|Ltd\.?)$", "", name, flags=re.I).strip() or name


def _user_prompt(block: dict[str, Any]) -> str:
    name = block.get("instrument_name") or ""
    ch = block.get("change_1w_pct")
    move = block.get("move") or "up"
    arts = block.get("articles") or []
    lines = [
        f"Stock: {name}",
        f"Week change: {ch}%",
        f"Move: {move}",
        "",
        f"Articles ({len(arts)}). Use all of them:",
    ]
    for i, art in enumerate(arts, 1):
        body = str(art.get("full_text") or art.get("snippet") or "").strip()
        lines.extend(
            [
                f"--- Article {i} ---",
                f"Title: {art.get('title') or ''}",
                f"Date: {art.get('published_at') or ''}",
                body,
                "",
            ]
        )
    lines.append(
        "Write one short paragraph (under 75 words). "
        f"The stock was {'up' if move == 'up' else 'down'} this week — "
        "say which news best explains that and how each point links to the move."
    )
    return "\n".join(lines)


def explain_one_block(block: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    out = dict(block)
    if dry_run or not block.get("articles"):
        out["why"] = None
        out["why_skip"] = True
        out["usable_news"] = False
        return out

    user = _user_prompt(block)
    try:
        result = call_json_llm(
            system_prompt=_SYSTEM,
            user_content=user,
            max_tokens=200,
            temperature=0.25,
            stage="equity_fund_week_stock",
            response_schema={
                "type": "object",
                "properties": {"why": {"type": "string"}, "skip": {"type": "boolean"}},
                "required": ["why", "skip"],
            },
        )
    except Exception:
        out["why"] = None
        out["why_skip"] = True
        out["usable_news"] = False
        return out

    raw = result.parsed if isinstance(result, LlmCallResult) else result
    if not isinstance(raw, dict) or raw.get("skip"):
        out["why"] = None
        out["why_skip"] = True
        out["usable_news"] = False
        return out

    why = clamp_why_paragraph(str(raw.get("why") or "").strip())
    if not why or len(why.split()) < 8:
        out["why"] = None
        out["why_skip"] = True
        out["usable_news"] = False
        return out

    out["why"] = why
    out["why_skip"] = False
    out["usable_news"] = True
    return out


def attach_stock_whys(
    stock_news: list[dict[str, Any]],
    *,
    dry_run: bool = False,
    max_workers: int = 4,
) -> list[dict[str, Any]]:
    if dry_run or not stock_news:
        return stock_news

    workers = min(max_workers, len(stock_news))
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(explain_one_block, b, dry_run=dry_run): i for i, b in enumerate(stock_news)}
        buf: dict[int, dict[str, Any]] = {}
        for fut in as_completed(futs):
            buf[futs[fut]] = fut.result()
        results = [buf[i] for i in range(len(stock_news))]
    return [b for b in results if b.get("usable_news") and not b.get("why_skip") and b.get("why")]