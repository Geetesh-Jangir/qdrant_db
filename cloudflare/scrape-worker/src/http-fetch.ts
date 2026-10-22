import { buildErrorRecord, describeHttpStatus } from "./errors";
import type { ScraperConfig } from "./config";
import { backoffSeconds, failureCategoryForStatus, parseRetryAfter, shouldRetryStatus } from "./retry-policy";
import type { FailedSourceItem, ScrapeErrorRecord } from "./types";

export function hostFromUrl(url: string): string | null {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

export function sanitizeExcerpt(text: string, maxChars: number): string {
  const cleaned = text.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  if (cleaned.length <= maxChars) return cleaned;
  return cleaned.slice(0, maxChars - 3) + "...";
}

export type FetchOk = { finalUrl: string; html: string; status: number; durationMs: number; attempts: number };

export type SleepFn = (ms: number) => Promise<void>;

const defaultSleep: SleepFn = (ms) => new Promise((r) => setTimeout(r, ms));

export async function fetchHtmlWithPolicy(
  url: string,
  referer: string,
  config: ScraperConfig,
  item: FailedSourceItem,
  sleep: SleepFn = defaultSleep,
): Promise<FetchOk | { error: ScrapeErrorRecord }> {
  const started = Date.now();
  const titleHint = item.title ?? null;
  const source = item.source ?? hostFromUrl(url);
  let attempts = 0;
  let lastStatus: number | null = null;
  let lastExcerpt = "";

  while (attempts <= config.maxRetries) {
    attempts += 1;
    const attemptStarted = Date.now();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), config.requestTimeoutMs);
    try {
      const response = await fetch(url, {
        method: "GET",
        redirect: "follow",
        signal: controller.signal,
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
          Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          "Accept-Language": "en-IN,en;q=0.9",
          Referer: referer,
        },
      });
      clearTimeout(timer);
      lastStatus = response.status;
      const finalUrl = response.url || url;

      if (!response.ok) {
        const bodyText = await response.text();
        lastExcerpt = sanitizeExcerpt(bodyText, config.maxBodyExcerptChars);
        const { code, message } = describeHttpStatus(response.status);

        if (!shouldRetryStatus(response.status) || attempts > config.maxRetries) {
          const err = buildErrorRecord({
            url,
            title: titleHint,
            source,
            stage: "http_fetch",
            httpStatus: response.status,
            errorCode: code,
            message,
            detail: `${response.status} for url: ${url}`,
            item,
            scrapedAt: new Date().toISOString(),
            durationMs: Date.now() - started,
            attempts,
            failureCategory: failureCategoryForStatus(response.status, code),
            responseExcerpt: lastExcerpt,
            retryAfterSec: null,
            domainDelaySec: null,
          });
          if (response.status === 403) err.retriable = false;
          if (response.status === 401) err.retriable = false;
          return { error: err };
        }

        let waitSec = 0;
        if (response.status === 429) {
          const ra = parseRetryAfter(response.headers.get("Retry-After"));
          waitSec = ra !== null ? Math.min(ra, config.maxRetryAfterSec) : backoffSeconds(
            attempts - 1,
            config.backoffBaseSec,
            config.backoffMaxSec,
            0,
          );
        } else {
          const jitter = response.status >= 500 ? 0.25 : 0;
          waitSec = backoffSeconds(attempts - 1, config.backoffBaseSec, config.backoffMaxSec, jitter);
        }
        if (waitSec > config.maxRetryAfterSec) {
          const err = buildErrorRecord({
            url,
            title: titleHint,
            source,
            stage: "http_fetch",
            httpStatus: response.status,
            errorCode: code,
            message: `${message} Cooldown ${waitSec}s exceeds job limit; defer to next run.`,
            detail: `retry_after_sec=${waitSec}`,
            item,
            scrapedAt: new Date().toISOString(),
            durationMs: Date.now() - started,
            attempts,
            failureCategory: failureCategoryForStatus(response.status, code),
            responseExcerpt: lastExcerpt,
            retryAfterSec: waitSec,
            domainDelaySec: null,
          });
          err.retriable = true;
          return { error: err };
        }
        await sleep(waitSec * 1000);
        continue;
      }

      const html = await response.text();
      if (!html.trim()) {
        if (attempts <= config.maxRetries) {
          await sleep(backoffSeconds(attempts - 1, config.backoffBaseSec, config.backoffMaxSec, 0) * 1000);
          continue;
        }
        return {
          error: buildErrorRecord({
            url,
            title: titleHint,
            source,
            stage: "http_fetch",
            httpStatus: response.status,
            errorCode: "EMPTY_BODY",
            message: "HTTP 200 but response body was empty.",
            detail: "empty page",
            item,
            scrapedAt: new Date().toISOString(),
            durationMs: Date.now() - started,
            attempts,
            failureCategory: "empty_body",
            responseExcerpt: "",
            retryAfterSec: null,
            domainDelaySec: null,
          }),
        };
      }

      return {
        finalUrl,
        html,
        status: response.status,
        durationMs: Date.now() - attemptStarted,
        attempts,
      };
    } catch (exc) {
      clearTimeout(timer);
      const detail = exc instanceof Error ? exc.message : String(exc);
      const isTimeout =
        detail.toLowerCase().includes("abort") || detail.toLowerCase().includes("timeout");
      const code = isTimeout ? "FETCH_TIMEOUT" : "NETWORK_ERROR";
      if (attempts <= config.maxRetries) {
        await sleep(backoffSeconds(attempts - 1, config.backoffBaseSec, config.backoffMaxSec, 0) * 1000);
        continue;
      }
      return {
        error: buildErrorRecord({
          url,
          title: titleHint,
          source,
          stage: "http_fetch",
          httpStatus: lastStatus,
          errorCode: code,
          message: isTimeout
            ? `Request timed out after ${config.requestTimeoutMs}ms.`
            : "Network or TLS error while fetching the publisher page.",
          detail,
          item,
          scrapedAt: new Date().toISOString(),
          durationMs: Date.now() - started,
          attempts,
          failureCategory: failureCategoryForStatus(null, code),
          responseExcerpt: lastExcerpt,
          retryAfterSec: null,
          domainDelaySec: null,
        }),
      };
    }
  }

  const { code, message } = describeHttpStatus(lastStatus ?? 0);
  return {
    error: buildErrorRecord({
      url,
      title: titleHint,
      source,
      stage: "http_fetch",
      httpStatus: lastStatus,
      errorCode: code,
      message,
      detail: "exhausted retries",
      item,
      scrapedAt: new Date().toISOString(),
      durationMs: Date.now() - started,
      attempts,
      failureCategory: failureCategoryForStatus(lastStatus, code),
      responseExcerpt: lastExcerpt,
      retryAfterSec: null,
      domainDelaySec: null,
    }),
  };
}
