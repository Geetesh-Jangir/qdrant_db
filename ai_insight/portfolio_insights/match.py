"""Match user portfolio weights to stored sector and holding insight cards."""

from __future__ import annotations

from typing import Any

from lib.portfolio_scope import match_holding_to_corpus_entity, normalize_sector_label, sector_query_for_label

from ai_insight.common.market_daily_store import load_market_daily
from ai_insight.holding_insights.daily_store import load_daily
from ai_insight.holding_insights.holding_stock_insights_store import load_holding_stock_insights
from ai_insight.portfolio_insights.config import MAX_HOLDING, MAX_SECTOR
from ai_insight.portfolio_insights.personalize import personalize_card_headline


def _sector_index_from_daily(trading_date: str) -> dict[str, dict[str, Any]]:
    snap = load_market_daily(trading_date)
    if not snap or snap.get("trading_date") != trading_date:
        return {}
    index: dict[str, dict[str, Any]] = {}
    for item in snap.get("sectors") or []:
        if item.get("status") not in ("ok", "degraded", None):
            continue
        card = {
            "insight_id": "sector_index_insights",
            "trading_date": trading_date,
            "status": item.get("status") or "ok",
            "headline": item.get("headline") or "",
            "body": item.get("body") or item.get("insight") or "",
            "chips": [],
            "usage": {
                "input_tokens": item.get("input_tokens") or 0,
                "output_tokens": item.get("output_tokens") or 0,
                "calls": item.get("calls") or 0,
            },
            "sources": [{"url": a.get("url"), "published_at": a.get("published_at")} for a in (item.get("articles") or [])],
        }
        for name in item.get("names") or []:
            if not name:
                continue
            index[str(name).casefold()] = card
            norm = normalize_sector_label(str(name)).casefold()
            index[norm] = card
            mapped = sector_query_for_label(str(name))
            if mapped:
                index[mapped[0].casefold()] = card
    return index


def _sector_index(bundle_cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map casefolded sector labels to projected cards (raw envelopes not in projection — use facts from bundle load)."""
    from ai_insight.common.config import load_config
    from ai_insight.common.store import load_bundle
    from ai_insight.api import _bundle_is_live, _newer_bundle, _visible_on_page, public_projection

    # bundle_cards from _project_bundle are already projected; we need facts for matching — reload bundle items
    trading_date = bundle_cards[0].get("trading_date") if bundle_cards else None
    if not trading_date:
        return {}

    root = load_config().data_dir
    bundle = load_bundle("sector_index_insights", trading_date, root=root)
    live = load_bundle("sector_index_insights", trading_date, root=root, live=True)
    chosen = _newer_bundle(bundle, live)
    if chosen is None:
        return {}

    bundle_live = _bundle_is_live(chosen)
    index: dict[str, dict[str, Any]] = {}
    for item in chosen.items:
        facts = item.facts or {}
        if facts.get("kind") == "sector_rotation":
            continue
        if item.status not in ("ok", "degraded"):
            continue
        if not _visible_on_page(item, bundle_live=bundle_live):
            continue
        projected = public_projection(item)
        names: set[str] = set()
        for key in ("catalog_sectors", "sectors"):
            raw = facts.get(key)
            if isinstance(raw, list):
                for name in raw:
                    if name:
                        names.add(str(name))
            elif isinstance(raw, str) and raw:
                names.add(raw)
        idx = facts.get("index")
        if idx:
            names.add(str(idx))
        news_sector = facts.get("news_sector")
        if isinstance(news_sector, list):
            names.update(str(x) for x in news_sector)
        elif isinstance(news_sector, str) and news_sector:
            names.add(news_sector)

        for name in names:
            index[name.casefold()] = projected
            norm = normalize_sector_label(name).casefold()
            index[norm] = projected
            mapped = sector_query_for_label(name)
            if mapped:
                index[mapped[0].casefold()] = projected
    return index


def _portfolio_sectors(raw: dict[str, Any]) -> list[dict[str, Any]]:
    rows = raw.get("sector_allocation") if isinstance(raw.get("sector_allocation"), list) else []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        pct = row.get("percentage")
        if pct is None:
            continue
        out.append({"sector": str(row.get("sector") or "").strip(), "weight_pct": float(pct)})
    out.sort(key=lambda r: r["weight_pct"], reverse=True)
    return out


def _portfolio_holdings(raw: dict[str, Any]) -> list[dict[str, Any]]:
    rows = raw.get("top_holdings") if isinstance(raw.get("top_holdings"), list) else []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        pct = row.get("percentage")
        if pct is None:
            continue
        out.append(
            {
                "instrument_name": str(row.get("instrument_name") or "").strip(),
                "weight_pct": float(pct),
            }
        )
    out.sort(key=lambda r: r["weight_pct"], reverse=True)
    return out


def match_sectors(
    portfolio_raw: dict[str, Any],
    trading_date: str,
    *,
    crn: str = "",
    bundle_cards: list[dict[str, Any]] | None = None,
    limit: int = MAX_SECTOR,
) -> tuple[list[dict[str, Any]], list[str]]:
    index = _sector_index_from_daily(trading_date)
    if not index and bundle_cards:
        index = _sector_index(bundle_cards)
    if not index:
        return [], [s["sector"] for s in _portfolio_sectors(portfolio_raw)]

    user_sectors = _portfolio_sectors(portfolio_raw)
    matched: list[dict[str, Any]] = []
    unmatched: list[str] = []
    used_sectors: set[str] = set()

    for row in user_sectors:
        label = row["sector"]
        if not label:
            continue
        card = None
        sector_key = ""
        mapped = sector_query_for_label(label)
        if mapped and mapped[0].casefold() in index:
            sector_key = mapped[0].casefold()
            card = index[sector_key]
        elif label.casefold() in index:
            sector_key = label.casefold()
            card = index[sector_key]
        elif normalize_sector_label(label).casefold() in index:
            sector_key = normalize_sector_label(label).casefold()
            card = index[sector_key]
        else:
            folded = label.casefold()
            for key in index:
                if folded in key or key in folded:
                    sector_key = key
                    card = index[key]
                    break
        if card is None:
            unmatched.append(label)
            continue
        if sector_key in used_sectors:
            continue
        used_sectors.add(sector_key or label.casefold())
        item = {**card, "match_meta": {"sector": label, "weight_pct": row["weight_pct"]}}
        if crn:
            item = personalize_card_headline(item, portfolio_raw, crn=crn, match_key=label)
        else:
            item["headline_base"] = item.get("headline") or ""
        matched.append(item)
        if len(matched) >= limit:
            break

    return matched, unmatched


def _week_change(price: dict[str, Any] | None) -> float | None:
    bars = (price or {}).get("bars") if isinstance(price, dict) else None
    if not isinstance(bars, list) or len(bars) < 2:
        return None
    try:
        first = float(bars[0].get("close"))
        last = float(bars[-1].get("close"))
        if not first:
            return None
        return (last - first) / first * 100
    except (TypeError, ValueError, AttributeError):
        return None


def _holding_card(record: dict[str, Any], instrument_name: str, weight_pct: float) -> dict[str, Any]:
    lines = record.get("insight_lines") or []
    body = str(record.get("insight") or record.get("body") or "").strip()
    if not body and lines:
        body = "\n".join(str(x) for x in lines)
    chips = []
    if weight_pct is not None:
        chips.append({"label": "Your book", "value": f"{weight_pct:.2f}%", "tone": "neutral"})
    week = record.get("week_change_pct")
    if week is None:
        week = _week_change(record.get("price"))
    if week is not None:
        tone = "positive" if week > 0 else "negative" if week < 0 else "neutral"
        chips.append({"label": "Week", "value": f"{week:+.2f}%", "tone": tone})
    return {
        "insight_id": "holding_insights",
        "stock_id": record.get("stock_id"),
        "stock_name": record.get("stock_name"),
        "headline": record.get("headline") or record.get("stock_name"),
        "body": body,
        "chips": chips,
        "log_url": record.get("log_url"),
        "status": "ok",
        "match_meta": {"instrument_name": instrument_name, "weight_pct": weight_pct},
    }


def match_holdings(
    portfolio_raw: dict[str, Any],
    trading_date: str,
    *,
    crn: str = "",
    limit: int = MAX_HOLDING,
) -> tuple[list[dict[str, Any]], list[str]]:
    archive = load_holding_stock_insights(trading_date)
    insights: list[dict[str, Any]] = []
    if archive and archive.get("trading_date") == trading_date:
        insights = [
            r
            for r in (archive.get("holdings") or [])
            if isinstance(r, dict) and r.get("status") in ("ok", None) and r.get("stock_id")
        ]
    if not insights:
        daily = load_daily(trading_date)
        if daily:
            insights = [r for r in (daily.get("insights") or []) if isinstance(r, dict)]
    if not insights:
        return [], [h["instrument_name"] for h in _portfolio_holdings(portfolio_raw)]
    by_name: dict[str, dict[str, Any]] = {}
    corpus: set[str] = set()
    for row in insights:
        name = str(row.get("stock_name") or "").strip()
        if name:
            by_name[name] = row
            corpus.add(name)
        sid = str(row.get("stock_id") or "").strip()
        if sid:
            by_name[sid.casefold()] = row

    user = _portfolio_holdings(portfolio_raw)
    matched: list[dict[str, Any]] = []
    unmatched: list[str] = []
    used: set[str] = set()

    for row in user:
        inst = row["instrument_name"]
        if not inst:
            continue
        key = match_holding_to_corpus_entity(inst, corpus)
        record = by_name.get(key) or by_name.get(inst)
        if record is None:
            for cname, rec in by_name.items():
                if match_holding_to_corpus_entity(inst, {cname}) == cname:
                    record = rec
                    break
        if record is None:
            unmatched.append(inst)
            continue
        sid = str(record.get("stock_id") or key)
        if sid in used:
            continue
        used.add(sid)
        item = _holding_card(record, inst, row["weight_pct"])
        if crn:
            item = personalize_card_headline(item, portfolio_raw, crn=crn, match_key=inst)
        else:
            item["headline_base"] = item.get("headline") or ""
        matched.append(item)
        if len(matched) >= limit:
            break

    return matched, unmatched