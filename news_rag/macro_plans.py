"""Deterministic plans for common research questions (no investor-book lookup)."""

from __future__ import annotations

import re

from news_rag.fund_search import (
    collect_fund_phrase_candidates,
    extract_fund_phrase_from_question,
    is_macro_metals_question,
)
from news_rag.query_plan import DataNeed, QueryPlan, SubQuery

PRESET_SOURCES = frozenset(
    {
        "macro_metals",
        "preset_crude_energy",
        "preset_fund_insights",
        "preset_market_pulse",
        "preset_sector_tape",
    }
)


def is_crude_energy_question(question: str) -> bool:
    lower = (question or "").lower()
    oil = bool(re.search(r"\b(barrel+s?|brent|wti|crude|oil\s+price|petroleum)\b", lower))
    if not oil:
        return False
    if re.search(r"\b(hdfc|icici|axis|kotak|sbi|nippon|mirae)\b.+\bfund\b", lower):
        return False
    return bool(
        re.search(
            r"\b(sector|energy|fund|funds|invested|affect|impact|omc|power|refiner)\b",
            lower,
        )
    )


def is_market_pulse_question(question: str) -> bool:
    lower = (question or "").lower()
    if is_macro_metals_question(question) or is_crude_energy_question(question):
        return False
    if re.search(r"\b(hdfc|icici|axis|kotak|sbi|nippon|mirae)\b.+\bfund\b", lower):
        return False
    return bool(
        re.search(
            r"\b(what('?s| is) hot|hot in the market|how'?s the market|"
            r"how is the market|market doing|what to focus on|"
            r"current market|market right now|market currently)\b",
            lower,
        )
    )


def is_sector_tape_question(question: str) -> bool:
    lower = (question or "").lower()
    if not re.search(r"\bsectors?\b", lower):
        return False
    if re.search(r"\b(hdfc|icici|axis|kotak)\b.+\bfund\b", lower):
        return False
    return bool(
        re.search(
            r"\b(positive|postive|negative|last month|past month|doing well|laggard|winner|loser)\b",
            lower,
        )
    )


def _fund_phrase_for_insights(question: str) -> str:
    candidates = collect_fund_phrase_candidates(question)
    if candidates:
        return candidates[0]
    _isin, name = extract_fund_phrase_from_question(question)
    if _isin:
        return _isin
    return (name or "").strip()


def is_fund_insights_question(question: str) -> bool:
    lower = (question or "").lower()
    if is_macro_metals_question(question) or is_crude_energy_question(question):
        return False
    if is_market_pulse_question(question) or is_sector_tape_question(question):
        return False
    if not _fund_phrase_for_insights(question):
        return False
    return bool(
        re.search(
            r"\b(insight|insights|tell me about|what.?s happening|"
            r"invested in|news (on|for|about)|how is .{0,40}(doing|working)|"
            r"update on|brief on)\b",
            lower,
        )
    )


def skip_scheme_resolution(question: str, plan_source: str = "") -> bool:
    if plan_source in PRESET_SOURCES and plan_source != "preset_fund_insights":
        return True
    if is_macro_metals_question(question):
        return True
    if is_crude_energy_question(question):
        return True
    if is_market_pulse_question(question) or is_sector_tape_question(question):
        return True
    return False


def try_macro_metals_plan(question: str) -> QueryPlan | None:
    if not is_macro_metals_question(question):
        return None
    return QueryPlan(
        sub_queries=[
            SubQuery(
                id="Q1",
                text="Recent gold and silver price moves",
                answer_style="news_brief",
                needs_reasoning=True,
                data_needs=[
                    DataNeed(tool="metals_spot"),
                    DataNeed(
                        tool="news_search",
                        semantic_query=(
                            "gold silver prices fall decline reasons India MCX bullion "
                            "imports dollar rupee profit booking"
                        ),
                        scope="macro_bullion",
                        window_days=21,
                    ),
                ],
            ),
            SubQuery(
                id="Q2",
                text="Mutual funds with gold and silver exposure",
                answer_style="short_list",
                needs_reasoning=False,
                data_needs=[
                    DataNeed(
                        tool="sector_funds",
                        semantic_query="gold silver precious metals non ferrous",
                        top_n=8,
                    ),
                ],
            ),
        ],
        source="macro_metals",
    )


def try_crude_energy_plan(question: str) -> QueryPlan | None:
    if not is_crude_energy_question(question):
        return None
    return QueryPlan(
        sub_queries=[
            SubQuery(
                id="Q1",
                text="Crude barrel price news and energy sectors",
                answer_style="news_brief",
                needs_reasoning=True,
                data_needs=[
                    DataNeed(
                        tool="news_search",
                        semantic_query="crude oil Brent barrel prices India energy OMCs refiners power",
                        scope="event_only",
                        window_days=30,
                    ),
                ],
            ),
            SubQuery(
                id="Q2",
                text="Funds with high energy and oil-product exposure",
                answer_style="short_list",
                needs_reasoning=False,
                data_needs=[
                    DataNeed(
                        tool="sector_funds",
                        semantic_query="energy oil petroleum power crude barrel",
                        top_n=8,
                    ),
                ],
            ),
        ],
        source="preset_crude_energy",
    )


def _fund_insights_focus(question: str) -> str:
    """full | holdings | sectors — narrow tool set when user asks for one slice only."""
    lower = (question or "").lower()
    holdings_only = bool(
        re.search(
            r"\b(top\s+holdings?|holdings?\s+only|portfolio\s+stocks?|what\s+stocks?|which\s+stocks?|"
            r"underlying\s+stocks?|companies\s+held)\b",
            lower,
        )
    )
    sectors_only = bool(
        re.search(
            r"\b(sector\s+allocation|sector\s+breakdown|sector\s+exposure|sectors?\s+only|"
            r"what\s+sectors?|industry\s+allocation)\b",
            lower,
        )
    )
    if sectors_only and not holdings_only:
        return "sectors"
    if holdings_only and not sectors_only:
        return "holdings"
    return "full"


def try_fund_insights_plan(question: str) -> QueryPlan | None:
    if not is_fund_insights_question(question):
        return None
    fund_raw = _fund_phrase_for_insights(question) or "HDFC Defence Fund"
    focus = _fund_insights_focus(question)
    sub_queries: list[SubQuery] = []

    if focus != "sectors":
        sub_queries.append(
            SubQuery(
                id="Q1",
                text=f"{fund_raw} performance",
                answer_style="performance_summary",
                needs_reasoning=False,
                data_needs=[
                    DataNeed(tool="fund_nav", fund_raw=fund_raw, scope="with_returns"),
                ],
            )
        )

    if focus == "sectors":
        sub_queries.append(
            SubQuery(
                id="Q1",
                text=f"{fund_raw} sector allocation",
                answer_style="short_list",
                needs_reasoning=False,
                data_needs=[
                    DataNeed(tool="fund_nav", fund_raw=fund_raw, scope="latest_only"),
                    DataNeed(tool="fund_sectors", fund_raw=fund_raw, scope="top_n", top_n=8),
                ],
            )
        )
    elif focus == "holdings":
        sub_queries.append(
            SubQuery(
                id="Q2",
                text=f"{fund_raw} top holdings",
                answer_style="short_list",
                needs_reasoning=False,
                data_needs=[
                    DataNeed(tool="fund_holdings", fund_ref="Q1", scope="top_n", top_n=10),
                ],
            )
        )
    else:
        sub_queries.append(
            SubQuery(
                id="Q2",
                text=f"{fund_raw} holdings and sectors",
                answer_style="short_list",
                needs_reasoning=False,
                data_needs=[
                    DataNeed(tool="fund_holdings", fund_ref="Q1", scope="top_n", top_n=8),
                    DataNeed(tool="fund_sectors", fund_ref="Q1", scope="top_n", top_n=6),
                ],
            )
        )

    sub_queries.append(
        SubQuery(
            id="Q3",
            text=f"News on {fund_raw} holdings, sectors, and macro",
            answer_style="exposure_note",
            needs_reasoning=True,
            data_needs=[
                DataNeed(
                    tool="fund_portfolio_news",
                    fund_ref="Q1",
                    scope="top_n",
                    top_n=10,
                    window_days=30,
                ),
            ],
        ),
    )

    return QueryPlan(sub_queries=sub_queries, source="preset_fund_insights")


def try_market_pulse_plan(question: str) -> QueryPlan | None:
    if not is_market_pulse_question(question):
        return None
    return QueryPlan(
        sub_queries=[
            SubQuery(
                id="Q1",
                text="What is moving Indian markets now",
                answer_style="news_brief",
                needs_reasoning=True,
                data_needs=[
                    DataNeed(
                        tool="news_search",
                        semantic_query="India stock market Nifty Sensex sector movers crude RBI rupee",
                        scope="event_only",
                        window_days=14,
                    ),
                ],
            ),
        ],
        source="preset_market_pulse",
    )


def try_sector_tape_plan(question: str) -> QueryPlan | None:
    if not is_sector_tape_question(question):
        return None
    return QueryPlan(
        sub_queries=[
            SubQuery(
                id="Q1",
                text="Sectors with constructive news last month",
                answer_style="news_brief",
                needs_reasoning=True,
                data_needs=[
                    DataNeed(
                        tool="news_search",
                        semantic_query="India sectors rally gain outperform last month banks IT auto defence",
                        scope="event_only",
                        window_days=30,
                    ),
                ],
            ),
            SubQuery(
                id="Q2",
                text="Sectors under pressure last month",
                answer_style="news_brief",
                needs_reasoning=True,
                data_needs=[
                    DataNeed(
                        tool="news_search",
                        semantic_query="India sectors decline pressure lag last month oil metals realty",
                        scope="event_only",
                        window_days=30,
                    ),
                ],
            ),
        ],
        source="preset_sector_tape",
    )


def try_preset_plan(question: str) -> QueryPlan | None:
    """First matching research preset; order is metals → crude → fund insights → sectors → market."""
    return (
        try_macro_metals_plan(question)
        or try_crude_energy_plan(question)
        or try_fund_insights_plan(question)
        or try_sector_tape_plan(question)
        or try_market_pulse_plan(question)
    )
