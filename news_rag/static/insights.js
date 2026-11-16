(function () {
  const main = document.getElementById("main");
  const dateEl = document.getElementById("date");
  const updated = document.getElementById("updated");
  const errorEl = document.getElementById("error");
  const progressEl = document.getElementById("progress");
  const createBtn = document.getElementById("create");
  const params = new URLSearchParams(window.location.search);
  let payload = null;
  let current = params.get("date") || "";

  function api(path) {
    const base = window.location.pathname.replace(/\/(insights|market-insights)\/?$/, "/");
    return base + String(path || "").replace(/^\//, "");
  }

  function headers() {
    const extra = {};
    const admin = params.get("admin_token");
    if (admin) {
      try { sessionStorage.setItem("insights_admin_token", admin); } catch (_e) { /* ignore */ }
    }
    try {
      const token = sessionStorage.getItem("insights_admin_token");
      if (token) extra["X-Admin-Token"] = token;
    } catch (_e) { /* ignore */ }
    return typeof ragHeaders === "function" ? ragHeaders(extra) : extra;
  }

  function istTime(iso) {
    if (!iso) return "—";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat("en-IN", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata" }).format(date) + " IST";
  }

  function rel(iso) {
    if (!iso) return "";
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return "";
    const hours = Math.round((Date.now() - then) / 3600000);
    if (hours < 1) return "just now";
    if (hours < 48) return hours + "h ago";
    return Math.round(hours / 24) + "d ago";
  }

  function arrow(tone) {
    if (tone === "positive") return "↑ ";
    if (tone === "negative") return "↓ ";
    return "• ";
  }

  function chart(viz) {
    const data = (viz && viz.data) || {};
    if (!viz || viz.type === "none") return "";
    if (viz.type === "index_move" || viz.type === "ohlc_week" || viz.type === "trend_line") {
      const rows = viz.type === "index_move" ? (data.range_5d || []) : (data.rows || []);
      const values = rows.map((row) => typeof row === "number" ? row : Number(row.close || row.week_change_pct || 0));
      return spark(values, viz.type === "index_move" ? "Nifty closes" : "Series");
    }
    if (viz.type === "flow_bars") return bars(data.days || [], "FII and DII nets");
    if (viz.type === "diverging_bars") return diverging(data.items || []);
    return "";
  }

  function spark(values, label) {
    if (!values.length) return "";
    const min = Math.min.apply(null, values);
    const max = Math.max.apply(null, values);
    const span = max - min || 1;
    const w = 280;
    const h = 70;
    const pts = values.map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * (w - 8) + 4;
      const y = h - 8 - ((value - min) / span) * (h - 16);
      return x + "," + y;
    }).join(" ");
    return '<svg class="chart" viewBox="0 0 ' + w + " " + h + '" role="img" aria-label="' + label + '"><title>' + label + "</title><polyline fill=\"none\" stroke=\"#2563eb\" stroke-width=\"2\" points=\"" + pts + '"/></svg>';
  }

  function bars(days, label) {
    const width = 280;
    const height = 80;
    const max = Math.max.apply(null, days.map((day) => Math.max(Math.abs(day.fii_net || 0), Math.abs(day.dii_net || 0))).concat([1]));
    const slot = width / Math.max(days.length, 1);
    let shapes = "";
    days.forEach((day, index) => {
      const x = index * slot + 4;
      ["fii_net", "dii_net"].forEach((key, offset) => {
        const value = Number(day[key] || 0);
        const bh = Math.abs(value) / max * 30;
        const y = value >= 0 ? 40 - bh : 40;
        const color = key === "fii_net" ? "#1d4ed8" : "#0f766e";
        shapes += '<rect x="' + (x + offset * 8) + '" y="' + y + '" width="6" height="' + bh + '" fill="' + color + '"><title>' + day.date + " " + key + " " + value + "</title></rect>";
      });
    });
    return '<svg class="chart" viewBox="0 0 ' + width + " " + height + '" role="img" aria-label="' + label + '"><title>' + label + '</title><line x1="0" y1="40" x2="' + width + '" y2="40" stroke="#cbd5e1"/>' + shapes + "</svg>";
  }

  function esc(text) {
    return String(text || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function pulseDrivers(viz, insightId) {
    if (insightId !== "sector_leaderboard" || !viz || viz.type !== "diverging_bars") return "";
    const drivers = (viz.data && viz.data.drivers) || null;
    if (!drivers) return "";
    const blocks = [];
    ["best", "worst"].forEach(function (side) {
      const block = drivers[side];
      if (!block || !block.total) return;
      const index = esc(block.index || block.sector || side);
      const pct = block.week_change_pct != null ? " (" + (block.week_change_pct >= 0 ? "+" : "") + Number(block.week_change_pct).toFixed(2) + "% week)" : "";
      const theme = block.theme ? '<p class="driver-theme"><strong>' + index + "</strong>" + pct + " — " + esc(block.theme) + "</p>" : "<p class=\"driver-theme\"><strong>" + index + "</strong>" + pct + "</p>";
      const meta = '<p class="muted driver-meta">' + block.total + " stories scanned · " + block.boosting + " boosting · " + block.weighing + " weighing on sector entities</p>";
      let lists = "";
      [["boosting", "Boosting headlines", "positive"], ["weighing", "Weighing headlines", "negative"]].forEach(function (row) {
        const key = row[0];
        const heading = row[1];
        const tone = row[2];
        const headlines = (block.headlines && block.headlines[key]) || [];
        if (!headlines.length) return;
        lists += '<p class="driver-heading ' + tone + '">' + heading + "</p><ul class="driver-list">';
        headlines.forEach(function (item) {
          const title = esc(item.title || "Story");
          const href = esc(item.url || "#");
          const src = esc(item.source || "");
          lists += "<li>" + (src ? '<span class="muted">' + src + " · </span>" : "") + '<a href="' + href + '" target="_blank" rel="noopener">' + title + "</a></li>";
        });
        lists += "</ul>";
      });
      blocks.push('<div class="driver-block">' + theme + meta + lists + "</div>");
    });
    if (!blocks.length) return "";
    return '<div class="pulse-drivers">' + blocks.join("") + "</div>";
  }

  function diverging(items) {
    if (!items.length) return '<p class="muted" aria-label="Sector movers">No sector bars</p>';
  const hasWeek = items.some((item) => item.week_change_pct != null);
    if (!hasWeek) {
      const text = items.slice(0, 6).map((item) => (item.display || item.sector || item.name || "") + " " + (item.score || "")).join(", ");
      return '<p class="muted" aria-label="Sector scores">' + text + "</p>";
    }
    const width = 300;
    const height = 88;
    const values = items.map((item) => Number(item.week_change_pct || 0));
    const maxAbs = Math.max.apply(null, values.map(Math.abs).concat([0.5]));
    let shapes = "";
    const slot = width / Math.max(items.length, 1);
    items.forEach((item, index) => {
      const value = Number(item.week_change_pct || 0);
      const label = item.display || item.sector || "";
      const bh = Math.abs(value) / maxAbs * 34;
      const y = value >= 0 ? 42 - bh : 42;
      const x = index * slot + slot / 2 - 14;
      const color = value >= 0 ? "#1d4ed8" : "#b91c1c";
      const pct = (value >= 0 ? "+" : "") + value.toFixed(2) + "%";
      shapes += '<rect x="' + x + '" y="' + y + '" width="28" height="' + bh + '" fill="' + color + '"><title>' + label + " " + pct + "</title></rect>";
      shapes += '<text x="' + (x + 14) + '" y="78" text-anchor="middle" font-size="10" fill="#475569">' + label.replace(/^Nifty /, "") + "</text>";
    });
    return '<svg class="chart" viewBox="0 0 ' + width + " " + height + '" role="img" aria-label="Index week moves"><title>Index week moves</title><line x1="0" y1="42" x2="' + width + '" y2="42" stroke="#cbd5e1"/>' + shapes + "</svg>";
  }

  const INSIGHT_ORDER = [
    "sector_leaderboard",
    "market_driver_digest",
    "fii_dii_flow_narrative",
    "sector_index_insights",
    "additional_insights",
  ];

  function card(item, label) {
    if (!item || (item.status !== "ok" && item.status !== "degraded")) {
      const closed = item && item.skip_reason === "market_closed";
      return '<article class="placeholder">' + label + ": " + (closed ? "Market closed" : "Not available for this date") + "</article>";
    }
    const chips = (item.chips || []).map((chip) => '<span class="chip ' + chip.tone + '">' + arrow(chip.tone) + chip.label + " " + chip.value + "</span>").join("");
    const sources = (item.sources || []).map((source) => '<div class="source">' + (source.source || "") + ' · <a href="' + source.url + '" target="_blank" rel="noopener">' + source.title + "</a> · " + rel(source.published_at) + "</div>").join("");
    const badge = item.prominence === "high" ? '<span class="badge">Notable</span>' : "";
    const review = item.status === "degraded" ? '<span class="badge">Review</span>' : "";
    const live = item.run_mode === "live" ? '<span class="badge">Live</span>' : "";
    const beta = item.insight_id === "additional_insights" ? '<span class="badge">Beta</span>' : "";
    const usage = item.usage || {};
    const showUsage = usage.calls || usage.input_tokens || usage.output_tokens;
    const callCount = usage.calls || (usage.calls_detail || []).length || 0;
    const usageLine = showUsage
      ? '<p class="usage"><strong>Tokens</strong> ' + callCount + " LLM calls · in " + (usage.input_tokens || 0) + " · out " + (usage.output_tokens || 0) + "</p>"
      : "";
    const stale = item.stale ? '<p class="banner">Showing last good card: ' + (item.stale_reason || "stale") + "</p>" : "";
    const logLink = item.log_url ? '<a class="log-link" href="' + item.log_url + '" target="_blank" rel="noopener">View log</a>' : "";
    const logPath = item.log_path ? '<p class="muted log-path">' + item.log_path + "</p>" : "";
    const vizHtml = chart(item.viz);
    const driverHtml = pulseDrivers(item.viz, item.insight_id);
    const callTable = (usage.calls_detail || []).length
      ? '<details class="why"><summary>LLM calls</summary><table class="log-table"><thead><tr><th>Label</th><th>Kind</th><th>In</th><th>Out</th></tr></thead><tbody>' +
        usage.calls_detail.map((row) => "<tr><td>" + (row.label || "") + "</td><td>" + (row.kind || "") + "</td><td>" + (row.input_tokens || 0) + "</td><td>" + (row.output_tokens || 0) + "</td></tr>").join("") +
        "</tbody></table></details>"
      : "";
    return '<article class="card"><div class="kicker"><span>' + label + "</span><span>" + badge + review + live + beta + '</span></div>' + stale + "<h3>" + item.headline + "</h3><p>" + item.body + "</p>" + vizHtml + driverHtml + '<div class="chips">' + chips + "</div>" + usageLine + callTable + '<details class="why"><summary>Why we say this</summary>' + (sources || '<p class="muted">No source linked.</p>') + "</details>" + logLink + logPath + "</article>";
  }

  function render() {
    if (!payload) return;
    dateEl.textContent = payload.date || "—";
    const totals = payload.token_totals || {};
    const totalLine = totals.total_input_tokens || totals.total_output_tokens
      ? " · tokens in " + (totals.total_input_tokens || 0) + " / out " + (totals.total_output_tokens || 0)
      : "";
    updated.textContent = "Last updated " + istTime(payload.generated_at) + totalLine;
    document.getElementById("prev").disabled = !payload.prev_date;
    document.getElementById("next").disabled = !payload.next_date;
    const insights = payload.insights || {};
    const sector = (payload.sector_performance || []).map((item) => card(item, "Sector")).join("");
    const extra = (payload.additional || []).map((item) => card(item, "Finding")).join("");
    main.innerHTML = [
      section("Market Today", card(insights.market_driver_digest, "Market Today")),
      section("Institutional Flows", card(insights.fii_dii_flow_narrative, "Institutional Flows")),
      section("Sector Pulse", card(insights.sector_leaderboard, "Sector Pulse")),
      section("Sector Performance", '<div class="grid">' + (sector || card(null, "Sector Performance")) + "</div>"),
      section("Additional Insights", '<div class="grid">' + (extra || '<article class="placeholder">No additional findings.</article>') + "</div>")
    ].join("");
  }

  function section(title, html) {
    return '<section class="section"><h2>' + title + "</h2>" + html + "</section>";
  }

  function showError(message) {
    errorEl.hidden = false;
    errorEl.innerHTML = message + ' <button type="button" id="retry">Retry</button>';
    const retry = document.getElementById("retry");
    if (retry) retry.onclick = () => load(current);
  }

  async function load(date) {
    errorEl.hidden = true;
    main.innerHTML = '<div class="skeleton"></div><div class="skeleton"></div>';
    if (params.get("fixture") === "1") {
      const response = await fetch("/static/insights.fixtures.json");
      payload = await response.json();
      render();
      return;
    }
    const query = date ? "?date=" + encodeURIComponent(date) : "";
    const response = await fetch(api("api/insights/daily" + query), { headers: headers() });
    const body = await (typeof parseRagJsonResponse === "function" ? parseRagJsonResponse(response) : response.json());
    if (!response.ok) {
      showError(body.detail || "Could not load insights.");
      return;
    }
    payload = body;
    current = body.date || date;
    render();
  }

  function progressLine(name, p) {
    const status = String((p && p.status) || "");
    const step = String((p && p.step) || "");
    if (status === "done" || status === "failed") {
      const tok = p && p.tokens ? " · " + p.tokens + " tok" : "";
      return "✓ " + name + ": " + status + tok;
    }
    if (status === "running" || step) return "… " + name + ": " + (step || status || "running");
    return "○ " + name + ": queued";
  }

  async function poll(jobId) {
    createBtn.disabled = true;
    createBtn.textContent = "Generating...";
    progressEl.hidden = false;
    const started = Date.now();
    const finished = new Set();
    let viewDate = current;
    for (let i = 0; i < 400; i += 1) {
      const response = await fetch(api("api/insights/jobs/" + jobId), { headers: headers() });
      const job = await response.json();
      if (job.trading_date) viewDate = job.trading_date;
      const order = (job.insights && job.insights.length) ? job.insights : INSIGHT_ORDER;
      const lines = order.map((name) => progressLine(name, (job.progress || {})[name]));
      progressEl.textContent = lines.join(" · ") + " (" + Math.round((Date.now() - started) / 1000) + "s)";
      let shouldRefresh = false;
      order.forEach((name) => {
        const p = (job.progress || {})[name] || {};
        if ((p.status === "done" || p.status === "failed") && !finished.has(name)) {
          finished.add(name);
          shouldRefresh = true;
        }
      });
      if (shouldRefresh) await load(viewDate || undefined);
      if (job.status === "done") break;
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    createBtn.disabled = false;
    createBtn.textContent = "Create insights";
    await load(viewDate || current || undefined);
  }

  createBtn.onclick = async function () {
    const response = await fetch(api("api/insights/generate"), { method: "POST", headers: Object.assign({ "Content-Type": "application/json" }, headers()), body: "{}" });
    const body = await response.json();
    const jobId = body.job_id || (body.detail && body.detail.job_id);
    if (jobId) poll(jobId);
    else showError("Could not start a run.");
  };
  document.getElementById("prev").onclick = function () { if (payload && payload.prev_date) load(payload.prev_date); };
  document.getElementById("next").onclick = function () { if (payload && payload.next_date) load(payload.next_date); };
  load(current).catch((error) => showError(String(error.message || error)));
})();
