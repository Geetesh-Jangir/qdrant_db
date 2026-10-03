"""Short deterministic explanations for why sector-ranked funds are affected."""

from __future__ import annotations


def sector_impact_reasoning(
    question: str,
    *,
    sector_keys: list[str],
    event_focus: str = "",
    direction_filter: str = "any",
    article_count: int = 0,
) -> str:
    """1–2 sentences on mechanism (no LLM)."""
    blob = f"{question} {event_focus}".lower()
    sectors = ", ".join(sector_keys)
    sector_fold = {s.casefold() for s in sector_keys}

    tailwind = direction_filter == "positive"
    headwind = direction_filter == "negative"

    def _dir_clause() -> str:
        if headwind:
            return "headline risk and selling pressure in those stocks"
        if tailwind:
            return "improving sentiment and gains in those stocks"
        return "price moves in those stocks"

    news_hook = ""
    if article_count > 0:
        news_hook = (
            f" Recent verified news in your window ({article_count} article(s)) "
            f"is aligned with this theme."
        )

    if sector_fold & {"automobiles", "auto components"} or any(
        t in blob for t in ("auto", "automobile", "automotive")
    ):
        mechanism = (
            "Automotive news (demand, margins, regulation, or supply chain) tends to move "
            "carmakers and component makers together."
        )
        if headwind:
            effect = "Funds with the heaviest **Automobiles** / **Auto Components** weights usually feel that weakness in NAV first."
        elif tailwind:
            effect = "Funds with the heaviest **Automobiles** / **Auto Components** weights usually capture more of that upside in NAV."
        else:
            effect = (
                f"Funds with the largest **{sectors}** allocation pass through more of {_dir_clause()} to NAV."
            )
        return f"{mechanism} {effect}{news_hook}"

    if sector_fold & {"banks", "finance"} or any(
        t in blob for t in ("rbi", "repo", "banking", "bank sector", "rate hike", "monetary policy")
    ):
        if any(t in blob for t in ("rbi", "repo", "rate hike", "monetary policy", "repo rate")):
            mechanism = (
                "RBI repo and rate moves change funding costs, loan demand, and how investors "
                "price banks and financials."
            )
        else:
            mechanism = (
                "Banking-sector news flows mainly through lender and NBFC stock prices."
            )
        if headwind:
            effect = (
                "Funds most concentrated in **Banks** and **Finance** often see sharper NAV "
                "drawdowns when rate-hike or risk-off headlines dominate."
            )
        elif tailwind:
            effect = (
                "Funds most concentrated in **Banks** and **Finance** often benefit more in NAV "
                "when banking sentiment turns positive."
            )
        else:
            effect = (
                f"Funds with the highest **{sectors}** weights tend to reflect that news in NAV "
                "more than diversified peers."
            )
        return f"{mechanism} {effect}{news_hook}"

    if sector_fold & {"petroleum products"} or any(t in blob for t in ("crude", "oil", "petroleum")):
        mechanism = (
            "Oil and crude headlines affect refiners, marketing firms, and energy-linked "
            "industrials through margins and input costs."
        )
        effect = (
            f"Funds with meaningful **{sectors}** exposure transmit more of that channel into NAV."
        )
        return f"{mechanism} {effect}{news_hook}"

    mechanism = (
        f"News that shifts **{sectors}** earnings or valuations moves those holdings in a fund's portfolio."
    )
    effect = (
        f"The list below ranks Regular Growth schemes by how much of the portfolio sits in that "
        f"sector slice, so they are typically the first to show {_dir_clause()} in NAV."
    )
    return f"{mechanism} {effect}{news_hook}"


def single_fund_crude_impact_summary(
    fund_name: str,
    *,
    oil_rising: bool,
    crude_sectors: list[tuple[str, float]],
    top_sectors: list[tuple[str, float]],
    article_count: int,
    window_label: str,
) -> str:
    """Narrative for named-fund + crude/oil questions."""
    total = sum(p for _, p in crude_sectors)
    move = "rises" if oil_rising else "falls"

    if total < 3.0:
        magnitude = "limited"
        mag_detail = "Oil-linked sectors are a small share of this portfolio."
    elif total < 12.0:
        magnitude = "moderate"
        mag_detail = "Oil-linked sectors matter, but the fund is still diversified elsewhere."
    else:
        magnitude = "material"
        mag_detail = "A meaningful part of the portfolio sits in oil-sensitive sectors."

    channels = ", ".join(f"**{s}** ({p:.2f}%)" for s, p in crude_sectors[:4])
    if not channels:
        channels = "no mapped oil-sensitive sector weights in the latest holdings file"

    crude_names = {s for s, _ in crude_sectors}
    diversifiers = ", ".join(
        f"**{s}** ({p:.2f}%)" for s, p in top_sectors[:5] if s not in crude_names
    )
    div_clause = ""
    if diversifiers:
        div_clause = (
            f" Larger weights such as {diversifiers} usually shape NAV more than the oil slice."
        )

    mechanism = (
        f"When crude **{move}**, flexi-cap funds mainly feel it through auto, transport, and energy "
        f"holdings (fuel costs, margins, and demand) — not through every sector in the portfolio."
    )
    effect = (
        f"For **{fund_name}**, oil-linked exposure totals about **{total:.2f}%** "
        f"({channels}). Overall oil impact is **{magnitude}** — {mag_detail}{div_clause}"
    )
    news = ""
    if article_count > 0:
        news = f" **{article_count}** recent article(s) in {window_label} mention oil/crude."
    return f"{mechanism} {effect}{news}"


def single_fund_rbi_impact_summary(
    fund_name: str,
    *,
    tightening: bool,
    rate_sectors: list[tuple[str, float]],
    top_sectors: list[tuple[str, float]],
    article_count: int,
    window_label: str,
) -> str:
    total = sum(p for _, p in rate_sectors)
    policy = "tightening" if tightening else "easing"

    if total < 8.0:
        magnitude = "limited"
        mag_detail = "Banks/finance are not a dominant slice of this portfolio."
    elif total < 25.0:
        magnitude = "moderate"
        mag_detail = "Rate moves matter through the financials allocation, alongside other sectors."
    else:
        magnitude = "material"
        mag_detail = "A large share of the portfolio is in rate-sensitive financials."

    channels = ", ".join(f"**{s}** ({p:.2f}%)" for s, p in rate_sectors[:4])
    if not channels:
        channels = "low mapped Banks/Finance weight in latest holdings"

    fin_names = {s for s, _ in rate_sectors}
    diversifiers = ", ".join(
        f"**{s}** ({p:.2f}%)" for s, p in top_sectors[:4] if s not in fin_names
    )
    div_clause = ""
    if diversifiers and total < 25.0:
        div_clause = f" Non-financial weights such as {diversifiers} also drive NAV."

    mechanism = (
        f"RBI repo **{policy}** flows through funding costs, credit demand, and how investors "
        f"price banks and NBFCs."
    )
    effect = (
        f"For **{fund_name}**, Banks/Finance exposure is about **{total:.2f}%** "
        f"({channels}). Rate impact on this scheme looks **{magnitude}** — {mag_detail}{div_clause}"
    )
    news = ""
    if article_count > 0:
        news = f" **{article_count}** article(s) in {window_label} mention RBI/rates."
    return f"{mechanism} {effect}{news}"
