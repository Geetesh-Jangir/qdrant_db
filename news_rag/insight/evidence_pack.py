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

        if tool == "get_fund_data":
            # Extract snapshot, return series, attribution
            fund_name = r.get("fund") or ""
            if isinstance(data, dict):
                data_pack[f"fund:{fund_name or 'primary'}"] = data
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
            data_pack["market"] = data
            rows.append(EvidenceRow(
                entity_id="market",
                entity_type="market",
                entity_name="Market Benchmark & Macro",
                metrics=data,
                evidence_ids=["market_snapshot"],
            ))

        elif tool == "screen_funds_by_exposure":
            data_pack["screen"] = data
            rows.append(EvidenceRow(
                entity_id="screen",
                entity_type="screen",
                entity_name="Screened Funds",
                metrics=data,
                evidence_ids=["screen_funds"],
            ))

        elif tool == "search_financial_news":
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

    perf = _fund_performance_digest(data_pack)
    from news_rag.insight.fund_display import build_fund_display_tables

    from news_rag.insight.display_table_policy import (
        filter_display_tables,
        resolve_display_table_policy,
    )

    all_tables = build_fund_display_tables(data_pack, digest=perf, question=question)
    table_policy = resolve_display_table_policy(question, plan)
    display_tables = filter_display_tables(all_tables, table_policy)

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

    fund_name = str(mgr.get("fund_name") or (plan.funds[0] if plan.funds else "Fund")).strip()
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

    # Check for Single Fund Snapshot / NAV
    fund_entries = [v for k, v in data.items() if k.startswith("fund:")]
    portfolio_entries = [v for k, v in data.items() if k.startswith("portfolio:")]

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
            return "\n".join(lines)

        if dt.get("vs_benchmark_table") and plan.answer_mode == AnswerMode.DATA_ONLY:
            name = dt.get("_title") or (plan.funds[0] if plan.funds else "Fund")
            lines = [f"### Returns — {name}", "", dt["vs_benchmark_table"]]
            if dt.get("short_horizon_vs_category_table"):
                lines.extend(["", dt["short_horizon_vs_category_table"]])
            return "\n".join(lines)

        snap = f_data.get("snapshot") or (f_data if f_data.get("nav") is not None else {})
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

            return "\n".join(lines)

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

    if "screen" in data:
        screen = data.get("screen") or {}
        rankings = screen.get("rankings") or screen.get("funds") or []
        if not rankings:
            note = str(screen.get("ranking_note") or screen.get("note") or "").strip()
            sector = str(screen.get("sector_name") or "").strip()
            lines = ["### Fund screen"]
            if sector:
                lines.append(f"No funds matched **{sector}** with the filters used.")
            else:
                lines.append("No funds matched your screen filters.")
            if note:
                lines.append(note)
            return "\n".join(lines)
        if rankings:
            from news_rag.tools import return_window_label

            window = str(screen.get("return_window") or "1M").upper()
            n = min(len(rankings), 15)
            lines = [
                f"### Funds screened ({return_window_label(window)} return)",
                "",
                f"**{n}** fund(s) matched your filters. Measured returns are in the table below.",
            ]
            note = str(screen.get("ranking_note") or "").strip()
            if note:
                lines.extend(["", note])
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
