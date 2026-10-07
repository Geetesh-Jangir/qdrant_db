# Data files for Lightsail / production `/api/ask`

These paths are **committed in git** (branch `ask-a-question` or `huge-corpus`). They are **not** downloaded at install time except the embedding model.

## Required (install fails without them)

| File | Purpose |
|------|---------|
| `data/fund_holdings_aggregate/sector_to_isin_weights.json` | Sector exposure ranking (~310 sectors → fund weights) |
| `data/fund_holdings_aggregate/regular-growth-by-amc.md` | Fund universe catalog (~2,194 schemes) |
| `data/fund_holdings_aggregate/aggregated_holdings_map.json` | Stock name → industry + holder count; initials match (e.g. BHEL) |
| `data/metals_prices.json` | Gold/silver context in answers |
| `data/direct_plan_growth_isins.txt` | ISIN list used when rebuilding holdings aggregates |

Verify on the server:

```bash
python3 scripts/verify_rag_deploy_data.py
```

## Optional (larger / built locally)

| File | Purpose |
|------|---------|
| `data/fund_holdings_aggregate/allisin_sectors_with_holdings.json` | Full offline holdings map (very large; not in git) |
| `data/fund_holdings_aggregate/portfolio_allisin_holdings.json` | Small subset from `scripts/build_portfolio_allisin_subset.py` |
| `data/fund_name_embeddings.json` | Faster fuzzy fund-name match (`scripts/build_fund_name_embeddings.py`) |

If no local holdings JSON exists, **stock holder scans** call the RupeeStop fund API at runtime (needs outbound HTTPS). NAV history uses `https://backend.rupeestop.com/api/nav/{isin}/HISTORY` with cache under `data/nav_cache/`.

## Never commit

- `.env` (secrets)
- `data/embedding_models/` (run `scripts/download_embedding_model.py` on install)
- `data/qdrant_storage/` (use Qdrant Cloud; set `QDRANT_URL` in `.env`)
- `data/nav_cache/`, `data/rag_query_logs/`

## News corpus

Articles live in **Qdrant Cloud** (`QDRANT_COLLECTION`, default `news_articles`). Ingest separately via `news_pipeline` or CI — not bundled in this repo.
