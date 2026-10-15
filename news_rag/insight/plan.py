"""The planner: ONE LLM call that reads the question and decides everything.

It returns a single JSON plan: whether the question is in scope, which funds / sectors / stocks /
macro drivers it is about, the time frame, which tools to call (and only those), whether news is
needed and how deep, the sub-questions, and how the answer should be presented.

Nothing here matches keywords. The model decides; code only validates names against the registry
and resolves entity names against the fund and sector indexes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from news_rag.insight.brief import QuestionBrief, SubAsk, nearest_return_window
from news_rag.insight.registry import all_tools, ensure_registry, get_tool, tools_providing
from news_rag.llm_client import call_json_llm, llm_api_key_configured, router_model

SCOPE_KINDS = ("in_scope", "out_of_scope", "needs_clarification")
INTENTS = ("lookup", "explain_cause", "compare", "overview", "rank", "outlook")
NEWS_DEPTHS = ("none", "headlines", "detailed")
STYLES = ("short_answer", "bullets", "paragraph", "table", "sections")
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
            },
            "required": ["goal", "intent"],
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
        "direction": {"type": "string", "enum": ["any", "positive", "negative"]},
        "layer1": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "args": {"type": "object"},
                    "required": {"type": "boolean"},
                    "why": {"type": "string"},
                },
                "required": ["tool"],
            },
        },
        "layer2_news": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "enum": ["holdings", "sectors", "macro", "stock", "sector", "market"]},
                    "source": {},
                    "top_n": {"type": "integer"},
                    "window_days": {"type": "integer"},
                    "direction": {"type": "string"},
                    "articles_per_entity": {"type": "integer"},
                    "chars_per_article": {"type": "integer"},
                    "required": {"type": "boolean"},
                },
                "required": ["scope"],
            },
        },
        "asks_not_supported": {"type": "array", "items": {"type": "string"}},
        "sub_queries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "answered_by": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text"],
            },
        },
        "reasoning_depth": {"type": "string", "enum": list(DEPTHS)},
        "presentation": {
            "type": "object",
            "properties": {
                "style": {"type": "string", "enum": list(STYLES)},
                "max_words": {"type": "integer"},
                "lead_with": {"type": "string"},
                "notes": {"type": "string"},
            },
        },
        "clarification_question": {"type": "string"},
    },
    "required": ["scope", "understanding", "layer1", "presentation"],
}


@dataclass
class Plan:
    scope_kind: str = "in_scope"
    direct_reply: str = ""
    asks_for_advice: bool = False
    goal: str = ""
    intent: str = "lookup"
    funds: list[str] = field(default_factory=list)
    random_fund_count: int = 0
    random_fund_name_contains: str = ""
    sectors: list[str] = field(default_factory=list)
    stocks: list[str] = field(default_factory=list)
    drivers: list[dict[str, str]] = field(default_factory=list)
    window_days: int = 30
    window_label: str = "1 month"
    direction: str = "any"
    tool_calls: list[dict[str, str]] = field(default_factory=list)
    layer1: list[dict[str, Any]] = field(default_factory=list)
    layer2_news: list[dict[str, Any]] = field(default_factory=list)
    asks_not_supported: list[str] = field(default_factory=list)
    news_depth: str = "none"
    news_query: str = ""
    holding_attribution: bool = False
    sub_queries: list[dict[str, Any]] = field(default_factory=list)
    reasoning_depth: str = "standard"
    style: str = "paragraph"
    max_words: int = 220
    lead_with: str = ""
    presentation_notes: str = ""
    clarification_question: str = ""
    dropped_tools: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def tool_names(self) -> list[str]:
        return [t["tool"] for t in self.tool_calls]

    def summary(self) -> dict[str, Any]:
        """What the log shows: the decisions, not the whole JSON."""
        return {
            "scope": self.scope_kind,
            "intent": self.intent,
            "funds": self.funds,
            "random_funds": self.random_fund_count,
            "sectors": self.sectors,
            "stocks": self.stocks,
            "drivers": self.drivers,
            "window_days": self.window_days,
            "tools": self.tool_names,
            "layer1": [{"tool": c.get("tool"), "args": c.get("args")} for c in self.layer1],
            "layer2_news": [s.get("scope") for s in self.layer2_news],
            "dropped_tools": self.dropped_tools,
            "news_depth": self.news_depth,
            "attribution": self.holding_attribution,
            "depth": self.reasoning_depth,
            "style": self.style,
            "sub_queries": [s.get("text", "")[:60] for s in self.sub_queries],
        }


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if isinstance(v, (str, int, float)) and str(v).strip()]


def _pick_enum(value: Any, allowed: tuple[str, ...], default: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in allowed else default


def parse_plan(data: dict[str, Any]) -> Plan:
    ensure_registry()
    scope = data.get("scope") if isinstance(data.get("scope"), dict) else {}
    under = data.get("understanding") if isinstance(data.get("understanding"), dict) else {}
    ents = data.get("entities") if isinstance(data.get("entities"), dict) else {}
    when = data.get("time") if isinstance(data.get("time"), dict) else {}
    news = data.get("news") if isinstance(data.get("news"), dict) else {}
    compute = data.get("compute") if isinstance(data.get("compute"), dict) else {}
    pres = data.get("presentation") if isinstance(data.get("presentation"), dict) else {}
    rnd = ents.get("random_funds") if isinstance(ents.get("random_funds"), dict) else {}

    plan = Plan(raw=data)
    plan.scope_kind = _pick_enum(scope.get("kind"), SCOPE_KINDS, "in_scope")
    plan.direct_reply = str(scope.get("direct_reply") or "").strip()
    plan.asks_for_advice = bool(scope.get("asks_for_advice"))
    plan.goal = str(under.get("goal") or "").strip()
    plan.intent = _pick_enum(under.get("intent"), INTENTS, "lookup")
    plan.funds = _str_list(ents.get("funds"))
    try:
        plan.random_fund_count = max(0, min(10, int(rnd.get("count") or 0)))
    except (TypeError, ValueError):
        plan.random_fund_count = 0
    plan.random_fund_name_contains = str(rnd.get("name_contains") or "").strip()
    plan.sectors = _str_list(ents.get("sectors"))
    plan.stocks = _str_list(ents.get("stocks"))
    for d in ents.get("drivers") or []:
        if isinstance(d, dict) and str(d.get("id") or "").strip():
            plan.drivers.append(
                {"id": str(d["id"]).strip(), "direction": str(d.get("direction") or "").strip().lower()}
            )
        elif isinstance(d, str) and d.strip():
            plan.drivers.append({"id": d.strip(), "direction": ""})
    try:
        plan.window_days = max(1, min(1825, int(when.get("window_days") or 30)))
    except (TypeError, ValueError):
        plan.window_days = 30
    plan.window_label = str(when.get("label") or "").strip() or _label_for_days(plan.window_days)
    plan.direction = _pick_enum(data.get("direction"), ("any", "positive", "negative"), "any")

    from news_rag.insight.layer_tools import clamp_news_scope, clamp_tool_args

    raw_calls = data.get("layer1") or data.get("tool_calls") or []
    seen: set[str] = set()
    for call in raw_calls:
        name = str((call or {}).get("tool") if isinstance(call, dict) else call or "").strip()
        if not name or name in seen:
            continue
        if get_tool(name) is None:
            plan.dropped_tools.append(name)
            continue
        seen.add(name)
        args = clamp_tool_args(name, call.get("args") if isinstance(call, dict) else {})
        why = str(call.get("why") or "").strip() if isinstance(call, dict) else ""
        plan.layer1.append({"tool": name, "args": args, "required": bool(call.get("required", True)) if isinstance(call, dict) else True, "why": why})
        plan.tool_calls.append({"tool": name, "why": why})

    for scope in data.get("layer2_news") or []:
        clamped = clamp_news_scope(scope, default_window=plan.window_days)
        if clamped:
            plan.layer2_news.append(clamped)
    plan.asks_not_supported = _str_list(data.get("asks_not_supported"))[:6]

    plan.news_depth = "detailed" if plan.layer2_news else _pick_enum(news.get("depth"), NEWS_DEPTHS, "none")
    plan.news_query = str(news.get("search_query") or "").strip()
    plan.holding_attribution = bool(compute.get("holding_attribution")) or any(
        c["tool"] == "fund_attribution" for c in plan.layer1
    )
    for sq in data.get("sub_queries") or []:
        if isinstance(sq, dict) and str(sq.get("text") or "").strip():
            plan.sub_queries.append(
                {"text": str(sq["text"]).strip(), "answered_by": _str_list(sq.get("answered_by"))}
            )
        elif isinstance(sq, str) and sq.strip():
            plan.sub_queries.append({"text": sq.strip(), "answered_by": []})
    plan.reasoning_depth = _pick_enum(data.get("reasoning_depth"), DEPTHS, "standard")
    plan.style = _pick_enum(pres.get("style"), STYLES, "paragraph")
    try:
        plan.max_words = max(30, min(700, int(pres.get("max_words") or 220)))
    except (TypeError, ValueError):
        plan.max_words = 220
    plan.lead_with = str(pres.get("lead_with") or "").strip()
    plan.presentation_notes = str(pres.get("notes") or "").strip()
    plan.clarification_question = str(data.get("clarification_question") or "").strip()
    return plan


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


# ---------------------------------------------------------------------------
# Plan -> executable pieces
# ---------------------------------------------------------------------------


def tools_to_facets(tool_names: list[str]) -> tuple[list[str], dict[str, str]]:
    """Map the planner's tools onto facets so gather can run exactly those tools.

    Each tool claims one facet it provides. A facet that another chosen tool needs is preferred,
    so prerequisites resolve to the planner's own pick instead of a default provider.
    """
    ensure_registry()
    specs = [get_tool(n) for n in tool_names]
    specs = [s for s in specs if s is not None]
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


def plan_to_brief(plan: Plan, *, sector_keys: list[str], funds: list[str]) -> QuestionBrief:
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
    fund_list_tools = {"sector_funds", "driver_affected_funds", "screen_funds"}
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
        direction=plan.direction,
        wants_funds_flag=bool(fund_list_tools & set(plan.tool_names)),
        raw={"source": "plan", "news_query": plan.news_query},
    )


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def _clip(text: str, n: int) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def tool_catalog() -> str:
    """Only the data tools. News is a separate layer2_news block, not a tool name."""
    from news_rag.insight.layer_tools import ARG_HELP, PLANNER_TOOLS

    ensure_registry()
    by_name = {spec.name: spec for spec in all_tools()}
    lines: list[str] = []
    for name in PLANNER_TOOLS:
        spec = by_name.get(name)
        if spec is None:
            continue
        parts = [f"- {spec.name}: {_clip(spec.description, 180)}"]
        if spec.when_to_use:
            parts.append(f"  use: {_clip(spec.when_to_use, 160)}")
        if name in ARG_HELP:
            parts.append(f"  args: {_clip(ARG_HELP[name], 220)}")
        if spec.requires:
            needs = sorted({t.name for f in spec.requires for t in tools_providing(f) if t.name in PLANNER_TOOLS})
            if needs:
                parts.append("  needs first: " + " or ".join(needs))
        lines.append("\n".join(parts))
    return "\n".join(lines)


PLAN_SYSTEM = """You are the planner for an assistant that answers questions about Indian mutual funds, stocks, sectors and the market. Read the question once and return ONE JSON object. The system runs exactly what you write, so ask for the smallest set that answers the question.

DECIDE
1. scope.kind: in_scope, out_of_scope (short direct_reply, empty layer1), or needs_clarification (one clarification_question). asks_for_advice is true for buy, sell or hold questions; still plan the facts, never a recommendation.
2. understanding: goal in one sentence, intent one of lookup, explain_cause, compare, overview, rank, outlook.
3. entities as the user wrote them. random_funds.count when they want funds chosen for them (any 5 funds means count 5). Never invent a fund name. Drivers use ids __DRIVERS__ and direction one of __DIRECTIONS__.
4. time.window_days: today or this week 7, month 30, quarter 90, year 365. Default 30 for a fund or sector, 7 for the market.
5. layer1: data tools only, fewest that answer the question. Each item is {tool, args, required, why}. Default top_n_holdings and top_n_sectors to 3. Raise a count only when the user names a number: "top 15 holdings" means top_n_holdings 15 and top_n_sectors still 3 unless they also asked for sectors. A pure lookup (NAV, price, holdings list, category) has no layer2_news.
   For "how is this fund doing", "tell me about this fund", or "why did it move", include fund_snapshot, fund_portfolio (top 3 and top 3), fund_attribution (top_n 3), and index_return with index "benchmark".
6. layer2_news: news grouped by what it is about. Each item is {scope, source, top_n, window_days, direction, articles_per_entity, chars_per_article, required}.
   scope is holdings, sectors, macro, stock, sector or market.
   source is "layer1" to take names from the data tools (top holdings, top sectors, biggest movers) or a list of topics such as ["crude oil"] or ["RBI"].
   Default top_n is 3 for holdings, sectors and macro. Use a higher top_n only when the user asked for that many.
   For scope market with no topic list: use source layer1 (empty topics). The system runs eight parallel theme searches (Nifty, banks, RBI/liquidity, FII/DII, crude/inflation, earnings, banking credit, global risk). Default top_n 8 and articles_per_entity 3.
   For scope market when the user names a macro topic (crude oil, RBI, FII flows, earnings, etc.): set source to that topic list, e.g. ["crude oil"] or ["RBI repo rate"]. One search per topic; top_n equals the number of topics (max 8).
   For "how is this fund doing" or "tell me about this fund" use three scopes: holdings top_n 3, sectors top_n 3, and macro with source layer1 and empty topics so topics are derived from the fund's sectors.
   Leave layer2_news empty for a number, a holdings list, a price or a category.
7. asks_not_supported: expense ratio, AUM, fund manager, exit load, or anything else no tool can return. Do not invent a tool for them.
8. sub_queries: one per part of the question.
9. reasoning_depth: quick, standard or deep.
10. presentation: style short_answer, bullets, paragraph, table or sections. max_words 40 to 80 for a lookup. When layer2_news is not empty, use style sections and max_words about 480 so the answer can explain the move with the news. lead_with is the first sentence. notes is any format the user asked for.

EXAMPLES
- "nav of hdfc large cap": layer1=[{tool: fund_snapshot, args: {windows: ["1M"]}}], layer2_news=[], style short_answer.
- "top 15 holdings of hdfc large cap": layer1=[{tool: fund_portfolio, args: {top_n_holdings: 15, top_n_sectors: 3}}], layer2_news=[].
- "how is hdfc large cap doing" or "tell me about hdfc large cap": layer1=[fund_snapshot, fund_portfolio args top_n_holdings 3 top_n_sectors 3, fund_attribution top_n 3, index_return index benchmark], layer2_news=[holdings top_n 3, sectors top_n 3, macro source layer1], style sections, max_words 480.
- "why did parag parikh flexi cap fall this month": layer1=[fund_snapshot, fund_return_series, fund_portfolio top 3, fund_attribution top_n 3, index_return index benchmark], layer2_news=[holdings top_n 3, sectors top_n 3, macro source layer1], max_words 480.
- "price of hdfc bank": layer1=[stock_snapshot], layer2_news=[].
- "what is happening in the market" / "market right now": layer1=[index_return args index nifty50 window_days 7, sector_ranking window_days 7], layer2_news=[{scope: market, source: layer1, top_n: 8, window_days: 7, articles_per_entity: 3}], style sections, max_words 480.
- "what is RBI doing and how is the market reacting": layer1=[index_return nifty50, macro_series series yield usdinr], layer2_news=[{scope: market, source: ["RBI repo rate"], window_days: 14, articles_per_entity: 3}].
- "crude oil news impact on Indian market": layer1=[index_return nifty50, macro_series series crude], layer2_news=[{scope: market, source: ["crude oil"], window_days: 14, articles_per_entity: 3}].
- "which funds are hurt if crude rises": drivers crude_oil up, layer1=[macro_sector_impact, driver_affected_funds], layer2_news=[macro source ["crude oil"]].
- "expense ratio of X": layer1=[fund_snapshot], asks_not_supported=["expense ratio"].

TOOLS
__CATALOG__

Return JSON only."""


_system_cache: str | None = None


def plan_system_prompt() -> str:
    global _system_cache
    if _system_cache is None:
        _system_cache = (
            PLAN_SYSTEM.replace("__DRIVERS__", ", ".join(DRIVER_IDS))
            .replace("__DIRECTIONS__", ", ".join(DRIVER_DIRECTIONS))
            .replace("__CATALOG__", tool_catalog())
        )
    return _system_cache


def make_plan(
    question: str,
    *,
    prior_context: dict[str, Any] | None = None,
    query_log: Any = None,
) -> Plan | None:
    """The first and only planning LLM call. None means: use the legacy pipeline."""
    from news_rag.config import get_settings

    settings = get_settings()
    if not llm_api_key_configured(settings):
        return None
    user = f"Question:\n{question.strip()}"
    if prior_context:
        user += f"\n\nPrevious turn (for follow-ups): {prior_context}"
    try:
        res = call_json_llm(
            system_prompt=plan_system_prompt(),
            user_content=user,
            model_override=router_model(settings),
            max_tokens=2200,
            temperature=0.0,
            query_log=query_log,
            response_schema=PLAN_SCHEMA,
            stage="plan",
        )
    except Exception as exc:  # noqa: BLE001
        if query_log is not None:
            query_log.write(f"PLAN_FAIL error={str(exc)[:200]}")
        return None
    data = res.parsed if isinstance(res.parsed, dict) else {}
    if not data:
        return None
    plan = parse_plan(data)
    # The kind of fund count is the planner's call; keep the range sane for the gather fan-out.
    plan.random_fund_count = min(plan.random_fund_count, int(getattr(settings, "insight_fan_out_cap", 8)))
    return plan


__all__ = [
    "PLAN_SCHEMA",
    "Plan",
    "make_plan",
    "parse_plan",
    "plan_system_prompt",
    "plan_to_brief",
    "tool_catalog",
    "tools_to_facets",
    "nearest_return_window",
]
