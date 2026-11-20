"""Twelve Data Brent history (XBR/USD) under data/ai_insights/_data/."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal

from ai_insight.common.store import load_json, save_json
from ai_insight.fii_dii_flow_narrative.collector import append_record, history_has_date
from news_pipeline.config import repo_root

REQUESTED_SYMBOL = "XBR/USD"
FALLBACK_SYMBOL = "BCO"
HISTORY_NAME = "xbr_usd_history.json"
API = "https://api.twelvedata.com/time_series"
BACKFILL_DAYS = 30

Status = Literal["saved", "backfilled", "already_present", "unavailable"]


@dataclass
class BrentSyncResult:
    status: Status
    symbol: str
    detail: str
    rows_added: int = 0


def history_path(data_dir: Path | None = None) -> Path:
    root = data_dir or (repo_root() / "data" / "ai_insights")
    return Path(root) / "_data" / HISTORY_NAME


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _api_key() -> str:
    raw = os.environ.get("TWELVE_DATA_API_KEY", "").strip().strip('"').strip("'")
    if raw:
        return raw
    env_file = repo_root() / ".env"
    if not env_file.is_file():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "TWELVE_DATA_API_KEY":
            return value.strip().strip('"').strip("'")
    return ""


def _requested_symbol() -> str:
    return (os.environ.get("TWELVE_DATA_BRENT_SYMBOL") or REQUESTED_SYMBOL).strip() or REQUESTED_SYMBOL


def _parse_day(raw: str) -> str:
    text = str(raw or "").strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    if "T" in text:
        return text.split("T", 1)[0]
    return text


def _num(raw: Any) -> float | None:
    if raw in (None, ""):
        return None
    try:
        return round(float(raw), 6)
    except (TypeError, ValueError):
        return None


def _call_time_series(
    api_key: str,
    symbol: str,
    *,
    outputsize: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "symbol": symbol,
        "interval": "1day",
        "apikey": api_key,
        "order": "DESC",
    }
    if outputsize is not None:
        params["outputsize"] = outputsize
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{API}?{query}",
        headers={"User-Agent": "RupeeStopInsight/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"code": exc.code, "message": body[:240]}
        payload.setdefault("code", exc.code)
        payload["status"] = "error"
        return payload


def _plan_block(payload: dict[str, Any]) -> bool:
    message = str(payload.get("message") or "").lower()
    return payload.get("code") == 404 and ("available starting with" in message or "invalid" in message)


def resolve_fetch_symbol(api_key: str) -> tuple[str, str]:
    requested = _requested_symbol()
    probe = _call_time_series(api_key, requested, outputsize=1)
    if probe.get("status") == "ok" and probe.get("values"):
        return requested, ""
    if _plan_block(probe) and requested.upper() != FALLBACK_SYMBOL:
        fallback = _call_time_series(api_key, FALLBACK_SYMBOL, outputsize=1)
        if fallback.get("status") == "ok" and fallback.get("values"):
            detail = (
                f"{requested} not on current Twelve Data plan; using {FALLBACK_SYMBOL} "
                f"({str(probe.get('message') or '')[:120]})"
            )
            return FALLBACK_SYMBOL, detail
    message = str(probe.get("message") or probe.get("body") or "time_series failed")
    raise RuntimeError(message[:240])


def _row_from_value(
    value: dict[str, Any],
    *,
    symbol: str,
    requested: str,
    detail: str = "",
) -> dict[str, Any] | None:
    day = _parse_day(value.get("datetime"))
    close = _num(value.get("close"))
    if not day or close is None:
        return None
    record: dict[str, Any] = {
        "date": day,
        "close": close,
        "open": _num(value.get("open")),
        "high": _num(value.get("high")),
        "low": _num(value.get("low")),
        "volume": _num(value.get("volume")),
        "unit": "usd",
        "symbol": symbol,
        "requested_symbol": requested,
        "source": "twelvedata:time_series",
        "fetched_at_utc": _utc_now(),
    }
    if detail:
        record["detail"] = detail[:240]
    return record


def fetch_days(
    api_key: str,
    symbol: str,
    *,
    outputsize: int,
) -> list[dict[str, Any]]:
    payload = _call_time_series(api_key, symbol, outputsize=outputsize)
    if payload.get("status") != "ok":
        raise RuntimeError(str(payload.get("message") or payload.get("code") or "fetch failed"))
    values = payload.get("values") or []
    requested = _requested_symbol()
    detail = "" if symbol == requested else f"stored via {symbol} (requested {requested})"
    rows: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        row = _row_from_value(value, symbol=symbol, requested=requested, detail=detail)
        if row:
            rows.append(row)
    return rows


def fetch_day(api_key: str, symbol: str, day: date) -> dict[str, Any] | None:
    iso = day.isoformat()
    payload = _call_time_series(api_key, symbol, outputsize=8)
    if payload.get("status") != "ok":
        raise RuntimeError(str(payload.get("message") or payload.get("code") or "fetch failed"))
    requested = _requested_symbol()
    for value in payload.get("values") or []:
        if not isinstance(value, dict):
            continue
        if _parse_day(value.get("datetime")) == iso:
            return _row_from_value(value, symbol=symbol, requested=requested)
    return None


def _merge_rows(path: Path, rows: list[dict[str, Any]]) -> int:
    added = 0
    for row in sorted(rows, key=lambda item: str(item.get("date") or "")):
        day = str(row.get("date") or "")
        if not day:
            continue
        if history_has_date(path, day):
            continue
        append_record(path, row)
        added += 1
    return added


def sync_brent_history(
    trading_date: date | None = None,
    *,
    data_dir: Path | None = None,
) -> BrentSyncResult:
    api_key = _api_key()
    if not api_key:
        return BrentSyncResult("unavailable", _requested_symbol(), "TWELVE_DATA_API_KEY not set")

    path = history_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    target = trading_date or date.today()

    try:
        symbol, resolve_detail = resolve_fetch_symbol(api_key)
    except RuntimeError as exc:
        return BrentSyncResult("unavailable", _requested_symbol(), str(exc))

    existing = load_json(path) or []
    if not isinstance(existing, list):
        existing = []

    if not existing:
        try:
            rows = fetch_days(api_key, symbol, outputsize=BACKFILL_DAYS)
        except RuntimeError as exc:
            return BrentSyncResult("unavailable", symbol, str(exc))
        added = _merge_rows(path, rows)
        detail = resolve_detail or f"backfilled {added} days"
        return BrentSyncResult("backfilled", symbol, detail, added)

    iso = target.isoformat()
    if history_has_date(path, iso):
        return BrentSyncResult("already_present", symbol, resolve_detail or iso)

    try:
        row = fetch_day(api_key, symbol, target)
    except RuntimeError as exc:
        return BrentSyncResult("unavailable", symbol, str(exc))
    if row is None:
        return BrentSyncResult(
            "already_present",
            symbol,
            f"no daily bar for {iso} yet (will retry next run)",
        )
    append_record(path, row)
    detail = resolve_detail or f"appended {iso}"
    return BrentSyncResult("saved", symbol, detail, 1)


def main() -> int:
    result = sync_brent_history()
    print(
        f"brent_history {result.status} symbol={result.symbol} "
        f"rows_added={result.rows_added} {result.detail}"
    )
    print(f"path={history_path()}")
    return 1 if result.status == "unavailable" else 0


if __name__ == "__main__":
    raise SystemExit(main())