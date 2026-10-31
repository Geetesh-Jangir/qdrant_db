"""RupeeStop fund metrics: vs-benchmark and category-average returns (authoritative)."""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any

import httpx

from news_rag.fund_search import _API_BASE_URL, resolve_canonical_isin

logger = logging.getLogger(__name__)

_VS_PERIODS_USE = frozenset({"1y", "3y", "5y"})
_CAT_AVG_PERIODS_USE = frozenset({"1m", "3m", "6m", "1y", "3y", "5y"})
LONG_HORIZON_PERIODS: tuple[str, ...] = ("1Y", "3Y", "5Y")
SHORT_HORIZON_PERIODS: tuple[str, ...] = ("1M", "3M", "6M")

_PERIOD_ALIASES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b1\s*(?:y|yr|year|years)\b", re.I), "1Y"),
    (re.compile(r"\b3\s*(?:y|yr|year|years)\b", re.I), "3Y"),
    (re.compile(r"\b5\s*(?:y|yr|year|years)\b", re.I), "5Y"),
    (re.compile(r"\b6\s*(?:m|mo|month|months)\b", re.I), "6M"),
    (re.compile(r"\b3\s*(?:m|mo|month|months)\b", re.I), "3M"),
    (re.compile(r"\b1\s*(?:m|mo|month|months)\b", re.I), "1M"),
    (re.compile(r"\bytd\b", re.I), "YTD"),
    (re.compile(r"\b1\s*w(?:eek)?\b", re.I), "1W"),
]

_vs_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_vs_lock = threading.Lock()
_VS_TTL_SEC = 3600.0


def _period_label(key: str) -> str:
    return str(key).strip().lower()


def _optional_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _period_words(count: str, unit: str) -> str:
    n = str(count).strip()
    kind = (unit or "").strip().lower()
    if kind.startswith("y"):
        word = "year"
    elif kind.startswith("m"):
        word = "month"
    elif kind.startswith("d"):
        word = "day"
    else:
        word = kind or "year"
    if n != "1":
        word += "s"
    return f"{n} {word}"


def summarize_exit_load(remarks: str) -> str:
    """Turn the API remark into one sentence. Empty when there is no remark."""
    text = re.sub(r"\s+", " ", remarks or "").strip()
    if not text:
        return ""
    matched = re.search(
        r"(\d+(?:\.\d+)?)\s*%\s+on or before\s+(\d+)\s*([A-Za-z]+).*?\bnil\b\s+after\s+(\d+)\s*([A-Za-z]+)",
        text,
        re.I,
    )
    if matched:
        pct, before_n, before_unit, after_n, after_unit = matched.groups()
        before = _period_words(before_n, before_unit)
        after = _period_words(after_n, after_unit)
        return f"Exit load is {pct}% if you leave within {before}, and nothing after {after}."
    if re.fullmatch(r"(?:nil|none|no exit load|0%?)", text, re.I):
        return "This fund has no exit load."
    return text


def parse_fund_costs(facts: dict[str, Any] | None) -> dict[str, Any]:
    """Expense ratio (TER) and exit-load remark from fund_facts."""
    block = facts if isinstance(facts, dict) else {}
    ter = block.get("ter_expense_ratio")
    if not isinstance(ter, dict):
        ter = block.get("expense_ratio") if isinstance(block.get("expense_ratio"), dict) else {}
    remarks = ""
    slabs = block.get("exit_load_slabs") or []
    if isinstance(slabs, list):
        for slab in slabs:
            if not isinstance(slab, dict):
                continue
            note = str(slab.get("remarks") or "").strip()
            if note:
                remarks = note
                break
    if not remarks:
        remarks = str(block.get("exit_load_remarks") or block.get("exit_load") or "").strip()
    return {
        "expense_ratio": {
            "regular": _optional_number(ter.get("regular")),
            "direct": _optional_number(ter.get("direct")),
            "as_on_date": str(ter.get("as_on_date") or "").strip(),
        },
        "exit_load_remarks": remarks,
        "exit_load_summary": summarize_exit_load(remarks),
        "aum": _optional_number(block.get("aum")),
        "aum_as_on_date": str(block.get("aum_as_on_date") or "").strip(),
    }


def expense_ratio_for_question(expense: dict[str, Any] | None, question: str) -> dict[str, Any]:
    """Regular plan unless the user asked for the direct plan."""
    src = expense if isinstance(expense, dict) else {}
    wants_direct = bool(re.search(r"\bdirect\b", question or "", re.I))
    out: dict[str, Any] = {}
    as_on = str(src.get("as_on_date") or "").strip()
    if as_on:
        out["as_on_date"] = as_on
    if wants_direct:
        if src.get("direct") is not None:
            out["direct"] = src["direct"]
            out["plan"] = "direct"
        return out
    if src.get("regular") is not None:
        out["regular"] = src["regular"]
        out["plan"] = "regular"
    return out


def normalize_category_average_returns(raw: dict[str, Any] | None) -> dict[str, float]:
    """From fund detail `ratios.category_averages.returns` (skip inception / 10y)."""
    if not isinstance(raw, dict):
        return {}
    block = raw.get("returns") if "returns" in raw and isinstance(raw.get("returns"), dict) else raw
    if not isinstance(block, dict):
        return {}
    out: dict[str, float] = {}
    for key, val in block.items():
        pk = _period_label(key)
        if pk not in _CAT_AVG_PERIODS_USE:
            continue
        if pk == "as_of":
            continue
        try:
            out[pk.upper()] = round(float(val), 2)
        except (TypeError, ValueError):
            continue
    return out


def fund_returns_from_detail(detail: dict[str, Any] | None) -> dict[str, float]:
    """Trailing returns from GET /fund/{isin} `returns` block (authoritative for fund)."""
    if not detail:
        return {}
    rets = detail.get("returns") if isinstance(detail.get("returns"), dict) else {}
    out: dict[str, float] = {}
    for pk in ("1w", "1m", "3m", "6m", "1y", "3y", "5y", "ytd"):
        val = rets.get(pk)
        if val is None:
            continue
        try:
            out[pk.upper()] = round(float(val), 2)
        except (TypeError, ValueError):
            continue
    return out


def periods_requested_in_question(question: str) -> list[str]:
    """Periods the user named; empty list means show default long table (1Y/3Y/5Y)."""
    q = question or ""
    if re.search(r"\b1\s*,\s*3\s*,\s*5\b", q) or re.search(r"\b1\s*,\s*3\s+and\s+5\b", q, re.I):
        return ["1Y", "3Y", "5Y"]
    found: list[str] = []
    for pattern, label in _PERIOD_ALIASES:
        if pattern.search(q) and label not in found:
            found.append(label)
    return found


def resolve_display_periods(
    requested: list[str],
    *,
    available_long: tuple[str, ...] = LONG_HORIZON_PERIODS,
    available_short: tuple[str, ...] = SHORT_HORIZON_PERIODS,
) -> tuple[list[str], list[str]]:
    """Pick rows to show; unknown horizons fall back to full 1Y/3Y/5Y long table."""
    if not requested:
        return list(available_long), []
    long_pick = [p for p in requested if p in available_long]
    short_pick = [p for p in requested if p in available_short]
    if not long_pick and not short_pick:
        return list(available_long), []
    if not long_pick and short_pick:
        return [], short_pick
    return long_pick or list(available_long), short_pick


def build_comparison_periods(
    detail: dict[str, Any] | None,
    vs_benchmark: dict[str, Any] | None,
    category_average_returns: dict[str, float] | None,
) -> dict[str, dict[str, Any]]:
    """1Y/3Y/5Y: fund from fund API; benchmark from vs-benchmark; category avg from fund API."""
    fund_rets = fund_returns_from_detail(detail)
    cat_avg = category_average_returns or {}
    vs_periods = (vs_benchmark or {}).get("periods") if isinstance(vs_benchmark, dict) else {}
    if not isinstance(vs_periods, dict):
        vs_periods = {}
    out: dict[str, dict[str, Any]] = {}
    for period in LONG_HORIZON_PERIODS:
        row: dict[str, Any] = {}
        if period in fund_rets:
            row["fund_return"] = fund_rets[period]
        vs_row = vs_periods.get(period) if isinstance(vs_periods.get(period), dict) else {}
        if isinstance(vs_row, dict) and vs_row.get("benchmark_return") is not None:
            row["benchmark_return"] = vs_row["benchmark_return"]
        if period in cat_avg:
            row["category_average_return"] = cat_avg[period]
        if row.get("fund_return") is not None and row.get("benchmark_return") is not None:
            row["vs_benchmark"] = round(
                float(row["fund_return"]) - float(row["benchmark_return"]),
                2,
            )
        elif isinstance(vs_row, dict) and vs_row.get("vs_benchmark") is not None:
            row["vs_benchmark"] = vs_row["vs_benchmark"]
        if row.get("fund_return") is not None and row.get("category_average_return") is not None:
            row["vs_category"] = round(
                float(row["fund_return"]) - float(row["category_average_return"]),
                2,
            )
        if row:
            out[period] = row
    return out


def normalize_vs_benchmark_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Parse GET /fund/{isin}/vs-benchmark — benchmark fields only (fund_return filled later from fund API)."""
    if not payload or not isinstance(payload, dict):
        return None
    data = payload.get("data") if payload.get("data") is not None else payload
    if not isinstance(data, dict):
        return None
    periods_raw = data.get("periods") or {}
    periods: dict[str, dict[str, Any]] = {}
    for pk, row in periods_raw.items():
        label = _period_label(pk)
        if label not in _VS_PERIODS_USE or not isinstance(row, dict):
            continue
        try:
            periods[label.upper()] = {
                "fund_return": _f(row.get("fund_return")),
                "benchmark_return": _f(row.get("benchmark_return")),
                "vs_benchmark": _f(row.get("vs_benchmark")),
                "peer_return": _f(row.get("peer_return")),
            }
        except (TypeError, ValueError):
            continue
    if not periods:
        return None
    bench_name = str(data.get("benchmark_name") or "").strip()
    return {
        "isin": str(data.get("isin") or "").strip().upper(),
        "fund_name": data.get("fund_short_name") or data.get("fund_name"),
        "benchmark_name": bench_name,
        "periods": periods,
        "as_on": data.get("as_on") if isinstance(data.get("as_on"), dict) else {},
    }


def _f(val: Any) -> float | None:
    if val is None:
        return None
    return round(float(val), 2)


def fetch_vs_benchmark(isin: str, *, timeout: float = 12.0, use_cache: bool = True) -> dict[str, Any] | None:
    isin_clean = resolve_canonical_isin((isin or "").strip().upper())
    if not isin_clean:
        return None
    now = time.time()
    if use_cache:
        with _vs_lock:
            hit = _vs_cache.get(isin_clean)
            if hit and hit[0] > now:
                return hit[1]

    url = f"{_API_BASE_URL}/{isin_clean}/vs-benchmark"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning("vs-benchmark API status %s for %s", resp.status_code, isin_clean)
                return None
            payload = resp.json()
    except Exception as exc:
        logger.warning("vs-benchmark fetch failed for %s: %s", isin_clean, exc)
        return None

    normalized = normalize_vs_benchmark_payload(payload)
    if normalized and use_cache:
        with _vs_lock:
            _vs_cache[isin_clean] = (now + _VS_TTL_SEC, normalized)
    return normalized


def merge_fund_insight_metrics(
    detail: dict[str, Any] | None,
    *,
    vs_benchmark: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Single block for evidence / DISPLAY from catalog detail + optional vs-benchmark API."""
    if not detail:
        return {}
    out: dict[str, Any] = {
        "isin": detail.get("isin"),
        "fund_name": detail.get("fund_short_name") or detail.get("fund_name"),
        "category": detail.get("category"),
        "scheme_benchmark_name": detail.get("benchmark"),
    }
    fund_rets = fund_returns_from_detail(detail)
    if fund_rets:
        out["fund_returns_pct"] = fund_rets
        short_horizon = {k: fund_rets[k] for k in SHORT_HORIZON_PERIODS if k in fund_rets}
        if short_horizon:
            out["fund_returns_short_horizon_pct"] = short_horizon

    cat_avg = detail.get("category_average_returns")
    if isinstance(cat_avg, dict) and cat_avg:
        out["category_average_returns_pct"] = cat_avg

    if vs_benchmark:
        out["vs_benchmark"] = vs_benchmark
        out["benchmark_name"] = vs_benchmark.get("benchmark_name") or out.get("scheme_benchmark_name")

    comparison = build_comparison_periods(detail, vs_benchmark, cat_avg if isinstance(cat_avg, dict) else None)
    if comparison:
        out["comparison_periods"] = comparison
    return out


def asks_fund_category_average(question: str) -> bool:
    q = (question or "").strip()
    if not q:
        return False
    if not re.search(r"\bfunds?\b", q, re.I) and not re.search(r"\bisin\b", q, re.I):
        from news_rag.domain_intake import question_mentions_fund_scheme

        if not question_mentions_fund_scheme(q):
            return False
    return bool(
        re.search(
            r"\bcategory\s+(?:avg|average|mean)\b|\b(?:avg|average)\s+(?:return\s+)?(?:of\s+)?(?:the\s+)?category\b",
            q,
            re.I,
        )
    )


def asks_category_performance(question: str) -> bool:
    """How the fund's category is doing — not a sector screen or a random fund list."""
    q = (question or "").strip()
    if not q or not re.search(r"\bcategory\b", q, re.I):
        return False
    if asks_fund_category_average(q):
        return True
    if not re.search(
        r"\b(?:perform|performance|performing|doing|fared|return(?:s|ed)?)\b",
        q,
        re.I,
    ):
        return False
    if re.search(r"\bsector\b", q, re.I):
        return False
    from news_rag.tools import asks_funds_with_sector_exposure

    if asks_funds_with_sector_exposure(q):
        return False
    return True
