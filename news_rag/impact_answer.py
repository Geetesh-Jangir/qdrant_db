"""Deterministic impact packets and display for sector discovery + single-fund paths."""

from __future__ import annotations

from typing import Any

from news_rag.fund_search import extract_top_holdings, extract_top_sectors, get_fund_index
from news_rag.impact_evidence import EventEvidence, gather_impact_evidence
from news_rag.impact_gating import infer_ranking_limit, ranking_mode, should_use_sector_ranking_index
from news_rag.insight_format import format_insight_display
from news_rag.parse import ParsedQuery
from news_rag.query_router import RouterResult
from news_rag.impact_event import (
    crude_oil_price_rising,
    crude_sector_channel_note,
    crude_sensitive_sectors,
    event_search_tokens,
    filter_articles_for_event,
    is_crude_oil_event,
    is_rbi_rate_event,
    rbi_rate_tightening,
    rbi_sector_channel_note,
    rbi_sensitive_sectors,
)
from news_rag.impact_rationale import (
    sector_impact_reasoning,
    single_fund_crude_impact_summary,
    single_fund_rbi_impact_summary,
)
from news_rag.sector_fund_ranking import rank_funds_by_sector_exposure


def _sources_from_articles(articles: list[dict], limit: int = 8) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    for a in articles[:limit]:
        url = str(a.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        rows.append(
            {
                "title": a.get("title"),
                "url": url,
                "source": a.get("source"),
                "published_at": a.get("published_at"),
            }
        )
    return rows


def _fund_display_name(isin: str) -> str:
    index = get_fund_index()
    hits = index.search(isin, limit=3)
    for h in hits:
        if str(h.get("isin") or "").upper() == isin.upper():
            return str(h.get("fund_short_name") or isin)
    detail = index.get_fund_detail(isin)
    if detail:
        return str(detail.get("fund_short_name") or detail.get("fund_name") or isin)
    return isin


def build_sector_discovery_packet(
    parsed: ParsedQuery,
    evidence: EventEvidence,
    *,
    limit: int,
    router: RouterResult | None = None,
) -> dict[str, Any]:
    sector_keys = evidence.sector_keys
    if not sector_keys:
        msg = (
            "Could not map this event to a sector label in the sector exposure index. "
            "Try naming the sector (e.g. Automobiles, Banks) or narrowing the time window."
        )
        return {
            "ok": False,
            "reason": "no_sector_mapping",
            "insight_bullets": [],
            "insight_summary": msg,
            "insight": msg,
            "sources": _sources_from_articles(evidence.articles),
            "intent": parsed.intent,
            "insight_source": "impact_sector_ranking",
            "impact_rankings": {"funds": [], "sectors": []},
            "ranking_source": "sector_to_isin_weights",
            "ranking_universe": "regular_growth",
            "contract": {"aligned": True, "use_articles_count": len(evidence.articles)},
        }

    ranked = rank_funds_by_sector_exposure(
        sector_keys,
        limit=limit,
        severity=evidence.severity,
        regular_growth_only=True,
        combine="max",
    )
    funds_out = []
    bullets: list[str] = []
    for i, row in enumerate(ranked["rankings"], start=1):
        isin = row["isin"]
        name = _fund_display_name(isin)
        w = row["sector_weight_pct"]
        sk = ", ".join(row.get("sector_breakdown") or sector_keys)
        bullets.append(f"**{i}. {name}** (`{isin}`): **{w:.2f}%** exposure ({sk})")
        funds_out.append({**row, "fund_name": name, "rank": i})

    sector_label = ", ".join(sector_keys)
    event_focus = (router.event_focus if router else "") or ""
    why = sector_impact_reasoning(
        parsed.question,
        sector_keys=sector_keys,
        event_focus=event_focus,
        direction_filter=evidence.direction_filter,
        article_count=len(evidence.articles),
    )
    summary = (
        f"{why} "
        f"Top **{len(funds_out)}** Regular Growth funds with the highest **{sector_label}** "
        f"allocation (latest portfolio sector weights)."
    )
    if evidence.articles:
        summary += (
            f" Supported by **{len(evidence.articles)}** verified article(s) in your date window."
        )
    if evidence.direction_filter != "any":
        summary += f" News tone filter: **{evidence.direction_filter}**."
    if any(row.get("passive_sector_product") for row in funds_out):
        summary += (
            " Prefer **active diversified** funds for portfolio impact; "
            "sector **index/ETF** schemes naturally have the highest sector weight."
        )

    display = format_insight_display(bullets, summary)
    return {
        "ok": True,
        "insight_bullets": bullets,
        "insight_summary": summary,
        "insight": display,
        "sources": _sources_from_articles(evidence.articles),
        "intent": parsed.intent,
        "insight_source": "impact_sector_ranking",
        "impact_rankings": {
            "funds": funds_out,
            "sectors": sector_keys,
        },
        "ranking_source": ranked["ranking_source"],
        "ranking_universe": ranked["ranking_universe"],
        "evidence": {
            "severity": evidence.severity,
            "direction": evidence.direction,
            "direction_filter": evidence.direction_filter,
            "article_count": len(evidence.articles),
            "cluster_count": len(evidence.clusters),
        },
        "contract": {
            "aligned": True,
            "use_articles_count": len(evidence.articles),
        },
    }


def build_single_fund_impact_packet(
    parsed: ParsedQuery,
    articles: list[dict],
    *,
    router: RouterResult | None = None,
) -> dict[str, Any]:
    detail = parsed.fund_resolved or {}
    name = str(detail.get("fund_short_name") or detail.get("fund_name") or "Fund")
    isin = str(detail.get("isin") or "")

    event_focus = (router.event_focus if router else "") or ""
    event_articles = filter_articles_for_event(articles, parsed.question, event_focus)
    event_tokens = event_search_tokens(parsed.question, event_focus)

    crude_event = is_crude_oil_event(event_tokens)
    rbi_event = is_rbi_rate_event(event_tokens)
    touched_sectors: list[tuple[str, float]] = []
    touched_holdings: list[tuple[str, float]] = []

    if crude_event:
        touched_sectors = crude_sensitive_sectors(detail, limit=8)
    elif rbi_event:
        touched_sectors = rbi_sensitive_sectors(detail, limit=8)
    else:
        entity_set: set[str] = set()
        for a in event_articles:
            for e in a.get("entity_names") or []:
                entity_set.add(str(e).lower())

        seen_sec: set[str] = set()
        for row in extract_top_sectors(detail, limit=15):
            sec = str(row.get("sector") or "")
            if sec.lower() in entity_set or any(sec.lower() in e for e in entity_set):
                touched_sectors.append((sec, float(row.get("percentage") or 0)))
                seen_sec.add(sec)

        for row in extract_top_holdings(detail, limit=20):
            hname = str(row.get("name") or "")
            if hname.lower() in entity_set or any(hname.lower() in e for e in entity_set):
                touched_holdings.append((hname, float(row.get("percentage") or 0)))

    top_sector_rows = [
        (str(r.get("sector") or ""), float(r.get("percentage") or 0))
        for r in extract_top_sectors(detail, limit=8)
    ]

    bullets: list[str] = []
    if crude_event:
        oil_rising = crude_oil_price_rising(parsed.question, event_focus)
        for s, pct in touched_sectors:
            note = crude_sector_channel_note(s, oil_rising=oil_rising)
            bullets.append(f"**{s}** ({pct:.2f}%): {note}")
        if not touched_sectors:
            bullets.append(
                "No oil-sensitive sector weights found in the latest holdings; "
                "crude moves would likely affect this fund only indirectly."
            )
    elif rbi_event:
        tightening = rbi_rate_tightening(parsed.question, event_focus)
        for s, pct in touched_sectors:
            note = rbi_sector_channel_note(s, tightening=tightening)
            bullets.append(f"**{s}** ({pct:.2f}%): {note}")
        if not touched_sectors:
            bullets.append(
                "Banks/Finance are a small slice of this portfolio; RBI moves may affect NAV mainly indirectly."
            )
    else:
        if touched_holdings:
            for h, pct in touched_holdings[:8]:
                bullets.append(f"**{h}**: **{pct:.2f}%** of **{name}** — mentioned in related news")
        if touched_sectors:
            for s, pct in touched_sectors[:6]:
                bullets.append(f"**{s}** sector: **{pct:.2f}%** of **{name}**")

    clusters: list[list[dict]] = []
    if event_articles and not crude_event and not rbi_event:
        from news_rag.fund_brief import cluster_articles

        clusters = cluster_articles(event_articles)

    if not event_articles:
        if crude_event and touched_sectors:
            summary = single_fund_crude_impact_summary(
                name,
                oil_rising=crude_oil_price_rising(parsed.question, event_focus),
                crude_sectors=touched_sectors,
                top_sectors=top_sector_rows,
                article_count=0,
                window_label=parsed.window_label,
            )
            display = format_insight_display(bullets, summary)
            return {
                "ok": True,
                "insight_bullets": bullets,
                "insight_summary": summary,
                "insight": display,
                "sources": [],
                "intent": parsed.intent,
                "insight_source": "impact_single_fund",
                "impact_breakdown": {
                    "fund_name": name,
                    "isin": isin,
                    "touched_holdings": [],
                    "touched_sectors": [{"sector": s, "pct": p} for s, p in touched_sectors],
                },
                "ranking_source": "fund_api",
                "contract": {"aligned": True, "use_articles_count": 0},
            }
        if rbi_event and touched_sectors:
            asked = parsed.question
            if "top 100" in asked.lower() and "large cap" in name.lower():
                name = f"{name} (resolved from “HDFC Top 100 Fund” in your question)"
            summary = single_fund_rbi_impact_summary(
                name,
                tightening=rbi_rate_tightening(parsed.question, event_focus),
                rate_sectors=touched_sectors,
                top_sectors=top_sector_rows,
                article_count=0,
                window_label=parsed.window_label,
            )
            display = format_insight_display(bullets, summary)
            return {
                "ok": True,
                "insight_bullets": bullets,
                "insight_summary": summary,
                "insight": display,
                "sources": [],
                "intent": parsed.intent,
                "insight_source": "impact_single_fund",
                "impact_breakdown": {
                    "fund_name": name,
                    "isin": isin,
                    "touched_holdings": [],
                    "touched_sectors": [{"sector": s, "pct": p} for s, p in touched_sectors],
                },
                "ranking_source": "fund_api",
                "contract": {"aligned": True, "use_articles_count": 0},
            }
        msg = (
            f"No verified news in the store for **{name}** (`{isin}`) in {parsed.window_label}. "
            "Exposure uses live fund holdings/sectors only."
        )
        return {
            "ok": True,
            "insight_bullets": bullets,
            "insight_summary": msg,
            "insight": format_insight_display(bullets, msg) if bullets else msg,
            "sources": [],
            "intent": parsed.intent,
            "insight_source": "impact_single_fund",
            "impact_breakdown": {
                "fund_name": name,
                "isin": isin,
                "touched_holdings": [{"name": h, "pct": p} for h, p in touched_holdings],
                "touched_sectors": [{"sector": s, "pct": p} for s, p in touched_sectors],
            },
            "ranking_source": "fund_api",
            "contract": {"aligned": True, "use_articles_count": 0},
        }

    focus_label = event_focus or "the event you asked about"
    if crude_event:
        summary = single_fund_crude_impact_summary(
            name,
            oil_rising=crude_oil_price_rising(parsed.question, event_focus),
            crude_sectors=touched_sectors,
            top_sectors=top_sector_rows,
            article_count=len(event_articles),
            window_label=parsed.window_label,
        )
    elif rbi_event:
        summary = single_fund_rbi_impact_summary(
            name,
            tightening=rbi_rate_tightening(parsed.question, event_focus),
            rate_sectors=touched_sectors,
            top_sectors=top_sector_rows,
            article_count=len(event_articles),
            window_label=parsed.window_label,
        )
    else:
        summary = (
            f"**{name}** (`{isin}`) vs **{focus_label}**: **{len(clusters)}** relevant news cluster(s); "
            f"**{len(touched_holdings)}** holding(s) and **{len(touched_sectors)}** sector slice(s) in the portfolio."
        )
    display = format_insight_display(bullets[:10], summary)
    return {
        "ok": True,
        "insight_bullets": bullets[:10],
        "insight_summary": summary,
        "insight": display,
        "sources": _sources_from_articles(event_articles),
        "intent": parsed.intent,
        "insight_source": "impact_single_fund",
        "impact_breakdown": {
            "fund_name": name,
            "isin": isin,
            "touched_holdings": [{"name": h, "pct": p} for h, p in touched_holdings],
            "touched_sectors": [{"sector": s, "pct": p} for s, p in touched_sectors],
        },
        "ranking_source": "fund_api",
        "contract": {"aligned": True, "use_articles_count": len(event_articles)},
    }


def try_impact_answer(
    parsed: ParsedQuery,
    articles: list[dict],
    router: RouterResult,
    *,
    question: str,
    published_from: str,
    published_to: str,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log=None,
) -> dict[str, Any] | None:
    mode = ranking_mode(router)
    if router.intent not in ("impact_funds", "fund_event_impact"):
        return None

    if should_use_sector_ranking_index(router):
        limit = infer_ranking_limit(question)
        raw = router.raw_json or {}
        if isinstance(raw.get("impact_limit"), int):
            limit = raw["impact_limit"]
        evidence = gather_impact_evidence(
            question,
            router,
            published_from=published_from,
            published_to=published_to,
            min_impact=min_impact,
            source=source,
            direction=direction,
            query_log=query_log,
        )
        if query_log is not None:
            query_log.write(
                f"impact_ranking sector_index=true ranking_universe=regular_growth limit={limit}"
            )
        return build_sector_discovery_packet(parsed, evidence, limit=limit, router=router)

    if mode == "single_fund" and parsed.fund_resolved:
        if query_log is not None:
            query_log.write("impact_ranking sector_index=false path=single_fund fund_api=true")
        return build_single_fund_impact_packet(parsed, articles, router=router)

    return None
