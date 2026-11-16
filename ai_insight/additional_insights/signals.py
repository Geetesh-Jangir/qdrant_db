"""Deterministic signals. Prose is written later, from these numbers only."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_insight.common.trends import DayPoint, trend_stats


@dataclass
class Signal:
    id: str
    kind: str
    numbers: dict[str, Any]
    cluster_ids: list[str] = field(default_factory=list)
    title: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "numbers": self.numbers, "cluster_ids": self.cluster_ids, "title": self.title}


def detect_signals(*, series: dict[str, list[DayPoint]] | None = None, prices: dict[str, float] | None = None, flows: list[dict] | None = None, clusters: list[dict] | None = None) -> list[Signal]:
    found: list[Signal] = []
    for name, points in (series or {}).items():
        stats = trend_stats(points)
        if stats.history_days >= 5 and stats.z_today is not None and abs(stats.z_today) >= 1.5:
            found.append(Signal(f"shift-{name}", "sector_shift", {"name": name, "z": stats.z_today, "streak_days": stats.streak_days, "history_days": stats.history_days}, title=name))
        if points and _surge(points):
            found.append(Signal(f"surge-{name}", "news_surge", {"name": name, "today": points[-1].n_stories, "history_days": len(points)}, title=name))
    for name, change in (prices or {}).items():
        if abs(change) >= 3:
            found.append(Signal(f"price-{name}", "price_extreme", {"name": name, "change_pct": change}, title=name))
    if flows:
        last = flows[-1]
        if last.get("fii_net", 0) < 0 and last.get("nifty_change", 0) > 0:
            found.append(Signal("diverge-fii", "divergence", {"fii_net": last["fii_net"], "nifty_change": last["nifty_change"]}, title="FII selling while the index rose"))
    themes: dict[str, int] = {}
    for cluster in clusters or []:
        label = str(cluster.get("label") or "")
        themes[label] = themes.get(label, 0) + int(cluster.get("days") or 1)
    for label, days in themes.items():
        if label and days >= 3:
            found.append(Signal(f"theme-{label}", "recurring_theme", {"label": label, "days": days}, title=label))
    return found


def _surge(points: list[DayPoint]) -> bool:
    if len(points) < 4:
        return False
    prior = [point.n_stories for point in points[:-1]]
    avg = sum(prior) / len(prior)
    return avg > 0 and points[-1].n_stories >= avg * 2
