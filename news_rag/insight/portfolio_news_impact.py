"""Portfolio-wide news → sector impact → user book exposure (extra LLM + top-holdings API)."""

from __future__ import annotations

import re
from typing import Any

from news_rag.insight.contracts import ExecutionPlan, ToolCall

_INVESTOR_TOOL = "get_investor_portfolio"
_IMPACT_RE = re.compile(
    r"\b(affect(?:ed|s|ing)?|impact(?:ed|s|ing)?|hurt|benefit|exposed|influence)\b",
    re.I,
)
_NEWS_RE = re.compile(r"\bnews\b|\bheadline\b|\bcrude\b|\boil\b|\bbrent\b|\bmacro\b", re.I)


def question_is_portfolio_news_impact(question: str, plan: ExecutionPlan) -> bool:
    """User asks how news / a macro theme would affect their own portfolio."""
    from news_rag.insight.investor_drawback import question_signals_investor_book

    q = (question or "").strip().lower()
    if not question_signals_investor_book(question) and "portfolio" not in q:
        return False
    if "portfolio" not in q and not re.search(r"\bmy\b.*\b(funds?|holdings?|book)\b", q):
        return False
    if not _IMPACT_RE.search(q):
        return False
    if not any(c.tool == "search_financial_news" for c in (plan.tool_calls or [])):
        if not _NEWS_RE.search(q):
            return False
    scope = str(plan.portfolio_scope or "").lower().strip()
    if scope == "catalog":
        return False
    if not any(c.tool == _INVESTOR_TOOL for c in (plan.tool_calls or [])):
        return False
    return True


def ensure_portfolio_news_impact_plan(plan: ExecutionPlan, question: str) -> ExecutionPlan:
    """Fetch concentration (top-holdings API) and topic-aware news when impact-on-book is asked."""
    if not question_is_portfolio_news_impact(question, plan):
        return plan
    plan.portfolio_scope = "investor"
    plan.requires_compose = True
    plan.tool_calls = [
        c for c in (plan.tool_calls or []) if c.tool != "screen_funds_by_exposure"
    ]
    for call in plan.tool_calls or []:
        if call.tool != _INVESTOR_TOOL:
            continue
        args = dict(call.arguments or {})
        modules = list(args.get("modules") or [])
        for mod in ("summary", "holdings", "allocation", "concentration"):
            if mod not in modules:
                modules.append(mod)
        args["modules"] = modules
        call.arguments = args
    for call in plan.tool_calls or []:
        if call.tool != "search_financial_news":
            continue
        args = dict(call.arguments or {})
        if not (args.get("topics") or args.get("query")):
            topics: list[str] = []
            if re.search(r"\bcrude\b|\bbrent\b|\boil\b|\bpetroleum\b", question, re.I):
                topics = ["crude oil", "crude", "brent", "oil prices"]
            else:
                topics = ["RBI", "repo rate", "inflation", "rupee", "crude oil"]
            args["topics"] = topics
            args["scope"] = args.get("scope") or "macro"
        call.arguments = args
        call.wave = 1
    if not any(c.tool == "search_financial_news" for c in plan.tool_calls or []):
        plan.tool_calls.append(
            ToolCall(
                tool="search_financial_news",
                arguments={
                    "scope": "macro",
                    "topics": ["RBI", "repo rate", "inflation", "rupee", "crude oil"],
                    "top_n": 8,
                    "window_days": min(int(plan.window_days or 7), 30),
                    "direction": "any",
                },
                wave=1,
                why="Macro news to map against portfolio sector weights",
            )
        )
    plan.presentation_notes = (
        f"{plan.presentation_notes} Map each news theme to concentration.sectors weights. "
        "Example: an RBI repo-rate item applies to Banks at that sector's portfolio weight. "
        "Say the weight from EVIDENCE. Do not invent a sector weight."
    ).strip()
    return plan


def _articles_from_pack(news_grouped: dict[str, Any]) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    for bucket in (news_grouped or {}).values():
        if isinstance(bucket, list):
            articles.extend(item for item in bucket if isinstance(item, dict))
    return articles[:12]


def _portfolio_sector_weights(raw: dict[str, Any], idx: Any) -> list[dict[str, Any]]:
    rows = raw.get("sector_allocation") if isinstance(raw.get("sector_allocation"), list) else []
    merged: dict[str, float] = {}
    labels: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("sector") or "").strip()
        try:
            pct = float(row.get("percentage") or 0)
        except (TypeError, ValueError):
            pct = 0.0
        if not label or pct <= 0:
            continue
        keys = idx.resolve_sector_keys([label])
        key = keys[0] if keys else label
        merged[key] = merged.get(key, 0.0) + pct
        labels[key] = label
    out = [
        {"sector_key": key, "sector_label": labels.get(key, key), "portfolio_weight_pct": round(pct, 2)}
        for key, pct in merged.items()
    ]
    out.sort(key=lambda row: float(row.get("portfolio_weight_pct") or 0), reverse=True)
    return out


def _rule_sector_picks(question: str, direction: str) -> list[dict[str, str]]:
    from news_rag.macro_impact_map import canonical_direction_for_driver, macro_impact_entry, normalize_driver
    from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

    idx = get_sector_fund_ranking_index()
    q = (question or "").lower()
    driver_key = ""
    for token in ("crude", "brent", "oil", "petroleum", "rupee", "inflation", "repo", "rate"):
        if re.search(rf"\b{token}\b", q):
            driver_key = normalize_driver(token)
            break
    if not driver_key:
        return []
    dir_for_map = canonical_direction_for_driver(driver_key, direction or None)
    entry = macro_impact_entry(driver_key, direction=dir_for_map or None)
    picks: list[dict[str, str]] = []
    for row in (entry or {}).get("sectors") or []:
        sign = row.get("expected_sign")
        if sign not in ("positive", "negative"):
            continue
        keys = idx.resolve_sector_keys([str(row.get("sector") or "")])
        if not keys:
            continue
        picks.append(
            {
                "name": keys[0],
                "direction": str(sign),
                "reason": str(row.get("transmission") or row.get("reason") or "").strip(),
                "source": "rule_table",
            }
        )
    return picks


def _merge_sector_picks(
    news_picks: list[dict[str, str]],
    rule_picks: list[dict[str, str]],
    direction: str,
) -> list[dict[str, str]]:
    asked = str(direction or "any").strip().lower()
    merged: dict[str, dict[str, str]] = {}
    for row in [*news_picks, *rule_picks]:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        tagged = str(row.get("direction") or asked).strip().lower()
        if tagged not in ("positive", "negative"):
            tagged = "negative" if asked == "negative" else "positive"
        if asked in ("positive", "negative") and tagged != asked:
            continue
        prev = merged.get(name)
        if prev is None or (row.get("source") != "rule_table" and prev.get("source") == "rule_table"):
            merged[name] = {**row, "name": name, "direction": tagged}
    return list(merged.values())


def _infer_direction(question: str, articles: list[dict[str, Any]]) -> str:
    q = (question or "").lower()
    if re.search(r"\brise|\brises|\brising|\bincrease|\bhigher|\bup\b|\bsurge", q):
        return "negative" if re.search(r"\bhurt|\bnegativ|\bloss|\bdrag", q) else "any"
    if re.search(r"\bfall|\bdown|\bdrop|\blower", q):
        return "positive"
    blob = " ".join(
        f"{a.get('title') or ''} {a.get('summary') or ''}" for a in articles[:6] if isinstance(a, dict)
    ).lower()
    if "rise" in blob or "surge" in blob or "higher" in blob:
        return "any"
    return "any"


def _linkage(portfolio_weight_pct: float, impact_type: str = "") -> str:
    if portfolio_weight_pct >= 1.0:
        return "direct"
    if portfolio_weight_pct > 0:
        return "direct"
    if impact_type == "indirect" or portfolio_weight_pct <= 0:
        return "indirect"
    return "indirect"


def build_portfolio_news_impact_dossier(
    *,
    question: str,
    plan: ExecutionPlan,
    data_pack: dict[str, Any],
    news_grouped: dict[str, Any],
    query_log: Any = None,
) -> dict[str, Any] | None:
    """Run sector-impact LLM, join portfolio sector weights and fund-level exposure."""
    articles = _articles_from_pack(news_grouped)
    if not articles:
        return None

    investor = data_pack.get("investor_portfolio")
    if not isinstance(investor, dict):
        return None

    from news_rag.config import get_settings
    from news_rag.portfolio.cache import get_active_crn
    from news_rag.portfolio.concentration import fetch_top_holdings
    from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

    idx = get_sector_fund_ranking_index()
    crn = get_active_crn()
    raw_holdings = fetch_top_holdings(crn)
    portfolio_sectors = _portfolio_sector_weights(raw_holdings, idx)
    portfolio_weight_by_key = {
        str(row["sector_key"]): float(row["portfolio_weight_pct"]) for row in portfolio_sectors
    }

    direction = _infer_direction(question, articles)
    rule_picks = _rule_sector_picks(question, direction)
    hint = ""
    if rule_picks:
        helped = ", ".join(p["name"] for p in rule_picks if p["direction"] == "positive")
        hurt = ", ".join(p["name"] for p in rule_picks if p["direction"] == "negative")
        hint = (
            f"\n\nTypical transmission for this driver (use only if articles support it): "
            f"helps [{helped or 'none'}]; hurts [{hurt or 'none'}]."
        )

    from news_rag.affected_sectors import pick_affected_sectors

    from news_rag.sector_fund_ranking import candidate_sector_names

    cap = int(getattr(get_settings(), "insight_sector_candidate_cap", 50) or 50)
    extra = [p["name"] for p in rule_picks]
    extra.extend(str(row.get("sector_label") or "") for row in portfolio_sectors[:20])
    prompt_names = candidate_sector_names(articles, extra, cap=cap) or idx.sector_names[:cap]

    news_picks = pick_affected_sectors(
        question=question + hint,
        articles=articles,
        direction=direction,
        sector_names=prompt_names,
        extra_sectors=extra,
        query_log=query_log,
        stage="sector_impact",
        max_tokens=1400,
    )
    sector_picks = _merge_sector_picks(news_picks, rule_picks, direction)
    if not sector_picks and rule_picks:
        sector_picks = rule_picks
    if not sector_picks:
        return None

    holdings = [r for r in (investor.get("holdings") or []) if isinstance(r, dict)]
    isin_allowlist = {str(r.get("isin") or "").strip().upper() for r in holdings if r.get("isin")}
    name_by_isin = {str(r.get("isin") or "").strip().upper(): str(r.get("scheme_name") or "") for r in holdings}
    aum_by_isin = {str(r.get("isin") or "").strip().upper(): float(r.get("aum_inr") or 0) for r in holdings}
    total_aum = sum(aum_by_isin.values()) or float((investor.get("summary") or {}).get("aum_inr") or 0)

    exposure_rows: list[dict[str, Any]] = []
    for pick in sector_picks:
        keys = idx.resolve_sector_keys([pick["name"]])
        key = keys[0] if keys else pick["name"]
        port_pct = portfolio_weight_by_key.get(key, 0.0)
        exposure_rows.append(
            {
                "sector": key,
                "direction": pick.get("direction"),
                "reason": pick.get("reason") or "",
                "source": pick.get("source") or "news",
                "portfolio_weight_pct": round(port_pct, 2),
                "linkage": _linkage(port_pct),
            }
        )

    fund_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for pick in sector_picks:
        keys = idx.resolve_sector_keys([pick["name"]])
        for key in keys or [pick["name"]]:
            for isin, sector_weight, breakdown in idx.top_funds_for_sectors(
                [key],
                limit=10,
                min_weight_pct=2.0,
                isin_allowlist=isin_allowlist,
            ):
                pair = (isin, key)
                if pair in seen:
                    continue
                seen.add(pair)
                scheme_aum = aum_by_isin.get(isin, 0.0)
                scheme_share = round(100.0 * scheme_aum / total_aum, 2) if total_aum else 0.0
                fund_rows.append(
                    {
                        "scheme_name": name_by_isin.get(isin, isin),
                        "isin": isin,
                        "sector": key,
                        "sector_weight_in_fund_pct": round(sector_weight, 2),
                        "sector_breakdown_pct": {k: round(v, 2) for k, v in breakdown.items()},
                        "scheme_portfolio_weight_pct": scheme_share,
                        "impact_direction": pick.get("direction"),
                        "sector_reason": pick.get("reason") or "",
                    }
                )
    fund_rows.sort(
        key=lambda row: (
            -float(row.get("sector_weight_in_fund_pct") or 0),
            -float(row.get("scheme_portfolio_weight_pct") or 0),
        )
    )

    return {
        "question_focus": (plan.goal or plan.planner_reading or question)[:240],
        "news_article_count": len(articles),
        "portfolio_sectors": portfolio_sectors,
        "sector_impact_analysis": exposure_rows,
        "fund_sector_exposure": fund_rows[:12],
        "macro_direction": direction,
    }


def _strip_book_concentration_tables(text: str) -> str:
    """Remove generic top-holdings / top-sectors blocks appended for overview queries."""
    cut = len(text)
    for marker in ("### Top holdings", "### Top sectors", "### Portfolio concentration"):
        idx = (text or "").find(marker)
        if idx >= 0:
            cut = min(cut, idx)
    if cut < len(text or ""):
        return (text or "")[:cut].rstrip()
    return (text or "").strip()


_NO_DRIVER = "No major news lines up with this. It looks like a broader market move."


def render_portfolio_news_impact_markdown(dossier: dict[str, Any]) -> str:
    """Deterministic sector + fund impact tables (replaces concentration + screen rankings)."""
    parts: list[str] = []
    analysis = [row for row in (dossier.get("sector_impact_analysis") or []) if isinstance(row, dict)]
    if analysis:
        parts.extend(
            [
                "### Sectors affected by the news",
                "",
                "| Sector | Direction | Your portfolio weight | Linkage | Why |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for row in analysis:
            direction = str(row.get("direction") or "—")
            weight = row.get("portfolio_weight_pct")
            weight_s = f"{float(weight):.2f}%" if weight is not None else "—"
            parts.append(
                "| {sector} | {dir} | {wt} | {link} | {why} |".format(
                    sector=str(row.get("sector") or ""),
                    dir=direction,
                    wt=weight_s,
                    link=str(row.get("linkage") or ""),
                    why=str(row.get("reason") or "").replace("|", " ")[:160],
                )
            )

    funds = [row for row in (dossier.get("fund_sector_exposure") or []) if isinstance(row, dict)]
    if funds:
        parts.extend(
            [
                "",
                "### Your funds affected",
                "",
                "| Fund | Sector | Sector weight in fund | Your portfolio weight | Expected direction | How news may affect it |",
                "| --- | --- | ---: | ---: | --- | --- |",
            ]
        )
        for row in funds:
            parts.append(
                "| {name} | {sector} | {sw}% | {pw}% | {dir} | {why} |".format(
                    name=str(row.get("scheme_name") or "")[:56],
                    sector=str(row.get("sector") or ""),
                    sw=row.get("sector_weight_in_fund_pct"),
                    pw=row.get("scheme_portfolio_weight_pct"),
                    dir=str(row.get("impact_direction") or "—"),
                    why=str(row.get("sector_reason") or "").replace("|", " ")[:120],
                )
            )
    text = "\n".join(parts).strip()
    if not text:
        return _NO_DRIVER
    return text
