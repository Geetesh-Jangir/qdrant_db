"""Normalize LLM query plans into executable sub-queries (one primary output each)."""

from __future__ import annotations

import re
from typing import Any

from news_rag.query_plan import DataNeed, QueryPlan, SubQuery

_FUND_TOOLS = frozenset({"fund_nav", "fund_holdings", "fund_sectors"})


def _wants_holdings_list(question: str) -> bool:
    lower = question.lower()
    if re.search(r"\btop\s*\d+\s+holdings?\b", lower):
        return True
    if re.search(r"\blist\b", lower) and re.search(r"\bholdings?\b", lower):
        return True
    return False


def _wants_impact(question: str) -> bool:
    lower = question.lower()
    if re.search(r"\b(affecting|affected|impact|influence|related|relation)\b", lower):
        return True
    return bool(re.search(r"\b(crude|oil|petroleum|gold|rbi|repo)\b", lower))


def _impact_clause_from_question(question: str) -> str:
    m = re.search(r"\band\b(.+)$", question, re.I)
    if m:
        return m.group(1).strip().rstrip("?")
    return ""


def _has_macro_topic(text: str) -> bool:
    lower = (text or "").lower()
    return bool(re.search(r"\b(crude|oil|petroleum|brent|rbi|repo|gold|silver)\b", lower))


def _impact_subquery_text(question: str, news_need: DataNeed) -> str:
    clause = _impact_clause_from_question(question)
    if clause and (_has_macro_topic(clause) or _wants_impact(clause)):
        return clause
    sem = (news_need.semantic_query or "").strip()
    if sem and _has_macro_topic(sem):
        return sem
    if clause:
        return clause
    if sem:
        return sem
    return "News impact on the fund"


def _primary_fund_raw(sq: SubQuery) -> str:
    for need in sq.data_needs:
        if need.fund_raw:
            return need.fund_raw
    return ""


def _split_sub_query(sq: SubQuery, *, question: str) -> list[SubQuery]:
    """One sub-query with multiple fund tools → several sub-queries."""
    nav_needs = [n for n in sq.data_needs if n.tool == "fund_nav"]
    hold_needs = [n for n in sq.data_needs if n.tool == "fund_holdings"]
    sector_needs = [n for n in sq.data_needs if n.tool == "fund_sectors"]
    news_needs = [n for n in sq.data_needs if n.tool == "news_search"]
    other_needs = [n for n in sq.data_needs if n.tool not in _FUND_TOOLS and n.tool != "news_search"]

    fund_raw = _primary_fund_raw(sq)
    lower_q = question.lower()
    performance = bool(
        re.search(r"\b(working|performing|performance|last\s+month|past\s+month|how\s+is|how\s+has)\b", lower_q)
    )

    out: list[SubQuery] = []
    next_id = 1
    base_id = sq.id or "Q1"
    first_fund_id = base_id

    if nav_needs or (not hold_needs and not sector_needs and news_needs and fund_raw):
        nav_need = nav_needs[0] if nav_needs else DataNeed(tool="fund_nav", fund_raw=fund_raw, scope="with_returns")
        if performance and nav_need.scope == "latest_only":
            nav_need.scope = "with_returns"
        style = "performance_summary" if performance else "one_metric"
        needs: list[DataNeed] = [nav_need]
        out.append(
            SubQuery(
                id=f"{base_id}" if next_id == 1 else f"{base_id}_{next_id}",
                text=sq.text or "Fund performance",
                answer_style=style,
                needs_reasoning=False,
                data_needs=needs,
            )
        )
        first_fund_id = out[-1].id
        next_id += 1

    skip_holdings_list = bool(news_needs and _wants_impact(question) and not _wants_holdings_list(question))
    if hold_needs and not skip_holdings_list:
        hn = hold_needs[0]
        if not hn.fund_raw:
            hn.fund_raw = fund_raw
        if not hn.fund_ref and fund_raw:
            hn.fund_ref = first_fund_id
        top = hn.top_n or 5
        m = re.search(r"\btop\s*(\d{1,2})\b", question, re.I)
        if m:
            top = max(1, min(int(m.group(1)), 25))
        hn.top_n = top
        out.append(
            SubQuery(
                id=f"{base_id}_{next_id}" if len(out) else base_id,
                text="Top holdings",
                answer_style="short_list",
                needs_reasoning=False,
                data_needs=[hn],
            )
        )
        next_id += 1
        hold_needs = []

    if sector_needs:
        sn = sector_needs[0]
        if not sn.fund_raw:
            sn.fund_raw = fund_raw
        if not sn.fund_ref and fund_raw:
            sn.fund_ref = first_fund_id
        out.append(
            SubQuery(
                id=f"{base_id}_{next_id}",
                text="Sector allocation",
                answer_style="short_table",
                needs_reasoning=False,
                data_needs=[sn],
            )
        )
        next_id += 1

    if news_needs:
        if _wants_impact(question):
            impact_text = _impact_subquery_text(question, news_needs[0])
            hold_for_refine = hold_needs[0] if hold_needs else DataNeed(
                tool="fund_holdings",
                fund_ref=first_fund_id,
                fund_raw=fund_raw,
                scope="top_n",
                top_n=8,
            )
            out.append(
                SubQuery(
                    id=f"{base_id}_{next_id}",
                    text=impact_text,
                    answer_style="exposure_note",
                    needs_reasoning=True,
                    data_needs=[hold_for_refine, news_needs[0]],
                )
            )
            next_id += 1
        elif not performance:
            out.append(
                SubQuery(
                    id=f"{base_id}_{next_id}",
                    text=sq.text or "News",
                    answer_style="news_brief",
                    needs_reasoning=True,
                    data_needs=news_needs,
                )
            )
            next_id += 1

    for need in other_needs:
        out.append(
            SubQuery(
                id=f"{base_id}_{next_id}",
                text=sq.text,
                answer_style="short_list",
                needs_reasoning=False,
                data_needs=[need],
            )
        )
        next_id += 1

    return out if out else [sq]


def _ensure_explicit_asks(question: str, plan: QueryPlan) -> QueryPlan:
    """If the user explicitly asked for holdings/sectors but the plan omitted the tool, add a sub-query."""
    lower = question.lower()
    has_hold = any(n.tool == "fund_holdings" for sq in plan.sub_queries for n in sq.data_needs)
    has_sectors = any(n.tool == "fund_sectors" for sq in plan.sub_queries for n in sq.data_needs)

    fund_raw = ""
    for sq in plan.sub_queries:
        fund_raw = _primary_fund_raw(sq) or fund_raw
        for need in sq.data_needs:
            if need.fund_raw:
                fund_raw = need.fund_raw
                break

    if not fund_raw:
        return plan

    first_id = plan.sub_queries[0].id if plan.sub_queries else "Q1"
    extra: list[SubQuery] = []

    if re.search(r"\bholdings?\b", lower) and not has_hold and not (
        _wants_impact(question) and not _wants_holdings_list(question)
    ):
        top = 5
        m = re.search(r"\btop\s*(\d{1,2})\b", question, re.I)
        if m:
            top = max(1, min(int(m.group(1)), 25))
        extra.append(
            SubQuery(
                id=f"Q{len(plan.sub_queries) + len(extra) + 1}",
                text="Top holdings",
                answer_style="short_list",
                needs_reasoning=False,
                data_needs=[
                    DataNeed(
                        tool="fund_holdings",
                        fund_ref=first_id,
                        fund_raw=fund_raw,
                        scope="top_n",
                        top_n=top,
                    )
                ],
            )
        )

    if re.search(r"\bsectors?\b", lower) and not has_sectors and (
        "sector allocation" in lower or re.search(r"\btop\s*\d+\s+sectors?\b", lower)
    ):
        top = 5
        m = re.search(r"\btop\s*(\d{1,2})\b", question, re.I)
        if m:
            top = max(1, min(int(m.group(1)), 25))
        extra.append(
            SubQuery(
                id=f"Q{len(plan.sub_queries) + len(extra) + 1}",
                text="Top sectors",
                answer_style="short_table",
                needs_reasoning=False,
                data_needs=[
                    DataNeed(
                        tool="fund_sectors",
                        fund_ref=first_id,
                        fund_raw=fund_raw,
                        scope="top_n",
                        top_n=top,
                    )
                ],
            )
        )

    if not extra:
        return plan
    subs = list(plan.sub_queries) + extra
    return QueryPlan(sub_queries=subs[:4], raw_json=plan.raw_json, source=plan.source + "+explicit")


def normalize_query_plan(plan: QueryPlan, question: str) -> QueryPlan:
    """Expand multi-tool / multi_block plans into one-output sub-queries."""
    if not plan.sub_queries:
        return plan

    expanded: list[SubQuery] = []
    for sq in plan.sub_queries:
        fund_tool_count = sum(1 for n in sq.data_needs if n.tool in _FUND_TOOLS)
        multi_tool = fund_tool_count > 1 or (
            fund_tool_count >= 1 and len(sq.data_needs) > fund_tool_count
        )
        if sq.answer_style == "multi_block" or multi_tool:
            expanded.extend(_split_sub_query(sq, question=question))
        else:
            expanded.append(sq)

    # Re-id sequentially Q1, Q2, ...
    renumbered: list[SubQuery] = []
    id_map: dict[str, str] = {}
    for i, sq in enumerate(expanded[:4], start=1):
        new_id = f"Q{i}"
        id_map[sq.id] = new_id
        renumbered.append(
            SubQuery(
                id=new_id,
                text=sq.text,
                answer_style=sq.answer_style,
                needs_reasoning=sq.needs_reasoning,
                data_needs=[],
            )
        )
        for need in sq.data_needs:
            nd = DataNeed(
                tool=need.tool,
                fund_raw=need.fund_raw,
                fund_ref=id_map.get(need.fund_ref, need.fund_ref) if need.fund_ref else "",
                scope=need.scope,
                top_n=need.top_n,
                stock_name=need.stock_name,
                sector_name=need.sector_name,
                semantic_query=need.semantic_query,
                depends_on_portfolio=need.depends_on_portfolio,
                window_days=need.window_days,
            )
            if nd.fund_ref and nd.fund_ref not in id_map.values() and nd.fund_ref in id_map:
                nd.fund_ref = id_map[nd.fund_ref]
            renumbered[-1].data_needs.append(nd)

    # Fix fund_ref: holdings should ref first sub-query with fund_nav
    first_with_nav = next((s.id for s in renumbered if any(n.tool == "fund_nav" for n in s.data_needs)), renumbered[0].id)
    for sq in renumbered:
        for need in sq.data_needs:
            if need.tool in ("fund_holdings", "fund_sectors") and need.fund_ref and need.fund_ref == sq.id:
                need.fund_ref = first_with_nav
            if need.tool in ("fund_holdings", "fund_sectors") and not need.fund_ref and not need.fund_raw:
                need.fund_ref = first_with_nav

    normalized = QueryPlan(sub_queries=renumbered, raw_json=plan.raw_json, source=plan.source + "+normalized")
    normalized = _rebalance_compound_plan(question, normalized)
    normalized = _collapse_duplicate_impact_sections(question, normalized)
    return _ensure_explicit_asks(question, normalized)


def _collapse_duplicate_impact_sections(question: str, plan: QueryPlan) -> QueryPlan:
    """One macro/impact ask → at most one exposure_note (LLM often emits two)."""
    if not plan.sub_queries or not _wants_impact(question):
        return plan

    impact_styles = frozenset({"exposure_note", "news_brief"})
    impact_subs = [s for s in plan.sub_queries if s.answer_style in impact_styles]
    if not impact_subs:
        return plan

    fund_raw = ""
    for sq in plan.sub_queries:
        fund_raw = _primary_fund_raw(sq) or fund_raw
        for need in sq.data_needs:
            if need.fund_raw:
                fund_raw = need.fund_raw

    first_nav_id = next(
        (s.id for s in plan.sub_queries if any(n.tool == "fund_nav" for n in s.data_needs)),
        plan.sub_queries[0].id,
    )

    if len(impact_subs) == 1 and impact_subs[0].answer_style == "exposure_note":
        only = impact_subs[0]
        clause = _impact_subquery_text(question, next((n for n in only.data_needs if n.tool == "news_search"), DataNeed(tool="news_search")))
        if only.text.strip() != clause.strip():
            rebuilt = []
            for sq in plan.sub_queries:
                if sq.id == only.id:
                    news = [n for n in sq.data_needs if n.tool == "news_search"]
                    rest = [n for n in sq.data_needs if n.tool != "news_search"]
                    if news:
                        news[0].semantic_query = clause
                    rebuilt.append(
                        SubQuery(
                            id=sq.id,
                            text=clause,
                            answer_style="exposure_note",
                            needs_reasoning=True,
                            data_needs=rest + news,
                        )
                    )
                else:
                    rebuilt.append(sq)
            return QueryPlan(sub_queries=rebuilt, raw_json=plan.raw_json, source=plan.source + "+impact1")
        return plan

    merged = _merge_impact_subqueries(question, impact_subs, first_nav_id, fund_raw)
    rebuilt: list[SubQuery] = []
    merged_used = False
    for sq in plan.sub_queries:
        if sq.answer_style in impact_styles:
            if not merged_used:
                rebuilt.append(merged)
                merged_used = True
        else:
            rebuilt.append(sq)

    renumbered: list[SubQuery] = []
    for i, sq in enumerate(rebuilt[:4], start=1):
        new_id = f"Q{i}"
        renumbered.append(
            SubQuery(
                id=new_id,
                text=sq.text,
                answer_style=sq.answer_style,
                needs_reasoning=sq.needs_reasoning,
                data_needs=list(sq.data_needs),
            )
        )
    first_nav = next((s.id for s in renumbered if any(n.tool == "fund_nav" for n in s.data_needs)), renumbered[0].id)
    for sq in renumbered:
        for need in sq.data_needs:
            if need.tool in ("fund_holdings", "fund_sectors") and not need.fund_ref:
                need.fund_ref = first_nav
    return QueryPlan(sub_queries=renumbered, raw_json=plan.raw_json, source=plan.source + "+impact_merged")


def _merge_impact_subqueries(
    question: str,
    impact_subs: list[SubQuery],
    first_nav_id: str,
    fund_raw: str,
) -> SubQuery:
    news_needs: list[DataNeed] = []
    hold: DataNeed | None = None
    for sq in impact_subs:
        for n in sq.data_needs:
            if n.tool == "news_search":
                news_needs.append(n)
            elif n.tool == "fund_holdings" and hold is None:
                hold = n

    def _news_rank(n: DataNeed) -> int:
        q = (n.semantic_query or "").lower()
        score = 0
        if _has_macro_topic(q):
            score += 3
        if _wants_impact(q):
            score += 1
        return score

    news = max(news_needs, key=_news_rank) if news_needs else DataNeed(
        tool="news_search",
        semantic_query="",
        depends_on_portfolio=True,
        window_days=30,
    )
    clause = _impact_subquery_text(question, news)
    news.semantic_query = clause
    if not news.depends_on_portfolio:
        news.depends_on_portfolio = True
    if not news.window_days:
        news.window_days = 30

    hold = hold or DataNeed(
        tool="fund_holdings",
        fund_ref=first_nav_id,
        fund_raw=fund_raw,
        scope="top_n",
        top_n=8,
    )
    return SubQuery(
        id="Qx",
        text=clause,
        answer_style="exposure_note",
        needs_reasoning=True,
        data_needs=[hold, news],
    )


def _rebalance_compound_plan(question: str, plan: QueryPlan) -> QueryPlan:
    """Strip news from performance; replace spurious holdings lists on impact asks."""
    if not plan.sub_queries:
        return plan

    wants_hold = _wants_holdings_list(question)
    wants_impact = _wants_impact(question)
    fund_raw = ""
    for sq in plan.sub_queries:
        for need in sq.data_needs:
            if need.fund_raw:
                fund_raw = need.fund_raw
                break

    first_nav_id = next(
        (s.id for s in plan.sub_queries if any(n.tool == "fund_nav" for n in s.data_needs)),
        plan.sub_queries[0].id,
    )

    rebuilt: list[SubQuery] = []
    loose_news: list[DataNeed] = []
    loose_hold: DataNeed | None = None

    for sq in plan.sub_queries:
        nav_needs = [n for n in sq.data_needs if n.tool == "fund_nav"]
        news_needs = [n for n in sq.data_needs if n.tool == "news_search"]
        hold_needs = [n for n in sq.data_needs if n.tool == "fund_holdings"]
        other = [n for n in sq.data_needs if n.tool not in _FUND_TOOLS and n.tool != "news_search"]

        if sq.answer_style == "performance_summary" or (nav_needs and sq.answer_style == "one_metric"):
            loose_news.extend(news_needs)
            rebuilt.append(
                SubQuery(
                    id=sq.id,
                    text=sq.text or "Fund performance",
                    answer_style=sq.answer_style if sq.answer_style != "one_metric" else "performance_summary",
                    needs_reasoning=False,
                    data_needs=nav_needs,
                )
            )
            continue

        if (
            sq.answer_style == "short_list"
            and hold_needs
            and wants_impact
            and not wants_hold
        ):
            loose_hold = hold_needs[0]
            loose_news.extend(news_needs)
            continue

        if sq.answer_style == "exposure_note":
            rebuilt.append(sq)
            continue

        rebuilt.append(sq)

    has_exposure = any(s.answer_style == "exposure_note" for s in rebuilt)
    if wants_impact and not has_exposure:
        news_need = loose_news[0] if loose_news else DataNeed(
            tool="news_search",
            semantic_query=_impact_subquery_text(question, DataNeed(tool="news_search")),
            depends_on_portfolio=True,
            window_days=30,
        )
        if not news_need.depends_on_portfolio:
            news_need.depends_on_portfolio = True
        hold_need = loose_hold or DataNeed(
            tool="fund_holdings",
            fund_ref=first_nav_id,
            fund_raw=fund_raw,
            scope="top_n",
            top_n=8,
        )
        rebuilt.append(
            SubQuery(
                id=f"Q{len(rebuilt) + 1}",
                text=_impact_subquery_text(question, news_need),
                answer_style="exposure_note",
                needs_reasoning=True,
                data_needs=[hold_need, news_need],
            )
        )

    if not rebuilt:
        return plan

    renumbered: list[SubQuery] = []
    id_map: dict[str, str] = {}
    for i, sq in enumerate(rebuilt[:4], start=1):
        new_id = f"Q{i}"
        id_map[sq.id] = new_id
        renumbered.append(
            SubQuery(
                id=new_id,
                text=sq.text,
                answer_style=sq.answer_style,
                needs_reasoning=sq.needs_reasoning,
                data_needs=[],
            )
        )
        for need in sq.data_needs:
            nd = DataNeed(
                tool=need.tool,
                fund_raw=need.fund_raw,
                fund_ref=id_map.get(need.fund_ref, need.fund_ref) if need.fund_ref else "",
                scope=need.scope,
                top_n=need.top_n,
                stock_name=need.stock_name,
                sector_name=need.sector_name,
                semantic_query=need.semantic_query,
                depends_on_portfolio=need.depends_on_portfolio,
                window_days=need.window_days,
            )
            renumbered[-1].data_needs.append(nd)

    first_nav = next((s.id for s in renumbered if any(n.tool == "fund_nav" for n in s.data_needs)), renumbered[0].id)
    for sq in renumbered:
        for need in sq.data_needs:
            if need.tool in ("fund_holdings", "fund_sectors") and (not need.fund_ref or need.fund_ref not in {s.id for s in renumbered}):
                need.fund_ref = first_nav

    return QueryPlan(sub_queries=renumbered, raw_json=plan.raw_json, source=plan.source + "+rebalanced")
