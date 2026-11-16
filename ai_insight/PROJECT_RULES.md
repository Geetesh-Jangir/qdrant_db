# Tier 1 Investor Insights (RupeeStop) — canonical spec

These rules apply to every task in the Tier 1 insights series. Agents must follow `.cursor/rules/tier1-investor-insights.mdc` when touching `ai_insight/` or `data/ai_insights/`.

## Workflow rules

1. For every task: FIRST inspect relevant existing code, THEN write a concise implementation plan (files to create/modify, function signatures, data flow, test list, risks), THEN STOP and wait for approval. Do not write code before approval.
2. After approval: implement exactly the approved plan. No unrelated refactors. Do not change news ingestion (`news_pipeline/*`) or Qdrant payload/indexes in this project.
3. Reuse existing code (listed below). Do not duplicate logic. If an existing function is unsuitable, say why in the plan.
4. Every module gets unit tests under `tests/`. Run the tests you wrote and report results.
5. When unsure about existing behavior, read the code and cite paths in the plan.

## The 3 insights (independent modules)

1. **Daily Market Driver Digest** — why markets moved (Nifty move, top macro theme, FII/DII colour, one practical implication).
2. **FII/DII Flow Narrative** — today’s flow, streak, news-backed reason.
3. **Sector Sentiment Leaderboard** — most positive and negative sector, story behind each.

**Independence:** Each insight has its own package, schema, LLM prompt, entrypoint, output file, and failure handling. Import only from `ai_insight/common/`. One insight failing must not affect another.

## Hard architecture

- Code computes all numbers; the LLM writes short prose from a `facts` JSON only and may NOT introduce numbers, companies, or events not in `facts` or cited news.
- No DB for v1: JSON under `data/ai_insights/` via `ai_insight/common/store.py` (save/load/exists/list).
- v1 reads existing Qdrant collection `news_articles`; explode `entities[]` and gate per entity (do not trust top-level `max_relevance`, `max_impact`, `direction`). Coarse server filter on indexed fields only (`published_at`, `entity_names`, `sector_names`).
- Sectors: 30 pipeline names from `SECTOR_QUERIES` / `load_sectors`. Display names are cosmetic only.
- Macro: 19 `Macro - X` entities; FII/DII “why” prefers `Macro - Rupee / USD`, `Macro - Bond Yields`, `Macro - FII DII Flows`, `Macro - Crude Oil`, `Macro - RBI Repo Rate`, `Macro - Geopolitical Risk`, `Macro - Tariffs & Trade`.
- Time: IST-aware; storage UTC ISO `Z`. Session window = previous trading day 15:30 IST → run cutoff. Run insight jobs AFTER Lightsail ingest (17:10 IST cron).

## Output envelope (`ai_insight/common/schemas.py`)

```json
{
  "insight_id": "market_driver_digest | fii_dii_flow_narrative | sector_leaderboard",
  "trading_date": "YYYY-MM-DD",
  "as_of_ist": "ISO8601 with +05:30",
  "status": "ok | degraded | skipped | failed",
  "skip_reason": null,
  "prominence": "normal | high",
  "headline": "<= 12 words, plain English, no jargon",
  "body": "<= 3 sentences AND <= 55 words total",
  "chips": [{"label": "Nifty 50", "value": "-0.61%", "tone": "negative"}],
  "viz": {"type": "diverging_bars | flow_bars | index_move", "data": {}},
  "sources": [{"title": "", "url": "", "source": "", "published_at": ""}],
  "facts": {},
  "meta": {"model": "", "prompt_version": "v1", "window_utc": ["", ""], "cluster_ids": [], "validation": {}}
}
```

## Writing-style contract

- Headline + body ≤ 55 words, ≤ 3 sentences; every sentence adds new information.
- Plain English; numbers in `chips`/`viz`; body explains WHY from news.
- 1–3 `sources` from cited clusters; no unsupported cause claims.
- No advice, targets, or predictions; hedge implications.
- No forced explanation — use `degraded` or plain uncertainty when news does not support a cause.

## States

| Status | Meaning |
|--------|---------|
| `ok` | Complete, validated, show to investors |
| `degraded` | Numbers OK, news/validation weak — save, do not show |
| `skipped` | Non-trading day, thin data, stale external data |
| `failed` | Exception with traceback summary |

## Reuse map

| Concern | Module |
|---------|--------|
| LLM JSON | `news_rag/llm_client.py` → `call_json_llm` |
| Clustering | `news_rag/market_pulse.py` |
| Qdrant read | `news_rag/qdrant_reader.py` |
| Market / FII-DII numbers | `ai_insight/data/yfinance_source.py`, `nse_fii_dii.py`, `run.py` |
| Number grounding ideas | `news_rag/insight/grounding.py` |
| Time / ISO | `news_pipeline/textutil.py` |
| HTTP | `lib/fetch.py`, `lib/google_guard.py` |
| API / UI | `news_rag/app.py`, `news_rag/static/` |
| Deploy | `deploy/lightsail/` |

## Layer split

- **`ai_insight/data/`** — deterministic numeric snapshots (`data/ai_insight/*.json`).
- **`ai_insight/<insight>/`** — daily insight modules. Shared code is `ai_insight/common/`. Outputs stay under `data/ai_insights/`.