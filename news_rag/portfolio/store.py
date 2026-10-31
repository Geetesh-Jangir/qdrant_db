"""Read-only view over a normalized portfolio document."""

from __future__ import annotations

from typing import Any

from news_rag.portfolio.normalize import match_scheme_filter


class PortfolioStore:
    def __init__(self, doc: dict[str, Any]) -> None:
        self._doc = doc if isinstance(doc, dict) else {}

    @property
    def doc(self) -> dict[str, Any]:
        return self._doc

    def holdings(
        self,
        *,
        scheme_filter: str = "",
        top_n: int = 20,
        sort_by: str = "aum",
    ) -> list[dict[str, Any]]:
        rows = list(self._doc.get("holdings") or [])
        if scheme_filter:
            rows = [r for r in rows if match_scheme_filter(str(r.get("scheme_name") or ""), scheme_filter)]
        key = sort_by if sort_by in ("aum", "gain_loss", "xirr") else "aum"
        field = {"aum": "aum_inr", "gain_loss": "gain_loss_inr", "xirr": "xirr_pct"}[key]

        def sort_key(row: dict[str, Any]) -> float:
            val = row.get(field)
            try:
                return float(val) if val is not None else float("-inf")
            except (TypeError, ValueError):
                return float("-inf")

        rows.sort(key=sort_key, reverse=True)
        return rows[: max(1, min(int(top_n or 20), 50))]

    def pnl_scheme(self, scheme_filter: str) -> dict[str, Any] | None:
        for row in self._doc.get("pnl_schemes") or []:
            if not isinstance(row, dict):
                continue
            if match_scheme_filter(str(row.get("scheme_name") or ""), scheme_filter):
                return row
        return None
