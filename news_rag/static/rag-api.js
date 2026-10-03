/** API base when RAG is mounted at /insights on Rupeestop-AI, or at / when run standalone. */
function ragUrl(path) {
  const normalized = String(path || "").replace(/^\//, "");
  const p = window.location.pathname || "/";
  const base = p.includes("/insights") ? "/insights/" : "/";
  return base + normalized;
}
