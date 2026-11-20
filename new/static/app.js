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

  function pctClass(v) {
    if (v == null || v === "") return "";
    return Number(v) >= 0 ? "pos" : "neg";
  }

  function pctFmt(v) {
    if (v == null || v === "") return "—";
    var n = Number(v);
    if (isNaN(n)) return String(v);
    return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
  }

  function impactTable(title, rows) {
    if (!rows || !rows.length) {
      return "<p class='muted'>" + esc(title) + ": none priced.</p>";
    }
    var html =
      "<h4 class='table-title'>" +
      esc(title) +
      "</h4><table class='hold'><thead><tr><th>Stock</th><th>Wt%</th><th>1W%</th><th>Impact%</th></tr></thead><tbody>";
    rows.forEach(function (r) {
      html +=
        "<tr><td>" +
        esc(r.instrument_name) +
        "</td><td>" +
        esc(r.percentage) +
        "</td><td class='" +
        pctClass(r.change_1w_pct) +
        "'>" +
        esc(r.change_1w_pct == null ? "—" : r.change_1w_pct) +
        "</td><td class='" +
        pctClass(r.impact_1w_pct) +
        "'>" +
        esc(r.impact_1w_pct == null ? "—" : r.impact_1w_pct) +
        "</td></tr>";
    });
    return html + "</tbody></table>";
  }

  function attributionBlock(attr) {
    if (!attr || attr.nav_1w_pct == null) return "";
    var total =
      attr.total_stock_impact_1w_pct != null
        ? attr.total_stock_impact_1w_pct
        : attr.explained_1w_pct;
    return (
      "<p class='attrib-compact muted'>" +
      "NAV 1W <span class='" +
      pctClass(attr.nav_1w_pct) +
      "'>" +
      esc(attr.nav_1w_pct) +
      "%</span> · Top movers explain <span class='" +
      pctClass(total) +
      "'>" +
      esc(total) +
      "%</span> · Gap " +
      esc(attr.residual_1w_pct) +
      "%</p>"
    );
  }

  function newsWithCoverage(stockNews) {
    return (stockNews || []).filter(function (block) {
      return block.usable_news !== false && (block.articles || []).length && block.why;
    });
  }

  function newsRefs(stockNews) {
    var covered = newsWithCoverage(stockNews);
    if (!covered.length) return "";
    var html = "<details class='news-refs'><summary>News sources used</summary><ul>";
    covered.forEach(function (block) {
      var label =
        esc(block.instrument_name) +
        " (" +
        (block.move === "up" ? "+" : "") +
        esc(block.change_1w_pct) +
        "%)";
      html += "<li><strong>" + label + "</strong><ul>";
      (block.articles || []).forEach(function (a) {
        var t = esc(a.title || "Article");
        if (a.url) {
          html += "<li><a href='" + esc(a.url) + "' target='_blank' rel='noopener'>" + t + "</a></li>";
        } else {
          html += "<li>" + t + "</li>";
        }
      });
      html += "</ul></li>";
    });
    return html + "</ul></details>";
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

  function structuredInsight(n) {
    var gainers = n.gainers || [];
    var losers = n.losers || [];
    if (!n.opening && !gainers.length && !losers.length) {
      var text = n.insight || n.summary || "";
      var parts = text.split(/\n\n+/).filter(Boolean);
      var inner = parts.map(function (p) {
        return "<p>" + esc(p).replace(/\n/g, " ") + "</p>";
      }).join("");
      return "<div class='insight-body'>" + inner + "</div>";
    }
    var html = "<div class='insight-body'>";
    html += "<p class='lead'>" + esc(n.opening || "") + "</p>";
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
    var cush = (n.cushioned_funds || []).filter(Boolean);
    return (
      "<article class='card fund-card'>" +
      "<h3>" +
      esc(n.headline || f.scheme_name) +
      "</h3>" +
      "<p class='muted fund-sub'>" +
      esc(f.scheme_name) +
      " · " +
      esc(f.portfolio_pct) +
      "% of your book</p>" +
      attributionBlock(f.attribution) +
      structuredInsight(n) +
      newsRefs(f.stock_news) +
      (cush.length
        ? "<p class='muted cush'>Other funds that held up: " + esc(cush.join(", ")) + "</p>"
        : "") +
      "<div class='tables-bottom'>" +
      impactTable("Top 5 gainers (by impact)", f.gainers) +
      impactTable("Top 5 losers (by impact)", f.losers) +
      "</div></article>"
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
        var meta = data.meta || {};
        var head =
          "<p class='muted'>Equity funds: " +
          esc(data.fund_count) +
          (meta.total_aum_inr != null ? " · book ₹" + esc(meta.total_aum_inr) : "") +
          "</p>";
        var cards = (data.funds || []).map(fundCard).join("");
        main.innerHTML = head + cards;
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