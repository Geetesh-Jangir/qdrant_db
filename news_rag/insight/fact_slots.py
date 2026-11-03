"""Render planner-chosen facts from tool results — no question parsing."""

from __future__ import annotations

from typing import Any

from news_rag.insight.contracts import ExecutionPlan

_MODULE_TO_SLOT = {
    "managers": "fund_manager",
    "rating": "rs_rating",
}


def slots_from_plan(plan: ExecutionPlan) -> list[str]:
    """Slots implied by planner asked_facts and wave-1 get_fund_data arguments."""
    out: list[str] = []
    for raw in plan.asked_facts or []:
        item = str(raw or "").strip()
        if item:
            out.append(item)
    for call in plan.tool_calls or []:
        if call.tool != "get_fund_data":
            continue
        args = call.arguments or {}
        modules = [str(m).lower() for m in (args.get("modules") or [])]
        if "snapshot" in modules:
            for code in args.get("windows") or []:
                slot = f"return:{str(code).upper()}"
                if slot not in out:
                    out.append(slot)
            if not args.get("windows"):
                out.extend(["return:1Y", "return:3Y", "return:5Y"])
        if args.get("pillars"):
            if "four_pillars" not in out:
                out.append("four_pillars")
        for mod, slot in _MODULE_TO_SLOT.items():
            if mod in modules and slot not in out:
                out.append(slot)
    return list(dict.fromkeys(out))


def asked_slots(question: str = "") -> list[str]:
    """Backward-compatible alias; callers should pass plan via slots_from_plan."""
    del question
    return []


def merge_planner_asked_facts(plan: ExecutionPlan) -> None:
    plan.asked_facts = list(dict.fromkeys([*(plan.asked_facts or []), *slots_from_plan(plan)]))


def tag_answer_parts(plan: ExecutionPlan) -> ExecutionPlan:
    """Fill sub_query source only when the planner omitted it."""
    task = str(getattr(plan, "concept_brief", "") or "")
    for part in plan.sub_queries or []:
        if part.get("source"):
            continue
        if str(plan.data_need or "") == "none" and not plan.tool_calls:
            part["source"] = "llm"
        elif task:
            part["source"] = "llm"
        else:
            part["source"] = "tool"
    return plan


def render_asked_facts(slots: list[str], results: list[dict[str, Any]] | None) -> str:
    if not slots:
        return ""
    lines = ["| Fact | Value |", "| --- | --- |"]
    found = False
    for row in results or []:
        if not row.get("ok") or row.get("tool") != "get_fund_data":
            continue
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        snap = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else data
        fund = str(row.get("fund") or snap.get("fund_name") or "").strip()
        prefix = f"{fund} — " if fund else ""
        for slot in slots:
            value = _slot_value(slot, data, snap)
            if not value:
                continue
            lines.append(f"| {prefix}{_slot_label(slot)} | {value} |")
            found = True
    if not found:
        return ""
    return "\n".join(lines)


def missing_slots(slots: list[str], results: list[dict[str, Any]] | None) -> list[str]:
    block = render_asked_facts(slots, results)
    return [
        slot
        for slot in slots
        if _slot_label(slot).lower() not in block.lower() and slot.split(":")[0] not in block.lower()
    ]


def _slot_label(slot: str) -> str:
    if slot.startswith("return:"):
        return f"{slot.split(':', 1)[1]} return"
    return {
        "nav": "NAV",
        "fund_manager": "Fund manager",
        "rs_rating": "RS rating",
        "four_pillars": "Four pillars",
        "aum": "AUM",
        "expense": "Expense ratio",
    }.get(slot, slot)


def _slot_value(slot: str, data: dict[str, Any], snap: dict[str, Any]) -> str:
    if slot == "nav" and snap.get("nav") is not None:
        date = snap.get("nav_date") or ""
        return f"{snap.get('nav')}{(' (' + str(date) + ')') if date else ''}"
    if slot.startswith("return:"):
        code = slot.split(":", 1)[1]
        if code.upper() == "1D":
            day = snap.get("day_change_pct")
            if day is None:
                day = snap.get("day_change")
            if day is not None:
                return str(day)
        returns = snap.get("returns") if isinstance(snap.get("returns"), dict) else {}
        if not returns:
            returns = data.get("returns") if isinstance(data.get("returns"), dict) else {}
        for key in (code, code.lower(), code.upper()):
            if returns.get(key) is not None:
                return str(returns.get(key))
        return ""
    if slot == "fund_manager":
        managers = data.get("managers") or snap.get("managers") or []
        if isinstance(managers, dict):
            managers = managers.get("current") or managers.get("managers") or []
        names = []
        for item in managers if isinstance(managers, list) else []:
            if isinstance(item, dict) and item.get("name"):
                names.append(str(item["name"]))
            elif isinstance(item, str):
                names.append(item)
        return ", ".join(names)
    rating = data.get("rating") if isinstance(data.get("rating"), dict) else {}
    if slot == "rs_rating":
        label = rating.get("label") or rating.get("rs_label") or snap.get("rs_label")
        score = rating.get("score") or rating.get("rs_score") or snap.get("rs_score")
        if label or score is not None:
            return " ".join(str(part) for part in (label, score) if part not in (None, ""))
    if slot == "four_pillars":
        pillars = rating.get("pillars") if isinstance(rating.get("pillars"), dict) else {}
        if pillars:
            return "; ".join(f"{key} {value}" for key, value in pillars.items())
    return ""
