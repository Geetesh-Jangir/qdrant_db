# `ai_insight` — numeric layer for Tier 1 insights

This package fetches and caches **deterministic market data** (Nifty, FX, FII/DII, macro snapshots). It does **not** generate investor-facing prose.

- Run: `python -m ai_insight.data.run` → writes under `data/ai_insight/`.
- Shared job code lives in **`ai_insight/common/`** (time, Qdrant gate, clustering, market data, Haiku JSON, validation, store, runner).
- Daily insight modules live in **`ai_insight/`** (see `ai_insight/PROJECT_RULES.md`). Outputs go to `data/ai_insights/`.
- Cursor agent rules for this work: `.cursor/rules/tier1-investor-insights.mdc`.