"""Merge cached stock insight with per-investor holding %."""


def render(stock_insight: dict, investor_holding_pct: float) -> str:
    name = stock_insight.get("stock_name") or stock_insight.get("stock_id") or "Stock"
    lines = stock_insight.get("insight_lines") or []
    body = " ".join(lines)
    return f"{name} ({investor_holding_pct}% of your portfolio)\n{body}"