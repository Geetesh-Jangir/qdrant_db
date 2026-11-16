# Graph Report - db_design_with_qdrant_locally  (2026-11-16)

## Corpus Check
- 651 files · ~965,740 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 22 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 3)

## Summary
- 6863 nodes · 22248 edges · 249 communities (194 shown, 55 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 753 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `60db9241`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- sources/google_news.py
- fund_rating_screen.py
- interpret.py
- load_config
- market_driver_digest/run.py
- update.py
- node_compose
- grounding.py
- Settings
- GraphState
- plan_enforce.py
- load_config
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
- typing
- tool_runners.py
- sector_leaderboard/run.py
- fund_display.py
- gather.py
- pack_sanitize.py
- plan_enforce.py
- nse_fii_dii.py
- infer_fund_news_layers
- NewsStore
- task_exec.py
- llm_client.py
- load_config
- Any
- normalize.py
- insight/portfolio_scope.py
- scrape_bodies.py
- env
- normalize_rs_label
- article_quality.py
- plan.py
- macro_news_cache.py
- env
- sector_alignment.py
- portfolio_news_impact.py
- ToolCall
- fund_catalog.py
- app.py
- gold_service.py
- env
- investor_subject.py
- fund_rupeestop_metrics.py
- contracts.py
- pytest
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
- _return_slice_covers
- insight/guardrails.py
- http-fetch.ts
- embed.py
- portfolio/cache.py
- holdings_market.py
- fund_portfolio_news.py
- with
- Envelope
- affected_sectors.py
- stock_fund_ranking.py
- get_settings
- display_table_policy.py
- validate.py
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- sector_fund_ranking.py
- test_ai_insight_quality.py
- ExecutionPlan
- test_portfolio_allocation.py
- normalize_answer_markdown
- test_metal_fund_rating.py
- test_answer_quality_logs.py
- env
- steps
- evidence_pack.py
- test_news_only_answer.py
- NumericRecord
- httpx
- strip_missing_data_caveats
- shared_system_prefix
- MospiClient
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- get_sector_fund_ranking_index
- parse_rating_screen
- fund_rating_categories.py
- return_windows.py
- lib/portfolio_scope.py
- EvidencePack
- dataclasses
- news_digest.py
- insights.py
- vitest
- format_inr
- universe.py
- compilerOptions
- compilerOptions
- get_macro_news
- eval_planner.py
- backfill
- stitch_display_tables_into_answer
- prompts.py
- memory/evidence.py
- run-pipeline
- build_evidence_pack
- sector_query_for_label
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
- apply_task_layer
- test_fund_drawdown.py
- run-backfill.sh
- qdrant
- test_stocks_service.py
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
- main.py
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- portfolio/client.py
- owned_holding_names
- diagnose_lightsail_site.sh
- asks_computed_illustration
- validate_capability_args
- EntityFunnel
- unittest_mock
- _attach_rs_ratings_to_screen
- test_call_json_llm.py
- repo_root
- test_ai_insight_mospi.py
- insight_links.py
- lib/google_news.py
- compare_ask_speed.py
- query_log.py
- pack_trim.py
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
- test_one_rated_fund_per_category_does_not_fill_with_gold
- test_answer_precision.py
- news_rag/config.py
- ask_market_bridge.py
- _unhandled_exception_handler
- run_ask_engine
- insights.js
- insight_log.js
- rank_funds_by_sector_exposure
- PublisherStats
- strip_news_roundup
- csv
- run_insights_daily.sh
- data_pack.py
- install-insights-cron.sh
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- test_rupeestop_auth.py
- test_failed_login_keeps_previous_token

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 607 edges
2. `ToolCall` - 367 edges
3. `get_settings()` - 143 edges
4. `apply_planner_post_hooks()` - 123 edges
5. `AnswerMode` - 108 edges
6. `node_compose()` - 102 edges
7. `QueryLogger` - 100 edges
8. `load_config()` - 90 edges
9. `Settings` - 88 edges
10. `QuestionBrief` - 88 edges

## Surprising Connections (you probably didn't know these)
- `test_slug_macro_name()` --calls--> `slug()`  [EXTRACTED]
  tests/test_entity_retrieval.py → ai_insight/common/entity_retrieval.py
- `_qdrant_holding_names()` --uses--> `Settings`  [INFERRED]
  ai_insight/common/entity_retrieval.py → news_pipeline/config.py
- `test_cli_dry_run()` --calls--> `cli_main()`  [EXTRACTED]
  tests/test_ai_insight_common_runner.py → ai_insight/common/runner.py
- `TestGoogleNewsFetch` --uses--> `Settings`  [INFERRED]
  tests/test_google_news_fetch.py → news_pipeline/config.py
- `test_story_weight_matches_the_hand_calculation()` --calls--> `story_weight()`  [INFERRED]
  tests/test_sector_leaderboard_score.py → ai_insight/common/evidence.py

## Import Cycles
- 2-file cycle: `ai_insight/common/entity_retrieval.py -> ai_insight/common/retrieval_plan.py -> ai_insight/common/entity_retrieval.py`

## Communities (249 total, 55 thin omitted)

### Community 0 - "logging"
Cohesion: 0.08
Nodes (45): get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate() (+37 more)

### Community 1 - "sources/google_news.py"
Cohesion: 0.14
Nodes (15): fetch_entity_items(), _fetch_query_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url(), fetch_macro_items(), is_macro_match(), macro_fetch_entities() (+7 more)

### Community 2 - "fund_rating_screen.py"
Cohesion: 0.05
Nodes (58): categories_for(), metal_scheme_categories(), pickable_categories(), _add_category_comparison(), _allocation_mix_spec(), _amc_matches(), _amc_outside_label(), _amc_token() (+50 more)

### Community 3 - "interpret.py"
Cohesion: 0.07
Nodes (69): QuestionBrief, Findings, FundFinding, SectorFinding, EvidenceSet, mentions_publication_date(), _article_context_for_interpret(), _assemble() (+61 more)

### Community 4 - "load_config"
Cohesion: 0.05
Nodes (69): CommonConfig, editorial_context(), market_numbers(), ordinal(), cumulative(), FlowDay, history_path(), load_flow_history() (+61 more)

### Community 5 - "market_driver_digest/run.py"
Cohesion: 0.14
Nodes (24): fmt_ist(), _resolve_end(), rolling_window(), session_window(), to_ist(), week_window(), _closed_dates(), is_trading_day() (+16 more)

### Community 6 - "update.py"
Cohesion: 0.24
Nodes (11): add_gist(), empty_frame(), empty_state(), expire_stale_entities(), push_fund(), stack_entry(), _subject(), test_repeated_fund_mention_refreshes_entity_ttl() (+3 more)

### Community 7 - "node_compose"
Cohesion: 0.19
Nodes (17): field_answer_needs_composer(), is_pure_field_answer(), render_benchmark_comparison_table(), render_fact_answer(), wants_comparison_table(), _plan(), test_all_holdings_rs_uses_composer_not_field_template(), test_aum_and_expense_both_appear() (+9 more)

### Community 8 - "grounding.py"
Cohesion: 0.07
Nodes (35): analyst_should_run(), asks_market_briefing(), collect_evidence_calendar_dates(), add_article(), cores_for_float(), cores_in_text(), finalize_text_fields(), format_user_calendar_date() (+27 more)

### Community 9 - "Settings"
Cohesion: 0.08
Nodes (32): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), article_in_fetch_window(), google_time_query(), has_news_date_range(), iter_inclusive_days() (+24 more)

### Community 10 - "GraphState"
Cohesion: 0.09
Nodes (30): facts_only_compose_allowed(), _attach_conversation(), build_result(), _catalog_fanout_fund_names(), _conversation_id(), _drop_scheme_is_the_whole_book(), _ensure_portfolio_for_fund_news(), GraphState (+22 more)

### Community 11 - "plan_enforce.py"
Cohesion: 0.04
Nodes (65): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), _amc_token_set(), _bound_fund_name(), _compare_sides_resolvable(), _known_names_in_text(), single_fund_for_deictic(), _resolve_funds() (+57 more)

### Community 12 - "load_config"
Cohesion: 0.05
Nodes (55): notify_failure(), bundle_exists(), _check_id(), _dump(), exists(), _file(), _is_date(), latest() (+47 more)

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (45): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+37 more)

### Community 14 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (57): retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), run_driver_affected_funds_adapter(), DataNeed, rank_funds_by_sector_exposure(), _active_sector_equity(), _articles_for_affected_question(), _as_date() (+49 more)

### Community 16 - "parse.py"
Cohesion: 0.07
Nodes (26): _warmup_embeddings_background(), _run(), _pack_row(), _retrieve_bullion_for_entities(), _trim_snippet(), embed_query(), embed_query(), warmup_query_vectors() (+18 more)

### Community 17 - "test_fund_name_gate_and_hydrate.py"
Cohesion: 0.11
Nodes (32): _store_turn_memory(), note_cache(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view() (+24 more)

### Community 18 - "QueryLogger"
Cohesion: 0.09
Nodes (9): slots_from_plan(), run_graph_pipeline(), clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest(), test_finish_writes_json_sidecar() (+1 more)

### Community 19 - "news_reader.py"
Cohesion: 0.10
Nodes (34): _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority(), _clean_claims(), _clean_sector_calls() (+26 more)

### Community 20 - "macro_data.py"
Cohesion: 0.15
Nodes (24): BondYieldResult, _client(), _codes(), walk(), CPIRecord, fetch_bond_yields(), fetch_cpi(), fetch_gdp() (+16 more)

### Community 21 - "runner.py"
Cohesion: 0.07
Nodes (40): _env_secrets(), prune_logs(), _redact(), _redact_text(), _rmtree(), RunArtifacts, _usage(), _append() (+32 more)

### Community 22 - "project_modules"
Cohesion: 0.07
Nodes (24): question_wants_invested_value_table(), fetch_top_holdings(), project_concentration(), _drop_sold(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules() (+16 more)

### Community 23 - "typing"
Cohesion: 0.05
Nodes (40): main(), prune_insight_logs(), Publisher, SectorQuery, Settings, _merge_publisher_error_reasons(), write_day_report(), _atomic_write() (+32 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.12
Nodes (41): _window_pct_from_nav_payload(), build_default_registry(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+33 more)

### Community 25 - "sector_leaderboard/run.py"
Cohesion: 0.04
Nodes (100): sector_label(), LlmJsonResult, LlmUsage, scrub_refusal_prose(), split_sentences(), FactsBase, FiiDiiFactsBase, SectorLeaderboardFactsBase (+92 more)

### Community 26 - "fund_display.py"
Cohesion: 0.11
Nodes (29): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+21 more)

### Community 27 - "gather.py"
Cohesion: 0.07
Nodes (50): _brief_system(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext (+42 more)

### Community 28 - "pack_sanitize.py"
Cohesion: 0.09
Nodes (26): _fund_performance_digest(), attach_drawback_digest(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer(), question_asks_all_schemes_in_answer(), question_wants_scheme_names(), _display_holding_row() (+18 more)

### Community 29 - "plan_enforce.py"
Cohesion: 0.06
Nodes (50): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), _spaced_category_words(), asks_category_performance(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition() (+42 more)

### Community 30 - "nse_fii_dii.py"
Cohesion: 0.18
Nodes (13): current_artifacts(), log_external(), _bucket(), _httpx_json(), _impit_json(), _leg(), _log_external(), _nse_json() (+5 more)

### Community 31 - "infer_fund_news_layers"
Cohesion: 0.36
Nodes (5): infer_fund_news_layers(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only(), test_overview_news_is_holdings_and_sectors()

### Community 32 - "NewsStore"
Cohesion: 0.08
Nodes (10): _to_article(), EntityScore, StoredArticle, merge_stored_article(), payload_to_stored(), _datetime_range(), NewsStore, point_id_for_url() (+2 more)

### Community 33 - "task_exec.py"
Cohesion: 0.14
Nodes (27): bind_subjects(), _book_total_line(), _canon_fact(), _cell(), _compare_subject_kind(), coverage_line(), _fact_label(), _facts_from_plan() (+19 more)

### Community 34 - "llm_client.py"
Cohesion: 0.08
Nodes (41): anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts(), _call_anthropic(), _call_deepseek(), _call_gemini(), call_insight_llm(), _call_insight_llm_body() (+33 more)

### Community 35 - "load_config"
Cohesion: 0.05
Nodes (47): _all_dates(), _bundle_is_live(), create_router(), daily(), dates(), generate(), health(), job_latest() (+39 more)

### Community 36 - "Any"
Cohesion: 0.14
Nodes (15): headline_rating(), _clean_company_name(), fetch_fund_managers_for_isin(), _fund_context_for_managers(), _fund_text(), _named_weights(), _normalize_manager_record(), _optional_number() (+7 more)

### Community 37 - "normalize.py"
Cohesion: 0.18
Nodes (21): aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values(), _book_has_market_value(), _fill_missing_from_live(), _first() (+13 more)

### Community 38 - "insight/portfolio_scope.py"
Cohesion: 0.09
Nodes (35): build_drawdown_wave2_calls(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), question_signals_investor_book(), plan_targets_single_fund_measured_return(), question_asks_current_book_allocation(), question_asks_holding_metric_and_glossary() (+27 more)

### Community 39 - "scrape_bodies.py"
Cohesion: 0.15
Nodes (12): thread_session(), _entity_refs(), _log_scrape_record(), _scrape(), scrape_bodies(), _drop(), clip_log_text(), scrape_article_url() (+4 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "normalize_rs_label"
Cohesion: 0.13
Nodes (21): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), infer_anchor_label_from_excludes() (+13 more)

### Community 42 - "article_quality.py"
Cohesion: 0.12
Nodes (21): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+13 more)

### Community 43 - "plan.py"
Cohesion: 0.10
Nodes (23): explanation_brief(), canonicalize_field(), field_prompt_table(), mentions_advice(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years() (+15 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.16
Nodes (14): select_macro_for_question(), _slim_clusters(), _digest(), test_banking_and_banks_are_one_search(), test_cache_keeps_the_article_body_not_only_the_title(), test_cache_searches_named_macro_parameters(), test_clusters_are_ordered_by_how_many_articles_are_in_the_db(), test_failed_refresh_keeps_the_previous_cache() (+6 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "sector_alignment.py"
Cohesion: 0.07
Nodes (37): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _rule_sector_picks(), _rule_sector_picks(), canonical_direction_for_driver() (+29 more)

### Community 47 - "portfolio_news_impact.py"
Cohesion: 0.10
Nodes (26): book_wide_sectors(), _display_name(), _has_named_stock(), news_calls_for_book(), _news_name(), _pct(), resolve_book_sector(), sector_book() (+18 more)

### Community 48 - "ToolCall"
Cohesion: 0.06
Nodes (56): ensure_rating_screen(), finalize_unnamed_catalog_compare(), pick_random_scheme_category_for_compare(), _split_count(), ToolCall, ensure_screen_facts(), _bind_fund_list(), enforce_planner_catalog_plan() (+48 more)

### Community 49 - "fund_catalog.py"
Cohesion: 0.10
Nodes (24): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+16 more)

### Community 50 - "app.py"
Cohesion: 0.08
Nodes (53): ask(), ask_memory(), ask_query_log(), ask_sources(), ask_stream(), AskRequest, _attach_llm_meta(), _attach_portfolio_to_ask() (+45 more)

### Community 51 - "gold_service.py"
Cohesion: 0.09
Nodes (21): _fetch(), get_gold_snapshot(), get_silver_snapshot(), gold_horizon_code(), gold_macro_series_row(), _load_payload(), _merged_series(), add() (+13 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "investor_subject.py"
Cohesion: 0.05
Nodes (70): question_asks_portfolio_level_drawdown(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_deictic_and_memory_primary_fund(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan(), ensure_deictic_fund_period_return_plan() (+62 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.13
Nodes (19): asks_fund_category_average(), build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns() (+11 more)

### Community 55 - "contracts.py"
Cohesion: 0.03
Nodes (109): rating_list_plan(), rating_concept_plan(), ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), apply_concept_example_to_plan() (+101 more)

### Community 56 - "pytest"
Cohesion: 0.10
Nodes (26): _add_usage(), _default_call(), format_articles_block(), generate_json(), _invoke_with_retry(), LlmSchemaError, LlmUnavailable, _run_bounded() (+18 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "resolve_fund_for_query"
Cohesion: 0.12
Nodes (22): fetch_fund_managers_for_query(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), prefer_resolved_fund_name(), resolve_fund_for_query(), resolve_fund_from_question() (+14 more)

### Community 59 - "executor.py"
Cohesion: 0.05
Nodes (48): asks_rating_list(), rating_spec_for_forced_screen(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _conversation_id(), _conversation_turn(), _detail_for_fund_tool() (+40 more)

### Community 60 - "test_fund_risk.py"
Cohesion: 0.05
Nodes (70): asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison() (+62 more)

### Community 61 - "graph.py"
Cohesion: 0.16
Nodes (14): RequestTelemetry, _answer_stream_chunks(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed(), event_phase_started(), event_quality_check() (+6 more)

### Community 62 - "typing"
Cohesion: 0.08
Nodes (34): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), AskPlan, EntityMention, _int_list(), PlannedTool (+26 more)

### Community 63 - "re"
Cohesion: 0.09
Nodes (26): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+18 more)

### Community 64 - "nav_service.py"
Cohesion: 0.21
Nodes (11): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+3 more)

### Community 65 - "fund_universe_agent.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "_return_slice_covers"
Cohesion: 0.09
Nodes (18): CapabilityCache, _Entry, get_capability_cache(), _one_fund(), _positive_ms(), _return_slice_covers(), _trim_cached_to_ask(), test_missing_window_is_not_covered() (+10 more)

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
Cohesion: 0.12
Nodes (19): _run_get_investor_portfolio(), _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), find_cached_holdings(), get_active_crn(), get_normalized_portfolio() (+11 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "fund_portfolio_news.py"
Cohesion: 0.08
Nodes (25): corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news() (+17 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "Envelope"
Cohesion: 0.06
Nodes (54): build(), compose(), _cards(), main(), _build(), _user(), Signal, news_map_block() (+46 more)

### Community 77 - "affected_sectors.py"
Cohesion: 0.15
Nodes (14): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+6 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 79 - "get_settings"
Cohesion: 0.18
Nodes (15): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+7 more)

### Community 80 - "display_table_policy.py"
Cohesion: 0.09
Nodes (22): periods_requested_in_question(), resolve_display_periods(), DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), filter_display_tables(), _limit_tables(), _named_fund_overview() (+14 more)

### Community 81 - "validate.py"
Cohesion: 0.15
Nodes (21): Envelope, numeric_leaves(), walk(), _allowed_numbers(), _banned(), _blob(), walk(), _body() (+13 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.11
Nodes (41): _age(), _allocation_bucket_rows(), _as_of(), _asks_portfolio_rs_ratings(), _book_line(), _category_amount_map(), _comparison_rows(), _composition_line() (+33 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "sector_fund_ranking.py"
Cohesion: 0.13
Nodes (13): classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path(), sector_ranking_data_available() (+5 more)

### Community 86 - "test_ai_insight_quality.py"
Cohesion: 0.06
Nodes (40): detect_signals(), _surge(), bellwether_holdings(), merge_evidence(), _qdrant_holding_names(), EvidenceArticle, _float(), format_evidence_block() (+32 more)

### Community 87 - "ExecutionPlan"
Cohesion: 0.04
Nodes (98): asks_ideal_portfolio_shape(), category_composition_plan_applies(), ExecutionPlan, _portfolio_sections_from_plan(), merge_planner_asked_facts(), tag_answer_parts(), ensure_fund_concentration_plan(), clarify_plan_if_fund_unknown() (+90 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.17
Nodes (16): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+8 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.22
Nodes (9): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), strip_context_disclaimer(), _clean_answer(), test_pads_short_row() (+1 more)

### Community 90 - "test_metal_fund_rating.py"
Cohesion: 0.13
Nodes (13): ensure_quality_fund_list(), fetch_category_ratings(), _payload(), _rating(), test_category_rating_request_uses_admin_header(), test_gold_etf_only_stays_on_the_etf_category(), test_gold_fund_list_uses_only_gold_scheme_categories(), test_gold_list_spreads_etf_and_fund_of_funds() (+5 more)

### Community 91 - "test_answer_quality_logs.py"
Cohesion: 0.18
Nodes (10): question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), question_wants_gold_table(), scrub_unknown_fund_mentions(), test_gold_price_still_wants_a_draft_table(), test_invested_in_gold_is_not_a_spot_price_ask(), test_scrub_replaces_reading_when_no_deictic() (+2 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.06
Nodes (64): _add_category_comparison(), append_investor_portfolio_overview_tables(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line(), _compare_cell(), _compare_header(), _complete_fund_row() (+56 more)

### Community 96 - "test_news_only_answer.py"
Cohesion: 0.22
Nodes (9): _news_subject(), clean_news_insight(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words(), test_news_about_hdfc_bank_is_not_a_market_pulse(), test_news_insight_drops_publisher_clips_and_unrelated_articles() (+1 more)

### Community 97 - "NumericRecord"
Cohesion: 0.16
Nodes (18): latest_quote(), NumericRecord, unavailable(), fetch_cpi_record(), pick(), fetch_fii_dii(), fetch_gdp_record(), fetch_gsec() (+10 more)

### Community 98 - "httpx"
Cohesion: 0.27
Nodes (3): main(), main(), main()

### Community 99 - "strip_missing_data_caveats"
Cohesion: 0.17
Nodes (9): strip_missing_data_caveats(), test_a_rating_pick_does_not_apologise_for_returns_or_pillars(), test_strip_removes_risk_trend_apology(), test_a_holding_outside_the_top_five_still_gets_weight_and_sector(), test_a_top_five_apology_is_removed(), test_each_holding_keeps_the_article_text_not_only_one_headline(), test_grouped_news_keeps_the_article_body(), test_overview_fund_facts_are_a_short_table() (+1 more)

### Community 100 - "shared_system_prefix"
Cohesion: 0.24
Nodes (7): build_anthropic_messages_body(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), _body(), test_planner_and_composer_share_the_first_system_block(), test_tools_stay_available_when_there_is_no_shared_prefix()

### Community 102 - "MospiClient"
Cohesion: 0.19
Nodes (6): _cache_dir(), MospiClient, MospiError, _payload(), _sse_json(), GraphUnavailable

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.18
Nodes (12): asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score(), test_default_manager_answer_drops_former_managers() (+4 more)

### Community 106 - "get_sector_fund_ranking_index"
Cohesion: 0.06
Nodes (39): execute_wave(), candidate_sector_names(), get_sector_fund_ranking_index(), top_sector_names(), asks_fund_portfolio_holdings(), asks_funds_holding_stock(), asks_funds_with_sector_exposure(), _clean_stock_capture() (+31 more)

### Community 107 - "parse_rating_screen"
Cohesion: 0.08
Nodes (48): asks_taxonomy(), match_all_fund_types(), fund_naming_clause(), _keep_asked_return(), parse_rating_screen(), rating_screen_question(), _return_direction(), run_rating_list() (+40 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.16
Nodes (14): CategoryMatch, _close(), fund_type_for_category(), _metal_category(), _metal_flags(), _names_a_type(), _phrase_score(), rating_scope_pairs() (+6 more)

### Community 109 - "return_windows.py"
Cohesion: 0.14
Nodes (17): _capability_cache_key(), _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows() (+9 more)

### Community 110 - "lib/portfolio_scope.py"
Cohesion: 0.21
Nodes (13): build_portfolio_scope(), FundRef, _holding_equity_allowed(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest(), load_portfolio_funds() (+5 more)

### Community 111 - "EvidencePack"
Cohesion: 0.10
Nodes (21): EvidencePack, repair_investor_insight_prose(), strip_grounding_holes(), investor_book_cores(), sanitize_data_pack_for_composer(), test_compare_table_shows_the_drawdown_row(), test_screen_table_shows_the_drawdown_column(), test_expense_ratio_meaning_and_judgment_uses_composer() (+13 more)

### Community 112 - "dataclasses"
Cohesion: 0.05
Nodes (81): _adapter(), Cluster, cluster_rows(), cluster_score(), _collapse(), _dedupe(), find(), union() (+73 more)

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
Cohesion: 0.13
Nodes (22): _resolve_bellwether(), rank(), _clean_holding_tokens(), instrument_to_qdrant_names(), match_holding_to_corpus_entity(), resolve_allisin_holdings_path(), load_portfolio_universe(), _aliases_for() (+14 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "get_macro_news"
Cohesion: 0.31
Nodes (6): _cache_has_article_text(), _fresh(), get_macro_news(), _log(), _read(), _write()

### Community 121 - "eval_planner.py"
Cohesion: 0.24
Nodes (4): check(), main(), run_case(), _Usage

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "stitch_display_tables_into_answer"
Cohesion: 0.07
Nodes (32): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers() (+24 more)

### Community 124 - "prompts.py"
Cohesion: 0.25
Nodes (5): build_brief_prompt(), build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 125 - "memory/evidence.py"
Cohesion: 0.10
Nodes (23): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), _take_conversation_slice(), widen_portfolio_args(), clear_conversation(), drain_cache_events(), recall_slice() (+15 more)

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "build_evidence_pack"
Cohesion: 0.05
Nodes (39): _followup_modules(), EvidenceRow, build_evidence_pack(), sector_focus_from_market(), has_second_part(), _wants_end_summary(), asks_one_figure(), ensure_multi_fact_tools() (+31 more)

### Community 128 - "sector_query_for_label"
Cohesion: 0.15
Nodes (4): normalize_sector_label(), sector_query_for_label(), _sector_label_in_text(), SectorFundRankingIndex

### Community 129 - "layer_tools.py"
Cohesion: 0.11
Nodes (23): nifty50_ticker(), _price_holdings(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns(), _read_cache(), scheme_benchmark_metadata() (+15 more)

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

### Community 135 - "test_greeting.py"
Cohesion: 0.27
Nodes (7): greeting_reply(), identity_reply(), _mirror_greeting(), test_fund_question_is_not_greeting_or_identity(), test_hello_mirrors_greeting(), test_main_memory_in_prompt_view(), test_who_are_you_identity()

### Community 136 - "fields.py"
Cohesion: 0.06
Nodes (50): _asks_book(), bind_fields_to_tools(), _book_fields(), fields_from_question(), _fund_fields(), _leave_tools_alone(), _legacy_facts(), planner_field_names() (+42 more)

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
Cohesion: 0.19
Nodes (13): amc_token_in_question(), _category_phrases_in_question(), _constraint_in_scheme_name(), _distinctive_constraints(), pick_best_matching_scheme(), question_amc_hints(), scheme_match_score(), _scheme_name_tokens() (+5 more)

### Community 141 - "apply_task_layer"
Cohesion: 0.16
Nodes (17): apply_task_layer(), _has_peer_screen(), _modules_for(), parse_task_list(), test_aum_without_a_named_fund_is_the_book_total(), test_category_filter_does_not_bind_every_holding(), test_compare_pair_screen_does_not_add_a_peer_screen(), test_compare_reading_adds_large_cap_peer_screen() (+9 more)

### Community 142 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (58): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+50 more)

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

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

### Community 159 - "main.py"
Cohesion: 0.09
Nodes (23): _bucket(), _entity_names(), summarize_errors(), write_error_summary(), reset_run_buffers(), main(), _write_summary(), covered_calendar_days() (+15 more)

### Community 163 - "fund_match.py"
Cohesion: 0.13
Nodes (11): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+3 more)

### Community 169 - "portfolio/client.py"
Cohesion: 0.14
Nodes (16): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), InvalidCRN, PortfolioError, PortfolioNotConfigured, PortfolioUnavailable (+8 more)

### Community 170 - "owned_holding_names"
Cohesion: 0.12
Nodes (23): owned_holding_names(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question(), validate_plan_tools(), _all_holdings_metric_spec() (+15 more)

### Community 174 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

### Community 178 - "validate_capability_args"
Cohesion: 0.14
Nodes (12): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded() (+4 more)

### Community 182 - "test_call_json_llm.py"
Cohesion: 0.40
Nodes (9): _client(), _gemini_response(), _settings(), test_agent_keeps_truncated_tools_without_repair(), test_composer_keeps_truncated_answer_without_a_second_call(), test_gemini_request_includes_response_schema(), test_judge_truncated_json_does_not_repair(), test_salvage_closes_a_cut_off_composer_object() (+1 more)

### Community 183 - "repo_root"
Cohesion: 0.20
Nodes (11): write_ask_market_snapshot(), FiiDiiSnapshot, write_snapshot(), fetch_fii_dii_snapshot(), fetch_all(), main(), write_fii_dii(), write_latest() (+3 more)

### Community 184 - "test_ai_insight_mospi.py"
Cohesion: 0.25
Nodes (10): _client(), _sse(), test_400_is_not_retried(), test_gdp_yoy_uses_prior_fiscal_year(), handler(), test_retries_500_then_reads_cache(), handler(), test_snapshot_keeps_other_entities_when_one_fails() (+2 more)

### Community 185 - "insight_links.py"
Cohesion: 0.13
Nodes (16): aggregate_sectors_from_holdings(), extract_top_holdings(), extract_top_sectors(), normalize_holding_row(), normalize_sector_row(), _portfolio_for_fund_news(), build_insight_links(), _fact() (+8 more)

### Community 186 - "lib/google_news.py"
Cohesion: 0.05
Nodes (32): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+24 more)

### Community 187 - "compare_ask_speed.py"
Cohesion: 0.53
Nodes (4): compare(), _load(), main(), _numbers()

### Community 188 - "query_log.py"
Cohesion: 0.12
Nodes (14): asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), ParsedQuery, attach_query_log_meta(), find_query_log_file() (+6 more)

### Community 191 - "build_derived_views"
Cohesion: 0.19
Nodes (14): clear_cache_for_tests(), seed_portfolio_cache_for_tests(), asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct() (+6 more)

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 193 - "fund_search.py"
Cohesion: 0.10
Nodes (24): _detect_funds(), is_quant_amc_entry(), is_quantum_amc_entry(), _scheme_matches_amc(), _attach_trailing_product(), build_holding_overlap(), _clean_fund_phrase(), collect_fund_phrase_candidates() (+16 more)

### Community 194 - "._ensure_loaded"
Cohesion: 0.12
Nodes (6): detail_has_live_facts(), _expand_query_token(), FundIndex, get_fund_benchmark(), _infer_category_and_type(), resolve_canonical_isin()

### Community 195 - "compare_evidence.py"
Cohesion: 0.24
Nodes (8): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_maybe_run_compare_retries_after_failed_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 197 - "QuestionBrief"
Cohesion: 0.08
Nodes (32): asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), build_question_brief(), _detect_direction(), _detect_funds(), _detect_sector() (+24 more)

### Community 198 - "283041/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 203 - "fund_brief.py"
Cohesion: 0.11
Nodes (30): PortfolioScope, qdrant_filter_names(), _article_entities(), build_events(), cluster_articles(), _cluster_entities(), compose_fund_insight(), _day_key() (+22 more)

### Community 206 - "test_ai_insight.py"
Cohesion: 0.18
Nodes (6): digest_filter(), _holding_mentioned(), matches_entity(), contains_phrase(), test_digest_filter_uses_stricter_scores(), test_sector_exclude_drops_nbfc_from_banks()

### Community 208 - "datetime"
Cohesion: 0.14
Nodes (18): _bars(), catalog_path(), fetch_ohlc(), IndexSpec, load_catalog(), news_sectors_for_index(), OhlcBar, series_is_usable() (+10 more)

### Community 209 - "57e233/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 211 - "fund_type_name_spec"
Cohesion: 0.13
Nodes (16): question_is_standalone_macro(), apply_pure_concept_plan(), question_is_pure_general_concept(), ensure_catalog_tools_for_fund_news(), apply_standalone_macro_scope(), _macro_news_topics(), test_all_holdings_metrics_adds_investor_tool(), test_large_cap_vs_mid_cap_is_pure_concept() (+8 more)

### Community 212 - "c72b25/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 213 - "a45664/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 214 - "test_composer_table_summaries.py"
Cohesion: 0.19
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections()

### Community 217 - "7859f0/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 218 - "test_one_rated_fund_per_category_does_not_fill_with_gold"
Cohesion: 1.00
Nodes (3): test_one_rated_fund_per_category_does_not_fill_with_gold(), fetch(), _row()

### Community 219 - "test_answer_precision.py"
Cohesion: 0.17
Nodes (9): fact_values_already_stated(), question_wants_fact_table(), strip_meta_opening_heading(), _strip_unasked_closers(), test_fact_table_only_for_compare_or_an_explicit_list(), test_fact_table_skipped_when_prose_has_the_figure(), test_next_steps_and_summary_are_removed(), test_specific_lookup_has_no_default_table() (+1 more)

### Community 221 - "news_rag/config.py"
Cohesion: 0.16
Nodes (3): Settings, _repo_root(), _resolve_path()

### Community 222 - "ask_market_bridge.py"
Cohesion: 0.24
Nodes (6): fetch_ask_market_records(), fetch_gold_record(), get_ask_market_snapshot(), test_fetch_ask_market_records_includes_extras(), test_fetch_gold_record_ok(), test_get_ask_market_snapshot_shape()

### Community 224 - "run_ask_engine"
Cohesion: 0.14
Nodes (8): _events(), run_ask_engine(), stream_ask_engine(), run_insight_pipeline(), stream_insight_pipeline(), main(), test_ask_engine_delegates_to_insight_pipeline(), test_streaming_sse_order()

### Community 225 - "insights.js"
Cohesion: 0.24
Nodes (16): api(), arrow(), bars(), card(), chart(), diverging(), headers(), istTime() (+8 more)

### Community 227 - "insight_log.js"
Cohesion: 0.70
Nodes (4): api(), esc(), headers(), load()

### Community 232 - "rank_funds_by_sector_exposure"
Cohesion: 0.42
Nodes (5): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships()

### Community 237 - "strip_news_roundup"
Cohesion: 0.33
Nodes (6): append_news_section(), _insert_before_disclaimer(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 239 - "csv"
Cohesion: 0.28
Nodes (3): sector_query_gaps(), main(), main()

### Community 240 - "run_insights_daily.sh"
Cohesion: 0.50
Nodes (4): note(), PYTHONPATH, PYTHONUNBUFFERED, run_insights_daily.sh script

### Community 241 - "data_pack.py"
Cohesion: 0.32
Nodes (4): build_data_pack(), build(), _compact(), test_data_pack_groups_by_fund_and_hides_internal_fields()

### Community 255 - "test_rupeestop_auth.py"
Cohesion: 0.18
Nodes (7): rupeestop_admin_request_headers(), _jwt(), test_admin_headers_include_bearer(), test_admin_headers_use_token_from_login(), test_bearer_prefers_auth_token_over_admin_token(), test_non_admin_url_has_no_authorization(), test_valid_jwt_does_not_call_login()

## Knowledge Gaps
- **22 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+17 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1912 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **55 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `fund_rating_screen.py`, `update.py`, `node_compose`, `fields.py`, `GraphState`, `plan_enforce.py`, `apply_task_layer`, `test_fund_drawdown.py`, `test_fund_name_gate_and_hydrate.py`, `QueryLogger`, `macro_data.py`, `project_modules`, `fund_display.py`, `pack_sanitize.py`, `plan_enforce.py`, `task_exec.py`, `insight/portfolio_scope.py`, `owned_holding_names`, `plan.py`, `portfolio_news_impact.py`, `ToolCall`, `app.py`, `gold_service.py`, `_attach_rs_ratings_to_screen`, `investor_subject.py`, `contracts.py`, `query_log.py`, `test_fund_risk.py`, `build_derived_views`, `compare_evidence.py`, `QuestionBrief`, `display_table_policy.py`, `fact_answer.py`, `fund_type_name_spec`, `test_composer_table_summaries.py`, `test_portfolio_allocation.py`, `test_metal_fund_rating.py`, `test_answer_precision.py`, `test_answer_quality_logs.py`, `evidence_pack.py`, `test_news_only_answer.py`, `enrich_manager_payload`, `parse_rating_screen`, `return_windows.py`, `EvidencePack`, `build_evidence_pack`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `ExecutionPlan` (e.g. with `news_calls_for_book()` and `sector_book()`) actually correct?**
  _`ExecutionPlan` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _22 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.07971014492753623 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ToolCall` to `fund_rating_screen.py`, `update.py`, `fields.py`, `GraphState`, `plan_enforce.py`, `apply_task_layer`, `test_fund_drawdown.py`, `test_fund_name_gate_and_hydrate.py`, `macro_data.py`, `project_modules`, `pack_sanitize.py`, `plan_enforce.py`, `task_exec.py`, `insight/portfolio_scope.py`, `portfolio/client.py`, `owned_holding_names`, `plan.py`, `portfolio_news_impact.py`, `gold_service.py`, `investor_subject.py`, `contracts.py`, `executor.py`, `test_fund_risk.py`, `build_derived_views`, `compare_evidence.py`, `_return_slice_covers`, `QuestionBrief`, `display_table_policy.py`, `fund_type_name_spec`, `ExecutionPlan`, `test_portfolio_allocation.py`, `test_metal_fund_rating.py`, `test_answer_quality_logs.py`, `evidence_pack.py`, `test_news_only_answer.py`, `get_sector_fund_ranking_index`, `parse_rating_screen`, `return_windows.py`, `memory/evidence.py`, `build_evidence_pack`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ToolCall` (e.g. with `news_calls_for_book()` and `_apply_planner_request()`) actually correct?**
  _`ToolCall` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `sources/google_news.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1396011396011396 - nodes in this community are weakly interconnected._