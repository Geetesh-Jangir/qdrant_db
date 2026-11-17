"""Prompts for per-stock holding insights."""

from __future__ import annotations

from typing import Any

from ai_insight.holding_insights.config import HOLDING_LOOKBACK_DAYS, HOLDING_PRICE_BARS
from ai_insight.holding_insights.news import NewsArticle

SYSTEM_PROMPT = """You write short, readable stock insights—not news summaries or data dumps.

The user message includes stock name, 7 daily price bars, recent news, and the stock's week change %. Never claim input is missing when those sections are present.

Output: ONLY one JSON object with keys skip, headline, insight, reason_if_skipped (use null when skip is false).

Headline (required when skip is false):
- One short eye-catching line for the stock—not the body insight.
- Format: "{Short stock name} up/down X% on/as/due to {driver from news}" using the EXACT week change % given in the user message (X must match; round to one decimal).
- Driver must come only from supplied news (rates, regulation, earnings theme, governance, etc.)—no invented causes.
- 5–14 words. No portfolio or fund language.

Field insight must be one plain paragraph (no line breaks): 2–3 short sentences, 24–36 words total — count before you answer. No bullets or markdown. Do not repeat the headline verbatim.

Voice and focus:
- Write about this stock and its impact: earnings quality, margins, growth, governance, regulation, sentiment, competition, funding—only what the input supports.
- Explain why the story matters for the stock and the market around it. Do NOT mention portfolios, ownership, or how much anyone is invested.
- Sound like a clear market insight: confident, plain English, no jargon stacks.
- Never open with a headline repeat; lead with impact, not events.
- Do NOT list products, rate tables, or dates without saying what they change for the stock.

Price week change:
- The input gives a 7-session (week) % change. Weave it in naturally once if it helps the story (e.g. "after a firm week" or "despite a small weekly slip")—words preferred over printing the %; one % only if it sharpens impact.
- Do not make the whole paragraph about price action.

Pick news:
- Prefer articles with clear stock/market impact (relevance/impact scores are hints).
- Ignore low-impact, stale, or tangential articles silently.

Strict:
- Use only facts from the input. No advice, targets, or broker calls.
- Live session price is not a closing price.
- If nothing credibly affects the stock outlook, set skip true and explain in reason_if_skipped."""


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
        "Last 7 sessions (grounding—fold week tone into the insight, do not list bars):",
        (
            f"Latest {price_snapshot.get('latest_price')} ({price_snapshot.get('session_state')}) "
            f"on {price_snapshot.get('price_as_of')}; week change {hints.get('week_change_pct')}% "
            f"(use in prose as week move, not a separate stats line)."
        ),
        f"One row per session day ({len(bars)} days):",
    ]
    for bar in bars:
        lines.append(_bar_line(bar))
    lines.extend(
        [
            "",
            "News (pick items with clear stock and market impact; relevance and impact scores are hints):",
        ]
    )
    for i, art in enumerate(articles, start=1):
        lines.append(
            f"[{i}] ({art.published_at}, relevance={art.relevancy_score}, impact={art.nav_impact_display}, "
            f"{art.sentiment}) {art.headline}"
        )
        lines.append(art.full_text)
        lines.append("")

    week = hints.get("week_change_pct")
    short = stock_name.replace(" Limited", "").replace(" Ltd.", "").strip()
    lines.append(
        f"Headline checklist: use short name \"{short}\"; week change is exactly {week}% — headline must show that % "
        f"with up/down/flat and a news-based reason (on/as/due to/because of)."
    )
    lines.append(
        "Task: JSON headline + insight. insight = one readable paragraph, 24–36 words—stock impact from news; "
        "week tone woven in if useful. Do not repeat the headline in insight."
    )
    return "\n".join(lines)