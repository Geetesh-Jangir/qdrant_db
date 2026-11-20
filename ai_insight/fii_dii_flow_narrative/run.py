"""Build the FII/DII card."""

from __future__ import annotations

from typing import Any

from ai_insight.common.context import market_numbers, news_map_block
from ai_insight.common.entity_retrieval import sector_names_for_pulse
from ai_insight.common.narrative import sector_tilt_hint
from ai_insight.common.display import fmt_inr_crore
from ai_insight.common.flows import cumulative, history_path, load_flow_history
from ai_insight.common.market_data import get_fii_dii_today
from ai_insight.common.retrieval_plan import fetch_section
from ai_insight.common.quality import LoopSpec, run_quality_loop
from ai_insight.common.runner import RunContext, cli_main
from ai_insight.common.schemas import Chip, Envelope, Meta, Source, Viz
from ai_insight.common.time_ist import ist_now
from ai_insight.fii_dii_flow_narrative.aggregate import compute_flow_facts, fallback_headline, flow_period_totals
from ai_insight.fii_dii_flow_narrative.flow_datasets import build_flow_datasets
from ai_insight.fii_dii_flow_narrative.collector import _record, history_has_date, store_record_if_new
from ai_insight.fii_dii_flow_narrative.prompt import (
    PROMPT_VERSION,
    REVISE,
    SYSTEM,
    VERIFY,
    assemble_fii_body,
    build_user,
    normalize_fii_draft,
    persist_fii_sections,
)
from ai_insight.fii_dii_flow_narrative.schema import DRAFT_SCHEMA, INSIGHT_ID, NO_DRIVER


def build(ctx: RunContext) -> Envelope:
    store = history_path(ctx.config.data_dir)
    trading_date = ctx.trading_date.isoformat()
    snapshot = get_fii_dii_today(trading_date, config=ctx.config)
    if snapshot.status in {"ok", "stale"} and snapshot.data:
        record = _record(snapshot.data, snapshot.source)
        if history_has_date(store, trading_date):
            ctx.log.line("FLOW", f"history already has {trading_date}; NSE not re-appended")
        elif store_record_if_new(store, record):
            ctx.log.line("FLOW", f"appended flow for {record['date']} (NSE status={snapshot.status})")
        elif snapshot.status == "stale":
            ctx.log.line("FLOW", f"NSE status=stale {snapshot.detail}; flow for {record.get('date')} already on file")
    elif snapshot.status != "ok":
        ctx.log.line("FLOW", f"NSE status={snapshot.status} {snapshot.detail}")
    history = load_flow_history(store)
    if snapshot.status in {"ok", "stale"} and snapshot.data:
        history = _with_today(history, snapshot.data)
    if not history:
        return _shell(ctx, "skipped", {}, skip_reason="fii_dii_not_published")
    facts = compute_flow_facts(
        history,
        trading_date,
        streak_high=ctx.config.streak_high_days,
        ratio_high=ctx.config.ratio_high,
        min_history=ctx.config.ratio_min_history,
    )
    if facts.get("fii_net_crore") is None and facts.get("dii_net_crore") is None:
        return _shell(ctx, "skipped", facts, skip_reason="fii_dii_not_published")
    if facts.get("flow_lagged"):
        ctx.log.line("FLOW", f"card uses flow_trade_date={facts.get('flow_trade_date')} (no NSE row for {trading_date})")
    facts["fii_5d"] = cumulative(history, 5)
    facts["dii_5d"] = cumulative(history, 5, "dii_net")
    facts.update(market_numbers(ctx))
    _best, _worst, week_meta = sector_names_for_pulse(ctx)
    facts["week_pulse"] = week_meta
    flow_history = [day for day in history if day.date and day.date <= trading_date]
    facts["flow_totals"] = flow_period_totals(flow_history, trading_date)
    facts["datasets"] = build_flow_datasets(ctx, flow_history, facts)
    pack = fetch_section(ctx, "fii_dii_flow_narrative", client=getattr(ctx, "qdrant", None))
    ctx.window = pack.window
    clusters = pack.clusters[:8]
    evidence = pack.evidence
    facts["article_count"] = len(evidence)
    facts["news_map"] = news_map_block(clusters)
    facts["sector_tilt_hint"] = sector_tilt_hint(facts["news_map"], week_meta)
    bank = facts.get("banknifty_history") or {}
    for row in reversed(bank.get("daily") or []):
        if row.get("date") == trading_date and row.get("change_pct") is not None:
            facts["banknifty_change_pct"] = row.get("change_pct")
            break
    facts["nifty_change_pct"] = facts.get("nifty_change_pct") or facts.get("change_pct")
    ctx.emit_facts(facts)
    if ctx.artifacts is not None:
        ctx.artifacts.write_json("retrieval.json", pack.diagnostics)
        ctx.artifacts.write_json("clusters.json", [_cluster_row(item) for item in clusters])
        ctx.artifacts.write_json("scores.json", facts)
    ctx.decision = f"Week window scanned; {len(clusters)} clusters for flows."
    if ctx.artifacts is not None:
        ctx.artifacts.decision(ctx.decision)

    ctx.draft_normalize = normalize_fii_draft

    def compose(data: dict[str, Any]) -> Envelope:
        data = normalize_fii_draft(data)
        headline = str(data.get("headline") or "") or fallback_headline(facts)
        body = assemble_fii_body(data)
        status = "ok" if body.strip() else "degraded"
        if not body.strip():
            body = NO_DRIVER
        persist_fii_sections(facts, data)
        facts["observations"] = list(data.get("observations") or [])
        return _shell(
            ctx,
            status,
            facts,
            headline=headline,
            body=body,
            cluster_ids=[str(item) for item in (data.get("chosen_cluster_ids") or [])],
            clusters=clusters,
        )

    spec = LoopSpec(SYSTEM, VERIFY, REVISE, build_user(facts, evidence), DRAFT_SCHEMA, compose, max_tokens=1600)
    result = run_quality_loop(ctx, spec=spec, facts=facts, evidence=evidence)
    return result.envelope


def main(argv: list[str] | None = None) -> int:
    return cli_main(INSIGHT_ID, build, argv)


def _with_today(history, data: dict) -> list:
    from ai_insight.common.flows import FlowDay

    day = str(data.get("trade_date") or "")
    if not day or any(item.date == day for item in history):
        return history
    fii = data.get("fii") or {}
    dii = data.get("dii") or {}
    return sorted(
        [
            *history,
            FlowDay(day, float(fii.get("net_inr_crore") or 0), float(dii.get("net_inr_crore") or 0), fii, dii, str(data.get("source") or "")),
        ],
        key=lambda item: item.date,
    )


def _shell(ctx, status, facts, *, skip_reason=None, headline="", body="", cluster_ids=None, clusters=None) -> Envelope:
    chips: list[Chip] = []
    if facts.get("fii_net_crore") is not None:
        chips.append(Chip(label="FII net", value=fmt_inr_crore(facts["fii_net_crore"]), tone=_tone(facts["fii_net_crore"])))
    if facts.get("dii_net_crore") is not None:
        chips.append(Chip(label="DII net", value=fmt_inr_crore(facts["dii_net_crore"]), tone=_tone(facts["dii_net_crore"])))
    if facts.get("fii_streak_days"):
        chips.append(Chip(label="FII streak", value=f"{facts['fii_streak_days']} days", tone="neutral"))
    if facts.get("ratio") is not None:
        chips.append(Chip(label="vs 20-day avg", value=f"{facts['ratio']}x", tone="neutral"))
    sources = _sources(clusters or [], cluster_ids or [])
    return Envelope(
        insight_id=INSIGHT_ID,
        trading_date=ctx.trading_date.isoformat(),
        as_of_ist=ist_now().isoformat(),
        status=status,
        skip_reason=skip_reason,
        prominence=facts.get("prominence") or "normal",
        headline=headline,
        body=body,
        chips=chips,
        viz=Viz(type="flow_bars", data={"days": facts.get("bars") or []}),
        sources=sources,
        facts=facts,
        meta=Meta(prompt_version=PROMPT_VERSION, cluster_ids=list(cluster_ids or [])),
    )


def _sources(clusters, cited: list[str]) -> list[Source]:
    found: list[Source] = []
    wanted = set(cited)
    for cluster in clusters:
        if wanted and cluster.cluster_id not in wanted:
            continue
        for row in cluster.articles[:2]:
            article = row.get("article") or {}
            if not article.get("url"):
                continue
            found.append(Source(title=article.get("title") or "", url=article.get("url") or "", source=article.get("source") or "", published_at=article.get("published_at") or ""))
            if len(found) >= 2:
                return found
    return found[:2]


def _cluster_row(cluster) -> dict:
    return {"cluster_id": cluster.cluster_id, "title": cluster.representative_title, "urls": cluster.member_urls, "weight": cluster.weight, "direction_mix": cluster.direction_mix}


def _tone(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


if __name__ == "__main__":
    raise SystemExit(main())
