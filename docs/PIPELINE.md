# News pipeline — step by step

This document describes what happens when you run:

```bash
python -m news_pipeline
```

It covers every stage, every filter, and every threshold that is in the code today. Defaults live in `news_pipeline/config.py` (`Settings`). Any of those settings can be overridden by environment variables or `.env` (Pydantic settings: field `title_noul_min` maps to `TITLE_NOUL_MIN`).

A shorter agent context lives in `docs/PROJECT_CONTEXT.md`. This file is the operational walkthrough.

---

## What the pipeline is for

Build a searchable store of **recent English India financial news** tied to:

- **Holdings** — company names that appear most often in Rupeestop mutual-fund portfolios, each with an Accord **industry** (sector label).
- **Sectors** — Accord sector labels that have a hand-written Google News query in `SECTOR_QUERIES`.

For each article that survives, the pipeline stores **one Qdrant point per canonical URL**, with scores per company/sector, industry tags, and a local embedding vector.

External systems:

| System | Role |
|--------|------|
| Rupeestop fund API | Source of holdings + industry (offline aggregate script, not every news run) |
| Google News RSS | Headlines for the last day, India English edition |
| Jev System One (`JEV_BASE_URL`) | Title screen and body scores |
| Local Hugging Face model | Embeddings (`BAAI/bge-small-en-v1.5`, 384 dimensions) |
| Qdrant | Vector + payload store (`collection_name`, default `news_articles`) |

Required env before a run: `JEV_BASE_URL`, `JEV_API_KEY`, and a valid `QDRANT_URL` (plus `QDRANT_API_KEY` for Cloud).

---

## Before the graph starts (`main.py`)

1. Load `Settings` from `.env`.
2. Validate Qdrant settings. Exit if Jev URL or key is missing.
3. Build a run id from UTC time, e.g. `20260923T084251Z`.
4. **Fresh start** (when `fresh_start_each_run` is true, default **true**):
   - Delete scrape cache files under `data/news_scrape_cache`.
   - Delete previous `.log` and `.json` files in `data/news_runs`.
   - If `fresh_start_clear_qdrant` is true (default **true**), **drop and recreate** the Qdrant collection so the run starts empty and URL skip finds nothing.
5. Open `data/news_runs/{run_id}.log`.
6. `ensure_collection()` — create the collection if missing, or add any missing payload indexes.
7. Invoke the LangGraph. The graph is a **straight line**. It does not branch.

After the graph:

- Leftover scrape files are deleted.
- `data/news_runs/{run_id}.json` is written with `counts`, `errors`, `telemetry` (step timings, Jev token usage, estimated input cost).

---

## Threshold and filter catalog

These are the knobs that drop or keep items. Defaults are the values in `config.py` as of this document.

### Universe size

| Setting | Default | What it does |
|---------|---------|----------------|
| `holdings_limit` | 5 | How many top holdings (by `fund_count`) become search entities |
| `sectors_limit` | 5 | How many mapped sectors become search entities |

### Google News fetch

| Setting / rule | Default | What it does |
|----------------|---------|----------------|
| RSS query suffix | `when:1d` | Google “last day” window on the query string |
| Locale | `hl=en-IN&gl=IN&ceid=IN:en` | English India edition |
| `max_items_per_query` | 0 (unlimited) | Stop after this many **kept** items per RSS query. **`0` scans the full feed** after publisher/time/language/https filters |
| `news_window_hours` | 24 | Drop items whose publish time is older than 24 hours. Missing publish time is **kept** at fetch time |
| Clock skew | +15 minutes | Publish time may be up to 15 minutes in the future |
| English title | 80% Latin letters | `is_english_title`: among alphabetic characters, at least 80% must be A–Z / a–z |
| Publisher allowlist | 10 domains | Economic Times, Mint, Business Standard, Moneycontrol, Business Line, Financial Express, Reuters, Bloomberg, CNBC-TV18, NDTV Profit |
| URL | must start with `https://` after canonicalization | Tracking params (`utm_*`, etc.) stripped; `m.` / `amp.` hosts normalized |
| `fetch_workers` | 2 | Parallel RSS fetches |
| RSS throttle | 0.4 seconds | Minimum gap between RSS requests (process-wide lock) |
| `macro_news_enabled` | true | Extra RSS query after entity fetches |
| `macro_news_query` | `India RBI economy markets budget` | The macro search phrase |

### Title dedupe (stage name `dedupe_and_alias`; alias keyword gate is off)

| Setting | Default | What it does |
|---------|---------|----------------|
| `title_similarity` | 80 | RapidFuzz `token_set_ratio` on normalized titles. At or above this, the match is a duplicate |
| Short-title exception | length &lt; 18 | Exact normalized match still counts as duplicate. Fuzzy match is **not** applied when either title is shorter than 18 characters |
| `recent_title_hours` | 48 | Titles already in Qdrant for that entity name, published in the last 48 hours, count as prior titles |

### What stays strict (Qdrant quality)

These gates prevent unwanted articles in the database even when fetch and scrape are wide:

| Gate | Default | Role |
|------|---------|------|
| Publisher allowlist + 24h + English | — | No random sites or old/foreign headlines in the funnel |
| `title_noul_min` | 0.7 | Jev must say the **title** is about this entity and material |
| `about_name_min` | 0.7 | Jev must say the **body** is about this name |
| `relevance_min` | 2 | Body must be at least “about this name” on the 0–4 relevance scale |
| Title dedupe | similarity 80 | Skip near-duplicate headlines per entity |
| Skip URL in Qdrant | — | Do not re-store the same canonical URL |

Scrape volume can be large; **only URLs with at least one entity passing body Jev are upserted**.

---

### Jev title screen

| Setting | Default | What it does |
|---------|---------|----------------|
| `title_noul_min` | 0.7 | Minimum Jev **noul** (0–1) for a title to pass for that entity |
| `max_titles_per_jev_call` | 0 | `0` means send **all** titles for that entity in one call. A positive number keeps only the newest N |
| `max_scrape_per_entity` | 0 (unlimited) | After title Jev, scrape every title with noul ≥ `title_noul_min`. Set a positive number to cap scrapes per entity |
| `max_scrape_per_industry` | 0 (off) | Optional cap on holding scrapes sharing one industry |

### Scrape

| Setting | Default | What it does |
|---------|---------|----------------|
| `scrape_workers` | 4 | Parallel page fetches |
| Scrape retries | 2 | Inside `scrape_one` |
| `min_body_chars` | 400 | Body shorter than this is dropped |
| `news_window_hours` | 24 | Applied again after scrape, using RSS time or scraped date. **Missing date is dropped here** (unlike fetch) |
| Status `fetch_failed` / `resolve_failed` | — | Dropped |

### Jev body scores

| Setting | Default | What it does |
|---------|---------|----------------|
| `body_words` | 2000 | Article text sent to Jev is truncated to this many words |
| `about_name_min` | 0.7 | Minimum noul on “is this about this name?” |
| `relevance_min` | 2 | Minimum relevance **score** (integer 0–4). Level 2 means “about this name but not material”. Levels 0 and 1 fail |
| Impact, direction, event, scope noul | stored, not gated | `impact` 0–3, direction, event type, `affects_stock` / `affects_sector` / `affects_macro` are saved even if low |

### Embed and retention

| Setting | Default | What it does |
|---------|---------|----------------|
| `embed_chars` | 1500 | Characters of body included in the embedding text (after whitespace collapse) |
| `embed_batch` | 32 | Embedding batch size |
| `embedding_dim` | 384 | Must match the model |
| `upsert_batch` | 128 | Qdrant upsert batch |
| `retention_days` | 180 | Delete points whose `published_at` is older than this |
| `QUERY_PREFIX` | `Represent this sentence for searching relevant passages: ` | Prepended on **search** queries only, not on stored document embeddings |

### Relevance scale (body, integer)

| Score | Meaning (`RELEVANCE_LEVELS`) |
|-------|------------------------------|
| 0 | Unrelated to this name |
| 1 | Name is only mentioned in passing |
| 2 | About this name but not material to the outlook (**minimum kept**) |
| 3 | Material to this name today |
| 4 | Major event (results, ban, large order, regulatory action) |

### Impact scale (body, integer, not a hard filter)

| Score | Meaning (`IMPACT_LEVELS`) |
|-------|---------------------------|
| 0 | No impact on the outlook |
| 1 | Color only (small price move, no new fact) |
| 2 | Could move this name today |
| 3 | Likely to move this name |

---

## Offline data (not part of the daily graph)

`python scripts/aggregate_fund_holdings.py` reads every ISIN in `data/direct_plan_growth_isins.txt` and calls:

`GET https://backend.rupeestop.com/api/v1/app/fund/{ISIN}`

From each fund’s `portfolio.holdings[]` it reads `instrument_name`, `percentage`, and **`industry`**.

It writes:

- `data/fund_holdings_aggregate/aggregated_holdings.csv` — columns `instrument_name`, `industry`, `total_percentage`, `fund_count`
- `data/fund_holdings_aggregate/aggregated_holdings_map.json` — per name: industry, totals, fund count
- `data/fund_holdings_aggregate/aggregated_sectors.csv` — sector rollup used to pick sector entities

The daily pipeline **reads those files**. It does not call the fund API.

`python scripts/report_sector_query_gaps.py` lists sectors in the CSV that have **no** entry in `SECTOR_QUERIES` (those sectors never get their own Google query).

---

## Step 0 — Load universe

**Code:** `news_pipeline/graph/nodes/load_universe.py`, `news_pipeline/sources/universe.py`

### Holdings

1. Read `aggregated_holdings.csv`.
2. Group rows that collapse to the same canonical name (strip Ltd/Limited, punctuation, “EQ -” prefixes).
3. Rank by `fund_count` descending, then name.
4. Take the first `holdings_limit` rows.
5. Build aliases (full name, short name, two-word headline form, plus `EXTRA_ALIASES` such as SBI, ONGC).
6. Set `industry` from the CSV (Accord label, e.g. `Banks`).
7. Set the Google query:
   - Normal: `"Short Name"`
   - If the name looks ambiguous (lookalike negatives, or a short name of at most two words and under 22 characters) **and** industry is set: `"Short Name" {hint} India`
   - Hint is the first word of that industry’s `SECTOR_QUERIES` phrase when the industry matches a key (so Banks often becomes `RBI`), otherwise the first word of the industry label.

Each holding entity:

```text
name, type=holding, industry, query, aliases, keywords=[], fund_count, total_percentage
```

### Sectors

1. Read `aggregated_sectors.csv`.
2. Drop names whose lowercase text contains a fragment in `SECTOR_BLOCK_FRAGMENTS`: mutual fund, etf, foreign security, index future, overseas, reit, invit, precious metal, others.
3. Keep the row only if the sector name matches a key in `SECTOR_QUERIES` (case-insensitive). The Google query is the phrase in that map, **not** the raw sector label. Keywords from the map are stored on the entity (they are passed to Jev state; they are **not** used as a pre-filter anymore).
4. Rank sectors by `fund_count` and take `sectors_limit`.
5. Sector `industry` is set to the sector’s own name.

### Logs

The run log lists every entity (`name`, `type`, `industry`, `query`, `fund_count`) and up to 10 sectors that exist in the CSV but have no `SECTOR_QUERIES` mapping.

**Output:** `state.entities`. Count key: `entities`.

---

## Step 1 — Fetch Google News

**Code:** `fetch_google_news.py`, `google_news.py`, `macro_news.py`

For each entity (parallel, `fetch_workers`):

1. Build RSS URL: `https://news.google.com/rss/search?q={query} when:1d&hl=en-IN&gl=IN&ceid=IN:en`
2. Parse `<item>` nodes.
3. For each RSS item in order (when `max_items_per_query` is **0**, scan the **entire** feed; otherwise stop after that many kept items):
   - Strip HTML from the title. Drop empty title or empty link.
   - Drop if the title is not English (80% Latin letters).
   - Parse `pubDate`. Drop if it falls outside `news_window_hours` (missing time is allowed).
   - If the link is a `news.google.com` redirect, try to resolve the publisher URL.
   - Match publisher by host of the source URL or article URL, or by source name when the article host is still Google News.
   - Canonicalize the URL. Drop if it does not start with `https://`.
4. Each kept hit:

```text
url, title, source, published_at, snippet,
entity_name, entity_type, entity_industry, fund_count, total_percentage
```

One entity failing (RSS blocked, timeout) is logged and the run continues.

### Macro fetch

If `macro_news_enabled`, one extra RSS call uses `macro_news_query` and a synthetic entity:

```text
name=Macro, type=macro, industry="", fund_count=0
```

Those hits use the **same** publisher, language, time, and item-cap filters. They are appended to the hit list.

**Output:** `state.candidates` is still a flat list of hits (not yet merged). Counts: `google_items`, `macro_items`.

---

## Step 2 — Merge URLs and skip known points

**Code:** `skip_known_urls.py`

1. Group hits by canonical URL.
2. Each group becomes one candidate with a `matches` list. A match is one entity that returned that URL. Duplicate entity names on the same URL are not added twice.
3. If titles differ, the **longer** title is kept. The longer snippet is kept. The first non-empty publish time is kept.
4. Compute a stable point id: UUID5 of the URL.
5. Ask Qdrant which of those ids already exist.
6. Drop candidates whose id is already stored.

On a fresh start that cleared Qdrant, this skip count is zero.

**Counts:** `merged_urls`, `skipped_existing`. Log also records `multi_entity_urls` (one article matched more than one entity at fetch time).

---

## Step 3 — Title dedupe

**Code:** `dedupe_and_alias.py`

The historical “alias gate” (require a company alias or sector keyword in the title) is **off**. Jev decides whether a title is about the entity.

What this stage still does:

1. For each universe entity, load titles already in Qdrant where `entity_names` contains that name and `published_at` is within `recent_title_hours` (cap 200 titles).
2. Sort today’s candidates newest first.
3. For each candidate, for each match:
   - Normalize the title (lowercase, strip a trailing “ - Publisher” style suffix, keep letters and digits).
   - Compare to prior titles for **that entity only** (Qdrant recents, then titles already accepted earlier in this run).
   - Drop the match if normalized titles are equal, or if both are at least 18 characters and fuzzy ratio ≥ `title_similarity`.
4. If every match on a URL is dropped, the URL is dropped.

**Counts:** `after_alias` (URLs entering this stage; name is historical), `after_title_dedupe`, `title_dedupe_dropped`.

---

## Step 4 — Jev title screen

**Code:** `jev_titles.py`, `jev/client.py` (`title_questions`)

### Which titles each entity sees

For each non-macro entity, one Jev call contains:

- Every remaining candidate that already has a match for that entity (from that entity’s RSS).
- Plus every candidate that has a **macro** match, if that URL is not already in the list.

Titles are sorted newest first. If `max_titles_per_jev_call` &gt; 0, only the first N are sent.

### What is sent to Jev

One HTTP POST:

```text
model: jev_model (default jev-latest)
state: { name, type, industry, aliases, keywords }
questions: { t0, t1, ... }
```

Each question is type **`noul`** (a 0–1 confidence, not a 0–4 score).

**Holding instructions (shape):**

> Title: {headline}. Is this headline specifically about {name}. The company is in the {industry} sector (Accord industry label). and material enough to change the stock outlook? False for a price recap, a technical call, a generic market wrap, a different company, or a story clearly about another industry.

Criteria true/false repeat the company and industry when industry is set.

**Sector instructions (shape):**

> Title: {headline}. Is this headline about the {name} sector as a whole, or about policy that moves that sector? False when the headline is only about one company, or when it is a price recap.

The headline is inside the question. Entity context (including industry and aliases) is in `state`.

### How the number is used

1. Read `answers[tN].noul` (or `probability`), clamp to 0–1. That value is the title score for `(article index, entity name)`.
2. Log `pass` if score ≥ `title_noul_min`, else `fail`.
3. A direct (non-macro) match is kept in the scored set only if its noul ≥ `title_noul_min`. The score is stored as `title_relevance`.
4. A macro article is attached to **every** entity whose noul on that title passed the threshold, with that entity’s industry and fund stats. The original Macro match is not stored as a scored entity.
5. Per entity, sort passing titles by noul descending.
6. Select for scrape: every title with noul ≥ `title_noul_min` (when `max_scrape_per_entity` is **0**). Optional positive caps: `max_scrape_per_entity`, `max_scrape_per_industry`.
7. A URL continues only if at least one `(url, entity)` pair was selected.

Industry pass/fail totals are logged as `industry_stats`.

**Count:** `after_title_jev` = number of unique URLs still in the candidate list.

---

## Step 5 — Scrape bodies

**Code:** `scrape_bodies.py`, `scrape/engine.py`

Each remaining URL is fetched in parallel (`scrape_workers`).

A candidate is **dropped** when:

| Reason | Rule |
|--------|------|
| `no_record` | Scrape raised or returned nothing usable |
| `fetch_failed` / `resolve_failed` | Engine could not get the page |
| `short_body` | Stripped text length &lt; `min_body_chars` (400) |
| `outside_news_window` | No publish time, or time outside the last `news_window_hours` (and not more than 15 minutes in the future) |
| `empty_title` | Neither RSS title nor scraped title |

Kept candidates gain `scraped_text`, `scraped_at`, a normalized `published_at`, and possibly a filled-in title.

**Count:** `scraped`.

---

## Step 6 — Jev article (body) scores

**Code:** `jev_articles.py`, `article_questions` in `jev/client.py`

**One Jev call per scraped URL** (not per entity).

### State

```text
title, source, published_at,
entities: [ { name, type, industry, aliases }, ... ],
article: first body_words words of the scraped text
```

### Questions per matched entity (prefix `e0`, `e1`, …)

| Key | Type | What it asks |
|-----|------|----------------|
| `_about` | noul | Is the body about this company (and its industry) or this sector? |
| `_relevance` | score 0–4 | Relevance scale above |
| `_impact` | score 0–3 | Impact scale above |
| `_direction` | choice | positive, negative, neutral, unclear |
| `_event` | choice | results, order, deal, regulatory, operations, macro, opinion, price_recap |
| `_stock` | noul | Affects this company or stock |
| `_sector` | noul | Affects this company’s Accord industry, or the sector as a whole for sector entities |
| `_macro` | noul | Affects macro backdrop (RBI, crude, rupee, Fed, budget, flows) |

Holding questions mention the industry in the about / relevance / impact wording when industry is set.

### Hard filters (per entity on that URL)

1. `about_this_name` (the `_about` noul) must be ≥ `about_name_min` (0.7).
2. `relevance` must be ≥ `relevance_min` (2).

Impact, direction, and event type do **not** drop the match. They are stored.

If no entity on the URL passes, the URL is dropped (`no_entity_passed`). A Jev HTTP error drops that URL and is recorded in `errors`.

**Count:** `after_body_jev`.

---

## Step 7 — Embed and upsert

**Code:** `embed_upsert.py`, `embeddings/encoder.py`, `storage/qdrant_store.py`, `models.py`

For each surviving candidate, build a `StoredArticle`:

| Field | How it is chosen |
|-------|------------------|
| `entities[]` | One `EntityScore` per passing match, including `industry` and `title_relevance` |
| `entity_names` | All those names |
| `holding_names` | Names whose type is `holding` |
| `sector_names` | Names whose type is `sector` |
| `industry_names` | Sorted unique non-empty industries |
| `primary_industry` | Industry of the lead entity (highest impact, then relevance, then about-noul). If that is empty, the first industry in the sorted list |
| `max_relevance` / `max_impact` | Max across entities |
| `direction` / `event_type` | Taken from the lead entity |

Embedding text:

```text
{industry_names joined by " | "} | {title}

{first embed_chars of the body}
```

Vectors are L2-normalized cosine embeddings, batch size `embed_batch`.

Upsert uses point id = UUID5(url), payload = the full article model (including `scraped_text`). Batch size `upsert_batch`.

Payload indexes (created on the collection): `published_at`, `scraped_at`, `entity_names`, `industry_names`, `primary_industry`, `holding_names`, `sector_names`, `source`, `max_relevance`, `max_impact`, `direction`, `event_type`.

After a successful upsert, scrape files for those URLs are removed.

**Counts:** `upserted`, `scrape_files_removed`.

Listing and semantic search can filter by `entity_names` and `industry_names`. Default list/search still requires `max_relevance` ≥ 2.

---

## Step 8 — Drop old points

**Code:** `drop_old_points.py`

Delete every point whose `published_at` is strictly older than `retention_days` (default 180). If `retention_days` is 0 or less, nothing is deleted.

**Count:** `deleted`.

---

## What a stored point is useful for

After a run you can:

- Filter articles that mention a company (`entity_names` / `holding_names`).
- Filter articles tagged with an Accord industry (`industry_names`, `primary_industry`), including companies in that industry and sector-level matches that used the same label.
- Rank by `max_impact` and `max_relevance`.
- Semantic search with `NewsStore.semantic_search` (query text gets the BGE query prefix).

Inspect samples:

```bash
python scripts/inspect_qdrant.py
```

Logs land in `data/qdrant_inspect/`.

---

## Counts you should see in the JSON summary

Typical keys, in pipeline order:

| Key | Meaning |
|-----|---------|
| `entities` | Holdings + sectors loaded |
| `google_items` | Raw hits including macro |
| `macro_items` | Hits from the macro query only |
| `merged_urls` | Unique URLs after merge |
| `skipped_existing` | URLs already in Qdrant |
| `after_alias` | URLs entering title dedupe |
| `after_title_dedupe` | URLs after similar-title drops |
| `title_dedupe_dropped` | URLs removed because every match was a duplicate title |
| `after_title_jev` | URLs selected for scrape |
| `scraped` | URLs with a long enough in-window body |
| `after_body_jev` | URLs with at least one entity passing body thresholds |
| `upserted` | Points written |
| `deleted` | Points removed by retention |

`errors` is a list of stage failures that did not abort the whole run (fetch, Jev, scrape). A failure inside `main` before the summary is written exits with status 1.

---

## Architecture

```text
                    OFFLINE (when holdings change)
                    scripts/aggregate_fund_holdings.py
                    Rupeestop GET /api/v1/app/fund/{ISIN}
                              |
                              v
                    aggregated_holdings.csv  (+ industry)
                    aggregated_sectors.csv
                    aggregated_holdings_map.json

                    DAILY RUN
                    python -m news_pipeline
                              |
                              v
                    [optional fresh start]
                    clear scrape cache, old run logs,
                    optionally delete Qdrant collection
                              |
                              v
              +---------------+----------------+
              |  LangGraph (linear, no branches)
              +---------------+----------------+
                              |
                              v
                    1. load_universe
                       top N holdings + top M sectors
                       industry on every holding
                              |
                              v
                    2. fetch_google_news
                       full RSS per entity (when:1d, English, publishers)
                       no default cap on kept items (max_items_per_query=0)
                       + one macro RSS query
                              |
                              v
                    3. skip_known_urls
                       merge same URL -> matches[]
                       drop UUID already in Qdrant
                              |
                              v
                    4. dedupe_and_alias
                       fuzzy title dedupe per entity
                       vs last 48h in Qdrant and earlier hits
                              |
                              v
                    5. jev_title_screen
                       one System One call per entity, all titles
                       noul >= 0.7 -> scrape (no default scrape cap)
                              |
                              v
                    6. scrape_bodies
                       full text, min length, 24h window
                              |
                              v
                    7. jev_article_scores
                       one call per URL, all entities together
                       about-noul + relevance gates
                              |
                              v
                    8. embed_and_upsert
                       industry-prefixed text -> 384-d vector
                       one point per URL with industry_names,
                       holding_names, sector_names, entity scores
                              |
                              v
                    9. drop_old_points
                       delete published_at older than retention_days
                              |
                              v
                    data/news_runs/{run_id}.log
                    data/news_runs/{run_id}.json
                    Qdrant collection news_articles
```

### Data shape as it moves

```text
entities[]
    name, type, industry, query, aliases, fund_count

hits[]  (after fetch)
    url, title, source, entity_name, entity_industry, ...

candidates[]  (after merge, through scrape)
    url, title, matches[{name, type, industry, title_relevance, ...}],
    scraped_text (after scrape)

StoredArticle  (Qdrant payload)
    url, title, source, scraped_text, published_at,
    entity_names, industry_names, primary_industry,
    holding_names, sector_names,
    entities[{scores}], max_impact, max_relevance, direction, event_type
    + vector
```

### Who decides “keep this article?”

```text
Google + publishers + 24h + English     -> all matching RSS items (no 20 cap)
Qdrant URL id                           -> not already stored
Fuzzy title                             -> not a near-duplicate for that entity
Jev title noul >= 0.7                   -> worth opening (all passes may scrape)
Body >= 400 chars and dated in window   -> readable article
Jev about >= 0.7 and relevance >= 2     -> stored in Qdrant (quality gate)
```

An article can be stored against several entities at once when each entity passes title and body Jev. Many URLs may be scraped in a run; **Qdrant only receives articles that pass body scoring**.
