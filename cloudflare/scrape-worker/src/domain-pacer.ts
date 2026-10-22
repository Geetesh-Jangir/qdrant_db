/** Per-domain spacing within a single Worker invocation (one concurrent request per host). */

export type SleepFn = (ms: number) => Promise<void>;
export type NowFn = () => number;

const defaultSleep: SleepFn = (ms) => new Promise((r) => setTimeout(r, ms));
const defaultNow: NowFn = () => Date.now();

export class DomainPacer {
  private lastByHost = new Map<string, number>();
  private readonly sleep: SleepFn;
  private readonly now: NowFn;

  constructor(sleep: SleepFn = defaultSleep, now: NowFn = defaultNow) {
    this.sleep = sleep;
    this.now = now;
  }

  async wait(host: string, delaySec: number): Promise<number> {
    if (!host || delaySec <= 0) return 0;
    const t = this.now();
    const last = this.lastByHost.get(host);
    if (last === undefined) {
      this.lastByHost.set(host, t);
      return 0;
    }
    const needMs = delaySec * 1000 - (t - last);
    const waitedMs = needMs > 0 ? needMs : 0;
    if (waitedMs > 0) await this.sleep(waitedMs);
    this.lastByHost.set(host, this.now());
    return waitedMs;
  }

  reset(): void {
    this.lastByHost.clear();
  }
}
