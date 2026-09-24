# News pipeline — project context

Use this document when changing the repo, debugging runs, or onboarding an agent.

## Purpose

Daily **English India financial news** pipeline for Rupeestop fund research:

1. Build a **search universe** from top mutual-fund **holdings** and **sectors** (Accord labels).
2. Fetch **Google News RSS** (24h window, allowlisted publishers).
3. **Dedupe** URLs/titles, skip URLs already in Qdrant.
4. **Jev (System One)** screens titles, then scrapes bodies and scores articles.
5. **Embed** (local Hugging Face `BAAI/bge-small-en-v1.5`) and **upsert** one Qdrant point per canonical URL.
6. **Retention** drops old points.

Entry point:

```bash
python -m news_pipeline
```

Inspect Qdrant:

```bash
python scripts/inspect_qdrant.py
```

Regenerate holdings/sectors from Rupeestop fund API (~1800 ISINs):

```bash
python scripts/aggregate_fund_holdings.py
```

Report sectors missing Google query mappings:

```bash
python scripts/report_sector_query_gaps.py
```

## Data sources

### Rupeestop fund API

`GET https://backend.rupeestop.com/api/v1/app/fund/{ISIN}`

- Holdings: `data.portfolio.holdings[]` with `instrument_name`, `percentage`, **`industry`** (Accord sector for that stock).
- Used by `scripts/aggregate_fund_holdings.py` with ISIN list `data/direct_plan_growth_isins.txt`.

### Aggregate files

| File | Role |
|------|------|
| `data/fund_holdings_aggregate/aggregated_holdings.csv` | `instrument_name`, `industry`, `total_percentage`, `fund_count` |
| `data/fund_holdings_aggregate/aggregated_holdings_map.json` | Per name: `{ industry, total_percentage, fund_count }` |
| `data/fund_holdings_aggregate/aggregated_sectors.csv` | Sector rollups for universe |

### Universe (`news_pipeline/sources/universe.py`)

- **`holdings_limit`** (default 5) top names from CSV.
- **`sectors_limit`** (default 5) from `aggregated_sectors.csv`, only if sector name exists in **`SECTOR_QUERIES`** (`config.py`).
- Each entity dict: `name`, `type` (`holding` \| `sector`), **`industry`**, `query`, `aliases`, `fund_count`, …
- **Holdings**: Google query `"Short Name"`; ambiguous names get `"{name}" {hint} India` using sector hint.
- **Sectors**: top `sectors_limit` rows that match `SECTOR_QUERIES`.

## LangGraph pipeline

`news_pipeline/graph/build.py`:

```
load_universe → fetch_google_news (+ macro) → skip_known_urls → dedupe_and_alias
→ jev_title_screen → scrape_bodies → jev_article_scores → embed_and_upsert → drop_old_points
```

State: `entities`, `candidates`, `counts`, `errors`, `llm_usage`.

### Google News

- `news_pipeline/sources/google_news.py` — RSS, publisher filter, canonical URL.
- Hits carry `entity_name`, `entity_type`, **`entity_industry`**, `fund_count`.
- Macro pool: `macro_news_enabled`, `macro_news_query` in config.

### Jev

- Client: `news_pipeline/jev/client.py` → POST `JEV_BASE_URL` (e.g. `https://api.typesafe.ai/v1/systemone`).
- Env: `JEV_BASE_URL`, `JEV_API_KEY`, `JEV_MODEL`.
- **Title screen**: one call per entity with all titles; holdings use **name + industry** in instructions and criteria.
- **Body scores**: holdings use industry in about/relevance/impact; `affects_sector` scoped to the holding’s **industry** label.
- **`max_items_per_query`**: `0` = scan full RSS after publisher/time filters (no 20-item stop).
- Thresholds: `title_noul_min`, `about_name_min`, `relevance_min` gate quality; `max_scrape_per_entity` / `max_scrape_per_industry` default **0** (unlimited scrape among title passes).

### Qdrant payload (`news_pipeline/models.py`)

One point per URL. Notable fields:

| Field | Meaning |
|-------|---------|
| `entity_names` | All matched entity display names |
| `industry_names` | Deduped Accord industries from matches |
| `primary_industry` | Lead entity’s industry (by impact/relevance) |
| `holding_names` / `sector_names` | Split by entity type |
| `entities[]` | Per-entity scores including **`industry`** |
| `max_impact`, `max_relevance`, `direction`, `event_type` | Article-level rollups |

Indexed for filter: `entity_names`, `industry_names`, `primary_industry`, `holding_names`, `sector_names`, dates, impact, etc.

Embeddings prefix industries: `"Banks \| It - Software \| {title}\n\n{body}"`.

### Config highlights (`news_pipeline/config.py`)

- `SECTOR_QUERIES` — maps Accord sector label → Google phrase + keyword tuple (legacy; alias gate removed from graph).
- `fresh_start_each_run` / `fresh_start_clear_qdrant` — local dev clears scrape cache and optionally Qdrant.
- Paths: `holdings_csv`, `sectors_csv`, `run_summary_dir`, `qdrant_inspect_dir`.

### Environment (`.env`)

```
QDRANT_URL=
QDRANT_API_KEY=
JEV_BASE_URL=
JEV_API_KEY=
```

## Run artifacts

- `data/news_runs/{run_id}.log` — stage-by-stage log.
- `data/news_runs/{run_id}.json` — counts, errors, LLM usage summary.
- `data/qdrant_inspect/{stamp}.log|json` — sample points from Cloud/local Qdrant.

## CI (GitHub Actions)

Workflows under `.github/workflows/` — RSS-only vs full pipeline; full run needs Qdrant + Jev secrets.

## Conventions for changes

- Keep **industry** on entity dicts end-to-end: universe → Google hit → Jev state → stored `EntityScore.industry` → `industry_names`.
- Sector labels in CSV/API must match **`SECTOR_QUERIES` keys** (case-insensitive) for sector RSS to run.
- Prefer run-log lines over silent behavior; pipeline ops rely on `data/news_runs/*.log`.
- Do not commit `.env` or API keys.

## Related scripts

| Script | Role |
|--------|------|
| `scripts/aggregate_fund_holdings.py` | Pull all ISIN holdings + industries |
| `scripts/inspect_qdrant.py` | Sample collection payloads |
| `scripts/report_sector_query_gaps.py` | Sectors without `SECTOR_QUERIES` |
