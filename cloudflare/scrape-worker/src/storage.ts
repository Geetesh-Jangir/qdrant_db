import { buildErrorsFile, buildScrapedFile } from "./batch";
import type {
  Env,
  FailedSourcesFile,
  RunState,
  ScrapeErrorsFile,
  ScrapeErrorRecord,
  ScrapedArticlesFile,
  ScrapedArticle,
} from "./types";

export function hasR2(env: Env): boolean {
  return env.SCRAPE_BUCKET !== undefined && env.SCRAPE_BUCKET !== null;
}

const DEFAULT_INPUT = "input/failed_sources.json";
const DEFAULT_SCRAPED = "output/scraped_articles.json";
const DEFAULT_ERRORS = "output/scrape_errors.json";
const DEFAULT_STATE = "output/run_state.json";

export function keys(env: Env) {
  return {
    input: env.INPUT_KEY || DEFAULT_INPUT,
    scraped: env.OUTPUT_SCRAPED_KEY || DEFAULT_SCRAPED,
    errors: env.OUTPUT_ERRORS_KEY || DEFAULT_ERRORS,
    state: env.STATE_KEY || DEFAULT_STATE,
  };
}

export async function readJson<T>(bucket: R2Bucket, key: string): Promise<T | null> {
  const obj = await bucket.get(key);
  if (!obj) return null;
  const text = await obj.text();
  return JSON.parse(text) as T;
}

export async function writeJson(bucket: R2Bucket, key: string, payload: unknown): Promise<void> {
  await bucket.put(key, JSON.stringify(payload, null, 2), {
    httpMetadata: { contentType: "application/json; charset=utf-8" },
  });
}

export async function loadFailedSources(env: Env): Promise<FailedSourcesFile> {
  if (!hasR2(env)) {
    throw new Error("R2 is not configured");
  }
  const k = keys(env);
  const data = await readJson<FailedSourcesFile>(env.SCRAPE_BUCKET!, k.input);
  if (!data || !Array.isArray(data.items)) {
    throw new Error(`Missing or invalid input at R2 key ${k.input}. Upload failed_sources JSON first.`);
  }
  return data;
}

export async function loadOrInitState(env: Env, total: number, runId: string): Promise<RunState> {
  const bucket = env.SCRAPE_BUCKET!;
  const k = keys(env);
  const existing = await readJson<RunState>(bucket, k.state);
  if (existing && !existing.completed && existing.total === total) {
    return existing;
  }
  const state: RunState = {
    offset: 0,
    total,
    run_id: runId,
    updated_at: new Date().toISOString(),
    completed: false,
  };
  await writeJson(bucket, k.state, state);
  return state;
}

export async function mergeOutputs(
  env: Env,
  runId: string,
  sourceKey: string,
  newScraped: ScrapedArticle[],
  newErrors: ScrapeErrorRecord[],
): Promise<{ scraped: ScrapedArticlesFile; errors: ScrapeErrorsFile }> {
  const k = keys(env);
  const bucket = env.SCRAPE_BUCKET!;

  const prevScraped =
    (await readJson<ScrapedArticlesFile>(bucket, k.scraped)) ??
    buildScrapedFile(runId, sourceKey, []);

  const prevErrors =
    (await readJson<ScrapeErrorsFile>(bucket, k.errors)) ??
    buildErrorsFile(runId, sourceKey, []);

  const scrapedItems = [...prevScraped.items, ...newScraped];
  const errorItems = [...prevErrors.items, ...newErrors];

  const scraped = buildScrapedFile(runId, sourceKey, scrapedItems);
  const errors = buildErrorsFile(runId, sourceKey, errorItems);

  await writeJson(bucket, k.scraped, scraped);
  await writeJson(bucket, k.errors, errors);
  return { scraped, errors };
}
