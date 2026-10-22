# Cloudflare failed-source scraper (no R2 / no card)

Scrape URLs from your Lightsail `failed_sources` / `source.json` using a **Cloudflare Worker**, then **save JSON on your PC**. **R2 is optional** (not required).

## Layout

| Path | Purpose |
|------|---------|
| `input/failed_sources.json` | Copy of `news_failures/source.json` |
| `output/scraped_articles.json` | Written by `run-scrape-local.ps1` |
| `output/scrape_errors.json` | Failures with `error_code` + `message` |
| `worker-url.txt` | Your `https://....workers.dev` URL (create from example) |
| `scrape-worker/` | Worker source |
| `scripts/run-scrape-local.ps1` | **Main runner** — batches requests, saves output locally |
| `scripts/run-scrape-403.ps1` | Re-scrape only `http_status=403` rows from `scrape_errors.json` |

## One-time setup (no credit card)

1. `wrangler login`
2. Register **workers.dev** subdomain (dashboard prompt on first deploy):
   [Workers onboarding](https://dash.cloudflare.com/?to=/:account/workers/onboarding)
3. Deploy:

```powershell
cd cloudflare\scrape-worker
npm install
npm run deploy
```

4. Copy the deployed URL into `cloudflare\worker-url.txt` (see `worker-url.txt.example`).

5. Optional: `wrangler secret put SCRAPE_TRIGGER_SECRET` — then pass `-Secret` to the script.

## Prepare input

```powershell
Copy-Item "...\lightsail_logs\news_failures\source.json" `
  "...\cloudflare\input\failed_sources.json"
```

## Run scrape and save on PC

```powershell
cd cloudflare\scripts
.\run-scrape-local.ps1
```

### Retry HTTP 403 failures only

After a full run, re-attempt URLs that returned **403** (one paced try per URL; 403 is not retried in a loop):

```powershell
.\run-scrape-403.ps1 -BatchSize 5 -DelaySec 8
```

Writes:

- `output/scraped_403_retry.json` — recovered articles
- `output/scrape_403_remaining_errors.json` — still failing
- `output/run_403_state.json` — batch `run_summary` from the Worker

Options:

```powershell
.\run-scrape-local.ps1 -WorkerUrl "https://failed-source-scraper.xxx.workers.dev" -BatchSize 10 -MaxItems 50 -DelaySec 2
```

Results:

- `cloudflare\output\scraped_articles.json`
- `cloudflare\output\scrape_errors.json`
- `cloudflare\output\run_state.json`

## How it works

1. PowerShell reads `input/failed_sources.json`.
2. Sends batches to **`POST /run`** with body `{ "items": [ ... ] }`.
3. Worker scrapes on Cloudflare edge and returns `scraped` + `errors` JSON in the response.
4. Script merges all batches and writes files under `output/`.

No R2 upload/download.

## Worker endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | `r2_enabled: false` when no R2 binding |
| POST | `/run` | Body `{ "items": [ { "url": "..." }, ... ] }` (max 25 per request, default 10) |
| POST | `/scrape-inline` | Same as `/run` with items body |

## Optional R2 mode

If you later add a card and enable R2, uncomment `[[r2_buckets]]` in `wrangler.toml`, create the bucket, redeploy, and use `upload-failed-sources.ps1` + GET `/run` without a body.

## Limits

- **~10 URLs per request** (configurable `BATCH_SIZE`, max 25) — Worker CPU/time limits.
- Large ledgers need many batches; use `-DelaySec` to avoid rate limits.
- Extraction is lighter than Python/trafilatura; compare `scrape_errors.json` with Lightsail results.

## Scraper pacing and HTTP handling (Worker)

Within each `/run` batch the Worker processes URLs **sequentially** and enforces a **per-domain delay** (default 5s, min 3s, max 10s). Different publishers do not block each other unless they share the same hostname.

| Status | Behavior |
|--------|----------|
| 200 | Parse HTML; thin extraction still recorded as `extract_thin` error |
| 401 | Logged; **no retry**; `retriable: false` |
| 403 | Logged with bounded body excerpt; **no retry**; not treated as “slow down and try again” |
| 429 | Honors `Retry-After` (capped); else exponential backoff; defers if wait exceeds job cap |
| 5xx | Bounded exponential backoff + small jitter; up to `SCRAPER_MAX_RETRIES` |
| Network / timeout | Bounded backoff; does not abort the batch |

Configure via `scrape-worker/wrangler.toml` `[vars]` or dashboard:

| Variable | Default |
|----------|---------|
| `SCRAPER_REQUEST_TIMEOUT_SECONDS` | 20 |
| `SCRAPER_DEFAULT_DOMAIN_DELAY_SECONDS` | 5 |
| `SCRAPER_MIN_DOMAIN_DELAY_SECONDS` | 3 |
| `SCRAPER_MAX_DOMAIN_DELAY_SECONDS` | 10 |
| `SCRAPER_MAX_RETRIES` | 3 |
| `SCRAPER_BACKOFF_BASE_SECONDS` | 2 |
| `SCRAPER_BACKOFF_MAX_SECONDS` | 30 |
| `SCRAPER_MAX_RETRY_AFTER_SECONDS` | 60 |
| `SCRAPER_DOMAIN_DELAYS` | optional `host=seconds,...` |

Responses include `run_summary` (counts by status and per-publisher 403 rate). Logs: JSON lines with `type: scrape_request` (view with `npm run tail`).

**Deploy after changes:** `cd cloudflare\scrape-worker && npm run deploy`

**Tests:** `cd cloudflare\scrape-worker && npm install && npm test`

**Multi-worker note:** Per-domain pacing applies inside one Worker invocation. Parallel PCs or cron jobs hitting the same publisher can still overlap; use smaller batches and `-DelaySec`, or a single runner for 403 retries.
