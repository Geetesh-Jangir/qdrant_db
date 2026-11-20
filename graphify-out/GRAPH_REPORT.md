# Graph Report - db_design_with_qdrant_locally  (2026-11-20)

## Corpus Check
- 745 files · ~1,119,621 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 31 file(s) not represented in the graph (top: .example 6, .log 5, (none) 4)

## Summary
- 7534 nodes · 24457 edges · 283 communities (221 shown, 62 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 743 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9806c0c3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- execute_capability
- plan_enforce.py
- interpret.py
- build_evidence_pack
- collector.py
- fii_dii_flow_narrative/run.py
- format_inr
- test_two_wave_pipeline.py
- Settings
- sector_leaderboard/run.py
- execute_capability
- display_table_policy.py
- compute.py
- layer_tools.py
- tools.py
- retrieve_scoped_news
- holding_insights/run.py
- QueryLogger
- news_reader.py
- macro_data.py
- datetime
- api.py
- Settings
- tool_runners.py
- test_equity_fund_week.py
- test_fund_display_tables.py
- gather.py
- investor_drawback.py
- ExecutionPlan
- market_driver_digest/run.py
- trends.py
- sources/google_news.py
- task_exec.py
- llm_client.py
- sector_query_for_label
- fund_display.py
- normalize.py
- project_modules
- plan.py
- env
- time_ist.py
- article_quality.py
- plan_enforce.py
- test_portfolio_startup_cache.py
- env
- get_sector_fund_ranking_index
- book_news_map.py
- entity_retrieval.py
- fund_scheme_match.py
- app.py
- gold_service.py
- env
- investor_subject.py
- fund_rupeestop_metrics.py
- typing
- test_sector_leaderboard_run.py
- scrape-worker/package.json
- resolve_fund_for_query
- executor.py
- node_compose
- slot_route
- holding_stock_insights_store.py
- re
- pytest
- fund_universe_agent.py
- batch.ts
- twelve_data_brent.py
- insight/guardrails.py
- http-fetch.ts
- embed.py
- portfolio/cache.py
- holdings_market.py
- fund_rating_screen.py
- with
- fields.py
- sector_fund_ranking.py
- stock_fund_ranking.py
- rupeestop_auth.py
- news_rag/config.py
- time
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- RunLogger
- workspace.py
- sector_indices.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- lib/portfolio_scope.py
- test_category_rating_request_uses_admin_header
- env
- steps
- evidence_pack.py
- validate_capability_args
- NumericRecord
- test_fact_answer.py
- qdrant_access.py
- sector_exposure_tables.py
- portfolio/client.py
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- portfolio_news_impact.py
- market_pulse.py
- _normalize_fund_text
- fund_drawdown.py
- fund_match.py
- sources/universe.py
- slot_router.py
- fund_rating_categories.py
- insights.py
- vitest
- atomic_write_json
- _run_get_fund_data
- compilerOptions
- compilerOptions
- macro_news_cache.py
- new/run.py
- backfill
- macro_context.py
- news_digest.py
- normalize_rs_label
- run-pipeline
- update.py
- common/store.py
- graph.py
- worker/src/index.ts
- steps
- steps
- with
- json
- test_fund_drawdown.py
- validate.py
- inputs
- with
- inputs
- asks_computed_illustration
- price.py
- test_news_only_answer.py
- run-backfill.sh
- qdrant
- test_investor_grounding.py
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
- threading
- install.sh
- test_sector_leaderboard_score.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- nse_fii_dii.py
- GraphState
- diagnose_lightsail_site.sh
- Any
- graph.py
- EntityFunnel
- news.py
- test_metal_fund_rating.py
- portfolio_insights.js
- fund_catalog.py
- v2_scoring.py
- strip_missing_data_caveats
- nav_service.py
- .lookup_extracted_fund
- typing
- security_master.py
- build_derived_views
- metals_spot_tables.py
- infer_fund_news_layers
- csv
- HoldingInsightsJobManager
- brief.py
- 283041/manifest.json
- render_drawdown_body
- fund_brief.py
- test_ai_insight.py
- Envelope
- 57e233/manifest.json
- test_return_windows.py
- c72b25/manifest.json
- a45664/manifest.json
- compare_evidence.py
- 7859f0/manifest.json
- test_greeting.py
- contracts.py
- aggregate_fund_holdings.py
- clarify_plan_if_fund_unknown
- index_series.py
- test_call_json_llm.py
- Cluster
- insights.js
- holding_insights.js
- insight_log.js
- fix-daily-ingest.sh
- news_pipeline/config.py
- test_admin_headers_use_token_from_login
- test_guardrails_domain.py
- data_pack.py
- router.py
- repo_root
- holding_insights/llm.py
- app.js
- glossary.py
- run_insights_daily.sh
- build_top100_holdings.py
- install-insights-cron.sh
- test_ai_insight_mospi.py
- test_composer_table_summaries.py
- test_fund_rating_screen.py
- eval_planner.py
- pick_evidence
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- holding_insights_stock_log.js
- planner_catalog_knowledge.py
- test_daily_cron_settings.py
- JobManager
- strip_news_roundup
- MospiError
- top_n_from_question
- normalize_user_facing_text
- nav_settled.py
- load_equity_holdings
- question_is_pure_general_concept
- compose_llm.py
- unittest_mock
- yf_week.py

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 607 edges
2. `ToolCall` - 367 edges
3. `get_settings()` - 147 edges
4. `apply_planner_post_hooks()` - 123 edges
5. `load_config()` - 113 edges
6. `AnswerMode` - 108 edges
7. `node_compose()` - 102 edges
8. `QueryLogger` - 100 edges
9. `Settings` - 95 edges
10. `QuestionBrief` - 88 edges

## Surprising Connections (you probably didn't know these)
- `test_filter_rejects_breadcrumb_and_roundup()` --calls--> `score_article()`  [EXTRACTED]
  tests/test_equity_fund_week.py → new/news_filter.py
- `fake()` --calls--> `InvalidCRN`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/portfolio/errors.py
- `reject()` --calls--> `InvalidCRN`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/portfolio/errors.py
- `fetch_google_news()` --uses--> `GoogleBlockedError`  [INFERRED]
  news_pipeline/graph/nodes/fetch_google_news.py → lib/google_guard.py
- `test_market_sector_lists_in_display_without_funds()` --uses--> `SubAsk`  [INFERRED]
  tests/test_insight_interpret.py → news_rag/insight/brief.py

## Import Cycles
- 2-file cycle: `ai_insight/common/entity_retrieval.py -> ai_insight/common/retrieval_plan.py -> ai_insight/common/entity_retrieval.py`

## Communities (283 total, 62 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (54): get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate() (+46 more)

### Community 1 - "execute_capability"
Cohesion: 0.14
Nodes (7): CapabilityCache, _Entry, get_capability_cache(), test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner(), test_capabilities_cache_stores_and_retrieves()

### Community 2 - "plan_enforce.py"
Cohesion: 0.04
Nodes (67): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), pick_best_matching_scheme(), _bound_fund_name(), _compare_sides_resolvable(), _known_names_in_text(), question_refers_deictic_fund_safe(), single_fund_for_deictic() (+59 more)

### Community 3 - "interpret.py"
Cohesion: 0.07
Nodes (61): Findings, FundFinding, SectorFinding, _assemble(), _caveat(), check_composer_guardrails(), _claim_for_sector(), _claim_map() (+53 more)

### Community 4 - "build_evidence_pack"
Cohesion: 0.05
Nodes (47): ensure_rating_screen(), _followup_modules(), asks_fund_risk(), EvidenceRow, build_evidence_pack(), has_second_part(), _wants_end_summary(), asks_one_figure() (+39 more)

### Community 5 - "collector.py"
Cohesion: 0.06
Nodes (55): _bool(), CommonConfig, _float(), _freshness_flag(), _int(), load_config(), build_aligned_table(), _done() (+47 more)

### Community 6 - "fii_dii_flow_narrative/run.py"
Cohesion: 0.06
Nodes (48): editorial_context(), market_numbers(), cumulative(), FlowDay, history_path(), load_flow_history(), _num(), reset_circuit_for_tests() (+40 more)

### Community 7 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 8 - "test_two_wave_pipeline.py"
Cohesion: 0.06
Nodes (38): analyst_should_run(), asks_market_briefing(), asks_sector_lists(), collect_evidence_calendar_dates(), add_article(), cores_for_float(), cores_in_text(), finalize_text_fields() (+30 more)

### Community 9 - "Settings"
Cohesion: 0.09
Nodes (31): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), article_in_fetch_window(), google_time_query(), has_news_date_range(), iter_inclusive_days() (+23 more)

### Community 10 - "sector_leaderboard/run.py"
Cohesion: 0.08
Nodes (62): sector_label(), split_sentences(), SectorLeaderboardFactsBase, _block(), build_user(), _abs_scores(), backtest(), build() (+54 more)

### Community 11 - "execute_capability"
Cohesion: 0.10
Nodes (26): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), _positive_ms(), _take_conversation_slice(), widen_portfolio_args(), clear_conversation(), drain_cache_events() (+18 more)

### Community 12 - "display_table_policy.py"
Cohesion: 0.07
Nodes (29): periods_requested_in_question(), DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), fact_values_already_stated(), filter_display_tables(), _limit_tables(), _named_fund_overview() (+21 more)

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (50): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+42 more)

### Community 14 - "layer_tools.py"
Cohesion: 0.13
Nodes (18): aggregate_sectors_from_holdings(), extract_top_holdings(), normalize_holding_row(), normalize_sector_row(), _price_holdings(), build_insight_links(), _fact(), _key() (+10 more)

### Community 15 - "tools.py"
Cohesion: 0.07
Nodes (56): retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _plan_fund_performance_screen(), run_driver_affected_funds_adapter(), DataNeed, _active_sector_equity(), _articles_for_affected_question(), _as_date() (+48 more)

### Community 16 - "retrieve_scoped_news"
Cohesion: 0.04
Nodes (42): _lifespan(), _warmup_embeddings_background(), _run(), _pack_row(), _trim_snippet(), embed_query(), embed_query(), warmup_query_vectors() (+34 more)

### Community 17 - "holding_insights/run.py"
Cohesion: 0.17
Nodes (14): _articles_for_log(), _build_batch_outcome(), main(), _news_summary_block(), _persist_run_snapshot(), _process_stock(), run_batch(), _week_change_pct() (+6 more)

### Community 18 - "QueryLogger"
Cohesion: 0.08
Nodes (16): _retrieve_bullion_for_entities(), _collect_pulse_pool(), _fetch_one_macro_query(), run_market_pulse(), ParsedQuery, attach_query_log_meta(), clip_log_text(), find_query_log_file() (+8 more)

### Community 19 - "news_reader.py"
Cohesion: 0.10
Nodes (36): _article_context_for_interpret(), measured_facts_block(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority() (+28 more)

### Community 20 - "macro_data.py"
Cohesion: 0.21
Nodes (22): PortfolioComposeRequest, BondYieldResult, _client(), _codes(), walk(), CPIRecord, fetch_bond_yields(), fetch_cpi() (+14 more)

### Community 21 - "datetime"
Cohesion: 0.08
Nodes (35): _env_secrets(), prune_logs(), _redact(), _redact_text(), _rmtree(), RunArtifacts, _usage(), _append() (+27 more)

### Community 22 - "api.py"
Cohesion: 0.05
Nodes (77): _all_dates(), _bundle_is_live(), create_router(), daily(), dates(), generate(), health(), holding_insights_job_latest() (+69 more)

### Community 23 - "Settings"
Cohesion: 0.07
Nodes (36): _merge_publisher_error_reasons(), write_day_report(), _bucket(), _entity_names(), summarize_errors(), write_error_summary(), _atomic_write(), day_failure_slices_for_run() (+28 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.10
Nodes (45): build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+37 more)

### Community 25 - "test_equity_fund_week.py"
Cohesion: 0.23
Nodes (16): attribution_summary(), build_fund_facts(), cushion_funds(), _equity_holdings_from_detail(), _fmt_signed_pct(), _fund_return_1w_api(), FundFacts, holding_impact_1w() (+8 more)

### Community 26 - "test_fund_display_tables.py"
Cohesion: 0.08
Nodes (28): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), format_display_tables_markdown(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers(), strip_markdown_tables_from_prose(), _strip_overview_prose_block() (+20 more)

### Community 27 - "gather.py"
Cohesion: 0.06
Nodes (51): canonical_facet(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext (+43 more)

### Community 28 - "investor_drawback.py"
Cohesion: 0.08
Nodes (27): append_investor_portfolio_overview_tables(), _fund_performance_digest(), strip_unasked_scheme_names(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer(), question_wants_scheme_names(), _display_holding_row() (+19 more)

### Community 29 - "ExecutionPlan"
Cohesion: 0.04
Nodes (87): _use_rating_concept(), _compare_fund_count(), finalize_unnamed_catalog_compare(), _split_count(), ExecutionPlan, asked_slots(), merge_planner_asked_facts(), slots_from_plan() (+79 more)

### Community 30 - "market_driver_digest/run.py"
Cohesion: 0.08
Nodes (32): fmt_inr_crore(), fmt_pct(), ordinal(), MarketDriverFactsBase, normalize_market_draft(), persist_market_sections(), backtest(), build() (+24 more)

### Community 31 - "trends.py"
Cohesion: 0.13
Nodes (14): detect_signals(), _surge(), DayPoint, entity_daily_series(), price_trend(), price_trend_from_closes(), PriceTrend, session_day() (+6 more)

### Community 32 - "sources/google_news.py"
Cohesion: 0.07
Nodes (28): fetch_url(), article_id_from_url(), _batchexecute(), cached_resolve(), is_google_news_article_url(), _parse_garturlres(), resolve_google_news_url(), _connection() (+20 more)

### Community 33 - "task_exec.py"
Cohesion: 0.13
Nodes (29): _spaced_category_words(), bind_subjects(), _book_total_line(), _canon_fact(), _category_in_planner_text(), _cell(), _compare_subject_kind(), coverage_line() (+21 more)

### Community 34 - "llm_client.py"
Cohesion: 0.07
Nodes (56): ask(), ask_stream(), AskRequest, _attach_llm_meta(), fund_brief(), health(), get_settings(), anthropic_cache_control() (+48 more)

### Community 35 - "sector_query_for_label"
Cohesion: 0.14
Nodes (18): append_personal_tail(), _display_fund_name(), _fetch_fund_short_name(), format_fund_tail(), fund_isins_from_row(), _headline_ends_with_your(), holding_row_for_instrument(), personalize_card_headline() (+10 more)

### Community 36 - "fund_display.py"
Cohesion: 0.12
Nodes (27): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+19 more)

### Community 37 - "normalize.py"
Cohesion: 0.17
Nodes (22): aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values(), _book_has_market_value(), _drop_sold(), _fill_missing_from_live() (+14 more)

### Community 38 - "project_modules"
Cohesion: 0.09
Nodes (19): project_concentration(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore, normalized_doc() (+11 more)

### Community 39 - "plan.py"
Cohesion: 0.06
Nodes (36): explanation_brief(), field_prompt_table(), mentions_advice(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), _invalidate_plan_system_cache() (+28 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "time_ist.py"
Cohesion: 0.09
Nodes (29): notify_failure(), fmt_ist(), _resolve_end(), rolling_window(), session_window(), to_ist(), week_window(), _closed_dates() (+21 more)

### Community 42 - "article_quality.py"
Cohesion: 0.09
Nodes (31): filter_usable_articles(), _is_low_quality_article(), merge_article_pool(), rank_and_pick_articles(), score_article(), _stock_terms(), _title_mentions_stock(), _vector_strength() (+23 more)

### Community 43 - "plan_enforce.py"
Cohesion: 0.03
Nodes (108): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), asks_ideal_portfolio_shape(), fund_type_name_spec(), asks_category_performance(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan() (+100 more)

### Community 44 - "test_portfolio_startup_cache.py"
Cohesion: 0.17
Nodes (17): clear_cache_for_tests(), seed_portfolio_cache_for_tests(), set_active_crn(), test_concentration_question_loads_stock_and_sector_data(), test_executor_with_fixture(), test_repair_empty_investor_tool_calls(), test_switch_evicts_the_previous_crn(), fake() (+9 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "get_sector_fund_ranking_index"
Cohesion: 0.06
Nodes (44): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+36 more)

### Community 47 - "book_news_map.py"
Cohesion: 0.26
Nodes (11): _clean_holding_tokens(), book_wide_sectors(), _display_name(), _has_named_stock(), _news_name(), _pct(), resolve_book_sector(), sector_book() (+3 more)

### Community 48 - "entity_retrieval.py"
Cohesion: 0.12
Nodes (32): rank_clusters(), bellwether_holdings(), EntityPack, evidence_from_clusters(), fetch_entity_pack(), fetch_fii_dii(), fetch_macro_packs(), work() (+24 more)

### Community 49 - "fund_scheme_match.py"
Cohesion: 0.16
Nodes (15): is_quantum_amc_entry(), _category_phrases_in_question(), _constraint_in_scheme_name(), _distinctive_constraints(), scheme_match_score(), _scheme_matches_amc(), _scheme_name_tokens(), _scheme_vocab_tokens() (+7 more)

### Community 50 - "app.py"
Cohesion: 0.09
Nodes (41): holding_insights_page(), holding_insights_stock_log_page(), ask_memory(), ask_query_log(), ask_sources(), _attach_portfolio_to_ask(), backfill_page(), backfill_start() (+33 more)

### Community 51 - "gold_service.py"
Cohesion: 0.08
Nodes (28): _fetch(), get_gold_snapshot(), get_silver_snapshot(), gold_horizon_code(), gold_macro_series_row(), _load_payload(), _merged_series(), add() (+20 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "investor_subject.py"
Cohesion: 0.04
Nodes (84): amc_token_in_question(), question_amc_hints(), _amc_token_set(), question_is_standalone_macro(), _categories_equivalent(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope() (+76 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (20): build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns(), normalize_vs_benchmark_payload() (+12 more)

### Community 55 - "typing"
Cohesion: 0.09
Nodes (16): _events(), run_ask_engine(), stream_ask_engine(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), trim_news_grouped() (+8 more)

### Community 56 - "test_sector_leaderboard_run.py"
Cohesion: 0.14
Nodes (26): LlmJsonResult, LlmUsage, call(), DryRunHalt, _both_sides(), _cfg(), _ctx(), _echo() (+18 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "resolve_fund_for_query"
Cohesion: 0.11
Nodes (23): extract_top_sectors(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), resolve_fund_for_query(), resolve_fund_from_question(), _portfolio_for_fund_news() (+15 more)

### Community 59 - "executor.py"
Cohesion: 0.06
Nodes (41): _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _capability_cache_key(), _conversation_id(), _conversation_turn(), _one_fund(), _fill_returns_from_catalog() (+33 more)

### Community 60 - "node_compose"
Cohesion: 0.06
Nodes (54): asks_about_score_bands(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison(), asks_score_only() (+46 more)

### Community 61 - "slot_route"
Cohesion: 0.11
Nodes (23): execute_wave(), _asks_driver_sector_or_fund_impact(), slot_route(), asks_funds_holding_stock(), asks_funds_with_sector_exposure(), _clean_stock_capture(), stock_name_from_question(), test_crude_increase_compound_question_screens_negatively_affected_funds() (+15 more)

### Community 62 - "holding_stock_insights_store.py"
Cohesion: 0.21
Nodes (12): _articles(), build_holding_stock_insights_snapshot(), _cap(), _daily_path(), _insight_text(), _row_from_record(), save_holding_stock_insights(), _usage() (+4 more)

### Community 63 - "re"
Cohesion: 0.12
Nodes (16): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+8 more)

### Community 64 - "pytest"
Cohesion: 0.15
Nodes (20): _add_usage(), _default_call(), format_articles_block(), generate_json(), _invoke_with_retry(), LlmSchemaError, LlmUnavailable, _run_bounded() (+12 more)

### Community 65 - "fund_universe_agent.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "twelve_data_brent.py"
Cohesion: 0.18
Nodes (18): BrentSyncResult, _call_time_series(), fetch_day(), fetch_days(), history_path(), main(), _merge_rows(), _num() (+10 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.10
Nodes (22): _amc_hints_from_tokens(), candidates_block(), entity_candidates(), _holding_candidates(), _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known() (+14 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "embed.py"
Cohesion: 0.15
Nodes (9): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), embeddings_ready() (+1 more)

### Community 71 - "portfolio/cache.py"
Cohesion: 0.13
Nodes (19): _run_get_investor_portfolio(), _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), get_active_crn(), get_normalized_portfolio(), peek_derived() (+11 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.12
Nodes (21): fetch_stock_news(), _holding_rows(), news_for_movers(), _one_mover(), _scoped_rows(), _slim_article(), _article_mentions_holding(), build_holdings_market_snapshots() (+13 more)

### Community 73 - "fund_rating_screen.py"
Cohesion: 0.05
Nodes (55): categories_for(), metal_scheme_categories(), pickable_categories(), _add_category_comparison(), _allocation_mix_spec(), _amc_matches(), _amc_outside_label(), _amc_token() (+47 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "fields.py"
Cohesion: 0.06
Nodes (52): _asks_book(), bind_fields_to_tools(), _book_fields(), canonicalize_field(), field_need(), FieldNeed, fields_from_question(), _find_term() (+44 more)

### Community 77 - "sector_fund_ranking.py"
Cohesion: 0.06
Nodes (21): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors() (+13 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 79 - "rupeestop_auth.py"
Cohesion: 0.16
Nodes (19): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+11 more)

### Community 80 - "news_rag/config.py"
Cohesion: 0.11
Nodes (7): fetch_portfolio(), valid_crn(), fetch_top_holdings(), row_fund_isins(), main(), main(), main()

### Community 81 - "time"
Cohesion: 0.15
Nodes (25): _load_planner_memory(), _store_turn_memory(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), _fresh(), get_memory(), get_or_create(), reset_memory() (+17 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.12
Nodes (39): _age(), _allocation_bucket_rows(), _as_of(), _asks_portfolio_rs_ratings(), _book_line(), _category_amount_map(), _comparison_rows(), _composition_line() (+31 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 86 - "workspace.py"
Cohesion: 0.13
Nodes (10): main(), prune_insight_logs(), apply_fresh_start(), _clear_run_json_summaries(), clear_scrape_workspace(), remove_scrape_artifacts(), remove_scrape_artifacts_many(), url_artifact_stem() (+2 more)

### Community 87 - "sector_indices.py"
Cohesion: 0.17
Nodes (17): _bars(), catalog_path(), fetch_ohlc(), IndexSpec, load_catalog(), news_sectors_for_index(), OhlcBar, series_is_usable() (+9 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.14
Nodes (19): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+11 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 90 - "lib/portfolio_scope.py"
Cohesion: 0.17
Nodes (16): build_portfolio_scope(), FundRef, _holding_equity_allowed(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest(), load_portfolio_funds() (+8 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.06
Nodes (64): _add_category_comparison(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line(), _compare_cell(), _compare_header(), _complete_fund_row(), _complete_shown_funds() (+56 more)

### Community 96 - "validate_capability_args"
Cohesion: 0.12
Nodes (15): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded() (+7 more)

### Community 97 - "NumericRecord"
Cohesion: 0.12
Nodes (23): fetch_ask_market_records(), fetch_gold_record(), get_ask_market_snapshot(), NumericRecord, unavailable(), fetch_cpi_record(), pick(), fetch_fii_dii() (+15 more)

### Community 98 - "test_fact_answer.py"
Cohesion: 0.11
Nodes (26): EvidencePack, is_pure_field_answer(), render_benchmark_comparison_table(), render_fact_answer(), wants_comparison_table(), _drop_scheme_is_the_whole_book(), node_compose(), _plan() (+18 more)

### Community 99 - "qdrant_access.py"
Cohesion: 0.10
Nodes (32): is_stale(), newest_scraped_at(), _as_dict(), _client(), _drop(), _entity_view(), EntityRowsResult, _explode() (+24 more)

### Community 100 - "sector_exposure_tables.py"
Cohesion: 0.11
Nodes (24): owned_holding_names(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question(), validate_plan_tools(), _all_holdings_metric_spec() (+16 more)

### Community 102 - "portfolio/client.py"
Cohesion: 0.17
Nodes (12): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), InvalidCRN, PortfolioError, PortfolioNotConfigured, PortfolioUnavailable (+4 more)

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.11
Nodes (18): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_PIPELINE_DAILY (+10 more)

### Community 104 - "env"
Cohesion: 0.11
Nodes (18): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL (+10 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.18
Nodes (12): _rating_lead_for_pack(), asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score() (+4 more)

### Community 106 - "portfolio_news_impact.py"
Cohesion: 0.08
Nodes (36): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _rule_sector_picks(), canonical_direction_for_driver(), clear_macro_impact_cache() (+28 more)

### Community 107 - "market_pulse.py"
Cohesion: 0.06
Nodes (38): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), AskPlan, EntityMention, _int_list(), PlannedTool (+30 more)

### Community 108 - "_normalize_fund_text"
Cohesion: 0.12
Nodes (18): labels_name_the_same_scheme(), _attach_trailing_product(), build_holding_overlap(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _entry_matches_query_scheme() (+10 more)

### Community 109 - "fund_drawdown.py"
Cohesion: 0.19
Nodes (17): _add_drawdown_call(), attach_screen_drawdown(), average_peer_drawdown(), compare_drawdown_rows(), fetch_drawdown_periods(), fetch_trailing_drawdown(), load_fund_drawdown(), _money() (+9 more)

### Community 110 - "fund_match.py"
Cohesion: 0.15
Nodes (10): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), load_fund_embedding_cache(), _normalize_fund_text() (+2 more)

### Community 111 - "sources/universe.py"
Cohesion: 0.12
Nodes (24): _resolve_bellwether(), rank(), instrument_to_qdrant_names(), match_holding_to_corpus_entity(), resolve_allisin_holdings_path(), load_portfolio_universe(), _fund_stats_from_csv(), load_holdings_rows_from_xlsx() (+16 more)

### Community 112 - "slot_router.py"
Cohesion: 0.11
Nodes (18): rating_concept_plan(), asks_fund_category_average(), plan_matches_intent(), QuestionIntent, resolve_question_intent(), _top_n_from_question(), _asks_catalog_fund_performance(), _asks_fund_manager() (+10 more)

### Community 113 - "fund_rating_categories.py"
Cohesion: 0.14
Nodes (15): CategoryMatch, _close(), _metal_category(), _metal_flags(), _names_a_type(), _phrase_score(), rating_scope_pairs(), _rating_tokens() (+7 more)

### Community 114 - "insights.py"
Cohesion: 0.30
Nodes (10): build_insights(), _equity_pct(), Insight, insight_lines(), insights_for_brief(), _num(), _style_band(), _book() (+2 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "atomic_write_json"
Cohesion: 0.14
Nodes (13): atomic_write_json(), holding_data_dir(), _daily_path(), load_daily(), save_daily(), build_log_document(), load_stock_log(), _price_summary() (+5 more)

### Community 117 - "_run_get_fund_data"
Cohesion: 0.10
Nodes (17): fetch_public_rating(), headline_rating(), load_fund_risk(), rating_for_request(), rating_needs_pillars(), _isin_for_fund_name(), _repair_incomplete_fund_data(), _run_get_fund_data() (+9 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "macro_news_cache.py"
Cohesion: 0.11
Nodes (22): _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), select_macro_for_question() (+14 more)

### Community 121 - "new/run.py"
Cohesion: 0.25
Nodes (8): nav_1w_for_isin(), run_endpoint(), _prefetch_nav(), _process_one(), run_equity_fund_week(), attach_stock_whys(), explain_one_block(), _user_prompt()

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "macro_context.py"
Cohesion: 0.18
Nodes (19): _brent_horizons(), _brent_usd(), build_digest_datasets(), _closest_close_on_or_before(), _cpi_ytd(), _ddmmyyyy_to_iso(), _fii_dii_7d(), _gsec_7d() (+11 more)

### Community 124 - "news_digest.py"
Cohesion: 0.17
Nodes (12): primary_metal_in_question(), _fund_cap(), _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers() (+4 more)

### Community 125 - "normalize_rs_label"
Cohesion: 0.10
Nodes (26): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), infer_anchor_label_from_excludes() (+18 more)

### Community 126 - "run-pipeline"
Cohesion: 0.29
Nodes (6): jobs, run-pipeline, name, on, runs-on, timeout-minutes

### Community 127 - "update.py"
Cohesion: 0.12
Nodes (23): drop_old_turns(), compare_payload_matches_funds(), push_recent_fund_focus(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), append_chat_turn(), empty_frame() (+15 more)

### Community 128 - "common/store.py"
Cohesion: 0.10
Nodes (35): bundle_exists(), _check_id(), _dump(), exists(), _file(), _is_date(), latest(), list_dates() (+27 more)

### Community 129 - "graph.py"
Cohesion: 0.07
Nodes (32): drawdown_words(), _attach_conversation(), _catalog_fanout_fund_names(), _ensure_portfolio_for_fund_news(), _maybe_compare_funds_after_multi_screen(), _maybe_enrich_picked_fund_from_screen(), Node, node_bridge() (+24 more)

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

### Community 134 - "json"
Cohesion: 0.12
Nodes (19): _json_default(), safe_json_dumps(), fetch_fund(), load_done_isins(), load_isins(), main(), _pct(), run() (+11 more)

### Community 135 - "test_fund_drawdown.py"
Cohesion: 0.18
Nodes (23): asks_category_drawdown(), ensure_drawdown_tools(), is_drawdown_definition(), _named_standard_periods(), periods_for_question(), _plan(), test_category_drawdown_asks_for_the_peer_average(), test_comparison_keeps_compare_funds_and_drops_ten_year() (+15 more)

### Community 136 - "validate.py"
Cohesion: 0.19
Nodes (20): numeric_leaves(), walk(), _allowed_numbers(), _banned(), _blob(), walk(), _body(), CheckResult (+12 more)

### Community 137 - "inputs"
Cohesion: 0.40
Nodes (5): default, description, required, type, holdings_limit

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

### Community 141 - "price.py"
Cohesion: 0.17
Nodes (6): history_closes(), latest_quote(), _consecutive_down_days(), DayBar, get_price_snapshot(), test_consecutive_down_days()

### Community 142 - "test_news_only_answer.py"
Cohesion: 0.20
Nodes (7): clean_news_insight(), complete_sentences(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words(), test_news_insight_drops_publisher_clips_and_unrelated_articles()

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

### Community 146 - "test_investor_grounding.py"
Cohesion: 0.22
Nodes (11): repair_investor_insight_prose(), strip_grounding_holes(), derived_cores(), investor_book_cores(), _sample_book(), test_grounding_keeps_category_weight_in_prose(), test_investor_book_cores_includes_pnl_term_gains(), test_investor_book_cores_includes_rounded_allocation_pct() (+3 more)

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

### Community 159 - "threading"
Cohesion: 0.06
Nodes (29): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), _fetch_http_get() (+21 more)

### Community 163 - "test_sector_leaderboard_score.py"
Cohesion: 0.17
Nodes (18): llm_schema(), prominence(), rank(), score_sector(), score_stories(), trim_text(), _cluster(), _row() (+10 more)

### Community 169 - "nse_fii_dii.py"
Cohesion: 0.19
Nodes (13): current_artifacts(), log_external(), FlowLeg, _bucket(), fetch_fii_dii_snapshot(), _httpx_json(), _impit_json(), _leg() (+5 more)

### Community 170 - "GraphState"
Cohesion: 0.15
Nodes (15): build_result(), _conversation_id(), GraphState, _insight_headline_narrative(), node_reply(), node_wave2(), run_graph(), run_graph_pipeline() (+7 more)

### Community 174 - "Any"
Cohesion: 0.17
Nodes (15): _clean_company_name(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers(), _fund_text(), _named_weights(), _normalize_manager_record(), _optional_number() (+7 more)

### Community 178 - "graph.py"
Cohesion: 0.12
Nodes (17): LLMUsageRecord, PhaseRecord, RequestTelemetry, ToolRecord, _answer_stream_chunks(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta() (+9 more)

### Community 180 - "news.py"
Cohesion: 0.18
Nodes (11): _fetch_rows(), get_top_news(), news_window(), NewsArticle, NewsBundle, _published_in_window(), _rows_to_articles(), sort_key() (+3 more)

### Community 181 - "test_metal_fund_rating.py"
Cohesion: 0.27
Nodes (8): ensure_quality_fund_list(), _payload(), _rating(), test_gold_list_spreads_etf_and_fund_of_funds(), fetch(), test_my_gold_fund_does_not_add_category_screen(), test_named_gold_etf_is_not_a_category_list(), test_planner_gold_sector_screen_becomes_rating_list()

### Community 182 - "portfolio_insights.js"
Cohesion: 0.42
Nodes (9): api(), card(), chipHtml(), esc(), headers(), loadReady(), renderCompose(), renderReady() (+1 more)

### Community 183 - "fund_catalog.py"
Cohesion: 0.13
Nodes (20): _detect_funds(), all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog() (+12 more)

### Community 184 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 185 - "strip_missing_data_caveats"
Cohesion: 0.17
Nodes (9): strip_missing_data_caveats(), test_a_rating_pick_does_not_apologise_for_returns_or_pillars(), test_strip_removes_risk_trend_apology(), test_a_holding_outside_the_top_five_still_gets_weight_and_sector(), test_a_top_five_apology_is_removed(), test_each_holding_keeps_the_article_text_not_only_one_headline(), test_grouped_news_keeps_the_article_body(), test_overview_fund_facts_are_a_short_table() (+1 more)

### Community 186 - "nav_service.py"
Cohesion: 0.20
Nodes (12): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+4 more)

### Community 187 - ".lookup_extracted_fund"
Cohesion: 0.10
Nodes (8): detail_has_live_facts(), _expand_query_token(), FundIndex, get_fund_benchmark(), _infer_category_and_type(), resolve_canonical_isin(), _sync_amc_prefix_from_catalog(), _detail_for_fund_tool()

### Community 188 - "typing"
Cohesion: 0.05
Nodes (48): enforce_prompt_budget(), EvidenceArticle, format_evidence_block(), assemble_body(), beats_from_draft(), build_user_prompt(), compact_facts(), _compact_news_map() (+40 more)

### Community 190 - "security_master.py"
Cohesion: 0.35
Nodes (8): _load_index(), load_master_index(), lookup_instrument(), lookup_master(), normalize_name(), _pick_best_master(), resolve_yf_ticker(), test_master_lookup()

### Community 191 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 193 - "infer_fund_news_layers"
Cohesion: 0.18
Nodes (9): infer_fund_news_layers(), prefers_planner_over_slot(), asks_fund_related_news(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only(), test_overview_news_is_holdings_and_sectors() (+1 more)

### Community 194 - "csv"
Cohesion: 0.15
Nodes (8): multi_query_for(), _strip_legal_suffix(), short_name(), main(), main(), load_top_holdings(), main(), test_get_stock_profile_includes_one_year_return()

### Community 195 - "HoldingInsightsJobManager"
Cohesion: 0.17
Nodes (6): HoldingInsightsJobManager, on_progress(), HoldingJobBusy, HoldingJobView, _write(), report()

### Community 197 - "brief.py"
Cohesion: 0.07
Nodes (37): asks_random_fund_compare(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief(), _detect_direction(), _detect_funds(), _heuristic_brief() (+29 more)

### Community 198 - "283041/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 199 - "render_drawdown_body"
Cohesion: 0.19
Nodes (14): collapse_episodes(), investment_amount(), _period_heading(), render_drawdown_body(), _rupee_line(), rupee_loss(), _open_episode(), _recovered_episode() (+6 more)

### Community 203 - "fund_brief.py"
Cohesion: 0.10
Nodes (30): Settings, _article_entities(), build_events(), cluster_articles(), _cluster_entities(), compose_fund_insight(), _day_key(), _empty_brief() (+22 more)

### Community 206 - "test_ai_insight.py"
Cohesion: 0.18
Nodes (6): digest_filter(), _holding_mentioned(), matches_entity(), contains_phrase(), test_digest_filter_uses_stricter_scores(), test_sector_exclude_drops_nbfc_from_banks()

### Community 208 - "Envelope"
Cohesion: 0.06
Nodes (56): build(), compose(), _cards(), main(), _build(), _user(), Signal, news_map_block() (+48 more)

### Community 209 - "57e233/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 211 - "test_return_windows.py"
Cohesion: 0.17
Nodes (15): _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows(), window_label() (+7 more)

### Community 212 - "c72b25/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 213 - "a45664/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 214 - "compare_evidence.py"
Cohesion: 0.24
Nodes (8): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_maybe_run_compare_retries_after_failed_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 217 - "7859f0/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 218 - "test_greeting.py"
Cohesion: 0.15
Nodes (13): greeting_reply(), identity_reply(), _mirror_greeting(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens() (+5 more)

### Community 219 - "contracts.py"
Cohesion: 0.04
Nodes (81): rating_list_plan(), news_calls_for_book(), _sector_call(), _stock_call(), ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results() (+73 more)

### Community 220 - "aggregate_fund_holdings.py"
Cohesion: 0.20
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 221 - "clarify_plan_if_fund_unknown"
Cohesion: 0.09
Nodes (24): question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), question_wants_gold_table(), facts_only_compose_allowed(), clarify_plan_if_fund_unknown(), _plan_uses_fund_scoped_tools(), scrub_unknown_fund_mentions() (+16 more)

### Community 222 - "index_series.py"
Cohesion: 0.25
Nodes (10): nifty50_ticker(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns(), _read_cache(), scheme_benchmark_metadata(), _write_cache() (+2 more)

### Community 223 - "test_call_json_llm.py"
Cohesion: 0.32
Nodes (11): _layered_news_topics(), _client(), _gemini_response(), _settings(), test_agent_keeps_truncated_tools_without_repair(), test_composer_keeps_truncated_answer_without_a_second_call(), test_gemini_request_includes_response_schema(), test_judge_truncated_json_does_not_repair() (+3 more)

### Community 224 - "Cluster"
Cohesion: 0.10
Nodes (32): _adapter(), Cluster, cluster_rows(), cluster_score(), _collapse(), _dedupe(), find(), union() (+24 more)

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
Nodes (29): Publisher, SectorQuery, Settings, is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), fetch_entity_items() (+21 more)

### Community 230 - "test_admin_headers_use_token_from_login"
Cohesion: 0.13
Nodes (4): _jwt(), test_admin_headers_use_token_from_login(), test_failed_login_keeps_previous_token(), test_valid_jwt_does_not_call_login()

### Community 231 - "test_guardrails_domain.py"
Cohesion: 0.20
Nodes (11): question_in_finance_scope(), check_guardrails(), financial_keyword_signal(), GuardrailResult, test_crude_why_not_misrouted_to_random_fund(), test_fund_question_still_passes(), test_hdfc_bank_passes_guardrails(), test_hdfc_bank_short_happening_passes() (+3 more)

### Community 232 - "data_pack.py"
Cohesion: 0.38
Nodes (3): build_data_pack(), build(), _compact()

### Community 233 - "router.py"
Cohesion: 0.16
Nodes (5): portfolio_insights_page(), equity_fund_week_page(), create_equity_fund_week_router(), page(), EquityFundWeekRequest

### Community 236 - "repo_root"
Cohesion: 0.19
Nodes (11): write_ask_market_snapshot(), FiiDiiSnapshot, _cache_dir(), write_snapshot(), main(), write_fii_dii(), write_latest(), _api_key() (+3 more)

### Community 237 - "holding_insights/llm.py"
Cohesion: 0.13
Nodes (23): llm_allow_fallback(), _as_paragraph(), call_holding_llm(), _call(), _headline_week_matches(), _normalize_response(), parse_insight_lines(), _pct_in_text() (+15 more)

### Community 238 - "app.js"
Cohesion: 0.39
Nodes (10): attributionBlock(), esc(), fundCard(), impactTable(), newsRefs(), newsWithCoverage(), paragraphSection(), pctClass() (+2 more)

### Community 239 - "glossary.py"
Cohesion: 0.26
Nodes (10): asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), glossary_execution_plan(), meaning_reply(), _normalize_term(), test_fund_nav_not_glossary(), test_nav_full_form_direct_reply() (+2 more)

### Community 240 - "run_insights_daily.sh"
Cohesion: 0.50
Nodes (4): note(), PYTHONPATH, PYTHONUNBUFFERED, run_insights_daily.sh script

### Community 241 - "build_top100_holdings.py"
Cohesion: 0.38
Nodes (7): check_yfinance(), load_master_index(), lookup_master(), main(), normalize_name(), pick_best_master(), resolve_yf_ticker()

### Community 252 - "test_ai_insight_mospi.py"
Cohesion: 0.25
Nodes (10): _client(), _sse(), test_400_is_not_retried(), test_gdp_yoy_uses_prior_fiscal_year(), handler(), test_retries_500_then_reads_cache(), handler(), test_snapshot_keeps_other_entities_when_one_fails() (+2 more)

### Community 253 - "test_composer_table_summaries.py"
Cohesion: 0.24
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_parse_tables_append_directive(), test_strip_empty_bold_sections(), test_summarize_tables_for_composer_extracts_mix_and_holdings()

### Community 254 - "test_fund_rating_screen.py"
Cohesion: 0.07
Nodes (54): asks_taxonomy(), match_all_fund_types(), asks_rating_list(), fund_naming_clause(), _looks_like_fund_list(), parse_rating_screen(), rating_screen_question(), _return_direction() (+46 more)

### Community 255 - "eval_planner.py"
Cohesion: 0.24
Nodes (4): check(), main(), run_case(), _Usage

### Community 257 - "pick_evidence"
Cohesion: 0.25
Nodes (7): _float(), _int(), pick_evidence(), story_weight(), _representative(), test_pick_evidence_keeps_top_by_weight(), test_story_weight_matches_the_hand_calculation()

### Community 260 - "holding_insights_stock_log.js"
Cohesion: 0.60
Nodes (5): api(), escapeHtml(), headers(), load(), render()

### Community 261 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 268 - "JobManager"
Cohesion: 0.14
Nodes (7): JobProgress, _write(), JobBusy, JobManager, JobView, _write(), test_job_isolates_one_failure()

### Community 270 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 273 - "MospiError"
Cohesion: 0.21
Nodes (5): MospiClient, MospiError, _payload(), _sse_json(), _unhandled_exception_handler()

### Community 274 - "top_n_from_question"
Cohesion: 0.31
Nodes (6): _get_top_n(), top_n_from_question(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

### Community 275 - "normalize_user_facing_text"
Cohesion: 0.22
Nodes (6): ensure_markdown_table_spacing(), normalize_user_facing_text(), strip_context_disclaimer(), _clean_answer(), test_normalize_inserts_blank_line_before_markdown_table(), test_normalize_na_to_hyphen()

### Community 276 - "nav_settled.py"
Cohesion: 0.48
Nodes (3): nav_change_1w_settled(), settled_nav_records(), test_settled_nav_drops_today()

### Community 277 - "load_equity_holdings"
Cohesion: 0.33
Nodes (4): _is_equity(), load_equity_holdings(), fund_type_for_category(), test_equity_filter_from_workspace()

### Community 278 - "question_is_pure_general_concept"
Cohesion: 0.44
Nodes (6): apply_pure_concept_plan(), question_is_pure_general_concept(), test_all_holdings_metrics_adds_investor_tool(), test_large_cap_vs_mid_cap_is_pure_concept(), test_my_funds_is_not_pure_concept(), test_named_large_cap_scheme_keeps_tools()

### Community 279 - "compose_llm.py"
Cohesion: 0.46
Nodes (5): compose_fund_narrative(), _paragraph_entry(), _usable_block(), _short_name(), test_compose_structured_narrative()

## Knowledge Gaps
- **26 isolated node(s):** `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT` (+21 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2046 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **62 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `graph.py`, `plan_enforce.py`, `build_evidence_pack`, `test_fund_drawdown.py`, `display_table_policy.py`, `test_news_only_answer.py`, `tools.py`, `macro_data.py`, `question_is_pure_general_concept`, `investor_drawback.py`, `task_exec.py`, `fund_display.py`, `project_modules`, `plan.py`, `GraphState`, `plan_enforce.py`, `test_portfolio_startup_cache.py`, `get_sector_fund_ranking_index`, `book_news_map.py`, `gold_service.py`, `investor_subject.py`, `test_metal_fund_rating.py`, `node_compose`, `slot_route`, `brief.py`, `fund_rating_screen.py`, `fields.py`, `time`, `fact_answer.py`, `test_return_windows.py`, `compare_evidence.py`, `test_portfolio_allocation.py`, `contracts.py`, `clarify_plan_if_fund_unknown`, `evidence_pack.py`, `test_fact_answer.py`, `sector_exposure_tables.py`, `glossary.py`, `slot_router.py`, `_run_get_fund_data`, `test_composer_table_summaries.py`, `test_fund_rating_screen.py`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `ExecutionPlan` (e.g. with `news_calls_for_book()` and `sector_book()`) actually correct?**
  _`ExecutionPlan` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN` to the rest of the system?**
  _26 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.06663205261336103 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `contracts.py` to `graph.py`, `plan_enforce.py`, `execute_capability`, `build_evidence_pack`, `test_fund_drawdown.py`, `execute_capability`, `display_table_policy.py`, `test_news_only_answer.py`, `tools.py`, `macro_data.py`, `question_is_pure_general_concept`, `ExecutionPlan`, `task_exec.py`, `project_modules`, `plan.py`, `GraphState`, `plan_enforce.py`, `test_portfolio_startup_cache.py`, `get_sector_fund_ranking_index`, `book_news_map.py`, `gold_service.py`, `test_metal_fund_rating.py`, `investor_subject.py`, `executor.py`, `node_compose`, `slot_route`, `brief.py`, `fund_rating_screen.py`, `fields.py`, `time`, `test_return_windows.py`, `compare_evidence.py`, `test_portfolio_allocation.py`, `clarify_plan_if_fund_unknown`, `evidence_pack.py`, `sector_exposure_tables.py`, `fund_drawdown.py`, `slot_router.py`, `test_fund_rating_screen.py`, `update.py`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ToolCall` (e.g. with `news_calls_for_book()` and `_apply_planner_request()`) actually correct?**
  _`ToolCall` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `execute_capability` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._