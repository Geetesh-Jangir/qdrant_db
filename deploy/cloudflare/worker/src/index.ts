/**
 * Cloudflare Worker: trigger Historical news backfill on GitHub Actions.
 *
 * The Python pipeline does NOT run inside this Worker (Workers cannot host
 * multi-hour ingest + local embeddings). This starts the existing
 * .github/workflows/historical-news-backfill.yml workflow via the GitHub API.
 */

export interface Env {
  GITHUB_PAT: string;
  GITHUB_REPO: string;
  GITHUB_WORKFLOW_FILE: string;
  GITHUB_REF: string;
  BACKFILL_START: string;
  BACKFILL_END: string;
  HOLDINGS_LIMIT: string;
  SECTORS_LIMIT: string;
  BACKFILL_PAUSE_SEC: string;
  BACKFILL_TRIGGER_SECRET?: string;
}

type DispatchInputs = {
  start_date: string;
  end_date: string;
  holdings_limit: string;
  sectors_limit: string;
  pause_sec: string;
};

async function dispatchBackfill(env: Env, inputs?: Partial<DispatchInputs>): Promise<Response> {
  const pat = env.GITHUB_PAT;
  if (!pat) {
    return json({ ok: false, error: "GITHUB_PAT secret is not set" }, 500);
  }

  const repo = env.GITHUB_REPO || "Geetesh-Jangir/qdrant_db";
  const [owner, name] = repo.split("/");
  if (!owner || !name) {
    return json({ ok: false, error: "Invalid GITHUB_REPO" }, 500);
  }

  const workflow = env.GITHUB_WORKFLOW_FILE || "historical-news-backfill.yml";
  const url = `https://api.github.com/repos/${owner}/${name}/actions/workflows/${workflow}/dispatches`;

  const body = {
    ref: env.GITHUB_REF || "main",
    inputs: {
      start_date: inputs?.start_date ?? env.BACKFILL_START ?? "1/10/2026",
      end_date: inputs?.end_date ?? env.BACKFILL_END ?? "3/10/2026",
      holdings_limit: inputs?.holdings_limit ?? env.HOLDINGS_LIMIT ?? "500",
      sectors_limit: inputs?.sectors_limit ?? env.SECTORS_LIMIT ?? "50",
      pause_sec: inputs?.pause_sec ?? env.BACKFILL_PAUSE_SEC ?? "600",
    },
  };

  const gh = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${pat}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "news-backfill-trigger-worker",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify(body),
  });

  if (!gh.ok) {
    const text = await gh.text();
    return json(
      {
        ok: false,
        error: "GitHub workflow dispatch failed",
        status: gh.status,
        detail: text.slice(0, 2000),
        inputs: body.inputs,
      },
      502,
    );
  }

  return json({
    ok: true,
    message: "historical-news-backfill workflow dispatched",
    ref: body.ref,
    inputs: body.inputs,
    actions_url: `https://github.com/${owner}/${name}/actions/workflows/${workflow}`,
  });
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function authorize(request: Request, env: Env): boolean {
  const secret = env.BACKFILL_TRIGGER_SECRET;
  if (!secret) {
    return true;
  }
  const auth = request.headers.get("Authorization") || "";
  return auth === `Bearer ${secret}`;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const path = new URL(request.url).pathname;

    if (path === "/" || path === "/health") {
      return json({ ok: true, service: "news-backfill-trigger" });
    }

    if (path === "/trigger" && request.method === "POST") {
      if (!authorize(request, env)) {
        return json({ ok: false, error: "Unauthorized" }, 401);
      }
      let overrides: Partial<DispatchInputs> = {};
      try {
        const text = await request.text();
        if (text.trim()) {
          const parsed = JSON.parse(text) as Partial<DispatchInputs>;
          overrides = parsed;
        }
      } catch {
        return json({ ok: false, error: "Invalid JSON body" }, 400);
      }
      return dispatchBackfill(env, overrides);
    }

    return json({ ok: false, error: "Not found. Use POST /trigger" }, 404);
  },

  async scheduled(_event: ScheduledEvent, env: Env, _ctx: ExecutionContext): Promise<void> {
    const res = await dispatchBackfill(env);
    const body = await res.text();
    console.log(`scheduled backfill dispatch status=${res.status} body=${body}`);
  },
};
