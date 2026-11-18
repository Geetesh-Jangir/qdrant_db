"""Trading date resolution and store readiness for portfolio compose."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_insight.common.config import load_config
from ai_insight.common.store import list_dates, load_best, load_bundle
from ai_insight.common.market_daily_store import load_market_daily
from ai_insight.holding_insights.daily_store import load_daily
from ai_insight.holding_insights.holding_stock_insights_store import load_holding_stock_insights
from ai_insight.portfolio_insights.config import COMMON_IDS, SECTOR_BUNDLE_ID

_BUNDLES = (SECTOR_BUNDLE_ID,)
_SINGLES = COMMON_IDS


def resolve_trading_date(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    found: set[str] = set()
    root = load_config().data_dir
    for name in (*_SINGLES, *_BUNDLES):
        found.update(list_dates(name, root=root))
    daily_root = root / "daily"
    if daily_root.is_dir():
        found.update(p.stem for p in daily_root.glob("*.json"))
    archive_root = root / "holding_stock_insights"
    if archive_root.is_dir():
        found.update(p.stem for p in archive_root.glob("*.json"))
    dates = sorted(found)
    for day in reversed(dates):
        check = readiness(day)
        if check.ready:
            return day
    return dates[-1] if dates else None


def _acceptable(envelope) -> bool:
    if envelope is None:
        return False
    return envelope.status in ("ok", "degraded")


@dataclass
class ReadinessResult:
    trading_date: str
    ready: bool
    missing: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def readiness(trading_date: str) -> ReadinessResult:
    root = load_config().data_dir
    missing: list[str] = []
    details: dict[str, Any] = {"common": {}, "sectors": {}, "holdings": {}, "market_daily": {}, "holding_archive": {}}

    market_daily = load_market_daily(trading_date)
    md_common = {
        row.get("insight_id"): row
        for row in (market_daily or {}).get("common") or []
        if isinstance(row, dict) and row.get("insight_id")
    }
    for insight_id in COMMON_IDS:
        item = md_common.get(insight_id)
        if item and item.get("status") in ("ok", "degraded"):
            ok = True
            status = item.get("status")
            source = "market_daily"
        else:
            env = load_best(insight_id, trading_date, root=root)
            ok = _acceptable(env)
            status = env.status if env else None
            source = "envelope"
        details["common"][insight_id] = {"ok": ok, "status": status, "source": source}
        if not ok:
            missing.append(f"common:{insight_id}")

    market_sector_count = len((market_daily or {}).get("sectors") or [])

    bundle = load_bundle(SECTOR_BUNDLE_ID, trading_date, root=root)
    sector_ok = market_sector_count > 0
    sector_count = market_sector_count
    if not sector_ok and bundle and bundle.status in ("ok", "degraded") and bundle.items:
        for item in bundle.items:
            kind = (item.facts or {}).get("kind")
            if kind == "sector_rotation":
                continue
            if item.status in ("ok", "degraded"):
                sector_count += 1
        sector_ok = sector_count > 0
    details["sectors"] = {"ok": sector_ok, "count": sector_count, "bundle_status": bundle.status if bundle else None}
    if not sector_ok:
        missing.append("sectors:sector_index_insights")

    market_ok = bool(
        market_daily
        and market_daily.get("trading_date") == trading_date
        and len(market_daily.get("common") or []) >= len(COMMON_IDS)
        and market_sector_count > 0
    )
    details["market_daily"] = {
        "ok": market_ok,
        "common_count": len((market_daily or {}).get("common") or []),
        "sector_count": len((market_daily or {}).get("sectors") or []),
    }
    if not market_ok:
        missing.append("market:daily_snapshot")

    archive = load_holding_stock_insights(trading_date)
    archive_ok = bool(
        archive
        and archive.get("trading_date") == trading_date
        and sum(1 for row in (archive.get("holdings") or []) if (row or {}).get("status") == "ok") > 0
    )
    details["holding_archive"] = {
        "ok": archive_ok,
        "count": sum(1 for row in (archive or {}).get("holdings") or [] if (row or {}).get("status") == "ok"),
        "job_id": (archive or {}).get("job_id"),
    }

    daily = load_daily(trading_date)
    daily_ok = False
    if daily:
        generated = str(daily.get("generated_on") or "")
        counts = daily.get("counts") or {}
        daily_ok = generated == trading_date and int(counts.get("ok") or 0) > 0
    hold_ok = archive_ok or daily_ok
    details["holdings"] = {
        "ok": hold_ok,
        "archive_ok": archive_ok,
        "daily_ok": daily_ok,
        "generated_on": (daily or {}).get("generated_on"),
        "counts": (daily or {}).get("counts") or (archive or {}).get("counts"),
    }
    if not hold_ok:
        missing.append("holdings:stock_insights")

    return ReadinessResult(
        trading_date=trading_date,
        ready=len(missing) == 0,
        missing=missing,
        details=details,
    )


def load_sector_bundle_projected(trading_date: str) -> list[dict[str, Any]]:
    from ai_insight.api import _project_bundle

    return _project_bundle(SECTOR_BUNDLE_ID, trading_date)


def load_common_projected(trading_date: str, limit: int) -> list[dict[str, Any]]:
    from ai_insight.api import _project_single

    out: list[dict[str, Any]] = []
    for insight_id in COMMON_IDS[:limit]:
        card = _project_single(insight_id, trading_date)
        if card and card.get("status") in ("ok", "degraded"):
            card = {**card, "section": insight_id}
            out.append(card)
    return out