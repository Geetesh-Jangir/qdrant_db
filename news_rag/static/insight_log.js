(function () {
  const main = document.getElementById("main");
  const subtitle = document.getElementById("subtitle");
  const parts = window.location.pathname.split("/").filter(Boolean);
  const idx = parts.indexOf("log");
  const insight = parts[idx + 1] || "";
  const date = parts[idx + 2] || "";
  const runId = parts[idx + 3] || "";

  function api(path) {
    return "/api/insights/" + path.replace(/^\//, "");
  }

  function headers() {
    const extra = {};
    try {
      const token = sessionStorage.getItem("insights_admin_token");
      if (token) extra["X-Admin-Token"] = token;
    } catch (_e) { /* ignore */ }
    return typeof ragHeaders === "function" ? ragHeaders(extra) : extra;
  }

  function esc(text) {
  return String(text || "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
  }

  async function load() {
    subtitle.textContent = insight + " · " + date + " · run " + runId;
    const response = await fetch(api("runs/" + encodeURIComponent(insight) + "/" + encodeURIComponent(date) + "/" + encodeURIComponent(runId)), { headers: headers() });
    const body = await response.json();
    if (!response.ok) {
      main.innerHTML = "<p class='muted'>Could not load log.</p>";
      return;
    }
    const usage = body.usage || {};
    const calls = usage.calls_detail || [];
    const rows = calls
      .map((row) => "<tr><td>" + esc(row.seq) + "</td><td>" + esc(row.label) + "</td><td>" + esc(row.kind) + "</td><td>" + esc(row.input_tokens) + "</td><td>" + esc(row.output_tokens) + "</td><td>" + esc(row.latency_ms) + "</td></tr>")
      .join("");
    const path = body.run_dir ? "<p><strong>Local:</strong> <code>" + esc(body.run_dir) + "</code></p>" : "";
    main.innerHTML =
      path +
      "<p>LLM calls: " + esc(usage.calls) + " · in " + esc(usage.input_tokens) + " · out " + esc(usage.output_tokens) + "</p>" +
      "<table class='log-table'><thead><tr><th>#</th><th>Label</th><th>Kind</th><th>In</th><th>Out</th><th>ms</th></tr></thead><tbody>" +
      rows +
      "</tbody></table><pre class='trace'>" +
      esc(body.decision_trace || "") +
      "</pre>";
  }

  load().catch((error) => {
    main.innerHTML = "<p class='muted'>" + esc(error.message || error) + "</p>";
  });
})();