"""The planner: ONE structured LLM call that reads the question and emits an ExecutionPlan.

Uses the six capability facades (get_fund_data, get_portfolio_data, compare_funds,
search_financial_news, screen_funds_by_exposure, get_market_snapshot).
The planner schema enforces wave assignment (wave 1 vs wave 2) and deterministic
wave 2 trigger policies.

Slot rules replace bulky prompt examples to minimize prompt bloat and overfitting.
"""

from __future__ import annotations

import re
from typing import Any

from news_rag.insight.brief import QuestionBrief, SubAsk, nearest_return_window
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
from news_rag.insight.registry import all_tools, ensure_registry, get_tool, tools_providing
from news_rag.llm_client import call_json_llm, llm_api_key_configured, router_model

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
        "tool_calls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": list(CAPABILITIES.keys())},
                    "arguments": {"type": "object"},
                    "wave": {"type": "integer", "enum": [1, 2]},
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
    "required": ["scope", "understanding", "tool_calls"],
}


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
        wave = int(raw_tc.get("wave") or 1)
        if wave not in (1, 2):
            wave = 1
        tool_calls.append(ToolCall(
            tool=tool_name,
            arguments=valid_args,
            wave=wave,
            required=bool(raw_tc.get("required", True)),
            why=str(raw_tc.get("why") or ""),
        ))

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
    )
    return plan


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


def plan_system_prompt() -> str:
    global _SYSTEM_CACHE
    if _SYSTEM_CACHE is not None:
        return _SYSTEM_CACHE

    catalog = capability_catalog_text()
    prompt = f"""You are the planner for an Indian mutual fund, stock, and market analytics assistant.
Read the user's question and emit ONE structured JSON ExecutionPlan using ONLY the six capabilities below.

### CAPABILITY TOOLS
{catalog}

### SLOT RULES
1. **answer_mode**:
   - `DATA_ONLY`: Pure metric lookups (NAV, returns, top holdings, benchmark, 52-week high/low, sector rankings). Do NOT call search_financial_news. Wave 2 policy is "none".
   - `NEWS_ONLY`: General macro news queries without fund numbers (e.g. "latest news on RBI rate hike").
   - `INSIGHT_FUSION`: Explain moves, "why did fund fall", fund outlook, or multi-factor analysis combining metrics with news.
2. **Waves**:
   - Wave 1: Independent data tools needed to answer the question (`get_fund_data`, `get_portfolio_data`, `compare_funds`, `get_market_snapshot`, `screen_funds_by_exposure`).
   - Wave 2: Run conditionally via `wave_2_policy` (e.g., trigger `search_financial_news` if fund negative return < -2% or holding weight > 5%).
3. **Caps**:
   - Limit `top_n` to 3 unless user explicitly requests more (e.g., "top 10 holdings" -> top_n: 10).
   - Maximum 1 Wave 2 call. Never plan more than 4 total tool calls.
4. **Entities**:
   - Extract exact fund names, sector names, stock names as user wrote them. Never invent fund names.
   - For macro drivers, use IDs: {', '.join(DRIVER_IDS)}.
5. **Presentation** (composer can mix bullets + tables inside sections when style is sections):
   - `response_shape`: short_answer (lookup), bullets (lists/holdings), paragraph (brief), table (compare/rankings — prefer ≤4 columns), sections (fusion: ### headings, bullets for drivers, tables for metrics).
   - `max_words`: 40-80 for lookups, 200-450 for fusions with tables.

### EXAMPLE SHAPES
Simple NAV lookup:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Check NAV of fund", "intent": "lookup", "answer_mode": "DATA_ONLY", "query_class": "simple"}}, "entities": {{"funds": ["HDFC Top 100"]}}, "tool_calls": [{{"tool": "get_fund_data", "arguments": {{"modules": ["snapshot"]}}, "wave": 1}}], "wave_2_policy": {{"trigger": "none"}}, "presentation": {{"response_shape": "short_answer", "max_words": 50}}}}

Why did fund fall:
{{"scope": {{"kind": "in_scope"}}, "understanding": {{"goal": "Explain recent underperformance", "intent": "explain_cause", "answer_mode": "INSIGHT_FUSION", "query_class": "standard"}}, "entities": {{"funds": ["Parag Parikh Flexi Cap"]}}, "time": {{"window_days": 30}}, "tool_calls": [{{"tool": "get_fund_data", "arguments": {{"modules": ["snapshot", "return_series", "attribution"]}}, "wave": 1}}, {{"tool": "get_portfolio_data", "arguments": {{"sections": ["holdings", "sectors"], "top_n": 3}}, "wave": 1}}], "wave_2_policy": {{"trigger": "negative_return", "threshold": -1.5, "max_calls": 1}}, "presentation": {{"response_shape": "sections", "max_words": 280}}}}
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

    settings = get_settings()
    if not llm_api_key_configured(settings):
        return None

    user = f"Question:\n{question.strip()}"
    if prior_context:
        user += f"\n\nPrevious conversation turns: {prior_context}"

    try:
        res = call_json_llm(
            system_prompt=plan_system_prompt(),
            user_content=user,
            model_override=router_model(settings),
            max_tokens=1800,
            temperature=0.0,
            query_log=query_log,
            response_schema=PLAN_SCHEMA,
            stage="plan",
        )
    except Exception as exc:  # noqa: BLE001
        if query_log is not None:
            query_log.write(f"PLAN_FAIL error={str(exc)[:200]}")
        return None

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
        return None

    plan = parse_plan(data)
    plan.random_fund_count = min(
        plan.random_fund_count, int(getattr(settings, "insight_fan_out_cap", 8))
    )
    return plan


__all__ = [
    "PLAN_SCHEMA",
    "Plan",
    "ExecutionPlan",
    "make_plan",
    "parse_plan",
    "plan_system_prompt",
    "plan_to_brief",
    "tools_to_facets",
    "nearest_return_window",
]
