# Graph Report - db_design_with_qdrant_locally  (2026-11-21)

## Corpus Check
- 756 files · ~1,132,961 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 31 file(s) not represented in the graph (top: .example 6, .log 5, (none) 4)

## Summary
- 7697 nodes · 25001 edges · 278 communities (209 shown, 69 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 750 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8968bdb6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- bridge.py
- re
- interpret.py
- ExecutionPlan
- category_plan.py
- query_log.py
- load_config
- test_ask_speed.py
- Settings
- sector_leaderboard/run.py
- market_driver_digest/run.py
- load_config
- compute.py
- insight_links.py
- tools.py
- validate.py
- json
- QueryLogger
- news_reader.py
- macro_data.py
- narrative.py
- match.py
- market_daily_store.py
- tool_runners.py
- insight/portfolio_scope.py
- build_fund_display_tables
- gather.py
- investor_drawback.py
- normalize_user_facing_text
- portfolio_news_impact.py
- trends.py
- fund_name_gate.py
- task_exec.py
- get_settings
- sector_query_for_label
- fund_display.py
- normalize.py
- pytest
- plan.py
- env
- test_sector_leaderboard_run.py
- news_filter.py
- plan_enforce.py
- logging.py
- env
- get_sector_fund_ranking_index
- sources/google_news.py
- entity_retrieval.py
- fund_scheme_match.py
- app.py
- gold_service.py
- env
- graph.py
- fund_rupeestop_metrics.py
- execute_capability
- generate_json
- scrape-worker/package.json
- get_fund_index
- executor.py
- test_fund_risk.py
- test_fund_drawdown.py
- test_portfolio_layer.py
- re
- lib/portfolio_scope.py
- fund_universe_agent.py
- batch.ts
- twelve_data_brent.py
- insight/guardrails.py
- http-fetch.ts
- news_rag/config.py
- portfolio/cache.py
- retrieve_scoped_news
- market_data.py
- with
- test_portfolio_intents.py
- sector_fund_ranking.py
- stock_fund_ranking.py
- rupeestop_auth.py
- holdings_market.py
- test_conversation_memory.py
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- RunLogger
- portfolio_equity.py
- macro_context.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- official.py
- test_sector_leaderboard_score.py
- env
- steps
- evidence_pack.py
- contracts.py
- fund_type_name_spec
- test_ai_insight_common_qdrant_access.py
- update.py
- parse.py
- test_greeting.py
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- sector_alignment.py
- market_pulse.py
- fund_search.py
- fact_slots.py
- fund_match.py
- Settings
- Cluster
- fund_rating_categories.py
- insights.py
- vitest
- data_pack.py
- test_fund_drawdown.py
- compilerOptions
- compilerOptions
- macro_news_cache.py
- prompts.py
- backfill
- fields.py
- news_digest.py
- fund_rating_screen.py
- run-pipeline
- GraphState
- ._ensure_loaded
- ask_plan.py
- worker/src/index.ts
- steps
- steps
- with
- aggregate_fund_holdings.py
- format_inr
- Settings
- inputs
- with
- inputs
- repo_root
- news_insight_articles
- test_daily_cron_settings.py
- run-backfill.sh
- qdrant
- portfolio_bind.py
- extract.ts
- sync-news-runs-to-r2.sh
- date_range
- google_news_when
- portfolio_json
- sectors_limit
- end_date
- holdings_limit
- pause_sec
- start_date
- rag-api.js
- time
- install.sh
- test_portfolio_startup_cache.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- nse_fii_dii.py
- ask_market_bridge.py
- diagnose_lightsail_site.sh
- fund_search.py
- graph.py
- EntityFunnel
- stock_news.py
- book_news_map.py
- portfolio_insights.js
- fund_catalog.py
- v2_scoring.py
- test_fund_name_gate_and_hydrate.py
- fund_by_isin.py
- yf_week.py
- prune_insight_logs.py
- node_wave1
- unittest_mock
- metals_spot_tables.py
- infer_fund_news_layers
- validate_capability_args
- pick_random_scheme_category_for_compare
- brief.py
- 283041/manifest.json
- repair_compose_placeholders
- fund_brief.py
- test_ai_insight.py
- Envelope
- 57e233/manifest.json
- row_fund_isins
- c72b25/manifest.json
- a45664/manifest.json
- test_risk_analysis_without_periods_still_loads_one_three_and_five_year
- 7859f0/manifest.json
- layer_tools.py
- test_category_rating_request_uses_admin_header
- insights.js
- holding_insights.js
- insight_log.js
- fix-daily-ingest.sh
- news_pipeline/config.py
- concurrent_futures
- sector_news.py
- test_ai_insight_mospi.py
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- holding_insights/llm.py
- app.js
- embed.py
- run_insights_daily.sh
- test_ai_insight_common_clustering.py
- install-insights-cron.sh
- extract.py
- test_composer_table_summaries.py
- test_fund_rating_screen.py
- PublisherStats
- holding_insights_stock_log.js
- model_validator
- build_derived_views
- test_multi_fact_fund.py
- CapabilityCache
- new/fund_context.py
- router.py
- strip_news_roundup
- compose_llm.py
- build_top100_holdings.py
- test_macro_scope.py
- MospiClient
- AnswerMode
- nav_service.py
- pack_trim.py

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 606 edges
2. `ToolCall` - 366 edges
3. `get_settings()` - 147 edges
4. `apply_planner_post_hooks()` - 125 edges
5. `load_config()` - 115 edges
6. `AnswerMode` - 107 edges
7. `node_compose()` - 105 edges
8. `QueryLogger` - 100 edges
9. `Settings` - 95 edges
10. `QuestionBrief` - 88 edges

## Surprising Connections (you probably didn't know these)
- `test_several_facts_include_each_sector_weight()` --calls--> `investor_fact_brief()`  [EXTRACTED]
  tests/test_fund_drawdown.py → news_rag/insight/evidence_pack.py
- `test_repair_category_book_opening_matches_allocation_not_double_count()` --calls--> `repair_category_book_opening()`  [EXTRACTED]
  tests/test_investor_grounding.py → news_rag/insight/evidence_pack.py
- `test_repair_fills_empty_term_gain_bullets()` --calls--> `repair_investor_insight_prose()`  [EXTRACTED]
  tests/test_investor_grounding.py → news_rag/insight/evidence_pack.py
- `test_portfolio_concentration_report_format()` --calls--> `_portfolio_concentration_report()`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/insight/evidence_pack.py
- `_qdrant_holding_names()` --uses--> `Settings`  [INFERRED]
  ai_insight/common/entity_retrieval.py → news_pipeline/config.py

## Import Cycles
- 2-file cycle: `ai_insight/common/entity_retrieval.py -> ai_insight/common/retrieval_plan.py -> ai_insight/common/entity_retrieval.py`

## Communities (278 total, 69 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (56): get_encoder(), get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match() (+48 more)

### Community 1 - "bridge.py"
Cohesion: 0.21
Nodes (6): ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), test_market_affected_funds_question_schedules_a_screen()

### Community 2 - "re"
Cohesion: 0.06
Nodes (47): strip_fund_example_clauses(), _amc_token_in_question(), asks_these_equity_funds(), _canonical_chat_fund_name(), _chat_fund_mention_recency(), _compare_pair_from_chat_turns(), comparison_fund_names(), _filter() (+39 more)

### Community 3 - "interpret.py"
Cohesion: 0.07
Nodes (73): QuestionBrief, Findings, FundFinding, SectorFinding, EvidenceSet, mentions_publication_date(), publication_date_keys(), _article_context_for_interpret() (+65 more)

### Community 4 - "ExecutionPlan"
Cohesion: 0.03
Nodes (122): asks_ideal_portfolio_shape(), ensure_quality_fund_list(), ensure_rating_screen(), asks_category_performance(), _compare_fund_count(), ensure_category_performance_plan(), ensure_fund_holdings_followup_plan(), ensure_rating_list_funds() (+114 more)

### Community 5 - "category_plan.py"
Cohesion: 0.07
Nodes (37): match_all_scheme_categories(), match_scheme_category(), _named_scheme_category(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), asks_cross_category_compare(), asks_fund_holdings_followup() (+29 more)

### Community 6 - "query_log.py"
Cohesion: 0.12
Nodes (11): _events(), run_ask_engine(), stream_ask_engine(), run_insight_pipeline(), stream_insight_pipeline(), find_query_log_file(), new_fund_brief_logger(), new_query_logger() (+3 more)

### Community 7 - "load_config"
Cohesion: 0.06
Nodes (64): CommonConfig, _parse(), _append(), _clock(), RunLog, _write(), _bound_llm(), bundle_cli_main() (+56 more)

### Community 8 - "test_ask_speed.py"
Cohesion: 0.11
Nodes (24): collect_evidence_calendar_dates(), add_article(), cores_for_float(), cores_in_text(), finalize_text_fields(), format_user_calendar_date(), fund_portfolio_cores(), number_is_grounded() (+16 more)

### Community 9 - "Settings"
Cohesion: 0.08
Nodes (33): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), article_in_fetch_window(), google_time_query(), has_news_date_range(), iter_inclusive_days() (+25 more)

### Community 10 - "sector_leaderboard/run.py"
Cohesion: 0.07
Nodes (58): SectorLeaderboardFactsBase, build_narrative_user(), _block(), build_user(), _abs_scores(), backtest(), _cell(), _chips() (+50 more)

### Community 11 - "market_driver_digest/run.py"
Cohesion: 0.05
Nodes (66): editorial_context(), market_numbers(), fmt_inr_crore(), fmt_pct(), ordinal(), sector_names_for_pulse(), cumulative(), FlowDay (+58 more)

### Community 12 - "load_config"
Cohesion: 0.05
Nodes (48): _bool(), _float(), _freshness_flag(), _int(), load_config(), notify_failure(), load_json(), backfill_recent() (+40 more)

### Community 13 - "compute.py"
Cohesion: 0.08
Nodes (42): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+34 more)

### Community 14 - "insight_links.py"
Cohesion: 0.19
Nodes (12): _group_layered_articles(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings() (+4 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (59): fetch_fund_managers_for_isin(), _finalize_screen_payload(), run_driver_affected_funds_adapter(), DataNeed, _active_sector_equity(), _args_from_question(), _articles_for_affected_question(), _as_date() (+51 more)

### Community 16 - "validate.py"
Cohesion: 0.12
Nodes (28): _data(), _dump(), LoopResult, _problems(), run_quality_loop(), _validation_payload(), _verify_user(), numeric_leaves() (+20 more)

### Community 17 - "json"
Cohesion: 0.05
Nodes (43): atomic_write_json(), holding_data_dir(), _daily_path(), load_daily(), save_daily(), HoldingInsightsJobManager, on_progress(), HoldingJobBusy (+35 more)

### Community 18 - "QueryLogger"
Cohesion: 0.08
Nodes (13): _pillar_maximum(), ParsedQuery, attach_query_log_meta(), clip_log_text(), _kv(), query_log_page_href(), QueryLogger, _shrink_for_log() (+5 more)

### Community 19 - "news_reader.py"
Cohesion: 0.06
Nodes (53): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+45 more)

### Community 20 - "macro_data.py"
Cohesion: 0.15
Nodes (25): PortfolioComposeRequest, BondYieldResult, _client(), _codes(), walk(), CPIRecord, fetch_bond_yields(), fetch_cpi() (+17 more)

### Community 21 - "narrative.py"
Cohesion: 0.05
Nodes (45): enforce_prompt_budget(), EvidenceArticle, format_evidence_block(), assemble_body(), beats_from_draft(), build_user_prompt(), compact_facts(), _compact_news_map() (+37 more)

### Community 22 - "match.py"
Cohesion: 0.05
Nodes (66): _all_dates(), _bundle_is_live(), create_router(), daily(), dates(), generate(), health(), holding_insights_job_latest() (+58 more)

### Community 23 - "market_daily_store.py"
Cohesion: 0.08
Nodes (25): JobProgress, _write(), _articles(), build_market_daily_snapshot(), _daily_path(), _newer_bundle(), save_market_daily(), _sector_names() (+17 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.09
Nodes (47): extract_top_sectors(), build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has() (+39 more)

### Community 25 - "insight/portfolio_scope.py"
Cohesion: 0.09
Nodes (37): _ensure_portfolio_for_fund_news(), node_bridge(), build_drawdown_wave2_calls(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), question_asks_portfolio_level_drawdown(), question_signals_investor_book() (+29 more)

### Community 26 - "build_fund_display_tables"
Cohesion: 0.10
Nodes (23): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), format_display_tables_markdown(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers(), strip_markdown_tables_from_prose(), _strip_overview_prose_block() (+15 more)

### Community 27 - "gather.py"
Cohesion: 0.05
Nodes (59): canonical_facet(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), EvidenceItem, _extract_funds_from_result(), gather_evidence() (+51 more)

### Community 28 - "investor_drawback.py"
Cohesion: 0.08
Nodes (35): strip_grounding_holes(), investor_book_cores(), attach_drawback_digest(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer(), question_asks_all_schemes_in_answer(), question_wants_scheme_names() (+27 more)

### Community 29 - "normalize_user_facing_text"
Cohesion: 0.17
Nodes (8): ensure_markdown_table_spacing(), normalize_user_facing_text(), strip_context_disclaimer(), _clean_answer(), strip_meta_opening_heading(), test_strip_meta_opening_heading_keeps_summary_prose(), test_normalize_inserts_blank_line_before_markdown_table(), test_normalize_na_to_hyphen()

### Community 30 - "portfolio_news_impact.py"
Cohesion: 0.13
Nodes (18): _articles_from_pack(), build_portfolio_news_impact_dossier(), ensure_portfolio_news_impact_plan(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), question_is_portfolio_news_impact() (+10 more)

### Community 31 - "trends.py"
Cohesion: 0.12
Nodes (15): detect_signals(), _surge(), DayPoint, entity_daily_series(), price_trend(), price_trend_from_closes(), PriceTrend, session_day() (+7 more)

### Community 32 - "fund_name_gate.py"
Cohesion: 0.09
Nodes (28): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), _bound_fund_name(), clarify_plan_if_fund_unknown(), _compare_sides_resolvable(), is_fund_name_clarification_prompt(), _known_names_in_text(), _plan_uses_fund_scoped_tools() (+20 more)

### Community 33 - "task_exec.py"
Cohesion: 0.13
Nodes (29): bind_subjects(), _book_total_line(), _canon_fact(), _category_in_planner_text(), _cell(), _compare_subject_kind(), coverage_line(), _fact_label() (+21 more)

### Community 34 - "get_settings"
Cohesion: 0.06
Nodes (66): ask(), ask_stream(), AskRequest, _attach_llm_meta(), fund_brief(), health(), get_settings(), make_plan() (+58 more)

### Community 35 - "sector_query_for_label"
Cohesion: 0.12
Nodes (22): sector_headline_phrase(), append_personal_tail(), _display_fund_name(), _fetch_fund_short_name(), format_fund_tail(), fund_isins_from_row(), _headline_ends_with_your(), holding_row_for_instrument() (+14 more)

### Community 36 - "fund_display.py"
Cohesion: 0.10
Nodes (31): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_pct(), _fmt_pp() (+23 more)

### Community 37 - "normalize.py"
Cohesion: 0.18
Nodes (21): aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values(), _book_has_market_value(), _fill_missing_from_live(), _first() (+13 more)

### Community 38 - "pytest"
Cohesion: 0.11
Nodes (25): MarketDriverFactsBase, _brent_horizons(), _brent_usd(), build_digest_datasets(), _closest_close_on_or_before(), _cpi_ytd(), _ddmmyyyy_to_iso(), _fii_dii_7d() (+17 more)

### Community 39 - "plan.py"
Cohesion: 0.09
Nodes (25): explanation_brief(), canonicalize_field(), field_prompt_table(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), normalize_fund_pick_from_planner() (+17 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "test_sector_leaderboard_run.py"
Cohesion: 0.14
Nodes (30): LlmJsonResult, LlmUsage, call(), DryRunHalt, build(), compose_headline(), main(), _both_sides() (+22 more)

### Community 42 - "news_filter.py"
Cohesion: 0.16
Nodes (19): filter_usable_articles(), _is_low_quality_article(), merge_article_pool(), rank_and_pick_articles(), score_article(), _stock_terms(), _title_mentions_stock(), _vector_strength() (+11 more)

### Community 43 - "plan_enforce.py"
Cohesion: 0.08
Nodes (21): merge_planner_asked_facts(), tag_answer_parts(), question_asks_current_book_allocation(), apply_category_scoped_compare_funds(), apply_deictic_equity_compare_funds(), _compare_category_slug(), drop_misclassified_category_composition(), ensure_compare_fund_pair() (+13 more)

### Community 44 - "logging.py"
Cohesion: 0.18
Nodes (8): _env_secrets(), prune_logs(), _redact(), _redact_text(), _rmtree(), RunArtifacts, _usage(), test_artifacts_redact_and_prune()

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "get_sector_fund_ranking_index"
Cohesion: 0.06
Nodes (38): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+30 more)

### Community 47 - "sources/google_news.py"
Cohesion: 0.12
Nodes (17): fetch_entity_items(), _fetch_query_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url(), fetch_macro_items(), is_macro_match(), macro_fetch_entities() (+9 more)

### Community 48 - "entity_retrieval.py"
Cohesion: 0.08
Nodes (45): _adapter(), cluster_rows(), _collapse(), _dedupe(), find(), union(), _group_of(), _keys() (+37 more)

### Community 49 - "fund_scheme_match.py"
Cohesion: 0.12
Nodes (23): _phrase_in(), amc_token_in_question(), catalog_fund_matches_question(), _category_phrases_in_question(), _constraint_in_scheme_name(), _distinctive_constraints(), pick_best_matching_scheme(), _prune_distinctive_constraints() (+15 more)

### Community 50 - "app.py"
Cohesion: 0.06
Nodes (48): holding_insights_page(), holding_insights_stock_log_page(), portfolio_insights_page(), ask_memory(), ask_query_log(), ask_sources(), _attach_portfolio_to_ask(), backfill_page() (+40 more)

### Community 51 - "gold_service.py"
Cohesion: 0.10
Nodes (21): _fetch(), get_gold_snapshot(), get_silver_snapshot(), gold_horizon_code(), gold_macro_series_row(), _load_payload(), _merged_series(), add() (+13 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "graph.py"
Cohesion: 0.05
Nodes (73): _amc_token_set(), _categories_equivalent(), node_evidence_gate(), node_route(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_deictic_and_memory_primary_fund() (+65 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (20): build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns(), normalize_vs_benchmark_payload() (+12 more)

### Community 55 - "execute_capability"
Cohesion: 0.11
Nodes (23): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), _positive_ms(), widen_portfolio_args(), clear_conversation(), drain_cache_events(), recall_slice() (+15 more)

### Community 56 - "generate_json"
Cohesion: 0.14
Nodes (21): _add_usage(), _default_call(), format_articles_block(), generate_json(), _invoke_with_retry(), LlmSchemaError, LlmUnavailable, _run_bounded() (+13 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "get_fund_index"
Cohesion: 0.07
Nodes (36): _catalog_alias_keys(), fetch_fund_managers_for_query(), get_fund_index(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), prefer_resolved_fund_name(), resolve_fund_for_query() (+28 more)

### Community 59 - "executor.py"
Cohesion: 0.05
Nodes (52): asks_rating_list(), fetch_category_ratings(), rating_spec_for_forced_screen(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _capability_cache_key(), _conversation_id() (+44 more)

### Community 60 - "test_fund_risk.py"
Cohesion: 0.04
Nodes (77): _followup_modules(), asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept() (+69 more)

### Community 61 - "test_fund_drawdown.py"
Cohesion: 0.13
Nodes (29): asks_category_drawdown(), drawdown_words(), ensure_drawdown_tools(), is_drawdown_definition(), _named_standard_periods(), periods_for_question(), _question_needs_drawdown(), requested_fund_facts() (+21 more)

### Community 62 - "test_portfolio_layer.py"
Cohesion: 0.08
Nodes (20): project_concentration(), _drop_sold(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore (+12 more)

### Community 63 - "re"
Cohesion: 0.10
Nodes (24): asks_financial_news(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+16 more)

### Community 64 - "lib/portfolio_scope.py"
Cohesion: 0.10
Nodes (27): build_portfolio_scope(), FundRef, _holding_equity_allowed(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest(), load_portfolio_funds() (+19 more)

### Community 65 - "fund_universe_agent.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "twelve_data_brent.py"
Cohesion: 0.17
Nodes (19): _api_key(), BrentSyncResult, _call_time_series(), fetch_day(), fetch_days(), history_path(), main(), _merge_rows() (+11 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.14
Nodes (15): asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), memory_shows_investor_book(), mentions_advice(), _tokens() (+7 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "news_rag/config.py"
Cohesion: 0.10
Nodes (10): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, _build_encoder(), embeddings_ready(), main() (+2 more)

### Community 71 - "portfolio/cache.py"
Cohesion: 0.15
Nodes (18): _run_get_investor_portfolio(), _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), get_active_crn(), get_normalized_portfolio(), peek_derived() (+10 more)

### Community 72 - "retrieve_scoped_news"
Cohesion: 0.12
Nodes (15): _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news(), _sector_entities() (+7 more)

### Community 73 - "market_data.py"
Cohesion: 0.15
Nodes (20): _done(), _flow_data(), _from_history(), get_fii_dii_today(), get_nifty(), get_series(), get_usdinr(), _iso_date() (+12 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "test_portfolio_intents.py"
Cohesion: 0.06
Nodes (59): _leave_tools_alone(), owned_holding_names(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings(), _ensure_portfolio_data_for_compare(), _ensure_portfolio_data_for_holdings(), ensure_whole_book_catalog_scope() (+51 more)

### Community 77 - "sector_fund_ranking.py"
Cohesion: 0.06
Nodes (24): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), candidate_sector_names(), classify_sector_fund_purity(), _damerau() (+16 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 79 - "rupeestop_auth.py"
Cohesion: 0.09
Nodes (22): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url(), _looks_like_jwt() (+14 more)

### Community 80 - "holdings_market.py"
Cohesion: 0.15
Nodes (16): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+8 more)

### Community 81 - "test_conversation_memory.py"
Cohesion: 0.17
Nodes (21): _store_turn_memory(), note_cache(), append_chat_turn(), _fresh(), get_memory(), get_or_create(), reset_memory(), save_sources() (+13 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.08
Nodes (55): _age(), _allocation_bucket_rows(), _as_of(), _asks_portfolio_rs_ratings(), _book_line(), _category_amount_map(), _comparison_rows(), _composition_line() (+47 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 86 - "portfolio_equity.py"
Cohesion: 0.14
Nodes (14): _is_equity(), load_equity_holdings(), fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), InvalidCRN, PortfolioNotConfigured (+6 more)

### Community 87 - "macro_context.py"
Cohesion: 0.09
Nodes (24): week_index_movers(), _bars(), catalog_path(), fetch_ohlc(), IndexSpec, load_catalog(), news_sectors_for_index(), OhlcBar (+16 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.13
Nodes (21): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_category_allocation_without_planner_tools_still_fetches_the_book() (+13 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 90 - "official.py"
Cohesion: 0.17
Nodes (17): NumericRecord, unavailable(), fetch_cpi_record(), pick(), fetch_fii_dii(), fetch_gdp_record(), fetch_gsec(), fetch_gst() (+9 more)

### Community 91 - "test_sector_leaderboard_score.py"
Cohesion: 0.18
Nodes (18): sector_label(), llm_schema(), prominence(), rank(), score_sector(), score_stories(), _cluster(), _row() (+10 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.03
Nodes (93): normalize_holding_row(), normalize_sector_row(), EvidencePack, EvidenceRow, _add_category_comparison(), append_investor_portfolio_overview_tables(), _attach_rs_ratings_to_screen(), _one() (+85 more)

### Community 96 - "contracts.py"
Cohesion: 0.05
Nodes (39): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), fact_values_already_stated() (+31 more)

### Community 97 - "fund_type_name_spec"
Cohesion: 0.16
Nodes (12): _fund_type_in_name_clause(), fund_type_name_spec(), asks_computed_illustration(), apply_pure_concept_plan(), question_is_pure_general_concept(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator(), test_name_me_debt_fund_gets_rating_spec() (+4 more)

### Community 98 - "test_ai_insight_common_qdrant_access.py"
Cohesion: 0.13
Nodes (26): is_stale(), newest_scraped_at(), _as_dict(), _client(), _drop(), _entity_view(), EntityRowsResult, _explode() (+18 more)

### Community 99 - "update.py"
Cohesion: 0.13
Nodes (18): drop_old_turns(), compare_payload_matches_funds(), fund_name_mentioned_in_memory(), add_gist(), empty_frame(), empty_state(), expire_stale_entities(), stack_entry() (+10 more)

### Community 100 - "parse.py"
Cohesion: 0.17
Nodes (11): _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), infer_window_days_from_question(), parse_date_field(), parse_time_window() (+3 more)

### Community 102 - "test_greeting.py"
Cohesion: 0.16
Nodes (13): greeting_reply(), identity_reply(), _mirror_greeting(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens() (+5 more)

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.11
Nodes (18): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_PIPELINE_DAILY (+10 more)

### Community 104 - "env"
Cohesion: 0.11
Nodes (18): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL (+10 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.22
Nodes (10): build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score(), test_default_manager_answer_drops_former_managers(), test_enrich_filters_past_only() (+2 more)

### Community 106 - "sector_alignment.py"
Cohesion: 0.08
Nodes (36): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _rule_sector_picks(), canonical_direction_for_driver(), clear_macro_impact_cache() (+28 more)

### Community 107 - "market_pulse.py"
Cohesion: 0.10
Nodes (26): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), _fetch_macro_query(), _query_variants(), run_macro_news_enhanced(), _collect() (+18 more)

### Community 108 - "fund_search.py"
Cohesion: 0.15
Nodes (13): _attach_trailing_product(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question() (+5 more)

### Community 109 - "fact_slots.py"
Cohesion: 0.18
Nodes (12): asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), slots_from_plan(), plan_wants_fund_concentration(), _book() (+4 more)

### Community 110 - "fund_match.py"
Cohesion: 0.11
Nodes (14): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+6 more)

### Community 111 - "Settings"
Cohesion: 0.09
Nodes (28): _fund_stats_from_csv(), load_holdings_rows_from_xlsx(), multi_query_for(), _strip_legal_suffix(), _aliases_for(), build_holding_entities(), canonical_key(), _display_name() (+20 more)

### Community 112 - "Cluster"
Cohesion: 0.14
Nodes (22): Cluster, cluster_score(), rank_clusters(), evidence_from_clusters(), _float(), _int(), pick_evidence(), story_weight() (+14 more)

### Community 113 - "fund_rating_categories.py"
Cohesion: 0.09
Nodes (22): CategoryMatch, _close(), fund_type_for_category(), _metal_category(), _metal_flags(), _names_a_type(), _phrase_score(), rating_scope_pairs() (+14 more)

### Community 114 - "insights.py"
Cohesion: 0.30
Nodes (10): build_insights(), _equity_pct(), Insight, insight_lines(), insights_for_brief(), _num(), _style_band(), _book() (+2 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "data_pack.py"
Cohesion: 0.50
Nodes (3): build_data_pack(), build(), _compact()

### Community 117 - "test_fund_drawdown.py"
Cohesion: 0.15
Nodes (27): _add_drawdown_call(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), fetch_drawdown_periods(), fetch_trailing_drawdown(), investment_amount() (+19 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "macro_news_cache.py"
Cohesion: 0.10
Nodes (20): _cache_has_article_text(), _fresh(), get_macro_news(), _log(), _read(), select_macro_for_question(), _slim_clusters(), _write() (+12 more)

### Community 121 - "prompts.py"
Cohesion: 0.15
Nodes (11): plan_system_prompt(), build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix() (+3 more)

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "fields.py"
Cohesion: 0.09
Nodes (33): _asks_book(), bind_fields_to_tools(), _book_fields(), field_need(), FieldNeed, fields_from_question(), _find_term(), _fund_fields() (+25 more)

### Community 124 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 125 - "fund_rating_screen.py"
Cohesion: 0.05
Nodes (65): categories_for(), pickable_categories(), is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank() (+57 more)

### Community 126 - "run-pipeline"
Cohesion: 0.29
Nodes (6): jobs, run-pipeline, name, on, runs-on, timeout-minutes

### Community 127 - "GraphState"
Cohesion: 0.12
Nodes (17): build_result(), _conversation_id(), GraphState, _insight_headline_narrative(), node_reply(), node_resolve(), node_wave2(), run_graph() (+9 more)

### Community 128 - "._ensure_loaded"
Cohesion: 0.16
Nodes (3): FundIndex, _infer_category_and_type(), _sync_amc_prefix_from_catalog()

### Community 129 - "ask_plan.py"
Cohesion: 0.24
Nodes (9): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), test_ask_plan_keeps_rich_agent_fields(), test_cluster_prefers_larger_groups() (+1 more)

### Community 130 - "worker/src/index.ts"
Cohesion: 0.43
Nodes (7): authorize(), dispatchBackfill(), DispatchInputs, Env, fetch(), json(), scheduled()

### Community 131 - "steps"
Cohesion: 0.25
Nodes (8): PYTHONPATH, steps, env, if, name, run, uses, working-directory

### Community 132 - "steps"
Cohesion: 0.25
Nodes (8): steps, PYTHONPATH, env, if, name, run, uses, working-directory

### Community 133 - "with"
Cohesion: 0.25
Nodes (8): with, cache, if-no-files-found, key, name, path, python-version, restore-keys

### Community 134 - "aggregate_fund_holdings.py"
Cohesion: 0.10
Nodes (24): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+16 more)

### Community 135 - "format_inr"
Cohesion: 0.21
Nodes (11): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), _fmt_inr(), test_format_indian_amount_lakh() (+3 more)

### Community 136 - "Settings"
Cohesion: 0.07
Nodes (40): Settings, _merge_publisher_error_reasons(), write_day_report(), _bucket(), _entity_names(), summarize_errors(), write_error_summary(), _atomic_write() (+32 more)

### Community 137 - "inputs"
Cohesion: 0.40
Nodes (5): default, description, required, type, holdings_limit

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "repo_root"
Cohesion: 0.30
Nodes (11): write_ask_market_snapshot(), FiiDiiSnapshot, write_snapshot(), fetch_fii_dii_snapshot(), fetch_all(), main(), write_fii_dii(), write_latest() (+3 more)

### Community 141 - "news_insight_articles"
Cohesion: 0.15
Nodes (9): _news_subject(), clean_news_insight(), complete_sentences(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words(), test_news_about_hdfc_bank_is_not_a_market_pulse() (+1 more)

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

### Community 146 - "portfolio_bind.py"
Cohesion: 0.24
Nodes (9): bind_cached_portfolio(), _catalog_fund_holdings_question(), ensure_tools_for_data_question(), finish_portfolio_plan_bind(), _investor_args(), _merge_fund(), question_mentions_own_book(), test_catalog_fund_holdings_not_own_book() (+1 more)

### Community 147 - "extract.ts"
Cohesion: 0.80
Nodes (4): decodeHtmlEntities(), extractFromHtml(), metaContent(), stripTags()

### Community 148 - "sync-news-runs-to-r2.sh"
Cohesion: 0.40
Nodes (4): AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, sync-news-runs-to-r2.sh script

### Community 149 - "date_range"
Cohesion: 0.29
Nodes (7): default, description, required, type, date_range, workflow_dispatch, inputs

### Community 150 - "google_news_when"
Cohesion: 0.40
Nodes (5): default, description, required, type, google_news_when

### Community 151 - "portfolio_json"
Cohesion: 0.40
Nodes (5): portfolio_json, default, description, required, type

### Community 152 - "sectors_limit"
Cohesion: 0.40
Nodes (5): sectors_limit, default, description, required, type

### Community 153 - "end_date"
Cohesion: 0.40
Nodes (5): default, description, required, type, end_date

### Community 154 - "holdings_limit"
Cohesion: 0.40
Nodes (5): default, description, required, type, holdings_limit

### Community 155 - "pause_sec"
Cohesion: 0.40
Nodes (5): pause_sec, default, description, required, type

### Community 156 - "start_date"
Cohesion: 0.40
Nodes (5): start_date, default, description, required, type

### Community 159 - "time"
Cohesion: 0.04
Nodes (38): _backoff(), _consent_jar(), _fetch_http_get(), fetch_publisher_url(), fetch_url(), _handle_google_response(), make_session(), post_url() (+30 more)

### Community 163 - "test_portfolio_startup_cache.py"
Cohesion: 0.25
Nodes (11): clear_cache_for_tests(), seed_portfolio_cache_for_tests(), PortfolioError, PortfolioUnavailable, _doc(), test_compare_binds_cached_large_cap(), test_derived_views_split_assets_and_categories(), test_preload_failure_returns_false() (+3 more)

### Community 169 - "nse_fii_dii.py"
Cohesion: 0.20
Nodes (11): current_artifacts(), log_external(), _bucket(), _httpx_json(), _impit_json(), _leg(), _log_external(), _nse_json() (+3 more)

### Community 170 - "ask_market_bridge.py"
Cohesion: 0.23
Nodes (6): fetch_ask_market_records(), fetch_gold_record(), get_ask_market_snapshot(), test_fetch_ask_market_records_includes_extras(), test_fetch_gold_record_ok(), test_get_ask_market_snapshot_shape()

### Community 174 - "fund_search.py"
Cohesion: 0.13
Nodes (18): headline_rating(), build_holding_overlap(), _clean_company_name(), detail_has_live_facts(), _entry_matches_query_scheme(), _fund_context_for_managers(), _fund_text(), get_fund_benchmark() (+10 more)

### Community 178 - "graph.py"
Cohesion: 0.12
Nodes (19): RequestTelemetry, question_wants_concentration_tables(), _answer_stream_chunks(), _drop_scheme_is_the_whole_book(), Node, _plan_fetches_manager_roster(), stream_graph_pipeline(), _scheme_type_slug_from_question() (+11 more)

### Community 180 - "stock_news.py"
Cohesion: 0.23
Nodes (9): fetch_stock_news(), _holding_rows(), news_for_movers(), _news_window(), _one_mover(), _slim_article(), filter_articles_to_week(), published_in_equity_week() (+1 more)

### Community 181 - "book_news_map.py"
Cohesion: 0.21
Nodes (14): _clean_holding_tokens(), book_wide_sectors(), _display_name(), _has_named_stock(), news_calls_for_book(), _news_name(), _pct(), resolve_book_sector() (+6 more)

### Community 182 - "portfolio_insights.js"
Cohesion: 0.42
Nodes (9): api(), card(), chipHtml(), esc(), headers(), loadReady(), renderCompose(), renderReady() (+1 more)

### Community 183 - "fund_catalog.py"
Cohesion: 0.11
Nodes (24): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+16 more)

### Community 184 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 185 - "test_fund_name_gate_and_hydrate.py"
Cohesion: 0.33
Nodes (7): _load_planner_memory(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), test_hydrate_memory_from_ui_prior_turns(), test_load_planner_memory_hydrates_from_prior_context(), test_load_planner_memory_ignores_incomplete_prior_turn(), test_normalize_prior_turns_skips_incomplete_assistant()

### Community 186 - "fund_by_isin.py"
Cohesion: 0.18
Nodes (13): fetch_fund_detail_for_week(), fund_row_from_detail(), is_equity_scheme_type(), is_valid_isin_shape(), load_equity_fund_by_isin(), normalize_isin(), scheme_type_label(), resolve_canonical_isin() (+5 more)

### Community 187 - "yf_week.py"
Cohesion: 0.44
Nodes (4): _bars_before_today(), _history_settled_bars(), stock_change_1w_settled(), stock_daily_week_settled()

### Community 188 - "prune_insight_logs.py"
Cohesion: 0.36
Nodes (3): main(), prune_insight_logs(), test_prune_keeps_latest_artifact_and_matching_flat_log()

### Community 190 - "node_wave1"
Cohesion: 0.32
Nodes (5): _attach_conversation(), _catalog_fanout_fund_names(), _maybe_compare_funds_after_multi_screen(), _maybe_enrich_picked_fund_from_screen(), node_wave1()

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 193 - "infer_fund_news_layers"
Cohesion: 0.31
Nodes (6): infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only(), test_overview_news_is_holdings_and_sectors()

### Community 194 - "validate_capability_args"
Cohesion: 0.10
Nodes (18): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded() (+10 more)

### Community 195 - "pick_random_scheme_category_for_compare"
Cohesion: 0.40
Nodes (3): metal_scheme_categories(), pick_random_scheme_category_for_compare(), test_debt_type_picks_a_debt_scheme_category()

### Community 197 - "brief.py"
Cohesion: 0.06
Nodes (37): analyst_should_run(), asks_market_briefing(), asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief() (+29 more)

### Community 198 - "283041/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 203 - "fund_brief.py"
Cohesion: 0.09
Nodes (35): instrument_to_qdrant_names(), PortfolioScope, qdrant_filter_names(), Settings, _article_entities(), build_events(), cluster_articles(), _cluster_entities() (+27 more)

### Community 206 - "test_ai_insight.py"
Cohesion: 0.18
Nodes (6): digest_filter(), _holding_mentioned(), matches_entity(), contains_phrase(), test_digest_filter_uses_stricter_scores(), test_sector_exclude_drops_nbfc_from_banks()

### Community 208 - "Envelope"
Cohesion: 0.05
Nodes (84): build(), compose(), _cards(), main(), _build(), _user(), Signal, news_map_block() (+76 more)

### Community 209 - "57e233/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 212 - "c72b25/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 213 - "a45664/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 217 - "7859f0/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 222 - "layer_tools.py"
Cohesion: 0.09
Nodes (28): nifty50_ticker(), aggregate_sectors_from_holdings(), extract_top_holdings(), _run_get_market_snapshot(), _run_get_portfolio_data(), _price_holdings(), benchmark_return_for_scheme(), _cache_path() (+20 more)

### Community 225 - "insights.js"
Cohesion: 0.22
Nodes (18): api(), arrow(), bars(), card(), chart(), diverging(), esc(), headers() (+10 more)

### Community 226 - "holding_insights.js"
Cohesion: 0.35
Nodes (14): api(), clearError(), escapeHtml(), headers(), instrumentMeta(), loadSaved(), logLink(), poll() (+6 more)

### Community 227 - "insight_log.js"
Cohesion: 0.70
Nodes (4): api(), esc(), headers(), load()

### Community 229 - "news_pipeline/config.py"
Cohesion: 0.05
Nodes (23): Publisher, SectorQuery, is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), finish_run_logger(), _datetime_range() (+15 more)

### Community 230 - "concurrent_futures"
Cohesion: 0.24
Nodes (4): check(), main(), run_case(), _Usage

### Community 231 - "sector_news.py"
Cohesion: 0.24
Nodes (9): SectorCluster, _direction_for_side(), _fetch_layered(), fetch_sector_cluster_news(), _filter_by_direction(), news_for_sector_clusters(), _week_filter_window(), equity_week_window() (+1 more)

### Community 233 - "test_ai_insight_mospi.py"
Cohesion: 0.25
Nodes (10): _client(), _sse(), test_400_is_not_retried(), test_gdp_yoy_uses_prior_fiscal_year(), handler(), test_retries_500_then_reads_cache(), handler(), test_snapshot_keeps_other_entities_when_one_fails() (+2 more)

### Community 237 - "holding_insights/llm.py"
Cohesion: 0.13
Nodes (23): llm_allow_fallback(), _as_paragraph(), call_holding_llm(), _call(), _headline_week_matches(), _normalize_response(), parse_insight_lines(), _pct_in_text() (+15 more)

### Community 238 - "app.js"
Cohesion: 0.31
Nodes (12): errText(), esc(), fundCard(), moverTable(), onCrnInput(), onIsinInput(), paragraphSection(), parseResponse() (+4 more)

### Community 239 - "embed.py"
Cohesion: 0.07
Nodes (19): embed_query(), corpus_entity_names(), _body(), grouped_news(), NewsTarget, search_targets(), _normalize_key(), resolve_corpus_entities() (+11 more)

### Community 240 - "run_insights_daily.sh"
Cohesion: 0.50
Nodes (4): note(), PYTHONPATH, PYTHONUNBUFFERED, run_insights_daily.sh script

### Community 241 - "test_ai_insight_common_clustering.py"
Cohesion: 0.39
Nodes (7): _row(), _sample(), _signature(), test_hash_seed_does_not_change_ids(), test_same_clusters_after_shuffle(), test_syndicated_copies_count_once(), test_title_mode_does_not_merge_unrelated_stories_that_share_an_entity()

### Community 252 - "extract.py"
Cohesion: 0.36
Nodes (5): _authors(), _clean(), extract_article(), _meta(), _meta_fallback()

### Community 253 - "test_composer_table_summaries.py"
Cohesion: 0.19
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_parse_tables_append_directive(), test_strip_empty_bold_sections(), test_summarize_tables_for_composer_extracts_mix_and_holdings()

### Community 254 - "test_fund_rating_screen.py"
Cohesion: 0.05
Nodes (62): asks_taxonomy(), match_all_fund_types(), _category_fund_name_spec(), fund_naming_clause(), _keep_asked_return(), _label_in(), _looks_like_fund_list(), _metal_fund_categories() (+54 more)

### Community 260 - "holding_insights_stock_log.js"
Cohesion: 0.60
Nodes (5): api(), escapeHtml(), headers(), load(), render()

### Community 270 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 274 - "test_multi_fact_fund.py"
Cohesion: 0.10
Nodes (23): table_source(), ensure_multi_fact_tools(), ensure_planner_fund_fact_modules(), top_n_from_question(), _fund_plan(), test_a_rating_row_is_filled_with_returns_riskometer_and_category_average(), test_aum_and_exit_load_render_only_those_lines(), test_deictic_exit_load_swaps_limits_for_snapshot() (+15 more)

### Community 275 - "CapabilityCache"
Cohesion: 0.15
Nodes (7): CapabilityCache, _Entry, get_capability_cache(), test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner(), test_capabilities_cache_stores_and_retrieves()

### Community 276 - "new/fund_context.py"
Cohesion: 0.16
Nodes (18): _attach_daily_bars(), attribution_summary(), _daily_prices_for_holding(), _equity_holdings_from_detail(), _fmt_signed_pct(), _fund_return_1w_api(), FundFacts, holding_impact_1w() (+10 more)

### Community 277 - "router.py"
Cohesion: 0.15
Nodes (14): build_fund_facts(), cushion_funds(), nav_1w_for_isin(), equity_fund_week_page(), FundRow, create_equity_fund_week_router(), page(), run_endpoint() (+6 more)

### Community 278 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 279 - "compose_llm.py"
Cohesion: 0.09
Nodes (44): scrub_refusal_prose(), split_sentences(), _clean_summary_sentence(), compose_fund_narrative(), _compose_user_message(), _dry_mover_rows(), _ensure_fund_summary(), _facts_payload() (+36 more)

### Community 281 - "build_top100_holdings.py"
Cohesion: 0.38
Nodes (7): check_yfinance(), load_master_index(), lookup_master(), main(), normalize_name(), pick_best_master(), resolve_yf_ticker()

### Community 282 - "test_macro_scope.py"
Cohesion: 0.16
Nodes (11): question_is_standalone_macro(), ensure_catalog_tools_for_fund_news(), reconcile_planner_invented_fund_name(), apply_standalone_macro_scope(), _macro_news_topics(), test_fund_news_adds_catalog_tools(), test_how_its_affecting_rupee_is_not_deictic_fund_title(), test_macro_scope_injects_news_when_planner_sent_no_tools() (+3 more)

### Community 285 - "MospiClient"
Cohesion: 0.15
Nodes (7): _cache_dir(), MospiClient, MospiError, _payload(), _sse_json(), _unhandled_exception_handler(), GraphUnavailable

### Community 287 - "AnswerMode"
Cohesion: 0.02
Nodes (118): asks_macro_explanation(), question_mentions_fund_scheme(), rating_list_plan(), rating_concept_plan(), asks_fund_category_average(), periods_requested_in_question(), apply_concept_example_to_plan(), asks_concept_with_catalog_example() (+110 more)

### Community 288 - "nav_service.py"
Cohesion: 0.10
Nodes (26): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+18 more)

## Knowledge Gaps
- **26 isolated node(s):** `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT` (+21 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2084 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **69 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `bridge.py`, `re`, `category_plan.py`, `news_insight_articles`, `test_multi_fact_fund.py`, `portfolio_bind.py`, `macro_data.py`, `insight/portfolio_scope.py`, `test_macro_scope.py`, `investor_drawback.py`, `portfolio_news_impact.py`, `AnswerMode`, `fund_name_gate.py`, `task_exec.py`, `get_settings`, `test_portfolio_startup_cache.py`, `fund_display.py`, `plan.py`, `plan_enforce.py`, `graph.py`, `book_news_map.py`, `graph.py`, `test_fund_name_gate_and_hydrate.py`, `test_fund_risk.py`, `test_fund_drawdown.py`, `node_wave1`, `test_portfolio_layer.py`, `test_portfolio_intents.py`, `test_conversation_memory.py`, `fact_answer.py`, `test_portfolio_allocation.py`, `evidence_pack.py`, `contracts.py`, `fund_type_name_spec`, `fact_slots.py`, `test_composer_table_summaries.py`, `fields.py`, `fund_rating_screen.py`, `test_fund_rating_screen.py`, `GraphState`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `ExecutionPlan` (e.g. with `news_calls_for_book()` and `sector_book()`) actually correct?**
  _`ExecutionPlan` has 33 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN` to the rest of the system?**
  _26 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.06710839279646619 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `get_settings` to `interpret.py`, `ExecutionPlan`, `query_log.py`, `compute.py`, `portfolio_bind.py`, `CapabilityCache`, `news_reader.py`, `match.py`, `insight/portfolio_scope.py`, `gather.py`, `portfolio_news_impact.py`, `time`, `AnswerMode`, `task_exec.py`, `sector_query_for_label`, `plan.py`, `get_sector_fund_ranking_index`, `fund_search.py`, `app.py`, `gold_service.py`, `graph.py`, `graph.py`, `execute_capability`, `executor.py`, `test_fund_risk.py`, `node_wave1`, `test_portfolio_layer.py`, `validate_capability_args`, `insight/guardrails.py`, `brief.py`, `news_rag/config.py`, `portfolio/cache.py`, `retrieve_scoped_news`, `fund_brief.py`, `sector_fund_ranking.py`, `stock_fund_ranking.py`, `rupeestop_auth.py`, `portfolio_equity.py`, `test_ai_insight_common_qdrant_access.py`, `parse.py`, `market_pulse.py`, `fund_match.py`, `embed.py`, `prompts.py`, `GraphState`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ToolCall` (e.g. with `news_calls_for_book()` and `_apply_planner_request()`) actually correct?**
  _`ToolCall` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `re` be split into smaller, more focused modules?**
  _Cohesion score 0.056140350877192984 - nodes in this community are weakly interconnected._