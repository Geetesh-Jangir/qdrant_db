# GitHub Actions, secrets, and running pipeline vs RAG

## Two apps (run independently)

| App | Purpose | Local command |
|-----|---------|----------------|
| **News pipeline** | Fetch Google News → Jev → scrape → embed → **write Qdrant** | `python -m news_pipeline` |
| **News RAG** | Read Qdrant only → retrieve → **DeepSeek** → web UI | `uvicorn news_rag.app:app --host 0.0.0.0 --port 8080` |

They share **Qdrant** (`QDRANT_URL`, `QDRANT_API_KEY`, collection `news_articles`) but do **not** import each other. Run the pipeline on a schedule to ingest; run RAG whenever you want to query (locally, VM, or Railway/Fly).

### Local setup (once)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install -r news_rag/requirements.txt
```

Copy `.env` at repo root with secrets (see below). Optional one-time embedding download:

```bash
python scripts/download_embedding_model.py
```

### News pipeline only

```bash
# from repo root, venv active
python -m news_pipeline
```

Portfolio-scoped ingest (holdings ≥ 2%, sectors ≥ 3% in that portfolio; append-only to Qdrant):

```bash
set PORTFOLIO_JSON=investor_data\mohit\portfolio.json
python -m news_pipeline
```

Writes `data/fund_holdings_aggregate/portfolio_news_scope.json` for the RAG fund brief to use the same names.

Logs: `data/news_runs/{run_id}.log` and `{run_id}.json` (kept across runs).

Optional `.env` overrides: `NEWS_WINDOW_HOURS`, `GOOGLE_NEWS_WHEN`, `NEWS_CORPUS_MODE`, etc.

### RAG only

```bash
uvicorn news_rag.app:app --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080`. Fund brief UI: `http://127.0.0.1:8080/fund` (requires `PORTFOLIO_JSON` in `.env`). Logs per question: `data/rag_query_logs/`.

Requires corpus already in Qdrant from at least one pipeline run.

**Insight LLM (`.env`):** default is DeepSeek. For Google Gemini:

```env
RAG_LLM_PROVIDER=gemini
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Restart uvicorn after changing `.env`. `GET /health` shows `llm_provider` and `llm_model`.

---

## Push to GitHub

```bash
git add -A
git status
git commit -m "Your message"
git push origin main
```

Remote for this repo: `https://github.com/Geetesh-Jangir/qdrant_db`

---

## GitHub Actions workflows

| Workflow | Trigger | What it runs |
|----------|---------|----------------|
| **Cloud portfolio news pipeline** | Manual (`workflow_dispatch`) | Portfolio (default Mohit) `python -m news_pipeline` → Qdrant Cloud |
| **Cloud news test** | Manual, mode **rss-only** or **full-pipeline** | RSS test script or full pipeline |
| **Cloud RAG smoke** | Manual | Starts RAG app, one `/api/ask`, uploads RAG query log |

After a run, download **Artifacts** (run logs / RAG log) from the Actions run page.

---

## Repository secrets (Settings → Secrets and variables → Actions)

### Required for **full pipeline** (both cloud pipeline workflows)

| Secret | Example / notes |
|--------|------------------|
| `QDRANT_URL` | `https://….cloud.qdrant.io` |
| `QDRANT_API_KEY` | Qdrant Cloud API key |
| `JEV_BASE_URL` | `https://api.typesafe.ai/v1/systemone` |
| `JEV_API_KEY` | Typesafe / Jev API key |

### Optional for pipeline

| Secret | Default if omitted |
|--------|---------------------|
| `JEV_MODEL` | `jev-latest` (set in workflow env if you add it) |

Workflow env already sets: `FRESH_START_EACH_RUN=false`, `FRESH_START_CLEAR_QDRANT=false`, `NEWS_CORPUS_MODE=true` (full pipeline workflow).

### Required for **RAG smoke** workflow

| Secret | Notes |
|--------|--------|
| `QDRANT_URL` | Same cluster as pipeline |
| `QDRANT_API_KEY` | Same |
| `DEEPSEEK_API_KEY` | If `RAG_LLM_PROVIDER=deepseek` (default) |
| `GEMINI_API_KEY` | If `RAG_LLM_PROVIDER=gemini` |

### Optional for RAG

| Secret | Notes |
|--------|--------|
| `RAG_LLM_PROVIDER` | `deepseek` (default) or `gemini` |
| `DEEPSEEK_MODEL` | e.g. `deepseek-chat` or `deepseek-flash` |
| `DEEPSEEK_BASE_URL` | Default `https://api.deepseek.com` |
| `GEMINI_MODEL` | Default `gemini-3.5-flash-lite` (older `gemini-2.5-flash-lite` may 404 for new keys) |
| `APP_TOKEN` | If set, smoke test sends `X-App-Token` header |

**Do not** commit `.env`. Only store these in GitHub Secrets (and local `.env`).

---

## Suggested order on GitHub

1. Add secrets above.
2. Run **Cloud portfolio news pipeline** (Actions → workflow_dispatch) to fill Qdrant for the default portfolio.
3. Run **Cloud RAG smoke** to verify read + DeepSeek (needs data in collection).

RAG is not a long-running service on GitHub Actions; for a public UI host RAG on a VM/PaaS with the same env vars as local.
