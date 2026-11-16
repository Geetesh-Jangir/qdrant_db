# Market insights

Daily cards live under `ai_insight/`. Shared code is `ai_insight/common/`. Saved JSON is `data/ai_insights/<insight_id>/<YYYY-MM-DD>.json`. A live run writes `<YYYY-MM-DD>.live.json` and does not replace the nightly file.

## What runs

| Module | Command |
| --- | --- |
| FII/DII collector | `python -m ai_insight.fii_dii_flow_narrative.collector --date YYYY-MM-DD` |
| FII/DII narrative | `python -m ai_insight.fii_dii_flow_narrative.run --date YYYY-MM-DD` |
| Market driver | `python -m ai_insight.market_driver_digest.run --date YYYY-MM-DD` |
| Sector leaderboard | `python -m ai_insight.sector_leaderboard.run --date YYYY-MM-DD` |
| Sector index cards | `python -m ai_insight.sector_index_insights.run --date YYYY-MM-DD` |
| Additional findings | `python -m ai_insight.additional_insights.run --date YYYY-MM-DD` |

`--dry-run` prints the facts and stops before the model. `--live` ends the window at the current time.

The page is `/insights` (alias `/market-insights`). Open `/insights?fixture=1` to review the layout without a backend. **Create insights** starts one background job. It always calls NSE FII/DII first (unless the session date is a holiday), updates `data/ai_insight/fii_dii_latest.json`, and appends any new trade date to `data/ai_insights/_data/fii_dii_history.json` without duplicating rows. Cards fill in as each module finishes. Only `status=ok` text is shown. Other statuses say "Not available for this date" (or "Market closed").

## How a card is written

1. Code computes numbers, streaks, and index changes.
2. Haiku (`INSIGHTS_LLM_MODEL`, default `claude-haiku-5-5`) drafts the headline and body from those facts plus the full article text.
3. A second Haiku call checks the draft. If it is unsupported, too long, or unclear, one revise call runs, then an optional re-check (`INSIGHTS_REVERIFY`).
4. The code validator rejects invented numbers, unhedged "because", and banned advice.
5. A failure after retries is logged and saved as `failed`. Gemini and DeepSeek are not used.

## FII/DII history

NSE publishes one day. The collector appends it to `data/ai_insights/_data/fii_dii_history.json`.

```bash
python -m ai_insight.fii_dii_flow_narrative.collector --date 2026-11-16 --import-csv flows.csv
```

CSV columns: `date,fii_buy,fii_sell,fii_net,dii_buy,dii_sell,dii_net`. Dates can be `dd-Mon-yyyy` or ISO. A net that is not buy minus sell is imported and warned. Exit code 3 means the NSE file is not for that trading date yet.

## Logs

Each run writes `data/ai_insights/logs/<date>/<insight_id>/<run_id>/` with `run.log`, `run.jsonl`, the prompts, the evidence articles, and `decision_trace.md`.

```bash
python -m ai_insight.tools.explain --insight fii_dii_flow_narrative --date 2026-11-16
```

The nightly orchestrator writes `data/ai_insights/logs/run_<date>.json`. Logs older than `INSIGHTS_LOG_RETENTION_DAYS` (60) are removed.

## Scheduling

Lightsail **news** ingest cron is 11:40 UTC (`deploy/lightsail/install-daily-cron.sh` only — do **not** install insights cron on Lightsail until you ask). Run insights manually or from the **Create insights** button on `/insights`. Optional later: `deploy/lightsail/install-insights-cron.sh` and `python -m ai_insight.tools.run_daily`. The orchestrator can wait for `data/news_runs_daily/run_summary.json` or a `daily success` / `daily failed` line in `cron/cron.log`.

```bash
python -m ai_insight.tools.run_daily --dry-run
python -m ai_insight.tools.backtest --days 14
```

## Adding an insight

1. New package `ai_insight/<name>/` with `run.py`, `prompt.py`, and a schema. Import only `ai_insight.common`.
2. Compute numbers in code. Pass facts and full articles to `run_quality_loop`.
3. Return an `Envelope` or an `InsightBundle`. Save with `store.save` or `store.save_bundle`.
4. Add the module name to `MODULES` in `ai_insight/jobs.py` and `ai_insight/tools/run_daily.py`.
5. Add a section on the page only if investors should see it. Otherwise leave it in the additional bundle.

## Writing rules

Headline at most 12 words. Body at most 3 sentences and 55 words. Numbers in chips and charts. The body explains why, hedged, and only from the facts or the cited articles. No advice and no predictions.

## Config

| Env | Default | Meaning |
| --- | --- | --- |
| `INSIGHTS_LLM_MODEL` | `claude-haiku-5-5` | Model for every insight call |
| `INSIGHTS_LLM_RETRIES` | 3 | Transport retries before a hard failure |
| `INSIGHTS_REVERIFY` | true | Second check after a revise |
| `INSIGHTS_MAX_PROMPT_CHARS` | 600000 | Drop whole articles above this, never trim one |
| `INSIGHTS_MAX_INGEST_AGE_HOURS` | 24 | If the newest `scraped_at` in the window is older than this, the card is **degraded** (matches once-daily ingest) |
| `INSIGHTS_ALLOW_PRICE_ONLY` | true | A sector card may say the reason is unclear |
| `INSIGHTS_SHOW_ADDITIONAL` | true | Show the Beta section |
| `INSIGHTS_PUBLIC` | true | `false` also requires `INSIGHTS_ADMIN_TOKEN` |
| `INSIGHTS_ALLOW_GENERATE` | true | Hide the button when false |
| `INSIGHTS_STREAK_HIGH_DAYS` | 3 | Prominence threshold |
| `INSIGHTS_RATIO_HIGH` | 1.5 | Prominence vs 20-day average |
| `INSIGHTS_LIVE_PARALLEL` | 3 | Modules at once for the button |
| `INSIGHTS_NEWS_WINDOW_DAYS` | 7 | News scroll window for retrieval |
| `INSIGHTS_BODY_MAX_WORDS` | 110 | Prose validator body limit |
| `INSIGHTS_LOG_FULL_PROMPTS` | false | Store full prompts in run logs |
| `INSIGHTS_FAILURE_WEBHOOK_URL` | empty | Off until set |

## Manual page check

With `?fixture=1`: an ok market card, an ok flow card with bars, a skipped sector card ("Market closed"), a sector candle card, and a Beta additional card. Keyboard: the date arrows and Create insights are buttons. Charts have an `aria-label`.
