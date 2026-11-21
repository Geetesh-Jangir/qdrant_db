# SUM CHATBOT — Overview for investors and product teams

This document describes **SUM CHATBOT**: the conversational feature on the RupeeStop **News Insight** page where you type a question and receive a written answer grounded in fund data, portfolio information (when loaded), and a stored financial-news library. In the product, the assistant introduces itself as an **AI bot by SUM**.

---

## A. Executive overview

**What it is.** SUM CHATBOT is a question-and-answer assistant focused on **Indian mutual funds, listed stocks, sectors, and market news**. It turns your question into a short research plan, fetches the numbers and articles it needs, and writes a plain-language answer—often with tables for comparisons or portfolio facts.

**Primary purpose.** Help you understand **what happened**, **what a fund holds**, **how it performed over a period you care about**, and **what news may be relevant**—without opening many screens or reading long news lists yourself.

**What you can use it for.**

- Look up NAV, returns, risk labels, RupeeStop ratings, and fund facts for a **named scheme**.
- See **top holdings and sector weights** for a fund.
- **Compare** two or more named funds.
- Explore **sectors**, **indices**, **macro topics** (crude, RBI, inflation, gold, and similar), and **market-wide** news.
- Ask **“why did this fund fall?”**-style questions that combine performance, holdings, and news.
- When you **load your portfolio** (via a client reference number, CRN), ask about **your holdings, allocation, SIPs, XIRR**, and how news may relate to your book.

**Why it is useful.** It connects **live or recent fund metrics**, **holdings files maintained in the system**, **retrieved news articles**, and (optionally) **your actual portfolio** into one narrative, with source articles you can open from the answer.

**What it is not designed to do.**

- It does **not** give buy, sell, hold, or switch advice, price targets, or predictions.
- It does **not** guarantee complete data for every fund, stock, or date range.
- It does **not** replace official scheme documents, AMFI filings, or personalized advice from a human adviser.
- It does **not** explain its own internal technology when asked.

---

## B. How the feature works from an investor’s perspective

1. **You ask a question** in the chat box (and optionally **load a portfolio** so “my funds” questions can be answered).
2. **The system checks the question** for topics it supports, policy rules (for example advice requests), and whether it needs a fund name or portfolio login.
3. **It decides what to look up**—for example fund returns, holdings, news about a sector, or your portfolio summary—and fetches that information in one or two steps (numbers first, then targeted news when useful).
4. **It writes the answer** using only what was fetched, with instructions to avoid inventing numbers or fund names. Simple numeric questions may get a very short reply; richer “why” questions get sections and news context.
5. **You can ask follow-up questions** in the same chat. The system keeps a **short conversation memory** (recent funds discussed, last period, last intent) for roughly **30 minutes** of inactivity, and the web page sends recent turns with each new question.

You may see a brief wait while data and news are gathered; complex questions are allowed more time than very simple ones.

**Optional filters.** The server can accept date ranges, news impact level, source, and direction filters on an ask request. The default **News Insight** chat UI does **not** expose these; they matter mainly for advanced or API use.

---

## C. What questions can it answer?

Below are categories **actually wired** in the current SUM CHATBOT pipeline (planner + data tools + news tools + composer). Wording can vary; examples illustrate typical support.

### Fund information (facts about a named scheme)

- **What you can ask:** NAV, latest returns (1 day, 1 week, 1 month, and longer windows when requested), expense ratio, AUM, exit load, minimum SIP, category, benchmark name, SEBI riskometer, RupeeStop rating label, fund managers, 52-week NAV range.
- **What it uses:** RupeeStop fund services and on-disk fund catalogue; ratings from RupeeStop when requested.
- **What to expect:** Factual numbers with the **time window stated**; short answers for single figures, more detail if you ask for “about this fund.”
- **Limits:** Fund name must resolve to a known scheme; similar names may need clarification on the **first** message in a chat. Use the **full official scheme name** when possible. If the chat uses a **nickname** (for example “SBI Bluechip”), it may answer using the **closest catalogue name** (for example SBI Large Cap) and say so. **RupeeStop rating** may be missing when the rating API does not return data.

*Example:* “What is the 1-year return of Parag Parikh Flexi Cap Fund?”

### Fund performance and benchmarks

- **What you can ask:** Performance over periods you name (or implied defaults—see section F), comparison to benchmark where the data provides it, drawdown over standard horizons.
- **What it uses:** NAV history and benchmark metadata for the scheme.
- **Limits:** Very long custom ranges may map to the nearest supported return window (for example 1M, 3M, 6M, 1Y).

*Example:* “How did Parag Parikh Flexi Cap do over the last month versus its benchmark?”

### Fund holdings and sectors (inside one scheme)

- **What you can ask:** Top stocks held, sector allocation, how many stocks, finding a specific company in the portfolio.
- **What it uses:** Holdings and sector weights from aggregated fund files (regular-growth universe is emphasized in several rankings).
- **Limits:** **`top_n`** defaults to a small number (often 3–5) unless you say “top 10”; holdings are as of the aggregate snapshot, not necessarily today’s AMFI disclosure.

*Example:* “Top 5 holdings of Axis Bluechip Fund.”

### Why a fund moved (performance explanation)

- **What you can ask:** Why a fund rose or fell over a recent period; which holdings or sectors may have contributed.
- **What it uses:** Fund return for the period, **attribution-style** breakdown (estimated contribution from major holdings using stock moves), sector weights, and—when the move looks materially negative or policy triggers—**financial news** about the fund, its holdings, or sectors.
- **What to expect:** A plausible story linking **numbers + weights + news**, not a legally proven cause.
- **Limits:** Attribution includes an **“unexplained”** portion when holdings do not fully account for the fund move; news may be incomplete for thinly covered stocks. If the fund **rose** in the period you asked about, the answer explains the **gain** instead of insisting on a fall.

*Example:* “Why did Bandhan Large Cap fall in the last month?”

### Sector and market views

- **What you can ask:** How a sector is doing, sector index returns, which funds have high exposure to a sector, sector-level news.
- **What it uses:** Sector indices (where available), sector–fund mapping files, news search scoped to sector or market.
- **Limits:** Sector naming must match the system’s sector list; weak coverage for niche themes.

*Example:* “How is the automobile sector doing over the last six months?”

### Financial news

- **What you can ask:** Recent news on a fund’s holdings, a stock, a sector, macro topics, or broad market pulse.
- **What it uses:** A **stored news library** (searchable by meaning, not just keywords) plus optional filters when provided via API.
- **Limits:** Default news lookback is often **roughly 2–4 weeks** per tool settings unless the plan sets a longer window (up to about 180 days for some news tools). The answer cites a **limited number of articles** (often up to about eight considered for writing, fewer shown in full detail).

*Example:* “What recent news could affect banking sector funds?”

### Market and macro conditions

- **What you can ask:** Index returns (for example Nifty 50), sector rankings, crude, USD/INR, gold (India 24K quote), US yield series, individual stock quotes where supported.
- **What it uses:** Market snapshot tools and RupeeStop price APIs; some series use public market data feeds.
- **Limits:** **Silver spot price is not available**—silver questions are handled via news only. Macro “which funds benefit if oil rises” uses **rule- and exposure-based screens**, not a forecast.

*Example:* “What is gold doing this month?”

### Fund comparison and screening

- **What you can ask:** Compare two or more **named** funds (metrics and overlap); find top funds in a category by RupeeStop rating; list funds with high exposure to a sector, stock, or macro driver; random or “top N” screens when you do not name a fund.
- **Limits:** Compare needs at least two resolved fund names; unnamed “best fund” questions depend on category wording and rating screens. **Nicknames** (for example “SBI Bluechip”) may be answered using the **nearest official scheme name** in the catalogue.

*Example:* “Compare HDFC Flexi Cap and Parag Parikh Flexi Cap.”

### Investor portfolio (your book)

- **What you can ask:** When a **CRN is loaded** for the chat session: total value, allocation, list of holdings, per-scheme P&L, XIRR, SIP/STP lists, concentration, risk profile, returns for all holdings over a window, “how am I doing,” sector exposure of **your** book, news mapped to your portfolio or a sector you hold.
- **What it uses:** RupeeStop portfolio API for the loaded CRN (cached briefly on the server).
- **Limits:** Without loading a portfolio, “my funds” questions receive a **sign-in message** (for example: “Please sign in to see your own portfolio…”). There is **no** generic JSON portfolio file for ask in default configuration.

*Example:* “One-month return of every fund in my portfolio.”

### Education and glossary-style questions

- **What you can ask:** What a fund type means (for example Fund of Funds), combined with **one real example scheme** from the catalogue when you ask to “name one.”
- **Limits:** Example names must come from screening tools, not invented.

*Example:* “What is a Fund of Funds? Name one example.”

### Simple financial arithmetic (no fund lookup)

- **What you can ask:** Some **SIP / goal / FIRE-style illustrations** where the question is purely calculable from amounts and rates stated in the question.
- **Limits:** Not tied to live fund performance unless you also ask for fund data.

### Follow-up questions

- **Supported:** References like “that fund,” “last month” again, compare sides from chat memory, portfolio category funds (“my contra fund”) when portfolio is loaded and memory is warm.
- **Limits:** Memory expires after **~30 minutes** idle; only the last several turns and a small stack of recent fund names are kept.

### What it will decline early

- **Investment advice** (“should I buy…”) → redirected to the app for recommendations; factual parts may still be answered in some mixed questions.
- **Predictions and forecasts** (explicit predict/forecast/target price patterns in the legacy guard used on some fallback paths).
- **Non-finance** topics.
- **Questions about how the bot is built** (prompts, models, APIs).

---

## D. What can it answer fully, partially, or not at all?

| Question type | Support level | What it can provide | Important limitation | Example question |
|---|---|---|---|---|
| NAV or return for a **named** fund | **Supported** | Figures for standard windows when data exists | Needs correct scheme name; deadline may cut off slow API | “Latest NAV of SBI Bluechip Fund” |
| Holdings / sectors of a **named** fund | **Supported** | Top holdings and sector weights from aggregates | Snapshot freshness; default small `top_n` | “Sector breakdown of UTI Nifty 50 Index Fund” |
| **Compare** two named funds | **Supported** | Side-by-side metrics and holding overlap | Both names must resolve | “Compare Nippon Large Cap vs ICICI Pru Bluechip” |
| **Why** fund fell / rose | **Partially supported** | Return, attribution estimates, news | Not full proven causality; unexplained return gap | “Why did my flexi cap fall last month?” |
| Holding-level **exact** return contribution | **Partially supported** | Estimated contributors/detractors (top names) | Not full portfolio attribution to every stock | “Which stocks hurt Bandhan Large Cap most?” |
| **Screen** funds by sector/driver/rating | **Supported** | Ranked list from catalogue rules | “Regular growth” bias in some impact rankings | “Funds with high bank exposure” |
| Sector / index **performance** | **Partially supported** | Index return series for many sectors | Gaps for ill-defined sectors | “Bank Nifty performance last 3 months” |
| **Market-wide** news pulse | **Supported** | Thematic news summary | Article cap and window limits | “What is happening in the market today?” |
| Macro **which funds benefit** | **Partially supported** | Funds screened by exposure + news | Directional linkage, not prediction | “If crude rises, which funds may benefit?” |
| **Stock** price snapshot | **Partially supported** | Quote when ticker resolves | Coverage not universal | “How did Reliance stock do this month?” |
| **Silver** spot price | **Not supported** | News about silver only | No silver price series in tools | “Silver price today?” |
| **Your portfolio** metrics | **Supported** (if CRN loaded) | Holdings, XIRR, SIP, allocation, etc. | Requires portfolio load; API timeouts on slow days | “What is my XIRR?” |
| **Your portfolio** without CRN | **Not supported** | Prompt to load portfolio | No default personal book | “Show my holdings” |
| Buy / sell / recommend | **Not supported** | Policy message + pointer to app | By design | “Should I sell HDFC Balanced Advantage?” |
| Future NAV / predictions | **Not supported** | Refusal or no forecast data | By design | “Will this fund double next year?” |
| **Past** policy / RBI **explain** with news | **Supported** | Historical news + macro snapshot | News may lag event | “How did RBI rate cut news affect banking funds?” |
| SIP math in question only | **Supported** | Computed illustration | Not investment advice | “If I invest ₹10,000 monthly at 12% for 10 years…” |
| Every fund in India / unlimited list | **Partially supported** | Screens and top-N lists | Hard caps on list length and fan-out | “List all mutual funds” |
| Real-time **intra-day** trading | **Partially supported** | Day change where NAV feed provides | Not a live trading terminal | “Intraday NAV tick by tick” |

**Factual vs explanatory:** Reporting “the fund fell 2.1% over 1M” is **factual** when NAV data is present. Saying “it fell because of IT earnings” is **interpretive**, supported only when news and attribution data back the link—and should be read as **plausible context**, not certainty.

---

## E. What data does the system have access to?

| Data category | What is available | How SUM CHATBOT uses it | What you learn | Freshness / coverage notes |
|---|---|---|---|---|
| Mutual fund catalogue | Scheme names, ISINs, categories, AMC | Name resolution, screens, comparisons | Which fund you are discussing | Fuzzy matching; ambiguous names may need clarification |
| NAV and returns | Latest NAV, standard return windows, day change | Snapshots, return series, portfolio holding returns | Performance over stated periods | From RupeeStop/backend; cached briefly on server |
| Holdings & sectors | Stock weights, sector weights per scheme (aggregated files) | Holdings questions, attribution, exposure screens | What the fund owns | Aggregate files under fund holdings data; not live for every scheme field |
| Sector ↔ fund mapping | Which funds overweight a sector | Sector screens, driver screens | Funds exposed to a theme | Regular-growth emphasis in some rankings |
| RupeeStop rating | Score and label bands | Ratings, category “best fund” screens | Relative quality label | Fetched per ISIN; concept explained in answers |
| Benchmark metadata | Stated benchmark name; index returns for context | vs-benchmark answers | Relative performance | Benchmark **name** vs actual index return may differ; Nifty 50 sometimes used as broad reference |
| Financial news | Ingested articles in searchable store | Semantic search by fund, stock, sector, macro | Events that may explain moves | Depends on ingest; `retrieve_max_articles` and composer caps limit how many shape the answer |
| Market indices & macros | Nifty, Sensex, sector indices, crude, USD/INR, gold, yields | Market snapshot module | Macro context | Some via APIs and market data feeds |
| Stock prices | Selected listed names | Attribution, stock quote | Stock move over window | Not every small cap guaranteed |
| Investor portfolio | Holdings, transactions, XIRR, SIP for **loaded CRN** | `get_investor_portfolio` when enabled | Your personal book | Live API; longer time budget when portfolio tools run |
| Commodity spot | **Gold** (INR); not silver | Metals spot in market snapshot | Gold level | Silver: news only |

**Not available to this feature by default:** A personal portfolio without CRN binding; arbitrary uploaded portfolios; guaranteed complete news for all global events; silver spot; certified attribution from the AMC.

**Exists elsewhere in the project but separate products:** Scheduled **Market Insights**, **Stock Holding Insights**, and **Fund News Brief** pages may use overlapping data but are not the same chat flow.

---

## F. Default values and assumptions

Behavior can differ between the **main planner path** and the **backup rule-based router** used when the planner fails. The table states what the code configures.

| Situation | Actual default or behavior | What it means for the investor |
|---|---|---|
| No time period mentioned (planner path) | **`window_days` = 30** on the execution plan | “Recently” often means **about the last month** unless you say otherwise |
| “Right now,” “today,” “currently,” “this week” (planner rules) | **7 days** | Very near-term news and moves |
| “Why down” / recent move without dates (planner rules) | **30 days** typical for metrics and attribution | Align questions with “last month” if you want consistency |
| No time period (backup rule router only) | **180 days (6 months)** from text heuristics | Rare path; if answers feel long-windowed, rephrase with explicit dates |
| Fund return windows not specified in data call | **`1Y`, `3Y`, `5Y`** for snapshot-style returns | Long-term facts unless you asked for 1M etc. |
| Attribution / return series lookback | **`window_days` default 30** (7–365 allowed) | “Why fell” usually tied to ~1 month of stock moves |
| News search window (tool default) | **14 days** (`search_financial_news`) | Tight recent news unless plan sets more (up to ~180) |
| News articles considered | Up to **`news_top_k` 6** retrieval flavor; composer often **up to 8** articles, **4** with longer body text | Answer may miss older or minor stories |
| Top holdings shown | **`top_n` default 3** (holdings tool); request **`count` default 3** in planner schema | Say “top 10” for more names |
| Fund screen list size | **`top_n` default 5** (max 20) | “Top funds” lists are capped |
| Investor portfolio holdings list | **`top_n` default 10** | Large books summarized |
| Compare unnamed funds in category | Rating screen + pick rules | May pick “best” or alternate by RupeeStop label rules |
| Ambiguous fund name (new chat) | May ask: **“Which mutual fund do you mean?”** | Examples in prompt are not treated as your choice |
| “My fund” without portfolio | **Sign-in / load portfolio message** | Load CRN in UI first |
| Mixed advice + data question | Advice part redirected; data may still be planned | Ask fact and advice separately for clarity |
| Conversation memory idle | **30 minutes** then reset | Start a new chat or repeat fund name after a break |
| Chat history sent to server | Up to **8 recent chat turns** in memory design | Very long threads lose early context |
| Query time budget | Server **deadlines** default to **~8s simple**, **~20s standard**, **~45s complex** (portfolio asks can use longer); **end-to-end** time often includes **~6–8s** for planning plus data and composition, so simple factual asks are commonly **~15–20s** | Slow APIs → partial answers or retries |
| Silver | No price series | Ask for news on silver instead |

**“Current” or “latest” NAV** means the newest value returned by the fund data service at ask time, not a exchange tick.

**Timezone / dates:** News and NAV dates follow data provider timestamps; the UI does not let you pick a news date range by default.

---

## G. How does it explain why a fund went up or down?

SUM CHATBOT can combine several **layers** when you ask a cause-style question about a **named fund** (typical mode: **INSIGHT_FUSION**—numbers plus news):

1. **What happened:** Fund return over the plan’s window (from NAV data).
2. **What the fund owns:** Sector weights and major holdings.
3. **Estimated holding impact:** An **attribution** module prices top holdings over the window and lists **contributors** and **detractors**, with **explained vs unexplained** portions of the fund move.
4. **Benchmark context:** Benchmark name and, when requested, return comparison.
5. **News (often second step):** If the fund’s return is meaningfully negative (policy threshold near **−1%** in examples) or the plan always requests news, it searches articles about the fund, its holdings, or sectors—then the composer links themes to the numbers.

**Levels of certainty (important):**

| Level | Meaning |
|---|---|
| **Report** | “The fund returned −2.3% over 1 month.” — factual if data loaded. |
| **Exposure** | “IT was 28% of the portfolio.” — factual from holdings file. |
| **Estimated contribution** | “Stock X may have weighed on returns.” — arithmetic from weights × stock moves; incomplete coverage. |
| **Narrative** | “Earnings downgrades in IT were in the news.” — grounded to articles retrieved, not proof the fund fell solely for that reason. |

The assistant is instructed **not** to invent holdings or events and to label windows on every return figure.

**Illustrative example (not a live result):**  
*You ask:* “Why did Fund ABC fall last month?”  
*You might get:* “Fund ABC returned about −1.8% over 1 month. Attribution suggests two large IT holdings together accounted for roughly half of the explained move, with the rest unexplained. News in that period mentioned sector profit warnings. This is context, not a guarantee those stocks caused the entire NAV change.”*

---

## H. Important limitations and potential failure cases

| Limitation | Why it matters | What you might see | Tip |
|---|---|---|---|
| **Incomplete holdings file** | Attribution uses top holdings only | Short contributor list; high **unexplained** % | Name the period; ask for top 10 holdings |
| **Stale aggregates** | Holdings files update on ingest schedule | Weights slightly old vs today’s factsheet | Cross-check AMFI factsheet for precision |
| **Fund name errors** | Fuzzy match has accept/reject thresholds | Clarification prompt or wrong fund if typo is close | Use full official scheme name |
| **Time deadlines** | Server stops waiting after budget | “Couldn’t get data right now” fragments | Simpler question or named single fund |
| **Portfolio API slow** | Extra time budget but not unlimited | Partial portfolio answer | Retry; ask one module at a time |
| **News gaps** | Not every stock has recent articles | Number-led answer with little news | Broaden to sector or macro news |
| **Correlation ≠ causation** | Composer synthesizes | Persuasive story that overfits | Treat as hypotheses |
| **No advice** | Regulatory/product policy | Refusal on pure recommendation asks | Use app for recommendations |
| **LLM wording risk** | Text is generated | Rare unsupported superlative | Check numbers against tables in answer |
| **Memory loss** | 30-minute idle timeout | Follow-up “it” unclear | Repeat fund name and period |
| **Silver / some macros** | Data absent | “News only” for silver | Ask gold or crude explicitly |
| **Regular-growth scope** | Some rankings filter plan type | Screen results omit direct plans if so configured | Name the plan type if needed |

---

## I. How investors can get the most value from it

**Be specific:** Include **fund name**, **period** (“1 month”, “since last RBI meeting”), and **what you want** (holdings vs news vs compare).

**Grouped example questions (aligned with current capabilities):**

*Performance and facts*

- “1-year and 3-year return of Parag Parikh Flexi Cap Fund.” (use the **full official scheme name**)
- “RupeeStop rating and risk label for Kotak Emerging Equity Fund.” (short names may match the nearest catalogue scheme)

*Holdings and sectors*

- “Top 10 holdings and largest sectors in Mirae Asset Large Cap.”
- “Does this fund hold Infosys? How much?”

*Explain moves*

- “Why did [fund name] fall over the last month?”
- “Which holdings may have hurt [fund name] recently?”

*Compare and screen*

- “Compare SBI Bluechip and ICICI Pru Bluechip.”
- “Top 5 flexi cap funds by RupeeStop rating.”
- “Funds with high exposure to banking.”

*Market and macro*

- “How is the pharma sector doing over 3 months?”
- “What is happening in the market this week?”
- “How could rising crude oil affect equity funds with energy exposure?”

*Portfolio (after loading CRN)*

- “How am I doing overall?”
- “1-month return of each of my funds.”
- “Where am I losing money?”
- “What is my allocation between equity and debt?”
- “News that may affect my portfolio this week.”

**Broad vs narrow:** “Tell me about flexi cap” triggers overview behavior; “1-month return of Parag Parikh Flexi Cap” triggers a precise numeric path.

---

## J. Quick reference: What should an investor expect?

| Topic | Expectation |
|---|---|
| **Does best** | Named-fund facts, holdings, comparisons, grounded news summaries, portfolio lookups when CRN is loaded |
| **Best questions** | Full scheme name + time window + clear intent (fact, compare, why, or my portfolio) |
| **Strong data** | NAV/returns for resolved funds, catalogue screens, news store, gold macro, many sector indices |
| **Weaker data** | Silver spot, every stock, complete daily attribution, all historical dates |
| **Defaults to remember** | ~**30 days** for many “recent” plans; **7 days** for “this week/today”; news often **~2 weeks** unless widened |
| **Hard limits** | No buy/sell advice; no futures; portfolio needs CRN; list and article caps |
| **If answer is thin** | Add period and fund name; load portfolio for “my” questions; split compound questions; start **New chat** if memory confused |

---

*Document based on the SUM CHATBOT implementation (`POST /api/ask` and `/api/ask/stream`), two-wave graph pipeline, capability tools, News Insight UI, guardrails, and configuration defaults in the repository. For technical architecture detail aimed at engineers, see `docs/ASK_A_QUESTION_FEATURE.md` (note: some sections there predate the graph planner and may describe older facet names).*