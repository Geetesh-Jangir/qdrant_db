"""Portfolio drawback / weakness — routing, wave-2 drawdown, and deterministic answers."""

from __future__ import annotations

import re
from typing import Any

from news_rag.insight.contracts import ExecutionPlan, ToolCall

_DRAWBACK_HINTS = (
    "drawback",
    "drawdown",
    "weakness",
    "underperform",
    "not performing",
    "poor return",
    "low return",
    "worst fund",
    "biggest drag",
    "not doing well",
)

_INVESTOR_BOOK_HINTS = (
    "my portfolio",
    " my ",
    "my holdings",
    "my funds",
    "my book",
    "i hold",
    "i own",
    "our portfolio",
)


def question_signals_investor_book(question: str) -> bool:
    q = f" {(question or '').lower()} "
    if q.strip().startswith("my "):
        return True
    return any(hint in q for hint in _INVESTOR_BOOK_HINTS)


def plan_wants_portfolio_drawback(plan: ExecutionPlan, question: str = "") -> bool:
    blob = " ".join(
        str(part or "").lower()
        for part in (question, plan.planner_reading, plan.goal)
    )
    if any(hint in blob for hint in _DRAWBACK_HINTS):
        return True
    return False


def plan_wants_investor_drawdown_fetch(plan: ExecutionPlan, question: str = "") -> bool:
    """Wave 2 get_fund_data drawdown for each holding after get_investor_portfolio."""
    from news_rag.fund_drawdown import drawdown_words, is_drawdown_definition

    q = question or ""
    if is_drawdown_definition(q):
        return False
    asked = {str(x).lower() for x in (plan.asked_facts or [])}
    if "drawdown" not in asked and not drawdown_words(q):
        return False
    if str(plan.data_need or "").lower().strip() == "investor_risk":
        return True
    if str(getattr(plan, "holding_scope", "") or "").lower() == "all_holdings":
        return True
    return question_signals_investor_book(q)


def question_asks_portfolio_level_drawdown(question: str, plan: ExecutionPlan | None = None) -> bool:
    """Book-level max drawdown — not a single named scheme."""
    from news_rag.fund_drawdown import drawdown_words, is_drawdown_definition

    q = (question or "").strip()
    if is_drawdown_definition(q):
        return False
    if not drawdown_words(q) and "drawdown" not in q.lower():
        return False
    if plan is not None and str(plan.data_need or "").lower().strip() == "investor_risk":
        return question_signals_investor_book(q) or "portfolio" in q.lower()
    return question_signals_investor_book(q) and (
        "portfolio" in q.lower()
        or any(w in q.lower() for w in ("biggest", "largest", "worst", "maximum", "max "))
    )


def plan_wants_pure_concentration(plan: ExecutionPlan, question: str = "") -> bool:
    """Concentration-only template — not a broad drawback / weakness review."""
    if plan_wants_portfolio_drawback(plan, question):
        return False
    q = (question or "").lower()
    if "concentration" in q or "diversif" in q:
        return True
    text = " ".join(str(part or "").lower() for part in (plan.planner_reading, plan.goal))
    if ("concentration" in text or "diversif" in text) and "weakness" not in text and "drawback" not in text:
        return True
    return False


def plan_wants_fund_concentration(plan: ExecutionPlan, question: str = "") -> bool:
    """Holdings/sector concentration for one catalog scheme (not the investor book)."""
    from news_rag.insight.portfolio_scope import _data_need_is_investor

    if not plan_wants_pure_concentration(plan, question):
        return False
    if _data_need_is_investor(plan):
        return False
    if str(plan.portfolio_scope or "").lower().strip() == "investor":
        return False
    return bool(plan.funds) or str(plan.subject_ref or "").strip().lower() == "memory_primary"


def build_drawdown_wave2_calls(
    wave1_results: list[dict[str, Any]],
    *,
    plan: ExecutionPlan | None = None,
    question: str = "",
    max_funds: int = 8,
) -> list[ToolCall]:
    """Fetch trailing drawdown for each scheme in the user's book (wave 2)."""
    periods: list[str] = ["1y", "3y", "5y"]
    if plan is not None:
        for call in plan.tool_calls or []:
            if call.tool != "get_fund_data" or int(call.wave or 1) != 2:
                continue
            raw = (call.arguments or {}).get("periods")
            if raw:
                periods = [str(p) for p in raw if str(p).strip()]
            break

    investor = None
    for row in wave1_results or []:
        if row.get("tool") == "get_investor_portfolio" and row.get("ok"):
            data = row.get("data")
            if isinstance(data, dict):
                investor = data
                break
    if not investor:
        return []

    holdings = [
        h for h in (investor.get("holdings") or []) if isinstance(h, dict) and h.get("scheme_name")
    ]
    if plan_wants_investor_drawdown_fetch(plan, question) if plan else question_asks_portfolio_level_drawdown(
        question, plan
    ):
        holdings = [h for h in holdings if float(h.get("aum_inr") or 0) > 0]
        holdings.sort(key=lambda item: -float(item.get("aum_inr") or 0))
        cap = max(max_funds, 8)
    else:
        holdings.sort(key=lambda item: float(item.get("xirr_pct") or 0))
        cap = max_funds
    calls: list[ToolCall] = []
    for row in holdings[:cap]:
        name = str(row.get("scheme_name") or "").strip()
        if not name:
            continue
        calls.append(
            ToolCall(
                tool="get_fund_data",
                arguments={
                    "fund": name,
                    "modules": ["drawdown"],
                    "periods": periods,
                    "include_category": False,
                },
                wave=2,
                required=False,
                why=f"Drawdown and recovery for holding {name[:48]}",
            )
        )
    return calls


def attach_drawback_digest(
    data_pack: dict[str, Any],
    performance: dict[str, Any],
    plan: ExecutionPlan,
    question: str,
) -> None:
    if not plan_wants_portfolio_drawback(plan, question):
        return
    investor = data_pack.get("investor_portfolio")
    if not isinstance(investor, dict):
        return

    from news_rag.insight.pack_sanitize import (
        _rollup_investor_summary,
        scheme_gain_loss_pct,
        sort_holdings_weakest_first,
    )

    summary = _rollup_investor_summary(investor)
    holdings = [h for h in (investor.get("holdings") or []) if isinstance(h, dict)]
    holdings_sorted = sort_holdings_weakest_first(holdings)

    computed = investor.get("computed") if isinstance(investor.get("computed"), dict) else {}
    allocation = computed.get("allocation_by_category") or []

    underperformers = []
    for row in holdings_sorted:
        xirr = row.get("xirr_pct")
        gl = row.get("gain_loss_inr")
        if xirr is None and gl is None:
            continue
        underperformers.append(
            {
                "scheme_name": row.get("scheme_name"),
                "category": row.get("scheme_category"),
                "xirr_pct": xirr,
                "gain_loss_inr": gl,
                "gain_on_invested_pct": scheme_gain_loss_pct(row),
                "value_inr": row.get("aum_inr"),
                "invested_inr": row.get("invested_inr"),
            }
        )

    equity_pct = None
    alloc = investor.get("allocation") if isinstance(investor.get("allocation"), dict) else {}
    for row in alloc.get("schemeTypeShare") or []:
        if isinstance(row, dict) and str(row.get("name") or "").lower() == "equity":
            equity_pct = row.get("aum_pct")

    drawdown_by_fund: list[dict[str, Any]] = []
    for key, block in data_pack.items():
        if not str(key).startswith("fund:") or not isinstance(block, dict):
            continue
        dd = block.get("drawdown")
        if not isinstance(dd, dict):
            continue
        episodes = dd.get("episodes") if isinstance(dd.get("episodes"), list) else []
        if not episodes and isinstance(dd.get("1Y"), dict):
            episodes = [dd["1Y"]]
        fund_name = str(block.get("fund_name") or key.removeprefix("fund:")).strip()
        for ep in episodes[:2]:
            if not isinstance(ep, dict):
                continue
            drawdown_by_fund.append(
                {
                    "fund_name": fund_name,
                    "period": ep.get("period") or ep.get("label") or "1Y",
                    "max_drawdown_pct": ep.get("max_drawdown") or ep.get("max_drawdown_pct"),
                    "recovered": ep.get("recovered"),
                    "recovery_date": ep.get("recovery_date") or ep.get("recovered_on"),
                }
            )

    performance["investor_portfolio_drawback"] = {
        "portfolio_summary": summary,
        "equity_allocation_pct": equity_pct,
        "category_allocation": allocation,
        "underperformers": underperformers,
        "drawdown_by_holding": drawdown_by_fund,
        "composer_note": (
            "Answer the biggest drawback using underperformers (lowest XIRR / losses first), "
            "100% equity or category concentration if material, low portfolio absolute/XIRR returns, "
            "and drawdown recovery flags when present. Do not reply with only a concentration essay."
        ),
    }


def _fmt_inr(value: Any) -> str:
    from news_rag.indian_format import format_inr

    return format_inr(value)


def _pretty_category(name: str) -> str:
    text = (name or "").strip()
    if not text:
        return "—"
    return text[0].upper() + text[1:] if len(text) > 1 else text.upper()


def render_portfolio_drawback_answer(pack: Any, plan: ExecutionPlan, question: str = "") -> str | None:
    """Deterministic drawback review from investor book + optional drawdown fetches."""
    if not plan_wants_portfolio_drawback(plan, question):
        return None
    data = pack.data_pack if pack else {}
    investor = data.get("investor_portfolio")
    if not isinstance(investor, dict):
        return None

    from news_rag.insight.pack_sanitize import (
        _rollup_investor_summary,
        investor_holdings_for_display,
        scheme_gain_loss_pct,
        sort_holdings_weakest_first,
    )

    summary = _rollup_investor_summary(investor)
    holdings = [h for h in (investor.get("holdings") or []) if isinstance(h, dict)]
    sorted_all = sort_holdings_weakest_first(holdings)
    worst = sorted_all[0] if sorted_all else None
    if not worst:
        return None

    w_name = str(worst.get("scheme_name") or "")
    w_xirr = worst.get("xirr_pct")
    w_gl = worst.get("gain_loss_inr")
    w_gain_pct = scheme_gain_loss_pct(worst)

    meta = investor.get("meta") if isinstance(investor.get("meta"), dict) else {}
    as_of = str(meta.get("as_of_date") or "").strip()

    lines: list[str] = []
    headline = f"### Biggest drawback in your portfolio"
    if as_of:
        headline += f" (as of {as_of})"
    lines.append(headline)
    lines.append("")

    if w_xirr is not None or w_gl is not None:
        lead = f"The main drag is **{w_name}**"
        if w_xirr is not None:
            lead += f", with XIRR **{float(w_xirr):.2f}%**"
        if w_gl is not None:
            lead += f" and {_fmt_inr(w_gl)} gain/loss"
            if w_gain_pct is not None:
                lead += f" (**{w_gain_pct:.2f}%** on amount invested)"
        lead += "."
        lines.append(lead)
    lines.append("")

    port_xirr = summary.get("portfolio_xirr_pct")
    port_gl = summary.get("gain_loss_inr")
    if port_xirr is not None or port_gl is not None:
        lines.append("### Overall returns")
        lines.append("")
        bits = []
        if summary.get("invested_inr") is not None and summary.get("aum_inr") is not None:
            bits.append(
                f"Book value {_fmt_inr(summary.get('aum_inr'))} on {_fmt_inr(summary.get('invested_inr'))} invested"
            )
        if port_gl is not None:
            bits.append(f"total gain/loss {_fmt_inr(port_gl)}")
        if summary.get("absolute_return_pct") is not None:
            bits.append(f"**{float(summary.get('absolute_return_pct')):.2f}%** on invested (book-wide)")
        if port_xirr is not None:
            bits.append(f"**{float(port_xirr):.2f}%** portfolio XIRR")
        lines.append(". ".join(bits) + ".")
        lines.append("")

    computed = investor.get("computed") if isinstance(investor.get("computed"), dict) else {}
    allocation = computed.get("allocation_by_category") or []
    if allocation:
        lines.append("### Allocation")
        lines.append("")
        lines.append("| Category | Weight | Value (₹) |")
        lines.append("| --- | ---: | ---: |")
        for row in allocation:
            if not isinstance(row, dict):
                continue
            cat = _pretty_category(str(row.get("category") or ""))
            pct = row.get("weight_pct")
            val = row.get("value_inr")
            if val is None and pct is not None and summary.get("aum_inr"):
                val = float(summary["aum_inr"]) * float(pct) / 100.0
            lines.append(
                f"| {cat} | {float(pct):.2f}% | {_fmt_inr(val).replace('₹', '')} |"
                if pct is not None
                else f"| {cat} | — | — |"
            )
        equity_note = ""
        for row in (investor.get("allocation") or {}).get("schemeTypeShare") or []:
            if isinstance(row, dict) and str(row.get("name") or "").lower() == "equity":
                equity_note = f" The book is **{float(row.get('aum_pct') or 0):.0f}% equity**."
                break
        if equity_note:
            lines.append("")
            lines.append(equity_note.strip())
        lines.append("")

    display_rows, total_schemes, truncated = investor_holdings_for_display(
        holdings, question, plan, sort_weakest=True
    )
    lines.append("### Scheme performance (weakest first)")
    lines.append("")
    lines.append("| Scheme | XIRR | Gain/loss (₹) | Gain on invested |")
    lines.append("| --- | ---: | ---: | ---: |")
    for row in display_rows:
        xirr = row.get("xirr_pct")
        gl = row.get("gain_loss_inr")
        gain_pct = scheme_gain_loss_pct(row)
        lines.append(
            "| {name} | {xirr} | {gl} | {gp} |".format(
                name=str(row.get("scheme_name") or "")[:64],
                xirr=f"{float(xirr):.2f}%" if xirr is not None else "—",
                gl=_fmt_inr(gl).replace("₹", "") if gl is not None else "—",
                gp=f"{gain_pct:.2f}%" if gain_pct is not None else "—",
            )
        )
    if truncated:
        lines.append("")
        lines.append(
            f"*Showing {len(display_rows)} of {total_schemes} schemes (weakest by gain/loss); "
            f"totals above include all schemes.*"
        )
    lines.append("")

    dd_rows: list[str] = []
    for key, block in data.items():
        if not str(key).startswith("fund:") or not isinstance(block, dict):
            continue
        dd = block.get("drawdown")
        if not isinstance(dd, dict):
            continue
        fund_label = str(block.get("fund_name") or key.removeprefix("fund:"))[:48]
        episodes = dd.get("episodes") if isinstance(dd.get("episodes"), list) else []
        for label, ep_key in (("1Y", "1Y"), ("3Y", "3Y")):
            ep = dd.get(ep_key) if isinstance(dd.get(ep_key), dict) else None
            if ep:
                episodes = [ep] + episodes
        seen = set()
        for ep in episodes:
            if not isinstance(ep, dict):
                continue
            period = str(ep.get("period") or ep.get("label") or "1Y")
            key_id = (fund_label, period)
            if key_id in seen:
                continue
            seen.add(key_id)
            fall = ep.get("max_drawdown") or ep.get("max_drawdown_pct")
            recovered = ep.get("recovered")
            if fall is None:
                continue
            status = "recovered" if recovered else "not yet recovered"
            dd_rows.append(f"| {fund_label} | {period} | {abs(float(fall)):.2f}% | {status} |")

    if dd_rows:
        lines.append("### Drawdown and recovery (catalog)")
        lines.append("")
        lines.append("| Fund | Period | Max fall | Status |")
        lines.append("| --- | --- | ---: | --- |")
        lines.extend(dd_rows)
        lines.append("")

    conc = investor.get("concentration")
    if isinstance(conc, dict) and conc.get("top_holdings_weight_pct") is not None:
        lines.append("### Underlying concentration")
        lines.append("")
        lines.append(
            f"Top underlying names are **{float(conc.get('top_holdings_weight_pct')):.2f}%** of combined "
            f"holdings — stock-level concentration is moderate; scheme-level mix is shown above."
        )

    return "\n".join(lines).strip()
