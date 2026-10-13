"""Why a named fund moved: its sectors, those sector indexes, then holdings.

Order, always:
  1. The fund's own return over the question window.
  2. Its largest real sectors (not cash, tenor buckets, or "Mutual Funds").
  3. Each sector's index return over the same window.
  4. News for the sectors that moved the same way as the fund.
  5. The fund's holdings in those sectors. If a stock moved the other way,
     pull that stock's news. If it moved the same way, the sector news is the reason.
"""

from __future__ import annotations

import re
from typing import Any

from news_rag.insight.brief import QuestionBrief
from news_rag.insight.gather import EvidenceItem, EvidenceSet

_SKIP_SECTOR = re.compile(
    r"mutual fund|^\d+\s*days?$|cash|others?|debt fund|gilt|arbitrage",
    re.I,
)
_WHY_RE = re.compile(
    r"\bwhy\b|\bdown\b|\bup\b|\bfell\b|\brose\b|\bperform\w*|\bdoing\b|\bmoved\b",
    re.I,
)


def named_fund_why(question: str, brief: QuestionBrief) -> bool:
    return bool(brief.funds) and not brief.primary_sector() and bool(_WHY_RE.search(question or ""))


def enrich_named_fund_why(
    question: str,
    brief: QuestionBrief,
    evidence: EvidenceSet,
    *,
    query_log: Any = None,
) -> EvidenceSet:
    if not named_fund_why(question, brief):
        return evidence
    comps = evidence.by_facet("fund_composition") or evidence.by_facet("fund_facts_holdings")
    if not comps:
        return evidence

    from news_rag.insight.index_series import index_return_for_sector
    from news_rag.tools import run_layered_news

    window = int(brief.window_days or 30)
    payloads: list[dict[str, Any]] = []
    targets: list[str] = []

    for item in comps[:2]:
        data = item.data
        isin = str(data.get("isin") or item.entity_key or "")
        fund_ret = _fund_return(evidence, isin)
        sectors = [
            s for s in (data.get("sectors") or [])
            if isinstance(s, dict) and s.get("sector") and not _SKIP_SECTOR.search(str(s.get("sector")))
        ][:4]
        drags: list[dict[str, Any]] = []
        for sector in sectors[:3]:
            name = str(sector.get("sector"))
            weight = float(sector.get("percentage") or 0)
            idx = index_return_for_sector(name, window_days=window)
            idx_ret = idx.get("return_pct")
            same = _same_sign(fund_ret, idx_ret)
            news_line, articles = _sector_news(run_layered_news, question, name, window)
            for art in articles:
                art["_attr_sector"] = name
                art["_attr_isin"] = isin
            _append_articles(evidence, articles)
            holdings = _holdings_for_sector(
                data.get("holdings") or [], name, fund_ret, idx_ret, question, window, allow_fallback=same
            )
            drags.append(
                {
                    "sector": name,
                    "weight_pct": round(weight, 1),
                    "index_return_pct": idx_ret,
                    "index_label": idx.get("benchmark_label") or name,
                    "same_direction": same,
                    "news": news_line,
                    "holdings": holdings,
                }
            )
            if same or (fund_ret is None and idx_ret is not None):
                targets.append(name)
        payloads.append({"isin": isin, "fund_return_pct": fund_ret, "drags": drags})

    if targets:
        brief.raw["attribution_target"] = ", ".join(dict.fromkeys(targets))
    evidence.items.append(
        EvidenceItem(facet="fund_attribution", tool="fund_why", entity_key="", data={"funds": payloads})
    )
    if query_log is not None:
        query_log.write(
            "FUND_WHY funds="
            + str(len(payloads))
            + " sectors="
            + ",".join(targets[:4])
        )
    return evidence


def _fund_return(evidence: EvidenceSet, isin: str) -> float | None:
    key = (isin or "").upper()
    for item in evidence.by_facet("return_series") + evidence.by_facet("fund_facts_nav"):
        d = item.data
        if key and str(d.get("isin") or item.entity_key or "").upper() not in ("", key):
            continue
        for field in ("return_pct", "window_return_pct", "return_1m_pct"):
            val = d.get(field)
            if isinstance(val, (int, float)):
                return float(val)
    return None


def _sector_matches(sector: str, industry: str) -> bool:
    if sector in industry.lower() or industry.lower() in sector:
        return True
    left = re.findall(r"[a-z]{4,}", sector)
    right = re.findall(r"[a-z]{4,}", industry.lower())
    return any(a[:4] == b[:4] for a in left for b in right)


def _same_sign(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return False
    if abs(a) < 0.4 or abs(b) < 0.4:
        return False
    return (a < 0 and b < 0) or (a > 0 and b > 0)


def _plain_news(article: dict[str, Any]) -> str:
    from news_rag.snippet_clean import article_body_for_llm

    body = article_body_for_llm(article, limit=500)
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", body) if len(p.strip()) > 40]
    text = " ".join(parts[:2]) if parts else str(article.get("title") or "").strip()
    return text[:320].rstrip(" -")


def _sector_news(run_layered_news, question: str, sector: str, window: int) -> tuple[str, list[dict[str, Any]]]:
    try:
        res = run_layered_news(
            layer="sector_news",
            semantic_query=sector,
            question=f"why is the {sector} sector moving",
            entity_filters=[sector],
            window_days=window,
        )
    except Exception:
        return "", []
    data = res.get("data") if isinstance(res, dict) else {}
    articles = [a for a in (data.get("articles") or []) if isinstance(a, dict)][:4]
    line = _plain_news(articles[0]) if articles else ""
    return line, articles


def _holdings_for_sector(
    holdings: list[Any],
    sector: str,
    fund_ret: float | None,
    index_ret: float | None,
    question: str,
    window: int,
    *,
    allow_fallback: bool = False,
) -> list[dict[str, Any]]:
    from historical_data.stocks_service import get_stock_profile
    from news_rag.holdings_market import fetch_dedicated_holding_news

    sector_l = sector.lower()
    rows: list[dict[str, Any]] = []
    for h in holdings:
        if not isinstance(h, dict):
            continue
        industry = str(h.get("industry") or "")
        if not industry or not _sector_matches(sector_l, industry):
            continue
        name = str(h.get("name") or "")
        if not name:
            continue
        profile = get_stock_profile(name) or {}
        stock_ret = profile.get("return_1m") if window <= 45 else profile.get("return_1m")
        try:
            stock_ret_f = float(stock_ret) if stock_ret is not None else None
        except (TypeError, ValueError):
            stock_ret_f = None
        diverged = (
            stock_ret_f is not None
            and index_ret is not None
            and not _same_sign(stock_ret_f, float(index_ret))
            and abs(stock_ret_f) >= 0.4
        )
        arts = fetch_dedicated_holding_news(name, question, window_days=window, limit=1) or []
        news = _plain_news(arts[0]) if arts else ""
        rows.append(
            {
                "name": name,
                "weight_pct": round(float(h.get("percentage") or 0), 1),
                "return_pct": stock_ret_f,
                "diverged": diverged,
                "news": news,
            }
        )
        if len(rows) >= 3:
            break
    if rows or not allow_fallback:
        return rows
    for h in holdings[:3]:
        if not isinstance(h, dict) or not h.get("name"):
            continue
        name = str(h.get("name"))
        profile = get_stock_profile(name) or {}
        stock_ret = profile.get("return_1m")
        try:
            stock_ret_f = float(stock_ret) if stock_ret is not None else None
        except (TypeError, ValueError):
            stock_ret_f = None
        diverged = (
            stock_ret_f is not None
            and index_ret is not None
            and not _same_sign(stock_ret_f, float(index_ret))
            and abs(stock_ret_f) >= 0.4
        )
        arts = fetch_dedicated_holding_news(name, question, window_days=window, limit=1) or []
        news = _plain_news(arts[0]) if arts else ""
        rows.append(
            {
                "name": name,
                "weight_pct": round(float(h.get("percentage") or 0), 1),
                "return_pct": stock_ret_f,
                "diverged": diverged,
                "news": news,
            }
        )
    return rows


def _append_articles(evidence: EvidenceSet, articles: list[dict[str, Any]]) -> None:
    seen = {str(a.get("url") or a.get("title") or "") for a in evidence.articles}
    for art in articles:
        key = str(art.get("url") or art.get("title") or "")
        if key and key not in seen:
            seen.add(key)
            evidence.articles.append(art)
