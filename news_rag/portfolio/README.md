# Investor portfolio layer

Optional integration with RupeeStop admin **workspace** API for “my portfolio” Q&A.

## Environment

| Variable | Purpose |
|----------|---------|
| `CLIENT_REF_NO` | **Required for portfolio Q&A.** CRN (e.g. `CRN-…`). Empty = catalog-only RAG. |
| `RUPEESTOP_BACKEND_BASE` | Default `https://backend.rupeestop.com` |
| `RUPEESTOP_ADMIN_TOKEN` | Optional Bearer if your environment requires auth on workspace GET |
| `PORTFOLIO_TTL_SEC` | In-process cache TTL (default 180) |
| `PORTFOLIO_HTTP_TIMEOUT_SEC` | HTTP timeout (default 15) |
| `PORTFOLIO_HTTP_RETRIES` | Retries on 502/503/504 (default 1) |
| `PORTFOLIO_FIXTURE_PATH` | Optional override: local workspace JSON instead of HTTP |
| `RAG_USE_PLANNER_WHEN_PORTFOLIO` | When CRN set, skip slot router (default true) |

**Load order:** explicit `PORTFOLIO_FIXTURE_PATH` → `data/portfolios/{CLIENT_REF_NO}.json` → if `RUPEESTOP_ADMIN_TOKEN` is empty, `data/workspace_sample.json` (local dev) → live workspace HTTP for that CRN.

## Deployment

- **Single uvicorn worker:** in-process TTL cache is enough.
- **Multiple workers:** each worker has its own cache; set `PORTFOLIO_FIXTURE_PATH` only in test. For shared cache, extend `cache.py` with Redis (not enabled by default).

PII (PAN, email, mobile, address, account numbers) is stripped before any LLM-facing payload.
