"""Holding-level attribution: contribution = weight% × stock return% / 100.

Computed in code. The writer narrates this block and does not replace it with sector-index × weight.
"""

from __future__ import annotations

import re
from typing import Any


def contribution_pct(weight_pct: float, return_pct: float) -> float:
    return round(float(weight_pct) * float(return_pct) / 100.0, 2)


def attribute_rows(
    holdings: list[dict[str, Any]],
    *,
    fund_return_pct: float | None,
    return_field: str = "return_pct",
) -> dict[str, Any]:
    """Pure attribution from holdings that already include a stock return.

    Unexplained = fund return − sum of priced contributions (two decimals).
    """
    priced: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for h in holdings:
        if not isinstance(h, dict) or not h.get("name"):
            continue
        try:
            weight = round(float(h.get("weight_pct") if h.get("weight_pct") is not None else h.get("percentage") or 0), 2)
        except (TypeError, ValueError):
            continue
        raw_ret = h.get(return_field)
        if raw_ret is None:
            raw_ret = h.get("return_pct")
        try:
            ret = round(float(raw_ret), 2) if raw_ret is not None else None
        except (TypeError, ValueError):
            ret = None
        row = {
            "name": str(h.get("name")),
            "sector": str(h.get("sector") or h.get("industry") or ""),
            "weight_pct": weight,
            "return_pct": ret,
            "contribution_pct": contribution_pct(weight, ret) if ret is not None else None,
        }
        if row["contribution_pct"] is None:
            missing.append(row)
        else:
            priced.append(row)

    explained = round(sum(r["contribution_pct"] for r in priced), 2)
    unexplained = None
    if fund_return_pct is not None:
        unexplained = round(float(fund_return_pct) - explained, 2)

    by_impact = sorted(priced, key=lambda r: r["contribution_pct"])
    detractors = [r for r in by_impact if r["contribution_pct"] < 0][:3]
    contributors = [r for r in reversed(by_impact) if r["contribution_pct"] > 0][:3]
    table = sorted(priced, key=lambda r: abs(r["contribution_pct"]), reverse=True)[:12]

    sector_w: dict[str, float] = {}
    for r in priced + missing:
        sec = r["sector"] or "Other"
        sector_w[sec] = round(sector_w.get(sec, 0.0) + r["weight_pct"], 2)

    top_sector = max(sector_w, key=sector_w.get) if sector_w else ""
    return {
        "method": "holding_weight_times_stock_return",
        "rows": table,
        "all_priced": priced,
        "missing_price": missing[:8],
        "explained_pct": explained,
        "unexplained_pct": unexplained,
        "fund_return_pct": None if fund_return_pct is None else round(float(fund_return_pct), 2),
        "detractors": detractors,
        "contributors": contributors,
        "priced_weight_pct": round(sum(r["weight_pct"] for r in priced), 2),
        "top_sector": top_sector,
        "top_sector_weight_pct": sector_w.get(top_sector),
        "sector_weights": [
            {"sector": k, "weight_pct": v}
            for k, v in sorted(sector_w.items(), key=lambda kv: -kv[1])[:5]
        ],
    }


def render_attribution_table(attr: dict[str, Any]) -> str:
    lines = [
        "| Holding | Weight % | Return % | Contribution (pp) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for r in attr.get("rows") or []:
        ret = r.get("return_pct")
        contrib = r.get("contribution_pct")
        lines.append(
            f"| {short_holding_name(str(r.get('name') or ''))} | {r.get('weight_pct'):.2f} | "
            f"{'' if ret is None else f'{ret:.2f}'} | "
            f"{'' if contrib is None else f'{contrib:.2f}'} |"
        )
    if attr.get("unexplained_pct") is not None:
        lines.append(f"| Other / unexplained |  |  | {float(attr['unexplained_pct']):.2f} |")
    if attr.get("fund_return_pct") is not None:
        lines.append(f"| Fund total |  |  | {float(attr['fund_return_pct']):.2f} |")
    return "\n".join(lines)


_NAME_NOISE = frozenset({"limited", "ltd", "industries", "india", "company", "corporation"})
_DISMISS = re.compile(
    r"does not explain|different compan|no company-specific|no fundamental|general (?:market|nifty)|"
    r"cannot be linked|not a holding|stocks to watch",
    re.I,
)
_ROUNDUP_TITLE = re.compile(r"stocks to watch|more stocks|markets?:|shares to watch", re.I)


def short_holding_name(name: str) -> str:
    return re.sub(r"\s+(Limited|Ltd\.?)$", "", str(name or ""), flags=re.I).strip()


def _name_tokens(name: str) -> list[str]:
    return [
        t
        for t in re.findall(r"[a-z]{4,}", (name or "").lower())
        if t not in _NAME_NOISE
    ]


def news_is_about_company(news: str, name: str) -> bool:
    return bool(company_news_line(news, name))


def company_news_line(news: str, name: str, *, title: str = "") -> str:
    """One sentence about this company, or empty when the item is a roundup or another firm."""
    raw = re.sub(r"https?://\S+", "", news or "")
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw or _DISMISS.search(title or "") or _ROUNDUP_TITLE.search(title or raw[:80]):
        return ""
    tokens = _name_tokens(name)
    if not tokens:
        return ""
    titled = any(t in (title or "").lower() for t in tokens)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw) if len(s.strip()) > 40]
    if not sentences:
        sentences = [raw] if len(raw) > 40 else []

    def _about(sentence: str) -> bool:
        blob = sentence.lower()
        if not any(t in blob for t in tokens):
            return False
        if _DISMISS.search(sentence):
            return False
        # A watchlist sentence names several firms and no business fact.
        other_hits = len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", sentence))
        has_fact = bool(re.search(r"\d|crore|growth|profit|margin|deposit|advance|order|sales", sentence, re.I))
        if other_hits >= 4 and not has_fact:
            return False
        return True

    for sentence in sentences:
        if _about(sentence):
            return sentence[:280].rstrip(" -")
    if titled and not _ROUNDUP_TITLE.search(title or ""):
        for sentence in sentences:
            if re.search(r"\d|crore|growth|profit|deposit|advance", sentence, re.I):
                return sentence[:280].rstrip(" -")
    return ""


def _join_names(rows: list[dict[str, Any]]) -> str:
    names = [short_holding_name(str(r.get("name") or "")) for r in rows if r.get("name")]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def render_investor_answer(
    *,
    fund_name: str,
    window_label: str,
    attr: dict[str, Any],
    benchmark_name: str = "",
    benchmark_return_pct: float | None = None,
    alternate_return_pct: float | None = None,
    return_notes: list[str] | None = None,
) -> str:
    """Investor-facing brief. Field names, dates with '?', and unmatched news stay out."""
    del return_notes  # kept for callers; never printed
    ret = attr.get("fund_return_pct")
    detractors = list(attr.get("detractors") or [])
    contributors = list(attr.get("contributors") or [])
    drag_sum = round(sum(float(r["contribution_pct"]) for r in detractors), 2) if detractors else None
    off_sum = round(sum(float(r["contribution_pct"]) for r in contributors), 2) if contributors else None
    window = window_label or "the measured window"
    name = fund_name or "The fund"

    if ret is None:
        opening = f"**{name}** has no return for **{window}**."
    else:
        opening = f"**{name}** returned **{float(ret):.2f}%** over **{window}**."

    bits: list[str] = []
    if detractors and drag_sum is not None:
        bits.append(
            f"{_join_names(detractors)} pulled it down by **{drag_sum:.2f}** percentage points."
        )
    if contributors and off_sum is not None:
        bits.append(
            f"{_join_names(contributors)} offset **{off_sum:+.2f}** percentage points."
        )
    if attr.get("explained_pct") is not None and attr.get("unexplained_pct") is not None:
        bits.append(
            f"Holdings with a price explain **{float(attr['explained_pct']):.2f}** percentage points. "
            f"**{float(attr['unexplained_pct']):.2f}** percentage points are not explained by those holdings."
        )

    sections = [opening, "", " ".join(bits), "", "### What moved the fund", "", render_attribution_table(attr), ""]

    news_lines: list[str] = []
    for row in detractors + contributors:
        label = short_holding_name(str(row.get("name") or ""))
        contrib = float(row.get("contribution_pct") or 0)
        line = company_news_line(str(row.get("news") or ""), label, title=str(row.get("news_title") or ""))
        if not line:
            continue
        url = str(row.get("news_url") or "").strip()
        if url:
            line = f"{line} [source]({url})"
        news_lines.append(f"- **{label}** ({contrib:+.2f} percentage points): {line}")
    if news_lines:
        sections.extend(["### What the news adds", ""] + news_lines + [""])

    if attr.get("top_sector") and attr.get("top_sector_weight_pct") is not None:
        drag_sectors = {str(r.get("sector") or "") for r in detractors}
        outside = attr["top_sector"] not in drag_sectors
        sentence = f"**{attr['top_sector']}** is **{float(attr['top_sector_weight_pct']):.2f}%** of the fund."
        if outside and detractors:
            sentence += " The largest drags are outside that sector."
        sections.extend([sentence, ""])

    if benchmark_return_pct is not None and benchmark_name:
        gap = None if ret is None else round(float(ret) - float(benchmark_return_pct), 2)
        gap_txt = f" The fund was **{gap:+.2f}** percentage points versus that benchmark." if gap is not None else ""
        sections.append(f"{benchmark_name} returned **{float(benchmark_return_pct):.2f}%**.{gap_txt}")
    elif benchmark_name:
        sections.append(f"The benchmark ({benchmark_name}) has no return for this window.")
    sections.append("")

    missing = attr.get("missing_price") or []
    if missing:
        miss_w = round(sum(float(r.get("weight_pct") or 0) for r in missing), 2)
        miss_names = ", ".join(short_holding_name(str(r.get("name") or "")) for r in missing[:4])
        sections.append(f"Prices are missing for {miss_names} ({miss_w:.2f}% of the fund).")
        sections.append("")
    if alternate_return_pct is not None and ret is not None and abs(float(alternate_return_pct) - float(ret)) > 0.15:
        sections.append(
            f"A second return figure for this window is **{float(alternate_return_pct):.2f}%**. "
            f"The total above uses **{float(ret):.2f}%**."
        )
        sections.append("")

    sections.append("*For context only — not investment advice.*")
    return "\n".join(sections).strip() + "\n"


def arithmetic_ok(attr: dict[str, Any], tol: float = 0.02) -> bool:
    explained = float(attr.get("explained_pct") or 0)
    total = round(sum(float(r["contribution_pct"]) for r in attr.get("all_priced") or attr.get("rows") or []), 2)
    if abs(explained - total) > tol and attr.get("all_priced"):
        return False
    fund = attr.get("fund_return_pct")
    unexplained = attr.get("unexplained_pct")
    if fund is not None and unexplained is not None:
        return abs(round(float(fund) - explained, 2) - float(unexplained)) <= tol
    return True
