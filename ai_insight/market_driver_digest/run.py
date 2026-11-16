"""Build the market driver digest."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Any

from ai_insight.common.config import CommonConfig, load_config
from ai_insight.common.context import market_numbers, news_map_block
from ai_insight.common.display import fmt_inr_crore, fmt_pct
from ai_insight.common.flows import history_path, load_flow_history
from ai_insight.common.market_data import get_fii_dii_today, get_nifty, get_series
from ai_insight.common.retrieval_plan import fetch_section
from ai_insight.common.quality import LoopSpec, run_quality_loop
from ai_insight.common.runner import RunContext, cli_main
from ai_insight.common.run_log import RunLog
from ai_insight.common.schemas import Chip, Envelope, Meta, Source, Viz
from ai_insight.common.time_ist import ist_now, session_window
from ai_insight.common.trading_calendar import is_trading_day, prev_trading_day
from ai_insight.data.yfinance_source import YF_SERIES
from ai_insight.market_driver_digest.prompt import PROMPT_VERSION, REVISE, SYSTEM, VERIFY, build_user
from ai_insight.market_driver_digest.rank import move_phrase, pick_drivers
from ai_insight.market_driver_digest.schema import DRAFT_SCHEMA, INSIGHT_ID


def build(ctx: RunContext) -> Envelope:
    nifty = get_nifty(ctx.trading_date.isoformat(), config=ctx.config)
    if nifty.status != "ok" or not nifty.data:
        return _shell(ctx, "skipped", {"nifty_status": nifty.status}, skip_reason="nifty_stale" if nifty.status == "stale" else "nifty_unavailable")
    facts = _facts(ctx, nifty.data)
    facts.update(market_numbers(ctx))
    pack = fetch_section(ctx, "market_driver_digest", client=getattr(ctx, "qdrant", None))
    ctx.window = pack.window
    facts["article_count"] = len(pack.evidence)
    facts["news_map"] = news_map_block(pack.clusters)
    ctx.emit_facts(facts)
    if ctx.artifacts is not None:
        ctx.artifacts.write_json("retrieval.json", pack.diagnostics)
    shown = pack.clusters[:6]
    drivers = pick_drivers(shown)
    if ctx.artifacts is not None:
        ctx.artifacts.write_json("clusters.json", [{"id": item.cluster_id, "title": item.representative_title, "urls": item.member_urls} for item in shown])
        ctx.artifacts.write_json("scores.json", {"phrase": facts["phrase"], "used_recap_only": drivers.used_recap_only})
    evidence = pack.evidence
    if not shown:
        return _fallback(ctx, facts, "degraded")

    def compose(data: dict[str, Any]) -> Envelope:
        headline = str(data.get("headline") or "") or _fallback_headline(facts)
        body = str(data.get("body") or "")
        weak = data.get("confidence") == "low" or drivers.used_recap_only
        status = "degraded" if weak and not body.strip() else "ok"
        if not body.strip():
            body = (
                f"Nifty {facts.get('phrase') or 'moved'} "
                f"{fmt_pct(facts.get('nifty_change_pct') or 0)} to {facts.get('nifty_close')}."
            )
        facts["observations"] = list(data.get("observations") or [])
        return _shell(ctx, status, facts, headline=headline, body=body, cluster_ids=list(data.get("cited_cluster_ids") or []), clusters=shown)

    outcome = run_quality_loop(ctx, spec=LoopSpec(SYSTEM, VERIFY, REVISE, build_user(facts, evidence), DRAFT_SCHEMA, compose), facts=facts, evidence=evidence)
    return outcome.envelope


def backtest(n: int, *, end: date | None = None, config: CommonConfig | None = None, client: Any = None) -> Path:
    cfg = config or load_config()
    end_day = end or prev_trading_day(ist_now().date(), holidays_path=cfg.holidays_path)
    days = _days(n, end_day, cfg.holidays_path)
    sections = ["# Market driver digest backtest", ""]
    for day in days:
        ctx = _context(day, cfg, client)
        try:
            envelope = build(ctx)
        except Exception as exc:
            sections.append(f"## {day.isoformat()}\n\nError: {type(exc).__name__}: {exc}\n")
            continue
        sections.append(_section(envelope))
    path = cfg.data_dir / "_reports" / "market_driver_digest_backtest.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(sections), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_insight.market_driver_digest.run")
    parser.add_argument("--backtest", type=int, default=0)
    parser.add_argument("--date", default="")
    known, _rest = parser.parse_known_args(argv)
    if known.backtest:
        path = backtest(known.backtest, end=date.fromisoformat(known.date) if known.date else None)
        print(f"backtest report {path}")
        return 0
    return cli_main(INSIGHT_ID, build, argv)


def _facts(ctx: RunContext, nifty: dict) -> dict:
    change = nifty.get("change_pct")
    facts: dict[str, Any] = {
        "trading_date": ctx.trading_date.isoformat(),
        "nifty_close": nifty.get("close"),
        "nifty_change_pct": change,
        "nifty_prev_close": nifty.get("prev_close"),
        "phrase": move_phrase(change),
        "move_size": move_phrase(change),
    }
    vix = get_series("Macro - India VIX", ctx.trading_date.isoformat())
    if vix.status == "ok" and vix.data:
        facts["vix_change_pct"] = vix.data.get("change_pct")
        facts["vix_close"] = vix.data.get("close")
    usd = get_series("Macro - Rupee / USD", ctx.trading_date.isoformat())
    if usd.status == "ok" and usd.data and usd.data.get("date") == ctx.trading_date.isoformat():
        facts["usdinr"] = usd.data.get("close")
    flow = get_fii_dii_today(ctx.trading_date.isoformat(), config=ctx.config)
    if flow.status == "ok" and flow.data and flow.data.get("fii"):
        facts["fii_net_crore"] = flow.data["fii"].get("net_inr_crore")
    history = load_flow_history(history_path(ctx.config.data_dir))
    facts["flow_history_days"] = len(history)
    facts["range_5d"] = []
    return facts


def _fallback(ctx, facts, status) -> Envelope:
    return _shell(ctx, status, facts, headline=_fallback_headline(facts), body="News flow doesn't point to one clear driver today.")


def _fallback_headline(facts: dict) -> str:
    change = facts.get("nifty_change_pct")
    if change is None:
        return "Nifty 50 moved today"
    verb = "rises" if change > 0 else "slips" if change < 0 else "is flat"
    return f"Nifty 50 {verb} {fmt_pct(change)} today"


def _shell(ctx, status, facts, *, skip_reason=None, headline="", body="", cluster_ids=None, clusters=None) -> Envelope:
    chips: list[Chip] = []
    if facts.get("nifty_close") is not None:
        chips.append(Chip(label="Nifty 50", value=f"{facts['nifty_close']} ({fmt_pct(facts.get('nifty_change_pct') or 0)})", tone=_tone(facts.get("nifty_change_pct"))))
    if facts.get("vix_change_pct") is not None:
        chips.append(Chip(label="India VIX", value=fmt_pct(facts["vix_change_pct"]), tone=_tone(facts["vix_change_pct"])))
    if facts.get("fii_net_crore") is not None:
        chips.append(Chip(label="FII net", value=fmt_inr_crore(facts["fii_net_crore"]), tone=_tone(facts["fii_net_crore"])))
    if facts.get("usdinr") is not None:
        chips.append(Chip(label="USD/INR", value=str(facts["usdinr"]), tone="neutral"))
    return Envelope(
        insight_id=INSIGHT_ID,
        trading_date=ctx.trading_date.isoformat(),
        as_of_ist=ist_now().isoformat(),
        status=status,
        skip_reason=skip_reason,
        headline=headline,
        body=body,
        chips=chips,
        viz=Viz(type="index_move", data={"nifty": {"close": facts.get("nifty_close"), "change_pct": facts.get("nifty_change_pct"), "prev_close": facts.get("nifty_prev_close")}, "range_5d": facts.get("range_5d") or []}),
        sources=_sources(clusters or [], cluster_ids or []),
        facts=facts,
        meta=Meta(prompt_version=PROMPT_VERSION, cluster_ids=list(cluster_ids or [])),
    )


def _sources(clusters, cited) -> list[Source]:
    wanted = set(cited)
    found: list[Source] = []
    for cluster in clusters:
        if wanted and cluster.cluster_id not in wanted:
            continue
        article = (cluster.articles[0].get("article") if cluster.articles else {}) or {}
        if article.get("url"):
            found.append(Source(title=article.get("title") or "", url=article.get("url") or "", source=article.get("source") or "", published_at=article.get("published_at") or ""))
        if len(found) >= 3:
            break
    return found


def _tone(value) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "neutral"
    return "positive" if value > 0 else "negative" if value < 0 else "neutral"


def _days(n: int, end: date, holidays: Path) -> list[date]:
    cursor = end if is_trading_day(end, holidays_path=holidays) else prev_trading_day(end, holidays_path=holidays)
    days = []
    while len(days) < n:
        days.append(cursor)
        cursor = prev_trading_day(cursor, holidays_path=holidays)
    days.reverse()
    return days


def _context(day: date, config: CommonConfig, client: Any) -> RunContext:
    import uuid

    ctx = RunContext(INSIGHT_ID, day, session_window(day, config=config), False, config, RunLog(insight_id=INSIGHT_ID, trading_date=day.isoformat(), run_id=uuid.uuid4().hex[:6], log_dir=config.log_dir), lambda *a, **k: None)
    ctx.qdrant = client
    return ctx


def _section(envelope: Envelope) -> str:
    return f"## {envelope.trading_date}\n\nStatus: {envelope.status}\nHeadline: {envelope.headline}\nBody: {envelope.body}\nNifty: {envelope.facts.get('nifty_change_pct')}\n"


_ = YF_SERIES


if __name__ == "__main__":
    raise SystemExit(main())
