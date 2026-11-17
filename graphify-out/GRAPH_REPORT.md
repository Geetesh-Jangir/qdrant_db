# Graph Report - db_design_with_qdrant_locally  (2026-11-17)

## Corpus Check
- 654 files · ~967,207 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 24 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 3)

## Summary
- 6887 nodes · 22344 edges · 260 communities (204 shown, 56 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 746 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4fa84378`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- sources/google_news.py
- fund_rating_screen.py
- interpret.py
- load_config
- market_driver_digest/run.py
- portfolio_news_impact.py
- node_compose
- grounding.py
- Settings
- test_insight_graph.py
- update.py
- Envelope
- compute.py
- v2_scoring.py
- tools.py
- parse.py
- test_fund_name_gate_and_hydrate.py
- QueryLogger
- news_reader.py
- macro_data.py
- runner.py
- project_modules
- main.py
- tool_runners.py
- sector_leaderboard/run.py
- fund_display.py
- gather.py
- pack_sanitize.py
- plan_enforce.py
- nse_fii_dii.py
- test_two_wave_pipeline.py
- Settings
- task_exec.py
- llm_client.py
- JobManager
- Any
- normalize.py
- insight/portfolio_scope.py
- planner_policy.py
- env
- normalize_rs_label
- article_quality.py
- plan.py
- macro_news_cache.py
- env
- sector_alignment.py
- book_news_map.py
- ExecutionPlan
- fund_catalog.py
- app.py
- gold_service.py
- env
- investor_subject.py
- fund_rupeestop_metrics.py
- AnswerMode
- test_sector_leaderboard_run.py
- scrape-worker/package.json
- resolve_fund_for_query
- executor.py
- test_fund_risk.py
- graph.py
- typing
- re
- nav_service.py
- fund_universe_agent.py
- batch.ts
- CapabilityCache
- insight/guardrails.py
- http-fetch.ts
- embed.py
- portfolio/cache.py
- holdings_market.py
- fund_portfolio_news.py
- with
- additional_insights/run.py
- screen_hints_from_question
- stock_fund_ranking.py
- get_settings
- clarify_plan_if_fund_unknown
- validate.py
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- get_sector_fund_ranking_index
- test_ai_insight_quality.py
- plan_enforce.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- test_metal_fund_rating.py
- node_route
- env
- steps
- evidence_pack.py
- test_news_only_answer.py
- NumericRecord
- question_intent.py
- clustering.py
- shared_system_prefix
- MospiClient
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- slot_route
- parse_rating_screen
- fund_rating_categories.py
- return_windows.py
- lib/portfolio_scope.py
- test_investor_grounding.py
- entity_retrieval.py
- news_digest.py
- insights.py
- vitest
- format_inr
- universe.py
- compilerOptions
- compilerOptions
- macro_news_cache.py
- workspace.py
- backfill
- stitch_display_tables_into_answer
- prompts.py
- memory/evidence.py
- run-pipeline
- ToolCall
- qdrant_access.py
- layer_tools.py
- worker/src/index.ts
- steps
- steps
- with
- aggregate_fund_holdings.py
- test_greeting.py
- fields.py
- inputs
- with
- inputs
- fund_scheme_match.py
- explicit_fund_count
- test_fund_drawdown.py
- run-backfill.sh
- qdrant
- canonical_key
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
- RunLogger
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- portfolio_bind.py
- sector_exposure_tables.py
- diagnose_lightsail_site.sh
- asks_computed_illustration
- validate_capability_args
- EntityFunnel
- Cluster
- test_ai_insight_common_qdrant_access.py
- test_call_json_llm.py
- repo_root
- portfolio_plan.py
- insight_links.py
- lib/google_news.py
- json
- fact_slots.py
- ScopeKind
- build_derived_views
- metals_spot_tables.py
- fund_search.py
- ._ensure_loaded
- compare_evidence.py
- QuestionBrief
- 283041/manifest.json
- fund_brief.py
- test_ai_insight.py
- datetime
- 57e233/manifest.json
- fund_type_name_spec
- c72b25/manifest.json
- a45664/manifest.json
- test_composer_table_summaries.py
- 7859f0/manifest.json
- glossary.py
- test_answer_precision.py
- test_screen_facts.py
- NumericRecord
- test_ai_insight_common_market.py
- run_ask_engine
- insights.js
- insight_log.js
- synthesize_tasks
- assemble_fund_overview_answer
- test_screen_rating_screen_arg.py
- test_entity_retrieval.py
- rank_funds_by_sector_exposure
- planner_catalog_knowledge.py
- PublisherStats
- normalize_user_facing_text
- _fund_performance_digest
- portfolio_universe.py
- _public_pillars
- csv
- run_insights_daily.sh
- data_pack.py
- install-insights-cron.sh
- health.py
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- LLMUsageRecord
- test_rupeestop_auth.py
- PhaseRecord
- ToolRecord

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 607 edges
2. `ToolCall` - 367 edges
3. `get_settings()` - 143 edges
4. `apply_planner_post_hooks()` - 123 edges
5. `AnswerMode` - 108 edges
6. `node_compose()` - 102 edges
7. `QueryLogger` - 100 edges
8. `Settings` - 94 edges
9. `load_config()` - 90 edges
10. `QuestionBrief` - 88 edges

## Surprising Connections (you probably didn't know these)
- `_qdrant_holding_names()` --uses--> `Settings`  [INFERRED]
  ai_insight/common/entity_retrieval.py → news_pipeline/config.py
- `TestGoogleNewsFetch` --uses--> `Settings`  [INFERRED]
  tests/test_google_news_fetch.py → news_pipeline/config.py
- `test_story_weight_matches_the_hand_calculation()` --calls--> `story_weight()`  [INFERRED]
  tests/test_sector_leaderboard_score.py → ai_insight/common/evidence.py
- `jev_filter_events()` --uses--> `JevError`  [INFERRED]
  news_rag/fund_brief.py → news_pipeline/jev/client.py
- `test_400_is_not_retried()` --uses--> `MospiError`  [INFERRED]
  tests/test_ai_insight_mospi.py → ai_insight/data/macro_data.py

## Import Cycles
- 2-file cycle: `ai_insight/common/entity_retrieval.py -> ai_insight/common/retrieval_plan.py -> ai_insight/common/entity_retrieval.py`

## Communities (260 total, 56 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (49): get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate() (+41 more)

### Community 1 - "sources/google_news.py"
Cohesion: 0.21
Nodes (12): is_google_exhausted(), _fetch_query_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url(), canonical_url(), host_matches(), host_of() (+4 more)

### Community 2 - "fund_rating_screen.py"
Cohesion: 0.08
Nodes (39): categories_for(), _add_category_comparison(), _allocation_mix_spec(), _amc_matches(), _amc_outside_label(), _amc_token(), _apply_category_difference(), asks_balanced_long_horizon_fund_menu() (+31 more)

### Community 3 - "interpret.py"
Cohesion: 0.07
Nodes (61): Findings, FundFinding, SectorFinding, mentions_publication_date(), publication_date_keys(), _assemble(), _caveat(), check_composer_guardrails() (+53 more)

### Community 4 - "load_config"
Cohesion: 0.05
Nodes (66): CommonConfig, load_config(), editorial_context(), market_numbers(), news_map_block(), cumulative(), FlowDay, history_path() (+58 more)

### Community 5 - "market_driver_digest/run.py"
Cohesion: 0.05
Nodes (59): fmt_inr_crore(), fmt_pct(), ordinal(), fetch_section(), _fetch_section_broad(), _parse(), plan_window(), MarketDriverFactsBase (+51 more)

### Community 6 - "portfolio_news_impact.py"
Cohesion: 0.08
Nodes (29): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _rule_sector_picks() (+21 more)

### Community 7 - "node_compose"
Cohesion: 0.07
Nodes (35): EvidencePack, _asks_portfolio_rs_ratings(), field_answer_needs_composer(), _investor_holdings_rows(), is_pure_field_answer(), render_benchmark_comparison_table(), render_fact_answer(), render_investor_rs_ratings_table() (+27 more)

### Community 8 - "grounding.py"
Cohesion: 0.10
Nodes (24): collect_evidence_calendar_dates(), add_article(), cores_in_text(), finalize_text_fields(), format_user_calendar_date(), number_is_grounded(), numeric_core(), _ordinal_day() (+16 more)

### Community 9 - "Settings"
Cohesion: 0.08
Nodes (34): _subprocess(), _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), article_in_fetch_window(), google_time_query(), has_news_date_range() (+26 more)

### Community 10 - "test_insight_graph.py"
Cohesion: 0.16
Nodes (12): build_result(), _insight_headline_narrative(), node_resolve(), run_graph(), run_graph_pipeline(), _state(), test_lookup_route_skips_news_and_sends_no_identifiers_to_the_writer(), test_out_of_scope_question_ends_after_the_planner() (+4 more)

### Community 11 - "update.py"
Cohesion: 0.11
Nodes (23): drop_old_turns(), compare_payload_matches_funds(), push_recent_fund_focus(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), empty_frame(), empty_state() (+15 more)

### Community 12 - "Envelope"
Cohesion: 0.05
Nodes (85): compose(), _all_dates(), _bundle_is_live(), create_router(), daily(), dates(), generate(), health() (+77 more)

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (50): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+42 more)

### Community 14 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 15 - "tools.py"
Cohesion: 0.05
Nodes (61): get_fund_index(), _add(), run_driver_affected_funds_adapter(), DataNeed, rank_funds_by_sector_exposure(), _active_sector_equity(), _articles_for_affected_question(), _as_date() (+53 more)

### Community 16 - "parse.py"
Cohesion: 0.05
Nodes (27): _warmup_embeddings_background(), _run(), _pack_row(), _trim_snippet(), embed_query(), embed_query(), embeddings_ready(), warmup_query_vectors() (+19 more)

### Community 17 - "test_fund_name_gate_and_hydrate.py"
Cohesion: 0.13
Nodes (32): _conversation_id(), GraphState, _load_planner_memory(), _store_turn_memory(), drain_cache_events(), note_cache(), hydrate_memory_from_prior_turns(), normalize_prior_turns() (+24 more)

### Community 18 - "QueryLogger"
Cohesion: 0.10
Nodes (11): _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), jev_filter_events(), slots_from_plan(), clip_log_text(), _kv(), QueryLogger (+3 more)

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (38): _article_context_for_interpret(), measured_facts_block(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority() (+30 more)

### Community 20 - "macro_data.py"
Cohesion: 0.13
Nodes (32): BondYieldResult, _client(), _codes(), walk(), CPIRecord, fetch_bond_yields(), fetch_cpi(), fetch_gdp() (+24 more)

### Community 21 - "runner.py"
Cohesion: 0.08
Nodes (37): _env_secrets(), prune_logs(), _redact(), _redact_text(), _rmtree(), RunArtifacts, _usage(), _append() (+29 more)

### Community 22 - "project_modules"
Cohesion: 0.07
Nodes (28): _run_get_investor_portfolio(), question_wants_invested_value_table(), get_active_crn(), peek_portfolio(), fetch_top_holdings(), project_concentration(), _drop_sold(), match_scheme_filter() (+20 more)

### Community 23 - "main.py"
Cohesion: 0.08
Nodes (36): _merge_publisher_error_reasons(), write_day_report(), _bucket(), _entity_names(), summarize_errors(), write_error_summary(), _atomic_write(), day_failure_slices_for_run() (+28 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.10
Nodes (45): build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+37 more)

### Community 25 - "sector_leaderboard/run.py"
Cohesion: 0.06
Nodes (81): sector_label(), scrub_refusal_prose(), split_sentences(), SectorLeaderboardFactsBase, _block(), build_user(), _abs_scores(), backtest() (+73 more)

### Community 26 - "fund_display.py"
Cohesion: 0.10
Nodes (28): _as_float(), _assess_table_quality(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct(), _fmt_pp() (+20 more)

### Community 27 - "gather.py"
Cohesion: 0.06
Nodes (52): _brief_system(), canonical_facet(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence() (+44 more)

### Community 28 - "pack_sanitize.py"
Cohesion: 0.13
Nodes (21): attach_drawback_digest(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer(), _display_holding_row(), _enrich_investor_computed_fields(), _internal_contribution_row(), investor_holdings_for_display() (+13 more)

### Community 29 - "plan_enforce.py"
Cohesion: 0.06
Nodes (52): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), asks_category_performance(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), asks_cross_category_compare() (+44 more)

### Community 30 - "nse_fii_dii.py"
Cohesion: 0.21
Nodes (12): current_artifacts(), log_external(), _bucket(), fetch_fii_dii_snapshot(), _httpx_json(), _impit_json(), _leg(), _log_external() (+4 more)

### Community 31 - "test_two_wave_pipeline.py"
Cohesion: 0.07
Nodes (20): ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified() (+12 more)

### Community 32 - "Settings"
Cohesion: 0.05
Nodes (30): Publisher, SectorQuery, Settings, is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), finish_run_logger() (+22 more)

### Community 33 - "task_exec.py"
Cohesion: 0.19
Nodes (21): bind_subjects(), _book_total_line(), _cell(), coverage_line(), _fact_label(), _fmt(), _funds_from_pack(), _holding_for_category() (+13 more)

### Community 34 - "llm_client.py"
Cohesion: 0.07
Nodes (55): ask(), ask_stream(), health(), get_settings(), make_plan(), anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts() (+47 more)

### Community 35 - "JobManager"
Cohesion: 0.17
Nodes (6): JobProgress, _write(), JobBusy, JobManager, JobView, _write()

### Community 36 - "Any"
Cohesion: 0.12
Nodes (18): headline_rating(), _clean_company_name(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers(), _fund_text(), _named_weights(), _normalize_manager_record() (+10 more)

### Community 37 - "normalize.py"
Cohesion: 0.17
Nodes (22): aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values(), _book_has_market_value(), _fill_missing_from_live(), _first() (+14 more)

### Community 38 - "insight/portfolio_scope.py"
Cohesion: 0.11
Nodes (30): build_drawdown_wave2_calls(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), question_asks_portfolio_level_drawdown(), plan_targets_single_fund_measured_return(), _data_need_is_investor(), enforce_portfolio_scope() (+22 more)

### Community 39 - "planner_policy.py"
Cohesion: 0.09
Nodes (23): sector_focus_from_market(), _invalidate_plan_system_cache(), apply_now_window(), drop_unasked_fund_modules(), finalize_planner_plan(), narrow_deictic_follow_up(), question_uses_now_window(), trim_named_fund_overview() (+15 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "normalize_rs_label"
Cohesion: 0.09
Nodes (28): pickable_categories(), is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded() (+20 more)

### Community 42 - "article_quality.py"
Cohesion: 0.10
Nodes (23): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+15 more)

### Community 43 - "plan.py"
Cohesion: 0.13
Nodes (19): canonicalize_field(), field_prompt_table(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), _label_for_days(), _news_mode() (+11 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.21
Nodes (10): select_macro_for_question(), _digest(), test_cache_searches_named_macro_parameters(), test_failed_refresh_keeps_the_previous_cache(), test_macro_news_is_reused_for_two_hours_then_overwritten(), fetch(), test_question_gets_two_articles_from_each_leading_section(), test_seven_day_question_uses_the_seven_day_cache() (+2 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "sector_alignment.py"
Cohesion: 0.12
Nodes (22): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), extract_top_sectors(), analyze_sector_block(), canonical_sector_for_holding() (+14 more)

### Community 47 - "book_news_map.py"
Cohesion: 0.21
Nodes (14): book_wide_sectors(), _display_name(), _has_named_stock(), news_calls_for_book(), _news_name(), _pct(), resolve_book_sector(), sector_book() (+6 more)

### Community 48 - "ExecutionPlan"
Cohesion: 0.06
Nodes (58): ExecutionPlan, _attach_rs_ratings_to_screen(), question_asks_all_schemes_in_answer(), question_wants_scheme_names(), owned_holding_names(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings() (+50 more)

### Community 49 - "fund_catalog.py"
Cohesion: 0.15
Nodes (19): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+11 more)

### Community 50 - "app.py"
Cohesion: 0.06
Nodes (49): ask_memory(), ask_query_log(), ask_sources(), AskRequest, _attach_llm_meta(), _attach_portfolio_to_ask(), backfill_page(), backfill_start() (+41 more)

### Community 51 - "gold_service.py"
Cohesion: 0.08
Nodes (23): get_ask_market_snapshot(), _fetch(), get_gold_snapshot(), get_silver_snapshot(), gold_horizon_code(), gold_macro_series_row(), _load_payload(), _merged_series() (+15 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "investor_subject.py"
Cohesion: 0.03
Nodes (106): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), _bound_fund_name(), _compare_sides_resolvable(), _known_names_in_text(), question_refers_deictic_fund_safe(), single_fund_for_deictic(), _resolve_funds() (+98 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (20): build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), normalize_category_average_returns(), normalize_vs_benchmark_payload(), _optional_number() (+12 more)

### Community 55 - "AnswerMode"
Cohesion: 0.10
Nodes (28): rating_list_plan(), rating_concept_plan(), AnswerMode, QueryClass, Wave2Policy, align_planned_news_execution(), _ensure_sector_overview(), _get_top_n() (+20 more)

### Community 56 - "test_sector_leaderboard_run.py"
Cohesion: 0.08
Nodes (46): _add_usage(), _default_call(), format_articles_block(), generate_json(), _invoke_with_retry(), LlmJsonResult, LlmSchemaError, LlmUnavailable (+38 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "resolve_fund_for_query"
Cohesion: 0.10
Nodes (25): _attach_trailing_product(), extract_fund_phrase_from_question(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), resolve_fund_for_query(), resolve_fund_from_question() (+17 more)

### Community 59 - "executor.py"
Cohesion: 0.05
Nodes (45): merge_fund_insight_metrics(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _capability_cache_key(), _conversation_id(), _conversation_turn(), _detail_for_fund_tool() (+37 more)

### Community 60 - "test_fund_risk.py"
Cohesion: 0.05
Nodes (53): asks_about_score_bands(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison(), asks_score_only() (+45 more)

### Community 61 - "graph.py"
Cohesion: 0.07
Nodes (33): refetch_partial_fund_tools(), RequestTelemetry, facts_only_compose_allowed(), _answer_stream_chunks(), _attach_conversation(), _catalog_fanout_fund_names(), _drop_scheme_is_the_whole_book(), _ensure_portfolio_for_fund_news() (+25 more)

### Community 62 - "typing"
Cohesion: 0.07
Nodes (36): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), AskPlan, EntityMention, _int_list(), PlannedTool (+28 more)

### Community 63 - "re"
Cohesion: 0.09
Nodes (26): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+18 more)

### Community 64 - "nav_service.py"
Cohesion: 0.21
Nodes (11): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+3 more)

### Community 65 - "fund_universe_agent.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "CapabilityCache"
Cohesion: 0.19
Nodes (5): CapabilityCache, _Entry, test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner()

### Community 68 - "insight/guardrails.py"
Cohesion: 0.09
Nodes (23): _amc_hints_from_tokens(), candidates_block(), entity_candidates(), _holding_candidates(), _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known() (+15 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "embed.py"
Cohesion: 0.15
Nodes (8): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), main()

### Community 71 - "portfolio/cache.py"
Cohesion: 0.10
Nodes (28): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), get_normalized_portfolio(), peek_derived(), preload_configured_portfolio(), _run() (+20 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "fund_portfolio_news.py"
Cohesion: 0.12
Nodes (17): corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news() (+9 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "additional_insights/run.py"
Cohesion: 0.10
Nodes (20): build(), _cards(), main(), _build(), _user(), detect_signals(), Signal, _surge() (+12 more)

### Community 77 - "screen_hints_from_question"
Cohesion: 0.16
Nodes (14): question_needs_affected_sectors(), _args_from_question(), _exposure_ask(), _heavy_and_return(), _return_direction_in_question(), screen_hints_from_question(), test_defence_fund_screen_uses_defense_category(), test_fof_fund_screen_returns_fof_schemes() (+6 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.20
Nodes (14): extract_top_holdings(), _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file() (+6 more)

### Community 79 - "get_settings"
Cohesion: 0.18
Nodes (15): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+7 more)

### Community 80 - "clarify_plan_if_fund_unknown"
Cohesion: 0.05
Nodes (42): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), filter_display_tables() (+34 more)

### Community 81 - "validate.py"
Cohesion: 0.19
Nodes (19): numeric_leaves(), walk(), _allowed_numbers(), _banned(), _blob(), walk(), _body(), CheckResult (+11 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.13
Nodes (37): pending_rating_line(), _age(), _allocation_bucket_rows(), _as_of(), _book_line(), _category_amount_map(), _comparison_rows(), _composition_line() (+29 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "get_sector_fund_ranking_index"
Cohesion: 0.05
Nodes (34): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+26 more)

### Community 86 - "test_ai_insight_quality.py"
Cohesion: 0.10
Nodes (23): enforce_prompt_budget(), EvidenceArticle, _float(), format_evidence_block(), _int(), pick_evidence(), story_weight(), _data() (+15 more)

### Community 87 - "plan_enforce.py"
Cohesion: 0.05
Nodes (54): asks_ideal_portfolio_shape(), category_composition_plan_applies(), merge_planner_asked_facts(), tag_answer_parts(), question_signals_investor_book(), question_asks_current_book_allocation(), asks_these_equity_funds(), apply_category_scoped_compare_funds() (+46 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.14
Nodes (19): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+11 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 90 - "test_metal_fund_rating.py"
Cohesion: 0.13
Nodes (13): ensure_quality_fund_list(), fetch_category_ratings(), _payload(), _rating(), test_category_rating_request_uses_admin_header(), test_gold_etf_only_stays_on_the_etf_category(), test_gold_fund_list_uses_only_gold_scheme_categories(), test_gold_list_spreads_etf_and_fund_of_funds() (+5 more)

### Community 91 - "node_route"
Cohesion: 0.09
Nodes (22): ensure_fund_concentration_plan(), node_route(), ensure_planner_fund_fact_modules(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question() (+14 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.06
Nodes (67): _add_category_comparison(), append_investor_portfolio_overview_tables(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line(), _compare_cell(), _compare_header(), _complete_fund_row() (+59 more)

### Community 96 - "test_news_only_answer.py"
Cohesion: 0.17
Nodes (7): _news_subject(), clean_news_insight(), complete_sentences(), news_insight_articles(), strip_publisher(), _subject_words(), test_news_about_hdfc_bank_is_not_a_market_pulse()

### Community 97 - "NumericRecord"
Cohesion: 0.26
Nodes (10): fetch_cpi_record(), pick(), fetch_gdp_record(), fetch_gsec(), fetch_gst(), fetch_iip_record(), fetch_official(), fetch_wpi_record() (+2 more)

### Community 98 - "question_intent.py"
Cohesion: 0.11
Nodes (19): question_mentions_fund_scheme(), asks_fund_category_average(), plan_matches_intent(), QuestionIntent, resolve_question_intent(), _top_n_from_question(), _asks_catalog_fund_performance(), _extract_fund_names() (+11 more)

### Community 99 - "clustering.py"
Cohesion: 0.15
Nodes (18): _adapter(), cluster_rows(), _collapse(), _dedupe(), find(), union(), _group_of(), _keys() (+10 more)

### Community 100 - "shared_system_prefix"
Cohesion: 0.26
Nodes (7): plan_system_prompt(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), _body(), test_planner_and_composer_share_the_first_system_block(), test_tools_stay_available_when_there_is_no_shared_prefix()

### Community 102 - "MospiClient"
Cohesion: 0.23
Nodes (4): MospiError, _payload(), _sse_json(), GraphUnavailable

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.18
Nodes (12): _rating_lead_for_pack(), asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score() (+4 more)

### Community 106 - "slot_route"
Cohesion: 0.09
Nodes (26): asks_rating_list(), execute_wave(), _asks_driver_sector_or_fund_impact(), _extract_drivers(), _extract_stocks(), _infer_window_days(), slot_route(), primary_sector_for_question() (+18 more)

### Community 107 - "parse_rating_screen"
Cohesion: 0.08
Nodes (46): asks_taxonomy(), match_all_fund_types(), parse_rating_screen(), _return_direction(), run_rating_list(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap() (+38 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.15
Nodes (15): CategoryMatch, _close(), explanation_brief(), fund_type_for_category(), _metal_category(), _metal_flags(), _names_a_type(), _phrase_score() (+7 more)

### Community 109 - "return_windows.py"
Cohesion: 0.17
Nodes (15): _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows(), window_label() (+7 more)

### Community 110 - "lib/portfolio_scope.py"
Cohesion: 0.13
Nodes (21): build_portfolio_scope(), _clean_holding_tokens(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc() (+13 more)

### Community 111 - "test_investor_grounding.py"
Cohesion: 0.16
Nodes (14): strip_grounding_holes(), cores_for_float(), derived_cores(), fund_portfolio_cores(), investor_book_cores(), sanitize_data_pack_for_composer(), _sample_book(), test_grounding_keeps_category_weight_in_prose() (+6 more)

### Community 112 - "entity_retrieval.py"
Cohesion: 0.25
Nodes (18): EntityPack, evidence_from_clusters(), fetch_entity_pack(), fetch_fii_dii(), fetch_macro_packs(), work(), fetch_market_driver(), fetch_sector_index() (+10 more)

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 114 - "insights.py"
Cohesion: 0.30
Nodes (10): build_insights(), _equity_pct(), Insight, insight_lines(), insights_for_brief(), _num(), _style_band(), _book() (+2 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 117 - "universe.py"
Cohesion: 0.18
Nodes (16): _aliases_for(), build_holding_entities(), _display_name(), _holding_query(), _industry_search_hint(), _is_exchange_label(), load_holdings(), load_macro_entities() (+8 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "macro_news_cache.py"
Cohesion: 0.16
Nodes (13): _run_get_macro_news(), _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read() (+5 more)

### Community 121 - "workspace.py"
Cohesion: 0.13
Nodes (10): main(), prune_insight_logs(), apply_fresh_start(), _clear_run_json_summaries(), clear_scrape_workspace(), remove_scrape_artifacts(), remove_scrape_artifacts_many(), url_artifact_stem() (+2 more)

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "stitch_display_tables_into_answer"
Cohesion: 0.10
Nodes (28): append_news_section(), build_fund_display_tables(), format_display_tables_markdown(), _insert_before_disclaimer(), stitch_display_tables_into_answer(), strip_composer_display_sections(), _strip_heading_sections(), strip_markdown_tables_from_prose() (+20 more)

### Community 124 - "prompts.py"
Cohesion: 0.22
Nodes (6): build_brief_prompt(), build_composer_prompt(), build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 125 - "memory/evidence.py"
Cohesion: 0.10
Nodes (26): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), _positive_ms(), _take_conversation_slice(), widen_portfolio_args(), clear_conversation(), recall_slice() (+18 more)

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "ToolCall"
Cohesion: 0.04
Nodes (67): ensure_rating_screen(), _followup_modules(), asks_fund_risk(), _ensure_pillar_rating_plan(), ensure_risk_tools(), _ensure_risk_trend_plan(), _use_rating_concept(), finalize_unnamed_catalog_compare() (+59 more)

### Community 128 - "qdrant_access.py"
Cohesion: 0.22
Nodes (17): _as_dict(), _client(), _drop(), _entity_view(), EntityRowsResult, _explode(), fetch_entity_rows(), _filter() (+9 more)

### Community 129 - "layer_tools.py"
Cohesion: 0.11
Nodes (25): nifty50_ticker(), aggregate_sectors_from_holdings(), _price_holdings(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns(), _read_cache() (+17 more)

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
Cohesion: 0.07
Nodes (28): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+20 more)

### Community 135 - "test_greeting.py"
Cohesion: 0.18
Nodes (12): greeting_reply(), identity_reply(), _mirror_greeting(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens(), prompt_view() (+4 more)

### Community 136 - "fields.py"
Cohesion: 0.07
Nodes (41): _asks_book(), bind_fields_to_tools(), _book_fields(), field_need(), FieldNeed, fields_from_question(), _fund_fields(), _leave_tools_alone() (+33 more)

### Community 137 - "inputs"
Cohesion: 0.29
Nodes (7): default, description, required, type, holdings_limit, workflow_dispatch, inputs

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "fund_scheme_match.py"
Cohesion: 0.15
Nodes (16): amc_token_in_question(), _category_phrases_in_question(), _constraint_in_scheme_name(), _distinctive_constraints(), pick_best_matching_scheme(), question_amc_hints(), scheme_match_score(), _scheme_name_tokens() (+8 more)

### Community 141 - "explicit_fund_count"
Cohesion: 0.11
Nodes (13): metal_scheme_categories(), _category_fund_name_spec(), fund_naming_clause(), _label_in(), _looks_like_fund_list(), _metal_fund_categories(), _metal_fund_spec(), _question_names_amc_scheme() (+5 more)

### Community 142 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (57): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+49 more)

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

### Community 146 - "canonical_key"
Cohesion: 0.17
Nodes (12): _resolve_bellwether(), rank(), _fund_stats_from_csv(), load_holdings_rows_from_xlsx(), multi_query_for(), _strip_legal_suffix(), canonical_key(), _article_entities() (+4 more)

### Community 147 - "extract.ts"
Cohesion: 0.80
Nodes (4): decodeHtmlEntities(), extractFromHtml(), metaContent(), stripTags()

### Community 148 - "sync-news-runs-to-r2.sh"
Cohesion: 0.40
Nodes (4): AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, sync-news-runs-to-r2.sh script

### Community 149 - "date_range"
Cohesion: 0.40
Nodes (5): default, description, required, type, date_range

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

### Community 163 - "fund_match.py"
Cohesion: 0.11
Nodes (14): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+6 more)

### Community 169 - "portfolio_bind.py"
Cohesion: 0.18
Nodes (12): _category_slug_from_question(), question_asks_category_book_share(), question_asks_category_money(), bind_cached_portfolio(), _catalog_fund_holdings_question(), ensure_tools_for_data_question(), finish_portfolio_plan_bind(), _investor_args() (+4 more)

### Community 170 - "sector_exposure_tables.py"
Cohesion: 0.14
Nodes (17): merge_fund_isins_map(), bind_shown_list_followup(), windows_named_in_question(), _all_holdings_metric_spec(), _fund_data_from_results(), _investor_holdings_rating_rows(), _metric_cell(), render_all_holdings_metric_table() (+9 more)

### Community 174 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

### Community 178 - "validate_capability_args"
Cohesion: 0.15
Nodes (11): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded() (+3 more)

### Community 180 - "Cluster"
Cohesion: 0.26
Nodes (14): Cluster, cluster_score(), rank_clusters(), Drivers, is_index_recap(), move_phrase(), move_size(), _names() (+6 more)

### Community 181 - "test_ai_insight_common_qdrant_access.py"
Cohesion: 0.22
Nodes (11): is_stale(), newest_scraped_at(), _article(), FakeQdrant, _point(), test_freshness_stale_when_missing_or_old(), test_holding_without_names_raises(), test_low_relevance_sector_is_rejected_when_article_max_relevance_is_high() (+3 more)

### Community 182 - "test_call_json_llm.py"
Cohesion: 0.45
Nodes (8): _client(), _gemini_response(), _settings(), test_agent_keeps_truncated_tools_without_repair(), test_composer_keeps_truncated_answer_without_a_second_call(), test_gemini_request_includes_response_schema(), test_judge_truncated_json_does_not_repair(), test_truncated_json_triggers_one_repair_call()

### Community 183 - "repo_root"
Cohesion: 0.24
Nodes (8): write_ask_market_snapshot(), FiiDiiSnapshot, _cache_dir(), write_snapshot(), main(), write_fii_dii(), write_latest(), repo_root()

### Community 184 - "portfolio_plan.py"
Cohesion: 0.18
Nodes (8): _slot_fallback(), normalize_portfolio_plan_from_question(), top_n_from_question(), test_normalize_portfolio_skips_planner_routed_plans(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

### Community 185 - "insight_links.py"
Cohesion: 0.17
Nodes (13): normalize_holding_row(), _group_layered_articles(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows() (+5 more)

### Community 186 - "lib/google_news.py"
Cohesion: 0.04
Nodes (39): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+31 more)

### Community 187 - "json"
Cohesion: 0.07
Nodes (18): notify_failure(), explain(), main(), _short(), ingest_ready(), main(), run_daily(), _json_default() (+10 more)

### Community 188 - "fact_slots.py"
Cohesion: 0.33
Nodes (6): asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), test_aum_slot_renders_from_snapshot()

### Community 190 - "ScopeKind"
Cohesion: 0.29
Nodes (11): apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), ScopeKind, asks_fof_funds(), test_concept_example_plan_screen_fof() (+3 more)

### Community 191 - "build_derived_views"
Cohesion: 0.14
Nodes (17): clear_cache_for_tests(), asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation() (+9 more)

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 193 - "fund_search.py"
Cohesion: 0.15
Nodes (14): build_holding_overlap(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _entry_matches_query_scheme(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase() (+6 more)

### Community 194 - "._ensure_loaded"
Cohesion: 0.12
Nodes (6): detail_has_live_facts(), FundIndex, get_fund_benchmark(), _infer_category_and_type(), resolve_canonical_isin(), _sync_amc_prefix_from_catalog()

### Community 195 - "compare_evidence.py"
Cohesion: 0.24
Nodes (8): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_maybe_run_compare_retries_after_failed_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 197 - "QuestionBrief"
Cohesion: 0.07
Nodes (37): analyst_should_run(), asks_market_briefing(), asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), build_question_brief(), _detect_direction() (+29 more)

### Community 198 - "283041/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 203 - "fund_brief.py"
Cohesion: 0.08
Nodes (34): Settings, build_events(), cluster_articles(), _cluster_entities(), compose_fund_insight(), _day_key(), _empty_brief(), _exposure_for_holding() (+26 more)

### Community 206 - "test_ai_insight.py"
Cohesion: 0.18
Nodes (6): digest_filter(), _holding_mentioned(), matches_entity(), contains_phrase(), test_digest_filter_uses_stricter_scores(), test_sector_exclude_drops_nbfc_from_banks()

### Community 208 - "datetime"
Cohesion: 0.07
Nodes (34): _bool(), _float(), _freshness_flag(), _int(), week_index_movers(), LoopSpec, _bars(), catalog_path() (+26 more)

### Community 209 - "57e233/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 211 - "fund_type_name_spec"
Cohesion: 0.08
Nodes (29): fund_type_name_spec(), question_is_standalone_macro(), enforce_user_authorized_funds_only(), fund_authorized_for_question(), _named_in_chat_turns(), plan_allows_server_fund_pick(), apply_pure_concept_plan(), question_is_pure_general_concept() (+21 more)

### Community 212 - "c72b25/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 213 - "a45664/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 214 - "test_composer_table_summaries.py"
Cohesion: 0.19
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_parse_tables_append_directive(), test_strip_empty_bold_sections(), test_summarize_tables_for_composer_extracts_mix_and_holdings()

### Community 217 - "7859f0/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 218 - "glossary.py"
Cohesion: 0.26
Nodes (10): asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), glossary_execution_plan(), meaning_reply(), _normalize_term(), test_fund_nav_not_glossary(), test_nav_full_form_direct_reply() (+2 more)

### Community 219 - "test_answer_precision.py"
Cohesion: 0.17
Nodes (9): fact_values_already_stated(), question_wants_fact_table(), strip_meta_opening_heading(), _strip_unasked_closers(), test_fact_table_only_for_compare_or_an_explicit_list(), test_fact_table_skipped_when_prose_has_the_figure(), test_next_steps_and_summary_are_removed(), test_specific_lookup_has_no_default_table() (+1 more)

### Community 221 - "test_screen_facts.py"
Cohesion: 0.22
Nodes (8): screen_fact_names(), test_any_fund_screen_keeps_requested_aum(), _detail(), test_screen_can_ask_for_several_facts(), test_screen_manager_name_and_experience_are_separate_facts(), test_screen_table_includes_aum(), test_screen_table_includes_manager_name_and_experience(), test_sector_screen_aum_does_not_mean_top_sectors()

### Community 222 - "NumericRecord"
Cohesion: 0.14
Nodes (14): latest_quote(), fetch_ask_market_records(), fetch_gold_record(), NumericRecord, unavailable(), fetch_fii_dii(), numeric_from_fii_dii_snapshot(), fetch_all() (+6 more)

### Community 223 - "test_ai_insight_common_market.py"
Cohesion: 0.33
Nodes (8): FlowLeg, _cfg(), _quote(), test_fii_dii_date_and_partial(), test_nifty_ok_and_stale(), test_nifty_timeout_and_exception(), slow(), test_usdinr_must_be_dated_on_the_trading_day()

### Community 224 - "run_ask_engine"
Cohesion: 0.16
Nodes (7): _events(), run_ask_engine(), stream_ask_engine(), run_insight_pipeline(), stream_insight_pipeline(), main(), test_ask_engine_delegates_to_insight_pipeline()

### Community 225 - "insights.js"
Cohesion: 0.22
Nodes (18): api(), arrow(), bars(), card(), chart(), diverging(), esc(), headers() (+10 more)

### Community 227 - "insight_log.js"
Cohesion: 0.70
Nodes (4): api(), esc(), headers(), load()

### Community 228 - "synthesize_tasks"
Cohesion: 0.20
Nodes (8): _spaced_category_words(), _canon_fact(), _category_in_planner_text(), _compare_subject_kind(), _facts_from_plan(), _owned_fund_names(), synthesize_tasks(), _window_code()

### Community 229 - "assemble_fund_overview_answer"
Cohesion: 0.18
Nodes (7): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), strip_empty_table_pointers(), _strip_overview_prose_block(), test_overview_drops_repeated_title_and_nav_paragraph(), test_overview_puts_rating_and_tables_before_news(), test_a_risk_read_does_not_point_at_a_missing_returns_table()

### Community 230 - "test_screen_rating_screen_arg.py"
Cohesion: 0.24
Nodes (7): test_finalize_screen_adds_returns_for_compare_question(), fake_detail(), get_fund_detail(), test_rating_screen_uses_focus_question_not_full_compare_question(), test_rating_screen_uses_forced_category_spec(), fake_fetch(), test_validate_capability_args_keeps_rating_screen()

### Community 231 - "test_entity_retrieval.py"
Cohesion: 0.33
Nodes (6): bellwether_holdings(), merge_evidence(), _qdrant_holding_names(), test_bellwether_holdings_resolves_it_majors(), test_merge_evidence_dedupes_url(), test_slug_macro_name()

### Community 232 - "rank_funds_by_sector_exposure"
Cohesion: 0.42
Nodes (5): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships()

### Community 233 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 235 - "normalize_user_facing_text"
Cohesion: 0.22
Nodes (6): ensure_markdown_table_spacing(), normalize_user_facing_text(), strip_context_disclaimer(), _clean_answer(), test_normalize_inserts_blank_line_before_markdown_table(), test_normalize_na_to_hyphen()

### Community 236 - "_fund_performance_digest"
Cohesion: 0.38
Nodes (4): _fund_performance_digest(), prefers_planner_over_slot(), test_fund_news_does_not_force_planner(), test_performance_digest_from_snapshot()

### Community 238 - "_public_pillars"
Cohesion: 0.33
Nodes (4): _catalog_name(), _public_row(), _pillar_maximum(), _public_pillars()

### Community 240 - "run_insights_daily.sh"
Cohesion: 0.50
Nodes (4): note(), PYTHONPATH, PYTHONUNBUFFERED, run_insights_daily.sh script

### Community 241 - "data_pack.py"
Cohesion: 0.50
Nodes (3): build_data_pack(), build(), _compact()

### Community 255 - "test_rupeestop_auth.py"
Cohesion: 0.12
Nodes (8): rupeestop_admin_request_headers(), _jwt(), test_admin_headers_include_bearer(), test_admin_headers_use_token_from_login(), test_bearer_prefers_auth_token_over_admin_token(), test_failed_login_keeps_previous_token(), test_non_admin_url_has_no_authorization(), test_valid_jwt_does_not_call_login()

## Knowledge Gaps
- **22 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+17 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1915 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **56 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `fund_rating_screen.py`, `portfolio_news_impact.py`, `node_compose`, `fields.py`, `test_insight_graph.py`, `update.py`, `test_fund_drawdown.py`, `test_fund_name_gate_and_hydrate.py`, `QueryLogger`, `macro_data.py`, `project_modules`, `fund_display.py`, `gather.py`, `pack_sanitize.py`, `plan_enforce.py`, `test_two_wave_pipeline.py`, `task_exec.py`, `llm_client.py`, `insight/portfolio_scope.py`, `planner_policy.py`, `portfolio_bind.py`, `sector_exposure_tables.py`, `plan.py`, `book_news_map.py`, `gold_service.py`, `investor_subject.py`, `AnswerMode`, `portfolio_plan.py`, `fact_slots.py`, `test_fund_risk.py`, `ScopeKind`, `graph.py`, `build_derived_views`, `compare_evidence.py`, `clarify_plan_if_fund_unknown`, `fact_answer.py`, `fund_type_name_spec`, `test_composer_table_summaries.py`, `plan_enforce.py`, `test_portfolio_allocation.py`, `glossary.py`, `test_answer_precision.py`, `node_route`, `test_metal_fund_rating.py`, `test_screen_facts.py`, `evidence_pack.py`, `question_intent.py`, `synthesize_tasks`, `slot_route`, `parse_rating_screen`, `return_windows.py`, `ToolCall`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `ExecutionPlan` (e.g. with `news_calls_for_book()` and `sector_book()`) actually correct?**
  _`ExecutionPlan` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _22 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.0735930735930736 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `llm_client.py` to `qdrant_access.py`, `interpret.py`, `portfolio_news_impact.py`, `node_compose`, `compute.py`, `tools.py`, `parse.py`, `QueryLogger`, `news_reader.py`, `project_modules`, `gather.py`, `task_exec.py`, `fund_match.py`, `insight/portfolio_scope.py`, `portfolio_bind.py`, `plan.py`, `ExecutionPlan`, `app.py`, `gold_service.py`, `validate_capability_args`, `investor_subject.py`, `AnswerMode`, `portfolio_plan.py`, `executor.py`, `json`, `graph.py`, `typing`, `fund_search.py`, `insight/guardrails.py`, `QuestionBrief`, `embed.py`, `portfolio/cache.py`, `fund_portfolio_news.py`, `fund_brief.py`, `stock_fund_ranking.py`, `get_settings`, `get_sector_fund_ranking_index`, `node_route`, `shared_system_prefix`, `slot_route`, `health.py`, `memory/evidence.py`, `test_rupeestop_auth.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ToolCall` (e.g. with `news_calls_for_book()` and `_apply_planner_request()`) actually correct?**
  _`ToolCall` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `fund_rating_screen.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07769423558897243 - nodes in this community are weakly interconnected._