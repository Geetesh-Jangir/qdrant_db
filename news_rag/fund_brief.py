"""Fund-level and portfolio-level brief from stored news (read-only Qdrant)."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from lib.portfolio_scope import (
    HOLDING_MIN_PCT,
    SECTOR_MIN_PCT,
    PortfolioScope,
    build_portfolio_scope,
    instrument_to_qdrant_names,
    qdrant_filter_names,
    resolve_allisin_holdings_path,
)
from news_rag.config import Settings, get_settings
from news_rag.insight_format import clamp_bullets, clamp_summary, parse_structured_insight
from news_rag.llm_client import call_insight_llm, llm_api_key_configured, missing_llm_key_message
from news_rag.parse import parse_time_window, to_iso, utc_now
from news_rag.qdrant_reader import QdrantReader, build_filter


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
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


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


def retrieve_fund_articles(
    settings: Settings,
    filter_names: list[str],
    *,
    window_days: int | None = None,
) -> tuple[str, list[dict]]:
    days = window_days if window_days is not None else settings.default_window_days
    published_from, published_to, window_label = parse_time_window(
        "",
        date_from=None,
        date_to=to_iso(utc_now()),
        default_days=days,
    )
    filt = build_filter(
        entity_names=filter_names or None,
        published_from=published_from,
        published_to=published_to,
        min_relevance=settings.min_relevance,
    )
    reader = QdrantReader()
    rows = reader.scroll_filtered(filt, limit=120)
    by_url: dict[str, dict] = {}
    for row in rows:
        if row.get("event_type") == "price_recap":
            continue
        url = str(row.get("url") or "")
        if not url:
            continue
        by_url[url] = {
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
            "snippet": _trim_snippet(str(row.get("scraped_text") or ""), settings.snippet_chars),
        }
    articles = list(by_url.values())
    articles.sort(
        key=lambda item: (item["max_impact"], item.get("published_at") or ""),
        reverse=True,
    )
    return window_label, articles


def _weight_for_article(
    article: dict,
    *,
    isin: str,
    scope: PortfolioScope,
    name_map: dict[str, str],
    fund_only: bool,
) -> float:
    article_ents = _article_entities(article)
    weight = 0.0
    for holding in scope.holdings:
        qname = name_map.get(holding.instrument_name, holding.instrument_name)
        if qname.lower() not in article_ents and holding.industry.lower() not in article_ents:
            continue
        fund_pct = holding.by_fund.get(isin)
        if fund_only:
            if fund_pct is None:
                continue
            weight = max(weight, fund_pct * (1 + 0.2 * article.get("max_impact", 0)))
        else:
            other_pct = 0.0
            for other_isin, pct in holding.by_fund.items():
                if other_isin == isin:
                    continue
                other_pct = max(other_pct, pct)
            if other_pct:
                weight = max(weight, other_pct * (1 + 0.2 * article.get("max_impact", 0)))

    for sector in scope.sectors:
        if sector.canonical_name.lower() not in article_ents:
            continue
        fund_pct = sector.by_fund.get(isin)
        if fund_only:
            if fund_pct is None:
                continue
            weight = max(weight, fund_pct * (1 + 0.15 * article.get("max_impact", 0)))
        else:
            other_pct = 0.0
            for other_isin, pct in sector.by_fund.items():
                if other_isin == isin:
                    continue
                other_pct = max(other_pct, pct)
            if other_pct:
                weight = max(weight, other_pct * (1 + 0.15 * article.get("max_impact", 0)))
    return weight


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


def _format_context_block(clusters: list[list[dict]], limit: int) -> str:
    blocks: list[str] = []
    count = 0
    for cluster in clusters:
        lead = cluster[0]
        count += 1
        extra = ""
        if len(cluster) > 1:
            extra = f" (also reported by {len(cluster) - 1} similar story/stories)"
        blocks.append(
            f"[{count}] title={lead.get('title')!r}{extra}\n"
            f"    source={lead.get('source')} published={lead.get('published_at')}\n"
            f"    direction={lead.get('direction')} event={lead.get('event_type')} "
            f"impact={lead.get('max_impact')} entities={lead.get('entity_names')}\n"
            f"    text={lead.get('snippet')!r}"
        )
        if count >= limit:
            break
    return "\n\n".join(blocks)


def _build_exposure_lines(
    scope: PortfolioScope,
    isin: str,
    name_map: dict[str, str],
    *,
    fund_only: bool,
) -> str:
    lines: list[str] = []
    fund = next((f for f in scope.funds if f.isin == isin), None)
    fund_label = fund.fund_short_name if fund else isin
    for holding in scope.holdings:
        qname = name_map.get(holding.instrument_name, holding.instrument_name)
        if fund_only:
            pct = holding.by_fund.get(isin)
            if pct is None:
                continue
            lines.append(f"- {qname}: {pct:.2f}% of {fund_label}")
        else:
            parts = []
            for other in scope.funds:
                if other.isin == isin:
                    continue
                pct = holding.by_fund.get(other.isin)
                if pct is not None:
                    parts.append(f"{other.fund_short_name} {pct:.2f}%")
            if parts:
                lines.append(f"- {qname}: also held in " + ", ".join(parts))
    for sector in scope.sectors:
        if fund_only:
            pct = sector.by_fund.get(isin)
            if pct is None:
                continue
            lines.append(f"- Sector {sector.canonical_name}: {pct:.2f}% of {fund_label}")
        else:
            parts = []
            for other in scope.funds:
                if other.isin == isin:
                    continue
                pct = sector.by_fund.get(other.isin)
                if pct is not None:
                    parts.append(f"{other.fund_short_name} {pct:.2f}%")
            if parts:
                lines.append(f"- Sector {sector.canonical_name}: " + ", ".join(parts))
    return "\n".join(lines[:40])


SYSTEM_PROMPT = """You help Indian mutual fund investors understand recent news in plain, simple English.

You receive exposure weights and numbered news excerpts. Use ONLY facts from those excerpts.

Write exactly this structure (plain text):

THIS_FUND_BULLETS:
- 2 or 3 bullets. Each starts with "- ". One sentence each. Name the holding or sector, its weight in THIS fund, and one concrete fact from the excerpt. No buy/sell advice.

THIS_FUND_SUMMARY:
One short paragraph (about 40-55 words) about what matters for THIS fund only.

REST_PORTFOLIO_BULLETS:
- 2 or 3 bullets about the OTHER funds in the book (not the selected fund). Mention which other fund is exposed and one fact from the excerpts.

REST_PORTFOLIO_SUMMARY:
One short paragraph (about 40-55 words) about the rest of the portfolio.

Rules:
- Do not invent companies, numbers, or events.
- If excerpts are thin, say news was limited; do not guess.
- Do not copy headlines without adding a fact from the text= field.
- No URLs in the prose.
"""


def _section_text(raw: str, label: str) -> str:
    pattern = re.compile(
        rf"(?mi)^{re.escape(label)}:\s*\n(.*?)(?=^(?:THIS_FUND_BULLETS|THIS_FUND_SUMMARY|REST_PORTFOLIO_BULLETS|REST_PORTFOLIO_SUMMARY):|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(raw or "")
    return match.group(1).strip() if match else ""


def _bullets_from_block(block: str) -> list[str]:
    bullets: list[str] = []
    for line in block.splitlines():
        cleaned = line.strip()
        if cleaned.startswith("- "):
            bullets.append(cleaned[2:].strip())
    return bullets


def _parse_dual_insight(raw: str) -> dict[str, Any]:
    fund_bullets_body = _section_text(raw, "THIS_FUND_BULLETS")
    fund_summary_body = _section_text(raw, "THIS_FUND_SUMMARY")
    port_bullets_body = _section_text(raw, "REST_PORTFOLIO_BULLETS")
    port_summary_body = _section_text(raw, "REST_PORTFOLIO_SUMMARY")

    fund_bullets = _bullets_from_block(fund_bullets_body)
    port_bullets = _bullets_from_block(port_bullets_body)
    if not fund_bullets and fund_bullets_body:
        fund_bullets, fund_summary_body = parse_structured_insight(
            f"BULLETS:\n{fund_bullets_body}\nSUMMARY:\n{fund_summary_body}"
        )
    if not port_bullets and port_bullets_body:
        port_bullets, port_summary_body = parse_structured_insight(
            f"BULLETS:\n{port_bullets_body}\nSUMMARY:\n{port_summary_body}"
        )

    return {
        "fund_bullets": fund_bullets,
        "fund_summary": " ".join(fund_summary_body.split()),
        "portfolio_bullets": port_bullets,
        "portfolio_summary": " ".join(port_summary_body.split()),
    }


def generate_fund_brief(isin: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    scope = load_scope(settings)
    allowed_isins = {f.isin for f in scope.funds}
    if isin not in allowed_isins:
        raise ValueError(f"ISIN {isin} is not in the configured portfolio")

    fund = next(f for f in scope.funds if f.isin == isin)
    name_map = instrument_to_qdrant_names(scope)
    filter_names = qdrant_filter_names(scope)
    window_label, articles = retrieve_fund_articles(settings, filter_names)

    quiet = _quiet_holdings(scope, isin, articles, name_map)

    if not articles:
        msg = (
            f"No matching news was found in the last {settings.default_window_days} days "
            f"for holdings and sectors at or above {HOLDING_MIN_PCT:g}% / {SECTOR_MIN_PCT:g}%."
        )
        return {
            "fund_short_name": fund.fund_short_name,
            "isin": isin,
            "window": window_label,
            "fund_bullets": [],
            "fund_summary": msg,
            "portfolio_bullets": [],
            "portfolio_summary": msg,
            "quiet_holdings": quiet,
            "sources": [],
            "insight_source": "no_articles",
        }

    ranked = sorted(
        articles,
        key=lambda row: _weight_for_article(
            row, isin=isin, scope=scope, name_map=name_map, fund_only=True
        ),
        reverse=True,
    )
    clusters = cluster_articles(ranked)
    top_clusters = sorted(
        clusters,
        key=lambda cluster: _weight_for_article(
            cluster[0], isin=isin, scope=scope, name_map=name_map, fund_only=True
        ),
        reverse=True,
    )[: settings.retrieve_max_articles]

    sources: list[dict] = []
    seen_urls: set[str] = set()
    for cluster in top_clusters:
        for row in cluster:
            url = str(row.get("url") or "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            sources.append(
                {
                    "url": url,
                    "title": row.get("title"),
                    "source": row.get("source"),
                    "published_at": row.get("published_at"),
                }
            )

    if not llm_api_key_configured(settings):
        raise RuntimeError(missing_llm_key_message())

    user_content = (
        f"Selected fund: {fund.fund_short_name} (ISIN {isin})\n"
        f"Time window: {window_label}\n\n"
        f"THIS FUND exposure (holdings >= {settings.portfolio_holding_min_pct:g}%%, "
        f"sectors >= {settings.portfolio_sector_min_pct:g}%%):\n"
        f"{_build_exposure_lines(scope, isin, name_map, fund_only=True)}\n\n"
        f"REST OF PORTFOLIO exposure (other funds only):\n"
        f"{_build_exposure_lines(scope, isin, name_map, fund_only=False)}\n\n"
        f"News excerpts:\n{_format_context_block(top_clusters, settings.retrieve_max_articles)}\n"
    )

    llm_result = call_insight_llm(system_prompt=SYSTEM_PROMPT, user_content=user_content)
    parsed = _parse_dual_insight(llm_result.raw_text)
    settings_ref = settings
    fund_bullets = clamp_bullets(
        parsed["fund_bullets"],
        max_count=settings_ref.insight_max_bullets,
        max_chars=settings_ref.insight_bullet_max_chars,
    )
    port_bullets = clamp_bullets(
        parsed["portfolio_bullets"],
        max_count=settings_ref.insight_max_bullets,
        max_chars=settings_ref.insight_bullet_max_chars,
    )
    fund_summary = clamp_summary(parsed["fund_summary"], max_words=settings_ref.insight_summary_max_words)
    port_summary = clamp_summary(parsed["portfolio_summary"], max_words=settings_ref.insight_summary_max_words)

    return {
        "fund_short_name": fund.fund_short_name,
        "isin": isin,
        "window": window_label,
        "fund_bullets": fund_bullets,
        "fund_summary": fund_summary,
        "portfolio_bullets": port_bullets,
        "portfolio_summary": port_summary,
        "quiet_holdings": quiet,
        "sources": sources[:12],
        "insight_source": "llm",
        "llm_provider": llm_result.provider,
        "llm_model": llm_result.model,
    }
