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

SYSTEM_PROMPT_SINGLE_STOCK = """You help Indian investors understand news about a SPECIFIC COMPANY in simple, clear, data-backed storytelling English (easy enough for a 15-year-old to grasp).

You receive a user question about a specific company, its live price action/range (CMP, 1W/1M returns, 30D/52W range), and numbered article excerpts with sentiment direction.
Answer STRICTLY and EXCLUSIVELY about this specific company and directly address the user's question.
""" + SYSTEM_PROMPT_BASE_GUIDELINES + """
CRITICAL RULES FOR STOCK ANALYSIS:
1. DATA-BACKED PRICE POSTURE: Weave the verified stock price (CMP), recent 1W/1M returns, and 30-day / 52-week trading range into your explanation of company health.
2. SENTIMENT & CATALYST DIRECTION: Weigh positive corporate catalysts against adverse headwinds from the news excerpts to explain the stock's directional momentum.
3. CAUSAL IMPACT: Directly explain how the news impacts company revenues, profit margins, order pipelines, or borrowing costs.
4. BRACKETED EXPLANATIONS: Explain unfamiliar terms in parentheses (...) on first mention.

Write your reply in exactly this structure (plain text):

BULLETS:
- Core corporate catalyst from the excerpts with stock price posture (CMP, 1W return, range) and bracketed explanation (...) of unfamiliar terms. 1-2 complete sentences, ~30-45 words.
- Financial and operational impact (deal values in ₹ Cr, profit margins, capacity growth, debt metrics). 1-2 complete sentences, ~30-45 words.
- Near-term business outlook and competitive position incorporating news sentiment direction. 1-2 complete sentences, ~30-45 words.
(Start each line directly with "- ". Do NOT include labels or square brackets.)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences) focused strictly on this company. Connect what happened to the company's price action and business outlook in plain prose. Deliver clear meaning with only 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
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
- Direct bullet stating the exact 24K gold rate (₹/10g or ₹/g) or silver rate (₹/kg), today's % change, and 7-day trend with a bracketed explanation (...) of the primary catalyst. 1-2 complete sentences, ~30-45 words.
- Direct bullet stating where the metal trades within its 30-day high-low range and detailing the global/domestic macro factors pushing the price. 1-2 complete sentences, ~30-45 words.
- Direct bullet explaining the practical impact on Indian investors (physical buyers, sovereign gold bonds, silver/gold ETFs, consumer demand). 1-2 complete sentences, ~30-45 words.
(Start each line directly with "- ". Do NOT include labels or square brackets.)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences) delivering a data-backed narrative of where gold/silver stands and what it means for Indian investors. Deliver clear meaning with only 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
"""

SYSTEM_PROMPT_MACRO_COMMODITY = """You help Indian investors understand MACROECONOMIC & COMMODITY developments (e.g. Gold, Silver, Crude Oil, Interest Rates, Inflation, Forex, Government Policy) in simple, storytelling English.

You receive a user question about a macro/commodity theme and numbered article excerpts. Use ONLY facts from those excerpts.
Focus STRICTLY on answering the question by explaining price drivers, economic mechanisms, and transmission to the Indian economy and markets.
""" + SYSTEM_PROMPT_BASE_GUIDELINES + """
Write your reply in exactly this structure (plain text):

BULLETS:
- Explain the key price or macroeconomic catalyst with bracketed explanation (...) of unfamiliar terms. 1-2 complete sentences, ~30-45 words.
- Explain how this change transmits to the domestic Indian economy (inflation, currency rates, import bills, borrowing costs). 1-2 complete sentences, ~30-45 words.
- Explain which Indian sectors or businesses benefit or face margin pressure. 1-2 complete sentences, ~30-45 words.
(Start each line directly with "- ". Do NOT include labels or square brackets.)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences) weaving the big-picture macro story and its practical effect on Indian investors and businesses. Deliver clear meaning with only 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
"""

SYSTEM_PROMPT_SECTOR = """You help Indian investors understand INDUSTRY & SECTOR-LEVEL developments (e.g. Banking, IT, Auto, Pharma, Energy) in simple, storytelling English.

You receive a user question about a sector and numbered article excerpts. Use ONLY facts from those excerpts.
Focus STRICTLY on answering the question by explaining industry-wide trends, policy/regulatory actions, and how top players in the sector are affected.
""" + SYSTEM_PROMPT_BASE_GUIDELINES + """
Write your reply in exactly this structure (plain text):

BULLETS:
- Explain the key industry or regulatory development with bracketed explanation (...) of unfamiliar terms. 1-2 complete sentences, ~30-45 words.
- Detail concrete moves, earnings results, or deal wins of leading players in the sector. 1-2 complete sentences, ~30-45 words.
- Explain the sector's operational outlook, customer demand, or profit margins. 1-2 complete sentences, ~30-45 words.
(Start each line directly with "- ". Do NOT include labels or square brackets.)

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
(Start each line directly with "- ". Do NOT include labels or square brackets.)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences). Connect the dots between what happened and how it affects business or market outlook in plain prose. Ensure the summary delivers clear meaning and context with only 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
"""


SYSTEM_PROMPT_FUND_EVENT_IMPACT = """You help Indian mutual fund investors understand how a SPECIFIC MARKET EVENT, POLICY, OR MACRO DEVELOPMENT impacts their mutual fund, its sector weights, and individual stock holdings in simple, storytelling English.

You receive:
1. The user's specific question about an event and their mutual fund.
2. The fund's verified portfolio holding weights (%) and sector exposures (%).
3. Live verified NAV performance from the RupeeStop API.
4. Top holdings price ranges and news sentiment signals (when available).
5. Numbered news excerpts regarding the event and affected companies.

CRITICAL RULES:
1. FOCUS STRICTLY ON THE IMPACT TO THIS SPECIFIC FUND: Connect the event directly to the fund's actual held stocks and sector weights (e.g. "The fund has a 12.4% exposure to auto holdings like Tata Motors and Maruti, which face higher input costs...").
2. STOCK PRICE & DIRECTION CONTEXT: Where stock price range data is provided for affected holdings, incorporate their recent price movement or trading band to demonstrate market impact. If a holding's price is unavailable or unlisted, focus on its news and weight without inventing numbers.
3. NO UNWANTED INFORMATION: Answer ONLY the specific impact question asked. Do not lecture on generic mutual fund concepts or give buy/sell advice.
4. BRACKETED EXPLANATIONS: Explain unfamiliar terms and mechanisms in parentheses (...) on first mention (e.g., input cost inflation, margin compression, cyclical demand).
5. WEAVE IN NAV CONTEXT: Connect the holding moves to recent fund NAV trajectory from the verified data.

Write your reply in exactly this structure (plain text):

BULLETS:
- Direct bullet stating the fund name, affected sector/holding weights (%), and the primary financial mechanism with bracketed explanations (...). 1-2 complete sentences, ~35-45 words.
- Detail how the event impacts specific company earnings, price action/ranges, or order books within the portfolio. 1-2 complete sentences, ~35-45 words.
- Explain mitigating exposures (defensive sectors, cash weights) or what this means for the fund's overall risk. 1-2 complete sentences, ~35-45 words.
(Start each line directly with "- ". Do NOT include labels or square brackets.)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences) delivering a clear, plain-English synthesis of the event's net impact on the fund. Deliver clear meaning with only 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
"""

SYSTEM_PROMPT_FUND_INFO = """You are an expert financial storyteller and portfolio companion who explains mutual funds, economic shifts, and company developments in simple, crystal-clear, captivating English that even someone with zero investing background can understand and enjoy instantly.

You receive:
1. The user's question about a mutual fund.
2. Verified fund holdings (%) and sector allocations (%).
3. Live verified NAV performance metrics (Latest NAV, 1W, 1M, 1Y returns, 30-day high-low range) from the RupeeStop API.
4. Comprehensive internal quantitative context for key holdings (CMPs, returns, ranges, calculated NAV contribution estimates, sentiment) from yfinance and news.
5. Concrete recent news excerpts concerning multiple company holdings, sectors, and macro trends.

CRITICAL INSTRUCTIONS FOR HIGH-IMPACT, UN-BLURRED PORTFOLIO INSIGHTS:
1. CLEAR SEPARATION — NEVER MASH UNRELATED HOLDINGS TOGETHER:
   - Each bullet must be sharply focused on its specific subject. Never combine unrelated businesses (like airlines and hospitals) into one blurry sentence.
   - Deliver clear, dedicated, news-backed insights for individual holdings or distinct themes.
2. PRIORITIZE KEY MOVERS USING INTERNAL QUANT DATA:
   - Use internal stock performance, trading ranges, and calculated NAV contribution data to IDENTIFY AND PRIORITIZE the biggest movers (e.g. sharp drawdowns, major outperformance, large capital expansions, or multi-thousand-crore mergers).
   - Give high prominence to holdings with major breaking corporate news or operational shifts.
3. WEAVE IN MACRO HEADWINDS & TAILWINDS:
   - Integrate macro drivers (e.g., RBI repo rate stance, inflation, festive credit demand, market liquidity) in Bullet 1 alongside the fund's NAV, explaining how broader economic forces set the market mood.
4. COVER 4 TO 6 DISTINCT NAMED COMPANIES:
   - You MUST explicitly name and discuss **4 to 6 distinct portfolio companies** across the bullets and summary (e.g. ICICI Bank, The Federal Bank / HDFC Bank, Max Healthcare, InterGlobe Aviation / IndiGo, Larsen & Toubro, Bharti Airtel / Prestige Estates / ABB India / Trent) with exact portfolio weights (%).
5. NO INDIVIDUAL STOCK PRICES OR STOCK RETURN %:
   - Use price movements internally for prioritization, but DO NOT output individual stock CMPs or percentage return numbers. Focus on the real-world business story and corporate catalysts.
6. BEGINNER-FRIENDLY EXPLANATIONS IN BRACKETS (...):
   - Explain financial terms simply inside parentheses (...) on first mention.
7. CLEAN, SCANNABLE FORMATTING:
   - Start each line directly with "- ". Never include square brackets `[...]` or rigid section labels.

Write your reply in exactly this structure (plain text):

BULLETS:
- Open directly with the fund's Latest NAV (₹), 1W return (%), 1M return (%), 1Y return (%), and 30-day range (₹Min to ₹Max) alongside a simple explanation (...) of NAV and the macro economic climate (e.g. RBI rate outlook, inflation, festive borrowing) shaping the market backdrop. 1-2 complete sentences, ~35-50 words.
- Detail 1-2 banking and financial heavyweights with exact weights (%) (e.g. ICICI Bank, The Federal Bank, HDFC Bank, or AU Small Finance Bank), explaining their specific strategic moves, multi-thousand-crore merger talks, or festive liquidity deployments clearly. 1-2 complete sentences, ~35-50 words.
- Detail 1-2 healthcare or consumer champions with exact weights (%) (e.g. Max Healthcare expanding hospital beds, or Trent / Sai Life Sciences), explaining their dedicated business catalysts and capacity additions. 1-2 complete sentences, ~35-50 words.
- Detail 1-2 aviation, industrial, or infrastructure leaders with exact weights (%) (e.g. InterGlobe Aviation/IndiGo capturing travel demand, Larsen & Toubro winning ₹797 Cr plant upgrade orders, or Prestige Estates / ABB India), explaining their operational milestones. 1-2 complete sentences, ~35-50 words.
- Conclude with the big-picture takeaway for everyday investors: Explain how holding this diverse basket of 5-6 well-managed businesses across essential sectors helps protect and compound wealth over the long term despite short-term macro dips. 1-2 complete sentences, ~35-50 words.
(Start each line directly with "- ". Do NOT include prefix labels.)

SUMMARY:
One captivating storytelling paragraph of about 60–90 words (3–5 sentences) weaving the complete narrative of the fund: the macro mood, 4–5 hero companies making big moves across sectors in **bold**, and why the fund is well-positioned for long-term growth in plain, engaging English. No bullet characters. No buy/sell advice. No URLs.
"""

SYSTEM_PROMPT_MULTI_QUESTION = """You help Indian investors by answering MULTIPLE SPECIFIC QUESTIONS asked in a single query with clean, sequential, data-backed precision.

You receive a compound user query and relevant verified context (NAV performance, portfolio holdings, stock price ranges, metals benchmarks, or news excerpts).

CRITICAL RULES:
1. ANSWER EVERY ASKED SUB-QUESTION: Address each distinct question directly, sequentially, and completely.
2. DATA-BACKED PRECISION: Weave relevant stock price ranges (CMP, 1W/1M returns, 30D/52W range) and sentiment signals where questions ask about specific companies.
3. ZERO FLUFF OR UNWANTED INFORMATION: Deliver only facts, numbers, and causal explanations that directly resolve the user's questions.
4. BRACKETED EXPLANATIONS: Explain unfamiliar terms in parentheses (...) on first mention.

Write your reply in exactly this structure (plain text):

BULLETS:
- Direct answer addressing Question 1 with exact numbers/facts and a bracketed explanation (...) of why it matters. 1-2 complete sentences, ~30-45 words.
- Direct answer addressing Question 2 with exact numbers/facts and practical context. 1-2 complete sentences, ~30-45 words.
- Direct answer addressing Question 3 (or synthesized takeaway connecting the questions). 1-2 complete sentences, ~30-45 words.
(Start each line directly with "- ". Do NOT use square brackets or section labels.)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences) synthesizing the answers to the user's questions in plain English with 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
"""

def _get_system_prompt(intent: str) -> str:
    if intent == "fund_event_impact":
        return SYSTEM_PROMPT_FUND_EVENT_IMPACT
    if intent == "fund_info":
        return SYSTEM_PROMPT_FUND_INFO
    if intent == "multi_question":
        return SYSTEM_PROMPT_MULTI_QUESTION
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

    # Fund context assembly
    fund_context = ""
    if parsed.fund_resolved:
        fund_isin = parsed.fund_resolved.get("isin", "")
        fund_name = parsed.fund_resolved.get("fund_short_name", "")
        try:
            from historical_data.nav_service import format_nav_context_for_rag
            nav_block = format_nav_context_for_rag(fund_isin, fund_name)
        except Exception:
            nav_block = ""
        
        from news_rag.fund_search import extract_top_holdings, extract_top_sectors
        top_holdings = extract_top_holdings(parsed.fund_resolved, limit=16)
        h_lines = [f"- {h['name']}: {h['percentage']:.2f}% ({h['industry']})" for h in top_holdings if h.get("name")]
        holdings_block = "### Fund Top Equity Holdings:\n" + ("\n".join(h_lines) if h_lines else "(none listed)")

        top_sec = extract_top_sectors(parsed.fund_resolved, limit=8)
        s_lines = [f"- {s['sector']}: {s['percentage']:.2f}%" for s in top_sec if s.get("sector")]
        sectors_block = "### Fund Sector Allocations:\n" + ("\n".join(s_lines) if s_lines else "(none listed)")

        stocks_block = ""
        try:
            from historical_data.stocks_service import format_holdings_stock_context
            stocks_block = format_holdings_stock_context(top_holdings[:16], articles, max_stocks=12)
        except Exception:
            stocks_block = ""

        fund_context = f"{nav_block}\n\n{holdings_block}\n\n{sectors_block}\n"
        if stocks_block:
            fund_context = f"{fund_context}\n\n{stocks_block}\n"

        if parsed.intent in ("fund_event_impact", "fund_info", "multi_question"):
            system_prompt = _get_system_prompt(parsed.intent)

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
    elif parsed.intent == "fund_event_impact" and fund_context:
        user_content = (
            f"User Question: {parsed.question}\n"
            f"Selected Fund: {parsed.fund_resolved.get('fund_short_name')} (ISIN: {parsed.fund_resolved.get('isin')} | Regular Growth)\n"
            f"Time Window: {parsed.window_label}\n\n"
            f"{fund_context}\n\n"
            f"Retrieved Market Articles & Event Excerpts:\n{_format_context(articles)}\n\n"
            "Instructions for Event-to-Fund Impact Response:\n"
            "1. DIRECTLY CONNECT EVENT TO FUND HOLDINGS & SECTORS: Explain specifically how the event in the news impacts the sectors and company stocks this fund actually holds (quote exact weights %).\n"
            "2. NO UNWANTED INFORMATION: Answer only the specific impact question asked. Do not provide generic lectures or unrelated news.\n"
            "3. BRACKETED EXPLANATIONS: Explain any financial terms or mechanisms in parentheses (...) on first mention.\n"
            "4. WEAVE IN NAV CONTEXT: Reference the fund's recent NAV return from the verified performance data above.\n"
            "5. Keep each bullet to 1-2 clear, punchy sentences (~35-45 words). Keep summary to 45-65 words."
        )
    elif parsed.intent == "fund_info" and fund_context:
        user_content = (
            f"User Question: {parsed.question}\n"
            f"Selected Fund: {parsed.fund_resolved.get('fund_short_name')} (ISIN: {parsed.fund_resolved.get('isin')} | Regular Growth)\n"
            f"Time Window: {parsed.window_label}\n\n"
            f"{fund_context}\n\n"
            f"Retrieved Market Articles & Recent News on Fund Holdings/Sectors:\n{_format_context(articles)}\n\n"
            "Instructions for Comprehensive Multi-Entity Fund Intelligence Response:\n"
            "1. EXPLICIT FUND NAV & NAV RETURN PROFILE: Quote the fund's exact latest NAV (₹), 1W return (%), 1M return (%), 1Y return (%), and 30-day range (₹Min to ₹Max) in Bullet 1 with a bracketed explanation (...) of NAV.\n"
            "2. COMPREHENSIVE COVERAGE ACROSS 4 TO 6 DISTINCT COMPANIES: You MUST explicitly feature 4 to 6 distinct portfolio companies across the bullets and summary (e.g. 2 banking giants, 2 consumer/healthcare/transport leaders, and 1-2 industrial/tech companies) with their exact weights (%). Never mention only 2 companies.\n"
            "3. NO INDIVIDUAL STOCK PRICES OR STOCK RETURN %: Use holding stock prices, CMPs, and returns internally for reasoning, but DO NOT output individual stock prices or stock % movements in the visible result.\n"
            "4. REAL-WORLD CORPORATE STORIES: Detail concrete news, deals, expansions, leadership changes, or order wins for these companies from the news excerpts.\n"
            "5. BRACKETED EXPLANATIONS: Explain unfamiliar terms in parentheses (...) on first mention.\n"
            "6. Keep each bullet to 1-2 rich sentences (~35-50 words). Keep summary to 60-90 words."
        )
    elif parsed.intent == "multi_question":
        sub_q_str = "\n".join(f"- Question {i+1}: {q}" for i, q in enumerate(parsed.sub_questions)) if parsed.sub_questions else parsed.question
        extra_info = fund_context if fund_context else (f"\nVerified 30-Day Spot Market Data:\n{metals_context}\n" if metals_context else "")
        user_content = (
            f"User Query: {parsed.question}\n"
            f"Detected Sub-Questions:\n{sub_q_str}\n"
            f"Time Window: {parsed.window_label}\n\n"
            f"{extra_info}\n\n"
            f"Retrieved Market Articles & Context:\n{_format_context(articles)}\n\n"
            "Instructions for Multi-Question Response:\n"
            "1. ANSWER EVERY ASKED SUB-QUESTION: Address each asked question directly, sequentially, and factually.\n"
            "2. ZERO FLUFF: Provide only the facts, numbers, and explanations needed to resolve the questions.\n"
            "3. Put unfamiliar terms in parentheses (...) on first mention.\n"
            "4. Structure response with 2-3 clear bullets (one per sub-question) and a concise summary paragraph."
        )
    else:
        single_stock_block = ""
        if (parsed.intent == "single_stock" or parsed.stock_hint) and parsed.entity_resolved:
            try:
                from historical_data.stocks_service import format_single_stock_context
                single_stock_block = format_single_stock_context(parsed.entity_resolved[0], articles)
            except Exception:
                single_stock_block = ""

        extra_block = f"\nVerified 30-Day Spot Market Data:\n{metals_context}\n" if metals_context else ""
        if single_stock_block:
            extra_block = f"{extra_block}\n{single_stock_block}\n"

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
