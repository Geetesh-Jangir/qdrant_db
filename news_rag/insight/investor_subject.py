"""Resolve 'my contra fund' and similar asks to a holding in the investor book — no question regex."""

from __future__ import annotations

import difflib
import re
from typing import Any

from news_rag.insight.contracts import ExecutionPlan, ToolCall


def question_refers_to_investor_holding(question: str) -> bool:
    q = (question or "").strip().lower()
    if q.startswith("my "):
        return True
    return " my " in f" {q} "


def question_asks_current_book_allocation(question: str) -> bool:
    """Category mix the user already holds — not an ideal portfolio screen."""
    from news_rag.insight.investor_drawback import question_signals_investor_book

    if not question_signals_investor_book(question):
        return False
    q = (question or "").lower()
    if not re.search(
        r"\ballocations?\b|\bcategory\s+mix\b|\basset\s+mix\b|\bhow\s+(?:is|am)\s+i\s+allocated\b",
        q,
        re.I,
    ):
        return False
    if re.search(
        r"\b(?:ideal|recommend|suggest|should\s+i|what\s+should|how\s+should|"
        r"\d+\s*years?\b|year\s+horizon|stay\s+invested|for\s+\d+\s*years?)\b",
        q,
        re.I,
    ):
        return False
    return True


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
        "gold",
        "silver",
        "liquid",
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


def resolve_investor_holding_by_amc_token(
    question: str,
    memory: dict[str, Any] | None,
    *,
    holdings: list[dict[str, Any]] | None = None,
) -> str:
    """'My quant fund' → Quant Small Cap in holdings when category slug does not match."""
    if not question_refers_to_investor_holding(question):
        return ""
    from news_rag.insight.brief import _amc_token_set

    q_tokens = set(re.findall(r"[a-z0-9]+", (question or "").lower()))
    amc_hits = [t for t in q_tokens if t in _amc_token_set()]
    if not amc_hits:
        return ""

    rows: list[dict[str, Any]] = list(holdings or [])
    if not rows and isinstance(memory, dict):
        for row in memory.get("holdings_in_chat") or []:
            if isinstance(row, dict):
                rows.append(row)
        frame = memory.get("frame") if isinstance(memory.get("frame"), dict) else {}
        for row in frame.get("investor_subjects") or []:
            if isinstance(row, dict):
                rows.append(row)

    matches: list[str] = []
    for row in rows:
        name = str(row.get("scheme_name") or row.get("name") or "").strip()
        if not name:
            continue
        lowered = name.lower()
        if not any(re.search(rf"\b{re.escape(amc)}\b", lowered) for amc in amc_hits):
            continue
        matches.append(name)
    unique = list(dict.fromkeys(matches))
    if len(unique) == 1:
        return unique[0]
    if len(unique) > 1:
        from news_rag.fund_scheme_match import pick_best_matching_scheme

        picked = pick_best_matching_scheme(question, unique)
        if picked:
            return picked
    return ""


def resolve_investor_holding_fund_name(
    question: str,
    memory: dict[str, Any] | None,
) -> str:
    if not question_refers_to_investor_holding(question):
        return ""
    cat = _category_slug_from_question(question)
    if cat:
        row = investor_holding_for_category(memory, cat)
        if row:
            return str(row.get("name") or "").strip()
    return resolve_investor_holding_by_amc_token(question, memory)


def resolve_category_holding_fund_name(
    question: str,
    memory: dict[str, Any] | None,
) -> str:
    """'the contra fund' / manager of contra — category in text, no 'my'."""
    cat = _category_slug_from_question(question)
    if not cat:
        return ""
    row = investor_holding_for_category(memory, cat)
    if row:
        return str(row.get("name") or "").strip()
    return ""


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
    book_phrases = (
        "my portfolio",
        "whole portfolio",
        "entire portfolio",
        "all my funds",
        "my all funds",
        "all of my funds",
        "each of my funds",
        "every fund i own",
        "all my holdings",
        "my holdings",
        "my mutual funds",
        "my mutual fund portfolio",
        "portfolio allocation",
        "my portfolio allocation",
    )
    has_book_phrase = any(p in q for p in book_phrases)
    portfolio_health = "portfolio" in q and re.search(r"\bhealth\s+check\b", q)
    portfolio_about = (
        "portfolio" in q
        and not question_refers_deictic_fund(question)
        and (
            question_refers_to_investor_holding(question)
            or "about" in q
            or "tell me" in q
            or portfolio_health
        )
    )
    if portfolio_health and not _category_slug_from_question(question):
        return True
    if plan is not None:
        need = str(plan.data_need or "").lower().strip()
        if need == "investor_summary":
            return True
        asked = {str(x).lower() for x in (plan.asked_facts or [])}
        per_fund_metrics = {
            "rs_rating",
            "nav",
            "aum",
            "expense",
            "returns",
            "managers",
            "fund_manager",
            "exit_load",
            "benchmark",
            "inception",
            "risk",
            "drawdown",
        }
        has_return_window = any(x.startswith("return:") for x in asked)
        if (asked & per_fund_metrics or has_return_window) and any(
            c.tool == "get_fund_data" for c in plan.tool_calls or []
        ):
            return False
        if str(plan.holding_scope or "") == "all_holdings" and any(
            c.tool == "get_fund_data" for c in plan.tool_calls or []
        ):
            intent = str(plan.intent or "").lower().strip()
            scope = str(plan.portfolio_scope or "").lower().strip()
            if not (
                intent == "overview"
                and scope in ("investor", "both")
                and (has_book_phrase or portfolio_about or portfolio_health)
            ):
                return False
        intent = str(plan.intent or "").lower().strip()
        scope = str(plan.portfolio_scope or "").lower().strip()
        if intent == "overview" and scope in ("investor", "both") and not (plan.funds or []):
            return True
    if has_book_phrase:
        return True
    if portfolio_about:
        return True
    return False


def question_wants_scheme_names(question: str, plan: ExecutionPlan | None = None) -> bool:
    """Scheme names only when the user asked for a fund or a holdings list."""
    if plan is not None and (plan.funds or []):
        return True
    if question_asks_all_schemes_in_answer(question, plan):
        return True
    q = (question or "").lower()
    markers = (
        "holding",
        "which fund",
        "which scheme",
        "what fund",
        "what scheme",
        "list my",
        "name the fund",
        "name my fund",
        "top fund",
        "largest holding",
        "my schemes",
        "my funds",
        "scheme name",
    )
    return any(marker in q for marker in markers)


def question_asks_all_schemes_in_answer(question: str, plan: ExecutionPlan | None = None) -> bool:
    """User wants every scheme listed — not the default top-8 table."""
    del plan
    q = (question or "").lower()
    phrases = (
        "all my funds",
        "all of my funds",
        "every fund i own",
        "each of my funds",
        "all my holdings",
        "all schemes",
        "every scheme",
        "list all my",
        "all funds",
    )
    return any(p in q for p in phrases)


def resolve_investor_holding_from_holdings_rows(
    question: str,
    holdings: list[dict[str, Any]] | None,
) -> str:
    """After get_investor_portfolio when memory was empty at plan time."""
    if not question_refers_to_investor_holding(question):
        return ""
    cat = _category_slug_from_question(question)
    if cat:
        from news_rag.insight.category_plan import _categories_equivalent

        for row in holdings or []:
            if not isinstance(row, dict):
                continue
            row_cat = str(row.get("scheme_category") or row.get("category") or "").strip().lower()
            if _categories_equivalent(row_cat, cat):
                return str(row.get("scheme_name") or row.get("name") or "").strip()
    return resolve_investor_holding_by_amc_token(question, None, holdings=holdings)


def apply_investor_category_fund_to_plan(
    plan: ExecutionPlan,
    question: str,
    memory: dict[str, Any] | None,
    wave1_results: list[dict[str, Any]] | None = None,
) -> ExecutionPlan:
    name = resolve_investor_holding_fund_name(question, memory)
    if not name:
        name = resolve_investor_holding_by_amc_token(question, memory)
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


def question_wants_invested_value_table(question: str) -> bool:
    """Per-scheme invested amount and current market value (not category totals)."""
    q = (question or "").lower()
    if not re.search(r"\b(?:invested|investment|how much)\b", q):
        return False
    if not re.search(
        r"\b(?:current value|market value|worth now|value of each|each of them|"
        r"every scheme|all of them|all of my|each scheme|them now)\b",
        q,
    ):
        return False
    if re.search(r"\b(?:by|per|each|every)\s+categor|\bcategor(?:y|ies)\b", q) and "scheme" not in q:
        return False
    if re.search(r"\b(?:i have|i've|in all|my portfolio|my funds|my schemes)\b", q):
        return True
    return question_refers_to_investor_holding(question)


def question_asks_category_money(question: str) -> bool:
    """Invested amount or share by category, including one category such as gold."""
    q = (question or "").lower()
    if re.search(r"\b(?:this|that|the|my)\s+fund\b", q):
        return False
    if re.search(r"\b(?:nav|xirr|expense|manager|sip)\b", q) and "categor" not in q:
        return False
    if not re.search(r"\b(?:invested|investment|how much|allocations?)\b", q):
        return False
    if re.search(r"\b(?:each|every|all|per|by)\s+categor|\bcategor(?:y|ies)\b", q):
        return True
    if any(f"invested in {label}" in q for label in ("equity", "debt", "hybrid")):
        return True
    return bool(_category_slug_from_question(question))


def _scheme_type_slug_from_question(question: str) -> str:
    """Book-level equity/debt/hybrid money ask (scheme type, not SEBI category)."""
    q = (question or "").lower()
    if "invested" not in q and "investment" not in q and "how much" not in q and "money" not in q:
        return ""
    for label in ("equity", "debt", "hybrid"):
        if label in q:
            return label
    return ""


def question_asks_category_book_share(question: str) -> bool:
    """How much of the whole book sits in a category — not 'my large cap fund' NAV."""
    q = (question or "").lower()
    if not _category_slug_from_question(question):
        return False
    money = any(w in q for w in ("how much", "money", "invested", "investment", "allocation", "share of"))
    book = "portfolio" in q or " my " in f" {q} " or "book" in q
    one_scheme = any(w in q for w in (" my fund", "that fund", "this fund", "the fund"))
    return money and book and not one_scheme


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
    if question_asks_category_money(question):
        plan.portfolio_scope = "investor"
        plan.holding_scope = "all_holdings"
        plan.funds = []
        plan.data_need = "investor_summary"
        plan.tool_calls = [c for c in (plan.tool_calls or []) if c.tool != "get_fund_data"]
        args = {
            "modules": ["summary", "allocation", "holdings"],
            "include_meta": True,
            "holdings_fields": "standard",
            "top_n": 20,
            "sort_by": "aum",
        }
        investor_calls = [c for c in plan.tool_calls if c.tool == "get_investor_portfolio"]
        if investor_calls:
            investor_calls[0].arguments = args
            investor_calls[0].why = f"Full book allocation so {cat} is a share of the portfolio, not 100% of a filtered list"
            investor_calls[0].arguments.pop("scheme_filter", None)
        else:
            plan.tool_calls = [
                ToolCall(
                    tool="get_investor_portfolio",
                    arguments=args,
                    wave=1,
                    why=f"Full book allocation so {cat} is a share of the portfolio",
                ),
                *plan.tool_calls,
            ]
        label = cat or "each category"
        note = (
            f"Category share of the whole book for {label}. "
            "Use allocation.investedByCategory and aumByCategory versus the portfolio total. "
            "Show invested amount and current value. Drop categories with no money invested. "
            "Do not say the category is 100% of the book just because one scheme is listed."
        )
        plan.presentation_notes = f"{plan.presentation_notes} {note}".strip()
        plan.requires_compose = True
        return plan
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


def _plan_wants_manager_roster(plan: ExecutionPlan) -> bool:
    roster_facts = {"managers", "manager", "fund_manager", "manager_tenure", "past_managers"}
    asked = {str(f).lower() for f in (plan.asked_facts or []) if str(f).strip()}
    if asked & roster_facts:
        return True
    for call in plan.tool_calls or []:
        if call.tool != "get_fund_data":
            continue
        mods = {str(m).lower() for m in (call.arguments or {}).get("modules") or []}
        if "managers" in mods:
            return True
    return False


def _question_wants_all_fund_managers(question: str) -> bool:
    q = (question or "").lower()
    return bool(
        re.search(
            r"\b(?:each|every|all)\s+(?:my\s+)?(?:funds?|holdings?|schemes?).*\bmanag",
            q,
        )
    ) or bool(re.search(r"\bmanagers?\s+(?:of|for)\s+(?:each|every|all)\b", q))


def ensure_manager_fund_scope(
    plan: ExecutionPlan,
    question: str,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """One scheme's managers — not fan-out on every holding when user meant contra / a named fund."""
    if not _plan_wants_manager_roster(plan):
        return plan
    if _question_wants_all_fund_managers(question):
        return plan
    funds = [str(f).strip() for f in (plan.funds or []) if str(f).strip()]
    if len(funds) == 1 and user_explicitly_named_scheme(question, funds[0]):
        plan.holding_scope = "single"
        return plan

    name = resolve_user_named_fund_in_memory(question, memory)
    if not name and len(funds) == 1:
        name = funds[0]
    if not name:
        from news_rag.fund_search import resolve_fund_from_question

        detail, amb, _close = resolve_fund_from_question(question)
        if detail and not amb:
            candidate = str(
                detail.get("scheme_name") or detail.get("fund_name") or detail.get("name") or ""
            ).strip()
            if candidate and user_explicitly_named_scheme(question, candidate):
                name = candidate
    if not name:
        name = resolve_category_holding_fund_name(question, memory)
    if not name and isinstance(memory, dict):
        frame = memory.get("frame") if isinstance(memory.get("frame"), dict) else {}
        focus = str(frame.get("last_fund_focus") or "").strip()
        cat = _category_slug_from_question(question)
        if focus and cat and re.search(rf"\b{re.escape(cat.split()[0])}\b", (question or "").lower()):
            name = focus

    if name:
        plan.funds = [name]
        plan.holding_scope = "single"
        if str(plan.data_need or "").lower().strip() in ("none", ""):
            plan.data_need = "investor_holding"
        scope = str(plan.portfolio_scope or "").lower().strip()
        if scope in ("none", "", "catalog"):
            plan.portfolio_scope = "both"
    return plan


def ensure_my_holding_fund_scope(
    plan: ExecutionPlan,
    question: str,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """Bind 'my quant fund' to holdings_in_chat and set portfolio_scope before catalog fan-out."""
    if not question_refers_to_investor_holding(question):
        return plan
    if question_asks_whole_investor_portfolio(question, plan):
        return plan
    if not any(c.tool in ("get_fund_data", "get_portfolio_data") for c in plan.tool_calls or []):
        return plan
    name = resolve_investor_holding_fund_name(question, memory)
    if not name and (plan.funds or []):
        from news_rag.insight.memory.fund_context import isin_for_owned_holding

        for raw in plan.funds:
            if isin_for_owned_holding(memory, str(raw)):
                name = str(raw).strip()
                break
    if name:
        plan.funds = [name]
    scope = str(plan.portfolio_scope or "").lower().strip()
    if scope in ("none", "", "catalog"):
        plan.portfolio_scope = "both"
    plan.holding_scope = "single"
    plan.requires_compose = True
    return plan


def ensure_all_holdings_metrics_plan(
    plan: ExecutionPlan,
    question: str,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """Returns for all my funds: one get_investor_portfolio with windows when possible."""
    if not question_asks_whole_investor_portfolio(question, plan):
        return plan
    if not any(c.tool in ("get_fund_data", "get_portfolio_data", "compare_funds") for c in plan.tool_calls or []):
        return plan
    from news_rag.config import get_settings
    from news_rag.insight.memory.fund_context import owned_holding_names
    from news_rag.insight.return_windows import normalize_window_code

    if not get_settings().portfolio_enabled:
        return plan
    plan.holding_scope = "all_holdings"
    plan.portfolio_scope = "both"

    windows: list[str] = []
    label = str(getattr(plan, "window_label", "") or "").strip().upper()
    if label:
        code = normalize_window_code(label)
        if code:
            windows.append(code)
    for call in plan.tool_calls or []:
        if call.tool != "get_fund_data":
            continue
        for raw in (call.arguments or {}).get("windows") or []:
            code = normalize_window_code(str(raw))
            if code and code not in windows:
                windows.append(code)

    investor_calls = [c for c in plan.tool_calls or [] if c.tool == "get_investor_portfolio"]
    if not investor_calls:
        inv_args: dict[str, Any] = {
            "modules": ["holdings"],
            "include_meta": True,
            "holdings_fields": "standard",
            "top_n": 20,
            "sort_by": "aum",
        }
        if windows:
            inv_args["windows"] = windows[:8]
        plan.tool_calls = [
            ToolCall(
                tool="get_investor_portfolio",
                arguments=inv_args,
                wave=1,
                why="Load book and catalog returns for all holdings in one call",
            ),
            *(plan.tool_calls or []),
        ]
    elif windows:
        for call in plan.tool_calls or []:
            if call.tool == "get_investor_portfolio":
                call.arguments = {**(call.arguments or {}), "windows": windows[:8]}

    if windows:
        plan.tool_calls = [
            c
            for c in (plan.tool_calls or [])
            if not (
                c.tool == "get_fund_data"
                and set((c.arguments or {}).get("modules") or []) <= {"snapshot"}
            )
        ]
        plan.funds = []
    else:
        names = owned_holding_names(memory)
        if names:
            plan.funds = names
    plan.requires_compose = True
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
    if question_asks_catalog_fund_list(question, plan):
        return ""
    if question_asks_whole_investor_portfolio(question, plan):
        return ""
    from news_rag.insight.brief import question_is_standalone_macro

    if question_is_standalone_macro(question):
        return ""

    explicit = resolve_user_named_fund_in_memory(question, memory)
    if explicit:
        return explicit

    funds = [str(f).strip() for f in (plan.funds or []) if str(f).strip()]
    for name in funds:
        if user_explicitly_named_scheme(question, name):
            return name
    if len(funds) == 1:
        return funds[0]
    if len(funds) > 1:
        return ""

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
    from news_rag.insight.investor_drawback import question_asks_portfolio_level_drawdown

    if question_asks_portfolio_level_drawdown(question, plan):
        return ""
    if question_refers_deictic_fund(question) and question_asks_fund_measured_return(question):
        return ""
    if len(holdings) == 1:
        row = holdings[0]
        if isinstance(row, dict):
            return str(row.get("scheme_name") or row.get("name") or "").strip()
    return ""


def _heading_matches_scheme(heading: str, scheme: str) -> bool:
    h = (heading or "").strip().lower()
    s = (scheme or "").strip().lower()
    if not h or not s:
        return False
    return h == s or h in s or s in h


def fix_unasked_scheme_opening_heading(
    text: str,
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
) -> str:
    """Do not lead with a scheme the user did not ask about."""
    lines = (text or "").splitlines()
    if not lines:
        return text or ""
    m = re.match(r"^##\s+(.+?)\s*$", lines[0].strip())
    if not m:
        return text
    heading = m.group(1).strip()
    if "your portfolio" in heading.lower():
        return text

    subject = resolve_answer_subject(question, plan, memory)
    if subject and _heading_matches_scheme(heading, subject):
        return text

    funds = [str(f).strip() for f in (plan.funds or []) if str(f).strip()]
    if not any(_heading_matches_scheme(heading, f) for f in funds):
        return text

    if any(user_explicitly_named_scheme(question, f) and _heading_matches_scheme(heading, f) for f in funds):
        return text

    if question_asks_whole_investor_portfolio(question, plan):
        lines[0] = "## Your portfolio"
        return "\n".join(lines)

    if len(funds) > 1:
        return "\n".join(lines[1:]).lstrip()
    return text


def ensure_portfolio_opening_heading(text: str, question: str, plan: ExecutionPlan) -> str:
    body = (text or "").strip()
    if not body or not question_asks_whole_investor_portfolio(question, plan):
        return text
    if body.startswith("##"):
        return text
    return f"## Your portfolio\n\n{body}"


def question_refers_deictic_fund(question: str) -> bool:
    """Follow-ups like 'do its risk analysis' — pronoun refers to a fund already in chat."""
    stripped = (question or "").strip().lower()
    if stripped.startswith(("its ", "it ")):
        return True
    q = f" {stripped} "
    if any(p in q for p in (" this fund", " that fund", " this scheme", " that scheme")):
        return True
    if re.search(
        r"\bits\s+(?:risk|returns?|nav|rating|holdings?|drawdown|news|portfolio|"
        r"allocation|performance|aum|expense|benchmark|category|sectors?)\b",
        q,
    ):
        return True
    if re.search(
        r"\bis it a(?:n| the|\s+(?:bad|good|right|wrong|safe|worth|better|worse|time)\b)",
        q,
    ):
        return False
    if re.search(
        r"\b(?:some|any|many|top|best|few)\s+it\b|\bit\s+(?:sector|stocks?|companies|industry|services|focused)\b",
        q,
    ):
        return False
    if " it " in q and any(
        w in q for w in ("risk", "return", "nav", "rating", "holdings", "drawdown", "news", "portfolio")
    ):
        return True
    return False


def resolve_user_named_fund_in_memory(question: str, memory: dict[str, Any] | None) -> str:
    """Best-matching session fund whose tokens the user actually wrote (not longest AMC-only hit)."""
    from news_rag.fund_scheme_match import pick_best_matching_scheme
    from news_rag.insight.memory.fund_context import memory_known_fund_names

    text = str(question or "").strip()
    if not text:
        return ""
    return pick_best_matching_scheme(text, list(memory_known_fund_names(memory)))


def resolve_deictic_fund_name(
    question: str,
    memory: dict[str, Any] | None,
) -> str:
    from news_rag.insight.memory.fund_context import (
        deictic_fund_context_active,
        fund_name_mentioned_in_memory,
        last_fund_name_from_gists,
        memory_known_fund_names,
        primary_fund_name,
        recent_fund_focus_names,
    )

    if not question_refers_deictic_fund(question):
        return ""
    if not deictic_fund_context_active(memory):
        return ""
    if isinstance(memory, dict):
        frame = memory.get("frame")
        if isinstance(frame, dict):
            focus = str(frame.get("last_fund_focus") or "").strip()
            if focus:
                return focus
    mentioned = fund_name_mentioned_in_memory(question, memory)
    if mentioned:
        return mentioned
    for name in recent_fund_focus_names(memory):
        return name
    gist_name = last_fund_name_from_gists(memory)
    if gist_name:
        return gist_name
    known_list = memory_known_fund_names(memory)
    known = {n.lower() for n in known_list}
    if len(known_list) == 1:
        return known_list[0]
    focused = primary_fund_name(memory)
    if focused and len(known_list) <= 1:
        return focused
    if isinstance(memory, dict):
        stack = memory.get("entity_stack") or []
        for row in reversed(stack):
            if isinstance(row, dict) and row.get("name"):
                candidate = str(row["name"]).strip()
                if candidate.lower() in known:
                    return candidate
        if len(stack) == 1 and isinstance(stack[0], dict) and stack[0].get("name"):
            return str(stack[0]["name"]).strip()
    from news_rag.insight.memory.fund_context import _frame_subjects

    subjects = _frame_subjects(memory)
    if len(subjects) == 1 and subjects[0].get("name"):
        candidate = str(subjects[0]["name"]).strip()
        if candidate.lower() in known:
            return candidate
    return ""


def question_asks_fund_measured_return(question: str) -> bool:
    """User wants a catalog/measured return for a period (1M, 1W, …), not whole-book P&L."""
    q = (question or "").lower()
    from news_rag.tools import explicit_return_window

    if explicit_return_window(question or ""):
        return True
    if re.search(r"\b(?:last|past|this|one|recent)\s+(?:day|week|month|year)s?\b", q):
        return True
    if re.search(r"\b\d+\s*(?:day|week|month|year)s?\b", q):
        return True
    if re.search(
        r"\b(change|changes|return|returns|performance|nav|gain|loss|move|moved|doing)\b",
        q,
    ) and re.search(r"\b(?:month|week|year|day|1m|1w|1y)\b", q):
        return True
    return False


def question_asks_catalog_fund_list(question: str, plan: ExecutionPlan) -> bool:
    """Sector/theme fund screen listing several schemes — not a single-fund memory follow-up."""
    if question_refers_deictic_fund(question):
        return False
    if resolve_user_named_fund_in_memory(question, None):
        return False
    has_screen = any(c.tool == "screen_funds_by_exposure" for c in (plan.tool_calls or []))
    if not has_screen:
        return False
    q = (question or "").lower()
    from news_rag.tools import explicit_fund_count

    count = explicit_fund_count(question or "")
    if count and count >= 2:
        return True
    if int(plan.planner_count or 0) >= 2:
        return True
    if str(plan.intent or "").lower() == "rank" and re.search(r"\bfunds?\b", q):
        return True
    if re.search(
        r"\bsome\b|\ba few\b|\bwhich funds\b|\blist\b|\btell me .{0,24} funds\b|\bfunds .{0,20} returns\b",
        q,
    ):
        return True
    for call in plan.tool_calls or []:
        if call.tool == "screen_funds_by_exposure" and int((call.arguments or {}).get("top_n") or 0) >= 2:
            return True
    return False


def enforce_catalog_fund_list_scope(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> ExecutionPlan:
    """Keep catalog screens off chat memory / list_cursor fund bindings."""
    del memory
    if not question_asks_catalog_fund_list(question, plan):
        return plan
    plan.funds = []
    plan.subject_ref = "none"
    plan.holding_scope = "none"
    if str(plan.portfolio_scope or "").lower() in ("investor", "both"):
        plan.portfolio_scope = "none"
    plan.tool_calls = [c for c in (plan.tool_calls or []) if c.tool != "get_fund_data"]
    return plan


def plan_targets_single_fund_measured_return(plan: ExecutionPlan, question: str = "") -> bool:
    del question
    if len(plan.funds or []) != 1:
        return False
    return any(call.tool == "get_fund_data" for call in plan.tool_calls or [])


def ensure_deictic_fund_period_return_plan(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> ExecutionPlan:
    """Deictic / memory_primary + measured return → get_fund_data snapshot, not investor_pnl only."""
    if str(plan.holding_scope or "").strip().lower() == "all_holdings":
        return plan
    if question_asks_whole_investor_portfolio(question, plan):
        return plan
    if question_asks_catalog_fund_list(question, plan):
        return plan
    if not question_asks_fund_measured_return(question):
        return plan

    ref = str(plan.subject_ref or "none").strip().lower()
    deictic = question_refers_deictic_fund(question)
    binds_memory = deictic or ref in ("memory_primary", "memory_stack", "list_cursor")
    fund = str((plan.funds or [""])[0] or "").strip()
    if not fund and binds_memory:
        fund = resolve_deictic_fund_name(question, memory)
    if not fund and binds_memory and memory:
        from news_rag.insight.memory.fund_context import primary_fund_name

        fund = primary_fund_name(memory)
    if not fund:
        return plan

    from news_rag.insight.plan_catalog_bind import _window_codes_from_plan

    windows = _window_codes_from_plan(plan)
    if not windows:
        from news_rag.insight.return_windows import window_to_days

        days = int(plan.window_days or 0)
        from news_rag.insight.plan_catalog_bind import _DAYS_TO_WINDOW

        code = _DAYS_TO_WINDOW.get(days)
        windows = [code] if code else []
    window = windows[0] if windows else "1M"
    window_days = int(plan.window_days or 0) or 30
    from news_rag.insight.return_windows import window_to_days

    window_days = window_to_days(window) or window_days

    plan.funds = [fund]
    plan.holding_scope = "single"
    plan.subject_ref = "memory_primary"
    plan.data_need = "none"
    plan.portfolio_scope = "catalog"
    plan.window_days = window_days
    if not str(plan.window_label or "").strip():
        from news_rag.insight.return_windows import window_label as _window_label

        plan.window_label = _window_label(window)

    plan.tool_calls = [c for c in plan.tool_calls if c.tool != "get_investor_portfolio"]

    args = {
        "modules": ["snapshot"],
        "windows": [window],
        "window_days": window_days,
    }
    merged = False
    for call in plan.tool_calls:
        if call.tool != "get_fund_data":
            continue
        existing = dict(call.arguments or {})
        modules = list(existing.get("modules") or [])
        if "snapshot" not in modules:
            modules.insert(0, "snapshot")
        windows = list(existing.get("windows") or [])
        if window not in windows:
            windows = [window]
        call.arguments = {**existing, "modules": modules, "windows": windows, "window_days": window_days}
        merged = True
        break
    if not merged:
        plan.tool_calls = [
            ToolCall(
                tool="get_fund_data",
                arguments=args,
                wave=1,
                why="Measured return for fund in chat memory for the asked window",
            ),
            *plan.tool_calls,
        ]
    plan.requires_compose = True
    return plan


def _amc_token_in_question(token: str, amc_tokens: set[str]) -> str:
    from news_rag.fund_scheme_match import amc_token_in_question

    return amc_token_in_question(token, amc_tokens)


def user_explicitly_named_scheme(question: str, fund_name: str) -> bool:
    """True only when the user text actually names this scheme — not a token like 'minimum' alone."""
    from news_rag.fund_scheme_match import user_text_names_scheme

    return user_text_names_scheme(question, fund_name)


def reconcile_planner_invented_fund_name(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> ExecutionPlan:
    """Follow-ups with no new scheme in the question — keep last_fund_focus, not planner word-match."""
    from news_rag.insight.brief import question_is_standalone_macro
    from news_rag.insight.memory.fund_context import memory_known_fund_names, primary_fund_name

    if question_is_standalone_macro(question):
        plan.funds = []
        plan.subject_ref = "none"
        return plan

    if not plan.funds:
        return plan
    if not memory:
        current = str((plan.funds or [""])[0] or "").strip()
        if current and not user_explicitly_named_scheme(question, current):
            plan.funds = []
        return plan
    pick = str(plan.fund_pick or "none").strip().lower()
    if pick not in ("none", "", "single"):
        return plan
    if str(plan.portfolio_scope or "").lower().strip() in ("investor", "both"):
        if question_refers_to_investor_holding(question):
            return plan
    ref = str(plan.subject_ref or "none").strip().lower()
    if ref in ("memory_stack", "list_cursor"):
        return plan
    if len(plan.funds or []) > 1:
        return plan

    current = str((plan.funds or [""])[0] or "").strip()
    if not current:
        return plan
    known = {n.lower() for n in memory_known_fund_names(memory)}
    if current.lower() in known:
        return plan
    if user_explicitly_named_scheme(question, current):
        return plan

    focus = primary_fund_name(memory)
    if not focus:
        return plan
    plan.funds = [focus]
    plan.subject_ref = "memory_primary"
    reading = str(getattr(plan, "planner_reading", "") or "").strip()
    if reading and focus.lower() not in reading.lower():
        plan.planner_reading = f"Follow-up on {focus} already in this chat"
    return plan


def reconcile_deictic_planner_fund(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> ExecutionPlan:
    """Deictic follow-ups: bind fund from memory, drop planner-invented catalog names."""
    from news_rag.insight.memory.fund_context import memory_known_fund_names

    explicit = resolve_user_named_fund_in_memory(question, memory)
    if explicit:
        plan.funds = [explicit]
        plan.subject_ref = "user_named"
        return plan

    if not question_refers_deictic_fund(question):
        return plan
    from news_rag.insight.memory.fund_context import deictic_fund_context_active, memory_known_fund_names

    if not deictic_fund_context_active(memory):
        current = str((plan.funds or [""])[0] or "").strip()
        if current and not user_explicitly_named_scheme(question, current):
            plan.funds = []
        plan.subject_ref = "memory_primary"
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
    from news_rag.fund_rating_screen import fund_type_name_spec
    from news_rag.insight.memory.fund_context import (
        deictic_fund_context_active,
        memory_known_fund_names,
        primary_fund_name,
    )

    if fund_type_name_spec(question):
        plan.funds = []
        plan.subject_ref = "none"
        return plan

    from news_rag.insight.memory.fund_context import question_asks_compare_both_in_chat
    from news_rag.insight.plan_intent import plan_wants_fund_compare

    if (
        plan_wants_fund_compare(plan)
        and question_asks_compare_both_in_chat(question)
        and len([f for f in (plan.funds or []) if str(f).strip()]) >= 2
    ):
        return plan

    ref = str(plan.subject_ref or "none").strip().lower()
    deictic = question_refers_deictic_fund(question)
    binds_memory = ref in ("memory_primary", "memory_stack", "list_cursor") or deictic
    if not binds_memory or not memory:
        return plan

    explicit = resolve_user_named_fund_in_memory(question, memory)
    if explicit:
        plan.funds = [explicit]
        plan.subject_ref = "user_named"
        return plan

    if deictic:
        focus = str((memory.get("frame") or {}).get("last_fund_focus") or "").strip()
        if focus and deictic_fund_context_active(memory):
            plan.funds = [focus]
            plan.subject_ref = "memory_primary"
            return plan
        if not deictic_fund_context_active(memory):
            current = str((plan.funds or [""])[0] or "").strip()
            if current and not user_explicitly_named_scheme(question, current):
                plan.funds = []
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
        name = resolve_deictic_fund_name(question, memory)
        if not name and not deictic:
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


def ensure_catalog_tools_for_fund_news(
    plan: ExecutionPlan,
    question: str = "",
) -> ExecutionPlan:
    """News tied to a fund needs that fund's snapshot + portfolio holdings/sectors in wave 1."""
    from news_rag.insight.brief import question_is_standalone_macro

    if question_is_standalone_macro(question):
        return plan
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
