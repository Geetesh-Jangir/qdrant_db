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
from news_rag.news_digest import LayerDigest
from news_rag.llm_text import parse_json_from_text

if TYPE_CHECKING:
    from news_rag.ask_plan import AskPlan
    from news_rag.ask_execution import ExecutionBundle
    from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

COMPOSER_SYSTEM = """You write answers for a mutual-fund research app.
Format: a crisp headline, story-like bullet points, then a short closing paragraph.

Return JSON only:
{
  "headline": "One line hook; wrap the **fund or topic name** in **asterisks**",
  "narrative": "Always leave \"\"",
  "bullets": [
    "Max 8 bullets total. Each bullet ends with how it affects the **fund** (NAV, largest weights, or sector mix) — not stock trivia alone.",
    "One theme per bullet; never repeat the same news story (e.g. CEO/RBI once only). No ellipses (... or …). Max ~40 words."
  ],
  "closing_summary": "100–150 words. Flowing prose (no bullets). Address every part of the user's question; weave the bullets into one easy-to-read story with a clear beginning (context), middle (what changed), and end (what it means for the reader). Use plain language.",
  "advice_declined_note": ""
}

Story & clarity:
- Bullets should read in order like a mini-narrative, not a random fact sheet.
- Never start a bullet with category labels (wrong: \"Top Holdings:\", \"News Drivers:\", \"Sector —\", \"Macro:\").
- Fund facts: separate bullets for NAV/returns, top holdings (with %), top sectors (with %) — natural sentences.
- News: when digests exist, bullets on what happened and **why it matters** for this fund (name holding or sector in the sentence).
- Bullet order in JSON should be: NAV/returns first, then highest-impact holdings, then sectors, then macro — each tied to **fund** impact.
- Do NOT write per-holding bullets in JSON when holdings_market is in context — the system adds those; you add only fund NAV, sector mix, and 2–3 macro bullets with **fund impact**.
- If you mention a holding, tie to **% weight** and **effect on the fund**; never repeat a headline already covered.
- No truncated snippets, no "Listen…", no ellipses.
- closing_summary must not repeat the headline verbatim; it synthesizes and answers the full question.
- Do not paste long digest paragraphs into bullets. News only from digests. No invented causes. No buy/sell/target price advice. No markdown headings (#).
"""


_MAX_BOLD_SPANS = 12
_MAX_INSIGHT_BULLETS = 10
_DIGEST_INJECT_MAX = 2
_CLOSING_MIN_WORDS = 90
_CLOSING_MAX_WORDS = 165


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


def _apply_bold_budget(headline: str, narrative: str, bullets: list[str]) -> tuple[str, str, list[str]]:
    budget = [_MAX_BOLD_SPANS]
    bolded_bullets = [_limit_bold_spans(b, budget) for b in bullets]
    return (
        _limit_bold_spans(headline, budget),
        _limit_bold_spans(narrative, budget),
        bolded_bullets,
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
    parts = [f"**{name}** — **NAV** ₹{nav_val}"]
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


def _polish_bullet_list(bullets: list[str]) -> list[str]:
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
            nav_note = f" That move contributed about **{float(drag):+.2f}%** to the fund's NAV over the same window."
        except (TypeError, ValueError):
            nav_note = ""
    if "no company-specific headline" in reason.lower():
        return (
            f"**{name}** ({weight:.2f}% weight) moved **{ret:+.2f}%** over the past {window}; "
            f"we found no dedicated news story for this name in our store, but the position still "
            f"shapes fund returns through its weight.{nav_note}"
        )
    verb = "rose" if ret >= 0 else "fell"
    return (
        f"**{name}** ({weight:.2f}% weight) {verb} **{ret:+.2f}%** over the past {window}; "
        f"news driver: {reason} "
        f"This matters for the fund because the name is a top holding.{nav_note}"
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
    fund_name: str = "",
) -> list[str]:
    added: list[str] = []
    pool = list(bullets)
    max_add = _DIGEST_INJECT_MAX if holdings_market else 4
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
                line = f"{line} For **{fn}**, this flows through sector weights and top holdings."
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

    bold_terms = _collect_bold_terms(bundle, nav)
    headline = _autobold_phrases(headline, bold_terms)
    narrative = _autobold_phrases(narrative, bold_terms)
    bullets = [_autobold_phrases(b, bold_terms) for b in bullets]
    bullets = [_strip_bullet_prefix(b) for b in bullets]
    bullets = _inject_holdings_market_bullets(bullets, holdings_market)
    nav = _nav_payload(bundle)
    fund_name = str((nav or {}).get("fund_name") or "")
    if digests:
        bullets = _inject_digest_insights(
            bullets, digests, holdings_market=holdings_market, fund_name=fund_name
        )
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

    headline, narrative, bullets = _apply_bold_budget(headline, narrative, bullets)
    return headline, narrative, bullets


def _finalize_closing(
    closing: str,
    *,
    headline: str,
    bullets: list[str],
    bundle: ExecutionBundle,
    answer_parts: str,
) -> str:
    text = re.sub(r"^[-*•]\s+", "", (closing or "").strip())
    text = re.sub(r"\n+", " ", text)
    if not text:
        text = _closing_from_bullets(headline, bullets, answer_parts)
    if not text:
        return ""
    nav = _nav_payload(bundle)
    bold_terms = _collect_bold_terms(bundle, nav)
    text = _autobold_phrases(text, bold_terms)
    text = _clamp_closing_words(text)
    return text


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
    headline, narrative, bullets = _finalize_compose(
        headline,
        narrative,
        bullets,
        bundle,
        digests,
        holdings_market=None,
        question="",
        answer_parts=plan.answer_parts,
    )
    closing = _finalize_closing(
        "",
        headline=headline,
        bullets=bullets,
        bundle=bundle,
        answer_parts=plan.answer_parts,
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
    news_article_count = sum(len(v) for v in bundle.articles_by_focus.values()) + sum(
        len(v) for v in bundle.articles_by_layer.values()
    )
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

    system_prompt = COMPOSER_SYSTEM
    if cross:
        drivers = ", ".join(str(d) for d in (cross.get("drivers") or []))
        system_prompt = (
            f"{COMPOSER_SYSTEM}\n\n{CROSS_IMPACT_COMPOSER_ADDENDUM}\n"
            f"Active drivers for this question: {drivers}."
        )

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
