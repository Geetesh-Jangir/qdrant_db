import { domainDelaySec, loadConfig, parseDomainDelays } from "./config";
import { DomainPacer, type SleepFn } from "./domain-pacer";
import { hostFromUrl } from "./http-fetch";
import type {
  Env,
  FailedSourceItem,
  ScrapeErrorRecord,
  ScrapeErrorsFile,
  ScrapeRunSummary,
  ScrapedArticle,
  ScrapedArticlesFile,
} from "./types";
import { scrapeOneItem } from "./scraper";

export type ScrapeBatchResult = {
  scraped: ScrapedArticle[];
  errors: ScrapeErrorRecord[];
  runSummary: ScrapeRunSummary;
};

function publisherKey(source: string | null | undefined, url: string): string {
  if (source) return source.toLowerCase();
  return hostFromUrl(url) ?? "unknown";
}

function logScrapeEvent(event: Record<string, unknown>): void {
  console.log(JSON.stringify({ type: "scrape_request", ts: new Date().toISOString(), ...event }));
}

function emptyRunSummary(): ScrapeRunSummary {
  return {
    attempted: 0,
    http_200: 0,
    http_401: 0,
    http_403: 0,
    http_429: 0,
    other_http_errors: 0,
    connection_or_timeout: 0,
    articles_parsed_ok: 0,
    articles_extract_thin: 0,
    articles_failed: 0,
    by_publisher: {},
  };
}

function bumpPublisher(
  summary: ScrapeRunSummary,
  pub: string,
  field: "attempted" | "ok" | "http_403",
): void {
  if (!summary.by_publisher[pub]) {
    summary.by_publisher[pub] = { attempted: 0, ok: 0, http_403: 0 };
  }
  summary.by_publisher[pub][field] += 1;
}

function recordOutcome(summary: ScrapeRunSummary, item: FailedSourceItem, result: { ok?: ScrapedArticle; err?: ScrapeErrorRecord }): void {
  summary.attempted += 1;
  const pub = publisherKey(item.source, item.url);
  bumpPublisher(summary, pub, "attempted");

  if (result.ok) {
    summary.http_200 += 1;
    if (result.ok.status === "ok") summary.articles_parsed_ok += 1;
    else summary.articles_extract_thin += 1;
    bumpPublisher(summary, pub, "ok");
    return;
  }

  const err = result.err!;
  summary.articles_failed += 1;
  const st = err.http_status;
  if (st === 401) summary.http_401 += 1;
  else if (st === 403) {
    summary.http_403 += 1;
    bumpPublisher(summary, pub, "http_403");
  } else if (st === 429) summary.http_429 += 1;
  else if (st !== null && st >= 400) summary.other_http_errors += 1;
  if (err.error_code === "FETCH_TIMEOUT" || err.error_code === "NETWORK_ERROR") {
    summary.connection_or_timeout += 1;
  }
}

export async function scrapeItems(
  items: FailedSourceItem[],
  minBody: number,
  env: Env,
  options?: { pacer?: DomainPacer; sleep?: SleepFn },
): Promise<ScrapeBatchResult> {
  const config = loadConfig(env);
  const domainDelays = parseDomainDelays(env.SCRAPER_DOMAIN_DELAYS);
  const pacer = options?.pacer ?? new DomainPacer(options?.sleep);
  const sleep = options?.sleep;

  const scraped: ScrapedArticle[] = [];
  const errors: ScrapeErrorRecord[] = [];
  const runSummary = emptyRunSummary();

  for (const item of items) {
    const url = (item.url || "").trim();
    const host = hostFromUrl(url) ?? publisherKey(item.source, url);
    const delaySec = domainDelaySec(config, host, domainDelays);
    const waitedMs = await pacer.wait(host, delaySec);

    const started = Date.now();
    const result = await scrapeOneItem(item, minBody, config, sleep);
    const durationMs = Date.now() - started;

    if ("ok" in result) {
      scraped.push(result.ok);
      logScrapeEvent({
        publisher: host,
        url,
        http_status: 200,
        duration_ms: durationMs,
        domain_delay_sec: delaySec,
        waited_ms: waitedMs,
        outcome: result.ok.status,
      });
      recordOutcome(runSummary, item, { ok: result.ok });
    } else {
      const err = result.err;
      if (err.domain_delay_sec == null) err.domain_delay_sec = delaySec;
      if (err.duration_ms == null) err.duration_ms = durationMs;
      errors.push(err);
      logScrapeEvent({
        publisher: host,
        url,
        http_status: err.http_status,
        duration_ms: durationMs,
        domain_delay_sec: delaySec,
        waited_ms: waitedMs,
        attempt: err.attempts ?? 1,
        retry_after_sec: err.retry_after_sec ?? null,
        failure_category: err.failure_category ?? null,
        error_code: err.error_code,
        outcome: "failed",
      });
      recordOutcome(runSummary, item, { err });
    }
  }

  logScrapeEvent({ type: "scrape_batch_summary", ...runSummary });
  return { scraped, errors, runSummary };
}

export function summarizeScraped(items: ScrapedArticle[]): ScrapedArticlesFile["summary"] {
  return {
    total_ok: items.filter((i) => i.status === "ok").length,
    total_thin: items.filter((i) => i.status === "extract_thin").length,
  };
}

export function summarizeErrors(items: ScrapeErrorRecord[]): ScrapeErrorsFile["summary"] {
  const byCode: Record<string, number> = {};
  const byStatus: Record<string, number> = {};
  for (const e of items) {
    byCode[e.error_code] = (byCode[e.error_code] || 0) + 1;
    const st = e.http_status == null ? "none" : String(e.http_status);
    byStatus[st] = (byStatus[st] || 0) + 1;
  }
  return {
    attempted: items.length,
    failed: items.length,
    by_error_code: byCode,
    by_http_status: byStatus,
  };
}

export function buildScrapedFile(
  runId: string,
  sourceKey: string,
  items: ScrapedArticle[],
): ScrapedArticlesFile {
  return {
    schema: "cloudflare-scrape/v1",
    generated_at: new Date().toISOString(),
    run_id: runId,
    source_key: sourceKey,
    items,
    summary: summarizeScraped(items),
  };
}

export function buildErrorsFile(
  runId: string,
  sourceKey: string,
  items: ScrapeErrorRecord[],
): ScrapeErrorsFile {
  return {
    schema: "cloudflare-scrape-errors/v1",
    generated_at: new Date().toISOString(),
    run_id: runId,
    source_key: sourceKey,
    items,
    summary: summarizeErrors(items),
  };
}

/** Map prior scrape_errors.json rows (403) back to worker input items. */
export function failedSourceFromErrorRow(row: ScrapeErrorRecord): FailedSourceItem {
  return {
    url: row.url,
    title: row.title ?? undefined,
    source: row.source ?? undefined,
    drop_reason: row.drop_reason ?? "fetch_failed",
    last_error: row.message ?? row.detail,
    retriable: false,
  };
}
