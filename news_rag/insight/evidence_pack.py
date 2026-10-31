"""Evidence Pack — joins metrics and news per canonical entity for the composer.

Eliminates the disjoint DATA vs NEWS dichotomy by joining all collected facts
by entity (fund, sector, stock, market) with token budget bounding.

Also provides deterministic DATA_ONLY templates that bypass the composer LLM
entirely for instant lookup answers (<500ms).
"""

from __future__ import annotations

import logging
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
    if not isinstance(screen, dict) or not _wants_fund_ratings(question, plan):
        return
    from news_rag.fund_risk import fetch_public_rating

    for key in ("rankings", "funds"):
        for row in list(screen.get(key) or []):
            if not isinstance(row, dict):
                continue
            isin = str(row.get("isin") or "").strip().upper()
            if not isin:
                continue
            rating = fetch_public_rating(isin)
            if not rating:
                continue
            row["rs_score"] = rating.get("final_score")
            row["rs_label"] = rating.get("label")
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
        if got_isin == isin and rating:
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
                                            "summary": a.get("summary") or a.get("snippet") or a.get("text", "")[:400],
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
                                    "summary": a.get("summary") or a.get("snippet") or a.get("text", "")[:400],
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
                            "summary": a.get("summary") or a.get("snippet") or a.get("text", "")[:400],
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
