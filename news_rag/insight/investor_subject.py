"""Resolve 'my contra fund' and similar asks to a holding in the investor book — no question regex."""

from __future__ import annotations

from typing import Any

from news_rag.insight.contracts import ExecutionPlan, ToolCall


def question_refers_to_investor_holding(question: str) -> bool:
    q = (question or "").strip().lower()
    if q.startswith("my "):
        return True
    return " my " in f" {q} "


def _category_slug_from_question(question: str) -> str:
    from news_rag.fund_rating_categories import match_scheme_category
    from news_rag.insight.category_plan import _categories_equivalent

    match = match_scheme_category(question or "")
    if match and match.category:
        return str(match.category).strip().lower()
    q = (question or "").lower()
    # Investor API slugs not always in rating taxonomy (e.g. contra).
    for token in (
        "contra",
        "large cap",
        "mid cap",
        "small cap",
        "large & mid cap",
        "flexi cap",
        "multi cap",
        "elss",
        "aggressive hybrid",
        "conservative hybrid",
    ):
        if token in q:
            return token
    return ""


def investor_holding_for_category(
    memory: dict[str, Any] | None,
    category_slug: str,
) -> dict[str, Any] | None:
    from news_rag.insight.category_plan import _categories_equivalent

    cat = str(category_slug or "").strip().lower()
    if not cat or not isinstance(memory, dict):
        return None
    for row in memory.get("holdings_in_chat") or []:
        if not isinstance(row, dict):
            continue
        row_cat = str(row.get("category") or "").strip().lower()
        if _categories_equivalent(row_cat, cat):
            return row
    frame = memory.get("frame") if isinstance(memory.get("frame"), dict) else {}
    for row in frame.get("investor_subjects") or []:
        if not isinstance(row, dict):
            continue
        row_cat = str(row.get("category") or "").strip().lower()
        if _categories_equivalent(row_cat, cat):
            return row
    return None


def resolve_investor_holding_fund_name(
    question: str,
    memory: dict[str, Any] | None,
) -> str:
    if not question_refers_to_investor_holding(question):
        return ""
    cat = _category_slug_from_question(question)
    if not cat:
        return ""
    row = investor_holding_for_category(memory, cat)
    if not row:
        return ""
    return str(row.get("name") or "").strip()


def holdings_rows_from_investor_tool_results(
    wave1_results: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in wave1_results or []:
        if item.get("tool") != "get_investor_portfolio" or not item.get("ok"):
            continue
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        for row in data.get("holdings") or []:
            if isinstance(row, dict):
                rows.append(row)
    return rows


def question_asks_whole_investor_portfolio(question: str, plan: ExecutionPlan | None = None) -> bool:
    """Book-level ask (value, allocation, all schemes) — not 'my contra fund'."""
    if _category_slug_from_question(question):
        return False
    q = (question or "").strip().lower()
    if plan is not None:
        need = str(plan.data_need or "").lower().strip()
        if need == "investor_summary":
            return True
        intent = str(plan.intent or "").lower().strip()
        scope = str(plan.portfolio_scope or "").lower().strip()
        if intent == "overview" and scope in ("investor", "both") and not (plan.funds or []):
            return True
    book_phrases = (
        "my portfolio",
        "whole portfolio",
        "entire portfolio",
        "all my funds",
        "all my holdings",
        "my holdings",
        "my mutual funds",
        "my mutual fund portfolio",
    )
    if any(p in q for p in book_phrases):
        return True
    if "portfolio" in q and not question_refers_deictic_fund(question):
        if question_refers_to_investor_holding(question) or "about" in q or "tell me" in q:
            return True
    return False


def resolve_investor_holding_from_holdings_rows(
    question: str,
    holdings: list[dict[str, Any]] | None,
) -> str:
    """After get_investor_portfolio when memory was empty at plan time."""
    if not question_refers_to_investor_holding(question):
        return ""
    cat = _category_slug_from_question(question)
    if not cat:
        return ""
    from news_rag.insight.category_plan import _categories_equivalent

    for row in holdings or []:
        if not isinstance(row, dict):
            continue
        row_cat = str(row.get("scheme_category") or row.get("category") or "").strip().lower()
        if _categories_equivalent(row_cat, cat):
            return str(row.get("scheme_name") or row.get("name") or "").strip()
    return ""


def apply_investor_category_fund_to_plan(
    plan: ExecutionPlan,
    question: str,
    memory: dict[str, Any] | None,
    wave1_results: list[dict[str, Any]] | None = None,
) -> ExecutionPlan:
    name = resolve_investor_holding_fund_name(question, memory)
    if not name:
        name = resolve_investor_holding_from_holdings_rows(
            question,
            holdings_rows_from_investor_tool_results(wave1_results),
        )
    if name:
        plan.funds = [name]
        if str(plan.portfolio_scope or "").lower().strip() in ("none", "", "catalog"):
            plan.portfolio_scope = "investor"
    return plan


def question_asks_holding_metric_and_glossary(question: str) -> bool:
    q = (question or "").lower()
    glossary = ("full form", "stands for", "stand for", "meaning of", "what does", "define", "definition", "abbreviation")
    metrics = ("nav", "xirr", "aum", "return", "units", "gain", "loss")
    return any(g in q for g in glossary) and any(m in q for m in metrics)


def question_needs_category_holdings_fetch(question: str) -> bool:
    """User asks for a figure on my {category} fund — needs holdings rows, not portfolio summary alone."""
    if not question_refers_to_investor_holding(question):
        return False
    return bool(_category_slug_from_question(question))


def ensure_my_category_fund_investor_plan(
    plan: ExecutionPlan,
    question: str,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """NAV/XIRR on 'my contra fund' → holdings module + category filter; not investor_summary."""
    cat = _category_slug_from_question(question)
    if not question_needs_category_holdings_fetch(question) or not cat:
        return plan

    name = resolve_investor_holding_fund_name(question, memory)
    if name:
        plan.funds = [name]
    plan.portfolio_scope = "investor"
    need = str(plan.data_need or "none").lower().strip()
    if need in ("investor_summary", "none", ""):
        plan.data_need = "investor_holding"

    holdings_args: dict[str, Any] = {
        "modules": ["holdings"],
        "include_meta": True,
        "holdings_fields": "standard",
        "top_n": 20,
        "sort_by": "aum",
        "scheme_filter": cat,
    }

    investor_calls = [c for c in plan.tool_calls or [] if c.tool == "get_investor_portfolio"]
    if investor_calls:
        for call in investor_calls:
            args = dict(call.arguments or {})
            modules = [str(m).lower() for m in (args.get("modules") or [])]
            if "holdings" not in modules:
                args["modules"] = ["holdings"]
            else:
                args["modules"] = modules
            args.update(holdings_args)
            args["modules"] = list(dict.fromkeys(args["modules"]))
            call.arguments = args
    else:
        plan.tool_calls = [
            ToolCall(
                tool="get_investor_portfolio",
                arguments=holdings_args,
                wave=1,
                why=f"Holdings for user's {cat} scheme (NAV/metrics)",
            ),
            *(plan.tool_calls or []),
        ]

    plan.requires_compose = True
    if question_asks_holding_metric_and_glossary(question):
        plan.response_shape = "short_answer"
        plan.max_words = max(int(plan.max_words or 0), 120)
    return plan


def refetch_category_holdings_if_missing(
    question: str,
    plan: ExecutionPlan,
    wave1_results: list[dict[str, Any]],
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    """Planner sometimes keeps summary-only; refetch holdings before compose."""
    if not question_needs_category_holdings_fetch(question):
        return wave1_results
    if holdings_rows_from_investor_tool_results(wave1_results):
        return wave1_results
    cat = _category_slug_from_question(question)
    if not cat:
        return wave1_results
    from news_rag.insight.capabilities.executor import execute_capability

    call = ToolCall(
        tool="get_investor_portfolio",
        arguments={
            "modules": ["holdings"],
            "include_meta": True,
            "holdings_fields": "standard",
            "top_n": 20,
            "sort_by": "aum",
            "scheme_filter": cat,
        },
        wave=1,
    )
    extra = execute_capability(call, fund_names=[], ctx=ctx, telemetry=None)
    if extra:
        return [*wave1_results, *extra]
    return wave1_results


def resolve_answer_subject(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    *,
    investor_holdings: list[dict[str, Any]] | None = None,
    wave1_results: list[dict[str, Any]] | None = None,
) -> str:
    subject = str((plan.funds or [""])[0] or "").strip()
    if subject:
        return subject
    subject = resolve_investor_holding_fund_name(question, memory)
    if subject:
        return subject
    holdings = list(investor_holdings or [])
    if not holdings:
        holdings = holdings_rows_from_investor_tool_results(wave1_results)
    subject = resolve_investor_holding_from_holdings_rows(question, holdings)
    if subject:
        return subject
    if not subject and question_refers_deictic_fund(question):
        subject = resolve_deictic_fund_name(question, memory)
    if subject:
        return subject
    if question_refers_to_investor_holding(question) and _category_slug_from_question(question):
        return ""
    if question_asks_whole_investor_portfolio(question, plan):
        return ""
    for row in holdings:
        if isinstance(row, dict) and row.get("scheme_name"):
            return str(row["scheme_name"]).strip()
        if isinstance(row, dict) and row.get("name"):
            return str(row["name"]).strip()
    return ""


def question_refers_deictic_fund(question: str) -> bool:
    """Follow-ups like 'do its risk analysis' — pronoun refers to a fund already in chat."""
    stripped = (question or "").strip().lower()
    if stripped.startswith(("its ", "it ")):
        return True
    q = f" {stripped} "
    if any(p in q for p in (" its ", " it ", " this fund", " that fund", " this scheme", " that scheme")):
        return True
    if any(p in q for p in (" its ", " it ")) and any(
        w in q for w in ("risk", "return", "nav", "rating", "holdings", "drawdown", "news", "portfolio")
    ):
        return True
    return False


def resolve_deictic_fund_name(
    question: str,
    memory: dict[str, Any] | None,
) -> str:
    from news_rag.insight.memory.fund_context import (
        fund_name_mentioned_in_memory,
        last_fund_name_from_gists,
        memory_known_fund_names,
        primary_fund_name,
        recent_fund_focus_names,
    )

    if not question_refers_deictic_fund(question):
        return ""
    mentioned = fund_name_mentioned_in_memory(question, memory)
    if mentioned:
        return mentioned
    for name in recent_fund_focus_names(memory):
        return name
    name = primary_fund_name(memory)
    if name:
        return name
    gist_name = last_fund_name_from_gists(memory)
    if gist_name:
        return gist_name
    known = {n.lower() for n in memory_known_fund_names(memory)}
    if isinstance(memory, dict):
        stack = memory.get("entity_stack") or []
        for row in stack:
            if isinstance(row, dict) and row.get("name"):
                candidate = str(row["name"]).strip()
                if candidate.lower() in known:
                    return candidate
        if len(stack) == 1 and isinstance(stack[0], dict) and stack[0].get("name"):
            return str(stack[0]["name"]).strip()
    return ""


def reconcile_deictic_planner_fund(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> ExecutionPlan:
    """Deictic follow-ups: bind fund from memory, drop planner-invented catalog names."""
    from news_rag.insight.memory.fund_context import memory_known_fund_names

    if not question_refers_deictic_fund(question):
        return plan
    plan.subject_ref = "memory_primary"
    known = {n.lower(): n for n in memory_known_fund_names(memory)}
    resolved = resolve_deictic_fund_name(question, memory)
    current = str((plan.funds or [""])[0] or "").strip()
    if resolved:
        plan.funds = [resolved]
    elif current and known and current.lower() not in known:
        plan.funds = []
    reading = str(getattr(plan, "planner_reading", "") or "").strip()
    if reading and resolved and resolved.lower() not in reading.lower():
        plan.planner_reading = f"Follow-up on {resolved} already in this chat"
    elif reading and resolved:
        plan.planner_reading = reading
    return plan


def enforce_deictic_and_memory_primary_fund(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> ExecutionPlan:
    """Drop planner-hallucinated funds on 'its' / memory_primary when the name is not in session memory."""
    from news_rag.insight.memory.fund_context import memory_known_fund_names, primary_fund_name

    ref = str(plan.subject_ref or "none").strip().lower()
    deictic = question_refers_deictic_fund(question)
    binds_memory = ref in ("memory_primary", "memory_stack", "list_cursor") or deictic
    if not binds_memory or not memory:
        return plan

    known = {n.lower(): n for n in memory_known_fund_names(memory)}
    current = str((plan.funds or [""])[0] or "").strip()
    if deictic:
        resolved = resolve_deictic_fund_name(question, memory)
        if resolved:
            plan.funds = [resolved]
            plan.subject_ref = "memory_primary"
            return plan
    if current and known and current.lower() not in known:
        replacement = resolve_deictic_fund_name(question, memory) or primary_fund_name(memory)
        if replacement:
            plan.funds = [replacement]
            plan.subject_ref = "memory_primary"
        elif deictic and any(c.tool == "get_fund_data" for c in plan.tool_calls or []):
            plan.funds = []
    elif ref == "memory_primary" and not plan.funds:
        name = primary_fund_name(memory)
        if name:
            plan.funds = [name]
    return plan


def enforce_investor_holding_subject(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> ExecutionPlan:
    """'My contra fund' → Kotak in holdings, not list_cursor catalog names."""
    name = resolve_investor_holding_fund_name(question, memory)
    if not name:
        return plan
    plan.funds = [name]
    if str(plan.portfolio_scope or "").lower().strip() in ("none", "", "catalog"):
        plan.portfolio_scope = "investor"
    note = (
        f"The user means **their holding** {name} in the investor book — not a catalog screen pick "
        "from an earlier compare. Tie news and portfolio data to this scheme only."
    )
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    return plan


def ensure_catalog_tools_for_fund_news(plan: ExecutionPlan) -> ExecutionPlan:
    """News tied to a fund needs that fund's snapshot + portfolio holdings/sectors in wave 1."""
    if not any(c.tool == "search_financial_news" for c in plan.tool_calls or []):
        return plan
    fund = str((plan.funds or [""])[0] or "").strip()
    if not fund:
        return plan

    def _has_fund_modules(*mods: str) -> bool:
        need = {m.lower() for m in mods}
        for call in plan.tool_calls or []:
            if call.tool != "get_fund_data":
                continue
            got = {str(m).lower() for m in (call.arguments or {}).get("modules") or []}
            if need <= got:
                return True
        return False

    def _has_portfolio(*sections: str) -> bool:
        need = {s.lower() for s in sections}
        for call in plan.tool_calls or []:
            if call.tool != "get_portfolio_data":
                continue
            got = {str(s).lower() for s in (call.arguments or {}).get("sections") or []}
            if need <= got:
                return True
        return False

    extra: list[ToolCall] = []
    if not _has_fund_modules("snapshot"):
        extra.append(
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot", "attribution"], "windows": ["1M"]},
                wave=1,
                why=f"Fund metrics for news context on {fund[:48]}",
            )
        )
    if not _has_portfolio("holdings", "sectors"):
        extra.append(
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": ["holdings", "sectors"], "top_n": 8},
                wave=1,
                why=f"Holdings/sectors to link news to {fund[:48]}",
            )
        )
    if extra:
        plan.tool_calls = [*extra, *(plan.tool_calls or [])]
        plan.requires_compose = True
    return plan
