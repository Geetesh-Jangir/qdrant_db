"""Prompts for per-stock holding insights."""

from __future__ import annotations

from typing import Any

from ai_insight.holding_insights.config import HOLDING_LOOKBACK_DAYS, HOLDING_PRICE_BARS
from ai_insight.holding_insights.news import NewsArticle

SYSTEM_PROMPT = """You write short impact-led insights for mutual fund investors who hold this stock—not news summaries.

The user message always includes stock name, 7 daily OHLCV bars, and news from the last 7 days. Never claim input is missing when those sections are present.

Output: ONLY one JSON object with keys skip, insight, reason_if_skipped (use null when skip is false).
Field insight must be one plain paragraph (no line breaks): 2–3 short sentences, 24–36 words total — count before you answer. No bullets or markdown.

Impact-first (required):
- Every sentence must answer "so what for someone holding this in a fund?" — not "what happened."
- Name the investor angle: margins, growth, governance risk, regulation, sentiment, competition, or funding cost—only if supported by the news.
- Tie sector or market moves to this stock only when the input links them; do not invent market impact.
- Do NOT list events, rates, or products without saying how they could affect holders near term.
- Never open with a headline repeat; lead with why it matters.

Pick news:
- Prefer articles with clear holder impact (relevance/impact scores in the input are hints).
- Ignore low-impact, stale, or tangential articles silently.
- Do NOT write an information brief, earnings table, or price run-down.

Numbers:
- Prefer words over figures. Use at most one price or % move in the whole insight, only if news alone is not enough.
- Do not stack dates, targets, broker names, or multiple percentages.

Strict:
- Use only facts from the input. News claims need a date only when you cite a specific event.
- Live session price is not a closing price.
- No advice, portfolio %, or filler.
- If no news shows a credible holder impact, set skip true and explain in reason_if_skipped."""


def _bar_line(bar: dict[str, Any]) -> str:
    state = "live" if bar.get("session_state") == "live" else "settled"
    return (
        f"{bar['date']}: O={bar['open']} H={bar['high']} L={bar['low']} C={bar['close']} "
        f"vol={bar['volume']} ({state})"
    )


def build_user_prompt(
    stock_name: str,
    sector: str,
    price_snapshot: dict[str, Any],
    articles: list[NewsArticle],
) -> str:
    hints = price_snapshot.get("pattern_hints") or {}
    bars = (price_snapshot.get("bars") or [])[-HOLDING_PRICE_BARS:]
    lines = [
        f"Stock: {stock_name}",
        f"Sector: {sector}",
        f"Data window: prices last {HOLDING_LOOKBACK_DAYS} sessions; news prioritizes last {HOLDING_LOOKBACK_DAYS} days (may include up to 14d if thin).",
        f"News articles attached: {len(articles)}",
        "",
        "Last 7 sessions (use for grounding only—do not dump into insight):",
        (
            f"Latest {price_snapshot.get('latest_price')} ({price_snapshot.get('session_state')}) "
            f"on {price_snapshot.get('price_as_of')}; 7-session move {hints.get('week_change_pct')}%."
        ),
        f"One row per session day ({len(bars)} days):",
    ]
    for bar in bars:
        lines.append(_bar_line(bar))
    lines.extend(
        [
            "",
            f"News (pick items with clear holder/market impact; relevance and impact scores are hints):",
        ]
    )
    for i, art in enumerate(articles, start=1):
        lines.append(
            f"[{i}] ({art.published_at}, relevance={art.relevancy_score}, impact={art.nav_impact_display}, "
            f"{art.sentiment}) {art.headline}"
        )
        lines.append(art.full_text)
        lines.append("")

    lines.append(
        "Task: JSON insight = one paragraph, 24–36 words. For a fund holder: what could matter for this stock "
        "and why (risk, earnings path, sentiment)—impact first, not a news recap."
    )
    return "\n".join(lines)