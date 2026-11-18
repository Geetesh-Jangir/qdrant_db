(function () {
  const parts = window.location.pathname.split("/").filter(Boolean);
  const logIdx = parts.indexOf("log");
  const jobId = logIdx >= 0 ? parts[logIdx + 1] : "";
  const stockId = logIdx >= 0 ? parts[logIdx + 2] : "";
  const main = document.getElementById("main");
  const title = document.getElementById("title");
  const subtitle = document.getElementById("subtitle");
  const errorEl = document.getElementById("error");

  function api(path) {
    const base = window.location.pathname.replace(/\/holding-insights\/log\/[^/]+\/[^/]+\/?$/, "/");
    return base + String(path || "").replace(/^\//, "");
  }

  function headers() {
    return typeof ragHeaders === "function" ? ragHeaders() : {};
  }

  function escapeHtml(text) {
    return String(text || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function render(doc) {
    title.textContent = doc.stock_name || doc.stock_id;
    subtitle.textContent = "Job " + doc.job_id + " · " + (doc.outcome || "");
    let html = "";
    if (doc.usage) {
      html += "<section class=\"card\"><h2>LLM usage</h2>";
      var inst = doc.stock_name || doc.stock_id || "";
      if (inst || doc.sector_name) {
        html += "<p class=\"usage\">";
        if (inst) html += "<strong>" + escapeHtml(inst) + "</strong>";
        if (doc.stock_id && doc.stock_id !== inst) html += " · (" + escapeHtml(doc.stock_id) + ")";
        if (doc.sector_name) html += " · Sector: " + escapeHtml(doc.sector_name);
        html += "</p>";
      }
      html += "<p>Input tokens: <strong>" + (doc.usage.input_tokens || 0) + "</strong></p>";
      html += "<p>Output tokens: <strong>" + (doc.usage.output_tokens || 0) + "</strong></p>";
      html += "<p>LLM calls: <strong>" + (doc.usage.llm_calls || 0) + "</strong></p>";
      html += "<p>Model: " + escapeHtml(doc.usage.model || "—") + "</p></section>";
    }
    html += "<section class=\"card\"><h2>What happened</h2><ul>";
    (doc.timeline || []).forEach(function (step) {
      html += "<li><strong>" + escapeHtml(step.step) + ":</strong> " + escapeHtml(step.summary) + "</li>";
    });
    html += "</ul></section>";
    if (doc.price_summary) {
      html += "<section class=\"card\"><h2>Price (summary)</h2>";
      var wk = doc.price_summary.pattern_hints && doc.price_summary.pattern_hints.week_change_pct;
      if (wk != null) {
        var n = Number(wk);
        html += "<p>7-day change: <strong>" + (n > 0 ? "+" : "") + n + "%</strong></p>";
      }
      html += "<pre class=\"log-pre\">" + escapeHtml(JSON.stringify(doc.price_summary, null, 2)) + "</pre></section>";
    }
    if (doc.news_summary) {
      var arts = doc.news_summary.articles_sent || [];
      html += "<section class=\"card\"><h2>News</h2>";
      if (doc.news_summary.filters) {
        html += "<h3>Filters</h3><pre class=\"log-pre\">" + escapeHtml(JSON.stringify(doc.news_summary.filters, null, 2)) + "</pre>";
      }
      if (arts.length) {
        html += "<h3>Articles sent to the LLM (" + arts.length + ")</h3><ol class=\"article-links\">";
        arts.forEach(function (art) {
          var href = art.url || "#";
          html += "<li><a href=\"" + escapeHtml(href) + "\" target=\"_blank\" rel=\"noopener\">" +
            escapeHtml(art.headline || href) + "</a>";
          if (art.published_at) html += " <span class=\"muted\">" + escapeHtml(art.published_at) + "</span>";
          if (art.relevance != null) html += " <span class=\"muted\">· rel " + art.relevance + "</span>";
          html += "</li>";
        });
        html += "</ol>";
      }
      html += "<h3>Counts</h3><pre class=\"log-pre\">" + escapeHtml(JSON.stringify({
        entity: doc.news_summary.entity,
        scanned: doc.news_summary.scanned,
        after_gate: doc.news_summary.after_gate,
        sent_to_llm: doc.news_summary.sent_to_llm,
        window: doc.news_summary.window,
      }, null, 2)) + "</pre></section>";
    }
    if (doc.headline) {
      html += "<section class=\"card\"><h2>Headline</h2><p class=\"insight-body\">" + escapeHtml(doc.headline) + "</p></section>";
    }
    if (doc.insight_lines && doc.insight_lines.length) {
      html += "<section class=\"card\"><h2>Insight</h2>";
      html += "<p class=\"insight-body\">" + escapeHtml(doc.insight_lines.join(" ")) + "</p>";
      html += "</section>";
    }
    if (doc.llm_response_preview) {
      html += "<section class=\"card\"><h2>LLM response (preview)</h2><pre class=\"log-pre\">" + escapeHtml(doc.llm_response_preview) + "</pre></section>";
    }
    main.innerHTML = html;
  }

  async function load() {
    if (!jobId || !stockId) {
      errorEl.hidden = false;
      errorEl.textContent = "Bad log URL.";
      return;
    }
    try {
      const res = await fetch(api("api/holding-insights/logs/" + encodeURIComponent(jobId) + "/" + encodeURIComponent(stockId)), {
        headers: headers(),
      });
      if (!res.ok) throw new Error("Log not found");
      const doc = await (typeof parseRagJsonResponse === "function" ? parseRagJsonResponse(res) : res.json());
      render(doc);
    } catch (err) {
      errorEl.hidden = false;
      errorEl.textContent = err.message || String(err);
    }
  }

  load();
})();