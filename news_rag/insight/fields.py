"""Closed list of attributes a basic question can ask for.

The planner names these on request.fields. A regex on the current question
fills any the planner skips. Nothing is copied from an earlier turn.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from news_rag.insight.contracts import ExecutionPlan, ToolCall

_RETURN_RE = re.compile(r"^return:([A-Z0-9]+)$")
_WINDOW_RE = re.compile(r"^[0-9]+[DWMY]$|^YTD$|^INCEPTION$")


@dataclass(frozen=True)
class FieldNeed:
    """Smallest tool slice that can answer one attribute."""

    tool: str
    slot: str  # get_fund_data module, get_portfolio_data section, or investor module
    label: str
    book: bool = False


# Fund attributes. return:<code> is added at lookup time, not listed here.
FUND_FIELDS: dict[str, FieldNeed] = {
    "identity": FieldNeed("get_fund_data", "snapshot", "About this fund"),
    "category": FieldNeed("get_fund_data", "snapshot", "Category"),
    "fund_type": FieldNeed("get_fund_data", "snapshot", "Fund type"),
    "plan_type": FieldNeed("get_fund_data", "snapshot", "Plan"),
    "option": FieldNeed("get_fund_data", "snapshot", "Option"),
    "inception_date": FieldNeed("get_fund_data", "snapshot", "Inception date"),
    "fund_age": FieldNeed("get_fund_data", "snapshot", "Fund age"),
    "benchmark": FieldNeed("get_fund_data", "snapshot", "Benchmark"),
    "nav": FieldNeed("get_fund_data", "snapshot", "NAV"),
    "nav_change_1d": FieldNeed("get_fund_data", "snapshot", "Day change"),
    "range_52w": FieldNeed("get_fund_data", "snapshot", "52-week range"),
    "aum": FieldNeed("get_fund_data", "snapshot", "AUM"),
    "expense_ratio": FieldNeed("get_fund_data", "snapshot", "Expense ratio"),
    "expense_direct": FieldNeed("get_fund_data", "snapshot", "Direct expense ratio"),
    "exit_load": FieldNeed("get_fund_data", "snapshot", "Exit load"),
    "return_since_inception": FieldNeed("get_fund_data", "snapshot", "Return since inception"),
    "benchmark_return": FieldNeed("get_fund_data", "vs_benchmark", "Benchmark return"),
    "vs_benchmark": FieldNeed("get_fund_data", "vs_benchmark", "Versus benchmark"),
    "category_avg": FieldNeed("get_fund_data", "vs_benchmark", "Category average"),
    "lock_in": FieldNeed("get_fund_data", "limits", "Lock-in"),
    "min_sip": FieldNeed("get_fund_data", "limits", "Minimum SIP"),
    "min_lumpsum": FieldNeed("get_fund_data", "limits", "Minimum lumpsum"),
    "min_additional": FieldNeed("get_fund_data", "limits", "Minimum additional purchase"),
    "redemption_period": FieldNeed("get_fund_data", "limits", "Redemption settlement"),
    "sip_frequencies": FieldNeed("get_fund_data", "limits", "SIP frequencies"),
    "demat_physical": FieldNeed("get_fund_data", "limits", "Demat or physical"),
    "asset_allocation": FieldNeed("get_fund_data", "composition", "Asset allocation"),
    "market_cap_mix": FieldNeed("get_fund_data", "composition", "Market-cap mix"),
    "stock_count": FieldNeed("get_fund_data", "composition", "Number of stocks"),
    "top_n_weight": FieldNeed("get_fund_data", "composition", "Top-holdings weight"),
    "holdings": FieldNeed("get_portfolio_data", "holdings", "Holdings"),
    "holding_lookup": FieldNeed("get_portfolio_data", "holdings", "Holding lookup"),
    "sectors": FieldNeed("get_portfolio_data", "sectors", "Sectors"),
    "sector_lookup": FieldNeed("get_portfolio_data", "sectors", "Sector weight"),
    "riskometer": FieldNeed("get_fund_data", "risk", "SEBI riskometer"),
    "rs_rating": FieldNeed("get_fund_data", "rating", "RupeeStop rating"),
    "pillars": FieldNeed("get_fund_data", "rating", "Pillar scores"),
    "drawdown": FieldNeed("get_fund_data", "drawdown", "Drawdown"),
    "managers": FieldNeed("get_fund_data", "managers", "Fund manager"),
    "manager_tenure": FieldNeed("get_fund_data", "managers", "Manager tenure"),
    "past_managers": FieldNeed("get_fund_data", "managers", "Past managers"),
}

BOOK_FIELDS: dict[str, FieldNeed] = {
    "book_value": FieldNeed("get_investor_portfolio", "summary", "Portfolio value", book=True),
    "invested": FieldNeed("get_investor_portfolio", "summary", "Amount invested", book=True),
    "gain_abs": FieldNeed("get_investor_portfolio", "summary", "Gain or loss", book=True),
    "gain_pct": FieldNeed("get_investor_portfolio", "summary", "Gain or loss percent", book=True),
    "scheme_count": FieldNeed(
        "get_investor_portfolio",
        "summary",
        "Number of open schemes with current value (excludes zero-balance folios)",
        book=True,
    ),
    "holdings_list": FieldNeed("get_investor_portfolio", "holdings", "Holdings", book=True),
    "largest_holding": FieldNeed("get_investor_portfolio", "holdings", "Largest holding", book=True),
    "smallest_holding": FieldNeed("get_investor_portfolio", "holdings", "Smallest holding", book=True),
    "amcs": FieldNeed("get_investor_portfolio", "holdings", "AMCs", book=True),
    "holding_rs_labels": FieldNeed("get_investor_portfolio", "holdings", "RupeeStop labels", book=True),
    "categories": FieldNeed("get_investor_portfolio", "allocation", "Categories", book=True),
    "asset_mix": FieldNeed("get_investor_portfolio", "allocation", "Asset mix", book=True),
    "book_xirr": FieldNeed("get_investor_portfolio", "xirr", "Portfolio XIRR", book=True),
    "holding_xirr": FieldNeed("get_investor_portfolio", "xirr", "Holding XIRR", book=True),
    "sip_list": FieldNeed("get_investor_portfolio", "sip", "SIP plans", book=True),
    "sip_total": FieldNeed("get_investor_portfolio", "sip", "Monthly SIP", book=True),
    "stp_list": FieldNeed("get_investor_portfolio", "stp", "STP plans", book=True),
    "concentration": FieldNeed("get_investor_portfolio", "concentration", "Concentration", book=True),
    "underlying_top": FieldNeed("get_investor_portfolio", "concentration", "Underlying holdings", book=True),
    "weakness": FieldNeed("get_investor_portfolio", "holdings", "Weakness", book=True),
    "book_risk": FieldNeed("get_investor_portfolio", "profile_risk", "Portfolio risk", book=True),
}

_LEGACY_FACT = {
    "nav": "nav",
    "aum": "aum",
    "expense_ratio": "expense",
    "expense_direct": "expense",
    "exit_load": "exit_load",
    "benchmark": "benchmark",
    "benchmark_return": "benchmark",
    "rs_rating": "rs_rating",
    "drawdown": "drawdown",
    "managers": "managers",
    "manager_tenure": "managers",
    "past_managers": "managers",
    "riskometer": "risk",
    "holdings": "holdings",
    "holding_lookup": "holdings",
    "sectors": "sectors",
    "sector_lookup": "sectors",
}


def planner_field_names() -> list[str]:
    """Names the planner may emit, including the common return codes."""
    codes = ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "5Y", "YTD", "INCEPTION"]
    return [*FUND_FIELDS, *[f"return:{code}" for code in codes], *BOOK_FIELDS]


def field_need(name: str) -> FieldNeed | None:
    if name in FUND_FIELDS:
        return FUND_FIELDS[name]
    if name in BOOK_FIELDS:
        return BOOK_FIELDS[name]
    match = _RETURN_RE.match(name)
    if match and _WINDOW_RE.match(match.group(1)):
        return FieldNeed("get_fund_data", "snapshot", f"{match.group(1)} return")
    return None


def canonicalize_field(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    key = text.lower().replace(" ", "_")
    if key in FUND_FIELDS or key in BOOK_FIELDS:
        return key
    upper = text.upper().replace(" ", "")
    if upper.startswith("RETURN:"):
        from news_rag.insight.return_windows import normalize_window_code

        code = normalize_window_code(upper.split(":", 1)[1])
        return f"return:{code}" if code else ""
    return ""


def field_label(name: str) -> str:
    need = field_need(name)
    return need.label if need else name


def _unique(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


_BOOK_RE = re.compile(
    r"\b(?:my|mine|i\s+hold|i\s+own|our)\b|\bmy\s+portfolio\b|\bmy\s+book\b",
    re.I,
)
_WHOLE_BOOK_RE = re.compile(
    r"\b(?:my\s+portfolio|my\s+book|my\s+holdings|all\s+my\s+funds|my\s+mutual\s+funds?)\b",
    re.I,
)
_COMPARISON_TABLE_RE = re.compile(
    r"\b(?:fund\b.*\b(?:benchmark|bench)\b.*\bcategory\b|"
    r"benchmark\b.*\bfund\b.*\bcategory\b|"
    r"category\b.*\bbenchmark\b|"
    r"benchmark\s+vs\b|\bvs\b.*\bcategory\s+avg|"
    r"\b(?:fund|scheme)\b.*\bvs\b.*\b(?:benchmark|bench)\b|"
    r"\b(?:benchmark|bench)\b.*\bvs\b.*\bfund\b|"
    r"\b(?:fund|scheme)\b.*\bvs\b.*\bcategory\b|"
    r"\bcategory\b.*\bvs\b.*\bfund\b)",
    re.I,
)
_BENCHMARK_RETURN_RE = re.compile(
    r"\bbenchmark\s+return\b|\breturn\s+of\s+(?:the\s+)?benchmark\b|"
    r"\b(?:what\s+is|how\s+much\s+is)\s+(?:the\s+)?benchmark\s+return\b",
    re.I,
)


def _asks_book(question: str) -> bool:
    return bool(_BOOK_RE.search(question or ""))


def _return_fields(question: str) -> list[str]:
    from news_rag.fund_rupeestop_metrics import periods_requested_in_question

    return [f"return:{code}" for code in periods_requested_in_question(question or "")]


def fields_from_question(question: str) -> list[str]:
    """Attributes named in this message. Empty when the question is not a fact ask."""
    q = question or ""
    if not q.strip():
        return []
    from news_rag.fund_risk import asks_about_score_bands, asks_rating_concept

    if asks_rating_concept(q) or asks_about_score_bands(q):
        return []
    if _asks_book(q) and _book_fields(q):
        # "NAV of my HDFC fund" is still a fund fact. A whole-book ask is not.
        book = _book_fields(q)
        if book and not re.search(r"\b(?:of|for)\s+my\s+\w+\s+fund\b", q, re.I):
            if _WHOLE_BOOK_RE.search(q) or not re.search(
                r"\b(?:nav|expense|exit\s+load|benchmark|sectors?|manager)\b",
                q,
                re.I,
            ):
                return book
            if set(book) & {
                "holdings_list",
                "largest_holding",
                "smallest_holding",
                "book_value",
                "invested",
                "gain_abs",
                "gain_pct",
                "scheme_count",
            }:
                return book
    return _fund_fields(q)


def _book_fields(question: str) -> list[str]:
    q = question or ""
    found: list[str] = []
    if re.search(r"\b(?:portfolio\s+value|current\s+value|my\s+aum|aum\s+of\s+my)\b", q, re.I):
        found.append("book_value")
    if re.search(r"\bhow\s+much\s+(?:have\s+)?i\s+invested\b|\binvested\s+amount\b|\bmoney\s+invested\b", q, re.I):
        found.append("invested")
    low = q.lower()
    if "invested" not in found and "how much" in low and "invested" in low and "have" in low:
        found.append("invested")
    if any(f"invested in {label}" in low for label in ("equity", "debt", "hybrid")):
        found.append("asset_mix")
    if re.search(r"\bgain\s+or\s+loss\s+percent|\bgain\s*%|\bpercentage\s+gain\b", q, re.I):
        found.append("gain_pct")
    elif re.search(r"\bgain\b|\bloss\b|\bp\s*&\s*l\b|\bpnl\b", q, re.I):
        found.append("gain_abs")
    if re.search(r"\bhow\s+many\s+(?:schemes|funds)\b|\bnumber\s+of\s+(?:schemes|funds)\b", q, re.I):
        found.append("scheme_count")
    if re.search(r"\b(?:list|show)\s+(?:all\s+)?my\s+(?:funds|holdings|schemes)\b|\bwhat\s+do\s+i\s+(?:own|hold)\b", q, re.I):
        found.append("holdings_list")
    if re.search(
        r"\b(?:top|largest|biggest)\s+(?:\d+\s+)?(?:holdings?|funds?|schemes?)\b",
        q,
        re.I,
    ):
        found.append("holdings_list")
    if re.search(r"\blargest\b", q, re.I):
        found.append("largest_holding")
    if re.search(r"\bsmallest\b", q, re.I):
        found.append("smallest_holding")
    if re.search(r"\bamcs?\b", q, re.I):
        found.append("amcs")
    if re.search(r"\b(?:categories|category\s+mix)\b", q, re.I):
        found.append("categories")
    if re.search(r"\basset\s+mix\b|\bequity\s+vs\s+debt\b|\bmostly\s+equity\b", q, re.I):
        found.append("asset_mix")
    if re.search(r"\bxirr\b", q, re.I):
        found.append("holding_xirr" if re.search(r"\bmy\s+\w+\s+fund\b", q, re.I) else "book_xirr")
    if re.search(r"\bstp\b", q, re.I):
        found.append("stp_list")
    if re.search(r"\bsips?\b", q, re.I):
        found.append("sip_total" if re.search(r"\b(?:total|per\s+month|monthly)\b", q, re.I) else "sip_list")
    if re.search(r"\bunderlying\b|\btop\s+stocks\s+across\b", q, re.I):
        found.append("underlying_top")
    elif re.search(r"\bconcentrat\w*\b|\bdiversif\w*\b", q, re.I):
        found.append("concentration")
    if re.search(r"\b(?:weakness|drawback|underperform|biggest\s+drag|worst\s+fund)\b", q, re.I):
        found.append("weakness")
    if re.search(r"\brisk\s+of\s+my\s+portfolio\b", q, re.I):
        found.append("book_risk")
    if re.search(r"\brs\s+(?:rating|label|score)\b|\brupee\s*stop\b", q, re.I):
        found.append("holding_rs_labels")
    if re.search(
        r"\bwhat\s+is\s+my\s+portfolio\s*\??\s*$|\btell\s+me\s+about\s+my\s+(?:portfolio|holdings)\b",
        q,
        re.I,
    ):
        found.extend(["book_value", "invested", "scheme_count", "holdings_list"])
    return _unique(found)


def wants_comparison_table(question: str, plan: ExecutionPlan | None = None) -> bool:
    """Fund vs benchmark vs category — show the 1Y/3Y/5Y table, not one-line slots."""
    q = question or ""
    if _BENCHMARK_RETURN_RE.search(q) and not re.search(r"\bvs\b|\bversus\b|\bcompare\b", q, re.I):
        return False
    if _COMPARISON_TABLE_RE.search(q):
        return True
    if re.search(r"\bbenchmark\b", q, re.I) and re.search(r"\bcategory\b", q, re.I):
        if re.search(r"\bvs\b|\bversus\b|\bfund\b|\baverage\b|\bavg\b", q, re.I):
            return True
    if plan is not None:
        if str(plan.data_need or "") == "category_performance":
            return True
        fields = set(plan.asked_fields or [])
        if fields & {"vs_benchmark", "category_avg"}:
            if str(plan.intent or "") == "compare":
                return True
            if re.search(r"\bvs\b|\bversus\b|\bcompare\b|\bperformance\b", q, re.I):
                return True
    return False


def _fund_fields(question: str) -> list[str]:
    q = question or ""
    found: list[str] = []
    if wants_comparison_table(q):
        found: list[str] = []
        if re.search(r"\bbenchmark|\bbench\b", q, re.I):
            found.append("vs_benchmark")
        if re.search(r"\bcategory\b", q, re.I):
            found.append("category_avg")
        if not found:
            found = ["vs_benchmark", "category_avg"]
        return _unique(found)
    if _BENCHMARK_RETURN_RE.search(q):
        found.append("benchmark_return")
        if re.search(r"\bfund\b.*\breturn\b|\breturn\b.*\bfund\b", q, re.I):
            found.extend(_return_fields(q))
        return _unique(found)
    if re.search(r"\b(?:which\s+)?category\b", q, re.I) and not re.search(
        r"\b(?:best in category|good choice|recommended|underperformer|average)\b",
        q,
        re.I,
    ):
        found.append("category")
    if re.search(r"\bregular\s+plan\b|\bdirect\s+plan\b", q, re.I):
        found.append("plan_type")
    if re.search(r"\bgrowth\b|\bidcw\b|\bdividend\s+option\b", q, re.I) and re.search(
        r"\boption\b|\bgrowth\s+or\b|\bor\s+idcw\b", q, re.I
    ):
        found.append("option")
    if re.search(r"\b(?:inception|launch(?:ed)?|when\s+was\s+.+\blaunch)\b", q, re.I):
        found.append("inception_date")
    if re.search(r"\bhow\s+old\b|\bfund\s+age\b|\bscheme\s+age\b", q, re.I):
        found.append("fund_age")
    if re.search(r"\bbenchmark\b", q, re.I) and not _BENCHMARK_RETURN_RE.search(q):
        found.append("benchmark")
    if re.search(r"\b(?:equity|debt|hybrid)\b", q, re.I) and re.search(
        r"\btype\s+of\s+fund\b|\bwhat\s+type\b", q, re.I
    ):
        found.append("fund_type")
    if re.search(r"\b(?:nav|net\s+asset\s+value|current\s+price)\b", q, re.I):
        found.append("nav")
    if re.search(r"\b(?:day\s+change|daily\s+move|change\s+today|nav\s+change)\b", q, re.I):
        found.append("nav_change_1d")
    if re.search(r"\b52[\s-]*week\b", q, re.I):
        found.append("range_52w")
    if re.search(r"\baum\b|assets?\s+under\s+management", q, re.I):
        found.append("aum")
    if re.search(r"\bdirect\b", q, re.I) and re.search(r"\bexpense|\bter\b", q, re.I):
        found.append("expense_direct")
    if re.search(r"\bexpense\s+ratio\b|\bter\b|total\s+expense", q, re.I):
        found.append("expense_ratio")
    if re.search(r"\bexit\s+load\b", q, re.I):
        found.append("exit_load")
    if re.search(r"\bsince\s+inception\b", q, re.I):
        found.append("return_since_inception")
    if re.search(r"\bvs\.?\s+benchmark\b|\bversus\s+(?:its\s+)?benchmark\b|\bbeating\b|\blagging\b|\balpha\b", q, re.I):
        found.append("vs_benchmark")
        if "benchmark" in found and not re.search(r"\bwhat\s+is\s+(?:the\s+)?benchmark\b", q, re.I):
            found.remove("benchmark")
    if re.search(r"\bcategory\s+average\b|\bvs\.?\s+peers\b|\bpeer\b", q, re.I):
        found.append("category_avg")
    if re.search(r"\block[\s-]*in\b", q, re.I):
        found.append("lock_in")
    if re.search(r"\bmin(?:imum)?\s+sip\b|\bsip\s+amount\b", q, re.I):
        found.append("min_sip")
    if re.search(r"\b(?:lumpsum|lump\s+sum)\b", q, re.I):
        found.append("min_lumpsum")
    if re.search(r"\badditional\s+purchase\b", q, re.I):
        found.append("min_additional")
    if re.search(r"\bredemption\b|\bsettlement\b|\bdays\s+to\s+get\s+money\b", q, re.I):
        found.append("redemption_period")
    if re.search(r"\bsip\s+frequenc", q, re.I):
        found.append("sip_frequencies")
    if re.search(r"\bdemat\b|\bphysical\b", q, re.I) and re.search(r"\binvest\b", q, re.I):
        found.append("demat_physical")
    if re.search(r"\basset\s+allocation\b|\bequity\s+vs\s+cash\b", q, re.I):
        found.append("asset_allocation")
    if re.search(r"\bmarket\s+cap\s+mix\b|\bmid\s+and\s+small\b|\blarge\s*/\s*mid\b", q, re.I):
        found.append("market_cap_mix")
    if re.search(r"\bhow\s+many\s+stocks\b|\bnumber\s+of\s+stocks\b", q, re.I):
        found.append("stock_count")
    if re.search(r"\bconcentrat\w*\b|\bdiversif\w*\b|\btop\s+\d+\s+stock\s+weight\b", q, re.I):
        found.append("top_n_weight")
    if re.search(
        r"\b(?:banks?|banking|financials|pharma|auto|fmcg)\b|\bit\s+sector\b|\bin\s+it\b",
        q,
        re.I,
    ) and re.search(
        r"\b(?:how\s+much|exposure|weight|tilted)\b",
        q,
        re.I,
    ):
        found.append("sector_lookup")
    elif re.search(
        r"\bdoes\s+(?:it|this\s+fund|the\s+fund|my\s+fund)\s+hold\b|"
        r"\bhow\s+much\s+(?:of\s+the\s+fund\s+)?is\s+in\b",
        q,
        re.I,
    ):
        found.append("holding_lookup")
    elif re.search(r"\bholdings?\b|\bwhich\s+stocks\b|\bstocks?\s+does\s+it\b", q, re.I):
        found.append("holdings")
    if re.search(r"\bsectors?\b", q, re.I):
        if re.search(r"\bhow\s+much\s+is\s+in\b|\bexposure\b|\bbanking\b|\bfinancials\b", q, re.I):
            found.append("sector_lookup")
        else:
            found.append("sectors")
    if re.search(r"\briskometer\b", q, re.I):
        found.append("riskometer")
    elif re.search(r"\bhow\s+risky\b|\brisk\s+analysis\b", q, re.I):
        found.append("riskometer")
    if re.search(r"\bpillar\b", q, re.I):
        found.append("pillars")
    if re.search(r"\brupee\s*stop\b|\brs\s+(?:rating|score|label)\b", q, re.I):
        found.append("rs_rating")
    if re.search(r"\bdrawdown\b|\bmax(?:imum)?\s+fall\b", q, re.I):
        found.append("drawdown")
    if re.search(r"\bpast\s+managers?\b", q, re.I):
        found.append("past_managers")
    elif re.search(r"\btenure\b|\bhow\s+long\s+has\s+the\s+manager\b|\bexperience\b", q, re.I):
        found.append("manager_tenure")
    elif re.search(r"\b(?:fund\s+)?managers?\b|\bwho\s+manages\b", q, re.I):
        found.append("managers")
    returns = _return_fields(q)
    if returns:
        found.extend(returns)
    elif re.search(r"\b(?:performing|performance|historical\s+performance|up\s+or\s+down)\b", q, re.I):
        found.extend(["return:1M", "return:1Y", "return:3Y"])
    # "What is HDFC Large Cap?" with no other attribute is the identity sentence.
    if not found and re.search(r"\bwhat\s+is\b|\btell\s+me\s+about\b", q, re.I):
        if re.search(r"\bfund\b", q, re.I) and not re.search(
            r"\b(?:large|mid|small|multi|flexi)\s+cap\s+fund\s*\??\s*$",
            q,
            re.I,
        ):
            found.append("identity")
        elif re.search(
            r"\b(?:hdfc|icici|sbi|axis|kotak|bandhan|parag|quant|invesco|nippon|mirae)\b",
            q,
            re.I,
        ):
            found.append("identity")
    return _unique(found)


def resolve_asked_fields(question: str, plan: ExecutionPlan) -> list[str]:
    """Current question wins. Planner fields are used only when the regex finds nothing."""
    from_question = fields_from_question(question)
    if from_question:
        return from_question
    return _unique([canonicalize_field(item) for item in (plan.asked_fields or [])])


def _legacy_facts(fields: list[str]) -> list[str]:
    out: list[str] = []
    for name in fields:
        if name.startswith("return:"):
            mapped = "returns"
        else:
            mapped = _LEGACY_FACT.get(name, "")
        if mapped and mapped not in out:
            out.append(mapped)
    return out


_PROTECTED_TOOLS = frozenset({
    "compare_funds",
    "screen_funds_by_exposure",
    "search_financial_news",
    "get_macro_news",
    "get_market_snapshot",
})


def _leave_tools_alone(question: str, plan: ExecutionPlan) -> bool:
    if wants_comparison_table(question, plan):
        return True
    if str(plan.intent or "") in ("explain_cause", "overview", "compare", "rank", "outlook"):
        return True
    if plan.answer_mode.value != "DATA_ONLY":
        return True
    if any(call.tool in _PROTECTED_TOOLS for call in plan.tool_calls or []):
        return True
    try:
        from news_rag.insight.investor_drawback import (
            plan_wants_fund_concentration,
            plan_wants_portfolio_drawback,
        )

        if plan_wants_fund_concentration(plan, question) or plan_wants_portfolio_drawback(plan, question):
            return True
    except Exception:
        pass
    from news_rag.insight.portfolio_intents import normalize_portfolio_intent, shape_for

    intent = normalize_portfolio_intent(getattr(plan, "portfolio_intent", ""))
    if (
        shape_for(intent) == "fact"
        and any(c.tool == "get_investor_portfolio" for c in plan.tool_calls or [])
    ):
        return True
    return False


def _top_n(question: str, plan: ExecutionPlan) -> int:
    count = int(plan.planner_count or 0)
    match = re.search(r"\btop\s+(\d+)\b", question or "", re.I)
    if match:
        count = max(count, int(match.group(1)))
    if re.search(r"\b(?:all|full|every)\s+holdings?\b", question or "", re.I):
        count = max(count, 50)
    return count or 5


def _find_term(question: str, kind: str) -> str:
    q = question or ""
    if kind == "holding":
        match = re.search(r"\bhold\s+([A-Za-z][A-Za-z0-9& .'-]{1,40})", q, re.I)
        if match:
            return match.group(1).strip(" ?.")
    if kind == "sector":
        for token in ("banks", "banking", "financials", "it", "pharma", "auto", "fmcg"):
            if re.search(rf"\b{token}\b", q, re.I):
                return "banks" if token in ("banking", "financials") else token
    return ""


def bind_fields_to_tools(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Fetch the modules these attributes need, and drop modules a lookup did not ask for."""
    fields = resolve_asked_fields(question, plan)
    plan.asked_fields = fields
    if not fields:
        return plan
    mapped = _legacy_facts(fields)
    if mapped:
        plan.asked_facts = mapped

    comparison_fields = {"benchmark_return", "vs_benchmark", "category_avg"}
    needs_comparison_fetch = bool(comparison_fields & set(fields))

    if _leave_tools_alone(question, plan):
        if needs_comparison_fetch:
            windows: list[str] = []
            if "benchmark_return" in fields and not wants_comparison_table(question, plan):
                from news_rag.fund_rupeestop_metrics import periods_requested_in_question

                windows = periods_requested_in_question(question) or []
            _set_fund_call(plan, ["vs_benchmark"], windows, False, question, fields)
        return plan

    fund_modules: list[str] = []
    sections: list[str] = []
    investor_modules: list[str] = []
    windows: list[str] = []
    pillars = False
    for name in fields:
        need = field_need(name)
        if need is None:
            continue
        if name.startswith("return:"):
            windows.append(name.split(":", 1)[1])
        if name == "pillars":
            pillars = True
        if need.tool == "get_fund_data" and need.slot not in fund_modules:
            fund_modules.append(need.slot)
        elif need.tool == "get_portfolio_data" and need.slot not in sections:
            sections.append(need.slot)
        elif need.tool == "get_investor_portfolio" and need.slot not in investor_modules:
            investor_modules.append(need.slot)

    if needs_comparison_fetch:
        fund_modules = ["vs_benchmark"]
        windows = []
    if fund_modules:
        _set_fund_call(plan, fund_modules, windows, pillars, question, fields)
    if sections:
        _set_portfolio_call(plan, sections, _top_n(question, plan), question, fields)
    if investor_modules:
        _set_investor_call(plan, investor_modules, question)
    return plan


def _set_fund_call(
    plan: ExecutionPlan,
    modules: list[str],
    windows: list[str],
    pillars: bool,
    question: str,
    fields: list[str] | None = None,
) -> None:
    call = next((item for item in plan.tool_calls if item.tool == "get_fund_data"), None)
    if call is None:
        call = ToolCall(tool="get_fund_data", arguments={}, wave=1)
        plan.tool_calls = [call, *plan.tool_calls]
    args = dict(call.arguments or {})
    args["modules"] = modules
    if windows:
        args["windows"] = windows
    elif "snapshot" in modules and "vs_benchmark" not in modules:
        asked = set(fields or plan.asked_fields or [])
        if asked & {"benchmark_return", "vs_benchmark", "category_avg"}:
            args.pop("windows", None)
        elif not any(name.startswith("return:") for name in asked):
            args["windows"] = ["1D"] if "nav_change_1d" in asked else ["1Y"]
    if pillars:
        args["pillars"] = True
    else:
        args.pop("pillars", None)
    if "drawdown" in modules and not args.get("periods"):
        args["periods"] = ["1y", "3y", "5y"]
    call.arguments = args
    del question


def _set_portfolio_call(
    plan: ExecutionPlan,
    sections: list[str],
    top_n: int,
    question: str,
    fields: list[str],
) -> None:
    call = next((item for item in plan.tool_calls if item.tool == "get_portfolio_data"), None)
    if call is None:
        call = ToolCall(tool="get_portfolio_data", arguments={}, wave=1)
        plan.tool_calls.append(call)
    args = dict(call.arguments or {})
    args["sections"] = sections
    args["top_n"] = top_n
    if "holding_lookup" in fields:
        found = _find_term(question, "holding")
        if found:
            args["find"] = found
    elif "sector_lookup" in fields:
        found = _find_term(question, "sector")
        if found:
            args["find"] = found
    call.arguments = args


def _set_investor_call(plan: ExecutionPlan, modules: list[str], question: str) -> None:
    del question
    from news_rag.insight.portfolio_intents import modules_for, normalize_portfolio_intent

    intent = normalize_portfolio_intent(getattr(plan, "portfolio_intent", ""))
    if intent != "none":
        for slot in modules_for(intent):
            if slot not in modules:
                modules.append(slot)
    call = next((item for item in plan.tool_calls if item.tool == "get_investor_portfolio"), None)
    if call is None:
        call = ToolCall(tool="get_investor_portfolio", arguments={}, wave=1)
        plan.tool_calls = [call, *plan.tool_calls]
    args = dict(call.arguments or {})
    args["modules"] = modules
    if "holdings" in modules and not args.get("holdings_fields"):
        args["holdings_fields"] = "standard"
    call.arguments = args


def field_prompt_table() -> str:
    """Compact field-to-module map for the planner prompt."""
    lines = [
        "request.fields lists ONLY the attributes asked in this message. Never copy fields from Conversation memory.",
        "A follow-up that adds a fact lists every fact in that new message (AUM, then AUM and expense ratio, lists both).",
        "field -> tool slot",
    ]
    seen: set[str] = set()
    for name, need in {**FUND_FIELDS, **BOOK_FIELDS}.items():
        key = f"{need.tool}:{need.slot}"
        if key in seen:
            continue
        seen.add(key)
        names = [
            item
            for item, other in {**FUND_FIELDS, **BOOK_FIELDS}.items()
            if other.tool == need.tool and other.slot == need.slot
        ]
        lines.append(f"- {', '.join(names)} -> {need.tool} {need.slot}")
    lines.append("- return:1W, return:1M, return:3M, return:6M, return:1Y, return:3Y, return:5Y, return:YTD -> get_fund_data snapshot windows of those codes only")
    return "\n".join(lines)
