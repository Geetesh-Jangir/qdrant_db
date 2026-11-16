"""Card assembly, theme checks, and the backtest report. The model and Qdrant are fakes."""

import json
import re
from datetime import date
from types import SimpleNamespace

from ai_insight.common.config import load_config
from ai_insight.common.display import sector_label
from ai_insight.common.llm import LlmJsonResult, LlmSchemaError, LlmUsage
from ai_insight.common.run_log import RunLog
from ai_insight.common.runner import DryRunHalt, RunContext
from ai_insight.common.schemas import Envelope
from ai_insight.common.store import save
from ai_insight.common.time_ist import session_window
from ai_insight.common.trading_calendar import is_trading_day
from ai_insight.common.validate import validate_insight

from ai_insight.sector_leaderboard.fetch import fetch_sector_stories
from ai_insight.sector_leaderboard.prompt import PROMPT_VERSION
from ai_insight.sector_leaderboard.run import backtest, build, compose_body, compose_headline, main, theme_problems
from ai_insight.sector_leaderboard.schema import INSIGHT_ID, SectorScore, StoryScore
from ai_insight.sector_leaderboard.score import score_sector

DAY = date(2026, 11, 13)


def _cfg(tmp_path):
    holidays = tmp_path / "holidays.json"
    holidays.write_text(json.dumps({"2026": ["2026-11-10", "2026-11-24"]}), encoding="utf-8")
    return load_config(
        {
            "INSIGHTS_DATA_DIR": str(tmp_path / "data"),
            "INSIGHTS_LOG_DIR": str(tmp_path / "logs"),
            "INSIGHTS_HOLIDAYS_PATH": str(holidays),
            "INSIGHTS_CUTOFF_IST": "23:59",
        }
    )


class RepeatClient:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = 0

    def scroll(self, **kwargs):
        self.calls += 1
        return [SimpleNamespace(payload=payload) for payload in self.payloads], None


def _payload(url, title, sector, direction, text="Plain story about the sector.", **entity):
    body = {
        "url": url,
        "title": title,
        "source": "Mint",
        "published_at": "2026-11-13T06:00:00Z",
        "scraped_text": text,
        "alias_urls": entity.pop("alias_urls", []),
        "entities": [
            {
                "name": sector,
                "type": "sector",
                "relevance": 4,
                "impact": 3,
                "direction": direction,
                "event_type": "results",
                "about_this_name": 1.0,
                **entity,
            }
        ],
    }
    return body


def _ctx(tmp_path, client, llm, day=DAY):
    cfg = _cfg(tmp_path)
    log = RunLog(insight_id=INSIGHT_ID, trading_date=day.isoformat(), run_id="test01", log_dir=cfg.log_dir)
    ctx = RunContext(
        insight_id=INSIGHT_ID,
        trading_date=day,
        window=session_window(day, config=cfg),
        dry_run=False,
        config=cfg,
        log=log,
        llm=llm,
    )
    ctx.qdrant = client
    return ctx


def _echo(best="lenders won fresh corporate mandates", worst="home buyers delayed new bookings"):
    def call(system, user, schema, max_tokens=400):
        ids = re.findall(r"STORY (\S+) \|", user)
        data = {"cited_cluster_ids": ids}
        if "best_theme" in schema["properties"]:
            data["best_theme"] = best
        if "worst_theme" in schema["properties"]:
            data["worst_theme"] = worst
        return LlmJsonResult(data=data, usage=LlmUsage("test", "test"))

    return call


def _both_sides():
    return [
        _payload("https://banks/a", "Banks win a large corporate mandate", "Banks", "positive"),
        _payload("https://banks/b", "Deposit franchises expand across districts", "Banks", "positive"),
        _payload("https://realty/a", "Home buyers delay bookings", "Realty", "negative"),
        _payload("https://realty/b", "Builders cut project launches", "Realty", "negative"),
    ]


def test_listed_weekday_holidays_are_closed():
    assert is_trading_day(date(2026, 11, 10)) is False
    assert is_trading_day(date(2026, 1, 26)) is False
    assert is_trading_day(date(2026, 12, 25)) is False
    assert is_trading_day(date(2026, 11, 13)) is True


def test_syndicated_duplicates_count_as_one_story_using_the_stronger_copy(tmp_path):
    same_title = [
        _payload("https://mint/a", "Banks win a large corporate mandate", "Banks", "positive"),
        _payload(
            "https://et/a",
            "Banks win a large corporate mandate",
            "Banks",
            "positive",
            relevance=3,
            impact=2,
            about_this_name=0.8,
        ),
    ]
    fetched = fetch_sector_stories(("2026-11-12T10:00:00Z", "2026-11-13T18:00:00Z"), client=RepeatClient(same_title))
    sector = score_sector(fetched.sectors[0].name, fetched.sectors[0].clusters)
    assert sector.n_stories == 1
    assert sector.stories[0].weight == 1.0

    aliased = [
        _payload(
            "https://mint/power",
            "Power plants add solar capacity fast",
            "Power",
            "positive",
            alias_urls=["https://et/power"],
        ),
        _payload(
            "https://et/power",
            "Ports report a record coal shipment",
            "Power",
            "negative",
            relevance=3,
            impact=2,
            about_this_name=0.8,
        ),
    ]
    fetched = fetch_sector_stories(("2026-11-12T10:00:00Z", "2026-11-13T18:00:00Z"), client=RepeatClient(aliased))
    sector = score_sector(fetched.sectors[0].name, fetched.sectors[0].clusters)
    assert sector.n_stories == 1
    assert sector.stories[0].weight == 1.0
    assert sector.stories[0].sign == 1

    similar = [
        _payload("https://mint/c1", "Cement firms lift prices today", "Cement & Cement Products", "positive"),
        _payload(
            "https://et/c2",
            "Cement firms lift prices again",
            "Cement & Cement Products",
            "positive",
            relevance=3,
            impact=2,
            about_this_name=0.8,
        ),
    ]
    fetched = fetch_sector_stories(("2026-11-12T10:00:00Z", "2026-11-13T18:00:00Z"), client=RepeatClient(similar))
    sector = score_sector(fetched.sectors[0].name, fetched.sectors[0].clusters)
    assert sector.n_stories == 1
    assert sector.stories[0].weight == 1.0
    assert re.search(r"\bc\d+\b", sector.stories[0].cluster_id) is None


def test_both_sides_build_a_card_the_validator_accepts(tmp_path):
    ctx = _ctx(tmp_path, RepeatClient(_both_sides()), _echo())
    envelope = build(ctx)
    assert envelope.status == "ok"
    assert envelope.facts["positive_sector"] == "Banks"
    assert envelope.facts["negative_sector"] == "Realty"
    assert envelope.meta.prompt_version == PROMPT_VERSION
    assert envelope.viz.type == "diverging_bars"
    assert [item["tone"] for item in envelope.viz.data["items"]] == ["positive", "negative"]
    assert all(row["stories"] >= 2 for row in envelope.facts["ranking"])
    assert {chip.tone for chip in envelope.chips} == {"positive", "negative", "neutral"}
    assert any("news tone" in chip.label or chip.label == "Sectors tracked" for chip in envelope.chips)
    assert envelope.viz.data.get("drivers")
    assert 1 <= len(envelope.sources) <= 3
    assert {source.url for source in envelope.sources} >= {"https://banks/a", "https://realty/a"} or {
        source.url for source in envelope.sources
    } <= {"https://banks/a", "https://banks/b", "https://realty/a", "https://realty/b"}
    urls = {source.url for source in envelope.sources}
    assert any(url.startswith("https://banks/") for url in urls)
    assert any(url.startswith("https://realty/") for url in urls)
    checked = validate_insight(envelope)
    assert checked.ok, checked.errors
    assert len(envelope.body.split()) <= 55
    assert envelope.body.count(".") <= 3
    assert "best_theme" in envelope.facts and "worst_theme" in envelope.facts
    assert envelope.facts["gate"]["entities_passed"] == 4


def test_one_strong_side_is_kept_and_a_thin_side_is_not_invented(tmp_path):
    payloads = [
        _payload("https://banks/a", "Banks win a large corporate mandate", "Banks", "positive"),
        _payload("https://banks/b", "Deposit franchises expand across districts", "Banks", "positive"),
        _payload("https://banks/c", "Credit cards see festival spending", "Banks", "positive"),
        _payload("https://realty/a", "Home buyers delay bookings", "Realty", "positive"),
        _payload("https://realty/b", "Builders cut project launches", "Realty", "positive"),
    ]
    envelope = build(_ctx(tmp_path, RepeatClient(payloads), _echo()))
    assert envelope.status == "ok"
    assert envelope.facts["negative_sector"] == ""
    assert envelope.facts["negative_score"] is None
    assert all(item["tone"] == "positive" for item in envelope.viz.data["items"])
    assert "lagged" not in envelope.body
    assert "Several separate stories backed the lead." in envelope.body
    assert validate_insight(envelope).ok

    thin_side = payloads[:2] + payloads[3:]
    skipped = build(_ctx(tmp_path, RepeatClient(thin_side), _echo()))
    assert skipped.status == "skipped"
    assert skipped.skip_reason == "thin coverage"
    assert skipped.headline == ""


def test_thin_coverage_skips_when_fewer_than_two_sectors_qualify(tmp_path):
    payloads = [
        _payload("https://banks/a", "Banks win a large corporate mandate", "Banks", "positive"),
        _payload("https://banks/b", "Deposit franchises expand across districts", "Banks", "positive"),
        _payload("https://banks/c", "Credit cards see festival spending", "Banks", "positive"),
    ]
    envelope = build(_ctx(tmp_path, RepeatClient(payloads), _echo()))
    assert envelope.status == "skipped"
    assert envelope.skip_reason == "thin coverage"
    assert envelope.facts["eligible_count"] == 1


def test_theme_checks_reject_invented_numbers_breaks_and_unknown_clusters():
    story = StoryScore(
        cluster_id="s00_c0",
        title="Lenders cut rates",
        url="https://banks/a",
        source="Mint",
        published_at="2026-11-13T06:00:00Z",
        text="Lenders cut rates by 25 basis points.",
        weight=1,
        magnitude=1,
        sign=1,
        direction="positive",
    )
    assert theme_problems(
        {"best_theme": "lenders cut rates by 25 basis points", "cited_cluster_ids": ["s00_c0"]},
        [story],
        [],
    ) == []
    invented = theme_problems(
        {"best_theme": "lenders cut rates by 99 basis points", "cited_cluster_ids": ["s00_c0"]},
        [story],
        [],
    )
    assert any("99" in problem for problem in invented)
    assert theme_problems(
        {"best_theme": "orders rose. demand held", "cited_cluster_ids": ["s00_c0"]},
        [story],
        [],
    )
    assert theme_problems(
        {"best_theme": " ".join(["orders"] * 15), "cited_cluster_ids": ["s00_c0"]},
        [story],
        [],
    )
    assert theme_problems(
        {"best_theme": "lenders cut rates by 25 basis points", "cited_cluster_ids": ["s99_c9"]},
        [story],
        [],
    )


def test_bad_themes_degrade_and_a_second_reply_can_recover(tmp_path):
    client = RepeatClient(_both_sides())
    envelope = build(_ctx(tmp_path, client, _echo(best="lenders moved 99 points")))
    assert envelope.status == "degraded"
    assert "99" not in envelope.body
    assert "stood out" in envelope.body
    assert validate_insight(envelope).ok or "because" not in envelope.body

    calls = {"n": 0}

    def recover(system, user, schema, max_tokens=400):
        calls["n"] += 1
        ids = re.findall(r"STORY (\S+) \|", user)
        theme = "orders rose. demand held" if calls["n"] == 1 else "lenders won fresh corporate mandates"
        return LlmJsonResult(
            data={
                "best_theme": theme,
                "worst_theme": "home buyers delayed new bookings",
                "cited_cluster_ids": ids,
            },
            usage=LlmUsage("test", "test"),
        )

    recovered = build(_ctx(tmp_path, RepeatClient(_both_sides()), recover))
    assert calls["n"] == 2
    assert recovered.status == "ok"
    assert "orders rose" not in recovered.body

    def explode(system, user, schema, max_tokens=400):
        raise LlmSchemaError("schema")

    failed = build(_ctx(tmp_path, RepeatClient(_both_sides()), explode))
    assert failed.status == "degraded"
    assert failed.meta.validation["ok"] is False


def test_a_number_that_is_in_the_story_passes_the_shared_validator(tmp_path):
    payloads = [
        _payload(
            "https://banks/a",
            "Lenders cut rates",
            "Banks",
            "positive",
            text="Lenders cut rates by 25 basis points for corporate loans.",
        ),
        _payload("https://banks/b", "Deposit franchises expand across districts", "Banks", "positive"),
        _payload("https://realty/a", "Home buyers delay bookings", "Realty", "negative"),
        _payload("https://realty/b", "Builders cut project launches", "Realty", "negative"),
    ]
    envelope = build(
        _ctx(tmp_path, RepeatClient(payloads), _echo(best="lenders cut rates by 25 basis points"))
    )
    assert envelope.status == "ok"
    checked = validate_insight(envelope)
    assert checked.ok, checked.errors
    assert "25" in envelope.body


def test_compose_body_keeps_both_sides_when_week_pct_has_decimals():
    wm = {
        "best_index": {"display": "Nifty Bank", "week_change_pct": 10.13},
        "worst_index": {"display": "Nifty IT", "week_change_pct": -0.38},
    }
    best = SectorScore(name="Banks", display="Banks", score=0.041, n_stories=25, stories=[])
    worst = SectorScore(name="It - Software", display="It - Software", score=-0.009, n_stories=6, stories=[])
    body = compose_body(
        best,
        worst,
        "Banks may gain as oil and bond yields ease, though rate hikes loom",
        "IT firms face H-1B visa scrutiny and weak organic revenue",
        week_meta=wm,
    )
    assert "Nifty Bank" in body
    assert "Nifty IT" in body
    assert "10.13%" in body
    assert "0.38%" in body


def test_body_stays_inside_the_length_contract_and_drops_the_extra_line():
    best = SectorScore(
        name="Agricultural, Commercial & Construction Vehicles",
        display=sector_label("Agricultural, Commercial & Construction Vehicles"),
        score=0.4,
        n_stories=3,
        stories=[],
    )
    worst = SectorScore(
        name="Pharmaceuticals & Biotechnology",
        display=sector_label("Pharmaceuticals & Biotechnology"),
        score=-0.2,
        n_stories=2,
        stories=[],
    )
    theme = " ".join(["orders"] * 14)
    body = compose_body(best, worst, theme, theme)
    assert len(body.split()) <= 55
    assert body.count(".") == 3
    assert "Several separate stories backed the lead." in body
    headline = compose_headline(best, worst, DAY)
    assert len(headline.split()) <= 12

    short_best = SectorScore(name="Banks", display="Banks", score=0.4, n_stories=3, stories=[])
    short_worst = SectorScore(name="Realty", display="Realty", score=-0.2, n_stories=2, stories=[])
    trimmed = compose_body(short_best, short_worst, "fresh orders", "slow bookings", word_limit=12)
    assert "Several" not in trimmed
    assert trimmed.count(".") == 2
    tighter = compose_body(short_best, short_worst, "fresh orders", "slow bookings", word_limit=5)
    assert tighter == "Banks led: fresh orders."


def test_prominence_uses_saved_days(tmp_path):
    for offset, day in enumerate(("2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06")):
        save(
            Envelope(
                insight_id=INSIGHT_ID,
                trading_date=day,
                as_of_ist="2026-11-06T18:00:00+05:30",
                status="ok",
                headline="Banks led sector news today",
                body="Banks led: lenders won fresh mandates.",
                facts={"positive_score": 0.1, "negative_score": -0.1},
            ),
            root=tmp_path / "data",
        )
        del offset
    high = build(_ctx(tmp_path, RepeatClient(_both_sides()), _echo()))
    assert high.prominence == "high"

    quiet_root = tmp_path / "quiet"
    for day in ("2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"):
        save(
            Envelope(
                insight_id=INSIGHT_ID,
                trading_date=day,
                as_of_ist="2026-11-06T18:00:00+05:30",
                status="ok",
                headline="Banks led sector news today",
                body="Banks led: lenders won fresh mandates.",
                facts={"positive_score": 0.1},
            ),
            root=quiet_root,
        )
    cfg = _cfg(tmp_path)
    cfg = load_config(
        {
            "INSIGHTS_DATA_DIR": str(quiet_root),
            "INSIGHTS_LOG_DIR": str(tmp_path / "logs"),
            "INSIGHTS_HOLIDAYS_PATH": str(tmp_path / "holidays.json"),
            "INSIGHTS_CUTOFF_IST": "23:59",
        }
    )
    ctx = _ctx(tmp_path, RepeatClient(_both_sides()), _echo())
    ctx.config = cfg
    assert build(ctx).prominence == "normal"


def test_dry_run_records_facts_then_stops_before_a_card(tmp_path):
    def halt(system, user, schema, max_tokens=400):
        raise DryRunHalt()

    ctx = _ctx(tmp_path, RepeatClient(_both_sides()), halt)
    try:
        build(ctx)
    except DryRunHalt:
        pass
    else:
        raise AssertionError("dry run should stop at the model call")
    assert ctx.facts["positive_sector"] == "Banks"
    assert ctx.facts["ranking"]


def test_backtest_writes_a_report_and_does_not_save(tmp_path, monkeypatch):
    saved = []
    monkeypatch.setattr("ai_insight.common.store.save", lambda *args, **kwargs: saved.append(args))

    def factory(ctx):
        return _echo()

    path = backtest(
        3,
        end=DAY,
        config=_cfg(tmp_path),
        client=RepeatClient(_both_sides()),
        llm=factory,
        report_path=tmp_path / "sector_leaderboard_backtest.md",
    )
    text = path.read_text(encoding="utf-8")
    assert saved == []
    for day in ("2026-11-11", "2026-11-12", "2026-11-13"):
        assert f"## {day}" in text
    assert "### Ranking" in text
    assert "### Chosen" in text
    assert "### Stories used" in text
    assert "Banks" in text and "Realty" in text
    assert "Banks win a large corporate mandate" in text
    assert "Headline:" in text and "Body:" in text
    assert "lenders won fresh corporate mandates" in text
    assert "ok=3" in text
    assert "23:59" in text


def test_cli_backtest_flag_does_not_call_the_model(monkeypatch, tmp_path):
    seen = {}

    def fake(n, end=None, **kwargs):
        seen["n"] = n
        seen["end"] = end
        target = tmp_path / "report.md"
        target.write_text("ok", encoding="utf-8")
        return target

    monkeypatch.setattr("ai_insight.sector_leaderboard.run.backtest", fake)
    assert main(["--backtest", "3", "--date", "2026-11-13"]) == 0
    assert seen == {"n": 3, "end": date(2026, 11, 13)}


def test_main_forwards_live_flag_to_cli_main(monkeypatch):
    seen: list[list[str]] = []

    def fake_cli(_insight_id, _build, argv):
        seen.append(list(argv or []))
        return 0

    monkeypatch.setattr("ai_insight.sector_leaderboard.run.cli_main", fake_cli)
    assert main(["--live"]) == 0
    assert seen == [["--live"]]
