"""Evidence Pack — joins metrics and news per canonical entity for the composer.

Eliminates the disjoint DATA vs NEWS dichotomy by joining all collected facts
by entity (fund, sector, stock, market) with token budget bounding.

Also provides deterministic DATA_ONLY templates that bypass the composer LLM
entirely for instant lookup answers (<500ms).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from news_rag.insight.contracts import (
    AnswerMode,
    EvidencePack,
    EvidenceRow,
    ExecutionPlan,
)

logger = logging.getLogger(__name__)


def _fund_performance_digest(data_pack: dict[str, Any]) -> dict[str, Any]:
    """Compact NAV/returns/benchmark for composer — kept even when NEWS is trimmed."""
    for key, block in data_pack.items():
        if not str(key).startswith("fund:") or not isinstance(block, dict):
            continue
        snap = block.get("snapshot")
        if not isinstance(snap, dict):
            snap = block if block.get("nav") is not None else {}
        if not snap:
            continue
        name = (
            snap.get("fund_name")
            or snap.get("fund_short_name")
            or str(key).replace("fund:", "")
        )
        digest: dict[str, Any] = {"fund_name": name}
        nav = snap.get("nav")
        if nav is not None:
            digest["nav"] = nav
        day = snap.get("day_change_pct")
        if day is None:
            day = snap.get("day_change")
        if day is not None:
            digest["day_change_pct"] = day
        rets = snap.get("returns")
        if isinstance(rets, dict) and rets:
            digest["returns_pct"] = {
                str(k).upper().replace("RETURN_", ""): v
                for k, v in rets.items()
                if v is not None
            }
        if snap.get("category"):
            digest["category"] = snap.get("category")
        if snap.get("benchmark"):
            digest["scheme_benchmark_name"] = snap.get("benchmark")
        if snap.get("nav_date"):
            digest["nav_date"] = snap.get("nav_date")
        if snap.get("high_52w") is not None:
            digest["52_week_high"] = snap.get("high_52w")
        if snap.get("low_52w") is not None:
            digest["52_week_low"] = snap.get("low_52w")
        expense = snap.get("expense_ratio")
        if isinstance(expense, dict) and (expense.get("regular") is not None or expense.get("direct") is not None):
            digest["expense_ratio"] = expense
        exit_load = str(snap.get("exit_load_summary") or "").strip()
        if exit_load:
            digest["exit_load_summary"] = exit_load
        if snap.get("aum") is not None:
            digest["aum_crore"] = snap.get("aum")
        if snap.get("aum_as_on_date"):
            digest["aum_as_on_date"] = snap.get("aum_as_on_date")
        r52 = snap.get("52_week_range")
        if isinstance(r52, dict) and r52.get("low") is not None:
            digest["52_week_range"] = r52

        series = block.get("return_series")
        if isinstance(series, dict):
            wr = series.get("fund_return")
            if wr is None:
                wr = series.get("window_pct")
            if wr is not None:
                digest["nav_history_window_pct"] = wr
                digest["nav_history_window_days"] = series.get("window_days")

        attr = block.get("attribution")
        if isinstance(attr, dict):
            if attr.get("fund_return") is not None:
                digest["attribution_fund_return_pct"] = attr.get("fund_return")
            from news_rag.insight.pack_sanitize import _display_holding_row, _internal_contribution_row

            top_pos = []
            internal_pos = []
            for row in (attr.get("contributors") or attr.get("top_contributors") or [])[:3]:
                if isinstance(row, dict):
                    top_pos.append(_display_holding_row(row))
                    internal_pos.append(_internal_contribution_row(row))
            top_neg = []
            internal_neg = []
            for row in (attr.get("detractors") or [])[:3]:
                if isinstance(row, dict):
                    top_neg.append(_display_holding_row(row))
                    internal_neg.append(_internal_contribution_row(row))
            if top_pos:
                digest["top_contributors"] = top_pos
            if top_neg:
                digest["top_detractors"] = top_neg
            if internal_pos or internal_neg:
                digest["holding_contribution_pp_internal"] = {
                    "contributors": internal_pos,
                    "detractors": internal_neg,
                }

        insights = block.get("fund_insights")
        if isinstance(insights, dict):
            if insights.get("category"):
                digest["category"] = insights.get("category")
            if insights.get("category_average_returns_pct"):
                digest["category_average_returns_pct"] = insights["category_average_returns_pct"]
            if insights.get("fund_returns_short_horizon_pct"):
                digest["fund_returns_short_horizon_pct"] = insights["fund_returns_short_horizon_pct"]
        vs = block.get("vs_benchmark")
        if isinstance(vs, dict):
            digest["vs_benchmark"] = vs
            if vs.get("benchmark_name"):
                digest["benchmark_name"] = vs.get("benchmark_name")
        if isinstance(insights, dict) and insights.get("comparison_periods"):
            digest["comparison_periods"] = insights["comparison_periods"]
        if isinstance(insights, dict) and insights.get("fund_returns_pct"):
            digest["fund_returns_pct"] = insights["fund_returns_pct"]

        bench = data_pack.get("market")
        if isinstance(bench, dict):
            idx = bench.get("index_return") or bench
            if isinstance(idx, dict):
                if idx.get("scheme_benchmark_name"):
                    digest["scheme_benchmark_name"] = idx.get("scheme_benchmark_name")
                nifty_block = idx.get("nifty50_reference")
                if isinstance(nifty_block, dict):
                    by_w = nifty_block.get("returns_pct")
                    if isinstance(by_w, dict) and by_w:
                        digest["nifty50_returns_pct"] = {
                            str(k).upper(): v for k, v in by_w.items() if v is not None
                        }
                    digest["nifty50_reference_note"] = nifty_block.get("note")

        return digest
    return {}


def sector_focus_from_market(market: dict[str, Any], question: str) -> dict[str, Any] | None:
    """The asked sector's return, the index return, and the gap, when both are measured."""
    from news_rag.tools import asks_sector_overview

    if not asks_sector_overview(question) or not isinstance(market, dict):
        return None
    from news_rag.sector_fund_ranking import primary_sector_for_question

    canon, keys = primary_sector_for_question(question)
    names = {str(name) for name in (canon, *keys) if name}
    ranking = market.get("sector_ranking") if isinstance(market.get("sector_ranking"), dict) else {}
    rows = list(ranking.get("leaders") or []) + list(ranking.get("laggards") or [])
    hit = None
    for row in rows:
        if isinstance(row, dict) and str(row.get("sector") or "") in names:
            hit = row
            break
    if hit is None:
        return None
    index_block = market.get("index_return") if isinstance(market.get("index_return"), dict) else {}
    sector_ret = hit.get("return_pct")
    index_ret = index_block.get("return_pct")
    gap = None
    if isinstance(sector_ret, (int, float)) and isinstance(index_ret, (int, float)):
        gap = round(float(sector_ret) - float(index_ret), 2)
    horizon = ranking.get("horizon") or index_block.get("horizon") or ""
    return {
        "sector": hit.get("sector") or canon,
        "return_pct": sector_ret,
        "index_return_pct": index_ret,
        "gap_vs_index_pct": gap,
        "horizon": horizon,
    }


def _wants_fund_ratings(question: str, plan: ExecutionPlan) -> bool:
    import re

    q = (question or "").lower()
    if re.search(r"\b(?:rupeestop\s+)?ratings?\b|\brs\s+rating\b|\b(?:our|your)\s+score\b", q):
        return True
    if "rating" in (plan.asked_facts or []):
        return True
    for call in plan.tool_calls or []:
        if call.tool == "get_fund_data" and "rating" in (call.arguments.get("modules") or []):
            return True
    return False


def _attach_rs_ratings_to_screen(
    screen: dict[str, Any] | None,
    question: str,
    plan: ExecutionPlan,
) -> None:
    """Ratings sit on every screened fund, including performance lists."""
    del question, plan
    if not isinstance(screen, dict):
        return
    from concurrent.futures import ThreadPoolExecutor

    from news_rag.fund_risk import fetch_public_rating

    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for key in ("rankings", "funds"):
        for row in list(screen.get(key) or []):
            if not isinstance(row, dict) or id(row) in seen:
                continue
            seen.add(id(row))
            if str(row.get("isin") or "").strip():
                rows.append(row)
    if not rows:
        return

    def _one(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        isin = str(row.get("isin") or "").strip().upper()
        if row.get("rs_label") and (row.get("final_score") is not None or row.get("rs_score") is not None):
            return row, {
                "label": row.get("rs_label"),
                "final_score": row.get("final_score") if row.get("final_score") is not None else row.get("rs_score"),
            }
        return row, fetch_public_rating(isin)

    workers = min(8, len(rows))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fetched = list(pool.map(_one, rows))
    for row, rating in fetched:
        if not rating or rating.get("rating_pending"):
            continue
        if rating.get("final_score") is not None:
            row["rs_score"] = rating.get("final_score")
            row["final_score"] = rating.get("final_score")
        if rating.get("label"):
            row["rs_label"] = rating.get("label")
        if rating.get("pillars"):
            row["pillars"] = rating.get("pillars")


def _refresh_fund_blocks_ratings(data_pack: dict[str, Any]) -> None:
    from news_rag.fund_risk import fetch_public_rating
    from news_rag.fund_search import get_fund_index

    for key, block in list(data_pack.items()):
        if not str(key).startswith("fund:") or not isinstance(block, dict):
            continue
        fund_name = str(block.get("fund_name") or key.removeprefix("fund:")).strip()
        detail, _amb, _close = get_fund_index().lookup_extracted_fund(name=fund_name)
        isin = str((detail or {}).get("isin") or "").strip().upper()
        if not isin:
            continue
        insights = block.get("fund_insights") if isinstance(block.get("fund_insights"), dict) else {}
        got_isin = str(insights.get("isin") or "").strip().upper()
        rating = block.get("rs_rating") if isinstance(block.get("rs_rating"), dict) else {}
        if rating:
            rating.pop("computed_at", None)
            block["rs_rating"] = rating
            if not got_isin or got_isin == isin:
                continue
            if not rating.get("pillars"):
                continue
        if not rating.get("pillars"):
            continue
        fresh = fetch_public_rating(isin)
        if fresh:
            block["rs_rating"] = fresh
        if got_isin and got_isin != isin:
            block.pop("fund_insights", None)


def build_evidence_pack(
    plan: ExecutionPlan,
    wave1_results: list[dict[str, Any]],
    wave2_results: list[dict[str, Any]],
    *,
    token_budget: int = 10000,
    question: str = "",
) -> EvidencePack:
    """Join Wave 1 and Wave 2 results into a structured EvidencePack."""
    rows: list[EvidenceRow] = []
    data_pack: dict[str, Any] = {}
    news_grouped: dict[str, Any] = {}
    limitations: list[str] = list(plan.asks_not_supported)
    missing: list[str] = []

    all_results = wave1_results + wave2_results

    # 1. Process data capabilities
    for r in all_results:
        tool = r.get("tool", "")
        ok = r.get("ok", False)
        error = r.get("error", "")
        data = r.get("data") or {}

        if not ok:
            if r.get("required", False):
                missing.append(tool)
            if error:
                limitations.append(f"Tool {tool} failed: {error}")
            continue

        if r.get("partial"):
            limitations.append(
                f"Tool {tool} returned incomplete data for {r.get('fund') or 'the fund'}; "
                "figures may be missing."
            )

        if tool == "get_fund_data":
            # Extract snapshot, return series, attribution
            fund_name = r.get("fund") or ""
            if isinstance(data, dict):
                key = f"fund:{fund_name or 'primary'}"
                previous = data_pack.get(key)
                if isinstance(previous, dict):
                    merged = dict(previous)
                    for field, value in data.items():
                        if isinstance(value, dict) and isinstance(merged.get(field), dict):
                            merged[field] = {**merged[field], **value}
                        else:
                            merged[field] = value
                    data = merged
                data_pack[key] = data
                rows.append(EvidenceRow(
                    entity_id=fund_name,
                    entity_type="fund",
                    entity_name=fund_name,
                    metrics=data,
                    evidence_ids=[f"fund_data:{fund_name}"],
                ))

        elif tool == "get_portfolio_data":
            fund_name = r.get("fund") or ""
            data_pack[f"portfolio:{fund_name or 'primary'}"] = data
            # Update or create row
            existing = next((row for row in rows if row.entity_id == fund_name), None)
            if existing:
                existing.metrics.update({"portfolio": data})
            else:
                rows.append(EvidenceRow(
                    entity_id=fund_name,
                    entity_type="fund",
                    entity_name=fund_name,
                    metrics={"portfolio": data},
                    evidence_ids=[f"portfolio:{fund_name}"],
                ))

        elif tool == "get_investor_portfolio":
            if isinstance(data, dict) and "balance_verdicts" not in data:
                from news_rag.portfolio.views import balance_verdicts_for_payload

                notes = balance_verdicts_for_payload(data)
                if notes:
                    data = {**data, "balance_verdicts": notes}
                from news_rag.insight.portfolio_intents import normalize_portfolio_intent, shape_for
                from news_rag.portfolio.insights import insight_lines, insights_for_brief

                brief_intent = normalize_portfolio_intent(getattr(plan, "portfolio_intent", ""))
                if shape_for(brief_intent) in ("brief", "insight_card"):
                    lines = insight_lines(insights_for_brief(brief_intent, data))
                    if lines:
                        data = {**data, "portfolio_insights": lines}
            data_pack["investor_portfolio"] = data
            rows.append(EvidenceRow(
                entity_id="investor",
                entity_type="investor_book",
                entity_name="Your portfolio",
                metrics=data,
                evidence_ids=["get_investor_portfolio"],
            ))

        elif tool == "compare_funds":
            data_pack["compare"] = data
            rows.append(EvidenceRow(
                entity_id="compare",
                entity_type="comparison",
                entity_name="Fund Comparison",
                metrics=data,
                evidence_ids=["compare_funds"],
            ))

        elif tool == "get_market_snapshot":
            focus = sector_focus_from_market(data, question)
            if focus:
                data = {**data, "sector_focus": focus}
            spot = data.get("metals_spot") if isinstance(data.get("metals_spot"), dict) else {}
            if spot.get("available") is False:
                data = {
                    **data,
                    "price_note": spot.get("message")
                    or "No price data for this metal. Use news only and do not invent a price or return.",
                }
            data_pack["market"] = data
            rows.append(EvidenceRow(
                entity_id="market",
                entity_type="market",
                entity_name="Market Benchmark & Macro",
                metrics=data,
                evidence_ids=["market_snapshot"],
            ))

        elif tool == "screen_funds_by_exposure":
            existing = data_pack.get("screen")
            new_rankings = [
                row for row in (data.get("rankings") or data.get("funds") or []) if isinstance(row, dict)
            ]
            if isinstance(existing, dict) and (
                existing.get("rankings") or existing.get("funds") or existing.get("multi_category_compare")
            ):
                old_rankings = [
                    row
                    for row in (existing.get("rankings") or existing.get("funds") or [])
                    if isinstance(row, dict)
                ]
                merged: list[dict[str, Any]] = []
                seen: set[str] = set()
                for row in old_rankings + new_rankings:
                    key = str(row.get("isin") or row.get("fund_name") or "").strip().lower()
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    merged.append(row)
                data = {
                    **existing,
                    **data,
                    "rankings": merged,
                    "funds": merged,
                    "multi_category_compare": True,
                    "ranking_note": (
                        "One RupeeStop-rated example per category for side-by-side comparison."
                    ),
                }
            data_pack["screen"] = data
            rows.append(EvidenceRow(
                entity_id="screen",
                entity_type="screen",
                entity_name="Screened Funds",
                metrics=data,
                evidence_ids=["screen_funds"],
            ))

        elif tool == "get_macro_news":
            if isinstance(data, dict):
                clusters = data.get("clusters") or []
                if isinstance(clusters, list) and clusters:
                    data_pack["macro_news"] = {
                        "window_days": data.get("window_days"),
                        "article_total": data.get("article_total"),
                    }
                    bucket = news_grouped.setdefault("macro", [])
                    for cluster in clusters:
                        if not isinstance(cluster, dict):
                            continue
                        theme = str(cluster.get("label") or "")
                        for a in (cluster.get("articles") or [])[:8]:
                            if not isinstance(a, dict):
                                continue
                            bucket.append(
                                {
                                    "theme": theme,
                                    "title": a.get("title") or a.get("headline", ""),
                                    "summary": a.get("summary")
                                    or a.get("snippet")
                                    or a.get("text")
                                    or "",
                                    "source": a.get("source", ""),
                                    "url": a.get("url", ""),
                                    "date": a.get("published_at")
                                    or a.get("published_date")
                                    or a.get("date", ""),
                                    "published_at": a.get("published_at")
                                    or a.get("published_date")
                                    or a.get("date", ""),
                                }
                            )

        elif tool == "search_financial_news":
            if isinstance(data.get("macro_news"), dict):
                data_pack["macro_news"] = data["macro_news"]
            # News results: handle nested grouped dict or flat list of articles
            grouped = data.get("grouped")
            if isinstance(grouped, dict) and grouped:
                for grp_scope, entities in grouped.items():
                    bucket = news_grouped.setdefault(grp_scope, [])
                    if isinstance(entities, dict):
                        for entity_name, arts in entities.items():
                            if isinstance(arts, list):
                                for a in arts[:8]:
                                    if isinstance(a, dict):
                                        bucket.append({
                                            "theme": str(entity_name or ""),
                                            "title": a.get("title") or a.get("headline", ""),
                                            "summary": a.get("summary") or a.get("snippet") or a.get("text") or "",
                                            "source": a.get("source", ""),
                                            "url": a.get("url", ""),
                                            "date": a.get("published_at") or a.get("published_date") or a.get("date", ""),
                                            "published_at": a.get("published_at") or a.get("published_date") or a.get("date", ""),
                                            "sentiment": a.get("sentiment", ""),
                                            "max_impact": a.get("max_impact"),
                                            "direction": a.get("direction"),
                                        })
                    elif isinstance(entities, list):
                        for a in entities[:8]:
                            if isinstance(a, dict):
                                bucket.append({
                                    "title": a.get("title") or a.get("headline", ""),
                                    "summary": a.get("summary") or a.get("snippet") or a.get("text") or "",
                                    "source": a.get("source", ""),
                                    "url": a.get("url", ""),
                                    "date": a.get("published_at") or a.get("published_date") or a.get("date", ""),
                                    "published_at": a.get("published_at") or a.get("published_date") or a.get("date", ""),
                                    "sentiment": a.get("sentiment", ""),
                                    "max_impact": a.get("max_impact"),
                                    "direction": a.get("direction"),
                                })
            else:
                scope = r.get("scope") or "general"
                articles = data.get("articles") or []
                if isinstance(articles, list) and articles:
                    news_grouped[scope] = [
                        {
                            "title": a.get("title") or a.get("headline", ""),
                            "summary": a.get("summary") or a.get("snippet") or a.get("text") or "",
                            "source": a.get("source", ""),
                            "url": a.get("url", ""),
                            "date": a.get("published_at") or a.get("published_date") or a.get("date", ""),
                            "published_at": a.get("published_at") or a.get("published_date") or a.get("date", ""),
                            "sentiment": a.get("sentiment", ""),
                            "max_impact": a.get("max_impact"),
                            "direction": a.get("direction"),
                        }
                        for a in articles[:8]
                        if isinstance(a, dict)
                    ]

    # Coverage summary
    coverage = {
        "wave1_tools": [r.get("tool") for r in wave1_results if r.get("ok")],
        "wave2_tools": [r.get("tool") for r in wave2_results if r.get("ok")],
        "missing_required": missing,
        "has_news": bool(news_grouped),
    }

    _attach_rs_ratings_to_screen(data_pack.get("screen"), question, plan)
    _refresh_fund_blocks_ratings(data_pack)

    perf = _fund_performance_digest(data_pack)
    from news_rag.insight.investor_drawback import attach_drawback_digest

    attach_drawback_digest(data_pack, perf, plan, question)
    from news_rag.insight.fund_display import build_fund_display_tables

    from news_rag.insight.display_table_policy import (
        filter_display_tables,
        resolve_display_table_policy,
    )

    all_tables = build_fund_display_tables(data_pack, digest=perf, question=question)
    table_policy = resolve_display_table_policy(question, plan)
    display_tables = filter_display_tables(all_tables, table_policy)
    asked = set(plan.asked_facts or [])
    if asked & {"benchmark", "returns"}:
        display_tables = dict(display_tables)
        if all_tables.get("vs_benchmark_table"):
            display_tables["vs_benchmark_table"] = all_tables["vs_benchmark_table"]
            heading = all_tables.get("_heading_vs_benchmark_table")
            if heading:
                display_tables["_heading_vs_benchmark_table"] = heading
        elif not display_tables.get("vs_benchmark_table"):
            benchmark_lines = _benchmark_lines_from_pack(data_pack)
            if benchmark_lines:
                display_tables["vs_benchmark_table"] = benchmark_lines
                display_tables["_heading_vs_benchmark_table"] = "### Returns vs benchmark"

    from news_rag.insight.insight_links import build_insight_links

    links = build_insight_links(data_pack, news_grouped)
    if links:
        data_pack["insight_links"] = links

    return EvidencePack(
        rows=rows,
        limitations=limitations,
        token_budget=token_budget,
        data_pack=data_pack,
        news_grouped=news_grouped,
        performance_digest=perf,
        display_tables=display_tables,
        display_table_policy=table_policy.for_composer(),
        coverage=coverage,
        missing=missing,
    )


# ---------------------------------------------------------------------------
# DATA_ONLY Templates (Bypass Composer LLM)
# ---------------------------------------------------------------------------


def _holding_label(h: dict[str, Any]) -> str:
    return str(
        h.get("company_name") or h.get("name") or h.get("instrument_name") or ""
    ).strip() or "—"


def _holding_weight_pct(h: dict[str, Any]) -> float:
    for key in ("weight_pct", "percentage", "weight"):
        val = h.get(key)
        if val is not None and val != "":
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return 0.0


def _sector_label(s: dict[str, Any]) -> str:
    return str(s.get("sector") or s.get("sector_label") or s.get("name") or "").strip() or "—"


def _sector_weight_pct(s: dict[str, Any]) -> float:
    for key in ("weight_pct", "percentage", "weight"):
        val = s.get(key)
        if val is not None and val != "":
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return 0.0


def _scheme_tenure_lines(fund_name: str, schemes: list[Any]) -> list[str]:
    on_scheme = [
        s
        for s in schemes
        if isinstance(s, dict)
        and fund_name.lower() in str(s.get("scheme_name") or "").lower()
    ]
    out: list[str] = []
    if on_scheme:
        out.append("- **Tenure on this scheme:**")
        for s in on_scheme[:4]:
            end = (s.get("to_date") or "").strip() or "present"
            out.append(f"  - {s.get('from_date') or '—'} → {end}")
    elif schemes:
        out.append("- **Other schemes (sample):**")
        for s in schemes[:4]:
            if not isinstance(s, dict):
                continue
            end = (s.get("to_date") or "").strip() or "ongoing"
            out.append(
                f"  - {s.get('scheme_name') or '—'} ({s.get('from_date') or '—'} – {end})"
            )
    return out


def _render_fund_managers_markdown(mgr: dict[str, Any], plan: ExecutionPlan) -> str:
    from news_rag.insight.manager_view import manager_answer_title

    from news_rag.fund_match import labels_name_the_same_scheme

    api_name = str(mgr.get("fund_name") or "").strip()
    planned = plan.funds[0] if plan.funds else ""
    if planned and api_name and not labels_name_the_same_scheme(planned, api_name):
        fund_name = planned
    else:
        fund_name = api_name or planned or "Fund"
    focus = str(mgr.get("roster_focus") or "all")
    lines = [f"## {manager_answer_title(focus, fund_name)}"]
    isin = str(mgr.get("isin") or "").strip()
    if isin:
        lines.append(f"**ISIN:** {isin}")

    note = str(mgr.get("roster_note") or "").strip()
    if note and focus in ("past", "current") and not (
        (mgr.get("display_current") or mgr.get("current"))
        or (mgr.get("display_past") or mgr.get("past"))
    ):
        lines.extend(["", note])
        return "\n".join(lines)

    def _mgr_section(title: str, rows: list[dict[str, Any]], numbered: bool) -> None:
        if not rows:
            return
        lines.extend(["", f"### {title}"])
        for i, m in enumerate(rows, start=1):
            name = str(m.get("name") or "—").strip()
            prefix = f"{i}. " if numbered else ""
            lines.append(f"\n#### {prefix}{name}")
            facts: list[str] = []
            if m.get("designation"):
                facts.append(str(m["designation"]))
            if m.get("managing_since"):
                facts.append(f"on role since {m['managing_since']}")
            if m.get("total_experience_years") is not None:
                facts.append(f"{m['total_experience_years']} yrs industry experience")
            if facts:
                lines.append(" · ".join(facts))
            if m.get("qualification"):
                lines.append(f"**Qualifications:** {m['qualification']}")
            bio = str(m.get("basic_details") or "").strip()
            if bio:
                lines.extend(["", "**About**", "", bio])
            else:
                lines.append(
                    "\n*No extended biography is published for this manager on RupeeStop.*"
                )
            tenure = _scheme_tenure_lines(fund_name, list(m.get("other_schemes") or []))
            if tenure:
                lines.extend(["", *tenure])

    current = list(mgr.get("display_current") or mgr.get("current") or [])
    past = list(mgr.get("display_past") or mgr.get("past") or [])
    if focus != "past":
        _mgr_section("Current manager(s)", current, numbered=len(current) > 1)
    if focus != "current":
        _mgr_section("Past manager(s)", past, numbered=False)

    if not current and not past:
        lines.append("\nNo fund manager records were returned for this scheme.")
    elif note:
        lines.extend(["", note])

    return "\n".join(lines)


def _portfolio_sections_from_plan(plan: ExecutionPlan) -> list[str]:
    from news_rag.insight.portfolio_plan import portfolio_sections_from_plan

    return portfolio_sections_from_plan(plan)


def _portfolio_top_n(plan: ExecutionPlan) -> int:
    for call in plan.tool_calls:
        if call.tool == "get_portfolio_data":
            try:
                return max(1, min(20, int((call.arguments or {}).get("top_n") or 3)))
            except (TypeError, ValueError):
                return 5
    return 5


def _benchmark_lines_from_pack(data_pack: dict[str, Any]) -> str:
    """Fund versus benchmark rows when the display table was not built."""
    lines: list[str] = []
    for key, value in data_pack.items():
        if not str(key).startswith("fund:") or not isinstance(value, dict):
            continue
        insights = value.get("fund_insights") if isinstance(value.get("fund_insights"), dict) else {}
        vs = value.get("vs_benchmark") if isinstance(value.get("vs_benchmark"), dict) else insights.get("vs_benchmark")
        if not isinstance(vs, dict):
            continue
        periods = vs.get("periods") if isinstance(vs.get("periods"), dict) else {}
        name = str(vs.get("benchmark_name") or insights.get("scheme_benchmark_name") or "benchmark")
        rows: list[str] = []
        for label in ("1Y", "3Y", "5Y"):
            row = periods.get(label)
            if not isinstance(row, dict):
                continue
            fund_return = row.get("fund_return")
            benchmark_return = row.get("benchmark_return")
            gap = row.get("vs_benchmark")
            if fund_return is None and benchmark_return is None:
                continue
            rows.append(
                f"| {label} | {fund_return if fund_return is not None else '—'}% | "
                f"{benchmark_return if benchmark_return is not None else '—'}% | "
                f"{gap if gap is not None else '—'} |"
            )
        if not rows:
            continue
        lines.extend(
            [
                f"Benchmark: {name}",
                "",
                "| Period | Fund | Benchmark | Fund vs benchmark (pp) |",
                "| --- | ---: | ---: | ---: |",
                *rows,
            ]
        )
    return "\n".join(lines)


def _row_bits(row: dict[str, Any]) -> list[str]:
    bits: list[str] = []
    for key, value in row.items():
        if str(key).startswith("_") or value in ("", None):
            continue
        if key == "pillars" and isinstance(value, dict):
            marks = []
            for pillar in value.values():
                if isinstance(pillar, dict) and pillar.get("score") is not None:
                    marks.append(f"{pillar.get('label') or ''} {pillar.get('score')}/{pillar.get('max')}".strip())
            if marks:
                bits.append("pillars=" + "; ".join(marks))
            continue
        if isinstance(value, (dict, list)):
            continue
        bits.append(f"{key}={value}")
    return bits


_MEASURE_WINDOWS = ("1Y", "3Y", "5Y")


def _complete_shown_funds(data_pack: dict[str, Any]) -> None:
    """Put 1Y/3Y/5Y, the riskometer, the benchmark, and the category average on each shown fund."""
    screen = data_pack.get("screen") if isinstance(data_pack.get("screen"), dict) else None
    rows = [row for row in ((screen or {}).get("rankings") or (screen or {}).get("funds") or []) if isinstance(row, dict)]
    compare = data_pack.get("compare") if isinstance(data_pack.get("compare"), dict) else None
    rows.extend(row for row in ((compare or {}).get("fund_briefs") or []) if isinstance(row, dict))
    for row in rows[:8]:
        _complete_fund_row(row)


def _complete_fund_row(row: dict[str, Any]) -> None:
    isin = str(row.get("isin") or "").strip()
    if not isin:
        return
    returns = row.get("returns") if isinstance(row.get("returns"), dict) else {}
    has_return = any(row.get(f"return_{code.lower()}_pct") is not None for code in _MEASURE_WINDOWS) or any(
        returns.get(code) is not None for code in _MEASURE_WINDOWS
    )
    has_risk = bool(row.get("riskometer"))
    has_average = any(row.get(f"category_avg_{code.lower()}_pct") is not None for code in _MEASURE_WINDOWS)
    has_benchmark = isinstance(row.get("comparison"), dict) and bool(row.get("comparison"))
    if has_return and has_risk and has_average and has_benchmark:
        return
    try:
        from news_rag.fund_search import get_fund_index

        detail = get_fund_index().get_fund_detail(isin) or {}
    except Exception:
        detail = {}
    if not isinstance(detail, dict):
        detail = {}
    catalog_returns = detail.get("returns") if isinstance(detail.get("returns"), dict) else {}
    averages = detail.get("category_average_returns") if isinstance(detail.get("category_average_returns"), dict) else {}
    owned = row.get("returns") if isinstance(row.get("returns"), dict) else None
    for code in _MEASURE_WINDOWS:
        raw = catalog_returns.get(code.lower())
        if raw is None:
            raw = catalog_returns.get(code)
        if raw is not None:
            number = round(float(raw), 2)
            row.setdefault(f"return_{code.lower()}_pct", number)
            if owned is not None:
                owned.setdefault(code, number)
        average = averages.get(code)
        if average is None:
            average = averages.get(code.lower())
        if average is not None:
            row.setdefault(f"category_avg_{code.lower()}_pct", round(float(average), 2))
    riskometer = str(detail.get("sebi_riskometer") or "").strip()
    if riskometer and not row.get("riskometer"):
        row["riskometer"] = riskometer
    if has_benchmark or not detail:
        return
    try:
        from news_rag.fund_rupeestop_metrics import build_comparison_periods, fetch_vs_benchmark

        versus = fetch_vs_benchmark(isin)
        comparison = build_comparison_periods(detail, versus, averages)
    except Exception:
        comparison = {}
    if not comparison:
        return
    row["comparison"] = comparison
    for code, item in comparison.items():
        if not isinstance(item, dict):
            continue
        if item.get("benchmark_return") is not None:
            row.setdefault(f"benchmark_{code.lower()}_pct", item["benchmark_return"])
        if item.get("vs_benchmark") is not None:
            row.setdefault(f"vs_benchmark_{code.lower()}_pct", item["vs_benchmark"])
        if item.get("category_average_return") is not None:
            row.setdefault(f"category_avg_{code.lower()}_pct", item["category_average_return"])


def table_source(data_pack: dict[str, Any]) -> str:
    """Compact rows the composer uses when it builds the answer table."""
    _complete_shown_funds(data_pack)
    lines: list[str] = []
    screen = data_pack.get("screen") if isinstance(data_pack.get("screen"), dict) else None
    rankings = list((screen or {}).get("rankings") or (screen or {}).get("funds") or [])
    for row in rankings[:8]:
        if isinstance(row, dict):
            bits = _row_bits(row)
            if bits:
                lines.append(" | ".join(bits))
    note = str((screen or {}).get("ranking_note") or "").strip()
    if note:
        lines.append(f"note={note}")
    for key, block in data_pack.items():
        if not str(key).startswith("fund:") or not isinstance(block, dict):
            continue
        snap = block.get("snapshot") if isinstance(block.get("snapshot"), dict) else {}
        insights = block.get("fund_insights") if isinstance(block.get("fund_insights"), dict) else {}
        rating = block.get("rs_rating") if isinstance(block.get("rs_rating"), dict) else {}
        risk = block.get("risk") if isinstance(block.get("risk"), dict) else {}
        returns = snap.get("returns") if isinstance(snap.get("returns"), dict) else {}
        flat: dict[str, Any] = {
            "fund": snap.get("fund_name") or insights.get("fund_name") or block.get("fund_name") or "",
            "nav": snap.get("nav"),
            "expense_ratio": (snap.get("expense_ratio") or {}).get("regular") if isinstance(snap.get("expense_ratio"), dict) else None,
            "aum": snap.get("aum"),
            "benchmark": snap.get("benchmark") or insights.get("benchmark_name") or insights.get("scheme_benchmark_name"),
            "category": insights.get("category") or snap.get("category"),
            "label": rating.get("label"),
            "final_score": rating.get("final_score"),
            "pillars": rating.get("pillars"),
            "riskometer": (
                risk.get("riskometer")
                or insights.get("riskometer")
                or insights.get("sebi_riskometer")
            ),
        }
        for code, value in returns.items():
            if value is not None:
                flat[f"return_{code}"] = value
        _add_category_comparison(flat, insights)
        bits = _row_bits(flat)
        if bits:
            lines.append(" | ".join(bits))
    compare = data_pack.get("compare") if isinstance(data_pack.get("compare"), dict) else None
    briefs = [row for row in ((compare or {}).get("fund_briefs") or []) if isinstance(row, dict)][:6]
    categories = {str(row.get("category") or "").strip().lower() for row in briefs}
    categories.discard("")
    same_category = len(categories) == 1
    for brief in briefs:
        lines.append(_compare_brief_line(brief, same_category=same_category))
    return "\n".join(lines)


def _add_category_comparison(flat: dict[str, Any], insights: dict[str, Any]) -> None:
    """Copy the 1Y/3Y/5Y fund, benchmark, and category-average figures the tool already returned."""
    periods = insights.get("comparison_periods") if isinstance(insights.get("comparison_periods"), dict) else {}
    averages = insights.get("category_average_returns_pct") if isinstance(insights.get("category_average_returns_pct"), dict) else {}
    fund_returns = insights.get("fund_returns_pct") if isinstance(insights.get("fund_returns_pct"), dict) else {}
    for code in ("1Y", "3Y", "5Y"):
        row = periods.get(code) if isinstance(periods.get(code), dict) else {}
        fund_return = row.get("fund_return")
        if fund_return is None:
            fund_return = fund_returns.get(code)
        if fund_return is not None:
            flat[f"{code}_fund"] = fund_return
        if row.get("benchmark_return") is not None:
            flat[f"{code}_benchmark"] = row.get("benchmark_return")
        average = row.get("category_average_return")
        if average is None:
            average = averages.get(code)
        if average is not None:
            flat[f"{code}_category_avg"] = average
        if row.get("vs_category") is not None:
            flat[f"{code}_vs_category"] = row.get("vs_category")
        if row.get("vs_benchmark") is not None:
            flat[f"{code}_vs_benchmark"] = row.get("vs_benchmark")


def _compare_brief_line(brief: dict[str, Any], *, same_category: bool) -> str:
    """One comparison row: 1Y/3Y/5Y unless a period was named, plus rating and benchmark."""
    windows = [str(code) for code in (brief.get("return_windows") or ["1Y", "3Y", "5Y"])]
    returns = brief.get("returns") if isinstance(brief.get("returns"), dict) else {}
    bits = [f"fund={brief.get('fund_name') or ''}"]
    if brief.get("category"):
        bits.append(f"category={brief.get('category')}")
    if brief.get("benchmark"):
        bits.append(f"benchmark={brief.get('benchmark')}")
    if brief.get("riskometer"):
        bits.append(f"riskometer={brief.get('riskometer')}")
    if brief.get("rs_label"):
        bits.append(f"rs_label={brief.get('rs_label')}")
    if brief.get("rs_score") is not None:
        bits.append(f"rs_score={brief.get('rs_score')}")
    pillars = brief.get("pillars") if isinstance(brief.get("pillars"), dict) else {}
    marks = []
    for pillar in pillars.values():
        if isinstance(pillar, dict) and pillar.get("score") is not None:
            marks.append(f"{pillar.get('label') or ''} {pillar.get('score')}/{pillar.get('max')}".strip())
    if marks:
        bits.append("pillars=" + "; ".join(marks))
    if brief.get("expense_ratio") is not None:
        bits.append(f"expense_ratio={brief.get('expense_ratio')}")
    if brief.get("aum") is not None:
        bits.append(f"aum={brief.get('aum')}")
    comparison = brief.get("comparison") if isinstance(brief.get("comparison"), dict) else {}
    for code in windows:
        row = comparison.get(code) if isinstance(comparison.get(code), dict) else {}
        fund_return = row.get("fund_return")
        if fund_return is None:
            fund_return = returns.get(code)
        if fund_return is None:
            continue
        piece = f"{code} fund={fund_return}"
        if row.get("benchmark_return") is not None:
            piece += f" benchmark={row.get('benchmark_return')} vs_benchmark={row.get('vs_benchmark')}"
        if same_category and row.get("category_average_return") is not None:
            piece += f" category_avg={row.get('category_average_return')} vs_category={row.get('vs_category')}"
        bits.append(piece)
    return "brief " + " | ".join(bits)


def extra_part_brief(data_pack: dict[str, Any]) -> str:
    """Risk notes for each fund. The comparison table does not replace these."""
    parts: list[str] = []
    for key, value in data_pack.items():
        if not str(key).startswith("fund:") or not isinstance(value, dict):
            continue
        body = _risk_body(value)
        if not body:
            continue
        name = str(value.get("fund_name") or key.removeprefix("fund:")).strip()
        parts.append(f"{name}\n{body}")
    return "\n\n".join(parts)


def investor_fact_brief(data_pack: dict[str, Any], asked: list[str] | set[str]) -> str:
    """Short fact sheet for a question that names several facts. The composer rewrites this."""
    wanted = set(asked or [])
    if len(wanted) < 2:
        return ""
    fund = next(
        (value for key, value in data_pack.items() if str(key).startswith("fund:") and isinstance(value, dict)),
        {},
    )
    portfolio = next(
        (value for key, value in data_pack.items() if str(key).startswith("portfolio:") and isinstance(value, dict)),
        {},
    )
    parts: list[str] = []
    snap = fund.get("snapshot") if isinstance(fund.get("snapshot"), dict) else {}
    name = snap.get("fund_name") or fund.get("fund_name") or ""
    if name:
        parts.append(str(name))
    if "nav" in wanted and snap.get("nav") is not None:
        nav_line = f"NAV: ₹{float(snap['nav']):,.2f}"
        if snap.get("nav_date"):
            nav_line += f" as on {snap['nav_date']}"
        parts.append(nav_line)
    if "aum" in wanted and snap.get("aum") is not None:
        aum_line = f"AUM: Rs {float(snap['aum']):,.2f} crore"
        if snap.get("aum_as_on_date"):
            aum_line += f" as on {snap['aum_as_on_date']}"
        parts.append(aum_line)
    if "expense" in wanted:
        expense = snap.get("expense_ratio") if isinstance(snap.get("expense_ratio"), dict) else {}
        if expense.get("regular") is not None:
            er = f"Expense ratio (regular): {float(expense['regular']):.2f}%"
            if expense.get("as_on_date"):
                er += f" as on {expense['as_on_date']}"
            parts.append(er)
    if "exit_load" in wanted:
        summary = str(snap.get("exit_load_summary") or "").strip()
        if summary:
            parts.append(f"Exit load: {summary}")
    if "drawdown" in wanted:
        body = _drawdown_body(fund)
        if body:
            parts.append("Drawdown:\n" + body)
    if "risk" in wanted:
        risk_body = _risk_body(fund)
        if risk_body:
            parts.append("Risk:\n" + risk_body)
    if wanted & {"benchmark", "returns"}:
        versus = _benchmark_lines_from_pack(data_pack)
        if versus:
            parts.append(versus)
    if "managers" in wanted:
        managers = fund.get("managers") if isinstance(fund.get("managers"), dict) else {}
        current = [row for row in (managers.get("current") or []) if isinstance(row, dict) and row.get("name")]
        if current:
            lines = ["Fund manager:"]
            for row in current:
                bits = [str(row.get("name"))]
                if row.get("managing_since"):
                    bits.append(f"managing since {row['managing_since']}")
                if row.get("total_experience_years") not in (None, ""):
                    bits.append(f"{row['total_experience_years']} years of experience")
                lines.append("- " + ", ".join(bits))
            parts.append("\n".join(lines))
    if "sectors" in wanted:
        sectors = [row for row in (portfolio.get("sectors") or []) if isinstance(row, dict)]
        if sectors:
            as_on = portfolio.get("as_on") or ""
            lines = [f"Top sectors{f' as on {as_on}' if as_on else ''}:"]
            for row in sectors:
                label = row.get("sector") or row.get("name") or ""
                weight = row.get("weight_pct") if row.get("weight_pct") is not None else row.get("percentage")
                if not label:
                    continue
                if weight is None:
                    lines.append(f"- {label}")
                else:
                    lines.append(f"- {label}: {float(weight):.2f}%")
            if len(lines) > 1:
                parts.append("\n".join(lines))
    rs = fund.get("rs_rating") if isinstance(fund.get("rs_rating"), dict) else {}
    if not rs and isinstance(fund.get("rating"), dict):
        rs = fund["rating"]
    if "rs_rating" in wanted and rs:
        label = str(rs.get("label") or "").strip()
        score = rs.get("final_score") if rs.get("final_score") is not None else rs.get("score")
        if label or score is not None:
            bits = [b for b in (label, f"{score} out of {rs.get('max_score') or 100}" if score is not None else "") if b]
            parts.append("RupeeStop rating: " + ", ".join(bits))
    if "four_pillars" in wanted and rs.get("pillars"):
        from news_rag.fund_risk import render_pillar_marks_table

        table = render_pillar_marks_table(rs)
        if table:
            parts.append(table)
    for slot in sorted(wanted):
        if not slot.startswith("return:"):
            continue
        code = slot.split(":", 1)[1].upper()
        returns = snap.get("returns") if isinstance(snap.get("returns"), dict) else {}
        val = returns.get(code) if returns.get(code) is not None else returns.get(code.lower())
        if val is not None:
            parts.append(f"{code} return: {float(val):+.2f}%".replace("+", ""))
    holdings = [row for row in (portfolio.get("holdings") or []) if isinstance(row, dict)]
    if "holdings" in wanted and holdings:
        lines = ["Top holdings:"]
        for row in holdings[:5]:
            label = row.get("name") or row.get("company_name") or ""
            weight = row.get("weight_pct") if row.get("weight_pct") is not None else row.get("percentage")
            if label and weight is not None:
                lines.append(f"- {label}: {float(weight):.2f}%")
        if len(lines) > 1:
            parts.append("\n".join(lines))
    return "\n\n".join(part for part in parts if part)


def _risk_body(fund_data: dict[str, Any]) -> str:
    payload = fund_data.get("risk") if isinstance(fund_data.get("risk"), dict) else None
    if not payload:
        return ""
    lines = str(payload.get("lines") or "").strip()
    if lines:
        return lines
    from news_rag.fund_risk import render_risk_lines

    return render_risk_lines(payload)


def _drawdown_body(fund_data: dict[str, Any]) -> str:
    payload = fund_data.get("drawdown") if isinstance(fund_data.get("drawdown"), dict) else None
    if not payload:
        return ""
    from news_rag.fund_drawdown import render_drawdown_body

    return render_drawdown_body(payload, str(payload.get("question") or ""))


def _with_drawdown(text: str, fund_data: dict[str, Any]) -> str:
    body = _drawdown_body(fund_data)
    if not body:
        return text
    return text.rstrip() + "\n\n### Drawdown\n\n" + body


def _show_snapshot_field(plan: ExecutionPlan, field: str) -> bool:
    asked = set(plan.asked_facts or [])
    return not asked or field in asked


def _snapshot_markdown(snap: dict[str, Any], plan: ExecutionPlan) -> str:
    name = snap.get("fund_name") or snap.get("fund_short_name") or (plan.funds[0] if plan.funds else "Fund")
    nav = snap.get("nav")
    day_change = snap.get("day_change_pct") or snap.get("day_change") or 0.0
    category = snap.get("category") or ""
    benchmark = snap.get("benchmark") or ""
    range_52w = snap.get("52_week_range") or {}
    rets = snap.get("returns") or {}
    show_all = not plan.asked_facts
    lines = [f"### {name}"]
    if _show_snapshot_field(plan, "nav") and nav is not None:
        lines.append(
            f"- **Current NAV:** ₹{nav:,.2f}" if isinstance(nav, (int, float)) else f"- **Current NAV:** ₹{nav}"
        )
    if show_all and day_change:
        sign = "+" if float(day_change) > 0 else ""
        lines.append(f"- **Day Change:** {sign}{float(day_change):.2f}%")
    if show_all and category:
        lines.append(f"- **Category:** {category}")
    if _show_snapshot_field(plan, "benchmark") and benchmark:
        lines.append(f"- **Benchmark:** {benchmark}")
    expense = snap.get("expense_ratio") if isinstance(snap.get("expense_ratio"), dict) else {}
    if _show_snapshot_field(plan, "expense") and expense.get("regular") is not None:
        ratio = f"{float(expense['regular']):.2f}%"
        if expense.get("as_on_date"):
            ratio = f"{ratio} (as on {expense['as_on_date']})"
        lines.append(f"- **Expense ratio (regular):** {ratio}")
    elif _show_snapshot_field(plan, "expense") and expense.get("direct") is not None:
        ratio = f"{float(expense['direct']):.2f}%"
        if expense.get("as_on_date"):
            ratio = f"{ratio} (as on {expense['as_on_date']})"
        lines.append(f"- **Expense ratio (direct):** {ratio}")
    exit_load = str(snap.get("exit_load_summary") or "").strip()
    if _show_snapshot_field(plan, "exit_load") and exit_load:
        lines.append(f"- **Exit load:** {exit_load}")
    if _show_snapshot_field(plan, "aum") and snap.get("aum") is not None:
        aum_text = f"Rs {float(snap['aum']):,.2f} crore"
        if snap.get("aum_as_on_date"):
            aum_text = f"{aum_text} (as on {snap['aum_as_on_date']})"
        lines.append(f"- **AUM:** {aum_text}")
    if show_all and isinstance(range_52w, dict) and range_52w.get("low") and range_52w.get("high"):
        lines.append(f"- **52-Week Range:** ₹{range_52w['low']} – ₹{range_52w['high']}")
    if _show_snapshot_field(plan, "returns") and isinstance(rets, dict) and rets:
        lines.append("\n**Historical Returns:**")
        ret_strs = [
            f"{k}: {v:+.2f}%" if isinstance(v, (int, float)) else f"{k}: {v}"
            for k, v in rets.items()
            if v is not None
        ]
        lines.append(" | ".join(ret_strs))
    for row in snap.get("unavailable_returns") or []:
        if isinstance(row, dict) and str(row.get("note") or "").strip():
            lines.append(f"- {row['note']}")
    return "\n".join(lines)


def _portfolio_markdown(p_data: dict[str, Any], plan: ExecutionPlan) -> str:
    holdings = p_data.get("holdings") or []
    sectors = p_data.get("sectors") or []
    fund_name = plan.funds[0] if plan.funds else "Fund"
    sector_rows = [s for s in sectors if _sector_label(s) != "—" or _sector_weight_pct(s) > 0]
    holding_rows = [
        h for h in holdings if _holding_label(h) != "—" and _holding_weight_pct(h) > 0
    ]
    cap = _portfolio_top_n(plan)
    sections = _portfolio_sections_from_plan(plan)
    sectors_only = sections == ["sectors"] or (sector_rows and not holding_rows)
    lines = [f"### Top {cap} sectors — {fund_name}" if sectors_only else f"### Portfolio — {fund_name}"]
    if sector_rows:
        lines.append("\n| Sector | Weight (%) |")
        lines.append("| --- | ---: |")
        for s in sector_rows[:cap]:
            lines.append(f"| {_sector_label(s)} | {_sector_weight_pct(s):.2f}% |")
    if holding_rows and "holdings" in sections:
        lines.append("\n| Stock / company | Sector | Weight (%) |")
        lines.append("| --- | --- | ---: |")
        for h in holding_rows[:cap]:
            lines.append(
                f"| {_holding_label(h)} | {h.get('sector') or h.get('industry') or '—'} | "
                f"{_holding_weight_pct(h):.2f}% |"
            )
        top_sum = round(sum(_holding_weight_pct(h) for h in holding_rows[:cap]), 2)
        as_on = str(p_data.get("as_on") or "").strip()
        suffix = f" (as on {as_on})" if as_on else ""
        lines.append(
            f"\nTogether, the top {min(cap, len(holding_rows))} holdings make up **{top_sum:.2f}%** "
            f"of the fund{suffix}."
        )
    return "\n".join(lines)


_RETURN_ROWS = ("1Y", "3Y", "5Y")


def _compare_cell(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "/")


def _compare_header(briefs: list[dict[str, Any]]) -> list[str]:
    names = [str(b.get("fund_name") or "Fund") for b in briefs]
    return [
        "",
        "| | " + " | ".join(names) + " |",
        "| --- | " + " | ".join("---" for _ in names) + " |",
    ]


def _mix_cell(rows: Any) -> str:
    if not isinstance(rows, list):
        return "—"
    parts: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()
        try:
            percentage = float(row.get("percentage"))
        except (TypeError, ValueError):
            continue
        if label:
            parts.append(f"{label} {percentage:.2f}%")
    return ", ".join(parts) if parts else "—"


def _risk_for_brief(brief: dict[str, Any], fund_entries: list[dict[str, Any]]) -> dict[str, Any]:
    name = str(brief.get("fund_name") or "").strip().lower()
    for entry in fund_entries:
        risk = entry.get("risk") if isinstance(entry.get("risk"), dict) else None
        if not risk:
            continue
        fund_name = str(risk.get("fund_name") or entry.get("fund_name") or "").strip().lower()
        if fund_name and (fund_name == name or fund_name in name or name in fund_name):
            return risk
    return {}


def _render_fund_compare_markdown(
    compare: dict[str, Any],
    fund_entries: list[dict[str, Any]] | None = None,
) -> str:
    overlap = compare.get("holding_overlap") if isinstance(compare.get("holding_overlap"), dict) else {}
    fund_names = [str(name) for name in (overlap.get("fund_names") or []) if name]
    briefs = [row for row in (compare.get("fund_briefs") or []) if isinstance(row, dict)]
    lines = ["## Fund comparison"]
    if briefs:
        lines.extend(_compare_header(briefs))

        def _row(label: str, values: list[str]) -> None:
            lines.append("| " + " | ".join([label, *values]) + " |")

        _row("NAV", [_compare_cell(b.get("nav")) for b in briefs])
        _row(
            "AUM (Rs crore)",
            [
                _compare_cell(f"{float(b['aum']):,.2f}" if b.get("aum") is not None else None)
                for b in briefs
            ],
        )
        _row(
            "Expense ratio",
            [
                _compare_cell(f"{float(b['expense_ratio']):.2f}%" if b.get("expense_ratio") is not None else None)
                for b in briefs
            ],
        )
        _row("Category", [_compare_cell(b.get("category")) for b in briefs])
        _row("Top sector", [_compare_cell(b.get("top_sector")) for b in briefs])
        _row("Exit load", [_compare_cell(b.get("exit_load_summary")) for b in briefs])

        lines.extend(["", "### Historical returns", *_compare_header(briefs)[1:]])
        windows = [str(code) for code in (compare.get("return_windows") or _RETURN_ROWS)]
        for window in windows:
            values = []
            for brief in briefs:
                returns = brief.get("returns") if isinstance(brief.get("returns"), dict) else {}
                raw = returns.get(window)
                values.append(_compare_cell(f"{float(raw):.2f}%" if raw is not None else None))
            lines.append("| " + " | ".join([window, *values]) + " |")
    cells = compare.get("drawdown_cells") if isinstance(compare.get("drawdown_cells"), dict) else {}
    if cells:
        lines.extend(["", "### Drawdown", *_compare_header(briefs)[1:]])
        labels = {"1y": "1Y worst fall", "3y": "3Y worst fall", "5y": "5Y worst fall"}
        for period, values in cells.items():
            lines.append("| " + " | ".join([labels.get(period, period), *[_compare_cell(v) for v in values]]) + " |")
        note = str(compare.get("drawdown_note") or "").strip()
        if note:
            lines.extend(["", note])
    risks = [_risk_for_brief(brief, fund_entries or []) for brief in briefs]
    if any(risks):
        lines.extend(["", "### Risk", *_compare_header(briefs)[1:]])

        def _risk_row(label: str, values: list[str]) -> None:
            lines.append("| " + " | ".join([label, *values]) + " |")

        _risk_row("SEBI riskometer", [_compare_cell(risk.get("riskometer")) for risk in risks])
        _risk_row("RS label", [_compare_cell(risk.get("label")) for risk in risks])
        _risk_row(
            "RS score",
            [
                _compare_cell(f"{float(risk['final_score']):.2f}" if risk.get("final_score") is not None else None)
                for risk in risks
            ],
        )
        _risk_row("Asset mix", [_mix_cell(risk.get("assets")) for risk in risks])
        _risk_row("Market cap", [_mix_cell(risk.get("market_cap")) for risk in risks])
    lines.extend(["", "### Overlapping stocks"])
    rows = [row for row in (overlap.get("rows") or []) if isinstance(row, dict)]
    if not rows:
        lines.append("")
        lines.append("There is no overlapping stock holding between these funds.")
        return "\n".join(lines)
    header_funds = fund_names or sorted({name for row in rows for name in (row.get("weights") or {})})
    lines.append("")
    lines.append("| Stock | " + " | ".join(header_funds) + " |")
    lines.append("| --- | " + " | ".join("---:" for _ in header_funds) + " |")
    for row in rows:
        weights = row.get("weights") if isinstance(row.get("weights"), dict) else {}
        cells = []
        for name in header_funds:
            value = weights.get(name)
            cells.append(f"{float(value):.2f}%" if value is not None else "—")
        lines.append("| " + " | ".join([str(row.get("stock") or "—"), *cells]) + " |")
    return "\n".join(lines)


def _render_screen_markdown(screen: Any) -> str | None:
    if not isinstance(screen, dict):
        return None
    rankings = [row for row in (screen.get("rankings") or screen.get("funds") or []) if isinstance(row, dict)]
    note = str(screen.get("ranking_note") or screen.get("note") or "").strip()
    if not rankings:
        lines = ["### Funds", "No funds matched your screen filters."]
        if note:
            lines.append(note)
        return "\n".join(lines)
    lead = _screen_lead(rankings)
    if note:
        lead = f"{lead} {note}"
    return f"### Funds\n\n{lead}\n\nThe funds are in the table below."


def _screen_lead(rankings: list[dict[str, Any]]) -> str:
    count = len(rankings)
    word = "fund" if count == 1 else "funds"
    categories = sorted({str(row.get("category") or "").strip() for row in rankings})
    categories = [item for item in categories if item]
    if len(categories) >= 2:
        return f"{count} {word} across " + " and ".join(categories) + "."
    category = _shared_value(rankings, "category")
    label = _shared_value(rankings, "rs_label")
    sentence = f"{count} {word}"
    if category:
        sentence += f" in {category}"
    if label:
        sentence += f" labeled {label}"
    return sentence + "."


def _shared_value(rankings: list[dict[str, Any]], key: str) -> str:
    values = {str(row.get(key) or "").strip() for row in rankings}
    values.discard("")
    if len(values) == 1:
        return next(iter(values))
    return ""


def _fmt_inr(value: Any) -> str:
    from news_rag.indian_format import format_inr

    return format_inr(value)


def _fmt_table_inr(value: Any) -> str:
    from news_rag.indian_format import format_inr

    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    decimals = 0 if abs(n - round(n)) < 0.005 else 2
    return format_inr(n, max_decimals=decimals)


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "—"


def _pretty_category(name: str) -> str:
    text = str(name or "").strip()
    if not text:
        return "—"
    return text[0].upper() + text[1:]


def _short_label(text: str, *, limit: int = 34) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _short_holding_name(name: str) -> str:
    text = " ".join(str(name or "").split())
    upper = text.upper()
    for suffix in (" LIMITED", " LTD.", " LTD", " CO.", " INC."):
        if upper.endswith(suffix):
            text = text[: -len(suffix)].strip()
            break
    return _short_label(text, limit=32)


def _category_rows_from_investor(investor: dict[str, Any]) -> list[tuple[str, float, float]]:
    allocation = investor.get("allocation") if isinstance(investor.get("allocation"), dict) else {}
    share = allocation.get("categoryShare")
    if isinstance(share, list) and share:
        rows: list[tuple[str, float, float]] = []
        for item in share:
            if not isinstance(item, dict):
                continue
            try:
                amt = float(item.get("aum_inr") or 0)
                pct = float(item.get("aum_pct") or 0)
            except (TypeError, ValueError):
                continue
            if amt <= 0:
                continue
            rows.append((_pretty_category(str(item.get("name") or "")), amt, round(pct, 2)))
        rows.sort(key=lambda row: row[2], reverse=True)
        if rows:
            return rows
    conc = investor.get("concentration") if isinstance(investor.get("concentration"), dict) else {}
    mapping = conc.get("aum_by_category") if isinstance(conc.get("aum_by_category"), dict) else {}
    return [(_pretty_category(name), amt, pct) for name, amt, pct in _sorted_inr_weights(mapping)]


def _render_investor_holdings_table(
    data: dict[str, Any],
    plan: ExecutionPlan,
    prefix: str,
    question: str = "",
) -> str | None:
    """Deterministic holdings / returns table (no composer — avoids grounding stripping totals)."""
    holdings = [row for row in (data.get("holdings") or []) if isinstance(row, dict)]
    if not holdings:
        return None

    from news_rag.insight.pack_sanitize import (
        _rollup_investor_summary,
        investor_holdings_for_display,
        scheme_gain_loss_pct,
    )

    rolled = _rollup_investor_summary(data)
    need = str(plan.data_need or "").lower().strip()
    returns_focus = need in ("investor_pnl", "investor_xirr")

    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    xirr_win = meta.get("xirr_window") if isinstance(meta.get("xirr_window"), dict) else {}
    win_from = str(xirr_win.get("from") or "").strip()
    win_to = str(xirr_win.get("to") or str(meta.get("as_of_date") or "")).strip()

    parts: list[str] = []
    if prefix.strip():
        parts.append(prefix.strip())

    count = len(holdings)
    if rolled.get("aum_inr") is not None and rolled.get("invested_inr") is not None:
        lead = (
            f"You hold **{count}** mutual fund scheme{'s' if count != 1 else ''}, "
            f"with current value {_fmt_inr(rolled.get('aum_inr'))} on "
            f"{_fmt_inr(rolled.get('invested_inr'))} invested"
        )
        if rolled.get("gain_loss_inr") is not None:
            lead += f" and total gain {_fmt_inr(rolled.get('gain_loss_inr'))}"
        if rolled.get("absolute_return_pct") is not None:
            lead += f" (**{float(rolled.get('absolute_return_pct')):.2f}%** overall absolute return)"
        if rolled.get("portfolio_xirr_pct") is not None:
            lead += f". Portfolio XIRR is **{_fmt_pct(rolled.get('portfolio_xirr_pct'))}**"
            if win_from and win_to:
                lead += f" for {win_from} to {win_to}"
        lead += "."
        parts.append(lead)

    heading = "### Returns by scheme\n" if returns_focus else "### Your holdings\n"
    header = (
        "| Scheme | Category | Current value (₹) | Invested (₹) | Gain/loss (₹) | "
        "Gain on invested | XIRR | RS label |\n"
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"
    )
    display_rows, total_schemes, truncated = investor_holdings_for_display(
        holdings, question, plan, sort_weakest=False
    )
    body_rows: list[str] = []
    for row in display_rows:
        rs = str(row.get("rs_label") or "—")
        if row.get("rs_score") is not None:
            rs = f"{rs} ({row.get('rs_score')})"
        gp = scheme_gain_loss_pct(row)
        body_rows.append(
            "| {name} | {cat} | {val} | {inv} | {gl} | {gp} | {xirr} | {rs} |".format(
                name=str(row.get("scheme_name") or "")[:72],
                cat=_pretty_category(str(row.get("scheme_category") or "")),
                val=_fmt_table_inr(row.get("aum_inr")).replace("₹", ""),
                inv=_fmt_table_inr(row.get("invested_inr")).replace("₹", ""),
                gl=_fmt_table_inr(row.get("gain_loss_inr")).replace("₹", ""),
                gp=_fmt_pct(gp) if gp is not None else "—",
                xirr=_fmt_pct(row.get("xirr_pct")),
                rs=rs,
            )
        )
    if not body_rows:
        return None
    table = "\n".join([header, *body_rows])
    chunks = [p for p in parts if p]
    chunks.append(heading.strip())
    if truncated:
        chunks.append(
            f"*Showing {len(display_rows)} of {total_schemes} schemes by current value; "
            f"portfolio totals include all {total_schemes} schemes.*"
        )
    lead = "\n\n".join(chunks).strip()
    return f"{lead}\n\n{table}".strip() if lead else table


def _render_investor_category_allocation_table(data: dict[str, Any]) -> str | None:
    allocation = data.get("allocation") if isinstance(data.get("allocation"), dict) else {}
    rows = [r for r in (allocation.get("categoryShare") or []) if isinstance(r, dict)]
    if len(rows) < 2:
        return None
    header = "| Category | Current value (₹) | Share |\n| --- | ---: | ---: |"
    body_rows: list[str] = []
    for row in rows:
        try:
            pct = float(row.get("aum_pct") or 0)
            amount = float(row.get("aum_inr") or 0)
        except (TypeError, ValueError):
            continue
        if amount <= 0 and pct <= 0:
            continue
        body_rows.append(
            "| {cat} | {val} | {pct} |".format(
                cat=_pretty_category(str(row.get("name") or "")),
                val=_fmt_table_inr(amount).replace("₹", ""),
                pct=f"{pct:.2f}%",
            )
        )
    if len(body_rows) < 2:
        return None
    table = "\n".join([header, *body_rows])
    return f"### Allocation by category\n\n{table}"


_SCHEME_SECTION = re.compile(
    r"^#{2,3}\s+.*\b(?:holdings|schemes)\b",
    re.I,
)


def strip_unasked_scheme_names(text: str) -> str:
    """Drop scheme tables and holdings sections when the question did not ask for a fund."""
    lines = (text or "").splitlines()
    kept: list[str] = []
    skipping = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^#{1,3}\s+", line.strip()):
            skipping = bool(_SCHEME_SECTION.match(line.strip()))
            if skipping:
                i += 1
                continue
        if skipping:
            i += 1
            continue
        if line.strip().startswith("|") and re.search(r"\bScheme\b", line):
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                i += 1
            continue
        kept.append(line)
        i += 1
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def append_investor_portfolio_overview_tables(
    prose: str,
    data: dict[str, Any],
    plan: ExecutionPlan,
    question: str = "",
) -> str:
    """Append category tables. Scheme names only when the question asked for them."""
    from news_rag.insight.investor_subject import question_wants_scheme_names

    text = (prose or "").strip()
    show_schemes = question_wants_scheme_names(question, plan)
    if not show_schemes:
        text = strip_unasked_scheme_names(text)
    alloc = _render_investor_category_allocation_table(data)
    if alloc:
        text = re.sub(
            r"### Allocation by category\b.*?(?=\n### |\Z)",
            "",
            text,
            count=1,
            flags=re.S,
        ).strip()
    blocks: list[str] = []
    if show_schemes and "### Your holdings" not in text and "### Returns by scheme" not in text:
        holdings_table = _render_investor_holdings_table(data, plan, "", question)
        if holdings_table:
            blocks.append(holdings_table)
    if alloc:
        blocks.append(alloc)
    if not blocks:
        return text
    return f"{text}\n\n" + "\n\n".join(blocks).strip()


def _render_investor_portfolio_markdown(data: dict[str, Any], plan: ExecutionPlan) -> str | None:
    """Deterministic DATA_ONLY answers for investor book slices."""
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    as_of = str(meta.get("as_of_date") or "").strip()
    prefix = f"As of {as_of}. " if as_of else ""

    from news_rag.insight.portfolio_scope import plan_wants_concentration

    conc = data.get("concentration")
    if isinstance(conc, dict) and plan_wants_concentration(plan):
        report = _portfolio_concentration_report(data)
        if report:
            return report

    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    if summary and not data.get("holdings") and not data.get("sip"):
        lines = [
            prefix + "Portfolio summary:",
            f"- Current value: {_fmt_inr(summary.get('aum_inr'))}",
            f"- Invested: {_fmt_inr(summary.get('invested_inr'))}",
            f"- Gain/loss: {_fmt_inr(summary.get('gain_loss_inr'))}",
        ]
        if summary.get("absolute_return_pct") is not None:
            lines.append(f"- Absolute return: {summary.get('absolute_return_pct')}%")
        if summary.get("portfolio_xirr_pct") is not None:
            lines.append(f"- Portfolio XIRR: {summary.get('portfolio_xirr_pct')}%")
        return "\n".join(lines)

    from news_rag.insight.portfolio_scope import investor_uses_holdings_table

    holdings = data.get("holdings") if isinstance(data.get("holdings"), list) else []
    if holdings and (plan.response_shape == "table" or investor_uses_holdings_table(plan)):
        table = _render_investor_holdings_table(data, plan, prefix)
        if table:
            return table

    sip = data.get("sip") if isinstance(data.get("sip"), dict) else {}
    plans = sip.get("plans") if isinstance(sip.get("plans"), list) else []
    if plans:
        header = "| Scheme | Amount | Frequency | Next due |\n| --- | ---: | --- | --- |"
        body_rows = []
        for row in plans:
            if not isinstance(row, dict):
                continue
            body_rows.append(
                "| {name} | {amt} | {freq} | {due} |".format(
                    name=str(row.get("scheme_name") or "")[:50],
                    amt=_fmt_inr(row.get("amount")).replace("₹", ""),
                    freq=str(row.get("frequency") or "—"),
                    due=str(row.get("next_due_date") or "—"),
                )
            )
        if body_rows:
            return prefix + "Your SIPs:\n\n" + header + "\n" + "\n".join(body_rows)

    concentration = _concentration_markdown(data.get("concentration"))
    if concentration and not holdings and not summary:
        return prefix + concentration

    return None


    return "\n".join(parts).strip()


def render_fund_concentration_answer(
    pack: EvidencePack,
    plan: ExecutionPlan,
    question: str = "",
) -> str | None:
    """Deterministic holdings/sector concentration for one mutual fund scheme."""
    from news_rag.insight.investor_drawback import plan_wants_fund_concentration

    if not plan_wants_fund_concentration(plan, question):
        return None

    data = pack.data_pack if pack else {}
    if not isinstance(data, dict):
        return None

    fund_entry = None
    portfolio_entry = None
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        if key.startswith("fund:"):
            fund_entry = val
        elif key.startswith("portfolio:"):
            portfolio_entry = val
    if portfolio_entry is None:
        return None

    fund_name = str(
        (plan.funds or [""])[0]
        or portfolio_entry.get("fund_name")
        or (fund_entry or {}).get("fund_name")
        or "Fund"
    ).strip()
    holdings = [h for h in (portfolio_entry.get("holdings") or []) if isinstance(h, dict)]
    sectors = [s for s in (portfolio_entry.get("sectors") or []) if isinstance(s, dict)]
    if not holdings and not sectors:
        return None

    composition = {}
    if isinstance(fund_entry, dict):
        composition = fund_entry.get("composition") if isinstance(fund_entry.get("composition"), dict) else {}
    risk = fund_entry.get("risk") if isinstance(fund_entry, dict) and isinstance(fund_entry.get("risk"), dict) else {}

    cap = _portfolio_top_n(plan)
    cap = max(cap, min(10, len(holdings) or len(sectors) or cap))

    holding_rows = [
        h for h in holdings if _holding_label(h) != "—" and _holding_weight_pct(h) > 0
    ]
    sector_rows = [s for s in sectors if _sector_label(s) != "—" or _sector_weight_pct(s) > 0]

    top_hold_sum = round(sum(_holding_weight_pct(h) for h in holding_rows[:cap]), 2)
    top_sector_sum = round(sum(_sector_weight_pct(s) for s in sector_rows[:cap]), 2)
    top5_official = composition.get("top_5_pct")
    top10_official = composition.get("top_10_pct")
    holding_count = composition.get("holding_count")

    lines: list[str] = [f"## {fund_name}", ""]
    summary_bits: list[str] = []
    if top_hold_sum:
        summary_bits.append(
            f"the top {min(cap, len(holding_rows))} holdings account for **{top_hold_sum:.2f}%** of the portfolio"
        )
    if top_sector_sum:
        summary_bits.append(
            f"the top {min(cap, len(sector_rows))} sectors account for **{top_sector_sum:.2f}%**"
        )
    if top5_official is not None:
        summary_bits.append(f"the scheme reports **{float(top5_official):.2f}%** in its top 5 stocks")
    if summary_bits:
        lines.append(" ".join(summary_bits[:2]).capitalize() + ".")
        if len(summary_bits) > 2:
            lines.append(summary_bits[2].capitalize() + ".")
    if holding_count is not None:
        lines.append(f"The portfolio holds **{int(holding_count)}** stocks in total.")
    lines.append("")

    if sector_rows:
        lines.append(f"### Top {min(cap, len(sector_rows))} sectors")
        lines.append("")
        lines.append("| Sector | Weight (%) |")
        lines.append("| --- | ---: |")
        for row in sector_rows[:cap]:
            lines.append(f"| {_sector_label(row)} | {_sector_weight_pct(row):.2f}% |")
        lines.append("")
        lines.append(
            f"Together, these sectors are **{top_sector_sum:.2f}%** of the fund."
        )
        lines.append("")

    if holding_rows:
        lines.append(f"### Top {min(cap, len(holding_rows))} holdings")
        lines.append("")
        lines.append("| Stock / company | Sector | Weight (%) |")
        lines.append("| --- | --- | ---: |")
        for row in holding_rows[:cap]:
            lines.append(
                f"| {_holding_label(row)} | {row.get('sector') or row.get('industry') or '—'} | "
                f"{_holding_weight_pct(row):.2f}% |"
            )
        lines.append("")
        lines.append(
            f"Together, these holdings are **{top_hold_sum:.2f}%** of the fund."
        )

    market_cap = risk.get("market_cap") if isinstance(risk.get("market_cap"), list) else []
    if market_cap:
        cap_parts = []
        for row in market_cap:
            if not isinstance(row, dict):
                continue
            label = str(row.get("label") or "").strip()
            try:
                pct = float(row.get("percentage"))
            except (TypeError, ValueError):
                continue
            if label:
                cap_parts.append(f"{label} {pct:.2f}%")
        if cap_parts:
            lines.extend(["", "### Market cap mix", "", ", ".join(cap_parts) + "."])

    if top10_official is not None and top5_official is not None:
        lines.extend(
            [
                "",
                f"Reported concentration: top 5 stocks **{float(top5_official):.2f}%**, "
                f"top 10 stocks **{float(top10_official):.2f}%**.",
            ]
        )

    return "\n".join(lines).strip()


def render_investor_concentration_answer(
    pack: EvidencePack,
    plan: ExecutionPlan,
    question: str = "",
) -> str | None:
    from news_rag.insight.portfolio_scope import plan_wants_concentration

    if not plan_wants_concentration(plan, question):
        return None
    data = pack.data_pack if pack else {}
    if not isinstance(data, dict):
        return None
    investor = data.get("investor_portfolio")
    if not isinstance(investor, dict):
        return None
    report = _portfolio_concentration_report(investor)
    return report


def repair_investor_insight_prose(text: str, investor: dict[str, Any]) -> str:
    """Replace hollow allocation / holding lines with facts from the book payload."""
    if not text or not isinstance(investor, dict):
        return text
    computed = investor.get("computed") if isinstance(investor.get("computed"), dict) else {}
    allocation = computed.get("allocation_by_category") if isinstance(computed.get("allocation_by_category"), list) else []
    summary = investor.get("summary") if isinstance(investor.get("summary"), dict) else {}
    total = computed.get("total_value_inr") or summary.get("aum_inr")
    lines_out: list[str] = []
    for line in text.splitlines():
        low = line.lower()
        if allocation and "spread across" in low and re.search(r"about\s*\)|about\s*,|\(\s*\)", line):
            parts = []
            for row in allocation:
                if not isinstance(row, dict):
                    continue
                cat = _pretty_category(str(row.get("category") or ""))
                pct = row.get("weight_pct")
                if pct is None:
                    continue
                parts.append(f"**{cat} (about {int(round(float(pct)))}%)**")
            if parts and total is not None:
                lines_out.append(
                    f"- Your portfolio weight is spread across {', '.join(parts)}, "
                    f"based on each fund's share of ₹{float(total):,.0f} total value."
                )
                continue
        if re.search(r"invested and now worth about|loss of about\s*\.?\s*$", line, re.I):
            holdings = [
                row for row in (investor.get("holdings") or []) if isinstance(row, dict) and row.get("xirr_pct") is not None
            ]
            if holdings:
                worst = min(holdings, key=lambda row: float(row.get("xirr_pct") or 0))
                name = str(worst.get("scheme_name") or "").strip()
                cat = _pretty_category(str(worst.get("scheme_category") or ""))
                inv_amt = worst.get("invested_inr")
                val = worst.get("aum_inr")
                gl = worst.get("gain_loss_inr")
                if name and inv_amt is not None and val is not None and gl is not None:
                    lines_out.append(
                        f"- **{name}** ({cat}): invested {_fmt_inr(inv_amt)} and now worth "
                        f"{_fmt_inr(val)}, a {'gain' if float(gl) >= 0 else 'loss'} of {_fmt_inr(abs(float(gl)))}."
                    )
                    continue
        lines_out.append(line)
    return "\n".join(lines_out).strip()


def _pct_of_total(part_inr: float, total_inr: float) -> float:
    if total_inr <= 0:
        return 0.0
    return round(part_inr / total_inr * 100, 2)


def _sorted_inr_weights(mapping: dict[str, Any]) -> list[tuple[str, float, float]]:
    rows: list[tuple[str, float, float]] = []
    for key, raw in (mapping or {}).items():
        try:
            amt = float(raw)
        except (TypeError, ValueError):
            continue
        if amt <= 0:
            continue
        rows.append((str(key).strip(), amt, 0.0))
    total = sum(item[1] for item in rows)
    out: list[tuple[str, float, float]] = []
    for name, amt, _ in rows:
        out.append((name, amt, _pct_of_total(amt, total)))
    out.sort(key=lambda item: item[2], reverse=True)
    return out


def _portfolio_concentration_report(investor: dict[str, Any]) -> str | None:
    conc = investor.get("concentration")
    if not isinstance(conc, dict):
        return None
    holdings = [row for row in (conc.get("top_holdings") or []) if isinstance(row, dict)]
    sectors = [row for row in (conc.get("sectors") or []) if isinstance(row, dict)]
    if not holdings and not sectors:
        return None

    weight_sum = conc.get("top_holdings_weight_pct")
    count = int(conc.get("top_holdings_count") or len(holdings))

    summary = investor.get("summary") if isinstance(investor.get("summary"), dict) else {}
    meta = investor.get("meta") if isinstance(investor.get("meta"), dict) else {}
    as_of = str(meta.get("as_of_date") or conc.get("as_of_date") or "").strip()
    try:
        scheme_count = int(summary.get("scheme_count") or 0)
    except (TypeError, ValueError):
        scheme_count = 0
    try:
        total_inr = float(conc.get("total_current_value") or summary.get("aum_inr") or 0)
    except (TypeError, ValueError):
        total_inr = 0.0

    scheme_types = _sorted_inr_weights(
        conc.get("aum_by_scheme_type") if isinstance(conc.get("aum_by_scheme_type"), dict) else {}
    )
    asset_note = ""
    if len(scheme_types) == 1:
        only_name, _, only_pct = scheme_types[0]
        asset_note = f" All in {_pretty_category(only_name)} ({_fmt_pct(only_pct)})."
    elif scheme_types:
        asset_note = " Mix: " + ", ".join(f"{_pretty_category(n)} {_fmt_pct(p)}" for n, _, p in scheme_types[:3]) + "."

    lines: list[str] = ["### Portfolio concentration", ""]
    lead_bits: list[str] = []
    if total_inr > 0:
        lead_bits.append(_fmt_table_inr(total_inr))
    if scheme_count > 0:
        word = "scheme" if scheme_count == 1 else "schemes"
        lead_bits.append(f"{scheme_count} {word}")
    if as_of:
        lead_bits.append(f"as of {as_of}")
    if lead_bits:
        lines.append(" · ".join(lead_bits) + "." + asset_note)
        lines.append("")
    lines.append(
        "Concentration is how much of your portfolio sits in each **fund category**, "
        "**underlying stock or cash line**, and **sector**."
    )
    lines.append("")

    categories = _category_rows_from_investor(investor)
    top_cat_pct = categories[0][2] if categories else 0.0
    top3_cat_pct = round(sum(item[2] for item in categories[:3]), 2) if categories else 0.0

    if categories:
        lines.extend(["### Fund categories", "", "| Category | Weight | Value |", "| --- | ---: | ---: |"])
        for name, amt, pct in categories:
            lines.append(f"| {_short_label(name, limit=28)} | {_fmt_pct(pct)} | {_fmt_table_inr(amt)} |")
        lines.extend(
            [
                "",
                f"{categories[0][0]} is the largest slice at {_fmt_pct(top_cat_pct)} "
                f"({_fmt_table_inr(categories[0][1])}). "
                f"The top three categories together are {_fmt_pct(top3_cat_pct)} of the book.",
                "",
            ]
        )

    if holdings:
        intro = f"The top {count} underlying names total {_fmt_pct(weight_sum)} of the portfolio."
        lines.extend(["### Top holdings", "", intro, ""])
        lines.extend(["| Holding | Weight | Value |", "| --- | ---: | ---: |"])
        for row in holdings:
            try:
                w = float(row.get("weight_pct") or 0)
            except (TypeError, ValueError):
                w = 0.0
            est = _fmt_table_inr(total_inr * w / 100) if total_inr > 0 else "—"
            lines.append(
                f"| {_short_holding_name(str(row.get('name') or ''))} | {_fmt_pct(row.get('weight_pct'))} | {est} |"
            )
        lines.append("")

    if sectors:
        top5 = sectors[:5]
        top5_sum = round(sum(float(r.get("weight_pct") or 0) for r in top5), 2)
        lines.extend(
            [
                "### Top sectors",
                "",
                f"These five sectors add up to {_fmt_pct(top5_sum)} of the portfolio.",
                "",
                "| Sector | Weight | Value |",
                "| --- | ---: | ---: |",
            ]
        )
        for row in top5:
            try:
                w = float(row.get("weight_pct") or 0)
            except (TypeError, ValueError):
                w = 0.0
            est = _fmt_table_inr(total_inr * w / 100) if total_inr > 0 else "—"
            lines.append(
                f"| {_short_label(str(row.get('sector') or ''), limit=30)} | {_fmt_pct(row.get('weight_pct'))} | {est} |"
            )
        lines.append("")

    read_parts: list[str] = []
    if categories:
        if top_cat_pct >= 50:
            scheme_read = "concentrated in one fund category"
        elif top_cat_pct >= 35:
            scheme_read = "moderately concentrated in one fund category"
        else:
            scheme_read = "spread across fund categories"
        read_parts.append(
            f"At the **scheme** level the book is {scheme_read} "
            f"(largest {_fmt_pct(top_cat_pct)}, top three {_fmt_pct(top3_cat_pct)})."
        )
    if holdings and weight_sum is not None:
        if float(weight_sum) <= 25:
            stock_read = "Individual **stocks** are relatively spread: the top names are a small share of the total."
        elif float(weight_sum) >= 35:
            stock_read = "Individual **stocks** are somewhat concentrated in the top names listed above."
        else:
            stock_read = "Individual **stocks** show moderate concentration in the top names listed above."
        read_parts.append(f"{stock_read} Top {count} names: {_fmt_pct(weight_sum)}.")
    if sectors:
        try:
            top_sector_w = float(sectors[0].get("weight_pct") or 0)
        except (TypeError, ValueError):
            top_sector_w = 0.0
        sector_name = str(sectors[0].get("sector") or "—")
        if top_sector_w >= 15:
            sector_read = f"**Sectors** tilt toward {sector_name} ({_fmt_pct(top_sector_w)})."
        else:
            sector_read = f"**Sectors** are fairly balanced; largest is {sector_name} at {_fmt_pct(top_sector_w)}."
        read_parts.append(sector_read)

    if read_parts:
        lines.extend(["### How to read this", ""] + read_parts)

    return "\n".join(lines).strip()


def _concentration_markdown(concentration: Any) -> str:
    if not isinstance(concentration, dict):
        return ""
    holdings = [row for row in (concentration.get("top_holdings") or []) if isinstance(row, dict)]
    sectors = [row for row in (concentration.get("sectors") or []) if isinstance(row, dict)]
    if not holdings and not sectors:
        return ""
    parts: list[str] = []
    if holdings:
        count = int(concentration.get("top_holdings_count") or len(holdings))
        weight = concentration.get("top_holdings_weight_pct")
        parts.append("### Top holdings")
        parts.append("")
        parts.append("| Holding | Weight | Funds holding it | Sector |")
        parts.append("| --- | ---: | ---: | --- |")
        for row in holdings:
            parts.append(
                "| {name} | {weight}% | {funds} | {sector} |".format(
                    name=str(row.get("name") or "")[:48],
                    weight=row.get("weight_pct"),
                    funds=row.get("fund_count") if row.get("fund_count") is not None else "—",
                    sector=str(row.get("industry") or "—")[:40],
                )
            )
        if weight is not None:
            parts.append("")
            parts.append(f"These {count} holdings are **{weight}%** of the portfolio.")
    if sectors:
        parts.append("")
        parts.append("### Top sectors")
        parts.append("")
        parts.append("| Sector | Weight |")
        parts.append("| --- | ---: |")
        for row in sectors:
            parts.append(f"| {row.get('sector')} | {row.get('weight_pct')}% |")
    return "\n".join(parts).strip()


def render_data_only_template(
    pack: EvidencePack,
    plan: ExecutionPlan,
) -> str | None:
    """Render a deterministic template for DATA_ONLY queries.

    Returns None if the data doesn't have the required structure,
    triggering fall-through to the composer LLM.
    """
    if plan.requires_compose or (plan.concept_brief or "").strip():
        return None

    data = pack.data_pack
    if not data:
        return None

    if str(plan.holding_scope or "") == "all_holdings":
        from news_rag.insight.sector_exposure_tables import render_all_holdings_metric_table

        holdings_table = render_all_holdings_metric_table(
            plan,
            memory=None,
            data_pack=data,
        )
        if holdings_table:
            return holdings_table

    investor = data.get("investor_portfolio") if isinstance(data.get("investor_portfolio"), dict) else None
    if investor and not any(str(k).startswith("fund:") for k in data):
        rendered = _render_investor_portfolio_markdown(investor, plan)
        if rendered:
            return rendered

    compare = data.get("compare") if isinstance(data.get("compare"), dict) else None
    if compare and isinstance(compare.get("holding_overlap"), dict):
        fund_entries = [value for key, value in data.items() if str(key).startswith("fund:") and isinstance(value, dict)]
        return _render_fund_compare_markdown(compare, fund_entries)

    screen_answer = _render_screen_markdown(data.get("screen"))
    if screen_answer:
        return screen_answer

    # Check for Single Fund Snapshot / NAV
    fund_entries = [v for k, v in data.items() if k.startswith("fund:")]
    portfolio_entries = [v for k, v in data.items() if k.startswith("portfolio:")]

    if fund_entries:
        f_data = fund_entries[0]
        asked = set(plan.asked_facts or [])
        if _drawdown_body(f_data) and asked <= {"drawdown"}:
            return "### Drawdown\n\n" + _drawdown_body(f_data)
        if _risk_body(f_data) and asked <= {"risk"}:
            return "### Risk\n\n" + _risk_body(f_data)
        mgr_block = f_data.get("managers")
        has_managers = bool(
            isinstance(mgr_block, dict) and (mgr_block.get("current") or mgr_block.get("past"))
        )
        snap_for_multi = f_data.get("snapshot") if isinstance(f_data.get("snapshot"), dict) else {}
        has_snap = bool(snap_for_multi) and snap_for_multi.get("nav") is not None
        asked = set(plan.asked_facts or [])
        fact_blocks = int(has_snap) + int(bool(portfolio_entries)) + int(has_managers)
        if fact_blocks >= 2:
            parts: list[str] = []
            if has_snap and (not asked or asked & {"nav", "aum", "expense", "exit_load", "returns", "benchmark"}):
                parts.append(_snapshot_markdown(snap_for_multi, plan))
            if portfolio_entries and (not asked or asked & {"sectors", "holdings"}):
                parts.append(_portfolio_markdown(portfolio_entries[0], plan))
            if has_managers and (not asked or "managers" in asked):
                parts.append(_render_fund_managers_markdown(mgr_block, plan))
            if parts:
                return _with_drawdown("\n\n".join(part for part in parts if part), f_data)

    if fund_entries and not portfolio_entries:
        f_data = fund_entries[0]
        mgr_block = f_data.get("managers")
        if isinstance(mgr_block, dict) and (mgr_block.get("current") or mgr_block.get("past")):
            return _render_fund_managers_markdown(mgr_block, plan)

        dt = pack.display_tables or {}
        if dt.get("category_average_table") and plan.goal and "category average" in plan.goal.lower():
            name = dt.get("_title") or (plan.funds[0] if plan.funds else "Fund")
            cat = (f_data.get("fund_insights") or {}).get("category") or ""
            lines = [f"### Category average — {name}"]
            if cat:
                lines.append(f"**Category:** {cat}")
            lines.append("")
            lines.append(dt["category_average_table"])
            if dt.get("vs_benchmark_table"):
                lines.extend(["", "### Fund vs benchmark (1Y / 3Y / 5Y)", "", dt["vs_benchmark_table"]])
            return _with_drawdown("\n".join(lines), f_data)

        if dt.get("vs_benchmark_table") and plan.answer_mode == AnswerMode.DATA_ONLY:
            name = dt.get("_title") or (plan.funds[0] if plan.funds else "Fund")
            lines = [f"### Returns — {name}", "", dt["vs_benchmark_table"]]
            if dt.get("short_horizon_vs_category_table"):
                lines.extend(["", dt["short_horizon_vs_category_table"]])
            return _with_drawdown("\n".join(lines), f_data)

        snap = f_data.get("snapshot") or (f_data if f_data.get("nav") is not None else {})
        if plan.asked_facts and snap and snap.get("nav") is not None:
            return _with_drawdown(_snapshot_markdown(snap, plan), f_data)
        if snap and snap.get("nav") is not None:
            name = snap.get("fund_name") or snap.get("fund_short_name") or (plan.funds[0] if plan.funds else "Fund")
            nav = snap.get("nav")
            day_change = snap.get("day_change_pct") or snap.get("day_change") or 0.0
            category = snap.get("category") or ""
            benchmark = snap.get("benchmark") or ""
            range_52w = snap.get("52_week_range") or {}
            rets = snap.get("returns") or {}

            lines = [
                f"### {name}",
                f"- **Current NAV:** ₹{nav:,.2f}" if isinstance(nav, (int, float)) else f"- **Current NAV:** ₹{nav}",
            ]
            if day_change:
                sign = "+" if float(day_change) > 0 else ""
                lines.append(f"- **Day Change:** {sign}{float(day_change):.2f}%")
            if category:
                lines.append(f"- **Category:** {category}")
            if benchmark:
                lines.append(f"- **Benchmark:** {benchmark}")
            expense = snap.get("expense_ratio") if isinstance(snap.get("expense_ratio"), dict) else {}
            if expense.get("regular") is not None:
                ratio = f"{float(expense['regular']):.2f}%"
                if expense.get("as_on_date"):
                    ratio = f"{ratio} (as on {expense['as_on_date']})"
                lines.append(f"- **Expense ratio (regular):** {ratio}")
            elif expense.get("direct") is not None:
                ratio = f"{float(expense['direct']):.2f}%"
                if expense.get("as_on_date"):
                    ratio = f"{ratio} (as on {expense['as_on_date']})"
                lines.append(f"- **Expense ratio (direct):** {ratio}")
            exit_load = str(snap.get("exit_load_summary") or "").strip()
            if exit_load:
                lines.append(f"- **Exit load:** {exit_load}")
            if snap.get("aum") is not None:
                aum_text = f"Rs {float(snap['aum']):,.2f} crore"
                if snap.get("aum_as_on_date"):
                    aum_text = f"{aum_text} (as on {snap['aum_as_on_date']})"
                lines.append(f"- **AUM:** {aum_text}")

            if isinstance(range_52w, dict) and range_52w.get("low") and range_52w.get("high"):
                lines.append(f"- **52-Week Range:** ₹{range_52w['low']} – ₹{range_52w['high']}")

            if isinstance(rets, dict) and rets:
                lines.append("\n**Historical Returns:**")
                ret_strs = [f"{k}: {v:+.2f}%" if isinstance(v, (int, float)) else f"{k}: {v}" for k, v in rets.items() if v is not None]
                lines.append(" | ".join(ret_strs))

            return _with_drawdown("\n".join(lines), f_data)

    # Check for Portfolio Holdings / Sectors
    if portfolio_entries and not fund_entries:
        p_data = portfolio_entries[0]
        holdings = p_data.get("holdings") or []
        sectors = p_data.get("sectors") or []
        fund_name = plan.funds[0] if plan.funds else "Fund"

        sector_rows = [s for s in sectors if _sector_label(s) != "—" or _sector_weight_pct(s) > 0]
        holding_rows = [
            h
            for h in holdings
            if _holding_label(h) != "—" and _holding_weight_pct(h) > 0
        ]

        cap = _portfolio_top_n(plan)
        sections = _portfolio_sections_from_plan(plan)
        sectors_only = sections == ["sectors"]
        holdings_only = sections == ["holdings"]

        if holdings_only:
            lines = [f"### Top {cap} holdings — {fund_name}"]
            if not holding_rows:
                lines.append("\nNo holding weights are available for this fund.")
                return "\n".join(lines)
            lines.append("\n| Stock / company | Sector | Weight (%) |")
            lines.append("| --- | --- | ---: |")
            for h in holding_rows[:cap]:
                lines.append(
                    f"| {_holding_label(h)} | {h.get('sector') or h.get('industry') or '—'} | "
                    f"{_holding_weight_pct(h):.2f}% |"
                )
            return "\n".join(lines)

        if sector_rows and (sectors_only or not holding_rows):
            lines = [f"### Top {cap} sectors — {fund_name}"]
            if p_data.get("sectors_from_holdings"):
                lines.append(
                    "\n_No equity sector file for this scheme; weights below are rolled up from holding asset types._"
                )
            lines.append("\n| Sector | Weight (%) |")
            lines.append("| --- | ---: |")
            for s in sector_rows[:cap]:
                lines.append(f"| {_sector_label(s)} | {_sector_weight_pct(s):.2f}% |")
            if len(sector_rows) < cap:
                lines.append("")
                lines.append(
                    f"_Only {len(sector_rows)} sector weights are available in the latest portfolio data._"
                )
            return "\n".join(lines)

        if sectors_only and holding_rows:
            lines = [f"### Top {cap} — {fund_name}"]
            lines.append(
                "\n_This scheme does not publish an equity sector breakdown; top portfolio constituents are shown instead._"
            )
            lines.append("\n| Constituent | Asset type | Weight (%) |")
            lines.append("| --- | --- | ---: |")
            for h in holding_rows[:cap]:
                lines.append(
                    f"| {_holding_label(h)} | {h.get('sector') or h.get('industry') or '—'} | "
                    f"{_holding_weight_pct(h):.2f}% |"
                )
            return "\n".join(lines)

        lines = [f"### Portfolio — {fund_name}"]
        if sector_rows and not sectors_only:
            lines.append("\n**Top sector allocations**")
            lines.append("\n| Sector | Weight (%) |")
            lines.append("|---|---:|")
            for s in sector_rows[:10]:
                lines.append(f"| {_sector_label(s)} | {_sector_weight_pct(s):.2f}% |")

        if holding_rows and not sectors_only:
            lines.append("\n**Top holdings**")
            lines.append("\n| Stock / company | Sector | Weight (%) |")
            lines.append("|---|---|---:|")
            for h in holding_rows[:10]:
                lines.append(
                    f"| {_holding_label(h)} | {h.get('sector') or h.get('industry') or '—'} | "
                    f"{_holding_weight_pct(h):.2f}% |"
                )

        if not sector_rows and not holding_rows:
            lines.append("\nNo portfolio sector or holding data is available for this fund.")
        return "\n".join(lines)

    # Check for Market Benchmark
    if "market" in data:
        m_data = data["market"]
        idx = m_data.get("index_return") or {}
        ranking = m_data.get("sector_ranking") or []
        lines = ["### Market Snapshot"]
        if idx:
            for k, v in idx.items():
                if isinstance(v, dict):
                    chg = v.get("pct_change", v.get("return", 0.0))
                    lines.append(f"- **{k.upper()}:** {float(chg):+.2f}%")
        if ranking and isinstance(ranking, list):
            lines.append("\n**Sector Performance:**")
            for item in ranking[:6]:
                if isinstance(item, dict):
                    sec = item.get("sector", "")
                    ret = item.get("return_pct", item.get("return", 0.0))
                    lines.append(f"- {sec}: {float(ret):+.2f}%")
        return "\n".join(lines)

    return None
