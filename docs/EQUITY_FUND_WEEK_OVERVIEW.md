# Equity Fund Week Insights — Overview for investors and product teams

This document describes **Equity Fund Week Insights**: the page at **http://localhost:8080/equity-fund-week** (linked as **Equity fund week** from News Insight). It summarizes how your **equity mutual funds** moved over the **last seven settled trading days**, which **holdings** helped or hurt, and—when news is available—a short **plain-language story** for each fund.

---

## A. What this feature does

**What it is.** A one-click (or one-run) weekly digest for **equity schemes only**. For each fund you choose, it shows:

- **Fund NAV change over the last week** (settled window, not a custom date range).
- **Top gainers and top losers** among holdings: weight in the fund, **one-week stock price change**, and estimated **impact on NAV**.
- A **written summary** that ties the week’s move to named holdings and, where possible, **recent financial news** about those names or related sectors.
- Optional **“Dry run”** mode: numbers and holding tables only, with **no news lookup and no AI summary**.

**Primary purpose.** Answer: *“How did this equity fund (or my equity funds) do this week, and what in the portfolio likely drove it?”*—without reading holding files and news feeds fund by fund.

**What it is not.**

- It does **not** cover **debt, liquid, gold, or hybrid** funds when you enter a fund ISIN (those are rejected). With a **CRN**, only **equity holdings** in the portfolio are included; other asset types are skipped.
- It does **not** give buy, sell, hold, or switch advice, targets, or forecasts.
- It does **not** let you pick a different time window (the week is fixed at **about seven trading days**).
- Holding-level explanations are **indicative**: top movers plus news do not always fully “explain” the entire NAV move.

---

## B. How to use it

1. Open **http://localhost:8080/equity-fund-week** (or use **Equity fund week** in the navigation bar on other Insight pages).
2. Enter **either** a **CRN** (your portfolio reference) **or** a single **fund ISIN**—**not both**.
3. **Optional (CRN only):** set **Top N funds** to limit how many equity schemes to process (largest by value in the portfolio first). Leave blank to run **all** equity funds in the portfolio.
4. **Optional:** tick **Dry run** if you only want NAV and holding price tables (faster; no news or AI text).
5. Click **Run**. Wait while fund data, prices, and (unless dry run) news are gathered.
6. Read one **card per fund**: headline summary, “What helped” / “What held back” sections when available, and tables for **Top gainers** and **Top losers**.

**CRN mode** shows each fund’s **share of your portfolio (%)** next to the name. **ISIN mode** looks at **one named scheme** and does not show portfolio weight.

If your environment uses an **app token** for Insight APIs (same as Ask a Question), open the site once with a valid token in the session so **Run** is authorized—otherwise the request may be rejected.

---

## C. Inputs you can provide

| Input | Required? | What it does |
|--------|-----------|----------------|
| **CRN** | One of CRN or ISIN | Loads **equity mutual fund holdings** from your RupeeStop portfolio workspace and runs the week insight for each (or for the top **N** by value). |
| **Fund ISIN** | One of CRN or ISIN | Runs the insight for **one** scheme identified by AMFI-style ISIN (typically starts with `INF`). Scheme must be classified as **equity**. |
| **Top N funds** | No (CRN only) | Integer from **1** to **50**. Ignored when ISIN is filled. Empty means **all** equity funds in the portfolio. |
| **Dry run** | No | When checked, returns **NAV and holding moves only**—no news retrieval and no AI-written narrative. |

**Rules enforced on the page**

- You must supply **exactly one** of CRN or ISIN.
- ISIN must be a valid **11-character** fund ISIN shape (`INF` plus nine alphanumeric characters).
- Invalid CRN, unknown ISIN, or a **non-equity** ISIN produces a clear error message instead of a fund card.

---

## D. Limitations and what to expect

**Scope and data**

- **Time window:** Last **seven settled trading days** only (not calendar week, not month/year custom ranges).
- **Equity only:** Debt, liquid, arbitrage-only, and other non-equity ISINs are not supported in single-fund mode.
- **Holdings snapshot:** Weights and names come from **fund holdings data** in the system; they may not match today’s live AMFI disclosure.
- **Stock prices:** One-week moves use available **market price history**; some instruments may show missing weekly change.
- **News:** Articles are limited to the same week window. Holdings **without** matching news may be **dropped** from news-backed explanations; the summary still uses price and impact numbers where present.
- **Attribution:** Estimated impact from top gainers and losers often **does not add up to 100%** of the fund’s NAV move; the UI may note **unaccounted** residue.

**Portfolio (CRN) mode**

- Requires a **valid CRN** and working **portfolio access** on the server. If portfolio lookup is not configured, you will see a failure message instead of fund cards.
- If the portfolio has **no equity funds**, you get an empty result with a short message—not an error.
- Processing **many** large equity holdings can take **longer** than a single ISIN run.

**Output quality**

- AI summaries are **narrative interpretations** of fetched facts and news snippets, not audited research or compliance advice.
- **Dry run** is useful for checking numbers when news or LLM output is unavailable or you want a quick check.

---

## E. Example equity fund ISINs (regular plan, growth)

You can paste any valid **equity** scheme ISIN. Examples below are **regular plan – growth** schemes from the project’s fund catalogue (names for reference only):

| Scheme (short label) | Example ISIN |
|----------------------|--------------|
| HDFC Large Cap Fund – Growth | `INF179K01BE2` |
| Axis Large Cap Fund – Regular Plan – Growth | `INF846K01164` |
| Mirae Asset Large Cap Fund – Regular Plan – Growth | `INF769K01010` |
| Parag Parikh Flexi Cap Fund – Regular Plan – Growth | `INF879O01019` |
| Kotak Flexi Cap Fund – Growth | `INF174K01336` |
| Aditya Birla Sun Life Large Cap Fund – Regular Plan – Growth | `INF209K01BR9` |

**Direct plan** schemes use different ISINs; any **equity** ISIN that resolves in the fund directory should work the same way.

---

## F. Quick reference

| Topic | Expectation |
|--------|-------------|
| **Best for** | “What happened to my equity funds **this week**?” and “Which holdings moved the NAV?” |
| **Inputs** | CRN **or** one ISIN; optional Top N (CRN); optional dry run |
| **Output** | Per-fund NAV % change, gainer/loser tables, optional news-backed summary |
| **Hard limits** | ~7 trading days; equity only; no advice; CRN needs valid portfolio access |
| **If something fails** | Check CRN/ISIN; confirm scheme is equity; try dry run; use a single ISIN to isolate one fund |

---

*Document based on the Equity Fund Week page (`/equity-fund-week`) and its run action for investors and product teams. It intentionally omits engineering and architecture detail.*