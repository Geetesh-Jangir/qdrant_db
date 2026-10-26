"""Deterministic markdown tables for fund Q&A — scannable, minimal prose."""

from __future__ import annotations

import re
from typing import Any

from news_rag.fund_rupeestop_metrics import (
    LONG_HORIZON_PERIODS,
    asks_fund_category_average,
    periods_requested_in_question,
    resolve_display_periods,
)

_MISSING = "-"

_TABLE_LINE_RE = re.compile(r"^\s*\|")
_TABLE_SEP_RE = re.compile(r"^\s*\|[-:\s|]+\|\s*$")
_COMPOSER_SECTION_HEADINGS = (
    "Recent returns vs category",
    "Returns vs benchmark and category",
    "Holdings that drove the move",
    "Snapshot",
    "Category average",
    "Fund vs benchmark",
    "Returns vs benchmark",
)


def _cell(text: Any) -> str:
    """Safe table cell: no pipes or newlines; use hyphen for empty."""
    if text is None or text == "":
        return _MISSING
    s = str(text).replace("|", "/").replace("\n", " ").strip()
    return s if s else _MISSING


def _table_row(cells: list[str], column_count: int) -> str:
    """Fixed-width row so UI parsers never shift columns."""
    padded = (cells + [_MISSING] * column_count)[:column_count]
    return "| " + " | ".join(padded) + " |"


def _short_benchmark_label(name: str, max_len: int = 28) -> str:
    s = re.sub(r"\s+", " ", (name or "Benchmark").strip())
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def _holding_row_cells(row: dict[str, Any]) -> list[str]:
    name = row.get("name") or row.get("stock") or ""
    weight = row.get("weight_pct")
    if weight is None:
        weight = row.get("percentage")
    ret = row.get("return_pct")
    return [
        _cell(name),
        _cell(_fmt_weight(weight)),
        _cell(_fmt_pct(ret, signed=True)),
    ]


def _fmt_weight(val: Any) -> str:
    if val is None or val == "":
        return _MISSING
    try:
        return f"{float(val):.2f}%"
    except (TypeError, ValueError):
        return str(val)


def _fmt_pct(val: Any, *, signed: bool = True) -> str:
    if val is None or val == "":
        return _MISSING
    try:
        x = float(val)
    except (TypeError, ValueError):
        return str(val)
    if signed and x > 0:
        return f"+{x:.2f}%"
    return f"{x:.2f}%"


def _fmt_pp(val: Any) -> str:
    if val is None or val == "":
        return _MISSING
    try:
        x = float(val)
    except (TypeError, ValueError):
        return str(val)
    if x > 0:
        return f"+{x:.2f} pp"
    return f"{x:.2f} pp"


def _fmt_inr(val: Any) -> str:
    if val is None or val == "":
        return _MISSING
    try:
        return f"₹{float(val):,.2f}"
    except (TypeError, ValueError):
        return str(val)


def _fund_block(data_pack: dict[str, Any]) -> dict[str, Any] | None:
    for key, block in data_pack.items():
        if str(key).startswith("fund:") and isinstance(block, dict):
            return block
    return None


def _insights(block: dict[str, Any] | None) -> dict[str, Any]:
    if not block:
        return {}
    ins = block.get("fund_insights")
    if isinstance(ins, dict):
        return ins
    return {}


def _vs_block(block: dict[str, Any] | None, insights: dict[str, Any]) -> dict[str, Any] | None:
    if block and isinstance(block.get("vs_benchmark"), dict):
        return block["vs_benchmark"]
    if isinstance(insights.get("vs_benchmark"), dict):
        return insights["vs_benchmark"]
    return None


def _normalize_returns(rets: dict[str, Any] | None) -> dict[str, float]:
    out: dict[str, float] = {}
    if not isinstance(rets, dict):
        return out
    order = ("1W", "1M", "3M", "6M", "1Y", "3Y", "5Y", "YTD")
    for label in order:
        for k, v in rets.items():
            if v is None:
                continue
            if str(k).upper().replace("RETURN_", "") == label:
                try:
                    out[label] = float(v)
                except (TypeError, ValueError):
                    pass
                break
    return out


def build_fund_display_tables(
    data_pack: dict[str, Any],
    *,
    digest: dict[str, Any] | None = None,
    question: str = "",
) -> dict[str, str]:
    """Markdown tables the composer should reuse (weight/return only on holdings)."""
    digest = digest or {}
    block = _fund_block(data_pack)
    insights = _insights(block)
    vs = _vs_block(block, insights)
    snap = (block or {}).get("snapshot") if block else {}
    if not isinstance(snap, dict):
        snap = digest
    if not snap and not digest and not vs and not insights:
        return {}

    tables: dict[str, str] = {}
    name = (
        snap.get("fund_name")
        or snap.get("fund_short_name")
        or insights.get("fund_name")
        or digest.get("fund_name")
        or "Fund"
    )
    category = insights.get("category") or snap.get("category") or digest.get("category") or ""
    bench_label = (vs or {}).get("benchmark_name") or insights.get("benchmark_name") or digest.get(
        "benchmark_name"
    ) or snap.get("benchmark") or ""

    rets = insights.get("fund_returns_pct") or _normalize_returns(
        snap.get("returns") or digest.get("returns_pct")
    )
    cat_avg = insights.get("category_average_returns_pct") or digest.get("category_average_returns_pct") or {}
    comparison = insights.get("comparison_periods") or digest.get("comparison_periods") or {}

    requested = periods_requested_in_question(question)
    long_rows, short_rows = resolve_display_periods(requested)
    long_for_benchmark = long_rows if long_rows else list(LONG_HORIZON_PERIODS)

    if comparison:
        bl = _cell(_short_benchmark_label(str(bench_label or "Benchmark")))
        long_headers = [
            "Period",
            "Fund",
            "Benchmark",
            "vs bench (pp)",
            "Category avg",
            "vs category (pp)",
        ]
        ncol = len(long_headers)
        lines = [
            _table_row(long_headers, ncol),
            _table_row(["---"] * ncol, ncol),
        ]
        for period in long_for_benchmark:
            row = comparison.get(period)
            if not isinstance(row, dict):
                continue
            vs_cat = row.get("vs_category")
            if vs_cat is None and row.get("fund_return") is not None and row.get("category_average_return") is not None:
                vs_cat = round(
                    float(row["fund_return"]) - float(row["category_average_return"]),
                    2,
                )
            lines.append(
                _table_row(
                    [
                        _cell(period),
                        _cell(_fmt_pct(row.get("fund_return"))),
                        _cell(_fmt_pct(row.get("benchmark_return"))),
                        _cell(_fmt_pp(row.get("vs_benchmark"))),
                        _cell(_fmt_pct(row.get("category_average_return"))),
                        _cell(_fmt_pp(vs_cat)),
                    ],
                    ncol,
                )
            )
        if len(lines) > 2:
            tables["vs_benchmark_table"] = "\n".join(lines)

    if cat_avg and (asks_fund_category_average(question) or requested):
        ncol = 2
        lines = [_table_row(["Period", "Category avg"], ncol), _table_row(["---", "---"], ncol)]
        for period in long_rows:
            if period in cat_avg:
                lines.append(_table_row([_cell(period), _cell(_fmt_pct(cat_avg[period]))], ncol))
        if len(lines) > 2:
            tables["category_average_table"] = "\n".join(lines)

    short = insights.get("fund_returns_short_horizon_pct") or {}
    if not short and rets:
        short = {k: rets[k] for k in ("1M", "3M", "6M") if k in rets}
    if short_rows:
        short = {k: short[k] for k in short_rows if k in short}
    if short or cat_avg:
        short_headers = ["Period", "Fund", "Category avg", "vs category (pp)"]
        ncol = len(short_headers)
        lines = [_table_row(short_headers, ncol), _table_row(["---"] * ncol, ncol)]
        show_short = short_rows or ("1M", "3M", "6M")
        for period in show_short:
            fk = period
            ck = period.lower()
            fund_v = short.get(fk) or short.get(ck) or rets.get(fk)
            cat_v = cat_avg.get(fk) or cat_avg.get(ck)
            if fund_v is None and cat_v is None:
                continue
            vs_cat = None
            if fund_v is not None and cat_v is not None:
                vs_cat = round(float(fund_v) - float(cat_v), 2)
            lines.append(
                _table_row(
                    [
                        _cell(period),
                        _cell(_fmt_pct(fund_v) if fund_v is not None else None),
                        _cell(_fmt_pct(cat_v) if cat_v is not None else None),
                        _cell(_fmt_pp(vs_cat)),
                    ],
                    ncol,
                )
            )
        if len(lines) > 2:
            tables["short_horizon_vs_category_table"] = "\n".join(lines)

    nav = snap.get("nav") if snap.get("nav") is not None else digest.get("nav")
    nav_date = snap.get("nav_date") or digest.get("nav_date") or ""
    day = snap.get("day_change_pct")
    if day is None:
        day = digest.get("day_change_pct")
    hi = snap.get("high_52w") or digest.get("52_week_high")
    lo = snap.get("low_52w") or digest.get("52_week_low")

    snap_ncol = 2
    snap_lines = [_table_row(["Metric", "Value"], snap_ncol), _table_row(["---", "---"], snap_ncol)]
    if category:
        snap_lines.append(_table_row(["Category", _cell(category)], snap_ncol))
    if nav is not None:
        snap_lines.append(_table_row([f"NAV ({_cell(nav_date or 'latest')})", _cell(_fmt_inr(nav))], snap_ncol))
    if day is not None:
        snap_lines.append(_table_row(["Day change", _cell(_fmt_pct(day))], snap_ncol))
    if bench_label:
        snap_lines.append(_table_row(["Benchmark", _cell(bench_label)], snap_ncol))
    if hi is not None and lo is not None:
        try:
            nav_f = float(nav) if nav is not None else None
            hi_f = float(hi)
            lo_f = float(lo)
            snap_lines.append(_table_row(["52-week high", _cell(_fmt_inr(hi_f))], snap_ncol))
            snap_lines.append(_table_row(["52-week low", _cell(_fmt_inr(lo_f))], snap_ncol))
            if nav_f and hi_f > 0:
                from_high = (nav_f / hi_f - 1.0) * 100.0
                from_low = (nav_f / lo_f - 1.0) * 100.0 if lo_f > 0 else None
                snap_lines.append(_table_row(["vs 52W high", _cell(_fmt_pct(from_high))], snap_ncol))
                if from_low is not None:
                    snap_lines.append(_table_row(["vs 52W low", _cell(_fmt_pct(from_low))], snap_ncol))
        except (TypeError, ValueError):
            pass
    if len(snap_lines) > 2:
        tables["snapshot_table"] = "\n".join(snap_lines)

    attr = (block or {}).get("attribution") if block else None
    rows = []
    if isinstance(attr, dict):
        rows = list(attr.get("detractors") or []) + list(attr.get("contributors") or [])
        seen: set[str] = set()
        deduped = []
        for r in rows:
            n = str(r.get("name") or r.get("stock") or "")
            if n and n not in seen:
                seen.add(n)
                deduped.append(r)
        rows = deduped[:8]
    if rows:
        hold_ncol = 3
        hlines = [
            _table_row(["Holding", "Weight", "Holding return"], hold_ncol),
            _table_row(["---", "---", "---"], hold_ncol),
        ]
        for r in rows:
            hlines.append(_table_row(_holding_row_cells(r), hold_ncol))
        tables["holdings_move_table"] = "\n".join(hlines)

    if tables:
        tables["_title"] = str(name)
    return tables


_DISPLAY_SECTIONS: tuple[tuple[str, str], ...] = (
    ("short_horizon_vs_category_table", "### Recent returns vs category"),
    ("vs_benchmark_table", "### Returns vs benchmark and category"),
    ("holdings_move_table", "### Holdings that drove the move"),
    ("snapshot_table", "### Snapshot"),
    ("category_average_table", "### Category average"),
)


def format_display_tables_markdown(
    tables: dict[str, str],
    *,
    question: str = "",
    only_keys: frozenset[str] | None = None,
) -> str:
    """Single markdown block with blank lines between sections (safe for UI renderers)."""
    if not tables:
        return ""
    if only_keys is not None:
        tables = {k: v for k, v in tables.items() if k in only_keys or k == "_title"}
    if not any(k for k in tables if k != "_title"):
        return ""
    title = tables.get("_title")
    parts: list[str] = []
    if title:
        parts.append(f"## {_cell(title)}\n")
    requested = periods_requested_in_question(question)
    _, short_rows = resolve_display_periods(requested)
    prefer_short = bool(short_rows)
    order = list(_DISPLAY_SECTIONS)
    if prefer_short:
        order.sort(key=lambda x: 0 if x[0] == "short_horizon_vs_category_table" else 1)
    for key, heading in order:
        body = (tables.get(key) or "").strip()
        if not body:
            continue
        parts.append(f"{heading}\n\n{body}\n")
    return "\n".join(parts).strip()


def strip_markdown_tables_from_prose(text: str) -> str:
    """Remove markdown table blocks the composer may have added (we append canonical tables once)."""
    if not text:
        return text
    lines = text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _TABLE_LINE_RE.match(line):
            while i < len(lines) and _TABLE_LINE_RE.match(lines[i]):
                i += 1
            if out and out[-1].strip():
                out.append("")
            continue
        out.append(line)
        i += 1
    return "\n".join(out).strip()


def strip_composer_display_sections(prose: str) -> str:
    """Drop duplicate ### sections that mirror server-appended tables."""
    if not prose:
        return prose
    text = strip_markdown_tables_from_prose(prose)
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line.strip())
        if m:
            title = m.group(1).strip()
            if any(title.lower().startswith(h.lower()) for h in _COMPOSER_SECTION_HEADINGS):
                i += 1
                while i < len(lines) and not re.match(r"^#{2,3}\s+", lines[i].strip()):
                    i += 1
                continue
        out.append(line)
        i += 1
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def stitch_display_tables_into_answer(prose: str, tables: dict[str, str], *, question: str = "") -> str:
    """Append server-built tables once; composer writes narrative only."""
    block = format_display_tables_markdown(tables, question=question)
    if not block:
        return prose
    text = strip_composer_display_sections(prose or "")
    if block in text:
        return text
    disclaimer = "*For context only — not investment advice.*"
    if disclaimer.lower() in text.lower():
        idx = text.lower().rfind(disclaimer.lower())
        if idx >= 0:
            before = text[:idx].rstrip()
            after = text[idx:].lstrip()
            return f"{before}\n\n{block}\n\n{after}"
    return f"{text.rstrip()}\n\n{block}\n"


def normalize_user_facing_text(text: str) -> str:
    """Use '-' for missing values; soften common LLM table mistakes."""
    if not text:
        return text
    out = text
    out = re.sub(r"\bN/A\b", "-", out, flags=re.I)
    out = re.sub(r"\bn/a\b", "-", out)
    out = re.sub(r"—", "-", out)
    return out
