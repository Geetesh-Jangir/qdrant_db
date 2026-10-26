"""Evidence Pack — joins metrics and news per canonical entity for the composer.

Eliminates the disjoint DATA vs NEWS dichotomy by joining all collected facts
by entity (fund, sector, stock, market) with token budget bounding.

Also provides deterministic DATA_ONLY templates that bypass the composer LLM
entirely for instant lookup answers (<500ms).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from news_rag.insight.contracts import (
    AnswerMode,
    EvidencePack,
    EvidenceRow,
    ExecutionPlan,
)

logger = logging.getLogger(__name__)


def build_evidence_pack(
    plan: ExecutionPlan,
    wave1_results: list[dict[str, Any]],
    wave2_results: list[dict[str, Any]],
    *,
    token_budget: int = 10000,
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

    return EvidencePack(
        rows=rows,
        limitations=limitations,
        token_budget=token_budget,
        data_pack=data_pack,
        news_grouped=news_grouped,
        coverage=coverage,
        missing=missing,
    )


# ---------------------------------------------------------------------------
# DATA_ONLY Templates (Bypass Composer LLM)
# ---------------------------------------------------------------------------


def _render_fund_managers_markdown(mgr: dict[str, Any], plan: ExecutionPlan) -> str:
    fund_name = str(mgr.get("fund_name") or (plan.funds[0] if plan.funds else "Fund")).strip()
    lines = [f"### Fund manager — {fund_name}"]
    isin = str(mgr.get("isin") or "").strip()
    if isin:
        lines.append(f"- **ISIN:** {isin}")

    def _mgr_section(title: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        lines.extend(["", f"**{title}**"])
        for m in rows:
            name = m.get("name") or "—"
            lines.append(f"\n#### {name}")
            if m.get("designation"):
                lines.append(f"- **Role:** {m['designation']}")
            if m.get("managing_since"):
                lines.append(f"- **Managing since:** {m['managing_since']}")
            if m.get("total_experience_years") is not None:
                lines.append(f"- **Experience:** {m['total_experience_years']} years")
            if m.get("qualification"):
                lines.append(f"- **Qualifications:** {m['qualification']}")
            if m.get("age") is not None:
                lines.append(f"- **Age:** {m['age']}")
            if m.get("basic_details"):
                lines.append(f"- **Profile:** {m['basic_details']}")
            schemes = m.get("other_schemes") or []
            on_scheme = [
                s
                for s in schemes
                if isinstance(s, dict)
                and fund_name.lower() in str(s.get("scheme_name") or "").lower()
            ]
            if on_scheme:
                lines.append("- **Tenure on this scheme:**")
                for s in on_scheme[:3]:
                    lines.append(
                        f"  - {s.get('from_date') or '?'} → {s.get('to_date') or 'present'}"
                    )
            elif schemes:
                lines.append("- **Other schemes managed (sample):**")
                for s in schemes[:4]:
                    lines.append(
                        f"  - {s.get('scheme_name') or '—'} ({s.get('from_date') or '?'} – {s.get('to_date') or '?'})"
                    )

    _mgr_section("Current manager(s)", list(mgr.get("current") or []))
    _mgr_section("Past manager(s)", list(mgr.get("past") or []))
    if len(lines) <= 2:
        lines.append("\nNo fund manager records were returned for this scheme.")
    return "\n".join(lines)


def render_data_only_template(
    pack: EvidencePack,
    plan: ExecutionPlan,
) -> str | None:
    """Render a deterministic template for DATA_ONLY queries.

    Returns None if the data doesn't have the required structure,
    triggering fall-through to the composer LLM.
    """
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

        lines = [f"### Portfolio Holdings: {fund_name}"]
        if holdings:
            lines.append("\n| Stock / Company | Sector | Weight (%) |")
            lines.append("|---|---|---|")
            for h in holdings[:10]:
                c_name = h.get("company_name", "Unknown")
                s_name = h.get("sector", "-")
                w = h.get("weight_pct", h.get("weight", 0.0))
                lines.append(f"| {c_name} | {s_name} | {float(w):.2f}% |")

        if sectors:
            lines.append("\n**Top Sector Allocations:**")
            for s in sectors[:5]:
                s_name = s.get("sector", "Other")
                w = s.get("weight_pct", s.get("weight", 0.0))
                lines.append(f"- **{s_name}:** {float(w):.2f}%")

        return "\n".join(lines)

    if "screen" in data:
        screen = data.get("screen") or {}
        rankings = screen.get("rankings") or screen.get("funds") or []
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
