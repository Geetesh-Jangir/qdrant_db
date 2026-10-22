import { describe, expect, it } from "vitest";
import {
  backoffSeconds,
  failureCategoryForStatus,
  parseRetryAfter,
  shouldRetryStatus,
} from "../src/retry-policy";

describe("retry-policy", () => {
  it("does not retry 401 or 403", () => {
    expect(shouldRetryStatus(401)).toBe(false);
    expect(shouldRetryStatus(403)).toBe(false);
  });

  it("retries 429 and 5xx", () => {
    expect(shouldRetryStatus(429)).toBe(true);
    expect(shouldRetryStatus(503)).toBe(true);
  });

  it("parses Retry-After seconds", () => {
    expect(parseRetryAfter("15")).toBe(15);
    expect(parseRetryAfter(null)).toBe(null);
  });

  it("bounded exponential backoff", () => {
    expect(backoffSeconds(0, 2, 30, 0)).toBe(2);
    expect(backoffSeconds(1, 2, 30, 0)).toBe(4);
    expect(backoffSeconds(10, 2, 30, 0)).toBe(30);
  });

  it("failure categories", () => {
    expect(failureCategoryForStatus(403, "HTTP_FORBIDDEN")).toBe("access_denied");
    expect(failureCategoryForStatus(401, "HTTP_UNAUTHORIZED")).toBe("authentication_required");
    expect(failureCategoryForStatus(429, "HTTP_RATE_LIMITED")).toBe("rate_limited");
  });
});
