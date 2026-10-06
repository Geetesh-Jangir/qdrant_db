"""Live price snapshots for fund top holdings, aligned with the news retrieval window."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, TYPE_CHECKING

from historical_data.stocks_service import get_stock_profile

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger


def holdings_top_n_from_question(question: str, default: int = 3) -> int:
    q = question or ""
    m = re.search(r"\btop\s*(\d+)\b", q, re.I)
    if m:
        try:
            return max(1, min(int(m.group(1)), 10))
        except ValueError:
            pass
    if re.search(r"\btop\s+three\b", q, re.I):
        return 3
    return default


def question_wants_holdings_performance(question: str) -> bool:
    lower = (question or "").lower()
    if not lower:
        return False
    patterns = (
        r"\bholdings?\b",
        r"\btop\s*\d+\s+hold",
        r"\bhow\b.+\bworking\b",
        r"\bperforming\b",
        r"\bstock(s)?\s+in\s+(the\s+)?fund\b",
        r"\bportfolio\s+composition\b",
    )
    return any(re.search(p, lower) for p in patterns)


def _holding_match_aliases(h_name: str) -> tuple[str, list[str], list[str]]:
    """Return (core label, required phrases, forbidden substrings for false positives)."""
    h_low = h_name.lower().strip()
    forbidden: list[str] = []
    if "icici bank" in h_low:
        forbidden = ["prudential", "mutual fund", "amc ", "asset management"]
    elif "hdfc bank" in h_low:
        forbidden = ["hdfc life", "hdfc amc", "mutual fund", "asset management"]
    elif "reliance industries" in h_low:
        forbidden = ["reliance capital", "mutual fund"]
    core = re.sub(r"\s+(limited|ltd\.?)$", "", h_low, flags=re.I).strip()
    return core, [core], forbidden


def _article_mentions_holding(h_name: str, article: dict[str, Any]) -> bool:
    if not h_name:
        return False
    core, phrases, forbidden = _holding_match_aliases(h_name)
    blob = " ".join(
        [
            str(article.get("title") or ""),
            str(article.get("snippet") or ""),
            " ".join(str(e) for e in (article.get("entity_names") or [])),
        ]
    ).lower()
    if any(f in blob for f in forbidden):
        return False
    if core in blob:
        return True
    # Shorter alias: first two words if distinctive (e.g. "power grid")
    parts = core.split()
    if len(parts) >= 2:
        short = " ".join(parts[:2])
        if len(short) >= 8 and short in blob:
            return True
    for e in article.get("entity_names") or []:
        el = str(e).lower()
        if any(f in el for f in forbidden):
            continue
        if core in el or el in core:
            return True
    return False


def _slim_article(a: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(a.get("title") or "")[:200],
        "snippet": str(a.get("snippet") or "")[:420],
        "direction": a.get("direction") or "unclear",
        "max_impact": a.get("max_impact"),
        "url": str(a.get("url") or ""),
        "published_at": a.get("published_at"),
    }


def _linked_articles_from_pool(
    h_name: str, articles: list[dict[str, Any]], *, limit: int = 5
) -> list[dict[str, Any]]:
    linked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for a in articles:
        if not _article_mentions_holding(h_name, a):
            continue
        url = str(a.get("url") or "").strip()
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        linked.append(_slim_article(a))
        if len(linked) >= limit:
            break
    return linked


def fetch_dedicated_holding_news(
    h_name: str,
    question: str,
    *,
    window_days: int = 30,
    query_log: QueryLogger | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Per-holding vector search when the merged pool has thin coverage."""
    from news_rag.news_entity_resolve import resolve_corpus_entity
    from news_rag.query_plan import ScopeRefinement
    from news_rag.scoped_retrieve import retrieve_scoped_news

    entity = resolve_corpus_entity(h_name)
    if not entity:
        entity = h_name
    scope = ScopeRefinement(news_entities=[entity], news_topics=[], search_mode="event_plus_entities")
    hits = retrieve_scoped_news(
        f"{entity} India stock earnings results management news why shares",
        scope=scope,
        question=question,
        window_days=window_days,
        query_log=query_log,
    )
    if not hits:
        scope = ScopeRefinement(search_mode="event_only", news_topics=[entity])
        hits = retrieve_scoped_news(
            f"{entity} India company shares decline rally reasons",
            scope=scope,
            question=question,
            window_days=window_days,
            query_log=query_log,
        )
    return [_slim_article(a) for a in (hits or [])[:limit]]


def _news_stats_for_holding(
    h_name: str, articles: list[dict[str, Any]], linked: list[dict[str, Any]]
) -> dict[str, Any]:
    pos = neg = neu = 0
    headlines: list[str] = []
    for a in linked:
        d = str(a.get("direction") or "neutral").lower()
        if d == "positive":
            pos += 1
        elif d == "negative":
            neg += 1
        else:
            neu += 1
        title = str(a.get("title") or "").strip()
        if title and len(headlines) < 4:
            headlines.append(title[:160])
    return {
        "positive": pos,
        "negative": neg,
        "neutral": neu,
        "total": len(linked),
        "sample_headlines": headlines,
        "linked_articles": linked,
    }


def _snapshot_one(
    row: dict[str, Any],
    articles: list[dict[str, Any]],
    window_days: int,
    *,
    question: str = "",
    query_log: QueryLogger | None = None,
    dedicated_news: bool = True,
) -> dict[str, Any]:
    name = str(row.get("name") or "").strip()
    try:
        weight = float(row.get("percentage") or 0.0)
    except (TypeError, ValueError):
        weight = 0.0
    industry = str(row.get("industry") or row.get("sector") or "").strip()
    linked = _linked_articles_from_pool(name, articles, limit=5)
    if dedicated_news and len(linked) < 2 and name:
        extra = fetch_dedicated_holding_news(
            name, question, window_days=window_days, query_log=query_log, limit=5
        )
        seen = {a.get("url") for a in linked if a.get("url")}
        for a in extra:
            u = a.get("url")
            if u and u in seen:
                continue
            if u:
                seen.add(u)
            linked.append(a)
            if len(linked) >= 5:
                break
    news = _news_stats_for_holding(name, articles, linked)
    profile = get_stock_profile(name) if name else None
    window_days = max(7, min(int(window_days or 30), 60))
    primary_window = "1w" if window_days <= 16 else "1m"

    out: dict[str, Any] = {
        "name": name,
        "weight_pct": round(weight, 2),
        "industry": industry,
        "news_window_days": window_days,
        "primary_return_window": primary_window,
        "news": news,
        "price": None,
    }
    if not profile:
        return out

    ret_1w = profile.get("return_1w")
    ret_1m = profile.get("return_1m")
    approx_1w = (float(ret_1w) * weight / 100.0) if ret_1w is not None else None
    approx_1m = (float(ret_1m) * weight / 100.0) if ret_1m is not None else None
    out["price"] = {
        "ticker": profile.get("ticker"),
        "cmp": profile.get("cmp"),
        "return_1d": profile.get("return_1d"),
        "return_1w": ret_1w,
        "return_1m": ret_1m,
        "range_30d": profile.get("range_30d"),
        "range_52w": profile.get("range_52w"),
        "approx_nav_contribution_1w_pct": round(approx_1w, 3) if approx_1w is not None else None,
        "approx_nav_contribution_1m_pct": round(approx_1m, 3) if approx_1m is not None else None,
    }
    return out


def build_holdings_market_snapshots(
    holdings_rows: list[dict[str, Any]],
    articles: list[dict[str, Any]],
    *,
    top_n: int = 3,
    window_days: int = 30,
    question: str = "",
    dedicated_news: bool = True,
    query_log: QueryLogger | None = None,
) -> list[dict[str, Any]]:
    """Fetch yfinance profiles for top holdings and attach corpus news stats for the same window."""
    if not holdings_rows:
        return []
    top_n = max(1, min(top_n, 8))
    rows = holdings_rows[:top_n]
    snapshots: list[dict[str, Any]] = [None] * len(rows)  # type: ignore[list-item]

    with ThreadPoolExecutor(max_workers=max(1, min(4, len(rows)))) as pool:
        futs = {
            pool.submit(
                _snapshot_one,
                row,
                articles,
                window_days,
                question=question,
                query_log=query_log,
                dedicated_news=dedicated_news,
            ): i
            for i, row in enumerate(rows)
        }
        for fut in as_completed(futs):
            idx = futs[fut]
            try:
                snapshots[idx] = fut.result()
            except Exception as exc:
                row = rows[idx]
                snapshots[idx] = {
                    "name": row.get("name"),
                    "weight_pct": row.get("percentage"),
                    "error": str(exc),
                }

    result = [s for s in snapshots if s]
    if query_log is not None and result:
        with_price = sum(1 for s in result if s.get("price"))
        with_news = sum(1 for s in result if (s.get("news") or {}).get("total"))
        query_log.write(
            f"HOLDINGS_MARKET top_n={top_n} window_days={window_days} "
            f"priced={with_price}/{len(result)} with_news={with_news}/{len(result)} "
            f"pool_articles={len(articles)}"
        )
    return result


def should_fetch_holdings_market(question: str, plan_tools: set[str], has_holdings: bool) -> bool:
    if not has_holdings:
        return False
    if question_wants_holdings_performance(question):
        return True
    if "holdings_news" in plan_tools:
        return True
    if ("fund_top_stocks" in plan_tools or "fund_holdings" in plan_tools) and (
        "holdings_news" in plan_tools
        or "sector_news" in plan_tools
        or "macro_news" in plan_tools
    ):
        return True
    return False


def news_window_days_from_plan(tools: list[Any], default: int = 30) -> int:
    for t in tools:
        name = getattr(t, "tool", None) or (t.get("tool") if isinstance(t, dict) else None)
        if name in ("holdings_news", "sector_news", "macro_news"):
            wd = getattr(t, "window_days", None) if not isinstance(t, dict) else t.get("window_days")
            if wd:
                try:
                    return int(wd)
                except (TypeError, ValueError):
                    pass
    return default
