"""Flow facts: nets, streak, ratio. Numbers only, no prose."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from ai_insight.common.flows import FlowDay


@dataclass
class StreakInfo:
    days: int
    sign: int
    history_days: int


def streak_days(days: list[FlowDay], key: str = "fii_net", *, trading_days: set[str] | None = None) -> StreakInfo:
    """Consecutive same-sign nets ending on the last row. A gap, a zero, or a flip breaks it."""
    present = [day for day in days if day.date]
    if not present:
        return StreakInfo(0, 0, 0)
    last = present[-1]
    sign = _sign(float(getattr(last, key)))
    history_days = len(present)
    if sign == 0:
        return StreakInfo(0, 0, history_days)
    by_date = {day.date: day for day in present}
    cursor = date.fromisoformat(last.date)
    count = 0
    while count < history_days:
        iso = cursor.isoformat()
        if trading_days is not None and iso not in trading_days and iso != last.date:
            break
        row = by_date.get(iso)
        if row is None:
            if trading_days is None:
                break
            if iso in trading_days:
                break
        else:
            if _sign(float(getattr(row, key))) != sign:
                break
            count += 1
        cursor -= timedelta(days=1)
        if (date.fromisoformat(last.date) - cursor).days > 40:
            break
    return StreakInfo(count, sign, history_days)


def rolling_avg_abs_net(days: list[FlowDay], window: int = 20, key: str = "fii_net") -> tuple[float | None, int]:
    """Average absolute net of the days before the last row."""
    prior = days[:-1] if days else []
    sample = prior[-window:]
    if not sample:
        return None, 0
    return round(sum(abs(float(getattr(day, key))) for day in sample) / len(sample), 2), len(sample)


def compute_flow_facts(history: list[FlowDay], trading_date: str, *, streak_high: int = 3, ratio_high: float = 1.5, min_history: int = 5, trading_days: set[str] | None = None) -> dict:
    ordered = [day for day in history if day.date <= trading_date]
    today = next((day for day in ordered if day.date == trading_date), None)
    if today is None and ordered:
        today = ordered[-1]
    flow_trade_date = today.date if today else None
    flow_lagged = bool(flow_trade_date and flow_trade_date != trading_date)
    streak = streak_days(ordered, trading_days=trading_days)
    avg, sample = rolling_avg_abs_net(ordered)
    fii = today.fii_net if today else None
    dii = today.dii_net if today else None
    ratio = None
    if fii is not None and avg and sample >= min_history:
        ratio = round(abs(fii) / avg, 2)
    offsets = bool(fii is not None and dii is not None and _sign(fii) and _sign(dii) and _sign(fii) != _sign(dii))
    high = streak.days >= streak_high or (ratio is not None and ratio >= ratio_high)
    return {
        "trading_date": trading_date,
        "flow_trade_date": flow_trade_date,
        "flow_lagged": flow_lagged,
        "fii_net_crore": fii,
        "dii_net_crore": dii,
        "fii_direction": _word(_sign(fii or 0)),
        "dii_direction": _word(_sign(dii or 0)),
        "fii_streak_days": streak.days,
        "fii_streak_sign": streak.sign,
        "history_days": streak.history_days,
        "rolling_avg_abs_net": avg,
        "ratio": ratio,
        "dii_offsets_fii": offsets,
        "prominence": "high" if high else "normal",
        "bars": [{"date": day.date, "fii_net": day.fii_net, "dii_net": day.dii_net} for day in ordered[-10:]],
    }


def fallback_headline(facts: dict) -> str:
    net = facts.get("fii_net_crore")
    if net is None:
        return "FII flow is not available"
    from ai_insight.common.display import fmt_inr_crore, ordinal

    verb = "bought" if net > 0 else "sold" if net < 0 else "were flat"
    text = f"FIIs {verb} {fmt_inr_crore(abs(net))}"
    streak = int(facts.get("fii_streak_days") or 0)
    if streak >= 2:
        word = "buying" if net > 0 else "selling"
        text = f"FIIs {verb} {fmt_inr_crore(abs(net))}, a {ordinal(streak)} straight day of {word}"
    words = text.split()
    return " ".join(words[:12])


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _word(sign: int) -> str:
    return "buying" if sign > 0 else "selling" if sign < 0 else "flat"


def flow_period_totals(days: list[FlowDay], trading_date: str) -> dict[str, Any]:
    """Weekly (Fri), monthly, and trailing session totals. Sums of daily nets only."""
    present = [day for day in days if day.date and day.date <= trading_date]
    if not present:
        return {"partial_week": True, "partial_month": True}
    from collections import defaultdict

    week: dict[str, float] = defaultdict(float)
    month: dict[str, float] = defaultdict(float)
    for day in present:
        try:
            d = date.fromisoformat(day.date)
        except ValueError:
            continue
        wk = d.isoformat()  # group by week ending Friday
        offset = (d.weekday() - 4) % 7
        week_end = d - timedelta(days=offset)
        wk = week_end.isoformat()
        week[wk] += day.fii_net
        week[f"dii:{wk}"] += day.dii_net
        mk = f"{d.year:04d}-{d.month:02d}"
        month[mk] += day.fii_net
        month[f"dii:{mk}"] += day.dii_net
    last_week = max((k for k in week if not k.startswith("dii:")), default="")
    last_month = max((k for k in month if not k.startswith("dii:")), default="")
    return {
        "week_fii_net": week.get(last_week),
        "week_dii_net": week.get(f"dii:{last_week}"),
        "month_fii_net": month.get(last_month),
        "month_dii_net": month.get(f"dii:{last_month}"),
        "net_5d_fii": sum(day.fii_net for day in present[-5:]),
        "net_5d_dii": sum(day.dii_net for day in present[-5:]),
        "net_20d_fii": sum(day.fii_net for day in present[-20:]),
        "net_20d_dii": sum(day.dii_net for day in present[-20:]),
        "partial_week": False,
        "partial_month": False,
    }
