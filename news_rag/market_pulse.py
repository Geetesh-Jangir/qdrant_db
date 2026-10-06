"""Broad 'market right now' retrieval: multi-macro search, cluster by theme, rank by coverage."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from news_rag.article_pool import article_dedupe_key
from news_rag.ask_plan import AskPlan
from news_rag.parse import infer_window_days_from_question
from news_rag.query_plan import ScopeRefinement

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

# Default lookback for "what's happening in the market now?" (no explicit "last N days" in question).
MARKET_PULSE_DEFAULT_WINDOW_DAYS = 30
MARKET_PULSE_RETRY_WINDOW_DAYS = 90
MARKET_PULSE_TOP_CLUSTERS = 8

_PULSE_THEME_LABELS: dict[str, str] = {
    "nifty": "Nifty & broader equity market",
    "nifty_banks": "Nifty Bank & lenders",
    "rates_liquidity": "RBI, repo rate & liquidity",
    "flows": "FII / DII flows",
    "crude_inflation": "Crude oil, rupee & inflation",
    "earnings": "Corporate earnings season",
    "banking": "Banking & credit",
    "global_risk": "Global risk & geopolitics",
}

# Parallel macro searches — always includes Nifty-focused queries.
MACRO_QUERY_SPECS: list[tuple[str, str]] = [
    ("Nifty 50 Sensex India equity markets today drivers", "nifty"),
    ("Nifty Bank index India markets RBI liquidity", "nifty_banks"),
    ("RBI repo rate rupee liquidity India financial markets", "rates_liquidity"),
    ("FII DII flows India stock market foreign investors", "flows"),
    ("crude oil rupee inflation India bond yields macro", "crude_inflation"),
    ("India earnings results corporate guidance stock market", "earnings"),
    ("India banking credit demand lenders asset quality", "banking"),
    ("global risk geopolitics impact India equity markets", "global_risk"),
]

_STOPWORDS = frozenset(
    {
        "india",
        "indian",
        "market",
        "markets",
        "stock",
        "stocks",
        "news",
        "today",
        "says",
        "said",
        "after",
        "with",
        "from",
        "that",
        "this",
        "will",
        "have",
        "been",
        "their",
        "about",
        "into",
        "over",
        "amid",
    }
)

CLUSTERED_MACRO_TOOL_NAMES = frozenset(
    {"common_market_news", "market_pulse", "macro_news_enhanced"}
)


def common_market_news_from_plan(plan: AskPlan) -> bool:
    return any(t.tool in ("common_market_news", "market_pulse") for t in plan.tools)


def macro_news_enhanced_from_plan(plan: AskPlan) -> bool:
    return any(t.tool == "macro_news_enhanced" for t in plan.tools)


def market_pulse_from_plan(plan: AskPlan) -> bool:
    """Broad market-now compose/digest path (planner must select common_market_news)."""
    return common_market_news_from_plan(plan)


def clustered_macro_data_from_bundle(bundle: Any) -> dict[str, Any]:
    for key, val in (getattr(bundle, "tool_results", None) or {}).items():
        if not val.get("ok"):
            continue
        tool_name = str(key).rsplit("_", 1)[0]
        if tool_name not in CLUSTERED_MACRO_TOOL_NAMES:
            continue
        data = val.get("data")
        if isinstance(data, dict) and ("clusters" in data or "representative_articles" in data):
            return data
    return {}


def market_pulse_data_from_bundle(bundle: Any) -> dict[str, Any]:
    return clustered_macro_data_from_bundle(bundle)


def market_pulse_window_days(question: str, tool_window_days: int | None = None) -> int:
    """Resolve lookback days for market pulse (tool override, then question, then default)."""
    if tool_window_days is not None:
        base = int(tool_window_days)
    else:
        base = infer_window_days_from_question(
            question,
            default_days=MARKET_PULSE_DEFAULT_WINDOW_DAYS,
        )
    return max(7, min(base, 90))


@dataclass
class MacroThemeCluster:
    cluster_id: str
    label: str
    theme_key: str
    article_count: int
    score: float
    articles: list[dict[str, Any]] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)


def _title_signature(article: dict[str, Any]) -> set[str]:
    title = str(article.get("title") or "")
    words = [
        w
        for w in re.findall(r"[a-z0-9]{4,}", title.lower())
        if w not in _STOPWORDS and not w.isdigit()
    ]
    sig = set(words[:10])
    for ent in (article.get("entity_names") or [])[:5]:
        for w in re.findall(r"[a-z]{4,}", str(ent).lower()):
            if w not in _STOPWORDS:
                sig.add(w[:24])
    return sig


def _cluster_label(articles: list[dict[str, Any]]) -> str:
    pulse_counts: dict[str, int] = {}
    for a in articles:
        key = str(a.get("_pulse_query") or "").strip()
        if key:
            pulse_counts[key] = pulse_counts.get(key, 0) + 1
    if pulse_counts:
        top_key, top_n = max(pulse_counts.items(), key=lambda x: x[1])
        human = _PULSE_THEME_LABELS.get(top_key)
        if human and top_n >= max(1, len(articles) // 4):
            return human
    ent_counts: dict[str, int] = {}
    sector_counts: dict[str, int] = {}
    for a in articles:
        for e in a.get("entity_names") or []:
            key = str(e).strip()
            if len(key) >= 3:
                ent_counts[key] = ent_counts.get(key, 0) + 1
        for s in a.get("sector_names") or []:
            key = str(s).strip()
            if key:
                sector_counts[key] = sector_counts.get(key, 0) + 1
    if sector_counts:
        top = max(sector_counts.items(), key=lambda x: x[1])[0]
        return str(top)[:72]
    if ent_counts:
        top_ent = max(ent_counts.items(), key=lambda x: x[1])[0]
        return str(top_ent)[:72]
    title = str((articles[0] or {}).get("title") or "Macro theme")[:70]
    return title


def cluster_articles_by_theme(articles: list[dict[str, Any]]) -> list[MacroThemeCluster]:
    """Group articles; larger groups = more coverage of the same event."""
    if not articles:
        return []
    buckets: list[dict[str, Any]] = []

    for art in articles:
        sig = _title_signature(art)
        if not sig:
            buckets.append({"sig": set(), "articles": [art]})
            continue
        best_idx = -1
        best_ratio = 0.0
        art_ents = {str(e).lower()[:40] for e in (art.get("entity_names") or []) if e}
        for i, bucket in enumerate(buckets):
            bsig = bucket["sig"]
            if not bsig and not bucket.get("entities"):
                continue
            inter = len(sig & bsig)
            ent_overlap = art_ents & bucket.get("entities", set())
            if ent_overlap:
                ratio = 0.5
                inter = max(inter, 2)
            elif inter < 2:
                continue
            else:
                ratio = inter / min(len(sig), len(bsig))
            if ratio >= 0.35 and inter >= 2 and ratio > best_ratio:
                best_ratio = ratio
                best_idx = i
        if best_idx >= 0:
            buckets[best_idx]["articles"].append(art)
            buckets[best_idx]["sig"] |= sig
            buckets[best_idx]["entities"] |= art_ents
        else:
            buckets.append({"sig": sig, "articles": [art], "entities": set(art_ents)})

    clusters: list[MacroThemeCluster] = []
    for i, bucket in enumerate(buckets):
        arts = bucket["articles"]
        if not arts:
            continue
        impacts = [int(a.get("max_impact") or 0) for a in arts]
        avg_impact = sum(impacts) / max(len(impacts), 1)
        count = len(arts)
        score = count * (1.0 + avg_impact / 4.0) + (0.15 * max(impacts) if impacts else 0)
        label = _cluster_label(arts)
        sectors: list[str] = []
        entities: list[str] = []
        for a in arts:
            sectors.extend(str(s) for s in (a.get("sector_names") or []) if s)
            entities.extend(str(e) for e in (a.get("entity_names") or []) if e)
        ranked_arts = sorted(
            arts,
            key=lambda a: (int(a.get("max_impact") or 0), float(a.get("_rrf_score") or 0)),
            reverse=True,
        )[:1]
        theme_slug = re.sub(r"[^a-z0-9]+", "_", label.lower())[:32] or f"theme_{i}"
        clusters.append(
            MacroThemeCluster(
                cluster_id=f"c{i}",
                label=label,
                theme_key=theme_slug,
                article_count=count,
                score=score,
                articles=ranked_arts,
                sectors=list(dict.fromkeys(sectors))[:6],
                entities=list(dict.fromkeys(entities))[:6],
            )
        )

    clusters.sort(key=lambda c: c.score, reverse=True)
    return clusters[:MARKET_PULSE_TOP_CLUSTERS]


def pick_cluster_representative(articles: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not articles:
        return None
    return sorted(
        articles,
        key=lambda a: (int(a.get("max_impact") or 0), float(a.get("_rrf_score") or 0)),
        reverse=True,
    )[0]


def market_pulse_representatives_from_clusters(
    clusters: list[dict[str, Any]],
    *,
    limit: int = MARKET_PULSE_TOP_CLUSTERS,
) -> list[dict[str, Any]]:
    """One representative article per top cluster for LLM synthesis."""
    rows: list[dict[str, Any]] = []
    for cl in clusters[:limit]:
        arts = cl.get("articles") if isinstance(cl.get("articles"), list) else []
        rep = arts[0] if arts else None
        if not rep:
            rep = pick_cluster_representative(arts)
        if not rep:
            continue
        rows.append(
            {
                "theme": str(cl.get("label") or "Macro theme"),
                "theme_key": cl.get("theme_key"),
                "articles_in_theme": int(cl.get("article_count") or len(arts) or 1),
                "title": rep.get("title"),
                "url": rep.get("url"),
                "source": rep.get("source"),
                "published_at": rep.get("published_at"),
                "direction": rep.get("direction"),
                "max_impact": rep.get("max_impact"),
                "snippet": (str(rep.get("snippet") or rep.get("scraped_text") or ""))[:520],
                "sectors": cl.get("sectors") if isinstance(cl.get("sectors"), list) else [],
                "entities": cl.get("entities") if isinstance(cl.get("entities"), list) else [],
            }
        )
    return rows


def _fetch_one_macro_query(
    semantic: str,
    theme_key: str,
    question: str,
    *,
    window_days: int,
    query_log: QueryLogger | None,
    filter_kwargs: dict[str, Any],
) -> list[dict[str, Any]]:
    from news_rag.scoped_retrieve import retrieve_scoped_news

    # Vector search already scopes by semantic query; full-sentence topic filter dropped all hits.
    scope = ScopeRefinement(search_mode="event_only", news_topics=[])
    rows = retrieve_scoped_news(
        semantic,
        scope=scope,
        question=question,
        window_days=window_days,
        query_log=query_log,
        ignore_question_time_hints=True,
        **filter_kwargs,
    )
    for row in rows:
        row["_pulse_query"] = theme_key
        row["_news_layer"] = "macro"
        row["_search_focus"] = f"pulse_{theme_key}"
    return rows


def _collect_pulse_pool(
    question: str,
    *,
    window_days: int,
    query_log: QueryLogger | None,
    per_query_cap: int,
    filter_kwargs: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    pool: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(8, len(MACRO_QUERY_SPECS)))) as pool_exec:
        futs = {
            pool_exec.submit(
                _fetch_one_macro_query,
                semantic,
                theme_key,
                question,
                window_days=window_days,
                query_log=query_log,
                filter_kwargs=filter_kwargs,
            ): theme_key
            for semantic, theme_key in MACRO_QUERY_SPECS
        }
        for fut in as_completed(futs):
            theme_key = futs[fut]
            try:
                for row in fut.result()[:per_query_cap]:
                    dedupe = article_dedupe_key(row)
                    if not dedupe:
                        continue
                    prev = pool.get(dedupe)
                    if prev is None or int(row.get("max_impact") or 0) > int(prev.get("max_impact") or 0):
                        pool[dedupe] = row
            except Exception as exc:
                if query_log is not None:
                    query_log.write(f"MARKET_PULSE query_fail {theme_key} {exc}")
    return pool


def run_market_pulse(
    question: str,
    *,
    window_days: int | None = None,
    query_log: QueryLogger | None = None,
    per_query_cap: int = 6,
    **filter_kwargs: Any,
) -> dict[str, Any]:
    """Multi-query macro retrieval + theme clustering (market-wide questions only)."""
    import time

    started = time.perf_counter()
    from news_rag.parse import parse_time_window

    wd = market_pulse_window_days(question, window_days)

    pool = _collect_pulse_pool(
        question,
        window_days=wd,
        query_log=query_log,
        per_query_cap=per_query_cap,
        filter_kwargs=filter_kwargs,
    )
    if not pool:
        wide = min(MARKET_PULSE_RETRY_WINDOW_DAYS, max(wd + 30, MARKET_PULSE_DEFAULT_WINDOW_DAYS + 30))
        if query_log is not None:
            query_log.write(f"MARKET_PULSE retry wider window_days={wide}")
        pool = _collect_pulse_pool(
            question,
            window_days=wide,
            query_log=query_log,
            per_query_cap=per_query_cap,
            filter_kwargs=filter_kwargs,
        )
        if pool:
            wd = wide

    articles = list(pool.values())
    clusters = cluster_articles_by_theme(articles)
    flat_for_digest: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cl in clusters:
        for art in cl.articles:
            key = article_dedupe_key(art)
            if key and key not in seen:
                seen.add(key)
                art = {**art, "_pulse_cluster": cl.cluster_id, "_pulse_label": cl.label}
                flat_for_digest.append(art)

    published_from, published_to, window_label = parse_time_window(
        "",
        date_from=None,
        date_to=None,
        default_days=wd,
    )

    elapsed = (time.perf_counter() - started) * 1000
    if query_log is not None:
        query_log.write(
            f"MARKET_PULSE queries={len(MACRO_QUERY_SPECS)} unique_articles={len(articles)} "
            f"clusters={len(clusters)} window_days={wd}"
        )
        query_log.log_stage(
            "market_pulse",
            articles=len(articles),
            clusters=len(clusters),
            top_labels=[c.label for c in clusters[:4]],
        )

    cluster_payloads = [
        {
            "id": c.cluster_id,
            "label": c.label,
            "theme_key": c.theme_key,
            "article_count": c.article_count,
            "score": round(c.score, 3),
            "sectors": c.sectors,
            "entities": c.entities,
            "articles": c.articles,
        }
        for c in clusters
    ]
    representatives = market_pulse_representatives_from_clusters(cluster_payloads)

    return {
        "ok": True,
        "data": {
            "window_days": wd,
            "window_label": window_label,
            "published_from": published_from,
            "published_to": published_to,
            "queries": [{"key": k, "semantic": s} for s, k in MACRO_QUERY_SPECS],
            "articles": flat_for_digest,
            "representative_articles": representatives,
            "clusters": cluster_payloads,
        },
        "error": "",
        "elapsed_ms": elapsed,
    }
