"""Phase 3: deterministic finding blocks.

Turns evidence + the news read into findings:
  - sector: tone and reason (from the news reader), cited claims, index return
  - per fund: exposure, return, the weight sitting in sectors the news helps / hurts,
    the resulting news tilt, and whether the fund's actual return lined up with it.
No LLM here; every number is computed from tool output.
"""

from __future__ import annotations

import re
from typing import Any

from news_rag.config import get_settings
from news_rag.insight.brief import QuestionBrief
from news_rag.insight.findings import FindingLimit, Findings, FundFinding, SectorFinding
from news_rag.insight.gather import EvidenceSet
from news_rag.insight.news_digest import digest_articles, executive_sector_summary
from news_rag.insight.news_reader import NewsRead

MIN_NEWS_EXPOSURE = 3.0  # % of a fund in news-touched sectors before we call a tilt
DILUTED_BELOW = 15.0  # % of a fund in news-touched sectors below which the news barely reaches it
FLAT_RETURN = 1.0  # |return| % under which a fund "did not move"


def _drags_for(evidence: EvidenceSet, isin: str) -> list[dict[str, Any]]:
    key = (isin or "").upper()
    for item in evidence.by_facet("fund_attribution"):
        for row in item.data.get("funds") or []:
            if not isinstance(row, dict):
                continue
            if key and str(row.get("isin") or "").upper() not in ("", key):
                continue
            return [d for d in (row.get("drags") or []) if isinstance(d, dict)]
    return []


def _topic_sector_label(brief: QuestionBrief) -> str:
    return brief.primary_sector() or "sector"


def _match_fund_rows(evidence: EvidenceSet) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for facet in ("exposure_link", "fund_screen"):
        for item in evidence.by_facet(facet):
            for r in item.data.get("rankings") or []:
                if isinstance(r, dict):
                    key = str(r.get("isin") or r.get("fund_name") or id(r))
                    if key not in seen:
                        seen.add(key)
                        rows.append(r)
    return rows


def _named_fund_rows(evidence: EvidenceSet) -> list[dict[str, Any]]:
    """Funds the user named: built from composition/holdings when no ranking tool produced rows."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for facet in ("fund_composition", "fund_facts_holdings", "exposure_link"):
        for item in evidence.by_facet(facet):
            d = item.data
            isin = str(d.get("isin") or item.entity_key or "")
            if isin and isin not in seen:
                seen.add(isin)
                rows.append({"isin": isin, "fund_name": d.get("fund_name") or isin})
            for r in d.get("rows") or []:
                if isinstance(r, dict):
                    r_isin = str(r.get("isin") or "")
                    if r_isin and r_isin not in seen:
                        seen.add(r_isin)
                        rows.append({"isin": r_isin, "fund_name": r.get("fund_name") or r_isin})
    return rows


def _item_for_isin(
    evidence: EvidenceSet, facet: str, isin: str, prefer_key: str = ""
) -> dict[str, Any] | None:
    """Evidence dict for this ISIN. Several tools can fill one facet, so prefer the one carrying `prefer_key`."""
    key = (isin or "").upper()
    if not key:
        return None
    first: dict[str, Any] | None = None
    for item in evidence.by_facet(facet):
        d = item.data
        if str(d.get("isin") or "").upper() == key or item.entity_key.upper() == key:
            if not prefer_key or d.get(prefer_key) is not None:
                return d
            if first is None:
                first = d
    return first



def _news_from_articles(articles: list[dict[str, Any]]) -> dict[str, Any]:
    pos = neg = 0
    for art in articles[:40]:
        if not isinstance(art, dict):
            continue
        d = str(art.get("direction") or "").lower()
        if d == "positive":
            pos += 1
        elif d == "negative":
            neg += 1
    direction = "unknown"
    if pos > neg * 1.2 and pos:
        direction = "positive"
    elif neg > pos * 1.2 and neg:
        direction = "negative"
    elif pos or neg:
        direction = "mixed"
    return {"direction": direction, "article_count": len(articles)}


def _benchmark(evidence: EvidenceSet) -> dict[str, Any]:
    for item in evidence.by_facet("benchmark"):
        return item.data
    for item in evidence.by_facet("entity_state_over_time"):
        if "return_pct" in item.data:
            return item.data
    return {}


def _short_source(source: str) -> str:
    s = (source or "").lower().replace("www.", "")
    s = re.sub(r"^(m|amp)\.", "", s)
    names = {
        "economictimes": "Economic Times",
        "livemint": "Mint",
        "business-standard": "Business Standard",
        "moneycontrol": "Moneycontrol",
        "financialexpress": "Financial Express",
        "thehindubusinessline": "BusinessLine",
        "reuters": "Reuters",
        "ndtvprofit": "NDTV Profit",
        "cnbctv18": "CNBC-TV18",
    }
    head = s.split(".")[0]
    if head in names:
        return names[head]
    return head.replace("-", " ").title() if head else ""


def _fmt_date(d: str) -> str:
    # 2026-09-23 -> 23 Sep
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", d or "")
    if not m:
        return ""
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    return f"{int(m.group(3))} {months[int(m.group(2)) - 1]}"


def _claims_for_findings(read: NewsRead | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not read:
        return out
    for i, c in enumerate(read.claims, 1):
        src = _short_source(c.source)
        when = _fmt_date(c.published)
        cite = ", ".join(x for x in (src, when) if x)
        out.append(
            {
                "id": f"c{i}",
                "text": c.text,
                "sentiment": c.sentiment,
                "source": src,
                "cite": cite,
                "title": c.title,
                "url": c.url,
            }
        )
    return out


def _sector_calls(
    read: NewsRead | None,
    target: str,
    tone: str,
    picks: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Positive / negative sector lists, with the target sector added from the tone if missing.

    `picks` are the affected-sector picks from gather (news + rule table); they fill in any sector
    the reader did not mention.
    """
    pos = [{"name": s.name, "reason": s.reason} for s in (read.sectors_positive if read else [])]
    neg = [{"name": s.name, "reason": s.reason} for s in (read.sectors_negative if read else [])]
    for p in picks or []:
        item = {"name": str(p.get("name") or ""), "reason": str(p.get("reason") or "")}
        if not item["name"] or any(_name_matches(item["name"], x["name"]) for x in pos + neg):
            continue
        if p.get("direction") == "positive":
            pos.append(item)
        elif p.get("direction") == "negative":
            neg.append(item)
    if target:
        names = [x["name"].lower() for x in pos + neg]
        listed = any(target.lower() in n or n in target.lower() for n in names)
        if not listed:
            reason = read.tone_reason if read else ""
            if tone == "positive":
                pos.append({"name": target, "reason": reason})
            elif tone == "negative":
                neg.append({"name": target, "reason": reason})
            elif tone == "mixed":
                pos.append({"name": target, "reason": reason})
                neg.append({"name": target, "reason": reason})
    return pos, neg


def _name_matches(a: str, b: str) -> bool:
    x, y = (a or "").strip().lower(), (b or "").strip().lower()
    return bool(x and y and (x == y or x in y or y in x))


def _news_link_for_fund(
    comp_sectors: list[dict[str, Any]],
    pos_calls: list[dict[str, str]],
    neg_calls: list[dict[str, str]],
) -> tuple[float, float, float, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pos_total = neg_total = mix_total = 0.0
    pos_rows: list[dict[str, Any]] = []
    neg_rows: list[dict[str, Any]] = []
    mix_rows: list[dict[str, Any]] = []
    for s in comp_sectors:
        if not isinstance(s, dict):
            continue
        name = str(s.get("sector") or "")
        try:
            pct = float(s.get("percentage") or 0)
        except (TypeError, ValueError):
            continue
        if pct <= 0:
            continue
        in_pos = any(_name_matches(name, p["name"]) for p in pos_calls)
        in_neg = any(_name_matches(name, n["name"]) for n in neg_calls)
        row = {"sector": name, "percentage": round(pct, 2)}
        if in_pos and in_neg:
            mix_total += pct  # the news pulls both ways on this sector
            mix_rows.append(row)
        elif in_pos:
            pos_total += pct
            pos_rows.append(row)
        elif in_neg:
            neg_total += pct
            neg_rows.append(row)
    for rows in (pos_rows, neg_rows, mix_rows):
        rows.sort(key=lambda x: -x["percentage"])
    return round(pos_total, 2), round(neg_total, 2), round(mix_total, 2), pos_rows, neg_rows, mix_rows


def _tilt(pos: float, neg: float, mixed: float = 0.0) -> str:
    # a "mixed" sector counts half on each side
    pos, neg = pos + mixed / 2, neg + mixed / 2
    if pos < MIN_NEWS_EXPOSURE and neg < MIN_NEWS_EXPOSURE:
        return "neutral"
    hi, lo = max(pos, neg), min(pos, neg)
    if lo >= MIN_NEWS_EXPOSURE and lo / hi >= 0.5:
        return "mixed"
    return "tailwind" if pos > neg else "headwind"


def _alignment(tilt: str, touched_pct: float, ret: float | None) -> str:
    if tilt == "unknown":
        return "unknown"
    if touched_pct < DILUTED_BELOW:
        return "diluted"
    if tilt in ("mixed", "neutral"):
        return "mixed"
    if ret is None:
        return "unknown"
    if abs(ret) <= FLAT_RETURN:
        return "flat"
    if tilt == "tailwind":
        return "aligned" if ret > 0 else "diverged"
    return "aligned" if ret < 0 else "diverged"


def _mechanism(
    pos_rows: list[dict[str, Any]],
    neg_rows: list[dict[str, Any]],
    pos_calls: list[dict[str, str]],
    neg_calls: list[dict[str, str]],
) -> str:
    def reason(rows: list[dict[str, Any]], calls: list[dict[str, str]]) -> str:
        for r in rows:
            for c in calls:
                if _name_matches(str(r["sector"]), c["name"]) and c.get("reason"):
                    return c["reason"]
        return ""

    parts: list[str] = []
    rp = reason(pos_rows, pos_calls)
    rn = reason(neg_rows, neg_calls)
    if pos_rows and rp:
        parts.append(f"{pos_rows[0]['sector']}: {rp}")
    if neg_rows and rn:
        parts.append(f"{neg_rows[0]['sector']}: {rn}")
    return " | ".join(parts)


def _driver_row_tilt(row: dict[str, Any]) -> tuple[str, str]:
    """Rows from driver_affected_funds already say which way the news pushes the fund."""
    d = str(row.get("affected_direction") or "").lower()
    reason = str(row.get("sector_reason") or "")
    if d == "positive":
        return "tailwind", reason
    if d == "negative":
        return "headwind", reason
    return "unknown", reason


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
    """Everything the writer may quote. The grounding step strips numbers that are not here."""
    lines: list[str] = []
    s = findings.sector
    if s:
        lines.append(f"news_direction={s.news_direction}")
        lines.append(f"news_tone_reason={s.tone_reason}")
        if s.index_return_pct is not None:
            lines.append(f"sector_index_return={s.index_return_pct}")
            lines.append(f"sector_index_return={round(float(s.index_return_pct), 1)}")
        if s.news_stats.get("avg_impact") is not None:
            lines.append(f"avg_news_impact={s.news_stats['avg_impact']}")
        lines.append(f"news_positive={s.news_stats.get('positive', 0)}")
        lines.append(f"news_negative={s.news_stats.get('negative', 0)}")
        lines.append(f"articles={s.article_count}")
        for c in s.claims:
            lines.append(f"claim_{c['id']}={c['text']}")
        for ins in s.news_insights[:6]:
            for m in re.findall(r"\d+(?:\.\d+)?", ins):
                lines.append(f"news_metric={m}")
        for th in s.news_themes[:5]:
            lines.append(f"news_theme={th[:80]}")
        for x in s.sectors_positive + s.sectors_negative:
            lines.append(f"sector_call={x.get('name')}: {x.get('reason')}")
    for f in findings.funds:
        tag = f.fund_name.replace(" ", "_")[:40]
        vals: list[Any] = [
            f.exposure_pct,
            f.return_window_pct,
            f.relative_to_benchmark_pct,
            f.pos_exposure_pct,
            f.neg_exposure_pct,
            f.mixed_exposure_pct,
            f.pos_exposure_pct + f.neg_exposure_pct + f.mixed_exposure_pct,
            (f.attribution or {}).get("topic_share_pct"),
            (f.attribution or {}).get("residual_other_pct"),
        ]
        for os_ in f.other_top_sectors[:4]:
            vals.append(os_.get("percentage"))
            lines.append(f"{tag}_sector={os_.get('sector')}")
        for sm in f.sector_mix:
            vals.append(sm.get("percentage"))
            vals.append(sm.get("index_return_pct"))
            lines.append(f"{tag}_sector_mix={sm.get('sector')}")
        for h in f.top_holdings:
            vals.append(h.get("percentage"))
            lines.append(f"{tag}_holding={h.get('name')}")
        for m in f.monthly_returns[-6:]:
            vals.append(m.get("return_pct"))
            lines.append(f"{tag}_{m.get('month')}={m.get('return_pct')}")
        if f.exposure_pct is not None:
            lines.append(f"{tag}_exposure={f.exposure_pct}")
        if f.return_window_pct is not None:
            lines.append(f"{tag}_return={f.return_window_pct}")
        if f.relative_to_benchmark_pct is not None:
            lines.append(f"{tag}_vs_index={f.relative_to_benchmark_pct}")
        lines.append(f"{tag}_tilt={f.news_tilt} alignment={f.alignment}")
        if f.mechanism:
            lines.append(f"{tag}_mechanism={f.mechanism}")
        for drag in f.drag_sectors[:4]:
            vals.append(drag.get("weight_pct"))
            vals.append(drag.get("index_return_pct"))
            lines.append(f"{tag}_drag={drag.get('sector')} index={drag.get('index_return_pct')} news={drag.get('news')}")
            for h in drag.get("holdings") or []:
                if isinstance(h, dict):
                    vals.append(h.get("weight_pct"))
                    vals.append(h.get("return_pct"))
                    lines.append(f"{tag}_stock={h.get('name')} ret={h.get('return_pct')} news={h.get('news')}")
        for v in vals:
            if v is not None:
                lines.append(f"{tag}_n={v}")
                lines.append(f"{round(float(v), 2)}")
                lines.append(f"{round(float(v), 1)}")
                lines.append(f"{round(float(v))}")
    return "\n".join(lines)


def compute_findings(
    brief: QuestionBrief,
    evidence: EvidenceSet,
    news_read: NewsRead | None = None,
) -> Findings:
    settings = get_settings()
    sector_label = _topic_sector_label(brief)
    bench = _benchmark(evidence)
    bench_pct = bench.get("return_pct")
    bench_label = str(bench.get("benchmark_label") or bench.get("sector_label") or "")

    news_insights, news_stats = digest_articles(evidence.articles, limit=5)
    tagged = _news_from_articles(evidence.articles)
    tag_dir = str(tagged.get("direction") or "unknown")

    read_ok = bool(news_read and news_read.mode in ("llm", "heuristic") and news_read.claims)
    if read_ok and news_read.tone in ("positive", "negative", "mixed"):
        news_dir = news_read.tone
    else:
        news_dir = tag_dir
    if news_dir in ("", "unknown"):
        # fall back to an aggregate tone from a signal tool
        for item in evidence.by_facet("news_drivers") + evidence.by_facet("entity_state_over_time"):
            d = str(item.data.get("direction") or "")
            if d in ("positive", "negative", "mixed"):
                news_dir = d
                break
    claims = _claims_for_findings(news_read)
    picks: list[dict[str, Any]] = []
    for item in evidence.by_facet("sector_impact_direction"):
        picks += [p for p in (item.data.get("sector_picks") or []) if isinstance(p, dict)]
    pos_calls, neg_calls = _sector_calls(
        news_read, sector_label if sector_label != "sector" else "", news_dir, picks
    )
    themes = list(news_read.themes) if news_read and news_read.themes else []
    if not themes:
        themes = [str(a.get("title") or "")[:100] for a in evidence.articles[:4] if a.get("title")]

    executive = executive_sector_summary(news_stats, news_insights)
    sector_finding = SectorFinding(
        sector_label=sector_label,
        news_themes=themes,
        news_direction=news_dir,
        index_return_pct=bench_pct if isinstance(bench_pct, (int, float)) else None,
        benchmark_label=bench_label,
        article_count=len(evidence.articles),
        news_summary=news_read.tone_reason if read_ok and news_read.tone_reason else executive,
        news_insights=news_insights,
        news_stats=news_stats,
        executive_summary=executive,
        tone=news_dir,
        tone_reason=news_read.tone_reason if news_read else "",
        claims=claims,
        sectors_positive=pos_calls,
        sectors_negative=neg_calls,
        read_mode=news_read.mode if news_read else "none",
    )

    findings = Findings(goal=brief.goal, sector=sector_finding, limits=[])
    if bench.get("substituted_broad_index"):
        findings.limits.append(
            FindingLimit("benchmark_substitute", "Sector index unavailable; used broad market proxy.")
        )

    fund_rows = _match_fund_rows(evidence) or _named_fund_rows(evidence)
    asked = (brief.direction or "any").strip().lower()
    if asked in ("positive", "negative"):
        fund_rows = [
            r for r in fund_rows
            if str(r.get("affected_direction") or asked).lower() == asked
        ]
    fund_rows.sort(
        key=lambda r: float(r.get("sector_weight_pct") or r.get("exposure_pct") or 0),
        reverse=True,
    )
    cap = int(getattr(settings, "insight_fan_out_cap", 8))
    # A fund is "impacted" when the sector is a real part of it; keep thinner ones only if nothing else.
    meaningful = [
        r for r in fund_rows if float(r.get("sector_weight_pct") or r.get("exposure_pct") or 0) >= 5.0
    ]
    named_only = not _match_fund_rows(evidence)
    filtered_rows = fund_rows if named_only else (meaningful or fund_rows[:cap])

    seen_funds: set[str] = set()
    for row in filtered_rows[: cap * 2]:
        if len(findings.funds) >= cap:
            break
        isin = str(row.get("isin") or "")
        name = str(row.get("fund_name") or row.get("name") or isin)
        fund_key = re.sub(r"\W+", " ", re.sub(r"\bindia\b|\bfund\b|direct|regular|growth|plan", "", name, flags=re.I)).strip().lower()
        if fund_key in seen_funds:
            continue
        seen_funds.add(fund_key)
        exposure = row.get("sector_weight_pct") or row.get("exposure_pct")
        try:
            exposure_f = float(exposure) if exposure is not None else None
        except (TypeError, ValueError):
            exposure_f = None
        breakdown = row.get("sector_breakdown") if isinstance(row.get("sector_breakdown"), dict) else {}
        comp = _item_for_isin(evidence, "fund_composition", isin) or {}
        sectors_list = comp.get("sectors") or []

        other_sectors: list[dict[str, Any]] = []
        topic_share = 0.0
        for s_ in sectors_list:
            if not isinstance(s_, dict):
                continue
            label = str(s_.get("sector") or "")
            pct = float(s_.get("percentage") or 0)
            topic_label = str(row.get("affected_sector") or (sector_label if sector_label != "sector" else ""))
            if topic_label and _name_matches(label, topic_label):
                topic_share += pct
            else:
                other_sectors.append({"sector": label, "percentage": pct})
        other_sectors.sort(key=lambda x: -float(x.get("percentage") or 0))
        other_sectors = other_sectors[:4]

        sector_mix: list[dict[str, Any]] = []
        vs_idx = _item_for_isin(evidence, "fund_vs_index", isin) or {}
        idx_by_sector = {
            re.sub(r"\W+", " ", str(x.get("sector") or "")).strip().lower(): x
            for x in (vs_idx.get("sectors") or [])
            if isinstance(x, dict)
        }
        for s_ in sorted(
            [x for x in sectors_list if isinstance(x, dict)],
            key=lambda x: -float(x.get("percentage") or 0),
        )[:10]:
            lab = str(s_.get("sector") or "")
            hit = idx_by_sector.get(re.sub(r"\W+", " ", lab).strip().lower()) or {}
            sector_mix.append(
                {
                    "sector": lab,
                    "percentage": round(float(s_.get("percentage") or 0), 2),
                    "index_label": hit.get("nse_index_name") or "",
                    "index_return_pct": hit.get("index_return_pct"),
                }
            )
        ret_data = (
            _item_for_isin(evidence, "return_series", isin, prefer_key="window_pct")
            or _item_for_isin(evidence, "fund_facts_nav", isin)
            or {}
        )
        window_pct = ret_data.get("window_pct")
        if window_pct is None:
            for k in ("return_pct", "return_1m_pct", "return_3m_pct", "return_1y_pct"):
                try:
                    if ret_data.get(k) is not None:
                        window_pct = float(ret_data.get(k))
                        break
                    elif row.get(k) is not None:
                        window_pct = float(row.get(k))
                        break
                except (TypeError, ValueError):
                    pass
        monthly = ret_data.get("monthly") if isinstance(ret_data.get("monthly"), list) else []

        rel = None
        if window_pct is not None and bench_pct is not None:
            rel = round(float(window_pct) - float(bench_pct), 2)
        fund_ret_f = float(window_pct) if window_pct is not None else None

        # ---- news -> fund link ----
        pos_exp, neg_exp, mix_exp, pos_rows, neg_rows, mix_rows = _news_link_for_fund(
            sectors_list, pos_calls, neg_calls
        )
        mechanism = _mechanism(pos_rows + mix_rows, neg_rows + mix_rows, pos_calls, neg_calls)
        if sectors_list:
            tilt = _tilt(pos_exp, neg_exp, mix_exp)
        elif row.get("affected_direction"):
            tilt, mechanism = _driver_row_tilt(row)
            pos_exp = float(exposure_f or 0) if tilt == "tailwind" else 0.0
            neg_exp = float(exposure_f or 0) if tilt == "headwind" else 0.0
        else:
            tilt = "unknown"
        touched = pos_exp + neg_exp + mix_exp
        alignment = _alignment(tilt, touched, fund_ret_f)

        trace = _item_for_isin(evidence, "relationship_trace", isin) or {}
        direct = [str(d.get("name")) for d in (trace.get("direct") or []) if isinstance(d, dict) and d.get("name")][:3]

        divergence = alignment == "diverged"
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

        findings.funds.append(
            FundFinding(
                fund_name=name,
                isin=isin,
                exposure_pct=exposure_f if exposure_f is not None else (round(topic_share, 2) or None),
                exposure_sector=str(row.get("affected_sector") or (sector_label if sector_label != "sector" else "")),
                top_holdings=[
                    {"name": h.get("name"), "percentage": round(float(h.get("percentage") or 0), 2)}
                    for h in (comp.get("holdings") or [])[:5]
                    if isinstance(h, dict) and h.get("name")
                ],
                exposure_sectors=breakdown,
                other_top_sectors=other_sectors,
                sector_mix=sector_mix,
                category=str(comp.get("category") or ""),
                as_on=str(comp.get("as_on") or ""),
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
                pos_exposure_pct=pos_exp,
                neg_exposure_pct=neg_exp,
                pos_sectors=pos_rows[:3],
                neg_sectors=neg_rows[:3],
                mixed_exposure_pct=mix_exp,
                mixed_sectors=mix_rows[:3],
                news_tilt=tilt,
                alignment=alignment,
                mechanism=mechanism,
                direct_holdings=direct,
                drag_sectors=_drags_for(evidence, isin),
            )
        )

    findings.evidence_text = _build_evidence_text(findings)
    if sector_finding.news_direction != "unknown":
        findings.cross_cutting.append(f"Sector news tone: {sector_finding.news_direction}")
    return findings
