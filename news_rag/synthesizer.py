"""Render sections and optional LLM narrative per sub-query."""

from __future__ import annotations

import json
import re
from typing import Any, TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.json_util import safe_json_dumps
from news_rag.insights import article_takeaway
from news_rag.snippet_clean import clean_scraped_snippet
from news_rag.llm_client import call_insight_llm, llm_api_key_configured
from news_rag.query_plan import SubQuery

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

NARRATIVE_SYSTEM = """You answer ONE sub-question using ONLY the JSON context provided.
- No buy/sell advice. No predictions. No facts outside the context.
- For exposure_note: read each article's "snippet" (body text from our store). Summarize the news
  (numbers, who is affected, what moved) in prose — never reply with only headlines or a title list.
  Then explain how that theme could matter for the fund's listed holdings (direct name overlap vs indirect).
  If snippets do not mention those companies, say so clearly.
- For news_brief: summarize what article snippets state; do not invent prices.
- Length: exposure_note about 120-180 words; news_brief 80-120 words.
Return plain text only (no markdown headers)."""


def render_performance_summary(nav_payload: dict[str, Any], articles: list[dict] | None = None) -> str:
    name = nav_payload.get("fund_name") or "Fund"
    nav = nav_payload.get("nav")
    nav_date = nav_payload.get("nav_date") or ""
    rets = nav_payload.get("returns") or {}
    lines: list[str] = []
    if nav is not None:
        head = f"**{name}** — NAV **₹{nav}**"
        if nav_date:
            head += f" (as of {nav_date})"
        lines.append(head + ".")
    for label, key in (("1 week", "1w"), ("1 month", "1m"), ("3 months", "3m"), ("6 months", "6m"), ("1 year", "1y")):
        val = rets.get(key)
        if val is not None:
            try:
                lines.append(f"**{label} return**: {float(val):+.2f}%")
            except (TypeError, ValueError):
                pass
    ch = nav_payload.get("day_change_pct")
    if ch is not None:
        try:
            lines.append(f"**Latest day change**: {float(ch):+.2f}%")
        except (TypeError, ValueError):
            pass
    if not lines:
        return f"No performance data available for **{name}**."
    return "\n".join(lines)


def render_one_metric(payload: dict[str, Any]) -> str:
    nav = payload.get("nav")
    name = payload.get("fund_name") or "Fund"
    nav_date = payload.get("nav_date") or ""
    if nav is None:
        return f"Latest NAV is not available for **{name}**."
    if nav_date:
        return f"**{name}** — NAV **₹{nav}** (as of {nav_date})."
    return f"**{name}** — NAV **₹{nav}**."


def render_short_table(rows: list[dict[str, Any]], label: str) -> tuple[str, list[str]]:
    bullets = [f"**{r.get('sector')}**: {float(r.get('percentage', 0)):.2f}%" for r in rows if r.get("sector")]
    text = "\n".join(f"- {b}" for b in bullets) if bullets else f"No {label} data available."
    return text, bullets


def render_short_list(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    bullets = [
        f"**{r.get('name')}**: {float(r.get('percentage', 0)):.2f}%"
        for r in rows
        if r.get("name")
    ]
    text = "\n".join(f"- {b}" for b in bullets) if bullets else "No holdings data available."
    return text, bullets


def build_subquery_section(
    sq: SubQuery,
    tool_results: dict[str, Any],
    *,
    user_question: str = "",
    query_log: QueryLogger | None = None,
) -> dict[str, Any]:
    """tool_results keyed by tool name with ok/data."""
    style = sq.answer_style
    section: dict[str, Any] = {
        "id": sq.id,
        "style": style,
        "text": "",
        "bullets": [],
        "needs_llm": sq.needs_reasoning,
    }

    nav_data = tool_results.get("fund_nav", {}).get("data") if tool_results.get("fund_nav", {}).get("ok") else None
    holdings_data = tool_results.get("fund_holdings", {}).get("data") if tool_results.get("fund_holdings", {}).get("ok") else None
    sectors_data = tool_results.get("fund_sectors", {}).get("data") if tool_results.get("fund_sectors", {}).get("ok") else None
    news_data = tool_results.get("news_search", {}).get("data") if tool_results.get("news_search", {}).get("ok") else None
    metals_data = tool_results.get("metals_spot", {}).get("data") if tool_results.get("metals_spot", {}).get("ok") else None

    if style == "performance_summary":
        if nav_data:
            section["text"] = render_performance_summary(nav_data)
        else:
            section["text"] = "Fund performance data is not available."
        return section

    if style == "one_metric" and nav_data:
        section["text"] = render_one_metric(nav_data)
        return section

    if style == "short_table" and sectors_data:
        rows = sectors_data.get("rows") or []
        text, bullets = render_short_table(rows, "sector")
        section["text"] = text
        section["bullets"] = bullets
        return section

    sector_funds_data = (
        tool_results.get("sector_funds", {}).get("data")
        if tool_results.get("sector_funds", {}).get("ok")
        else None
    )
    if style in ("short_list", "short_table") and sector_funds_data and not holdings_data:
        rankings = sector_funds_data.get("rankings") or []
        bullets = []
        for i, row in enumerate(rankings[:10], start=1):
            name = row.get("fund_name") or row.get("isin")
            w = row.get("sector_weight_pct") or row.get("impact_score")
            if name and w is not None:
                bullets.append(f"**{i}. {name}** — sector exposure **{float(w):.2f}%**")
        text = "\n".join(f"- {b}" for b in bullets) if bullets else "No ranked funds found for this theme."
        section["text"] = text
        section["bullets"] = bullets
        return section

    if style in ("short_list", "short_table") and holdings_data:
        rows = holdings_data.get("rows") or []
        text, bullets = render_short_list(rows)
        section["text"] = text
        section["bullets"] = bullets
        return section

    if metals_data and style == "one_metric":
        recap = metals_data.get("recap") or metals_data
        section["text"] = json.dumps(recap, ensure_ascii=False)[:500]
        return section

    if style in ("news_brief", "exposure_note"):
        articles_raw = (news_data or {}).get("articles") if news_data else []
        articles_raw = articles_raw or []
        topic_blob = f"{user_question} {sq.text}".strip()
        articles = _filter_articles_by_subquery(topic_blob, articles_raw)
        compact_articles = _compact_articles_for_context(articles)
        ctx = {
            "sub_query": sq.text,
            "user_question": user_question,
            "fund_nav": nav_data,
            "holdings": (holdings_data or {}).get("rows") if holdings_data else None,
            "sectors": (sectors_data or {}).get("rows") if sectors_data else None,
            "articles": compact_articles,
            "metals": metals_data,
            "sector_fund_rankings": (sector_funds_data or {}).get("rankings")
            if sector_funds_data
            else None,
        }
        if not llm_api_key_configured(get_settings()):
            if query_log is not None:
                query_log.write("synth_exposure mode=deterministic reason=no_llm_api_key")
            articles_left = ctx.get("articles") or []
            if not articles_left and not ctx.get("holdings") and not ctx.get("sectors"):
                section["text"] = "We do not have information related to this query in our data."
            else:
                section["text"] = _deterministic_exposure(ctx, articles_full=articles)
            return section
        user = (
            f"Sub-question: {sq.text}\n"
            f"User question (full): {user_question[:500]}\n\n"
            f"Use article snippets below for facts. Context JSON:\n"
            f"{safe_json_dumps(ctx, limit=14000)}"
        )
        try:
            res = call_insight_llm(NARRATIVE_SYSTEM, user, query_log=query_log)
            section["text"] = (res.text or "").strip()
        except Exception as exc:
            if query_log is not None:
                query_log.write(f"synth_llm_error={exc}")
            section["text"] = _deterministic_exposure(ctx, articles_full=articles)
        return section

    if style == "clarification":
        section["text"] = tool_results.get("_clarification") or "Please clarify the fund name."
        return section

    if style == "multi_block" or (nav_data or holdings_data or sectors_data):
        parts: list[str] = []
        if nav_data:
            parts.append(
                render_performance_summary(nav_data)
                if (nav_data.get("returns") or sq.text.lower().find("perform") >= 0)
                else render_one_metric(nav_data)
            )
        if holdings_data:
            rows = holdings_data.get("rows") or []
            text, bullets = render_short_list(rows)
            if text:
                parts.append(text)
                section["bullets"] = bullets
        if sectors_data:
            rows = sectors_data.get("rows") or []
            text, bullets = render_short_table(rows, "sector")
            if text:
                parts.append(text)
                section["bullets"] = bullets
        if parts:
            section["text"] = "\n\n".join(parts)
            return section

    section["text"] = sq.text + ": data not available in our sources."
    return section


def _filter_articles_by_subquery(sub_query: str, articles: list[dict]) -> list[dict]:
    import re

    lower = (sub_query or "").lower()
    tokens: list[str] = []
    if re.search(r"\b(crude|oil|petroleum|brent|barrel+)\b", lower):
        tokens.extend(["crude", "oil", "petroleum", "brent", "barrel"])
    if re.search(r"\b(gold|silver)\b", lower):
        tokens.extend(["gold", "silver"])
    if re.search(r"\b(rbi|repo|rate hike|interest rate)\b", lower):
        tokens.extend(["rbi", "repo", "rate"])
    if not tokens:
        return articles

    def matches(article: dict) -> bool:
        hay = " ".join(
            [
                str(article.get("title") or ""),
                str(article.get("snippet") or ""),
            ]
        ).lower()
        return any(t in hay for t in tokens)

    filtered = [a for a in articles if matches(a)]
    return filtered if filtered else []


def _mentions_crude(*parts: str) -> bool:
    blob = " ".join(p for p in parts if p).lower()
    return bool(re.search(r"\b(crude|oil|petroleum|brent)\b", blob))


def _compact_articles_for_context(articles: list[dict]) -> list[dict]:
    """Pass snippet body to the insight LLM (not just titles)."""
    settings = get_settings()
    cap = max(800, min(settings.snippet_chars, 2500))
    out: list[dict] = []
    for row in articles[:5]:
        snippet = clean_scraped_snippet(str(row.get("snippet") or ""))
        if len(snippet) > cap:
            snippet = snippet[:cap].rsplit(" ", 1)[0]
        out.append(
            {
                "title": row.get("title"),
                "published_at": row.get("published_at"),
                "snippet": snippet,
                "entity_names": (row.get("entity_names") or [])[:10],
                "sector_names": (row.get("sector_names") or [])[:6],
            }
        )
    return out


def _holding_names_overlap_articles(holdings: list[dict], articles: list[dict]) -> list[str]:
    names: list[str] = []
    for row in holdings[:8]:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        low = name.lower()
        for art in articles:
            title = str(art.get("title") or "").lower()
            ents = {str(e).lower() for e in (art.get("entity_names") or [])}
            snip = str(art.get("snippet") or "").lower()
            if low in ents or low in title or low in snip:
                names.append(name)
                break
    return names


def _fund_linkage_paragraph(topic_blob: str, holdings: list[dict], articles: list[dict]) -> str:
    top = holdings[:5]
    labels = [f"**{r.get('name')}** ({float(r.get('percentage', 0)):.1f}%)" for r in top if r.get("name")]
    if not labels:
        return ""
    overlap = _holding_names_overlap_articles(holdings, articles)
    joined = ", ".join(labels)
    if overlap:
        return (
            f"**Link to this fund:** Stored articles explicitly mention **{', '.join(overlap)}** "
            f"among the largest weights ({joined})."
        )
    if _mentions_crude(topic_blob):
        return (
            f"**Link to this fund:** These crude/macro pieces do not name the fund's top holdings "
            f"({joined}). The read-through is mostly indirect — fuel subsidies and import-cost pressure "
            f"on the economy, rupee and rate moves — rather than direct oil marketing exposure. "
            f"Defence-heavy books may feel second-order effects (sentiment, industrial input costs) more "
            f"than spot crude itself."
        )
    return f"**Link to this fund:** Largest weights to compare against the stories above: {joined}."


def _deterministic_exposure(ctx: dict[str, Any], *, articles_full: list[dict] | None = None) -> str:
    sub_q = str(ctx.get("sub_query") or "")
    user_q = str(ctx.get("user_question") or "")
    topic_blob = f"{user_q} {sub_q}"
    pool = articles_full if articles_full is not None else ctx.get("articles") or []
    articles = _filter_articles_by_subquery(topic_blob, pool)
    holdings = ctx.get("holdings") or []
    sectors = ctx.get("sectors") or []

    if not articles:
        if _mentions_crude(topic_blob):
            top = holdings[:5]
            if top:
                names = ", ".join(
                    f"**{r.get('name')}** ({float(r.get('percentage', 0)):.1f}%)"
                    for r in top
                    if r.get("name")
                )
                return (
                    "We did not find crude-oil headlines in our news window that explicitly mention "
                    f"this fund's largest holdings ({names}). "
                    "Crude moves can still affect the portfolio indirectly (input costs, macro risk "
                    "sentiment, and any energy-linked suppliers) — but this defence-heavy sleeve has "
                    "limited direct fuel exposure compared with energy or consumption funds."
                )
            return (
                "We did not find crude-oil headlines in our news window for this question. "
                "Without holdings context we cannot map crude news to specific portfolio names."
            )
        return "We do not have verified news in our store that matches this part of your question."

    lines: list[str] = []
    head = "**What stored articles say:**" if _mentions_crude(topic_blob) else "**News recap (from our store):**"
    lines.append(head)
    for art in articles[:3]:
        title = (art.get("title") or "").strip()
        takeaway = article_takeaway(art)
        if title and takeaway.lower() != title.lower():
            lines.append(f"- {takeaway}")
        elif title:
            lines.append(f"- {title}")

    link = _fund_linkage_paragraph(topic_blob, holdings, articles)
    if link:
        lines.append("")
        lines.append(link)

    if sectors and _mentions_crude(topic_blob):
        sec = ", ".join(
            f"**{r.get('sector')}** ({float(r.get('percentage', 0)):.1f}%)"
            for r in sectors[:4]
            if r.get("sector")
        )
        if sec:
            lines.append(f"**Sector weights:** {sec}.")
    return "\n".join(lines)


def merge_insight(sections: list[dict[str, Any]]) -> str:
    parts = [str(s.get("text") or "").strip() for s in sections if str(s.get("text") or "").strip()]
    return "\n\n".join(parts)
