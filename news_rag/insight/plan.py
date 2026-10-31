"""The planner: ONE structured LLM call that reads the question and emits an ExecutionPlan.

Uses the six capability facades (get_fund_data, get_portfolio_data, compare_funds,
search_financial_news, screen_funds_by_exposure, get_market_snapshot).
The planner schema enforces wave assignment (wave 1 vs wave 2) and deterministic
wave 2 trigger policies.

Slot rules replace bulky prompt examples to minimize prompt bloat and overfitting.
"""

from __future__ import annotations

import json
from typing import Any

from news_rag.insight.brief import QuestionBrief, SubAsk
from news_rag.insight.capabilities.catalog import (
    CAPABILITIES,
    capability_catalog_text,
    validate_capability_args,
)
from news_rag.insight.contracts import (
    AnswerMode,
    ExecutionPlan,
    QueryClass,
    ScopeKind,
    ToolCall,
    Wave2Policy,
)
from news_rag.insight.registry import ensure_registry, get_tool
from news_rag.llm_client import call_json_llm, llm_api_key_configured

# Backwards compatibility alias
Plan = ExecutionPlan

SCOPE_KINDS = ("in_scope", "out_of_scope", "needs_clarification")
INTENTS = ("lookup", "explain_cause", "compare", "overview", "rank", "outlook")
ANSWER_MODES = ("DATA_ONLY", "NEWS_ONLY", "INSIGHT_FUSION")
QUERY_CLASSES = ("simple", "standard", "complex")
RESPONSE_SHAPES = ("short_answer", "bullets", "paragraph", "table", "sections")
DEPTHS = ("quick", "standard", "deep")

DRIVER_IDS = (
    "rbi_repo", "crude_oil", "usd_inr", "cpi_inflation", "fpi_flows",
    "gsec_10y", "us_fed_yields", "monsoon", "govt_capex", "growth_indicators",
)
DRIVER_DIRECTIONS = ("tighten", "ease", "up", "down", "weaken", "strengthen")

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "scope": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": list(SCOPE_KINDS)},
                "direct_reply": {"type": "string"},
                "asks_for_advice": {"type": "boolean"},
            },
            "required": ["kind"],
        },
        "understanding": {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "intent": {"type": "string", "enum": list(INTENTS)},
                "answer_mode": {"type": "string", "enum": list(ANSWER_MODES)},
                "query_class": {"type": "string", "enum": list(QUERY_CLASSES)},
                "task": {
                    "type": "string",
                    "enum": ["explain", "data"],
                    "description": (
                        "explain when the user wants to understand a term, a fund type, or which categories exist. "
                        "data when they want numbers, a fund list, or one named scheme."
                    ),
                },
                "data_need": {
                    "type": "string",
                    "enum": [
                        "none",
                        "fund_holdings_breakdown",
                        "category_composition",
                        "category_performance",
                        "rating_for_screened_list",
                    ],
                    "description": (
                        "What data to fetch beyond a generic lookup. "
                        "fund_holdings_breakdown: asset mix, cap mix, sectors, top holdings for one scheme. "
                        "category_composition: what a SEBI category may hold plus one example fund's measured mix. "
                        "category_performance: fund in memory vs its category averages. "
                        "rating_for_screened_list: RupeeStop ratings for funds on the list cursor."
                    ),
                },
                "subject_ref": {
                    "type": "string",
                    "enum": ["none", "user_named", "memory_primary", "memory_stack", "list_cursor"],
                    "description": (
                        "Who or what the question is about. memory_primary when they say it/this fund and "
                        "Conversation memory has the scheme. list_cursor when they mean the on-screen list."
                    ),
                },
            },
            "required": ["goal", "intent", "answer_mode"],
        },
        "entities": {
            "type": "object",
            "properties": {
                "funds": {"type": "array", "items": {"type": "string"}},
                "random_funds": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "name_contains": {"type": "string"},
                    },
                },
                "sectors": {"type": "array", "items": {"type": "string"}},
                "scheme_categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Two or more category slugs when comparing categories.",
                },
                "stocks": {"type": "array", "items": {"type": "string"}},
                "drivers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "direction": {"type": "string"},
                        },
                        "required": ["id"],
                    },
                },
            },
        },
        "time": {
            "type": "object",
            "properties": {
                "window_days": {"type": "integer"},
                "label": {"type": "string"},
            },
        },
        "request": {
            "type": "object",
            "description": (
                "Your reading of the question before tools. Interpret meaning, including misspellings. "
                "count is the number the user asked for (0 if they did not ask for a count). "
                "portfolio_slice is holdings, sectors, both, or none."
            ),
            "properties": {
                "count": {"type": "integer"},
                "portfolio_slice": {
                    "type": "string",
                    "enum": ["holdings", "sectors", "both", "none"],
                },
                "reading": {"type": "string"},
                "fund_pick": {
                    "type": "string",
                    "enum": [
                        "none",
                        "best_in_category",
                        "alternate_in_category",
                        "random_in_category",
                        "compare_categories",
                    ],
                    "description": (
                        "alternate_in_category when the user wants a different fund in a category "
                        "already discussed (another/other/different), not a repeat of the top-rated name."
                    ),
                },
                "scheme_category": {
                    "type": "string",
                    "description": "Single SEBI scheme category slug when the ask is category-scoped.",
                },
                "rs_label": {
                    "type": "string",
                    "description": (
                        "RupeeStop RS label when the user wants a tier: Best in category, Recommended, "
                        "Good Choice, Average, Underperformer. Use with scheme_category on screens."
                    ),
                },
            },
            "required": ["count", "portfolio_slice", "reading"],
        },
        "tool_calls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": list(CAPABILITIES.keys())},
                    "arguments": {"type": "object"},
                    "wave": {"type": "string", "enum": ["1", "2"]},
                    "required": {"type": "boolean"},
                    "why": {"type": "string"},
                },
                "required": ["tool"],
            },
        },
        "memory": {
            "type": "object",
            "description": (
                "How this question uses the conversation. continue keeps the fund. "
                "partial_keep changes the period or the section. reset starts a new subject. "
                "stack_refs and list_ordinals are numbers from Conversation memory. "
                "depth is more when the user did not understand or asked to be told more."
            ),
            "properties": {
                "turn_relation": {"type": "string", "enum": ["continue", "partial_keep", "reset"]},
                "stack_refs": {"type": "array", "items": {"type": "integer"}},
                "list_ordinals": {"type": "array", "items": {"type": "integer"}},
                "depth": {"type": "string", "enum": ["short", "more"]},
                "refers_to_turn": {"type": "integer"},
            },
        },
        "wave_2_policy": {
            "type": "object",
            "properties": {
                "trigger": {
                    "type": "string",
                    "enum": ["none", "negative_return", "material_sector", "always"],
                },
                "threshold": {"type": "number"},
                "max_calls": {"type": "integer"},
            },
        },
        "presentation": {
            "type": "object",
            "properties": {
                "response_shape": {"type": "string", "enum": list(RESPONSE_SHAPES)},
                "max_words": {"type": "integer"},
                "lead_with": {"type": "string"},
                "presentation_notes": {"type": "string"},
                "asks_not_supported": {"type": "array", "items": {"type": "string"}},
                "sub_queries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                        },
                        "required": ["text"],
                    },
                },
                "reasoning_depth": {"type": "string", "enum": list(DEPTHS)},
            },
        },
    },
    "required": ["scope", "understanding", "request", "tool_calls"],
}


def _apply_planner_request(tool_calls: list[ToolCall], request: dict[str, Any]) -> tuple[int, str]:
    """Copy the planner's own count and portfolio slice onto tool arguments.

    This does not re-read the question with regex. If the planner understood
    'top 5' and 'holdings only', those fields win over a lazy default of 3 / both.
    """
    slice_name = str(request.get("portfolio_slice") or "none").strip().lower()
    if slice_name not in ("holdings", "sectors", "both", "none"):
        slice_name = "none"
    try:
        count = int(request.get("count") or 0)
    except (TypeError, ValueError):
        count = 0
    count = max(0, min(50, count))
    section_map = {
        "holdings": ["holdings"],
        "sectors": ["sectors"],
        "both": ["holdings", "sectors"],
    }
    sections = section_map.get(slice_name)
    for call in tool_calls:
        args = dict(call.arguments or {})
        if call.tool == "get_portfolio_data":
            if sections:
                args["sections"] = sections
            if count >= 1:
                args["top_n"] = count
            call.arguments = args
        elif call.tool == "screen_funds_by_exposure" and count >= 1 and slice_name == "none":
            args["top_n"] = min(20, count)
            call.arguments = args
    return count, slice_name


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if isinstance(v, (str, int, float)) and str(v).strip()]


def _pick_enum(value: Any, allowed: tuple[str, ...], default: str) -> str:
    text = str(value or "").strip().lower()
    for item in allowed:
        if item.lower() == text:
            return item
    return default


def _label_for_days(days: int) -> str:
    if days <= 1:
        return "1 day"
    if days < 14:
        return f"{days} days"
    if days < 60:
        weeks = round(days / 7)
        return f"{weeks} weeks" if weeks != 4 else "1 month"
    months = round(days / 30)
    return "1 month" if months == 1 else f"{months} months"


def parse_plan(data: dict[str, Any]) -> ExecutionPlan:
    """Parse JSON planner LLM output into a validated ExecutionPlan."""
    scope = data.get("scope") if isinstance(data.get("scope"), dict) else {}
    under = data.get("understanding") if isinstance(data.get("understanding"), dict) else {}
    ents = data.get("entities") if isinstance(data.get("entities"), dict) else {}
    when = data.get("time") if isinstance(data.get("time"), dict) else {}
    pres = data.get("presentation") if isinstance(data.get("presentation"), dict) else {}
    rnd = ents.get("random_funds") if isinstance(ents.get("random_funds"), dict) else {}
    w2p = data.get("wave_2_policy") if isinstance(data.get("wave_2_policy"), dict) else {}

    raw_scope_kind = _pick_enum(scope.get("kind"), SCOPE_KINDS, "in_scope")
    scope_kind = ScopeKind(raw_scope_kind)

    raw_intent = _pick_enum(under.get("intent"), INTENTS, "lookup")
    raw_mode = str(under.get("answer_mode") or "").upper()
    if raw_mode not in ANSWER_MODES:
        raw_mode = "DATA_ONLY" if raw_intent == "lookup" else "INSIGHT_FUSION"
    answer_mode = AnswerMode(raw_mode)

    raw_qclass = str(under.get("query_class") or "").lower()
    if raw_qclass not in QUERY_CLASSES:
        raw_qclass = "simple" if answer_mode == AnswerMode.DATA_ONLY else "standard"
    query_class = QueryClass(raw_qclass)

    # Entities
    funds = _str_list(ents.get("funds"))
    sectors = _str_list(ents.get("sectors"))
    stocks = _str_list(ents.get("stocks"))
    drivers: list[dict[str, str]] = []
    for d in ents.get("drivers") or []:
        if isinstance(d, dict) and str(d.get("id") or "").strip():
            drivers.append({
                "id": str(d["id"]).strip(),
                "direction": str(d.get("direction") or "").strip().lower(),
            })
        elif isinstance(d, str) and d.strip():
            drivers.append({"id": d.strip(), "direction": ""})

    try:
        random_count = max(0, min(10, int(rnd.get("count") or 0)))
    except (TypeError, ValueError):
        random_count = 0
    random_name_contains = str(rnd.get("name_contains") or "").strip()

    # Time
    try:
        window_days = max(1, min(1825, int(when.get("window_days") or 30)))
    except (TypeError, ValueError):
        window_days = 30
    window_label = str(when.get("label") or "").strip() or _label_for_days(window_days)

    # Tool calls validation
    raw_tool_calls = data.get("tool_calls") or []
    tool_calls: list[ToolCall] = []
    for raw_tc in raw_tool_calls:
        if not isinstance(raw_tc, dict):
            continue
        tool_name = str(raw_tc.get("tool") or "").strip()
        if tool_name not in CAPABILITIES:
            continue
        raw_args = raw_tc.get("arguments") or raw_tc.get("args") or {}
        valid_args = validate_capability_args(tool_name, raw_args if isinstance(raw_args, dict) else {})
        try:
            wave = int(raw_tc.get("wave") or 1)
        except (TypeError, ValueError):
            wave = 1
        if wave not in (1, 2):
            wave = 1
        tool_calls.append(ToolCall(
            tool=tool_name,
            arguments=valid_args,
            wave=wave,
            required=bool(raw_tc.get("required", True)),
            why=str(raw_tc.get("why") or ""),
        ))

    request = data.get("request") if isinstance(data.get("request"), dict) else {}
    planner_count, planner_slice = _apply_planner_request(tool_calls, request)
    planner_reading = str(request.get("reading") or "").strip()
    fund_pick = str(request.get("fund_pick") or "none").strip().lower()
    from news_rag.insight.plan_intent import FUND_PICK_VALUES

    if fund_pick not in FUND_PICK_VALUES:
        fund_pick = "none"
    scheme_category = str(request.get("scheme_category") or "").strip()
    scheme_categories = _str_list(ents.get("scheme_categories"))
    from news_rag.fund_rating_labels import normalize_rs_label

    rs_label = normalize_rs_label(str(request.get("rs_label") or ""))
    memory = data.get("memory") if isinstance(data.get("memory"), dict) else {}
    relation = str(memory.get("turn_relation") or "").strip()
    if relation not in ("continue", "partial_keep", "reset"):
        relation = ""
    depth = str(memory.get("depth") or "").strip()
    if depth not in ("short", "more"):
        depth = "short"
    stack_refs = []
    for ref in memory.get("stack_refs") or []:
        try:
            number = int(ref)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 5 and number not in stack_refs:
            stack_refs.append(number)
    list_ordinals = []
    for ref in memory.get("list_ordinals") or []:
        try:
            number = int(ref)
        except (TypeError, ValueError):
            continue
        if number >= 1 and number not in list_ordinals:
            list_ordinals.append(number)
    try:
        refers_to_turn = int(memory.get("refers_to_turn") or 0)
    except (TypeError, ValueError):
        refers_to_turn = 0

    # Wave 2 Policy
    policy = Wave2Policy(
        trigger=str(w2p.get("trigger") or "none"),
        threshold=float(w2p["threshold"]) if w2p.get("threshold") is not None else None,
        max_calls=max(1, min(2, int(w2p.get("max_calls") or 1))),
    )

    # Presentation
    response_shape = _pick_enum(pres.get("response_shape"), RESPONSE_SHAPES, "sections")
    max_words = max(30, min(1000, int(pres.get("max_words") or 220)))
    lead_with = str(pres.get("lead_with") or "").strip()
    presentation_notes = str(pres.get("presentation_notes") or "").strip()
    reasoning_depth = _pick_enum(pres.get("reasoning_depth"), DEPTHS, "standard")
    asks_not_supported = _str_list(pres.get("asks_not_supported"))

    sub_queries: list[dict[str, Any]] = []
    for sq in pres.get("sub_queries") or []:
        if isinstance(sq, dict) and str(sq.get("text") or "").strip():
            sub_queries.append({"text": str(sq["text"]).strip()})
        elif isinstance(sq, str) and sq.strip():
            sub_queries.append({"text": sq.strip()})

    plan = ExecutionPlan(
        guardrail_passed=True,
        can_answer_directly=bool(scope.get("direct_reply")),
        direct_reply=str(scope.get("direct_reply") or "").strip(),
        scope_kind=scope_kind,
        intent=raw_intent,
        goal=str(under.get("goal") or "").strip(),
        answer_mode=answer_mode,
        query_class=query_class,
        funds=funds,
        sectors=sectors,
        stocks=stocks,
        drivers=drivers,
        random_fund_count=random_count,
        random_fund_name_contains=random_name_contains,
        window_days=window_days,
        window_label=window_label,
        tool_calls=tool_calls,
        wave_2_policy=policy,
        response_shape=response_shape,
        max_words=max_words,
        lead_with=lead_with,
        presentation_notes=presentation_notes,
        asks_for_advice=bool(scope.get("asks_for_advice")),
        asks_not_supported=asks_not_supported,
        sub_queries=sub_queries,
        reasoning_depth=reasoning_depth,
        routed_by="planner",
        confidence=0.9,
        planner_count=planner_count,
        planner_portfolio_slice=planner_slice,
        planner_reading=planner_reading,
        fund_pick=fund_pick,
        scheme_category=scheme_category,
        scheme_categories=scheme_categories,
        rs_label=rs_label,
        data_need=str(under.get("data_need") or "none").strip().lower() or "none",
        subject_ref=str(under.get("subject_ref") or "none").strip().lower() or "none",
        turn_relation=relation,
        stack_refs=stack_refs,
        list_ordinals=list_ordinals,
        answer_depth=depth,
        refers_to_turn=refers_to_turn,
    )
    from news_rag.insight.plan_intent import normalize_fund_pick_from_planner

    normalize_fund_pick_from_planner(plan)

    canned = bool((plan.direct_reply or "").strip() and not plan.tool_calls)
    plan.requires_compose = not canned
    if str(under.get("task") or "").strip().lower() == "explain":
        from news_rag.fund_rating_categories import explanation_brief

        example = _example_part(plan.sub_queries)
        plan.direct_reply = ""
        plan.can_answer_directly = False
        plan.requires_compose = True
        plan.concept_brief = explanation_brief()
        plan.max_words = max(int(plan.max_words or 0), 280 if example or len(plan.sub_queries) > 1 else 180)
        if example:
            screen = next((call for call in plan.tool_calls if call.tool == "screen_funds_by_exposure"), None)
            if screen is None:
                screen = ToolCall(
                    tool="screen_funds_by_exposure",
                    arguments={"top_n": 1, "direction": "any", "focus_question": example},
                    why="The user asked for one example fund.",
                    required=True,
                )
            else:
                args = dict(screen.arguments or {})
                args["top_n"] = 1
                args["direction"] = "any"
                args["focus_question"] = example
                screen.arguments = args
            plan.tool_calls = [screen]
            note = (
                "Answer every part of the question. Explain from concept_brief. "
                "Then name exactly one fund from the screen rankings. Use that fund name. "
                "Do not say that no fund was provided."
            )
        else:
            plan.tool_calls = []
            plan.funds = []
            note = (
                "Answer from concept_brief. Explain the idea in plain sentences. "
                "Do not name a fund. Do not invent a category, a return, or a score."
            )
        plan.presentation_notes = f"{plan.presentation_notes} {note}".strip()
    return plan


def _example_part(sub_queries: list[dict[str, Any]]) -> str:
    """A planner part that asks for a fund name, separate from the explanation."""
    import re

    pattern = re.compile(
        r"\b(?:name|example|which|show|give|suggest|pick)\b.{0,48}\bfunds?\b|"
        r"\bfunds?\b.{0,32}\b(?:name|example)\b",
        re.I,
    )
    for part in sub_queries:
        text = str(part.get("text") or "").strip()
        if text and pattern.search(text):
            return text
    return ""


def tools_to_facets(tool_names: list[str]) -> tuple[list[str], dict[str, str]]:
    """Backwards compatibility adapter for legacy gather routines."""
    ensure_registry()
    specs = [get_tool(n) for n in tool_names if get_tool(n) is not None]
    needed_by_chosen = {f for s in specs for f in s.requires}
    claimed: set[str] = set()
    facets: list[str] = []
    forced: dict[str, str] = {}
    for spec in specs:
        options = sorted(spec.provides)
        ordered = [f for f in options if f in needed_by_chosen] + [
            f for f in options if f not in needed_by_chosen
        ]
        facet = next((f for f in ordered if f not in claimed), None)
        if facet is None:
            continue
        claimed.add(facet)
        facets.append(facet)
        forced[facet] = spec.name
    return facets, forced


def plan_to_brief(plan: ExecutionPlan, *, sector_keys: list[str], funds: list[str]) -> QuestionBrief:
    """Backwards compatibility adapter mapping ExecutionPlan to QuestionBrief."""
    facets, _forced = tools_to_facets(plan.tool_names)
    intent_map = {
        "lookup": "measure",
        "overview": "measure",
        "explain_cause": "explain_cause",
        "compare": "compare",
        "rank": "rank",
        "outlook": "outlook",
    }
    sub_asks = [
        SubAsk(id=f"s{i}", text=sq["text"], kind="describe", order=i)
        for i, sq in enumerate(plan.sub_queries, 1)
    ]
    subjects: list[dict[str, str]] = []
    for key in sector_keys[:1]:
        subjects.append({"raw": key, "role": "sector", "canonical": key})
    for d in plan.drivers:
        subjects.append({"raw": d["id"], "role": "macro_driver", "canonical": d["id"]})
    for name in funds:
        subjects.append({"raw": name, "role": "fund_scheme", "canonical": name})
    for name in plan.stocks:
        subjects.append({"raw": name, "role": "stock", "canonical": name})

    return QuestionBrief(
        goal=plan.goal,
        intent=intent_map.get(plan.intent, "measure"),
        sub_asks=sub_asks,
        subjects=subjects,
        window_days=plan.window_days,
        window_label=plan.window_label,
        evidence_needs=facets,
        sector_keys=list(sector_keys),
        drivers=[d["id"] for d in plan.drivers],
        driver_direction=next((d["direction"] for d in plan.drivers if d.get("direction")), ""),
        funds=list(funds),
        stocks=list(plan.stocks),
        direction="any",
        wants_funds_flag=bool("screen_funds_by_exposure" in plan.tool_names),
        raw={"source": "plan"},
    )


# ---------------------------------------------------------------------------
# Planner System Prompt with Slot Rules
# ---------------------------------------------------------------------------

_SYSTEM_CACHE: str | None = None


def _invalidate_plan_system_cache() -> None:
    global _SYSTEM_CACHE
    _SYSTEM_CACHE = None


def plan_system_prompt() -> str:
    global _SYSTEM_CACHE
    if _SYSTEM_CACHE is not None:
        return _SYSTEM_CACHE

    catalog = capability_catalog_text()
    prompt = f"""You are the planner for an Indian mutual fund, stock, and market analytics assistant.
Read the user's question and emit ONE structured JSON ExecutionPlan using ONLY the six capabilities below.

### CAPABILITY TOOLS
{catalog}

### FIELDS THE PARSER ACCEPTS
Optional fields may be omitted. Do not invent field names.
- `understanding.intent`: lookup, overview, explain_cause, compare, rank, outlook. A definition or a SIP/FIRE calculation uses lookup.
- `understanding.data_need`: none, fund_holdings_breakdown, category_composition, category_performance, rating_for_screened_list. Set the one that matches what numbers to fetch. The server will not second-guess this when you set it.
- `understanding.subject_ref`: none, user_named, memory_primary, memory_stack, list_cursor. Use memory_primary when they mean the fund already in Conversation memory (it, this fund, that scheme) even if misspelled.
- `understanding.task`: explain or data. explain means the user wants to understand a word, a fund type, or which categories exist, including a misspelled question such as "what are multi cap fund" or "sub category of the equity funds". data means they want a number, a list of schemes, a rating, or one named fund. A screen hint that names a category does not make an explanation into a fund list.
- `understanding.answer_mode`: DATA_ONLY, NEWS_ONLY, INSIGHT_FUSION. DATA_ONLY means do not fetch news. The composer still writes the answer.
- `entities.funds`, `entities.sectors`, `entities.stocks`: string arrays, as the user wrote them. Correct an obvious misspelling of a name they did give. Do not invent a fund they did not name.
- `entities.drivers`: objects {{"id", "direction"}}. id is one of: {', '.join(DRIVER_IDS)}. direction is up, down, tighten, ease, weaken, or strengthen. Do not use macro_drivers.
- `request`: count (integer), portfolio_slice (holdings, sectors, both, none), reading (one sentence), fund_pick (none, best_in_category, alternate_in_category, random_in_category, compare_categories), scheme_category (single category slug when category-scoped). Required when the question is about what is inside one fund. Otherwise set portfolio_slice to none and count to 0.
- `entities.scheme_categories`: when comparing two category types (conservative hybrid vs aggressive hybrid), list each slug here and set request.fund_pick to compare_categories. Do **not** set data_need to category_composition for that ask — use two screen_funds_by_exposure calls (one per category) or leave tool_calls empty and let the server expand; intent compare, not a holdings essay.
- **Another / other / different fund in the same category** (follow-up after you already named schemes): request.fund_pick alternate_in_category, request.scheme_category the slug (e.g. aggressive hybrid), memory.turn_relation continue. screen_funds_by_exposure with rating_screen true, pick_alternate true, focus_question only the category slug (not the full user sentence), top_n 1. Do not repeat a fund already in Conversation memory for that category.
- **RS label filters**: set request.rs_label and/or screen_funds_by_exposure rs_label when the user names a tier (Recommended, Good Choice, best in category, etc.). Always set scheme_category when the ask is category-scoped. If they want another fund at the same tier and none remain, the server walks to lower tiers in that category.
- `tool_calls[].wave`: 1 or 2. An integer is preferred. The strings "1" and "2" are also accepted.
- `wave_2_policy.trigger`: none, negative_return, material_sector, always. There is no high_weight_holding trigger.
- `scope.direct_reply`: set only when the whole answer is one glossary sentence. Omit it for calculations. An empty string is the same as omitting it.
- `scope.kind`: in_scope or out_of_scope. out_of_scope means the question is not about Indian funds, stocks, or markets. Then tool_calls is [] and response_shape is short_answer.

### DISAMBIGUATION
| User means | Tool | Do not use |
| Funds with heavy sector exposure, or which funds hold a stock | screen_funds_by_exposure | get_portfolio_data |
| Stocks or holdings inside one named fund | get_portfolio_data sections ["holdings"], top_n from the question | screen_funds_by_exposure, and do not also request sectors |
| Sectors inside one scheme | get_portfolio_data sections ["sectors"] only | get_fund_data, news, holdings |
| Compare two or more named funds | one compare_funds call, arguments mode metrics, overlap, or both | get_fund_data once per fund, and do not pass modules |
| Market or macro level, no fund named | get_market_snapshot modules index_return, sector_ranking, macro_series, metals_spot, or stock_quote. series crude, brent, wti, usdinr, gold, silver, yield | a macro_impact module or a driver argument on this tool |
| Which funds a driver hits | screen_funds_by_exposure with driver set to a lowercase id such as crude_oil | get_market_snapshot alone |
| NAV, returns, or managers of one fund | get_fund_data | screen_funds_by_exposure |

### PLANNER AUTHORITY
You are the sole routing authority. Every tool call, module, and wave comes from your JSON. Downstream code only fills gaps you leave; it does not re-route when you set data_need and tool_calls correctly.
Read the question as a person would: typos, missing words, and Hinglish still have one clear intent. Put your corrected reading in request.reading. Put canonical fund names in entities.funds when you recognize them (fix obvious spelling: "hdfc larg cap" → HDFC Large Cap Fund). Do not copy typos into entities if the catalog name is clear.
When the message includes Conversation memory, that block is the only earlier context. It has the current fund, a numbered fund stack (ref 1 is the newest), the list on screen, a news topic, and the last two one-line gists. It does not contain figures or article text.
Set memory.turn_relation to continue, partial_keep, or reset. continue keeps the same fund and period. partial_keep changes the period or the section and keeps the fund. reset starts a new subject and names that fund in entities.funds.
"I didn't understand" and "tell me more" are continue with memory.depth set to more. Repeat the same tools. Do not switch to a new overview.
If one part points at an earlier fund, set memory.stack_refs to those numbers. A follow-up may name the previous fund and the one before it. If a part points at a row of the list, set memory.list_ordinals. Do not invent a fund from a sector or a holding that appeared only inside an explanation.
A news follow-up keeps the news topic. "How is my fund affected" uses the fund plus that topic and fetches holdings or sectors and news. "Tell me more about that news" searches the topic again and does not dump the fund. "What is the RBI rate" is a definition with no fund tool. The topic stays for a later question.

### MINIMAL TOOLS
A specific question lists only the modules that answer it. query_class is simple. Do not add search_financial_news, return_series, or attribution.
- NAV, AUM, expense ratio, or exit load: get_fund_data modules ["snapshot"] only.
- One return period, such as 1 month: get_fund_data modules ["snapshot"] and windows set to that one code, such as ["1M"]. Do not add return_series and do not add the other periods. A period can be any length. Use 2M, 8M, 14D, YTD, 6M, or 1Y when that is what they asked. Two periods means both codes, such as ["6M", "1Y"]. Set time.label to those periods, not to 1 month, unless they asked for 1 month.
- A named-fund overview that also fetches news: add get_portfolio_data sections ["holdings", "sectors"] on wave 1. The news has to be tied to a weight. A later question that asks for a different section, period, or module is a new tool call. Do not reuse the previous call's arguments.
- Versus the benchmark only: get_fund_data modules ["vs_benchmark"] only. Do not add snapshot, return_series, or attribution.
- The fund manager's name: get_fund_data modules ["managers"] only.
- One pillar mark (performance, risk, portfolio quality, or fund manager): get_fund_data modules ["rating"] only. Add ["risk"] only when they ask how risky the fund is.
- A risk analysis: get_fund_data modules ["risk", "drawdown", "rating"] and periods ["1y", "3y", "5y"] when no horizon was named. The risk pillar is a score, not a statement that the fund is more or less risky.
A question with more than one part is still one plan. List each part in presentation.sub_queries and put every tool those parts need on wave 1. A figure plus what it means, or whether a low or high value is good, is several parts: fetch the figure, and leave the meaning and the judgement to the composer. No extra tool is required for a definition. A misspelling still means the intended word. Do not drop a part.
"Returns of this fund for 1 month, and why did they change?" is two parts: get_fund_data modules ["snapshot", "attribution"] with windows ["1M"], plus search_financial_news on wave 1. Do not load 1W, 3M, 6M, 1Y, or return_series.

### REQUEST
The server copies request onto the portfolio tool when the two disagree.
- count is the number they asked for. "top 5" and "top ten" are 5 and 10. Use 0 only when they asked for no number. Never substitute 3 for 5.
- portfolio_slice is holdings when they want stocks inside one fund and did not ask for sectors. sectors when they want sector weights only. both only when they asked for both or for the whole portfolio. none otherwise.
- reading is one corrected sentence.
Copy count into arguments.top_n and the slice into get_portfolio_data arguments.sections.

### TIME
"right now", "currently", "at the moment", and "market now" mean the last 7 days. Set time.window_days to 7 and set window_days to 7 on get_market_snapshot, search_financial_news, and get_fund_data. That percent is 1W. If the user also names a period, such as last month or this year, use that period instead of 7.

- Glossary only, such as the full form of NAV: tool_calls [], direct_reply one sentence, max_words at most 40, DATA_ONLY, task data.
- What a category or fund type is, or which categories exist: task explain, tool_calls [], omit direct_reply, max_words at least 180. The composer writes the explanation. Do not call screen_funds_by_exposure. "5 multi cap funds" and "best multi cap fund" are task data and do use the screen.
- A question with more than one part: list each part in presentation.sub_queries. Keep task explain when the parts are an explanation. If one part asks for the name of a fund, also add one screen_funds_by_exposure call with top_n 1. The composer answers every part and cites that one scheme.
- One question can ask for a fund and then for facts about that fund. Example: the highest rating equity fund, its historical returns, and a risk analysis. screen_funds_by_exposure top_n 1, then get_fund_data modules return_series, risk, and drawdown. The risk read is that fund call. Do not add search_financial_news for it, and do not write the risk analysis in the plan.
- A calculation or plan no tool can compute, such as a stepped-up SIP toward a corpus: tool_calls [], portfolio_slice none, omit direct_reply, task data, max_words at least 400. The composer does the arithmetic and states any missing input as an assumption. Do not answer with a sentence that only says a calculation is required.
- Concept plus one example, such as what a fund of funds is and name one: task data, screen_funds_by_exposure top_n 1, DATA_ONLY, response_shape sections, presentation_notes telling the composer to explain the concept and then cite the screened scheme.

### WAVES
1. DATA_ONLY is a fetch choice: a NAV, a list, a comparison, or a definition, and no search_financial_news. trigger is none. It is not a finished dump. The composer writes the reply, including a meaning or a high-or-low read from standard mutual-fund knowledge.
2. "Tell me about <fund>" or "how is <fund>" is INSIGHT_FUSION. Wave 1 gets get_fund_data modules ["snapshot", "rating"] and search_financial_news. Do not add return_series, attribution, or the portfolio unless that part of the question asks for returns, what drove the move, holdings, or sectors.
3. NEWS_ONLY is macro or market news with no fund numbers. Wave 1 may call get_market_snapshot. trigger is always, with one search_financial_news call on wave 2.
4. Wave 1 tools: get_fund_data, get_portfolio_data, compare_funds, get_market_snapshot, screen_funds_by_exposure. INSIGHT_FUSION is the mode when metrics and news are both needed.
5. If trigger is always, add the search_financial_news call with wave 2. If trigger is negative_return, material_sector, or none, do not add a wave-2 call. The bridge adds news when the condition is true. For "why did the fund fall", use negative_return and threshold -1.0. For a generic "why did it move", use threshold -2.0.
6. Fund news ("news related to HDFC Large Cap"): wave 1 get_portfolio_data sections holdings and sectors, wave 2 search_financial_news scope all. Narrow scope only when the user asked for sectors or macro only.
7. At most one wave-2 call and at most four tool_calls in total.
8. top_n equals request.count when count is 1 or more. Default 3 only when count is 0.
9. response_shape: short_answer for a lookup, table for a comparison or a top-N list, sections when metrics and news are combined. max_words 40-80 for lookups, 200-450 when the answer needs sections, at least 400 for a calculation.

### EXAMPLES
NAV:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Check NAV of fund", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "simple"}}, "request": {{"count": 0, "portfolio_slice": "none", "reading": "NAV of HDFC Top 100"}}, "entities": {{"funds": ["HDFC Top 100"]}}, "tool_calls": [{{"tool": "get_fund_data", "arguments": {{"modules": ["snapshot"]}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "short_answer", "max_words": 50}}}}

Expense ratio, what it means, and whether low or high is good:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Expense ratio, its meaning, and whether low or high is better", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "simple", "task": "data"}}, "request": {{"count": 0, "portfolio_slice": "none", "reading": "Expense ratio of HDFC Large Cap, what it means, and whether low or high is good"}}, "entities": {{"funds": ["HDFC Large Cap Fund"]}}, "tool_calls": [{{"tool": "get_fund_data", "arguments": {{"modules": ["snapshot"]}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "sections", "max_words": 180, "sub_queries": [{{"text": "the expense ratio figure"}}, {{"text": "what expense ratio means"}}, {{"text": "whether a low or high ratio is good"}}]}}}}

Tell me about one fund:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Overview of HDFC Large Cap", "intent": "overview", "answer_mode": "INSIGHT_FUSION", "query_class": "standard"}}, "request": {{"count": 0, "portfolio_slice": "both", "reading": "Overview of HDFC Large Cap Fund"}}, "entities": {{"funds": ["HDFC Large Cap Fund"]}}, "time": {{"window_days": 30}}, "tool_calls": [{{"tool": "get_fund_data", "arguments": {{"modules": ["snapshot", "rating"]}}, "wave": 1}}, {{"tool": "get_portfolio_data", "arguments": {{"sections": ["holdings", "sectors"], "top_n": 5}}, "wave": 1}}, {{"tool": "search_financial_news", "arguments": {{"scope": "all", "top_n": 8, "window_days": 30}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "sections", "max_words": 280, "sub_queries": [{{"text": "what the fund is"}}, {{"text": "what the news means for it"}}], "notes": "Rating first. Then what stands out in the news, tied to a holding or sector weight. End with a short overall read."}}}}

One month return and why it changed:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "1 month return and why it changed", "intent": "explain_cause", "answer_mode": "INSIGHT_FUSION", "query_class": "standard"}}, "request": {{"count": 0, "portfolio_slice": "none", "reading": "1 month return of Bandhan Large Cap and why it changed"}}, "entities": {{"funds": ["Bandhan Large Cap Fund"]}}, "time": {{"window_days": 30}}, "tool_calls": [{{"tool": "get_fund_data", "arguments": {{"modules": ["snapshot", "attribution", "rating"], "windows": ["1M"], "window_days": 30}}, "wave": 1}}, {{"tool": "search_financial_news", "arguments": {{"scope": "all", "top_n": 8, "window_days": 30}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "sections", "max_words": 280, "sub_queries": [{{"text": "1 month return"}}, {{"text": "why it changed"}}]}}}}

Versus the benchmark only:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Fund versus its benchmark", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "simple"}}, "request": {{"count": 0, "portfolio_slice": "none", "reading": "Bandhan Large Cap versus its benchmark"}}, "entities": {{"funds": ["Bandhan Large Cap Fund"]}}, "tool_calls": [{{"tool": "get_fund_data", "arguments": {{"modules": ["vs_benchmark", "rating"]}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "short_answer", "max_words": 80}}}}

Why the fund fell:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Explain the recent drop", "intent": "explain_cause", "answer_mode": "INSIGHT_FUSION", "query_class": "standard"}}, "request": {{"count": 0, "portfolio_slice": "both", "reading": "Why Parag Parikh Flexi Cap fell"}}, "entities": {{"funds": ["Parag Parikh Flexi Cap"]}}, "time": {{"window_days": 30}}, "tool_calls": [{{"tool": "get_fund_data", "arguments": {{"modules": ["snapshot", "return_series", "attribution"]}}, "wave": 1}}, {{"tool": "get_portfolio_data", "arguments": {{"sections": ["holdings", "sectors"], "top_n": 5}}, "wave": 1}}], "wave_2_policy": {{"trigger": "negative_return", "threshold": -1.0, "max_calls": 1}}, "presentation": {{"response_shape": "sections", "max_words": 280}}}}

One auto-sector fund, then its facts and sector news:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Pick one auto-sector fund and summarize it", "intent": "overview", "answer_mode": "INSIGHT_FUSION", "query_class": "standard"}}, "request": {{"count": 1, "portfolio_slice": "both", "reading": "One automobile fund, then its portfolio and news"}}, "entities": {{"sectors": ["Automobiles"]}}, "tool_calls": [{{"tool": "screen_funds_by_exposure", "arguments": {{"sector": "Automobiles", "direction": "any", "top_n": 1}}, "wave": 1}}, {{"tool": "get_fund_data", "arguments": {{"modules": ["snapshot", "attribution"]}}, "wave": 1}}, {{"tool": "get_portfolio_data", "arguments": {{"sections": ["holdings", "sectors"], "top_n": 5}}, "wave": 1}}, {{"tool": "search_financial_news", "arguments": {{"scope": "sectors", "top_n": 8, "window_days": 30}}, "wave": 2}}], "wave_2_policy": {{"trigger": "always", "max_calls": 1}}, "presentation": {{"response_shape": "sections", "max_words": 320}}}}

Top sectors only:
{{"request": {{"count": 5, "portfolio_slice": "sectors", "reading": "Top 5 sectors of Axis Large Cap"}}, "scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Top 5 sectors of the named scheme", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "simple"}}, "entities": {{"funds": ["Axis Large Cap Fund"]}}, "tool_calls": [{{"tool": "get_portfolio_data", "arguments": {{"sections": ["sectors"], "top_n": 5}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "table", "max_words": 80}}}}

Top holdings, including a misspelled word for holdings:
{{"request": {{"count": 5, "portfolio_slice": "holdings", "reading": "Top 5 holdings of Axis ELSS Tax Saver"}}, "scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Top 5 holdings of Axis ELSS Tax Saver", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "simple"}}, "entities": {{"funds": ["Axis ELSS - Tax Saver Fund"]}}, "tool_calls": [{{"tool": "get_portfolio_data", "arguments": {{"sections": ["holdings"], "top_n": 5}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "table", "max_words": 120}}}}

Fund news:
{{"request": {{"count": 5, "portfolio_slice": "both", "reading": "News relevant to HDFC Large Cap via holdings and sectors"}}, "scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "News relevant to the fund", "intent": "overview", "answer_mode": "INSIGHT_FUSION", "query_class": "standard"}}, "entities": {{"funds": ["HDFC Large Cap Fund"]}}, "time": {{"window_days": 30}}, "tool_calls": [{{"tool": "get_fund_data", "arguments": {{"modules": ["snapshot", "return_series", "attribution"]}}, "wave": 1}}, {{"tool": "get_portfolio_data", "arguments": {{"sections": ["holdings", "sectors"], "top_n": 5}}, "wave": 1}}, {{"tool": "get_market_snapshot", "arguments": {{"modules": ["index_return"], "index": "nifty50"}}, "wave": 1}}, {{"tool": "search_financial_news", "arguments": {{"scope": "all", "top_n": 8, "window_days": 30}}, "wave": 2}}], "wave_2_policy": {{"trigger": "always", "max_calls": 1}}, "presentation": {{"response_shape": "sections", "max_words": 420}}}}

Compare two funds:
{{"request": {{"count": 0, "portfolio_slice": "none", "reading": "Compare HDFC Top 100 and Axis Bluechip"}}, "scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Compare two named funds", "intent": "compare", "answer_mode": "DATA_ONLY", "query_class": "standard", "data_need": "none"}}, "entities": {{"funds": ["HDFC Top 100 Fund", "Axis Bluechip Fund"]}}, "tool_calls": [{{"tool": "compare_funds", "arguments": {{"mode": "both"}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "table", "max_words": 150}}}}

Compare two funds in one category when the user did not name schemes (server screens a pair, then compare_funds):
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Compare two large cap funds", "intent": "compare", "answer_mode": "DATA_ONLY", "query_class": "simple", "data_need": "none"}}, "request": {{"count": 0, "portfolio_slice": "none", "reading": "Compare two large cap funds side by side", "scheme_category": "large cap"}}, "tool_calls": [{{"tool": "screen_funds_by_exposure", "arguments": {{"rating_screen": true, "focus_question": "large cap", "top_n": 2, "compare_pair": true}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "table", "max_words": 220}}}}

Compare two random equity funds in the same scheme category (no fund names in entities; server picks category from large/mid/small/flexi/multi/large & mid cap):
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Compare two random equity funds in one category", "intent": "compare", "answer_mode": "DATA_ONLY", "query_class": "simple", "data_need": "none", "subject_ref": "none"}}, "request": {{"count": 2, "portfolio_slice": "none", "reading": "Compare two random equity funds in the same equity category", "fund_pick": "random_in_category"}}, "entities": {{"funds": []}}, "tool_calls": [{{"tool": "screen_funds_by_exposure", "arguments": {{"rating_screen": true, "top_n": 2, "compare_pair": true, "focus_question": "equity"}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "table", "max_words": 220}}}}

Compare both funds in one category already in Conversation memory (use category_funds_in_chat; not frame.subjects from an old conservative vs aggressive compare):
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Compare both aggressive hybrid funds from this chat", "intent": "compare", "answer_mode": "DATA_ONLY", "query_class": "simple", "data_need": "none", "subject_ref": "memory_stack"}}, "request": {{"count": 0, "portfolio_slice": "none", "reading": "Compare ICICI Prudential Aggressive Hybrid and SBI Aggressive Hybrid", "scheme_category": "aggressive hybrid"}}, "memory": {{"turn_relation": "continue"}}, "tool_calls": [{{"tool": "compare_funds", "arguments": {{"mode": "both"}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "table", "max_words": 200}}}}

Another fund in a category already discussed:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Name a different aggressive hybrid fund not already mentioned", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "simple", "data_need": "none", "subject_ref": "memory_primary"}}, "request": {{"count": 1, "portfolio_slice": "none", "reading": "Another aggressive hybrid fund, not one already named in this chat", "fund_pick": "alternate_in_category", "scheme_category": "aggressive hybrid"}}, "memory": {{"turn_relation": "continue"}}, "tool_calls": [{{"tool": "screen_funds_by_exposure", "arguments": {{"rating_screen": true, "pick_alternate": true, "focus_question": "aggressive hybrid", "top_n": 1}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "short_answer", "max_words": 120}}}}

What this fund holds (follow-up, typo ok):
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Holdings and allocation for the fund in memory", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "standard", "data_need": "fund_holdings_breakdown", "subject_ref": "memory_primary"}}, "request": {{"count": 5, "portfolio_slice": "both", "reading": "What the fund in context holds (user wrote holdengs)"}}, "memory": {{"turn_relation": "continue"}}, "tool_calls": [{{"tool": "get_fund_data", "arguments": {{"modules": ["risk", "snapshot"]}}, "wave": 1}}, {{"tool": "get_portfolio_data", "arguments": {{"sections": ["holdings", "sectors"], "top_n": 5}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "sections", "max_words": 320}}}}

Crude oil up, no fund named:
{{"request": {{"count": 5, "portfolio_slice": "none", "reading": "Sectors and funds if crude oil rises"}}, "scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Which sectors and funds benefit if crude rises", "intent": "explain_cause", "answer_mode": "NEWS_ONLY", "query_class": "standard"}}, "entities": {{"drivers": [{{"id": "crude_oil", "direction": "up"}}]}}, "tool_calls": [{{"tool": "get_market_snapshot", "arguments": {{"modules": ["macro_series", "sector_ranking"], "series": ["crude"]}}, "wave": 1}}, {{"tool": "screen_funds_by_exposure", "arguments": {{"driver": "crude_oil", "direction": "positive", "top_n": 5}}, "wave": 1}}, {{"tool": "search_financial_news", "arguments": {{"scope": "macro", "top_n": 8, "window_days": 7}}, "wave": 2}}], "wave_2_policy": {{"trigger": "always", "max_calls": 1}}, "presentation": {{"response_shape": "sections", "max_words": 250}}}}

Glossary:
{{"scope": {{"kind": "in_scope", "direct_reply": "SIP stands for Systematic Investment Plan: a fixed amount invested in a mutual fund at regular intervals."}}, "understanding": {{"goal": "Define SIP", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "simple", "task": "data"}}, "request": {{"count": 0, "portfolio_slice": "none", "reading": "Definition of SIP"}}, "tool_calls": [], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "short_answer", "max_words": 40}}}}

What a category is, or which categories exist:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Explain what a multi cap fund is", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "simple", "task": "explain"}}, "request": {{"count": 0, "portfolio_slice": "none", "reading": "What a multi cap fund is"}}, "entities": {{}}, "tool_calls": [], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "short_answer", "max_words": 180}}}}

Stepped-up SIP illustration:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Illustrate a stepped-up SIP that reaches 2 crore in 20 years", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "standard"}}, "request": {{"count": 0, "portfolio_slice": "none", "reading": "SIP plan for a 2 crore goal in 20 years with a 10 percent annual step-up"}}, "tool_calls": [], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "sections", "max_words": 420}}}}

Out of scope:
{{"scope": {{"kind": "out_of_scope"}}, "understanding": {{"goal": "Not about funds, stocks, or markets", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "simple"}}, "request": {{"count": 0, "portfolio_slice": "none", "reading": "Outside markets"}}, "tool_calls": [], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "short_answer", "max_words": 30}}}}
"""
    _SYSTEM_CACHE = prompt.strip()
    return _SYSTEM_CACHE


def _slot_fallback(question: str) -> ExecutionPlan | None:
    """Used only when the planner cannot return a plan."""
    from news_rag.insight.portfolio_plan import normalize_portfolio_plan_from_question
    from news_rag.insight.slot_router import slot_route

    det_plan = slot_route(question, confidence_threshold=0.88)
    if det_plan is None:
        return None
    return normalize_portfolio_plan_from_question(question, det_plan)


def make_plan(
    question: str,
    *,
    prior_context: dict[str, Any] | None = None,
    query_log: Any = None,
    telemetry: Any = None,
) -> ExecutionPlan | None:
    """The structured planning LLM call. Emits a validated ExecutionPlan."""
    from news_rag.config import get_settings

    settings = get_settings()
    if not llm_api_key_configured(settings):
        return _slot_fallback(question)

    from news_rag.insight.question_intent import planner_supplement_for_question

    user = f"Question:\n{question.strip()}"
    supplement = planner_supplement_for_question(question)
    if supplement:
        user += f"\n\n{supplement}"
    if isinstance(prior_context, dict) and prior_context.get("memory"):
        user += "\n\nConversation memory: " + json.dumps(prior_context["memory"], ensure_ascii=False)

    try:
        from news_rag.llm_client import planner_model, planner_provider
        from news_rag.prompts import shared_system_prefix

        res = call_json_llm(
            system_prompt=plan_system_prompt(),
            user_content=user,
            model_override=planner_model(settings),
            provider_override=planner_provider(settings),
            max_tokens=1800,
            temperature=0.0,
            query_log=query_log,
            response_schema=PLAN_SCHEMA,
            stage="plan",
            enable_gemini_context_cache=True,
            cached_system_prefix=shared_system_prefix(),
        )
    except Exception as exc:  # noqa: BLE001
        if query_log is not None:
            query_log.write(f"PLAN_FAIL error={str(exc)[:200]}")
        return _slot_fallback(question)

    if telemetry is not None and res is not None:
        telemetry.add_llm_usage(
            stage="plan",
            provider=res.provider,
            model=res.model,
            input_tokens=res.input_tokens,
            output_tokens=res.output_tokens,
            cached_input_tokens=getattr(res, "cached_tokens", 0),
            total_ms=round(res.duration_sec * 1000, 1),
            usage_source="api",
        )

    data = res.parsed if isinstance(res.parsed, dict) else {}
    if not data:
        return _slot_fallback(question)

    plan = parse_plan(data)
    plan.random_fund_count = min(
        plan.random_fund_count, int(getattr(settings, "insight_fan_out_cap", 8))
    )
    from news_rag.insight.planner_policy import finalize_planner_plan

    plan = finalize_planner_plan(question, plan)
    if query_log is not None:
        query_log.write(
            f"PLANNER authoritative tools={plan.tool_names} answer_mode={plan.answer_mode.value} "
            f"request_count={plan.planner_count} request_slice={plan.planner_portfolio_slice or 'none'} "
            f"data_need={getattr(plan, 'data_need', 'none')} subject_ref={getattr(plan, 'subject_ref', 'none')} "
            f"fund_pick={getattr(plan, 'fund_pick', 'none')} reading={getattr(plan, 'planner_reading', '')[:120]!r} "
            f"window_days={plan.window_days} window_label={plan.window_label}"
        )
    return plan


_invalidate_plan_system_cache()

__all__ = [
    "PLAN_SCHEMA",
    "Plan",
    "ExecutionPlan",
    "make_plan",
    "parse_plan",
    "plan_system_prompt",
    "plan_to_brief",
    "tools_to_facets",
]
