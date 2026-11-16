"""Deterministic theme clusters. Same rows in any order produce the same ids."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from news_rag.market_pulse import cluster_articles_by_theme

ClusterBy = Literal["title", "entity"]


@dataclass
class Cluster:
    cluster_id: str
    label: str
    member_urls: list[str]
    representative_title: str
    representative_url: str
    weight: int
    avg_impact: float
    direction_mix: dict[str, int]
    articles: list[dict[str, Any]] = field(default_factory=list)


def cluster_score(cluster: Cluster) -> float:
    """count * (1 + avg_impact/4) + 0.15 * max_impact."""
    impacts = [int((row.get("entity") or {}).get("impact") or 0) for row in cluster.articles]
    max_impact = max(impacts) if impacts else 0
    return cluster.weight * (1 + cluster.avg_impact / 4) + 0.15 * max_impact


def rank_clusters(clusters: list[Cluster], formula: str = "count_impact") -> list[Cluster]:
    if formula != "count_impact":
        raise ValueError(f"unknown cluster formula {formula!r}")
    return sorted(clusters, key=lambda cluster: (-cluster_score(cluster), cluster.cluster_id))


def cluster_rows(
    rows: list[dict[str, Any]],
    *,
    cluster_by: ClusterBy = "title",
    top_clusters: int = 8,
) -> list[Cluster]:
    ordered = sorted(rows, key=_sort_key)
    groups = _dedupe(ordered)
    groups.sort(key=lambda group: _sort_key(group["row"]))
    if not groups:
        return []
    adapters = [_adapter(group, cluster_by) for group in groups]
    themes = cluster_articles_by_theme(
        adapters,
        top_clusters=max(len(adapters), 1),
        articles_per_cluster=None,
    )
    scored: list[tuple[float, Cluster]] = []
    for theme in themes:
        members = [group for article in theme.articles if (group := _group_of(article)) is not None]
        if not members:
            continue
        members.sort(key=lambda member: _sort_key(member["row"]))
        impacts = [int(member["entity"].get("impact") or 0) for member in members]
        mix = {"positive": 0, "negative": 0, "neutral": 0, "unclear": 0}
        for member in members:
            direction = str(member["entity"].get("direction") or "unclear")
            mix[direction if direction in mix else "unclear"] += 1
        rep = sorted(
            members,
            key=lambda member: (
                -int(member["entity"].get("impact") or 0),
                _sort_key(member["row"]),
            ),
        )[0]
        cluster = Cluster(
            cluster_id="",
            label=theme.label,
            member_urls=[member["article"]["url"] for member in members],
            representative_title=rep["article"]["title"],
            representative_url=rep["article"]["url"],
            weight=len(members),
            avg_impact=round(sum(impacts) / len(impacts), 4),
            direction_mix=mix,
            articles=[member["row"] for member in members],
        )
        scored.append((float(theme.score), cluster))
    scored.sort(
        key=lambda item: (
            -item[0],
            _published(item[1]),
            item[1].member_urls[0] if item[1].member_urls else "",
        )
    )
    ranked = [cluster for _score, cluster in scored]
    for index, cluster in enumerate(ranked):
        cluster.cluster_id = f"c{index}"
    return ranked[:top_clusters]


def _published(cluster: Cluster) -> str:
    if not cluster.articles:
        return ""
    return str((cluster.articles[0].get("article") or {}).get("published_at") or "")


def _sort_key(row: dict[str, Any]) -> tuple[str, str]:
    article = row.get("article") or {}
    return (str(article.get("published_at") or ""), str(article.get("url") or ""))


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parent = list(range(len(rows)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    owner: dict[str, int] = {}
    for index, row in enumerate(rows):
        for key in _keys(row, index):
            if key in owner:
                union(index, owner[key])
            else:
                owner[key] = index
    buckets: dict[int, list[dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        buckets.setdefault(find(index), []).append(row)
    groups = []
    for index in range(len(rows)):
        if find(index) != index:
            continue
        groups.append(_collapse(buckets[index]))
    return groups


def _keys(row: dict[str, Any], index: int) -> list[str]:
    article = row.get("article") or {}
    keys: list[str] = []
    url = str(article.get("url") or "").strip()
    if url:
        keys.append("u:" + url)
    for alias in article.get("alias_urls") or []:
        alias_url = str(alias or "").strip()
        if alias_url:
            keys.append("u:" + alias_url)
    title = str(article.get("title") or "").strip().lower()
    if title:
        keys.append("t:" + title)
    if not keys:
        keys.append(f"anon:{index}")
    return keys


def _collapse(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """One article. Longest body wins when syndicated copies differ. Earliest row supplies the rest."""
    rows = sorted(rows, key=_sort_key)
    base = rows[0]
    article = dict(base.get("article") or {})
    longest = max(rows, key=lambda row: len(str((row.get("article") or {}).get("scraped_text") or "")))
    article["scraped_text"] = str((longest.get("article") or {}).get("scraped_text") or "")
    aliases: list[str] = []
    for row in rows:
        for url in [((row.get("article") or {}).get("url"))] + list((row.get("article") or {}).get("alias_urls") or []):
            text = str(url or "").strip()
            if text and text not in aliases and text != article.get("url"):
                aliases.append(text)
    article["alias_urls"] = aliases
    entity = max(
        (row.get("entity") or {} for row in rows),
        key=lambda item: (
            int(item.get("relevance") or 0),
            int(item.get("impact") or 0),
            float(item.get("about_this_name") or 0),
        ),
    )
    row = {"article": article, "entity": dict(entity)}
    return {"article": article, "entity": dict(entity), "row": row}


def _adapter(group: dict[str, Any], cluster_by: ClusterBy) -> dict[str, Any]:
    article = group["article"]
    entity = group["entity"]
    name = str(entity.get("name") or "")
    names = [] if cluster_by == "title" or not name else [name]
    sectors = [name] if cluster_by == "entity" and entity.get("type") == "sector" and name else []
    return {
        "url": article.get("url") or "",
        "title": article.get("title") or "",
        "source": article.get("source") or "",
        "published_at": article.get("published_at") or "",
        "scraped_text": article.get("scraped_text") or "",
        "alias_urls": list(article.get("alias_urls") or []),
        "max_impact": int(entity.get("impact") or 0),
        "entity_names": names,
        "sector_names": sectors,
        "_group": group,
    }


def _group_of(article: dict[str, Any]) -> dict[str, Any] | None:
    group = article.get("_group")
    return group if isinstance(group, dict) else None
