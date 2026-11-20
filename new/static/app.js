(function () {
  const main = document.getElementById("main");
  const errorEl = document.getElementById("error");
  const runBtn = document.getElementById("run");
  const crnEl = document.getElementById("crn");
  const isinEl = document.getElementById("isin");
  const topNEl = document.getElementById("top_n");
  const dryEl = document.getElementById("dry_run");

  function headers() {
    return typeof ragHeaders === "function" ? ragHeaders() : {};
  }

  function errText(detail) {
    if (!detail) return "";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map(function (x) {
          return (x && x.msg) || JSON.stringify(x);
        })
        .join("; ");
    }
    return String(detail);
  }

  function esc(text) {
    const d = document.createElement("div");
    d.textContent = text == null ? "" : String(text);
    return d.innerHTML;
  }

  function pctFmt(v) {
    if (v == null || v === "") return "—";
    var n = Number(v);
    if (isNaN(n)) return String(v);
    return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
  }

  function syncTopNState() {
    var isinOn = (isinEl && (isinEl.value || "").trim().length > 0);
    if (topNEl) {
      topNEl.disabled = isinOn;
      topNEl.style.opacity = isinOn ? "0.5" : "1";
    }
  }

  function onCrnInput() {
    if (!crnEl || !isinEl) return;
    if ((crnEl.value || "").trim()) {
      isinEl.value = "";
      isinEl.disabled = true;
    } else {
      isinEl.disabled = false;
    }
    syncTopNState();
  }

  function onIsinInput() {
    if (!crnEl || !isinEl) return;
    if ((isinEl.value || "").trim()) {
      crnEl.value = "";
      crnEl.disabled = true;
    } else {
      crnEl.disabled = false;
    }
    syncTopNState();
  }

  if (crnEl) crnEl.addEventListener("input", onCrnInput);
  if (isinEl) isinEl.addEventListener("input", onIsinInput);
  syncTopNState();

  function paragraphSection(items, heading) {
    if (!items || !items.length) return "";
    var html = "<h4>" + esc(heading) + "</h4>";
    items.forEach(function (g) {
      var ch = g.change_1w_pct != null ? " (" + pctFmt(g.change_1w_pct) + ")" : "";
      html +=
        "<p class='stock-para'><strong>" +
        esc(g.name) +
        ch +
        ".</strong> " +
        esc(g.why || "") +
        "</p>";
    });
    return html;
  }

  function summaryBlock(text) {
    if (!text) return "";
    return text
      .split(/\n\n+/)
      .filter(Boolean)
      .map(function (p) {
        return "<p class='fund-summary'>" + esc(p).replace(/\n/g, " ") + "</p>";
      })
      .join("");
  }

  function structuredInsight(n) {
    var gainers = n.gainers || [];
    var losers = n.losers || [];
    var lead = n.fund_summary || n.summary || "";
    if (!lead && !n.opening && !gainers.length && !losers.length) {
      var text = n.insight || "";
      return "<div class='insight-body'>" + summaryBlock(text) + "</div>";
    }
    var html = "<div class='insight-body'>";
    html += summaryBlock(lead || n.opening);
    html += paragraphSection(gainers, "What helped");
    html += paragraphSection(losers, "What held back");
    if (n.closing) html += "<p class='closing'>" + esc(n.closing) + "</p>";
    html += "</div>";
    return html;
  }

  function moverTable(rows, title) {
    if (!rows || !rows.length) return "";
    var html =
      "<p class='table-title'>" +
      esc(title) +
      "</p><table class='hold'><thead><tr><th>Holding</th><th>Weight %</th><th>1w price</th><th>NAV impact</th></tr></thead><tbody>";
    rows.forEach(function (h) {
      var ch = h.change_1w_pct;
      var n = ch == null ? NaN : Number(ch);
      var cls = !isNaN(n) && n < 0 ? "neg" : !isNaN(n) && n > 0 ? "pos" : "";
      html +=
        "<tr><td>" +
        esc(h.instrument_name) +
        "</td><td>" +
        (h.percentage != null ? Number(h.percentage).toFixed(2) : "—") +
        "</td><td class='" +
        cls +
        "'>" +
        pctFmt(ch) +
        "</td><td class='" +
        cls +
        "'>" +
        pctFmt(h.impact_1w_pct) +
        "</td></tr>";
    });
    return html + "</tbody></table>";
  }

  function fundCard(item, meta) {
    if (item.status === "failed") {
      return "<article class='card'><p>" + esc(item.error || "Failed") + "</p></article>";
    }
    var f = item.facts || {};
    var n = item.narrative || {};
    var navLine =
      f.nav_1w_pct != null
        ? "<p class='muted fund-nav-week'>Fund NAV, last week: <strong>" + pctFmt(f.nav_1w_pct) + "</strong></p>"
        : "";
    var tables =
      "<div class='tables-bottom'>" +
      moverTable(f.gainers, "Top gainers (1 week)") +
      moverTable(f.losers, "Top losers (1 week)") +
      "</div>";
    var badge =
      n.narrative_source === "dry_run"
        ? "<p class='banner'>Dry run — NAV and holding prices only (no news or LLM).</p>"
        : "";
    var isinMode = meta && meta.mode === "isin";
  var showPct =
    !isinMode && f.portfolio_pct != null && f.portfolio_pct !== "";
    var pctLine = showPct
      ? "<p class='muted fund-sub'>" + Number(f.portfolio_pct).toFixed(2) + "% of portfolio</p>"
      : "";
    return (
      "<article class='card fund-card'>" +
      "<h3>" +
      esc(n.headline || f.scheme_name) +
      "</h3>" +
      pctLine +
      navLine +
      badge +
      structuredInsight(n) +
      tables +
      "</article>"
    );
  }

  function parseResponse(r) {
    if (typeof parseRagJsonResponse === "function") {
      return parseRagJsonResponse(r);
    }
    return r.json().then(function (j) {
      if (!r.ok) throw new Error(errText(j.detail) || r.statusText);
      return j;
    });
  }

  runBtn.addEventListener("click", function () {
    errorEl.hidden = true;
    var crn = (crnEl && crnEl.value || "").trim();
    var isin = (isinEl && isinEl.value || "").trim();
    if (crn && isin) {
      errorEl.textContent = "Fill either CRN or ISIN, not both.";
      errorEl.hidden = false;
      return;
    }
    if (!crn && !isin) {
      errorEl.textContent = "Enter a CRN or an equity fund ISIN.";
      errorEl.hidden = false;
      return;
    }
    main.innerHTML = "<p class='muted'>Fetching fund data and prices…</p>";
    runBtn.disabled = true;
    var body = { dry_run: !!dryEl.checked };
    if (isin) {
      body.isin = isin;
    } else {
      body.crn = crn;
      var tn = parseInt(topNEl.value, 10);
      if (!isNaN(tn) && tn > 0) body.top_n = tn;
    }

    fetch("/api/equity-fund-week/run", {
      method: "POST",
      headers: Object.assign({ "Content-Type": "application/json" }, headers()),
      body: JSON.stringify(body),
    })
      .then(parseResponse)
      .then(function (data) {
        if (data.status === "bad_crn") {
          errorEl.textContent = data.message || "Bad CRN";
          errorEl.hidden = false;
          main.innerHTML = "";
          return;
        }
        if (data.status === "bad_isin") {
          errorEl.textContent = data.message || "Bad ISIN";
          errorEl.hidden = false;
          main.innerHTML = "";
          return;
        }
        if (data.status === "fund_not_found") {
          errorEl.textContent = data.message || "Fund not found";
          errorEl.hidden = false;
          main.innerHTML = "";
          return;
        }
        if (data.status === "not_equity") {
          errorEl.textContent = data.message || "Only equity schemes are supported.";
          errorEl.hidden = false;
          main.innerHTML = "";
          return;
        }
        if (data.status !== "ok") {
          errorEl.textContent = data.message || "Request failed";
          errorEl.hidden = false;
          main.innerHTML = "";
          return;
        }
        var funds = data.funds || [];
        if (!funds.length) {
          main.innerHTML =
            "<p class='muted placeholder'>" + esc(data.message || "No equity funds in this portfolio.") + "</p>";
          return;
        }
        var meta = data.meta || {};
        var metaLine =
          data.dry_run && data.fund_count
            ? "<p class='muted'>Dry run — showing " + esc(String(data.fund_count)) + " fund(s), last 7 days.</p>"
            : meta.mode === "isin"
              ? "<p class='muted'>Single fund (ISIN) — last 7 days.</p>"
              : "";
        main.innerHTML = metaLine + funds.map(function (f) { return fundCard(f, meta); }).join("");
      })
      .catch(function (e) {
        errorEl.textContent = e.message || String(e);
        errorEl.hidden = false;
        main.innerHTML = "";
      })
      .finally(function () {
        runBtn.disabled = false;
      });
  });
})();