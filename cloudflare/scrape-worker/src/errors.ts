import type { ScrapeErrorRecord } from "./types";

export function describeHttpStatus(status: number): { code: string; message: string } {
  switch (status) {
    case 401:
      return {
        code: "HTTP_UNAUTHORIZED",
        message:
          "Publisher returned 401 Unauthorized. Often a paywall or login requirement (e.g. wire services).",
      };
    case 403:
      return {
        code: "HTTP_FORBIDDEN",
        message:
          "Publisher returned 403 Forbidden. Often bot/WAF blocking or geo/datacenter IP block on Cloudflare egress.",
      };
    case 404:
      return {
        code: "HTTP_NOT_FOUND",
        message: "Publisher returned 404 Not Found. URL may be expired or AMP variant invalid.",
      };
    case 410:
      return {
        code: "HTTP_GONE",
        message: "Publisher returned 410 Gone. Article permanently removed.",
      };
    case 429:
      return {
        code: "HTTP_RATE_LIMITED",
        message: "Publisher returned 429 Too Many Requests. Slow down batch size or add delay.",
      };
    default:
      if (status >= 500) {
        return {
          code: "HTTP_SERVER_ERROR",
          message: `Publisher returned server error ${status}. Temporary outage or CDN issue.`,
        };
      }
      return {
        code: "HTTP_ERROR",
        message: `Publisher returned HTTP ${status}.`,
      };
  }
}

export function buildErrorRecord(params: {
  url: string;
  title: string | null;
  source: string | null;
  stage: ScrapeErrorRecord["stage"];
  httpStatus: number | null;
  errorCode: string;
  message: string;
  detail: string;
  item: { last_error?: string; drop_reason?: string; retriable?: boolean };
  scrapedAt: string;
  durationMs?: number;
  attempts?: number;
  failureCategory?: string;
  responseExcerpt?: string;
  retryAfterSec?: number | null;
  domainDelaySec?: number | null;
  retriableOverride?: boolean;
}): ScrapeErrorRecord {
  const rec: ScrapeErrorRecord = {
    url: params.url,
    title: params.title,
    source: params.source,
    stage: params.stage,
    http_status: params.httpStatus,
    error_code: params.errorCode,
    message: params.message,
    detail: params.detail,
    previous_pipeline_error: params.item.last_error ?? null,
    drop_reason: params.item.drop_reason ?? null,
    retriable: params.retriableOverride ?? params.item.retriable ?? true,
    scraped_at: params.scrapedAt,
  };
  if (params.durationMs !== undefined) rec.duration_ms = params.durationMs;
  if (params.attempts !== undefined) rec.attempts = params.attempts;
  if (params.failureCategory) rec.failure_category = params.failureCategory;
  if (params.responseExcerpt) rec.response_excerpt = params.responseExcerpt;
  if (params.retryAfterSec !== undefined) rec.retry_after_sec = params.retryAfterSec;
  if (params.domainDelaySec !== undefined) rec.domain_delay_sec = params.domainDelaySec;
  return rec;
}
