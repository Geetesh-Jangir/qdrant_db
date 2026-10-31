"""Deterministic markdown tables for fund Q&A — scannable, minimal prose."""

from __future__ import annotations

import re
from typing import Any

from news_rag.insight.contracts import AnswerMode
from news_rag.fund_rupeestop_metrics import (
    LONG_HORIZON_PERIODS,
    asks_fund_category_average,
    periods_requested_in_question,
    resolve_display_periods,
)

_MISSING = "-"
_RETURN_ORDER = ("1D", "1W", "1M", "3M", "6M", "9M", "YTD", "1Y", "2Y", "3Y", "5Y")
_CAVEAT_RE = re.compile(
    r"unexplained|cannot be stated|cannot be assessed|does not show a benchmark|"
    r"does not show a category|missing feed|no fund-vs-benchmark|"
    r"benchmark comparison is incomplete|gap to the index|"
    r"leaving most of the (?:fall|move|drop)|"
    r"not in the data|cannot be compared|no news|are not in the data|so it cannot|"
    r"not available in (?:this|the) data|cannot be reported|no drawdown episodes|"
    r"drawdown history is not|are not recorded|does not include|not available here|"
    r"holding-level sizing|treated as context|not a measured driver|"
    r"does not show how much|only context|was not included|"
    r"not a top-five|not a top five|top-five holding|cannot be measured|"
    r"does not show a .{0,40}weight|"
    r"no return figures|cannot be broken down|"
    r"only (?:have|has) one snapshot|earlier reading to compare|"
    r"less than before|cannot show whether|can't show whether|"
    r"supports reading the current risk|but not a trend|"
    r"the data here cannot show",
    re.I,
)
_LEAK_RE = re.compile(
    r"\b(?:claude|haiku|gemini|gpt-\d|qdrant|langgraph)\b|"
    r"backend\.rupeestop\.com|/api/v1/|"
    r"\b(?:get_fund_data|get_portfolio_data|search_financial_news)\b|"
    r"\b(?:sharpe|sortino)\b",
    re.I,
)

_TABLE_LINE_RE = re.compile(r"^\s*\|")
_TABLE_SEP_RE = re.compile(r"^\s*\|[-:\s|]+\|\s*$")
_COMPOSER_SECTION_HEADINGS = (
    "Returns",
    "Recent returns vs category",
    "Returns vs benchmark",
    "Returns vs category",
    "Returns vs benchmark and category",
    "Holdings that drove the move",
    "Snapshot",
    "Fund basics",
    "The fund",
    "Recent performance context",
    "Category average",
    "Fund vs benchmark",
    "Top holdings",
    "Top sectors",
)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _comparison_pair_ok(fund_return: Any, peer_return: Any) -> bool:
    """A comparison needs both numbers. All-zero pairs are an empty API feed."""
    fund = _as_float(fund_return)
    peer = _as_float(peer_return)
    if fund is None or peer is None:
        return False
    if fund == 0.0 and peer == 0.0:
        return False
    return True


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


def _weight_pct(row: dict[str, Any]) -> float | None:
    for key in ("weight_pct", "percentage", "weight"):
        val = row.get(key)
        if val is None or val == "":
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return None


def _labeled_mix_rows(rows: Any) -> list[tuple[str, float]]:
    if not isinstance(rows, list):
        return []
    out: list[tuple[str, float]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or row.get("sector") or row.get("name") or "").strip()
        pct = _weight_pct(row)
        if label and pct is not None:
            out.append((label, pct))
    return out


def _composition_table_markdown(
    risk: dict[str, Any],
    portfolio: dict[str, Any],
    *,
    fund_name: str = "Fund",
    top_n: int = 5,
) -> str:
    """Asset mix, market-cap mix, and top-holdings weight sum — deterministic for compose/DISPLAY."""
    assets = _labeled_mix_rows(risk.get("assets"))
    caps = _labeled_mix_rows(risk.get("market_cap"))
    holdings = [h for h in (portfolio.get("holdings") or []) if isinstance(h, dict)]
    if not assets and not caps and not holdings:
        return ""

    lines: list[str] = []
    ncol = 2
    if assets:
        lines.append("**Asset mix**")
        lines.append(_table_row(["Asset", "Weight"], ncol))
        lines.append(_table_row(["---", "---"], ncol))
        for label, pct in assets:
            lines.append(_table_row([_cell(label), _cell(_fmt_weight(pct))], ncol))
        lines.append("")

    if caps:
        lines.append("**Market cap mix**")
        lines.append(_table_row(["Cap bucket", "Weight"], ncol))
        lines.append(_table_row(["---", "---"], ncol))
        for label, pct in caps:
            lines.append(_table_row([_cell(label), _cell(_fmt_weight(pct))], ncol))
        lines.append("")

    if holdings:
        shown = holdings[: max(1, top_n)]
        weights = [w for w in (_weight_pct(h) for h in shown) if w is not None]
        if weights:
            total = round(sum(weights), 2)
            as_on = str(portfolio.get("as_on") or "").strip()
            suffix = f" (portfolio as on {as_on})" if as_on else ""
            lines.append(
                f"The **top {len(weights)} holdings** together make up **{total:.2f}%** of the fund{suffix}."
            )
    return "\n".join(line for line in lines if line is not None).strip()


def _table_body_row_count(body: str) -> int:
    """Data rows in a markdown table (exclude header and separator)."""
    rows = 0
    for line in (body or "").splitlines():
        if not _TABLE_LINE_RE.match(line):
            continue
        if _TABLE_SEP_RE.match(line):
            continue
        rows += 1
    return max(0, rows - 1)


def _assess_table_quality(key: str, body: str) -> str:
    body = (body or "").strip()
    if not body:
        return "empty"
    data_rows = _table_body_row_count(body)
    if key == "composition_table":
        if data_rows >= 4 and ("Equity" in body or "equity" in body.lower()):
            return "complete"
        if data_rows >= 1:
            return "partial"
        return "empty"
    if key in ("portfolio_holdings_table", "portfolio_sectors_table"):
        if data_rows >= 3:
            return "complete"
        if data_rows >= 1:
            return "partial"
        return "empty"
    if key == "fund_returns_table":
        return "complete" if data_rows >= 2 else ("partial" if data_rows else "empty")
    return "complete" if data_rows else "partial"


def summarize_tables_for_composer(
    data_pack: dict[str, Any],
    display_tables: dict[str, str],
) -> dict[str, Any]:
    """Structured portfolio facts for composer prose (numbers users should see first)."""
    fund = _fund_block(data_pack) or {}
    risk = fund.get("risk") if isinstance(fund.get("risk"), dict) else {}
    portfolios = _portfolio_blocks(data_pack)
    port = portfolios[0] if portfolios else {}

    asset_mix = [
        {"label": label, "weight_pct": round(pct, 2)}
        for label, pct in _labeled_mix_rows(risk.get("assets"))
    ]
    cap_mix = [
        {"label": label, "weight_pct": round(pct, 2)}
        for label, pct in _labeled_mix_rows(risk.get("market_cap"))
    ]

    top_holdings: list[dict[str, Any]] = []
    for row in (port.get("holdings") or [])[:5]:
        if not isinstance(row, dict):
            continue
        name = str(row.get("company_name") or row.get("name") or "").strip()
        weight = _weight_pct(row)
        if name and weight is not None:
            top_holdings.append({"name": name, "weight_pct": round(weight, 2)})

    top_sectors: list[dict[str, Any]] = []
    for row in (port.get("sectors") or [])[:5]:
        if not isinstance(row, dict):
            continue
        label = _sector_label(row)
        weight = _weight_pct(row)
        if label and weight is not None:
            top_sectors.append({"sector": label, "weight_pct": round(weight, 2)})

    top_sum: float | None = None
    if top_holdings:
        top_sum = round(sum(float(h["weight_pct"]) for h in top_holdings), 2)

    table_quality: dict[str, str] = {}
    for key, body in (display_tables or {}).items():
        if key.startswith("_"):
            continue
        table_quality[key] = _assess_table_quality(key, body)

    name = str(
        fund.get("fund_name")
        or port.get("fund_name")
        or display_tables.get("_title")
        or ""
    ).strip()

    if not (asset_mix or cap_mix or top_holdings or top_sectors):
        return {"fund_name": name, "table_quality": table_quality}

    out: dict[str, Any] = {
        "fund_name": name,
        "portfolio_as_on": str(port.get("as_on") or "").strip(),
        "asset_mix": asset_mix,
        "market_cap_mix": cap_mix,
        "top_holdings": top_holdings,
        "top_sectors": top_sectors,
        "table_quality": table_quality,
    }
    mid_small = _as_float(risk.get("smaller_companies_pct"))
    if mid_small is not None:
        out["mid_small_cap_combined_pct"] = round(mid_small, 2)
    if top_sum is not None:
        out["top_holdings_weight_sum_pct"] = top_sum
        out["top_holdings_count"] = len(top_holdings)
    return out


def _sector_label(row: dict[str, Any]) -> str:
    return str(row.get("sector") or row.get("sector_label") or row.get("name") or "").strip()


TABLES_APPEND_RE = re.compile(r"<!--\s*TABLES_APPEND:\s*([^>]+?)\s*-->", re.I)


def parse_tables_append_directive(text: str) -> tuple[str, frozenset[str] | None]:
    """Extract composer table plan. None = keep policy default tables."""
    match = TABLES_APPEND_RE.search(text or "")
    if not match:
        return (text or "").strip(), None
    raw = match.group(1).strip().lower()
    cleaned = TABLES_APPEND_RE.sub("", text or "").strip()
    if raw in ("default", "policy", "all", "*"):
        return cleaned, None
    if raw in ("none", "skip", "-", "no"):
        return cleaned, frozenset()
    keys = frozenset(part.strip() for part in raw.split(",") if part.strip())
    return cleaned, keys


def filter_display_tables_by_decision(
    tables: dict[str, str],
    decision: frozenset[str] | None,
) -> dict[str, str]:
    if decision is None:
        return tables
    if not decision:
        return {_k: tables[_k] for _k in ("_title",) if _k in tables}
    out: dict[str, str] = {}
    if tables.get("_title"):
        out["_title"] = tables["_title"]
    for key in decision:
        body = tables.get(key)
        if not body:
            continue
        out[key] = body
        heading = tables.get(f"_heading_{key}")
        if heading:
            out[f"_heading_{key}"] = heading
    return out


def strip_empty_bold_sections(prose: str) -> str:
    """Remove **Asset mix**-style labels with no following content."""
    if not prose:
        return prose
    lines = prose.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        bold = re.match(r"^\s*\*\*(.+?)\*\*\s*$", line.strip())
        if bold:
            j = i + 1
            has_content = False
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt:
                    j += 1
                    continue
                if re.match(r"^\*\*.+\*\*\s*$", nxt) or re.match(r"^#{1,3}\s+", nxt):
                    break
                if _TABLE_LINE_RE.match(nxt):
                    j += 1
                    continue
                has_content = True
                break
            if not has_content:
                i += 1
                continue
        out.append(line)
        i += 1
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


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


def _portfolio_blocks(data_pack: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for key, block in data_pack.items():
        if str(key).startswith("portfolio:") and isinstance(block, dict):
            blocks.append(block)
        elif isinstance(block, dict) and isinstance(block.get("portfolio"), dict):
            blocks.append(block["portfolio"])
    return blocks


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
    portfolios = _portfolio_blocks(data_pack)
    if not snap and not digest and not vs and not insights and not portfolios:
        return {}

    tables: dict[str, str] = {}
    portfolio_name = ""
    if portfolios:
        portfolio_name = str(portfolios[0].get("fund_name") or "").strip()
    name = (
        snap.get("fund_name")
        or snap.get("fund_short_name")
        or insights.get("fund_name")
        or digest.get("fund_name")
        or portfolio_name
        or "Fund"
    )
    category = insights.get("category") or snap.get("category") or digest.get("category") or ""
    bench_label = (vs or {}).get("benchmark_name") or insights.get("benchmark_name") or digest.get(
        "benchmark_name"
    ) or snap.get("benchmark") or ""

    rets = insights.get("fund_returns_pct") or _normalize_returns(
        snap.get("returns") or digest.get("returns_pct")
    )
    returns_by_period: dict[str, Any] = {}
    if isinstance(rets, dict):
        for key, val in rets.items():
            if _as_float(val) is None:
                continue
            returns_by_period[str(key).upper()] = val
    ordered = [p for p in _RETURN_ORDER if p in returns_by_period]
    ordered.extend(p for p in returns_by_period if p not in ordered)
    if ordered:
        ncol = 2
        lines = [_table_row(["Period", "Return"], ncol), _table_row(["---", "---"], ncol)]
        for period in ordered:
            lines.append(_table_row([period, _cell(_fmt_pct(returns_by_period[period]))], ncol))
        tables["fund_returns_table"] = "\n".join(lines)
    cat_avg = insights.get("category_average_returns_pct") or digest.get("category_average_returns_pct") or {}
    comparison = insights.get("comparison_periods") or digest.get("comparison_periods") or {}

    requested = periods_requested_in_question(question)
    long_rows, short_rows = resolve_display_periods(requested)
    long_for_benchmark = long_rows if long_rows else list(LONG_HORIZON_PERIODS)

    peer_rows = [row for row in comparison.values() if isinstance(row, dict)] if comparison else []
    has_benchmark = any(
        _comparison_pair_ok(row.get("fund_return"), row.get("benchmark_return")) for row in peer_rows
    )
    has_category = any(
        _comparison_pair_ok(row.get("fund_return"), row.get("category_average_return")) for row in peer_rows
    )
    if has_benchmark or has_category:
        long_headers = ["Period", "Fund"]
        if has_benchmark:
            long_headers.extend(["Benchmark", "vs bench (pp)"])
        if has_category:
            long_headers.extend(["Category avg", "vs category (pp)"])
        ncol = len(long_headers)
        lines = [
            _table_row(long_headers, ncol),
            _table_row(["---"] * ncol, ncol),
        ]
        for period in long_for_benchmark:
            row = comparison.get(period)
            if not isinstance(row, dict):
                continue
            bench_v = row.get("benchmark_return")
            cat_v = row.get("category_average_return")
            fund_v = row.get("fund_return")
            bench_ok = has_benchmark and _comparison_pair_ok(fund_v, bench_v)
            cat_ok = has_category and _comparison_pair_ok(fund_v, cat_v)
            if not bench_ok and not cat_ok:
                continue
            vs_cat = row.get("vs_category")
            if vs_cat is None and row.get("fund_return") is not None and cat_v is not None:
                vs_cat = round(float(row["fund_return"]) - float(cat_v), 2)
            cells = [_cell(period), _cell(_fmt_pct(fund_v))]
            if has_benchmark:
                cells.extend([
                    _cell(_fmt_pct(bench_v) if bench_ok else None),
                    _cell(_fmt_pp(row.get("vs_benchmark")) if bench_ok else None),
                ])
            if has_category:
                cells.extend([
                    _cell(_fmt_pct(cat_v) if cat_ok else None),
                    _cell(_fmt_pp(vs_cat) if cat_ok else None),
                ])
            lines.append(_table_row(cells, ncol))
        if len(lines) > 2:
            tables["vs_benchmark_table"] = "\n".join(lines)
            if has_benchmark and has_category:
                tables["_heading_vs_benchmark_table"] = "### Returns vs benchmark and category"
            elif has_benchmark:
                tables["_heading_vs_benchmark_table"] = "### Returns vs benchmark"
            else:
                tables["_heading_vs_benchmark_table"] = "### Returns vs category"

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
    show_short = short_rows or ("1M", "3M", "6M")
    short_pairs: list[tuple[str, Any, Any]] = []
    for period in show_short:
        fund_v = short.get(period) or short.get(period.lower()) or rets.get(period)
        cat_v = cat_avg.get(period) or cat_avg.get(period.lower())
        if cat_v is None and isinstance(comparison.get(period), dict):
            cat_v = comparison[period].get("category_average_return")
        if cat_v is not None:
            short_pairs.append((period, fund_v, cat_v))
    if short_pairs:
        short_headers = ["Period", "Fund", "Category avg", "vs category (pp)"]
        ncol = len(short_headers)
        lines = [_table_row(short_headers, ncol), _table_row(["---"] * ncol, ncol)]
        for period, fund_v, cat_v in short_pairs:
            vs_cat = None
            if fund_v is not None and cat_v is not None:
                vs_cat = round(float(fund_v) - float(cat_v), 2)
            lines.append(
                _table_row(
                    [
                        _cell(period),
                        _cell(_fmt_pct(fund_v) if fund_v is not None else None),
                        _cell(_fmt_pct(cat_v)),
                        _cell(_fmt_pp(vs_cat)),
                    ],
                    ncol,
                )
            )
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
    expense = snap.get("expense_ratio") if isinstance(snap.get("expense_ratio"), dict) else {}
    if expense.get("regular") is not None:
        ratio = f"{float(expense['regular']):.2f}%"
        if expense.get("as_on_date"):
            ratio = f"{ratio} (as on {expense['as_on_date']})"
        snap_lines.append(_table_row(["Expense ratio (regular)", _cell(ratio)], snap_ncol))
    elif expense.get("direct") is not None:
        ratio = f"{float(expense['direct']):.2f}%"
        if expense.get("as_on_date"):
            ratio = f"{ratio} (as on {expense['as_on_date']})"
        snap_lines.append(_table_row(["Expense ratio (direct)", _cell(ratio)], snap_ncol))
    exit_load = str(snap.get("exit_load_summary") or "").strip()
    if exit_load:
        snap_lines.append(_table_row(["Exit load", _cell(exit_load)], snap_ncol))
    if snap.get("aum") is not None:
        aum_text = f"Rs {float(snap['aum']):,.2f} crore"
        if snap.get("aum_as_on_date"):
            aum_text = f"{aum_text} (as on {snap['aum_as_on_date']})"
        snap_lines.append(_table_row(["AUM", _cell(aum_text)], snap_ncol))
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
        returns = snap.get("returns") if isinstance(snap.get("returns"), dict) else {}
        month = returns.get("1M")
        if month is None:
            month = snap.get("window_pct")
        fact_lines = [_table_row(["Metric", "Value"], snap_ncol), _table_row(["---", "---"], snap_ncol)]
        if category:
            fact_lines.append(_table_row(["Category", _cell(category)], snap_ncol))
        if bench_label:
            fact_lines.append(_table_row(["Benchmark", _cell(bench_label)], snap_ncol))
        if nav is not None:
            fact_lines.append(_table_row([f"NAV ({_cell(nav_date or 'latest')})", _cell(_fmt_inr(nav))], snap_ncol))
        if month is not None:
            fact_lines.append(_table_row(["1 month", _cell(_fmt_pct(month, signed=True))], snap_ncol))
        if expense.get("regular") is not None:
            ratio = f"{float(expense['regular']):.2f}%"
            if expense.get("as_on_date"):
                ratio = f"{ratio} (as on {expense['as_on_date']})"
            fact_lines.append(_table_row(["Expense ratio", _cell(ratio)], snap_ncol))
        if snap.get("aum") is not None:
            aum_text = f"Rs {float(snap['aum']):,.2f} crore"
            if snap.get("aum_as_on_date"):
                aum_text = f"{aum_text} (as on {snap['aum_as_on_date']})"
            fact_lines.append(_table_row(["AUM", _cell(aum_text)], snap_ncol))
        if exit_load:
            fact_lines.append(_table_row(["Exit load", _cell(exit_load)], snap_ncol))
        if len(fact_lines) > 2:
            tables["fund_facts_table"] = "\n".join(fact_lines)

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

    risk = (block or {}).get("risk") if isinstance(block, dict) else {}
    portfolio_block = portfolios[0] if portfolios else {}
    composition = _composition_table_markdown(
        risk if isinstance(risk, dict) else {},
        portfolio_block if isinstance(portfolio_block, dict) else {},
        fund_name=str(name),
    )
    if composition:
        tables["composition_table"] = composition
        tables["_heading_composition_table"] = f"### What {name} is made of"

    for block in portfolios:
        holdings = [h for h in (block.get("holdings") or []) if isinstance(h, dict)]
        if holdings and "portfolio_holdings_table" not in tables:
            ncol = 2
            lines = [_table_row(["Holding", "Weight"], ncol), _table_row(["---", "---"], ncol)]
            for h in holdings[:8]:
                name_h = h.get("name") or h.get("company_name")
                weight = h.get("weight_pct") if h.get("weight_pct") is not None else h.get("percentage")
                lines.append(_table_row([_cell(name_h), _cell(_fmt_pct(weight, signed=False))], ncol))
            if len(lines) > 2:
                tables["portfolio_holdings_table"] = "\n".join(lines)
        sectors = [s for s in (block.get("sectors") or []) if isinstance(s, dict)]
        if sectors and "portfolio_sectors_table" not in tables:
            ncol = 2
            lines = [_table_row(["Sector", "Weight"], ncol), _table_row(["---", "---"], ncol)]
            for s in sectors[:8]:
                label = s.get("sector") or s.get("name")
                weight = s.get("weight_pct") if s.get("weight_pct") is not None else s.get("percentage")
                lines.append(_table_row([_cell(label), _cell(_fmt_pct(weight, signed=False))], ncol))
            if len(lines) > 2:
                tables["portfolio_sectors_table"] = "\n".join(lines)

    if tables:
        tables["_title"] = str(name)
    return tables


_DISPLAY_SECTIONS: tuple[tuple[str, str], ...] = (
    ("composition_table", "### What the fund is made of"),
    ("fund_returns_table", "### Returns"),
    ("short_horizon_vs_category_table", "### Recent returns vs category"),
    ("vs_benchmark_table", "### Returns vs benchmark and category"),
    ("holdings_move_table", "### Holdings that drove the move"),
    ("portfolio_holdings_table", "### Top holdings"),
    ("portfolio_sectors_table", "### Top sectors"),
    ("snapshot_table", "### Snapshot"),
    ("fund_facts_table", "### The fund"),
    ("category_average_table", "### Category average"),
    ("drawdown_table", "### Drawdown"),
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
        heading = str(tables.get(f"_heading_{key}") or heading)
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
            title_l = title.lower()
            duplicate = any(title_l.startswith(h.lower()) for h in _COMPOSER_SECTION_HEADINGS)
            duplicate = duplicate or "is made of" in title_l
            if duplicate:
                i += 1
                while i < len(lines) and not re.match(r"^#{2,3}\s+", lines[i].strip()):
                    i += 1
                continue
        out.append(line)
        i += 1
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def strip_missing_data_caveats(prose: str) -> str:
    """Drop sentences that apologise for missing comparisons or unexplained holdings."""
    kept: list[str] = []
    for line in (prose or "").splitlines():
        if not line.strip() or line.strip().startswith("#") or _TABLE_LINE_RE.search(line):
            if line.strip().startswith("#") and _CAVEAT_RE.search(line):
                continue
            kept.append(line)
            continue
        parts = re.split(r"(?<=[.!?])\s+", line)
        clean = [part for part in parts if part and not _CAVEAT_RE.search(part)]
        if clean:
            kept.append(" ".join(clean))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def strip_private_leaks(prose: str) -> str:
    """Drop a sentence that names the model, an endpoint, a tool, or a rating input."""
    kept: list[str] = []
    for line in (prose or "").splitlines():
        parts = re.split(r"(?<=[.!?])\s+", line)
        clean = [part for part in parts if part and not _LEAK_RE.search(part)]
        if clean:
            kept.append(" ".join(clean))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def strip_empty_table_pointers(prose: str, tables: dict[str, str] | None = None) -> str:
    """Drop 'see the table below' when no returns table is actually attached."""
    tables = tables or {}
    has_returns = any(
        str(tables.get(key) or "").strip()
        for key in ("fund_returns_table", "short_horizon_vs_category_table", "vs_benchmark_table")
    )
    if has_returns:
        return prose
    kept: list[str] = []
    for line in (prose or "").splitlines():
        if re.search(r"see the table below", line, re.I):
            continue
        kept.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def strip_context_disclaimer(prose: str) -> str:
    """Drop the closing 'for context only' line, with either dash."""
    text = re.sub(
        r"(?im)^[ \t]*\*?For context only\s+[-—–]\s+not investment advice\.?\*?[ \t]*\n?",
        "",
        prose or "",
    )
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def stitch_display_tables_into_answer(prose: str, tables: dict[str, str], *, question: str = "") -> str:
    """Append server-built tables once; composer writes narrative only."""
    block = format_display_tables_markdown(tables, question=question)
    cleaned = strip_empty_table_pointers(
        strip_missing_data_caveats(
            strip_empty_bold_sections(strip_composer_display_sections(prose or ""))
        ),
        tables,
    )
    return strip_context_disclaimer(_insert_before_disclaimer(cleaned, block))


_PUBLISHER_TAIL = re.compile(
    r"\s+[-–—|]\s+(?:the\s+)?(?:"
    r"[\w.-]+\.(?:com|in|co\.in)"
    r"|business\s*line|live\s*mint|economic\s+times|moneycontrol|cnbc(?:\s*tv18)?"
    r"|business\s+standard|financial\s+express|reuters|bloomberg|the\s+hindu|mint|ndtv"
    r")\s*$",
    re.I,
)
_GENERIC_SUBJECT_WORDS = frozenset(
    {"bank", "banks", "market", "markets", "news", "the", "fund", "funds", "india", "stock"}
)


def strip_publisher(title: str) -> str:
    """Drop the outlet glued onto the end of a scraped headline."""
    return _PUBLISHER_TAIL.sub("", title or "").strip()


def clean_news_insight(text: str) -> str:
    """Remove a clipped line and any publisher tail the model copied."""
    kept: list[str] = []
    for line in (text or "").splitlines():
        if re.search(r"(?:\.\.\.|…)\s*$", line.strip()):
            continue
        kept.append(strip_publisher(line))
    return "\n".join(kept).strip()


def complete_sentences(text: str) -> str:
    """Keep finished sentences. A retrieval clip ends mid-thought and is not an insight."""
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = re.sub(r"(?:\.\.\.|…)\s*$", "", cleaned).strip()
    ends = list(re.finditer(r"[.!?](?:\s|$)", cleaned))
    if not ends:
        return ""
    return cleaned[: ends[-1].end()].strip()


def _subject_words(question: str) -> list[str]:
    from news_rag.insight.capabilities.executor import _news_subject

    subject = _news_subject(question)
    words = [
        word
        for word in re.findall(r"[a-z0-9]+", subject.lower())
        if word not in _GENERIC_SUBJECT_WORDS and len(word) > 2
    ]
    return words


def news_insight_articles(question: str, news_grouped: dict[str, Any]) -> list[dict[str, str]]:
    """Facts the composer can turn into an insight: no publisher, no clipped tail."""
    words = _subject_words(question)
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    articles: list[dict[str, Any]] = []
    for bucket in (news_grouped or {}).values():
        if isinstance(bucket, list):
            articles.extend(a for a in bucket if isinstance(a, dict))
        elif isinstance(bucket, dict):
            for arts in bucket.values():
                if isinstance(arts, list):
                    articles.extend(a for a in arts if isinstance(a, dict))
    for art in articles:
        title = strip_publisher(str(art.get("title") or ""))
        body = complete_sentences(str(art.get("summary") or art.get("text") or ""))
        blob = f"{title} {body}".lower()
        if words and not any(word in blob for word in words):
            continue
        key = title.lower()
        if not title or key in seen:
            continue
        if not body:
            continue
        seen.add(key)
        date = str(art.get("date") or art.get("published_at") or "")[:10]
        rows.append({"date": date, "what_happened": body})
        if len(rows) >= 8:
            break
    return rows


def is_article_only_news(plan: Any, pack: Any) -> bool:
    """A news question whose evidence is articles, with no fund or market snapshot."""
    if plan is None or pack is None or plan.answer_mode != AnswerMode.NEWS_ONLY:
        return False
    if not pack.news_grouped:
        return False
    data = pack.data_pack or {}
    if data.get("screen") or data.get("market") or any(str(key).startswith("fund:") for key in data):
        return False
    return True


def render_news_answer(news_grouped: dict[str, Any]) -> str:
    """A news question's answer is the retrieved articles, grouped by theme."""
    themes: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for scope, bucket in (news_grouped or {}).items():
        articles: list[dict[str, Any]] = []
        if isinstance(bucket, list):
            articles = [a for a in bucket if isinstance(a, dict)]
        elif isinstance(bucket, dict):
            for theme, arts in bucket.items():
                if isinstance(arts, list):
                    for art in arts:
                        if isinstance(art, dict):
                            articles.append({**art, "theme": art.get("theme") or theme})
        for art in articles:
            theme = str(art.get("theme") or scope or "News").strip() or "News"
            if theme.lower() in ("market", "general", "macro"):
                theme = "News"
            if theme not in themes:
                themes[theme] = []
                order.append(theme)
            themes[theme].append(art)
    lines: list[str] = []
    for theme in order:
        lines.extend([f"### {theme}", ""])
        seen: set[str] = set()
        for art in themes[theme]:
            title = str(art.get("title") or "").strip()
            key = title.lower()
            if not title or key in seen:
                continue
            seen.add(key)
            summary = re.sub(r"\s+", " ", str(art.get("summary") or "")).strip()
            if len(summary) > 280:
                summary = summary[:277].rstrip(" .") + "..."
            date = str(art.get("date") or art.get("published_at") or "")[:10]
            bullet = f"- **{title}**"
            if date:
                bullet += f" ({date})"
            if summary and summary.lower() not in title.lower():
                bullet += f": {summary}"
            lines.append(bullet)
        lines.append("")
    return "\n".join(lines).strip()


def news_only_answer(plan: Any, pack: Any) -> str:
    """Article lists are not the answer. The composer writes the insight."""
    return ""


def render_news_section(news_grouped: dict[str, Any]) -> str:
    """One bullet per retrieved article so a fund answer shows the news, not a teaser."""
    articles: list[dict[str, Any]] = []
    for bucket in (news_grouped or {}).values():
        if isinstance(bucket, list):
            articles.extend(a for a in bucket if isinstance(a, dict))
        elif isinstance(bucket, dict):
            for arts in bucket.values():
                if isinstance(arts, list):
                    articles.extend(a for a in arts if isinstance(a, dict))
    lines = ["### Recent news", ""]
    seen: set[str] = set()
    for art in articles:
        title = str(art.get("title") or "").strip()
        key = title.lower()
        if not title or key in seen:
            continue
        seen.add(key)
        summary = re.sub(r"\s+", " ", str(art.get("summary") or "")).strip()
        if len(summary) > 280:
            summary = summary[:280].rstrip(" .")
        date = str(art.get("date") or art.get("published_at") or "")[:10]
        bullet = f"- **{title}**"
        if date:
            bullet += f" ({date})"
        if summary and summary.lower() not in title.lower():
            bullet += f": {summary}"
        lines.append(bullet)
        if len(seen) >= 8:
            break
    if len(seen) == 0:
        return ""
    return "\n".join(lines)


def strip_news_roundup(prose: str) -> str:
    """Drop a news-list section. The answer should not end with an article roundup."""
    return _strip_heading_sections(
        prose or "",
        ("recent news", "what the news says", "news themes", "how the sector is held"),
    )


def append_news_section(prose: str, news_grouped: dict[str, Any]) -> str:
    block = render_news_section(news_grouped)
    if not block:
        return prose
    text = _strip_heading_sections(prose or "", ("recent news", "news themes"))
    return _insert_before_disclaimer(text, block)


def _strip_heading_sections(prose: str, headings: tuple[str, ...]) -> str:
    lines = (prose or "").split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", lines[i].strip())
        if m and any(m.group(1).strip().lower().startswith(h) for h in headings):
            i += 1
            while i < len(lines) and not re.match(r"^#{2,3}\s+", lines[i].strip()):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def _insert_before_disclaimer(prose: str, block: str) -> str:
    if not block:
        return prose
    text = prose or ""
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


def ensure_markdown_table_spacing(text: str) -> str:
    """Many renderers need a blank line immediately before a | table block."""
    if not text:
        return text
    lines = text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    for line in lines:
        if _TABLE_LINE_RE.match(line) and out and out[-1].strip() and not _TABLE_LINE_RE.match(out[-1]):
            out.append("")
        out.append(line)
    return "\n".join(out)


def normalize_user_facing_text(text: str) -> str:
    """Use '-' for missing values; soften common LLM table mistakes."""
    if not text:
        return text
    out = text
    out = re.sub(r"\bN/A\b", "-", out, flags=re.I)
    out = re.sub(r"\bn/a\b", "-", out)
    out = re.sub(r"—", "-", out)
    return ensure_markdown_table_spacing(out)
