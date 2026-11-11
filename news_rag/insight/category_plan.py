"""Follow-ups about how a fund's category is performing (memory-bound)."""

from __future__ import annotations

from typing import Any

import re

from news_rag.fund_rating_categories import match_all_scheme_categories, match_scheme_category
from news_rag.fund_rupeestop_metrics import asks_category_performance
from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall, Wave2Policy
from news_rag.insight.memory.fund_context import primary_fund_name

_CATEGORY_COMPOSITION_RE = re.compile(
    r"\b(?:"
    r"hold(?:s|ing)?|allocation|composition|invest(?:s|ing)?\s+in|"
    r"market\s+cap|large\s+cap|mid\s+cap|small\s+cap|micro\s+cap|"
    r"sector(?:s)?|holdings?"
    r")\b",
    re.I,
)

_DEICTIC_HOLD_RE = re.compile(
    r"\b(?:this|that|the)\b.{0,32}\b(?:hold|allocation|composition|portfolio)\b|"
    r"\bwhat\s+(?:this|that|it)\b.{0,40}\bholds?\b",
    re.I,
)

_CATEGORY_COMPOSITION_BRIEF: dict[str, str] = {
    "flexi cap": (
        "A **flexi cap** equity fund may invest across **large, mid, and small** cap stocks. "
        "The fund manager chooses the mix over time; there is no fixed percentage in each size bucket "
        "(unlike **multi cap**, which must keep at least 25% in each of large, mid, and small cap). "
        "Flexi cap funds still follow SEBI equity category rules on minimum equity exposure."
    ),
    "multi cap": (
        "A **multi cap** fund invests across large, mid, and small cap companies. "
        "SEBI rules require **at least 25%** of the portfolio in each of large cap, mid cap, and small cap."
    ),
    "large cap": (
        "A **large cap** fund invests mainly in the largest listed companies (large cap stocks)."
    ),
    "mid cap": (
        "A **mid cap** fund invests mainly in mid-sized companies (mid cap stocks)."
    ),
    "small cap": (
        "A **small cap** fund invests mainly in smaller companies (small cap stocks)."
    ),
}


def category_composition_plan_applies(question: str, plan: ExecutionPlan) -> bool:
    """Planner category_composition is valid only for a named SEBI category ask or follow-up."""
    if asks_category_composition(question):
        return True
    cat = str(plan.scheme_category or "").strip()
    if cat and match_scheme_category(cat):
        return True
    return False


def asks_category_composition(question: str) -> bool:
    """What a category holds (cap mix), not a named scheme's stock list."""
    q = question or ""
    match = match_scheme_category(q)
    if not (match and match.locked and match.category):
        return False
    if not _CATEGORY_COMPOSITION_RE.search(q):
        return False
    from news_rag.tools import asks_fund_portfolio_holdings

    if asks_fund_portfolio_holdings(q):
        return False
    return True


def _memory_example_fund(memory: dict[str, Any] | None) -> str:
    return primary_fund_name(memory)


_FUND_HOLD_FOLLOWUP_RE = re.compile(
    r"\b(?:what|tell\s+me|show\s+me)\b.{0,32}\b(?:it|this|that|the\s+fund)\b.{0,40}\bhold(?:s|ing)?\b|"
    r"\bwhat\s+(?:does\s+)?(?:it|this|that)\s+hold\b|"
    r"\b(?:portfolio|allocation|made\s+of)\b",
    re.I,
)


def asks_fund_holdings_followup(question: str) -> bool:
    """Holdings/allocation for the fund in memory (it / this fund), not a category essay."""
    q = question or ""
    if not _FUND_HOLD_FOLLOWUP_RE.search(q):
        return False
    if asks_category_composition(q):
        return False
    return True


def ensure_fund_holdings_followup_plan(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """Fetch asset mix, market cap, sectors, and holdings for the fund the user means."""
    from news_rag.insight.planner_policy import planner_owns

    if planner_owns(plan):
        if str(plan.data_need or "none").lower() != "fund_holdings_breakdown":
            return plan
    elif not asks_fund_holdings_followup(question):
        return plan

    fund = _memory_example_fund(memory) or (str(plan.funds[0]).strip() if plan.funds else "")
    if not fund:
        return plan

    news_calls = [c for c in (plan.tool_calls or []) if c.tool == "search_financial_news"]
    keep_fusion = plan.answer_mode == AnswerMode.INSIGHT_FUSION or bool(news_calls)

    fund_modules = ["risk", "rating", "snapshot"] if keep_fusion else ["risk", "snapshot"]

    plan.funds = [fund]
    if not keep_fusion:
        plan.intent = "lookup"
    plan.tool_calls = [
        ToolCall(
            tool="get_fund_data",
            arguments={"modules": fund_modules},
            wave=1,
        ),
        ToolCall(
            tool="get_portfolio_data",
            arguments={"sections": ["holdings", "sectors"], "top_n": 5},
            wave=1,
        ),
    ]
    if news_calls:
        plan.tool_calls.extend(news_calls)
    plan.answer_mode = (
        AnswerMode.INSIGHT_FUSION if keep_fusion else AnswerMode.DATA_ONLY
    )
    plan.requires_compose = True
    plan.wave_2_policy = Wave2Policy(trigger="none")
    plan.max_words = max(int(plan.max_words or 0), 320)
    note = (
        f"Answer for **{fund}**. Show **asset mix** (equity, cash, etc.) and **market cap mix** "
        "(large, mid, small) from risk data, then **top sectors** and **top holdings** with weights. "
        "State the **sum of the top holdings weights** as a number. Use DISPLAY.composition_table when present."
    )
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    return plan


def ensure_category_composition_plan(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """Explain cap mix for a category and show market-cap weights from a RupeeStop-rated example fund."""
    from news_rag.insight.plan_intent import plan_wants_alternate_in_category, plan_wants_compare_categories
    from news_rag.insight.planner_policy import planner_owns

    if plan_wants_compare_categories(plan) or plan_wants_alternate_in_category(plan):
        return plan
    if planner_owns(plan):
        if str(plan.data_need or "none").lower() != "category_composition":
            return plan
    elif not asks_category_composition(question):
        return plan

    if planner_owns(plan) and plan.scheme_category:
        match = match_scheme_category(plan.scheme_category)
    else:
        match = match_scheme_category(question)
    if not match or not match.category:
        return plan

    brief = _CATEGORY_COMPOSITION_BRIEF.get(match.category, "")
    if brief:
        plan.concept_brief = brief

    plan.intent = "lookup"
    mem_fund = _memory_example_fund(memory) if _DEICTIC_HOLD_RE.search(question or "") else ""
    portfolio_tools = [
        ToolCall(
            tool="get_fund_data",
            arguments={"modules": ["risk", "rating", "snapshot"]},
            wave=1,
        ),
        ToolCall(
            tool="get_portfolio_data",
            arguments={"sections": ["holdings", "sectors"], "top_n": 5},
            wave=1,
        ),
    ]
    if mem_fund:
        plan.funds = [mem_fund]
        plan.tool_calls = portfolio_tools
        note = (
            f"The user means the fund already in context (**{mem_fund}**). "
            "Do not substitute a different fund from an old screen row in memory text. "
            "Show **asset mix**, **market cap %** (large, mid, small), **top sectors with weights**, and **top holdings with weights** "
            "from EVIDENCE. State the **sum of top holdings weights** as a number. "
            "Use DISPLAY.composition_table when present. Briefly note what the category may hold, then this fund's measured mix."
        )
    else:
        plan.funds = []
        plan.tool_calls = [
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"top_n": 1, "rating_screen": True, "focus_question": match.category},
                wave=1,
                why="RupeeStop-rated example in this category.",
            ),
            *portfolio_tools,
        ]
        note = (
            "First explain what this **category** can hold (large / mid / small cap mix) from the concept brief. "
            "Then name the **example fund** from the screen (RupeeStop label and score when present). "
            "Show **market cap allocation %**, **top sectors with weights**, and **top holdings with weights** from EVIDENCE. "
            "Include **asset mix** (equity, cash, etc.) when present. "
            "State the **sum of the top holdings weights** as a number, not a blank. "
            "Use DISPLAY.composition_table when present. Do not say factsheet-only when these figures are in EVIDENCE."
        )
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.requires_compose = True
    plan.wave_2_policy = Wave2Policy(trigger="none")
    plan.max_words = max(int(plan.max_words or 0), 320)
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    return plan


_CROSS_CATEGORY_COMPARE_RE = re.compile(
    r"\bcompare\b|\bcomparison\b|\bvs\.?\b|\bversus\b|\bdifference\s+between\b",
    re.I,
)


def asks_cross_category_compare(question: str) -> bool:
    q = question or ""
    if not _CROSS_CATEGORY_COMPARE_RE.search(q):
        return False
    return len(match_all_scheme_categories(q)) >= 2


def ensure_cross_category_compare_plan(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Two (or more) scheme categories in one compare ask → one rated screen per category."""
    from news_rag.insight.plan_intent import plan_wants_compare_categories

    categories: list[str] = []
    if plan_wants_compare_categories(plan):
        categories = [str(c).strip() for c in (plan.scheme_categories or []) if str(c).strip()]
    if len(categories) < 2 and asks_cross_category_compare(question):
        categories = match_all_scheme_categories(question)
    if len(categories) < 2:
        return plan

    plan.tool_calls = [
        ToolCall(
            tool="screen_funds_by_exposure",
            arguments={
                "sector": "",
                "driver": "",
                "direction": "any",
                "top_n": 1,
                "rating_screen": True,
                "focus_question": category,
            },
            wave=1,
            why=f"RupeeStop-rated example in {category}.",
        )
        for category in categories[:3]
    ]
    plan.funds = []
    plan.intent = "compare"
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.requires_compose = True
    plan.wave_2_policy = Wave2Policy(trigger="none")
    plan.max_words = max(int(plan.max_words or 0), 360)
    labels = ", ".join(categories[:3])
    plan.presentation_notes = (
        f"Compare one example fund per category ({labels}). "
        "Open with one short paragraph on how these categories differ (equity vs debt tilt). "
        "Then one markdown table with both funds: category, RS score and label when present, "
        "risk label, and returns (1M, 1Y, 3Y, 5Y) from EVIDENCE. "
        "Do not say a category is missing when two funds are in the screen rankings."
    )
    return plan


def _memory_return_windows(memory: dict[str, Any] | None) -> list[str]:
    frame = memory.get("frame") if isinstance(memory, dict) and isinstance(memory.get("frame"), dict) else {}
    period = str(frame.get("period") or "").strip().lower()
    if not period:
        return []
    if "1 month" in period or period in {"1m", "1 mo"}:
        return ["1M"]
    if "3 month" in period or period in {"3m"}:
        return ["3M"]
    if "6 month" in period or period in {"6m"}:
        return ["6M"]
    return []


def _primary_fund_from_memory(memory: dict[str, Any] | None) -> str:
    return primary_fund_name(memory)


def ensure_rating_list_funds(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> ExecutionPlan:
    """Follow-up: ratings for funds on the list cursor, not stale memory subjects."""
    from news_rag.insight.plan_intent import plan_wants_fund_compare
    from news_rag.insight.planner_policy import planner_owns

    if plan_wants_fund_compare(plan):
        return plan
    if any(call.tool == "compare_funds" for call in plan.tool_calls or []):
        return plan

    if planner_owns(plan):
        if str(plan.data_need or "none").lower() != "rating_for_screened_list":
            return plan
    elif not re.search(r"\b(?:rupeestop\s+)?ratings?\b|\brs\s+rating\b", question or "", re.I):
        return plan
    cursor = memory.get("list_cursor") if isinstance(memory, dict) else None
    if not isinstance(cursor, dict):
        return plan
    names = [str(row.get("name") or "").strip() for row in (cursor.get("rows") or []) if row.get("name")]
    if not names:
        return plan
    plan.funds = names
    kept = [call for call in plan.tool_calls if call.tool != "get_fund_data"]
    plan.tool_calls = [
        ToolCall(tool="get_fund_data", arguments={"modules": ["rating"]}, wave=1),
        *kept,
    ]
    plan.asked_facts = ["rating"]
    plan.requires_compose = True
    note = (
        "Show each fund's RupeeStop score out of 100, the label (Best in category, Recommended, etc.), "
        "and pillar marks when present. Pair with recent returns from the screen when available."
    )
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    return plan


def _category_from_memory_cursor(memory: dict[str, Any] | None) -> tuple[str, str]:
    cursor = memory.get("list_cursor") if isinstance(memory, dict) else None
    if isinstance(cursor, dict):
        filters = cursor.get("filters") if isinstance(cursor.get("filters"), dict) else {}
        focus = str(filters.get("focus_question") or "")
        m2 = match_scheme_category(focus)
        if m2 and m2.category:
            return m2.category, str(m2.fund_type or "equity")
    return "", ""


def _category_for_alternate_plan(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> tuple[str, str]:
    fund_type, category = resolve_rs_rating_category(
        scheme_category=str(plan.scheme_category or ""),
        question=str(plan.planner_reading or plan.goal or ""),
        memory=memory,
        plan_funds=list(plan.funds or []),
        focus_question=_screen_focus_from_plan(plan),
    )
    if category:
        return category, fund_type
    cat = str(plan.scheme_category or "").strip()
    if cat:
        match = match_scheme_category(cat)
        if match and match.category:
            return match.category, str(match.fund_type or "equity")
        return cat, "equity"
    for call in plan.tool_calls or []:
        if call.tool != "screen_funds_by_exposure":
            continue
        focus = str((call.arguments or {}).get("focus_question") or "").strip()
        match = match_scheme_category(focus)
        if match and match.category:
            return match.category, str(match.fund_type or "equity")
    for text in (plan.planner_reading, plan.goal):
        match = match_scheme_category(text or "")
        if match and match.category:
            return match.category, str(match.fund_type or "equity")
    return _category_from_memory_cursor(memory)


def _screen_focus_from_plan(plan: ExecutionPlan) -> str:
    for call in plan.tool_calls or []:
        if call.tool != "screen_funds_by_exposure":
            continue
        focus = str((call.arguments or {}).get("focus_question") or "").strip()
        if focus:
            return focus
    return ""


def resolve_rs_rating_category(
    *,
    question: str = "",
    scheme_category: str = "",
    focus_question: str = "",
    memory: dict[str, Any] | None = None,
    plan_funds: list[str] | None = None,
) -> tuple[str, str]:
    """Map investor slugs (e.g. contra) to RS-rating API fund_type + category."""
    for raw in (scheme_category, focus_question, question):
        text = str(raw or "").strip()
        if not text:
            continue
        low = text.lower()
        if low in ("contra", "value contra", "value / contra") or (
            "contra" in low and "large" not in low and "mid" not in low
        ):
            return "equity", "value"
        match = match_scheme_category(text)
        if match and match.category:
            return str(match.fund_type or "equity"), match.category

    if isinstance(memory, dict):
        for row in memory.get("holdings_in_chat") or []:
            if not isinstance(row, dict):
                continue
            cat = str(row.get("category") or "").strip().lower()
            if cat == "contra":
                return "equity", "value"
            match = match_scheme_category(cat)
            if match and match.category:
                return str(match.fund_type or "equity"), match.category

    for name in plan_funds or []:
        sc = _fund_scheme_category(str(name))
        if sc == "contra":
            return "equity", "value"
        match = match_scheme_category(sc or str(name))
        if match and match.category:
            return str(match.fund_type or "equity"), match.category
    return "", ""


def _categories_equivalent(left: str, right: str) -> bool:
    a = str(left or "").strip().lower()
    b = str(right or "").strip().lower()
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    contra_value = {"contra", "value", "value / contra", "value contra"}
    return a in contra_value and b in contra_value


def _fund_scheme_category(fund_name: str) -> str:
    name = str(fund_name or "").strip()
    if not name:
        return ""
    from news_rag.fund_search import get_fund_index

    detail, _amb, _close = get_fund_index().lookup_extracted_fund(name=name)
    if not detail:
        return ""
    return str(detail.get("schemeCategory") or detail.get("category") or "").strip().lower()


def _exclude_funds_for_category(
    memory: dict[str, Any] | None,
    category: str,
) -> tuple[list[str], list[str]]:
    """Names and ISINs already discussed in this category (skip when picking 'another' fund)."""
    cat = category.lower().strip()
    if not cat:
        return [], []

    names: list[str] = []
    isins: list[str] = []
    seen_names: set[str] = set()
    seen_isins: set[str] = set()

    def _add(name: str, isin: str = "") -> None:
        n = str(name or "").strip()
        if not n:
            return
        key = n.lower()
        if key in seen_names:
            return
        seen_names.add(key)
        names.append(n)
        raw_isin = str(isin or "").strip().upper()
        if not raw_isin:
            from news_rag.fund_search import get_fund_index

            detail, _a, _c = get_fund_index().lookup_extracted_fund(name=n)
            raw_isin = str((detail or {}).get("isin") or "").strip().upper()
        if raw_isin and raw_isin not in seen_isins:
            seen_isins.add(raw_isin)
            isins.append(raw_isin)

    def _in_category(fund_name: str) -> bool:
        sc = _fund_scheme_category(fund_name)
        if sc:
            return cat in sc or sc == cat
        low = fund_name.lower()
        return cat.replace(" hybrid", "") in low and "hybrid" in low if "hybrid" in cat else cat in low

    sources: list[Any] = []
    if isinstance(memory, dict):
        frame = memory.get("frame") if isinstance(memory.get("frame"), dict) else {}
        sources.extend(frame.get("subjects") or [])
        sources.extend(memory.get("entity_stack") or [])
        cursor = memory.get("list_cursor")
        if isinstance(cursor, dict):
            sources.extend(cursor.get("rows") or [])

    for row in sources:
        if not isinstance(row, dict):
            continue
        fund_name = str(row.get("name") or row.get("fund_name") or "").strip()
        if fund_name and _in_category(fund_name):
            _add(fund_name, str(row.get("id") or row.get("isin") or ""))

    if isinstance(memory, dict):
        cursor = memory.get("list_cursor")
        if isinstance(cursor, dict):
            for row in cursor.get("rows") or []:
                if not isinstance(row, dict):
                    continue
                fund_name = str(row.get("name") or "").strip()
                if fund_name and _in_category(fund_name):
                    _add(fund_name, str(row.get("isin") or row.get("id") or ""))

    if isinstance(memory, dict):
        for row in memory.get("holdings_in_chat") or []:
            if not isinstance(row, dict):
                continue
            row_cat = str(row.get("category") or "").strip().lower()
            if not row_cat or not _categories_equivalent(row_cat, cat):
                continue
            fund_name = str(row.get("name") or "").strip()
            if fund_name:
                _add(fund_name, str(row.get("isin") or ""))

    return names, isins


def _anchor_rating_for_category(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    category: str,
) -> tuple[str, float | None, list[str], list[str]]:
    """Current holding in category (exclude list + anchor label/score for rating picks)."""
    from news_rag.fund_rating_labels import normalize_rs_label

    exclude_names, exclude_isins = _exclude_funds_for_category(memory, category)
    cat = category.lower().strip()
    anchor_label = ""
    anchor_score: float | None = None

    for name in plan.funds or []:
        n = str(name or "").strip()
        if n and n not in exclude_names:
            exclude_names.append(n)

    if isinstance(memory, dict):
        for row in memory.get("holdings_in_chat") or []:
            if not isinstance(row, dict):
                continue
            row_cat = str(row.get("category") or "").strip().lower()
            if not _categories_equivalent(row_cat, cat):
                continue
            anchor_label = normalize_rs_label(str(row.get("rs_label") or ""))
            raw_score = row.get("rs_score")
            if raw_score is not None:
                try:
                    anchor_score = float(raw_score)
                except (TypeError, ValueError):
                    anchor_score = None
            break

    return anchor_label, anchor_score, exclude_names, exclude_isins


def ensure_better_rated_category_fund_plan(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """Better fund in a category — rank by RupeeStop score, not NAV returns."""
    from news_rag.insight.plan_intent import plan_wants_better_rated_in_category

    if not plan_wants_better_rated_in_category(plan, question):
        return plan

    category, _fund_type = _category_for_alternate_plan(plan, memory)
    if not category:
        _fund_type, category = resolve_rs_rating_category(
            question=question,
            memory=memory,
            plan_funds=list(plan.funds or []),
            focus_question=_screen_focus_from_plan(plan),
        )
    if not category:
        return plan

    anchor_label, anchor_score, exclude_names, exclude_isins = _anchor_rating_for_category(
        plan, memory, category
    )
    plan.scheme_category = category
    screen_patch: dict[str, Any] = {
        "rating_screen": True,
        "pick_rating_better": True,
        "pick_alternate": True,
        "focus_question": category,
        "top_n": max(int(getattr(plan, "planner_count", 0) or 0), 1),
        "rating_fetch_n": 20,
        "exclude_names": exclude_names,
        "exclude_isins": exclude_isins,
    }
    if anchor_label:
        screen_patch["anchor_rs_label"] = anchor_label
    if anchor_score is not None:
        screen_patch["anchor_rs_score"] = anchor_score
    screen_patch.pop("rs_label", None)

    patched = False
    for call in plan.tool_calls or []:
        if call.tool != "screen_funds_by_exposure":
            continue
        args = dict(call.arguments or {})
        args.update(screen_patch)
        args.pop("rs_label", None)
        call.arguments = args
        patched = True

    if not patched:
        plan.tool_calls = [
            *([c for c in plan.tool_calls if c.tool != "screen_funds_by_exposure"]),
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={
                    "sector": "",
                    "driver": "",
                    "direction": "any",
                    **screen_patch,
                },
                wave=1,
                why=f"Better RupeeStop-rated fund in {category}, excluding the user's current holding.",
            ),
        ]

    note = (
        f"Recommend a **better** fund in **{category}** using RupeeStop **rs_label and final_score**, "
        "not recent NAV return rank. Exclude the user's current holding. "
        "If no higher-rated name exists, name the **next best by score** and say it may be a lower label tier. "
        "The server loads **compare_funds** for your holding and the picked fund — use aligned returns for both in any table."
    )
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    plan.requires_compose = True
    return plan


def ensure_alternate_category_fund_plan(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """Pick a RupeeStop-rated fund in the category that was not already in this conversation."""
    from news_rag.insight.plan_intent import plan_wants_alternate_in_category, plan_wants_compare_categories

    if not plan_wants_alternate_in_category(plan):
        return plan
    if plan_wants_compare_categories(plan):
        return plan

    category, _fund_type = _category_for_alternate_plan(plan, memory)
    if not category:
        return plan

    exclude_names, exclude_isins = _exclude_funds_for_category(memory, category)
    from news_rag.fund_rating_labels import normalize_rs_label

    rs_label = normalize_rs_label(str(plan.rs_label or "").strip())
    screen_args: dict[str, Any] = {
        "sector": "",
        "driver": "",
        "direction": "any",
        "top_n": 1,
        "rating_screen": True,
        "pick_alternate": True,
        "focus_question": category,
        "exclude_names": exclude_names,
        "exclude_isins": exclude_isins,
        "rating_fetch_n": 15,
    }
    if rs_label:
        screen_args["rs_label"] = rs_label

    plan.tool_calls = [
        ToolCall(
            tool="screen_funds_by_exposure",
            arguments=screen_args,
            wave=1,
            why=f"Another rated fund in {category}, excluding funds already named in this chat.",
        )
    ]
    plan.funds = []
    plan.intent = "lookup"
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.requires_compose = True
    plan.wave_2_policy = Wave2Policy(trigger="none")
    plan.max_words = max(int(plan.max_words or 0), 220)
    skip = ", ".join(exclude_names[:4]) if exclude_names else "none"
    note = (
        f"The user asked for **another** fund in **{category}**, not a repeat. "
        f"Do not name funds already in context ({skip}). "
        "Name the **new** fund from the screen with RupeeStop score and **rs_label** when present. "
        "If ranking_note says a lower label tier was used (e.g. Good Choice when Recommended is exhausted), "
        "say that clearly — same category, different label tier."
    )
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    return plan


def _memory_has_named_funds_for_planner(memory: dict[str, Any] | None) -> bool:
    """When memory already has schemes, the planner decides which funds to compare."""
    if not isinstance(memory, dict) or not memory:
        return False
    if memory.get("category_funds_in_chat"):
        return True
    frame = memory.get("frame") if isinstance(memory.get("frame"), dict) else {}
    if frame.get("subjects"):
        return True
    if memory.get("entity_stack"):
        return True
    return False


def _apply_same_category_pair_screen_plan(
    plan: ExecutionPlan,
    *,
    category: str,
    fund_type: str,
    presentation_note: str,
) -> None:
    plan.scheme_category = category
    plan.funds = []
    plan.data_need = "none"
    plan.intent = "compare"
    plan.tool_calls = [
        ToolCall(
            tool="screen_funds_by_exposure",
            arguments={
                "rating_screen": True,
                "focus_question": category,
                "top_n": 2,
                "compare_pair": True,
                "rating_fetch_n": 20,
            },
            wave=1,
        ),
    ]
    plan.requires_compose = True
    plan.wave_2_policy = Wave2Policy(trigger="none")
    existing = (plan.presentation_notes or "").strip()
    if presentation_note not in existing:
        plan.presentation_notes = f"{existing} {presentation_note}".strip()


def pick_random_scheme_category_for_compare(question: str) -> tuple[str, str]:
    """Pick one scheme category slug; both funds will come from this category."""
    import random

    from news_rag.fund_rating_categories import (
        CATEGORIES,
        RANDOM_EQUITY_COMPARE_CATEGORIES,
        match_scheme_category,
    )

    match = match_scheme_category(question or "")
    if match and match.category and match.locked:
        return str(match.category).strip(), str(match.fund_type or "equity").strip() or "equity"

    q = (question or "").lower()
    fund_type = "debt" if re.search(r"\bdebt\b", q) and not re.search(r"\bequity\b", q) else "equity"
    if fund_type == "equity":
        pool = list(RANDOM_EQUITY_COMPARE_CATEGORIES)
    else:
        pool = list(CATEGORIES.get("debt", ()))
    if not pool:
        return "", fund_type
    category = random.choice(pool)
    return category, fund_type


def plan_wants_random_same_category_pair_compare(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> bool:
    if str(plan.intent or "").strip().lower() != "compare":
        return False
    if _memory_has_named_funds_for_planner(memory):
        return False
    ref = str(plan.subject_ref or "none").strip().lower()
    if ref in {"memory_stack", "memory_primary", "list_cursor"}:
        return False
    from news_rag.insight.plan_intent import plan_wants_compare_categories

    if plan_wants_compare_categories(plan):
        return False
    q = question or ""
    randomish = str(plan.fund_pick or "").strip().lower() == "random_in_category" or bool(
        re.search(r"\brandom\b", q, re.I)
    )
    if not randomish:
        return False
    if not re.search(r"\bcompare\b|\bversus\b|\bvs\.?\b", q, re.I):
        return False
    if not re.search(r"\b(?:two|2|pair|any)\b", q, re.I):
        if int(getattr(plan, "random_fund_count", 0) or 0) < 2:
            return False
    if not re.search(r"\bequity\b|\bdebt\b", q, re.I):
        return False
    match = match_scheme_category(q)
    if match and match.category and match.locked:
        return False
    return True


def ensure_random_same_category_pair_compare_plan(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """Compare two random funds from one equity/debt scheme category (no chat memory)."""
    if not plan_wants_random_same_category_pair_compare(question, plan, memory):
        return plan
    category, fund_type = pick_random_scheme_category_for_compare(question)
    if not category:
        return plan
    note = (
        f"User asked to compare two random {fund_type} funds in the **same** scheme category. "
        f"The server picked **{category}** and will return two rated schemes from that category only "
        "(Best in category, then Recommended, then Good Choice). "
        "Do not invent fund names; use compare_funds output after the screen."
    )
    _apply_same_category_pair_screen_plan(
        plan,
        category=category,
        fund_type=fund_type,
        presentation_note=note,
    )
    return plan


def ensure_unnamed_category_pair_compare_plan(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """Compare two funds in one category (e.g. two large cap) without named schemes."""
    from news_rag.fund_rating_categories import match_scheme_category
    from news_rag.insight.plan_intent import plan_wants_unnamed_category_pair_compare

    if not plan_wants_unnamed_category_pair_compare(question, plan, memory):
        return plan

    match = match_scheme_category(question or "")
    if not match or not match.category:
        return plan
    category = str(match.category).strip()
    fund_type = str(match.fund_type or "equity").strip() or "equity"
    note = (
        f"User asked to compare two {category} funds without naming them. "
        "After the screen returns two schemes, the server runs compare_funds. "
        "Answer with a side-by-side compare using compare output, not one fund only."
    )
    _apply_same_category_pair_screen_plan(
        plan,
        category=category,
        fund_type=fund_type,
        presentation_note=note,
    )
    return plan


def ensure_category_performance_plan(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> ExecutionPlan:
    """Use the fund in memory and category-average returns, not a blind catalog screen."""
    from news_rag.insight.plan_intent import plan_wants_fund_compare
    from news_rag.insight.planner_policy import planner_owns

    if plan_wants_fund_compare(plan):
        return plan
    if any(call.tool == "compare_funds" for call in plan.tool_calls or []):
        return plan

    if planner_owns(plan):
        if str(plan.data_need or "none").lower() != "category_performance":
            return plan
    elif not asks_category_performance(question):
        return plan

    from news_rag.insight.investor_subject import resolve_user_named_fund_in_memory

    fund = resolve_user_named_fund_in_memory(question, memory)
    if not fund and plan.funds:
        fund = str(plan.funds[0]).strip()
    if not fund:
        fund = _primary_fund_from_memory(memory)
    if not fund:
        return plan

    windows = ["1Y", "3Y", "5Y"]
    for extra in _memory_return_windows(memory):
        if extra not in windows:
            windows.insert(0, extra)

    plan.funds = [fund]
    plan.tool_calls = [
        ToolCall(
            tool="get_fund_data",
            arguments={"modules": ["snapshot", "vs_benchmark"], "windows": windows},
            wave=1,
        )
    ]
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.requires_compose = True
    plan.wave_2_policy = Wave2Policy(trigger="none")
    plan.intent = "lookup"
    plan.sub_queries = []
    plan.response_shape = "short_answer"
    plan.max_words = max(int(plan.max_words or 0), 260)
    plan.asked_facts = []
    if not (plan.goal or "").strip():
        plan.goal = "How the fund's category is performing versus this fund"
    note = (
        "The user asked how this fund's category is performing. Name the category from the data. "
        "Compare the fund's returns with the category average for each period shown. "
        "Do not list unrelated funds from other categories."
    )
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    return plan


def ensure_name_fund_type_plan(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """Name one fund in a random scheme category for equity/debt/etc. via RS rating API."""
    from news_rag.fund_rating_screen import fund_naming_clause, fund_type_name_spec

    clause = fund_naming_clause(question) or question
    spec = fund_type_name_spec(clause)
    if spec is None:
        return plan

    q = question or ""
    existing = next((c for c in plan.tool_calls or [] if c.tool == "screen_funds_by_exposure"), None)
    if existing and (existing.arguments or {}).get("rating_screen") and (plan.routed_by or "") == "planner":
        args = dict(existing.arguments or {})
        args["rating_screen"] = True
        args["top_n"] = max(int(spec.count), int(args.get("top_n") or 0))
        args["focus_question"] = clause[:180]
        if spec.suggestion == "period" and spec.return_window:
            args["return_window"] = spec.return_window
        existing.arguments = args
        if re.search(r"\bdifference\b|\bdifferent\b", q, re.I) and re.search(r"\bdebt\b", q, re.I) and re.search(
            r"\bequity\b", q, re.I
        ):
            plan.concept_brief = (
                "**Equity funds** invest mainly in shares of listed companies. Returns follow the stock market; "
                "risk is typically higher and there is no guarantee.\n"
                "**Debt funds** invest mainly in bonds and other fixed-income securities. Returns are usually "
                "more stable than equity, but they are not guaranteed either."
            )
            plan.max_words = max(int(plan.max_words or 0), 320)
            plan.requires_compose = True
        return plan
    sections: list[str] = []
    if re.search(r"\bsector", q, re.I):
        sections.append("sectors")
    if re.search(r"\bholdings?\b|\ballocation\b|\bcomposition\b", q, re.I):
        sections.append("holdings")
    if not sections:
        sections = ["sectors"]

    focus_question = clause[:180]

    plan.funds = []
    plan.subject_ref = "none"
    plan.data_need = "none"
    plan.intent = "lookup"
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.requires_compose = True
    plan.wave_2_policy = Wave2Policy(trigger="none")

    tools: list[ToolCall] = [
        ToolCall(
            tool="screen_funds_by_exposure",
            arguments={
                "rating_screen": True,
                "top_n": max(int(spec.count), int((existing.arguments or {}).get("top_n") if existing else 0) or 0),
                "focus_question": focus_question,
                **(
                    {"return_window": spec.return_window}
                    if spec.suggestion == "period" and spec.return_window
                    else {}
                ),
            },
            wave=1,
            why=f"RS rating pick in {spec.fund_type}/{spec.category}/regular/growth",
        ),
        ToolCall(
            tool="get_fund_data",
            arguments={"modules": ["risk", "snapshot"]},
            wave=1,
        ),
        ToolCall(
            tool="get_portfolio_data",
            arguments={"sections": sections, "top_n": 10 if sections == ["sectors"] else 5},
            wave=1,
        ),
    ]
    plan.tool_calls = tools
    if re.search(r"\bdifference\b|\bdifferent\b", q, re.I) and re.search(
        r"\bdebt\b", q, re.I
    ) and re.search(r"\bequity\b", q, re.I):
        plan.concept_brief = (
            "**Equity funds** invest mainly in shares of listed companies. Returns follow the stock market; "
            "risk is typically higher and there is no guarantee.\n"
            "**Debt funds** invest mainly in bonds and other fixed-income securities. Returns are usually "
            "more stable than equity, but they are not guaranteed either."
        )
        plan.max_words = max(int(plan.max_words or 0), 320)
    note = (
        f"User asked to **name one {spec.fund_type} fund** — use the RS rating screen for category "
        f"**{spec.category}** (regular/growth). Do **not** reuse a fund from earlier chat unless it "
        f"appears in screen rankings. Name the fund from screen output, then show "
        f"{' and '.join(sections)} from portfolio data."
    )
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    return plan
