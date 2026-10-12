"""Structured findings produced by compute blocks (Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

VerdictKind = Literal[
    "topic_driven",
    "other_sector_driven",
    "mixed",
    "market_driven",
    "unknown",
]


@dataclass
class FindingLimit:
    code: str
    message: str


@dataclass
class FundFinding:
    fund_name: str
    isin: str = ""
    exposure_pct: float | None = None
    exposure_sectors: dict[str, float] = field(default_factory=dict)
    other_top_sectors: list[dict[str, Any]] = field(default_factory=list)
    return_window_pct: float | None = None
    monthly_returns: list[dict[str, Any]] = field(default_factory=list)
    benchmark_return_pct: float | None = None
    relative_to_benchmark_pct: float | None = None
    news_signal: str = "unknown"
    impact_score: float | None = None
    attribution: dict[str, float] = field(default_factory=dict)
    divergence: bool = False
    verdict: VerdictKind = "unknown"
    confidence: str = "low"
    limits: list[FindingLimit] = field(default_factory=list)


@dataclass
class SectorFinding:
    sector_label: str
    news_themes: list[str] = field(default_factory=list)
    news_direction: str = "unknown"
    index_return_pct: float | None = None
    benchmark_label: str = ""
    article_count: int = 0
    news_summary: str = ""
    news_insights: list[str] = field(default_factory=list)
    news_stats: dict[str, Any] = field(default_factory=dict)
    executive_summary: str = ""


@dataclass
class Findings:
    goal: str = ""
    sector: SectorFinding | None = None
    funds: list[FundFinding] = field(default_factory=list)
    cross_cutting: list[str] = field(default_factory=list)
    limits: list[FindingLimit] = field(default_factory=list)
    evidence_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "sector": None
            if self.sector is None
            else {
                "sector_label": self.sector.sector_label,
                "news_themes": self.sector.news_themes,
                "news_direction": self.sector.news_direction,
                "index_return_pct": self.sector.index_return_pct,
                "benchmark_label": self.sector.benchmark_label,
                "article_count": self.sector.article_count,
                "news_summary": self.sector.news_summary,
                "news_insights": self.sector.news_insights,
                "news_stats": self.sector.news_stats,
                "executive_summary": self.sector.executive_summary,
            },
            "funds": [
                {
                    "fund_name": f.fund_name,
                    "isin": f.isin,
                    "exposure_pct": f.exposure_pct,
                    "other_top_sectors": f.other_top_sectors,
                    "return_window_pct": f.return_window_pct,
                    "monthly_returns": f.monthly_returns,
                    "benchmark_return_pct": f.benchmark_return_pct,
                    "relative_to_benchmark_pct": f.relative_to_benchmark_pct,
                    "news_signal": f.news_signal,
                    "attribution": f.attribution,
                    "divergence": f.divergence,
                    "verdict": f.verdict,
                    "confidence": f.confidence,
                    "limits": [{"code": l.code, "message": l.message} for l in f.limits],
                }
                for f in self.funds
            ],
            "cross_cutting": self.cross_cutting,
            "limits": [{"code": l.code, "message": l.message} for l in self.limits],
        }
