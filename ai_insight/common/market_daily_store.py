"""Date-keyed market insight snapshots (common + sector cards) for portfolio compose."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_insight.common.config import load_config
from ai_insight.common.store import load_best, load_bundle
from ai_insight.holding_insights.atomic_io import atomic_write_json
_COMMON_IDS = ("market_driver_digest", "fii_dii_flow_narrative", "sector_leaderboard")
_SECTOR_BUNDLE_ID = "sector_index_insights"


def _daily_path(trading_date: str) -> Path:
    if len(trading_date) != 10 or trading_date[4] != "-" or trading_date[7] != "-":
        raise ValueError(f"trading_date must be YYYY-MM-DD, got {trading_date!r}")
    return load_config().data_dir / "daily" / f"{trading_date}.json"


def _articles(sources: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for src in sources:
        url = getattr(src, "url", None) or (src.get("url") if isinstance(src, dict) else "")
        if not url:
            continue
        published = getattr(src, "published_at", None) or (src.get("published_at") if isinstance(src, dict) else "")
        out.append({"url": str(url), "published_at": str(published or "")})
    return out


def _usage(meta: Any) -> dict[str, int]:
    usage = getattr(meta, "usage", None) or (meta.get("usage") if isinstance(meta, dict) else None) or {}
    inch = int(getattr(usage, "input_tokens", None) or (usage.get("input_tokens") if isinstance(usage, dict) else 0) or 0)
    outch = int(getattr(usage, "output_tokens", None) or (usage.get("output_tokens") if isinstance(usage, dict) else 0) or 0)
    calls = len(getattr(meta, "llm_calls", None) or (meta.get("llm_calls") if isinstance(meta, dict) else []) or [])
    return {"input_tokens": inch, "output_tokens": outch, "calls": calls}


def _sector_names(facts: dict[str, Any]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()

    def add(raw: Any) -> None:
        if not raw:
            return
        text = str(raw).strip()
        if text and text not in seen:
            seen.add(text)
            names.append(text)

    for key in ("catalog_sectors", "sectors", "news_sector"):
        raw = facts.get(key)
        if isinstance(raw, list):
            for item in raw:
                add(item)
        else:
            add(raw)
    add(facts.get("index"))
    add(facts.get("display"))
    add(facts.get("sector"))
    return names


def _newer_bundle(left: Any, right: Any) -> Any:
    if left is None:
        return right
    if right is None:
        return left
    return right if right.as_of_ist >= left.as_of_ist else left


def build_market_daily_snapshot(trading_date: str) -> dict[str, Any]:
    root = load_config().data_dir
    common: list[dict[str, Any]] = []
    stamps: list[str] = []

    for insight_id in _COMMON_IDS:
        env = load_best(insight_id, trading_date, root=root)
        if env is None or env.status not in ("ok", "degraded"):
            continue
        stamps.append(env.as_of_ist)
        common.append(
            {
                "insight_id": insight_id,
                "status": env.status,
                "headline": env.headline,
                "body": env.body,
                "insight": env.body,
                "chips": [
                    {"label": c.label, "value": c.value, "tone": c.tone}
                    for c in (env.chips or [])
                ],
                "viz_type": getattr(env.viz, "type", None) or "",
                **_usage(env.meta),
                "articles": _articles(env.sources),
            }
        )

    sectors: list[dict[str, Any]] = []
    bundle = load_bundle(_SECTOR_BUNDLE_ID, trading_date, root=root)
    live = load_bundle(_SECTOR_BUNDLE_ID, trading_date, root=root, live=True)
    chosen = _newer_bundle(bundle, live)
    if chosen is not None:
        stamps.append(chosen.as_of_ist)
        for item in chosen.items:
            facts = item.facts or {}
            if facts.get("kind") == "sector_rotation":
                continue
            if item.status not in ("ok", "degraded"):
                continue
            names = _sector_names(facts)
            if not names:
                continue
            sectors.append(
                {
                    "names": names,
                    "primary_name": names[0],
                    "status": item.status,
                    "headline": item.headline,
                    "body": item.body,
                    "insight": item.body,
                    **_usage(item.meta),
                    "articles": _articles(item.sources),
                }
            )

    generated_at = max(stamps) if stamps else None
    return {
        "trading_date": trading_date,
        "generated_at": generated_at,
        "common": common,
        "sectors": sectors,
    }


def save_market_daily(trading_date: str, snapshot: dict[str, Any]) -> Path:
    path = _daily_path(trading_date)
    atomic_write_json(path, snapshot)
    return path


def load_market_daily(trading_date: str) -> dict[str, Any] | None:
    path = _daily_path(trading_date)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None