"""Four-beat common insight narratives: assemble, compact facts, hints."""

from __future__ import annotations

import json
from typing import Any

from ai_insight.common.config import load_config
from ai_insight.common.evidence import EvidenceArticle, format_evidence_block
from ai_insight.common.prose_guard import scrub_refusal_prose

NARRATIVE_BEATS = ("what_happened", "why", "impacted", "investor_meaning")

FLOW_KEYS = (
    "fii_net_crore",
    "dii_net_crore",
    "fii_gross_buy_crore",
    "fii_gross_sell_crore",
    "dii_gross_buy_crore",
    "dii_gross_sell_crore",
    "fii_direction",
    "dii_direction",
    "fii_streak_days",
    "dii_offsets_fii",
    "flow_trade_date",
    "flow_lagged",
    "fii_5d",
    "dii_5d",
    "fii_net_5d",
    "dii_net_5d",
    "ratio",
)

MARKET_KEYS = (
    "trading_date",
    "nifty_close",
    "nifty_change_pct",
    "nifty_prev_close",
    "phrase",
    "vix_change_pct",
    "vix_close",
    "usdinr",
    "crude_change_pct",
    "banknifty_change_pct",
    "article_count",
    "news_note",
    "flow_note",
)

DRAFT_BEAT_PROPERTIES: dict[str, Any] = {
    beat: {"type": "string"} for beat in NARRATIVE_BEATS
}


def narrative_limits() -> tuple[int, int]:
    cfg = load_config()
    return cfg.body_max_words, cfg.body_max_sentences


def narrative_limits_text() -> str:
    words, sentences = narrative_limits()
    return f"Total body across all beats: ≤ {words} words and ≤ {sentences} sentences (each beat 1–2 short sentences). No filler; chips hold exact numbers."


def assemble_body(beats: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in NARRATIVE_BEATS:
        text = scrub_refusal_prose(str(beats.get(key) or "").strip())
        if text:
            parts.append(text)
    if not parts:
        legacy = str(beats.get("body") or "").strip()
        return scrub_refusal_prose(legacy)
    return "\n\n".join(parts)


def beats_from_draft(data: dict[str, Any]) -> dict[str, str]:
    return {beat: str(data.get(beat) or "").strip() for beat in NARRATIVE_BEATS}


def persist_narrative_beats(facts: dict[str, Any], data: dict[str, Any]) -> None:
    facts["narrative_beats"] = beats_from_draft(data)


def build_user_prompt(insight_id: str, facts: dict[str, Any], evidence: list[EvidenceArticle]) -> str:
    compact = compact_facts(insight_id, facts)
    articles = format_evidence_block(evidence) or "(none)"
    return (
        f"INSIGHT: {insight_id}\n"
        f"FACTS\n{json.dumps(compact, ensure_ascii=False, default=str)}\n\n"
        f"ARTICLES\n{articles}"
    )


def compact_facts(insight_id: str, facts: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"insight_id": insight_id}
    if insight_id == "market_driver_digest":
        for key in MARKET_KEYS:
            if key in facts and facts[key] is not None:
                out[key] = facts[key]
        if facts.get("week_pulse"):
            out["week_pulse"] = facts["week_pulse"]
        aligned = facts.get("aligned_market_flows") or []
        if aligned:
            out["aligned_market_flows"] = aligned[-5:]
        totals = facts.get("flow_totals")
        if totals:
            out["flow_totals"] = {k: totals[k] for k in ("net_5d_fii", "net_5d_dii", "week_fii_net", "week_dii_net") if k in totals}
        out["DATE_CONTEXT"] = {
            "trading_date": facts.get("trading_date"),
            "news_note": facts.get("news_note"),
            "flow_note": facts.get("flow_note"),
        }
        if facts.get("fund_data"):
            out["FUND_DATA"] = facts["fund_data"]
        else:
            out["FUND_DATA"] = None
            out["FUND_DATA_note"] = (
                "No fund-level holdings in this prompt. Discuss mutual fund categories by mechanism only; "
                "do not name specific schemes or claim portfolio exposure without FUND_DATA."
            )
    elif insight_id == "fii_dii_flow_narrative":
        for key in FLOW_KEYS:
            if key in facts and facts[key] is not None:
                out[key] = facts[key]
        for key in ("trading_date", "article_count", "news_note", "flow_note", "prominence"):
            if key in facts:
                out[key] = facts[key]
        out["DATE_CONTEXT"] = {
            "trading_date": facts.get("trading_date"),
            "flow_trade_date": facts.get("flow_trade_date"),
            "flow_lagged": facts.get("flow_lagged"),
            "news_note": facts.get("news_note"),
            "flow_note": facts.get("flow_note"),
        }
        if facts.get("fund_data"):
            out["FUND_DATA"] = facts["fund_data"]
        else:
            out["FUND_DATA"] = None
            out["FUND_DATA_note"] = (
                "No fund-level holdings in this card. Discuss mutual fund categories by mechanism only."
            )
        if facts.get("week_pulse"):
            out["week_pulse"] = facts["week_pulse"]
        if facts.get("sector_tilt_hint"):
            out["sector_tilt_hint"] = facts["sector_tilt_hint"]
        if facts.get("nifty_change_pct") is not None:
            out["nifty_change_pct"] = facts["nifty_change_pct"]
        if facts.get("banknifty_change_pct") is not None:
            out["banknifty_change_pct"] = facts["banknifty_change_pct"]
        aligned = facts.get("aligned_market_flows") or []
        if aligned:
            out["aligned_market_flows"] = aligned[-5:]
        nm = facts.get("news_map")
        if nm:
            out["news_map"] = _compact_news_map(nm)
    elif insight_id == "sector_leaderboard":
        out["trading_date"] = facts.get("trading_date")
        out["week_movers"] = facts.get("week_movers")
        out["best_theme"] = facts.get("best_theme")
        out["worst_theme"] = facts.get("worst_theme")
        out["article_count"] = facts.get("article_count")
        best = facts.get("best_sector_snapshot")
        worst = facts.get("worst_sector_snapshot")
        if best:
            out["best_sector"] = best
        if worst:
            out["worst_sector"] = worst
    else:
        for key in list(facts.keys())[:40]:
            if not key.startswith("_"):
                out[key] = facts[key]
    return out


def _compact_news_map(news_map: list[dict[str, Any]]) -> list[dict[str, Any]]:
    slim: list[dict[str, Any]] = []
    for row in news_map[:12]:
        entities = row.get("entities") or []
        top_entities = sorted(entities, key=lambda e: -(e.get("count") or 0))[:6]
        slim.append(
            {
                "cluster_id": row.get("cluster_id"),
                "label": row.get("label"),
                "weight": row.get("weight"),
                "entities": top_entities,
            }
        )
    return slim


def sector_tilt_hint(news_map: list[dict[str, Any]], week_meta: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Top entities from news clusters — not NSE sector FII allocation."""
    counts: dict[str, dict[str, Any]] = {}

    def bump(name: str, direction: str | None, n: int = 1) -> None:
        if not name or name.startswith("Macro - Nifty"):
            return
        bucket = counts.setdefault(name, {"name": name, "count": 0, "directions": {}})
        bucket["count"] += n
        if direction:
            d = str(direction).lower()
            bucket["directions"][d] = bucket["directions"].get(d, 0) + n

    for row in news_map or []:
        for ent in row.get("entities") or []:
            bump(str(ent.get("name") or ""), ent.get("direction"), int(ent.get("count") or 1))

    wm = week_meta or {}
    for side in ("best_index", "worst_index"):
        block = wm.get(side)
        if not block:
            continue
        for sec in block.get("sectors") or []:
            bump(str(sec), "positive" if side == "best_index" else "negative", 2)

    ranked = sorted(counts.values(), key=lambda item: -item["count"])
    return ranked[:8]


def enrich_flow_gross(facts: dict[str, Any], history: list[Any]) -> None:
    """Attach gross buy/sell for the flow day already referenced in facts."""
    flow_date = facts.get("flow_trade_date") or facts.get("trading_date")
    today = next((d for d in history if d.date == flow_date), None)
    if not today:
        return
    fii = today.fii or {}
    dii = today.dii or {}
    facts["fii_gross_buy_crore"] = _num(fii.get("buy_inr_crore") or fii.get("buy"))
    facts["fii_gross_sell_crore"] = _num(fii.get("sell_inr_crore") or fii.get("sell"))
    facts["dii_gross_buy_crore"] = _num(dii.get("buy_inr_crore") or dii.get("buy"))
    facts["dii_gross_sell_crore"] = _num(dii.get("sell_inr_crore") or dii.get("sell"))


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def repetition_score(beats: dict[str, str]) -> float:
    """Jaccard-like overlap between consecutive beats (0–1)."""
    ordered = [str(beats.get(b) or "").lower() for b in NARRATIVE_BEATS if str(beats.get(b) or "").strip()]
    if len(ordered) < 2:
        ordered = [str(v).lower() for v in beats.values() if str(v).strip()]
    texts = ordered
    if len(texts) < 2:
        return 0.0
    scores: list[float] = []
    for left, right in zip(texts, texts[1:]):
        wl = set(left.split())
        wr = set(right.split())
        if not wl or not wr:
            continue
        scores.append(len(wl & wr) / len(wl | wr))
    return max(scores) if scores else 0.0