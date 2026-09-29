"""LLM — structured insight (bullets + summary) from retrieved articles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.insight_format import (
    clamp_bullets,
    clamp_summary,
    format_insight_display,
    parse_structured_insight,
)
from news_rag.insights import build_structured_insight_from_articles
from news_rag.llm_client import call_insight_llm, llm_api_key_configured, missing_llm_key_message
from news_rag.parse import ParsedQuery
from news_rag.query_log import clip_log_text

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

SYSTEM_PROMPT_BASE_GUIDELINES = """
CORE GUIDELINES:

1. DIRECTLY ANSWER WHAT THE USER ASKED:
   - Answer the specific query directly and objectively using facts from the excerpts.
   - If the user asks "why" something happened or asks for "impact", lead directly with the cause-and-effect chain and tangible financial/business consequences.
   - Do NOT wander off-topic, recite generic market summaries, or answer unrelated questions.

2. WHEN RETRIEVED EXCERPTS LACK SPECIFIC NEWS OR THE QUERY IS A GENERAL CONCEPT:
   - NEVER output robotic bullets repeating "The provided excerpts do not contain information...".
   - If the user is asking to understand or define a financial term or business concept, provide a direct, simple explanation in the SUMMARY paragraph and OMIT the BULLETS section completely.
   - If the user asked for recent news about a specific company or event not present in the news store, provide a polite, simple 1-2 sentence explanation in the SUMMARY stating that no recent news was found in the verified store, without generating artificial bullet points.

3. PRACTICAL MEANING & REAL-WORLD BUSINESS IMPACT:
   - Do NOT just report dry headlines or isolated numbers. Every point MUST explain the practical real-world meaning:
     What happened -> What it means for company revenues, profit margins, borrowing costs, or business growth -> Why it matters for investors.

4. EXPLAIN UNFAMILIAR EVENTS & TERMS IN BRACKETS (...):
   - Whenever you mention a specific corporate action, financial metric, regulatory rule, or macroeconomic event that an ordinary person wouldn't immediately understand, immediately explain it simply inside parentheses (...).
   - Examples:
     * "10-year G-sec yield (the benchmark interest rate the government pays to borrow money)"
     * "Repo Rate hike (the central bank raising interest rates, which makes loans more expensive to cool inflation)"
     * "Brent crude rising to $107 (oil prices jumping, which increases fuel and transport costs for companies across India)"
     * "Captive power plant (a company-owned solar/wind unit that produces cheaper electricity for its own factories)"
     * "Core investment company (a holding company that owns shares in group entities rather than running direct operations)"
     * "Credit-deposit ratio (the proportion of customer deposits a bank has lent out as loans)"
     * "NIM / net interest margin (the profit margin a bank makes on loans after paying interest on deposits)"
     * "FII outflows (foreign institutional investors pulling money out of Indian stock markets)"
     * "EBITDA margin (the core operational profit percentage a company earns before taxes and accounting deductions)"
     * "CEO succession (the formal process of choosing the next top boss to lead the company)"
     * "Promoter pledge (founders using their company shares as collateral to borrow loans)"
     * "QoQ / Quarter-on-Quarter (comparing performance against the previous 3 months)"
     * "YoY / Year-on-Year (comparing performance against the same period last year)"

5. SIMPLE, JARGON-FREE LANGUAGE (FOR BEGINNERS & NON-FINANCE INVESTORS):
   - Use plain, conversational English that anyone with zero financial education can easily understand.
   - Replace heavy jargon with everyday words (e.g. say "making more profit on each loan" instead of "NIM expansion"; say "raw materials getting costlier" instead of "gross margin contraction via input cost inflation").

6. SHOW INTERCONNECTIVITY & CAUSAL CHAINS:
   - Explicitly show the cause-and-effect relationship (e.g., how higher global crude oil prices increase fuel and raw material input costs for paint and tyre makers, putting pressure on quarterly profit margins).

7. STRICT MINIMAL HIGHLIGHTING (DO NOT OVER-HIGHLIGHT):
   - Highlight ONLY 1 or 2 most critical anchor terms per bullet (e.g. primary company name or key metric like **₹5,000 Cr** or **+12%** or **$85/barrel**).
   - Keep the summary to at most 2 or 3 total bold highlights across the entire paragraph.
   - DO NOT bold common verbs, adjectives, regulatory bodies, acronym expansions, or the bracketed explanations.

8. REJECT TRIVIA & UNWANTED NOISE:
   - Exclude routine operational announcements, bank holiday notices, minor administrative changes, or generic price recaps without a business trigger.

9. NO BUY/SELL ADVICE:
   - Provide objective factual context and implications only.
"""

SYSTEM_PROMPT_CONCEPT = """You are a helpful, friendly financial guide explaining business, market, and investing concepts to beginners in very simple, plain English (easy enough for a 15-year-old to understand).

Explain the concept directly, intuitively, and concisely in ONE short, engaging paragraph (40–60 words).
- Do NOT generate any bullet points.
- Do NOT say "The provided text excerpts do not contain...".
- Use simple real-world Indian business examples (e.g. mentioning Tata Group or Reliance if explaining a conglomerate) to make the concept immediately clear and relatable.
- Deliver clear meaning with only 1 or 2 selective **bold** highlights.

OUTPUT FORMAT (PLAIN TEXT):

SUMMARY:
[Your clear, simple explanation in ONE concise paragraph. No bullet points.]
"""

SYSTEM_PROMPT_SINGLE_STOCK = """You help Indian investors understand news about a SPECIFIC COMPANY in simple, clear, storytelling English (easy enough for a 15-year-old to grasp).

You receive a user question about a specific company and numbered article excerpts. Use ONLY facts from those excerpts.
Answer STRICTLY and EXCLUSIVELY about this specific company and directly address the user's question.
""" + SYSTEM_PROMPT_BASE_GUIDELINES + """
Write your reply in exactly this structure (plain text):

BULLETS:
- [Clear bullet line starting immediately with the catalyst/event from excerpts, with bracketed explanation (...) of unfamiliar terms. 1-2 complete sentences, ~30-45 words.]
- [Clear bullet line explaining the financial and operational impact (numbers, ₹ Cr, profit margins, revenue growth, debt). 1-2 complete sentences, ~30-45 words.]
- [Clear bullet line explaining the company's competitive position or near-term outlook. 1-2 complete sentences, ~30-45 words.]
(Do NOT include label prefixes like "Bullet 1:" or "(Core Catalyst):". Start each line directly with "- ".)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences) focused strictly on this company. Connect what happened to the company's business outlook in plain prose. Deliver clear meaning with only 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
"""

SYSTEM_PROMPT_BULLION = """You help Indian investors understand GOLD (strictly 24-Karat pure gold) and SILVER prices, trends, and market drivers in simple, data-backed, storytelling English.

You receive a user question about Gold, Silver, or Bullion markets along with verified 30-day official benchmark data (IBJA daily rates) and relevant market news excerpts.
Answer the question directly, weaving the exact verified spot numbers, price changes, and 30-day range into your response.

CRITICAL RULES FOR GOLD/SILVER ANSWERS:
1. STRICT 24K GOLD BENCHMARK: For all gold figures and discussions, use EXCLUSIVELY 24-Karat pure gold (999 purity / XAU.24K.INR) in ₹/10 grams or ₹/gram. Do NOT mention 22K or 18K gold.
2. SILVER BENCHMARK: Use Silver (XAG.INR.KG) in ₹/kilogram or ₹/gram.
3. DATA-BACKED ANCHORS: Directly quote the latest official rate, 1-day % change, 7-day trend, and where the price stands within its 30-day range (e.g., near monthly low/high).
4. EXPLAIN WHY: Connect price moves to concrete catalysts (US dollar strength/weakness, geopolitical tensions, domestic festive/wedding demand, inflation hedging, interest rate outlook).
5. BRACKETED EXPLANATIONS: Explain unfamiliar concepts in parentheses (...) on first mention (e.g., profit booking, hedge, safe-haven asset, spot price).

Write your reply in exactly this structure (plain text):

BULLETS:
- [Spot Price & Recent Momentum: Direct bullet stating the exact 24K gold rate (₹/10g or ₹/g) or silver rate (₹/kg), today's % change, and 7-day trend with a bracketed explanation (...) of the primary catalyst. 1-2 complete sentences, ~30-45 words.]
- [30-Day Context & Core Macro Drivers: Direct bullet stating where the metal trades within its 30-day high-low range and detailing the global/domestic macro factors pushing the price. 1-2 complete sentences, ~30-45 words.]
- [Investor & Economic Takeaway: Direct bullet explaining the practical impact on Indian investors (physical buyers, sovereign gold bonds, silver/gold ETFs, consumer demand). 1-2 complete sentences, ~30-45 words.]
(Do NOT include label prefixes like "Bullet 1:". Start each line directly with "- ".)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences) delivering a data-backed narrative of where gold/silver stands and what it means for Indian investors. Deliver clear meaning with only 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
"""

SYSTEM_PROMPT_MACRO_COMMODITY = """You help Indian investors understand MACROECONOMIC & COMMODITY developments (e.g. Gold, Silver, Crude Oil, Interest Rates, Inflation, Forex, Government Policy) in simple, storytelling English.

You receive a user question about a macro/commodity theme and numbered article excerpts. Use ONLY facts from those excerpts.
Focus STRICTLY on answering the question by explaining price drivers, economic mechanisms, and transmission to the Indian economy and markets.
""" + SYSTEM_PROMPT_BASE_GUIDELINES + """
Write your reply in exactly this structure (plain text):

BULLETS:
- [Clear bullet line explaining the key price/macro catalyst with bracketed explanation (...) of unfamiliar terms. 1-2 complete sentences, ~30-45 words.]
- [Clear bullet line explaining how this change transmits to the domestic Indian economy (inflation, currency rates, import bills, borrowing costs). 1-2 complete sentences, ~30-45 words.]
- [Clear bullet line explaining which Indian sectors or businesses benefit or face margin pressure. 1-2 complete sentences, ~30-45 words.]
(Do NOT include label prefixes like "Bullet 1:" or "(Macro Drivers):". Start each line directly with "- ".)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences) weaving the big-picture macro story and its practical effect on Indian investors and businesses. Deliver clear meaning with only 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
"""

SYSTEM_PROMPT_SECTOR = """You help Indian investors understand INDUSTRY & SECTOR-LEVEL developments (e.g. Banking, IT, Auto, Pharma, Energy) in simple, storytelling English.

You receive a user question about a sector and numbered article excerpts. Use ONLY facts from those excerpts.
Focus STRICTLY on answering the question by explaining industry-wide trends, policy/regulatory actions, and how top players in the sector are affected.
""" + SYSTEM_PROMPT_BASE_GUIDELINES + """
Write your reply in exactly this structure (plain text):

BULLETS:
- [Clear bullet line explaining the key industry/policy development with bracketed explanation (...) of unfamiliar terms. 1-2 complete sentences, ~30-45 words.]
- [Clear bullet line explaining concrete moves, earnings results, or deal wins of leading players in the sector. 1-2 complete sentences, ~30-45 words.]
- [Clear bullet line explaining the sector's operational outlook, customer demand, or profit margins. 1-2 complete sentences, ~30-45 words.]
(Do NOT include label prefixes like "Bullet 1:". Start each line directly with "- ".)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences) explaining the overall sector trajectory and business environment. Deliver clear meaning with only 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
"""

SYSTEM_PROMPT_GENERAL = """You help Indian investors understand recent Indian market news in very simple, clear, storytelling English (easy enough for a 15-year-old to grasp).

You receive a user question and numbered article excerpts. Use ONLY facts from those excerpts.
Directly answer what the user asked by connecting what happened to real economic and business impact.
""" + SYSTEM_PROMPT_BASE_GUIDELINES + """
Write your reply in exactly this structure (plain text):

BULLETS:
- Exactly 2 or 3 bullet lines (no more). Each line starts with "- ".
- Exactly ONE bullet per distinct company, sector, or market theme (no duplicate bullets for the same entity).
- Each bullet is 1-2 complete sentences (~30-45 words): concrete facts from the excerpt (who did what, key numbers) PLUS a brief simple explanation of why it matters, including bracketed explanations (...) of unfamiliar terms.
- Use **bold** sparingly for only the 1-2 most critical anchor terms.
(Do NOT include label prefixes like "Bullet 1:". Start each line directly with "- ".)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences). Connect the dots between what happened and how it affects business or market outlook in plain prose. Ensure the summary delivers clear meaning and context with only 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
"""


def _get_system_prompt(intent: str) -> str:
    if intent == "bullion":
        return SYSTEM_PROMPT_BULLION
    if intent == "concept":
        return SYSTEM_PROMPT_CONCEPT
    if intent == "single_stock":
        return SYSTEM_PROMPT_SINGLE_STOCK
    if intent == "macro_commodity":
        return SYSTEM_PROMPT_MACRO_COMMODITY
    if intent == "sector":
        return SYSTEM_PROMPT_SECTOR
    return SYSTEM_PROMPT_GENERAL


def _format_context(articles: list[dict]) -> str:
    blocks = []
    for index, row in enumerate(articles, start=1):
        blocks.append(
            f"[{index}] title={row.get('title')!r}\n"
            f"    source={row.get('source')} published={row.get('published_at')}\n"
            f"    direction={row.get('direction')} event={row.get('event_type')} "
            f"entities={row.get('entity_names')}\n"
            f"    text={row.get('snippet')!r}"
        )
    return "\n\n".join(blocks)


def _insight_payload(
    bullets: list[str],
    summary: str,
    *,
    insight_source: str,
    parsed: ParsedQuery,
    sources: list[dict],
) -> dict:
    display = format_insight_display(bullets, summary)
    return {
        "answer": display,
        "insight": display,
        "insight_bullets": bullets,
        "insight_summary": summary,
        "insight_source": insight_source,
        "sources": sources,
        "window": parsed.window_label,
        "entities": parsed.entity_resolved,
        "entity_match_note": parsed.entity_match_note,
    }


def empty_answer(parsed: ParsedQuery) -> dict:
    window = parsed.window_label
    entity_bit = ""
    if parsed.entity_match_note == "not_in_corpus" and parsed.stock_hint:
        entity_bit = f" We could not match “{parsed.stock_hint}” to a name in the news store."
    text = (
        f"No matching news was found for {window}.{entity_bit} "
        "Try a wider date range or a different company name."
    )
    return {
        "answer": text,
        "insight": text,
        "insight_bullets": [],
        "insight_summary": text,
        "sources": [],
        "window": parsed.window_label,
        "entities": parsed.entity_resolved,
        "entity_match_note": parsed.entity_match_note,
        "insight_source": "no_articles",
    }


def generate_answer(
    parsed: ParsedQuery,
    articles: list[dict],
    *,
    query_log: QueryLogger | None = None,
) -> dict:
    if not articles:
        return empty_answer(parsed)

    settings = get_settings()
    if not llm_api_key_configured(settings):
        raise RuntimeError(missing_llm_key_message())

    system_prompt = _get_system_prompt(parsed.intent)

    metals_context = ""
    q_lower = parsed.question.lower()
    is_bullion_query = (
        parsed.intent == "bullion"
        or any(m in q_lower for m in ["gold", "silver", "bullion", "xau", "xag", "yellow metal", "white metal", "sgb", "ibja"])
        or any("gold" in str(e).lower() or "silver" in str(e).lower() for e in parsed.entity_resolved)
    )
    if is_bullion_query:
        try:
            from historical_data.metals_service import format_metals_context_for_llm
            metals_context = format_metals_context_for_llm()
            system_prompt = _get_system_prompt("bullion")
        except Exception:
            metals_context = ""

    if parsed.intent == "concept":
        user_content = (
            f"User Question: {parsed.question}\n\n"
            "Instructions:\n"
            "Explain this business/investing concept simply and clearly in ONE short, beginner-friendly paragraph (~40-60 words).\n"
            "Do NOT output any bullet points. Give a relatable real-world Indian example if helpful."
        )
    elif is_bullion_query and metals_context:
        user_content = (
            f"User Question: {parsed.question}\n"
            f"Time Window: {parsed.window_label}\n"
            f"{metals_context}\n\n"
            f"Retrieved Market Articles & News Excerpts:\n{_format_context(articles)}\n\n"
            "Instructions for Data-Backed Bullion Response:\n"
            "1. STRICT 24K GOLD RULE: When answering about gold, reference and quote ONLY 24-Karat pure gold (₹/10g or ₹/g) from the official benchmark data above. Do NOT mention 22K or 18K gold.\n"
            "2. DATA-BACKED ANCHORS: Weave the exact latest 24K gold rate (₹/10g or ₹/g) or silver rate (₹/kg), 1-day change %, 7-day trend %, and where the price sits in the 30-day range directly into the bullets and summary.\n"
            "3. EXPLAIN THE WHY & IMPACT: Explain the economic catalysts behind the movement (dollar index, interest rate expectations, inflation, safe haven demand, festive buying) and practical takeaways for Indian investors.\n"
            "4. Put unfamiliar financial terms in parentheses (...) on first mention.\n"
            "5. Keep each bullet to 1-2 clear, punchy sentences (~30-45 words). Keep summary to 45-65 words."
        )
    else:
        extra_block = f"\nVerified 30-Day Spot Market Data:\n{metals_context}\n" if metals_context else ""
        user_content = (
            f"User Question: {parsed.question}\n"
            f"Detected Intent: {parsed.intent}\n"
            f"Time Window: {parsed.window_label}\n"
            f"Resolved Entities: {', '.join(parsed.entity_resolved) or '(broad search)'}\n"
            f"{extra_block}\n"
            f"Retrieved Articles:\n{_format_context(articles)}\n\n"
            "Instructions for Response:\n"
            "1. Directly answer the user's specific question using facts from the excerpts above.\n"
            "2. If the user asks 'why' or asks for 'impact', focus directly on causal factors and tangible business effects (margins, profits, costs, debt, order book).\n"
            "3. If the excerpts do NOT contain relevant information for this question or if the question is a concept definition, do NOT generate dummy bullets saying 'excerpts do not contain info'. Instead, omit the BULLETS section and provide a single simple explanation in the SUMMARY paragraph.\n"
            "4. Explain every unfamiliar financial term, metric, or corporate action in parentheses (...) on first mention.\n"
            "5. Keep each bullet to 1-2 clear, punchy sentences (~30-45 words). Do not rewrite headline titles.\n"
            "6. Keep the summary paragraph to 45-65 words in plain, engaging English.\n"
            "7. Do not include unwanted trivia or unrelated stories."
        )

    llm_result = call_insight_llm(
        system_prompt=system_prompt,
        user_content=user_content,
        query_log=query_log,
    )
    if query_log is not None:
        query_log.record_llm_call(
            provider=llm_result.provider,
            model=llm_result.model,
            input_tokens=llm_result.input_tokens,
            output_tokens=llm_result.output_tokens,
            total_tokens=llm_result.total_tokens,
            duration_sec=llm_result.duration_sec,
            http_status=llm_result.http_status,
        )
        query_log.write(
            f"llm raw_preview provider={llm_result.provider} "
            f"text={clip_log_text(llm_result.raw_text, 500)}"
        )

    raw = llm_result.raw_text
    bullets, summary = parse_structured_insight(raw)
    insight_source = llm_result.provider

    if not bullets and not summary:
        bullets, summary = build_structured_insight_from_articles(parsed, articles)
        insight_source = "articles_fallback"
        if query_log is not None:
            query_log.write("insight llm_empty=true reason=empty_llm_content")
    elif not summary and bullets:
        summary = "These are the main themes from recent news in your store for this question."

    bullets = clamp_bullets(
        bullets,
        max_count=settings.insight_max_bullets,
        max_chars=settings.insight_bullet_max_chars,
    )
    summary = clamp_summary(summary, max_words=settings.insight_summary_max_words)

    sources = [
        {
            "title": row.get("title"),
            "url": row.get("url"),
            "source": row.get("source"),
            "published_at": row.get("published_at"),
        }
        for row in articles
    ]

    display = format_insight_display(bullets, summary)
    if query_log is not None:
        query_log.log_insight_output(
            insight_source=insight_source,
            char_count=len(display),
            preview=display,
        )
        query_log.write(f"insight_bullets_count={len(bullets)} summary_words={len(summary.split())}")

    return _insight_payload(
        bullets,
        summary,
        insight_source=insight_source,
        parsed=parsed,
        sources=sources,
    )
