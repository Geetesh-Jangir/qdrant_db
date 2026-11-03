"""Deterministic gold window tables from get_market_snapshot metals_spot."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_WINDOW_ORDER = ("1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "5Y")


def _fmt_inr_whole(value: float | int | None) -> str:
    if value is None:
        return "—"
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return "—"
    s = str(abs(n))
    if len(s) <= 3:
        grouped = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts: list[str] = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts + [last3])
    return grouped


def _short_date(iso: str | None) -> str:
    text = str(iso or "").strip()[:10]
    if not text:
        return "—"
    try:
        d = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return text
    return f"{d.day} {d.strftime('%b')}"


def _metals_spot_from_results(results: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    for row in results or []:
        if not row.get("ok") or row.get("tool") != "get_market_snapshot":
            continue
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        spot = data.get("metals_spot")
        if isinstance(spot, dict) and spot.get("metal") == "gold" and spot.get("available") is not False:
            returns = spot.get("returns")
            if isinstance(returns, dict) and returns:
                return spot
    return None


def render_gold_returns_table(results: list[dict[str, Any]] | None) -> str:
    spot = _metals_spot_from_results(results)
    if not spot:
        return ""
    returns = spot.get("returns") if isinstance(spot.get("returns"), dict) else {}
    keys = [k for k in _WINDOW_ORDER if k in returns]
    for k in returns:
        if k not in keys:
            keys.append(str(k))
    if not keys:
        return ""

    lines = [
        "| Window | Then (₹ per 10g) | Now (₹ per 10g) | Change |",
        "| --- | ---: | ---: | ---: |",
    ]
    for code in keys:
        block = returns.get(code)
        if not isinstance(block, dict):
            continue
        from_date = _short_date(block.get("from_date"))
        to_date = _short_date(block.get("to_date"))
        from_price = _fmt_inr_whole(block.get("from_price"))
        to_price = _fmt_inr_whole(block.get("to_price"))
        pct = block.get("pct")
        if pct is None:
            change = "—"
        else:
            try:
                change = f"{float(pct):+.2f}%"
            except (TypeError, ValueError):
                change = "—"
        approx = block.get("approx") is True
        window_label = f"{code} (from {from_date})"
        if approx:
            window_label = f"{window_label} ~"
        then_cell = f"{from_price} ({from_date})"
        now_cell = f"{to_price} ({to_date})"
        lines.append(f"| {window_label} | {then_cell} | {now_cell} | {change} |")
    return "\n".join(lines) if len(lines) > 2 else ""


_GOLD_WINDOW_TABLE = re.compile(
    r"\n?\| Window \|[^\n]*\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+",
    re.IGNORECASE,
)


def strip_gold_window_table(text: str) -> str:
    """Remove composer-built gold window tables so the server table is authoritative."""
    if not text:
        return text
    cleaned = _GOLD_WINDOW_TABLE.sub("\n", text)
    return cleaned.strip()
