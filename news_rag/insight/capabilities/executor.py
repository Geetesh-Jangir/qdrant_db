"""Capability executor — runs six capability tools in parallel with deadline enforcement.

Each capability delegates to existing layer_tools / tool_runners adapters.
The executor validates args, respects fan-out caps, and uses the TTL cache.
"""

from __future__ import annotations

import contextvars
import logging
import re
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from news_rag.config import get_settings
from news_rag.insight.capabilities.cache import get_capability_cache
from news_rag.insight.capabilities.catalog import validate_capability_args
from news_rag.insight.contracts import ToolCall, RequestTelemetry

logger = logging.getLogger(__name__)


def _isin_for_fund_name(fund_name: str, ctx: dict[str, Any] | None = None) -> str:
    from news_rag.fund_search import get_fund_index

    name = str(fund_name or "").strip()
    if not name:
        return ""
    ctx = ctx or {}
    mapping = ctx.get("fund_isins") if isinstance(ctx.get("fund_isins"), dict) else {}
    key = name.lower()
    if key in mapping:
        return str(mapping[key]).strip().upper()
    for map_name, isin in mapping.items():
        mn = str(map_name).strip().lower()
        if mn == key or key in mn or mn in key:
            return str(isin).strip().upper()
    ctx_isin = str(ctx.get("fund_isin") or "").strip().upper()
    if ctx_isin:
        return ctx_isin
    detail, ambiguous, _close = get_fund_index().lookup_extracted_fund(name=name)
    if ambiguous and not detail:
        logger.debug("ambiguous catalog name for ISIN lookup: %s", name[:80])
    return str((detail or {}).get("isin") or "").strip().upper()


def _fund_payload_matches_fund(
    fund_name: str,
    data: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> bool:
    """Reject conversation or TTL cache rows built for a different ISIN."""
    if not str(fund_name or "").strip() or not isinstance(data, dict):
        return False
    expected = _isin_for_fund_name(fund_name, ctx)
    insights = data.get("fund_insights") if isinstance(data.get("fund_insights"), dict) else {}
    got_isin = str(insights.get("isin") or "").strip().upper()
    if expected and got_isin and got_isin != expected:
        return False
    insight_name = str(insights.get("fund_name") or "").strip().lower()
    target = fund_name.strip().lower()
    if insight_name and target and insight_name != target:
        if insight_name not in target and target not in insight_name:
            return False
    rating = data.get("rs_rating") if isinstance(data.get("rs_rating"), dict) else {}
    if expected and rating.get("fund_type") == "debt" and "flexi cap" in target:
        return False
    return True


def _compare_cache_label(fund_names: list[str]) -> str:
    """Conversation cache key for compare_funds — one slot per fund pair, not per conversation."""
    parts: list[str] = []
    for name in fund_names:
        n = " ".join(str(name or "").lower().split())
        if not n:
            continue
        isin = _isin_for_fund_name(name)
        parts.append((isin or n)[:48])
    if not parts:
        return "compare|empty"
    return "compare|" + "|".join(sorted(parts))


def _compare_payload_matches_funds(fund_names: list[str], data: dict[str, Any]) -> bool:
    from news_rag.insight.memory.fund_context import compare_payload_matches_funds

    return compare_payload_matches_funds(fund_names, data)


def _capability_cache_key(
    tool: str,
    fund_name: str,
    args: dict[str, Any],
    ctx: dict[str, Any],
) -> str:
    """Cache keys must reflect modules, portfolio shape, and manager question focus."""
    if tool == "get_portfolio_data":
        sections = ",".join(sorted(args.get("sections") or ["holdings", "sectors"]))
        top_n = int(args.get("top_n") or 3)
        find = str(args.get("find") or "").strip()
        return f"{fund_name}|sections={sections}|top_n={top_n}|find={find}"
    if tool == "screen_funds_by_exposure":
        question = " ".join(str(ctx.get("question") or args.get("focus_question") or "").lower().split())[:180]
        return (
            f"screen|q={question}|w={args.get('return_window')}|n={args.get('top_n')}|"
            f"rating={bool(args.get('rating_screen'))}|sector={args.get('sector') or ''}"
        )
    modules = ",".join(args.get("modules") or [])
    windows = ",".join(str(item) for item in (args.get("windows") or []))
    key = f"{fund_name}|{modules}|w={windows}"
    if "managers" in (args.get("modules") or []):
        from news_rag.insight.manager_view import infer_manager_roster_focus

        focus = infer_manager_roster_focus(str(ctx.get("question") or ""))
        key = f"{key}|mgr_focus={focus}"
    if "attribution" in (args.get("modules") or []):
        key = f"{key}|attr_w={args.get('window_days', 30)}|attr_n={args.get('top_n', 3)}"
    if "return_series" in (args.get("modules") or []):
        key = f"{key}|series_w={args.get('window_days', 180)}"
    if "drawdown" in (args.get("modules") or []):
        periods = ",".join(args.get("periods") or [])
        key = f"{key}|dd={periods}|cat={bool(args.get('include_category'))}"
    if "risk" in (args.get("modules") or []):
        key = f"{key}|risk=1"
    if args.get("pillars") or "rating" in (args.get("modules") or []):
        from news_rag.fund_risk import rating_needs_pillars

        if rating_needs_pillars(args):
            key = f"{key}|pillars=1"
    return key


def _repair_incomplete_fund_data(
    fund_name: str,
    args: dict[str, Any],
    ctx: dict[str, Any],
    results: dict[str, Any],
) -> None:
    """One repair pass when a stub or a failed sub-call left requested modules empty."""
    if _return_slice_covers("get_fund_data", args, results):
        return
    modules = [str(item).lower() for item in (args.get("modules") or [])]
    detail = _detail_for_fund_tool(fund_name, ctx)
    isin = str((detail or {}).get("isin") or _isin_for_fund_name(fund_name) or "").strip().upper()

    if "snapshot" in modules:
        snap = results.get("snapshot") if isinstance(results.get("snapshot"), dict) else {}
        windows = [str(item).upper() for item in (args.get("windows") or []) if str(item).strip()]
        rets = snap.get("returns") if isinstance(snap.get("returns"), dict) else {}
        need_snapshot = not snap or (
            windows and not all(code in {str(key).upper() for key in rets} for code in windows)
        )
        if need_snapshot:
            from news_rag.insight.layer_tools import run_fund_snapshot

            snap_ctx = {
                **ctx,
                "fund_name": fund_name,
                "fund_names": [fund_name],
                "windows": args.get("windows") or ["1Y", "3Y", "5Y"],
            }
            snap_out = run_fund_snapshot(snap_ctx)
            if snap_out.get("ok"):
                results["snapshot"] = snap_out.get("data", {})

    if isin:
        from news_rag.fund_rupeestop_metrics import fetch_vs_benchmark, merge_fund_insight_metrics

        if "vs_benchmark" in modules and not isinstance(results.get("vs_benchmark"), dict):
            vs = fetch_vs_benchmark(isin)
            if vs:
                results["vs_benchmark"] = vs
        if "rating" in modules and not isinstance(results.get("rs_rating"), dict):
            from news_rag.fund_risk import rating_for_request

            rating = rating_for_request(detail, args)
            if rating:
                results["rs_rating"] = rating
        if detail:
            vs_block = results.get("vs_benchmark") if isinstance(results.get("vs_benchmark"), dict) else None
            insights = merge_fund_insight_metrics(detail, vs_benchmark=vs_block)
            if insights:
                results["fund_insights"] = insights


def refetch_partial_fund_tools(
    plan: Any,
    wave_results: list[dict[str, Any]],
    ctx: dict[str, Any],
) -> None:
    """Bypass caches once when Wave 1 stored incomplete fund payloads."""
    if not plan or not wave_results:
        return
    call = next((item for item in (getattr(plan, "tool_calls", None) or []) if item.tool == "get_fund_data"), None)
    if call is None:
        return
    args = validate_capability_args("get_fund_data", call.arguments or {})
    for index, row in enumerate(wave_results):
        if row.get("tool") != "get_fund_data":
            continue
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        fund = str(row.get("fund") or "").strip()
        if (
            _return_slice_covers("get_fund_data", args, data)
            and _fund_payload_matches_fund(fund, data)
        ):
            continue
        if not fund:
            continue
        repair_ctx = {**ctx, "skip_tool_cache": True}
        try:
            out = _run_get_fund_data(fund, args, repair_ctx)
        except Exception as exc:
            logger.warning("fund refetch failed for %s: %s", fund, exc)
            continue
        fresh = out.get("data") if isinstance(out.get("data"), dict) else {}
        if not fresh:
            continue
        wave_results[index] = {
            **row,
            "ok": bool(out.get("ok")),
            "data": fresh,
            "partial": bool(out.get("partial")),
            "error": str(out.get("error") or ""),
            "refetched": True,
            "cached": False,
        }


def _detail_for_fund_tool(fund_name: str, ctx: dict[str, Any] | None) -> dict[str, Any] | None:
    """Resolve this fund by name; use ctx ISIN / fund_isins before catalog name lookup."""
    from news_rag.fund_search import detail_has_live_facts, get_fund_index, resolve_fund_for_query

    ctx = ctx or {}
    isin = _isin_for_fund_name(fund_name, ctx)
    if isin:
        live = get_fund_index().get_fund_detail(isin)
        if live and detail_has_live_facts(live):
            return live
        detail, _amb, _close = get_fund_index().lookup_extracted_fund(isin=isin, name="")
        if detail and detail_has_live_facts(detail):
            return detail
    detail, _amb, _close = resolve_fund_for_query(fund_name, name=fund_name)
    if detail and not detail_has_live_facts(detail) and isin:
        live = get_fund_index().get_fund_detail(isin)
        if live and detail_has_live_facts(live):
            return live
    return detail


def _run_get_fund_data(fund_name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Delegate to existing fund snapshot / return_series / attribution tools."""
    from news_rag.insight.registry import ensure_registry

    ensure_registry()
    results: dict[str, Any] = {"fund_name": fund_name}
    modules = args.get("modules", ["snapshot"])

    if "snapshot" in modules:
        from news_rag.insight.layer_tools import run_fund_snapshot
        snap_ctx = {
            **ctx,
            "fund_name": fund_name,
            "fund_names": [fund_name],
            "windows": args.get("windows") or ["1Y", "3Y", "5Y"],
        }
        snap = run_fund_snapshot(snap_ctx)
        if snap.get("ok"):
            results["snapshot"] = snap.get("data", {})

    if "return_series" in modules:
        from news_rag.insight.tool_runners import _resolve_fund_detail
        detail = _resolve_fund_detail({**ctx, "fund_name": fund_name, "fund_names": [fund_name]})
        if detail:
            from news_rag.insight.tool_runners import run_fund_return_series_adapter
            series_ctx = {**ctx, "fund_name": fund_name, "fund_names": [fund_name], "window_days": args.get("window_days", 180)}
            series = run_fund_return_series_adapter(series_ctx)
            if series.get("ok"):
                results["return_series"] = series.get("data", {})

    if "attribution" in modules:
        from news_rag.insight.layer_tools import run_fund_attribution_tool
        attr_ctx = {**ctx, "fund_name": fund_name, "fund_names": [fund_name],
                    "window_days": args.get("window_days", 30), "top_n": args.get("top_n", 3)}
        attr = run_fund_attribution_tool(attr_ctx)
        if attr.get("ok"):
            results["attribution"] = attr.get("data", {})

    if "vs_benchmark" in modules or "rating" in modules or results.keys() - {"fund_name"}:
        detail = _detail_for_fund_tool(fund_name, ctx)
        isin = str((detail or {}).get("isin") or str(ctx.get("fund_isin") or "")).strip()
        if isin:
            from news_rag.fund_rupeestop_metrics import (
                fetch_vs_benchmark,
                merge_fund_insight_metrics,
            )

            vs = fetch_vs_benchmark(isin) if "vs_benchmark" in modules else None
            if vs:
                results["vs_benchmark"] = vs
            if detail:
                insights = merge_fund_insight_metrics(detail, vs_benchmark=vs)
                if insights:
                    results["fund_insights"] = insights
        if "rating" in modules:
            from news_rag.fund_risk import rating_for_request

            rating = rating_for_request(detail, args)
            if rating:
                results["rs_rating"] = rating

    if "limits" in modules or "composition" in modules:
        book = _detail_for_fund_tool(fund_name, ctx) or {}
        if "limits" in modules:
            results["investment_limits"] = book.get("investment_limits") or {}
        if "composition" in modules:
            results["composition"] = {
                "asset_allocation": book.get("asset_allocation") or [],
                "market_cap": book.get("market_cap") or [],
                "holding_count": book.get("holding_count"),
                "top_5_pct": book.get("top_5_pct"),
                "top_10_pct": book.get("top_10_pct"),
            }

    if "drawdown" in modules:
        from news_rag.fund_drawdown import load_fund_drawdown

        try:
            results["drawdown"] = load_fund_drawdown(
                fund_name,
                list(args.get("periods") or []),
                str(ctx.get("question") or ""),
                include_category=bool(args.get("include_category")),
            )
        except Exception as exc:
            logger.warning("drawdown load failed for %s: %s", fund_name, exc)

    if "risk" in modules:
        from news_rag.fund_risk import load_fund_risk, rating_needs_pillars

        try:
            results["risk"] = load_fund_risk(
                fund_name,
                str(ctx.get("question") or ""),
                include_pillars=rating_needs_pillars(args),
            )
        except Exception as exc:
            logger.warning("risk load failed for %s: %s", fund_name, exc)

    if "managers" in modules:
        from news_rag.fund_search import fetch_fund_managers_for_query

        mgr = fetch_fund_managers_for_query(fund_name)
        if not mgr:
            mgr = fetch_fund_managers_for_query(str(ctx.get("question") or ""))
        if mgr:
            from news_rag.insight.manager_view import enrich_manager_payload

            results["managers"] = enrich_manager_payload(
                mgr, str(ctx.get("question") or fund_name)
            )

    _repair_incomplete_fund_data(fund_name, args, ctx, results)
    if not _fund_payload_matches_fund(fund_name, results):
        isin = _isin_for_fund_name(fund_name)
        modules = [str(item).lower() for item in (args.get("modules") or [])]
        if isin and "rating" in modules:
            from news_rag.fund_risk import rating_for_request

            detail = _detail_for_fund_tool(fund_name, ctx)
            rating = rating_for_request(detail, args)
            if rating:
                results["rs_rating"] = rating
        results.pop("fund_insights", None)
        detail = _detail_for_fund_tool(fund_name, ctx)
        if detail:
            from news_rag.fund_rupeestop_metrics import merge_fund_insight_metrics

            insights = merge_fund_insight_metrics(detail)
            if insights:
                results["fund_insights"] = insights
    covers = _return_slice_covers("get_fund_data", args, results)
    has_data = bool(results.keys() - {"fund_name"})
    return {
        "ok": has_data,
        "data": results,
        "partial": has_data and not covers,
        "error": "incomplete_fund_modules" if has_data and not covers else "",
    }


def _run_get_portfolio_data(fund_name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.insight.layer_tools import run_fund_portfolio
    top_n = args.get("top_n", 3)
    find = args.get("find", "")
    include_count = "count" in args.get("sections", [])
    sections = list(args.get("sections") or ["holdings", "sectors"])
    question = str(ctx.get("question") or "")
    if re.search(
        r"\bhold(?:s|ing)?\b|\ballocation\b|\bcomposition\b|\bmade\s+of\b|\bportfolio\b",
        question,
        re.I,
    ):
        if "holdings" not in sections:
            sections.append("holdings")
        if "sectors" not in sections:
            sections.append("sectors")
    portfolio_ctx = {
        **ctx,
        "fund_name": fund_name,
        "fund_names": [fund_name],
        "top_n_holdings": top_n,
        "top_n_sectors": min(top_n, 10),
        "portfolio_sections": sections,
        "include_count": include_count,
        "find": find,
    }
    return run_fund_portfolio(portfolio_ctx)


def _run_compare_funds(fund_names: list[str], args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.insight.tool_runners import run_compare_funds_adapter
    compare_ctx = {
        **ctx,
        "fund_names": fund_names,
        "overlap": args.get("mode") in ("overlap", "both"),
        "drawdown_periods": args.get("drawdown_periods") or [],
    }
    return run_compare_funds_adapter(compare_ctx)


def _portfolio_for_fund_news(ctx: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Holdings/sectors from Wave 1 or a quick portfolio fetch for layered fund news."""
    holdings: list[dict[str, Any]] = []
    sectors: list[dict[str, Any]] = []
    fund_name = ""
    for r in ctx.get("wave1_results") or []:
        if r.get("tool") != "get_portfolio_data" or not r.get("ok"):
            continue
        data = r.get("data") if isinstance(r.get("data"), dict) else {}
        holdings = list(data.get("holdings") or [])
        sectors = list(data.get("sectors") or [])
        fund_name = str(r.get("fund") or data.get("fund_name") or "").strip()
        break

    names = list(ctx.get("fund_names") or [])
    if not fund_name and names:
        fund_name = str(names[0]).strip()

    if holdings or sectors:
        return holdings, sectors, fund_name

    if not fund_name:
        return [], [], ""

    from news_rag.fund_search import extract_top_holdings, extract_top_sectors, resolve_fund_for_query

    detail, _amb, _close = resolve_fund_for_query(fund_name)
    if not detail:
        return [], [], fund_name
    fund_name = str(
        detail.get("fund_short_name") or detail.get("fund_name") or fund_name
    ).strip()
    holdings = extract_top_holdings(detail, limit=10)
    sectors = extract_top_sectors(detail, limit=8)
    return holdings, sectors, fund_name


def _group_layered_articles(articles: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, str]]]]:
    from news_rag.snippet_clean import article_body_for_llm

    layer_map = {"holding": "holdings", "sector": "sectors", "macro": "macro"}
    grouped: dict[str, dict[str, list[dict[str, str]]]] = {}
    for row in articles:
        if not isinstance(row, dict):
            continue
        scope = layer_map.get(str(row.get("_news_layer") or ""), "macro")
        entity = str(row.get("_news_source_label") or row.get("source") or "general").strip()
        title = str(row.get("title") or "").strip()
        text = article_body_for_llm(row, limit=0)
        if not text:
            text = str(row.get("text") or row.get("summary") or "")
        grouped.setdefault(scope, {}).setdefault(entity, []).append(
            {
                "title": title,
                "headline": title,
                "text": text,
                "summary": text,
                "url": str(row.get("url") or ""),
                "source": str(row.get("source") or ""),
                "published_at": str(row.get("published_at") or ""),
                "sentiment": str(row.get("sentiment") or ""),
                "max_impact": row.get("max_impact"),
                "direction": row.get("direction"),
            }
        )
    return grouped


def _run_search_financial_news(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Market/stock news fanout, or layered holdings+sectors+macro for named funds."""
    from news_rag.insight.fund_news_scope import infer_fund_news_layers, layers_to_retrieval_keys
    from news_rag.insight.news_fanout import NewsTarget, grouped_news, search_targets

    scope = str(args.get("scope") or "market").lower()
    question = str(ctx.get("question") or "")
    topics = [str(t).strip() for t in (args.get("topics") or []) if str(t).strip()]
    subject = _news_subject(question) if scope == "market" and not topics else ""
    if subject:
        topics = [subject]
    top_n = int(args.get("top_n") or 3)
    if subject:
        top_n = max(top_n, 8)
    window_days = int(args.get("window_days") or ctx.get("window_days") or 14)
    direction = args.get("direction")
    if direction == "any":
        direction = None

    use_fund_layers = scope in ("all", "fund", "portfolio") or (
        scope in ("holdings", "sectors", "macro")
        and bool(ctx.get("fund_names"))
    )
    if use_fund_layers:
        holdings, sectors, fund_name = _portfolio_for_fund_news(ctx)
        if holdings or sectors:
            from news_rag.fund_portfolio_news import retrieve_layered_fund_news

            if scope in ("all", "fund", "portfolio"):
                layers = layers_to_retrieval_keys(infer_fund_news_layers(question))
            elif scope == "holdings":
                layers = frozenset({"holding"})
            elif scope == "sectors":
                layers = frozenset({"sector"})
            else:
                layers = frozenset({"macro"})

            articles = retrieve_layered_fund_news(
                holdings=holdings,
                sectors=sectors,
                question=question,
                fund_name=fund_name,
                window_days=window_days,
                query_log=ctx.get("query_log"),
                layers=layers,
            )
            articles = list(articles or [])[:8]
            grouped = _group_layered_articles(articles)
            return {
                "ok": bool(articles),
                "scope": scope if scope != "fund" else "all",
                "data": {
                    "grouped": grouped,
                    "articles": articles,
                    "article_count": len(articles),
                    "fund_name": fund_name,
                    "layers": sorted(layers),
                },
            }

    bullion = _bullion_topics(topics)
    named = [str(topic or "").strip() for topic in topics if str(topic or "").strip()]
    if bullion and named and len(bullion) == len(named):
        from news_rag.bullion_retrieve import retrieve_bullion_macro_news, retrieve_bullion_metal_news

        articles: list[dict[str, Any]] = []
        question = str(ctx.get("question") or "")
        query = " ".join(topics) or question
        if bullion == {"bullion"} or bullion >= {"gold", "silver"}:
            rows = retrieve_bullion_macro_news(
                query, question=question, window_days=window_days, query_log=ctx.get("query_log")
            )
            articles.extend(_bullion_articles(rows))
        else:
            for metal in sorted(bullion):
                if metal not in ("gold", "silver"):
                    continue
                rows = retrieve_bullion_metal_news(
                    metal, query, question=question, window_days=window_days, query_log=ctx.get("query_log")
                )
                articles.extend(_bullion_articles(rows))
        return {
            "ok": bool(articles),
            "scope": "macro",
            "data": {"articles": articles, "article_count": len(articles), "metal": sorted(bullion)},
        }

    targets = _news_search_targets(
        topics,
        scope=scope,
        top_n=top_n,
        window_days=window_days,
        direction=direction,
    )

    search_targets(targets)
    grouped = grouped_news(targets)
    articles = [art for t in targets for art in (t.articles or [])]
    return {
        "ok": bool(articles),
        "scope": scope,
        "data": {"grouped": grouped, "articles": articles, "article_count": len(articles)},
    }


_GENERIC_NEWS_SUBJECTS = frozenset(
    {
        "market",
        "the market",
        "markets",
        "the markets",
        "stock market",
        "the stock market",
        "india",
        "indian market",
    }
)


def _news_subject(question: str) -> str:
    """The named subject in 'news about HDFC Bank', or empty for a market-wide question."""
    import re

    match = re.search(
        r"\b(?:news|headlines?)\s+(?:about|on|regarding|for)\s+(.+)",
        question or "",
        re.I,
    )
    if not match:
        return ""
    subject = match.group(1).strip(" ?.!")
    subject = re.sub(r"\s+in\s+the\s+market$", "", subject, flags=re.I).strip()
    if len(subject) < 2 or subject.lower() in _GENERIC_NEWS_SUBJECTS:
        return ""
    return subject


_TOPIC_KEYS = {
    "bank": "banks",
    "banks": "banks",
    "banking": "banks",
}

_BULLION_TOPICS = {
    "gold": "gold",
    "silver": "silver",
    "bullion": "bullion",
    "precious metal": "bullion",
    "precious metals": "bullion",
}


def _bullion_topics(topics: list[Any]) -> set[str]:
    found: set[str] = set()
    for topic in topics or []:
        key = _BULLION_TOPICS.get(str(topic or "").strip().lower())
        if key:
            found.add(key)
    return found


def _bullion_articles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        text = str(row.get("snippet") or row.get("text") or row.get("summary") or "")
        title = str(row.get("title") or "")
        articles.append(
            {
                "title": title,
                "headline": title,
                "text": text,
                "summary": text,
                "url": str(row.get("url") or ""),
                "source": str(row.get("source") or ""),
                "published_at": str(row.get("published_at") or ""),
                "sentiment": str(row.get("sentiment") or ""),
                "max_impact": row.get("max_impact"),
                "direction": row.get("direction"),
            }
        )
    return articles


def _news_search_targets(
    topics: list[Any],
    *,
    scope: str,
    top_n: int,
    window_days: int,
    direction: str | None,
) -> list[Any]:
    """One search per distinct topic. Banking and Banks are the same search, with the asked count."""
    from news_rag.insight.news_fanout import NewsTarget

    if scope == "market" and not topics:
        from news_rag.insight.market_news import market_scope_entities

        entities = market_scope_entities(source_kind="layer1", topics=[], top_n=top_n)
    elif topics:
        entities = []
        seen: set[str] = set()
        for topic in topics:
            name = str(topic).strip()
            if not name:
                continue
            key = _TOPIC_KEYS.get(name.lower(), name.lower())
            if key in seen:
                continue
            seen.add(key)
            entities.append((name, f"{name} India market news"))
    else:
        entities = [(scope, f"{scope} India financial news")]

    limit = max(int(top_n or 8), 1)
    return [
        NewsTarget(
            scope=scope,
            entity=entity,
            query=query,
            window_days=window_days,
            direction=direction,
            limit=limit,
            chars=0,
            required=True,
        )
        for entity, query in entities
    ]


def _run_get_macro_news(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Two fresh articles for every named macro topic. No cache."""
    from news_pipeline.config import MACRO_ENTITIES
    from news_rag.insight.fund_display import complete_sentences, strip_publisher
    from news_rag.macro_news_cache import _article_text, _search_macro_parameters

    window_days = int(args.get("window_days") or ctx.get("window_days") or 30)
    specs = [(str(row["name"]), str(row["query"])) for row in MACRO_ENTITIES]
    clusters: list[dict[str, Any]] = []
    for group in _search_macro_parameters(specs, window_days):
        articles: list[dict[str, str]] = []
        for art in list(group.get("articles") or [])[:2]:
            if not isinstance(art, dict):
                continue
            body = complete_sentences(_article_text(art))
            title = strip_publisher(str(art.get("title") or art.get("headline") or ""))
            if not title or not body:
                continue
            articles.append(
                {
                    "title": title,
                    "summary": body,
                    "published_at": str(art.get("published_at") or art.get("date") or ""),
                }
            )
        if articles:
            clusters.append({"label": group.get("label") or "", "articles": articles})
    total = sum(len(cluster["articles"]) for cluster in clusters)
    return {
        "ok": bool(clusters),
        "data": {"window_days": window_days, "clusters": clusters, "article_total": total},
    }


def _attach_rs_rating_to_screen_rows(rows: list[dict[str, Any]]) -> None:
    """RupeeStop label and score from GET /api/v1/app/fund/{isin}."""
    from news_rag.fund_search import get_fund_index

    index = get_fund_index()
    for row in rows:
        if row.get("rs_label") and row.get("final_score") is not None:
            continue
        isin = str(row.get("isin") or "").strip()
        if not isin:
            continue
        detail = index.get_fund_detail(isin) or {}
        rating = detail.get("rupeestop_rating") if isinstance(detail.get("rupeestop_rating"), dict) else {}
        label = str(rating.get("label") or "").strip()
        score = rating.get("score")
        if label:
            row["rs_label"] = label
        if score is not None:
            row["final_score"] = score


def _fill_returns_from_catalog(rows: list[dict[str, Any]]) -> None:
    from news_rag.fund_search import get_fund_index

    index = get_fund_index()
    mapping = (
        ("1w", "return_1w_pct"),
        ("1m", "return_1m_pct"),
        ("3m", "return_3m_pct"),
        ("6m", "return_6m_pct"),
        ("1y", "return_1y_pct"),
        ("3y", "return_3y_pct"),
        ("5y", "return_5y_pct"),
    )
    for row in rows:
        if row.get("return_1y_pct") is not None and row.get("return_1m_pct") is not None:
            continue
        detail = index.get_fund_detail(str(row.get("isin") or "")) or {}
        returns = detail.get("returns") if isinstance(detail.get("returns"), dict) else {}
        expense = detail.get("expense_ratio") if isinstance(detail.get("expense_ratio"), dict) else {}
        for source, field in mapping:
            if row.get(field) is None and returns.get(source) is not None:
                row[field] = returns.get(source)
        if row.get("expense_ratio") is None:
            ratio = expense.get("regular")
            if ratio is None:
                ratio = expense.get("direct")
            if ratio is not None:
                row["expense_ratio"] = ratio
        if row.get("risk_label") is None and detail.get("risk_label"):
            row["risk_label"] = detail.get("risk_label")


def _finalize_screen_payload(data: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """NAV returns and catalog facts on screen rows — use the user question, not focus_question only."""
    if not isinstance(data, dict):
        return data
    rows = [row for row in (data.get("rankings") or data.get("funds") or []) if isinstance(row, dict)]
    if not rows:
        return data
    user_q = str(ctx.get("question") or "")
    from news_rag.tools import _attach_screen_facts, enrich_rankings_with_nav

    from news_rag.tools import infer_return_window, question_wants_performance_ranking

    enrich_window = infer_return_window(user_q) if question_wants_performance_ranking(user_q) else "3Y"
    if any(row.get("return_3y_pct") is None and row.get("return_1y_pct") is None for row in rows):
        enriched = enrich_rankings_with_nav(
            rows,
            direction="any",
            top_n=len(rows),
            sort_by="exposure",
            return_window=enrich_window,
        )
        if enriched:
            rows = enriched
    _attach_screen_facts(rows, user_q)
    if re.search(r"\bcompare\b|\bcomparison\b|\bversus\b|\bvs\.?\b", user_q, re.I):
        _fill_returns_from_catalog(rows)
    _attach_rs_rating_to_screen_rows(rows)
    out = dict(data)
    out["rankings"] = rows
    out["funds"] = rows
    return out


def _screen_row_excluded(row: dict[str, Any], exclude_isins: set[str], exclude_names: set[str]) -> bool:
    isin = str(row.get("isin") or "").strip().upper()
    if isin and isin in exclude_isins:
        return True
    name = str(row.get("fund_name") or row.get("name") or "").strip().lower()
    if not name or not exclude_names:
        return False
    for ex in exclude_names:
        if ex == name or name.startswith(ex) or ex.startswith(name):
            return True
    return False


def _filter_excluded_screen_rows(rows: list[Any], args: dict[str, Any]) -> list[Any]:
    exclude_isins = {str(x).strip().upper() for x in (args.get("exclude_isins") or []) if str(x).strip()}
    exclude_names = {str(x).strip().lower() for x in (args.get("exclude_names") or []) if str(x).strip()}
    if not exclude_isins and not exclude_names:
        return rows
    kept = [r for r in rows if isinstance(r, dict) and not _screen_row_excluded(r, exclude_isins, exclude_names)]
    return kept


def _run_catalog_screen_fallback(
    args: dict[str, Any],
    ctx: dict[str, Any],
    question: str,
) -> dict[str, Any]:
    """NAV/catalog screen when RS rating list returns no rows for a named category."""
    from news_rag.insight.registry import ensure_registry, get_tool
    from news_rag.tools import infer_return_window

    ensure_registry()
    spec = get_tool("screen_funds")
    if not spec or not spec.run:
        return {"ok": False, "data": {}}
    q = str(question or "").strip()
    screen_ctx = {
        **ctx,
        "question": q,
        "sector_name": str(args.get("sector") or ctx.get("sector_name") or ""),
        "top_n": max(int(args.get("top_n") or 1), 20 if args.get("pick_alternate") else 1),
        "direction": args.get("direction") or ctx.get("direction") or "any",
        "return_window": args.get("return_window") or infer_return_window(q),
        "random_sample": bool(args.get("random_sample")),
        "require_positive_1y": bool(args.get("require_positive_1y")),
    }
    return spec.run(screen_ctx)


def _run_screen_funds_by_exposure(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Delegate to sector_funds / driver_affected_funds / screen_funds."""
    question = str(ctx.get("question") or "")
    from news_rag.fund_rating_screen import asks_rating_list, run_rating_list

    rating_question = question if asks_rating_list(question) else ""
    if not rating_question:
        focus = str(args.get("focus_question") or "").strip()
        if focus and asks_rating_list(focus):
            rating_question = focus
    if args.get("rating_screen") or rating_question:
        from dataclasses import replace

        from news_rag.fund_rating_labels import normalize_rs_label
        from news_rag.fund_rating_categories import match_scheme_category
        from news_rag.insight.category_plan import resolve_rs_rating_category
        from news_rag.fund_rating_screen import (
            fetch_category_ratings,
            pick_alternate_funds_in_category,
            pick_better_rated_fund_in_category,
            pick_funds_by_label_cascade,
            pick_rows_by_label_cascade,
            rating_spec_for_forced_screen,
            _cascade_labels_for_spec,
            _rows_from_payload,
            _uses_label_cascade,
        )

        focus = str(args.get("focus_question") or "").strip()
        from news_rag.fund_rating_screen import rating_screen_question

        if args.get("rating_screen"):
            spec_question = rating_screen_question(question, focus or rating_question)
        else:
            spec_question = rating_question or question
        want = int(args.get("top_n") or 1)
        rs_label = normalize_rs_label(str(args.get("rs_label") or ""))

        if args.get("compare_pair"):
            match = match_scheme_category(spec_question)
            category = str(match.category if match else focus or spec_question).strip()
            fund_type = str(match.fund_type if match else "equity").strip() or "equity"
            if category:
                from news_rag.fund_rating_screen import pick_compare_pair_in_category

                pair = pick_compare_pair_in_category(
                    fund_type=fund_type,
                    category=category,
                    question=question,
                )
                rankings = pair.get("rankings") if isinstance(pair.get("rankings"), list) else []
                if len(rankings) >= 2:
                    result = _finalize_screen_payload(pair, ctx)
                    return {"ok": True, "data": result}

        if args.get("pick_alternate") or args.get("pick_rating_better"):
            match = match_scheme_category(spec_question)
            category = str(match.category if match else focus or spec_question).strip()
            fund_type = str(match.fund_type if match else "equity").strip() or "equity"
            if not category or category.lower() == "contra":
                ft, cat = resolve_rs_rating_category(
                    focus_question=focus or spec_question,
                    question=question,
                )
                if cat:
                    category, fund_type = cat, ft or fund_type
            if category:
                anchor_score = args.get("anchor_rs_score")
                try:
                    anchor_score_f = float(anchor_score) if anchor_score is not None else None
                except (TypeError, ValueError):
                    anchor_score_f = None
                if args.get("pick_rating_better"):
                    better = pick_better_rated_fund_in_category(
                        fund_type=fund_type,
                        category=category,
                        exclude_isins=args.get("exclude_isins") or [],
                        exclude_names=args.get("exclude_names") or [],
                        anchor_rs_label=str(args.get("anchor_rs_label") or rs_label or ""),
                        anchor_rs_score=anchor_score_f,
                        top_n=want,
                        question=question,
                    )
                    if better.get("rankings"):
                        result = _finalize_screen_payload(better, ctx)
                        return {"ok": True, "data": result}
                alt = pick_alternate_funds_in_category(
                    fund_type=fund_type,
                    category=category,
                    exclude_isins=args.get("exclude_isins") or [],
                    exclude_names=args.get("exclude_names") or [],
                    rs_label=rs_label,
                    top_n=want,
                    question=question,
                )
                if alt.get("rankings"):
                    result = _finalize_screen_payload(alt, ctx)
                    return {"ok": True, "data": result}

        if args.get("allocation_pairs"):
            from news_rag.fund_rating_screen import RatingScreenSpec

            raw_pairs = args.get("allocation_pairs") or []
            pairs = tuple(
                (str(pair[0]), str(pair[1]))
                for pair in raw_pairs
                if isinstance(pair, (list, tuple)) and len(pair) >= 2
            )
            spec = RatingScreenSpec(
                count=len(pairs),
                fund_type=pairs[0][0] if pairs else "equity",
                category="",
                locked=False,
                label="",
                min_score=None,
                highest_score=False,
                return_window="",
                return_direction="",
                compare_category=False,
                random_sample=False,
                amc="",
                suggestion="rated",
                walk_category_pairs=pairs,
                spread_categories=True,
                one_per_category=True,
                mix_note=str(args.get("allocation_note") or ""),
            )
            result = run_rating_list(question, spec=spec)
            result = _finalize_screen_payload(result, ctx)
            return {"ok": True, "data": result}

        fetch_n = int(args.get("rating_fetch_n") or want)
        if args.get("exclude_isins") or args.get("exclude_names"):
            fetch_n = max(fetch_n, 15)
        spec = rating_spec_for_forced_screen(
            spec_question,
            top_n=max(fetch_n, want),
            user_question=question,
        )
        if spec is not None and rs_label:
            spec = replace(spec, label=rs_label, label_fallback="Recommended")
        result = run_rating_list(spec_question, spec=spec)
        rankings = result.get("rankings") if isinstance(result.get("rankings"), list) else []
        rankings = _filter_excluded_screen_rows(rankings, args)[:want]
        if spec is not None and want > 1 and len(rankings) < want and _uses_label_cascade(spec):
            match = match_scheme_category(spec_question)
            category = str(spec.category or (match.category if match else "") or "").strip()
            fund_type = str(spec.fund_type or (match.fund_type if match else "") or "equity").strip() or "equity"
            if category:
                payload = fetch_category_ratings(fund_type, category)
                rows = _rows_from_payload(payload, fund_type=fund_type, category=category)
                start, max_tier = _cascade_labels_for_spec(spec)
                cascaded, tier_note = pick_funds_by_label_cascade(
                    rows,
                    want,
                    start_label=start,
                    max_tier=max_tier,
                    exclude_isins=args.get("exclude_isins") or [],
                    exclude_names=args.get("exclude_names") or [],
                    random_within_tier=False,
                )
                cascaded = _filter_excluded_screen_rows(cascaded, args)[:want]
                if len(cascaded) > len(rankings):
                    rankings = cascaded
                    if tier_note:
                        result = {
                            **result,
                            "ranking_note": " ".join(
                                part
                                for part in (str(result.get("ranking_note") or "").strip(), tier_note)
                                if part
                            ).strip(),
                        }
        result = {**result, "rankings": rankings}
        if args.get("rating_screen") and not rankings:
            if args.get("pick_rating_better") or args.get("pick_alternate"):
                result = _finalize_screen_payload(
                    {
                        "success": False,
                        "rankings": [],
                        "ranking_note": (
                            "No other rated fund in this category after excluding your holding."
                        ),
                        "screen_type": "rs_rating",
                    },
                    ctx,
                )
                return {"ok": False, "data": result}
            from news_rag.fund_rating_categories import match_scheme_category

            def _named_scheme_category(text: str) -> bool:
                match = match_scheme_category(text)
                return bool(match and match.locked and match.category)

            # An empty rating list is not a license to name random index ETFs by 1M NAV.
            if not _named_scheme_category(spec_question) and not _named_scheme_category(question):
                auth_note = (
                    "RupeeStop category ratings could not be loaded (admin token missing or expired). "
                    "Refresh RUPEESTOP_AUTH_TOKEN or set RUPEESTOP_ADMIN_USERNAME and RUPEESTOP_ADMIN_PASSWORD."
                )
                note = " ".join(
                    part for part in (str(result.get("ranking_note") or "").strip(), auth_note) if part
                ).strip()
                result = _finalize_screen_payload(
                    {
                        **result,
                        "rankings": [],
                        "rating_list_empty": True,
                        "ranking_note": note or auth_note,
                        "screen_type": "rs_rating",
                    },
                    ctx,
                )
                return {"ok": True, "data": result}
            nav = _run_catalog_screen_fallback(args, ctx, rating_screen_question(question, spec_question))
            if nav.get("ok") and isinstance(nav.get("data"), dict):
                nav_data = nav["data"]
                nav_rows = nav_data.get("rankings") or nav_data.get("funds") or []
                if nav_rows:
                    _attach_rs_rating_to_screen_rows(nav_rows)
                    if args.get("pick_alternate") or rs_label:
                        nav_rows, tier_note = pick_rows_by_label_cascade(
                            nav_rows,
                            rs_label=rs_label,
                            exclude_isins=args.get("exclude_isins") or [],
                            exclude_names=args.get("exclude_names") or [],
                            top_n=want,
                        )
                    else:
                        nav_rows = _filter_excluded_screen_rows(nav_rows, args)[:want]
                        tier_note = ""
                    if nav_rows:
                        note = str(result.get("ranking_note") or "").strip()
                        fallback_note = str(nav_data.get("ranking_note") or "").strip()
                        merged_note = " ".join(
                            part for part in (note, tier_note, fallback_note) if part
                        ).strip()
                        payload = {
                            **nav_data,
                            "rankings": nav_rows,
                            "funds": nav_rows,
                            "screen_type": nav_data.get("screen_type") or "catalog_nav",
                            "ranking_note": merged_note or nav_data.get("ranking_note") or "",
                            "rating_list_empty": True,
                        }
                        return {"ok": True, "data": _finalize_screen_payload(payload, ctx)}
        result = _finalize_screen_payload(result, ctx)
        return {"ok": bool(result.get("success")), "data": result}

    from news_rag.insight.registry import ensure_registry, get_tool

    ensure_registry()
    sector = args.get("sector", "")
    driver = args.get("driver", "")
    direction = args.get("direction", "any")

    if driver:
        from news_rag.insight.tool_runners import (
            infer_exposure_direction,
            resolve_driver_direction,
            _rule_sector_picks,
            run_driver_affected_funds_adapter,
        )

        driver_id = str(driver).strip()
        plan_drivers = ctx.get("drivers") or []
        if not plan_drivers:
            plan_drivers = [driver_id]

        from news_rag.tools import explicit_return_window

        question = str(ctx.get("question") or "")
        # News lookback (often 30 days / 1M) is not a fund-return window.
        screen_ctx = {
            **ctx,
            "drivers": plan_drivers if isinstance(plan_drivers, list) else [driver_id],
            "driver_direction": str(ctx.get("driver_direction") or "").strip(),
            "direction": direction if direction in ("positive", "negative") else str(ctx.get("direction") or "any"),
            "top_n": args.get("top_n", 5),
            "return_window": explicit_return_window(question) or "3Y",
        }
        # Allow planner/slot_router to pass macro move separately from exposure side.
        move_arg = str(args.get("driver_move") or args.get("driver_direction") or "").strip().lower()
        if move_arg in ("up", "down", "tighten", "ease", "weaken", "strengthen"):
            screen_ctx["driver_direction"] = move_arg
        elif str(direction).lower() in ("up", "down", "tighten", "ease", "weaken", "strengthen"):
            screen_ctx["driver_direction"] = str(direction).lower()

        resolved_move = resolve_driver_direction(screen_ctx, ctx.get("_articles") or [])
        if resolved_move:
            screen_ctx["driver_direction"] = resolved_move

        screen_ctx["direction"] = infer_exposure_direction(screen_ctx)

        picks = _rule_sector_picks(screen_ctx)
        if not picks:
            macro_spec = get_tool("macro_sector_impact")
            if macro_spec and macro_spec.run:
                macro_res = macro_spec.run(screen_ctx)
                if macro_res.get("ok"):
                    picks = _rule_sector_picks(screen_ctx)
        if not picks and resolved_move:
            # Re-apply canonical move after macro_sector_impact may have filled driver_direction.
            screen_ctx["driver_direction"] = resolved_move
            picks = _rule_sector_picks(screen_ctx)
        if not picks:
            from news_rag.macro_impact_map import macro_impact_entry, normalize_driver

            diag = macro_impact_entry(
                normalize_driver(driver_id),
                direction=resolved_move or None,
            )
            sectors_n = len((diag or {}).get("sectors") or [])
            return {
                "ok": False,
                "error": "no_sectors_for_driver",
                "data": {
                    "driver": driver_id,
                    "driver_direction": resolved_move,
                    "macro_sectors_in_map": sectors_n,
                },
            }

        screen_ctx["_sector_picks"] = picks
        result = run_driver_affected_funds_adapter(screen_ctx)
        data = result.get("data") if isinstance(result.get("data"), dict) else None
        if data:
            rows = [row for row in (data.get("rankings") or []) if isinstance(row, dict)]
            _attach_rs_rating_to_screen_rows(rows)
            from news_rag.tools import _RETURN_FIELDS

            window = str(screen_ctx.get("return_window") or "3Y")
            keep = _RETURN_FIELDS.get(window, "return_3y_pct")
            for row in rows:
                for key in list(row):
                    if str(key).startswith("return_") and key != keep:
                        row.pop(key, None)
            data["rankings"] = rows
            data["return_window"] = window
        return result
    if sector:
        from news_rag.tools import screen_hints_from_question

        q = str(ctx.get("question") or "")
        # "Banking funds" and "large cap funds" are scheme categories. Keep the
        # sector-weight tool for exposure asks that do not name a category.
        if not screen_hints_from_question(q).get("category"):
            spec = get_tool("sector_funds")
            if spec and spec.run:
                screen_ctx = {
                    **ctx,
                    "sector_name": sector,
                    "sector_keys": [sector],
                    "top_n": args.get("top_n", 5),
                }
                return spec.run(screen_ctx)
    spec = get_tool("screen_funds")
    if spec and spec.run:
        from news_rag.tools import infer_return_window

        q = str(args.get("focus_question") or ctx.get("question") or "")
        screen_ctx = {
            **ctx,
            "sector_name": sector or ctx.get("sector_name") or "",
            "top_n": args.get("top_n", 5),
            "direction": args.get("direction") or ctx.get("direction") or "any",
            "return_window": args.get("return_window") or infer_return_window(q),
            "random_sample": bool(args.get("random_sample")),
            "require_positive_1y": bool(args.get("require_positive_1y")),
        }
        return spec.run(screen_ctx)
    return {"ok": False, "error": "no_screen_tool", "data": {}}


def _run_get_market_snapshot(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Delegate to index_return / sector_ranking / macro_series / metals_spot."""
    from news_rag.insight.layer_tools import (
        run_index_return_tool,
        run_macro_series_tool,
        run_sector_ranking_tool,
    )
    from news_rag.insight.registry import ensure_registry, get_tool

    ensure_registry()
    modules = args.get("modules", ["index_return"])
    combined: dict[str, Any] = {}

    if "index_return" in modules:
        idx_ctx = {**ctx, "index": args.get("index", "nifty50"), "window_days": args.get("window_days", 30)}
        res = run_index_return_tool(idx_ctx)
        if res.get("ok"):
            combined["index_return"] = res.get("data", {})

    if "sector_ranking" in modules:
        rank_ctx = {**ctx, "window_days": args.get("window_days", 30), "top_n": args.get("top_n", 6)}
        res = run_sector_ranking_tool(rank_ctx)
        if res.get("ok"):
            combined["sector_ranking"] = res.get("data", {})

    if "macro_series" in modules:
        macro_ctx = {**ctx, "series": args.get("series", ["crude", "usdinr"]), "window_days": args.get("window_days", 30)}
        res = run_macro_series_tool(macro_ctx)
        if res.get("ok"):
            combined["macro_series"] = res.get("data", {})

    if "metals_spot" in modules:
        from historical_data.gold_service import get_gold_snapshot, get_silver_snapshot

        metal = str(args.get("metal") or "gold").strip().lower()
        if metal == "silver":
            combined["metals_spot"] = get_silver_snapshot()
        else:
            combined["metals_spot"] = get_gold_snapshot(
                windows=list(args.get("windows") or []),
                history_months=args.get("history_months"),
            )

    if "stock_quote" in modules:
        stock_name = str(args.get("stock") or ctx.get("stock_name") or "").strip()
        if stock_name:
            from news_rag.insight.tool_runners import run_stock_snapshot_adapter

            snap = run_stock_snapshot_adapter({**ctx, "stock_name": stock_name})
            if snap.get("ok"):
                combined["stock_quote"] = snap.get("data", {})

    return {"ok": bool(combined), "data": combined}


def _run_get_investor_portfolio(args: dict[str, Any], ctx: dict[str, Any] | None) -> dict[str, Any]:
    from news_rag.config import get_settings
    from news_rag.portfolio.cache import get_active_crn, get_normalized_portfolio
    from news_rag.portfolio.errors import PortfolioError
    from news_rag.portfolio.project import project_modules

    settings = get_settings()
    if not settings.portfolio_enabled:
        return {"ok": False, "error": "portfolio_not_configured", "data": {}}
    modules = list(args.get("modules") or [])
    if not modules:
        return {"ok": False, "error": "modules_required", "data": {}}

    crn = get_active_crn()
    try:
        doc, stats = get_normalized_portfolio(crn)
    except PortfolioError as exc:
        return {"ok": False, "error": exc.code, "data": {}, "message": str(exc)[:200]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "portfolio_fetch_failed", "data": {}, "message": str(exc)[:200]}

    projected = project_modules(doc, args)
    if not projected.get("ok"):
        return {"ok": False, "error": str(projected.get("error") or "project_failed"), "data": {}}

    data = projected.get("data") if isinstance(projected.get("data"), dict) else {}
    windows = [str(w).upper() for w in (args.get("windows") or []) if str(w).strip()]
    if windows and "holdings" in modules and isinstance(data.get("holdings"), list):
        from news_rag.insight.layer_tools import run_fund_snapshot

        for row in data["holdings"]:
            if not isinstance(row, dict):
                continue
            name = str(row.get("scheme_name") or row.get("name") or "").strip()
            isin = str(row.get("isin") or "").strip()
            if not name:
                continue
            snap = run_fund_snapshot(
                {
                    **(ctx or {}),
                    "fund_name": name,
                    "fund_names": [name],
                    "fund_isin": isin,
                    "windows": windows,
                }
            )
            if not snap.get("ok"):
                continue
            payload = snap.get("data") if isinstance(snap.get("data"), dict) else {}
            rets = payload.get("returns") if isinstance(payload.get("returns"), dict) else payload
            if rets:
                row["catalog_returns"] = {str(k).upper(): v for k, v in rets.items()}
    meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    if ctx is not None:
        ctx["portfolio_fetch_ms"] = stats.get("fetch_ms")
        ctx["portfolio_from_cache"] = stats.get("from_cache")
        ctx["portfolio_modules"] = modules
    return {
        "ok": True,
        "data": data,
        "as_of": str(meta.get("as_of_date") or ""),
        "partial": bool(stats.get("stale")),
    }


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

_RUNNERS = {
    "get_fund_data": _run_get_fund_data,
    "get_portfolio_data": _run_get_portfolio_data,
    "get_investor_portfolio": _run_get_investor_portfolio,
    "compare_funds": _run_compare_funds,
    "search_financial_news": _run_search_financial_news,
    "get_macro_news": _run_get_macro_news,
    "screen_funds_by_exposure": _run_screen_funds_by_exposure,
    "get_market_snapshot": _run_get_market_snapshot,
}


def _conversation_id(ctx: dict[str, Any] | None) -> str:
    return str((ctx or {}).get("conversation_id") or "").strip()


def _positive_ms(started: float) -> float:
    """A finished tool call has a duration. A cache hit still ran."""
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    return elapsed if elapsed > 0 else 0.1


def _conversation_turn(ctx: dict[str, Any] | None) -> int:
    try:
        return int((ctx or {}).get("conversation_turn") or 0)
    except (TypeError, ValueError):
        return 0


def widen_portfolio_args(question: str, args: dict[str, Any]) -> dict[str, Any]:
    """'Each holding' is the full list. A named count such as top 5 stays that count."""
    import re

    q = question or ""
    if re.search(r"\btop\s+\d+\b|\b\d+\s+(?:holdings?|stocks?|sectors?)\b", q, re.I):
        return args
    wants_all = bool(
        re.search(r"\b(?:each|every|all)\b[\w\s]{0,30}\b(?:holdings?|stocks?|sectors?|weights?)", q, re.I)
        or re.search(r"\bweight(?:age)?s?\b[\w\s]{0,30}\b(?:each|every|all|holdings?)", q, re.I)
    )
    if not wants_all:
        return args
    out = dict(args)
    out["top_n"] = 50
    return out


def _take_conversation_slice(ctx: dict[str, Any] | None, fund: str, tool: str, args: dict[str, Any]) -> Any | None:
    conv = _conversation_id(ctx)
    if not conv or not fund:
        return None
    from news_rag.insight.memory.evidence import note_cache, recall_slice, recall_wider_portfolio, slice_key

    key = slice_key(fund, tool, args)
    data = recall_slice(conv, fund, tool, args)
    if data is None and tool == "get_portfolio_data":
        data = recall_wider_portfolio(conv, fund, args)
    if data is None and tool == "get_fund_data":
        # A wider cached fetch (more modules or windows) answers a narrower ask without a new call.
        from news_rag.insight.memory.evidence import stored_fund_slices

        data = next((d for d in stored_fund_slices(conv, fund) if _return_slice_covers(tool, args, d)), None)
    if data is None or not _return_slice_covers(tool, args, data):
        note_cache(conv, "fetched", key)
        return None
    if tool == "get_fund_data" and not _fund_payload_matches_fund(fund, data):
        note_cache(conv, "fetched", key)
        return None
    note_cache(conv, "hit", key)
    return data


_FUND_MODULE_KEYS = {
    "snapshot": ("snapshot",),
    "rating": ("rs_rating", "rating"),
    "limits": ("investment_limits",),
    "composition": ("composition",),
    "risk": ("risk",),
    "drawdown": ("drawdown",),
    "managers": ("managers",),
    "attribution": ("attribution",),
    "vs_benchmark": ("vs_benchmark",),
    "return_series": ("return_series",),
}


def _trim_cached_to_ask(tool: str, args: dict[str, Any], data: Any) -> Any:
    """A wider cached fund payload is cut to the modules and return windows asked now."""
    if tool != "get_fund_data" or not isinstance(data, dict):
        return data
    wanted = {str(m).lower() for m in (args.get("modules") or [])}
    if not wanted:
        return data
    out = dict(data)
    for module, keys in _FUND_MODULE_KEYS.items():
        if module not in wanted:
            for key in keys:
                out.pop(key, None)
    windows = {str(w).upper() for w in (args.get("windows") or []) if str(w).strip()}
    snap = out.get("snapshot")
    if windows and isinstance(snap, dict):
        snap = dict(snap)
        if isinstance(snap.get("returns"), dict):
            snap["returns"] = {k: v for k, v in snap["returns"].items() if str(k).upper() in windows}
        out["snapshot"] = snap
    return out


def _return_slice_covers(tool: str, args: dict[str, Any], data: Any) -> bool:
    """Reuse a cached call only when it already has every section, module, and period asked now."""
    if not isinstance(data, dict):
        return False
    if tool == "get_portfolio_data":
        sections = [str(item).lower() for item in (args.get("sections") or ["holdings", "sectors"])]
        for section in sections:
            rows = data.get(section)
            if not isinstance(rows, list) or not rows:
                return False
        return True
    if tool == "get_market_snapshot":
        if not isinstance(data, dict):
            return False
        want_modules = {str(m) for m in (args.get("modules") or ["index_return"])}
        if not want_modules.issubset(data.keys()):
            return False
        want_days = int(args.get("window_days") or 30)
        for module in ("index_return", "sector_ranking", "macro_series"):
            if module not in want_modules:
                continue
            block = data.get(module)
            if not isinstance(block, dict):
                return False
            got_days = block.get("window_days")
            if got_days is not None and int(got_days) != want_days:
                return False
        return True
    if tool == "get_investor_portfolio":
        modules = [str(item).lower() for item in (args.get("modules") or [])]
        module_keys = {
            "meta": ("meta",),
            "summary": ("summary",),
            "allocation": ("allocation",),
            "holdings": ("holdings",),
            "pnl_summary": ("pnl_summary",),
            "pnl_scheme": ("pnl_scheme",),
            "sip": ("sip",),
            "stp": ("stp",),
            "xirr": ("xirr",),
            "profile_risk": ("profile_risk",),
            "concentration": ("concentration",),
        }

        def _block_ok(key: str) -> bool:
            block = data.get(key)
            if key == "holdings":
                return isinstance(block, list) and bool(block)
            if key in ("sip", "stp", "xirr"):
                return isinstance(block, dict) and bool(block)
            return isinstance(block, dict) and bool(block)

        for module in modules:
            keys = module_keys.get(module)
            if not keys:
                continue
            if not all(_block_ok(key) for key in keys):
                return False
        return True
    if tool != "get_fund_data":
        return True
    modules = [str(item).lower() for item in (args.get("modules") or [])]
    module_keys = {
        "snapshot": ("snapshot",),
        "rating": ("rs_rating", "rating"),
        "limits": ("investment_limits",),
        "composition": ("composition",),
        "risk": ("risk",),
        "drawdown": ("drawdown",),
        "managers": ("managers",),
        "attribution": ("attribution",),
        "vs_benchmark": ("vs_benchmark",),
        "return_series": ("return_series",),
    }
    for module in modules:
        keys = module_keys.get(module)
        if keys and not any(isinstance(data.get(key), (dict, list)) and data.get(key) for key in keys):
            return False
    if "rating" in modules:
        from news_rag.fund_risk import rating_needs_pillars

        if rating_needs_pillars(args):
            rating = data.get("rs_rating") if isinstance(data.get("rs_rating"), dict) else {}
            pillars = rating.get("pillars") if isinstance(rating.get("pillars"), dict) else {}
            if not pillars:
                return False
    windows = [str(item).upper() for item in (args.get("windows") or []) if str(item).strip()]
    if not windows:
        return True
    if "vs_benchmark" in modules and "snapshot" not in modules:
        vs = data.get("vs_benchmark") if isinstance(data.get("vs_benchmark"), dict) else {}
        periods = vs.get("periods") if isinstance(vs.get("periods"), dict) else {}
        if not periods:
            insights = data.get("fund_insights") if isinstance(data.get("fund_insights"), dict) else {}
            comp = insights.get("comparison_periods") if isinstance(insights.get("comparison_periods"), dict) else {}
            periods = comp
        covered_vs = {str(key).upper() for key in periods}
        if all(code in covered_vs for code in windows):
            return True
    snap = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else {}
    returns = snap.get("returns") if isinstance(snap.get("returns"), dict) else {}
    limits = snap.get("unavailable_returns") if isinstance(snap.get("unavailable_returns"), list) else []
    covered = {str(key).upper() for key in returns}
    covered.update(str(row.get("window") or "").upper() for row in limits if isinstance(row, dict))
    return all(code in covered for code in windows)


def _keep_conversation_slice(ctx: dict[str, Any] | None, fund: str, tool: str, args: dict[str, Any], data: Any, ok: bool) -> None:
    conv = _conversation_id(ctx)
    if not conv or not fund or not ok:
        return
    from news_rag.insight.memory.evidence import beside_keys, note_cache, remember_slice

    key = remember_slice(conv, fund, tool, args, data, turn=_conversation_turn(ctx))
    note_cache(conv, "stored", key, beside=beside_keys(conv, key))


def execute_capability(
    call: ToolCall,
    *,
    fund_names: list[str] | None = None,
    ctx: dict[str, Any] | None = None,
    telemetry: RequestTelemetry | None = None,
) -> list[dict[str, Any]]:
    """Run one capability, possibly fanning out over funds.

    Returns a list of result dicts [{ok, data, tool, fund, elapsed_ms}].
    """
    from news_rag.insight.capabilities.catalog import CAPABILITIES

    from news_rag.insight.capabilities.catalog import CAPABILITIES, INVESTOR_PORTFOLIO_CAPABILITY

    cap = CAPABILITIES.get(call.tool)
    if call.tool == "get_investor_portfolio":
        cap = INVESTOR_PORTFOLIO_CAPABILITY
    if cap is None:
        return [{"ok": False, "tool": call.tool, "fund": "", "error": f"unknown_capability:{call.tool}", "data": {}, "elapsed_ms": 0}]

    if call.tool == "get_investor_portfolio":
        from news_rag.config import get_settings

        if not get_settings().portfolio_enabled:
            return [{
                "ok": False,
                "tool": call.tool,
                "fund": "",
                "error": "portfolio_not_configured",
                "data": {},
                "elapsed_ms": 0,
            }]

    args = validate_capability_args(call.tool, call.arguments)
    if call.tool == "get_portfolio_data":
        args = widen_portfolio_args(str((ctx or {}).get("question") or ""), args)
    base_ctx = dict(ctx or {})
    cache = get_capability_cache()
    results: list[dict[str, Any]] = []

    runner = _RUNNERS.get(call.tool)
    if runner is None:
        return [{"ok": False, "tool": call.tool, "fund": "", "error": "no_runner", "data": {}, "elapsed_ms": 0}]

    if cap.get("per_fund"):
        target_funds = list(fund_names or [])
        arg_fund = str(call.arguments.get("fund") or call.arguments.get("fund_name") or "").strip()
        if arg_fund and arg_fund not in target_funds:
            target_funds.append(arg_fund)
        if not target_funds:
            from news_rag.portfolio.cache import find_cached_holdings

            target_funds = [
                str(row.get("scheme_name") or "").strip()
                for row in find_cached_holdings(str(base_ctx.get("question") or ""))
                if str(row.get("scheme_name") or "").strip()
            ]
        if not target_funds:
            return [{"ok": False, "tool": call.tool, "fund": "", "error": "no_funds_resolved", "data": {}, "elapsed_ms": 0}]
        skip_cache = bool(base_ctx.get("skip_tool_cache"))

        def _one_fund(name: str) -> dict[str, Any]:
            per_ctx = dict(base_ctx)
            per_isin = _isin_for_fund_name(name, base_ctx)
            if per_isin:
                per_ctx["fund_isin"] = per_isin
            else:
                per_ctx.pop("fund_isin", None)
                if call.tool == "get_fund_data":
                    logger.info(
                        "catalog bind: no ISIN for %r (ambiguous or unknown name)",
                        name[:80],
                    )
            started = time.perf_counter()
            remembered = None if skip_cache else _take_conversation_slice(per_ctx, name, call.tool, args)
            if remembered is not None:
                return {
                    "ok": True, "tool": call.tool, "fund": name,
                    "data": _trim_cached_to_ask(call.tool, args, remembered),
                    "elapsed_ms": _positive_ms(started), "cached": True, "cache_layer": "conversation",
                }
            cache_key = _capability_cache_key(call.tool, name, args, per_ctx)
            cached = None if skip_cache else cache.get(call.tool, cache_key)
            if cached is not None and (
                not _return_slice_covers(call.tool, args, cached)
                or (call.tool == "get_fund_data" and not _fund_payload_matches_fund(name, cached, per_ctx))
            ):
                cached = None
            if cached is not None:
                _keep_conversation_slice(per_ctx, name, call.tool, args, cached, True)
                return {
                    "ok": True, "tool": call.tool, "fund": name, "data": cached,
                    "elapsed_ms": _positive_ms(started), "cached": True, "cache_layer": "capability",
                }
            t0 = time.perf_counter()
            attempts = 2 if call.tool == "get_fund_data" else 1
            out = {"ok": False, "error": "no_attempt", "data": {}}
            for attempt in range(attempts):
                try:
                    out = runner(name, args, per_ctx)
                except Exception as exc:
                    out = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "data": {}}
                err = str(out.get("error") or "")
                if out.get("ok") or "timeout" not in err.lower() or attempt == attempts - 1:
                    break
                logger.info("get_fund_data retry after timeout fund=%s", name[:80])
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            data = out.get("data", {}) if isinstance(out.get("data"), dict) else {}
            complete = _return_slice_covers(call.tool, args, data)
            row = {
                "ok": bool(out.get("ok")),
                "tool": call.tool,
                "fund": name,
                "data": data,
                "elapsed_ms": elapsed,
                "error": str(out.get("error") or ""),
                "partial": bool(out.get("partial")) or (bool(out.get("ok")) and not complete),
                "cached": False,
            }
            if row["ok"] and complete and _fund_payload_matches_fund(name, row["data"], per_ctx):
                cache.set(call.tool, cache_key, row["data"])
                _keep_conversation_slice(per_ctx, name, call.tool, args, row["data"], True)
            return row

        if len(target_funds) > 1:
            jobs = [(contextvars.copy_context(), name) for name in target_funds]
            with ThreadPoolExecutor(max_workers=min(8, len(target_funds))) as pool:
                rows = list(pool.map(lambda job: job[0].run(_one_fund, job[1]), jobs))
        else:
            rows = [_one_fund(name) for name in target_funds]
        for row in rows:
            results.append(row)
            if telemetry and not row.get("cached"):
                telemetry.add_tool(
                    call.tool,
                    wave=call.wave,
                    ok=bool(row.get("ok")),
                    duration_ms=float(row.get("elapsed_ms") or 0),
                    fund=str(row.get("fund") or ""),
                )
    else:
        label = call.tool
        if call.tool == "compare_funds":
            label = _compare_cache_label(fund_names or [])
        elif call.tool == "search_financial_news":
            names = sorted(
                " ".join(str(name).lower().split())
                for name in (fund_names or [])
                if str(name).strip()
            )
            if names:
                label = " | ".join(names)
        skip_cache = bool(base_ctx.get("skip_tool_cache")) or bool(
            args.get("exclude_isins")
            or args.get("exclude_names")
            or args.get("pick_alternate")
            or args.get("pick_rating_better")
            or args.get("compare_pair")
        )
        started = time.perf_counter()
        remembered = None if skip_cache else _take_conversation_slice(base_ctx, label, call.tool, args)
        if remembered is not None and call.tool == "compare_funds":
            if not _compare_payload_matches_funds(fund_names or [], remembered):
                remembered = None
        if remembered is not None:
            elapsed = _positive_ms(started)
            results.append({
                "ok": True, "tool": call.tool, "fund": "", "data": remembered,
                "elapsed_ms": elapsed, "cached": True,
            })
            if telemetry:
                telemetry.add_tool(call.tool, wave=call.wave, ok=True, duration_ms=elapsed)
            return results
        if call.tool == "compare_funds":
            t0 = time.perf_counter()
            try:
                out = runner(fund_names or [], args, base_ctx)
            except Exception as exc:
                out = {"ok": False, "error": str(exc), "data": {}}
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
        else:
            t0 = time.perf_counter()
            try:
                out = runner(args, base_ctx)
            except Exception as exc:
                out = {"ok": False, "error": str(exc), "data": {}}
            elapsed = round((time.perf_counter() - t0) * 1000, 1)

        row = {"ok": bool(out.get("ok")), "tool": call.tool, "fund": "",
               "data": out.get("data", {}), "elapsed_ms": elapsed,
               "error": out.get("error", "")}
        if row["ok"]:
            _keep_conversation_slice(base_ctx, label, call.tool, args, row["data"], True)
        results.append(row)
        if telemetry:
            telemetry.add_tool(call.tool, wave=call.wave, ok=row["ok"], duration_ms=elapsed)

    return results


def execute_wave(
    calls: list[ToolCall],
    ctx: dict[str, Any] | None = None,
    *,
    fund_names: list[str] | None = None,
    telemetry: RequestTelemetry | None = None,
    deadline_at: float | None = None,
    deadline_ms: float | None = None,
    query_log: Any = None,
) -> list[dict[str, Any]]:
    """Execute all tool calls in a wave in parallel, respecting the deadline.

    Returns flat list of result dicts.
    """
    if ctx is not None and fund_names is None:
        fund_names = ctx.get("fund_names")
    if deadline_at is None and deadline_ms is not None:
        deadline_at = time.time() + (float(deadline_ms) / 1000.0)

    settings = get_settings()
    max_workers = min(getattr(settings, "max_concurrent_tools", 4), len(calls) or 1)
    all_results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures: list[tuple[Future, ToolCall]] = []
        for call in calls:
            # One copy per task. A shared context cannot be entered on two threads.
            task_ctx = contextvars.copy_context()
            fut = pool.submit(
                task_ctx.run, execute_capability, call,
                fund_names=fund_names, ctx=ctx, telemetry=telemetry,
            )
            futures.append((fut, call))

        for fut, call in futures:
            # Enforce deadline: if we've passed it, cancel remaining futures
            if deadline_at and time.time() > deadline_at:
                fut.cancel()
                all_results.append({
                    "ok": False, "tool": call.tool, "fund": "",
                    "error": "deadline_exceeded", "data": {}, "elapsed_ms": 0,
                })
                continue
            try:
                remaining = None
                if deadline_at:
                    remaining = max(0.5, deadline_at - time.time())
                results = fut.result(timeout=remaining)
                all_results.extend(results)
            except TimeoutError:
                # The portfolio call often lands just after the wave clock. Keep that payload.
                try:
                    results = fut.result(timeout=12)
                    all_results.extend(results)
                except Exception as exc:
                    all_results.append({
                        "ok": False, "tool": call.tool, "fund": "",
                        "error": f"{type(exc).__name__}: {exc}", "data": {}, "elapsed_ms": 0,
                    })
            except Exception as exc:
                all_results.append({
                    "ok": False, "tool": call.tool, "fund": "",
                    "error": f"{type(exc).__name__}: {exc}", "data": {}, "elapsed_ms": 0,
                })

    return all_results
