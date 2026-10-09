# Run historical news backfill with Cloudflare

The ingest pipeline (`python -m news_pipeline.backfill_days`) is **heavy Python**: ~500+ Google RSS passes, Jev, scraping, local Hugging Face embeddings, and writes to **Qdrant Cloud**. That cannot run inside a normal **Cloudflare Worker** (CPU/time limits, no full CPython + torch stack).

What Cloudflare **is** good for here:

| Piece | Where it runs |
|--------|----------------|
| **Actual backfill** | **GitHub Actions** (`historical-news-backfill.yml`) or a **VM** (Lightsail) |
| **Schedule / HTTP trigger** | **Cloudflare Worker** in this folder (starts GitHub Actions) |
| **Public RAG website** | Your **VM** behind **Cloudflare DNS + proxy** (orange cloud) |
| **Optional backup of logs** | **R2** (sync script below) |

Pick **one** backfill runtime (GitHub Actions is simplest if you already use it).

---

## Path A — Recommended: Cloudflare Worker triggers GitHub Actions

You keep running the pipeline on GitHub (artifacts, cache, 6h timeout). Cloudflare only **starts** the workflow on a cron or when you `POST /trigger`.

### 1. GitHub secrets (repo → Settings → Secrets and variables → Actions)

Already required by the workflow:

- `QDRANT_URL`, `QDRANT_API_KEY`
- `JEV_BASE_URL`, `JEV_API_KEY`

No change needed if daily ingest already works.

### 2. GitHub PAT for the Worker

Create a **fine-grained** token (GitHub → Settings → Developer settings → Fine-grained tokens):

- Repository: `Geetesh-Jangir/qdrant_db`
- Permissions: **Actions** = Read and write, **Contents** = Read (metadata)

Copy the token; you will set it as `GITHUB_PAT` in Cloudflare (step 5).

### 3. Cloudflare account

- Sign in at [dash.cloudflare.com](https://dash.cloudflare.com)
- Workers & Pages → **Workers** (paid plan not required for this small Worker; cron triggers need Workers on a paid plan — if you are on free, skip cron and use manual `POST /trigger` only)

### 4. Install Wrangler locally

```bash
npm install -g wrangler
wrangler login
```

### 5. Deploy the trigger Worker

```bash
cd deploy/cloudflare/worker
npm install
cp .dev.vars.example .dev.vars
# Edit .dev.vars: GITHUB_PAT, optional BACKFILL_TRIGGER_SECRET
wrangler secret put GITHUB_PAT
wrangler secret put BACKFILL_TRIGGER_SECRET
```

Edit `wrangler.toml` **vars** if needed (`BACKFILL_START`, `BACKFILL_END`, `HOLDINGS_LIMIT`, `SECTORS_LIMIT`).

```bash
npm run deploy
```

Note the Worker URL, e.g. `https://news-backfill-trigger.<account>.workers.dev`

### 6. Run a backfill

**Manual (with secret):**

```bash
curl -sS -X POST "https://news-backfill-trigger.<account>.workers.dev/trigger" \
  -H "Authorization: Bearer YOUR_BACKFILL_TRIGGER_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"start_date":"1/10/2026","end_date":"2/10/2026","holdings_limit":"500","sectors_limit":"50","pause_sec":"600"}'
```

**Cron:** default in `wrangler.toml` is `0 3 * * 0` (Sundays 03:00 UTC). Change `[triggers] crons` to your preference.

### 7. Download results

GitHub → **Actions** → run → artifacts:

- `news-YYYY-MM-DD` — per day: `run.log`, `run_summary.json`, `day_report.json`, `publisher_stats.json`, …
- `backfill-checkpoint`, `news-failure-ledger`

---

## Path B — Run backfill on a VM (Lightsail) + Cloudflare in front of RAG

Use this if you want ingest **off GitHub** but still use Cloudflare for DNS/proxy on the ask UI.

### 1. Server

Same as [deploy/lightsail/DEPLOY.md](../lightsail/DEPLOY.md): Ubuntu 2 GB+, clone repo to `/opt/news-rag`, `.env` with Qdrant + Jev + `PYTHONPATH`.

Add pipeline variables to `/opt/news-rag/.env`:

```env
NEWS_CORPUS_MODE=true
RETENTION_DAYS=0
HOLDINGS_LIMIT=500
SECTORS_LIMIT=50
JEV_BASE_URL=...
JEV_API_KEY=...
```

### 2. Install pipeline venv (once)

```bash
cd /opt/news-rag
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python scripts/download_embedding_model.py
```

### 3. Install backfill runner

```bash
sudo bash deploy/lightsail/install-backfill.sh
```

### 4. Run one range

```bash
sudo BACKFILL_START=1/10/2026 BACKFILL_END=2/10/2026 \
  systemctl start news-backfill.service
journalctl -u news-backfill.service -f
```

Outputs: `/opt/news-rag/data/news_runs/YYYY-MM-DD/` (same files as GitHub artifacts).

### 5. Point your domain at Cloudflare (RAG only)

1. Add site in Cloudflare → import DNS.
2. **A record** `ask` (or `@`) → Lightsail public IP, **Proxied** (orange cloud).
3. SSL/TLS → **Full** or **Full (strict)**.
4. On the server, use nginx from `deploy/lightsail/install.sh` (port 80).

The backfill does **not** need a public URL; only the RAG app does.

### 6. Optional: Worker triggers the VM instead of GitHub

If you add a small authenticated HTTP endpoint on the VM that runs `systemctl start news-backfill.service`, the Worker can `fetch()` that URL instead of GitHub. (Not shipped by default — use Path A or systemd timers on the VM.)

---

## Path C — Optional R2 backup of run data

After a VM backfill, sync logs to R2 (S3-compatible):

```bash
export R2_ACCOUNT_ID=...
export R2_ACCESS_KEY_ID=...
export R2_SECRET_ACCESS_KEY=...
export R2_BUCKET=news-pipeline-data
bash deploy/cloudflare/scripts/sync-news-runs-to-r2.sh
```

Create the bucket in Cloudflare → R2 → Create bucket. Create API token with Object Read & Write.

---

## What each output file is (per calendar day folder)

| File | Purpose |
|------|--------|
| `{run_id}.log` | Full text log |
| `run.log` | Stable copy of the log |
| `{run_id}.json` / `run_summary.json` | Pipeline summary (counts, telemetry, Qdrant) |
| `day_report.json` | Day rollup: Google vs scrape errors, publisher table |
| `publisher_stats.json` | Per-publisher received / scraped / scrape_errors |
| `entity_funnel.json` | Per-entity stage counts |
| `failed_google.json` / `failed_source.json` | Failure ledger slice for that day |

---

## FAQ

**Can the whole pipeline run inside Cloudflare Workers?**  
No — use Actions or a VM. Cloudflare **Containers** (beta) could run the Docker image in theory, but you would still need large memory, persistent checkpoint storage (R2), and careful handling of multi-hour runs; Path A or B is simpler.

**Worker returns 502 from GitHub**  
Check PAT scopes, workflow filename (`historical-news-backfill.yml`), and that `ref` is `main`.

**I only want Cloudflare for the website**  
Deploy RAG on Lightsail, proxy DNS through Cloudflare, and keep using **Actions → Historical news backfill** manually — no Worker required.
