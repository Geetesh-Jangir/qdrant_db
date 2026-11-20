"""Per-stock week story for fund holders (fund week flow)."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Literal

from ai_insight.common.prose_guard import scrub_refusal_prose, split_sentences
from new.equity_week_llm import equity_week_llm_kwargs
from news_rag.llm_client import LlmCallResult, call_json_llm

Move = Literal["up", "down"]
_MAX_WHY_WORDS = 75
_NUM_IN_PROSE = re.compile(
    r"\b\d{1,3}(?:[.,]\d+)?\s*%|\b₹\s*[\d,]+|(?:\d+,?)+\s*(?:crore|lakh|million|billion)\b",
    re.I,
)

_RECAP_VOICE = re.compile(
    r"\b(the articles?|headline|supplied|reported in|according to the)\b|"
    r"doesn'?t (?:clearly )?explain|it'?s unclear",
    re.I,
)

_SYSTEM = """You explain why a stock in a mutual fund had the week it had, for the fund owner reading below.

Output JSON only: {"why": string, "skip": boolean}

When skip is false:
- why is 2–4 short sentences (about 45–75 words). Plain English.
- Explain the business/market story and cause → effect. Mention timing vs the week's price path in words (e.g. "jumped after results, eased later") — no daily price table in the text.
- Do NOT put percentages, rupee amounts, or precise statistics in why (the stock's week % is shown separately in the UI).
- No portfolio-weight or fund-impact math. No "the article". No buy/sell advice.

Set skip true only when none of the articles are about this company. why must be "" when skip is true."""


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


def scrub_recap_voice(text: str) -> str:
    kept = [s for s in split_sentences(text) if not _RECAP_VOICE.search(s)]
    return " ".join(kept).strip() if kept else text.strip()


def scrub_number_heavy_sentences(text: str) -> str:
    kept = [s for s in split_sentences(text) if len(_NUM_IN_PROSE.findall(s)) <= 1]
    if kept:
        return " ".join(kept).strip()
    cleaned = re.sub(_NUM_IN_PROSE, " ", text or "")
    return " ".join(cleaned.split())


def polish_why(text: str) -> str:
    text = scrub_refusal_prose(text)
    text = scrub_recap_voice(text)
    text = scrub_number_heavy_sentences(text)
    return clamp_why_paragraph(text)


def _short_name(name: str) -> str:
    return re.sub(r"\s+(Limited|Ltd\.?)$", "", name, flags=re.I).strip() or name


def _fmt_nav_daily(points: list[dict[str, Any]]) -> str:
    if not points:
        return "  (none)"
    return "\n".join(f"  {p.get('date')}: NAV {p.get('nav')}" for p in points)


def _fmt_stock_daily(prices: list[dict[str, Any]]) -> str:
    if not prices:
        return "  (none)"
    lines = []
    for p in prices:
        vol = p.get("volume")
        vol_s = f", vol {vol:,}" if isinstance(vol, int) else ""
        lines.append(f"  {p.get('date')}: close {p.get('close')}{vol_s}")
    return "\n".join(lines)


def _fmt_movers_daily(movers: list[dict[str, Any]]) -> str:
    if not movers:
        return "  (none)"
    chunks: list[str] = []
    for m in movers:
        label = _short_name(str(m.get("instrument_name") or ""))
        lines = [f"  {label} (week {m.get('change_1w_pct')}%):"]
        for p in m.get("daily_prices") or []:
            vol = p.get("volume")
            vol_s = f", vol {vol:,}" if isinstance(vol, int) else ""
            lines.append(f"    {p.get('date')}: {p.get('close')}{vol_s}")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


def _user_prompt(block: dict[str, Any]) -> str:
    name = block.get("instrument_name") or ""
    ch = block.get("change_1w_pct")
    move = block.get("move") or "up"
    fund = block.get("fund_name") or "the fund"
    arts = block.get("articles") or []
    lines = [
        f"Fund context: {fund}",
        f"Holding: {name}",
        f"Stock week change: {ch}%",
        f"Direction: {'up' if move == 'up' else 'down'} week",
        "",
        "Fund NAV by day:",
        _fmt_nav_daily(block.get("fund_nav_daily") or []),
        "",
        f"{name} share price by day:",
        _fmt_stock_daily(block.get("daily_prices") or []),
        "",
        "Other top movers this week (price by day):",
        _fmt_movers_daily(block.get("movers_daily") or []),
        "",
        f"News ({len(arts)} articles — use fully):",
    ]
    for i, art in enumerate(arts, 1):
        body = str(art.get("full_text") or art.get("snippet") or "").strip()
        lines.extend([f"--- {i} ---", f"Title: {art.get('title') or ''}", body, ""])
    lines.append(
        "Write one rich paragraph: main drivers, how the week traded vs the news, "
        "mixed signals if any, and how it fits the week's up/down move."
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
            max_tokens=280,
            stage="equity_fund_week_stock",
            response_schema={
                "type": "object",
                "properties": {"why": {"type": "string"}, "skip": {"type": "boolean"}},
                "required": ["why", "skip"],
            },
            **equity_week_llm_kwargs(temperature=0.35),
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

    why = polish_why(str(raw.get("why") or "").strip())
    if not why or len(why.split()) < 12:
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