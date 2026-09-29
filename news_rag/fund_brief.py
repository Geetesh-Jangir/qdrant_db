"""Fund-level and portfolio-level brief from stored news (read-only Qdrant)."""

from __future__ import annotations

import json
import re
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

from lib.portfolio_scope import (
    HOLDING_MIN_PCT,
    SECTOR_MIN_PCT,
    PortfolioScope,
    build_portfolio_scope,
    instrument_to_qdrant_names,
    qdrant_filter_names,
    resolve_allisin_holdings_path,
)
from news_pipeline.config import Settings as PipelineSettings
from news_pipeline.jev.client import JevClient, JevError, read_noul
from news_rag.config import Settings, get_settings
from news_rag.embed import embed_query
from news_rag.insight_format import (
    clamp_bullets,
    clamp_summary,
    format_insight_display,
    parse_structured_insight,
    trim_chars_at_word,
)
from news_rag.llm_client import call_insight_llm, llm_api_key_configured, missing_llm_key_message
from news_rag.query_log import clip_log_text
from news_rag.parse import parse_time_window, to_iso, utc_now
from news_rag.qdrant_reader import (
    QdrantReader,
    build_filter,
    describe_filters_for_log,
    filter_spec,
)

FACT_TYPES = frozenset({"results", "order", "deal", "regulatory", "operations", "macro"})
FUND_BRIEF_MAX_BULLETS = 8
FUND_BRIEF_BULLET_MAX_CHARS = 480
FUND_BRIEF_SUMMARY_MAX_WORDS = 100


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_path(settings: Settings, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute():
        return path
    return _repo_root() / relative


def load_scope(settings: Settings) -> PortfolioScope:
    portfolio_raw = (settings.portfolio_json or "").strip()
    if not portfolio_raw:
        raise ValueError("PORTFOLIO_JSON not configured")
    configured_allisin = _resolve_path(settings, settings.allisin_sectors_holdings_json)
    if configured_allisin.is_file():
        allisin_path = configured_allisin
    else:
        allisin_path = resolve_allisin_holdings_path(
            _repo_root(),
            full_relative=settings.allisin_sectors_holdings_json,
            subset_relative=settings.portfolio_allisin_holdings_json,
        )
    return build_portfolio_scope(
        portfolio_path=_resolve_path(settings, portfolio_raw),
        allisin_path=allisin_path,
        holding_min=settings.portfolio_holding_min_pct,
        sector_min=settings.portfolio_sector_min_pct,
        aggregated_holdings_map_path=_resolve_path(settings, settings.aggregated_holdings_map),
        aggregated_holdings_csv_path=_resolve_path(settings, settings.aggregated_holdings_csv),
        require_aggregated_equity=True,
    )


def load_scope_for_fund(isin: str, settings: Settings) -> PortfolioScope:
    """Load scope dynamically for any fund in the mutual fund index."""
    from news_rag.fund_search import get_fund_index
    from lib.portfolio_scope import (
        FundRef,
        ScopedHolding,
        ScopedSector,
        _holding_equity_allowed,
        is_blocked_sector,
        load_aggregated_equity_keys,
        sector_query_for_label,
    )
    
    index = get_fund_index()
    entry = index.get_fund_detail(isin)
    
    if not isinstance(entry, dict) or entry.get("error"):
        if (settings.portfolio_json or "").strip():
            try:
                scope = load_scope(settings)
                if any(f.isin == isin for f in scope.funds):
                    return scope
            except Exception:
                pass
        raise ValueError(f"ISIN '{isin}' not found in fund database")

    fund_name = entry.get("fund_short_name") or entry.get("fund_name") or isin
    fund_ref = FundRef(isin=isin, fund_short_name=fund_name, current_value=1.0)

    equity_aggregate_keys = None
    try:
        equity_aggregate_keys = load_aggregated_equity_keys(
            map_path=_resolve_path(settings, settings.aggregated_holdings_map),
            csv_path=_resolve_path(settings, settings.aggregated_holdings_csv),
        )
    except Exception:
        pass

    holding_map: dict[str, ScopedHolding] = {}
    sector_map: dict[str, ScopedSector] = {}
    skipped_sectors: set[str] = set()

    raw_holdings = entry.get("holdings") or {}
    if isinstance(raw_holdings, dict):
        for name, info in raw_holdings.items():
            if not isinstance(info, dict):
                continue
            try:
                pct = float(info.get("percentage") or 0)
            except (TypeError, ValueError):
                continue
            if pct < settings.portfolio_holding_min_pct:
                continue
            instrument = str(name).strip()
            if equity_aggregate_keys is not None:
                skip_reason = _holding_equity_allowed(info, instrument, equity_aggregate_keys)
                if skip_reason:
                    continue
            industry = str(info.get("industry") or "").strip()
            key = instrument.casefold()
            holding_map[key] = ScopedHolding(
                instrument_name=instrument,
                industry=industry,
                percentage=pct,
                by_fund={isin: pct},
            )

    raw_sectors = entry.get("sectors") or {}
    if isinstance(raw_sectors, dict):
        for sector_name, weight in raw_sectors.items():
            label = str(sector_name).strip()
            if not label or is_blocked_sector(label):
                continue
            try:
                pct = float(weight or 0)
            except (TypeError, ValueError):
                continue
            if pct < settings.portfolio_sector_min_pct:
                continue
            mapped = sector_query_for_label(label)
            if mapped is None:
                skipped_sectors.add(label)
                continue
            canonical, _ = mapped
            key = canonical.casefold()
            sector_map[key] = ScopedSector(
                sector_label=label,
                canonical_name=canonical,
                percentage=pct,
                by_fund={isin: pct},
            )

    holdings = sorted(holding_map.values(), key=lambda h: (-h.percentage, h.instrument_name.lower()))
    sectors = sorted(sector_map.values(), key=lambda s: (-s.percentage, s.canonical_name.lower()))

    entity_names: set[str] = set()
    for h in holdings:
        entity_names.add(h.instrument_name)
    for s in sectors:
        entity_names.add(s.canonical_name)

    return PortfolioScope(
        funds=[fund_ref],
        holdings=holdings,
        sectors=sectors,
        skipped_sectors=sorted(skipped_sectors),
        skipped_holdings_non_equity=[],
        skipped_holdings_not_in_aggregate=[],
        entity_names_for_news=sorted(entity_names),
    )


def list_portfolio_funds(settings: Settings) -> list[dict[str, Any]]:
    scope = load_scope(settings)
    total = sum(f.current_value for f in scope.funds) or 1.0
    return [
        {
            "isin": f.isin,
            "fund_short_name": f.fund_short_name,
            "current_value": f.current_value,
            "portfolio_weight_pct": round(100.0 * f.current_value / total, 2),
        }
        for f in scope.funds
    ]


def _trim_snippet(text: str, limit: int) -> str:
    return trim_chars_at_word(text, limit)


def _normalize_title(title: str) -> str:
    return " ".join((title or "").lower().split())


def _day_key(published_at: str) -> str:
    return (published_at or "")[:10]


def _title_similar(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.72


def cluster_articles(articles: list[dict]) -> list[list[dict]]:
    clusters: list[list[dict]] = []
    used: set[int] = set()
    for index, article in enumerate(articles):
        if index in used:
            continue
        cluster = [article]
        used.add(index)
        title_a = _normalize_title(str(article.get("title") or ""))
        day_a = _day_key(str(article.get("published_at") or ""))
        ents_a = {str(n).lower() for n in (article.get("entity_names") or [])}
        for other_index, other in enumerate(articles):
            if other_index in used:
                continue
            if _day_key(str(other.get("published_at") or "")) != day_a:
                continue
            ents_b = {str(n).lower() for n in (other.get("entity_names") or [])}
            if ents_a and ents_b and not (ents_a & ents_b):
                continue
            title_b = _normalize_title(str(other.get("title") or ""))
            if _title_similar(title_a, title_b):
                cluster.append(other)
                used.add(other_index)
        clusters.append(cluster)
    return clusters


def _article_entities(row: dict) -> set[str]:
    names: set[str] = set()
    for key in ("entity_names", "holding_names"):
        for name in row.get(key) or []:
            if name:
                names.add(str(name).lower())
    industry = row.get("primary_industry")
    if industry:
        names.add(str(industry).lower())
    return names


def _pack_article(row: dict, settings: Settings, *, vector_score: float) -> dict | None:
    if row.get("event_type") == "price_recap":
        return None
    url = str(row.get("url") or "")
    if not url:
        return None
    return {
        "url": url,
        "title": row.get("title"),
        "source": row.get("source"),
        "published_at": row.get("published_at"),
        "entity_names": row.get("entity_names") or [],
        "primary_industry": row.get("primary_industry") or "",
        "max_impact": int(row.get("max_impact") or 0),
        "max_relevance": int(row.get("max_relevance") or 0),
        "direction": row.get("direction") or "",
        "event_type": row.get("event_type") or "",
        "snippet": _trim_snippet(str(row.get("scraped_text") or row.get("snippet") or ""), settings.snippet_chars),
        "_vector_score": vector_score,
    }


def fund_search_query(scope: PortfolioScope, isin: str, name_map: dict[str, str]) -> str:
    holdings_raw = sorted(
        scope.holdings_for_isin(isin),
        key=lambda holding: holding.by_fund.get(isin, 0),
        reverse=True,
    )
    # Ensure diverse holdings selection across distinct industries
    seen_industries: set[str] = set()
    diverse_holdings = []
    other_holdings = []
    for h in holdings_raw:
        ind = (h.industry or "").strip().casefold()
        if ind and ind not in seen_industries:
            seen_industries.add(ind)
            diverse_holdings.append(h)
        else:
            other_holdings.append(h)

    selected_holdings = (diverse_holdings + other_holdings)[:10]

    sectors = sorted(
        scope.sectors_for_isin(isin),
        key=lambda sector: sector.by_fund.get(isin, 0),
        reverse=True,
    )[:6]
    names = [name_map.get(holding.instrument_name, holding.instrument_name) for holding in selected_holdings]
    names.extend(sector.canonical_name for sector in sectors)
    if not names:
        return "material company and sector news"
    return ", ".join(names) + ". Material company, sector, and industry developments."



def retrieve_fund_articles(
    settings: Settings,
    filter_names: list[str],
    *,
    query_text: str,
    window_days: int | None = None,
    query_log: QueryLogger | None = None,
) -> tuple[str, list[dict]]:
    days = window_days if window_days is not None else settings.default_window_days
    published_from, published_to, window_label = parse_time_window(
        "",
        date_from=None,
        date_to=to_iso(utc_now()),
        default_days=days,
    )
    filter_kwargs = {
        "entity_names": filter_names or None,
        "published_from": published_from,
        "published_to": published_to,
        "min_relevance": settings.min_relevance,
    }
    filt = build_filter(**filter_kwargs)
    post_filter_meta = {
        "retrieve_vector_limit": settings.retrieve_vector_limit,
        "retrieve_impact_limit": settings.retrieve_impact_limit,
        "collection": settings.qdrant_collection,
    }
    if query_log is not None:
        query_log.write(
            "fund_retrieval "
            + f"window_label={json.dumps(window_label)} "
            + f"query_text={clip_log_text(query_text, 500)} "
            + f"filter_name_count={len(filter_names)}"
        )
        spec = filter_spec(**filter_kwargs)
        query_log.log_filters(spec, post_filters=post_filter_meta)
        query_log.log_filters_applied(
            describe_filters_for_log(
                spec,
                collection=settings.qdrant_collection,
                post_filters=post_filter_meta,
            )
        )
    reader = QdrantReader()
    vector_rows: list[dict] = []
    if query_text.strip() and filter_names:
        t_embed = time.perf_counter()
        vector = embed_query(query_text)
        if query_log is not None:
            query_log.log_step("embed_query", time.perf_counter() - t_embed, vector_dim=len(vector))
        t_vec = time.perf_counter()
        vector_rows = reader.query_vector(vector, filt, settings.retrieve_vector_limit)
        if query_log is not None:
            query_log.log_step(
                "qdrant_query_vector",
                time.perf_counter() - t_vec,
                hits=len(vector_rows),
                limit=settings.retrieve_vector_limit,
            )
            query_log.log_articles_block("qdrant_vector", vector_rows)
    elif query_log is not None:
        query_log.write("qdrant_query_vector skipped=true reason=empty_query_or_filter_names")
    t_scroll = time.perf_counter()
    impact_rows = reader.scroll_filtered(filt, settings.retrieve_impact_limit)
    if query_log is not None:
        query_log.log_step(
            "qdrant_scroll_filtered",
            time.perf_counter() - t_scroll,
            hits=len(impact_rows),
            limit=settings.retrieve_impact_limit,
        )
        query_log.log_articles_block("qdrant_scroll", impact_rows)

    # Calculate Reciprocal Rank Fusion (RRF) scores
    k = 60.0
    rrf_scores: dict[str, float] = {}
    by_url: dict[str, dict] = {}

    for rank, row in enumerate(vector_rows):
        packed = _pack_article(row, settings, vector_score=float(row.get("score") or 0.0))
        if packed is None:
            continue
        url = packed["url"]
        rrf_scores[url] = rrf_scores.get(url, 0.0) + (1.0 / (k + rank + 1))
        by_url[url] = packed

    for rank, row in enumerate(impact_rows):
        packed = _pack_article(row, settings, vector_score=0.0)
        if packed is None:
            continue
        url = packed["url"]
        rrf_scores[url] = rrf_scores.get(url, 0.0) + (1.0 / (k + rank + 1))
        existing = by_url.get(url)
        if existing is None:
            by_url[url] = packed
            continue
        existing["max_impact"] = max(existing["max_impact"], packed["max_impact"])
        if not existing.get("snippet"):
            existing["snippet"] = packed["snippet"]

    if query_log is not None:
        query_log.write(f"merge unique_urls={len(by_url)} rrf_candidates={len(rrf_scores)}")

    articles = list(by_url.values())
    for item in articles:
        item["_rrf_score"] = rrf_scores.get(item["url"], 0.0) + (0.01 * item["max_impact"])

    articles.sort(
        key=lambda item: (item.get("_rrf_score") or 0.0, item["max_impact"], item.get("published_at") or ""),
        reverse=True,
    )
    if query_log is not None:
        query_log.log_articles_block("fund_merged", articles, snippet_limit=settings.snippet_chars)
    return window_label, articles


def _fund_by_isin(scope: PortfolioScope, isin: str):
    for fund in scope.funds:
        if fund.isin == isin:
            return fund
    return None


def _exposure_for_holding(
    scope: PortfolioScope,
    isin: str,
    holding,
    *,
    fund_only: bool,
) -> tuple[float, float, str] | None:
    if fund_only:
        pct = holding.by_fund.get(isin)
        fund = _fund_by_isin(scope, isin)
        if pct is None or fund is None:
            return None
        return pct, fund.current_value * pct / 100.0, fund.fund_short_name

    best_pct = 0.0
    rupees = 0.0
    labels: list[str] = []
    for fund in scope.funds:
        if fund.isin == isin:
            continue
        pct = holding.by_fund.get(fund.isin)
        if pct is None:
            continue
        rupees += fund.current_value * pct / 100.0
        labels.append(f"{fund.fund_short_name} {pct:.1f}%")
        if pct > best_pct:
            best_pct = pct
    if not labels:
        return None
    return best_pct, rupees, ", ".join(labels)


def _exposure_for_sector(
    scope: PortfolioScope,
    isin: str,
    sector,
    *,
    fund_only: bool,
) -> tuple[float, float, str] | None:
    if fund_only:
        pct = sector.by_fund.get(isin)
        fund = _fund_by_isin(scope, isin)
        if pct is None or fund is None:
            return None
        return pct, fund.current_value * pct / 100.0, fund.fund_short_name

    best_pct = 0.0
    rupees = 0.0
    labels: list[str] = []
    for fund in scope.funds:
        if fund.isin == isin:
            continue
        pct = sector.by_fund.get(fund.isin)
        if pct is None:
            continue
        rupees += fund.current_value * pct / 100.0
        labels.append(f"{fund.fund_short_name} {pct:.1f}%")
        if pct > best_pct:
            best_pct = pct
    if not labels:
        return None
    return best_pct, rupees, ", ".join(labels)


def _quiet_holdings(
    scope: PortfolioScope,
    isin: str,
    articles: list[dict],
    name_map: dict[str, str],
) -> list[str]:
    covered = _article_entities({"entity_names": []})
    for row in articles:
        covered |= _article_entities(row)
    quiet: list[str] = []
    for holding in scope.holdings_for_isin(isin):
        qname = name_map.get(holding.instrument_name, holding.instrument_name)
        if qname.lower() in covered:
            continue
        quiet.append(f"{holding.instrument_name} ({holding.by_fund[isin]:.1f}% of this fund)")
    def _quiet_sort_key(line: str) -> float:
        match = re.search(r"\(([\d.]+)%", line)
        return float(match.group(1)) if match else 0.0

    quiet.sort(key=_quiet_sort_key, reverse=True)
    return quiet[:8]


def _cluster_entities(cluster: list[dict]) -> set[str]:
    names: set[str] = set()
    for row in cluster:
        names |= _article_entities(row)
    return names


def _lead_article(cluster: list[dict]) -> dict:
    return max(
        cluster,
        key=lambda row: (int(row.get("max_impact") or 0), float(row.get("_vector_score") or 0)),
    )


def build_events(
    articles: list[dict],
    *,
    scope: PortfolioScope,
    isin: str,
    name_map: dict[str, str],
    fund_only: bool,
    limit: int,
) -> list[dict]:
    clusters = cluster_articles(articles)
    events: list[dict] = []
    for cluster in clusters:
        ents = _cluster_entities(cluster)
        lead = _lead_article(cluster)
        matched_industries: set[str] = set()
        attachments: list[dict] = []

        for holding in scope.holdings:
            qname = name_map.get(holding.instrument_name, holding.instrument_name)
            if qname.lower() not in ents:
                continue
            exposure = _exposure_for_holding(scope, isin, holding, fund_only=fund_only)
            if exposure is None:
                continue
            pct, rupees, where = exposure
            if holding.industry:
                matched_industries.add(holding.industry.lower())
            attachments.append(
                {
                    "label": qname,
                    "kind_name": "holding",
                    "weight_pct": round(pct, 2),
                    "rupees": round(rupees, 2),
                    "where": where,
                }
            )

        for sector in scope.sectors:
            if sector.canonical_name.lower() not in ents:
                continue
            if sector.canonical_name.lower() in matched_industries:
                continue
            exposure = _exposure_for_sector(scope, isin, sector, fund_only=fund_only)
            if exposure is None:
                continue
            pct, rupees, where = exposure
            attachments.append(
                {
                    "label": sector.canonical_name,
                    "kind_name": "sector",
                    "weight_pct": round(pct, 2),
                    "rupees": round(rupees, 2),
                    "where": where,
                }
            )

        if not attachments:
            continue
        attachments.sort(key=lambda item: item["rupees"], reverse=True)
        top = attachments[0]
        directions = {str(row.get("direction") or "") for row in cluster}
        signed = {name for name in directions if name in ("positive", "negative")}
        event_type = str(lead.get("event_type") or "")
        events.append(
            {
                "label": top["label"],
                "match_type": top["kind_name"],
                "weight_pct": top["weight_pct"],
                "rupees": top["rupees"],
                "where": top["where"],
                "direction": str(lead.get("direction") or ""),
                "mixed": len(signed) > 1,
                "event_type": event_type,
                "kind": "fact" if event_type in FACT_TYPES else "opinion",
                "max_impact": int(lead.get("max_impact") or 0),
                "vector_score": float(lead.get("_vector_score") or 0),
                "title": lead.get("title") or "",
                "snippet": lead.get("snippet") or "",
                "url": lead.get("url") or "",
                "source": lead.get("source") or "",
                "published_at": lead.get("published_at") or "",
            }
        )

    # DIVERSE EVENT SELECTION:
    # 1. Sort all candidate events by portfolio-weighted impact, exposure rupees, and vector score.
    # 2. Pick the BEST event per unique entity (label) first so that one company/sector does not crowd out others.
    # 3. Then fill any remaining capacity up to `limit` with distinct event titles.
    events.sort(
        key=lambda item: (
            float(item.get("weight_pct") or 0.0) * (int(item.get("max_impact") or 0) + 1),
            int(item.get("max_impact") or 0),
            float(item.get("rupees") or 0.0),
            float(item.get("vector_score") or 0.0),
        ),
        reverse=True,
    )

    unique_events: list[dict] = []
    seen_labels: set[str] = set()
    for ev in events:
        lbl = ev["label"].casefold()
        if lbl not in seen_labels:
            seen_labels.add(lbl)
            unique_events.append(ev)
            if len(unique_events) >= limit:
                break

    if len(unique_events) < limit:
        seen_titles = {e.get("title", "").strip().casefold() for e in unique_events}
        for ev in events:
            t = ev.get("title", "").strip().casefold()
            if t not in seen_titles:
                seen_titles.add(t)
                unique_events.append(ev)
                if len(unique_events) >= limit:
                    break

    return unique_events


def jev_filter_events(events: list[dict], *, query_log: QueryLogger | None = None) -> list[dict]:
    if not events:
        return events
    pipeline = PipelineSettings()
    if not (pipeline.jev_base_url or "").strip() or not (pipeline.jev_api_key or "").strip():
        if query_log is not None:
            query_log.write("jev_filter skipped=true reason=not_configured")
        return events
    questions: dict[str, dict] = {}
    for index, event in enumerate(events):
        label = event["label"]
        questions[f"e{index}"] = {
            "type": "noul",
            "instructions": (
                f"Title: {event['title']}. Excerpt: {event['snippet'][:500]}. "
                f"Is this story specifically about {label} and does it describe a meaningful, material event (earnings, contracts, regulatory/policy action, capex, structural change) that could affect the company's business or stock outlook? "
                "False for routine operational noise (e.g. banks open on Sunday, holiday timings, branch notices, minor customer service updates), price recaps, or passing mentions."
            ),
            "criteria": {
                "true": f"About {label} and materially impactful to business/financial outlook",
                "false": "Routine/temporary operational noise, unrelated, wrong company, or not material",
            },
        }
    try:
        t_jev = time.perf_counter()
        with JevClient(pipeline) as client:
            answers = client.evaluate({"events": len(events)}, questions, stage="fund_event_check")
    except (JevError, OSError, ValueError) as exc:
        if query_log is not None:
            query_log.write(f"jev_filter skipped=true reason=error message={exc!s}"[:500])
        return events
    kept = []
    for index, event in enumerate(events):
        answer = answers.get(f"e{index}")
        if answer is None or read_noul(answer) >= 0.5:
            kept.append(event)
    if query_log is not None:
        query_log.log_step(
            "jev_filter",
            time.perf_counter() - t_jev,
            input_events=len(events),
            kept_events=len(kept),
        )
    return kept


FUND_BRIEF_PROMPT = """You are a high-impact financial news and storytelling agent for an Indian mutual fund investor.

Your job is NOT to summarize every piece of news. Your job is to identify only news that can have a meaningful, material impact on the companies in this portfolio, and explain it in VERY SIMPLE, ENGAGING, MEANINGFUL STORYTELLING LANGUAGE that anyone (even a 15-year-old) can easily understand.

The output must deliver clear meaning and context:
What happened -> Why it matters -> How it affects the company's business -> What it means for the investor's fund.

GUIDELINES FOR WRITING:
1. MEANINGFUL INSIGHTS (NOT JUST DRY FACTS):
   - Ensure every insight delivers practical meaning. Do not just state that an event happened or repeat a number; explain *why it matters* for the company's profitability, competitive strength, or industry position.
2. DIVERSITY & ONE BULLET PER ENTITY:
   - Exactly ONE bullet point per distinct company or sector. Do NOT write multiple bullets about the same company or sector (e.g., maximum 1 bullet for HDFC Bank, 1 for Automobile sector, 1 for Tata Motors, 1 for Reliance, etc.).
   - Ensure broad, diverse coverage across different sectors in the portfolio (e.g., Automobile, IT, Energy, Healthcare, FMCG, Banking) rather than concentrating all bullets on a single sector.
3. ACRONYM & SHORT-FORM EXPANSIONS:
   - On first mention of ANY financial, regulatory, or technical acronym/abbreviation, provide its full name in parentheses (e.g. SEBI (Securities and Exchange Board of India), RBI (Reserve Bank of India), FPIs (Foreign Portfolio Investors), IPOs (Initial Public Offerings), NIM (Net Interest Margin), NPA (Non-Performing Asset), GST (Goods and Services Tax), EV (Electric Vehicle)).
4. STRICT MINIMAL HIGHLIGHTING (DO NOT OVER-HIGHLIGHT):
   - Highlight ONLY 1 or 2 most critical anchor terms per bullet (e.g. the primary company name or a key metric like **₹5,000 crore** or **+15%**).
   - Keep the summary to at most 3 or 4 total bold highlights across the entire paragraph.
   - DO NOT bold common words, verbs, adjectives, regulatory bodies, acronym expansions, or general business terms (e.g., do NOT bold "approved", "growth", "demand", "framework", "investments", "market", "policy").
5. SIMPLE LANGUAGE:
   - Use plain everyday conversational English. Avoid dry financial jargon.
   - Replace complex terms with simple meanings (e.g. instead of "compressing NIMs", say "putting pressure on lending profits"; instead of "input-cost inflation", say "materials becoming more expensive"; instead of "margin expansion", say "making more profit on each sale"; instead of "regulatory headwinds", say "tougher government rules").
6. CAUSAL CONNECTION & REJECT TRIVIA:
   - Connect the event to the business mechanism and investor impact.
   - Reject temporary/operational noise (such as "banks open on Sunday" or holiday notices).
7. NO BUY/SELL ADVICE:
   - Provide factual context and business implications only.

Write exactly this structure (plain text):

BULLETS:
- Between 5 and 8 bullet lines (no fewer than 5 if enough distinct events exist). Each line starts with "- ".
- Exactly ONE bullet per distinct company or sector (cross-portfolio diversity across Auto, IT, Energy, FMCG, Banking, etc.).
- Each bullet is ONE clear, easy-to-read sentence connecting a concrete event from the excerpts to why it matters for this fund holding or sector (include portfolio weight/rupee exposure if provided).
- Use **bold** sparingly for only 1–2 most critical anchor terms (e.g. company name or major metric). Include acronym full forms in parentheses without bolding them.

SUMMARY:
One cohesive storytelling paragraph of about 90–120 words (4–6 sentences).
Tell the story of what is happening across the portfolio:
- Start with the big picture (the major national, regulatory, or economic theme).
- Explain how key companies across different sectors in the fund are affected (the causal business mechanism and what it means for growth or risk).
- Conclude with what this means for the investor's book.
Write in a smooth narrative flow delivering real meaning with only 3–4 selective **bold** highlights. No bullet characters. No buy/sell advice.
"""


def _format_event_block(event: dict, *, section: str) -> str:
    direction = "mixed" if event.get("mixed") else event.get("direction") or ""
    return (
        f"[{section}] label={event.get('label')} match={event.get('match_type')} "
        f"weight_pct={event.get('weight_pct')} rupees={event.get('rupees')} "
        f"where={event.get('where')} direction={direction} event_type={event.get('event_type')}\n"
        f"title={event.get('title')}\n"
        f"excerpt={event.get('snippet')}"
    )


def _sources_from_events(events: list[dict]) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    for event in events:
        url = str(event.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        rows.append(
            {
                "title": event.get("title"),
                "url": url,
                "source": event.get("source"),
                "published_at": event.get("published_at"),
            }
        )
    return rows


def _fallback_bullets_from_events(events: list[dict], *, max_count: int) -> list[str]:
    bullets: list[str] = []
    for event in events:
        label = str(event.get("label") or "").strip()
        title = str(event.get("title") or "").strip()
        snippet = _trim_snippet(str(event.get("snippet") or ""), 160)
        weight = event.get("weight_pct")
        where = str(event.get("where") or "").strip()
        bit = title
        if snippet and snippet.lower() not in title.lower():
            bit = f"{title} — {snippet}"
        if label:
            exposure = f" ({label}"
            if weight is not None:
                exposure += f", {weight}% in {where}" if where else f", {weight}%"
            exposure += ")"
            bit = bit.rstrip(".") + exposure + "."
        if bit:
            bullets.append(bit)
        if len(bullets) >= max_count:
            break
    return bullets


def _fallback_summary(fund_name: str, window: str, bullets: list[str]) -> str:
    if not bullets:
        return (
            f"No material news matched {fund_name} and the rest of the portfolio in {window}."
        )
    lead = bullets[0].rstrip(".")
    return (
        f"Over {window}, stored news mostly affects {fund_name} and your other funds through "
        f"the themes above. {lead}. "
        f"Together these items highlight where your largest weights saw headlines; "
        f"this is factual context only, not investment advice."
    )


def compose_fund_insight(
    *,
    fund_short_name: str,
    window_label: str,
    fund_events: list[dict],
    portfolio_events: list[dict],
    settings: Settings,
    query_log: QueryLogger | None = None,
) -> tuple[list[str], str, str, list[dict]]:
    """Returns bullets, summary, insight_source, sources."""
    all_events = fund_events + portfolio_events
    sources = _sources_from_events(all_events)
    if not all_events:
        return [], "", "no_articles", sources

    if not llm_api_key_configured(settings):
        raise RuntimeError(missing_llm_key_message())

    fund_blocks = [_format_event_block(event, section="this_fund") for event in fund_events]
    portfolio_blocks = [_format_event_block(event, section="other_funds") for event in portfolio_events]
    user_content = (
        f"Selected fund: {fund_short_name}\n"
        f"Time window: {window_label}\n\n"
        f"This fund events ({len(fund_blocks)}):\n"
        + ("\n\n".join(fund_blocks) if fund_blocks else "(none)\n")
        + f"\n\nOther funds in portfolio ({len(portfolio_blocks)}):\n"
        + ("\n\n".join(portfolio_blocks) if portfolio_blocks else "(none)\n")
    )

    result = call_insight_llm(
        system_prompt=FUND_BRIEF_PROMPT,
        user_content=user_content,
        query_log=query_log,
    )
    if query_log is not None:
        query_log.record_llm_call(
            provider=result.provider,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            duration_sec=result.duration_sec,
            http_status=result.http_status,
        )
        query_log.write(f"llm raw_preview text={clip_log_text(result.raw_text, 500)}")

    bullets, summary = parse_structured_insight(result.raw_text)
    insight_source = result.provider

    if not bullets and not summary:
        bullets = _fallback_bullets_from_events(all_events, max_count=FUND_BRIEF_MAX_BULLETS)
        summary = _fallback_summary(fund_short_name, window_label, bullets)
        insight_source = "events_fallback"
        if query_log is not None:
            query_log.write("insight llm_empty=true reason=empty_llm_content")
    elif not summary and bullets:
        summary = _fallback_summary(fund_short_name, window_label, bullets)

    bullets = clamp_bullets(
        bullets,
        max_count=FUND_BRIEF_MAX_BULLETS,
        max_chars=FUND_BRIEF_BULLET_MAX_CHARS,
    )
    summary = clamp_summary(summary, max_words=FUND_BRIEF_SUMMARY_MAX_WORDS)

    if query_log is not None:
        display = format_insight_display(bullets, summary)
        query_log.log_insight_output(
            insight_source=insight_source,
            char_count=len(display),
            preview=display,
        )
        query_log.write(f"insight_bullets_count={len(bullets)} summary_words={len(summary.split())}")

    return bullets, summary, insight_source, sources


def _empty_brief(fund, isin: str, window_label: str, quiet: list[str]) -> dict[str, Any]:
    msg = (
        f"No matching news was found for {window_label} "
        f"for holdings and sectors at or above {HOLDING_MIN_PCT:g}% / {SECTOR_MIN_PCT:g}%."
    )
    return {
        "fund_short_name": fund.fund_short_name,
        "isin": isin,
        "window": window_label,
        "insight_bullets": [],
        "insight_summary": msg,
        "insight": msg,
        "sources": [],
        "quiet_holdings": quiet,
        "insight_source": "no_articles",
    }


def generate_fund_brief(
    isin: str,
    settings: Settings | None = None,
    *,
    query_log: QueryLogger | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    scope = load_scope_for_fund(isin, settings)
    fund = scope.funds[0]
    name_map = instrument_to_qdrant_names(scope)
    filter_names = qdrant_filter_names(scope)
    query_text = fund_search_query(scope, isin, name_map)
    if query_log is not None:
        query_log.write(
            f"fund_context isin={isin} fund_short_name={json.dumps(fund.fund_short_name)} "
            f"filter_name_count={len(filter_names)}"
        )
    window_label, articles = retrieve_fund_articles(
        settings,
        filter_names,
        query_text=query_text,
        query_log=query_log,
    )
    quiet = _quiet_holdings(scope, isin, articles, name_map)
    if query_log is not None:
        query_log.write(f"quiet_holdings count={len(quiet)} names={json.dumps(quiet[:20], ensure_ascii=False)}")
    if not articles:
        return _empty_brief(fund, isin, window_label, quiet)

    limit = settings.retrieve_max_articles
    fund_events = build_events(
        articles,
        scope=scope,
        isin=isin,
        name_map=name_map,
        fund_only=True,
        limit=limit,
    )
    portfolio_events = build_events(
        articles,
        scope=scope,
        isin=isin,
        name_map=name_map,
        fund_only=False,
        limit=limit,
    )
    if query_log is not None:
        query_log.write(
            f"events_built fund_events={len(fund_events)} portfolio_events={len(portfolio_events)} limit={limit}"
        )
    combined = fund_events + portfolio_events
    kept = jev_filter_events(combined, query_log=query_log)
    kept_ids = {id(event) for event in kept}
    fund_events = [event for event in fund_events if id(event) in kept_ids]
    portfolio_events = [event for event in portfolio_events if id(event) in kept_ids]
    if query_log is not None:
        query_log.write(
            f"events_after_jev fund_events={len(fund_events)} portfolio_events={len(portfolio_events)}"
        )
    if not fund_events and not portfolio_events:
        return _empty_brief(
            fund,
            isin,
            window_label,
            quiet,
        )

    bullets, summary, insight_source, sources = compose_fund_insight(
        fund_short_name=fund.fund_short_name,
        window_label=window_label,
        fund_events=fund_events,
        portfolio_events=portfolio_events,
        settings=settings,
        query_log=query_log,
    )
    display = format_insight_display(bullets, summary)
    return {
        "fund_short_name": fund.fund_short_name,
        "isin": isin,
        "window": window_label,
        "insight_bullets": bullets,
        "insight_summary": summary,
        "insight": display,
        "sources": sources,
        "quiet_holdings": quiet,
        "insight_source": insight_source,
    }
