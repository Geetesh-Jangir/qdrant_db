# Graph Report - market_driver_digest  (2026-11-18)

## Corpus Check
- 6 files · ~2,007 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 72 nodes · 121 edges · 8 communities (3 shown, 5 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9806c0c3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- build
- rank.py
- fetch.py
- backtest
- prompt.py
- main

## God Nodes (most connected - your core abstractions)
1. `build()` - 13 edges
2. `backtest()` - 10 edges
3. `pick_drivers()` - 7 edges
4. `_shell()` - 7 edges
5. `_context()` - 6 edges
6. `compose()` - 5 edges
7. `_fallback()` - 5 edges
8. `assemble_market_body()` - 4 edges
9. `persist_market_sections()` - 4 edges
10. `build_user()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `build()` --calls--> `build_user()`  [EXTRACTED]
  ai_insight/market_driver_digest/run.py → ai_insight/market_driver_digest/prompt.py
- `_facts()` --calls--> `move_phrase()`  [EXTRACTED]
  ai_insight/market_driver_digest/run.py → ai_insight/market_driver_digest/rank.py
- `build()` --calls--> `pick_drivers()`  [EXTRACTED]
  ai_insight/market_driver_digest/run.py → ai_insight/market_driver_digest/rank.py
- `build()` --calls--> `assemble_market_body()`  [EXTRACTED]
  ai_insight/market_driver_digest/run.py → ai_insight/market_driver_digest/prompt.py
- `compose()` --calls--> `assemble_market_body()`  [EXTRACTED]
  ai_insight/market_driver_digest/run.py → ai_insight/market_driver_digest/prompt.py

## Import Cycles
- None detected.

## Communities (8 total, 5 thin omitted)

### Community 1 - "build"
Cohesion: 0.26
Nodes (10): assemble_market_body(), persist_market_sections(), build(), compose(), _facts(), _fallback(), _fallback_headline(), _shell() (+2 more)

### Community 2 - "rank.py"
Cohesion: 0.30
Nodes (8): Drivers, is_index_recap(), move_phrase(), move_size(), _names(), pick_drivers(), score(), split_index_recaps()

### Community 4 - "backtest"
Cohesion: 0.43
Nodes (4): backtest(), _context(), _days(), _section()

## Knowledge Gaps
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `backtest()` connect `backtest` to `run.py`, `build`, `main`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `build()` (e.g. with `compose()` and `main()`) actually correct?**
  _`build()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `run.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._
- **Why does `pick_drivers()` connect `rank.py` to `run.py`, `build`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._