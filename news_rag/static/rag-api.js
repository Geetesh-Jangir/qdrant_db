/** API base when RAG is mounted at /insights on Rupeestop-AI, or at / when run standalone. */
function ragUrl(path) {
  const normalized = String(path || "").replace(/^\//, "");
  const p = window.location.pathname || "/";
  const base = p.includes("/insights") ? "/insights/" : "/";
  return base + normalized;
}

/** Optional APP_TOKEN: ?app_token=... once (stored in sessionStorage) or set sessionStorage rag_app_token. */
function ragHeaders(extraHeaders) {
  const headers = Object.assign({}, extraHeaders || {});
  try {
    const fromQuery = new URLSearchParams(window.location.search).get("app_token");
    const stored = sessionStorage.getItem("rag_app_token");
    let token = (stored || fromQuery || "").trim();
    if (fromQuery && fromQuery.trim() && fromQuery.trim() !== stored) {
      token = fromQuery.trim();
      sessionStorage.setItem("rag_app_token", token);
    }
    if (token) {
      headers["X-App-Token"] = token;
    }
  } catch (_e) {
    /* ignore private mode */
  }
  return headers;
}

function ragAppTokenHint() {
  return (
    "Server requires APP_TOKEN. Open this page once as ?app_token=YOUR_TOKEN " +
    "(saved for the tab session), or remove APP_TOKEN from the server .env for a public demo."
  );
}

/**
 * Parse fetch response as JSON; if the server/nginx returned HTML or plain text, throw a clear Error.
 */
async function parseRagJsonResponse(response) {
  const text = await response.text();
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error(
      response.ok
        ? "Empty response from server."
        : response.status === 401
          ? ragAppTokenHint()
          : `Server error (${response.status} ${response.statusText}).`
    );
  }
  if (trimmed.startsWith("<")) {
    const hint =
      response.status === 504 || /timed out/i.test(trimmed)
        ? " Request timed out — try a shorter question or wait and retry (first query loads the embedding model)."
        : response.status === 502
          ? " Bad gateway — the app may have run out of memory; check sudo journalctl -u news-rag."
          : "";
    throw new Error(
      `Server returned HTML instead of JSON (HTTP ${response.status}).${hint} ` +
        "Ensure nginx proxies to port 8081 and news-rag is running."
    );
  }
  try {
    const data = JSON.parse(trimmed);
    if (!response.ok && response.status === 401) {
      const detail = data && data.detail;
      throw new Error(typeof detail === "string" && detail ? detail + " — " + ragAppTokenHint() : ragAppTokenHint());
    }
    return data;
  } catch (_parseErr) {
    if (!response.ok && response.status === 401) {
      throw new Error(ragAppTokenHint());
    }
    const preview = trimmed.slice(0, 200);
    throw new Error(
      `Invalid JSON from server (HTTP ${response.status}): ${preview}`
    );
  }
}

if (typeof globalThis !== "undefined") {
  globalThis.ragUrl = ragUrl;
  globalThis.ragHeaders = ragHeaders;
  globalThis.parseRagJsonResponse = parseRagJsonResponse;
}
