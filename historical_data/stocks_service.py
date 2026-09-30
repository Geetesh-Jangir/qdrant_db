"""Stock price range, returns, and sentiment service using Yahoo Finance (yfinance).

Features:
- Focused retrieval: fetches price movement ONLY for holdings considered in insights / top holdings.
- Graceful degradation: handles unlisted/unavailable tickers without failure.
- In-memory caching with 1-hour TTL for fast sub-millisecond retrieval.
- Comprehensive Indian NSE ticker mapping for top holdings across mutual fund portfolios.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import yfinance as yf

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600.0  # 1 hour cache

# In-memory cache for stock profiles
_STOCK_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_TIMESTAMP: dict[str, float] = {}

# Curated mapping of standard company names to NSE Yahoo Finance symbols
NAME_TO_NSE_TICKER: dict[str, str] = {
    # Heavyweights & Banks
    "icici bank limited": "ICICIBANK.NS",
    "icici bank": "ICICIBANK.NS",
    "hdfc bank limited": "HDFCBANK.NS",
    "hdfc bank": "HDFCBANK.NS",
    "state bank of india": "SBIN.NS",
    "sbi": "SBIN.NS",
    "axis bank limited": "AXISBANK.NS",
    "axis bank": "AXISBANK.NS",
    "kotak mahindra bank limited": "KOTAKBANK.NS",
    "kotak mahindra bank": "KOTAKBANK.NS",
    "the federal bank limited": "FEDERALBNK.NS",
    "federal bank": "FEDERALBNK.NS",
    "indusind bank limited": "INDUSINDBK.NS",
    "indusind bank": "INDUSINDBK.NS",
    "bank of baroda": "BANKBARODA.NS",
    "punjab national bank": "PNB.NS",
    "canara bank": "CANBK.NS",
    "idfc first bank limited": "IDFCFIRSTB.NS",
    "idfc first bank": "IDFCFIRSTB.NS",
    "bandhan bank limited": "BANDHANBNK.NS",
    "bandhan bank": "BANDHANBNK.NS",
    "au small finance bank limited": "AUBANK.NS",
    "au small finance bank": "AUBANK.NS",

    # NBFC & Financial Services
    "bajaj finance limited": "BAJFINANCE.NS",
    "bajaj finance": "BAJFINANCE.NS",
    "bajaj finserv limited": "BAJAJFINSV.NS",
    "bajaj finserv": "BAJAJFINSV.NS",
    "shriram finance limited": "SHRIRAMFIN.NS",
    "shriram finance": "SHRIRAMFIN.NS",
    "cholamandalam investment and finance company limited": "CHOLAFIN.NS",
    "cholamandalam investment": "CHOLAFIN.NS",
    "muthoot finance limited": "MUTHOOTFIN.NS",
    "muthoot finance": "MUTHOOTFIN.NS",
    "hまれ life insurance company limited": "HDFCLIFE.NS",
    "hdfc life insurance company limited": "HDFCLIFE.NS",
    "sbi life insurance company limited": "SBILIFE.NS",
    "icici prudential life insurance company limited": "ICICIPRULI.NS",
    "icici lombard general insurance company limited": "ICICIGI.NS",
    "life insurance corporation of india": "LICI.NS",
    "lic": "LICI.NS",
    "power finance corporation limited": "PFC.NS",
    "rural electrification corporation": "RECLTD.NS",
    "rec limited": "RECLTD.NS",

    # IT & Technology
    "infosys limited": "INFY.NS",
    "infosys": "INFY.NS",
    "tata consultancy services limited": "TCS.NS",
    "tata consultancy services": "TCS.NS",
    "tcs": "TCS.NS",
    "hcl technologies limited": "HCLTECH.NS",
    "hcl tech": "HCLTECH.NS",
    "hcl technologies": "HCLTECH.NS",
    "wipro limited": "WIPRO.NS",
    "wipro": "WIPRO.NS",
    "tech mahindra limited": "TECHM.NS",
    "tech mahindra": "TECHM.NS",
    "ltimindtree limited": "LTIM.NS",
    "ltimindtree": "LTIM.NS",
    "persistent systems limited": "PERSISTENT.NS",
    "persistent systems": "PERSISTENT.NS",
    "coforge limited": "COFORGE.NS",
    "coforge": "COFORGE.NS",
    "mphasis limited": "MPHASIS.NS",
    "tata elxsi limited": "TATAELXSI.NS",
    "kpit technologies limited": "KPITTECH.NS",

    # Industrial & Capital Goods
    "larsen & toubro limited": "LT.NS",
    "larsen and toubro limited": "LT.NS",
    "larsen & toubro": "LT.NS",
    "l&t": "LT.NS",
    "siemens limited": "SIEMENS.NS",
    "siemens": "SIEMENS.NS",
    "abb india limited": "ABB.NS",
    "abb india": "ABB.NS",
    "bharat electronics limited": "BEL.NS",
    "bharat electronics": "BEL.NS",
    "hindustan aeronautics limited": "HAL.NS",
    "hal": "HAL.NS",
    "cummins india limited": "CUMMINSIND.NS",
    "polycab india limited": "POLYCAB.NS",
    "havells india limited": "HAVELLS.NS",
    "bhel": "BHEL.NS",
    "bharat heavy electricals limited": "BHEL.NS",

    # Telecom, Consumer, Retail & Internet
    "bharti airtel limited": "BHARTIARTL.NS",
    "bharti airtel": "BHARTIARTL.NS",
    "airtel": "BHARTIARTL.NS",
    "reliance industries limited": "RELIANCE.NS",
    "reliance industries": "RELIANCE.NS",
    "reliance": "RELIANCE.NS",
    "itc limited": "ITC.NS",
    "itc": "ITC.NS",
    "hindustan unilever limited": "HINDUNILVR.NS",
    "hindustan unilever": "HINDUNILVR.NS",
    "hul": "HINDUNILVR.NS",
    "nestle india limited": "NESTLEIND.NS",
    "nestle india": "NESTLEIND.NS",
    "britannia industries limited": "BRITANNIA.NS",
    "trent limited": "TRENT.NS",
    "trent": "TRENT.NS",
    "zomato limited": "ZOMATO.NS",
    "zomato": "ZOMATO.NS",
    "titan company limited": "TITAN.NS",
    "titan": "TITAN.NS",
    "asian paints limited": "ASIANPAINT.NS",
    "asian paints": "ASIANPAINT.NS",
    "varun beverages limited": "VBL.NS",
    "godrej consumer products limited": "GODREJCP.NS",
    "marico limited": "MARICO.NS",
    "dabur india limited": "DABUR.NS",
    "tata consumer products limited": "TATACONSUM.NS",
    "avenue supermarts limited": "DMART.NS",
    "dmart": "DMART.NS",
    "interglobe aviation limited": "INDIGO.NS",
    "indigo": "INDIGO.NS",

    # Automobiles & Auto Components
    "maruti suzuki india limited": "MARUTI.NS",
    "maruti suzuki": "MARUTI.NS",
    "maruti": "MARUTI.NS",
    "tata motors limited": "TATAMOTORS.NS",
    "tata motors": "TATAMOTORS.NS",
    "mahindra & mahindra limited": "M&M.NS",
    "mahindra and mahindra": "M&M.NS",
    "m&m": "M&M.NS",
    "bajaj auto limited": "BAJAJ-AUTO.NS",
    "bajaj auto": "BAJAJ-AUTO.NS",
    "hero motocorp limited": "HEROMOTOCO.NS",
    "eicher motors limited": "EICHERMOT.NS",
    "tvs motor company limited": "TVSMOTOR.NS",
    "samvardhana motherson international limited": "MOTHERSON.NS",
    "motherson": "MOTHERSON.NS",
    "bosch limited": "BOSCHLTD.NS",
    "mrf limited": "MRF.NS",
    "balkrishna industries limited": "BALKRISIND.NS",

    # Healthcare & Pharma
    "max healthcare institute limited": "MAXHEALTH.NS",
    "max healthcare": "MAXHEALTH.NS",
    "sun pharmaceutical industries limited": "SUNPHARMA.NS",
    "sun pharma": "SUNPHARMA.NS",
    "cipla limited": "CIPLA.NS",
    "cipla": "CIPLA.NS",
    "dr. reddy's laboratories limited": "DRREDDY.NS",
    "dr reddys": "DRREDDY.NS",
    "apollo hospitals enterprise limited": "APOLLOHOSP.NS",
    "apollo hospitals": "APOLLOHOSP.NS",
    "divi's laboratories limited": "DIVISLAB.NS",
    "divis lab": "DIVISLAB.NS",
    "torrent pharmaceuticals limited": "TORNTPHARM.NS",
    "lupin limited": "LUPIN.NS",
    "aurobindo pharma limited": "AUROPHARMA.NS",
    "mankind pharma limited": "MANKIND.NS",
    "fortis healthcare limited": "FORTIS.NS",

    # Energy, Oil & Gas, Utilities, Commodities
    "oil and natural gas corporation limited": "ONGC.NS",
    "ongc": "ONGC.NS",
    "ntpc limited": "NTPC.NS",
    "ntpc": "NTPC.NS",
    "power grid corporation of india limited": "POWERGRID.NS",
    "power grid": "POWERGRID.NS",
    "coal india limited": "COALINDIA.NS",
    "coal india": "COALINDIA.NS",
    "bharat petroleum corporation limited": "BPCL.NS",
    "bpcl": "BPCL.NS",
    "indian oil corporation limited": "IOC.NS",
    "ioc": "IOC.NS",
    "gail (india) limited": "GAIL.NS",
    "gail": "GAIL.NS",
    "tata power company limited": "TATAPOWER.NS",
    "tata power": "TATAPOWER.NS",
    "adani enterprises limited": "ADANIENT.NS",
    "adani ports and special economic zone limited": "ADANIPORTS.NS",
    "adani ports": "ADANIPORTS.NS",
    "tata steel limited": "TATASTEEL.NS",
    "tata steel": "TATASTEEL.NS",
    "jsw steel limited": "JSWSTEEL.NS",
    "jsw steel": "JSWSTEEL.NS",
    "hindalco industries limited": "HINDALCO.NS",
    "hindalco": "HINDALCO.NS",
    "ultratech cement limited": "ULTRACEMCO.NS",
    "ultratech cement": "ULTRACEMCO.NS",
    "grasim industries limited": "GRASIM.NS",
    "grasim": "GRASIM.NS",
    "ambuja cements limited": "AMBUJACEM.NS",
    "acc limited": "ACC.NS",
    "pidilite industries limited": "PIDILITIND.NS",
    "pidilite": "PIDILITIND.NS",
    "prestige estates projects limited": "PRESTIGE.NS",
    "prestige estates": "PRESTIGE.NS",
    "l&t finance limited": "LTF.NS",
    "l&t finance": "LTF.NS",
    "glenmark pharmaceuticals limited": "GLENMARK.NS",
    "glenmark": "GLENMARK.NS",
    "bse limited": "BSE.NS",
    "bse": "BSE.NS",
    "interglobe aviation limited": "INDIGO.NS",
    "interglobe aviation": "INDIGO.NS",
    "indigo": "INDIGO.NS",
    "sai life sciences limited": "SAILIFE.NS",
}


def resolve_stock_ticker(entity_name: str) -> str | None:
    """Resolve a clean company entity name to an NSE Yahoo Finance ticker string."""
    if not entity_name:
        return None
    raw = entity_name.strip().lower()

    # Exact dictionary lookup
    if raw in NAME_TO_NSE_TICKER:
        return NAME_TO_NSE_TICKER[raw]

    # Clean punctuation and check again
    clean = re.sub(r"[^\w\s&]", "", raw).strip()
    if clean in NAME_TO_NSE_TICKER:
        return NAME_TO_NSE_TICKER[clean]

    # Check partial key matches
    for k, v in NAME_TO_NSE_TICKER.items():
        if k in raw or raw in k:
            return v

    # Fallback: if ends with .NS or .BO already
    if entity_name.upper().endswith(".NS") or entity_name.upper().endswith(".BO"):
        return entity_name.upper()

    return None


def get_stock_profile(ticker_or_name: str) -> dict[str, Any] | None:
    """Fetch 1W return, 1M return, 30D high/low, and 52W high/low for a given stock.

    Uses in-memory caching with 1-hour TTL for ultra-fast response.
    Returns None gracefully if the stock cannot be fetched.
    """
    if not ticker_or_name:
        return None

    ticker = resolve_stock_ticker(ticker_or_name)
    if not ticker:
        raw_upper = ticker_or_name.strip().upper()
        # If it's a single clean word (e.g. INFY, TCS) or already has .NS / .BO
        if " " not in raw_upper and len(raw_upper) <= 15:
            ticker = raw_upper if (raw_upper.endswith(".NS") or raw_upper.endswith(".BO")) else f"{raw_upper}.NS"
        else:
            return None

    now = time.time()
    if ticker in _STOCK_CACHE and (now - _CACHE_TIMESTAMP.get(ticker, 0.0)) < CACHE_TTL_SECONDS:
        return _STOCK_CACHE[ticker]


    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="3mo")
        if hist.empty or len(hist) < 2:
            _STOCK_CACHE[ticker] = None
            _CACHE_TIMESTAMP[ticker] = now
            return None

        cmp_price = float(hist["Close"].iloc[-1])

        # 1-Day change
        if len(hist) >= 2:
            p_1d = float(hist["Close"].iloc[-2])
            pct_1d = ((cmp_price - p_1d) / p_1d) * 100.0
        else:
            pct_1d = 0.0

        # 1-Week change (last 5 trading days)
        if len(hist) >= 5:
            p_1w = float(hist["Close"].iloc[-5])
            pct_1w = ((cmp_price - p_1w) / p_1w) * 100.0
        else:
            pct_1w = 0.0

        # 1-Month change (last 21 trading days)
        if len(hist) >= 21:
            p_1m = float(hist["Close"].iloc[-21])
            pct_1m = ((cmp_price - p_1m) / p_1m) * 100.0
        else:
            p_1m = float(hist["Close"].iloc[0])
            pct_1m = ((cmp_price - p_1m) / p_1m) * 100.0

        # 30-Day Trading Range
        last_30d = hist.tail(21)
        low_30d = float(last_30d["Low"].min())
        high_30d = float(last_30d["High"].max())

        # 52-Week Range from fast_info
        fifty_two_high = None
        fifty_two_low = None
        try:
            fifty_two_high = float(t.fast_info.year_high)
            fifty_two_low = float(t.fast_info.year_low)
        except Exception:
            pass

        profile = {
            "ticker": ticker,
            "cmp": round(cmp_price, 2),
            "return_1d": round(pct_1d, 2),
            "return_1w": round(pct_1w, 2),
            "return_1m": round(pct_1m, 2),
            "range_30d": (round(low_30d, 2), round(high_30d, 2)),
            "range_52w": (round(fifty_two_low, 2), round(fifty_two_high, 2))
            if (fifty_two_high and fifty_two_low)
            else None,
        }
        _STOCK_CACHE[ticker] = profile
        _CACHE_TIMESTAMP[ticker] = now
        return profile
    except Exception as exc:
        logger.warning("Failed to fetch yfinance stock profile for %s: %s", ticker, exc)
        _STOCK_CACHE[ticker] = None
        _CACHE_TIMESTAMP[ticker] = now
        return None


def format_holdings_stock_context(
    holdings_to_check: list[dict[str, Any]],
    articles: list[dict[str, Any]],
    *,
    max_stocks: int = 6,
) -> str:
    """Format price movement, calculated NAV impact, and sentiment signals for key holdings.

    Args:
        holdings_to_check: list of dicts with 'name', 'percentage', 'industry'
        articles: retrieved news articles with 'entity_names', 'direction', 'max_impact'
        max_stocks: maximum number of holding stock profiles to include

    Returns:
        Structured text block for LLM prompt context.
    """
    if not holdings_to_check:
        return ""

    # Count article sentiment / direction per holding
    holding_directions: dict[str, dict[str, int]] = {}
    for h in holdings_to_check:
        h_name = h.get("name", "")
        if not h_name:
            continue
        holding_directions[h_name] = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
        for a in articles:
            a_entities = [str(e).lower() for e in a.get("entity_names") or []]
            if any(h_name.lower() in e or e in h_name.lower() for e in a_entities):
                dir_val = str(a.get("direction") or "neutral").lower()
                if dir_val in ("positive", "negative", "neutral"):
                    holding_directions[h_name][dir_val] += 1
                holding_directions[h_name]["total"] += 1

    lines = []
    processed_count = 0

    for h in holdings_to_check:
        if processed_count >= max_stocks:
            break
        name = h.get("name", "")
        weight = h.get("percentage", 0.0)
        industry = h.get("industry", "")

        # Try to resolve price movement
        profile = get_stock_profile(name)
        dir_info = holding_directions.get(name, {})
        pos = dir_info.get("positive", 0)
        neg = dir_info.get("negative", 0)
        total_arts = dir_info.get("total", 0)

        sentiment_label = "Neutral"
        if pos > neg:
            sentiment_label = f"Positive Catalyst Momentum ({pos} positive news triggers)"
        elif neg > pos:
            sentiment_label = f"Negative Headwind Momentum ({neg} adverse news triggers)"
        elif total_arts > 0:
            sentiment_label = f"Balanced Sentiment ({total_arts} recent articles)"
        else:
            sentiment_label = "No direct breaking headlines in store"

        if profile:
            cmp_val = profile["cmp"]
            ret_1w = profile["return_1w"]
            ret_1m = profile["return_1m"]
            r_30d = profile["range_30d"]
            r_52w = profile.get("range_52w")

            range_52w_str = f" | 52W Range: ₹{r_52w[0]:.2f} - ₹{r_52w[1]:.2f}" if r_52w else ""
            approx_nav_impact_1w = (ret_1w * weight) / 100.0
            approx_nav_impact_1m = (ret_1m * weight) / 100.0

            lines.append(
                f"- **{name}** ({weight:.2f}% fund portfolio weight | {industry}):\n"
                f"  * Live Stock Price Movement: CMP: ₹{cmp_val:.2f} (1-Week Return: {ret_1w:+.2f}%, 1-Month Return: {ret_1m:+.2f}% | 30-Day Range: ₹{r_30d[0]:.2f} to ₹{r_30d[1]:.2f}{range_52w_str})\n"
                f"  * Calculated NAV Impact: A {ret_1w:+.2f}% 1-week price change on a {weight:.2f}% holding weight directly contributed approximately {approx_nav_impact_1w:+.2f}% to the fund's 1-week NAV movement (and {approx_nav_impact_1m:+.2f}% over 1 month).\n"
                f"  * News Sentiment & Direction: {sentiment_label}"
            )
            processed_count += 1
        else:
            # If no price feed available (unlisted / unmapped), state clearly without failing
            lines.append(
                f"- **{name}** ({weight:.2f}% fund portfolio weight | {industry}):\n"
                f"  * Live Stock Price Movement: (Price feed unavailable / unlisted company)\n"
                f"  * News Sentiment & Direction: {sentiment_label}"
            )
            processed_count += 1

    if not lines:
        return ""

    return "### Top Key Holdings Live Price Action, Calculated NAV Impact & Sentiment Posture (yfinance):\n" + "\n".join(lines)


def format_single_stock_context(
    entity_name: str,
    articles: list[dict[str, Any]],
) -> str:
    """Format single stock price range and sentiment direction for single_stock queries."""
    profile = get_stock_profile(entity_name)
    if not profile:
        return ""

    # Direction breakdown from articles
    pos, neg, neu = 0, 0, 0
    for a in articles:
        d = str(a.get("direction") or "").lower()
        if d == "positive":
            pos += 1
        elif d == "negative":
            neg += 1
        else:
            neu += 1

    cmp_val = profile["cmp"]
    ret_1d = profile["return_1d"]
    ret_1w = profile["return_1w"]
    ret_1m = profile["return_1m"]
    r_30d = profile["range_30d"]
    r_52w = profile.get("range_52w")

    range_52w_str = f" | 52W Range: ₹{r_52w[0]:.2f} - ₹{r_52w[1]:.2f}" if r_52w else ""
    sentiment_summary = f"{pos} Positive, {neg} Negative, {neu} Neutral"

    return (
        f"### {entity_name} Live Price Action & Trading Range (yfinance):\n"
        f"- Current Market Price (CMP): ₹{cmp_val:.2f} (1D: {ret_1d:+.2f}%, 1W: {ret_1w:+.2f}%, 1M: {ret_1m:+.2f}%)\n"
        f"- 30-Day Range: ₹{r_30d[0]:.2f} - ₹{r_30d[1]:.2f}{range_52w_str}\n"
        f"- News Sentiment Breakdown: {sentiment_summary}\n"
    )
