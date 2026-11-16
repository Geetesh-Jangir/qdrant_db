"""Turn signals into reviewable insight cards."""

from __future__ import annotations

import argparse
from datetime import date
from typing import Any

from ai_insight.common.context import market_numbers, news_map_block
from ai_insight.common.prose_guard import READER_VOICE
from ai_insight.common.quality import LoopSpec, run_quality_loop
from ai_insight.common.retrieval_plan import fetch_section
from ai_insight.common.runner import RunContext, run_bundle_insight
from ai_insight.common.schemas import Envelope, InsightBundle, Meta, Viz
from ai_insight.common.store import save_bundle
from ai_insight.common.time_ist import ist_now
from ai_insight.additional_insights.signals import Signal, detect_signals

INSIGHT_ID = "additional_insights"
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["signal_ids", "headline", "body", "confidence"],
                "properties": {
                    "signal_ids": {"type": "array", "items": {"type": "string"}},
                    "headline": {"type": "string"},
                    "body": {"type": "string"},
                    "confidence": {"type": "string"},
                    "kind": {"type": "string"},
                },
            },
        }
    },
}
SYSTEM = """Extra market findings for review.

""" + READER_VOICE + """

Use only the signals JSON and any news_map. Each item: signal_ids, headline (<=12 words), body (<=55 words), confidence, kind.
Name connections between signals and news themes. No advice.
"""
VERIFY = """Check each finding. supported is false if a number or event is not in the signals. Return supported, unsupported_claims, too_long, unclear_phrases, revised. revised.items may replace the list."""
REVISE = """Rewrite the findings using the verifier notes. Drop any finding that is not supported."""


def build(ctx: RunContext, *, signals: list[Signal] | None = None) -> InsightBundle:
    pack = fetch_section(ctx, "additional_insights", client=getattr(ctx, "qdrant", None))
    ctx.window = pack.window
    numbers = market_numbers(ctx)
    aligned = numbers.get("aligned_market_flows") or []
    flows = [
        {"fii_net": row.get("fii_net"), "dii_net": row.get("dii_net"), "nifty_change": row.get("nifty_pct")}
        for row in aligned
        if row.get("fii_net") is not None and row.get("nifty_pct") is not None
    ]
    clusters = [{"label": item.label, "days": item.weight} for item in pack.clusters[:12]]
    prices = {}
    chg = numbers.get("change_pct") or numbers.get("nifty_change_pct")
    if chg is not None:
        prices["Nifty 50"] = float(chg)
    found = signals if signals is not None else detect_signals(flows=flows, clusters=clusters, prices=prices)
    if ctx.artifacts is not None:
        ctx.artifacts.write_json("scores.json", [item.as_dict() for item in found])
    facts = {"signals": [item.as_dict() for item in found], "news_map": news_map_block(pack.clusters), **numbers}
    if not found:
        bundle = InsightBundle(
            insight_id=INSIGHT_ID,
            trading_date=ctx.trading_date.isoformat(),
            as_of_ist=ist_now().isoformat(),
            status="ok",
            skip_reason=None,
            items=[
                Envelope(
                    insight_id=INSIGHT_ID,
                    trading_date=ctx.trading_date.isoformat(),
                    as_of_ist=ist_now().isoformat(),
                    status="ok",
                    headline="No unusual signals today",
                    body="Nothing crossed the thresholds for extra findings this session.",
                    facts={"kind": "empty"},
                    meta=Meta(prompt_version="v1"),
                )
            ],
            meta={"signal_count": 0, "run_mode": "live" if ctx.live else "scheduled"},
        )
        if not ctx.dry_run:
            save_bundle(bundle, root=ctx.config.data_dir, live=ctx.live)
        return bundle

    def compose(data: dict[str, Any]) -> Envelope:
        return Envelope(
            insight_id=INSIGHT_ID,
            trading_date=ctx.trading_date.isoformat(),
            as_of_ist=ist_now().isoformat(),
            status="ok",
            headline="Additional findings",
            body="See items.",
            facts={**facts, "draft_items": data.get("items") or []},
            meta=Meta(prompt_version="v1"),
        )

    if ctx.dry_run or not ctx.llm:
        envelope = compose({"items": []})
    else:
        envelope = run_quality_loop(
            ctx,
            spec=LoopSpec(SYSTEM, VERIFY, REVISE, _user(facts), SCHEMA, compose),
            facts=facts,
            evidence=[],
        ).envelope
    items = _cards(ctx, envelope.facts.get("draft_items") or [], found)
    status = "ok" if any(item.status == "ok" for item in items) else "degraded"
    bundle = InsightBundle(insight_id=INSIGHT_ID, trading_date=ctx.trading_date.isoformat(), as_of_ist=ist_now().isoformat(), status=status, items=items, meta={"signal_count": len(found)})
    if not ctx.dry_run:
        save_bundle(bundle, root=ctx.config.data_dir, live=ctx.live)
    return bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_insight.additional_insights.run")
    parser.add_argument("--date", default="")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    day = date.fromisoformat(args.date) if args.date else ist_now().date()

    def _build(ctx: RunContext) -> InsightBundle:
        return build(ctx)

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


def _cards(ctx: RunContext, drafts: list[dict], signals: list[Signal]) -> list[Envelope]:
    known = {item.id: item for item in signals}
    cards = []
    for draft in drafts[:6]:
        ids = [str(item) for item in draft.get("signal_ids") or []]
        if any(item not in known for item in ids):
            continue
        numbers = " ".join(str(value) for item in ids for value in known[item].numbers.values())
        body = str(draft.get("body") or "")
        status = "ok" if draft.get("confidence") != "low" else "degraded"
        cards.append(Envelope(
            insight_id=INSIGHT_ID,
            trading_date=ctx.trading_date.isoformat(),
            as_of_ist=ist_now().isoformat(),
            status=status,  # type: ignore[arg-type]
            headline=str(draft.get("headline") or "Additional finding"),
            body=body,
            facts={"kind": draft.get("kind") or "additional", "signal_ids": ids, "numbers_text": numbers},
            viz=Viz(type="none"),
            meta=Meta(prompt_version="v1"),
        ))
    return cards


def _user(facts: dict) -> str:
    import json
    return "SIGNALS\n" + json.dumps(facts, default=str)


if __name__ == "__main__":
    raise SystemExit(main())