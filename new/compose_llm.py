"""Fund-week narrative composed by LLM from full fund context."""

from __future__ import annotations

import json
import re
from typing import Any

from ai_insight.common.prose_guard import scrub_refusal_prose, split_sentences
from news_rag.llm_client import LlmCallResult, call_json_llm

from new.equity_week_llm import equity_week_llm_kwargs
from new.stock_explain import _short_name, clamp_why_paragraph, polish_why
from new.week_window import strip_portfolio_pct_prose

_COMPOSE_SYSTEM = """You compose the weekly mutual fund insight for a portfolio owner.

FACTS JSON is complete. Never ask for more data.

Return JSON with:
- headline (under 10 words)
- summary_opener, summary_losses, summary_extra_drag (optional empty), summary_overall
- gainers[], losers[] for the detail section below the summary

TOP SUMMARY — one connected story (not ten separate stock blurbs). Four parts:

When sector_clusters in FACTS has has_news true, you MAY tie 2–3 named stocks to one verified sector driver from article_titles/snippets (e.g. banking strength). Do NOT invent a sector theme if has_news is false or sector_clusters is empty.

summary_opener — one sentence (MUST include fund week NAV change from nav_change_1w_pct once):
"[scheme_name], which makes up [portfolio_pct_of_book]% of your portfolio, [gained slightly / lost a little / was about flat] this week with NAV [up/down] [nav_change_1w_pct]%, supported by [sector-backed driver when evidence exists, else 2–3 gainer names + brief reasons]."

summary_losses — one sentence on offsetting weakness (sector or named losers):
"Losses in [loser names or weak sector] weighed on returns, with [one combined news-backed reason]."

summary_extra_drag — optional one sentence (empty string if nothing extra):
"[Name] added to the decline as [specific reason from drafts]."

summary_overall — one sentence starting with "Overall,":
"Overall, gains in [drivers] were [largely offset by / outweighed by] weakness in [offsets], leaving the fund [marginally positive / slightly negative / about flat]."

Use attribution.summary_line if present — do not claim you explained 100% of NAV when residual is large.

STYLE (do not copy names blindly — use FACTS):
"HSBC Value Fund gained 0.35% this week, supported by strength in banking stocks — several bank holdings benefited from firmer credit growth, while HDFC Bank rose on its own earnings update."
"Losses in IT names weighed on returns, as softer client-spending news hit the sector."
"Overall, gains in banking were partly offset by weakness in IT, leaving the fund marginally positive."

DETAIL BODY — gainers/losers with has_news only; change_1w_pct in JSON; why 2–4 sentences, no heavy numbers in why text.

READABILITY: Write for a first-time investor. Short sentences. If you use a finance term (credit cost, net interest margin, return on assets, valuation, FII/foreign flows, organic growth), add a few plain words in the same sentence saying what it means (e.g. "lower credit cost — fewer losses on bad loans").

No buy/sell advice. No "the article says"."""

_SUMMARY_ONLY_SYSTEM = """Write only the four top summary sentences for the fund owner.

Return JSON: {"summary_opener", "summary_losses", "summary_extra_drag", "summary_overall"}

Follow the four-part format and STYLE in the user message. Use scheme_name and portfolio_pct from FACTS.
Include nav_change_1w_pct in summary_opener. Use everyday words; briefly explain any jargon.
Name real stocks from gainer_ideas and loser_ideas. Use sector_clusters only when has_news is true. Never ask for more data."""

_REFUSAL = re.compile(
    r"(do not have the fund|not provided|please send|cannot complete|share the fund details)",
    re.I,
)
_FORBIDDEN = re.compile(
    r"\b(no news|news not|home\s*/\s*markets|listen to this article)\b",
    re.I,
)

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary_opener": {"type": "string"},
        "summary_losses": {"type": "string"},
        "summary_extra_drag": {"type": "string"},
        "summary_overall": {"type": "string"},
        "gainers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "change_1w_pct": {"type": ["number", "null"]},
                    "why": {"type": "string"},
                },
                "required": ["name", "why"],
            },
        },
        "losers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "change_1w_pct": {"type": ["number", "null"]},
                    "why": {"type": "string"},
                },
                "required": ["name", "why"],
            },
        },
    },
    "required": [
        "headline",
        "summary_opener",
        "summary_losses",
        "summary_overall",
        "gainers",
        "losers",
    ],
}

_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary_opener": {"type": "string"},
        "summary_losses": {"type": "string"},
        "summary_extra_drag": {"type": "string"},
        "summary_overall": {"type": "string"},
    },
    "required": ["summary_opener", "summary_losses", "summary_overall"],
}


def _fund_display_name(scheme: str) -> str:
    s = (scheme or "").strip()
    for cut in (" - Regular", " - Direct", " - Growth", " - IDCW"):
        if cut in s:
            return s.split(cut)[0].strip()
    return s.split(" - ")[0].strip() if " - " in s else s


def _usable_block(block: dict[str, Any]) -> bool:
    if block.get("why_skip"):
        return False
    why = str(block.get("why") or "").strip()
    if not why or _FORBIDDEN.search(why):
        return False
    return bool(block.get("usable_news") or block.get("articles"))


def _stock_entries(stock_news: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gainers: list[dict[str, Any]] = []
    losers: list[dict[str, Any]] = []
    for block in stock_news:
        if not _usable_block(block):
            continue
        name = _short_name(str(block.get("instrument_name") or ""))
        ch = block.get("change_1w_pct")
        try:
            ch_f = round(float(ch), 2) if ch is not None else None
        except (TypeError, ValueError):
            ch_f = None
        entry = {"name": name, "change_1w_pct": ch_f, "why": str(block.get("why") or "").strip()}
        if block.get("move") == "down":
            losers.append(entry)
        else:
            gainers.append(entry)
    return gainers, losers


def _theme_hint(why: str, *, max_words: int = 18) -> str:
    bits = split_sentences(scrub_refusal_prose(why))
    first = bits[0] if bits else why
    return clamp_why_paragraph(first, max_words=max_words)


def _sector_themes_for_facts(sector_news: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for block in sector_news or []:
        if not isinstance(block, dict):
            continue
        articles = block.get("articles") or []
        has_news = bool(block.get("usable_news") and articles)
        titles: list[str] = []
        snippets: list[str] = []
        for art in articles[:3]:
            if not isinstance(art, dict):
                continue
            t = str(art.get("title") or "").strip()
            if t:
                titles.append(t[:220])
            sn = str(art.get("snippet") or "").strip()
            if sn:
                snippets.append(sn[:280])
        stocks = block.get("holding_names") or []
        if not stocks and block.get("holdings"):
            stocks = [
                _short_name(str(h.get("instrument_name") or ""))
                for h in block.get("holdings") or []
                if isinstance(h, dict)
            ]
        out.append(
            {
                "sector": block.get("sector_key"),
                "side": block.get("side"),
                "stocks": stocks,
                "trigger": block.get("trigger"),
                "has_news": has_news,
                "article_titles": titles,
                "article_snippets": snippets,
            }
        )
    return out


def _facts_payload(
    facts: dict[str, Any],
    gainers: list[dict[str, Any]],
    losers: list[dict[str, Any]],
    *,
    omit_portfolio_pct: bool = False,
) -> dict[str, Any]:
    stock_news = facts.get("stock_news") or []
    drafts = []
    for block in stock_news:
        why = str(block.get("why") or "").strip() if _usable_block(block) else ""
        drafts.append(
            {
                "instrument_name": block.get("instrument_name"),
                "move": block.get("move"),
                "change_1w_pct": block.get("change_1w_pct"),
                "has_news": _usable_block(block),
                "draft_why": why or None,
                "theme_hint": _theme_hint(why) if why else None,
            }
        )
    scheme = str(facts.get("scheme_name") or "")
    nav = facts.get("nav_1w_pct")
    try:
        nav_f = float(nav) if nav is not None else None
    except (TypeError, ValueError):
        nav_f = None
    out: dict[str, Any] = {
        "scheme_name": _fund_display_name(scheme),
        "nav_change_1w_pct": nav_f,
        "gainer_ideas": [{"name": g["name"], "theme": _theme_hint(g["why"])} for g in gainers],
        "loser_ideas": [{"name": l["name"], "theme": _theme_hint(l["why"])} for l in losers],
        "draft_insights": drafts,
        "sector_clusters": _sector_themes_for_facts(facts.get("sector_news") or []),
        "attribution": facts.get("attribution") or {},
        "nav_daily": facts.get("nav_daily") or [],
        "prepared_gainers": gainers,
        "prepared_losers": losers,
    }
    if not omit_portfolio_pct:
        out["portfolio_pct_of_book"] = facts.get("portfolio_pct")
    return out


def _compose_user_message(
    facts: dict[str, Any],
    gainers: list[dict[str, Any]],
    losers: list[dict[str, Any]],
    *,
    omit_portfolio_pct: bool = False,
) -> str:
    payload = _facts_payload(facts, gainers, losers, omit_portfolio_pct=omit_portfolio_pct)
    extra = (
        "\n\nDo not mention portfolio weight or percent of the investor book."
        if omit_portfolio_pct
        else ""
    )
    return (
        "FACTS:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Fill all four summary_* fields as one fund-level story. Use sector_clusters when has_news is true; "
        "otherwise use gainer_ideas / loser_ideas stock names only."
        f"{extra}"
    )


def _summary_user_message(
    facts: dict[str, Any],
    gainers: list[dict[str, Any]],
    losers: list[dict[str, Any]],
    *,
    omit_portfolio_pct: bool = False,
) -> str:
    payload = _facts_payload(facts, gainers, losers, omit_portfolio_pct=omit_portfolio_pct)
    extra = (
        " Do not mention portfolio weight or percent of the book."
        if omit_portfolio_pct
        else ""
    )
    return "FACTS:\n" + json.dumps(payload, ensure_ascii=False, indent=2) + extra


def _clean_summary_sentence(text: str, *, max_words: int = 65) -> str:
    t = scrub_refusal_prose(str(text or "").strip())
    if not t or _REFUSAL.search(t):
        return ""
    return clamp_why_paragraph(t, max_words=max_words)


def _join_summary(parsed: dict[str, Any]) -> str:
    parts = [
        _clean_summary_sentence(parsed.get("summary_opener")),
        _clean_summary_sentence(parsed.get("summary_losses")),
        _clean_summary_sentence(str(parsed.get("summary_extra_drag") or "")),
        _clean_summary_sentence(parsed.get("summary_overall")),
    ]
    return "\n\n".join(p for p in parts if p)


def _summary_ok(text: str) -> bool:
    if not text or len(text.split()) < 25:
        return False
    if _REFUSAL.search(text):
        return False
    low = text.lower()
    if low.count("overall,") < 1 and "overall," not in low:
        return False
    if "portfolio" not in low and "%" not in text:
        return False
    return True


def _parse_mover_rows(
    rows: Any,
    *,
    fallback: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_name = {g["name"]: g for g in fallback}
    if not isinstance(rows, list):
        return list(fallback)
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = _short_name(str(row.get("name") or ""))
        why = polish_why(scrub_refusal_prose(str(row.get("why") or "").strip()))
        if not name or not why or _REFUSAL.search(why) or _FORBIDDEN.search(why):
            continue
        ch = row.get("change_1w_pct")
        if ch is None and name in by_name:
            ch = by_name[name].get("change_1w_pct")
        try:
            ch_f = round(float(ch), 2) if ch is not None else None
        except (TypeError, ValueError):
            ch_f = by_name.get(name, {}).get("change_1w_pct")
        out.append({"name": name, "change_1w_pct": ch_f, "why": why})
    return out or list(fallback)


def _dry_mover_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for h in rows or []:
        if not isinstance(h, dict):
            continue
        name = _short_name(str(h.get("instrument_name") or h.get("name") or ""))
        if not name:
            continue
        ch = h.get("change_1w_pct")
        try:
            ch_f = round(float(ch), 2) if ch is not None else None
        except (TypeError, ValueError):
            ch_f = None
        why = str(h.get("why") or "").strip()
        if not why:
            why = "Weekly price move from market data (dry run — no news or LLM)."
        out.append({"name": name, "change_1w_pct": ch_f, "why": why})
    return out


def _insight_text(fund_summary: str, gainers: list[dict[str, Any]], losers: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    if fund_summary:
        parts.append(fund_summary.strip())
    if gainers:
        parts.append("What helped:")
        for g in gainers:
            ch = g.get("change_1w_pct")
            ch_s = f" ({ch:+.2f}%)" if ch is not None else ""
            parts.append(f"{g['name']}{ch_s}. {g['why']}")
    if losers:
        parts.append("What held back:")
        for l in losers:
            ch = l.get("change_1w_pct")
            ch_s = f" ({ch:+.2f}%)" if ch is not None else ""
            parts.append(f"{l['name']}{ch_s}. {l['why']}")
    return "\n\n".join(parts)


def _package(
    scheme: str,
    fund_summary: str,
    gainers: list[dict[str, Any]],
    losers: list[dict[str, Any]],
    facts: dict[str, Any],
    *,
    headline: str,
    source: str,
) -> dict[str, Any]:
    stock_news = facts.get("stock_news") or []
    sources: list[str] = []
    for block in stock_news:
        if not _usable_block(block):
            continue
        for art in block.get("articles") or []:
            u = art.get("url")
            if u:
                sources.append(str(u))
    for block in facts.get("sector_news") or []:
        if not block.get("usable_news"):
            continue
        for art in block.get("articles") or []:
            u = art.get("url")
            if u and str(u) not in sources:
                sources.append(str(u))
    opening = fund_summary.split("\n\n")[0].strip() if fund_summary else ""
    insight = _insight_text(fund_summary, gainers, losers)
    cushioned = [c.get("scheme_name") for c in facts.get("cushioned_by") or [] if c.get("scheme_name")]
    return {
        "headline": headline or f"{scheme} — week in short",
        "fund_summary": fund_summary,
        "opening": opening,
        "gainers": gainers,
        "losers": losers,
        "closing": "",
        "insight": insight,
        "summary": fund_summary or insight,
        "cushioned_funds": cushioned,
        "sources": sources[:24],
        "narrative_source": source,
    }


def _llm_call(system: str, user: str, schema: dict[str, Any], stage: str) -> dict[str, Any] | None:
    llm = equity_week_llm_kwargs(temperature=0.32)
    try:
        result = call_json_llm(
            system_prompt=system,
            user_content=user,
            max_tokens=1400,
            stage=stage,
            response_schema=schema,
            **llm,
        )
    except Exception:
        return None
    raw = result.parsed if isinstance(result, LlmCallResult) else result
    return raw if isinstance(raw, dict) else None


def _ensure_fund_summary(
    facts: dict[str, Any],
    gainers: list[dict[str, Any]],
    losers: list[dict[str, Any]],
    parsed: dict[str, Any] | None,
    *,
    omit_portfolio_pct: bool = False,
) -> str:
    text = _join_summary(parsed or {})
    if omit_portfolio_pct:
        text = strip_portfolio_pct_prose(text)
    if _summary_ok(text):
        return text
    summary_only = _llm_call(
        _SUMMARY_ONLY_SYSTEM,
        _summary_user_message(facts, gainers, losers, omit_portfolio_pct=omit_portfolio_pct),
        _SUMMARY_SCHEMA,
        "equity_fund_week_summary",
    )
    if summary_only:
        text = _join_summary(summary_only)
        if _summary_ok(text):
            return text
    return text


def _finalize_summary(text: str, *, omit_portfolio_pct: bool) -> str:
    if not omit_portfolio_pct:
        return text
    return strip_portfolio_pct_prose(text)


def compose_fund_narrative(
    facts: dict[str, Any],
    *,
    dry_run: bool = False,
    omit_portfolio_pct: bool = False,
) -> dict[str, Any]:
    scheme = str(facts.get("scheme_name") or "Fund")
    gainers, losers = _stock_entries(facts.get("stock_news") or [])

    if dry_run:
        label = _fund_display_name(scheme)
        g_rows = _dry_mover_rows(facts.get("gainers") or [])
        l_rows = _dry_mover_rows(facts.get("losers") or [])
        if not g_rows and not l_rows:
            g_rows, l_rows = gainers, losers
        attr = facts.get("attribution") or {}
        summary_line = str(attr.get("summary_line") or "").strip()
        nav = facts.get("nav_1w_pct")
        if summary_line:
            fund_summary = f"{summary_line} (Dry run — prices only.)"
        elif nav is not None:
            fund_summary = f"{label}: fund NAV moved {nav:+.2f}% over the last week (dry run — prices only)."
        else:
            fund_summary = f"{label} — weekly facts loaded (dry run — prices only)."
        fund_summary = _finalize_summary(fund_summary, omit_portfolio_pct=omit_portfolio_pct)
        return _package(scheme, fund_summary, g_rows, l_rows, facts, headline=f"{label} — week", source="dry_run")

    parsed = _llm_call(
        _COMPOSE_SYSTEM,
        _compose_user_message(facts, gainers, losers, omit_portfolio_pct=omit_portfolio_pct),
        _RESPONSE_SCHEMA,
        "equity_fund_week_compose",
    )

    if not parsed:
        fund_summary = _finalize_summary(
            _ensure_fund_summary(facts, gainers, losers, None, omit_portfolio_pct=omit_portfolio_pct),
            omit_portfolio_pct=omit_portfolio_pct,
        )
        return _package(
            scheme,
            fund_summary,
            gainers,
            losers,
            facts,
            headline=_fund_display_name(scheme) + " — week",
            source="stitched",
        )

    fund_summary = _finalize_summary(
        _ensure_fund_summary(facts, gainers, losers, parsed, omit_portfolio_pct=omit_portfolio_pct),
        omit_portfolio_pct=omit_portfolio_pct,
    )
    out_gainers = _parse_mover_rows(parsed.get("gainers"), fallback=gainers)
    out_losers = _parse_mover_rows(parsed.get("losers"), fallback=losers)
    headline = str(parsed.get("headline") or "").strip() or f"{_fund_display_name(scheme)} — week"
    source = "llm" if _summary_ok(fund_summary) else "stitched"

    return _package(scheme, fund_summary, out_gainers, out_losers, facts, headline=headline, source=source)