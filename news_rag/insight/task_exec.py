"""Planner tasks: bind subjects, keep the tools those facts need, render the cells.

The planner names subjects and facts. This module does not read the user question.
"""

from __future__ import annotations

from typing import Any

from news_rag.insight.contracts import ExecutionPlan, ToolCall

SUBJECT_KINDS = frozenset({
    "all_holdings",
    "holding_by_category",
    "holding_by_name",
    "chat_ref",
    "catalog_fund",
    "category_peer",
})

# Fact name the planner may use -> get_fund_data module. None means the holdings row already has it.
FACT_MODULE: dict[str, str | None] = {
    "nav": None,
    "nav_date": None,
    "aum": None,
    "invested": None,
    "units": None,
    "xirr": None,
    "absolute_return": None,
    "category": None,
    "value": None,
    "manager": "managers",
    "managers": "managers",
    "fund_manager": "managers",
    "manager_experience": "managers",
    "returns": "snapshot",
    "return": "snapshot",
    "expense": "snapshot",
    "exit_load": "snapshot",
    "risk": "risk",
    "rating": "rating",
    "benchmark": "vs_benchmark",
    "holdings_composition": "composition",
    "composition": "composition",
}

_FACT_ALIASES = {
    "fund_manager": "manager",
    "managers": "manager",
    "return": "returns",
}

_HOLDING_COL = {
    "nav": "current_nav",
    "nav_date": "nav_date",
    "aum": "aum_inr",
    "value": "aum_inr",
    "invested": "invested_inr",
    "units": "units",
    "xirr": "xirr_pct",
    "absolute_return": "absolute_return_pct",
    "category": "scheme_category",
}


def _canon_fact(name: str) -> str:
    key = str(name or "").strip().lower().replace(" ", "_")
    return _FACT_ALIASES.get(key, key)


def parse_task_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw[:6]:
        if not isinstance(item, dict):
            continue
        subjects: list[dict[str, str]] = []
        for sub in item.get("subjects") or []:
            if not isinstance(sub, dict):
                continue
            kind = str(sub.get("kind") or "").strip().lower()
            if kind not in SUBJECT_KINDS:
                continue
            subjects.append({"kind": kind, "value": str(sub.get("value") or "").strip()})
        facts: list[dict[str, str]] = []
        for fact in item.get("facts") or []:
            if isinstance(fact, str):
                name, window = fact, ""
            elif isinstance(fact, dict):
                name = str(fact.get("name") or fact.get("fact") or "")
                window = str(fact.get("window") or "")
            else:
                continue
            name = _canon_fact(name)
            if name not in FACT_MODULE and name not in _HOLDING_COL:
                continue
            facts.append({"name": name, "window": window.strip().upper()})
        if not subjects:
            continue
        if not facts:
            facts = [{"name": "value", "window": ""}]
        op = str(item.get("operation") or "lookup").strip().lower()
        if op not in ("lookup", "compare", "rank", "explain"):
            op = "lookup"
        out.append({
            "subjects": subjects,
            "facts": facts,
            "operation": op,
            "presentation": str(item.get("presentation") or "table"),
        })
    return out


def _facts_from_plan(plan: ExecutionPlan) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in list(plan.asked_facts or []) + list(plan.asked_fields or []):
        name = _canon_fact(str(raw).split(":")[0])
        window = ""
        if ":" in str(raw):
            window = str(raw).split(":", 1)[1].strip().upper()
        if name not in FACT_MODULE and name not in _HOLDING_COL:
            continue
        key = f"{name}:{window}"
        if key in seen:
            continue
        seen.add(key)
        facts.append({"name": name, "window": window})
    return facts


def synthesize_tasks(plan: ExecutionPlan) -> list[dict[str, Any]]:
    """Build tasks from fields the planner already set. No question text."""
    if plan.tasks:
        return list(plan.tasks)
    facts = _facts_from_plan(plan)
    tasks: list[dict[str, Any]] = []
    intent = str(plan.intent or "").lower()

    if intent == "compare" or any(c.tool == "compare_funds" for c in plan.tool_calls or []):
        subjects: list[dict[str, str]] = []
        for side in plan.compare_sides or []:
            source = str(side.get("source") or "")
            if source == "my_holding":
                subjects.append({
                    "kind": "holding_by_category" if side.get("category") else "holding_by_name",
                    "value": str(side.get("category") or side.get("name") or ""),
                })
            elif source == "chat_memory":
                subjects.append({"kind": "chat_ref", "value": str(side.get("name") or "")})
            elif side.get("name"):
                subjects.append({"kind": "catalog_fund", "value": str(side.get("name") or "")})
        for name in plan.funds or []:
            if not any(s.get("value") == name for s in subjects):
                subjects.append({"kind": "holding_by_name", "value": str(name)})
        category = str(plan.scheme_category or "").strip()
        if not category and len(subjects) < 2:
            category = _category_in_planner_text(plan)
        if category and not any(s.get("kind") == "category_peer" and s.get("value") == category for s in subjects):
            if len([s for s in subjects if s.get("value")]) < 2:
                subjects.append({"kind": "category_peer", "value": category})
        if not facts:
            facts = [{"name": "returns", "window": _window_code(plan)}, {"name": "nav", "window": ""}]
        if len(subjects) >= 1:
            tasks.append({
                "subjects": subjects,
                "facts": facts,
                "operation": "compare",
                "presentation": "table",
            })

    if facts and not tasks:
        scope = str(plan.holding_scope or "").lower()
        need = str(plan.data_need or "").lower()
        book = need.startswith("investor") or str(plan.portfolio_scope or "").lower() in ("investor", "both")
        subjects = []
        if scope == "all_holdings" or (book and not plan.funds):
            subjects = [{"kind": "all_holdings", "value": ""}]
        elif plan.funds:
            subjects = [{"kind": "holding_by_name", "value": name} for name in plan.funds]
        elif scope == "single":
            subjects = [{"kind": "chat_ref", "value": ""}]
        if subjects:
            tasks.append({
                "subjects": subjects,
                "facts": facts,
                "operation": "lookup",
                "presentation": "table" if len(subjects) != 1 else "sentence",
            })
    return tasks


def _window_code(plan: ExecutionPlan) -> str:
    from news_rag.insight.return_windows import normalize_window_code

    code = normalize_window_code(str(plan.window_label or ""))
    return code or "1M"


def _category_in_planner_text(plan: ExecutionPlan) -> str:
    """A category slug the planner wrote that is not already one of the bound funds."""
    from news_rag.fund_rating_categories import _CATEGORY_ALIASES, _spaced_category_words

    blob = " ".join(
        part for part in (
            plan.planner_reading,
            plan.goal,
            plan.scheme_category,
            " ".join(plan.scheme_categories or []),
        ) if part
    )
    if not blob.strip():
        return ""
    low = _spaced_category_words(blob).lower()
    held = " ".join(plan.funds or []).lower()
    hits: list[tuple[int, str]] = []
    for phrase, _fund_type, category in _CATEGORY_ALIASES:
        if not phrase or not category:
            continue
        if category.lower() in held:
            continue
        at = low.find(phrase)
        if at >= 0:
            hits.append((len(phrase), category))
    if not hits:
        return ""
    hits.sort(key=lambda item: -item[0])
    return hits[0][1]


def _holding_names(memory: dict[str, Any] | None) -> list[dict[str, str]]:
    from news_rag.insight.memory.fund_context import owned_holding_rows

    categories: dict[str, str] = {}
    if isinstance(memory, dict):
        for row in memory.get("holdings_in_chat") or []:
            if isinstance(row, dict) and row.get("name"):
                categories[str(row["name"]).lower()] = str(row.get("category") or row.get("scheme_category") or "")
    rows = []
    for row in owned_holding_rows(memory):
        name = row.get("name") or ""
        rows.append({
            "name": name,
            "isin": row.get("isin") or "",
            "category": categories.get(name.lower(), ""),
        })
    return rows


_BOOK_TOTALS = frozenset({"aum", "value", "invested"})


def _scheme_filter(plan: ExecutionPlan) -> str:
    for call in plan.tool_calls or []:
        if call.tool != "get_investor_portfolio":
            continue
        filt = str((call.arguments or {}).get("scheme_filter") or "").strip()
        if filt and filt.lower() not in ("any", "all", "none", "*"):
            return filt
    return str(plan.scheme_category or "").strip()


def _narrow_aggregate_subjects(plan: ExecutionPlan, tasks: list[dict[str, Any]]) -> None:
    """Book totals stay one figure. A category filter stays that category, not every holding."""
    filt = _scheme_filter(plan)
    for task in tasks:
        facts = {str(f.get("name") or "") for f in (task.get("facts") or [])}
        if not facts or not facts <= _BOOK_TOTALS:
            continue
        if filt:
            task["subjects"] = [{"kind": "holding_by_category", "value": filt}]
            continue
        if any(s.get("kind") == "all_holdings" for s in (task.get("subjects") or [])) and not plan.funds:
            task["book_total"] = True
            task["presentation"] = "sentence"


def bind_subjects(tasks: list[dict[str, Any]], memory: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Attach resolved names from memory. category_peer stays for the rating screen."""
    rows = _holding_names(memory)
    by_name = {r["name"].lower(): r for r in rows if r["name"]}
    notes: list[str] = []
    for task in tasks:
        bound: list[dict[str, str]] = []
        for sub in task.get("subjects") or []:
            kind = sub.get("kind")
            value = str(sub.get("value") or "")
            if kind == "all_holdings":
                if rows:
                    bound.extend({"kind": "holding_by_name", "value": r["name"], "isin": r["isin"]} for r in rows)
                else:
                    bound.append({"kind": "all_holdings", "value": "", "isin": ""})
                continue
            if kind == "category_peer":
                held = _holding_for_category(rows, value)
                if held:
                    bound.append({"kind": "holding_by_name", "value": held["name"], "isin": held["isin"]})
                else:
                    bound.append({"kind": "category_peer", "value": value, "isin": ""})
                    notes.append(value)
                continue
            if kind in ("holding_by_name", "catalog_fund", "chat_ref"):
                hit = by_name.get(value.lower())
                if hit:
                    bound.append({"kind": "holding_by_name", "value": hit["name"], "isin": hit["isin"]})
                elif value:
                    bound.append({"kind": kind, "value": value, "isin": ""})
                continue
            if kind == "holding_by_category":
                held = _holding_for_category(rows, value)
                if held:
                    bound.append({"kind": "holding_by_name", "value": held["name"], "isin": held["isin"]})
                else:
                    bound.append({"kind": "category_peer", "value": value, "isin": ""})
                    notes.append(value)
        task["bound"] = bound
    return notes


def _holding_for_category(rows: list[dict[str, str]], category: str) -> dict[str, str] | None:
    cat = str(category or "").strip().lower()
    if not cat:
        return None
    for row in rows:
        if str(row.get("category") or "").strip().lower() == cat:
            return row
        if cat in str(row.get("name") or "").lower():
            return row
    return None


def _modules_for(tasks: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    modules: list[str] = []
    windows: list[str] = []
    for task in tasks:
        for fact in task.get("facts") or []:
            mod = FACT_MODULE.get(fact.get("name") or "")
            if mod and mod not in modules:
                modules.append(mod)
            window = str(fact.get("window") or "")
            if fact.get("name") in ("returns", "return") and window and window not in windows:
                windows.append(window)
    return modules, windows


def apply_task_layer(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
    query_log: Any = None,
) -> ExecutionPlan:
    """Restore tools the planner's facts need after earlier hooks, and name category peers."""
    tasks = synthesize_tasks(plan)
    if not tasks:
        return plan
    _narrow_aggregate_subjects(plan, tasks)
    peer_notes = bind_subjects(tasks, memory)
    plan.tasks = tasks
    modules, windows = _modules_for(tasks)
    needs_book = any(
        s.get("kind") in ("all_holdings", "holding_by_name", "holding_by_category", "chat_ref")
        for task in tasks
        for s in (task.get("subjects") or [])
    )
    peers = [
        s.get("value") or ""
        for task in tasks
        for s in (task.get("bound") or task.get("subjects") or [])
        if s.get("kind") == "category_peer" and s.get("value")
    ]

    if needs_book and not any(c.tool == "get_investor_portfolio" for c in plan.tool_calls or []):
        plan.tool_calls.insert(0, ToolCall(
            tool="get_investor_portfolio",
            arguments={"modules": ["holdings"], "include_meta": True, "holdings_fields": "standard", "top_n": 20},
            wave=1,
            why="Holdings for the planner's subjects",
        ))

    if any(s.get("kind") == "all_holdings" for t in tasks for s in (t.get("subjects") or [])):
        plan.holding_scope = "all_holdings"
        if str(plan.portfolio_scope or "").lower() in ("none", "", "investor"):
            plan.portfolio_scope = "both" if modules else plan.portfolio_scope or "investor"

    if modules:
        _merge_fund_modules(plan, modules, windows)
        if str(plan.portfolio_intent or "") == "list_holdings":
            plan.portfolio_intent = "none"
        plan.requires_compose = True

    for category in peers:
        if _has_peer_screen(plan, category):
            continue
        plan.tool_calls.append(ToolCall(
            tool="screen_funds_by_exposure",
            arguments={
                "rating_screen": True,
                "focus_question": category,
                "top_n": 1,
                "direction": "any",
            },
            wave=1,
            why=f"Peer fund in {category}; the user does not hold one",
        ))
    if peers and not any(c.tool == "compare_funds" for c in plan.tool_calls or []):
        plan.tool_calls.append(ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1))
        plan.intent = "compare"
        plan.requires_compose = True

    if peer_notes:
        note = (
            "No holding matched "
            + ", ".join(dict.fromkeys(peer_notes))
            + ". A top RupeeStop-rated fund in that category is the comparison peer, not a recommendation."
        )
        existing = (plan.presentation_notes or "").strip()
        if note not in existing:
            plan.presentation_notes = f"{existing} {note}".strip()

    if query_log is not None:
        query_log.write(
            "TASKS "
            + " | ".join(
                f"{t.get('operation')} subjects={[s.get('kind') for s in t.get('subjects') or []]} "
                f"facts={[f.get('name') for f in t.get('facts') or []]}"
                for t in tasks
            )
        )
        query_log.write(f"BIND peers={peers} modules={modules}")
    return plan


def _has_peer_screen(plan: ExecutionPlan, category: str) -> bool:
    cat = category.lower()
    for call in plan.tool_calls or []:
        if call.tool != "screen_funds_by_exposure":
            continue
        focus = str((call.arguments or {}).get("focus_question") or "").lower()
        if cat and cat in focus:
            return True
    return False


def _merge_fund_modules(plan: ExecutionPlan, modules: list[str], windows: list[str]) -> None:
    for call in plan.tool_calls or []:
        if call.tool != "get_fund_data":
            continue
        args = dict(call.arguments or {})
        have = [str(m) for m in (args.get("modules") or [])]
        for mod in modules:
            if mod not in have:
                have.append(mod)
        args["modules"] = have
        if windows:
            got = [str(w) for w in (args.get("windows") or [])]
            for window in windows:
                if window not in got:
                    got.append(window)
            args["windows"] = got
        call.arguments = args
        return
    args: dict[str, Any] = {"modules": modules}
    if windows:
        args["windows"] = windows
    plan.tool_calls.append(ToolCall(
        tool="get_fund_data",
        arguments=args,
        wave=1,
        why="Catalog facts the planner asked for, one call per holding",
    ))


def repair_compare_with_screen_peer(state: Any) -> None:
    """If compare failed and a rating screen returned a peer, compare the held fund with that peer."""
    plan = getattr(state, "plan", None)
    if plan is None or not plan.tasks:
        return
    peers = [
        s for t in plan.tasks for s in (t.get("bound") or []) if s.get("kind") == "category_peer"
    ]
    if not peers:
        return
    if any(r.get("tool") == "compare_funds" and r.get("ok") for r in state.wave1_results or []):
        return
    peer_name = ""
    for row in state.wave1_results or []:
        if row.get("tool") != "screen_funds_by_exposure" or not row.get("ok"):
            continue
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        for fund_row in data.get("rankings") or data.get("funds") or []:
            if isinstance(fund_row, dict) and str(fund_row.get("fund_name") or "").strip():
                peer_name = str(fund_row["fund_name"]).strip()
                break
        if peer_name:
            break
    held = [str(f).strip() for f in (plan.funds or []) if str(f).strip() and str(f).strip() != peer_name]
    if not peer_name or not held:
        return
    names = held[:1] + [peer_name]
    plan.funds = names
    from news_rag.insight.capabilities.executor import execute_wave

    ctx = {
        "question": getattr(state, "question", "") or "",
        "window_days": plan.window_days,
        "fund_names": names,
    }
    rows = execute_wave(
        [ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
        ctx,
        fund_names=names,
        telemetry=getattr(state, "telemetry", None),
    )
    state.wave1_results.extend(rows)
    log = getattr(state, "query_log", None)
    if log is not None:
        log.write(f"FANOUT compare_peer held={held[0]} peer={peer_name} ok={any(r.get('ok') for r in rows)}")


def render_task_answer(plan: ExecutionPlan, data_pack: dict[str, Any] | None) -> str:
    """One section per task. Figures come from tool data, not from a model."""
    tasks = list(plan.tasks or [])
    if not tasks or not isinstance(data_pack, dict):
        return ""
    holdings = _holdings_from_pack(data_pack)
    funds = _funds_from_pack(data_pack)
    summary = _summary_from_pack(data_pack)
    sections: list[str] = []
    coverage: list[str] = []
    for task in tasks:
        if task.get("operation") == "compare" and not funds and not holdings:
            continue
        section, cov = _render_task(task, holdings, funds, summary)
        if section:
            sections.append(section)
        coverage.extend(cov)
    if not sections:
        return ""
    text = "\n\n".join(sections)
    note = (plan.presentation_notes or "").strip()
    if "comparison peer" in note:
        text += "\n\n" + note
    return text


def coverage_line(plan: ExecutionPlan, data_pack: dict[str, Any] | None) -> str:
    if not plan.tasks or not isinstance(data_pack, dict):
        return ""
    holdings = _holdings_from_pack(data_pack)
    funds = _funds_from_pack(data_pack)
    summary = _summary_from_pack(data_pack)
    bits = []
    for task in plan.tasks:
        _, cov = _render_task(task, holdings, funds, summary)
        bits.extend(cov)
    return "COVERAGE " + " ".join(bits) if bits else ""


def _holdings_from_pack(data_pack: dict[str, Any]) -> list[dict[str, Any]]:
    book = data_pack.get("investor_portfolio")
    if isinstance(book, dict):
        rows = book.get("holdings")
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
    return []


def _summary_from_pack(data_pack: dict[str, Any]) -> dict[str, Any]:
    book = data_pack.get("investor_portfolio")
    if isinstance(book, dict) and isinstance(book.get("summary"), dict):
        return book["summary"]
    return {}


def _funds_from_pack(data_pack: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for key, value in data_pack.items():
        if str(key).startswith("fund:") and isinstance(value, dict):
            out.append(value)
    compare = data_pack.get("compare") or data_pack.get("fund_compare")
    if isinstance(compare, dict):
        for row in compare.get("funds") or compare.get("schemes") or []:
            if isinstance(row, dict):
                out.append(row)
    return out


def _render_task(
    task: dict[str, Any],
    holdings: list[dict[str, Any]],
    funds: list[dict[str, Any]],
    summary: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    facts = task.get("facts") or []
    if task.get("book_total"):
        return _book_total_line(facts, summary or {})
    names = _subject_names(task, holdings)
    if not names:
        return "", []
    header = ["Fund"] + [_fact_label(f) for f in facts]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    coverage = []
    for name in names:
        holding = _match_holding(holdings, name)
        fund = _match_fund(funds, name)
        cells = [name]
        for fact in facts:
            value, ok = _cell(fact, holding, fund)
            cells.append(value)
            coverage.append(f"{fact.get('name')}={'1' if ok else '0'}")
        lines.append("| " + " | ".join(cells) + " |")
    if len(names) == 1 and len(facts) == 1:
        fact = facts[0]
        holding = _match_holding(holdings, names[0])
        fund = _match_fund(funds, names[0])
        value, ok = _cell(fact, holding, fund)
        if not ok:
            return f"{names[0]}: {value}", [f"{fact.get('name')}=0"]
        return f"{names[0]}: {value}", [f"{fact.get('name')}=1"]
    return "\n".join(lines), coverage


def _book_total_line(facts: list[dict[str, str]], summary: dict[str, Any]) -> tuple[str, list[str]]:
    keys = {"aum": "aum_inr", "value": "aum_inr", "invested": "invested_inr"}
    bits: list[str] = []
    coverage: list[str] = []
    for fact in facts:
        name = fact.get("name") or ""
        raw = summary.get(keys.get(name, ""))
        ok = raw not in (None, "")
        if ok:
            bits.append(f"{_fact_label(fact)} {_fmt(name, raw)}")
        coverage.append(f"{name}={'1' if ok else '0'}")
    return ("; ".join(bits), coverage) if bits else ("", coverage)


def _subject_names(task: dict[str, Any], holdings: list[dict[str, Any]]) -> list[str]:
    bound = task.get("bound") or task.get("subjects") or []
    if any(s.get("kind") == "all_holdings" for s in bound) and holdings:
        return [str(r.get("scheme_name") or r.get("name") or "") for r in holdings]
    names = []
    for sub in bound:
        if sub.get("kind") == "category_peer":
            continue
        value = str(sub.get("value") or "").strip()
        if value and value not in names:
            names.append(value)
    if not names and holdings and any(s.get("kind") == "all_holdings" for s in (task.get("subjects") or [])):
        return [str(r.get("scheme_name") or "") for r in holdings]
    return names


def _fact_label(fact: dict[str, str]) -> str:
    name = fact.get("name") or ""
    labels = {
        "nav": "NAV",
        "nav_date": "NAV date",
        "aum": "Value",
        "value": "Value",
        "invested": "Invested",
        "absolute_return": "Return",
        "manager": "Manager",
        "manager_experience": "Experience",
        "returns": f"Return {fact.get('window') or ''}".strip(),
        "expense": "Expense",
        "exit_load": "Exit load",
        "risk": "Risk",
        "rating": "Rating",
        "category": "Category",
        "units": "Units",
        "xirr": "XIRR",
    }
    return labels.get(name, name.replace("_", " ").title())


def _match_holding(rows: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    key = name.lower()
    for row in rows:
        scheme = str(row.get("scheme_name") or row.get("name") or "").lower()
        if scheme == key or key in scheme or scheme in key:
            return row
    return None


def _match_fund(funds: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    key = name.lower()
    for fund in funds:
        label = str(fund.get("fund_name") or fund.get("scheme_name") or fund.get("name") or "").lower()
        if label == key or (key and (key in label or label in key)):
            return fund
    return None


def _cell(fact: dict[str, str], holding: dict[str, Any] | None, fund: dict[str, Any] | None) -> tuple[str, bool]:
    name = fact.get("name") or ""
    if name in _HOLDING_COL and holding is not None:
        raw = holding.get(_HOLDING_COL[name])
        if raw not in (None, ""):
            return _fmt(name, raw), True
    if name in ("manager", "manager_experience"):
        text = _manager_cell(fund, experience=name == "manager_experience")
        if text:
            return text, True
        return "n/a", False
    if name == "returns" and fund is not None:
        text = _return_cell(fund, fact.get("window") or "")
        if text:
            return text, True
        if holding is not None and not fact.get("window"):
            raw = holding.get("absolute_return_pct")
            if raw not in (None, ""):
                return _fmt("absolute_return", raw), True
    if fund is not None:
        snap = fund.get("snapshot") if isinstance(fund.get("snapshot"), dict) else {}
        if name == "expense" and snap.get("expense_ratio") not in (None, ""):
            return str(snap.get("expense_ratio")), True
        if name == "exit_load" and snap.get("exit_load_summary"):
            return str(snap.get("exit_load_summary")), True
        if name == "nav" and snap.get("nav") not in (None, ""):
            return _fmt("nav", snap.get("nav")), True
        if name == "risk":
            risk = fund.get("risk")
            if isinstance(risk, dict) and (risk.get("riskometer") or risk.get("level")):
                return str(risk.get("riskometer") or risk.get("level")), True
        if name == "rating":
            rating = fund.get("rating") if isinstance(fund.get("rating"), dict) else {}
            if rating.get("score") not in (None, ""):
                return str(rating.get("score")), True
    return "n/a", False


def _manager_cell(fund: dict[str, Any] | None, *, experience: bool) -> str:
    if not isinstance(fund, dict):
        return ""
    managers = fund.get("managers") if isinstance(fund.get("managers"), dict) else {}
    current = [r for r in (managers.get("current") or []) if isinstance(r, dict) and r.get("name")]
    if not current:
        return ""
    bits = []
    for row in current:
        if not experience:
            bits.append(str(row.get("name")))
            continue
        part = str(row.get("name"))
        if row.get("managing_since"):
            part += f" since {row['managing_since']}"
        years = row.get("total_experience_years")
        if years not in (None, ""):
            part += f", {years} years"
        elif not row.get("managing_since"):
            part += ", experience n/a"
        bits.append(part)
    return "; ".join(bits)


def _return_cell(fund: dict[str, Any], window: str) -> str:
    snap = fund.get("snapshot") if isinstance(fund.get("snapshot"), dict) else {}
    series = snap.get("returns") or snap.get("trailing_returns") or fund.get("returns")
    if isinstance(series, dict) and window:
        raw = series.get(window) or series.get(window.lower())
        if raw not in (None, ""):
            return _fmt("absolute_return", raw)
    if isinstance(series, dict):
        for key, raw in series.items():
            if raw not in (None, ""):
                return f"{key} {_fmt('absolute_return', raw)}"
    return ""


def _fmt(name: str, raw: Any) -> str:
    if name in ("nav", "aum", "value", "invested"):
        try:
            return f"Rs {float(raw):,.2f}"
        except (TypeError, ValueError):
            return str(raw)
    if name in ("absolute_return", "xirr"):
        try:
            num = float(raw)
        except (TypeError, ValueError):
            return str(raw)
        sign = "+" if num > 0 else ""
        return f"{sign}{num:.2f}%"
    return str(raw)
