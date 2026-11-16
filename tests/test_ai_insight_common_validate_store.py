"""Prose checks and the JSON store."""

import pytest

from ai_insight.common.schemas import Chip, Envelope, Meta, Source
from ai_insight.common.store import exists, latest, list_dates, load, save
from ai_insight.common.validate import validate_insight


def _env(**overrides):
    data = dict(
        insight_id="market_driver_digest",
        trading_date="2026-11-16",
        as_of_ist="2026-11-16T17:10:00+05:30",
        status="ok",
        headline="Banks fell after the policy hold",
        body="Lenders fell 0.61% after the central bank held rates.",
        chips=[Chip(label="Nifty 50", value="-0.61%", tone="negative")],
        sources=[Source(title="Mint", url="https://example.com/a", source="Mint", published_at="2026-11-16T04:00:00Z")],
        facts={"nifty_change_pct": -0.61, "fii_net_crore": 2340},
        meta=Meta(cluster_ids=["c0"]),
    )
    data.update(overrides)
    return Envelope(**data)


def test_valid_insight_passes():
    result = validate_insight(_env())
    assert result.ok, result.errors


def test_each_check_can_fail():
    long_headline = _env(headline="one two three four five six seven eight nine ten eleven twelve thirteen")
    assert any(not c.passed and c.name == "headline_len" for c in validate_insight(long_headline).checks)

    long_body = _env(body="One. Two. Three. Four. Five. Six.")
    assert any(not c.passed and c.name == "body_len" for c in validate_insight(long_body).checks)

    missing_number = _env(body="Lenders fell 9.5% after the central bank held rates.")
    numbers = validate_insight(missing_number)
    assert numbers.ok is False
    assert any(c.name == "numbers" and not c.passed for c in numbers.checks)

    wrong_way = _env(body="Lenders rose 0.61% after the central bank held rates.")
    assert any(c.name == "direction" and not c.passed for c in validate_insight(wrong_way).checks)

    unknown = _env(body="Lenders fell 0.61% after the central bank held rates in c9.")
    assert any(c.name == "cluster_ids" and not c.passed for c in validate_insight(unknown).checks)

    no_source = _env(sources=[], body="Lenders fell 0.61% after the central bank held rates.")
    assert any(c.name == "sources" and not c.passed for c in validate_insight(no_source).checks)

    banned = _env(headline="Investors should buy banks now")
    assert any(c.name == "banned" and not c.passed for c in validate_insight(banned).checks)


def test_number_forms_match_facts_or_chips():
    env = _env(
        headline="Flows were large",
        body="Funds bought ₹2,340 crore and a 2.3k print showed up. Nifty fell 0.61%.",
    )
    result = validate_insight(env)
    assert result.ok, result.errors


def test_decimal_does_not_split_a_sentence():
    env = _env(body="Nifty fell 0.61%. Banks sold into the close. The rupee held steady.")
    check = next(c for c in validate_insight(env).checks if c.name == "body_len")
    assert check.passed
    assert "3 sentences" in check.detail


def test_store_round_trip_and_latest(tmp_path):
    first = _env(headline="Banks fell ₹2,340")
    second = _env(trading_date="2026-11-13", headline="An earlier session")
    save(first, root=tmp_path)
    save(second, root=tmp_path)
    loaded = load("market_driver_digest", "2026-11-16", root=tmp_path)
    assert loaded is not None
    raw = (tmp_path / "market_driver_digest" / "2026-11-16.json").read_text(encoding="utf-8")
    assert "₹2,340" in raw
    assert "\\u" not in raw
    assert list_dates("market_driver_digest", root=tmp_path) == ["2026-11-13", "2026-11-16"]
    assert latest("market_driver_digest", root=tmp_path).trading_date == "2026-11-16"
    assert exists("market_driver_digest", "2026-11-16", status="ok", root=tmp_path)
    assert exists("market_driver_digest", "2026-11-16", status="failed", root=tmp_path) is False


def test_list_dates_includes_live_files(tmp_path):
    save(_env(), root=tmp_path, live=True)
    assert list_dates("market_driver_digest", root=tmp_path) == ["2026-11-16"]


def test_failed_write_leaves_no_partial_file(tmp_path, monkeypatch):
    def boom(_src, _dst):
        raise OSError("disk full")

    monkeypatch.setattr("ai_insight.common.store._replace", boom)
    with pytest.raises(OSError):
        save(_env(), root=tmp_path)
    assert not (tmp_path / "market_driver_digest" / "2026-11-16.json").exists()
    assert list(tmp_path.rglob("*.tmp")) == []


def test_path_traversal_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        load("../secrets", "2026-11-16", root=tmp_path)
