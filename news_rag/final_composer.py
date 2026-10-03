"""Single-segment answer: NAV + news + holdings in one LLM pass (bullets + summary)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from news_rag.config import Settings, get_settings
from news_rag.insight_format import (
    clamp_bullets,
    clamp_summary,
    format_insight_display,
    format_insight_sections_display,
    parse_structured_insight,
)
from news_rag.bullion_insights import compose_macro_metals_insight
from news_rag.llm_client import call_insight_llm, llm_api_key_configured
from news_rag.snippet_clean import (
    clean_scraped_snippet,
    looks_like_raw_scrape,
    sanitize_analyst_bullet,
)
from news_rag.bullion_insights import filter_bullion_articles
from news_rag.macro_plans import PRESET_SOURCES
from news_rag.synthesizer import (
    _compact_articles_for_context,
    _filter_articles_by_subquery,
    _fund_linkage_paragraph,
    _mentions_crude,
)

if TYPE_CHECKING:
    from news_rag.execution import SubQueryRun
    from news_rag.query_log import QueryLogger

UNIFIED_SYSTEM = """You are a mutual-fund and India-markets research analyst. Answer the user's FULL question using ONLY the JSON context.

Output format (required):

BULLETS:
- 4-7 short analyst bullets (max ~40 words each).
- Cover every part of the question that the context can support (prices, reasons, sectors, funds, stocks, NAV).
- Rewrite snippets in your own words. Never paste scrape text, datelines, or "..." fragments.
- Do NOT include publication dates, weekdays, "Min Read", loan/ad banners, or IST timestamps in bullets.
- Name funds from sector_fund_rankings or fund_nav when present. Name holdings only from holdings list.

SUMMARY:
2-4 sentences tying the pieces together. No buy/sell advice. No invented numbers.

If articles are thin, say so and still use NAV, metals, and fund rankings that ARE in context.
Do not name publishers."""

UNIFIED_BY_SOURCE = {
    "macro_metals": """Focus: WHY gold/silver fell (rupee, dollar/rates, MCX, import demand, profit-booking from range highs).
Use metals recap numbers. Use ONLY bullion-relevant article snippets — never defence deals, crude-only, or random equity M&A as reasons for bullion.
Then which mutual-fund sleeves (rankings) are most exposed. 'My portfolio' is hypothetical — do not claim you read the user's book.""",
    "preset_crude_energy": """Focus: barrel/crude news, energy/OMC/power transmission, then funds with high petroleum/power weights from rankings. Indirect hits (airlines, auto) only if snippets support them.""",
    "preset_fund_insights": """Focus: this named fund — NAV/returns first, then holdings/sectors, then news that actually names those companies. If news is generic, say the link is indirect.""",
    "preset_market_pulse": """Focus: what stored India-market news shows is moving NOW (macro, sectors, big events). 'What to focus on' = prominent themes in the store, not stock tips.""",
    "preset_sector_tape": """Focus: last-month sector tape — constructive vs pressured sectors with WHY from snippets. If the store is thin, group remaining headlines honestly rather than inventing a full league table.""",
}

UNIFIED_STRICT_RETRY = """Your prior draft pasted raw news text. Rewrite completely.
Short analyst bullets only (max 35 words each). Paraphrase snippets. Include fund linkage. Same BULLETS:/SUMMARY: format."""


@dataclass
class ComposedAnswer:
    bullets: list[str]
    summary: str
    display: str
    source: str  # unified_llm | unified_deterministic
    insight_sections: list[dict] | None = None


def should_unify_compose(plan: QueryPlan, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if not settings.rag_unified_compose:
        return False
    if plan.source in PRESET_SOURCES:
        return True
    if len(plan.sub_queries) < 2:
        return False
    styles = {sq.answer_style for sq in plan.sub_queries}
    tools = {n.tool for sq in plan.sub_queries for n in sq.data_needs}
    if "performance_summary" in styles and ("exposure_note" in styles or "news_brief" in styles):
        return True
    if "fund_nav" in tools and "news_search" in tools:
        return True
    if "metals_spot" in tools and ("news_search" in tools or "sector_funds" in tools):
        return True
    return False


def aggregate_runs(
    runs: list[SubQueryRun],
    question: str,
    *,
    plan_source: str = "",
) -> dict[str, Any]:
    nav: dict[str, Any] | None = None
    holdings: list[dict] = []
    sectors: list[dict] = []
    articles_by_url: dict[str, dict] = {}

    metals: dict[str, Any] | None = None
    sector_funds: dict[str, Any] | None = None
    for run in runs:
        tr = run.tool_results or {}
        if tr.get("fund_nav", {}).get("ok"):
            nav = tr["fund_nav"].get("data") or nav
        if tr.get("metals_spot", {}).get("ok"):
            metals = tr["metals_spot"].get("data") or metals
        if tr.get("sector_funds", {}).get("ok"):
            sector_funds = tr["sector_funds"].get("data") or sector_funds
        if tr.get("fund_holdings", {}).get("ok"):
            rows = (tr["fund_holdings"].get("data") or {}).get("rows") or []
            if rows:
                holdings = rows
        if tr.get("fund_sectors", {}).get("ok"):
            rows = (tr["fund_sectors"].get("data") or {}).get("rows") or []
            if rows:
                sectors = rows
        news = (tr.get("news_search") or {}).get("data") or {}
        for art in news.get("articles") or []:
            url = str(art.get("url") or "").strip()
            if url:
                articles_by_url[url] = art
            elif art.get("title"):
                articles_by_url[str(art.get("title"))] = art

    articles = list(articles_by_url.values())
    topic_blob = question
    filtered = _filter_articles_by_subquery(topic_blob, articles)
    if plan_source == "macro_metals":
        bullion = filter_bullion_articles(articles)
        filtered = bullion if bullion else filtered
    return {
        "nav": nav,
        "holdings": holdings,
        "sectors": sectors,
        "metals": metals,
        "sector_fund_rankings": (sector_funds or {}).get("rankings"),
        "articles": filtered,
        "articles_compact": _compact_articles_for_context(filtered),
    }


def _nav_performance_bullet(nav: dict[str, Any] | None) -> str:
    if not nav:
        return ""
    name = nav.get("fund_name") or "Fund"
    nav_val = nav.get("nav")
    nav_date = nav.get("nav_date") or ""
    rets = nav.get("returns") or {}
    chunks: list[str] = []
    if nav_val is not None:
        bit = f"**{name}** NAV **₹{nav_val}**"
        if nav_date:
            bit += f" ({nav_date})"
        chunks.append(bit)
    for label, key in (("1M", "1m"), ("1W", "1w"), ("6M", "6m"), ("1Y", "1y")):
        val = rets.get(key)
        if val is not None:
            try:
                chunks.append(f"{label} {float(val):+.2f}%")
            except (TypeError, ValueError):
                pass
    ch = nav.get("day_change_pct")
    if ch is not None:
        try:
            chunks.append(f"day {float(ch):+.2f}%")
        except (TypeError, ValueError):
            pass
    if not chunks:
        return ""
    return "**Performance:** " + "; ".join(chunks) + "."


def _article_corpus(articles: list[dict]) -> str:
    parts: list[str] = []
    for art in articles:
        parts.append(clean_scraped_snippet(str(art.get("snippet") or "")))
        parts.append(str(art.get("title") or ""))
    return " ".join(parts)


def _thematic_impact_bullets(corpus: str, holdings: list[dict]) -> list[str]:
    """Analyst-style themes — not raw snippet paste."""
    bullets: list[str] = []
    if not corpus.strip():
        return bullets

    if re.search(r"\b(IOC|HPCL|BPCL|OMC|under-recover|litre on petrol|litre on diesel|LPG)\b", corpus, re.I):
        bullets.append(
            "**Fuel-marketing margin stress:** Coverage highlights large daily under-recoveries on "
            "petrol, diesel and LPG for state-owned fuel retailers — a sector story for OMCs, not "
            "this fund's defence-heavy weights."
        )
    if re.search(r"\b(Brent|WTI|crude|import bill|\$9\d|\$8\d|per barrel)\b", corpus, re.I):
        bullets.append(
            "**Crude near highs:** Stored articles flag Brent/WTI in the high-$90s area and a "
            "wider oil import bill — raising macro energy-cost and currency pressure."
        )
    if re.search(r"\b(yield|bps|bond|gilt|10-year|five-year)\b", corpus, re.I):
        bullets.append(
            "**Tighter rates backdrop:** Bond yields moved up in the same window, adding macro "
            "volatility alongside the oil shock."
        )

    top = holdings[:5]
    if top:
        names = ", ".join(f"**{r.get('name')}**" for r in top if r.get("name"))
        bullets.append(
            f"**For this fund:** Top weights ({names}) are not fuel marketers; any crude read-through "
            f"is mainly indirect (macro sentiment, input costs for industrials) unless articles name them."
        )
    return bullets[:4]


def _polish_bullets(bullets: list[str]) -> list[str]:
    polished: list[str] = []
    for raw in bullets:
        text = sanitize_analyst_bullet(raw)
        if text:
            polished.append(text)
    return polished


def _bullets_need_rewrite(bullets: list[str]) -> bool:
    if not bullets:
        return True
    pasted = sum(1 for b in bullets if looks_like_raw_scrape(b))
    return pasted >= max(1, len(bullets) // 2)


def compose_unified_answer(
    question: str,
    agg: dict[str, Any],
    *,
    plan_source: str = "",
    query_log: QueryLogger | None = None,
) -> ComposedAnswer:
    settings = get_settings()
    if plan_source == "macro_metals":
        bullets, summary, insight_sections = compose_macro_metals_insight(
            agg.get("articles") or [],
            agg.get("metals"),
            agg.get("sector_fund_rankings") or [],
        )
        display = format_insight_sections_display(insight_sections, summary)
        if query_log is not None:
            query_log.write("unified_compose source=macro_metals_structured")
        return ComposedAnswer(
            bullets=bullets,
            summary=summary,
            display=display,
            source="unified_deterministic",
            insight_sections=insight_sections,
        )

    ctx = {
        "user_question": question,
        "plan_source": plan_source,
        "fund_nav": agg.get("nav"),
        "holdings": agg.get("holdings"),
        "sectors": agg.get("sectors"),
        "metals": agg.get("metals"),
        "sector_fund_rankings": agg.get("sector_fund_rankings"),
        "articles": agg.get("articles_compact"),
    }

    system = UNIFIED_SYSTEM
    extra = UNIFIED_BY_SOURCE.get(plan_source or "")
    if extra:
        system = UNIFIED_SYSTEM + "\n\nQuestion type: " + extra

    if llm_api_key_configured(settings):
        user = f"User question:\n{question}\n\nContext JSON:\n{json.dumps(ctx, ensure_ascii=False)[:16000]}"
        try:
            res = call_insight_llm(
                system_prompt=system,
                user_content=user,
                query_log=query_log,
            )
            bullets, summary = parse_structured_insight(res.text or "")
            bullets = _polish_bullets(bullets)
            if _bullets_need_rewrite(bullets):
                if query_log is not None:
                    query_log.write("unified_compose retry=strict_rewrite")
                res2 = call_insight_llm(
                    system_prompt=UNIFIED_STRICT_RETRY + "\n\n" + system,
                    user_content=user,
                    query_log=query_log,
                )
                bullets2, summary2 = parse_structured_insight(res2.text or "")
                bullets2 = _polish_bullets(bullets2)
                if bullets2 and not _bullets_need_rewrite(bullets2):
                    bullets, summary = bullets2, summary2 or summary
            bullets = clamp_bullets(
                bullets,
                max_count=settings.insight_max_bullets + 2,
                max_chars=settings.insight_bullet_max_chars,
            )
            summary = clamp_summary(summary, max_words=settings.insight_summary_max_words)
            if _bullets_need_rewrite(bullets):
                if query_log is not None:
                    query_log.write("unified_compose llm_output_rejected=raw_paste fallback=thematic")
                bullets, summary = _deterministic_unified(question, agg, plan_source=plan_source)
                display = format_insight_display(bullets, summary)
                return ComposedAnswer(
                    bullets=bullets,
                    summary=summary,
                    display=display,
                    source="unified_deterministic",
                )
            if bullets or summary:
                display = format_insight_display(bullets, summary)
                if query_log is not None:
                    query_log.write(f"unified_compose source=llm provider={res.provider}")
                return ComposedAnswer(bullets=bullets, summary=summary, display=display, source="unified_llm")
        except Exception as exc:
            if query_log is not None:
                query_log.write(f"unified_compose_llm_error={exc}")

    bullets, summary = _deterministic_unified(question, agg, plan_source=plan_source)
    display = format_insight_display(bullets, summary)
    if query_log is not None:
        query_log.write("unified_compose source=deterministic")
    return ComposedAnswer(bullets=bullets, summary=summary, display=display, source="unified_deterministic")


def _metals_bullets(metals: dict[str, Any] | None) -> list[str]:
    if not metals:
        return []
    recap = metals.get("recap") if isinstance(metals.get("recap"), dict) else metals
    if not isinstance(recap, dict):
        return []
    g7 = recap.get("gold_7d_change_pct")
    s7 = recap.get("silver_7d_change_pct")
    g1 = recap.get("gold_1d_change_pct")
    s1 = recap.get("silver_1d_change_pct")
    parts = []
    if g7 is not None or s7 is not None:
        try:
            parts.append(
                f"**Bullion tape:** 24K gold 7-day {float(g7 or 0):+.2f}%; silver 7-day {float(s7 or 0):+.2f}% "
                f"(1-day gold {float(g1 or 0):+.2f}%, silver {float(s1 or 0):+.2f}%)."
            )
        except (TypeError, ValueError):
            pass
    return parts


def _ranking_bullet(rankings: list[dict] | None, label: str) -> str:
    if not rankings:
        return ""
    names = []
    for row in rankings[:5]:
        name = row.get("fund_name") or row.get("isin")
        w = row.get("sector_weight_pct")
        if not name:
            continue
        if w is not None:
            try:
                names.append(f"**{name}** ({float(w):.1f}%)")
            except (TypeError, ValueError):
                names.append(f"**{name}**")
        else:
            names.append(f"**{name}**")
    if not names:
        return ""
    return f"**{label}:** " + "; ".join(names) + "."


def _news_theme_bullets(
    articles: list[dict],
    limit: int = 3,
    *,
    bullion_only: bool = False,
) -> list[str]:
    from news_rag.insights import analyst_line_from_article

    out: list[str] = []
    for art in articles[: limit * 2]:
        take = analyst_line_from_article(art, limit=220, bullion_only=bullion_only)
        if take:
            out.append(take)
        if len(out) >= limit:
            break
    return out


def _deterministic_unified(
    question: str,
    agg: dict[str, Any],
    *,
    plan_source: str = "",
) -> tuple[list[str], str]:
    articles = agg.get("articles") or []
    holdings = agg.get("holdings") or []
    sectors = agg.get("sectors") or []
    rankings = agg.get("sector_fund_rankings") or []
    corpus = _article_corpus(articles)
    bullets: list[str] = []

    if plan_source == "macro_metals":
        bullets, summary, _ = compose_macro_metals_insight(
            articles,
            agg.get("metals"),
            rankings,
        )
        return bullets[:10], summary

    if plan_source == "preset_crude_energy":
        bullets.extend(_thematic_impact_bullets(corpus, []) or _news_theme_bullets(articles, 3))
        if not bullets:
            bullets.append(
                "**Crude/energy:** Barrel headlines in our store were thin this window; still treat OMCs, refiners, and power as the first-order sector map."
            )
        bullets.append(
            "**Sectors in the blast radius:** Petroleum products and power are direct; airlines, chemicals, and some autos can feel fuel-cost second-round effects."
        )
        rb = _ranking_bullet(rankings, "Funds with high energy/oil-product weights")
        if rb:
            bullets.append(rb)
        summary = (
            "Barrel moves reprice energy and OMC cash flows first. Funds with the largest petroleum/power weights in our ranking "
            "are the ones most exposed; others only via inflation, rates, and sentiment."
        )
        return bullets[:7], summary

    if plan_source == "preset_fund_insights":
        perf = _nav_performance_bullet(agg.get("nav"))
        if perf:
            bullets.append(perf)
        if holdings:
            names = ", ".join(
                f"**{r.get('name')}** ({float(r.get('percentage', 0)):.1f}%)"
                for r in holdings[:5]
                if r.get("name")
            )
            if names:
                bullets.append(f"**Largest holdings:** {names}.")
        if sectors:
            names = ", ".join(
                f"**{r.get('sector')}** ({float(r.get('percentage', 0)):.1f}%)"
                for r in sectors[:4]
                if r.get("sector")
            )
            if names:
                bullets.append(f"**Sectors:** {names}.")
        news_bits = _news_theme_bullets(articles, 3)
        if news_bits:
            bullets.extend(news_bits)
        else:
            bullets.append(
                "**Holdings news:** No tightly matching headlines in this window; use NAV/weights as the factual core."
            )
        name = (agg.get("nav") or {}).get("fund_name") or "This fund"
        summary = (
            f"{name} insights here are NAV, current weights, and any stored news on those names — not a recommendation."
        )
        return bullets[:7], summary

    if plan_source == "preset_market_pulse":
        news_bits = _news_theme_bullets(articles, 5)
        if news_bits:
            bullets.extend(news_bits)
        else:
            bullets.append(
                "**Market pulse:** Our news window did not return a dense set of India-market headlines. "
                "Without that, we cannot invent a 'what's hot' tape."
            )
        summary = (
            "Focus on the themes actually present in stored news (macro, crude, rates, large-cap names) — "
            "this is a recap of what the tape has already printed, not a shopping list."
        )
        return bullets[:7], summary

    if plan_source == "preset_sector_tape":
        news_bits = _news_theme_bullets(articles, 5)
        if news_bits:
            bullets.extend(news_bits)
        else:
            bullets.append(
                "**Sector tape:** Not enough tagged sector stories in the last-month window to split winners vs laggards cleanly."
            )
        summary = (
            "Positive vs negative sector calls below are inferred only from stored headlines. "
            "Where the store is thin we say so rather than fabricate a full league table."
        )
        return bullets[:7], summary

    perf = _nav_performance_bullet(agg.get("nav"))
    if perf:
        bullets.append(perf)
    bullets.extend(_thematic_impact_bullets(corpus, holdings))
    if not bullets:
        bullets.extend(_news_theme_bullets(articles, 3))

    nav = agg.get("nav") or {}
    rets = nav.get("returns") or {}
    one_m = rets.get("1m")
    name = nav.get("fund_name") or "This fund"
    try:
        one_m_f = float(one_m) if one_m is not None else None
    except (TypeError, ValueError):
        one_m_f = None

    if one_m_f is not None and _mentions_crude(question):
        summary = (
            f"{name} has been **{one_m_f:+.2f}%** over the last month while crude and rates news "
            f"stayed in the tape. Treat commodity read-through as indirect unless holdings are named."
        )
    else:
        summary = _fund_linkage_paragraph(question, holdings, articles)
        summary = summary.replace("**Link to this fund:**", "").strip()

    if not summary:
        summary = "We do not have enough fund or news context to answer this question."
    return bullets[:7], summary
