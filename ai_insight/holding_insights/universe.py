"""Load top-N stocks from aggregated holdings JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass

from news_rag.news_entity_resolve import resolve_corpus_entity

from ai_insight.holding_insights.config import MAX_STOCK_LIMIT, TOP_HOLDINGS_PATH


@dataclass(frozen=True)
class StockRow:
    stock_id: str
    instrument_name: str
    sector_name: str
    symbol: str
    yfinance_ticker: str
    qdrant_entity_name: str


def load_top_stocks(limit: int) -> list[StockRow]:
    if limit < 1 or limit > MAX_STOCK_LIMIT:
        raise ValueError(f"limit must be 1..{MAX_STOCK_LIMIT}")
    if not TOP_HOLDINGS_PATH.is_file():
        raise FileNotFoundError(str(TOP_HOLDINGS_PATH))
    payload = json.loads(TOP_HOLDINGS_PATH.read_text(encoding="utf-8"))
    items = list(payload.get("items") or [])[:limit]
    rows: list[StockRow] = []
    for item in items:
        symbol = str(item.get("symbol") or "").strip()
        name = str(item.get("instrument_name") or "").strip()
        if not symbol or not name:
            continue
        rows.append(
            StockRow(
                stock_id=symbol,
                instrument_name=name,
                sector_name=str(item.get("sector_name") or "").strip(),
                symbol=symbol,
                yfinance_ticker=f"{symbol}.NS",
                qdrant_entity_name=resolve_corpus_entity(name),
            )
        )
    return rows