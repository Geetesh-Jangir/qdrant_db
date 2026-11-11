"""Maps a planner-named portfolio_intent to modules and answer shape.

Does not read the question. Unknown values are none.
"""

from __future__ import annotations

from news_rag.insight.contracts import AnswerMode, ExecutionPlan

FACT = frozenset({
    "aum",
    "invested",
    "overall_return",
    "xirr",
    "scheme_count",
    "nav_of_scheme",
    "next_sip",
    "sip_list",
    "stp_list",
    "dividends",
    "risk_profile",
    "st_vs_lt_gains",
    "list_holdings",
    "top_holdings",
    "allocation",
})

INSIGHT_CARD = frozenset({
    "scheme_performance",
    "where_losing",
    "sector_exposure",
    "stock_overlap",
})

BRIEF = frozenset({
    "portfolio_overview",
    "health_check",
    "risk_alignment",
    "sip_review",
    "period_change",
    "fy_summary",
})

PORTFOLIO_INTENTS = ("none",) + tuple(sorted(FACT | INSIGHT_CARD | BRIEF))

_MODULES: dict[str, tuple[str, ...]] = {
    "aum": ("summary",),
    "invested": ("summary",),
    "overall_return": ("summary",),
    "xirr": ("summary", "xirr"),
    "scheme_count": ("summary", "holdings"),
    "nav_of_scheme": ("holdings",),
    "next_sip": ("sip",),
    "sip_list": ("sip",),
    "stp_list": ("stp",),
    "dividends": ("pnl_summary",),
    "risk_profile": ("profile_risk",),
    "st_vs_lt_gains": ("pnl_summary", "pnl_scheme"),
    "list_holdings": ("holdings",),
    "top_holdings": ("holdings",),
    "allocation": ("allocation", "summary"),
    "scheme_performance": ("holdings", "xirr"),
    "where_losing": ("holdings", "summary"),
    "sector_exposure": ("concentration", "allocation"),
    "stock_overlap": ("concentration",),
    "portfolio_overview": ("summary", "allocation", "holdings", "xirr", "concentration"),
    "health_check": ("summary", "allocation", "holdings", "profile_risk", "sip", "concentration"),
    "risk_alignment": ("allocation", "profile_risk", "holdings"),
    "sip_review": ("sip", "holdings", "xirr"),
    "period_change": ("summary", "pnl_scheme", "holdings", "meta"),
    "fy_summary": ("meta", "pnl_summary", "xirr", "sip", "summary"),
}

_DATA_NEED: dict[str, str] = {
    "aum": "investor_summary",
    "invested": "investor_summary",
    "overall_return": "investor_summary",
    "xirr": "investor_xirr",
    "scheme_count": "investor_holding",
    "nav_of_scheme": "investor_holding",
    "next_sip": "investor_sip",
    "sip_list": "investor_sip",
    "stp_list": "investor_stp",
    "dividends": "investor_pnl",
    "risk_profile": "investor_risk",
    "st_vs_lt_gains": "investor_pnl",
    "list_holdings": "investor_holding",
    "top_holdings": "investor_holding",
    "allocation": "investor_summary",
    "scheme_performance": "investor_xirr",
    "where_losing": "investor_holding",
    "sector_exposure": "investor_risk",
    "stock_overlap": "investor_risk",
    "portfolio_overview": "investor_hybrid",
    "health_check": "investor_risk",
    "risk_alignment": "investor_risk",
    "sip_review": "investor_sip",
    "period_change": "investor_pnl",
    "fy_summary": "investor_pnl",
}

_TABLE_INTENTS = frozenset({
    "sip_list", "stp_list", "list_holdings", "top_holdings", "allocation",
    "sector_exposure", "stock_overlap", "where_losing",
})

_NEWS_TOOLS = frozenset({"search_financial_news"})


def normalize_portfolio_intent(raw: str | None) -> str:
    value = str(raw or "").strip().lower()
    return value if value in PORTFOLIO_INTENTS else "none"


def shape_for(intent: str) -> str:
    name = normalize_portfolio_intent(intent)
    if name in FACT:
        return "fact"
    if name in INSIGHT_CARD:
        return "insight_card"
    if name in BRIEF:
        return "brief"
    return "none"


def modules_for(intent: str) -> list[str]:
    return list(_MODULES.get(normalize_portfolio_intent(intent)) or [])


def data_need_for(intent: str) -> str:
    return _DATA_NEED.get(normalize_portfolio_intent(intent)) or ""


def should_attach_news(intent: str, *, planner_intent: str = "", answer_mode: str = "") -> bool:
    """News only for briefs, a losing-money card, or a planner explain/fusion ask."""
    name = normalize_portfolio_intent(intent)
    if name in FACT or name in (INSIGHT_CARD - {"where_losing"}):
        return False
    if name == "where_losing" or name in BRIEF:
        return True
    if str(planner_intent or "").lower() == "explain_cause":
        return True
    if str(answer_mode or "") == AnswerMode.INSIGHT_FUSION.value and name != "none":
        return True
    return False


def apply_portfolio_intent(plan: ExecutionPlan) -> ExecutionPlan:
    """Seed scope, modules are applied later. Fact intents skip the composer and news."""
    intent = normalize_portfolio_intent(getattr(plan, "portfolio_intent", ""))
    plan.portfolio_intent = intent
    if intent == "none":
        return plan
    if str(plan.portfolio_scope or "").lower().strip() in ("none", "", "catalog"):
        plan.portfolio_scope = "investor"
    if str(plan.data_need or "").lower().strip() in ("", "none"):
        need = data_need_for(intent)
        if need:
            plan.data_need = need
    if shape_for(intent) == "fact":
        plan.answer_mode = AnswerMode.DATA_ONLY
        plan.requires_compose = False
        plan.response_shape = "table" if intent in _TABLE_INTENTS else "short_answer"
        plan.tool_calls = [c for c in (plan.tool_calls or []) if c.tool not in _NEWS_TOOLS]
        if plan.wave_2_policy is not None:
            plan.wave_2_policy.trigger = "none"
    elif shape_for(intent) == "insight_card" and intent != "where_losing":
        plan.answer_mode = AnswerMode.DATA_ONLY
        plan.tool_calls = [c for c in (plan.tool_calls or []) if c.tool not in _NEWS_TOOLS]
    elif not should_attach_news(
        intent,
        planner_intent=plan.intent,
        answer_mode=plan.answer_mode.value,
    ):
        plan.tool_calls = [c for c in (plan.tool_calls or []) if c.tool not in _NEWS_TOOLS]
    return plan
