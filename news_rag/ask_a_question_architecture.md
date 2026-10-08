# Ask a Question — how it works, layer by layer

This document explains the **Ask a Question** feature (`POST /api/ask`). It is written so you can follow one question from the browser to the final insight: which code runs, which tools fire, what the LLM sees, and what comes back.

The live path is **not** the old `query_router.py` / `execution.py` files. Those stay unused. The live path is:

`news_rag/app.py` → `news_rag/ask_engine.py` → `news_rag/ask_agent.py` → tools → `news_rag/ask_composer.py` → judge (display only).

---

## 1. What the feature is

A user types a question in everyday language, for example:

- “What’s going on in the market?”
- “Name any two large-cap funds.”
- “Compare any two funds that hold BHEL stocks.”
- “Which funds are affected by crude news?”
- “NAV and holdings of HDFC Flexi Cap.”

The app must:

1. Refuse non-finance and buy/sell advice.
2. **Retrieve real rows** (news, NAV, holdings, sector weights). It must not invent expense ratio, AUM, TER, manager, or riskometer.
3. Write an answer in simple language that **only uses numbers and names from those rows**.

Typical live ask time is about **1–3 minutes**.

---

## 2. Picture of the whole pipeline

```text
Browser / API
    │  POST /api/ask  { question, optional date_from, date_to, min_impact, source, direction }
    ▼
App (news_rag/app.py)
    │  token check, Qdrant URL check, start a query log
    ▼
Ask engine (ask_engine.py)
    │
    ├── 1. Research agent (ask_agent.py)  ── LLM #1 (router / flash-lite)
    │         • guardrails
    │         • decide tools (JSON)
    │         • run tools (parallel)
    │         • look at observations
    │         • maybe more tools (up to 3 rounds)
    │         • gap filler if funds were asked but none came back
    │
    ├── 2. Composer (ask_composer.py)     ── LLM #2 (composer model)
    │         • article bodies + Context JSON
    │         • headline, narrative, bullets, closing
    │         • strip ungrounded numbers
    │
    └── 3. Judge                          ── LLM #3 or Jev (display only)
              • scores the draft
              • if grounded < 0.65 AND insight is not empty → ONE retry of agent + composer
              • empty insight is never retried
```

**Models (from `.env`):**

| Role | Default | Setting |
|------|---------|---------|
| Agent / router | Gemini flash-lite | `rag_router_model` or `GEMINI_MODEL` |
| Composer | Gemini 3.8 flash | `gemini_composer_model` |
| Judge / contract | flash-lite | `rag_contract_model` |
| Fallback | DeepSeek | `DEEPSEEK_API_KEY` if Gemini fails / quota |

Gemini is primary. If Gemini hits quota, further Gemini calls in that request are skipped and DeepSeek is used when configured.

---

## 3. Layer 0 — HTTP in (`app.py`)

**Input from the client**

```json
{
  "question": "which funds are affected by the crude price increase?",
  "stock": null,
  "date_from": null,
  "date_to": null,
  "min_impact": null,
  "source": null,
  "direction": null
}
```

Optional filters (`date_from`, `date_to`, `min_impact`, `source`, `direction`) are passed through to **news tools** as extra Qdrant filters. They are not required.

**What the app does before the engine**

1. Optional `APP_TOKEN` / `X-App-Token` / Bearer token.
2. Requires `QDRANT_URL`. Cloud URL also requires `QDRANT_API_KEY`.
3. Requires an LLM key (`GEMINI_API_KEY` or `DEEPSEEK_API_KEY`).
4. Opens a log file under `data/rag_query_logs/`.
5. Calls `run_ask_engine(...)`.

**What the client gets back (simplified)**

- `insight` — full text shown on the page (headline + narrative + bullets + closing)
- `insight_headline`, `insight_narrative`, `insight_bullets`, `insight_closing_summary`
- `sources` — article URLs (not printed as “Times of India, 7 Oct” in the insight)
- `research` — what the agent thought (intent, entities, tools, gaps)
- `answer_trace` — composer internals (themes, numbers cited, gaps)
- `output_scores` — judge scores (display / logs; they do not hide the answer)
- `refused` — true if out of scope or advice
- `pipeline_errors` — tool failures that still allowed a partial answer

---

## 4. Layer 1 — Guardrails (`guardrails.py`)

Think of this as a **bouncer at the door**. It looks only at the raw sentence. **No LLM. No Qdrant. No tools.**

```text
question string
      |
      v
  empty?  --------------------------------> refuse_out_of_domain  (STOP)
      |
      v
  "should I buy/sell/hold/invest"?  ------> refuse_advice  (flag only)
      |
      v
  predict / forecast / recommend /
  target price / buy now ... ?
      |
      |- but also historical words
      |  (how did, after the, due to, affected)
      |  and it is NOT should/recommend
      |                         ----------> still pass
      |
      +- otherwise ------------------------> refuse_advice  (flag only)
      |
      v
  has a finance word?
  (fund, funds, market, RBI, large cap, crude, stock...)
      |
      |- yes -----------------------------> pass
      |- "what is X" under 120 chars -----> pass
      |- poem / joke / python / recipe ---> refuse_out_of_domain  (STOP)
      +- short (<40 chars) no finance ----> refuse_out_of_domain  (STOP)
```

### What actually stops the pipeline

In `run_research_agent`, **only `refuse_out_of_domain` aborts** before the agent LLM.

`refuse_advice` is computed, but the agent **still runs**. The catalog tells the model: never request buy/sell. The composer later puts the disclaimer in `advice_declined_note` if `declined_parts` is set. That is the split: we can still fetch NAV or news for the factual part.

### Live-style examples (input to outcome)

**A. Hard refuse — not finance**

- **Input:** `write a python joke`
- **Checks:** no finance word; contains `python` and `joke`
- **Output:** `outcome=refuse_out_of_domain`
- **User sees:** *This question is outside our financial data scope. Ask about mutual funds, sectors, stocks, commodities, or recent market news in India.*
- **Stops?** Yes. No agent, no tools.

**B. Hard refuse — empty**

- **Input:** `""`
- **Output:** same out-of-scope message, `reason=empty`
- **Stops?** Yes.

**C. Pass — short fund question**

- **Input:** `give me any two large cap funds name?`
- **Checks:** `funds` and `large cap` match `_FINANCIAL_SIGNAL`
- **Output:** `pass`
- **Stops?** No. Agent continues and should call `screen_funds` with category Large Cap.

**D. Pass — market news (real log)**

- **Input:** `whats happening in the market right now?`
- **Checks:** word `market`
- **Output:** `pass`
- **What happened next** in `ask_20261007T070634Z_318abb`: Agent round 1 called `common_market_news` + `macro_news`.

**E. Advice flag — does not stop**

- **Input:** `should I buy HDFC Flexi Cap Fund now?`
- **Checks:** `should I buy` → `refuse_advice`
- **Stops?** **No.** Agent still runs. It should fetch fund facts and put buy/sell in `declined_parts`. Composer adds: *We provide historical data, current holdings, and analytical news context only. We do not provide price predictions, forward-looking forecasts, or investment advice.*

**F. Historical wording is allowed**

- **Input:** `how did banking funds move after the RBI hike?`
- **Checks:** `after the` is historical; not `should I buy`
- **Output:** `pass` — this is a past-impact question, not a prediction.

---

## 5. Layer 2 — Research agent (`ask_agent.py`)

The agent is a **researcher**, not a writer.

- It reads the question and (later) slim tool summaries.
- It returns JSON: what the user wants, which tools to run.
- It **never** writes the headline you see on the page. That is the composer.

```text
round = 1, 2, or 3   (ask_agent_max_rounds, default 3)
         |
         v
   Build briefing blocks  (question, today, name peek, last reading, observations)
         |
         v
   LLM #1  (router / flash-lite)  ->  JSON plan
         |
         v
   enrich_ask_plan  (aliases, extra hints from the sentence)
         |
         v
   Resolve fund names  (catalog / live API)
         |
         |- two funds match the same phrase --> stop. Ask user to pick. No composer.
         |
         v
   Split tools:
         standard  -- parallel (up to 8 threads)
         special   -- after that, because they need the rows just fetched
         |
         v
   Turn each result into a slim observation
         |
         |- status=need_tools and rounds left --> next round (observations now filled)
         |- status=ready or no more tools      --> exit loop
         |
         v
   Gap filler: if they asked for fund names and rankings are empty, run screen_funds anyway
```

After a failed judge (grounded < 0.65), the engine calls this again with **1 extra round** and a `grounding_note`.

---

### Walkthrough A — real log: “whats happening in the market right now?”

Log: `data/rag_query_logs/ask_20261007T070634Z_318abb.log` (7 Oct 2026).

#### Step 0 — Guardrail

`market` → **pass**.

#### Step 1 — Local name peek (no LLM)

The peek only runs a catalog lookup if the sentence has an **ISIN** (`INF…`) or the **singular** word `fund` (`\bfund\b`).

This question says “market”, not “fund”, and has no ISIN.

**Input to peek:** the question  
**Output in the briefing:**

```json
[]
```

So the agent is not nudged toward a scheme name. That is correct.

#### Step 2 — Briefing sent to LLM #1 (round 1)

The “user message” is **not** one paragraph. It is named blocks:

```text
[question]
whats happening in the market right now?

[today]
2026-10-07

[local_name_matches]
[]

[question_reading]
{}

[observations]
[]
```

Plus a long **system prompt** (`AGENT_SYSTEM`): you are the research agent, here is the tool catalog, return this JSON shape.

**LLM call (from the log):** Gemini `gemini-3.5-flash-lite`, about 1148 input tokens, 221 output tokens, about 3.6s.

#### Step 3 — Agent JSON out (round 1)

Log line:

```text
AGENT round=1 status=need_tools tools=["common_market_news", "macro_news"]
```

Meaning of `status`:

| `status` | Meaning |
|----------|---------|
| `need_tools` | Run the `tools` list, then show me observations. |
| `ready` | I have enough (or I am honest about the gap). Stop fetching. |

A typical filled-in JSON for this question looks like:

```json
{
  "status": "need_tools",
  "why": "Need a broad market snapshot and a short macro search for what is moving this week.",
  "question_reading": {
    "intent": "What is going on in Indian markets right now",
    "answer_shape": "narrative",
    "must_cover": ["main themes this week", "what is driving them"],
    "declined_parts": [],
    "sentiment": "any",
    "time_window_days": null
  },
  "entities": [],
  "relationships_to_check": [],
  "information_gaps": ["We do not yet have this week's clustered headlines."],
  "tools": [
    {
      "tool": "common_market_news",
      "purpose": "Broad Indian market snapshot for 'right now'.",
      "semantic_query": "India market news",
      "window_days": null
    },
    {
      "tool": "macro_news",
      "purpose": "One extra macro search.",
      "semantic_query": "RBI inflation oil India market"
    }
  ]
}
```

Why these two tools: the catalog says use `common_market_news` for “what is happening overall”, and news is allowed because they asked about the market. No `screen_funds` — they did not ask for fund names.

`enrich_ask_plan` may add window defaults. Tools not in `ALLOWED_PLANNER_TOOLS` would be dropped here.

#### Step 4 — Name resolution

No `fund_scheme` entities → nothing to resolve. Bundle starts empty except `names`.

#### Step 5 — How the two tools actually run

Both are **standard** tools → **same round, in parallel**.

From the same JSON log:

```text
tool_done  macro_news            key=macro_news_1           ~3.8s
market_pulse  articles=23  clusters=2
              top_labels=["Nifty Bank & lenders", "Corporate earnings season"]
tool_done  common_market_news    key=common_market_news_0   ~4.9s
```

So at once:

1. `common_market_news` embeds several themed queries, hits Qdrant, **clusters** articles. Kept 23 articles in 2 themes.
2. `macro_news` does one vector search (`event_only`, last 7 days, relevance >= 2).

Stored as `tool_results["common_market_news_0"]` and `tool_results["macro_news_1"]` (tool name + index).

#### Step 6 — Slim observations (what round 2 will see)

The agent does **not** get full article bodies. Each result is cut down. Shape:

```json
[
  {
    "tool": "common_market_news",
    "ok": true,
    "error": "",
    "purpose": "Broad Indian market snapshot for 'right now'.",
    "summary": "Themes: Nifty Bank & lenders, Corporate earnings season (23 articles).",
    "entities_found": ["Banks"],
    "numbers": [],
    "counts": { "articles": 23, "rows": 0 },
    "rows": [],
    "articles": [
      {
        "title": "India’s $133 billion cash deluge puts RBI on hawkish path",
        "direction": "negative",
        "sectors": ["Banks"],
        "entities": ["Banks"]
      }
    ]
  },
  {
    "tool": "macro_news",
    "ok": true,
    "summary": "macro_news returned 8 articles and 0 rows.",
    "counts": { "articles": 8, "rows": 0 },
    "articles": [
      {
        "title": "Markets bet on RBI hike as inflation pressure builds",
        "direction": "positive",
        "sectors": ["Banks"],
        "entities": ["Banks"]
      }
    ]
  }
]
```

Titles in observations are only **labels**. The composer later reads the **body**.

#### Step 7 — Round 2 briefing + LLM

Now `observations` is filled. `question_reading` is the JSON from round 1.

**LLM out (from the log):**

```text
AGENT round=2 status=ready tools=[]
```

Meaning: clusters already explain the week; do not fetch again. Loop can stop.

Then the composer writes the user-facing insight from **full bodies + Context**, not from these titles.

---

### Walkthrough B — two rounds + a special tool: “compare any two funds that hold BHEL stocks?”

This is the pattern when later tools **depend on** earlier rows.

#### Round 1 — agent input (same block shape)

```text
[question]  compare any two funds that hold BHEL stocks?
[today]     2026-10-07
[local_name_matches]  []     <- "funds" (plural) does not trigger \bfund\b peek
[question_reading]    {}
[observations]        []
```

**Typical agent output:**

```json
{
  "status": "need_tools",
  "why": "Need schemes that actually hold BHEL, then compare two of them.",
  "question_reading": {
    "intent": "Compare two mutual funds that hold BHEL",
    "answer_shape": "comparison",
    "must_cover": ["two fund names", "BHEL weight", "how they differ"],
    "declined_parts": [],
    "sentiment": "any"
  },
  "entities": [
    {
      "raw": "BHEL",
      "role": "holding",
      "cleaned_phrase": "BHEL",
      "why": "Stock the funds must hold"
    }
  ],
  "tools": [
    {
      "tool": "screen_funds",
      "purpose": "Find holders of BHEL",
      "stock_name": "BHEL",
      "top_n": 2
    },
    {
      "tool": "compare_funds",
      "purpose": "Compare the two holders just found",
      "depends_on": "screen_funds",
      "compare_on": "holdings",
      "stock_name": "BHEL",
      "top_n": 2
    }
  ]
}
```

#### Same round — split standard vs special

| List | Tools | When they run |
|------|--------|----------------|
| Standard | `screen_funds` | **Now**, in parallel (here only one) |
| Special | `compare_funds` | **After** screen rows are in the bundle |

Why: compare reads `bundle.tool_results` for rankings with `weight_pct`. If it ran at the same time as the screen, those rows would not exist yet.

**`screen_funds` input (after hints from the question):**

- `stock_name` = `bhel` (from `hold … stocks`)
- archive initials: **BHEL → Bharat Heavy Electricals Limited**
- scan industry Electrical Equipment, full holdings list, stop at 2 confirmed holders

**`screen_funds` data (shape):**

```json
{
  "ok": true,
  "data": {
    "stock_name": "Bharat Heavy Electricals Limited",
    "fund_count": 707,
    "rankings": [
      { "fund_name": "Holder A", "isin": "INFA", "holding_name": "Bharat Heavy Electricals Limited", "weight_pct": 2.1 },
      { "fund_name": "Holder B", "isin": "INFB", "holding_name": "Bharat Heavy Electricals Limited", "weight_pct": 1.4 }
    ]
  }
}
```

Observation for the agent:

```json
{
  "tool": "screen_funds",
  "ok": true,
  "entities_found": ["Holder A", "Holder B", "Bharat Heavy Electricals Limited"],
  "numbers": ["weight_pct=2.1", "weight_pct=1.4", "fund_count=707"],
  "counts": { "articles": 0, "rows": 2 },
  "rows": ["(the two ranking dicts, max 8)"]
}
```

**Then `compare_funds` (special):**

- Takes those two rows (must have `weight_pct` or `holding_name`; a fund with no holding is dropped).
- If fewer than two holders, it calls `funds_holding_stock("BHEL")` itself.
- Fetches only `compare_on=holdings` (plus window return if needed).

If the agent set `status=need_tools`, round 2 sees the compare numbers and usually returns `ready` with `tools: []`.

---

### 5.1 Local name peek — when it does fire

Question: `What is the NAV of HDFC Flexi Cap Fund?`

`\bfund\b` matches. Catalog lookup on the **whole sentence** (and any ISIN).

**Possible output:**

```json
[
  {
    "phrase": "",
    "canonical": "HDFC Flexi Cap Fund",
    "ambiguous": false,
    "close_matches": []
  }
]
```

The agent should then set a `fund_scheme` entity and call `fund_nav` with `fund_entity_index: 0`.

**Ambiguous example:** `NAV of HDFC Fund` might return several close matches. After name resolution the engine **stops**:

> Your query matched multiple funds: HDFC Flexi Cap Fund, HDFC Top 100 Fund, …. Please specify the full name or ISIN.

No composer.

---

### 5.2 Agent rules (catalog), in one list

- Smallest set of tools. Do not repeat a tool for data already in observations.
- Later tools should use names earlier tools returned (holdings to news; news sectors to fund ranking).
- News only if they asked what is happening in the market/news. AMC / category / stock / performance screens do **not** need news.
- “Right now” = recent week. Do not set a 1-day window.
- Sentiment `positive` = “who benefits”, **not** “only happy headlines”.
- Affected by a **driver** (crude, rates): news first, then `screen_funds`. **Do not set `sector_name` to “crude”.**
- Prefer `screen_funds` when direction or returns matter.

`enrich_ask_plan` then patches aliases (e.g. `market_pulse` → `common_market_news`) and extra question hints.

---

### 5.3 Standard vs special tools (why the split)

**Standard** (parallel via `execute_tool_round`):  
`fund_nav`, `fund_top_stocks`, `fund_top_sectors`, `holdings_news`, `sector_news`, `macro_news`, `macro_news_enhanced`, `common_market_news`, `screen_funds`, `sector_funds`, `affected_funds`, `metals_spot`, `stock_snapshot`.

**Special** (after standard, same round):  
`compare_funds`, `funds_holding_stock`, `trace_relationships`, `expand_news`, `fund_universe_search`.

| Special tool | Needs already in the bundle |
|--------------|-----------------------------|
| `compare_funds` | Screen / holder rows, or named scheme details |
| `expand_news` | Clusters from `common_market_news` / `macro_news_enhanced` |
| `trace_relationships` | Holdings rows + articles |
| `funds_holding_stock` | Just the stock name (can also run if compare is short of holders) |

---

### 5.4 Gap filler (code, not the model)

Runs **after** the agent loop if:

1. The question looks like it wants **fund names** (`funds`/`schemes` plus benefit / affected / performing / compare / name / which …), **and**
2. No ranking rows exist yet.

| Question | What the filler runs | Why |
|----------|----------------------|-----|
| “name 1 fund heavily invested in banking and positive last month” | `run_screen_funds` with sector=banking, direction=positive, window=1M | Agent forgot the screen, or dedicated banks were all down |
| “name one fund affected by crude news” | `run_funds_for_affected_question` (picker + ranking + company fallback) | Affected-by-driver path, not `sector_name=crude` |
| “whats happening in the market?” | nothing | No fund-name intent |

Hints come from **the question text**, not from the first news company name.

---

### Quick map: question to first agent tools

| User types | Guardrail | Typical round-1 tools | Special later? |
|------------|-----------|----------------------|----------------|
| what’s happening in the market | pass (`market`) | `common_market_news` (+ maybe `macro_news`) | `expand_news` only if they need more bodies |
| two large cap funds | pass (`funds` + large cap) | `screen_funds` category=Large Cap | no |
| NAV of HDFC Flexi Cap Fund | pass; name peek hits catalog | `fund_nav` | no |
| compare two BHEL holders | pass | `screen_funds` stock=BHEL | **yes** `compare_funds` |
| funds affected by crude | pass (`funds` + crude) | news, then `screen_funds` **without** sector=crude | company scan if ranking empty |
| should I buy this fund | advice **flag**, still runs | fund facts; `declined_parts` = buy/sell | no |
| write a python joke | **stop** | none | — |

---
## 6. Layer 3 — Tools: how data is fetched

Every tool returns the same envelope:

```json
{ "ok": true, "data": { ... }, "error": "", "elapsed_ms": 123 }
```

Below: **when it is chosen**, **where data comes from**, **filters**, **output shape**.

### 6.1 `fund_nav`

- **When:** user named a scheme; wants NAV / returns / 52-week range.
- **Needs:** resolved fund detail (`fund_entity_index`).
- **Fetch:** fields already on the fund object; optional `get_fund_nav_history(isin)` from RupeeStop (`/api/nav/{isin}/HISTORY`), cached ~12h in `data/nav_cache/`.
- **Output:** `fund_name`, `isin`, `nav`, `nav_date`, `day_change_pct`, `returns`, `benchmark`, `high_52w`, `low_52w`, `scheme_type`, `category`.

### 6.2 `fund_top_stocks` (alias `fund_holdings`)

- **When:** “what does this fund hold?”
- **Fetch:** `extract_top_holdings(detail, top_n)` from the live/cached fund portfolio API (company, %, industry).
- **Output:** `{ rows: [{ name, percentage, industry, ... }], fund_name }`.
- **Downstream:** holdings names can fill `holdings_news` entity filters.

### 6.3 `fund_top_sectors` (alias `fund_sectors`)

- Same idea as holdings, for sector allocation.
- **Output:** `{ rows: [{ sector, percentage }], fund_name }`.

### 6.4 `holdings_news` / `sector_news` / `macro_news`

These three share `run_layered_news`.

**Fetch path**

1. Embed the search text with **BGE small** (`BAAI/bge-small-en-v1.5`, prefix: “Represent this sentence for searching relevant passages: ”).
2. Search **Qdrant Cloud** collection `news_articles`.
3. Optional entity resolve: user/holding names mapped to names that actually exist in the corpus.
4. Date window: default recent days; `window_days` from the agent is **at least 7**.
5. Optional API filters: `date_from`, `date_to`, `min_impact`, `source`, `direction`.
6. Gold/silver questions may use a dedicated bullion retriever instead of generic macro.

**Layer differences**

| Tool | Search mode | Entities |
|------|-------------|----------|
| `holdings_news` | event + entities | holding names (from filters or top holdings of the named fund) |
| `sector_news` | event + entities | sector names |
| `macro_news` | event only | entities cleared; `semantic_query` should be a few keywords, **not** the full user sentence |

**Output:** `{ articles: [...], count, search_focus }`. Article fields include title, url, body/snippet, direction, sectors, entities, publish date (date is **not** copied into the insight as a newspaper dateline).

If one named fund is in play, execution may also run **`fund_portfolio_news`**: one layered search using that fund’s holdings then sectors then macro. Those articles are merged into the bundle.

### 6.5 `common_market_news` (alias `market_pulse`)

- **When:** “what’s going on in the market?”
- **Fetch:** several themed Qdrant searches (banking, IT, oil, RBI, …), then **cluster** articles into themes.
- **Output:** `{ clusters: [{ label, theme_key, articles, sectors, score }], representative_articles, window_days, published_from, published_to }`.

Composer uses cluster labels and **article bodies**, not titles.

### 6.6 `macro_news_enhanced`

- **When:** one driver (RBI, oil, inflation, FII flows) with clustering inside the tool.
- Same family as market pulse, narrower query.

### 6.7 `expand_news`

- **When:** agent already has clusters and wants more **bodies** for one theme.
- **Fetch:** no new Qdrant call. Walks existing cluster articles, attaches `article_body_for_llm` (~1000 chars).
- **Needs:** `theme` matching a cluster label.

### 6.8 `screen_funds` (main fund picker)

This is the workhorse for “name funds…”, “performing well”, “heavily invested in banking”, “HDFC funds”, “holders of ICICI”.

**Step A — hints from the question** (`screen_hints_from_question`)

Parses, in order:

- **Sector alias:** banking, finance, IT, crude, oil, auto, … (from `_SECTOR_ALIASES`). “crude” as a *driver* is **not** used as Petroleum when the question is “affected by crude” (see affected path).
- **Category:** Large Cap, Mid Cap, Flexi Cap, …
- **Stock:** `hold(s) … stock(s)|shares`
- **AMC token:** words from the catalog, skipping stopwords (`the`, `one`, `any`, `funds`, `sector`, …) so “name one fund” does not become AMC “ONE”.

A **sector written in the question overrides** a model-invented Large Cap category.

**Step B — early exit: affected questions**

If the question matches `question_needs_affected_sectors` (affected/impact/due to + fund/scheme, **not** an exposure-only ask, **no** category/AMC/stock hint) → jump to §6.9.

**Step C — candidate pool**

| Hint | Source |
|------|--------|
| sector | `sector_to_isin_weights.json` ranked by weight (cap 40) |
| category / AMC | catalog `regular-growth-by-amc.md` |
| both | intersection of ISINs |
| stock | archive match + scan of an **industry-capped** batch (see §6.11) |
| none of the above | catalog sample of ~80 schemes (performance list — **not** used as a fallback when a sector screen is empty) |

**Step D — dedicated vs diversified** (`_active_sector_equity`)

For a **sector** screen without category/AMC/stock: keep `dedicated_sectoral` schemes first. If none, keep `diversified_equity` (not arbitrage/hybrid/passive).

**Step E — NAV enrich**

Parallel `get_fund_nav_history` for the pool. Windows: `1W`, `1M`, `3M`, `1Y`.

Filters:

- **Stale NAV:** drop a date more than **45 days** behind the newest date in the same batch.
- **Round** returns to 2 decimals.
- **Direction:**
  - `positive` → keep only window return **> 0**
  - `negative` → keep only **< 0**
  - `any` → no sign filter (except exposure+direction below)
- **Never** list the “least-bad loser” as a beneficiary.

**Step F — sort**

- **Exposure ask** (“heavily invested”, “exposure”, “invested in”) **without** performing/positive/affected: sort by `sector_weight_pct`, direction forced to `any`.
- **Heavy + return** (“heavily invested in banking **and** performing positive last month”): sort by weight, **then** keep only the asked window sign. “Last one month” → `1M`. If dedicated schemes are all down, **retry the same sector ranking** (diversified high-weight funds). **Do not** switch to a large-cap list. **Do not** drop the return filter.
- Otherwise: sort by the window return (performance).

**Output:** `rankings` / `funds` with `fund_name`, `isin`, `sector_weight_pct`, `return_1w_pct`, `return_1m_pct`, …, `ranking_note`, `return_window`, hints echoed back.

Caps: `_SCREEN_CANDIDATE_CAP = 40`, `_PERFORMANCE_SAMPLE = 80`.

### 6.9 Affected-by-driver path (`run_funds_for_affected_question`)

Used for: “which funds are affected by crude?”, “positively affected due to crude”, “funds hurt by the rate hike”.

**Do not** lock crude → Petroleum Products. The news may say banks gain and autos/paints hurt.

**LLM #A — sector picker** (`pick_affected_sectors`)

- **Input:** unique sector **names from our index** (~310 names in `sector_to_isin_weights.json`) + up to 8 article **bodies** + a direction line (only winners / only losers / both).
- **Output JSON:** `{ sectors: [{ name, direction, reason }] }`. Invented names are dropped (must match the list, casefold). Direction tags that do not match the ask are dropped.

If no articles yet, the tool runs **one** `macro_news` search on the question.

**Then ranking**

For each direction group, `run_affected_funds(..., allow_broad_fallback=False)`:

- Rank dedicated funds in those sectors.
- Positive sectors → keep **positive** window returns; negative → declines.
- Default window `1M` unless the question says last week (`1W`).

**If that ranking is empty — LLM #B — company picker** (`pick_affected_companies`)

- **Input:** same articles, same direction: “name companies the articles say are affected.”
- Keep a name only if `_match_aggregated` finds it (substring **or** 3–5 letter initials, e.g. BHEL → Bharat Heavy Electricals Limited; skip words of/and/the so Limited still gives L).
- Scan a capped industry batch; attach holding **weight** and window **return**.
- Those rows become the fund list for the rest of the question (including compare).

**Composer rule:** name a fund only from these ranking rows; you may use each pick’s `reason`.

### 6.10 `sector_funds` / `affected_funds`

Older ranking tools. Same NAV + direction filters. `affected_funds` takes several sector names in one ranking. The catalog tells the agent to **prefer `screen_funds`**. `allow_broad_fallback` on the affected path is **False**, so an empty dedicated list does **not** become random large-caps.

### 6.11 `funds_holding_stock`

**Resolve name**

1. Substring match on `aggregated_holdings_map.json` (“ICICI Bank”).
2. If miss: initials of company words = token (3–5 letters, no spaces) → highest `fund_count` wins. BHEL → Bharat Heavy Electricals Limited, industry Electrical Equipment, count ~707.

**Find schemes**

- If `allisin_sectors_with_holdings.json` exists, scan that file.
- Else: take up to 40 funds from that industry (`holder_candidates_for_stock`). If industry is unknown, last resort is large-cap catalog — only for the scan batch, not as the answer list.
- For each candidate, `lookup_extracted_fund` + **full holdings list** (limit 500, not top 40), in chunks of 8, **stop** when the asked count is found.
- Sort by `weight_pct`.

**Output:** `{ stock_name, industry, fund_count, funds: [{ fund_name, isin, holding_name, weight_pct }], note }`.

Compare of “any two funds that hold X” uses **only** rows with `weight_pct` or `holding_name`. If fewer than two, it calls this scan itself.

### 6.12 `compare_funds`

- **When:** user said compare.
- **Inputs:** named funds (`entity_filters` / entity indexes) **or** `depends_on` a previous `screen_funds` / holders.
- **`compare_on`:** `nav` | `sectors` | `holdings` | `all` — only those blocks are fetched.
- Parallel pack: window return, optional holdings, optional sectors.
- **Output:** `{ funds: [...], count, compare_on, return_window }`.

### 6.13 `fund_universe_search`

- Catalog filter by category / AMC / keyword.
- Use when **no** return direction is needed. Otherwise `screen_funds`.

### 6.14 `metals_spot`

- Reads `data/metals_prices.json` (plus CSV helpers).
- Gold / silver spot moves for commodity questions.

### 6.15 `stock_snapshot`

- `get_stock_profile` (RupeeStop / stocks service) for one `stock_name`.

### 6.16 `trace_relationships`

- **When:** “how does crude hit this fund / sector?”
- **Input:** `driver`, `target`, current holdings rows, sector rows, **already retrieved** articles.
- **Output:** direct (holding / sector weight) vs indirect (names that co-occur in articles). No new vector search.

---

## 7. Layer 4 — Composer (`ask_composer.py`) — LLM #2

This is the only LLM that writes the **user-facing** answer.

### 7.1 Input

**System:** `COMPOSER_SYSTEM` (everyday language, no publisher names, no publication dates, copy numbers exactly, name funds only from matching rows, closing at most two sentences). Extra paragraph if cross-impact / relationships are in the plan.

**User message**

```
Write the final answer from the article bodies and Context. ...
Question:
{user question}

Articles:
{JSON of article bodies, not titles}

Context:
{JSON}
```

**Articles JSON** — bodies via `article_body_for_llm` (titles are labels only).

**Context JSON includes**

- `answer_parts`, `declined_parts`, `question_reading`, `relationships_to_check`, `information_gaps`, `sentiment`
- `fund_nav`, `holdings`, `sectors`
- `tool_results` (slim)
- `ranked_funds` (up to 3, with weights and returns)
- `sector_picks` / ranking notes when present
- `market_pulse_clusters` (labels, counts, sectors — not full bodies)
- `metals_spot`
- `news_article_count`

On a judge retry, a **grounding note** is appended.

**Temperature:** 0.2. **Max tokens:** at least 4096.

### 7.2 Output JSON

```json
{
  "headline": "...",
  "narrative": "...",
  "bullets": ["..."],
  "closing_summary": "...",
  "advice_declined_note": "",
  "format_chosen": "mixed",
  "themes": [{ "name": "", "direction": "", "why_it_matters": "" }],
  "relationships_used": [...],
  "numbers_cited": [{ "label": "", "value": "", "source": "nav|holding|sector|article|metals|rank" }],
  "gaps": ["..."]
}
```

### 7.3 Post-processing (code, after the LLM)

This is where many “blank percent” and “invented fund” bugs are stopped.

- Strip **numbers** that are not in the evidence text. Signed and unsigned cores count as the same (`-1.2` is grounded if `1.2` is in evidence).
- Remove dangling “per cent” with no digit in front.
- Drop generic “stay calm / long-term goals” closings.
- Closing must not repeat every figure.
- Fund naming checks: holder needs weight; positive screen needs positive window return; exposure needs sector weight; `sector_picks` must match ranking sectors.
- Build `display` = headline + narrative + bullets + optional advice note + closing.

If the composer LLM fails, a **deterministic fallback** builds a short answer from pulse representatives / ranking rows.

---

## 8. Layer 5 — Judge (display only)

**Input:** question, draft insight, a short summary of plan + tool keys.

**Scores (0–1):** `answers_query`, `grounded`, `on_topic`, `no_advice`, `no_extra`.

- Prefer **Jev** if configured; else JSON LLM (`JUDGE_FALLBACK_PROMPT`).
- Threshold `judge_min_score` default **0.65**.
- If `grounded` < 0.65 **and** insight is **non-empty** → **one** research retry with note: “The draft was not grounded in the retrieved evidence. Fetch the missing facts, then stop.”
- Empty insight is **not** retried.
- The user **always** sees the latest draft. Scores are for logs / UI, not a hard hide.

---

## 9. How different questions pick different tools

The model chooses tools, except where **hints / pickers override** a wrong large-cap or crude-as-petroleum guess.

### 9.1 “What’s going on in the market?”

Typical tools: `common_market_news` (maybe `sector_news` if they also ask who benefits).

Flow: Qdrant clusters → composer uses **bodies** → headline + theme bullets. No fund ranking unless they also asked for funds.

### 9.2 “What’s going on and which sectors / funds are performing well?”

Round 1: `common_market_news` + `screen_funds` (`direction=positive`, `return_window=1M`, **no** forced Large Cap).

Performing-well does **not** invent a category. Window returns must be **> 0**. Stale NAV dropped.

### 9.3 “Give me any two large cap funds”

Guardrail passes (large cap + funds). Agent: `screen_funds` with `category=Large Cap`, `top_n=2`. **No news.** Catalog → NAV → two names with returns.

### 9.4 “NAV / holdings of HDFC Flexi Cap”

`fund_nav` + `fund_top_stocks` (and maybe `fund_top_sectors`). Name resolution must uniquely match. Ambiguous → ask for full name.

### 9.5 “Compare any two funds that hold BHEL stocks”

1. Hint `stock_name=bhel`.
2. `screen_funds` or `funds_holding_stock`: initials → Bharat Heavy Electricals Limited.
3. Scan full holdings in Electrical Equipment batch.
4. `compare_funds` with `depends_on` / holder rows only (`weight_pct` required).
5. If compare is called with the stock name and fewer than two holders, it runs the holder scan itself.

### 9.6 “Heavily invested in banking and positive last one month”

Hints: sector `banking`, window `1M`, heavy+return → direction `positive`, sort by bank **weight**, keep return **> 0**. Dedicated banking schemes that are down are dropped; a diversified fund with high bank weight and a **gain** is kept. Never a random large-cap list.

### 9.7 “Which funds are affected by crude?” / “positively affected due to crude”

1. Agent: news (`macro_news` or `common_market_news`) then `screen_funds` **without** `sector_name=crude`.
2. `screen_funds` detects affected-question → sector picker LLM on article bodies + official sector list.
3. Rank funds in picked sectors (e.g. Automobiles down, Banks up) with matching window sign.
4. If empty → company picker LLM → holders of named companies.

“Affected” without positive/negative → **both** groups.

### 9.8 “Compare two HDFC large-cap funds” / “compare two funds from the screen”

`screen_funds` first, then `compare_funds` with `depends_on` pointing at that call. `compare_on` = nav / sectors / holdings / all.

### 9.9 Multi-tool, multi-round example

Question: “How does the RBI hike hit HDFC Flexi Cap and which banking funds are up this month?”

Possible rounds:

1. Resolve HDFC Flexi Cap → `fund_nav`, `fund_top_sectors`, `macro_news` (RBI keywords).
2. Observation: fund has Banks weight; articles mention NIM.
3. `trace_relationships` (driver=RBI, target=fund) + `screen_funds` (banking, positive, 1M).
4. Composer uses fund rows + article bodies. Judge may retry once if numbers were invented.

Standard tools in a round run **in parallel**. Special tools wait. The agent must not re-call `fund_nav` if it already has NAV in observations.

---

## 10. Data stores (what each layer reads)

| Store | Used for |
|-------|----------|
| Qdrant Cloud `news_articles` | All news tools. Vectors = BGE small. |
| `data/embedding_models/` | Local BGE weights (~130MB, downloaded on install). |
| `data/fund_holdings_aggregate/regular-growth-by-amc.md` | Fund universe / AMC / category. |
| `data/fund_holdings_aggregate/sector_to_isin_weights.json` | Sector → fund weights (~310 sectors). |
| `data/fund_holdings_aggregate/aggregated_holdings_map.json` | Stock legal names, industry, holder counts, initials. |
| `allisin_sectors_with_holdings.json` (optional, huge, not in git) | Offline full holdings. |
| RupeeStop fund API | Live holdings / sectors when scanning schemes. |
| RupeeStop NAV API | Window returns; cache `data/nav_cache/`. |
| `data/metals_prices.json` | Gold/silver. |
| `.env` | Qdrant, Gemini/DeepSeek keys. |

Not available (must not be invented): expense ratio, AUM, TER, manager, riskometer.

---

## 11. Filters cheat sheet

| Filter | Where | Rule |
|--------|--------|------|
| Advice / prediction | Guardrail | Refuse or strip to `advice_declined_note` |
| Non-finance | Guardrail | Refuse |
| Unknown planner tool | Plan parse | Dropped |
| Ambiguous fund name | Name resolution | Stop; ask user |
| News date window | Layered news | Min 7 days if set; default ~7–30 |
| `min_impact`, `source`, `direction` | API → Qdrant | Optional |
| Sentiment on news | Agent | Who benefits vs who is hurt; **not** “only happy headlines” |
| Sector name vs driver | Affected path | Driver is not a sector key |
| Question sector vs Large Cap | `_args_from_question` | Question wins |
| AMC false positives | `_AMC_SKIP` | the, one, funds, sector, news, … |
| Dedicated sector funds | `_active_sector_equity` | Prefer dedicated; else diversified equity |
| Heavy + return | `select_funds_by_nav` exposure + direction | Weight order AND sign |
| Empty dedicated + heavy+return | `run_screen_funds` | Same sector ranking, not large-cap |
| Positive / negative NAV | Window field | >0 or <0 only; no least-bad losers |
| Stale NAV | Batch dates | Drop if >45 days behind newest |
| Stock match | Archive | Substring then initials 3–5 chars |
| Holdings scan | Scheme detail | Full list cap 500; batch 40 funds; stop at asked count |
| Compare holders | Rows | Must have `weight_pct` or `holding_name` |
| Sector picker names | Official list | Invented names dropped |
| Company picker names | Archive resolve | Else dropped |
| Composer numbers | Evidence cores | Ungrounded digits stripped |
| Composer funds | Ranking rows | Must match ask (weight / sign / sector_picks) |
| Judge grounded | 0.65 | One retry if insight non-empty |

---

## 12. LLM map (every call)

| Stage | Who | Input | Output |
|-------|-----|--------|--------|
| `agent` | Router model | System catalog + briefing blocks | JSON plan + tools |
| `affected_sectors` | JSON LLM | Sector name list + article bodies + direction line | `{ sectors: [{name, direction, reason}] }` |
| `affected_companies` | JSON LLM | Article bodies + direction | `{ companies: ["..."] }` then archive filter |
| `composer` | Composer model | System writing rules + question + article bodies + Context | Headline / narrative / bullets / closing JSON |
| `output_score` / judge | Jev or contract model | Question + draft + short context | Scores 0–1 |

No other LLM writes user-facing prose.

---

## 13. What is passed between layers (one sentence each)

1. **HTTP → engine:** raw question + optional news filters.
2. **Guardrail → agent:** out-of-domain stops; advice is only a flag; otherwise pass.
3. **Agent LLM → code:** JSON plan (entities, tools, gaps).
4. **Plan → name resolver:** phrases → ISINs / details / close matches.
5. **Tools → bundle:** `ok/data` blobs, articles by layer, holdings rows, NAV blob.
6. **Bundle → observations:** slim summaries for the **next agent round**.
7. **Bundle → composer:** full article **bodies** + Context JSON (NAV, rankings, clusters).
8. **Composer → post-process:** JSON answer → grounded display string.
9. **Display → judge:** scores; maybe one more agent+composer cycle.
10. **Engine → HTTP:** insight, sources, research, scores, logs.

---

## 14. Files to open if you are debugging

| File | Role |
|------|------|
| `news_rag/app.py` | `/api/ask` |
| `news_rag/ask_engine.py` | Orchestrates agent → composer → judge |
| `news_rag/ask_agent.py` | Tool choice, briefing, gap filler, special tools |
| `news_rag/ask_execution.py` | Parallel standard tools, article merge |
| `news_rag/ask_plan.py` | Allowed tools, `PlannedTool` fields |
| `news_rag/tools.py` | Screen, news, NAV select, compare helpers |
| `news_rag/affected_sectors.py` | Sector/company pickers |
| `news_rag/stock_fund_ranking.py` | BHEL-style resolve and holder scan |
| `news_rag/sector_fund_ranking.py` | Sector aliases and weight index |
| `news_rag/ask_composer.py` | Final answer + grounding |
| `news_rag/guardrails.py` | Refuse rules |
| `news_rag/llm_client.py` | Gemini / DeepSeek |
| `data/rag_query_logs/ask_*.log` | One file per live question |

Read a log top to bottom: `QUESTION` → `agent` tools → `tool_done` → `COMPOSER` → `JUDGE` → `RESULT`. That is the same order as this document.
