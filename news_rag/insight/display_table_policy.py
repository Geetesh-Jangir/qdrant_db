"""Decide which fund comparison tables belong in the user-facing answer."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from news_rag.fund_rupeestop_metrics import (
    asks_fund_category_average,
    periods_requested_in_question,
    resolve_display_periods,
)
from news_rag.insight.contracts import AnswerMode, ExecutionPlan

TABLE_SHORT = "short_horizon_vs_category_table"
TABLE_LONG = "vs_benchmark_table"
TABLE_HOLDINGS = "holdings_move_table"
TABLE_SNAPSHOT = "snapshot_table"
TABLE_FUND_FACTS = "fund_facts_table"
TABLE_CATEGORY = "category_average_table"
TABLE_PORTFOLIO = "portfolio_holdings_table"
TABLE_SECTORS = "portfolio_sectors_table"
TABLE_COMPOSITION = "composition_table"
TABLE_RETURNS = "fund_returns_table"

_ALL_KEYS = frozenset({
    TABLE_SHORT,
    TABLE_LONG,
    TABLE_HOLDINGS,
    TABLE_SNAPSHOT,
    TABLE_FUND_FACTS,
    TABLE_CATEGORY,
    TABLE_PORTFOLIO,
    TABLE_SECTORS,
    TABLE_COMPOSITION,
    TABLE_RETURNS,
})

_NEWS_RE = re.compile(
    r"\b(?:news|headlines?|articles?|stories|coverage|press|media|announcements?)\b",
    re.I,
)
_PERF_RE = re.compile(
    r"\b(?:"
    r"return|returns|perform(?:ance|ing)?|vs\.?|versus|benchmark|category\s*avg(?:erage)?|"
    r"underperform(?:ed|ing)?|outperform(?:ed|ing)?|lag(?:ged|ging)?|beat(?:en)?|"
    r"nav|how\s+(?:is|did|has|was)|doing|fell|fallen|rose|drop(?:ped)?|down|up|"
    r"compare|comparison|relative|gap|alpha|"
    r"1\s*y(?:r|ear)?|3\s*y(?:r|ear)?|5\s*y(?:r|ear)?|"
    r"why\s+(?:did|has|is)|what\s+(?:drove|caused|happened)|attribution|"
    r"holdings?\s+that\s+drove|top\s+(?:gainers?|losers?|contributors?|detractors?)"
    r")\b",
    re.I,
)
_HOLDINGS_RE = re.compile(
    r"\b(?:hold(?:s|ing)?|holdings?|portfolio|composition|sectors?\s+allocation|"
    r"what\s+(?:does|this|that|it)\b.{0,40}\bhold(?:s|ing)?|top\s+stocks?)\b",
    re.I,
)
_NAV_SNAPSHOT_RE = re.compile(
    r"\b(?:nav|net\s+asset|52\s*week|fifty[-\s]?two|aum|expense\s+ratio|current\s+price)\b",
    re.I,
)
_WHY_RE = re.compile(
    r"\b(?:why\s+(?:did|has|is)|reason|cause|what\s+(?:drove|caused|happened|made)|explain\s+the\s+move)\b",
    re.I,
)
_OVERVIEW_RE = re.compile(
    r"\b(?:tell me about|overview of|how is|summar(?:y|ize)|about)\b",
    re.I,
)


_BENCHMARK_RE = re.compile(r"\bbenchmark\b", re.I)


def _plan_fetches_vs_benchmark(plan: ExecutionPlan | None) -> bool:
    if not plan:
        return False
    for call in plan.tool_calls or []:
        if call.tool != "get_fund_data":
            continue
        modules = {str(m).lower() for m in (call.arguments or {}).get("modules") or []}
        if "vs_benchmark" in modules:
            return True
    return False


@dataclass(frozen=True)
class DisplayTablePolicy:
    """Which pre-rendered markdown tables to append after compose."""

    include: frozenset[str] = field(default_factory=frozenset)
    rationale: str = ""

    def for_composer(self) -> dict[str, Any]:
        return {
            "tables_in_answer": sorted(self.include),
            "tables_rationale": self.rationale,
        }

    def wants_any(self) -> bool:
        return bool(self.include)


def _news_primary(question: str) -> bool:
    q = question or ""
    return bool(_NEWS_RE.search(q)) and not bool(_PERF_RE.search(q)) and not _WHY_RE.search(q)


def _named_fund_overview(question: str, plan: ExecutionPlan | None) -> bool:
    """A 'tell me about this fund' ask, not a news-only or why-it-moved ask."""
    q = question or ""
    if _NEWS_RE.search(q) or _WHY_RE.search(q):
        return False
    funds = list(plan.funds or []) if plan else []
    intent = (plan.intent if plan else "") or ""
    about = bool(_OVERVIEW_RE.search(q))
    if funds and (intent == "overview" or about):
        return True
    return intent == "overview" and about


def resolve_display_table_policy(
    question: str,
    plan: ExecutionPlan | None = None,
) -> DisplayTablePolicy:
    q = (question or "").strip()
    intent = (plan.intent if plan else "") or ""
    mode = plan.answer_mode if plan else AnswerMode.INSIGHT_FUSION
    window_days = int(plan.window_days) if plan else 30

    if asks_fund_category_average(q):
        inc = {TABLE_CATEGORY, TABLE_LONG}
        return DisplayTablePolicy(
            include=inc,
            rationale="User asked for category average — show category and full 1Y/3Y/5Y comparison.",
        )

    requested = periods_requested_in_question(q)
    long_rows, short_rows = resolve_display_periods(requested)
    user_named_periods = bool(requested)
    wants_short = user_named_periods and bool(short_rows)
    wants_long = user_named_periods and bool(long_rows)
    if user_named_periods and not wants_short and not wants_long:
        wants_long = True

    if mode == AnswerMode.DATA_ONLY:
        inc: set[str] = set()
        if asks_fund_category_average(q):
            inc.update({TABLE_CATEGORY, TABLE_LONG})
        elif _plan_fetches_vs_benchmark(plan) or _BENCHMARK_RE.search(q):
            inc.add(TABLE_LONG)
        elif _PERF_RE.search(q) or intent in ("lookup", "compare"):
            holdings_only = _HOLDINGS_RE.search(q) and not _PERF_RE.search(q)
            if not holdings_only:
                inc.add(TABLE_RETURNS)
                if wants_short:
                    inc.add(TABLE_SHORT)
                if wants_long:
                    inc.add(TABLE_LONG)
        if _HOLDINGS_RE.search(q):
            inc.update({TABLE_PORTFOLIO, TABLE_SECTORS, TABLE_COMPOSITION})
        if _WHY_RE.search(q):
            inc.add(TABLE_HOLDINGS)
        if _NAV_SNAPSHOT_RE.search(q) or not inc:
            inc.add(TABLE_SNAPSHOT)
        return DisplayTablePolicy(
            include=frozenset(inc & _ALL_KEYS),
            rationale="DATA_ONLY lookup — tables match explicit metrics asked.",
        )

    if intent == "explain_cause" or _WHY_RE.search(q):
        inc = {TABLE_RETURNS, TABLE_SHORT, TABLE_HOLDINGS, TABLE_LONG}
        if _NAV_SNAPSHOT_RE.search(q):
            inc.add(TABLE_SNAPSHOT)
        return DisplayTablePolicy(
            include=frozenset(inc),
            rationale="Explain move — returns vs peers/benchmark and holdings attribution.",
        )

    if _news_primary(q):
        explicit_horizon = user_named_periods or bool(
            re.search(
                r"\b(?:last|past|recent|this)\s+(?:(?:\d+|one|two|three|six|twelve)\s+)?"
                r"(?:day|days|week|weeks|month|months|quarter|quarters|year|years)\b",
                q,
                re.I,
            )
        )
        if explicit_horizon:
            return DisplayTablePolicy(
                include=frozenset({TABLE_SHORT}),
                rationale="News-focused question with a time window — short return vs category anchor only.",
            )
        return DisplayTablePolicy(
            include=frozenset(),
            rationale="News-focused question — no vs-benchmark/category tables; narrative and news only.",
        )

    if _named_fund_overview(q, plan):
        inc = {TABLE_FUND_FACTS}
        if re.search(r"\b(?:returns?|performance|performing)\b", q, re.I):
            inc.update({TABLE_RETURNS, TABLE_SHORT, TABLE_LONG})
        if re.search(r"\bholdings?\b|\btop\s+stocks?\b|\bwhat\s+(?:does|do)\s+it\s+hold\b", q, re.I):
            inc.update({TABLE_HOLDINGS, TABLE_PORTFOLIO, TABLE_COMPOSITION})
        if re.search(r"\bsectors?\b|\bsector\s+allocation\b", q, re.I):
            inc.update({TABLE_SECTORS, TABLE_COMPOSITION})
        return DisplayTablePolicy(
            include=frozenset(inc),
            rationale="Named-fund overview — a short fund table, plus returns, holdings, or sectors only when asked.",
        )

    inc = set()
    asks_returns = bool(re.search(r"\b(?:returns?|performance|performing)\b", q, re.I))
    if asks_returns or _PERF_RE.search(q):
        if asks_returns or intent in ("compare",):
            inc.add(TABLE_RETURNS)
            if wants_short:
                inc.add(TABLE_SHORT)
            if wants_long:
                inc.add(TABLE_LONG)
    if _HOLDINGS_RE.search(q):
        inc.update({TABLE_PORTFOLIO, TABLE_SECTORS, TABLE_COMPOSITION})
    if _WHY_RE.search(q):
        inc.add(TABLE_HOLDINGS)
    if _NAV_SNAPSHOT_RE.search(q):
        inc.add(TABLE_SNAPSHOT)

    if not inc and plan and "attribution" in str(plan.tool_names):
        inc.add(TABLE_HOLDINGS)

    if _PERF_RE.search(q) and TABLE_SHORT not in inc and TABLE_LONG not in inc:
        inc.update({TABLE_SHORT, TABLE_LONG})

    rationale = "Tables match performance / holdings / NAV signals in the question."
    if not inc:
        rationale = "No comparison or holdings signals — skip vs-format tables."

    return DisplayTablePolicy(include=frozenset(inc & _ALL_KEYS), rationale=rationale)


def filter_display_tables(
    tables: dict[str, str],
    policy: DisplayTablePolicy,
) -> dict[str, str]:
    if not tables or not policy.wants_any():
        out = {_k: tables[_k] for _k in ("_title",) if _k in tables}
        return out
    out: dict[str, str] = {}
    if tables.get("_title"):
        out["_title"] = tables["_title"]
    for key in policy.include:
        if tables.get(key):
            out[key] = tables[key]
            heading = tables.get(f"_heading_{key}")
            if heading:
                out[f"_heading_{key}"] = heading
    return out
