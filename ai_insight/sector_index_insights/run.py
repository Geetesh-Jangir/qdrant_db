"""Build one insight per healthy sector index, plus a rotation card."""

from __future__ import annotations

import argparse
from datetime import date
from typing import Any

from ai_insight.common.config import load_config
from ai_insight.common.context import editorial_context, news_map_block
from ai_insight.common.display import fmt_pct
from ai_insight.common.retrieval_plan import fetch_section, plan_window
from ai_insight.common.quality import LoopSpec, run_quality_loop
from ai_insight.common.runner import RunContext, run_bundle_insight
from ai_insight.common.schemas import Chip, Envelope, InsightBundle, Meta, Source, Viz
from ai_insight.common.sector_indices import IndexSeries, fetch_ohlc, load_catalog, news_sectors_for_index
from ai_insight.common.store import save_bundle
from ai_insight.common.time_ist import ist_now
from ai_insight.sector_index_insights.prompt import REVISE, ROTATION, SYSTEM, VERIFY, build_user
from ai_insight.sector_index_insights.schema import DRAFT_SCHEMA, INSIGHT_ID, PROMPT_VERSION


def build(ctx: RunContext, *, history=None, only: str = "") -> InsightBundle:
    specs = load_catalog(include_weak=ctx.config.include_weak_index)
    if only:
        specs = [spec for spec in specs if spec.key == only or only in spec.news_sectors]
    items: list[Envelope] = []
    serieses: list[IndexSeries] = []
    skipped: list[str] = []
    for spec in specs:
        series = fetch_ohlc(spec, ctx.trading_date, history=history)
        if series is None:
            skipped.append(spec.display)
            ctx.log.line("INDEX", f"skip {spec.display} (no usable Yahoo history)")
            if ctx.artifacts is not None:
                ctx.artifacts.warning(f"skipped index {spec.display}", step="yahoo")
            continue
        ctx.log.line("INDEX", f"ok {spec.display} ticker={series.ticker} week={series.week_change_pct}%")
        serieses.append(series)
        item = _one(ctx, series)
        items.append(item)
        _save(ctx, items, "ok" if any(card.status == "ok" for card in items) else item.status, skipped)
    if len(serieses) >= 2:
        items.append(_rotation(ctx, serieses))
        _save(ctx, items, "ok" if any(card.status == "ok" for card in items) else "degraded", skipped)
    status = "ok" if any(card.status == "ok" for card in items) else ("skipped" if not items else "degraded")
    return _save(ctx, items, status, skipped)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_insight.sector_index_insights.run")
    parser.add_argument("--date", default="")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--only", default="")
    parser.add_argument("--backtest", type=int, default=0)
    args = parser.parse_args(argv)
    cfg = load_config()
    day = date.fromisoformat(args.date) if args.date else ist_now().date()
    if args.backtest:
        return _backtest(args.backtest, day, cfg)

    def _build(ctx: RunContext) -> InsightBundle:
        ctx.window, _ = plan_window(ctx, "sector_index_insights")
        return build(ctx, only=args.only)

    outcome = run_bundle_insight(
        INSIGHT_ID,
        _build,
        day,
        force=args.force or args.live,
        dry_run=args.dry_run,
        verbose=args.verbose,
        live=args.live,
    )
    print(
        f"{outcome.status} exit={outcome.exit_code} duration={outcome.duration_sec:.1f}s "
        f"tokens={outcome.tokens} sources={outcome.source_count}"
    )
    return outcome.exit_code


def _one(ctx: RunContext, series: IndexSeries) -> Envelope:
    news_sectors = news_sectors_for_index(series.spec)
    facts = {
        "trading_date": ctx.trading_date.isoformat(),
        "index": series.spec.display,
        "news_sector": news_sectors[0] if len(news_sectors) == 1 else news_sectors,
        "fit": series.spec.fit,
        "sectors": news_sectors,
        "catalog_sectors": series.spec.news_sectors,
        "ticker": series.ticker,
        "week_change_pct": series.week_change_pct,
        "today_change_pct": series.today_change_pct,
        "stats": series.stats,
        "bars": [bar.as_dict() for bar in series.bars],
        "scope_note": series.spec.scope_note,
        "editorial": editorial_context(ctx),
    }
    ctx.scope(f"sector:{series.spec.display}")
    pack = fetch_section(ctx, "sector_index_insights", sector_names=news_sectors, client=getattr(ctx, "qdrant", None))
    clusters = pack.clusters[:8]
    evidence = pack.evidence
    facts["article_count"] = len(evidence)
    facts["narrative_mode"] = "price_only" if not evidence else "news_backed"
    facts["news_map"] = news_map_block(clusters)
    if ctx.artifacts is not None:
        ctx.artifacts.write_json(f"evidence_{series.spec.key}.json", [item.as_dict() for item in evidence])

    def compose(data: dict[str, Any]) -> Envelope:
        body = str(data.get("body") or "")
        change = series.week_change_pct or 0
        if not body.strip():
            body = (
                f"{series.spec.display} moved {fmt_pct(change)} over the week "
                f"and {fmt_pct(series.today_change_pct or 0)} today."
            )
        return Envelope(
            insight_id=INSIGHT_ID,
            trading_date=ctx.trading_date.isoformat(),
            as_of_ist=ist_now().isoformat(),
            status="ok",
            prominence="high" if abs(change) >= 2 else "normal",
            headline=str(data.get("headline") or f"{series.spec.display} this week"),
            body=body,
            chips=[
                Chip(label="Week", value=fmt_pct(change), tone=_tone(change)),
                Chip(label="Today", value=fmt_pct(series.today_change_pct or 0), tone=_tone(series.today_change_pct or 0)),
            ],
            viz=Viz(type="ohlc_week", data={"ticker": series.ticker, "rows": [bar.as_dict() for bar in series.bars], "week_change_pct": change}),
            sources=_sources(clusters, data.get("driver_cluster_ids") or []),
            facts={**facts, "kind": "sector_index"},
            meta=Meta(prompt_version=PROMPT_VERSION, cluster_ids=list(data.get("driver_cluster_ids") or [])),
        )

    if not ctx.llm or ctx.dry_run:
        return compose({"headline": f"{series.spec.display} this week", "body": "Dry run.", "reason_unclear": True, "explanation_confidence": "low", "driver_cluster_ids": [], "direction": "up" if (series.week_change_pct or 0) >= 0 else "down", "implication": None})
    before = len(getattr(ctx, "llm_summaries", []) or [])
    result = run_quality_loop(ctx, spec=LoopSpec(SYSTEM, VERIFY, REVISE, build_user(facts, evidence), DRAFT_SCHEMA, compose), facts=facts, evidence=evidence)
    env = result.envelope
    calls = list(getattr(ctx, "llm_summaries", []) or [])
    slice_calls = calls[before:]
    env.meta.run_id = getattr(ctx.artifacts, "run_id", "") if ctx.artifacts is not None else ""
    env.meta.run_mode = "live" if ctx.live else "scheduled"
    env.meta.llm_calls = slice_calls
    env.meta.usage.input_tokens = sum(int(c.get("input_tokens") or 0) for c in slice_calls)
    env.meta.usage.output_tokens = sum(int(c.get("output_tokens") or 0) for c in slice_calls)
    return env


def _rotation(ctx: RunContext, serieses: list[IndexSeries]) -> Envelope:
    ordered = sorted(serieses, key=lambda item: abs(item.week_change_pct or 0), reverse=True)
    facts = {"rows": [{"index": item.spec.display, "week_change_pct": item.week_change_pct, "sectors": item.spec.news_sectors} for item in ordered]}
    if ctx.dry_run or not ctx.llm:
        text = _rotation_fallback(ordered)
        return _rotation_envelope(ctx, text, text, facts)
    def compose(data: dict[str, Any]) -> Envelope:
        body = str(data.get("body") or "")
        return _rotation_envelope(ctx, str(data.get("headline") or "Sector rotation this week"), body, facts)
    result = run_quality_loop(ctx, spec=LoopSpec(ROTATION, VERIFY, REVISE, build_user(facts, []), DRAFT_SCHEMA, compose), facts=facts, evidence=[])
    return result.envelope


def _rotation_envelope(ctx, headline, body, facts) -> Envelope:
    return Envelope(
        insight_id=INSIGHT_ID,
        trading_date=ctx.trading_date.isoformat(),
        as_of_ist=ist_now().isoformat(),
        status="ok",
        headline=headline,
        body=body,
        facts={**facts, "kind": "sector_rotation"},
        viz=Viz(type="trend_line", data={"rows": facts.get("rows") or []}),
        meta=Meta(prompt_version=PROMPT_VERSION),
    )


def _rotation_fallback(serieses: list[IndexSeries]) -> str:
    if not serieses:
        return "Sector moves were mixed."
    lead = max(serieses, key=lambda item: item.week_change_pct or 0)
    lag = min(serieses, key=lambda item: item.week_change_pct or 0)
    return f"{lead.spec.display} led and {lag.spec.display} lagged this week."


def _save(ctx: RunContext, items: list[Envelope], status: str, skipped: list[str]) -> InsightBundle:
    bundle = InsightBundle(
        insight_id=INSIGHT_ID,
        trading_date=ctx.trading_date.isoformat(),
        as_of_ist=ist_now().isoformat(),
        status=status,  # type: ignore[arg-type]
        items=items,
        meta={"skipped_sectors": skipped, "run_mode": "live" if ctx.live else "scheduled"},
    )
    if not ctx.dry_run:
        save_bundle(bundle, root=ctx.config.data_dir, live=ctx.live)
    return bundle


def _sources(clusters, cited) -> list[Source]:
    wanted = set(cited)
    found = []
    for cluster in clusters:
        if wanted and cluster.cluster_id not in wanted:
            continue
        article = (cluster.articles[0].get("article") if cluster.articles else {}) or {}
        if article.get("url"):
            found.append(Source(title=article.get("title") or "", url=article.get("url") or "", source=article.get("source") or "", published_at=article.get("published_at") or ""))
        if len(found) >= 3:
            break
    return found


def _tone(value: float) -> str:
    return "positive" if value > 0 else "negative" if value < 0 else "neutral"


def _backtest(n: int, end: date, config) -> int:
    path = config.data_dir / "_reports" / "sector_index_insights_backtest.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Sector index backtest\n\nDays requested: {n}\nEnd: {end.isoformat()}\n\nRun with a live model to fill each day.\n", encoding="utf-8")
    print(f"backtest report {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
