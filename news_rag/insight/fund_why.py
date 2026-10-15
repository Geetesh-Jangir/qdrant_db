"""Why a named fund moved: holding-level attribution, then news on the biggest movers.

Contribution is weight × stock return, computed before any narrative.
Sector index × weight is not used as the drag.
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
    r"\bwhy\b|\bhappen\w*\b|\bdown\b|\bup\b|\bfell\b|\brose\b|\bperform\w*|\bdoing\b|\bmoved\b",
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
    force: bool = False,
) -> EvidenceSet:
    """`force` lets the planner decide that holding attribution is wanted (no keyword check)."""
    if not force and not named_fund_why(question, brief):
        return evidence
    comps = evidence.by_facet("fund_composition") or evidence.by_facet("fund_facts_holdings")
    if not comps:
        return evidence

    from news_rag.insight.holding_attribution import attribute_rows

    window = int(brief.window_days or 30)
    payloads: list[dict[str, Any]] = []
    mover_names: list[str] = []

    for item in comps[:2]:
        data = item.data
        isin = str(data.get("isin") or item.entity_key or "")
        fund_ret, alternate_ret = _fund_return_detail(evidence, isin)
        priced = _price_holdings(data.get("holdings") or [], window)
        attr = attribute_rows(priced, fund_return_pct=fund_ret)
        movers = _unique_movers(attr)
        news_by_name = _news_for_movers(movers, question, window)
        for row in movers:
            arts = news_by_name.get(str(row["name"]), [])
            if arts:
                row["news"] = _plain_news(arts[0])
                row["news_title"] = str(arts[0].get("title") or "")
                row["news_url"] = str(arts[0].get("url") or "")
                row["news_date"] = str(arts[0].get("published_at") or arts[0].get("date") or "")[:10]
                row["confidence"] = "price_and_news"
                for art in arts:
                    art["_attr_isin"] = isin
                    art["_attr_holding"] = row["name"]
                _append_articles(evidence, arts)
            else:
                row["confidence"] = "price_only"
            mover_names.append(str(row["name"]))
        for bucket in ("detractors", "contributors", "rows"):
            by_name = {str(r["name"]): r for r in movers}
            for r in attr.get(bucket) or []:
                extra = by_name.get(str(r.get("name")))
                if extra:
                    r.update({k: extra[k] for k in ("news", "news_title", "news_url", "news_date", "confidence") if k in extra})
        payloads.append(
            {
                "isin": isin,
                "fund_name": data.get("fund_name"),
                "fund_return_pct": fund_ret,
                "alternate_return_pct": alternate_ret,
                "window_days": window,
                "window_label": brief.window_label,
                "attribution": attr,
                "drags": [
                    {
                        "sector": r.get("sector") or r.get("name"),
                        "weight_pct": r.get("weight_pct"),
                        "approx_contribution_pct": r.get("contribution_pct"),
                        "holdings": [r],
                    }
                    for r in (attr.get("detractors") or [])
                ],
            }
        )

    if mover_names:
        brief.raw["attribution_target"] = ", ".join(dict.fromkeys(mover_names))
    evidence.items.append(
        EvidenceItem(facet="fund_attribution", tool="fund_why", entity_key="", data={"funds": payloads})
    )
    if query_log is not None:
        top = mover_names[:6]
        query_log.write("FUND_WHY funds=" + str(len(payloads)) + " movers=" + ",".join(top))
    return evidence


def _news_for_movers(movers: list[dict[str, Any]], question: str, window: int) -> dict[str, list[dict[str, Any]]]:
    """News for every top mover at once; each lookup is an independent search."""
    from concurrent.futures import ThreadPoolExecutor

    names = [str(r["name"]) for r in movers]
    if not names:
        return {}

    def one(name: str) -> list[dict[str, Any]]:
        try:
            return _news_for_holding(name, question, window) or []
        except Exception:  # noqa: BLE001 - one failed search must not drop the others
            return []

    with ThreadPoolExecutor(max_workers=min(6, len(names))) as pool:
        return dict(zip(names, pool.map(one, names)))


def _fund_return(evidence: EvidenceSet, isin: str) -> float | None:
    val, _alt = _fund_return_detail(evidence, isin)
    return val


def _fund_return_detail(evidence: EvidenceSet, isin: str) -> tuple[float | None, float | None]:
    """Canonical return, plus one alternate figure when a second series disagrees."""
    key = (isin or "").upper()
    canonical: float | None = None
    seen: list[float] = []
    for item in evidence.by_facet("return_series") + evidence.by_facet("fund_facts_nav"):
        d = item.data if isinstance(item.data, dict) else {}
        if key and str(d.get("isin") or item.entity_key or "").upper() not in ("", key):
            continue
        for field in ("window_pct", "return_pct", "window_return_pct", "return_1m_pct"):
            val = d.get(field)
            if isinstance(val, (int, float)):
                rounded = round(float(val), 2)
                seen.append(rounded)
                if canonical is None and field in ("window_pct", "return_pct"):
                    canonical = rounded
    if canonical is None and seen:
        canonical = seen[0]
    alternate = next((v for v in seen if canonical is not None and abs(v - canonical) > 0.15), None)
    return canonical, alternate


def _price_holdings(holdings: list[Any], window: int) -> list[dict[str, Any]]:
    from historical_data.stocks_service import get_stock_profile

    rows: list[dict[str, Any]] = []
    ranked = [h for h in holdings if isinstance(h, dict) and h.get("name")]
    ranked.sort(key=lambda h: -float(h.get("percentage") or 0))
    for h in ranked[:30]:
        name = str(h.get("name"))
        profile = get_stock_profile(name) or {}
        if window <= 10:
            raw = profile.get("return_1w")
        else:
            raw = profile.get("return_1m")
        try:
            ret = round(float(raw), 2) if raw is not None else None
        except (TypeError, ValueError):
            ret = None
        rows.append(
            {
                "name": name,
                "industry": str(h.get("industry") or ""),
                "sector": str(h.get("industry") or ""),
                "weight_pct": float(h.get("percentage") or 0),
                "return_pct": ret,
            }
        )
    return rows


def _unique_movers(attr: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in list(attr.get("detractors") or []) + list(attr.get("contributors") or []):
        name = str(row.get("name") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(dict(row))
    return out


def _news_for_holding(name: str, question: str, window: int) -> list[dict[str, Any]]:
    from news_rag.holdings_market import fetch_dedicated_holding_news

    try:
        arts = fetch_dedicated_holding_news(name, question, window_days=window, limit=2) or []
    except Exception:
        return []
    return [a for a in arts if isinstance(a, dict)][:1]


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
