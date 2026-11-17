(function () {
  const STORAGE_JOB = "holding_insights_job_id";
  const limitEl = document.getElementById("limit");
  const runBtn = document.getElementById("run");
  const progressEl = document.getElementById("progress");
  const errorEl = document.getElementById("error");
  const main = document.getElementById("main");
  let pollTimer = null;

  function api(path) {
    const base = window.location.pathname.replace(/\/holding-insights\/?$/, "/");
    return base + String(path || "").replace(/^\//, "");
  }

  function headers() {
    return typeof ragHeaders === "function" ? ragHeaders() : {};
  }

  function showError(msg) {
    errorEl.hidden = false;
    errorEl.textContent = msg;
  }

  function clearError() {
    errorEl.hidden = true;
    errorEl.textContent = "";
  }

  function rememberJob(jobId) {
    if (jobId) {
      try {
        localStorage.setItem(STORAGE_JOB, jobId);
      } catch (_e) { /* ignore */ }
    }
  }

  function usageBlock(row) {
    const u = row.usage || {};
    if (!u.input_tokens && !u.output_tokens && !u.llm_calls) return "";
    return (
      "<p class=\"usage\">Tokens — in: <strong>" + (u.input_tokens || 0) +
      "</strong>, out: <strong>" + (u.output_tokens || 0) +
      "</strong>, calls: <strong>" + (u.llm_calls || 0) + "</strong></p>"
    );
  }

  function logLink(row) {
    if (!row.log_url) return "";
    return "<a class=\"log-link\" href=\"" + escapeHtml(row.log_url) + "\">View run log</a>";
  }

  function escapeHtml(text) {
    return String(text || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function renderResult(payload) {
    if (!payload) return;
    const insights = payload.insights || [];
    const insufficient = payload.insufficient || [];
    const running = payload.status === "running";
    let html = "";
    if (payload.job_id) {
      html += "<p class=\"muted\">Run <code>" + escapeHtml(payload.job_id) + "</code>";
      if (payload.generated_on) html += " · " + escapeHtml(payload.generated_on);
      html += running ? " · <strong>in progress</strong>" : "";
      html += "</p>";
    }
    if (payload.counts) {
      html += "<p class=\"muted\">OK: " + (payload.counts.ok || 0) + " · Insufficient: " + (payload.counts.insufficient || 0) + "</p>";
    }
    if (payload.usage_total && (payload.usage_total.input_tokens || payload.usage_total.output_tokens)) {
      html += "<p class=\"muted\">Run totals — in: " + (payload.usage_total.input_tokens || 0) +
        ", out: " + (payload.usage_total.output_tokens || 0) + "</p>";
    }
    insights.forEach(function (row) {
      html += "<article class=\"card\"><h2>" + escapeHtml(row.headline || row.stock_name || row.stock_id) + "</h2>";
      var insightText = (row.insight_lines || []).join(" ");
      if (insightText) {
        html += "<p class=\"insight-body\">" + escapeHtml(insightText) + "</p>";
      }
      html += usageBlock(row);
      html += logLink(row);
      html += "</article>";
    });
    if (insufficient.length) {
      html += "<section class=\"insuff\"><h2>Insufficient data</h2><ul>";
      insufficient.forEach(function (row) {
        html += "<li>" + escapeHtml(row.stock_name || row.stock_id) + " — " + escapeHtml(row.reason || "unknown");
        if (row.detail) {
          html += " — <span class=\"muted\">" + escapeHtml(row.detail) + "</span>";
        }
        if (row.log_url) {
          html += ' <a class="log-link" href="' + escapeHtml(row.log_url) + '">log</a>';
        }
        html += "</li>";
      });
      html += "</ul></section>";
    }
    if (!insights.length && !insufficient.length && running) {
      html += "<p class=\"muted\">Waiting for first stock…</p>";
    }
    main.innerHTML = html;
  }

  function setProgress(payload) {
    const prog = payload.progress || {};
    progressEl.hidden = false;
    progressEl.textContent =
      "Status: " + (payload.status || "unknown") +
      (prog.total ? " · " + (prog.done || 0) + "/" + prog.total : "") +
      (prog.last_stock_id ? " · last " + prog.last_stock_id : "");
  }

  async function poll(jobId) {
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
    const res = await fetch(api("api/holding-insights/jobs/" + jobId), { headers: headers() });
    const body = await (typeof parseRagJsonResponse === "function" ? parseRagJsonResponse(res) : res.json());
    rememberJob(jobId);
    setProgress(body);
    renderResult(body);
    if (body.status === "running") {
      pollTimer = setTimeout(function () { poll(jobId); }, 1500);
      return;
    }
    progressEl.hidden = true;
    runBtn.disabled = false;
  }

  async function loadSaved() {
    try {
      const res = await fetch(api("api/holding-insights/jobs/latest"), { headers: headers() });
      const body = await (typeof parseRagJsonResponse === "function" ? parseRagJsonResponse(res) : res.json());
      if (!body.job_id || body.status === "idle") {
        return;
      }
      rememberJob(body.job_id);
      if (typeof body.limit === "number" && body.limit > 0) {
        limitEl.value = String(body.limit);
      }
      if (body.status === "running") {
        runBtn.disabled = true;
        poll(body.job_id);
        return;
      }
      renderResult(body);
    } catch (_err) {
      /* no saved run */
    }
  }

  async function run() {
    clearError();
    const limit = Math.min(99, Math.max(1, parseInt(limitEl.value, 10) || 10));
    limitEl.value = String(limit);
    runBtn.disabled = true;
    progressEl.hidden = false;
    progressEl.textContent = "Starting…";
    try {
      const res = await fetch(api("api/holding-insights/run"), {
        method: "POST",
        headers: Object.assign({ "Content-Type": "application/json" }, headers()),
        body: JSON.stringify({ limit: limit }),
      });
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err.slice(0, 400));
      }
      const body = await (typeof parseRagJsonResponse === "function" ? parseRagJsonResponse(res) : res.json());
      main.innerHTML = "<p class=\"muted\">Starting new run…</p>";
      rememberJob(body.job_id);
      poll(body.job_id);
    } catch (err) {
      runBtn.disabled = false;
      progressEl.hidden = true;
      showError(err.message || String(err));
    }
  }

  runBtn.addEventListener("click", run);
  loadSaved();
})();