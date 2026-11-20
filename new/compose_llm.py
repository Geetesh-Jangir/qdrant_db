"""Fund-week narrative composed by LLM from full fund context."""

from __future__ import annotations

import json
import re
from typing import Any

from ai_insight.common.prose_guard import scrub_refusal_prose, split_sentences
from news_rag.llm_client import LlmCallResult, call_json_llm

from new.equity_week_llm import equity_week_llm_kwargs
from new.stock_explain import _short_name, clamp_why_paragraph, polish_why

_COMPOSE_SYSTEM = """You compose the weekly mutual fund insight for a portfolio owner.

FACTS JSON is complete. Never ask for more data.

Return JSON with:
- headline (under 10 words)
- summary_opener, summary_losses, summary_extra_drag (optional empty), summary_overall
- gainers[], losers[] for the detail section below the summary

TOP SUMMARY — four parts (plain English, name stocks + brief reason, NOT sector buckets like "consumer durables"):

summary_opener — one sentence:
"[scheme_name], which makes up [portfolio_pct_of_book]% of your portfolio, [gained slightly / lost a little / was about flat] this week, supported by [2–3 gainer names] and short reasons (e.g. strong buying in X, higher electronics revenue at Y)."

summary_losses — one sentence:
"Losses in [loser names] weighed on returns, with [one combined reason — fuel costs, stake sale, weak profits]."

summary_extra_drag — optional one sentence (empty string if nothing extra):
"[Name] added to the decline as [specific reason from drafts]."

summary_overall — one sentence starting with "Overall,":
"Overall, gains in [names or themes] were [largely offset by / outweighed by] weakness in [names or themes], leaving the fund [marginally positive / slightly negative / about flat]."

STYLE (do not copy names blindly — use FACTS):
"Invesco India Large & Mid Cap Fund, which makes up 41.4% of your portfolio, gained slightly this week, supported by strong buying in Max Healthcare and higher electronics revenue at Amber Enterprises."
"Losses in Sai Life Sciences and InterGlobe Aviation weighed on returns, with rising airline fuel costs pressuring profitability."
"Aditya Infotech added to the decline as a major shareholder sold a significant stake, overshadowing strong profit growth."
"Overall, gains in healthcare and industrial holdings were largely offset by weakness in other stocks, leaving the fund marginally positive."

DETAIL BODY — gainers/losers with has_news only; change_1w_pct in JSON; why 2–4 sentences, no heavy numbers in why text.

No buy/sell advice. No "the article says"."""

_SUMMARY_ONLY_SYSTEM = """Write only the four top summary sentences for the fund owner.

Return JSON: {"summary_opener", "summary_losses", "summary_extra_drag", "summary_overall"}

Follow the four-part format and STYLE in the user message. Use scheme_name and portfolio_pct from FACTS.
Name real stocks from gainer_ideas and loser_ideas. Never ask for more data."""

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


def _facts_payload(facts: dict[str, Any], gainers: list[dict[str, Any]], losers: list[dict[str, Any]]) -> dict[str, Any]:
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
    return {
        "scheme_name": _fund_display_name(scheme),
        "portfolio_pct_of_book": facts.get("portfolio_pct"),
        "nav_change_1w_pct": nav_f,
        "gainer_ideas": [{"name": g["name"], "theme": _theme_hint(g["why"])} for g in gainers],
        "loser_ideas": [{"name": l["name"], "theme": _theme_hint(l["why"])} for l in losers],
        "draft_insights": drafts,
        "nav_daily": facts.get("nav_daily") or [],
        "prepared_gainers": gainers,
        "prepared_losers": losers,
    }


def _compose_user_message(facts: dict[str, Any], gainers: list[dict[str, Any]], losers: list[dict[str, Any]]) -> str:
    payload = _facts_payload(facts, gainers, losers)
    return (
        "FACTS:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Fill all four summary_* fields using specific stock names from gainer_ideas / loser_ideas."
    )


def _summary_user_message(facts: dict[str, Any], gainers: list[dict[str, Any]], losers: list[dict[str, Any]]) -> str:
    payload = _facts_payload(facts, gainers, losers)
    return "FACTS:\n" + json.dumps(payload, ensure_ascii=False, indent=2)


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
) -> str:
    text = _join_summary(parsed or {})
    if _summary_ok(text):
        return text
    summary_only = _llm_call(
        _SUMMARY_ONLY_SYSTEM,
        _summary_user_message(facts, gainers, losers),
        _SUMMARY_SCHEMA,
        "equity_fund_week_summary",
    )
    if summary_only:
        text = _join_summary(summary_only)
        if _summary_ok(text):
            return text
    return text


def compose_fund_narrative(facts: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    scheme = str(facts.get("scheme_name") or "Fund")
    gainers, losers = _stock_entries(facts.get("stock_news") or [])

    if dry_run:
        nav = facts.get("nav_1w_pct")
        label = _fund_display_name(scheme)
        fund_summary = f"{label} week NAV about {nav}% (dry run)."
        return _package(scheme, fund_summary, gainers, losers, facts, headline=f"{label} — week", source="dry_run")

    parsed = _llm_call(
        _COMPOSE_SYSTEM,
        _compose_user_message(facts, gainers, losers),
        _RESPONSE_SCHEMA,
        "equity_fund_week_compose",
    )

    if not parsed:
        fund_summary = _ensure_fund_summary(facts, gainers, losers, None)
        return _package(
            scheme,
            fund_summary,
            gainers,
            losers,
            facts,
            headline=_fund_display_name(scheme) + " — week",
            source="stitched",
        )

    fund_summary = _ensure_fund_summary(facts, gainers, losers, parsed)
    out_gainers = _parse_mover_rows(parsed.get("gainers"), fallback=gainers)
    out_losers = _parse_mover_rows(parsed.get("losers"), fallback=losers)
    headline = str(parsed.get("headline") or "").strip() or f"{_fund_display_name(scheme)} — week"
    source = "llm" if _summary_ok(fund_summary) else "stitched"

    return _package(scheme, fund_summary, out_gainers, out_losers, facts, headline=headline, source=source)