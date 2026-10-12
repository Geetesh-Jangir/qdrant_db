"""Phase 3: deterministic finding blocks."""

from __future__ import annotations

import re
from typing import Any

from news_rag.config import get_settings
from news_rag.insight.brief import QuestionBrief
from news_rag.insight.findings import FindingLimit, Findings, FundFinding, SectorFinding
from news_rag.insight.gather import EvidenceSet
from news_rag.insight.news_digest import digest_articles, executive_sector_summary


def _topic_sector_label(brief: QuestionBrief) -> str:
    return brief.primary_sector() or "sector"


def _match_fund_rows(evidence: EvidenceSet) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in evidence.by_facet("exposure_link"):
        data = item.data
        rankings = data.get("rankings") or []
        for r in rankings:
            if isinstance(r, dict):
                rows.append(r)
    return rows


def _composition_for_isin(evidence: EvidenceSet, isin: str) -> dict[str, Any] | None:
    key = (isin or "").upper()
    for item in evidence.by_facet("fund_composition"):
        d = item.data
        if str(d.get("isin") or "").upper() == key or item.entity_key.upper() == key:
            return d
    return None


def _returns_for_isin(evidence: EvidenceSet, isin: str) -> dict[str, Any] | None:
    key = (isin or "").upper()
    for item in evidence.by_facet("return_series"):
        d = item.data
        if str(d.get("isin") or "").upper() == key or item.entity_key.upper() == key:
            return d
    return None


def _synthesize_sector_news(direction: str, themes: list[str]) -> str:
    if not themes and direction == "unknown":
        return ""
    blob = " ".join(themes).lower()
    demand = any(w in blob for w in ("growth", "sales", "demand", "festive", "gst"))
    risk = any(w in blob for w in ("risk", "inflation", "cost", "pressure", "flare", "margin"))
    parts: list[str] = []
    if direction in ("positive", "mixed", "negative"):
        parts.append(f"News tone is **{direction}**")
    if demand:
        parts.append("headlines still point to **volume/demand** themes")
    if risk:
        parts.append("with **cost or macro risks** in several stories")
    if not parts:
        parts.append("recent headlines give a **mixed** read on the sector")
    return "; ".join(parts) + "."


def _news_from_articles(articles: list[dict[str, Any]]) -> dict[str, Any]:
    pos = neg = 0
    themes: list[str] = []
    for art in articles[:40]:
        if not isinstance(art, dict):
            continue
        d = str(art.get("direction") or "").lower()
        if d == "positive":
            pos += 1
        elif d == "negative":
            neg += 1
        title = str(art.get("title") or "").strip()
        if title and len(themes) < 5:
            themes.append(title[:100])
    direction = "unknown"
    if pos > neg * 1.2 and pos:
        direction = "positive"
    elif neg > pos * 1.2 and neg:
        direction = "negative"
    elif pos or neg:
        direction = "mixed"
    return {"direction": direction, "themes": themes, "article_count": len(articles)}


def _sector_news(evidence: EvidenceSet) -> dict[str, Any]:
    for facet in ("news_drivers", "entity_state_over_time"):
        for item in evidence.by_facet(facet):
            if item.tool == "sector_news_signal":
                data = item.data
                if data.get("direction") not in (None, "", "unknown") or data.get("themes"):
                    return data
    for item in evidence.items:
        if item.tool == "sector_news_signal":
            data = item.data
            if data.get("themes") or data.get("direction") not in (None, "", "unknown"):
                return data
    if evidence.articles:
        return _news_from_articles(evidence.articles)
    return {}


def _benchmark(evidence: EvidenceSet) -> dict[str, Any]:
    for item in evidence.by_facet("benchmark"):
        return item.data
    for item in evidence.by_facet("entity_state_over_time"):
        if "return_pct" in item.data:
            return item.data
    return {}


def _verdict(
    *,
    topic_weight: float,
    topic_attrib: float,
    news_dir: str,
    fund_return: float | None,
    rel_bench: float | None,
    settings,
) -> str:
    driven_thresh = float(getattr(settings, "insight_driven_by_share_pct", 35.0))
    if topic_attrib >= driven_thresh:
        return "topic_driven"
    if topic_weight >= 15 and news_dir == "positive" and fund_return is not None and fund_return < 0:
        return "other_sector_driven"
    if topic_weight >= 15 and news_dir == "negative" and fund_return is not None and fund_return > 0:
        return "other_sector_driven"
    if rel_bench is not None and abs(rel_bench) < 1.0:
        return "market_driven"
    if topic_weight >= 10:
        return "mixed"
    return "unknown"


def _build_evidence_text(findings: Findings) -> str:
    lines: list[str] = []
    s = findings.sector
    if s:
        lines.append(f"news_direction={s.news_direction}")
        if s.index_return_pct is not None:
            lines.append(f"sector_index_return={s.index_return_pct}")
        if s.news_stats.get("avg_impact") is not None:
            lines.append(f"avg_news_impact={s.news_stats['avg_impact']}")
        lines.append(f"news_positive={s.news_stats.get('positive', 0)}")
        lines.append(f"news_negative={s.news_stats.get('negative', 0)}")
        for ins in s.news_insights[:6]:
            for m in re.findall(r"\d+(?:\.\d+)?", ins):
                lines.append(f"news_metric={m}")
        for th in s.news_themes[:5]:
            lines.append(f"news_theme={th[:80]}")
    for f in findings.funds:
        tag = f.fund_name.replace(" ", "_")[:40]
        if f.exposure_pct is not None:
            lines.append(f"{tag}_exposure={f.exposure_pct}")
        if f.return_window_pct is not None:
            lines.append(f"{tag}_return={f.return_window_pct}")
        att = f.attribution or {}
        if att.get("topic_share_pct") is not None:
            lines.append(f"{tag}_auto_share={att['topic_share_pct']}")
        if att.get("residual_other_pct") is not None:
            lines.append(f"{tag}_other_share={att['residual_other_pct']}")
        if f.relative_to_benchmark_pct is not None:
            lines.append(f"{tag}_vs_index={f.relative_to_benchmark_pct}")
        for os in f.other_top_sectors[:3]:
            lines.append(f"{tag}_{os.get('sector')}={os.get('percentage')}")
        for m in f.monthly_returns[-6:]:
            lines.append(f"{tag}_{m.get('month')}={m.get('return_pct')}")
        att = f.attribution or {}
        if att.get("topic_share_pct") is not None:
            lines.append(f"{tag}_auto_share={att['topic_share_pct']}")
        for val in (f.exposure_pct, f.return_window_pct, att.get("topic_share_pct")):
            if val is not None:
                lines.append(f"{round(float(val), 2)}")
                lines.append(f"{round(float(val), 1)}")
    return "\n".join(lines)


def compute_findings(brief: QuestionBrief, evidence: EvidenceSet) -> Findings:
    settings = get_settings()
    sector_label = _topic_sector_label(brief)
    news = _sector_news(evidence)
    bench = _benchmark(evidence)
    bench_pct = bench.get("return_pct")
    bench_label = str(bench.get("benchmark_label") or bench.get("sector_label") or "")

    themes = list(news.get("themes") or [])[:6]
    news_dir = str(news.get("direction") or "unknown")
    art_count = int(news.get("article_count") or len(evidence.articles))
    news_insights, news_stats = digest_articles(evidence.articles, limit=5)
    if news_stats.get("positive") or news_stats.get("negative"):
        pos = int(news_stats.get("positive") or 0)
        neg = int(news_stats.get("negative") or 0)
        if pos > neg * 1.2:
            news_dir = "positive"
        elif neg > pos * 1.2:
            news_dir = "negative"
        elif pos or neg:
            news_dir = "mixed"
    executive = executive_sector_summary(news_stats, news_insights)
    news_summary = executive or _synthesize_sector_news(news_dir, themes)
    sector_finding = SectorFinding(
        sector_label=sector_label,
        news_themes=themes,
        news_direction=news_dir,
        index_return_pct=bench_pct if isinstance(bench_pct, (int, float)) else None,
        benchmark_label=bench_label,
        article_count=art_count,
        news_summary=news_summary,
        news_insights=news_insights,
        news_stats=news_stats,
        executive_summary=executive,
    )

    findings = Findings(goal=brief.goal, sector=sector_finding, limits=[])
    if bench.get("substituted_broad_index"):
        findings.limits.append(
            FindingLimit("benchmark_substitute", "Sector index unavailable; used broad market proxy.")
        )

    fund_rows = _match_fund_rows(evidence)
    fund_rows.sort(
        key=lambda r: float(r.get("sector_weight_pct") or r.get("exposure_pct") or 0),
        reverse=True,
    )
    topic_keys = ("automobile", "auto")
    cap = int(getattr(settings, "insight_fan_out_cap", 8))
    filtered_rows = [
        r
        for r in fund_rows
        if float(r.get("sector_weight_pct") or r.get("exposure_pct") or 0) >= 5.0
    ]
    if not filtered_rows:
        filtered_rows = fund_rows[:cap]
    for row in filtered_rows[:cap]:
        isin = str(row.get("isin") or "")
        name = str(row.get("fund_name") or row.get("name") or isin)
        exposure = row.get("sector_weight_pct") or row.get("exposure_pct")
        try:
            exposure_f = float(exposure) if exposure is not None else None
        except (TypeError, ValueError):
            exposure_f = None
        breakdown = row.get("sector_breakdown") if isinstance(row.get("sector_breakdown"), dict) else {}
        comp = _composition_for_isin(evidence, isin) or {}
        sectors_list = comp.get("sectors") or []
        other_sectors: list[dict[str, Any]] = []
        topic_share = 0.0
        for s in sectors_list:
            if not isinstance(s, dict):
                continue
            label = str(s.get("sector") or "").lower()
            pct = float(s.get("percentage") or 0)
            if any(t in label for t in topic_keys) or label == sector_label.lower():
                topic_share += pct
            else:
                other_sectors.append({"sector": s.get("sector"), "percentage": pct})
        other_sectors.sort(key=lambda x: -float(x.get("percentage") or 0))
        other_sectors = other_sectors[:4]

        ret_data = _returns_for_isin(evidence, isin) or {}
        window_pct = ret_data.get("window_pct")
        if window_pct is None:
            try:
                window_pct = float(row.get("return_3m_pct") or row.get("return_1y_pct"))
            except (TypeError, ValueError):
                window_pct = None
        monthly = ret_data.get("monthly") if isinstance(ret_data.get("monthly"), list) else []

        rel = None
        if window_pct is not None and bench_pct is not None:
            rel = round(float(window_pct) - float(bench_pct), 2)

        news_dir = sector_finding.news_direction
        fund_ret_f = float(window_pct) if window_pct is not None else None
        divergence = False
        if news_dir == "positive" and fund_ret_f is not None and fund_ret_f < -1:
            divergence = True
        if news_dir == "negative" and fund_ret_f is not None and fund_ret_f > 1:
            divergence = True

        topic_attrib = topic_share if topic_share else (exposure_f or 0)
        residual = 100.0 - topic_attrib if topic_attrib else 0
        verdict = _verdict(
            topic_weight=topic_attrib,
            topic_attrib=topic_attrib,
            news_dir=news_dir,
            fund_return=fund_ret_f,
            rel_bench=rel,
            settings=settings,
        )

        ff = FundFinding(
            fund_name=name,
            isin=isin,
            exposure_pct=exposure_f,
            exposure_sectors=breakdown,
            other_top_sectors=other_sectors,
            return_window_pct=fund_ret_f,
            monthly_returns=monthly,
            benchmark_return_pct=float(bench_pct) if bench_pct is not None else None,
            relative_to_benchmark_pct=rel,
            news_signal=news_dir,
            divergence=divergence,
            verdict=verdict,  # type: ignore[arg-type]
            confidence="medium" if comp and ret_data else "low",
            limits=[FindingLimit("attribution_approx", "Attribution uses latest portfolio weights snapshot.")],
            attribution={
                "topic_share_pct": round(topic_attrib, 2),
                "residual_other_pct": round(residual, 2),
            },
        )
        findings.funds.append(ff)

    findings.evidence_text = _build_evidence_text(findings)
    if sector_finding.news_direction != "unknown":
        findings.cross_cutting.append(f"Sector news tone: {sector_finding.news_direction}")
    return findings
