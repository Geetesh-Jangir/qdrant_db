"""Loaders for market_driver_digest DATASETS (math only)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace

import pytest

from ai_insight.common.config import load_config
from ai_insight.market_driver_digest.macro_context import (
    GSEC_CSV_NAME,
    _brent_horizons,
    _gsec_7d,
    _parse_gsec_csv,
    build_digest_datasets,
)
from ai_insight.market_driver_digest.prompt import compact_market_facts


def _ctx(tmp_path: Path, trading: str = "2026-11-19") -> SimpleNamespace:
    cfg = load_config()
    data_dir = tmp_path / "ai_insights"
    data_dir.mkdir(parents=True)
    (data_dir / "_data").mkdir(parents=True)
    cfg = replace(cfg, data_dir=data_dir)
    return SimpleNamespace(
        trading_date=date.fromisoformat(trading),
        config=cfg,
    )


def test_gsec_change_bp_7d(tmp_path: Path):
    root = tmp_path / "ai_insights" / "_data"
    root.mkdir(parents=True)
    content = '"Date","Price"\n"19-11-2026","7.30"\n"18-11-2026","7.28"\n'
    (root / GSEC_CSV_NAME).write_text(content, encoding="utf-8")
    limits: list[str] = []
    pack = _gsec_7d(root, limits)
    assert pack["change_bp_7d"] == pytest.approx(2.0, abs=0.1)
    assert len(pack["daily"]) == 2


def test_parse_gsec_csv_order():
    rows = _parse_gsec_csv_text(
        '"Date","Price"\n"10-11-2026","7.20"\n"11-11-2026","7.25"\n'
    )
    assert rows[0]["date"] == "2026-11-11"


def _parse_gsec_csv_text(text: str) -> list:
    path = Path("_tmp_gsec.csv")
    path.write_text(text, encoding="utf-8")
    try:
        return _parse_gsec_csv(path)
    finally:
        path.unlink(missing_ok=True)


def test_brent_horizons_sparse():
    series = [
        {"date": "2025-11-01", "close": 80.0},
        {"date": "2026-11-19", "close": 72.0},
    ]
    horizons = _brent_horizons(series, 72.0, "2026-11-19")
    assert horizons.get("1y") == pytest.approx(-10.0, abs=0.5)


def test_build_digest_datasets_limitations_when_missing(tmp_path: Path):
    ctx = _ctx(tmp_path)
    out = build_digest_datasets(ctx)
    assert "data_limitations" in out
    assert any("missing" in x.lower() or "only" in x.lower() for x in out["data_limitations"])


def test_compact_market_facts_includes_datasets():
    facts = {
        "trading_date": "2026-11-19",
        "nifty_change_pct": 0.5,
        "datasets": {"sector_indices_7d": [], "data_limitations": ["cpi_ytd: xlsx missing"]},
    }
    slim = compact_market_facts(facts)
    assert "DATASETS" in slim
    assert slim["data_limitations"] == ["cpi_ytd: xlsx missing"]