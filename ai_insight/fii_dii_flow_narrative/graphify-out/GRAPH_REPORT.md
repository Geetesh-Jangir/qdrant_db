# Graph Report - fii_dii_flow_narrative  (2026-11-19)

## Corpus Check
- 7 files · ~4,738 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 107 nodes · 207 edges · 10 communities (7 shown, 3 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9806c0c3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- aggregate.py
- collector.py
- run.py
- flow_datasets.py
- prompt.py
- collect
- _ingest_nse_result
- _record

## God Nodes (most connected - your core abstractions)
1. `build()` - 18 edges
2. `build_flow_datasets()` - 13 edges
3. `collect()` - 9 edges
4. `_ingest_nse_result()` - 9 edges
5. `import_csv()` - 7 edges
6. `compute_flow_facts()` - 7 edges
7. `_fii_dii_daily()` - 6 edges
8. `normalize_fii_draft()` - 6 edges
9. `build_user()` - 6 edges
10. `compose()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `build_flow_datasets()` --calls--> `flow_period_totals()`  [EXTRACTED]
  ai_insight/fii_dii_flow_narrative/flow_datasets.py → ai_insight/fii_dii_flow_narrative/aggregate.py
- `build()` --calls--> `build_flow_datasets()`  [EXTRACTED]
  ai_insight/fii_dii_flow_narrative/run.py → ai_insight/fii_dii_flow_narrative/flow_datasets.py
- `build()` --calls--> `normalize_fii_draft()`  [EXTRACTED]
  ai_insight/fii_dii_flow_narrative/run.py → ai_insight/fii_dii_flow_narrative/prompt.py
- `compose()` --calls--> `normalize_fii_draft()`  [EXTRACTED]
  ai_insight/fii_dii_flow_narrative/run.py → ai_insight/fii_dii_flow_narrative/prompt.py
- `build()` --calls--> `assemble_fii_body()`  [EXTRACTED]
  ai_insight/fii_dii_flow_narrative/run.py → ai_insight/fii_dii_flow_narrative/prompt.py

## Import Cycles
- None detected.

## Communities (10 total, 3 thin omitted)

### Community 0 - "aggregate.py"
Cohesion: 0.18
Nodes (7): compute_flow_facts(), flow_period_totals(), rolling_avg_abs_net(), _sign(), streak_days(), StreakInfo, _word()

### Community 1 - "collector.py"
Cohesion: 0.24
Nodes (4): _csv_row(), import_csv(), ImportReport, main()

### Community 2 - "run.py"
Cohesion: 0.13
Nodes (10): fallback_headline(), persist_fii_sections(), build(), compose(), _cluster_row(), main(), _shell(), _sources() (+2 more)

### Community 3 - "flow_datasets.py"
Cohesion: 0.20
Nodes (10): build_flow_datasets(), _fii_dii_daily(), _flow_history_highlights(), _flow_index_date_context(), _flow_with_market(), _macro_flow_focus(), _provisional_by_date(), _sector_focus() (+2 more)

### Community 4 - "prompt.py"
Cohesion: 0.16
Nodes (6): assemble_fii_body(), build_user(), _clean_paragraph(), compact_flow_facts(), _legacy_paragraph(), normalize_fii_draft()

### Community 5 - "collect"
Cohesion: 0.38
Nodes (3): collect(), CollectResult, prefetch_fii_dii()

### Community 6 - "_ingest_nse_result"
Cohesion: 0.60
Nodes (4): append_record(), history_has_date(), _ingest_nse_result(), store_record_if_new()

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build()` connect `run.py` to `aggregate.py`, `flow_datasets.py`, `prompt.py`, `_ingest_nse_result`, `_record`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `build()` (e.g. with `compose()` and `main()`) actually correct?**
  _`build()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `run.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12648221343873517 - nodes in this community are weakly interconnected._
- **Why does `build_flow_datasets()` connect `flow_datasets.py` to `aggregate.py`, `run.py`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Why does `collect()` connect `collect` to `collector.py`, `_ingest_nse_result`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._