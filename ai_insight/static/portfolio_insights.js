(function () {
  const main = document.getElementById("main");
  const errorEl = document.getElementById("error");
  const banner = document.getElementById("ready-banner");
  const tradingDateEl = document.getElementById("trading-date");
  const createBtn = document.getElementById("create");
  const crnEl = document.getElementById("crn");

  function api(path) {
    const base = window.location.pathname.replace(/\/portfolio-insights\/?$/, "/");
    return base + String(path || "").replace(/^\//, "");
  }

  function headers() {
    const extra = {};
    const params = new URLSearchParams(window.location.search);
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

  function esc(text) {
    const d = document.createElement("div");
    d.textContent = text == null ? "" : String(text);
    return d.innerHTML;
  }

  function chipHtml(chips) {
    return (chips || []).map(function (c) {
      const tone = c.tone && c.tone !== "neutral" ? " " + c.tone : "";
      return '<span class="chip' + tone + '">' + esc(c.label) + ": " + esc(c.value) + "</span>";
    }).join("");
  }

  function card(item, label) {
    if (!item) return '<article class="placeholder">No insight.</article>';
    const meta = item.match_meta || {};
    const weight = meta.weight_pct != null ? " · " + meta.weight_pct.toFixed(2) + "% of book" : "";
    const sub = meta.sector ? esc(meta.sector) + weight : meta.instrument_name ? esc(meta.instrument_name) + weight : "";
    const log = item.log_url ? '<a class="log-link" href="' + esc(item.log_url) + '">Run log</a>' : "";
    return (
      '<article class="card">' +
      '<div class="kicker"><span>' + esc(label) + "</span><span>" + esc(sub) + "</span></div>" +
      "<h3>" + esc(item.headline) + "</h3>" +
      "<p>" + esc(item.body).replace(/\n/g, "<br>") + "</p>" +
      '<div class="chips">' + chipHtml(item.chips) + "</div>" +
      log +
      "</article>"
    );
  }

  function section(title, html) {
    return '<section class="section"><h2>' + esc(title) + "</h2>" + html + "</section>";
  }

  function renderReady(body) {
    tradingDateEl.textContent = "Trading day " + (body.trading_date || "—");
    if (body.ready) {
      banner.hidden = true;
      createBtn.disabled = false;
      return;
    }
    banner.hidden = false;
    const missing = (body.missing || []).join(", ");
    banner.innerHTML =
      "Insights are not created and stored for this trading day" +
      (body.trading_date ? " (" + esc(body.trading_date) + ")" : "") +
      ". Missing: " + esc(missing || "unknown") +
      '. Run <a href="../insights">Create insights</a> on Market Insights and ' +
      '<a href="../holding-insights">Run</a> on Stock Holding Insights, then return here.';
    createBtn.disabled = false;
  }

  function renderCompose(body) {
    if (body.status !== "ok") {
      errorEl.hidden = false;
      errorEl.textContent = body.message || body.status;
      return;
    }
    errorEl.hidden = true;
    const common = (body.common || []).map(function (c) {
      const labels = { market_driver_digest: "Market Today", fii_dii_flow_narrative: "Institutional Flows", sector_leaderboard: "Sector Pulse" };
      return card(c, labels[c.section] || c.section || "Market");
    }).join("");
    const sectors = (body.sectors || []).map(function (c) { return card(c, "Your sector"); }).join("");
    const holdings = (body.holdings || []).map(function (c) { return card(c, "Your holding"); }).join("");
    main.innerHTML = [
      section("Common insights", '<div class="grid">' + (common || '<article class="placeholder">None</article>') + "</div>"),
      section("Sector insights", '<div class="grid">' + (sectors || '<article class="placeholder">No matching sector insights.</article>') + "</div>"),
      section("Holding insights", '<div class="grid">' + (holdings || '<article class="placeholder">No matching holding insights.</article>') + "</div>")
    ].join("");
  }

  async function loadReady() {
    const response = await fetch(api("api/portfolio-insights/ready"), { headers: headers() });
    const body = await (typeof parseRagJsonResponse === "function" ? parseRagJsonResponse(response) : response.json());
    if (!response.ok) {
      errorEl.hidden = false;
      errorEl.textContent = body.detail || "Could not check readiness.";
      return;
    }
    renderReady(body);
  }

  createBtn.onclick = async function () {
    const crn = (crnEl.value || "").trim();
    if (!crn) {
      errorEl.hidden = false;
      errorEl.textContent = "Enter a CRN.";
      return;
    }
    errorEl.hidden = true;
    main.innerHTML = '<div class="skeleton"></div>';
    createBtn.disabled = true;
    try {
      const response = await fetch(api("api/portfolio-insights/compose"), {
        method: "POST",
        headers: Object.assign({ "Content-Type": "application/json" }, headers()),
        body: JSON.stringify({ crn: crn })
      });
      const body = await (typeof parseRagJsonResponse === "function" ? parseRagJsonResponse(response) : response.json());
      if (body.status === "missing_insights") {
        renderReady(body);
        errorEl.hidden = false;
        errorEl.textContent = body.message || "Insights not ready.";
        main.innerHTML = "";
        return;
      }
      renderCompose(body);
    } catch (err) {
      errorEl.hidden = false;
      errorEl.textContent = String(err.message || err);
    } finally {
      createBtn.disabled = false;
    }
  };

  loadReady().catch(function (err) {
    errorEl.hidden = false;
    errorEl.textContent = String(err.message || err);
  });
})();