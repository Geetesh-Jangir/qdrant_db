"""Story weights and sector scores. No I/O and no model calls."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ai_insight.common.clustering import Cluster
from ai_insight.common.display import sector_label
from ai_insight.common.evidence import story_weight

from ai_insight.sector_leaderboard.schema import SectorScore, StoryScore

TEXT_CHARS = 600
_MIN_STORIES = 2


@dataclass
class Ranking:
    sectors: list[SectorScore]
    eligible: list[SectorScore]
    best: SectorScore | None
    worst: SectorScore | None


def score_stories(clusters: list[Cluster]) -> list[StoryScore]:
    """One story per cluster. The highest-magnitude article supplies the weight."""
    stories: list[StoryScore] = []
    for cluster in clusters:
        chosen = _representative(cluster)
        if chosen is None:
            continue
        weight, sign, magnitude, article, entity = chosen
        stories.append(
            StoryScore(
                cluster_id=cluster.cluster_id,
                title=str(article.get("title") or ""),
                url=str(article.get("url") or ""),
                source=str(article.get("source") or ""),
                published_at=str(article.get("published_at") or ""),
                text=trim_text(article.get("scraped_text") or ""),
                weight=weight,
                magnitude=magnitude,
                sign=sign,
                direction=str(entity.get("direction") or "unclear"),
            )
        )
    return stories


def score_sector(name: str, clusters: list[Cluster]) -> SectorScore:
    stories = score_stories(clusters)
    count = len(stories)
    total = sum(story.weight for story in stories)
    score = total / (count + 2) if count else 0.0
    return SectorScore(
        name=name,
        display=sector_label(name),
        score=score,
        n_stories=count,
        stories=stories,
    )


def rank(sectors: list[SectorScore]) -> Ranking:
    """Eligible means at least two distinct stories. A missing side is left empty."""
    eligible = [sector for sector in sectors if sector.n_stories >= _MIN_STORIES]
    eligible.sort(key=lambda sector: (-sector.score, sector.name))
    positives = [sector for sector in eligible if sector.score > 0]
    negatives = [sector for sector in eligible if sector.score < 0]
    best = positives[0] if positives else None
    worst = min(negatives, key=lambda sector: (sector.score, sector.name)) if negatives else None
    return Ranking(sectors=list(sectors), eligible=eligible, best=best, worst=worst)


def publishable(ranking: Ranking) -> bool:
    """Both sides, or a single side that itself has at least three stories, and at least two eligible sectors."""
    if len(ranking.eligible) < _MIN_STORIES:
        return False
    if ranking.best is not None and ranking.worst is not None:
        return True
    side = ranking.best or ranking.worst
    return side is not None and side.n_stories >= 3


def top_stories(sector: SectorScore, limit: int = 2) -> list[StoryScore]:
    ordered = sorted(sector.stories, key=lambda story: (-abs(story.weight), story.published_at, story.url))
    return ordered[:limit]


def viz_items(eligible: list[SectorScore], *, limit: int = 3) -> list[dict]:
    """Top positive and top negative eligible sectors, scores rounded to 3 dp."""
    positives = [sector for sector in eligible if sector.score > 0][:limit]
    negatives = sorted(
        (sector for sector in eligible if sector.score < 0),
        key=lambda sector: (sector.score, sector.name),
    )[:limit]
    items = [_item(sector, "positive") for sector in positives]
    items.extend(_item(sector, "negative") for sector in negatives)
    return items


def _driver_row(story: StoryScore) -> dict[str, Any]:
    return {
        "cluster_id": story.cluster_id,
        "title": story.title,
        "url": story.url,
        "source": story.source,
        "published_at": story.published_at,
        "direction": story.direction,
        "weight": shown(abs(story.weight)),
    }


def summarize_sector_news(sector: SectorScore, *, headline_limit: int = 5) -> dict[str, Any]:
    """Counts and top headlines by entity direction across every scored story."""
    stories = list(sector.stories)
    boosting = [story for story in stories if story.sign > 0]
    weighing = [story for story in stories if story.sign < 0]
    unclear = len(stories) - len(boosting) - len(weighing)

    def pick(pool: list[StoryScore]) -> list[StoryScore]:
        return sorted(pool, key=lambda story: (-story.magnitude, story.published_at, story.url))[:headline_limit]

    return {
        "sector": sector.display,
        "total": len(stories),
        "boosting": len(boosting),
        "weighing": len(weighing),
        "unclear": unclear,
        "net_score": shown(sector.score),
        "headlines": {
            "boosting": [_driver_row(story) for story in pick(boosting)],
            "weighing": [_driver_row(story) for story in pick(weighing)],
        },
    }


def build_pulse_drivers(
    ranking: Ranking,
    week_meta: dict[str, Any] | None,
    *,
    best_theme: str = "",
    worst_theme: str = "",
) -> dict[str, Any]:
    wm = week_meta or {}
    drivers: dict[str, Any] = {}
    for side, sector, index_key, theme in (
        ("best", ranking.best, "best_index", best_theme),
        ("worst", ranking.worst, "worst_index", worst_theme),
    ):
        if sector is None or not sector.stories:
            continue
        digest = summarize_sector_news(sector)
        index = wm.get(index_key) or {}
        drivers[side] = {
            "index": str(index.get("display") or sector.display),
            "week_change_pct": index.get("week_change_pct"),
            "theme": theme.strip(),
            **digest,
        }
    return drivers


def pulse_viz_data(
    ranking: Ranking,
    week_meta: dict[str, Any] | None = None,
    *,
    best_theme: str = "",
    worst_theme: str = "",
) -> dict[str, Any]:
    return {
        "items": pulse_viz_items(ranking, week_meta),
        "drivers": build_pulse_drivers(ranking, week_meta, best_theme=best_theme, worst_theme=worst_theme),
    }


def pulse_viz_items(ranking: Ranking, week_meta: dict[str, Any] | None = None) -> list[dict]:
    """Week index moves with linked news scores; falls back to raw sector scores."""
    wm = week_meta or {}
    by_name = {sector.name: sector for sector in ranking.eligible}
    items: list[dict] = []
    for key, tone in (("best_index", "positive"), ("worst_index", "negative")):
        index = wm.get(key)
        if not index:
            continue
        sectors = list(index.get("sectors") or [])
        sector = next((by_name.get(name) for name in sectors if name in by_name), None)
        display = str(index.get("display") or (sector.display if sector else sectors[0] if sectors else "Index"))
        row: dict[str, Any] = {
            "display": display,
            "sector": sector.display if sector else display,
            "week_change_pct": index.get("week_change_pct"),
            "tone": tone,
        }
        if sector is not None:
            row["score"] = shown(sector.score)
            row["stories"] = sector.n_stories
        items.append(row)
    if items:
        return items
    return viz_items(ranking.eligible)


def shown(score: float) -> float:
    return round(float(score), 3)


def prominence(current: list[float], history: list[float], history_days: int) -> str:
    """High when a side is in the top decile of the last saved days. Under five days stays normal."""
    if history_days < 5 or not history or not current:
        return "normal"
    ordered = sorted(history)
    index = math.ceil(0.9 * len(ordered)) - 1
    index = min(max(index, 0), len(ordered) - 1)
    cutoff = ordered[index]
    if any(value >= cutoff for value in current):
        return "high"
    return "normal"


def trim_text(text: str, limit: int = TEXT_CHARS) -> str:
    collapsed = " ".join(str(text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    clipped = collapsed[:limit]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped


def _representative(cluster: Cluster):
    chosen = None
    for row in cluster.articles:
        entity = row.get("entity") or {}
        article = row.get("article") or {}
        weight, sign, magnitude = story_weight(entity)
        key = (-magnitude, str(article.get("published_at") or ""), str(article.get("url") or ""))
        if chosen is None or key < chosen[0]:
            chosen = (key, weight, sign, magnitude, article, entity)
    if chosen is None:
        return None
    _key, weight, sign, magnitude, article, entity = chosen
    return weight, sign, magnitude, article, entity


def _item(sector: SectorScore, tone: str) -> dict:
    return {
        "sector": sector.display,
        "score": shown(sector.score),
        "stories": sector.n_stories,
        "tone": tone,
    }


def _int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
