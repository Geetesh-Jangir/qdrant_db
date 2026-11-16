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
