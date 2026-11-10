"""Standing macro-news digest for any question that reads the news index.

The first such question builds 7-day and 1-month groups from Qdrant and writes
them to disk. Later questions reuse that file for two hours. The next question
after that rebuilds both windows and overwrites the file.
"""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

TTL_SECONDS = 2 * 60 * 60
WINDOWS = (7, 30)
CACHE_VERSION = 2
ARTICLES_PER_SECTION = 2
MAX_MACRO_ARTICLES = 10
_WEEK_RE = re.compile(r"\b(?:this week|last week|past week|7\s*days?|one week)\b", re.I)
_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = _ROOT / "data" / "macro_news_cache.json"
_LOCK = threading.Lock()
_MEMORY: dict[str, dict[str, Any]] = {}

Fetch = Callable[[], dict[str, Any]]


def get_macro_news(
    *,
    now: float | None = None,
    path: Path | None = None,
    fetch: Fetch | None = None,
    query_log: Any = None,
) -> dict[str, Any]:
    """Return the cached digest, rebuilding it only when it is older than two hours."""
    moment = time.time() if now is None else float(now)
    cache_path = path or DEFAULT_PATH
    key = str(cache_path)
    with _LOCK:
        current = _MEMORY.get(key)
        if current is None:
            current = _read(cache_path)
            if current:
                _MEMORY[key] = current
        if current and _fresh(current, moment):
            hit = {**current, "cache_hit": True}
            _log(query_log, "hit")
            return hit
        try:
            built = fetch() if fetch is not None else compute_macro_news()
        except Exception as exc:
            _log(query_log, f"fail {exc}")
            if current:
                return {**current, "cache_hit": False, "stale": True}
            return {"cached_at": None, "ttl_seconds": TTL_SECONDS, "windows": {}, "cache_hit": False}
        payload = {
            "cached_at": moment,
            "ttl_seconds": TTL_SECONDS,
            "version": CACHE_VERSION,
            "windows": built.get("windows") or {},
        }
        _write(cache_path, payload)
        _MEMORY[key] = payload
        _log(query_log, "refresh")
        return {**payload, "cache_hit": False}


def select_macro_for_question(
    payload: dict[str, Any],
    question: str = "",
    window_days: int | None = None,
) -> dict[str, Any]:
    """The file keeps every hit. The model gets two articles from each leading section, ten at most."""
    windows = payload.get("windows") if isinstance(payload.get("windows"), dict) else {}
    use_week = _WEEK_RE.search(question or "") or (
        window_days is not None and int(window_days) <= 10
    )
    window_key = "7" if use_week else "30"
    window = windows.get(window_key) or windows.get("30") or windows.get("7") or {}
    if not isinstance(window, dict):
        window = {}
    chosen: list[dict[str, Any]] = []
    kept = 0
    for cluster in list(window.get("clusters") or []):
        if kept >= MAX_MACRO_ARTICLES or not isinstance(cluster, dict):
            break
        articles = [art for art in list(cluster.get("articles") or []) if isinstance(art, dict)]
        articles = articles[:ARTICLES_PER_SECTION]
        room = MAX_MACRO_ARTICLES - kept
        articles = articles[:room]
        if not articles:
            continue
        kept += len(articles)
        chosen.append(
            {
                "label": cluster.get("label") or "",
                "query": cluster.get("query") or "",
                "article_count": cluster.get("article_count"),
                "articles": articles,
            }
        )
    return {
        "window_days": window.get("window_days"),
        "label": window.get("label") or "",
        "clusters": chosen,
        "article_total": kept,
    }


def compute_macro_news() -> dict[str, Any]:
    """Search each named macro parameter and keep the ones with the most articles."""
    from news_pipeline.config import MACRO_ENTITIES

    specs = [(str(row["name"]), str(row["query"])) for row in MACRO_ENTITIES]
    windows: dict[str, Any] = {}
    for days in WINDOWS:
        found = _search_macro_parameters(specs, days)
        windows[str(days)] = {
            "window_days": days,
            "label": "7 days" if days == 7 else "1 month",
            "clusters": _slim_clusters(found),
        }
    return {"windows": windows}


def _search_macro_parameters(
    specs: list[tuple[str, str]],
    window_days: int,
) -> list[dict[str, Any]]:
    """One Qdrant search per macro parameter. The group name is that parameter."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from news_rag.article_pool import article_dedupe_key
    from news_rag.query_plan import ScopeRefinement
    from news_rag.scoped_retrieve import retrieve_scoped_news

    scope = ScopeRefinement(search_mode="event_only", news_topics=[])

    def _one(name: str, query: str) -> dict[str, Any] | None:
        rows = retrieve_scoped_news(
            query,
            scope=scope,
            question="",
            window_days=window_days,
            ignore_question_time_hints=True,
            vector_limit=12,
            body_char_limit=0,
        )
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            key = article_dedupe_key(row) or str(row.get("url") or row.get("title") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(row)
        if not unique:
            return None
        unique.sort(key=lambda row: int(row.get("max_impact") or 0), reverse=True)
        return {
            "label": name,
            "query": query,
            "article_count": len(unique),
            "articles": unique[:3],
        }

    groups: list[dict[str, Any]] = []
    workers = max(1, min(8, len(specs)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, name, query) for name, query in specs]
        for fut in as_completed(futures):
            try:
                group = fut.result()
            except Exception:
                continue
            if group:
                groups.append(group)
    groups.sort(key=lambda group: int(group.get("article_count") or 0), reverse=True)
    return groups


def _article_text(art: dict[str, Any]) -> str:
    """The story the index stored, not the headline."""
    from news_rag.snippet_clean import article_body_for_llm

    source = art
    if not (art.get("scraped_text") or art.get("body") or art.get("snippet")):
        source = {**art, "snippet": art.get("summary") or art.get("text") or ""}
    return article_body_for_llm(source, limit=0)


def _slim_clusters(clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        (c for c in clusters if isinstance(c, dict)),
        key=lambda c: (int(c.get("article_count") or 0), float(c.get("score") or 0)),
        reverse=True,
    )
    slim: list[dict[str, Any]] = []
    for cluster in ranked[:6]:
        articles = []
        for art in list(cluster.get("articles") or [])[:3]:
            if not isinstance(art, dict):
                continue
            articles.append(
                {
                    "title": art.get("title") or art.get("headline") or "",
                    "summary": _article_text(art),
                    "source": art.get("source") or "",
                    "url": art.get("url") or "",
                    "published_at": art.get("published_at") or art.get("date") or "",
                }
            )
        slim.append(
            {
                "label": cluster.get("label") or "",
                "query": cluster.get("query") or "",
                "article_count": int(cluster.get("article_count") or 0),
                "sectors": list(cluster.get("sectors") or [])[:8],
                "articles": articles,
            }
        )
    return slim


def _fresh(payload: dict[str, Any], now: float) -> bool:
    cached_at = payload.get("cached_at")
    if not isinstance(cached_at, (int, float)):
        return False
    if (now - float(cached_at)) >= TTL_SECONDS:
        return False
    if int(payload.get("version") or 0) != CACHE_VERSION:
        return False
    return _cache_has_article_text(payload)


def _cache_has_article_text(payload: dict[str, Any]) -> bool:
    """A file of headlines is not a usable digest. Rebuild it on the next question."""
    for window in (payload.get("windows") or {}).values():
        if not isinstance(window, dict):
            continue
        for cluster in window.get("clusters") or []:
            if not isinstance(cluster, dict):
                continue
            for art in cluster.get("articles") or []:
                if not isinstance(art, dict):
                    continue
                if not str(art.get("summary") or art.get("body") or "").strip():
                    return False
    return True


def _read(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _log(query_log: Any, message: str) -> None:
    if query_log is not None:
        query_log.write(f"MACRO_CACHE {message}")
