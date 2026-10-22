import type { Env } from "./types";

export type ScraperConfig = {
  requestTimeoutMs: number;
  defaultDomainDelaySec: number;
  minDomainDelaySec: number;
  maxDomainDelaySec: number;
  maxRetries: number;
  backoffBaseSec: number;
  backoffMaxSec: number;
  maxRetryAfterSec: number;
  maxConcurrentPerDomain: number;
  maxBodyExcerptChars: number;
};

function parseFloatEnv(raw: string | undefined, fallback: number): number {
  if (raw === undefined || raw === "") return fallback;
  const n = parseFloat(raw);
  return Number.isFinite(n) ? n : fallback;
}

function parseIntEnv(raw: string | undefined, fallback: number): number {
  if (raw === undefined || raw === "") return fallback;
  const n = parseInt(raw, 10);
  return Number.isFinite(n) ? n : fallback;
}

/** Per-domain delay overrides: `ndtvprofit.com=8,moneycontrol.com=6` */
export function parseDomainDelays(raw: string | undefined): Record<string, number> {
  const out: Record<string, number> = {};
  if (!raw?.trim()) return out;
  for (const part of raw.split(",")) {
    const [host, sec] = part.split("=").map((s) => s.trim());
    if (!host || !sec) continue;
    const n = parseFloat(sec);
    if (Number.isFinite(n) && n >= 0) out[host.toLowerCase()] = n;
  }
  return out;
}

export function loadConfig(env: Env): ScraperConfig {
  const minDelay = parseFloatEnv(env.SCRAPER_MIN_DOMAIN_DELAY_SECONDS, 3);
  const maxDelay = parseFloatEnv(env.SCRAPER_MAX_DOMAIN_DELAY_SECONDS, 10);
  const defaultDelay = parseFloatEnv(env.SCRAPER_DEFAULT_DOMAIN_DELAY_SECONDS, 5);
  const clampedDefault = Math.min(maxDelay, Math.max(minDelay, defaultDelay));

  return {
    requestTimeoutMs: parseIntEnv(env.SCRAPER_REQUEST_TIMEOUT_SECONDS, 20) * 1000,
    defaultDomainDelaySec: clampedDefault,
    minDomainDelaySec: minDelay,
    maxDomainDelaySec: maxDelay,
    maxRetries: parseIntEnv(env.SCRAPER_MAX_RETRIES, 3),
    backoffBaseSec: parseFloatEnv(env.SCRAPER_BACKOFF_BASE_SECONDS, 2),
    backoffMaxSec: parseFloatEnv(env.SCRAPER_BACKOFF_MAX_SECONDS, 30),
    maxRetryAfterSec: parseIntEnv(env.SCRAPER_MAX_RETRY_AFTER_SECONDS, 60),
    maxConcurrentPerDomain: parseIntEnv(env.SCRAPER_MAX_CONCURRENT_PER_DOMAIN, 1),
    maxBodyExcerptChars: parseIntEnv(env.SCRAPER_BODY_EXCERPT_CHARS, 500),
  };
}

export function domainDelaySec(
  config: ScraperConfig,
  host: string,
  overrides: Record<string, number>,
): number {
  const key = host.toLowerCase();
  const raw = overrides[key] ?? config.defaultDomainDelaySec;
  return Math.min(config.maxDomainDelaySec, Math.max(config.minDomainDelaySec, raw));
}
