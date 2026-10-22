import { describe, expect, it } from "vitest";
import { failedSourceFromErrorRow } from "../src/batch";
import type { ScrapeErrorRecord } from "../src/types";

describe("failedSourceFromErrorRow", () => {
  it("maps 403 error rows for retry input", () => {
    const row: ScrapeErrorRecord = {
      url: "https://ndtvprofit.com/x",
      title: "T",
      source: "ndtvprofit.com",
      stage: "http_fetch",
      http_status: 403,
      error_code: "HTTP_FORBIDDEN",
      message: "403",
      detail: "detail",
      previous_pipeline_error: null,
      drop_reason: "fetch_failed",
      retriable: true,
      scraped_at: "2026-01-01T00:00:00Z",
    };
    const item = failedSourceFromErrorRow(row);
    expect(item.url).toBe(row.url);
    expect(item.retriable).toBe(false);
    expect(item.last_error).toBe("403");
  });
});
