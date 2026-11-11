"""Computed reads from a projected investor book. The composer quotes these; it does not recompute them."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from news_rag.portfolio.views import BALANCE_THRESHOLDS, build_derived_views

_STYLE_BANDS: tuple[tuple[str, float, float], ...] = (
    ("conservative", 0.0, 35.0),
    ("moderate", 30.0, 70.0),
    ("balanced", 30.0, 70.0),
    ("aggressive", 65.0, 100.0),
    ("growth", 60.0, 100.0),
)

_BRIEF_KINDS = {
    "portfolio_overview": ("performance", "concentration", "as_of"),
    "health_check": ("risk_alignment", "concentration", "sip", "laggards"),
    "risk_alignment": ("risk_alignment",),
    "sip_review": ("sip", "performance"),
    "period_change": ("performance", "laggards", "as_of"),
    "fy_summary": ("performance", "sip", "as_of"),
    "where_losing": ("laggards",),
}


@dataclass(frozen=True)
class Insight:
    kind: str
    severity: str
    text: str
    evidence: str


def _num(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _equity_pct(derived: dict[str, Any]) -> float:
    split = derived.get("asset_split") if isinstance(derived.get("asset_split"), dict) else {}
    block = split.get("equity") if isinstance(split.get("equity"), dict) else {}
    return _num(block.get("aum_pct")) or 0.0


def _style_band(profile: dict[str, Any]) -> tuple[str, float, float] | None:
    raw = " ".join(
        str(profile.get(key) or "")
        for key in ("investment_style", "risk_profile", "label")
    ).lower()
    for name, low, high in _STYLE_BANDS:
        if name in raw:
            return name, low, high
    return None


def build_insights(data: dict[str, Any] | None) -> list[Insight]:
    book = data if isinstance(data, dict) else {}
    summary = book.get("summary") if isinstance(book.get("summary"), dict) else {}
    derived = build_derived_views(book)
    out: list[Insight] = []

    meta = book.get("meta") if isinstance(book.get("meta"), dict) else {}
    as_of = str(meta.get("as_of_date") or meta.get("as_of") or "").strip()
    if as_of:
        out.append(Insight("as_of", "info", f"Figures are as of {as_of}.", as_of))

    xirr = _num(summary.get("portfolio_xirr_pct"))
    absolute = _num(summary.get("absolute_return_pct"))
    if xirr is not None or absolute is not None:
        parts = []
        if absolute is not None:
            parts.append(f"absolute return {absolute:.1f}%")
        if xirr is not None:
            parts.append(f"XIRR {xirr:.1f}%")
        out.append(Insight("performance", "info", "Portfolio " + " and ".join(parts) + ".", ""))

    holdings = [row for row in (book.get("holdings") or []) if isinstance(row, dict)]
    ranked = sorted(holdings, key=lambda row: _num(row.get("absolute_return_pct")) or 0.0, reverse=True)
    if ranked:
        best = ranked[0]
        worst = ranked[-1]
        if best.get("scheme_name") and best is not worst:
            out.append(Insight(
                "performance",
                "info",
                f"Strongest holding is {best.get('scheme_name')} at {best.get('absolute_return_pct')}%. "
                f"Weakest is {worst.get('scheme_name')} at {worst.get('absolute_return_pct')}%.",
                "",
            ))
        gains = [(_num(row.get("gain_loss_inr")) or 0.0, row) for row in holdings]
        positive = sum(v for v, _ in gains if v > 0)
        top_gain = max(gains, key=lambda item: item[0]) if gains else None
        if top_gain and positive > 0 and top_gain[0] > 0:
            share = 100.0 * top_gain[0] / positive
            out.append(Insight(
                "performance",
                "watch" if share >= 60 else "info",
                f"{top_gain[1].get('scheme_name')} accounts for {share:.0f}% of positive gains.",
                f"{share:.0f}",
            ))

    largest = (derived.get("largest_holdings") or [None])[0]
    if isinstance(largest, dict):
        share = _num(largest.get("aum_pct")) or 0.0
        if share >= BALANCE_THRESHOLDS["single_fund_pct"]:
            out.append(Insight(
                "concentration",
                "review",
                f"{largest.get('scheme_name')} is {share:.0f}% of the book. You may want to review that concentration.",
                f"{share:.0f}",
            ))
    for sector in derived.get("top_categories") or []:
        share = _num(sector.get("aum_pct")) or 0.0
        if share >= BALANCE_THRESHOLDS["sector_concentration_pct"]:
            out.append(Insight(
                "concentration",
                "watch",
                f"{sector.get('name')} is {share:.0f}% of the book.",
                f"{share:.0f}",
            ))
            break

    conc = book.get("concentration") if isinstance(book.get("concentration"), dict) else {}
    stocks = conc.get("top_holdings") or conc.get("instruments") or []
    if isinstance(stocks, list) and stocks:
        top = stocks[0] if isinstance(stocks[0], dict) else {}
        weight = _num(top.get("weight_pct") or top.get("portfolio_weight_pct"))
        label = top.get("name") or top.get("instrument")
        if weight is not None and label:
            out.append(Insight(
                "concentration",
                "watch" if weight >= 8 else "info",
                f"Largest underlying stock is {label} at {weight:.1f}% of equity holdings.",
                f"{weight:.1f}",
            ))

    profile = book.get("profile_risk") if isinstance(book.get("profile_risk"), dict) else {}
    band = _style_band(profile)
    equity = _equity_pct(derived)
    if band:
        style, low, high = band
        if low <= equity <= high:
            severity, read = "aligned", "aligned"
        elif abs(equity - low) <= 10 or abs(equity - high) <= 10:
            severity, read = "watch", "close to the edge of"
        else:
            severity, read = "review", "outside"
        out.append(Insight(
            "risk_alignment",
            severity,
            f"Equity is {equity:.0f}% of the book, {read} a {style} band ({low:.0f}–{high:.0f}%).",
            f"{equity:.0f}",
        ))

    sip = book.get("sip") if isinstance(book.get("sip"), dict) else {}
    plans = [p for p in (sip.get("plans") or []) if isinstance(p, dict)]
    if "plans" in sip or plans:
        live = [p for p in plans if p.get("is_live", True)]
        paused = len(plans) - len(live)
        monthly = sum(_num(p.get("amount") or p.get("amount_inr")) or 0.0 for p in live)
        text = f"{len(live)} live SIPs"
        if paused:
            text += f", {paused} paused"
        if monthly:
            text += f", about {monthly:.0f} a month"
        dates = [
            str(p.get("next_due_date") or p.get("next_date") or p.get("next_installment_date") or "")
            for p in live
        ]
        dates = sorted(d for d in dates if d)
        if dates:
            text += f". Next date {dates[0]}"
        out.append(Insight("sip", "watch" if paused else "info", text + ".", ""))

    laggards = [row for row in holdings if (_num(row.get("absolute_return_pct")) or 0) < 0]
    weak = [row for row in holdings if str(row.get("rs_label") or "").lower() in ("avoid", "poor", "weak")]
    if laggards or weak:
        names = [str(row.get("scheme_name") or "") for row in (laggards or weak)[:3]]
        out.append(Insight(
            "laggards",
            "review",
            "Negative or weak holdings: " + ", ".join(n for n in names if n) + ". You may want to review these.",
            str(len(laggards or weak)),
        ))

    pnl = book.get("pnl_summary") if isinstance(book.get("pnl_summary"), dict) else {}
    short = _num(pnl.get("short_term_gain_inr"))
    long = _num(pnl.get("long_term_gain_inr"))
    if short is not None or long is not None:
        out.append(Insight(
            "gains_split",
            "info",
            f"Short-term gains {short or 0:.0f}, long-term gains {long or 0:.0f}.",
            "",
        ))
    return out


def insights_for_brief(intent: str, data: dict[str, Any] | None, *, limit: int = 4) -> list[Insight]:
    kinds = _BRIEF_KINDS.get(intent)
    rows = build_insights(data)
    if kinds:
        rows = [row for row in rows if row.kind in kinds]
    return rows[:limit]


def insight_lines(rows: list[Insight]) -> list[str]:
    return [row.text for row in rows]
