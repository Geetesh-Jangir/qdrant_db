"""Group pipeline errors into Google News vs Jev for run logs and JSON."""

from __future__ import annotations

from typing import Any

from news_pipeline.news_dates import covered_calendar_days, describe_fetch_window
from news_pipeline.run_log import clip_log_text

_GOOGLE_STAGES = frozenset({"fetch_google_news"})
_JEV_STAGES = frozenset({"jev_title_screen", "jev_article_scores", "merge_entity_links"})


def fetch_window_fields(settings) -> dict[str, Any]:
    days = covered_calendar_days(settings)
    return {
        "dates": days,
        "window": describe_fetch_window(settings),
        "news_date_range": (getattr(settings, "news_date_range", "") or "").strip() or None,
    }


def summarize_errors(errors: list[dict], *, settings=None) -> dict[str, Any]:
    window = fetch_window_fields(settings) if settings is not None else {"dates": [], "window": "", "news_date_range": None}
    google_rows: list[dict] = []
    jev_rows: list[dict] = []
    other_rows: list[dict] = []
    for row in errors or []:
        stage = str(row.get("stage") or "")
        if stage in _GOOGLE_STAGES or row.get("source") == "google_news":
            google_rows.append(row)
        elif stage in _JEV_STAGES or row.get("source") == "jev":
            jev_rows.append(row)
        else:
            other_rows.append(row)
    return {
        "google_news": _bucket("google_news", google_rows, window),
        "jev": _bucket("jev", jev_rows, window),
        "other": _bucket("other", other_rows, window) if other_rows else None,
    }


def write_error_summary(run_log, errors: list[dict], *, settings=None) -> dict[str, Any]:
    summary = summarize_errors(errors, settings=settings)
    if run_log is None:
        return summary
    run_log.write("--- error summary ---")
    for key in ("google_news", "jev"):
        bucket = summary[key]
        run_log.write(
            f"ERROR SUMMARY source={key} count={bucket['count']} "
            f"entity_count={len(bucket['entities'])} "
            f"dates={bucket['dates'] or 'relative_window'} "
            f"window={bucket['window']}"
        )
        if not bucket["entities"]:
            run_log.write(f"ERROR SUMMARY source={key} entities=[]")
        else:
            run_log.write(
                f"ERROR SUMMARY source={key} entities=[{', '.join(bucket['entities'])}]"
            )
        for item in bucket["errors"]:
            names = item.get("entities") or []
            name_bit = f" entities=[{', '.join(names)}]" if names else ""
            dates = item.get("dates") or bucket["dates"]
            date_bit = f" dates={dates}" if dates else ""
            run_log.write(
                f"ERROR DETAIL source={key} stage={item.get('stage')} "
                f"count={item.get('count', 1)}{name_bit}{date_bit} "
                f"error={clip_log_text(str(item.get('error') or ''), limit=400)}"
            )
    other = summary.get("other")
    if other and other["count"]:
        run_log.write(f"ERROR SUMMARY source=other count={other['count']}")
    run_log.write("--- end error summary ---")
    return summary


def _bucket(source: str, rows: list[dict], window: dict[str, Any]) -> dict[str, Any]:
    entities: list[str] = []
    seen: set[str] = set()
    dates: list[str] = list(window.get("dates") or [])
    date_seen = set(dates)
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        names = _entity_names(row)
        for name in names:
            if name not in seen:
                seen.add(name)
                entities.append(name)
        for day in row.get("dates") or []:
            if day not in date_seen:
                date_seen.add(day)
                dates.append(day)
        pub = str(row.get("published_at") or "")[:10]
        if pub and pub not in date_seen and len(pub) == 10:
            date_seen.add(pub)
            dates.append(pub)
        key = (str(row.get("stage") or source), str(row.get("error") or ""))
        bucket = grouped.setdefault(
            key,
            {
                "source": source,
                "stage": key[0],
                "error": key[1],
                "count": 0,
                "entities": [],
                "urls": [],
                "dates": list(row.get("dates") or window.get("dates") or []),
            },
        )
        bucket["count"] += int(row.get("count") or 1)
        for name in names:
            if name not in bucket["entities"]:
                bucket["entities"].append(name)
        url = row.get("url")
        if url and url not in bucket["urls"]:
            bucket["urls"].append(url)
    return {
        "source": source,
        "count": sum(item["count"] for item in grouped.values()) if grouped else 0,
        "entities": entities,
        "dates": dates,
        "window": window.get("window"),
        "news_date_range": window.get("news_date_range"),
        "errors": list(grouped.values()),
    }


def _entity_names(row: dict) -> list[str]:
    names: list[str] = []
    for key in ("entities", "entities_sample"):
        for name in row.get(key) or []:
            text = str(name).strip()
            if text and text not in names:
                names.append(text)
    for key in ("name", "entity"):
        text = str(row.get(key) or "").strip()
        if text and text not in names:
            names.append(text)
    return names
