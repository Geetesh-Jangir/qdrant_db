"""Final LLM answer from tool outputs and news digests."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.json_util import safe_json_dumps
from news_rag.llm_client import call_insight_llm, composer_model, llm_api_key_configured
from news_rag.cross_impact import CROSS_IMPACT_COMPOSER_ADDENDUM, cross_impact_from_plan
from news_rag.article_pool import collect_bundle_articles
from news_rag.market_pulse import (
    market_pulse_data_from_bundle,
    market_pulse_from_plan,
    market_pulse_representatives_from_clusters,
)
from news_rag.news_digest import LayerDigest
from news_rag.snippet_clean import article_body_for_llm
from news_rag.llm_text import parse_json_from_text

INSTITUTIONAL_ANALYST_RULES = """SECTOR AND FUND RULES
- A sector bullet opens with the sector name in bold, then an em dash: **Oil & Gas** — producers gain when crude rises; marketers face losses if pump prices stay fixed.
- Allowed sector names are sectors_positive, sectors_negative, ranked_funds.matched_sectors, and sectors named inside digests. Use at most three.
- Display names: Banks → Banking & Financial Services; IT - Software or Software → Information Technology; Pharmaceuticals → Pharmaceuticals & Biotechnology.
- A company (ONGC, BPCL, HDFC Bank, Tata Motors) is not a sector. Mention it inside the sector bullet.
- Crude, bond yields, the repo rate, the rupee, and inflation go in one **Macro Backdrop** bullet. They are not sectors.
- Do not add Information Technology, Pharma, PSU banks, or Capital Goods unless a digest supports that sector or the user specifically asks for it.
- Sector-fund answers use only ranked_funds with sector_purity=dedicated_sectoral. Never present arbitrage, hybrid, multi-asset, or debt funds as sector equity.
- If defensive_alternatives is non-empty, at most one bullet titled **Defensive / Market-Neutral Alternatives**, and label those schemes as arbitrage or hybrid.
- If all_drawdown is true, or every 1-month return in ranked_funds is negative: the sector pulled back. Title **Most Resilient Performers** and do not call a loss a gain.
- If fund_rank_direction is positive and ranked_funds is empty: say no screened dedicated equity fund has a positive 1-month NAV. Do not substitute weaker or unrelated funds.
- If the user did not ask about funds or sectors and they are not highly relevant to the general market pulse, DO NOT include them. Be dynamic."""

MARKET_PULSE_COMPOSER_ADDENDUM = """MARKET OVERVIEW
Read market_pulse_representatives and the market_pulse digest. Write a dynamic summary. If the user asks a general market question (like 'what is happening'), focus on the macro themes. DO NOT force sector or fund bullets if the question doesn't specifically ask for them or if they aren't directly relevant to the core narrative. Skip theme labels such as Bond Yields or RBI Repo Rate as if they were sectors. If news_article_count is 0, say the archive had no matching articles and stop."""

if TYPE_CHECKING:
    from news_rag.ask_plan import AskPlan
    from news_rag.ask_execution import ExecutionBundle
    from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

COMPOSER_SYSTEM = """You write the final answer for an Indian mutual-fund research app. Context is already retrieved. You only turn that Context into a clear answer. Return JSON only. No markdown fences.

{
  "headline": "One sentence that answers the question and names the sector or fund. Bold that name only.",
  "narrative": "",
  "bullets": ["Four to six bullets. One claim each."],
  "closing_summary": "Two or three new sentences, 40 to 80 words. Do not repeat the headline or the bullets.",
  "advice_declined_note": ""
}

ANSWER THE QUESTION FIRST
- "Which sector benefits" → the headline names the sectors that benefit, and any sector the same news hurts.
- "What is happening / which sectors are working" → the headline states the market driver and the sectors in focus.
- "Best or worst funds" → the headline states whether those funds are up or down.
- A named fund → the headline says how this news reaches that fund. Stay on that fund.
- If the evidence is mixed, say the split. Do not force a cheerful beneficiary list.

FACTS
- Use the article body, not the title alone. Also use digests, ranked_funds, sectors_positive, sectors_negative, holdings, and NAV fields in Context.
- Copy percentages, weights, prices, and basis points exactly. Do not invent or round them into a new figure.
- Do not paste article titles, URLs, bylines, dates, "Published", "Updated", source names, "related articles", "Impact x/5", or "mood".
- Rewrite the news as one clean sentence. A bad bullet copies the snippet. A good bullet states the effect.

SHAPE
1. Optional **Macro Backdrop** — only when rates, crude, yields, inflation, or the rupee are part of the answer.
2. One bullet per sector, bold sector name first.
3. If the user asked for funds, or ranked_funds is non-empty: one bullet per fund with the fund name, sector weight %, 1-month NAV %, and 1-week NAV %.
- No second bullet that repeats a fact. The closing adds the implication only.
- holdings_market is rendered separately. Do not write a bullet per holding.
- No buy, sell, or target price. No glossary in parentheses. No "stay calm" or long-term lecture. Complete sentences. No ellipses.

""" + INSTITUTIONAL_ANALYST_RULES


_MAX_BOLD_PER_HEADLINE = 10
_MAX_BOLD_PER_BULLET = 10
_MAX_BOLD_PER_CLOSING = 14
_MAX_INSIGHT_BULLETS = 12
_DIGEST_INJECT_MAX = 2
_DIGEST_INJECT_MAX_PULSE = 6
_GENERIC_CLOSING_MARKERS = (
    "stay calm",
    "long-term perspective",
    "long-term financial goals",
    "hasty decisions",
    "$100 a barrel",
    "crude oil prices climb",
    "weather these ups and downs",
    "weather the ups and downs",
    "normal part of investing",
    "normal part of market",
    "fluctuations are a normal",
    "everyday mutual fund investors",
    "short-term market turbulence",
    "short-term headlines",
    "best approach is to stay",
    "let professional fund managers",
    "fund managers navigate",
    "instead of reacting",
    "broad diversification helps",
    "diversification helps cushion",
    "focus on your long-term",
)


def _is_generic_investing_closing(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in _GENERIC_CLOSING_MARKERS)


def _pulse_headline(clusters: list[dict[str, Any]]) -> str:
    labels = [str(c.get("label") or "").strip() for c in clusters[:4] if c.get("label")]
    if not labels:
        return "What is moving the Indian market right now"
    if len(labels) == 1:
        return f"**{labels[0]}** is in focus across today's market news"
    joined = ", ".join(f"**{x}**" for x in labels[:3])
    return f"Top themes in our news feed: {joined}"


def _pulse_closing_from_bullets(bullets: list[str], clusters: list[dict[str, Any]]) -> str:
    """One short close. Do not repeat the bullet list or the user's question."""
    names = _sector_names_from_bullets(bullets)
    if not names:
        names = [
            _display_sector_name(str(s))
            for c in clusters[:4]
            for s in (c.get("sectors") or [])[:1]
            if str(s).strip()
        ]
        names = list(dict.fromkeys(names))[:3]
    if names:
        return f"The sectors in focus are {', '.join(names)}."
    return ""


_GENERIC_MARKET_FLUFF = (
    "keeping a close eye",
    "continue to trade actively",
    "watching inflation",
    "reporting their latest",
    "investors are keeping",
    "foreign investors and local",
    "companies are reporting",
    "very carefully",
    "stock market right now",
)
_CLOSING_MIN_WORDS = 60
_CLOSING_MAX_WORDS = 160


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", (text or "").strip()))


def _clamp_closing_words(text: str, min_words: int = _CLOSING_MIN_WORDS, max_words: int = _CLOSING_MAX_WORDS) -> str:
    """Soft trim for closing_summary; keep full text if under max and reasonably long."""
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if not raw:
        return ""
    words = raw.split()
    if len(words) > max_words:
        trimmed = " ".join(words[:max_words])
        if not trimmed.endswith((".", "!", "?")):
            trimmed += "."
        return trimmed
    return raw


def _closing_from_bullets(headline: str, bullets: list[str], answer_parts: str) -> str:
    """Deterministic closing when the LLM omits closing_summary."""
    del answer_parts  # the question restatement must not be pasted back into the answer
    seeds: list[str] = []
    if headline and "related articles" not in headline.lower():
        seeds.append(headline.replace("**", ""))
    names = _sector_names_from_bullets(bullets)
    if names:
        seeds.append(f"Sectors covered: {', '.join(names)}.")
    blob = " ".join(seeds)
    sentences = _split_into_sentences(blob)
    if not sentences:
        return ""
    parts: list[str] = []
    total = 0
    for sent in sentences:
        w = _word_count(sent)
        if total + w > _CLOSING_MAX_WORDS and parts:
            break
        parts.append(sent)
        total += w
        if total >= _CLOSING_MIN_WORDS:
            break
    closing = " ".join(parts)
    return _clamp_closing_words(closing)


def _limit_bold_spans(text: str, budget: list[int]) -> str:
    """Remove excess ** markers; budget[0] decreases per kept span."""

    def repl(match: re.Match[str]) -> str:
        if budget[0] > 0:
            budget[0] -= 1
            return match.group(0)
        return match.group(1)

    return re.sub(r"\*\*([^*]+)\*\*", repl, text or "")


def _span_already_bold(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 2) : end + 2]
    return window.count("**") >= 2


def _bold_regex_matches(text: str, pattern: str, limit: int, *, flags: int = 0) -> str:
    if not text or limit <= 0:
        return text
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        if count >= limit:
            return match.group(0)
        start, end = match.span()
        if _span_already_bold(text, start, end):
            return match.group(0)
        count += 1
        core = match.group(1) if match.lastindex else match.group(0)
        return match.group(0).replace(core, f"**{core}**", 1)

    return re.sub(pattern, repl, text, flags=flags)


def _collect_impact_bold_terms(
    bundle: ExecutionBundle,
    nav: dict[str, Any] | None,
    holdings_market: list[dict[str, Any]] | None = None,
) -> list[str]:
    terms = _collect_bold_terms(bundle, nav)
    for snap in holdings_market or []:
        label = _short_holding_label(str(snap.get("name") or ""))
        if label:
            terms.append(label)
    for row in bundle.sector_rows or []:
        if not isinstance(row, dict):
            continue
        sector = str(row.get("sector") or "").strip()
        if sector and len(sector) >= 3:
            terms.append(sector)
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out[:14]


def _emphasize_impact_text(text: str, terms: list[str], *, max_bold_spans: int = 10) -> str:
    """Bold fund names, holdings, sectors, NAV, ₹ amounts, and % moves."""
    out = (text or "").strip()
    if not out:
        return out
    for term in sorted(terms, key=len, reverse=True):
        out = _wrap_first(out, term)
    out = _bold_regex_matches(out, r"(?<!\*)\b(NAV)\b(?!\*)", 2, flags=re.I)
    out = _bold_regex_matches(out, r"(₹\s?[\d,]+(?:\.\d+)?)", 4)
    out = _bold_regex_matches(out, r"(\d+(?:\.\d+)?%\s+weight)", 3, flags=re.I)
    out = _bold_regex_matches(out, r"([+-]?\d+(?:\.\d+)?%)", 8)
    out = _bold_regex_matches(
        out,
        r"\b(news driver|fund(?:'s)?\s+NAV|top holding|sector|portfolio)\b",
        3,
        flags=re.I,
    )
    return _limit_bold_spans(out, [max_bold_spans])


def _apply_impact_emphasis(
    headline: str,
    narrative: str,
    bullets: list[str],
    terms: list[str],
) -> tuple[str, str, list[str]]:
    return (
        _emphasize_impact_text(headline, terms, max_bold_spans=_MAX_BOLD_PER_HEADLINE),
        _emphasize_impact_text(narrative, terms, max_bold_spans=_MAX_BOLD_PER_HEADLINE),
        [_emphasize_impact_text(b, terms, max_bold_spans=_MAX_BOLD_PER_BULLET) for b in bullets],
    )


def _nav_payload(bundle: ExecutionBundle) -> dict[str, Any] | None:
    data = bundle.fund_nav_data
    if data:
        return data
    for key, val in bundle.tool_results.items():
        if key.startswith("fund_nav") and val.get("ok"):
            return val.get("data") or None
    return None


def _format_nav_bullet(nav: dict[str, Any]) -> str | None:
    if not nav:
        return None
    name = nav.get("fund_name") or "Fund"
    nav_val = nav.get("nav")
    nav_date = nav.get("nav_date") or ""
    if nav_val is None:
        return None
    parts = [f"**{name}** — unit price (**NAV**) **₹{nav_val}**"]
    if nav_date:
        parts.append(f"(as of **{nav_date}**)")
    ch = nav.get("day_change_pct")
    if ch is not None:
        try:
            parts.append(f"**day change** {float(ch):+.2f}%")
        except (TypeError, ValueError):
            parts.append(f"**day change** {ch}%")
    rets = nav.get("returns") or {}
    if isinstance(rets, dict):
        for label, keys in (
            ("1 week", ("1w", "1W")),
            ("1 month", ("1m", "1M")),
            ("1 year", ("1y", "1Y")),
        ):
            val = None
            for key in keys:
                if key in rets:
                    val = rets.get(key)
                    break
            if isinstance(val, dict) and val.get("change_pct") is not None:
                val = val.get("change_pct")
            if val is not None:
                try:
                    parts.append(f"**{label}** {float(val):+.2f}%")
                except (TypeError, ValueError):
                    parts.append(f"**{label}** {val}%")
    return " ".join(parts)


_BULLET_PREFIX_RE = re.compile(
    r"^(\*\*)?"
    r"(?:top\s+)?(?:holdings?|sectors?|news\s+drivers?|leadership\s*(?:&|and)\s*regulatory\s*context|"
    r"portfolio|allocation|performance|overview|context|insight|news\s+insight)"
    r"(\*\*)?\s*[:\-—]\s*",
    re.I,
)
_LAYER_PREFIX_RE = re.compile(
    r"^(\*\*)?(?:holding|sector|macro|market)(?:\s*news)?(\*\*)?\s*(?:—\s*news\s*insight)?\s*[:\-—]\s*",
    re.I,
)
_HANGING_TRAIL_RE = re.compile(
    r"\s*(?:So\s+for\s+(?:your|the)\s+fund|So\s+for\s+(?:your|the)\s+portfolio|This\s+matters\s+because|So\s+for\s+your)\s*[.:—\-…]*\s*$",
    re.I,
)


def _strip_bullet_prefix(text: str) -> str:
    t = (text or "").strip()
    for _ in range(4):
        m = _BULLET_PREFIX_RE.match(t) or _LAYER_PREFIX_RE.match(t)
        if not m:
            break
        t = t[m.end() :].strip()
    t = re.sub(r"^NAV:\s*", "", t, flags=re.I)
    t = _HANGING_TRAIL_RE.sub("", t).strip()
    if t and t[-1] not in ".!?":
        t += "."
    return t.strip()


def _split_into_sentences(text: str) -> list[str]:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z*])", t)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) >= 28:
            out.append(p)
    return out


def _normalize_bullet_key(text: str) -> str:
    return re.sub(r"\W+", " ", (text or "").lower()).strip()[:90]


def _topic_tokens(text: str) -> set[str]:
    stop = {
        "that",
        "this",
        "with",
        "from",
        "have",
        "been",
        "were",
        "will",
        "fund",
        "over",
        "past",
        "month",
        "news",
        "bank",
        "limited",
    }
    words = re.findall(r"[a-z]{4,}", (text or "").lower())
    return {w for w in words if w not in stop}


def _is_near_duplicate_bullet(a: str, b: str) -> bool:
    ta, tb = _topic_tokens(a), _topic_tokens(b)
    if not ta or not tb:
        return False
    overlap = len(ta & tb)
    denom = min(len(ta), len(tb))
    if denom == 0:
        return False
    if overlap / denom >= 0.5:
        return True
    shared_themes = (
        ("leadership", "ceo", "rbi", "succession", "handover"),
        ("liquidity", "rupee", "repo", "tightening"),
        ("crude", "bond", "yield", "inflation"),
        ("icici", "prudential", "stake", "approval"),
    )
    for theme in shared_themes:
        in_a = any(t in ta for t in theme)
        in_b = any(t in tb for t in theme)
        if in_a and in_b:
            return True
    return False


def _clean_prose_fragment(text: str, max_chars: int = 140) -> str:
    t = re.sub(r"\.{2,}|…+", "", (text or "").strip())
    t = re.sub(r"\s+Listen\s*$", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t)
    if not t:
        return ""
    sentences = _split_into_sentences(t)
    pick = sentences[0] if sentences else t
    if len(pick) > max_chars:
        pick = pick[:max_chars].rsplit(" ", 1)[0]
    pick = pick.rstrip(" ,;:-")
    if pick and pick[-1] not in ".!?":
        pick += "."
    return pick


def _dedupe_pulse_bullets(bullets: list[str], limit: int = 8) -> list[str]:
    """Keep one bullet per cluster/sector label; do not truncate to first sentence."""
    out: list[str] = []
    seen_labels: set[str] = set()
    for raw in bullets:
        b = _strip_bullet_prefix((raw or "").strip())
        b = re.sub(r"\.{2,}|…+", "", b)
        if len(b) < 20:
            continue
        label_m = re.match(r"\*\*([^*]+)\*\*", b)
        label_key = (label_m.group(1) if label_m else b[:48]).lower().strip()
        if not label_key or label_key in seen_labels:
            continue
        seen_labels.add(label_key)
        if len(b) > 680:
            b = b[:680].rsplit(" ", 1)[0] + "."
        out.append(b)
    return out[:limit]


def _dedupe_bullets(bullets: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in bullets:
        b = _strip_bullet_prefix(raw)
        b = re.sub(r"\.{2,}|…+", "", b)
        if not b:
            continue
        if len(b) < 15 and not re.search(r"[\d%₹]", b):
            continue
        key = _normalize_bullet_key(b)
        if not key or key in seen:
            continue
        if any(key in s or s in key for s in seen if len(s) > 40):
            continue
        if any(_is_near_duplicate_bullet(b, prev) for prev in out):
            continue
        seen.add(key)
        out.append(b)
    return out


def _polish_bullet_list(bullets: list[str], *, market_pulse: bool = False) -> list[str]:
    if market_pulse:
        return _dedupe_pulse_bullets(bullets)
    return _dedupe_bullets(bullets)


def _collect_bold_terms(bundle: ExecutionBundle, nav: dict[str, Any] | None) -> list[str]:
    terms: list[str] = []
    if nav:
        fn = str(nav.get("fund_name") or "").strip()
        if fn:
            terms.append(fn)
    for row in bundle.holdings_rows or []:
        if not isinstance(row, dict):
            continue
        for key in ("stock_name", "name", "company_name", "holding_name"):
            val = str(row.get(key) or "").strip()
            if val and len(val) >= 3:
                terms.append(val)
                break
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out[:8]


def _wrap_first(text: str, phrase: str) -> str:
    if not phrase or f"**{phrase}**" in text:
        return text
    m = re.search(re.escape(phrase), text, flags=re.I)
    if not m:
        return text
    start, end = m.span()
    return text[:start] + f"**{m.group(0)}**" + text[end:]


def _autobold_phrases(text: str, terms: list[str]) -> str:
    if not text or "**" in text:
        return text
    out = text
    for term in sorted(terms, key=len, reverse=True):
        out = _wrap_first(out, term)
    out = re.sub(
        r"(?<!\*)\b(NAV)\b(?!\*)",
        r"**\1**",
        out,
        count=1,
        flags=re.I,
    )
    out = re.sub(
        r"(₹\s?[\d,]+(?:\.\d+)?)",
        lambda m: f"**{m.group(1)}**" if "**" not in m.group(1) else m.group(1),
        out,
        count=2,
    )
    out = re.sub(
        r"([+-]?\d+(?:\.\d+)?%)",
        lambda m: f"**{m.group(1)}**" if "**" not in m.group(1) else m.group(1),
        out,
        count=3,
    )
    return out


def _narrative_to_bullets(narrative: str, max_items: int = 24) -> list[str]:
    text = (narrative or "").strip()
    if not text:
        return []
    chunks = re.split(r"\n\s*\n+", text)
    bullets: list[str] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if len(chunk) < 220:
            bullets.append(chunk)
        else:
            for sent in re.split(r"(?<=[.!?])\s+", chunk):
                sent = sent.strip()
                if len(sent) >= 30:
                    bullets.append(sent)
    return bullets[:max_items]


def _digest_already_covered(bullets: list[str], digest: LayerDigest) -> bool:
    blob = " ".join(bullets).lower()
    summary = (digest.summary or "").lower()
    if summary and len(summary) > 40 and summary[:60] in blob:
        return True
    for item in digest.items or []:
        meaning = str(item.get("meaning") or "").lower()
        if len(meaning) > 30 and meaning[:40] in blob:
            return True
    return False


def _short_holding_label(name: str) -> str:
    n = (name or "").strip()
    n = re.sub(r"\s+Limited$", "", n, flags=re.I)
    n = re.sub(r"\s+Ltd\.?$", "", n, flags=re.I)
    return n.strip() or name


def _news_reason_from_snap(snap: dict[str, Any]) -> str:
    news = snap.get("news") if isinstance(snap.get("news"), dict) else {}
    linked = news.get("linked_articles") if isinstance(news.get("linked_articles"), list) else []
    if not linked:
        return "No company-specific headline in our news corpus for this window."
    ranked = sorted(
        linked,
        key=lambda a: (-int(a.get("max_impact") or 0), str(a.get("direction") or "")),
    )
    top = ranked[0]
    snippet = str(top.get("snippet") or "").strip()
    title = str(top.get("title") or "").strip()
    reason = _clean_prose_fragment(snippet, max_chars=130) if len(snippet) >= 30 else _clean_prose_fragment(title, max_chars=120)
    return reason or "Related coverage in our news store (see sources)."


def _holding_bullet_from_snap(snap: dict[str, Any]) -> str | None:
    name = _short_holding_label(str(snap.get("name") or ""))
    if not name:
        return None
    try:
        weight = float(snap.get("weight_pct") or 0.0)
    except (TypeError, ValueError):
        weight = 0.0
    price = snap.get("price") if isinstance(snap.get("price"), dict) else {}
    if not price:
        return None
    ret_m = price.get("return_1m")
    ret_w = price.get("return_1w")
    if ret_m is not None:
        try:
            ret = float(ret_m)
            window = "month"
        except (TypeError, ValueError):
            ret = None
            window = ""
    elif ret_w is not None:
        try:
            ret = float(ret_w)
            window = "week"
        except (TypeError, ValueError):
            return None
    else:
        return None
    reason = _news_reason_from_snap(snap)
    nav_note = ""
    drag = price.get("approx_nav_contribution_1m_pct")
    if drag is None and window == "week":
        drag = price.get("approx_nav_contribution_1w_pct")
    if drag is not None:
        try:
            nav_note = (
                f" Because this company is **{weight:.2f}%** of the fund, that move alone "
                f"roughly changed the fund's unit price by about **{float(drag):+.2f}%** over the same period."
            )
        except (TypeError, ValueError):
            nav_note = ""
    weight_plain = f"about **{weight:.2f}%** of the fund is in **{name}**"
    if "no company-specific headline" in reason.lower():
        return (
            f"{weight_plain}. Its share price moved **{ret:+.2f}%** in the past {window}. "
            f"We did not find a clear news story on this company in our archive, but because it is a large "
            f"part of the fund, the price move still affects your fund's returns.{nav_note}"
        )
    verb = "went up" if ret >= 0 else "went down"
    return (
        f"{weight_plain}. The stock {verb} **{abs(ret):.2f}%** in the past {window}. "
        f"News we found: {reason} "
        f"In simple terms: this is one of the fund's biggest positions, so this news and price move "
        f"can move the fund's unit price up or down.{nav_note}"
    )


def _bullet_mentions_holding(bullet: str, name: str) -> bool:
    b = bullet.lower()
    short = _short_holding_label(name).lower()
    if short and short in b:
        return True
    first = short.split()[0] if short else ""
    return len(first) > 3 and first in b


def _holding_impact_score(snap: dict[str, Any]) -> float:
    try:
        weight = float(snap.get("weight_pct") or 0.0)
    except (TypeError, ValueError):
        weight = 0.0
    price = snap.get("price") if isinstance(snap.get("price"), dict) else {}
    ret = 0.0
    for key in ("return_1m", "return_1w"):
        try:
            ret = abs(float(price.get(key) or 0.0))
            if ret:
                break
        except (TypeError, ValueError):
            continue
    drag = 0.0
    for key in ("approx_nav_contribution_1m_pct", "approx_nav_contribution_1w_pct"):
        try:
            drag = abs(float(price.get(key) or 0.0))
            if drag:
                break
        except (TypeError, ValueError):
            continue
    news_n = int((snap.get("news") or {}).get("total") or 0)
    return drag * 200.0 + weight * (1.0 + ret * 0.15) + min(news_n, 4) * 3.0


def _query_focus_tokens(question: str, answer_parts: str) -> set[str]:
    blob = f"{question} {answer_parts}".lower()
    tokens = _topic_tokens(blob)
    extra = re.findall(r"[a-z]{5,}", blob)
    return tokens | {w for w in extra if w not in {"about", "there", "these", "those", "which"}}


def _is_nav_bullet(bullet: str, nav: dict[str, Any] | None) -> bool:
    low = (bullet or "").lower()
    if "nav" not in low:
        return False
    if re.search(r"₹\s*[\d,]+", bullet or ""):
        return True
    if nav and str(nav.get("fund_name") or "").lower() in low:
        return True
    return bool(re.search(r"\b(1\s*week|1\s*month|1\s*year)\b", low, re.I) and "return" in low)


def _bullet_relevance_score(
    bullet: str,
    *,
    nav: dict[str, Any] | None,
    holdings_market: list[dict[str, Any]] | None,
    sector_rows: list[dict[str, Any]],
    query_tokens: set[str],
) -> float:
    low = (bullet or "").lower()
    score = 0.0
    for snap in holdings_market or []:
        name = str(snap.get("name") or "")
        if name and _bullet_mentions_holding(bullet, name):
            score = max(score, 80.0 + _holding_impact_score(snap))
    for row in sector_rows or []:
        if not isinstance(row, dict):
            continue
        sector = str(row.get("sector") or "").strip()
        pct = row.get("percentage")
        if sector and sector.lower() in low:
            try:
                score = max(score, 45.0 + float(pct or 0.0))
            except (TypeError, ValueError):
                score = max(score, 45.0)
    if any(p in low for p in ("fund", "portfolio", "nav", "weight", "holding")):
        score += 12.0
    if "sector" in low and "%" in bullet:
        score += 20.0
    overlap = len(query_tokens & _topic_tokens(bullet))
    score += overlap * 6.0
    if nav and str(nav.get("fund_name") or "").lower() in low:
        score += 8.0
    return score


def _rank_bullets_by_fund_impact(
    bullets: list[str],
    *,
    nav: dict[str, Any] | None,
    nav_line: str | None,
    holdings_market: list[dict[str, Any]] | None,
    sector_rows: list[dict[str, Any]],
    question: str,
    answer_parts: str,
) -> list[str]:
    if not bullets:
        return bullets
    query_tokens = _query_focus_tokens(question, answer_parts)
    nav_bullets: list[str] = []
    rest: list[str] = []
    for b in bullets:
        if _is_nav_bullet(b, nav) or (nav_line and b.strip() == nav_line.strip()):
            nav_bullets.append(b)
        else:
            rest.append(b)
    if not nav_bullets and nav_line:
        nav_bullets = [nav_line]
        rest = [b for b in rest if b.strip() != nav_line.strip()]

    scored = [
        (
            _bullet_relevance_score(
                b,
                nav=nav,
                holdings_market=holdings_market,
                sector_rows=sector_rows,
                query_tokens=query_tokens,
            ),
            i,
            b,
        )
        for i, b in enumerate(rest)
    ]
    scored.sort(key=lambda t: (-t[0], t[1]))
    ordered_rest = [b for _, _, b in scored]
    # One NAV bullet first (prefer nav_line match)
    first_nav = nav_bullets[0] if nav_bullets else None
    out: list[str] = []
    if first_nav:
        out.append(first_nav)
    seen_nav = {_normalize_bullet_key(first_nav)} if first_nav else set()
    for b in ordered_rest:
        if _is_nav_bullet(b, nav):
            key = _normalize_bullet_key(b)
            if key in seen_nav:
                continue
            seen_nav.add(key)
        out.append(b)
    return out


def _is_generic_market_fluff(bullet: str) -> bool:
    low = (bullet or "").lower()
    if any(m in low for m in ("news we found", "news says", "articles in our", "headline:", "matching articles")):
        return False
    return any(p in low for p in _GENERIC_MARKET_FLUFF)


def _direction_plain(direction: str | None) -> str:
    d = (direction or "").strip().lower()
    if d == "positive":
        return "supportive for stocks"
    if d == "negative":
        return "pressuring stocks"
    if d == "neutral":
        return "mixed/neutral"
    return "unclear direction"


_SECTOR_DISPLAY = {
    "banks": "Banking & Financial Services",
    "finance": "Financial Services",
    "financial services": "Financial Services",
    "capital markets": "Capital Markets",
    "it - software": "Information Technology",
    "software": "Information Technology",
    "information technology": "Information Technology",
    "pharmaceuticals": "Pharmaceuticals",
    "pharmaceuticals & biotechnology": "Pharmaceuticals & Biotechnology",
    "healthcare services": "Healthcare Services",
    "automobiles": "Automobiles",
    "capital goods": "Capital Goods",
    "fmcg": "FMCG",
    "consumer durables": "Consumer Durables",
    "power": "Power",
    "realty": "Realty",
    "petroleum products": "Oil & Gas",
    "oil": "Oil & Gas",
}


def _display_sector_name(name: str) -> str:
    text = (name or "").strip()
    return _SECTOR_DISPLAY.get(text.lower(), text)


def _sector_names_from_bullets(bullets: list[str]) -> list[str]:
    skip = {"macro backdrop", "fund performance", "most resilient performers", "defensive / market-neutral alternatives"}
    names: list[str] = []
    for b in bullets:
        match = re.match(r"\*\*([^*]+)\*\*", (b or "").strip())
        if not match:
            continue
        label = match.group(1).strip()
        if label.lower() in skip or label.lower().startswith("fund performance"):
            continue
        if label not in names:
            names.append(label)
    return names[:4]


_MACRO_THEME_MARKERS = (
    "yield",
    "repo",
    "rbi",
    "crude",
    "nifty",
    "rupee",
    "inflation",
    "bond",
    "policy",
    "fii",
    "flow",
)


def _is_macro_theme_label(label: str) -> bool:
    low = (label or "").lower()
    return any(m in low for m in _MACRO_THEME_MARKERS)


def _build_news_backed_pulse_bullets(
    clusters: list[dict[str, Any]],
    digests: list[LayerDigest] | None,
) -> list[str]:
    """Plain sector and macro bullets. No article counts, impact scores, or mood tags."""
    macro_bits: list[str] = []
    sector_lines: list[str] = []
    seen_sectors: set[str] = set()

    def _add_sector(name: str, sentence: str) -> None:
        shown = _display_sector_name(name)
        key = shown.strip().lower()
        if not key or key in seen_sectors:
            return
        seen_sectors.add(key)
        text = _clean_prose_fragment(sentence, max_chars=220) if sentence else ""
        if text:
            sector_lines.append(f"**{shown}** — {text}")

    for cl in clusters[:8]:
        label = str(cl.get("label") or "").strip()
        sectors = [str(s).strip() for s in (cl.get("sectors") or []) if str(s).strip()]
        arts = cl.get("articles") if isinstance(cl.get("articles"), list) else []
        rep = arts[0] if arts else {}
        snippet = _clean_prose_fragment(str(rep.get("snippet") or rep.get("title") or ""), max_chars=220)
        if sectors:
            _add_sector(sectors[0], snippet)
        elif label and not _is_macro_theme_label(label):
            _add_sector(label, snippet)
        elif snippet:
            macro_bits.append(snippet)

    for d in digests or []:
        for name in (d.sectors_positive or [])[:3]:
            _add_sector(str(name), "")

    bullets: list[str] = []
    if macro_bits:
        joined = " ".join(macro_bits[:2])
        bullets.append(f"**Macro Backdrop** — {_clean_prose_fragment(joined, max_chars=360)}")
    bullets.extend(sector_lines[:4])
    return bullets


def _sector_fund_payload(bundle: ExecutionBundle) -> tuple[str, str, list]:
    found: tuple[str, str, list] | None = None
    for k, val in bundle.tool_results.items():
        if not val.get("ok"):
            continue
        if "sector_funds" not in k and "affected_funds" not in k:
            continue
        data = val.get("data") or {}
        payload = (
            str(data.get("direction") or ""),
            str(data.get("ranking_note") or ""),
            list(data.get("rankings") or []),
        )
        if "affected_funds" in k:
            return payload
        found = payload
    return found or ("", "", [])


def _claims_negative_fund_as_best(bullet: str) -> bool:
    low = bullet.lower()
    if "fund" not in low:
        return False
    if not re.search(r"-\d+(?:\.\d+)?%", bullet):
        return False
    return any(w in low for w in ("resilien", "outperform", "best", "relative", "fund performance"))


def _extract_ranked_funds_from_bundle(bundle: ExecutionBundle) -> list[dict[str, Any]]:
    for k in ("affected_funds_post", "affected_funds_0", "sector_funds_0"):
        val = bundle.tool_results.get(k)
        if val and val.get("ok"):
            data = val.get("data") or {}
            rf = data.get("rankings")
            if isinstance(rf, list) and rf:
                return rf
    for k, val in bundle.tool_results.items():
        if ("affected_funds" in k or "sector_funds" in k) and val.get("ok"):
            data = val.get("data") or {}
            rf = data.get("rankings")
            if isinstance(rf, list) and rf:
                return rf
    return []


def _build_ranked_fund_bullets(
    ranked_funds: list[dict[str, Any]],
    limit: int = 3,
    sentiment: str = "any",
) -> list[str]:
    has_positive = any(
        f.get("return_1m_pct") is not None and float(f["return_1m_pct"]) > 0
        for f in ranked_funds
    )
    bullets: list[str] = []
    for f in ranked_funds:
        name = str(f.get("fund_name") or f.get("isin") or "").strip()
        if not name:
            continue
        weight = f.get("sector_weight_pct")
        sectors = f.get("matched_sectors") or []
        ret_1m = f.get("return_1m_pct")
        ret_1w = f.get("return_1w_pct")

        if sentiment == "positive" and has_positive and ret_1m is not None and float(ret_1m) <= 0:
            continue
        if sentiment == "negative":
            if not ((ret_1m is not None and ret_1m < 0) or (ret_1w is not None and ret_1w < 0)):
                continue

        sec_name = sectors[0] if sectors else "the target sector"
        purity = str(f.get("sector_purity") or "").strip()
        if purity == "defensive_neutral":
            continue
        weight_clause = (
            f"with **{weight}%** allocated to **{sec_name}**"
            if weight is not None
            else f"with meaningful **{sec_name}** exposure"
        )
        nav_clause = ""
        if ret_1m is not None and ret_1w is not None:
            s1m = "+" if ret_1m > 0 else ""
            s1w = "+" if ret_1w > 0 else ""
            nav_clause = (
                f", recording a **{s1m}{ret_1m}%** one-month and **{s1w}{ret_1w}%** one-week NAV change"
            )
        elif ret_1m is not None:
            s1m = "+" if ret_1m > 0 else ""
            nav_clause = f", with a **{s1m}{ret_1m}%** one-month NAV change"
        elif ret_1w is not None:
            s1w = "+" if ret_1w > 0 else ""
            nav_clause = f", with a **{s1w}{ret_1w}%** one-week NAV change"
        bullets.append(f"**{name}** {weight_clause}{nav_clause}.")
        if len(bullets) >= limit:
            break
    return bullets


def _market_pulse_clusters_from_bundle(bundle: ExecutionBundle) -> list[dict[str, Any]]:
    for _key, val in bundle.tool_results.items():
        tool_name = str(_key).rsplit("_", 1)[0]
        if tool_name not in ("common_market_news", "market_pulse", "macro_news_enhanced") or not val.get("ok"):
            continue
        data = val.get("data") or {}
        clusters = data.get("clusters")
        if isinstance(clusters, list):
            return clusters
    return []


def _inject_market_pulse_bullets(
    bullets: list[str],
    clusters: list[dict[str, Any]] | None,
) -> list[str]:
    if not clusters:
        return bullets
    added: list[str] = []
    for cl in clusters[:5]:
        label = str(cl.get("label") or "Macro theme").strip()
        count = int(cl.get("article_count") or 0)
        sectors = cl.get("sectors") if isinstance(cl.get("sectors"), list) else []
        arts = cl.get("articles") if isinstance(cl.get("articles"), list) else []
        rep = arts[0] if arts else {}
        title = str(rep.get("title") or "").strip()
        reason = _clean_prose_fragment(
            str(rep.get("snippet") or title or ""),
            max_chars=200,
        )
        impact = int(rep.get("max_impact") or 0)
        direction = _direction_plain(str(rep.get("direction") or ""))
        pub = str(rep.get("published_at") or "")[:10]
        sector_bit = ""
        if sectors:
            sector_bit = f" Likely impact on **{sectors[0]}** funds and similar sectors."
        line = (
            f"**{label}** — **{count}** matching articles (hot theme). Headline: **{title}** ({pub}). "
            f"{reason} Effect: **{direction}**, impact **{impact}**/5.{sector_bit}"
        )
        if any(_is_near_duplicate_bullet(line, b) for b in bullets + added):
            continue
        added.append(line)
    if not added:
        return bullets
    return _polish_bullet_list(added + bullets)


def _inject_holdings_market_bullets(
    bullets: list[str],
    holdings_market: list[dict[str, Any]] | None,
) -> list[str]:
    if not holdings_market:
        return bullets
    grounded: list[str] = []
    ranked_snaps = sorted(holdings_market, key=_holding_impact_score, reverse=True)
    for snap in ranked_snaps[:6]:
        line = _holding_bullet_from_snap(snap)
        if line:
            grounded.append(line)
    if not grounded:
        return bullets
    kept: list[str] = []
    for b in bullets:
        drop = False
        for snap in holdings_market:
            name = str(snap.get("name") or "")
            if _bullet_mentions_holding(b, name):
                drop = True
                break
            # Drop LLM rewrites of the same headline theme
            reason = _news_reason_from_snap(snap)
            if reason and len(reason) > 20 and _is_near_duplicate_bullet(b, reason):
                drop = True
                break
        if not drop:
            kept.append(b)
    merged = grounded + kept
    return _polish_bullet_list(merged)


_STOCK_NOISE_MARKERS = (
    "52-week low",
    "52 week low",
    "brokerage firms continue",
    "brokerage continue to issue",
    "bse 500 stocks",
    "among 24 bse",
    "strategic picks across nbfcs",
)

_SECTOR_BENEFICIARY_HINTS = (
    "information technology",
    " it ",
    "banking",
    "financial",
    "pharma",
    "healthcare",
    "defence",
    "defense",
    "capital goods",
    "export",
    "psu",
    "public sector",
    "beneficiar",
    "top beneficiary",
    "gainer",
)


def _is_entity_pair_cluster_bullet(bullet: str) -> bool:
    text = (bullet or "").strip()
    if " · " not in text:
        return False
    lead = text.split("—", 1)[0].split("-", 1)[0]
    if "sector" in lead.lower() or "macro" in lead.lower() or "market" in lead.lower():
        return False
    parts = [p.strip() for p in text.split(" · ") if p.strip()]
    if len(parts) < 2:
        return False
    if any("limited" in p.lower() or " ltd" in p.lower() for p in parts[:2]):
        return True
    return len(parts[0]) < 55 and len(parts[1]) < 55


def _is_stock_noise_bullet(bullet: str) -> bool:
    low = (bullet or "").lower()
    return any(m in low for m in _STOCK_NOISE_MARKERS)


def _is_pressure_sector_bullet(bullet: str) -> bool:
    low = (bullet or "").lower()
    return any(
        p in low
        for p in (
            "under pressure",
            "sectors under pressure",
            "headwind",
            "face pressure",
            "slipped to",
            "feeling the squeeze",
            "squeeze margins",
            "fuel costs squeeze",
        )
    )


def _count_sector_beneficiary_bullets(bullets: list[str]) -> int:
    n = 0
    for b in bullets:
        if _is_pressure_sector_bullet(b) or _is_entity_pair_cluster_bullet(b) or _is_stock_noise_bullet(b):
            continue
        low = b.lower()
        if any(h in low for h in _SECTOR_BENEFICIARY_HINTS):
            n += 1
    return n


def _meaning_for_sector(sector: str, items: list[dict[str, Any]]) -> str:
    key = sector.lower()
    for item in items:
        theme = str(item.get("theme") or item.get("headline") or "").lower()
        meaning = str(item.get("meaning") or "").strip()
        if meaning and (key in theme or any(tok in meaning.lower() for tok in key.split()[:2])):
            return _clean_prose_fragment(meaning, max_chars=220)
    return ""


def _inject_positive_sectors_from_digest(
    bullets: list[str],
    digests: list[LayerDigest] | None,
) -> list[str]:
    mp = next((d for d in digests or [] if (d.focus or "") == "market_pulse"), None)
    if not mp:
        return bullets
    out = list(bullets)
    items = mp.items or []
    need = 3
    for rank, sector in enumerate((mp.sectors_positive or [])[:3], start=1):
        if need <= 0:
            break
        meaning = _meaning_for_sector(sector, items)
        if not meaning:
            continue
        line = f"**{sector}** — {meaning}"
        if any(sector.lower() in b.lower() for b in out):
            continue
        out.append(line)
        need -= 1
    return out


def _apply_positive_sector_postprocess(
    bullets: list[str],
    digests: list[LayerDigest] | None,
    *,
    sentiment: str,
    pulse_mode: bool,
) -> list[str]:
    if not pulse_mode or sentiment != "positive":
        return bullets
    cleaned: list[str] = []
    for b in bullets:
        if _is_entity_pair_cluster_bullet(b) or _is_stock_noise_bullet(b):
            continue
        cleaned.append(b)
    pressure = [b for b in cleaned if _is_pressure_sector_bullet(b)]
    non_pressure = [b for b in cleaned if b not in pressure]
    bullets = non_pressure + pressure[:1]
    # Removed forced injection: bullets = _inject_positive_sectors_from_digest(bullets, digests)
    bullets = _drop_unbacked_sector_bullets(bullets, digests)
    return _dedupe_pulse_bullets(bullets)


def _sector_allowed(bullet_lower: str, allowed: list[str]) -> bool:
    for name in allowed:
        if name in bullet_lower:
            return True
        for tok in re.findall(r"[a-z]{5,}", name):
            stem = tok[:-3] if tok.endswith("ing") and len(tok) > 6 else tok
            if len(stem) >= 4 and stem in bullet_lower:
                return True
    return False


def _drop_unbacked_sector_bullets(
    bullets: list[str],
    digests: list[LayerDigest] | None,
) -> list[str]:
    """Only drop bullets that contradict negative sectors by falsely claiming they are top gainers."""
    mp = next((d for d in digests or [] if (d.focus or "") == "market_pulse"), None)
    neg_sectors = [str(s).lower() for s in ((mp.sectors_negative if mp else None) or []) if str(s).strip()]
    if not neg_sectors:
        return bullets
    kept: list[str] = []
    for b in bullets:
        low = b.lower()
        if "fund" in low:
            kept.append(b)
            continue
        is_claimed_gainer = any(w in low for w in ("top gainer", "beneficiary", "outperforming", "performing well"))
        is_in_negative = any(neg in low for neg in neg_sectors)
        if is_claimed_gainer and is_in_negative:
            continue
        kept.append(b)
    return kept


def _inject_digest_insights(
    bullets: list[str],
    digests: list[LayerDigest],
    *,
    holdings_market: list[dict[str, Any]] | None = None,
    market_pulse_clusters: list[dict[str, Any]] | None = None,
    fund_name: str = "",
) -> list[str]:
    added: list[str] = []
    pool = list(bullets)
    max_add = _DIGEST_INJECT_MAX if holdings_market else 4
    if market_pulse_clusters:
        max_add = _DIGEST_INJECT_MAX_PULSE
    skip_layers = {"holding"} if holdings_market else set()
    fn = (fund_name or "").strip()

    for d in digests:
        if d.layer in skip_layers:
            continue
        summary = (d.summary or "").strip()
        if summary and "no news articles were found" in summary.lower():
            continue
        for item in (d.items or [])[:2]:
            meaning = str(item.get("meaning") or "").strip()
            headline = str(item.get("headline") or "").strip()
            line = meaning if len(meaning) >= 30 else headline
            line = _strip_bullet_prefix(_clean_prose_fragment(line, max_chars=200))
            if len(line) < 28:
                continue
            low = line.lower()
            if fn and "fund" not in low and "nav" not in low and "portfolio" not in low:
                line = (
                    f"{line} For someone invested in **{fn}**, this can affect the fund because of "
                    f"which companies and industries it owns."
                )
            if _digest_already_covered(pool + added, LayerDigest(layer=d.layer, summary=line, items=[])):
                continue
            if any(_is_near_duplicate_bullet(line, prev) for prev in pool + added):
                continue
            added.append(line)
            if len(added) >= max_add:
                break
        if len(added) >= max_add:
            break
    if not added:
        return bullets
    return _polish_bullet_list(bullets + added)


def _finalize_compose(
    headline: str,
    narrative: str,
    bullets: list[str],
    bundle: ExecutionBundle,
    digests: list[LayerDigest] | None = None,
    holdings_market: list[dict[str, Any]] | None = None,
    market_pulse_clusters: list[dict[str, Any]] | None = None,
    question: str = "",
    answer_parts: str = "",
    sentiment: str = "any",
) -> tuple[str, str, list[str]]:
    nav = _nav_payload(bundle)
    nav_line = _format_nav_bullet(nav) if nav else None
    if nav_line:
        lower_blob = " ".join(bullets).lower()
        if "nav" not in lower_blob[:200]:
            bullets = [nav_line] + bullets

    if not bullets and narrative:
        bullets = _narrative_to_bullets(narrative)
        if len(bullets) >= 2:
            narrative = ""
    elif narrative and len(narrative) > 200 and len(bullets) <= 1:
        extra = _narrative_to_bullets(narrative)
        if extra:
            bullets = bullets + [b for b in extra if b not in bullets]
            narrative = ""

    bullets = [_strip_bullet_prefix(b) for b in bullets]
    backed = _build_news_backed_pulse_bullets(market_pulse_clusters or [], digests)
    cluster_dump = any(
        "related articles" in b.lower() or "mood:" in b.lower() for b in bullets
    )
    if market_pulse_clusters and backed and (not bullets or cluster_dump):
        bullets = list(backed)
    elif market_pulse_clusters:
        bullets = [b for b in bullets if not _is_generic_market_fluff(b)]
    bullets = _inject_holdings_market_bullets(bullets, holdings_market)
    nav = _nav_payload(bundle)
    fund_name = str((nav or {}).get("fund_name") or "")
    pulse_mode = bool(market_pulse_clusters)
    if digests and not pulse_mode:
        bullets = _inject_digest_insights(
            bullets,
            digests,
            holdings_market=holdings_market,
            market_pulse_clusters=market_pulse_clusters,
            fund_name=fund_name,
        )
    if pulse_mode:
        bullets = [b for b in bullets if not _is_generic_market_fluff(b)]
        bullets = _dedupe_pulse_bullets(bullets) if bullets else []
        bullets = _apply_positive_sector_postprocess(
            bullets, digests, sentiment=sentiment, pulse_mode=True
        )
        ranked_funds = _extract_ranked_funds_from_bundle(bundle)
        if ranked_funds:
            lower_q = (question + " " + answer_parts).lower()
            wants_funds = any(
                w in lower_q
                for w in ("fund", "funds", "mutual fund", "mutual funds", "scheme", "schemes")
            )
            has_fund_bullets = False
            for b in bullets:
                b_lower = b.lower()
                for rf in ranked_funds:
                    fname = str(rf.get("fund_name") or "").lower()
                    if fname and len(fname) > 5 and fname in b_lower:
                        has_fund_bullets = True
                        break
                if has_fund_bullets:
                    break
            if wants_funds and not has_fund_bullets:
                fund_bullets = _build_ranked_fund_bullets(ranked_funds, limit=3, sentiment=sentiment)
                for fb in fund_bullets:
                    if fb not in bullets:
                        bullets.append(fb)
    else:
        if market_pulse_clusters:
            bullets = [b for b in bullets if not _is_generic_market_fluff(b)]
            if backed:
                seen_keys = {_normalize_bullet_key(b) for b in backed}
                extra = [b for b in bullets if _normalize_bullet_key(b) not in seen_keys]
                bullets = _polish_bullet_list(backed + extra[:2])
        bullets = _polish_bullet_list(bullets)
        bullets = _rank_bullets_by_fund_impact(
            bullets,
            nav=nav,
            nav_line=nav_line,
            holdings_market=holdings_market,
            sector_rows=bundle.sector_rows or [],
            question=question,
            answer_parts=answer_parts,
        )[:_MAX_INSIGHT_BULLETS]
    sector_names = _sector_names_from_bullets(bullets)
    headline_low = (headline or "").lower()
    if sector_names and (
        not headline.strip()
        or "related articles" in headline_low
        or "mood:" in headline_low
        or headline.strip().lower().startswith("here is what our data")
    ):
        headline = "Sectors in focus: " + ", ".join(f"**{n}**" for n in sector_names[:3])

    fund_direction, fund_note, fund_rows = _sector_fund_payload(bundle)
    lower_q = (question + " " + answer_parts).lower()
    wants_funds = any(
        w in lower_q for w in ("fund", "funds", "mutual fund", "mutual funds", "scheme", "schemes")
    )
    if wants_funds and fund_direction == "positive" and not fund_rows and fund_note:
        bullets = [b for b in bullets if not _claims_negative_fund_as_best(b)]
        line = f"**Fund Performance** — {fund_note}"
        if line not in bullets:
            bullets.append(line)
    narrative = ""

    if not pulse_mode:
        impact_terms = _collect_impact_bold_terms(bundle, nav, holdings_market)
        headline, narrative, bullets = _apply_impact_emphasis(headline, narrative, bullets, impact_terms)
    return headline, narrative, bullets


def _finalize_closing(
    closing: str,
    *,
    headline: str,
    bullets: list[str],
    bundle: ExecutionBundle,
    answer_parts: str,
    holdings_market: list[dict[str, Any]] | None = None,
    market_pulse_clusters: list[dict[str, Any]] | None = None,
) -> str:
    text = re.sub(r"^[-*•]\s+", "", (closing or "").strip())
    text = re.sub(r"\n+", " ", text)
    if market_pulse_clusters and _is_generic_investing_closing(text):
        text = ""
    if market_pulse_clusters and not text:
        text = _pulse_closing_from_bullets(bullets, market_pulse_clusters)
    if not text:
        text = _closing_from_bullets(headline, bullets, answer_parts)
    if not text:
        return ""
    if not market_pulse_clusters:
        nav = _nav_payload(bundle)
        impact_terms = _collect_impact_bold_terms(bundle, nav, holdings_market)
        text = _emphasize_impact_text(text, impact_terms, max_bold_spans=_MAX_BOLD_PER_CLOSING)
    return _clamp_closing_words(text)


@dataclass
class ComposedAnswer:
    headline: str = ""
    narrative: str = ""
    closing_summary: str = ""
    summary: str = ""
    bullets: list[str] = field(default_factory=list)
    highlight_terms: list[str] = field(default_factory=list)
    impact_items: list[dict[str, Any]] = field(default_factory=list)
    display: str = ""
    advice_declined_note: str = ""
    error: str = ""


def _build_display(
    headline: str,
    narrative: str,
    bullets: list[str],
    note: str,
    closing_summary: str = "",
) -> str:
    parts: list[str] = []
    if note:
        parts.append(note)
    if headline:
        parts.append(headline)
    if narrative:
        parts.append(narrative)
    if bullets:
        parts.append("\n".join(f"• {b}" for b in bullets))
    if closing_summary:
        parts.append(closing_summary)
    return "\n\n".join(parts).strip()


def _deterministic_fallback(
    plan: AskPlan,
    bundle: ExecutionBundle,
    digests: list[LayerDigest],
) -> ComposedAnswer:
    bullets: list[str] = []
    narrative_parts: list[str] = []

    spot = next((v for k, v in bundle.tool_results.items() if k.startswith("metals_spot") and v.get("ok")), None)
    if spot:
        data = spot.get("data") or {}
        g = data.get("gold_7d_change_pct")
        s = data.get("silver_7d_change_pct")
        if g is not None or s is not None:
            narrative_parts.append(
                f"Spot moves: gold {g}% and silver {s}% over the recent window (from our metals feed)."
            )

    for d in digests:
        for item in (d.items or [])[:5]:
            line = str(item.get("meaning") or item.get("headline") or "").strip()
            if line:
                bullets.append(line)
        if d.summary:
            for sent in _split_into_sentences(d.summary)[:2]:
                bullets.append(sent)

    ranked_funds = _extract_ranked_funds_from_bundle(bundle)
    if ranked_funds:
        fund_bullets = _build_ranked_fund_bullets(ranked_funds, limit=3, sentiment=plan.sentiment)
        for fb in fund_bullets:
            if fb not in bullets:
                bullets.append(fb)

    note = ""
    if plan.declined_parts:
        note = "We do not provide buy/sell or target-price advice."

    headline = narrative_parts[0][:160] if narrative_parts else "Here is what our data and news show."
    narrative = " ".join(narrative_parts[1:]) if len(narrative_parts) > 1 else (narrative_parts[0] if narrative_parts else "")
    if not bullets and digests:
        bullets = [d.summary for d in digests if d.summary][:4]

    nav = _nav_payload(bundle)
    if nav and not bullets:
        nb = _format_nav_bullet(nav)
        if nb:
            bullets.append(nb)
    pulse_clusters = _market_pulse_clusters_from_bundle(bundle)
    headline, narrative, bullets = _finalize_compose(
        headline,
        narrative,
        bullets,
        bundle,
        digests,
        holdings_market=None,
        market_pulse_clusters=pulse_clusters if market_pulse_from_plan(plan) else None,
        question="",
        answer_parts=plan.answer_parts,
    )
    closing = _finalize_closing(
        "",
        headline=headline,
        bullets=bullets,
        bundle=bundle,
        answer_parts=plan.answer_parts,
        holdings_market=None,
    )
    return ComposedAnswer(
        headline=headline,
        narrative=narrative,
        closing_summary=closing,
        summary=headline,
        bullets=bullets,
        highlight_terms=[],
        display=_build_display(headline, narrative, bullets, note, closing),
        advice_declined_note=note,
    )


def _articles_for_llm(articles: list[dict[str, Any]], *, limit: int = 6) -> list[dict[str, Any]]:
    """Title plus cleaned body for the final model. Not a headline-only list."""
    ranked = sorted(
        articles,
        key=lambda row: (-int(row.get("max_impact") or 0), str(row.get("published_at") or "")),
    )
    rows: list[dict[str, Any]] = []
    for article in ranked:
        title = str(article.get("title") or "").strip()
        body = article_body_for_llm(article, limit=1000)
        if not title and not body:
            continue
        sectors = article.get("sector_names") or article.get("sectors") or []
        rows.append(
            {
                "title": title,
                "body": body,
                "source": article.get("source"),
                "published_at": str(article.get("published_at") or "")[:10],
                "sectors": sectors if isinstance(sectors, list) else [],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def compose_final_answer(
    question: str,
    plan: AskPlan,
    bundle: ExecutionBundle,
    digests: list[LayerDigest],
    *,
    holdings_market: list[dict[str, Any]] | None = None,
    query_log: QueryLogger | None = None,
) -> ComposedAnswer:
    pooled_articles = collect_bundle_articles(bundle)
    news_article_count = len(pooled_articles)
    metals_spot = next(
        (v.get("data") for k, v in bundle.tool_results.items() if k.startswith("metals_spot") and v.get("ok")),
        None,
    )
    cross = cross_impact_from_plan(plan)
    context = {
        "answer_parts": plan.answer_parts,
        "declined_parts": plan.declined_parts,
        "sentiment": plan.sentiment,
        "news_article_count": news_article_count,
        "cross_impact": cross,
        "metals_spot": metals_spot,
        "fund_nav": bundle.fund_nav_data,
        "holdings": bundle.holdings_rows,
        "sectors": bundle.sector_rows,
        "holdings_market": holdings_market or [],
        "tool_results": {k: v.get("data") for k, v in bundle.tool_results.items() if v.get("ok")},
        "digests": [
            {
                "focus": d.focus or d.layer,
                "layer": d.layer,
                "summary": d.summary,
                "items": d.items,
                "sectors_positive": d.sectors_positive,
                "sectors_negative": d.sectors_negative,
            }
            for d in digests
        ],
        "sectors_positive": list(dict.fromkeys(s for d in digests for s in (d.sectors_positive or [])))[:3],
        "sectors_negative": list(dict.fromkeys(s for d in digests for s in (d.sectors_negative or []))),
    }
    ranked_funds = _extract_ranked_funds_from_bundle(bundle)
    context["ranked_funds"] = [
        {
            "fund_name": r.get("fund_name"),
            "isin": r.get("isin"),
            "sector_weight_pct": r.get("sector_weight_pct"),
            "matched_sectors": r.get("matched_sectors"),
            "return_1w_pct": r.get("return_1w_pct"),
            "return_1m_pct": r.get("return_1m_pct"),
            "latest_nav": r.get("latest_nav"),
            "sector_purity": r.get("sector_purity"),
            "category": r.get("category"),
        }
        for r in ranked_funds[:3]
    ]
    defensive: list[dict[str, Any]] = []
    for k, val in bundle.tool_results.items():
        if not val.get("ok"):
            continue
        if "sector_funds" not in k and "affected_funds" not in k:
            continue
        data = val.get("data") or {}
        alt = data.get("defensive_alternatives")
        if isinstance(alt, list):
            defensive.extend(alt)
    context["defensive_alternatives"] = defensive[:4]
    for k, val in bundle.tool_results.items():
        if not val.get("ok"):
            continue
        if "sector_funds" not in k and "affected_funds" not in k:
            continue
        data = val.get("data") or {}
        if data.get("ranking_note") or data.get("ranking_basis") or "all_drawdown" in data:
            context["fund_ranking_basis"] = data.get("ranking_basis") or context.get("fund_ranking_basis") or ""
            context["ranking_note"] = data.get("ranking_note") or ""
            context["fund_rank_direction"] = data.get("direction") or ""
            context["all_drawdown"] = bool(data.get("all_drawdown"))
            if "affected_funds" in k:
                break
    if not llm_api_key_configured(get_settings()):
        return _deterministic_fallback(plan, bundle, digests)

    pulse_clusters = _market_pulse_clusters_from_bundle(bundle)
    pulse_data = market_pulse_data_from_bundle(bundle)
    pulse_reps = pulse_data.get("representative_articles") or market_pulse_representatives_from_clusters(
        pulse_clusters
    )
    context["market_pulse_clusters"] = [
        {
            "label": c.get("label"),
            "article_count": c.get("article_count"),
            "sectors": c.get("sectors"),
            "score": c.get("score"),
        }
        for c in pulse_clusters[:8]
    ]
    context["market_pulse_representatives"] = pulse_reps
    llm_articles = _articles_for_llm(pooled_articles)

    if market_pulse_from_plan(plan) and news_article_count == 0:
        pulse_data = market_pulse_data_from_bundle(bundle)
        wd = pulse_data.get("window_days")
        label = pulse_data.get("window_label") or (f"last {wd} days" if wd else "the configured window")
        pub_from = (pulse_data.get("published_from") or "")[:10]
        pub_to = (pulse_data.get("published_to") or "")[:10]
        range_bit = f" ({pub_from} to {pub_to})" if pub_from and pub_to else ""
        msg = (
            f"We searched our news archive (Nifty, RBI, flows, earnings, and other macro topics) "
            f"for **{label}**{range_bit} but found **no articles** matching filters "
            f"(including relevance ≥ 2). If your Qdrant index is older, try asking with "
            f"\"last 90 days\" or re-index recent news."
        )
        return ComposedAnswer(
            headline="No news articles available for this market question",
            bullets=[msg],
            closing_summary=msg,
            summary=msg,
            display=_build_display("No news articles available for this market question", "", [msg], "", msg),
        )

    system_prompt = COMPOSER_SYSTEM
    if cross:
        drivers = ", ".join(str(d) for d in (cross.get("drivers") or []))
        system_prompt = (
            f"{COMPOSER_SYSTEM}\n\n{CROSS_IMPACT_COMPOSER_ADDENDUM}\n"
            f"Active drivers for this question: {drivers}."
        )
    elif market_pulse_from_plan(plan):
        system_prompt = f"{COMPOSER_SYSTEM}\n\n{MARKET_PULSE_COMPOSER_ADDENDUM}"
        if plan.sentiment == "positive":
            system_prompt += (
                "\n\nThe question asks what is working or who benefits. "
                "Call a sector a beneficiary only when a digest states a benefit or a positive catalyst. "
                "If the same news shows another sector under pressure, give that sector its own bullet. "
                "Name each ranked_funds entry when that list is non-empty. If it is empty, do not invent gainers."
            )

    user = (
        "Write the final answer from the articles and Context. "
        "Each article has a title and a body. Read the body. Do not answer from the title alone. "
        "The headline answers the question. "
        "Sector bullets use sector names, not company names or article titles. "
        "Fund names and NAV figures come only from ranked_funds.\n\n"
        f"Question:\n{question}\n\n"
        f"Articles:\n{safe_json_dumps(llm_articles)}\n\n"
        f"Context:\n{safe_json_dumps(context, limit=8000)}"
    )
    try:
        res = call_insight_llm(
            system_prompt=system_prompt,
            user_content=user,
            query_log=query_log,
            model_override=composer_model(),
        )
        parsed = parse_json_from_text(res.raw_text) or {}
        headline = str(parsed.get("headline") or "").strip()
        narrative = str(parsed.get("narrative") or parsed.get("summary") or "").strip()
        bullets = [str(b) for b in (parsed.get("bullets") or []) if str(b).strip()][:24]
        headline, narrative, bullets = _finalize_compose(
            headline,
            narrative,
            bullets,
            bundle,
            digests,
            holdings_market=holdings_market,
            market_pulse_clusters=pulse_clusters,
            question=question,
            answer_parts=plan.answer_parts,
            sentiment=plan.sentiment,
        )
        closing_raw = str(
            parsed.get("closing_summary") or parsed.get("closing") or parsed.get("summary_paragraph") or ""
        ).strip()
        if closing_raw and closing_raw == headline:
            closing_raw = ""
        closing = _finalize_closing(
            closing_raw,
            headline=headline,
            bullets=bullets,
            bundle=bundle,
            answer_parts=plan.answer_parts,
            holdings_market=holdings_market,
            market_pulse_clusters=pulse_clusters if market_pulse_from_plan(plan) else None,
        )

        note = str(parsed.get("advice_declined_note") or "").strip()
        if plan.declined_parts and not note:
            note = "We do not provide buy/sell, target-price, or prediction advice."

        return ComposedAnswer(
            headline=headline,
            narrative=narrative,
            closing_summary=closing,
            summary=headline or narrative[:200],
            bullets=bullets,
            highlight_terms=[],
            impact_items=[],
            display=_build_display(headline, narrative, bullets, note, closing),
            advice_declined_note=note,
        )
    except Exception as exc:
        logger.warning("composer failed: %s", exc)
        if query_log is not None:
            query_log.write(f"COMPOSER_FAIL {exc}")
        fb = _deterministic_fallback(plan, bundle, digests)
        fb.error = str(exc)
        return fb
