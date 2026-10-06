"""Final LLM answer from tool outputs and news digests."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.json_util import safe_json_dumps
from news_rag.llm_client import call_insight_llm, llm_api_key_configured
from news_rag.cross_impact import CROSS_IMPACT_COMPOSER_ADDENDUM, cross_impact_from_plan
from news_rag.article_pool import collect_bundle_articles
from news_rag.market_pulse import (
    market_pulse_data_from_bundle,
    market_pulse_from_plan,
    market_pulse_representatives_from_clusters,
)
from news_rag.news_digest import LayerDigest
from news_rag.llm_text import parse_json_from_text

PLAIN_LANGUAGE_RULES = """PLAIN LANGUAGE (required — write for someone new to investing):
- Use short sentences. Prefer everyday words over jargon.
- When you use a term, explain it once in simple words in the same sentence, e.g.:
  "Nifty (India's main stock index)", "RBI (India's central bank)", "FII (foreign investors)",
  "liquidity (cash available in the banking system)", "repo rate (the rate at which banks borrow from RBI)".
- Say what happened in plain English, then what it means for people's money and mutual funds.
- You may use more bullets and a longer closing_summary if it helps clarity; do not sacrifice understanding for brevity.
- Avoid: salience, allocation, headwinds, tailwinds, repricing, risk-off, beta, unless you immediately explain them."""

MARKET_PULSE_COMPOSER_ADDENDUM = """MARKET PULSE mode (broad "what's happening in the market" question):
- Primary input: market_pulse_representatives (up to 8 themes; each has articles_in_theme + one representative article) and digests[focus=market_pulse] if present.
- Synthesize insights in plain English. Do NOT paste long article titles or URLs. Do NOT list themes as a comma-separated headline.
- Write at least 6 bullets when market_pulse_representatives has 6+ themes (otherwise one per theme provided). Order by articles_in_theme (highest first).
- Each bullet: **theme** → what happened (facts from snippet) → why it matters for Indian mutual fund investors / which sectors (banks, IT, defence, etc.).
- Mention article coverage when useful ("11 similar stories on bond yields") but focus on impact, not metadata.
- closing_summary: tie themes together in 120–200 words; no generic "stay calm" investing lectures; only facts from representatives/digest.
- If news_article_count is 0, say honestly that our news store had no articles for this window."""

if TYPE_CHECKING:
    from news_rag.ask_plan import AskPlan
    from news_rag.ask_execution import ExecutionBundle
    from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

COMPOSER_SYSTEM = """You write answers for a mutual-fund and markets app. Your reader may NOT know finance jargon.

Format: a clear headline, easy-to-read bullet points, then a friendly closing paragraph.

Return JSON only:
{
  "headline": "One simple line; wrap the **fund or topic** in **asterisks**",
  "narrative": "Always leave \"\"",
  "bullets": [
    "Use as many bullets as needed (often 6–10) for clarity. One idea per bullet.",
    "Bold **fund names**, **company names**, **NAV** (say 'price per unit' if helpful), **₹** amounts, and **%** changes.",
    "End each bullet with 'So for your fund…' or 'This matters because…' in plain language."
  ],
  "closing_summary": "150–280 words. Tell the story like you're explaining to a friend: what changed, why, and what to keep in mind. No bullet points in closing.",
  "advice_declined_note": ""
}

Story & clarity:
- Bullets should read in order: big picture → details → what it means for money in mutual funds.
- Never start with labels like \"Sector:\" or \"Macro:\".
- Explain % weight as \"about X% of the fund is in this company\" when useful.
- News: what happened + why it matters for someone holding that fund or sector.
- Order: fund price/returns first (if any), then important holdings, then sectors, then wider market news.
- Do NOT write per-holding bullets when holdings_market is in context — the system adds those.
- No ellipses (... or …). News only from digests/context. No buy/sell advice. No markdown headings (#).

""" + PLAIN_LANGUAGE_RULES


_MAX_BOLD_PER_HEADLINE = 10
_MAX_BOLD_PER_BULLET = 10
_MAX_BOLD_PER_CLOSING = 14
_MAX_INSIGHT_BULLETS = 12
_DIGEST_INJECT_MAX = 2
_DIGEST_INJECT_MAX_PULSE = 6
_GENERIC_CLOSING_MARKERS = (
    "stay calm",
    "long-term perspective",
    "hasty decisions",
    "$100 a barrel",
    "crude oil prices climb",
    "weather these ups and downs",
    "normal part of investing",
    "everyday mutual fund investors",
    "short-term market turbulence",
    "best approach is to stay",
)


def _is_generic_investing_closing(text: str) -> bool:
    low = (text or "").lower()
    return sum(1 for m in _GENERIC_CLOSING_MARKERS if m in low) >= 2


def _pulse_headline(clusters: list[dict[str, Any]]) -> str:
    labels = [str(c.get("label") or "").strip() for c in clusters[:4] if c.get("label")]
    if not labels:
        return "What is moving the Indian market right now"
    if len(labels) == 1:
        return f"**{labels[0]}** is in focus across today's market news"
    joined = ", ".join(f"**{x}**" for x in labels[:3])
    return f"Top themes in our news feed: {joined}"


def _pulse_closing_from_bullets(bullets: list[str], clusters: list[dict[str, Any]]) -> str:
    """Plain closing stitched only from retrieved themes (no generic investing lecture)."""
    labels = [str(c.get("label") or "") for c in clusters[:4] if c.get("label")]
    if labels:
        intro = (
            f"Across the last few weeks of news we indexed, the busiest themes are "
            f"{', '.join(labels[:4])}. "
        )
    else:
        intro = "Here is how the main news themes fit together for mutual fund investors. "
    snippets: list[str] = []
    for b in bullets[:4]:
        plain = re.sub(r"\*\*([^*]+)\*\*", r"\1", b)
        for sent in _split_into_sentences(plain):
            if len(sent) >= 40 and "related articles" not in sent.lower():
                snippets.append(sent)
            if len(snippets) >= 3:
                break
        if len(snippets) >= 3:
            break
    if not snippets and bullets:
        plain = re.sub(r"\*\*([^*]+)\*\*", r"\1", bullets[0])
        snippets = _split_into_sentences(plain)[:2]
    body = " ".join(snippets[:3])
    closing = (intro + body).strip()
    return _clamp_closing_words(closing, min_words=80, max_words=220)


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
_CLOSING_MIN_WORDS = 120
_CLOSING_MAX_WORDS = 300


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
    seeds: list[str] = []
    if (answer_parts or "").strip():
        seeds.append(answer_parts.strip())
    if headline:
        seeds.append(headline.replace("**", ""))
    for b in bullets[:6]:
        plain = re.sub(r"\*\*([^*]+)\*\*", r"\1", b)
        seeds.append(plain)
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


def _strip_bullet_prefix(text: str) -> str:
    t = (text or "").strip()
    for _ in range(4):
        m = _BULLET_PREFIX_RE.match(t) or _LAYER_PREFIX_RE.match(t)
        if not m:
            break
        t = t[m.end() :].strip()
    t = re.sub(r"^NAV:\s*", "", t, flags=re.I)
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


def _dedupe_pulse_bullets(bullets: list[str]) -> list[str]:
    """Keep one bullet per cluster label; do not truncate to first sentence."""
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
    return out[:6]


def _dedupe_bullets(bullets: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in bullets:
        b = _strip_bullet_prefix(_clean_prose_fragment(raw, max_chars=500) or raw)
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


def _build_news_backed_pulse_bullets(
    clusters: list[dict[str, Any]],
    digests: list[LayerDigest] | None,
) -> list[str]:
    bullets: list[str] = []
    for cl in clusters[:6]:
        label = str(cl.get("label") or "Market theme").strip()
        count = int(cl.get("article_count") or 0)
        sectors = cl.get("sectors") if isinstance(cl.get("sectors"), list) else []
        arts = cl.get("articles") if isinstance(cl.get("articles"), list) else []
        if not arts:
            continue
        rep = arts[0]
        title = str(rep.get("title") or "").strip()
        snippet = _clean_prose_fragment(str(rep.get("snippet") or ""), max_chars=180)
        impact = int(rep.get("max_impact") or 0)
        direction = _direction_plain(str(rep.get("direction") or ""))
        pub = str(rep.get("published_at") or "")[:10]
        core = snippet or title
        who = f" Watch **{sectors[0]}**-heavy funds." if sectors else ""
        bullets.append(
            f"**{label}** ({count} related articles) — **{title}** ({pub}). "
            f"{core} "
            f"Impact {impact}/5; mood: {direction}.{who}"
        )
    if bullets:
        return bullets
    for d in digests or []:
        if d.summary and "no news" not in d.summary.lower():
            bullets.append(_strip_bullet_prefix(_clean_prose_fragment(d.summary, max_chars=220)))
        for item in (d.items or [])[:1]:
            meaning = str(item.get("meaning") or item.get("headline") or "").strip()
            if len(meaning) >= 30:
                bullets.append(_strip_bullet_prefix(meaning))
        if len(bullets) >= 5:
            break
    return bullets[:6]


def _market_pulse_clusters_from_bundle(bundle: ExecutionBundle) -> list[dict[str, Any]]:
    for _key, val in bundle.tool_results.items():
        if not str(_key).startswith("market_pulse") or not val.get("ok"):
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
    if market_pulse_clusters and backed and (
        not bullets or all(_is_generic_market_fluff(b) for b in bullets)
    ):
        bullets = list(backed)
    elif market_pulse_clusters:
        bullets = [b for b in bullets if not _is_generic_market_fluff(b)]
        if len(bullets) < 4:
            bullets = _inject_market_pulse_bullets(bullets, market_pulse_clusters)
    bullets = _inject_holdings_market_bullets(bullets, holdings_market)
    nav = _nav_payload(bundle)
    fund_name = str((nav or {}).get("fund_name") or "")
    pulse_mode = bool(market_pulse_clusters)
    if digests and not (pulse_mode and backed):
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
        target = min(8, len(market_pulse_clusters or []) or 6)
        if digests and len(bullets) < target:
            mp_digest = next((d for d in digests if (d.focus or "") == "market_pulse"), None)
            if mp_digest:
                for item in mp_digest.items or []:
                    theme = str(item.get("theme") or item.get("headline") or "").strip()
                    meaning = str(item.get("meaning") or "").strip()
                    if len(meaning) < 40:
                        continue
                    line = f"**{theme}** — {meaning}" if theme else meaning
                    if not any(_is_near_duplicate_bullet(line, b) for b in bullets):
                        bullets.append(line)
                    if len(bullets) >= target:
                        break
        if len(bullets) < 4 and backed:
            bullets = _polish_bullet_list(backed, market_pulse=True)
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

    sf = next((v for k, v in bundle.tool_results.items() if "sector_funds" in k and v.get("ok")), None)
    if sf:
        ranks = (sf.get("data") or {}).get("rankings") or []
        names = [str(r.get("fund_name") or "") for r in ranks[:5] if r.get("fund_name")]
        if names:
            narrative_parts.append(
                "Funds with meaningful precious-metals exposure include "
                + ", ".join(names[:3])
                + (f" and others ({len(names)} ranked)." if len(names) > 3 else ".")
            )

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
            }
            for d in digests
        ],
    }
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
    context["source_headlines"] = [
        {
            "title": a.get("title"),
            "url": a.get("url"),
            "direction": a.get("direction"),
            "max_impact": a.get("max_impact"),
            "published_at": a.get("published_at"),
            "snippet": (str(a.get("snippet") or "")[:220]),
        }
        for a in sorted(
            pooled_articles,
            key=lambda x: (-int(x.get("max_impact") or 0), str(x.get("published_at") or "")),
        )[:20]
    ]

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

    user = f"Question:\n{question}\n\nContext:\n{safe_json_dumps(context, limit=14000)}"
    try:
        res = call_insight_llm(
            system_prompt=system_prompt,
            user_content=user,
            query_log=query_log,
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
