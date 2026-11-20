"""Append one NSE FII/DII snapshot, or backfill a CSV. Exit 3 means not published yet."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from ai_insight.common.config import CommonConfig, load_config
from ai_insight.common.flows import history_path
from ai_insight.common.market_data import MarketResult, get_fii_dii_today
from ai_insight.common.store import load_json, save_json
from ai_insight.common.trading_calendar import is_trading_day

Status = Literal["saved", "already_present", "stale", "unavailable"]


@dataclass
class CollectResult:
    status: Status
    record: dict | None
    detail: str


@dataclass
class ImportReport:
    added: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)


def history_has_date(path: Path, day: str) -> bool:
    rows = load_json(path) or []
    return any(isinstance(row, dict) and str(row.get("date") or "") == day for row in rows)


def store_record_if_new(path: Path, record: dict) -> bool:
    day = str(record.get("date") or "")
    if not day or history_has_date(path, day):
        return False
    append_record(path, record)
    return True


def _ingest_nse_result(result: MarketResult, store: Path) -> CollectResult:
    if result.status not in {"ok", "stale"} or not result.data:
        return CollectResult("unavailable", None, result.detail or result.status)
    record = _record(result.data, result.source)
    if not record.get("date"):
        return CollectResult("unavailable", None, result.detail or "missing trade date")
    if history_has_date(store, str(record["date"])):
        return CollectResult("already_present", record, result.detail)
    store_record_if_new(store, record)
    detail = "" if result.status == "ok" else result.detail
    return CollectResult("saved", record, detail)


def prefetch_fii_dii(trading_date: date, *, config: CommonConfig | None = None) -> CollectResult:
    """Create-insights hook: always call NSE, refresh fii_dii_latest.json, append any new trade date."""
    cfg = config or load_config()
    if not is_trading_day(trading_date, holidays_path=cfg.holidays_path):
        return CollectResult("already_present", None, "not_a_trading_day")
    from ai_insight.data.nse_fii_dii import fetch_fii_dii_snapshot
    from ai_insight.data.run import write_fii_dii
    from news_pipeline.config import repo_root

    snap = fetch_fii_dii_snapshot()
    write_fii_dii(snap, repo_root())
    store = history_path(cfg.data_dir)
    result = get_fii_dii_today(trading_date.isoformat(), fetch=lambda: snap, config=cfg)
    return _ingest_nse_result(result, store)


def collect(trading_date: date, *, history_path: Path, fetch: Callable[[], Any] | None = None, config: CommonConfig | None = None) -> CollectResult:
    cfg = config or load_config()
    iso = trading_date.isoformat()
    if history_has_date(history_path, iso):
        return CollectResult("already_present", None, "")
    result = get_fii_dii_today(iso, fetch=fetch, config=cfg)
    return _ingest_nse_result(result, history_path)


def append_record(path: Path, record: dict) -> list[dict]:
    clean = {key: value for key, value in record.items() if not str(key).startswith("_")}
    clean.setdefault("provisional", True)
    rows = load_json(path) or []
    if not isinstance(rows, list):
        rows = []
    by_date = {str(row.get("date")): row for row in rows if isinstance(row, dict) and row.get("date")}
    day = str(clean["date"])
    previous = by_date.get(day)
    if previous is not None and previous != clean:
        rev = list(previous.get("revisions") or [])
        snapshot = {k: v for k, v in previous.items() if k != "revisions"}
        rev.append(snapshot)
        clean["revisions"] = rev[-5:]
    by_date[day] = clean
    ordered = [by_date[key] for key in sorted(by_date)]
    save_json(path, ordered)
    return ordered


def import_csv(csv_path: Path, history: Path) -> ImportReport:
    report = ImportReport()
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for line, row in enumerate(reader, start=2):
            parsed = _csv_row(row)
            if parsed is None:
                report.warnings.append(f"line {line}: could not read the row")
                report.skipped += 1
                continue
            if parsed.get("_warn"):
                report.warnings.append(f"line {line}: {parsed.pop('_warn')}")
            before = load_json(history) or []
            dates = {item.get("date") for item in before} if isinstance(before, list) else set()
            append_record(history, parsed)
            if parsed["date"] in dates:
                report.skipped += 1
            else:
                report.added += 1
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_insight.fii_dii_flow_narrative.collector")
    parser.add_argument("--date", default="", help="Trading day for single-day NSE collect (not needed for backfill modes).")
    parser.add_argument("--import-csv", default="")
    parser.add_argument("--backfill", action="store_true", help="Try NSE snapshot append for recent days (best effort).")
    parser.add_argument(
        "--backfill-stockezee",
        action="store_true",
        help="Append net-only StockeZee history for dates before full NSE rows exist.",
    )
    parser.add_argument("--stockezee-from", default="2026-11-01", help="Inclusive start date (ISO).")
    parser.add_argument("--stockezee-before", default="2026-11-13", help="Exclusive end date; NSE keeps this day onward.")
    args = parser.parse_args(argv)
    cfg = load_config()
    path = history_path(cfg.data_dir)
    if args.import_csv:
        report = import_csv(Path(args.import_csv), path)
        print(f"added={report.added} skipped={report.skipped} warnings={len(report.warnings)}")
        for warning in report.warnings:
            print("warning:", warning)
        return 0
    if args.backfill:
        from ai_insight.data.fii_dii_backfill import backfill_recent

        report = backfill_recent(path)
        print(f"backfill added={report.added} skipped={report.skipped}")
        return 0
    if args.backfill_stockezee:
        from ai_insight.data.fii_dii_backfill import backfill_stockezee_net

        report = backfill_stockezee_net(
            path,
            from_date=date.fromisoformat(args.stockezee_from),
            before_date=date.fromisoformat(args.stockezee_before),
        )
        print(f"stockezee added={report.added} skipped={report.skipped} warnings={len(report.warnings)}")
        for warning in report.warnings:
            print("warning:", warning)
        return 0 if report.added or not report.warnings else 1
    if not args.date:
        parser.error("--date is required unless using --import-csv, --backfill, or --backfill-stockezee")
    result = collect(date.fromisoformat(args.date), history_path=path, config=cfg)
    print(f"{result.status} {result.detail}".strip())
    if result.status == "unavailable":
        return 3
    if result.status in {"saved", "already_present"}:
        return 0
    return 1


def _record(data: dict | None, source: str) -> dict:
    data = data or {}
    def leg(name: str) -> dict:
        raw = data.get(name) or {}
        return {
            "buy": raw.get("buy_inr_crore"),
            "sell": raw.get("sell_inr_crore"),
            "net": raw.get("net_inr_crore"),
        }
    return {
        "date": str(data.get("trade_date") or ""),
        "fii": leg("fii"),
        "dii": leg("dii"),
        "source": source,
        "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _csv_row(row: dict) -> dict | None:
    from ai_insight.common.market_data import _iso_date

    day = _iso_date(str(row.get("date") or ""))
    if not day:
        return None
    try:
        fii_buy, fii_sell, fii_net = float(row["fii_buy"]), float(row["fii_sell"]), float(row["fii_net"])
        dii_buy, dii_sell, dii_net = float(row["dii_buy"]), float(row["dii_sell"]), float(row["dii_net"])
    except (KeyError, TypeError, ValueError):
        return None
    warn = ""
    if abs((fii_buy - fii_sell) - fii_net) > 1 or abs((dii_buy - dii_sell) - dii_net) > 1:
        warn = "net does not equal buy - sell"
    payload = {
        "date": day,
        "fii": {"buy": fii_buy, "sell": fii_sell, "net": fii_net},
        "dii": {"buy": dii_buy, "sell": dii_sell, "net": dii_net},
        "source": "csv",
        "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if warn:
        payload["_warn"] = warn
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
