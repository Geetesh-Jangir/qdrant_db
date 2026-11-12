"""Number grounding and display polish for composed answers."""

from __future__ import annotations

import re

from datetime import date
from typing import Any

_MEDIA_OUTLETS = (
    "Economic Times",
    "Financial Express",
    "Business Standard",
    "BusinessLine",
    "The Hindu BusinessLine",
    "Moneycontrol",
    "Livemint",
    "Mint",
    "Reuters",
    "NDTV Profit",
    "CNBC-TV18",
    "CNBC",
    "Bloomberg",
    "PTI",
    "ANI",
    "Business Standard",
)
_OUTLET_CITE_RE = re.compile(
    r"\(\s*(?:"
    + "|".join(re.escape(o) for o in _MEDIA_OUTLETS)
    + r")\s*,\s*[^)]+\)",
    re.I,
)
_OUTLET_BARE_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(o) for o in _MEDIA_OUTLETS)
    + r")\b(?:\s*,\s*\d{1,2}\s+\w{3,9}(?:\s+\d{4})?)?",
    re.I,
)
_ACCORDING_RE = re.compile(r"\baccording to\s+(?:the\s+)?(?:reports?|news|media)\b[,.]?\s*", re.I)

_PCT_OR_BPS_RE = re.compile(
    r"(?<![\w.])([+-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:%|bps|bp)(?![\w])",
    re.I,
)
_MONEY_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?)",
    re.I,
)
_DECIMAL_RE = re.compile(r"(?<![\w.])([+-]?\d{1,3}(?:,\d{3})*\.\d+)(?![\w.])")
_ANY_NUMBER_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def numeric_core(raw: str) -> str:
    s = (raw or "").replace(",", "").strip().lstrip("+")
    if not s:
        return ""
    if re.fullmatch(r"-?\d+\.\d+", s):
        s = s.rstrip("0").rstrip(".")
    return s


def number_is_grounded(core: str, allowed: set[str]) -> bool:
    if not core:
        return False
    unsigned = core[1:] if core.startswith("-") else core
    return core in allowed or unsigned in allowed or f"-{unsigned}" in allowed


_CITE_DATE_RE = re.compile(
    r"\(\s*\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
    r"(?:\s+\d{4})?\s*\)",
    re.I,
)
_PROSE_DATE_RE = re.compile(
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
    r"|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2})\b",
    re.I,
)


def publication_date_keys(published_at: str) -> set[str]:
    """Normalized forms of an article timestamp, for citation checks."""
    raw = str(published_at or "").strip()
    if len(raw) < 10 or not raw[:4].isdigit():
        return set()
    try:
        year, month, day = int(raw[:4]), int(raw[5:7]), int(raw[8:10])
    except ValueError:
        return set()
    full = ("", "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december")
    short = ("", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
    if not 1 <= month <= 12:
        return set()
    keys = {
        f"{day} {full[month]}",
        f"{day} {short[month]}",
        f"{full[month]} {day}",
        f"{short[month]} {day}",
        f"{day} {full[month]} {year}",
        f"{day} {short[month]} {year}",
    }
    return keys


def _ordinal_day(day: int) -> str:
    if 11 <= (day % 100) <= 13:
        return f"{day}th"
    suffix = ("th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th")
    return f"{day}{suffix[day % 10]}"


def format_user_calendar_date(iso_timestamp: str, *, include_year: bool | None = None) -> str:
    """ISO publish time -> user-facing anchor like 2nd Nov or 31st Oct 2026."""
    raw = str(iso_timestamp or "").strip()
    if len(raw) < 10 or not raw[:4].isdigit():
        return ""
    try:
        year, month, day = int(raw[:4]), int(raw[5:7]), int(raw[8:10])
    except ValueError:
        return ""
    short = ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return ""
    show_year = include_year if include_year is not None else year != date.today().year
    base = f"{_ordinal_day(day)} {short[month]}"
    return f"{base} {year}" if show_year else base


def collect_evidence_calendar_dates(evidence: dict[str, Any], *, limit: int = 12) -> list[dict[str, str]]:
    """NEWS published_at rows the composer can anchor events to."""
    news = evidence.get("NEWS")
    if not isinstance(news, dict):
        return []
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_article(art: dict[str, Any], topic: str) -> None:
        if len(rows) >= limit:
            return
        iso = str(
            art.get("published_at") or art.get("date") or art.get("published_date") or ""
        ).strip()
        label = format_user_calendar_date(iso)
        if not label or label in seen:
            return
        seen.add(label)
        theme = str(art.get("theme") or topic or "").strip()
        rows.append({"date": label, "topic": theme[:96]})

    for scope, bucket in news.items():
        if isinstance(bucket, list):
            for art in bucket:
                if isinstance(art, dict):
                    add_article(art, str(scope))
        elif isinstance(bucket, dict):
            for entity, arts in bucket.items():
                if isinstance(arts, list):
                    for art in arts:
                        if isinstance(art, dict):
                            add_article(art, str(entity or scope))
    return rows


def mentions_publication_date(text: str, published_keys: set[str] | None = None) -> bool:
    """True only for parenthetical outlet-style date citations, not calendar dates in prose."""
    del published_keys
    return bool(_CITE_DATE_RE.search(text or ""))


def derived_cores(allowed: set[str]) -> set[str]:
    """Sum, gap and weight x return of two measured figures, so honest derived numbers are not deleted."""
    numbers: list[float] = []
    for core in allowed:
        try:
            value = float(core)
        except ValueError:
            continue
        if 0 < abs(value) <= 100:
            numbers.append(value)
    extra: set[str] = set()
    for index, left in enumerate(numbers[:30]):
        for right in numbers[index + 1 : 30]:
            # sum (cap totals), gap (fund minus benchmark), contribution (weight x return / 100)
            for total in (left + right, abs(left - right), left * right / 100):
                total = round(total, 2)
                extra.add(numeric_core(f"{total:.2f}"))
                extra.add(numeric_core(f"{total:.1f}"))
                extra.add(str(int(round(total))))
    extra.discard("")
    return extra


def cores_for_float(value: float) -> set[str]:
    """Numeric forms grounding may use in prose (₹ amounts, returns, weights)."""
    cores: set[str] = set()
    try:
        num = float(value)
    except (TypeError, ValueError):
        return cores
    cores.add(numeric_core(f"{num}"))
    cores.add(numeric_core(f"{num:.2f}"))
    cores.add(numeric_core(f"{num:.1f}"))
    if abs(num) >= 1:
        cores.add(str(int(round(num))))
    if abs(num) < 1000 and abs(num) > 0:
        cores.add(numeric_core(f"{num:.0f}"))
    cores.discard("")
    return cores


def fund_portfolio_cores(data_pack: dict[str, Any]) -> set[str]:
    """Allow sums of top holding/sector weights in concentration answers."""
    from news_rag.insight.evidence_pack import _holding_weight_pct, _sector_weight_pct

    if not isinstance(data_pack, dict):
        return set()
    cores: set[str] = set()
    for key, val in data_pack.items():
        if not str(key).startswith("portfolio:") or not isinstance(val, dict):
            continue
        holdings = [h for h in (val.get("holdings") or []) if isinstance(h, dict)]
        sectors = [s for s in (val.get("sectors") or []) if isinstance(s, dict)]
        for row in holdings[:15]:
            cores |= cores_for_float(_holding_weight_pct(row))
        for row in sectors[:15]:
            cores |= cores_for_float(_sector_weight_pct(row))
        for n in (5, 10, len(holdings), len(sectors)):
            if n <= 0:
                continue
            h_sum = round(sum(_holding_weight_pct(h) for h in holdings[:n]), 2)
            s_sum = round(sum(_sector_weight_pct(s) for s in sectors[:n]), 2)
            if h_sum:
                cores |= cores_for_float(h_sum)
            if s_sum:
                cores |= cores_for_float(s_sum)
        for fund_key, fund_val in data_pack.items():
            if not str(fund_key).startswith("fund:") or not isinstance(fund_val, dict):
                continue
            comp = fund_val.get("composition") if isinstance(fund_val.get("composition"), dict) else {}
            for field in ("top_5_pct", "top_10_pct"):
                raw = comp.get(field)
                if raw is not None:
                    cores |= cores_for_float(float(raw))
            count = comp.get("holding_count")
            if count is not None:
                cores.add(str(int(count)))
    return cores


def investor_book_cores(investor: dict[str, Any]) -> set[str]:
    """Allow rounded allocation % and common prose forms for the user's book."""
    if not isinstance(investor, dict):
        return set()
    cores: set[str] = set()
    summary = investor.get("summary") if isinstance(investor.get("summary"), dict) else {}
    for key in ("invested_inr", "aum_inr", "gain_loss_inr", "absolute_return_pct", "portfolio_xirr_pct"):
        val = summary.get(key)
        if val is not None:
            cores |= cores_for_float(float(val))

    computed = investor.get("computed") if isinstance(investor.get("computed"), dict) else {}
    total = computed.get("total_value_inr")
    if total is not None:
        cores |= cores_for_float(float(total))

    for row in computed.get("allocation_by_category") or []:
        if not isinstance(row, dict):
            continue
        pct = row.get("weight_pct")
        if pct is None:
            continue
        cores |= cores_for_float(float(pct))
        cores.add(str(int(round(float(pct)))))

    for row in computed.get("holdings") or []:
        if not isinstance(row, dict):
            continue
        for key in ("value_inr", "invested_inr", "gain_loss_inr", "xirr_pct", "absolute_return_pct", "weight_pct"):
            val = row.get(key)
            if val is not None:
                cores |= cores_for_float(float(val))

    for row in investor.get("holdings") or []:
        if not isinstance(row, dict):
            continue
        for key in ("aum_inr", "invested_inr", "gain_loss_inr", "xirr_pct", "absolute_return_pct"):
            val = row.get(key)
            if val is not None:
                cores |= cores_for_float(float(val))

    pnl = investor.get("pnl_summary") if isinstance(investor.get("pnl_summary"), dict) else {}
    for key in (
        "short_term_gain_inr",
        "long_term_gain_inr",
        "purchase",
        "netInvestment",
        "inflow",
        "currentValue",
        "gainLoss",
        "gainLossRounded",
        "absoluteReturnPercent",
        "portfolioXirrPercent",
        "xirrPercent",
    ):
        val = pnl.get(key)
        if val is not None:
            cores |= cores_for_float(float(val))

    sip = investor.get("sip") if isinstance(investor.get("sip"), dict) else {}
    sip_summary = sip.get("summary") if isinstance(sip.get("summary"), dict) else {}
    for key in ("totalSipAmount", "totalSipMonthlyAmount", "count", "liveCount"):
        val = sip_summary.get(key)
        if val is not None:
            cores |= cores_for_float(float(val))

    return cores


def cores_in_text(blob: str) -> set[str]:
    cores: set[str] = set()
    for match in _ANY_NUMBER_RE.finditer(blob or ""):
        core = numeric_core(match.group(0))
        if not core:
            continue
        cores.add(core)
        try:
            value = float(core)
        except ValueError:
            continue
        cores.add(numeric_core(f"{value:.2f}"))
        cores.add(numeric_core(f"{value:.1f}"))
    cores.discard("")
    return cores


def strip_media_attribution(text: str) -> str:
    """Remove newspaper names and inline source parentheses; sources live in the API `sources` list."""
    cleaned = text or ""
    cleaned = _OUTLET_CITE_RE.sub("", cleaned)
    cleaned = _OUTLET_BARE_RE.sub("", cleaned)
    cleaned = _ACCORDING_RE.sub("", cleaned)
    cleaned = re.sub(r"\(\s*\d{1,2}\s+\w{3,9}(?:\s+\d{4})?\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+\(\s*;\s*", " (", cleaned)
    return tidy_prose(cleaned)


def tidy_prose(text: str) -> str:
    # Drop a stray "per cent" only when it is not the unit of a number ("6.1 percent" stays).
    text = re.sub(r"(?<![\d.])\s+per\s*cent\b", "", text or "", flags=re.I)
    text = re.sub(r"\*{2,}\s*\*{2,}", "", text)
    text = re.sub(r"\broughly\s+\*\*\s*\*\*", "", text)
    text = re.sub(r"\bworth\s+roughly\s+\*\*\s*pp\*\*", "", text, flags=re.I)
    text = re.sub(r"\(\s*approx\.?\s*\)", "", text, flags=re.I)
    text = re.sub(r"\(about\s*\)", "", text, flags=re.I)
    text = re.sub(r"\*\*\s*\*\*", "", text)
    text = re.sub(r"\*\*\(\s*\)\*\*", "", text)
    text = re.sub(r"\babout\s*,", "", text, flags=re.I)
    text = re.sub(r"\bworth about\s*,", "", text, flags=re.I)
    text = re.sub(r"\binvested and now worth about\s*,", "", text, flags=re.I)
    text = re.sub(r"\ba loss of about\s*\.?", "", text, flags=re.I)
    text = re.sub(r"\(\s*about\s+\)", "", text, flags=re.I)
    text = re.sub(r"\bapprox\.?\s*pp\b", "", text, flags=re.I)
    text = re.sub(r"\s+pp\b(?!\w)", "", text, flags=re.I)
    text = re.sub(r"\bbetween\s+and\b", "", text, flags=re.I)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def strip_ungrounded_numbers(text: str, allowed: set[str]) -> str:
    def drop_pct(match: re.Match[str]) -> str:
        core = numeric_core(match.group(1))
        return match.group(0) if number_is_grounded(core, allowed) else ""

    def drop_money(match: re.Match[str]) -> str:
        core = numeric_core(match.group(1))
        return match.group(0) if number_is_grounded(core, allowed) else ""

    def drop_decimal(match: re.Match[str]) -> str:
        core = numeric_core(match.group(1))
        return match.group(0) if number_is_grounded(core, allowed) else ""

    cleaned = _PCT_OR_BPS_RE.sub(drop_pct, text or "")
    cleaned = _MONEY_RE.sub(drop_money, cleaned)
    cleaned = _DECIMAL_RE.sub(drop_decimal, cleaned)
    return tidy_prose(cleaned)


def finalize_text_fields(
    headline: str,
    narrative: str,
    bullets: list[str],
    closing: str,
    evidence_text: str,
) -> tuple[str, str, list[str], str]:
    allowed = cores_in_text(evidence_text)
    headline = strip_media_attribution(strip_ungrounded_numbers(headline, allowed))
    narrative = strip_media_attribution(strip_ungrounded_numbers(narrative, allowed))
    bullets = [
        strip_media_attribution(strip_ungrounded_numbers(b, allowed)) for b in bullets if b
    ]
    closing = strip_media_attribution(strip_ungrounded_numbers(closing, allowed))
    return headline, narrative, [b for b in bullets if b.strip()], closing
