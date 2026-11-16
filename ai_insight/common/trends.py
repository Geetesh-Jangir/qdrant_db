"""Trend stats computed from news counts and price history. The model only describes these."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


@dataclass
class DayPoint:
    date: str
    n_stories: int = 0
    net_signed: float = 0.0
    pos: int = 0
    neg: int = 0
    avg_impact: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "n_stories": self.n_stories,
            "net_signed": round(self.net_signed, 4),
            "pos": self.pos,
            "neg": self.neg,
            "avg_impact": round(self.avg_impact, 4),
        }


@dataclass
class TrendStats:
    streak_days: int = 0
    slope: float = 0.0
    z_today: float | None = None
    rank_change: int | None = None
    history_days: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "streak_days": self.streak_days,
            "slope": round(self.slope, 4),
            "z_today": None if self.z_today is None else round(self.z_today, 4),
            "rank_change": self.rank_change,
            "history_days": self.history_days,
        }


@dataclass
class PriceTrend:
    change_5d: float | None = None
    change_20d: float | None = None
    pct_from_high: float | None = None
    realized_vol: float | None = None
    closes: list[dict[str, Any]] = field(default_factory=list)
    history_days: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "change_5d": self.change_5d,
            "change_20d": self.change_20d,
            "pct_from_high": self.pct_from_high,
            "realized_vol": self.realized_vol,
            "closes": self.closes,
            "history_days": self.history_days,
        }


def session_day(published_at: str) -> str:
    """15:30 IST or later counts toward the next calendar day."""
    text = (published_at or "").replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    local = parsed.astimezone(IST)
    day = local.date()
    if local.hour > 15 or (local.hour == 15 and local.minute >= 30):
        day = day + timedelta(days=1)
    return day.isoformat()


def trend_stats(series: list[DayPoint]) -> TrendStats:
    """Never claims a streak longer than the days that are actually present."""
    if not series:
        return TrendStats()
    values = [point.net_signed for point in series]
    sign = _sign(values[-1])
    streak = 0
    if sign != 0:
        for value in reversed(values):
            if _sign(value) != sign:
                break
            streak += 1
    slope = _slope(values)
    z_today = None
    if len(values) >= 3:
        prior = values[:-1]
        mean = sum(prior) / len(prior)
        var = sum((item - mean) ** 2 for item in prior) / len(prior)
        std = math.sqrt(var)
        if std > 0:
            z_today = (values[-1] - mean) / std
    return TrendStats(
        streak_days=streak,
        slope=slope,
        z_today=z_today,
        rank_change=None,
        history_days=len(series),
    )


def price_trend_from_closes(rows: list[tuple[str, float]], *, end: date | None = None) -> PriceTrend:
    ordered = [(day, close) for day, close in rows if close]
    if end is not None:
        ordered = [(day, close) for day, close in ordered if day <= end.isoformat()]
    if not ordered:
        return PriceTrend()
    closes = [{"date": day, "close": round(close, 4)} for day, close in ordered]
    last = ordered[-1][1]
    high = max(close for _day, close in ordered)

    def change(n: int) -> float | None:
        if len(ordered) <= n or ordered[-1 - n][1] == 0:
            return None
        return round((last - ordered[-1 - n][1]) / ordered[-1 - n][1] * 100.0, 2)

    returns: list[float] = []
    for index in range(1, len(ordered)):
        prev = ordered[index - 1][1]
        if prev:
            returns.append((ordered[index][1] - prev) / prev)
    vol = None
    if len(returns) >= 2:
        mean = sum(returns) / len(returns)
        var = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
        vol = round(math.sqrt(var) * 100.0, 2)
    from_high = round((last - high) / high * 100.0, 2) if high else None
    return PriceTrend(
        change_5d=change(5),
        change_20d=change(20),
        pct_from_high=from_high,
        realized_vol=vol,
        closes=closes[-20:],
        history_days=len(ordered),
    )


def entity_daily_series(
    entity_type: str,
    names: list[str] | None,
    end: date,
    n_days: int = 20,
    *,
    client: Any = None,
    config: Any = None,
) -> dict[str, list[DayPoint]]:
    """One scroll over the range, bucketed by IST session day."""
    from ai_insight.common.evidence import story_weight
    from ai_insight.common.qdrant_access import fetch_entity_rows
    from ai_insight.common.time_ist import IST as _IST

    start = datetime.combine(end - timedelta(days=n_days + 3), time.min, tzinfo=_IST)
    end_dt = datetime.combine(end, time(23, 59, 59), tzinfo=_IST)
    from news_pipeline.textutil import to_iso

    window = (to_iso(start), to_iso(end_dt))
    result = fetch_entity_rows(entity_type, window, names, client=client, with_text=False)
    buckets: dict[str, dict[str, DayPoint]] = {}
    for row in result.rows:
        article = row.get("article") or {}
        entity = row.get("entity") or {}
        day = session_day(str(article.get("published_at") or ""))
        name = str(entity.get("name") or "")
        if not day or not name or day > end.isoformat():
            continue
        point = buckets.setdefault(name, {}).setdefault(day, DayPoint(date=day))
        signed, sign, _mag = story_weight(entity)
        point.n_stories += 1
        point.net_signed += signed
        point.avg_impact += int(entity.get("impact") or 0)
        if sign > 0:
            point.pos += 1
        elif sign < 0:
            point.neg += 1
    series: dict[str, list[DayPoint]] = {}
    for name, by_day in buckets.items():
        points = [by_day[key] for key in sorted(by_day)]
        for point in points:
            if point.n_stories:
                point.avg_impact = point.avg_impact / point.n_stories
        series[name] = points[-n_days:]
    return series


def price_trend(entity_name: str, end: date, days: int = 60) -> PriceTrend:
    from ai_insight.data.yfinance_source import fetch_history

    period = "6mo" if days > 40 else "3mo"
    rows = fetch_history(entity_name, period=period)
    return price_trend_from_closes(rows, end=end)


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    num = sum((index - mean_x) * (value - mean_y) for index, value in enumerate(values))
    den = sum((index - mean_x) ** 2 for index in range(n))
    if den == 0:
        return 0.0
    return num / den
