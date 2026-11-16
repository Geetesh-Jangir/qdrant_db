"""Build the sector leaderboard card and run it from the command line."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Callable

from ai_insight.common.config import CommonConfig, load_config
from ai_insight.common.display import fmt_pct, sector_label
from ai_insight.common.prose_guard import scrub_refusal_prose
from ai_insight.common.run_log import RunLog
from ai_insight.common.runner import RunContext, cli_main
from ai_insight.common.schemas import Chip, Envelope, Meta, Source, Viz
from ai_insight.common.store import list_dates, load
from ai_insight.common.time_ist import ist_now, session_window
from ai_insight.common.trading_calendar import is_trading_day, prev_trading_day

from ai_insight.sector_leaderboard.fetch import SectorFetch, fetch_sector_stories
from ai_insight.sector_leaderboard.prompt import PROMPT_VERSION, SYSTEM, build_user
from ai_insight.sector_leaderboard.schema import INSIGHT_ID, SectorFacts, SectorScore, StoryScore, Themes, llm_schema
from ai_insight.sector_leaderboard.score import (
    Ranking,
    publishable,
    rank,
    score_sector,
    shown,
    top_stories,
    viz_items,
)
from ai_insight.sector_leaderboard.score import prominence as score_prominence

_WORD_LIMIT = 55
_HEADLINE_LIMIT = 12
_BANNED = ("should buy", "will rise", "guaranteed", "target price")
_EXTRA_LEAD = "Several separate stories backed the lead."
_EXTRA_LAG = "Several separate stories backed the laggard."
_HISTORY_DAYS = 20


def build(ctx: RunContext) -> Envelope:
    from ai_insight.common.entity_retrieval import sector_names_for_pulse
    from ai_insight.common.retrieval_plan import plan_window

    ctx.window, _ = plan_window(ctx, "sector_leaderboard")
    best_names, worst_names, week_meta = sector_names_for_pulse(ctx)
    target = list(dict.fromkeys([*best_names, *worst_names]))
    fetched = fetch_sector_stories(
        ctx.window,
        client=getattr(ctx, "qdrant", None),
        log=ctx.log,
        only_sectors=target or None,
    )
    sectors = [score_sector(item.name, item.clusters) for item in fetched.sectors]
    ranking = _week_ranking(sectors, best_names, worst_names, week_meta)
    facts = _facts(ctx, fetched, ranking)
    facts["week_movers"] = week_meta
    ctx.emit_facts(facts)
    best_name = ranking.best.display if ranking.best else "-"
    worst_name = ranking.worst.display if ranking.worst else "-"
    ctx.log.line(
        "SCORE",
        f"with_news={facts['sectors_with_news']} eligible={facts['eligible_count']} "
        f"best={best_name} worst={worst_name}",
    )
    if not publishable(ranking):
        ctx.log.line("SCORE", "thin coverage, so no card was written")
        return _envelope(ctx, "skipped", facts, ranking, themes=None, skip_reason="thin coverage")
    evidence_best = top_stories(ranking.best, 4) if ranking.best else []
    evidence_worst = top_stories(ranking.worst, 4) if ranking.worst else []
    themes, problems = _themes(ctx, ranking, evidence_best, evidence_worst)
    if themes is None:
        ctx.log.warning("theme check failed twice; the card is saved as degraded")
        return _envelope(
            ctx,
            "degraded",
            facts,
            ranking,
            themes=None,
            problems=problems,
        )
    return _envelope(ctx, "ok", facts, ranking, themes=themes)


def compose_headline(
    best: SectorScore | None,
    worst: SectorScore | None,
    day: date,
    week_meta: dict | None = None,
) -> str:
    wm = week_meta or {}
    bi = wm.get("best_index")
    wi = wm.get("worst_index")
    if bi and wi:
        options = [
            f"{bi['display']} led the week, {wi['display']} lagged",
            f"Week's best {bi['display']}, worst {wi['display']}",
        ]
        for text in options:
            if len(text.split()) <= _HEADLINE_LIMIT:
                return text
    if best and worst:
        options = [
            f"{best.display} led, {worst.display} lagged today",
            f"{best.display} led while {worst.display} lagged",
            f"Today {best.display} led and {worst.display} lagged",
        ]
    elif best:
        options = [f"{best.display} led sector news today", f"{best.display} led the sector news"]
    else:
        name = worst.display if worst else "Sectors"
        options = [f"{name} lagged sector news today", f"{name} lagged the sector news"]
    start = day.toordinal() % len(options)
    for offset in range(len(options)):
        text = options[(start + offset) % len(options)]
        if len(text.split()) <= _HEADLINE_LIMIT:
            return text
    return options[0]


def compose_body(
    best: SectorScore | None,
    worst: SectorScore | None,
    best_theme: str,
    worst_theme: str,
    *,
    word_limit: int = _WORD_LIMIT,
    week_meta: dict | None = None,
) -> str:
    wm = week_meta or {}
    bi = wm.get("best_index")
    wi = wm.get("worst_index")
    sentences: list[str] = []
    if bi and best is not None and best_theme.strip():
        sentences.append(
            f"{bi['display']} led the week {fmt_pct(bi.get('week_change_pct') or 0)} — {_fragment(best_theme)}."
        )
    elif best is not None and best_theme.strip():
        sentences.append(f"{best.display} led: {_fragment(best_theme)}.")
    if wi and worst is not None and worst_theme.strip():
        sentences.append(
            f"{wi['display']} lagged {fmt_pct(wi.get('week_change_pct') or 0)} — {_fragment(worst_theme)}."
        )
    elif worst is not None and worst_theme.strip():
        sentences.append(f"{worst.display} lagged: {_fragment(worst_theme)}.")
    extra = _extra_line(best, worst)
    body = " ".join(sentences)
    if extra and len(sentences) < 3:
        candidate = f"{body} {extra}".strip()
        if _fits(candidate, word_limit):
            body = candidate
    return _trim_to_contract(body, word_limit)


def theme_problems(
    data: dict[str, Any],
    best_stories: list[StoryScore],
    worst_stories: list[StoryScore],
) -> list[str]:
    problems: list[str] = []
    allowed = {story.cluster_id for story in [*best_stories, *worst_stories]}
    cited = data.get("cited_cluster_ids") or []
    if not isinstance(cited, list) or not cited or any(item not in allowed for item in cited):
        problems.append("cited_cluster_ids must be chosen from the stories")
    if best_stories:
        problems.extend(_theme_problem("best_theme", data.get("best_theme"), best_stories))
    if worst_stories:
        problems.extend(_theme_problem("worst_theme", data.get("worst_theme"), worst_stories))
    return problems


def saved_history(root: Path, exclude: str) -> tuple[list[float], int]:
    """Absolute scores from the last 20 saved ok or degraded days, oldest last is fine."""
    pooled: list[float] = []
    days = 0
    for trading_date in reversed(list_dates(INSIGHT_ID, root=root)):
        if trading_date == exclude:
            continue
        envelope = load(INSIGHT_ID, trading_date, root=root)
        if envelope is None or envelope.status not in {"ok", "degraded"}:
            continue
        day_scores = _abs_scores(envelope.facts)
        if not day_scores:
            continue
        pooled.extend(day_scores)
        days += 1
        if days >= _HISTORY_DAYS:
            break
    return pooled, days


def backtest(
    n: int,
    *,
    end: date | None = None,
    config: CommonConfig | None = None,
    client: Any = None,
    llm: Callable[[RunContext], Callable[..., Any]] | None = None,
    report_path: Path | None = None,
) -> Path:
    """Run the last n trading days without saving. One bad day is recorded and skipped."""
    if n < 1:
        raise ValueError("backtest N must be at least 1")
    cfg = config or load_config()
    end_day = end or prev_trading_day(ist_now().date(), holidays_path=cfg.holidays_path)
    days = trading_days_ending(n, end_day, cfg.holidays_path)
    history: list[float] = []
    history_days = 0
    sections: list[str] = []
    counts: Counter[str] = Counter()
    for day in days:
        ctx = _context(day, cfg, client=client, llm=llm)
        ctx.score_history = list(history)  # type: ignore[attr-defined]
        ctx.score_history_days = history_days  # type: ignore[attr-defined]
        try:
            envelope = build(ctx)
        except Exception as exc:
            counts["error"] += 1
            sections.append(f"## {day.isoformat()}\n\nError: {type(exc).__name__}: {exc}\n")
            continue
        counts[envelope.status] += 1
        sections.append(_report_section(envelope))
        if envelope.status in {"ok", "degraded"}:
            day_scores = _abs_scores(envelope.facts)
            if day_scores:
                history.extend(day_scores)
                history_days += 1
    path = report_path or (cfg.data_dir / "_reports" / "sector_leaderboard_backtest.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    cutoff = cfg.cutoff_ist or "23:59 IST cap (INSIGHTS_CUTOFF_IST is not set)"
    header = "\n".join(
        [
            "# Sector leaderboard backtest",
            "",
            f"Days requested: {n}",
            f"Window end: {cutoff}",
            f"Range: {days[0].isoformat()} to {days[-1].isoformat()}",
            "",
            "Each day lists the eligible ranking, the sectors that were chosen, the stories the card used, and the text that was produced. Nothing was saved.",
            "",
        ]
    )
    footer = "\n".join(
        [
            "## Summary",
            "",
            ", ".join(f"{name}={count}" for name, count in sorted(counts.items())),
            "",
        ]
    )
    path.write_text(header + "\n".join(sections) + "\n" + footer, encoding="utf-8", newline="\n")
    return path


def trading_days_ending(n: int, end: date, holidays_path: Path) -> list[date]:
    cursor = end
    if not is_trading_day(cursor, holidays_path=holidays_path):
        cursor = prev_trading_day(cursor, holidays_path=holidays_path)
    days: list[date] = []
    while len(days) < n:
        days.append(cursor)
        cursor = prev_trading_day(cursor, holidays_path=holidays_path)
    days.reverse()
    return days


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_insight.sector_leaderboard.run")
    parser.add_argument("--date", default="", help="Trading date YYYY-MM-DD. Default: today in IST.")
    parser.add_argument("--force", action="store_true", help="Rewrite an existing ok file.")
    parser.add_argument("--dry-run", action="store_true", help="Print facts and prompts. Do not call the model or save.")
    parser.add_argument("--verbose", action="store_true", help="Keep the full prompt next to the log.")
    parser.add_argument("--backtest", type=int, default=0, metavar="N", help="Run the last N trading days and write a markdown report. Does not save cards.")
    known, _rest = parser.parse_known_args(argv)
    if known.backtest:
        end = date.fromisoformat(known.date) if known.date else None
        path = backtest(known.backtest, end=end)
        print(f"backtest report {path}")
        return 0
    return cli_main(INSIGHT_ID, build, argv)


def _themes(
    ctx: RunContext,
    ranking: Ranking,
    best_stories: list[StoryScore],
    worst_stories: list[StoryScore],
) -> tuple[Themes | None, list[str]]:
    sides: set[str] = set()
    if best_stories:
        sides.add("best")
    if worst_stories:
        sides.add("worst")
    schema = llm_schema(
        [story.cluster_id for story in best_stories],
        [story.cluster_id for story in worst_stories],
        sides,
    )
    user = build_user(
        ranking.best.display if ranking.best else None,
        best_stories,
        ranking.worst.display if ranking.worst else None,
        worst_stories,
        week_meta=getattr(ctx, "facts", {}).get("week_movers") or {},
    )
    prompt = user
    problems: list[str] = ["no reply"]
    for _attempt in range(2):
        try:
            result = ctx.llm(SYSTEM, prompt, schema, 400)
        except Exception as exc:
            problems = [f"{type(exc).__name__}: {exc}"]
            prompt = user + "\n\nThe previous reply failed: " + problems[0] + "\nReturn one JSON object that matches the schema."
            continue
        data = result.data if hasattr(result, "data") else result
        if not isinstance(data, dict):
            problems = ["reply was not a JSON object"]
            prompt = user + "\n\nThe previous reply failed: reply was not a JSON object."
            continue
        problems = theme_problems(data, best_stories, worst_stories)
        if not problems:
            return Themes.model_validate(
                {
                    "best_theme": str(data.get("best_theme") or ""),
                    "worst_theme": str(data.get("worst_theme") or ""),
                    "cited_cluster_ids": list(data.get("cited_cluster_ids") or []),
                }
            ), []
        prompt = user + "\n\nThe previous reply failed: " + "; ".join(problems) + "\nFix the reply and return JSON."
    return None, problems


def _envelope(
    ctx: RunContext,
    status: str,
    facts: dict[str, Any],
    ranking: Ranking,
    *,
    themes: Themes | None,
    skip_reason: str | None = None,
    problems: list[str] | None = None,
) -> Envelope:
    best = ranking.best
    worst = ranking.worst
    headline = ""
    body = ""
    chips: list[Chip] = []
    sources: list[Source] = []
    items: list[dict[str, Any]] = []
    cluster_ids: list[str] = []
    validation: dict[str, Any] = {}
    if status == "skipped":
        headline = ""
        body = ""
    else:
        best_theme = themes.best_theme if themes else ""
        worst_theme = themes.worst_theme if themes else ""
        if best_theme:
            facts["best_theme"] = best_theme
        if worst_theme:
            facts["worst_theme"] = worst_theme
        wm = facts.get("week_movers") or {}
        headline = compose_headline(best, worst, ctx.trading_date, wm)
        if status == "degraded":
            body = _degraded_body(best, worst)
            validation = {"ok": False, "errors": list(problems or [])}
        else:
            body = scrub_refusal_prose(compose_body(best, worst, best_theme, worst_theme, week_meta=wm))
            cluster_ids = list(themes.cited_cluster_ids) if themes else []
        chips = _chips(ranking, int(facts["sectors_with_news"]))
        items = viz_items(ranking.eligible)
        sources = _sources(ranking, cluster_ids)
    level = "normal"
    if status in {"ok", "degraded"}:
        level = _prominence(ctx, ranking)
    return Envelope(
        insight_id=INSIGHT_ID,
        trading_date=ctx.trading_date.isoformat(),
        as_of_ist=ist_now().isoformat(),
        status=status,  # type: ignore[arg-type]
        skip_reason=skip_reason,
        prominence=level,  # type: ignore[arg-type]
        headline=headline,
        body=body,
        chips=chips,
        viz=Viz(type="diverging_bars", data={"items": items}),
        sources=sources,
        facts=facts,
        meta=Meta(prompt_version=PROMPT_VERSION, cluster_ids=cluster_ids, validation=validation),
    )


def _week_ranking(
    sectors: list[SectorScore],
    best_names: list[str],
    worst_names: list[str],
    week_meta: dict[str, Any],
) -> Ranking:
    by_name = {sector.name: sector for sector in sectors}
    best: SectorScore | None = None
    for name in best_names:
        if name in by_name:
            best = by_name[name]
            break
    worst: SectorScore | None = None
    for name in worst_names:
        if name in by_name:
            worst = by_name[name]
            break
    if best is None and worst is None:
        return rank(sectors)
    eligible = [sector for sector in sectors if sector.n_stories >= 1]
    return Ranking(sectors=sectors, eligible=eligible, best=best, worst=worst)


def _facts(ctx: RunContext, fetched: SectorFetch, ranking: Ranking) -> dict[str, Any]:
    evidence: dict[str, list[dict[str, Any]]] = {}
    if ranking.best is not None:
        evidence["best"] = [_story_fact(story) for story in top_stories(ranking.best)]
    if ranking.worst is not None:
        evidence["worst"] = [_story_fact(story) for story in top_stories(ranking.worst)]
    model = SectorFacts(
        trading_date=ctx.trading_date.isoformat(),
        window_utc=[ctx.window[0], ctx.window[1]],
        positive_sector=ranking.best.name if ranking.best else "",
        negative_sector=ranking.worst.name if ranking.worst else "",
        positive_score=shown(ranking.best.score) if ranking.best else None,
        negative_score=shown(ranking.worst.score) if ranking.worst else None,
        sectors_with_news=len(fetched.sectors),
        eligible_count=len(ranking.eligible),
        ranking=[_rank_row(sector) for sector in ranking.eligible],
        evidence=evidence,
        gate={
            "articles_scanned": fetched.diagnostics.articles_scanned,
            "entities_scanned": fetched.diagnostics.entities_scanned,
            "entities_passed": fetched.diagnostics.entities_passed,
            "dropped": dict(fetched.diagnostics.dropped),
        },
    )
    return model.model_dump(mode="json")


def _rank_row(sector: SectorScore) -> dict[str, Any]:
    return {
        "name": sector.name,
        "display": sector.display,
        "score": shown(sector.score),
        "stories": sector.n_stories,
        "cluster_ids": [story.cluster_id for story in sector.stories],
    }


def _story_fact(story: StoryScore) -> dict[str, Any]:
    payload = story.model_dump(mode="json")
    payload["weight"] = round(float(story.weight), 4)
    payload["magnitude"] = round(float(story.magnitude), 4)
    return payload


def _chips(ranking: Ranking, sectors_with_news: int) -> list[Chip]:
    chips: list[Chip] = []
    if ranking.best is not None:
        chips.append(Chip(label=ranking.best.display, value=f"{ranking.best.n_stories} stories", tone="positive"))
    if ranking.worst is not None:
        chips.append(Chip(label=ranking.worst.display, value=f"{ranking.worst.n_stories} stories", tone="negative"))
    chips.append(Chip(label="Sectors tracked", value=f"{sectors_with_news} with news", tone="neutral"))
    return chips


def _sources(ranking: Ranking, cited: list[str]) -> list[Source]:
    by_id: dict[str, StoryScore] = {}
    best_ids: set[str] = set()
    worst_ids: set[str] = set()
    if ranking.best is not None:
        for story in ranking.best.stories:
            by_id[story.cluster_id] = story
            best_ids.add(story.cluster_id)
    if ranking.worst is not None:
        for story in ranking.worst.stories:
            by_id[story.cluster_id] = story
            worst_ids.add(story.cluster_id)
    ordered: list[str] = []
    for bucket in ([item for item in cited if item in best_ids], [item for item in cited if item in worst_ids]):
        if bucket and bucket[0] not in ordered:
            ordered.append(bucket[0])
    for item in cited:
        if item not in ordered:
            ordered.append(item)
    if not ordered:
        for sector in (ranking.best, ranking.worst):
            if sector is not None and sector.stories:
                ordered.append(top_stories(sector, 1)[0].cluster_id)
    sources: list[Source] = []
    seen: set[str] = set()
    for cluster_id in ordered:
        story = by_id.get(cluster_id)
        if story is None or not story.url or story.url in seen:
            continue
        seen.add(story.url)
        sources.append(
            Source(title=story.title, url=story.url, source=story.source, published_at=story.published_at)
        )
        if len(sources) >= 3:
            break
    return sources


def _prominence(ctx: RunContext, ranking: Ranking) -> str:
    current: list[float] = []
    if ranking.best is not None:
        current.append(shown(abs(ranking.best.score)))
    if ranking.worst is not None:
        current.append(shown(abs(ranking.worst.score)))
    history = getattr(ctx, "score_history", None)
    if history is not None:
        days = int(getattr(ctx, "score_history_days", 0))
        return score_prominence(current, list(history), days)
    pooled, days = saved_history(ctx.config.data_dir, ctx.trading_date.isoformat())
    return score_prominence(current, pooled, days)


def _degraded_body(best: SectorScore | None, worst: SectorScore | None) -> str:
    if best is not None and worst is not None:
        return f"{best.display} and {worst.display} stood out in today's sector news."
    side = best or worst
    name = side.display if side is not None else sector_label("Banks")
    return f"{name} stood out in today's sector news."


def _extra_line(best: SectorScore | None, worst: SectorScore | None) -> str | None:
    if best is not None and best.n_stories >= 3:
        return _EXTRA_LEAD
    if best is None and worst is not None and worst.n_stories >= 3:
        return _EXTRA_LAG
    return None


def _fragment(theme: str) -> str:
    return theme.strip().rstrip(".").strip()


def _fits(text: str, word_limit: int) -> bool:
    return len(text.split()) <= word_limit and _sentence_count(text) <= 3


def _trim_to_contract(body: str, word_limit: int) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", body) if part.strip()]
    while parts and not _fits(" ".join(parts), word_limit):
        parts.pop()
    return " ".join(parts)


def _sentence_count(text: str) -> int:
    return len([part for part in re.split(r"[.!?]+", text) if part.strip()])


def _theme_problem(name: str, theme: Any, stories: list[StoryScore]) -> list[str]:
    text = str(theme or "").strip()
    if not text:
        return [f"{name} is empty"]
    problems: list[str] = []
    if len(text.split()) > 14:
        problems.append(f"{name} is longer than 14 words")
    if re.search(r"[.!?]", text):
        problems.append(f"{name} contains a sentence break")
    evidence = " ".join(f"{story.title} {story.text}" for story in stories)
    allowed = set(re.findall(r"\d+", evidence))
    invented = [number for number in re.findall(r"\d+", text) if number not in allowed]
    if invented:
        problems.append(f"{name} uses numbers not in the stories: " + ", ".join(invented))
    lowered = text.lower()
    banned = [phrase for phrase in _BANNED if phrase in lowered]
    if banned:
        problems.append(f"{name} contains " + ", ".join(banned))
    return problems


def _abs_scores(facts: dict[str, Any]) -> list[float]:
    found: list[float] = []
    for key in ("positive_score", "negative_score"):
        value = facts.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        found.append(abs(float(value)))
    return found


def _context(
    day: date,
    config: CommonConfig,
    *,
    client: Any,
    llm: Callable[[RunContext], Callable[..., Any]] | None,
) -> RunContext:
    import uuid

    window = session_window(day, config=config)
    log = RunLog(
        insight_id=INSIGHT_ID,
        trading_date=day.isoformat(),
        run_id=uuid.uuid4().hex[:6],
        log_dir=config.log_dir,
    )
    ctx = RunContext(
        insight_id=INSIGHT_ID,
        trading_date=day,
        window=window,
        dry_run=False,
        config=config,
        log=log,
        llm=lambda *_args, **_kwargs: None,
    )
    ctx.qdrant = client  # type: ignore[attr-defined]
    ctx.llm = llm(ctx) if llm is not None else _live_llm(ctx)
    return ctx


def _live_llm(ctx: RunContext) -> Callable[..., Any]:
    def call(system: str, user: str, json_schema: dict[str, Any], max_tokens: int = 400) -> Any:
        ctx.prompts.append({"system": system, "user": user, "schema": json_schema, "max_tokens": max_tokens})
        from ai_insight.common.llm import generate_json

        result = generate_json(system, user, json_schema, max_tokens=max_tokens, config=ctx.config)
        ctx.add_usage(result.usage)
        return result

    return call


def _report_section(envelope: Envelope) -> str:
    facts = envelope.facts
    lines = [
        f"## {envelope.trading_date}",
        "",
        f"Status: {envelope.status}",
        f"Prominence: {envelope.prominence}",
        f"Headline: {envelope.headline or '-'}",
        f"Body: {envelope.body or '-'}",
        f"Best theme: {facts.get('best_theme') or '-'}",
        f"Worst theme: {facts.get('worst_theme') or '-'}",
        "",
        "### Ranking",
        "",
        "| Sector | Score | Stories | Cluster ids |",
        "| --- | --- | --- | --- |",
    ]
    for row in facts.get("ranking") or []:
        ids = ", ".join(row.get("cluster_ids") or [])
        lines.append(
            f"| {_cell(row.get('display'))} | {row.get('score')} | {row.get('stories')} | {_cell(ids)} |"
        )
    if not facts.get("ranking"):
        lines.append("| - | - | - | - |")
    errors = envelope.meta.validation.get("errors") or []
    if errors:
        lines.extend(["", "Theme check: " + "; ".join(str(item) for item in errors)])
    lines.extend(
        [
            "",
            "### Chosen",
            "",
            f"Best: {_cell(facts.get('positive_sector')) or '-'} ({facts.get('positive_score')})",
            f"Worst: {_cell(facts.get('negative_sector')) or '-'} ({facts.get('negative_score')})",
            "",
            "### Stories used",
            "",
        ]
    )
    lines.extend(_story_lines(facts.get("evidence") or {}))
    gate = facts.get("gate") or {}
    dropped = gate.get("dropped") or {}
    drop_text = " ".join(f"{key}={value}" for key, value in dropped.items())
    lines.extend(
        [
            "",
            "### Gate",
            "",
            f"scanned={gate.get('articles_scanned', 0)} passed={gate.get('entities_passed', 0)} dropped[{drop_text}]",
            "",
        ]
    )
    return "\n".join(lines)


def _story_lines(evidence: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for side in ("best", "worst"):
        stories = evidence.get(side) or []
        lines.append(f"{side.title()}")
        if not stories:
            lines.append("- none")
            lines.append("")
            continue
        for story in stories:
            lines.append(
                "- "
                + " | ".join(
                    [
                        _cell(story.get("cluster_id")),
                        _cell(story.get("title")),
                        _cell(story.get("source")),
                        _cell(story.get("published_at")),
                        f"weight={story.get('weight')}",
                        f"sign={story.get('sign')}",
                        _cell(story.get("url")),
                    ]
                )
            )
            text = _cell(story.get("text"))
            if text:
                lines.append(f"  {text}")
        lines.append("")
    return lines


def _cell(value: Any) -> str:
    return str(value or "").replace("|", "/").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
