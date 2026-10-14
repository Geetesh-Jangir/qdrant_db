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
    scheme_benchmark: str = ""
    relative_to_benchmark_pct: float | None = None
    nav: float | None = None
    nav_date: str = ""
    news_signal: str = "unknown"
    impact_score: float | None = None
    attribution: dict[str, float] = field(default_factory=dict)
    divergence: bool = False
    verdict: VerdictKind = "unknown"
    confidence: str = "low"
    limits: list[FindingLimit] = field(default_factory=list)
    # news -> fund link
    pos_exposure_pct: float = 0.0  # weight in sectors the news helps
    neg_exposure_pct: float = 0.0  # weight in sectors the news hurts
    pos_sectors: list[dict[str, Any]] = field(default_factory=list)
    neg_sectors: list[dict[str, Any]] = field(default_factory=list)
    exposure_sector: str = ""  # the sector `exposure_pct` refers to
    top_holdings: list[dict[str, Any]] = field(default_factory=list)  # name, percentage
    sector_mix: list[dict[str, Any]] = field(default_factory=list)  # sector, percentage, index_label, index_return_pct
    category: str = ""
    as_on: str = ""
    mixed_exposure_pct: float = 0.0  # weight in sectors where the news pulls both ways
    mixed_sectors: list[dict[str, Any]] = field(default_factory=list)
    news_tilt: str = "unknown"  # tailwind | headwind | mixed | neutral | unknown
    alignment: str = "unknown"  # aligned | diverged | diluted | mixed | unknown
    mechanism: str = ""  # why the news reaches this fund (from the articles)
    direct_holdings: list[str] = field(default_factory=list)
    drag_sectors: list[dict[str, Any]] = field(default_factory=list)


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
    tone: str = "unclear"
    tone_reason: str = ""
    claims: list[dict[str, Any]] = field(default_factory=list)  # id, text, sentiment, source, title, url
    sectors_positive: list[dict[str, Any]] = field(default_factory=list)
    sectors_negative: list[dict[str, Any]] = field(default_factory=list)
    read_mode: str = "none"


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
                "tone": self.sector.tone,
                "tone_reason": self.sector.tone_reason,
                "claims": self.sector.claims,
                "sectors_positive": self.sector.sectors_positive,
                "sectors_negative": self.sector.sectors_negative,
                "read_mode": self.sector.read_mode,
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
                    "pos_exposure_pct": f.pos_exposure_pct,
                    "neg_exposure_pct": f.neg_exposure_pct,
                    "pos_sectors": f.pos_sectors,
                    "neg_sectors": f.neg_sectors,
                    "exposure_sector": f.exposure_sector,
                    "top_holdings": f.top_holdings,
                    "sector_mix": f.sector_mix,
                    "mixed_exposure_pct": f.mixed_exposure_pct,
                    "mixed_sectors": f.mixed_sectors,
                    "news_tilt": f.news_tilt,
                    "alignment": f.alignment,
                    "mechanism": f.mechanism,
                    "direct_holdings": f.direct_holdings,
                    "verdict": f.verdict,
                    "confidence": f.confidence,
                    "limits": [{"code": l.code, "message": l.message} for l in f.limits],
                }
                for f in self.funds
            ],
            "cross_cutting": self.cross_cutting,
            "limits": [{"code": l.code, "message": l.message} for l in self.limits],
        }
