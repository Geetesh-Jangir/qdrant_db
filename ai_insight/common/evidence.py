"""Articles actually handed to the model. Whole articles only; nothing is trimmed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_SIGNS = {"positive": 1, "negative": -1}


@dataclass
class EvidenceArticle:
    cluster_id: str
    title: str
    source: str
    published_at: str
    url: str
    full_text: str
    weight: float
    entity: str
    direction: str
    impact: int
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "title": self.title,
            "source": self.source,
            "published_at": self.published_at,
            "url": self.url,
            "full_text": self.full_text,
            "weight": self.weight,
            "entity": self.entity,
            "direction": self.direction,
            "impact": self.impact,
            **self.extra,
        }


def story_weight(entity: dict[str, Any]) -> tuple[float, int, float]:
    """Signed weight, sign, and magnitude. Neutral and unclear contribute nothing."""
    relevance = _int(entity.get("relevance"))
    impact = _int(entity.get("impact"))
    about = _float(entity.get("about_this_name"))
    magnitude = (relevance / 4) * (impact / 3) * about
    sign = _SIGNS.get(str(entity.get("direction") or "").strip().lower(), 0)
    return magnitude * sign, sign, magnitude


def pick_evidence(clusters: list[Any], per_cluster: int = 3) -> list[EvidenceArticle]:
    """Top members by absolute weight inside each cluster."""
    chosen: list[EvidenceArticle] = []
    for cluster in clusters:
        ranked: list[tuple[float, dict[str, Any]]] = []
        for row in cluster.articles:
            entity = row.get("entity") or {}
            signed, _sign, magnitude = story_weight(entity)
            ranked.append((abs(signed) or magnitude, row))
        ranked.sort(key=lambda item: (-item[0], str((item[1].get("article") or {}).get("url") or "")))
        for weight, row in ranked[:per_cluster]:
            article = row.get("article") or {}
            entity = row.get("entity") or {}
            text = str(article.get("full_text") or article.get("scraped_text") or "")
            chosen.append(
                EvidenceArticle(
                    cluster_id=str(cluster.cluster_id),
                    title=str(article.get("title") or ""),
                    source=str(article.get("source") or ""),
                    published_at=str(article.get("published_at") or ""),
                    url=str(article.get("url") or ""),
                    full_text=text,
                    weight=round(weight, 4),
                    entity=str(entity.get("name") or ""),
                    direction=str(entity.get("direction") or "unclear"),
                    impact=_int(entity.get("impact")),
                )
            )
    return chosen


def format_evidence_block(evidence: list[EvidenceArticle]) -> str:
    parts: list[str] = []
    for item in evidence:
        parts.append(
            "\n".join(
                [
                    f"CLUSTER {item.cluster_id}",
                    f"TITLE: {item.title}",
                    f"SOURCE: {item.source}",
                    f"PUBLISHED: {item.published_at}",
                    f"URL: {item.url}",
                    "ARTICLE:",
                    item.full_text,
                ]
            )
        )
    return "\n\n".join(parts)


def enforce_prompt_budget(
    evidence: list[EvidenceArticle],
    max_chars: int,
) -> tuple[list[EvidenceArticle], list[EvidenceArticle]]:
    """Drop whole lowest-weight articles until the block fits. Never cut a body."""
    kept = list(evidence)
    dropped: list[EvidenceArticle] = []
    while kept and len(format_evidence_block(kept)) > max_chars:
        index = min(range(len(kept)), key=lambda i: (kept[i].weight, i))
        dropped.append(kept.pop(index))
    return kept, dropped


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
