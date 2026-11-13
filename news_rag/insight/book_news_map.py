"""Map a top-holdings payload to the sector and stocks a news question should cover."""

from __future__ import annotations

from typing import Any

from news_rag.insight.contracts import ExecutionPlan, ToolCall


def resolve_book_sector(label: str, sector_allocation: list[Any]) -> dict[str, Any] | None:
    """Match the planner's sector words to one row of sector_allocation."""
    wanted = str(label or "").strip()
    if not wanted:
        return None
    rows = [row for row in sector_allocation or [] if isinstance(row, dict)]
    for row in rows:
        name = str(row.get("sector") or "").strip()
        if name.casefold() == wanted.casefold():
            return {"sector": name, "weight_pct": _pct(row.get("percentage"))}
    try:
        from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

        keys = get_sector_fund_ranking_index().resolve_sector_keys([wanted])
    except Exception:
        keys = []
    if not keys:
        return None
    key = str(keys[0])
    for row in rows:
        name = str(row.get("sector") or "").strip()
        if name.casefold() == key.casefold():
            return {"sector": name, "weight_pct": _pct(row.get("percentage"))}
    return None


def sector_holdings(raw: dict[str, Any], label: str, n: int = 8) -> list[dict[str, Any]]:
    """Top holdings whose industry is that sector. Cap 8, keep at least 5 when they exist."""
    sector = str(label or "").strip()
    if not sector:
        return []
    rows = raw.get("top_holdings") if isinstance(raw.get("top_holdings"), list) else []
    matched = [
        row for row in rows
        if isinstance(row, dict) and str(row.get("industry") or "").strip().casefold() == sector.casefold()
    ]
    matched.sort(key=lambda row: _pct(row.get("percentage")), reverse=True)
    limit = min(8, max(5, int(n or 8)))
    if len(matched) < 5:
        limit = len(matched)
    out = []
    for row in matched[:limit]:
        raw_name = str(row.get("instrument_name") or "").strip()
        out.append({
            "name": _display_name(raw_name),
            "news_name": _news_name(raw_name),
            "weight_pct": _pct(row.get("percentage")),
            "fund_count": row.get("fund_count"),
            "industry": str(row.get("industry") or "").strip(),
        })
    return out


def book_wide_sectors(raw: dict[str, Any], n: int = 5) -> list[dict[str, Any]]:
    """Largest sectors that have a named stock, not a cash or paper bucket."""
    allocation = raw.get("sector_allocation") if isinstance(raw.get("sector_allocation"), list) else []
    kept = []
    for row in allocation:
        if not isinstance(row, dict):
            continue
        label = str(row.get("sector") or "").strip()
        if not label or not _has_named_stock(raw, label):
            continue
        kept.append({"sector": label, "weight_pct": _pct(row.get("percentage"))})
    kept.sort(key=lambda row: row["weight_pct"], reverse=True)
    return kept[: max(1, min(int(n or 5), 5))]


def news_calls_for_book(plan: ExecutionPlan, raw: dict[str, Any]) -> list[ToolCall]:
    """Sector news plus one stock-news call per top holding. Empty when this is not a book-news ask."""
    mode = str(getattr(plan, "portfolio_news_mode", "") or "none")
    if mode not in ("book_wide", "sector"):
        return []
    window = min(int(plan.window_days or 7), 30)
    calls: list[ToolCall] = []
    if mode == "sector":
        resolved = resolve_book_sector(
            plan.news_sector,
            raw.get("sector_allocation") if isinstance(raw, dict) else [],
        )
        label = str((resolved or {}).get("sector") or plan.news_sector or "").strip()
        if not label:
            return []
        calls.append(_sector_call(label, window))
        for holding in sector_holdings(raw, label):
            calls.append(_stock_call(holding["news_name"], window))
        return calls
    for row in book_wide_sectors(raw):
        calls.append(_sector_call(row["sector"], window))
    return calls


def sector_book(plan: ExecutionPlan, raw: dict[str, Any]) -> dict[str, Any] | None:
    mode = str(getattr(plan, "portfolio_news_mode", "") or "none")
    if mode == "sector":
        resolved = resolve_book_sector(
            plan.news_sector,
            raw.get("sector_allocation") if isinstance(raw, dict) else [],
        )
        if not resolved:
            return None
        holdings = sector_holdings(raw, resolved["sector"])
        return {"mode": "sector", "sector": resolved, "holdings": holdings, "sectors": [resolved]}
    if mode == "book_wide":
        sectors = book_wide_sectors(raw)
        return {"mode": "book_wide", "sector": None, "holdings": [], "sectors": sectors}
    return None


def _has_named_stock(raw: dict[str, Any], sector: str) -> bool:
    rows = raw.get("top_holdings") if isinstance(raw.get("top_holdings"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        industry = str(row.get("industry") or "").strip()
        name = str(row.get("instrument_name") or "").strip()
        if industry.casefold() == sector.casefold() and name.casefold() != industry.casefold():
            return True
    return False


def _sector_call(label: str, window: int) -> ToolCall:
    return ToolCall(
        tool="search_financial_news",
        arguments={"scope": "sector", "topics": [label], "top_n": 8, "window_days": window, "direction": "any"},
        wave=2,
        why=f"News for {label}, mapped to the portfolio weight",
    )


def _stock_call(name: str, window: int) -> ToolCall:
    return ToolCall(
        tool="search_financial_news",
        arguments={"scope": "stock", "topics": [name], "top_n": 3, "window_days": window, "direction": "any"},
        wave=2,
        why=f"News for holding {name}",
    )


def _pct(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _display_name(name: str) -> str:
    return " ".join(name.replace("£", " ").split()).strip(" .")


def _news_name(name: str) -> str:
    from lib.portfolio_scope import _clean_holding_tokens

    cleaned = _clean_holding_tokens(name)
    return cleaned or _display_name(name)
