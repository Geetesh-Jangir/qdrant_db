/** Matches news_pipeline failure ledger / failed_source.json rows. */
export type FailedSourceItem = {
  url: string;
  title?: string;
  snippet?: string;
  published_at?: string | null;
  source?: string;
  entities?: Array<{ name: string; type?: string }>;
  drop_reason?: string;
  retriable?: boolean;
  attempts?: number;
  exhausted?: boolean;
  pending?: boolean;
  last_error?: string;
  last_run_id?: string;
  calendar_day?: string;
  news_date_range?: string;
};

export type FailedSourcesFile = {
  items: FailedSourceItem[];
};

export type ScrapedArticle = {
  url: string;
  input_url: string;
  final_url: string | null;
  title: string | null;
  published_at: string | null;
  text: string;
  char_count: number;
  status: "ok" | "extract_thin";
  scraped_at: string;
  source?: string;
  entities?: FailedSourceItem["entities"];
  original_failure?: {
    drop_reason?: string;
    last_error?: string;
    last_run_id?: string;
    calendar_day?: string;
  };
};

export type ScrapeErrorRecord = {
  url: string;
  title: string | null;
  source: string | null;
  stage: "resolve" | "http_fetch" | "extract" | "input";
  http_status: number | null;
  error_code: string;
  message: string;
  detail: string;
  previous_pipeline_error: string | null;
  drop_reason: string | null;
  retriable: boolean;
  scraped_at: string;
  duration_ms?: number;
  attempts?: number;
  failure_category?: string;
  response_excerpt?: string;
  retry_after_sec?: number | null;
  domain_delay_sec?: number | null;
};

export type ScrapeRunSummary = {
  attempted: number;
  http_200: number;
  http_401: number;
  http_403: number;
  http_429: number;
  other_http_errors: number;
  connection_or_timeout: number;
  articles_parsed_ok: number;
  articles_extract_thin: number;
  articles_failed: number;
  by_publisher: Record<string, { attempted: number; ok: number; http_403: number }>;
};

export type ScrapedArticlesFile = {
  schema: "cloudflare-scrape/v1";
  generated_at: string;
  run_id: string;
  source_key: string;
  items: ScrapedArticle[];
  summary: {
    total_ok: number;
    total_thin: number;
  };
};

export type ScrapeErrorsFile = {
  schema: "cloudflare-scrape-errors/v1";
  generated_at: string;
  run_id: string;
  source_key: string;
  items: ScrapeErrorRecord[];
  summary: {
    attempted: number;
    failed: number;
    by_error_code: Record<string, number>;
    by_http_status: Record<string, number>;
  };
};

export type RunState = {
  offset: number;
  total: number;
  run_id: string;
  updated_at: string;
  completed: boolean;
};

export interface Env {
  SCRAPE_BUCKET?: R2Bucket;
  SCRAPE_TRIGGER_SECRET?: string;
  INPUT_KEY?: string;
  OUTPUT_SCRAPED_KEY?: string;
  OUTPUT_ERRORS_KEY?: string;
  STATE_KEY?: string;
  BATCH_SIZE?: string;
  MAX_BODY_CHARS?: string;
  SCRAPER_REQUEST_TIMEOUT_SECONDS?: string;
  SCRAPER_DEFAULT_DOMAIN_DELAY_SECONDS?: string;
  SCRAPER_MIN_DOMAIN_DELAY_SECONDS?: string;
  SCRAPER_MAX_DOMAIN_DELAY_SECONDS?: string;
  SCRAPER_MAX_RETRIES?: string;
  SCRAPER_BACKOFF_BASE_SECONDS?: string;
  SCRAPER_BACKOFF_MAX_SECONDS?: string;
  SCRAPER_MAX_RETRY_AFTER_SECONDS?: string;
  SCRAPER_MAX_CONCURRENT_PER_DOMAIN?: string;
  SCRAPER_BODY_EXCERPT_CHARS?: string;
  /** e.g. ndtvprofit.com=8,moneycontrol.com=6 */
  SCRAPER_DOMAIN_DELAYS?: string;
}
