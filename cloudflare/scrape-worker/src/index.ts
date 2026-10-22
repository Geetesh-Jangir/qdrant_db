/**
 * Cloudflare Worker: scrape failed-source URLs.
 * Default mode (no R2): POST /run with JSON body { "items": [...] } — results returned in response.
 * Optional R2 mode if SCRAPE_BUCKET binding is configured.
 */

import {
  buildErrorsFile,
  buildScrapedFile,
  scrapeItems,
} from "./batch";
import {
  hasR2,
  keys,
  loadFailedSources,
  loadOrInitState,
  mergeOutputs,
  writeJson,
} from "./storage";
import type { Env, FailedSourceItem } from "./types";

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

function unauthorized(): Response {
  return json({ ok: false, error: "Unauthorized" }, 401);
}

function checkAuth(request: Request, env: Env): boolean {
  const secret = env.SCRAPE_TRIGGER_SECRET;
  if (!secret) return true;
  const auth = request.headers.get("Authorization") || "";
  return auth === `Bearer ${secret}`;
}

function parseBatchSize(env: Env, request: Request, bodyLimit?: number): number {
  const url = new URL(request.url);
  const q = url.searchParams.get("limit");
  const raw = bodyLimit ?? (q ? parseInt(q, 10) : parseInt(env.BATCH_SIZE || "10", 10));
  const n = Number.isFinite(raw) ? raw : 10;
  if (n < 1) return 10;
  return Math.min(n, 25);
}

function parseMinBody(env: Env): number {
  const raw = env.MAX_BODY_CHARS || "400";
  const n = parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : 400;
}

function newRunId(): string {
  const t = new Date().toISOString().replace(/[-:]/g, "").replace(/\..+/, "Z");
  return `cf_${t}_${Math.random().toString(16).slice(2, 8)}`;
}

/** POST body: scrape these rows; no R2. Used by run-scrape-local.ps1 */
async function runBodyBatch(env: Env, request: Request): Promise<Response> {
  const minBody = parseMinBody(env);
  let body: { items?: FailedSourceItem[]; run_id?: string; source_key?: string };
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "Invalid JSON body. Send { \"items\": [ ... ] }" }, 400);
  }
  const all = (body.items || []).filter((r) => (r.url || "").trim());
  const maxPerRequest = parseBatchSize(env, request);
  const items = all.slice(0, Math.min(all.length, maxPerRequest));
  if (!items.length) {
    return json({ ok: false, error: "No items in body (need at least one url)" }, 400);
  }

  const { scraped, errors, runSummary } = await scrapeItems(items, minBody, env);
  const runId = body.run_id || newRunId();
  const sourceKey = body.source_key || "local/failed_sources.json";

  return json({
    ok: true,
    mode: "stateless",
    run_id: runId,
    batch: {
      processed: items.length,
      succeeded: scraped.length,
      failed: errors.length,
    },
    run_summary: runSummary,
    scraped: buildScrapedFile(runId, sourceKey, scraped),
    errors: buildErrorsFile(runId, sourceKey, errors),
  });
}

async function runR2Batch(env: Env, request: Request): Promise<Response> {
  const k = keys(env);
  const limit = parseBatchSize(env, request);
  const minBody = parseMinBody(env);
  const reset = new URL(request.url).searchParams.get("reset") === "1";

  let sources;
  try {
    sources = await loadFailedSources(env);
  } catch (e) {
    return json({ ok: false, error: String(e) }, 400);
  }

  const items = sources.items.filter((row) => (row.url || "").trim());
  const runId = newRunId();

  let state;
  if (reset) {
    state = {
      offset: 0,
      total: items.length,
      run_id: runId,
      updated_at: new Date().toISOString(),
      completed: false,
    };
    await writeJson(env.SCRAPE_BUCKET!, k.state, state);
    await writeJson(env.SCRAPE_BUCKET!, k.scraped, buildScrapedFile(runId, k.input, []));
    await writeJson(env.SCRAPE_BUCKET!, k.errors, buildErrorsFile(runId, k.input, []));
  } else {
    state = await loadOrInitState(env, items.length, runId);
  }

  if (state.completed || state.offset >= items.length) {
    return json({
      ok: true,
      mode: "r2",
      message: "Nothing to do — run already completed or offset past end.",
      state,
      keys: k,
    });
  }

  const slice = items.slice(state.offset, state.offset + limit);
  const { scraped: batchScraped, errors: batchErrors } = await scrapeItems(
    slice as FailedSourceItem[],
    minBody,
    env,
  );

  const merged = await mergeOutputs(env, state.run_id, k.input, batchScraped, batchErrors);

  const nextOffset = state.offset + slice.length;
  const completed = nextOffset >= items.length;
  const nextState = {
    ...state,
    offset: nextOffset,
    updated_at: new Date().toISOString(),
    completed,
  };
  await writeJson(env.SCRAPE_BUCKET!, k.state, nextState);

  return json({
    ok: true,
    mode: "r2",
    batch: {
      processed: slice.length,
      succeeded: batchScraped.length,
      failed: batchErrors.length,
      offset_before: state.offset,
      offset_after: nextOffset,
      total: items.length,
      completed,
    },
    output_keys: { scraped: k.scraped, errors: k.errors, state: k.state },
    summary: {
      scraped: merged.scraped.summary,
      errors: merged.errors.summary,
    },
  });
}

async function handleRun(env: Env, request: Request): Promise<Response> {
  if (request.method === "POST") {
    const contentType = request.headers.get("Content-Type") || "";
    if (contentType.includes("application/json")) {
      const cloned = request.clone();
      try {
        const peek = (await cloned.json()) as { items?: unknown };
        if (peek && Array.isArray(peek.items)) {
          return runBodyBatch(env, request);
        }
      } catch {
        /* fall through */
      }
    }
  }

  if (hasR2(env) && (request.method === "GET" || request.method === "POST")) {
    return runR2Batch(env, request);
  }

  return json(
    {
      ok: false,
      error: "No R2 bucket configured. POST /run with JSON body: { \"items\": [ { \"url\": \"...\" }, ... ] }",
      hint: "On your PC run: cloudflare\\scripts\\run-scrape-local.ps1",
    },
    400,
  );
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return json({
        ok: true,
        service: "cloudflare-failed-source-scraper",
        r2_enabled: hasR2(env),
      });
    }

    if (!checkAuth(request, env)) {
      return unauthorized();
    }

    if (url.pathname === "/run" && (request.method === "POST" || request.method === "GET")) {
      return handleRun(env, request);
    }

    if (url.pathname === "/scrape-inline" && request.method === "POST") {
      return runBodyBatch(env, request);
    }

    return json(
      {
        ok: false,
        hint:
          "POST /run with { items: [...] } (no R2), or use run-scrape-local.ps1. GET /health.",
      },
      404,
    );
  },
};
