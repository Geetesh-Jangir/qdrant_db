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
# Semicolon field templates are for short book answers; larger RS lists use a table or composer.
FIELD_TEMPLATE_COMPOSER_MIN_HOLDINGS = 6
FIELD_TEMPLATE_COMPOSER_MIN_CHARS = 500


def _investor_holdings_rows(data_pack: dict[str, Any] | None) -> list[dict[str, Any]]:
    pack = data_pack or {}
    investor = pack.get("investor_portfolio") if isinstance(pack.get("investor_portfolio"), dict) else {}
    return [row for row in (investor.get("holdings") or []) if isinstance(row, dict)]


def _asks_portfolio_rs_ratings(plan: ExecutionPlan, question: str) -> bool:
    fields = {str(x) for x in (plan.asked_fields or [])}
    if "holding_rs_labels" in fields:
        return True
    if "rs_rating" in {str(x).lower() for x in (plan.asked_facts or [])}:
        return True
    return bool(re.search(r"\brs\s+(?:rating|label|score)\b|\brupee\s*stop\s+(?:rating|score)\b", question or "", re.I))


def field_answer_needs_composer(
    plan: ExecutionPlan,
    data_pack: dict[str, Any] | None,
    template_text: str = "",
) -> bool:
    """Long RS lists need the composer (or a markdown table), not one semicolon sentence."""
    if not _asks_portfolio_rs_ratings(plan, ""):
        return False
    if str(plan.holding_scope or "").strip().lower() != "all_holdings":
        return False
    holdings = _investor_holdings_rows(data_pack)
    if len(holdings) >= FIELD_TEMPLATE_COMPOSER_MIN_HOLDINGS:
        return True
    if len(template_text or "") >= FIELD_TEMPLATE_COMPOSER_MIN_CHARS:
        return True
    return False


def render_investor_rs_ratings_table(
    plan: ExecutionPlan,
    data_pack: dict[str, Any] | None,
    question: str = "",
) -> str:
    """Markdown table of RS label + score for every holding (investor portfolio API)."""
    if not _asks_portfolio_rs_ratings(plan, question):
        return ""
    scope = str(plan.holding_scope or "").strip().lower()
    if scope != "all_holdings" and not re.search(
        r"\ball\s+(?:of\s+)?(?:my\s+)?(?:funds|schemes|holdings)\b",
        question or "",
        re.I,
    ):
        return ""
    holdings = _investor_holdings_rows(data_pack)
    if not holdings:
        return ""
    lines = [
        "### RupeeStop ratings for your funds",
        "",
        "| Scheme | RS label | Score |",
        "| --- | --- | ---: |",
    ]
    for row in sorted(holdings, key=lambda item: float(item.get("aum_inr") or 0), reverse=True):
        name = str(row.get("scheme_name") or "").strip()[:72]
        label = str(row.get("rs_label") or "—")
        score = row.get("rs_score")
        try:
            score_cell = f"{float(score):.2f}" if score is not None else "—"
        except (TypeError, ValueError):
            score_cell = "—"
        lines.append(f"| {name} | {label} | {score_cell} |")
    return "\n".join(lines)


def is_pure_field_answer(
    plan: ExecutionPlan,
    question: str,
    data_pack: dict[str, Any] | None = None,
) -> bool:
    """True when the whole reply is the asked figures and nothing else."""
    if plan.answer_mode != AnswerMode.DATA_ONLY:
        return False
    if wants_comparison_table(question, plan):
        return False
    if not plan.asked_fields:
        return False
    if field_answer_needs_composer(plan, data_pack, ""):
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
    from news_rag.indian_format import format_rs

    return format_rs(value)


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
        if rating.get("rating_pending"):
            from news_rag.fund_risk import pending_rating_line

            return pending_rating_line(fund)
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
    if name == "gain_pct":
        from news_rag.insight.pack_sanitize import _rollup_investor_summary

        rolled = _rollup_investor_summary(investor)
        if rolled.get("gain_loss_inr") is not None and rolled.get("invested_inr"):
            pct = 100.0 * float(rolled["gain_loss_inr"]) / float(rolled["invested_inr"])
            return f"Your gain or loss is {_pct(pct)}."
        if summary.get("absolute_return_pct") is not None:
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
        ranked = _allocation_bucket_rows(alloc, by="category")
        if ranked:
            bits = []
            for bucket, amt, pct in ranked[:8]:
                bit = f"{bucket} {_pct(pct)}" if pct is not None else f"{bucket} {_inr(amt)}"
                bits.append(bit)
            return "Allocation by category: " + "; ".join(bits) + "."
    if name == "asset_mix":
        alloc = investor.get("allocation") if isinstance(investor.get("allocation"), dict) else {}
        ranked = _allocation_bucket_rows(alloc, by="scheme_type")
        if ranked:
            bits = []
            for bucket, amt, pct in ranked:
                bit = f"{bucket} {_pct(pct)}" if pct is not None else f"{bucket} {_inr(amt)}"
                bits.append(bit)
            return "Asset mix: " + "; ".join(bits) + "."
    if name in ("book_xirr", "holding_xirr"):
        xirr = investor.get("xirr") if isinstance(investor.get("xirr"), dict) else {}
        if name == "book_xirr":
            book_xirr = _portfolio_xirr_pct(investor)
            if book_xirr is not None:
                return f"Your portfolio XIRR is {_pct(book_xirr)}."
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
            label = row.get("rs_label")
            score = row.get("rs_score")
            if not row.get("scheme_name") or (label is None and score is None):
                continue
            parts = [str(row.get("scheme_name"))]
            if label:
                parts.append(str(label))
            if score is not None:
                try:
                    parts.append(f"score {float(score):.2f}")
                except (TypeError, ValueError):
                    parts.append(f"score {score}")
            bits.append(" — ".join(parts))
        if bits:
            return "RupeeStop ratings: " + "; ".join(bits) + "."
    return f"{label} is not available for your portfolio right now."


_FACT_FOLLOWUP = {
    "aum": "Want the fund-by-fund breakdown?",
    "invested": "Want this split by fund?",
    "overall_return": "Want the fund-by-fund breakdown?",
    "xirr": "Want XIRR for each fund?",
    "list_holdings": "Want one fund in more detail?",
    "allocation": "Want this against your risk profile?",
    "sip_list": "Want the next SIP date?",
}


def _as_of(data: dict[str, Any]) -> str:
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    raw = str(meta.get("as_of_date") or meta.get("as_of") or "").strip()
    return f" as of {raw}" if raw else ""


def _portfolio_xirr_pct(book: dict[str, Any]) -> Any:
    summary = book.get("summary") if isinstance(book.get("summary"), dict) else {}
    val = summary.get("portfolio_xirr_pct")
    if val is not None:
        return val
    xirr = book.get("xirr") if isinstance(book.get("xirr"), dict) else {}
    return xirr.get("portfolio_xirr_pct")


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(cell.replace("|", "/") for cell in row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def _float_or_none(val: Any) -> float | None:
    try:
        if val is None or val == "":
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def _share_rows_from_list(rows: Any) -> list[tuple[str, float | None, float | None]]:
    if not isinstance(rows, list):
        return []
    out: list[tuple[str, float | None, float | None]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("category") or row.get("schemeType") or "").strip()
        if not name:
            continue
        amt = _float_or_none(
            row.get("aum_inr")
            if row.get("aum_inr") is not None
            else row.get("aumInr", row.get("marketValue"))
        )
        pct = _float_or_none(
            row.get("aum_pct")
            if row.get("aum_pct") is not None
            else row.get("aumPct", row.get("percentage", row.get("weight_pct")))
        )
        if amt is not None and amt <= 0:
            continue
        if (amt is None or amt <= 0) and (pct is None or pct <= 0):
            continue
        out.append((name, amt, pct))
    return out


def _share_rows_from_map(mapping: Any) -> list[tuple[str, float | None, float | None]]:
    if not isinstance(mapping, dict) or not mapping:
        return []
    amounts = {
        str(label): amt
        for label, value in mapping.items()
        if (amt := _float_or_none(value)) is not None and amt > 0
    }
    total = sum(amounts.values())
    out: list[tuple[str, float | None, float | None]] = []
    for label, amt in amounts.items():
        pct = round(100.0 * amt / total, 2) if total else None
        out.append((label, amt, pct))
    out.sort(key=lambda item: float(item[2] or item[1] or 0), reverse=True)
    return out


def _allocation_bucket_rows(alloc: dict[str, Any], *, by: str = "category") -> list[tuple[str, float | None, float | None]]:
    """categoryShare / schemeTypeShare lists or legacy amount maps from the investor API."""
    if by == "scheme_type":
        order = ("schemeTypeShare", "aumBySchemeType", "investedBySchemeType")
    else:
        order = ("categoryShare", "aumByCategory", "investedByCategory")
    for key in order:
        block = alloc.get(key)
        if key.endswith("Share"):
            rows = _share_rows_from_list(block)
        else:
            rows = _share_rows_from_map(block)
        if rows:
            if key.endswith("Share"):
                rows.sort(key=lambda item: float(item[2] or item[1] or 0), reverse=True)
            return rows
    return []


def _holdings(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("holdings") if isinstance(data.get("holdings"), list) else []
    return [row for row in rows if isinstance(row, dict)]


def _holding_row_for_plan(book: dict[str, Any], plan: ExecutionPlan | None) -> dict[str, Any] | None:
    rows = _holdings(book)
    if not rows:
        return None
    hint = ""
    if plan is not None:
        if plan.funds:
            hint = str(plan.funds[0] or "").strip()
        if not hint:
            for call in plan.tool_calls or []:
                if call.tool != "get_investor_portfolio":
                    continue
                hint = str((call.arguments or {}).get("scheme_filter") or "").strip()
                break
    if not hint:
        return rows[0]
    from news_rag.portfolio.normalize import match_scheme_filter

    for row in rows:
        name = str(row.get("scheme_name") or "")
        if match_scheme_filter(name, hint):
            return row
    return rows[0]


def render_portfolio_fact(
    intent: str,
    data: dict[str, Any] | None,
    *,
    plan: ExecutionPlan | None = None,
) -> str:
    """One short answer for a planner fact intent. Empty string when intent is not a fact."""
    from news_rag.insight.portfolio_intents import normalize_portfolio_intent, shape_for

    name = normalize_portfolio_intent(intent)
    if shape_for(name) != "fact":
        return ""
    book = data if isinstance(data, dict) else {}
    summary = book.get("summary") if isinstance(book.get("summary"), dict) else {}
    stamp = _as_of(book)
    line = ""

    if name == "aum":
        line = f"Your portfolio is worth **{_inr(summary.get('aum_inr'))}**{stamp}." if summary.get("aum_inr") is not None else "Portfolio value is not available right now."
    elif name == "invested":
        line = f"You have invested **{_inr(summary.get('invested_inr'))}**{stamp}." if summary.get("invested_inr") is not None else "Invested amount is not available right now."
    elif name == "overall_return":
        abs_ret = summary.get("absolute_return_pct")
        xirr = _portfolio_xirr_pct(book)
        if abs_ret is None and xirr is None:
            line = "Overall return is not available right now."
        else:
            bits = []
            if abs_ret is not None:
                bits.append(f"absolute return **{_pct(abs_ret)}**")
            if xirr is not None:
                bits.append(f"XIRR **{_pct(xirr)}**")
            line = "Your overall return is " + " and ".join(bits) + f"{stamp}."
    elif name == "xirr":
        book_xirr = _portfolio_xirr_pct(book)
        line = (
            f"Your portfolio XIRR is **{_pct(book_xirr)}**{stamp}."
            if book_xirr is not None
            else "Portfolio XIRR is not available right now."
        )
    elif name == "scheme_count":
        count = summary.get("scheme_count")
        if count is None:
            count = len(_holdings(book)) or None
        line = f"You hold **{count}** funds{stamp}." if count else "Fund count is not available right now."
    elif name == "nav_of_scheme":
        row = _holding_row_for_plan(book, plan)
        if not row:
            line = "NAV is not available for that scheme right now."
        else:
            nav = row.get("current_nav")
            when = row.get("nav_date") or ""
            label = str(row.get("scheme_name") or "That scheme")
            line = (
                f"{label} NAV is {_inr(nav)}" + (f" as of {when}" if when else stamp) + "."
                if nav is not None
                else f"NAV is not available for {label} right now."
            )
    elif name in ("sip_list", "next_sip"):
        sip = book.get("sip") if isinstance(book.get("sip"), dict) else {}
        plans = [p for p in (sip.get("plans") or []) if isinstance(p, dict)]
        if not plans:
            line = "No live SIPs."
        elif name == "next_sip":
            dated = sorted(
                plans,
                key=lambda p: str(
                    p.get("next_due_date") or p.get("next_date") or p.get("next_installment_date") or "9999"
                ),
            )
            first = dated[0]
            when = (
                first.get("next_due_date")
                or first.get("next_date")
                or first.get("next_installment_date")
                or "a date we don't have"
            )
            line = f"Next SIP is **{when}** for {first.get('scheme_name') or 'a fund'}."
        else:
            shown = plans[:8]
            rows = [
                [str(p.get("scheme_name") or "—")[:48], _inr(p.get("amount") or p.get("amount_inr")), str(p.get("frequency") or "—")]
                for p in shown
            ]
            extra = f"\n\n{len(plans) - len(shown)} more." if len(plans) > len(shown) else ""
            line = _table(["Fund", "Amount", "Frequency"], rows) + extra
    elif name == "stp_list":
        stp = book.get("stp") if isinstance(book.get("stp"), dict) else {}
        plans = [p for p in (stp.get("plans") or []) if isinstance(p, dict)]
        if not plans:
            line = "No live STPs."
        else:
            shown = plans[:8]
            rows = [
                [str(p.get("from_scheme") or p.get("scheme_name") or "—")[:40], str(p.get("to_scheme") or "—")[:40], _inr(p.get("amount") or p.get("amount_inr"))]
                for p in shown
            ]
            extra = f"\n\n{len(plans) - len(shown)} more." if len(plans) > len(shown) else ""
            line = _table(["From", "To", "Amount"], rows) + extra
    elif name == "dividends":
        pnl = book.get("pnl_summary") if isinstance(book.get("pnl_summary"), dict) else {}
        value = pnl.get("dividends_inr", pnl.get("dividends", pnl.get("divPayout")))
        line = f"Dividends received: **{_inr(value)}**{stamp}." if value is not None else "Dividend total is not available right now."
    elif name == "risk_profile":
        profile = book.get("profile_risk") if isinstance(book.get("profile_risk"), dict) else {}
        style = profile.get("investment_style") or profile.get("risk_profile") or profile.get("label")
        line = f"Your risk profile is **{style}**." if style else "Risk profile is not available right now."
    elif name == "st_vs_lt_gains":
        pnl = book.get("pnl_summary") if isinstance(book.get("pnl_summary"), dict) else {}
        short = pnl.get("short_term_gain_inr")
        long = pnl.get("long_term_gain_inr")
        if short is None and long is None:
            from news_rag.portfolio.normalize import aggregate_term_gains

            block = book.get("pnl_scheme") if isinstance(book.get("pnl_scheme"), dict) else {}
            schemes = block.get("schemes") if isinstance(block.get("schemes"), list) else []
            if not schemes and block.get("transactions"):
                schemes = [block]
            short, long = aggregate_term_gains([s for s in schemes if isinstance(s, dict)])
        if short is None and long is None:
            line = "Short-term and long-term gain split is not available right now."
        else:
            line = f"Short-term gains **{_inr(short or 0)}**, long-term gains **{_inr(long or 0)}**{stamp}."
    elif name in ("list_holdings", "top_holdings"):
        rows = sorted(_holdings(book), key=lambda r: float(r.get("aum_inr") or 0), reverse=True)
        if name == "top_holdings":
            rows = rows[:5]
        if not rows:
            line = "No holdings are available right now."
        else:
            shown = rows[:8]
            table_rows = [
                [str(r.get("scheme_name") or "—")[:48], str(r.get("scheme_category") or "—")[:24], _inr(r.get("aum_inr")), _pct(r.get("absolute_return_pct")) if r.get("absolute_return_pct") is not None else "—"]
                for r in shown
            ]
            extra = f"\n\n{len(rows) - len(shown)} more." if len(rows) > len(shown) else ""
            line = _table(["Fund", "Category", "Value", "Return"], table_rows) + extra
    elif name == "allocation":
        alloc = book.get("allocation") if isinstance(book.get("allocation"), dict) else {}
        ranked = _allocation_bucket_rows(alloc, by="category")
        if not ranked:
            ranked = _allocation_bucket_rows(alloc, by="scheme_type")
        if not ranked:
            line = "Allocation is not available right now."
        else:
            table_rows = [
                [
                    bucket,
                    _inr(amt) if amt is not None else "—",
                    _pct(pct) if pct is not None else "—",
                ]
                for bucket, amt, pct in ranked[:12]
            ]
            line = _table(["Bucket", "Value", "Share"], table_rows)
    else:
        return ""

    offer = _FACT_FOLLOWUP.get(name)
    if offer and "not available" not in line and not line.startswith("No "):
        return f"{line}\n\n{offer}"
    return line


def _category_amount_map(allocation: dict[str, Any], key: str) -> dict[str, float]:
    raw = allocation.get(key) if isinstance(allocation.get(key), dict) else {}
    out: dict[str, float] = {}
    for label, value in raw.items():
        amount = _float_or_none(value)
        if amount is None:
            continue
        out[str(label)] = amount
    return out


def _label_amount_in_map(mapping: dict[str, float], needle: str) -> float | None:
    n = (needle or "").strip().lower()
    if not n or not mapping:
        return None
    for label, amount in mapping.items():
        low = str(label).strip().lower()
        if low == n or n in low or low in n:
            return amount
    return None


def render_category_money_draft(
    allocation: dict[str, Any] | None,
    *,
    only: str = "",
    by: str = "category",
) -> str:
    """Invested and current value by category or scheme type. Zero rows are left out unless `only` is set."""
    alloc = allocation if isinstance(allocation, dict) else {}
    if by == "scheme_type":
        invested = _category_amount_map(alloc, "investedBySchemeType")
        current = _category_amount_map(alloc, "aumBySchemeType")
    else:
        invested = _category_amount_map(alloc, "investedByCategory")
        current = _category_amount_map(alloc, "aumByCategory")
    if not invested and not current:
        return ""
    labels: list[str] = []
    for label in list(current) + list(invested):
        if label not in labels:
            labels.append(label)
    needle = (only or "").strip().lower()
    if needle:
        labels = [label for label in labels if label.strip().lower() == needle]
    total_current = sum(max(amount, 0.0) for amount in current.values())
    rows: list[list[str]] = []
    for label in labels:
        inv = invested.get(label, 0.0)
        cur = current.get(label, 0.0)
        if inv <= 0 and cur <= 0:
            continue
        share = (100.0 * cur / total_current) if total_current and cur > 0 else None
        gain = cur - inv
        rows.append([
            label.title() if label.islower() else label,
            _inr(inv),
            _inr(cur),
            _inr(gain),
            _pct(share) if share is not None else "—",
        ])
    if not rows:
        if needle and (invested or current):
            inv = _label_amount_in_map(invested, needle)
            cur = _label_amount_in_map(current, needle)
            inv_amt = inv if inv is not None else 0.0
            cur_amt = cur if cur is not None else 0.0
            if inv_amt <= 0 and cur_amt <= 0:
                label = only.strip() or needle
                kind = "scheme type" if by == "scheme_type" else "category"
                return (
                    f"Measured {kind} **{label}**: invested **{_inr(0)}**, current value **{_inr(0)}**. "
                    f"You have not invested in {label.lower()}."
                )
        return ""
    rows.sort(key=lambda row: _inr_sort(row[2]), reverse=True)
    header = "Scheme type" if by == "scheme_type" else "Category"
    return _table([header, "Invested", "Current value", "Gain", "Share of value"], rows)


def _inr_sort(text: str) -> float:
    digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    try:
        return float(digits) if digits else 0.0
    except ValueError:
        return 0.0


def render_gold_exposure_draft(allocation: dict[str, Any] | None, metals: dict[str, Any] | None = None) -> str:
    """Gold category money, plus an approximate move from the spot return."""
    alloc = allocation if isinstance(allocation, dict) else {}
    table = render_category_money_draft(allocation, only="gold")
    if not table:
        if alloc.get("investedByCategory") or alloc.get("aumByCategory") or alloc.get("categoryShare"):
            return (
                "Measured gold category: invested **₹0**, current value **₹0**. "
                "You have not invested in gold."
            )
        return ""
    lines = [
        "Measured gold category (use this; do not say gold holdings are unavailable):",
        table,
    ]
    spot = metals if isinstance(metals, dict) else {}
    returns = spot.get("returns") if isinstance(spot.get("returns"), dict) else {}
    alloc = allocation if isinstance(allocation, dict) else {}
    current = _category_amount_map(alloc, "aumByCategory")
    gold_value = next((amount for label, amount in current.items() if label.strip().lower() == "gold"), 0.0)
    for window in ("1W", "1M"):
        row = returns.get(window) if isinstance(returns.get(window), dict) else {}
        pct = _float_or_none(row.get("pct"))
        if pct is None or gold_value <= 0:
            continue
        move = gold_value * pct / 100.0
        lines.append(
            f"Approximate {window} move on the gold current value: {_inr(move)} "
            f"({pct:.2f}% spot). This is an estimate, not a measured fund profit or loss."
        )
    return "\n".join(lines)
