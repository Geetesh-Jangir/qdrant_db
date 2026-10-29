"""The planner: ONE structured LLM call that reads the question and emits an ExecutionPlan.

Uses the six capability facades (get_fund_data, get_portfolio_data, compare_funds,
search_financial_news, screen_funds_by_exposure, get_market_snapshot).
The planner schema enforces wave assignment (wave 1 vs wave 2) and deterministic
wave 2 trigger policies.

Slot rules replace bulky prompt examples to minimize prompt bloat and overfitting.
"""

from __future__ import annotations

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
    )
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
- `understanding.task`: explain or data. explain means the user wants to understand a word, a fund type, or which categories exist, including a misspelled question such as "what are multi cap fund" or "sub category of the equity funds". data means they want a number, a list of schemes, a rating, or one named fund. A screen hint that names a category does not make an explanation into a fund list.
- `understanding.answer_mode`: DATA_ONLY, NEWS_ONLY, INSIGHT_FUSION.
- `entities.funds`, `entities.sectors`, `entities.stocks`: string arrays, as the user wrote them. Correct an obvious misspelling of a name they did give. Do not invent a fund they did not name.
- `entities.drivers`: objects {{"id", "direction"}}. id is one of: {', '.join(DRIVER_IDS)}. direction is up, down, tighten, ease, weaken, or strengthen. Do not use macro_drivers.
- `request`: count (integer), portfolio_slice (holdings, sectors, both, none), reading (one sentence). Required when the question is about what is inside one fund. Otherwise set portfolio_slice to none and count to 0.
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
You are the sole routing authority. Read the question as a person would. A misspelling still means the intended word.

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
1. DATA_ONLY is a metric lookup: a NAV, a top-N holdings or sectors list, a comparison table, a definition. Do not call search_financial_news. trigger is none.
2. "Tell me about <fund>", "how is <fund>", or any overview of one named fund is INSIGHT_FUSION, not DATA_ONLY. Wave 1 gets snapshot, returns, attribution, and the portfolio. Wave 2 always calls search_financial_news with scope all and top_n 8. The answer must connect those articles to the holdings and the return.
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

Tell me about one fund:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Overview of HDFC Large Cap with news tied to its holdings", "intent": "overview", "answer_mode": "INSIGHT_FUSION", "query_class": "standard"}}, "request": {{"count": 5, "portfolio_slice": "both", "reading": "Overview of HDFC Large Cap Fund"}}, "entities": {{"funds": ["HDFC Large Cap Fund"]}}, "time": {{"window_days": 30}}, "tool_calls": [{{"tool": "get_fund_data", "arguments": {{"modules": ["snapshot", "return_series", "attribution"]}}, "wave": 1}}, {{"tool": "get_portfolio_data", "arguments": {{"sections": ["holdings", "sectors"], "top_n": 5}}, "wave": 1}}, {{"tool": "search_financial_news", "arguments": {{"scope": "all", "top_n": 8, "window_days": 30}}, "wave": 2}}], "wave_2_policy": {{"trigger": "always", "max_calls": 1}}, "presentation": {{"response_shape": "sections", "max_words": 420, "notes": "Connect holdings and the return to the articles"}}}}

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
{{"request": {{"count": 0, "portfolio_slice": "none", "reading": "Compare HDFC Top 100 and Axis Bluechip"}}, "scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Compare two named funds", "intent": "compare", "answer_mode": "DATA_ONLY", "query_class": "standard"}}, "entities": {{"funds": ["HDFC Top 100 Fund", "Axis Bluechip Fund"]}}, "tool_calls": [{{"tool": "compare_funds", "arguments": {{"mode": "both"}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "table", "max_words": 150}}}}

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


def make_plan(
    question: str,
    *,
    prior_context: dict[str, Any] | None = None,
    query_log: Any = None,
    telemetry: Any = None,
) -> ExecutionPlan | None:
    """The structured planning LLM call. Emits a validated ExecutionPlan."""
    from news_rag.config import get_settings
    from news_rag.insight.slot_router import slot_route

    settings = get_settings()
    det_plan = slot_route(question, confidence_threshold=0.88)
    if not llm_api_key_configured(settings):
        return det_plan

    from news_rag.insight.question_intent import planner_supplement_for_question

    user = f"Question:\n{question.strip()}"
    supplement = planner_supplement_for_question(question)
    if supplement:
        user += f"\n\n{supplement}"
    if prior_context:
        user += f"\n\nPrevious conversation turns: {prior_context}"

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
        from news_rag.insight.portfolio_plan import normalize_portfolio_plan_from_question

        return normalize_portfolio_plan_from_question(question, det_plan) if det_plan else det_plan

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
        from news_rag.insight.portfolio_plan import normalize_portfolio_plan_from_question

        return normalize_portfolio_plan_from_question(question, det_plan) if det_plan else det_plan

    plan = parse_plan(data)
    plan.random_fund_count = min(
        plan.random_fund_count, int(getattr(settings, "insight_fan_out_cap", 8))
    )
    from news_rag.insight.planner_policy import finalize_planner_plan

    plan = finalize_planner_plan(question, plan)
    if not plan.tool_calls and det_plan and det_plan.tool_calls:
        if query_log is not None:
            query_log.write("PLANNER_EMPTY_TOOLS fallback=deterministic_slot_plan")
        from news_rag.insight.portfolio_plan import normalize_portfolio_plan_from_question

        return normalize_portfolio_plan_from_question(question, det_plan)
    if query_log is not None:
        query_log.write(
            f"PLANNER authoritative tools={plan.tool_names} answer_mode={plan.answer_mode.value} "
            f"request_count={plan.planner_count} request_slice={plan.planner_portfolio_slice or 'none'} "
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
