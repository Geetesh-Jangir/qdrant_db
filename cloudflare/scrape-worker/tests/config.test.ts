import { describe, expect, it } from "vitest";
import { domainDelaySec, loadConfig, parseDomainDelays } from "../src/config";

describe("config", () => {
  it("loads defaults from env", () => {
    const cfg = loadConfig({});
    expect(cfg.requestTimeoutMs).toBe(20_000);
    expect(cfg.defaultDomainDelaySec).toBe(5);
    expect(cfg.maxRetries).toBe(3);
  });

  it("parses per-domain delays", () => {
    const m = parseDomainDelays("ndtvprofit.com=8, moneycontrol.com=6");
    expect(m["ndtvprofit.com"]).toBe(8);
    expect(domainDelaySec(loadConfig({}), "ndtvprofit.com", m)).toBe(8);
  });

  it("clamps domain delay to min/max", () => {
    const cfg = loadConfig({
      SCRAPER_MIN_DOMAIN_DELAY_SECONDS: "3",
      SCRAPER_MAX_DOMAIN_DELAY_SECONDS: "10",
      SCRAPER_DEFAULT_DOMAIN_DELAY_SECONDS: "99",
    });
    expect(cfg.defaultDomainDelaySec).toBe(10);
  });
});
