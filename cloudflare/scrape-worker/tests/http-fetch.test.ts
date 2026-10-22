import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchHtmlWithPolicy, sanitizeExcerpt } from "../src/http-fetch";
import { loadConfig } from "../src/config";
import type { FailedSourceItem } from "../src/types";

const item: FailedSourceItem = { url: "https://example.com/article" };
const config = loadConfig({
  SCRAPER_REQUEST_TIMEOUT_SECONDS: "20",
  SCRAPER_MAX_RETRIES: "3",
  SCRAPER_MAX_RETRY_AFTER_SECONDS: "60",
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchHtmlWithPolicy", () => {
  it("returns html on 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response("<html><body>Hello article text here</body></html>", { status: 200 }),
      ),
    );
    const result = await fetchHtmlWithPolicy(
      "https://example.com/article",
      "https://news.google.com/",
      config,
      item,
      async () => {},
    );
    expect("finalUrl" in result).toBe(true);
    if ("finalUrl" in result) {
      expect(result.html).toContain("Hello");
    }
  });

  it("does not retry 403", async () => {
    const fetchMock = vi.fn(async () =>
      new Response("<html>blocked</html>", { status: 403 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const result = await fetchHtmlWithPolicy(
      "https://blocked.com/x",
      "https://news.google.com/",
      config,
      { ...item, url: "https://blocked.com/x" },
      async () => {},
    );
    expect("error" in result).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    if ("error" in result) {
      expect(result.error.http_status).toBe(403);
      expect(result.error.retriable).toBe(false);
      expect(result.error.response_excerpt).toContain("blocked");
    }
  });

  it("honors Retry-After on 429", async () => {
    const sleeps: number[] = [];
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response("slow down", {
          status: 429,
          headers: { "Retry-After": "2" },
        }),
      )
      .mockResolvedValueOnce(new Response("<html>ok body</html>", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchHtmlWithPolicy(
      "https://rate.example.com/x",
      "https://news.google.com/",
      config,
      { ...item, url: "https://rate.example.com/x" },
      async (ms) => {
        sleeps.push(ms);
      },
    );
    expect(sleeps).toEqual([2000]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect("finalUrl" in result).toBe(true);
  });

  it("retries 503 then succeeds", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("err", { status: 503 }))
      .mockResolvedValueOnce(new Response("<html>recovered</html>", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchHtmlWithPolicy(
      "https://flaky.example.com/x",
      "https://news.google.com/",
      config,
      { ...item, url: "https://flaky.example.com/x" },
      async () => {},
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect("finalUrl" in result).toBe(true);
  });
});

describe("sanitizeExcerpt", () => {
  it("strips tags and truncates", () => {
    const s = sanitizeExcerpt("<p>secret token Authorization: Bearer abc</p>", 20);
    expect(s.length).toBeLessThanOrEqual(20);
    expect(s).not.toContain("<p>");
  });
});
