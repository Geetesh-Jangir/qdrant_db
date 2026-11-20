(function () {
  const main = document.getElementById("main");
  const errorEl = document.getElementById("error");
  const runBtn = document.getElementById("run");
  const crnEl = document.getElementById("crn");
  const topNEl = document.getElementById("top_n");
  const dryEl = document.getElementById("dry_run");

  function headers() {
    return typeof ragHeaders === "function" ? ragHeaders() : {};
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

  function fundCard(item) {
    if (item.status === "failed") {
      return "<article class='card'><p>" + esc(item.error || "Failed") + "</p></article>";
    }
    var f = item.facts || {};
    var n = item.narrative || {};
    var navLine =
      f.nav_1w_pct != null
        ? "<p class='muted fund-nav-week'>Fund NAV, last week: <strong>" + pctFmt(f.nav_1w_pct) + "</strong></p>"
        : "";
    return (
      "<article class='card fund-card'>" +
      "<h3>" +
      esc(n.headline || f.scheme_name) +
      "</h3>" +
      navLine +
      structuredInsight(n) +
      "</article>"
    );
  }

  runBtn.addEventListener("click", function () {
    errorEl.hidden = true;
    main.innerHTML = "<p class='muted'>Fetching portfolio, prices, and news…</p>";
    runBtn.disabled = true;
    var body = {
      crn: (crnEl.value || "").trim(),
      dry_run: !!dryEl.checked,
    };
    var tn = parseInt(topNEl.value, 10);
    if (!isNaN(tn) && tn > 0) body.top_n = tn;

    fetch("/api/equity-fund-week/run", {
      method: "POST",
      headers: Object.assign({ "Content-Type": "application/json" }, headers()),
      body: JSON.stringify(body),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          if (!r.ok) throw new Error(j.detail || r.statusText);
          return j;
        });
      })
      .then(function (data) {
        if (data.status === "bad_crn") {
          errorEl.textContent = data.message || "Bad CRN";
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
        var cards = (data.funds || []).map(fundCard).join("");
        main.innerHTML = cards;
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