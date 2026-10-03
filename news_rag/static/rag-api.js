/** API base when RAG is mounted at /insights on Rupeestop-AI, or at / when run standalone. */
function ragUrl(path) {
  const normalized = String(path || "").replace(/^\//, "");
  const p = window.location.pathname || "/";
  const base = p.includes("/insights") ? "/insights/" : "/";
  return base + normalized;
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
    return JSON.parse(trimmed);
  } catch (_parseErr) {
    const preview = trimmed.slice(0, 200);
    throw new Error(
      `Invalid JSON from server (HTTP ${response.status}): ${preview}`
    );
  }
}
