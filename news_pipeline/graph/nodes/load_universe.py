"""Load the holdings and sectors that will be searched."""

from __future__ import annotations

import logging

from news_pipeline.graph.state import PipelineState
from news_pipeline.run_log import get_run_logger
from news_pipeline.services import get_settings
from news_pipeline.sources.universe import load_universe as read_universe, sector_query_gaps

logger = logging.getLogger(__name__)


def load_universe(state: PipelineState) -> dict:
    settings = get_settings()
    portfolio_mode = bool((settings.portfolio_json or "").strip())
    entities = read_universe(settings)
    run_log = get_run_logger()
    counts = dict(state.get("counts") or {})
    counts["entities"] = len(entities)
    if portfolio_mode:
        counts["portfolio_universe"] = True
    holdings = sum(1 for entity in entities if entity["type"] == "holding")
    sectors = len(entities) - holdings
    if run_log is not None:
        if portfolio_mode:
            run_log.write(
                f"load_universe mode=portfolio_json path={settings.portfolio_json} "
                f"manifest={settings.portfolio_manifest_path} "
                f"equity_aggregate={settings.aggregated_holdings_map}"
            )
        run_log.write(
            f"load_universe finished holdings={holdings} sectors={sectors} total={len(entities)}"
        )
        for entity in entities:
            run_log.write(
                f"load_universe entity name={entity['name']} type={entity['type']} "
                f"industry={entity.get('industry') or ''} "
                f"query={entity['query']!r} fund_count={entity['fund_count']}"
            )
        gaps = sector_query_gaps(settings, limit=10)
        all_gaps = sector_query_gaps(settings, limit=0)
        if all_gaps and run_log is not None:
            run_log.write(
                f"load_universe sector_query_gaps total={len(all_gaps)} "
                f"(sectors in CSV without SECTOR_QUERIES mapping)"
            )
            for name, fund_count in gaps:
                run_log.write(f"load_universe sector_query_gap sector={name!r} fund_count={fund_count}")
    logger.info("load_universe holdings=%s sectors=%s", holdings, sectors)
    return {"entities": entities, "counts": counts}
