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

7. HIGHLIGHT KEY WORDS & ANCHOR TERMS IN BULLETS & SUMMARY:
   - In each bullet point, ALWAYS bold the primary **Company Names**, **Key Numbers / Percentages**, and **Core Strategic Actions** (e.g. **ICICI Bank Limited (7.50% weight)**, **₹105.88**, **+6.44%**, **share-swap merger**, **₹797 Cr**).
   - In the summary, highlight 3 to 5 hero anchor names and key catalysts in **bold**.
   - DO NOT bold common filler words, prepositions, or parenthetical explanations.

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
- Deliver clear meaning with 2 or 3 selective **bold** highlights.

OUTPUT FORMAT (PLAIN TEXT):

SUMMARY:
[Your clear, simple explanation in ONE concise paragraph. No bullet points.]
"""

SYSTEM_PROMPT_SINGLE_STOCK = """You help Indian investors understand news about a SPECIFIC COMPANY in simple, clear, data-backed storytelling English (easy enough for a 15-year-old to grasp).

You receive a user question about a specific company, its live price action/range (CMP, 1W/1M returns, 30D/52W range), and numbered article excerpts with sentiment direction.
Answer STRICTLY and EXCLUSIVELY about this specific company and directly address the user's question.
""" + SYSTEM_PROMPT_BASE_GUIDELINES + """
CRITICAL RULES FOR STOCK ANALYSIS:
1. DATA-BACKED PRICE POSTURE: Weave the verified stock price (**CMP**), recent **1W/1M returns**, and **30-day / 52-week trading range** into your explanation of company health.
2. SENTIMENT & CATALYST DIRECTION: Weigh positive corporate catalysts against adverse headwinds from the news excerpts to explain the stock's directional momentum.
3. CAUSAL IMPACT: Directly explain how the news impacts company revenues, profit margins, order pipelines, or borrowing costs.
4. BRACKETED EXPLANATIONS: Explain unfamiliar terms in parentheses (...) on first mention.
5. HIGHLIGHT KEY WORDS: Highlight key metrics, company names, and strategic actions in **bold** in every bullet.

Write your reply in exactly this structure (plain text):

BULLETS:
- Core corporate catalyst from the excerpts with stock price posture (**CMP**, **1W return**, **range**) and bracketed explanation (...) of unfamiliar terms. 1-2 complete sentences, ~30-45 words.
- Financial and operational impact (**deal values in ₹ Cr**, **profit margins**, **capacity growth**, **debt metrics**). 1-2 complete sentences, ~30-45 words.
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
6. HIGHLIGHT KEY WORDS: Highlight key metal rates (**₹/10g**, **₹/kg**), **percentages**, and **primary catalysts** in **bold** in every bullet.

Write your reply in exactly this structure (plain text):

BULLETS:
- Direct bullet stating the exact **24K gold rate (₹/10g or ₹/g)** or **silver rate (₹/kg)**, **today's % change**, and **7-day trend** with a bracketed explanation (...) of the primary catalyst. 1-2 complete sentences, ~30-45 words.
- Direct bullet stating where the metal trades within its **30-day high-low range** and detailing the **global/domestic macro factors** pushing the price. 1-2 complete sentences, ~30-45 words.
- Direct bullet explaining the practical impact on **Indian investors** (physical buyers, sovereign gold bonds, silver/gold ETFs, consumer demand). 1-2 complete sentences, ~30-45 words.
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
- Explain the key **price or macroeconomic catalyst** with bracketed explanation (...) of unfamiliar terms. 1-2 complete sentences, ~30-45 words.
- Explain how this change transmits to the **domestic Indian economy** (inflation, currency rates, import bills, borrowing costs). 1-2 complete sentences, ~30-45 words.
- Explain which **Indian sectors or businesses** benefit or face margin pressure. 1-2 complete sentences, ~30-45 words.
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
- Explain the key **industry or regulatory development** with bracketed explanation (...) of unfamiliar terms. 1-2 complete sentences, ~30-45 words.
- Detail concrete moves, **earnings results**, or **deal wins** of leading players in the sector. 1-2 complete sentences, ~30-45 words.
- Explain the sector's **operational outlook**, **customer demand**, or **profit margins**. 1-2 complete sentences, ~30-45 words.
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
- Highlight the primary **Company Names**, **Key Numbers**, and **Strategic Moves** in **bold** in each bullet.
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
1. FOCUS STRICTLY ON THE IMPACT TO THIS SPECIFIC FUND: Connect the event directly to the fund's actual held stocks and sector weights (e.g. "The fund has a **12.4% exposure** to auto holdings like **Tata Motors** and **Maruti**, which face higher input costs...").
2. STOCK PRICE & DIRECTION CONTEXT: Where stock price range data is provided for affected holdings, incorporate their recent price movement or trading band to demonstrate market impact. If a holding's price is unavailable or unlisted, focus on its news and weight without inventing numbers.
3. NO UNWANTED INFORMATION: Answer ONLY the specific impact question asked. Do not lecture on generic mutual fund concepts or give buy/sell advice.
4. BRACKETED EXPLANATIONS: Explain unfamiliar terms and mechanisms in parentheses (...) on first mention (e.g., input cost inflation, margin compression, cyclical demand).
5. WEAVE IN NAV CONTEXT: Connect the holding moves to recent fund NAV trajectory from the verified data.
6. HIGHLIGHT KEY WORDS: Highlight company names, weights (%), and financial mechanisms in **bold** in every bullet.

Write your reply in exactly this structure (plain text):

BULLETS:
- Direct bullet stating the fund name, affected **sector/holding weights (%)**, and the **primary financial mechanism** with bracketed explanations (...). 1-2 complete sentences, ~35-45 words.
- Detail how the event impacts specific **company earnings**, **price action/ranges**, or **order books** within the portfolio. 1-2 complete sentences, ~35-45 words.
- Explain **mitigating exposures** (defensive sectors, cash weights) or what this means for the fund's overall risk. 1-2 complete sentences, ~35-45 words.
(Start each line directly with "- ". Do NOT include labels or square brackets.)

SUMMARY:
One short, engaging storytelling paragraph of about 45–65 words (2–4 sentences) delivering a clear, plain-English synthesis of the event's net impact on the fund. Deliver clear meaning with only 2–3 selective **bold** highlights. No bullet characters. No buy/sell advice. No URLs.
"""

SYSTEM_PROMPT_ANALYST_EXTRACTOR = """You are a senior quantitative portfolio analyst preparing an internal intelligence briefing for the Chief Investment Strategist.

Your task is to analyze the provided mutual fund data:
1. Fund Category & AMFI Benchmark
2. Live NAV Performance Metrics (Latest NAV, 1W/1M/1Y returns, 30-day range)
3. Top Portfolio Holdings (%) and Sector Allocations (%)
4. Quantitative Stock Performance (CMPs, 1W/1M returns, 30D ranges, calculated NAV contribution estimates)
5. 25-30 Recent Corporate & Macro News Articles

Synthesize this data into a structured PORTFOLIO CATALYST BRIEFING:
- KEY OUTPERFORMERS & POSITIVE CATALYSTS: Identify 2-3 portfolio companies whose corporate actions, earnings, or price action contributed positively to the fund. Quote specific corporate facts (e.g. hospital bed expansions, multi-thousand-crore order wins, festive consumption, loan growth).
- KEY UNDERPERFORMERS & RESILIENCE DRIVERS: Identify 1-2 companies navigating sector headwinds or valuation corrections, explaining the specific catalyst (e.g. merger transitions, regulatory adjustments, credit-deposit ratios).
- STRATEGIC DEALS, EXPANSIONS & LEADERSHIP ACTIONS: Highlight concrete corporate actions (e.g. Federal Bank share-swap merger talks with Jana SFB, L&T ₹797 Cr plant upgrade order, Max Healthcare institutional capacity expansion, IndiGo travel demand).
- SECTOR & MACRO REGIMES: Summarize how macro conditions (RBI repo rate outlook, inflation, systemic liquidity) and sector regulations affect the fund's top sectors (Banking, Healthcare, Retail, Industrials, IT).

Be factual, objective, and precise. Extract concrete corporate facts without generic filler.
"""

SYSTEM_PROMPT_FUND_INFO = """You are an expert financial storyteller and chief portfolio strategist who explains mutual funds, economic shifts, and company developments in simple, crystal-clear, captivating English that even someone with zero investing background can understand and enjoy instantly.

You receive:
1. Mutual fund details (Name, Category, AMFI Benchmark).
2. Live verified NAV metrics (Latest NAV, 1W %, 1M %, 1Y %, 30-day range) from the RupeeStop API.
3. Fund holdings (%) and sector allocations (%).
4. Structured Portfolio Catalyst Briefing prepared by your senior research analyst covering corporate deals, capacity additions, top movers, and macro regimes across 5-6 companies.

CRITICAL INSTRUCTIONS FOR HIGH-IMPACT, UN-BLURRED PORTFOLIO INSIGHTS:
1. HIGHLIGHT KEY WORDS IN BULLETS & SUMMARY:
   - In every bullet point, ALWAYS bold the primary **Company Names**, **Weights (%)**, **Key NAV Numbers/Returns**, and **Core Strategic Actions/Deals** (e.g. **ICICI Bank Limited (7.50% weight)**, **₹105.88**, **share-swap merger**, **hospital bed capacity**).
   - In the summary paragraph, highlight 4-5 hero companies and primary economic catalysts in **bold**.
2. CLEAR SEPARATION — NEVER MASH UNRELATED HOLDINGS TOGETHER:
   - Each bullet must be sharply focused on its specific subject. Never combine unrelated businesses (like airlines and hospitals) into one blurry sentence.
   - Dedicate distinct bullets to distinct sectors and company champions.
3. WEAVE IN MACRO BACKDROP & CATEGORY/BENCHMARK IN BULLET 1:
   - In Bullet 1, state the fund's Latest NAV (**₹...**), 1W return (**...%**), 1M return (**...%**), 1Y return (**...%**), and 30-day range (**₹Min to ₹Max**) alongside a beginner-friendly parenthetical explanation (...) of NAV. Mention the fund category and benchmark (e.g., **Nifty LargeMidcap 250 TRI**) and explain how macro economic drivers (e.g., **RBI repo rate stance**, **inflation**, festive credit demand) set the broader market mood.
4. COVER 5 TO 6 DISTINCT NAMED COMPANIES WITH REAL-WORLD STORIES:
   - Explicitly name and detail **5 to 6 distinct portfolio companies** across the bullets and summary (e.g. **ICICI Bank**, **The Federal Bank**, **Max Healthcare**, **InterGlobe Aviation / IndiGo**, **Larsen & Toubro**, **ABB India / Trent**) with exact portfolio weights (%).
5. NO RAW INDIVIDUAL STOCK PRICES OR STOCK RETURN %:
   - Do NOT output raw stock CMPs (₹) or individual stock % return numbers in the visible text. Focus entirely on the real-world business stories, capacity expansions, M&A deals, and order books.
6. EXPLAIN UNFAMILIAR TERMS IN BRACKETS (...):
   - Explain financial concepts in parentheses (...) on first mention (e.g., repo rate, credit-deposit ratio, net interest margin, capex, captive power plant).
7. CLEAN, SCANNABLE 5-BULLET STRUCTURE:
   - Start each bullet line directly with "- ". Never include square brackets `[...]` or prefix labels.

Write your reply in exactly this structure (plain text):

BULLETS:
- Open directly with the fund's **Latest NAV (₹...)**, **1W return (...%)**, **1M return (...%)**, **1Y return (...%)**, and **30-day range (₹Min to ₹Max)** alongside a simple explanation (...) of NAV, category/benchmark context, and the **macro economic climate** shaping the market backdrop. 1-2 complete sentences, ~35-50 words.
- Detail 1-2 banking and financial heavyweights with bolded names and weights (e.g. **ICICI Bank Limited (7.50% weight)**, **The Federal Bank Limited (3.16% weight)**), highlighting their specific **strategic moves**, **multi-thousand-crore merger talks**, or **liquidity deployments** clearly. 1-2 complete sentences, ~35-50 words.
- Detail 1-2 healthcare or consumer champions with bolded names and weights (e.g. **Max Healthcare Institute Limited (6.64% weight)**, **Trent Limited (3.67% weight)**), highlighting their dedicated **business catalysts** and **capacity expansions**. 1-2 complete sentences, ~35-50 words.
- Detail 1-2 aviation, industrial, or infrastructure leaders with bolded names and weights (e.g. **InterGlobe Aviation Limited (7.58% weight)**, **Larsen & Toubro Limited (3.62% weight)**, **ABB India Limited (4.63% weight)**), highlighting their **operational milestones** and **order wins**. 1-2 complete sentences, ~35-50 words.
- Conclude with the big-picture takeaway for everyday investors: Explain how holding this diverse basket of 5-6 well-managed businesses across essential sectors helps **protect and compound wealth** over the long term despite short-term macro dips. 1-2 complete sentences, ~35-50 words.
(Start each line directly with "- ". Do NOT include prefix labels.)

SUMMARY:
One captivating storytelling paragraph of about 65–90 words (3–5 sentences) weaving the complete narrative of the fund: the macro mood, 4–5 hero companies making big moves across sectors in **bold**, and why the fund is well-positioned for long-term growth in plain, engaging English. No bullet characters. No buy/sell advice. No URLs.
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

SYSTEM_PROMPT_FUND_NAV = """You help Indian mutual fund investors understand the NET ASSET VALUE (NAV) of their mutual fund in direct, concise, beginner-friendly English.

You receive:
1. The user's specific question asking about the NAV of a mutual fund.
2. Verified live NAV metrics from the RupeeStop API (Latest NAV, As On Date, 1W return, 1M return, 1Y return, 30-day range).
3. Fund details (Name, ISIN, Category, Official Benchmark).

CRITICAL RULES:
1. STRICTLY ANSWER ONLY WHAT WAS ASKED: The user asked specifically about NAV. Provide the exact latest NAV, as-on date, recent returns (1-week, 1-month, 1-year), 30-day trading band, and official benchmark context.
2. DO NOT DUMP UNREQUESTED INFORMATION: DO NOT list unrequested stock holdings or unrelated corporate news.
3. EXPLAIN NAV SIMPLY: Include a simple 1-sentence explanation of what Net Asset Value (NAV) represents in parentheses (...) or prose.
4. HIGHLIGHT KEY METRICS: Highlight the **Fund Name**, **Latest NAV (₹...)**, **As-On Date**, **Returns (%)**, and **30-Day Range** in bold.

Write your reply in exactly this structure (plain text):

BULLETS:
- The **[Fund Name]** recorded a **Latest NAV of ₹...** (as of **[Date]**), delivering a **1-week return of ...%**, **1-month return of ...%**, **1-year return of ...%**, and a **30-day trading range of ₹... to ₹...**. 1-2 complete sentences.
- Net Asset Value (**NAV**) represents the per-unit market price of the fund's underlying investments after accounting for fund operating expenses. 1 complete sentence.
- Operating in the **[Category]** category against the **[Benchmark]** benchmark, the fund's NAV tracks the collective market performance of its portfolio securities. 1 complete sentence.
(Start each line directly with "- ". Do NOT include prefix labels.)

SUMMARY:
One direct, concise summary paragraph of about 35–50 words stating the fund's current NAV standing, recent short-term trajectory, and official benchmark with 2–3 selective **bold** highlights. No extra fluff. No buy/sell advice. No URLs.
"""

SYSTEM_PROMPT_FUND_HOLDINGS = """You help Indian mutual fund investors understand the TOP EQUITY HOLDINGS of their mutual fund in direct, structured English.

You receive:
1. The user's specific question asking about fund holdings.
2. Verified top equity holdings list with exact weights (%) and industries.
3. Fund details (Name, Category, Benchmark).

CRITICAL RULES:
1. DIRECTLY ANSWER ONLY WHAT WAS ASKED: Present the top holdings with their exact allocation percentages (%) and sectors.
2. ZERO UNREQUESTED FLUFF: Do not lecture on unrelated macro events or give buy/sell advice.
3. HIGHLIGHT KEY WORDS: Highlight **Company Names** and **Allocation Weights (%)** in bold in every bullet.

Write your reply in exactly this structure (plain text):

BULLETS:
- Detail the fund's top 3 heavyweight equity holdings with exact bolded weights (e.g. **HDFC Bank Limited (7.63%)**, **ICICI Bank Limited (5.67%)**, **ITC Limited (5.26%)**) and their respective industry sectors. 1-2 complete sentences.
- Detail the next 3-4 prominent portfolio holdings with exact bolded weights and sectors. 1-2 complete sentences.
- Explain the overall portfolio concentration (e.g. total percentage held by the top 10 holdings) and multi-sector diversification. 1-2 complete sentences.
(Start each line directly with "- ". Do NOT include prefix labels.)

SUMMARY:
One concise summary paragraph of about 40–55 words highlighting the fund's core portfolio anchors in **bold** and its multi-sector diversification. No extra fluff. No buy/sell advice. No URLs.
"""

SYSTEM_PROMPT_FUND_SECTORS = """You help Indian mutual fund investors understand the SECTOR ALLOCATIONS of their mutual fund in direct, structured English.

You receive:
1. The user's specific question asking about sector allocation.
2. Verified top sectors with exact weights (%).
3. Fund details (Name, Category, Benchmark).

CRITICAL RULES:
1. DIRECTLY ANSWER ONLY WHAT WAS ASKED: Present the fund's sector allocations with exact percentages (%).
2. HIGHLIGHT KEY WORDS: Highlight **Sector Names** and **Percentages (%)** in bold in every bullet.

Write your reply in exactly this structure (plain text):

BULLETS:
- State the fund's primary sector exposures with exact bolded weights (e.g. **Banks (21.4%)**, **Technology (11.2%)**, **Automobiles (9.8%)**). 1-2 complete sentences.
- Detail secondary sector allocations and defensive exposures with exact bolded weights. 1-2 complete sentences.
(Start each line directly with "- ". Do NOT include prefix labels.)

SUMMARY:
One concise summary paragraph of about 35–50 words summarizing the fund's sector allocation and asset diversification in **bold**. No extra fluff. No buy/sell advice. No URLs.
"""

def _get_system_prompt(intent: str) -> str:
    if intent == "fund_nav":
        return SYSTEM_PROMPT_FUND_NAV
    if intent == "fund_holdings":
        return SYSTEM_PROMPT_FUND_HOLDINGS
    if intent == "fund_sectors":
        return SYSTEM_PROMPT_FUND_SECTORS
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


def _extract_portfolio_catalysts(
    parsed: ParsedQuery,
    articles: list[dict],
    fund_context: str,
    *,
    query_log: QueryLogger | None = None,
) -> str:
    """Stage 1: Portfolio Signal & Catalyst Extractor (Analyst LLM)."""
    fund_short_name = parsed.fund_resolved.get("fund_short_name", "") if parsed.fund_resolved else ""
    fund_isin = parsed.fund_resolved.get("isin", "") if parsed.fund_resolved else ""
    fund_category = parsed.fund_resolved.get("category", "") if parsed.fund_resolved else ""
    from news_rag.fund_search import get_fund_benchmark
    benchmark = get_fund_benchmark(fund_category, fund_short_name)

    user_content = (
        f"Fund Name: {fund_short_name} (ISIN: {fund_isin})\n"
        f"Fund Category: {fund_category} (Official AMFI Benchmark: {benchmark})\n\n"
        f"Verified Fund & Stock Portfolio Data:\n{fund_context}\n\n"
        f"Retrieved News Articles (Total: {len(articles)}):\n{_format_context(articles)}\n\n"
        "Extract the structured Portfolio Catalyst Briefing following the system instructions."
    )

    try:
        result = call_insight_llm(
            system_prompt=SYSTEM_PROMPT_ANALYST_EXTRACTOR,
            user_content=user_content,
            query_log=query_log,
        )
        if query_log is not None:
            query_log.record_llm_call(
                provider=result.provider,
                model=result.model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                total_tokens=result.total_tokens,
                duration_sec=result.duration_sec,
                http_status=result.http_status,
            )
        return result.raw_text.strip()
    except Exception as exc:
        if query_log is not None:
            query_log.log_error("stage1_analyst", str(exc))
        return ""


def _insight_payload(
    bullets: list[str],
    summary: str,
    *,
    insight_source: str,
    parsed: ParsedQuery,
    sources: list[dict],
) -> dict:
    display = format_insight_display(bullets, summary)
    payload = {
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
    if parsed.fund_resolved:
        from news_rag.fund_search import get_fund_benchmark
        f_cat = parsed.fund_resolved.get("category", "")
        f_name = parsed.fund_resolved.get("fund_short_name", "")
        payload["fund_metadata"] = {
            "isin": parsed.fund_resolved.get("isin"),
            "fund_name": f_name,
            "category": f_cat,
            "benchmark": get_fund_benchmark(f_cat, f_name),
            "scheme_type": parsed.fund_resolved.get("scheme_type"),
            "plan": parsed.fund_resolved.get("plan", "Regular"),
            "option": parsed.fund_resolved.get("option", "Growth"),
        }
    return payload


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

        if parsed.intent in ("fund_nav", "fund_holdings", "fund_sectors", "fund_event_impact", "fund_info", "multi_question"):
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
    elif parsed.intent == "fund_nav" and fund_context:
        from news_rag.fund_search import get_fund_benchmark
        fund_category = parsed.fund_resolved.get("category", "")
        fund_name = parsed.fund_resolved.get("fund_short_name", "")
        fund_benchmark = get_fund_benchmark(fund_category, fund_name)

        user_content = (
            f"User Question: {parsed.question}\n"
            f"Selected Fund: {fund_name} (ISIN: {parsed.fund_resolved.get('isin')} | Category: {fund_category} | Benchmark: {fund_benchmark})\n"
            f"Time Window: {parsed.window_label}\n\n"
            f"Verified NAV Performance Data:\n{nav_block}\n\n"
            "Instructions for Direct NAV Response:\n"
            "1. DIRECTLY AND CONCISELY ANSWER THE NAV QUESTION: Quote the fund's exact latest NAV (**₹...**), As-On Date, 1W return (**...%**), 1M return (**...%**), 1Y return (**...%**), and 30-day range (**₹Min to ₹Max**).\n"
            "2. EXPLAIN NAV: Include a simple 1-sentence explanation of what Net Asset Value (NAV) represents in parentheses (...) or prose.\n"
            "3. NO UNREQUESTED HOLDINGS OR NEWS: DO NOT list unrequested stock holdings or unrelated company news.\n"
            "4. HIGHLIGHT KEY METRICS: Bold the **Fund Name**, **Latest NAV**, **As-On Date**, **Returns (%)**, and **30-Day Range**.\n"
            "5. Structure: Exactly 2-3 short, clean bullets and a 35-50 word summary."
        )
    elif parsed.intent == "fund_holdings" and fund_context:
        from news_rag.fund_search import get_fund_benchmark
        fund_category = parsed.fund_resolved.get("category", "")
        fund_name = parsed.fund_resolved.get("fund_short_name", "")
        fund_benchmark = get_fund_benchmark(fund_category, fund_name)

        user_content = (
            f"User Question: {parsed.question}\n"
            f"Selected Fund: {fund_name} (ISIN: {parsed.fund_resolved.get('isin')} | Category: {fund_category} | Benchmark: {fund_benchmark})\n"
            f"Time Window: {parsed.window_label}\n\n"
            f"{holdings_block}\n\n"
            "Instructions for Fund Holdings Response:\n"
            "1. DIRECTLY ANSWER WITH TOP HOLDINGS: Detail the fund's top holdings with their exact bolded weights (e.g. **HDFC Bank Limited (7.63%)**) and sectors.\n"
            "2. ZERO UNREQUESTED FLUFF: Do not lecture on unrelated macro events or give buy/sell advice.\n"
            "3. HIGHLIGHT KEY WORDS: Highlight **Company Names** and **Weights (%)** in bold in every bullet.\n"
            "4. Structure: Exactly 3 short, clean bullets and a 40-55 word summary."
        )
    elif parsed.intent == "fund_sectors" and fund_context:
        from news_rag.fund_search import get_fund_benchmark
        fund_category = parsed.fund_resolved.get("category", "")
        fund_name = parsed.fund_resolved.get("fund_short_name", "")
        fund_benchmark = get_fund_benchmark(fund_category, fund_name)

        user_content = (
            f"User Question: {parsed.question}\n"
            f"Selected Fund: {fund_name} (ISIN: {parsed.fund_resolved.get('isin')} | Category: {fund_category} | Benchmark: {fund_benchmark})\n"
            f"Time Window: {parsed.window_label}\n\n"
            f"{sectors_block}\n\n"
            "Instructions for Fund Sectors Response:\n"
            "1. DIRECTLY ANSWER WITH SECTOR BREAKDOWN: State the fund's primary sector exposures with exact bolded weights (e.g. **Banks (21.4%)**, **Technology (11.2%)**).\n"
            "2. ZERO UNREQUESTED FLUFF: Do not lecture on unrelated macro events or give buy/sell advice.\n"
            "3. HIGHLIGHT KEY WORDS: Highlight **Sector Names** and **Percentages (%)** in bold in every bullet.\n"
            "4. Structure: Exactly 2-3 short, clean bullets and a 35-50 word summary."
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
        # Stage 1: Portfolio Signal & Catalyst Extraction (Analyst LLM)
        catalyst_briefing = _extract_portfolio_catalysts(
            parsed,
            articles,
            fund_context,
            query_log=query_log,
        )

        from news_rag.fund_search import get_fund_benchmark
        fund_category = parsed.fund_resolved.get("category", "")
        fund_name = parsed.fund_resolved.get("fund_short_name", "")
        fund_benchmark = get_fund_benchmark(fund_category, fund_name)

        user_content = (
            f"User Question: {parsed.question}\n"
            f"Selected Fund: {fund_name} (ISIN: {parsed.fund_resolved.get('isin')} | Category: {fund_category} | Benchmark: {fund_benchmark})\n"
            f"Time Window: {parsed.window_label}\n\n"
            f"{fund_context}\n\n"
            f"Internal Portfolio Catalyst Briefing:\n{catalyst_briefing}\n\n"
            "Instructions for Chief Investment Strategist Response:\n"
            "1. EXPLICIT FUND NAV & MACRO BACKDROP IN BULLET 1: Quote the fund's exact latest NAV (**₹...**), 1W return (**...%**), 1M return (**...%**), 1Y return (**...%**), and 30-day range (**₹Min to ₹Max**) alongside a bracketed explanation (...) of NAV, its category/benchmark context, and the macroeconomic climate (e.g. RBI rate outlook, inflation, festive credit demand) setting the broader market mood.\n"
            "2. HIGHLIGHT KEY WORDS IN ALL BULLETS: ALWAYS highlight the most important words in **bold** in each bullet (e.g. **Company Names (Weights %)**, **Key Metrics**, and **Core Strategic Actions/Deals** like **share-swap merger**, **capacity expansion**, **₹797 Cr order**).\n"
            "3. COVER 5 TO 6 DISTINCT NAMED COMPANIES WITH REAL-WORLD STORIES: You MUST explicitly feature 5 to 6 distinct portfolio companies across the bullets and summary (e.g. 2 banking giants, 2 consumer/healthcare/transport leaders, and 1-2 industrial/tech companies) with their exact weights (%). Never mash unrelated companies into the same sentence.\n"
            "4. NO RAW INDIVIDUAL STOCK PRICES OR STOCK RETURN %: Use holding stock prices and internal analyst signals internally for reasoning, but DO NOT output individual stock prices or stock % movements in the visible result.\n"
            "5. REAL-WORLD CORPORATE STORIES: Detail concrete news, deals, expansions, leadership changes, or order wins for these companies from the news excerpts and analyst briefing.\n"
            "6. BRACKETED EXPLANATIONS: Explain unfamiliar terms in parentheses (...) on first mention.\n"
            "7. Keep each bullet to 1-2 rich sentences (~35-50 words). Keep summary to 65-90 words with 4-5 hero companies in **bold**."
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
