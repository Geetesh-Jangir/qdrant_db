"""Best-effort official figures. Each call fails soft when the page is blocked or unparsable."""

from __future__ import annotations

import json
import re
import urllib.request

from ai_insight.data.base import NumericRecord, unavailable
from ai_insight.data.macro_data import fetch_cpi, fetch_gdp, fetch_iip, fetch_wpi
from ai_insight.data.nse_fii_dii import fetch_fii_dii_snapshot

_UA = "Mozilla/5.0 (compatible; RupeeStopInsight/1.0)"


def _get(url: str, timeout: float = 12.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json,text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def numeric_from_fii_dii_snapshot(snap) -> NumericRecord:
    entity = "Macro - FII DII Flows"
    if snap.status == "unavailable" or snap.fii is None:
        return unavailable(entity, snap.source, snap.detail or "no FII leg")
    return NumericRecord(
        entity,
        snap.trade_date,
        snap.fii.net_inr_crore,
        None,
        "inr_crore",
        snap.source,
        "ok" if snap.status == "ok" else snap.status,
        snap.detail,
    )


def fetch_fii_dii() -> NumericRecord:
    """Legacy single-value row: FII/FPI net only (see fii_dii_latest.json for full buy/sell/net)."""
    return numeric_from_fii_dii_snapshot(fetch_fii_dii_snapshot())


def fetch_gsec() -> NumericRecord:
    entity = "Macro - Bond Yields"
    # CCIL and RBI DBIE are JS apps. This HTML page sometimes includes the 10-year yield in text.
    url = "https://www.rbi.org.in/Scripts/BS_NSDPDisplay.aspx?param=4"
    try:
        html = _get(url)
    except Exception as exc:
        return unavailable(entity, "rbi.org.in", f"RBI page not readable: {exc}"[:240])
    match = re.search(r"10[-\s]?year[^0-9]{0,40}(\d{1,2}\.\d{2,4})", html, re.I)
    if not match:
        return unavailable(entity, "rbi.org.in", "page returned no 10-year yield (likely a script shell)")
    return NumericRecord(entity, "", float(match.group(1)), None, "percent", "rbi.org.in", "ok")


def _macro_row(entity: str, loader, pick, unit: str) -> NumericRecord:
    try:
        rows = loader()
        chosen = pick(rows)
    except Exception as exc:
        return unavailable(entity, SOURCE_MOSPI, str(exc)[:240])
    if chosen is None:
        return unavailable(entity, SOURCE_MOSPI, "no headline row")
    value, change, date, detail = chosen
    return NumericRecord(entity, date, value, change, unit, SOURCE_MOSPI, "ok", detail)


SOURCE_MOSPI = "mospi"


def fetch_cpi_record() -> NumericRecord:
    def pick(rows):
        head = next((row for row in rows if row.sector == "Combined"), None)
        if head is None or head.inflation_rate_yoy is None:
            return None
        return (
            head.inflation_rate_yoy,
            None,
            f"{head.year}-{head.month}",
            f"base {head.base_year} index {head.index_value}",
        )

    return _macro_row("Macro - Inflation (CPI)", fetch_cpi, pick, "percent")


def fetch_wpi_record() -> NumericRecord:
    def pick(rows):
        head = next((row for row in rows if row.commodity_group == "Wholesale Price Index"), None)
        if head is None:
            return None
        return (
            head.index_value,
            head.inflation_rate_yoy,
            f"{head.year}-{head.month}",
            f"base {head.base_year}; yoy derived",
        )

    return _macro_row("Macro - WPI Inflation", fetch_wpi, pick, "index")


def fetch_iip_record() -> NumericRecord:
    def pick(rows):
        head = next((row for row in rows if row.sector == "General"), None)
        if head is None:
            return None
        return (
            head.index_value,
            head.growth_rate_yoy,
            f"{head.year}-{head.month}",
            f"base {head.base_year}",
        )

    return _macro_row("Macro - IIP", fetch_iip, pick, "index")


def fetch_gdp_record() -> NumericRecord:
    def pick(rows):
        gdp = [row for row in rows if row.indicator == "Gross Domestic Product" and row.quarter]
        if not gdp:
            return None
        head = sorted(gdp, key=lambda row: row.quarter or "")[-1]
        return (
            head.value_rs_crore,
            head.growth_rate_yoy,
            f"{head.fiscal_year} {head.quarter}",
            f"constant {head.constant_rs_crore}; yoy derived on constant prices",
        )

    return _macro_row("Macro - GDP & Economy", fetch_gdp, pick, "inr_crore")


def fetch_gst() -> NumericRecord:
    entity = "Macro - GST Collections"
    url = "https://www.pib.gov.in/allRel.aspx"
    try:
        html = _get(url, timeout=10)
    except Exception as exc:
        return unavailable(entity, "pib.gov.in", f"PIB not readable: {exc}"[:240])
    if "GST" not in html:
        return unavailable(entity, "pib.gov.in", "PIB listing has no GST figure in the HTML")
    match = re.search(r"GST[^0-9]{0,80}(\d{1,3}(?:,\d{3})+|\d{4,7})\s*crore", html, re.I)
    if not match:
        return unavailable(entity, "pib.gov.in", "GST mentioned but no crore figure in the HTML")
    value = float(match.group(1).replace(",", ""))
    return NumericRecord(entity, "", value, None, "inr_crore", "pib.gov.in", "ok")


def fetch_official(*, include_fii: bool = True) -> list[NumericRecord]:
    rows: list[NumericRecord] = []
    if include_fii:
        rows.append(fetch_fii_dii())
    rows.extend(
        [
        fetch_gsec(),
        fetch_cpi_record(),
        fetch_wpi_record(),
        fetch_iip_record(),
        fetch_gdp_record(),
        fetch_gst(),
        ]
    )
    return rows


def _first_number(row: dict, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        raw = row.get(key)
        if raw is None:
            continue
        try:
            return float(str(raw).replace(",", ""))
        except ValueError:
            continue
    return None
