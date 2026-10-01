"""Agent 2 & Writer: Structured insight generation strictly aligned to the Answer Contract."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from historical_data.metals_service import format_metals_context_for_llm, get_latest_metals_spot
from historical_data.nav_service import get_fund_nav_history
from historical_data.stocks_service import get_stock_profile
from news_rag.answer_contract import AnswerContract, check_answer_alignment, plan_answer_contract
from news_rag.config import get_settings
from news_rag.fund_facts import try_fund_fact_answer
from news_rag.fund_search import extract_top_holdings, extract_top_sectors
from news_rag.insight_format import (
    clamp_bullets,
    clamp_summary,
    format_insight_display,
    parse_structured_insight,
)
from news_rag.llm_client import call_insight_llm, llm_api_key_configured, missing_llm_key_message
from news_rag.parse import ParsedQuery
from news_rag.query_log import clip_log_text
from news_rag.query_router import RouterFund, RouterResult

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

WRITER_SYSTEM_PROMPT = """You are an elite financial intelligence and investment storytelling expert for Indian mutual fund investors.
Your task is to answer the user's question directly, clearly, and concisely, strictly adhering to the provided ANSWER CONTRACT.

RULES:
1. STRICTLY OBEY THE ANSWER CONTRACT:
   - Address all points listed in "MUST ANSWER".
   - Under no circumstances include or mention topics listed in "FORBIDDEN".
   - Use ONLY the provided context blocks (Verified Articles, Fund NAV, Fund Holdings, Sector Allocations, Stock Quotes, Metals Prices). Do NOT hallucinate unverified data.
   - If no news articles or data were found for a specific event or query, state clearly and politely that no verified news was found in the store for that topic.

2. EXPLAIN UNFAMILIAR TERMS IN BRACKETS (...):
   - Whenever you mention a technical term, regulatory policy, financial ratio, or metric that an ordinary beginner wouldn't know, explain it simply inside parentheses (...).
   - Examples: "NIM (the profit margin a bank makes on loans)", "10-year G-sec yield (the benchmark interest rate the government pays to borrow money)", "Repo Rate (the RBI interest rate for lending to commercial banks)".

3. HIGHLIGHT KEY METRICS & NAMES:
   - Use **bold** selectively on key company names, fund names, percentages, and figures.

4. TONE & JARGON:
   - Use plain, conversational English.
   - Strictly NO buy/sell/hold recommendations.

5. OUTPUT FORMAT:
For pure list / breakdown queries (e.g., sector allocations, top holdings):
BULLETS:
- **[Item Name]**: [Percentage]% [(brief explanation of sector/industry if helpful)]
(Provide ALL requested items in the bullet list. Do NOT write a redundant summary paragraph re-listing the items. Leave SUMMARY empty.)

For conceptual definitions or single-fact answers (NAV, single metric, simple explanation):
SUMMARY:
[One clear, simple, cohesive explanation paragraph (40-80 words). No bullet points.]

For news analysis, portfolio impact, and multi-factor answers:
BULLETS:
- [Clear bullet line explaining the event/fact with bracketed explanation of unfamiliar terms and business impact]
- [Next bullet line...]

SUMMARY:
[One cohesive storytelling paragraph (60-120 words) connecting the key points to the broader market and investor takeaway. Do NOT just repeat the bullet points.]
"""

REWRITE_SYSTEM_PROMPT = """You are a strict financial alignment editor.
Your previous draft had alignment issues with the answer contract.
Rewrite the response to address the missing points and completely eliminate the forbidden/extra content.

Adhere strictly to:
- Addressing all points in MUST ANSWER.
- Removing anything in FORBIDDEN / EXTRA.
- Keeping language simple with bracketed explanations (...) on unfamiliar terms.
- No buy/sell advice.

OUTPUT FORMAT:
BULLETS: (if applicable)
- [Bullet points...]

SUMMARY:
[Cohesive explanation paragraph...]
"""


def _sources_from_articles(articles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    for a in articles:
        url = str(a.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        rows.append(
            {
                "title": a.get("title"),
                "url": url,
                "source": a.get("source"),
                "published_at": a.get("published_at"),
            }
        )
    return rows


def empty_answer(parsed: ParsedQuery) -> dict[str, Any]:
    """Fallback when no context or articles exist."""
    if parsed.fund_ambiguous:
        names_str = ", ".join(parsed.close_funds) if parsed.close_funds else "multiple schemes"
        msg = f"The query matched multiple mutual funds: {names_str}. Please specify the full fund name or ISIN."
    elif parsed.intent in ("fund_nav", "fund_holdings", "fund_sectors") and not parsed.fund_resolved:
        msg = "Please specify a valid mutual fund name or ISIN to view fund details."
    elif parsed.entity_resolved:
        names = ", ".join(parsed.entity_resolved)
        msg = f"No recent news matching '{names}' was found in the verified store for {parsed.window_label}."
    else:
        msg = f"No matching news was found in the verified store for {parsed.window_label}."

    return {
        "insight_bullets": [],
        "insight_summary": msg,
        "insight": msg,
        "sources": [],
        "intent": parsed.intent,
        "insight_source": "no_articles",
    }


def generate_answer(
    parsed: ParsedQuery,
    articles: list[dict],
    *,
    query_log: QueryLogger | None = None,
) -> dict[str, Any]:
    """Generates contract-governed answer with alignment check and single rewrite."""
    settings = get_settings()

    if query_log is not None:
        query_log.write(f"answer_phase start intent={parsed.intent} articles_retrieved={len(articles)}")

    # 1. Handle Ambiguous Fund matches early
    if parsed.fund_ambiguous:
        result = empty_answer(parsed)
        if query_log is not None:
            query_log.log_insight_output(
                insight_source=result["insight_source"],
                char_count=len(result.get("insight") or ""),
                preview=str(result.get("insight") or ""),
            )
        return result

    if parsed.intent in ("fund_nav", "fund_holdings", "fund_sectors") and not parsed.fund_resolved:
        result = empty_answer(parsed)
        if query_log is not None:
            query_log.log_insight_output(
                insight_source=result["insight_source"],
                char_count=len(result.get("insight") or ""),
                preview=str(result.get("insight") or ""),
            )
        return result

    fact = try_fund_fact_answer(parsed)
    if fact is not None:
        if query_log is not None:
            query_log.write("answer_path fund_facts deterministic=true llm_skipped=true")
            query_log.log_insight_output(
                insight_source=fact["insight_source"],
                char_count=len(fact.get("insight") or ""),
                preview=str(fact.get("insight") or "")[:500],
            )
        return fact

    if not llm_api_key_configured(settings):
        raise RuntimeError(missing_llm_key_message(settings))

    # 2. Gather Evidence and External Data Blocks
    router = parsed.router_result or RouterResult(
        intent=parsed.intent,
        fund=RouterFund(),
        companies=parsed.entity_resolved,
        event_focus="",
        window_days=None,
        asked=parsed.sub_questions,
    )

    fund_detail = parsed.fund_resolved
    fund_isin = fund_detail.get("isin", "") if fund_detail else ""
    fund_name = fund_detail.get("fund_short_name", "") or fund_detail.get("fund_name", "") if fund_detail else ""

    nav_info = None
    if fund_isin:
        try:
            nav_info = get_fund_nav_history(fund_isin)
        except Exception as exc:
            logger.warning("Could not fetch NAV history for %s: %s", fund_isin, exc)

    m_req = re.search(r"\btop\s*(\d{1,2})\b", parsed.question, re.I)
    requested_count = int(m_req.group(1)) if m_req else (10 if parsed.intent in ("fund_sectors", "fund_holdings") else 5)
    requested_count = max(1, min(requested_count, 25))

    top_holdings = extract_top_holdings(fund_detail, limit=max(10, requested_count)) if fund_detail else []
    top_sectors = extract_top_sectors(fund_detail, limit=max(10, requested_count)) if fund_detail else []

    stock_profiles: list[dict[str, Any]] = []
    if router.companies or (parsed.stock_hint and parsed.intent == "single_stock"):
        target_names = router.companies if router.companies else [parsed.stock_hint]
        for name in target_names[:3]:
            try:
                prof = get_stock_profile(name)
                if prof and isinstance(prof, dict):
                    stock_profiles.append({"company_name": name, **prof})
            except Exception as exc:
                logger.warning("Could not fetch stock quote for %s: %s", name, exc)

    metals_context_str = ""
    latest_metals = {}
    if parsed.intent == "bullion" or any(w in parsed.question.lower() for w in ("gold", "silver", "bullion")):
        try:
            metals_context_str = format_metals_context_for_llm()
            latest_metals = get_latest_metals_spot()
        except Exception as exc:
            logger.warning("Could not fetch metals context: %s", exc)

    # 3. Build Inventory for Contract Planning
    inventory = {
        "has_nav": bool(nav_info and nav_info.get("success")),
        "has_holdings": bool(top_holdings),
        "has_sectors": bool(top_sectors),
        "has_stock_prices": bool(stock_profiles),
        "has_metals": bool(metals_context_str),
        "articles": articles,
    }

    # 4. Plan Contract via Agent 2
    contract = plan_answer_contract(parsed.question, router, inventory, query_log=query_log)
    parsed.contract = contract

    # 5. Filter Articles according to Contract
    filtered_articles = [articles[i] for i in contract.use_articles if i < len(articles)]
    sources = _sources_from_articles(filtered_articles)
    if query_log is not None:
        query_log.log_article_filter(
            retrieved_count=len(articles),
            use_articles=list(contract.use_articles),
            kept_count=len(filtered_articles),
        )
        if articles and not filtered_articles:
            query_log.write(
                "contract_dropped_all_articles "
                "retrieval_had_hits=true but contract use_articles excluded every item"
            )

    # 6. Assemble Prompt Payload for Writer
    context_blocks: list[str] = []

    # Optional NAV block
    if contract.include_nav and nav_info and nav_info.get("success"):
        stats = nav_info.get("stats") or {}
        w1 = stats.get("1W") or {}
        m1 = stats.get("1M") or {}
        y1 = stats.get("1Y") or {}
        nav_lines = [
            f"[FUND NAV PERFORMANCE: {fund_name}]",
            f"- Current NAV: ₹{nav_info.get('latest_nav')} (Date: {nav_info.get('latest_date')})",
        ]
        if w1:
            nav_lines.append(f"- 1-Week Change: {w1.get('change_pct', 0):+.2f}% (from ₹{w1.get('start_nav')} to ₹{w1.get('end_nav')}, range: ₹{w1.get('min_nav')}–₹{w1.get('max_nav')})")
        if m1:
            nav_lines.append(f"- 1-Month Change: {m1.get('change_pct', 0):+.2f}% (range: ₹{m1.get('min_nav')}–₹{m1.get('max_nav')})")
        if y1:
            nav_lines.append(f"- 1-Year Change: {y1.get('change_pct', 0):+.2f}%")
        context_blocks.append("\n".join(nav_lines))

    # Optional Holdings block
    if contract.include_holdings and top_holdings:
        h_lines = [f"[FUND TOP HOLDINGS: {fund_name}]"]
        for h in top_holdings:
            h_lines.append(f"- {h['name']}: {h['percentage']:.2f}% ({h.get('industry', 'Equity')})")
        context_blocks.append("\n".join(h_lines))

    # Optional Sectors block
    if contract.include_sectors and top_sectors:
        s_lines = [f"[FUND SECTOR ALLOCATIONS: {fund_name}]"]
        for s in top_sectors:
            s_lines.append(f"- {s['sector']}: {s['percentage']:.2f}%")
        context_blocks.append("\n".join(s_lines))

    # Optional Stock Price block
    if contract.include_stock_price and stock_profiles:
        st_lines = ["[STOCK PRICE ACTION & RETURNS]"]
        for p in stock_profiles:
            r30 = p.get("range_30d") or (0.0, 0.0)
            st_lines.append(f"- {p.get('company_name')} ({p.get('ticker')}): CMP ₹{p.get('cmp')}, 1W: {p.get('return_1w'):+.2f}%, 1M: {p.get('return_1m'):+.2f}%, 30D Range: ₹{r30[0]}–₹{r30[1]}")
        context_blocks.append("\n".join(st_lines))

    # Optional Metals block
    if contract.include_metals and metals_context_str:
        context_blocks.append(f"[BULLION SPOT PRICES & 30-DAY TRENDS]\n{metals_context_str}")

    # Articles block
    if filtered_articles:
        art_lines = ["[VERIFIED NEWS ARTICLES]"]
        for idx, a in enumerate(filtered_articles, 1):
            art_lines.append(
                f"--- Article {idx} ---\n"
                f"Title: {a.get('title')}\n"
                f"Source: {a.get('source')} | Published: {a.get('published_at')}\n"
                f"Direction: {a.get('direction')} | Event Type: {a.get('event_type')}\n"
                f"Excerpt: {a.get('snippet')}\n"
            )
        context_blocks.append("\n".join(art_lines))

    must_answer_str = "\n".join(f"- {item}" for item in contract.must_answer) if contract.must_answer else f"- Answer: {parsed.question}"
    forbidden_str = "\n".join(f"- {item}" for item in contract.forbidden) if contract.forbidden else "- No buy/sell recommendations"
    context_str = "\n\n".join(context_blocks) if context_blocks else "(No specific news articles or auxiliary data blocks attached)"

    user_prompt = (
        f"USER QUESTION: {parsed.question}\n\n"
        f"ANSWER CONTRACT:\n"
        f"MUST ANSWER:\n{must_answer_str}\n\n"
        f"FORBIDDEN:\n{forbidden_str}\n\n"
        f"EVIDENCE CONTEXT:\n{context_str}\n\n"
        "Generate your response following the contract and format rules."
    )

    # 7. Generate Initial Draft via Writer LLM
    res = call_insight_llm(
        system_prompt=WRITER_SYSTEM_PROMPT,
        user_content=user_prompt,
        query_log=query_log,
    )
    raw_draft = res.raw_text

    # 8. Check Alignment via Agent 2
    alignment = check_answer_alignment(parsed.question, contract, raw_draft, query_log=query_log)
    final_raw = raw_draft
    insight_source = res.provider

    # 9. One Rewrite if not aligned
    if not alignment.aligned and (alignment.missing or alignment.extra):
        if query_log is not None:
            query_log.write(f"writer_rewrite_triggered missing={alignment.missing} extra={alignment.extra}")

        rewrite_prompt = (
            f"ORIGINAL QUESTION: {parsed.question}\n\n"
            f"MUST ANSWER:\n{must_answer_str}\n\n"
            f"FORBIDDEN:\n{forbidden_str}\n\n"
            f"EVIDENCE CONTEXT:\n{context_str}\n\n"
            f"PREVIOUS DRAFT:\n{raw_draft}\n\n"
            f"ALIGNMENT ISSUES DETECTED:\n"
            f"- Missing required coverage: {alignment.missing}\n"
            f"- Prohibited/extra content found: {alignment.extra}\n\n"
            "Please rewrite the answer fixing these issues completely."
        )

        res_rewrite = call_insight_llm(
            system_prompt=REWRITE_SYSTEM_PROMPT,
            user_content=rewrite_prompt,
            query_log=query_log,
        )
        final_raw = res_rewrite.raw_text
        insight_source = f"{res.provider}_rewritten"

    # 10. Parse Bullets & Summary
    bullets, summary = parse_structured_insight(final_raw)

    if not bullets and not summary:
        summary = final_raw.strip()

    # For pure list queries, drop redundant summaries that simply re-state the sectors or holdings
    if parsed.intent in ("fund_sectors", "fund_holdings") and bullets:
        if not summary or any(w in summary.lower() for w in ("consist", "consists", "led by", "followed by", "allocation", "reported", "available", "represent", "represents")):
            summary = ""

    max_bullets = requested_count if parsed.intent in ("fund_sectors", "fund_holdings") else settings.insight_max_bullets

    bullets = clamp_bullets(
        bullets,
        max_count=max_bullets,
        max_chars=settings.insight_bullet_max_chars,
    )
    if summary:
        summary = clamp_summary(summary, max_words=settings.insight_summary_max_words)
    display_insight = format_insight_display(bullets, summary)

    if query_log is not None:
        query_log.write(f"llm raw_preview text={clip_log_text(final_raw, 500)}")
        query_log.log_insight_output(
            insight_source=insight_source,
            char_count=len(display_insight),
            preview=display_insight,
        )
        query_log.note(
            "answer_done",
            intent=parsed.intent,
            sources=len(sources),
            aligned=alignment.aligned,
            writer_provider=insight_source,
        )

    return {
        "insight_bullets": bullets,
        "insight_summary": summary,
        "insight": display_insight,
        "sources": sources,
        "intent": parsed.intent,
        "insight_source": insight_source,
        "contract": {
            "must_answer": contract.must_answer,
            "forbidden": contract.forbidden,
            "use_articles_count": len(filtered_articles),
            "include_nav": contract.include_nav,
            "include_holdings": contract.include_holdings,
            "include_sectors": contract.include_sectors,
            "include_stock_price": contract.include_stock_price,
            "include_metals": contract.include_metals,
            "aligned": alignment.aligned,
        },
    }
