/** Pure retry decisions (unit-tested). */

export function parseRetryAfter(header: string | null): number | null {
  if (!header?.trim()) return null;
  const secs = parseInt(header.trim(), 10);
  if (Number.isFinite(secs) && secs >= 0) return secs;
  const date = Date.parse(header);
  if (!Number.isFinite(date)) return null;
  const delta = Math.ceil((date - Date.now()) / 1000);
  return delta > 0 ? delta : 0;
}

export function backoffSeconds(attempt: number, baseSec: number, maxSec: number, jitterSec: number): number {
  const exp = Math.min(maxSec, baseSec * 2 ** attempt);
  return Math.min(maxSec, exp + jitterSec);
}

export function shouldRetryStatus(status: number): boolean {
  if (status === 401 || status === 403) return false;
  if (status === 429) return true;
  if (status >= 500 && status <= 599) return true;
  return false;
}

export function failureCategoryForStatus(status: number | null, errorCode: string): string {
  if (status === 403) return "access_denied";
  if (status === 401) return "authentication_required";
  if (status === 429) return "rate_limited";
  if (status !== null && status >= 500) return "transient_server_error";
  if (errorCode === "FETCH_TIMEOUT") return "timeout";
  if (errorCode === "NETWORK_ERROR") return "network_error";
  if (errorCode === "EXTRACT_THIN") return "extract_thin";
  return "other";
}
