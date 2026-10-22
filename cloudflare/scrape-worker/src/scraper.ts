import { extractFromHtml, THIN_CHARS } from "./extract";
import { buildErrorRecord, describeHttpStatus } from "./errors";
import { fetchHtmlWithPolicy, hostFromUrl, type SleepFn } from "./http-fetch";
import type { ScraperConfig } from "./config";
import { failureCategoryForStatus } from "./retry-policy";
import type { FailedSourceItem, ScrapeErrorRecord, ScrapedArticle } from "./types";

export async function scrapeOneItem(
  item: FailedSourceItem,
  minBodyChars: number,
  config: ScraperConfig,
  sleep?: SleepFn,
): Promise<{ ok: ScrapedArticle } | { err: ScrapeErrorRecord }> {
  const inputUrl = (item.url || "").trim();
  const scrapedAt = new Date().toISOString();
  const titleHint = item.title ?? null;
  const source = item.source ?? hostFromUrl(inputUrl);

  if (!inputUrl) {
    return {
      err: buildErrorRecord({
        url: "",
        title: titleHint,
        source,
        stage: "input",
        httpStatus: null,
        errorCode: "MISSING_URL",
        message: "Input row has no URL.",
        detail: "url field empty",
        item,
        scrapedAt,
        failureCategory: "other",
      }),
    };
  }

  const referer = "https://news.google.com/";
  const fetched = await fetchHtmlWithPolicy(inputUrl, referer, config, item, sleep);
  if ("error" in fetched) {
    const err = fetched.error;
    err.title = titleHint;
    err.source = source;
    err.previous_pipeline_error = item.last_error ?? null;
    err.drop_reason = item.drop_reason ?? null;
    if (err.http_status === 403 || err.http_status === 401) err.retriable = false;
    else err.retriable = item.retriable ?? err.retriable;
    return { err };
  }

  const extracted = extractFromHtml(fetched.html, fetched.finalUrl);
  let text = extracted.text.trim();
  let title = extracted.title || titleHint;

  if (text.length < minBodyChars) {
    const snippet = (item.snippet || "").trim();
    if (snippet) text = `${title || ""}. ${snippet}`.trim();
    else if (title) text = title;
  }

  if (extracted.thin && text.length < THIN_CHARS) {
    return {
      err: buildErrorRecord({
        url: inputUrl,
        title: titleHint,
        source,
        stage: "extract",
        httpStatus: fetched.status,
        errorCode: "EXTRACT_THIN",
        message:
          "Page fetched but extracted text is very short; likely JS-rendered content, paywall shell, or wrong page type.",
        detail: `extracted_chars=${text.length} min_hint=${THIN_CHARS}`,
        item,
        scrapedAt,
        durationMs: fetched.durationMs,
        attempts: fetched.attempts,
        failureCategory: failureCategoryForStatus(fetched.status, "EXTRACT_THIN"),
      }),
    };
  }

  const article: ScrapedArticle = {
    url: inputUrl,
    input_url: inputUrl,
    final_url: fetched.finalUrl,
    title: title ?? null,
    published_at: item.published_at ?? extracted.date ?? null,
    text,
    char_count: text.length,
    status: extracted.thin ? "extract_thin" : "ok",
    scraped_at: scrapedAt,
    source: source ?? undefined,
    entities: item.entities,
    original_failure: {
      drop_reason: item.drop_reason,
      last_error: item.last_error,
      last_run_id: item.last_run_id,
      calendar_day: item.calendar_day,
    },
  };
  return { ok: article };
}
