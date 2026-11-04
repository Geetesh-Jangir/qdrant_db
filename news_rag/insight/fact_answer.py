"""One sentence per asked attribute. No extra facts, no answer LLM."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from news_rag.insight.contracts import AnswerMode, ExecutionPlan
from news_rag.insight.fields import field_label, field_need, wants_comparison_table

_NEWS_TOOLS = frozenset({"search_financial_news", "get_macro_news"})
_EXPLAIN_RE = re.compile(
    r"\b(?:what\s+does|meaning\s+of|stands\s+for|explain)\b|"
    r"\bwhat\s+is\b.+\band\b.+\bwhat\s+is\b",
    re.I,
)


def is_pure_field_answer(plan: ExecutionPlan, question: str) -> bool:
    """True when the whole reply is the asked figures and nothing else."""
    if plan.answer_mode != AnswerMode.DATA_ONLY:
        return False
    if wants_comparison_table(question, plan):
        return False
    if not plan.asked_fields:
        return False
    if str(plan.intent or "") in ("explain_cause", "overview", "compare", "rank", "outlook"):
        return False
    if (plan.concept_brief or "").strip():
        return False
    if any(call.tool in _NEWS_TOOLS for call in plan.tool_calls or []):
        return False
    if any(str(part.get("source") or "") == "llm" for part in plan.sub_queries or []):
        return False
    if _EXPLAIN_RE.search(question or ""):
        return False
    return True


def render_benchmark_comparison_table(
    pack: Any,
    plan: ExecutionPlan,
    question: str = "",
) -> str:
    """1Y / 3Y / 5Y fund, benchmark, and category average from vs-benchmark API."""
    from news_rag.insight.contracts import EvidencePack
    from news_rag.insight.evidence_pack import _benchmark_lines_from_pack

    if isinstance(pack, EvidencePack):
        data_pack = pack.data_pack or {}
        display = pack.display_tables or {}
        digest = pack.performance_digest
    else:
        data_pack = pack if isinstance(pack, dict) else {}
        display = {}
        digest = None

    table = str(display.get("vs_benchmark_table") or "").strip()
    if not table:
        from news_rag.insight.fund_display import build_fund_display_tables

        built = build_fund_display_tables(data_pack, digest=digest, question=question)
        table = str(built.get("vs_benchmark_table") or "").strip()
        heading = built.get("_heading_vs_benchmark_table")
        title = built.get("_title") or (plan.funds[0] if plan.funds else "Fund")
    else:
        heading = display.get("_heading_vs_benchmark_table")
        title = display.get("_title") or (plan.funds[0] if plan.funds else "Fund")

    if not table:
        fallback = _benchmark_lines_from_pack(data_pack)
        if fallback:
            return fallback
        return ""

    head = str(heading or "### Returns (1Y / 3Y / 5Y)").strip()
    return f"{head}\n\n{table}"


def render_fact_answer(
    plan: ExecutionPlan,
    data_pack: dict[str, Any] | None,
    question: str = "",
) -> str:
    fields = list(plan.asked_fields or [])
    if not fields:
        return ""
    pack = data_pack or {}
    fund_blocks = [
        (str(key).removeprefix("fund:"), value)
        for key, value in pack.items()
        if str(key).startswith("fund:") and isinstance(value, dict)
    ]
    portfolio_blocks = {
        str(key).removeprefix("portfolio:"): value
        for key, value in pack.items()
        if str(key).startswith("portfolio:") and isinstance(value, dict)
    }
    investor = pack.get("investor_portfolio") if isinstance(pack.get("investor_portfolio"), dict) else {}
    lines: list[str] = []
    targets = fund_blocks or [((plan.funds[0] if plan.funds else "This fund"), {})]
    book_only = all((field_need(name) and field_need(name).book) for name in fields)
    if book_only:
        for name in fields:
            lines.append(_book_line(name, investor, question))
        return "\n".join(line for line in lines if line)
    for fund_name, block in targets:
        for name in fields:
            need = field_need(name)
            if need and need.book:
                lines.append(_book_line(name, investor, question))
                continue
            text = _fund_line(name, fund_name, block, portfolio_blocks.get(fund_name) or {}, question)
            if text:
                lines.append(text)
    return "\n".join(lines)


def _missing(label: str, fund_name: str) -> str:
    who = fund_name or "this fund"
    return f"{label} is not available for {who} right now."


def _inr(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"Rs {number:,.2f}"


def _pct(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.2f}%"


def _snap(block: dict[str, Any]) -> dict[str, Any]:
    snap = block.get("snapshot")
    return snap if isinstance(snap, dict) else {}


def _fund_name(block: dict[str, Any], fallback: str) -> str:
    snap = _snap(block)
    return str(snap.get("fund_name") or block.get("fund_name") or fallback or "This fund").strip()


def _plan_and_option(name: str) -> tuple[str, str]:
    text = name.lower()
    plan = "direct" if "direct" in text else "regular"
    option = "IDCW" if "idcw" in text or "dividend" in text else "growth"
    return plan, option


def _age(inception: str) -> str:
    raw = str(inception or "").strip()[:10]
    try:
        started = date.fromisoformat(raw)
    except ValueError:
        return ""
    days = (date.today() - started).days
    if days < 0:
        return ""
    years = days // 365
    months = (days % 365) // 30
    if years <= 0:
        return f"{months} months"
    return f"{years} years {months} months"


def _fund_line(
    name: str,
    fallback: str,
    block: dict[str, Any],
    portfolio: dict[str, Any],
    question: str,
) -> str:
    fund = _fund_name(block, fallback)
    snap = _snap(block)
    label = field_label(name)
    if name == "identity":
        return _identity(fund, snap)
    if name == "nav" and snap.get("nav") is not None:
        when = str(snap.get("nav_date") or "").strip()
        suffix = f" (as on {when})" if when else ""
        return f"The NAV of {fund} is {_inr(snap.get('nav'))}{suffix}."
    if name == "nav_change_1d":
        day = snap.get("day_change_pct")
        if day is None:
            day = snap.get("day_change")
        if day is not None:
            return f"The day change of {fund} is {_pct(day)}."
    if name == "aum" and snap.get("aum") is not None:
        when = str(snap.get("aum_as_on_date") or "").strip()
        suffix = f" (as on {when})" if when else ""
        return f"The AUM of {fund} is {_inr(snap.get('aum'))} crore{suffix}."
    if name in ("expense_ratio", "expense_direct"):
        expense = snap.get("expense_ratio") if isinstance(snap.get("expense_ratio"), dict) else {}
        key = "direct" if name == "expense_direct" else "regular"
        if expense.get(key) is None and name == "expense_ratio":
            key = "direct" if expense.get("direct") is not None else key
        if expense.get(key) is not None:
            which = "direct plan" if key == "direct" else "regular plan"
            return f"The expense ratio of {fund} ({which}) is {float(expense[key]):.2f}%."
    if name == "exit_load":
        text = str(snap.get("exit_load_summary") or "").strip()
        if text:
            return f"The exit load of {fund} is {text}."
    if name == "benchmark":
        text = str(snap.get("benchmark") or "").strip()
        if text:
            return f"The benchmark of {fund} is {text}."
    if name == "benchmark_return":
        from news_rag.fund_rupeestop_metrics import periods_requested_in_question

        codes = periods_requested_in_question(question) or ["1Y"]
        vs = block.get("vs_benchmark") if isinstance(block.get("vs_benchmark"), dict) else {}
        insights = block.get("fund_insights") if isinstance(block.get("fund_insights"), dict) else {}
        if not vs:
            vs = insights.get("vs_benchmark") if isinstance(insights.get("vs_benchmark"), dict) else {}
        periods = vs.get("periods") if isinstance(vs.get("periods"), dict) else {}
        bench_label = str(
            vs.get("benchmark_name") or insights.get("scheme_benchmark_name") or snap.get("benchmark") or "the benchmark"
        ).strip()
        for code in codes:
            row = periods.get(code) or periods.get(str(code).upper())
            if isinstance(row, dict) and row.get("benchmark_return") is not None:
                return f"The {str(code).upper()} return of {bench_label} is {_pct(row['benchmark_return'])}."
        comp = insights.get("comparison_periods") if isinstance(insights.get("comparison_periods"), dict) else {}
        for code in codes:
            row = comp.get(code) or comp.get(str(code).upper())
            if isinstance(row, dict) and row.get("benchmark_return") is not None:
                return f"The {str(code).upper()} return of {bench_label} is {_pct(row['benchmark_return'])}."
        return _missing(label, fund)
    if name == "category":
        text = str(snap.get("category") or "").strip()
        if text:
            return f"{fund} is in the {text} category."
    if name == "fund_type":
        text = str(snap.get("scheme_type") or "").strip()
        if text:
            return f"{fund} is a {text} fund."
    if name in ("plan_type", "option"):
        plan, option = _plan_and_option(fund)
        if name == "plan_type":
            return f"{fund} is the {plan} plan."
        return f"{fund} is the {option} option."
    if name == "inception_date":
        text = str(snap.get("inception_date") or "").strip()
        if text:
            return f"{fund} was launched on {text}."
    if name == "fund_age":
        age = _age(str(snap.get("inception_date") or ""))
        if age:
            return f"{fund} is {age} old."
    if name == "range_52w":
        span = snap.get("52_week_range") if isinstance(snap.get("52_week_range"), dict) else {}
        low = span.get("low") if span else snap.get("low_52w")
        high = span.get("high") if span else snap.get("high_52w")
        if low and high:
            return f"The 52-week range of {fund} is {_inr(low)} to {_inr(high)}."
    if name.startswith("return:"):
        code = name.split(":", 1)[1]
        returns = snap.get("returns") if isinstance(snap.get("returns"), dict) else {}
        value = None
        for key in (code, code.lower(), code.upper()):
            if returns.get(key) is not None:
                value = returns.get(key)
                break
        if value is not None:
            return f"The {code} return of {fund} is {_pct(value)}."
    if name == "return_since_inception":
        returns = snap.get("returns") if isinstance(snap.get("returns"), dict) else {}
        value = returns.get("INCEPTION") or returns.get("inception")
        if value is not None:
            return f"The return of {fund} since inception is {_pct(value)}."
    if name in ("vs_benchmark", "category_avg"):
        text = _vs_line(name, fund, block)
        if text:
            return text
    if name in (
        "lock_in",
        "min_sip",
        "min_lumpsum",
        "min_additional",
        "redemption_period",
        "sip_frequencies",
        "demat_physical",
    ):
        text = _limits_line(name, fund, block)
        if text:
            return text
    if name in ("asset_allocation", "market_cap_mix", "stock_count", "top_n_weight"):
        text = _composition_line(name, fund, block)
        if text:
            return text
    if name in ("holdings", "holding_lookup", "sectors", "sector_lookup"):
        text = _portfolio_line(name, fund, portfolio, question)
        if text:
            return text
    if name == "riskometer":
        risk = block.get("risk") if isinstance(block.get("risk"), dict) else {}
        text = str(risk.get("riskometer") or risk.get("lines") or "").strip()
        if text:
            first = text.split("\n", 1)[0]
            return f"The SEBI riskometer of {fund} is {first}."
    if name == "rs_rating":
        rating = block.get("rs_rating") if isinstance(block.get("rs_rating"), dict) else {}
        label = str(rating.get("label") or rating.get("rs_label") or "").strip()
        score = rating.get("final_score")
        if score is None:
            score = rating.get("score")
        if label or score is not None:
            bits = " ".join(str(part) for part in (label, score) if part not in (None, ""))
            return f"The RupeeStop rating of {fund} is {bits}."
    if name == "pillars":
        rating = block.get("rs_rating") if isinstance(block.get("rs_rating"), dict) else {}
        pillars = rating.get("pillars") if isinstance(rating.get("pillars"), dict) else {}
        if pillars:
            body = "; ".join(f"{key} {value}" for key, value in pillars.items())
            return f"The pillar scores of {fund} are {body}."
    if name == "drawdown":
        body = block.get("drawdown") if isinstance(block.get("drawdown"), dict) else {}
        lines = str(body.get("lines") or "").strip()
        if lines:
            return lines
    if name in ("managers", "manager_tenure", "past_managers"):
        text = _manager_line(name, fund, block)
        if text:
            return text
    return _missing(label, fund)


def _identity(fund: str, snap: dict[str, Any]) -> str:
    category = str(snap.get("category") or "mutual fund").strip()
    scheme = str(snap.get("scheme_type") or "mutual fund").strip()
    plan, option = _plan_and_option(fund)
    parts = [f"{fund} is a {category} {scheme.lower()} fund ({plan} plan, {option} option)"]
    if snap.get("aum") is not None:
        parts.append(f"managing {_inr(snap.get('aum'))} crore")
    if snap.get("nav") is not None:
        when = str(snap.get("nav_date") or "").strip()
        suffix = f" (as on {when})" if when else ""
        parts.append(f"with a current NAV of {_inr(snap.get('nav'))}{suffix}")
    sentence = parts[0]
    if len(parts) == 2:
        sentence = f"{parts[0]}, {parts[1]}"
    elif len(parts) == 3:
        sentence = f"{parts[0]}, {parts[1]}, {parts[2]}"
    return sentence + "."


def _comparison_rows(block: dict[str, Any]) -> dict[str, Any]:
    insights = block.get("fund_insights") if isinstance(block.get("fund_insights"), dict) else {}
    comp = insights.get("comparison_periods") if isinstance(insights.get("comparison_periods"), dict) else {}
    if comp:
        return comp
    vs = block.get("vs_benchmark") if isinstance(block.get("vs_benchmark"), dict) else {}
    return vs.get("periods") if isinstance(vs.get("periods"), dict) else {}


def _vs_line(name: str, fund: str, block: dict[str, Any]) -> str:
    vs = block.get("vs_benchmark") if isinstance(block.get("vs_benchmark"), dict) else {}
    periods = vs.get("periods") if isinstance(vs.get("periods"), dict) else {}
    comparison = _comparison_rows(block)
    if not periods and not comparison:
        return ""
    bits: list[str] = []
    for code in ("1Y", "3Y", "5Y"):
        row = comparison.get(code) if isinstance(comparison.get(code), dict) else periods.get(code)
        if not isinstance(row, dict):
            continue
        if name == "category_avg":
            cat_v = row.get("category_average_return")
            if cat_v is None:
                cat_v = row.get("peer_return")
            if cat_v is not None:
                bits.append(f"{code} category average {_pct(cat_v)}")
        elif name == "vs_benchmark" and row.get("vs_benchmark") is not None:
            bits.append(f"{code} {_pct(row.get('vs_benchmark'))} vs benchmark")
    if not bits:
        return ""
    if name == "category_avg":
        return f"{fund} versus the category: " + "; ".join(bits) + "."
    bench = str(vs.get("benchmark_name") or _snap(block).get("benchmark") or "its benchmark").strip()
    return f"{fund} versus {bench}: " + "; ".join(bits) + "."


def _limits_line(name: str, fund: str, block: dict[str, Any]) -> str:
    limits = block.get("investment_limits") if isinstance(block.get("investment_limits"), dict) else {}
    if not limits:
        return ""
    if name == "min_sip" and limits.get("min_sip") is not None:
        return f"The minimum SIP in {fund} is {_inr(limits.get('min_sip'))}."
    if name == "min_lumpsum" and limits.get("min_lumpsum") is not None:
        return f"The minimum lumpsum in {fund} is {_inr(limits.get('min_lumpsum'))}."
    if name == "min_additional" and limits.get("min_additional") is not None:
        return f"The minimum additional purchase in {fund} is {_inr(limits.get('min_additional'))}."
    if name == "redemption_period" and limits.get("redemption_settlement"):
        return f"Redemption from {fund} is settled in {limits.get('redemption_settlement')}."
    if name == "sip_frequencies" and isinstance(limits.get("sip_frequencies"), dict):
        allowed = [
            key
            for key, row in limits["sip_frequencies"].items()
            if isinstance(row, dict) and row.get("allowed")
        ]
        if allowed:
            return f"SIP frequencies allowed in {fund}: {', '.join(allowed)}."
    if name == "demat_physical" and limits.get("transaction_modes"):
        modes = ", ".join(str(item) for item in limits.get("transaction_modes") or [])
        return f"{fund} can be bought as: {modes}."
    if name == "lock_in":
        text = str(limits.get("lock_in") or "").strip()
        if text:
            return f"The lock-in of {fund} is {text}."
        category = str(_snap(block).get("category") or "")
        if "elss" in category.lower() or "elss" in fund.lower():
            return f"{fund} has the ELSS lock-in of 3 years."
        return f"{fund} has no lock-in in the published limits."
    return ""


def _composition_line(name: str, fund: str, block: dict[str, Any]) -> str:
    comp = block.get("composition") if isinstance(block.get("composition"), dict) else {}
    if not comp:
        return ""
    if name == "stock_count" and comp.get("holding_count") is not None:
        return f"{fund} holds {comp.get('holding_count')} stocks."
    if name == "top_n_weight":
        bits = []
        if comp.get("top_5_pct") is not None:
            bits.append(f"top 5 {float(comp['top_5_pct']):.2f}%")
        if comp.get("top_10_pct") is not None:
            bits.append(f"top 10 {float(comp['top_10_pct']):.2f}%")
        if bits:
            return f"Concentration in {fund}: " + ", ".join(bits) + "."
    rows_key = "asset_allocation" if name == "asset_allocation" else "market_cap" if name == "market_cap_mix" else ""
    rows = comp.get(rows_key) if rows_key else None
    if isinstance(rows, list) and rows:
        bits = []
        for row in rows[:8]:
            if not isinstance(row, dict):
                continue
            label = row.get("label") or row.get("name") or ""
            pct = row.get("percentage")
            if label and pct is not None:
                bits.append(f"{label} {float(pct):.2f}%")
        if bits:
            title = "Asset allocation" if name == "asset_allocation" else "Market-cap mix"
            return f"{title} of {fund}: " + "; ".join(bits) + "."
    return ""


def _portfolio_line(name: str, fund: str, portfolio: dict[str, Any], question: str) -> str:
    if name in ("holdings", "holding_lookup"):
        rows = portfolio.get("holdings") if isinstance(portfolio.get("holdings"), list) else []
        if name == "holding_lookup":
            from news_rag.insight.fields import _find_term

            needle = _find_term(question, "holding").lower()
            hit = next(
                (
                    row
                    for row in rows
                    if isinstance(row, dict) and needle and needle in str(row.get("name") or row.get("company") or "").lower()
                ),
                None,
            )
            if hit is None and needle:
                return f"{fund} does not show {needle} in the holdings that were fetched."
            if isinstance(hit, dict):
                weight = hit.get("percentage") or hit.get("weight")
                label = hit.get("name") or hit.get("company")
                if weight is not None:
                    return f"{fund} holds {label} at {float(weight):.2f}%."
                return f"{fund} holds {label}."
        if rows:
            bits = []
            for row in rows[:10]:
                if not isinstance(row, dict):
                    continue
                label = row.get("name") or row.get("company") or row.get("holding")
                weight = row.get("percentage") if row.get("percentage") is not None else row.get("weight")
                if label and weight is not None:
                    bits.append(f"{label} {float(weight):.2f}%")
                elif label:
                    bits.append(str(label))
            if bits:
                return f"Top holdings of {fund}: " + "; ".join(bits) + "."
    if name in ("sectors", "sector_lookup"):
        rows = portfolio.get("sectors") if isinstance(portfolio.get("sectors"), list) else []
        if name == "sector_lookup":
            from news_rag.insight.fields import _find_term

            needle = _find_term(question, "sector").lower()
            hit = next(
                (
                    row
                    for row in rows
                    if isinstance(row, dict) and needle and needle in str(row.get("sector") or row.get("name") or "").lower()
                ),
                None,
            )
            if isinstance(hit, dict):
                weight = hit.get("percentage") if hit.get("percentage") is not None else hit.get("weight")
                label = hit.get("sector") or hit.get("name")
                if weight is not None:
                    return f"{fund} has {float(weight):.2f}% in {label}."
        if rows:
            bits = []
            for row in rows[:8]:
                if not isinstance(row, dict):
                    continue
                label = row.get("sector") or row.get("name")
                weight = row.get("percentage") if row.get("percentage") is not None else row.get("weight")
                if label and weight is not None:
                    bits.append(f"{label} {float(weight):.2f}%")
            if bits:
                return f"Sector allocation of {fund}: " + "; ".join(bits) + "."
    return ""


def _manager_line(name: str, fund: str, block: dict[str, Any]) -> str:
    managers = block.get("managers") if isinstance(block.get("managers"), dict) else {}
    current = managers.get("current") if isinstance(managers.get("current"), list) else []
    past = managers.get("past") if isinstance(managers.get("past"), list) else []
    if name == "past_managers" and past:
        names = [str(row.get("name")) for row in past if isinstance(row, dict) and row.get("name")]
        if names:
            return f"Past managers of {fund}: {', '.join(names)}."
    if current:
        bits = []
        for row in current:
            if not isinstance(row, dict) or not row.get("name"):
                continue
            if name == "manager_tenure" and row.get("managing_since"):
                bits.append(f"{row.get('name')} since {row.get('managing_since')}")
            else:
                bits.append(str(row.get("name")))
        if bits:
            return f"{fund} is managed by {', '.join(bits)}."
    return ""


def _book_line(name: str, investor: dict[str, Any], question: str) -> str:
    del question
    label = field_label(name)
    summary = investor.get("summary") if isinstance(investor.get("summary"), dict) else {}
    holdings = investor.get("holdings") if isinstance(investor.get("holdings"), list) else []
    if name == "book_value" and summary.get("aum_inr") is not None:
        return f"Your portfolio value is {_inr(summary.get('aum_inr'))}."
    if name == "invested" and summary.get("invested_inr") is not None:
        return f"You have invested {_inr(summary.get('invested_inr'))}."
    if name == "gain_abs" and summary.get("gain_loss_inr") is not None:
        return f"Your gain or loss is {_inr(summary.get('gain_loss_inr'))}."
    if name == "gain_pct" and summary.get("absolute_return_pct") is not None:
        return f"Your gain or loss is {_pct(summary.get('absolute_return_pct'))}."
    if name == "scheme_count":
        count = summary.get("scheme_count") or len(holdings)
        if count:
            return f"You hold {count} schemes."
    if name == "holdings_list" and holdings:
        names = [str(row.get("scheme_name")) for row in holdings if isinstance(row, dict) and row.get("scheme_name")]
        if names:
            return "You hold: " + "; ".join(names) + "."
    if name in ("largest_holding", "smallest_holding") and holdings:
        ranked = [
            row for row in holdings
            if isinstance(row, dict) and row.get("aum_inr") is not None
        ]
        if ranked:
            pick = max(ranked, key=lambda row: float(row["aum_inr"])) if name == "largest_holding" else min(
                ranked, key=lambda row: float(row["aum_inr"])
            )
            which = "largest" if name == "largest_holding" else "smallest"
            return f"Your {which} holding is {pick.get('scheme_name')} at {_inr(pick.get('aum_inr'))}."
    if name == "amcs" and holdings:
        names = sorted({str(row.get("amc_name")) for row in holdings if isinstance(row, dict) and row.get("amc_name")})
        if names:
            return "You invest with: " + ", ".join(names) + "."
    if name == "categories":
        alloc = investor.get("allocation") if isinstance(investor.get("allocation"), dict) else {}
        rows = alloc.get("aumByCategory") if isinstance(alloc.get("aumByCategory"), dict) else {}
        if rows:
            bits = [f"{key} {_inr(value)}" for key, value in list(rows.items())[:8]]
            return "Allocation by category: " + "; ".join(bits) + "."
    if name == "asset_mix":
        alloc = investor.get("allocation") if isinstance(investor.get("allocation"), dict) else {}
        rows = alloc.get("aumBySchemeType") if isinstance(alloc.get("aumBySchemeType"), dict) else {}
        if rows:
            bits = [f"{key} {_inr(value)}" for key, value in rows.items()]
            return "Asset mix: " + "; ".join(bits) + "."
    if name in ("book_xirr", "holding_xirr"):
        xirr = investor.get("xirr") if isinstance(investor.get("xirr"), dict) else {}
        if name == "book_xirr" and xirr.get("portfolio_xirr_pct") is not None:
            return f"Your portfolio XIRR is {_pct(xirr.get('portfolio_xirr_pct'))}."
        schemes = xirr.get("schemes") if isinstance(xirr.get("schemes"), list) else []
        if schemes:
            bits = [
                f"{row.get('scheme_name')} {_pct(row.get('xirr_pct'))}"
                for row in schemes
                if isinstance(row, dict) and row.get("xirr_pct") is not None
            ]
            if bits:
                return "XIRR by scheme: " + "; ".join(bits[:12]) + "."
    if name in ("sip_list", "sip_total", "stp_list"):
        key = "stp" if name == "stp_list" else "sip"
        block = investor.get(key) if isinstance(investor.get(key), dict) else {}
        plans = block.get("plans") if isinstance(block.get("plans"), list) else []
        summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
        if name == "sip_total":
            total = summary.get("monthlyAmount") or summary.get("totalAmount") or summary.get("amount")
            if total is not None:
                return f"Your monthly SIP total is {_inr(total)}."
        if plans:
            bits = []
            for row in plans[:12]:
                if not isinstance(row, dict):
                    continue
                scheme = row.get("scheme_name") or row.get("schemeName") or "scheme"
                amount = row.get("amount")
                bits.append(f"{scheme} {_inr(amount)}" if amount is not None else str(scheme))
            if bits:
                title = "STP plans" if name == "stp_list" else "SIP plans"
                return f"{title}: " + "; ".join(bits) + "."
    if name == "book_risk":
        profile = investor.get("profile_risk") if isinstance(investor.get("profile_risk"), dict) else {}
        text = str(profile.get("risk_profiler_category") or profile.get("book_type_label") or "").strip()
        if text:
            return f"Your portfolio risk profile is {text}."
    if name in ("concentration", "underlying_top"):
        block = investor.get("concentration") if isinstance(investor.get("concentration"), dict) else {}
        if block:
            return f"Portfolio concentration: {str(block)[:400]}"
    if name == "holding_rs_labels" and holdings:
        bits = []
        for row in holdings:
            if not isinstance(row, dict):
                continue
            label = row.get("rs_label") or row.get("rs_score")
            if row.get("scheme_name") and label:
                bits.append(f"{row.get('scheme_name')} {label}")
        if bits:
            return "RupeeStop labels: " + "; ".join(bits) + "."
    return f"{label} is not available for your portfolio right now."
