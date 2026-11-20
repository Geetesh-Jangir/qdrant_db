"""Lazy index over security-master-list.json for instrument → NSE ticker."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
_MASTER_PATH = _ROOT / "data" / "fund_holdings_aggregate" / "security-master-list.json"

_lock = threading.Lock()
_by_norm: dict[str, list[dict[str, Any]]] | None = None


def normalize_name(name: str) -> str:
    s = (name or "").lower()
    s = re.sub(r"\[.*?\]", " ", s)
    s = s.replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\bthe\b", "", s)
    s = re.sub(r"\benterprises\b", "enterprise", s)
    s = re.sub(r"\b(limited|ltd|ltd\.|co\.?|company|corporation|corp)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _pick_best_master(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None

    def score(r: dict[str, Any]) -> tuple[int, int, int]:
        sym = (r.get("symbol") or "").upper()
        st = (r.get("status") or "").lower()
        active = 1 if st == "active" else 0
        no_pp = 1 if not sym.endswith("PP") else 0
        has_idx = 1 if r.get("indiceName") else 0
        return (active, no_pp, has_idx)

    return max(rows, key=score)


def _load_index() -> dict[str, list[dict[str, Any]]]:
    global _by_norm
    if _by_norm is not None:
        return _by_norm
    with _lock:
        if _by_norm is not None:
            return _by_norm
        if not _MASTER_PATH.is_file():
            _by_norm = {}
            return _by_norm
        payload = json.loads(_MASTER_PATH.read_text(encoding="utf-8"))
        items = payload.get("items") if isinstance(payload, dict) else []
        _by_norm = load_master_index(list(items or []))
        return _by_norm


def load_master_index(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_norm: dict[str, list[dict[str, Any]]] = {}
    for row in items:
        if not isinstance(row, dict):
            continue
        key = normalize_name(str(row.get("companyName") or ""))
        if key:
            by_norm.setdefault(key, []).append(row)
    return by_norm


def lookup_master(by_norm: dict[str, list[dict[str, Any]]], instrument_name: str) -> dict[str, Any] | None:
    norm = normalize_name(instrument_name)
    if norm in by_norm:
        return _pick_best_master(by_norm[norm])
    candidates: list[tuple[int, dict[str, Any]]] = []
    for key, rows in by_norm.items():
        if norm in key or key in norm:
            picked = _pick_best_master(rows)
            if picked:
                candidates.append((max(len(norm), len(key)), picked))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def resolve_yf_ticker(symbol: str | None, scrip_code: str | None) -> list[str]:
    tickers: list[str] = []
    if symbol and str(symbol).strip():
        sym = str(symbol).strip().upper()
        if sym.endswith(".NS") or sym.endswith(".BO"):
            tickers.append(sym)
        else:
            tickers.append(f"{sym}.NS")
            tickers.append(f"{sym}.BO")
    if scrip_code and str(scrip_code).strip() and not tickers:
        sc = str(scrip_code).strip()
        if sc.isalpha():
            tickers.append(f"{sc.upper()}.NS")
    return tickers


def lookup_instrument(instrument_name: str) -> dict[str, Any] | None:
    by_norm = _load_index()
    row = lookup_master(by_norm, instrument_name)
    if not row:
        return None
    tickers = resolve_yf_ticker(row.get("symbol"), row.get("scripCode"))
    return {
        "instrument_name": instrument_name,
        "symbol": row.get("symbol"),
        "scrip_code": row.get("scripCode"),
        "tickers": tickers,
    }