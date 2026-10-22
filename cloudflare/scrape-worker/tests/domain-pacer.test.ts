import { describe, expect, it } from "vitest";
import { DomainPacer } from "../src/domain-pacer";

describe("DomainPacer", () => {
  it("waits between requests to the same host", async () => {
    let now = 0;
    const sleep = async (ms: number) => {
      now += ms;
    };
    const pacer = new DomainPacer(sleep, () => now);

    const w1 = await pacer.wait("example.com", 5);
    expect(w1).toBe(0);
    const w2 = await pacer.wait("example.com", 5);
    expect(w2).toBe(5000);
    expect(now).toBe(5000);
  });

  it("independent hosts do not delay each other", async () => {
    let now = 0;
    const sleep = async (ms: number) => {
      now += ms;
    };
    const pacer = new DomainPacer(sleep, () => now);

    await pacer.wait("a.com", 5);
    const w = await pacer.wait("b.com", 5);
    expect(w).toBe(0);
    expect(now).toBe(0);
  });
});
