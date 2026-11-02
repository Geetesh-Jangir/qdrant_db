"""Ensure every party in an implicit fund comparison has aligned catalog facts."""

from __future__ import annotations

from typing import Any

from news_rag.insight.contracts import ExecutionPlan, ToolCall


def _screen_ranking_names(wave1_results: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in wave1_results or []:
        if row.get("tool") != "screen_funds_by_exposure" or not row.get("ok"):
            continue
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        for fund_row in data.get("rankings") or data.get("funds") or []:
            if not isinstance(fund_row, dict):
                continue
            name = str(fund_row.get("fund_name") or "").strip()
            if name and name not in names:
                names.append(name)
    return names


def _screen_anchor_name(plan: ExecutionPlan | None) -> str:
    if plan is None:
        return ""
    for call in plan.tool_calls or []:
        if call.tool != "screen_funds_by_exposure":
            continue
        args = call.arguments or {}
        for raw in args.get("exclude_names") or []:
            name = str(raw or "").strip()
            if name:
                return name
    funds = [str(f or "").strip() for f in (plan.funds or []) if str(f or "").strip()]
    if len(funds) == 1:
        return funds[0]
    return ""


def _screen_wants_pair_compare(plan: ExecutionPlan | None) -> bool:
    if plan is None:
        return False
    for call in plan.tool_calls or []:
        if call.tool != "screen_funds_by_exposure":
            continue
        args = call.arguments or {}
        if args.get("pick_rating_better") or args.get("pick_alternate") or args.get("compare_pair"):
            return True
    intent = str(plan.intent or "").strip().lower()
    if intent == "compare" and any(c.tool == "screen_funds_by_exposure" for c in plan.tool_calls or []):
        return True
    return False


def resolve_compare_fund_pair(
    plan: ExecutionPlan | None,
    wave1_results: list[dict[str, Any]],
) -> list[str]:
    """Two fund names that should share compare_funds / aligned snapshot evidence."""
    if plan is not None and len(plan.funds or []) >= 2:
        pair = [str(f).strip() for f in plan.funds[:2] if str(f).strip()]
        if len(pair) >= 2:
            return pair[:2]

    picked = _screen_ranking_names(wave1_results)
    anchor = _screen_anchor_name(plan)

    if anchor and picked:
        candidate = next((n for n in picked if n.lower() != anchor.lower()), picked[0] if picked else "")
        if candidate and candidate.lower() != anchor.lower():
            return [anchor, candidate]

    if len(picked) >= 2:
        return picked[:2]

    return []


def maybe_run_compare_funds_for_parties(state: Any) -> None:
    """After wave 1, fetch compare_funds when a screen pick implies a two-fund comparison."""
    from news_rag.insight.capabilities.executor import execute_wave

    wave1 = list(getattr(state, "wave1_results", None) or [])
    if any(r.get("tool") == "compare_funds" and r.get("ok") for r in wave1):
        return

    plan = getattr(state, "plan", None)
    pair = resolve_compare_fund_pair(plan, wave1)
    if len(pair) < 2:
        return

    if not _screen_wants_pair_compare(plan) and str(getattr(plan, "intent", "") or "").lower() != "compare":
        return

    ctx = {
        "question": getattr(state, "question", "") or "",
        "window_days": getattr(plan, "window_days", 30) if plan else 30,
        "fund_names": pair,
        "return_window": "1M",
    }
    conv_id = getattr(state, "conversation_id", None)
    if conv_id:
        turn = 0
        mem = getattr(state, "memory", None)
        if isinstance(mem, dict):
            turn = int(mem.get("turn_count") or 0)
        ctx["conversation_id"] = conv_id
        ctx["conversation_turn"] = turn + 1
    state.resolved_funds = pair
    if plan is not None:
        plan.funds = pair
        plan.requires_compose = True
        note = (
            "Use compare_funds output for **both** schemes — same return windows and RupeeStop fields. "
            "Do not say a figure is missing for one side when compare_funds or fund blocks are present."
        )
        existing = (plan.presentation_notes or "").strip()
        if note not in existing:
            plan.presentation_notes = f"{existing} {note}".strip()

    compare_rows = execute_wave(
        [ToolCall(tool="compare_funds", arguments={"compare_on": "all", "mode": "both"}, wave=1)],
        ctx,
        fund_names=pair,
        telemetry=getattr(state, "telemetry", None),
        query_log=getattr(state, "query_log", None),
    )
    wave1.extend(compare_rows)
    state.wave1_results = wave1

    qlog = getattr(state, "query_log", None)
    if qlog is not None and compare_rows:
        qlog.write(
            f"TOOLS wave=1 compare_pair_followup funds={pair!r} "
            f"ok={sum(1 for r in compare_rows if r.get('ok'))}"
        )
