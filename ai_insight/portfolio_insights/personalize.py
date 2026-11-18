"""Deterministic portfolio fund names appended after LLM headline stub ending in \"your\"."""

from __future__ import annotations

import re
import threading
import time
from typing import Any

from lib.portfolio_scope import match_holding_to_corpus_entity, normalize_sector_label, sector_query_for_label

_SUFFIX_STRIP = re.compile(
    r"\s*-\s*(?:growth|dividend|direct|regular).*$",
    re.I,
)

_fund_name_cache: dict[str, tuple[float, str]] = {}
_fund_name_lock = threading.Lock()


def fund_isins_from_row(row: dict[str, Any]) -> list[str]:
    """Fund scheme ISINs on a concentration row (fund_isins preferred; list isin as fallback)."""
    raw = row.get("fund_isins")
    if raw is None:
        raw = row.get("isin")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        text = str(item or "").strip().upper()
        if text and text not in out:
            out.append(text)
    return out


def _display_fund_name(name: str) -> str:
    text = _SUFFIX_STRIP.sub("", name).strip()
    text = re.sub(r"\s+", " ", text)
    return text.lower() if text.isascii() else text


def resolve_fund_display(isin: str) -> str:
    """Resolve fund_short_name via RupeeStop GET /api/v1/app/fund/{isin} (first ISIN only in practice)."""
    isin = str(isin or "").strip().upper()
    if not isin:
        return ""
    now = time.time()
    with _fund_name_lock:
        cached = _fund_name_cache.get(isin)
        if cached and now - cached[0] < 300:
            return cached[1]
    name = _fetch_fund_short_name(isin)
    if not name:
        try:
            from news_rag.fund_search import get_fund_index

            detail = get_fund_index().fetch_fund_detail_from_api(isin)
            if detail:
                ident = detail.get("identity") if isinstance(detail.get("identity"), dict) else {}
                data = detail if detail.get("fund_short_name") else {}
                name = str(
                    data.get("fund_short_name")
                    or ident.get("fund_short_name")
                    or data.get("fund_name")
                    or ident.get("fund_name")
                    or ""
                ).strip()
                if name:
                    name = _display_fund_name(name)
        except Exception:
            pass
    if not name:
        name = isin
    with _fund_name_lock:
        _fund_name_cache[isin] = (now, name)
    return name


def _fetch_fund_short_name(isin: str) -> str:
    try:
        import httpx

        from news_rag.config import get_settings

        settings = get_settings()
        base = str(getattr(settings, "rupeestop_backend_base", "") or "https://backend.rupeestop.com").rstrip("/")
        timeout = float(getattr(settings, "portfolio_http_timeout_sec", 15) or 15)
        url = f"{base}/api/v1/app/fund/{isin}"
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return ""
    data = payload.get("data") if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return ""
    ident = data.get("identity") if isinstance(data.get("identity"), dict) else {}
    raw = str(ident.get("fund_short_name") or data.get("fund_short_name") or ident.get("fund_name") or "").strip()
    return _display_fund_name(raw) if raw else ""


def _headline_ends_with_your(base: str) -> bool:
    tokens = base.rstrip().casefold().split()
    return bool(tokens) and tokens[-1] == "your"


def format_fund_tail(lead: str, others: int) -> str:
    """Fund name(s) only — LLM headline already ends with \"your\"."""
    lead = (lead or "").strip()
    if not lead:
        return ""
    if others <= 0:
        return f" {lead}"
    return f" {lead} and {others} others"


def append_personal_tail(
    base_headline: str,
    isins: list[str],
    *,
    seed: str,
) -> tuple[str, dict[str, Any]]:
    del seed  # reserved; fund tail is deterministic
    base = str(base_headline or "").strip()
    isins = [i for i in isins if i]
    meta: dict[str, Any] = {
        "lead_fund": None,
        "other_count": 0,
        "phrase": None,
        "resolved_isins": isins,
        "lead_isin": isins[0] if isins else None,
    }
    if not base or not isins:
        return base, meta

    lead = resolve_fund_display(isins[0])
    if not lead:
        return base, meta

    if not _headline_ends_with_your(base):
        base = f"{base.rstrip()} in your"

    others = max(0, len(isins) - 1)
    tail = format_fund_tail(lead, others)
    meta.update(
        {
            "lead_fund": lead,
            "other_count": others,
            "phrase": tail.strip(),
        }
    )
    return (base + tail).strip(), meta


def _sector_row_key(label: str) -> str:
    mapped = sector_query_for_label(label)
    if mapped:
        return mapped[0].casefold()
    return normalize_sector_label(label).casefold()


def sector_row_for_label(portfolio_raw: dict[str, Any], sector_label: str) -> dict[str, Any] | None:
    rows = portfolio_raw.get("sector_allocation") if isinstance(portfolio_raw.get("sector_allocation"), list) else []
    want = _sector_row_key(sector_label)
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("sector") or "").strip()
        if not name:
            continue
        if _sector_row_key(name) == want or name.casefold() == sector_label.casefold():
            return row
        if want in name.casefold() or name.casefold() in want:
            return row
    return None


def holding_row_for_instrument(portfolio_raw: dict[str, Any], instrument_name: str) -> dict[str, Any] | None:
    rows = portfolio_raw.get("top_holdings") if isinstance(portfolio_raw.get("top_holdings"), list) else []
    names = [
        str(row.get("instrument_name") or "").strip()
        for row in rows
        if isinstance(row, dict) and row.get("instrument_name")
    ]
    corpus = set(names)
    matched = match_holding_to_corpus_entity(instrument_name, corpus) if corpus else instrument_name
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("instrument_name") or "").strip()
        if not name:
            continue
        if name == matched or match_holding_to_corpus_entity(instrument_name, {name}) == name:
            return row
    return None


def personalize_card_headline(
    card: dict[str, Any],
    portfolio_raw: dict[str, Any],
    *,
    crn: str,
    match_key: str,
) -> dict[str, Any]:
    """Set headline_base and extend headline when fund_isins lists are present."""
    base = str(card.get("headline") or "").strip()
    out = {**card, "headline_base": base}
    row: dict[str, Any] | None = None
    meta = dict(card.get("match_meta") or {})
    if card.get("insight_id") == "sector_index_insights":
        row = sector_row_for_label(portfolio_raw, str(meta.get("sector") or match_key))
    elif card.get("insight_id") == "holding_insights":
        row = holding_row_for_instrument(portfolio_raw, str(meta.get("instrument_name") or match_key))

    isins = fund_isins_from_row(row or {})
    seed = f"{crn}:{match_key}"
    headline, tail_meta = append_personal_tail(base, isins, seed=seed)
    out["headline"] = headline
    if tail_meta.get("lead_fund"):
        meta["personalization"] = tail_meta
        out["match_meta"] = meta
    return out