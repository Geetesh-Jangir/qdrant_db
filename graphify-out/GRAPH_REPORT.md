# Graph Report - db_design_with_qdrant_locally  (2026-11-16)

## Corpus Check
- 980 files · ~1,801,435 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 85 file(s) not represented in the graph (top: .log 42, .jsonl 21, .example 6)

## Summary
- 6811 nodes · 22086 edges · 244 communities (187 shown, 57 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 767 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3b55ab7e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- NewsStore
- fund_rating_screen.py
- interpret.py
- load_config
- market_driver_digest/run.py
- update.py
- node_compose
- test_ask_speed.py
- Settings
- clarify_plan_if_fund_unknown
- fund_context.py
- load_config
- compute.py
- v2_scoring.py
- tools.py
- bullion_retrieve.py
- test_fund_name_gate_and_hydrate.py
- QueryLogger
- news_reader.py
- macro_data.py
- runner.py
- jev/client.py
- typing
- tool_runners.py
- sector_leaderboard/run.py
- fund_display.py
- gather.py
- resolve_fund_for_query
- plan_enforce.py
- nse_fii_dii.py
- infer_fund_news_layers
- Settings
- task_exec.py
- llm_client.py
- affected_sectors.py
- .lookup_extracted_fund
- test_portfolio_layer.py
- pack_sanitize.py
- test_fund_rating_screen.py
- env
- fund_drawdown.py
- article_quality.py
- plan.py
- macro_news_cache.py
- env
- macro_impact_map.py
- portfolio_news_impact.py
- ExecutionPlan
- fund_catalog.py
- app.py
- gold_service.py
- env
- investor_subject.py
- fund_rupeestop_metrics.py
- contracts.py
- test_sector_leaderboard_run.py
- scrape-worker/package.json
- collect_fund_phrase_candidates
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
- Envelope
- call_json_llm
- stock_fund_ranking.py
- get_settings
- display_table_policy.py
- Any
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- sector_fund_ranking.py
- qdrant_access.py
- test_compare_pair_category.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- sector_alignment.py
- run_ask_engine
- env
- steps
- evidence_pack.py
- normalize_rs_label
- NumericRecord
- test_snapshot_uses_payload_returns_and_history_only_for_gaps
- build_evidence_pack
- _fund_performance_digest
- GraphUnavailable
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- get_sector_fund_ranking_index
- explicit_fund_count
- fund_rating_categories.py
- return_windows.py
- lib/portfolio_scope.py
- EvidencePack
- entity_retrieval.py
- news_digest.py
- build_derived_views
- vitest
- format_inr
- render_drawdown_body
- compilerOptions
- compilerOptions
- strip_missing_data_caveats
- synthesize_tasks
- backfill
- fund_scheme_match.py
- shared_system_prefix
- memory/evidence.py
- run-pipeline
- ToolCall
- ask_market_bridge.py
- layer_tools.py
- worker/src/index.ts
- steps
- steps
- with
- json
- test_greeting.py
- fields.py
- inputs
- with
- inputs
- aggregate_fund_holdings.py
- ensure_registry
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
- RunLogger
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- rank_funds_by_sector_exposure
- owned_holding_names
- diagnose_lightsail_site.sh
- get_stock_profile
- validate_capability_args
- EntityFunnel
- trends.py
- test_screen_rating_screen_arg.py
- ask_plan.py
- repo_root
- test_ai_insight_mospi.py
- insight_links.py
- sources/google_news.py
- compare_evidence.py
- query_log.py
- extract.py
- output_judge.py
- metals_spot_tables.py
- node_compose
- query_plan.py
- market_scope_entities
- QuestionBrief
- 283041/manifest.json
- fund_brief.py
- test_ai_insight.py
- datetime
- 57e233/manifest.json
- concept_asks.py
- c72b25/manifest.json
- a45664/manifest.json
- RunArtifacts
- 7859f0/manifest.json
- _run_screen_funds_by_exposure
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- test_admin_headers_use_token_from_login
- test_failed_login_keeps_previous_token
- pack_trim.py
- _unhandled_exception_handler
- LLMUsageRecord
- insights.js
- insight_log.js
- fact_slots.py
- planner_catalog_knowledge.py
- multi_fact.py
- _return_direction
- run_insights_daily.sh
- install-insights-cron.sh

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 607 edges
2. `ToolCall` - 367 edges
3. `get_settings()` - 143 edges
4. `apply_planner_post_hooks()` - 123 edges
5. `AnswerMode` - 108 edges
6. `node_compose()` - 102 edges
7. `QueryLogger` - 100 edges
8. `load_config()` - 90 edges
9. `QuestionBrief` - 88 edges
10. `Settings` - 86 edges

## Surprising Connections (you probably didn't know these)
- `test_400_is_not_retried()` --uses--> `MospiError`  [INFERRED]
  tests/test_ai_insight_mospi.py → ai_insight/data/macro_data.py
- `_check_plan()` --uses--> `ExecutionPlan`  [INFERRED]
  scripts/eval_basic_queries.py → news_rag/insight/contracts.py
- `_live_plan()` --uses--> `ExecutionPlan`  [INFERRED]
  scripts/eval_basic_queries.py → news_rag/insight/contracts.py
- `_modules()` --uses--> `ExecutionPlan`  [INFERRED]
  scripts/eval_basic_queries.py → news_rag/insight/contracts.py
- `fetch_google_news()` --uses--> `GoogleBlockedError`  [INFERRED]
  news_pipeline/graph/nodes/fetch_google_news.py → lib/google_guard.py

## Import Cycles
- 2-file cycle: `ai_insight/common/entity_retrieval.py -> ai_insight/common/retrieval_plan.py -> ai_insight/common/entity_retrieval.py`

## Communities (244 total, 57 thin omitted)

### Community 0 - "logging"
Cohesion: 0.10
Nodes (37): get_encoder(), get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match() (+29 more)

### Community 1 - "NewsStore"
Cohesion: 0.08
Nodes (11): _to_article(), EntityScore, StoredArticle, merge_stored_article(), payload_to_stored(), _datetime_range(), NewsStore, point_id_for_url() (+3 more)

### Community 2 - "fund_rating_screen.py"
Cohesion: 0.07
Nodes (41): categories_for(), pickable_categories(), _add_category_comparison(), _alternate_row_excluded(), _amc_matches(), _amc_outside_label(), _amc_token(), _apply_category_difference() (+33 more)

### Community 3 - "interpret.py"
Cohesion: 0.08
Nodes (63): asks_sector_lists(), QuestionBrief, Findings, FundFinding, SectorFinding, EvidenceSet, _article_context_for_interpret(), _assemble() (+55 more)

### Community 4 - "load_config"
Cohesion: 0.05
Nodes (79): _bool(), CommonConfig, _float(), _freshness_flag(), _int(), load_config(), market_numbers(), news_map_block() (+71 more)

### Community 5 - "market_driver_digest/run.py"
Cohesion: 0.06
Nodes (46): fmt_pct(), MarketDriverFactsBase, fmt_ist(), _resolve_end(), rolling_window(), session_window(), to_ist(), week_window() (+38 more)

### Community 6 - "update.py"
Cohesion: 0.13
Nodes (22): drop_old_turns(), compare_payload_matches_funds(), push_recent_fund_focus(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), empty_frame(), empty_state() (+14 more)

### Community 7 - "node_compose"
Cohesion: 0.08
Nodes (22): asks_computed_illustration(), facts_only_compose_allowed(), asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), has_second_part(), meaning_reply(), _normalize_term() (+14 more)

### Community 8 - "test_ask_speed.py"
Cohesion: 0.05
Nodes (40): analyst_should_run(), collect_evidence_calendar_dates(), add_article(), cores_in_text(), finalize_text_fields(), format_user_calendar_date(), mentions_publication_date(), number_is_grounded() (+32 more)

### Community 9 - "Settings"
Cohesion: 0.07
Nodes (36): _subprocess(), _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), article_in_fetch_window(), google_time_query(), has_news_date_range() (+28 more)

### Community 10 - "clarify_plan_if_fund_unknown"
Cohesion: 0.10
Nodes (23): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), question_wants_gold_table(), clarify_plan_if_fund_unknown(), _plan_uses_fund_scoped_tools(), question_refers_deictic_fund_safe() (+15 more)

### Community 11 - "fund_context.py"
Cohesion: 0.05
Nodes (57): _metal_fund_categories(), _bound_fund_name(), _compare_sides_resolvable(), _known_names_in_text(), single_fund_for_deictic(), fund_authorized_for_question(), _resolve_funds(), resolve_deictic_fund_name() (+49 more)

### Community 12 - "load_config"
Cohesion: 0.06
Nodes (51): _all_dates(), _bundle_is_live(), create_router(), daily(), dates(), generate(), health(), job_latest() (+43 more)

### Community 13 - "compute.py"
Cohesion: 0.08
Nodes (41): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+33 more)

### Community 14 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (56): run_driver_affected_funds_adapter(), DataNeed, _active_sector_equity(), _articles_for_affected_question(), _as_date(), asks_equity_funds(), _attach_screen_facts(), _one() (+48 more)

### Community 16 - "bullion_retrieve.py"
Cohesion: 0.12
Nodes (8): _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), describe_filters_for_log(), _point_row(), QdrantReader

### Community 17 - "test_fund_name_gate_and_hydrate.py"
Cohesion: 0.12
Nodes (24): _load_planner_memory(), _store_turn_memory(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view() (+16 more)

### Community 18 - "QueryLogger"
Cohesion: 0.11
Nodes (6): slots_from_plan(), clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest()

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (39): _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority(), _clean_claims(), _clean_sector_calls() (+31 more)

### Community 20 - "macro_data.py"
Cohesion: 0.12
Nodes (28): BondYieldResult, _client(), _codes(), walk(), CPIRecord, fetch_bond_yields(), fetch_cpi(), fetch_gdp() (+20 more)

### Community 21 - "runner.py"
Cohesion: 0.09
Nodes (43): main(), _append(), _clock(), RunLog, _write(), _bound_llm(), bundle_cli_main(), cli_main() (+35 more)

### Community 22 - "jev/client.py"
Cohesion: 0.19
Nodes (13): _entity_state(), _score_entity_titles(), _score_new_entities(), JevClient, JevError, _parse_token_usage(), read_choice(), read_noul() (+5 more)

### Community 23 - "typing"
Cohesion: 0.06
Nodes (38): _merge_publisher_error_reasons(), write_day_report(), _bucket(), _entity_names(), summarize_errors(), write_error_summary(), _atomic_write(), day_failure_slices_for_run() (+30 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.10
Nodes (45): build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+37 more)

### Community 25 - "sector_leaderboard/run.py"
Cohesion: 0.06
Nodes (64): sector_label(), SectorLeaderboardFactsBase, SectorFetch, _block(), build_user(), _abs_scores(), backtest(), _cell() (+56 more)

### Community 26 - "fund_display.py"
Cohesion: 0.04
Nodes (76): append_news_section(), _as_float(), assemble_fund_overview_answer(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown() (+68 more)

### Community 27 - "gather.py"
Cohesion: 0.08
Nodes (33): build_data_pack(), build(), _compact(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), EvidenceItem (+25 more)

### Community 28 - "resolve_fund_for_query"
Cohesion: 0.12
Nodes (22): _detect_funds(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), resolve_fund_for_query(), resolve_fund_from_question(), test_absl_and_ppfas_shorthand(), test_absl_conservative_hybrid_active_fof() (+14 more)

### Community 29 - "plan_enforce.py"
Cohesion: 0.04
Nodes (87): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), asks_balanced_long_horizon_fund_menu(), asks_category_performance(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition() (+79 more)

### Community 30 - "nse_fii_dii.py"
Cohesion: 0.19
Nodes (10): FlowLeg, _bucket(), _httpx_json(), _impit_json(), _leg(), _log_external(), _nse_json(), _num() (+2 more)

### Community 31 - "infer_fund_news_layers"
Cohesion: 0.24
Nodes (7): infer_fund_news_layers(), layers_to_retrieval_keys(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only(), test_overview_news_is_holdings_and_sectors()

### Community 32 - "Settings"
Cohesion: 0.07
Nodes (34): Publisher, SectorQuery, Settings, is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), finish_run_logger() (+26 more)

### Community 33 - "task_exec.py"
Cohesion: 0.17
Nodes (22): bind_subjects(), _book_total_line(), _cell(), coverage_line(), _fact_label(), _fmt(), _funds_from_pack(), _holding_for_category() (+14 more)

### Community 34 - "llm_client.py"
Cohesion: 0.10
Nodes (32): anthropic_cache_control(), anthropic_system_blocks(), _call_anthropic(), _call_deepseek(), _call_gemini(), call_insight_llm(), _call_insight_llm_body(), _invoke() (+24 more)

### Community 35 - "affected_sectors.py"
Cohesion: 0.16
Nodes (13): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+5 more)

### Community 36 - ".lookup_extracted_fund"
Cohesion: 0.11
Nodes (8): detail_has_live_facts(), _entry_matches_amc(), _expand_query_token(), FundIndex, get_fund_benchmark(), _infer_category_and_type(), resolve_canonical_isin(), _sync_amc_prefix_from_catalog()

### Community 37 - "test_portfolio_layer.py"
Cohesion: 0.06
Nodes (45): question_wants_invested_value_table(), fetch_top_holdings(), project_concentration(), aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values() (+37 more)

### Community 38 - "pack_sanitize.py"
Cohesion: 0.09
Nodes (32): attach_drawback_digest(), build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), _pretty_category(), question_asks_portfolio_level_drawdown() (+24 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.09
Nodes (45): asks_taxonomy(), parse_rating_screen(), run_rating_list(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap(), fetch(), test_a_one_month_performer_is_shown_beside_the_same_category_rating() (+37 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "fund_drawdown.py"
Cohesion: 0.20
Nodes (16): _add_drawdown_call(), attach_screen_drawdown(), average_peer_drawdown(), compare_drawdown_rows(), fetch_drawdown_periods(), fetch_trailing_drawdown(), load_fund_drawdown(), _money() (+8 more)

### Community 42 - "article_quality.py"
Cohesion: 0.11
Nodes (23): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+15 more)

### Community 43 - "plan.py"
Cohesion: 0.09
Nodes (25): explanation_brief(), field_prompt_table(), mentions_advice(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), _label_for_days() (+17 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.11
Nodes (23): _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), _search_macro_parameters() (+15 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "macro_impact_map.py"
Cohesion: 0.14
Nodes (17): _rule_sector_picks(), _rule_sector_picks(), canonical_direction_for_driver(), clear_macro_impact_cache(), _document(), _driver_row(), list_macro_drivers(), macro_impact_entry() (+9 more)

### Community 47 - "portfolio_news_impact.py"
Cohesion: 0.10
Nodes (26): book_wide_sectors(), _display_name(), _has_named_stock(), news_calls_for_book(), _news_name(), _pct(), resolve_book_sector(), sector_book() (+18 more)

### Community 48 - "ExecutionPlan"
Cohesion: 0.04
Nodes (78): ExecutionPlan, plan_targets_single_fund_measured_return(), question_asks_category_book_share(), question_asks_category_money(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings(), _ensure_portfolio_data_for_compare() (+70 more)

### Community 49 - "fund_catalog.py"
Cohesion: 0.14
Nodes (19): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+11 more)

### Community 50 - "app.py"
Cohesion: 0.06
Nodes (60): ask(), ask_memory(), ask_query_log(), ask_sources(), ask_stream(), _events(), AskRequest, _attach_llm_meta() (+52 more)

### Community 51 - "gold_service.py"
Cohesion: 0.14
Nodes (18): _fetch(), get_gold_snapshot(), get_silver_snapshot(), gold_horizon_code(), gold_macro_series_row(), _load_payload(), _merged_series(), add() (+10 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "investor_subject.py"
Cohesion: 0.05
Nodes (70): question_is_standalone_macro(), _categories_equivalent(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_deictic_and_memory_primary_fund(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan() (+62 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (20): asks_fund_category_average(), build_comparison_periods(), expense_ratio_for_question(), _f(), fund_returns_from_detail(), normalize_category_average_returns(), normalize_vs_benchmark_payload(), _optional_number() (+12 more)

### Community 55 - "contracts.py"
Cohesion: 0.03
Nodes (82): rating_list_plan(), rating_concept_plan(), ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), AnswerMode (+74 more)

### Community 56 - "test_sector_leaderboard_run.py"
Cohesion: 0.08
Nodes (48): _add_usage(), _default_call(), format_articles_block(), generate_json(), _invoke_with_retry(), LlmJsonResult, LlmSchemaError, LlmUnavailable (+40 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "collect_fund_phrase_candidates"
Cohesion: 0.13
Nodes (17): labels_name_the_same_scheme(), _attach_trailing_product(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _entry_matches_query_scheme(), _extend_amc_phrase_tail() (+9 more)

### Community 59 - "executor.py"
Cohesion: 0.05
Nodes (62): load_fund_risk(), rating_for_request(), rating_needs_pillars(), fetch_vs_benchmark(), merge_fund_insight_metrics(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics() (+54 more)

### Community 60 - "test_fund_risk.py"
Cohesion: 0.06
Nodes (58): asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison() (+50 more)

### Community 61 - "graph.py"
Cohesion: 0.07
Nodes (39): RequestTelemetry, _answer_stream_chunks(), _attach_conversation(), build_result(), _catalog_fanout_fund_names(), _conversation_id(), _ensure_portfolio_for_fund_news(), GraphState (+31 more)

### Community 62 - "typing"
Cohesion: 0.05
Nodes (51): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), embed_query(), embed_query(), warmup_query_vectors(), _fetch_macro_news() (+43 more)

### Community 63 - "re"
Cohesion: 0.07
Nodes (31): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+23 more)

### Community 64 - "nav_service.py"
Cohesion: 0.18
Nodes (13): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+5 more)

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
Cohesion: 0.10
Nodes (21): candidates_block(), entity_candidates(), _holding_candidates(), _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known(), guard_reply() (+13 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "embed.py"
Cohesion: 0.15
Nodes (8): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, _build_encoder(), embeddings_ready(), main()

### Community 71 - "portfolio/cache.py"
Cohesion: 0.07
Nodes (33): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), get_active_crn(), get_normalized_portfolio(), peek_derived(), preload_configured_portfolio() (+25 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "fund_portfolio_news.py"
Cohesion: 0.19
Nodes (11): corpus_entity_names(), _fetch_holding_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news(), _sector_entities() (+3 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "Envelope"
Cohesion: 0.05
Nodes (74): build(), compose(), _cards(), _build(), _user(), Signal, _data(), _dump() (+66 more)

### Community 77 - "call_json_llm"
Cohesion: 0.24
Nodes (15): _blocks_to_parts(), call_json_llm(), _model_for(), _composer_partial_usable(), _summarize_parsed_for_log(), _client(), _gemini_response(), _settings() (+7 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.19
Nodes (14): extract_top_holdings(), _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file() (+6 more)

### Community 79 - "get_settings"
Cohesion: 0.14
Nodes (21): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+13 more)

### Community 80 - "display_table_policy.py"
Cohesion: 0.07
Nodes (27): DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), fact_values_already_stated(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary() (+19 more)

### Community 81 - "Any"
Cohesion: 0.13
Nodes (17): headline_rating(), aggregate_sectors_from_holdings(), _clean_company_name(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers(), _fund_text(), _named_weights() (+9 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.08
Nodes (55): pending_rating_line(), _age(), _allocation_bucket_rows(), _as_of(), _asks_portfolio_rs_ratings(), _book_line(), _category_amount_map(), _comparison_rows() (+47 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "sector_fund_ranking.py"
Cohesion: 0.09
Nodes (14): classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path(), sector_ranking_data_available() (+6 more)

### Community 86 - "qdrant_access.py"
Cohesion: 0.10
Nodes (29): is_stale(), newest_scraped_at(), _as_dict(), _client(), _drop(), _entity_view(), EntityRowsResult, _explode() (+21 more)

### Community 87 - "test_compare_pair_category.py"
Cohesion: 0.15
Nodes (12): metal_scheme_categories(), _compare_fund_count(), finalize_unnamed_catalog_compare(), pick_random_scheme_category_for_compare(), _split_count(), test_debt_type_picks_a_debt_scheme_category(), test_finalize_rewrites_debt_type_to_a_scheme_category(), test_finalize_splits_count_across_planner_categories() (+4 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.14
Nodes (19): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+11 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 90 - "sector_alignment.py"
Cohesion: 0.12
Nodes (22): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), extract_top_sectors(), analyze_sector_block(), canonical_sector_for_holding() (+14 more)

### Community 91 - "run_ask_engine"
Cohesion: 0.20
Nodes (5): run_ask_engine(), stream_ask_engine(), run_insight_pipeline(), stream_insight_pipeline(), test_ask_engine_delegates_to_insight_pipeline()

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.05
Nodes (69): render_pillar_marks_table(), build_holding_overlap(), _holding_overlap_key(), _add_category_comparison(), append_investor_portfolio_overview_tables(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line() (+61 more)

### Community 96 - "normalize_rs_label"
Cohesion: 0.14
Nodes (16): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), pick_funds_by_label_cascade(), pick_rows_by_label_cascade() (+8 more)

### Community 97 - "NumericRecord"
Cohesion: 0.20
Nodes (15): NumericRecord, unavailable(), fetch_cpi_record(), pick(), fetch_gdp_record(), fetch_gsec(), fetch_gst(), fetch_iip_record() (+7 more)

### Community 99 - "build_evidence_pack"
Cohesion: 0.09
Nodes (21): fetch_public_rating(), _news_subject(), _attach_rs_ratings_to_screen(), _one(), build_evidence_pack(), _refresh_fund_blocks_ratings(), sector_focus_from_market(), clean_news_insight() (+13 more)

### Community 100 - "_fund_performance_digest"
Cohesion: 0.38
Nodes (4): _fund_performance_digest(), prefers_planner_over_slot(), test_fund_news_does_not_force_planner(), test_performance_digest_from_snapshot()

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.17
Nodes (13): _rating_lead_for_pack(), asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score() (+5 more)

### Community 106 - "get_sector_fund_ranking_index"
Cohesion: 0.07
Nodes (37): execute_wave(), get_sector_fund_ranking_index(), primary_sector_for_question(), asks_fund_portfolio_holdings(), asks_funds_holding_stock(), asks_funds_with_sector_exposure(), _clean_stock_capture(), phrase_looks_like_sector_reference() (+29 more)

### Community 107 - "explicit_fund_count"
Cohesion: 0.14
Nodes (11): _category_fund_name_spec(), fund_naming_clause(), _label_in(), _looks_like_fund_list(), _metal_fund_spec(), rating_screen_question(), _return_window(), _suggestion_spec() (+3 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.14
Nodes (16): CategoryMatch, _close(), fund_type_for_category(), match_all_fund_types(), _metal_category(), _metal_flags(), _names_a_type(), _phrase_score() (+8 more)

### Community 109 - "return_windows.py"
Cohesion: 0.16
Nodes (15): _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows(), window_label() (+7 more)

### Community 110 - "lib/portfolio_scope.py"
Cohesion: 0.08
Nodes (36): build_portfolio_scope(), _clean_holding_tokens(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc() (+28 more)

### Community 111 - "EvidencePack"
Cohesion: 0.09
Nodes (24): EvidencePack, strip_grounding_holes(), cores_for_float(), derived_cores(), investor_book_cores(), sanitize_data_pack_for_composer(), test_evidence_pack_compact_includes_table_summaries(), test_compare_table_shows_the_drawdown_row() (+16 more)

### Community 112 - "entity_retrieval.py"
Cohesion: 0.05
Nodes (69): _adapter(), Cluster, cluster_rows(), cluster_score(), _collapse(), _dedupe(), find(), union() (+61 more)

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 114 - "build_derived_views"
Cohesion: 0.13
Nodes (20): build_insights(), _equity_pct(), Insight, insight_lines(), insights_for_brief(), _num(), _style_band(), asset_bucket() (+12 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 117 - "render_drawdown_body"
Cohesion: 0.19
Nodes (14): collapse_episodes(), investment_amount(), _period_heading(), render_drawdown_body(), _rupee_line(), rupee_loss(), _open_episode(), _recovered_episode() (+6 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "strip_missing_data_caveats"
Cohesion: 0.15
Nodes (10): strip_missing_data_caveats(), strip_private_leaks(), test_a_rating_pick_does_not_apologise_for_returns_or_pillars(), test_missing_apology_and_private_leak_are_removed(), test_strip_removes_risk_trend_apology(), test_a_top_five_apology_is_removed(), test_each_holding_keeps_the_article_text_not_only_one_headline(), test_grouped_news_keeps_the_article_body() (+2 more)

### Community 121 - "synthesize_tasks"
Cohesion: 0.17
Nodes (10): _spaced_category_words(), _canon_fact(), _category_in_planner_text(), _compare_subject_kind(), _facts_from_plan(), _owned_fund_names(), parse_task_list(), synthesize_tasks() (+2 more)

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "fund_scheme_match.py"
Cohesion: 0.15
Nodes (18): amc_token_in_question(), _category_phrases_in_question(), _constraint_in_scheme_name(), _distinctive_constraints(), pick_best_matching_scheme(), question_amc_hints(), scheme_match_score(), _scheme_matches_amc() (+10 more)

### Community 124 - "shared_system_prefix"
Cohesion: 0.24
Nodes (7): build_anthropic_messages_body(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), _body(), test_planner_and_composer_share_the_first_system_block(), test_tools_stay_available_when_there_is_no_shared_prefix()

### Community 125 - "memory/evidence.py"
Cohesion: 0.12
Nodes (24): widen_portfolio_args(), clear_conversation(), drain_cache_events(), recall_slice(), recall_wider_portfolio(), remember_slice(), slice_key(), slice_slot() (+16 more)

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "ToolCall"
Cohesion: 0.03
Nodes (79): ensure_quality_fund_list(), ensure_rating_screen(), _followup_modules(), _install_suggestion_screen(), _keep_followup_plan(), ToolCall, ensure_compare_template(), ensure_multi_fact_tools() (+71 more)

### Community 128 - "ask_market_bridge.py"
Cohesion: 0.14
Nodes (11): fetch_ask_market_records(), fetch_gold_record(), get_ask_market_snapshot(), run_macro_series_tool(), test_fetch_ask_market_records_includes_extras(), test_fetch_gold_record_ok(), test_get_ask_market_snapshot_shape(), test_macro_series_gold_uses_india_series() (+3 more)

### Community 129 - "layer_tools.py"
Cohesion: 0.12
Nodes (22): nifty50_ticker(), _price_holdings(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns(), _read_cache(), scheme_benchmark_metadata() (+14 more)

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
Cohesion: 0.04
Nodes (41): notify_failure(), explain(), main(), _short(), main(), prune_insight_logs(), ingest_ready(), main() (+33 more)

### Community 135 - "test_greeting.py"
Cohesion: 0.27
Nodes (7): greeting_reply(), identity_reply(), _mirror_greeting(), test_fund_question_is_not_greeting_or_identity(), test_hello_mirrors_greeting(), test_main_memory_in_prompt_view(), test_who_are_you_identity()

### Community 136 - "fields.py"
Cohesion: 0.06
Nodes (42): _asks_book(), bind_fields_to_tools(), _book_fields(), canonicalize_field(), field_need(), FieldNeed, fields_from_question(), _find_term() (+34 more)

### Community 137 - "inputs"
Cohesion: 0.29
Nodes (7): default, description, required, type, holdings_limit, workflow_dispatch, inputs

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "aggregate_fund_holdings.py"
Cohesion: 0.20
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 141 - "ensure_registry"
Cohesion: 0.11
Nodes (24): plan_to_brief(), tools_to_facets(), all_tools(), _eligible(), ensure_registry(), pick_tool_for_facet(), registry_prompt_block(), tools_providing() (+16 more)

### Community 142 - "test_fund_drawdown.py"
Cohesion: 0.15
Nodes (27): asks_category_drawdown(), drawdown_words(), ensure_drawdown_tools(), is_drawdown_definition(), _named_standard_periods(), periods_for_question(), _question_needs_drawdown(), requested_fund_facts() (+19 more)

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

### Community 163 - "fund_match.py"
Cohesion: 0.15
Nodes (10): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), load_fund_embedding_cache(), _normalize_fund_text() (+2 more)

### Community 169 - "rank_funds_by_sector_exposure"
Cohesion: 0.29
Nodes (6): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), rank_funds_by_sector_exposure()

### Community 170 - "owned_holding_names"
Cohesion: 0.23
Nodes (14): owned_holding_names(), _all_holdings_metric_spec(), _fund_data_from_results(), _investor_holdings_rating_rows(), _metric_cell(), render_all_holdings_metric_table(), render_all_holdings_return_table(), render_all_holdings_sector_table() (+6 more)

### Community 174 - "get_stock_profile"
Cohesion: 0.25
Nodes (4): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker()

### Community 178 - "validate_capability_args"
Cohesion: 0.15
Nodes (11): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded() (+3 more)

### Community 180 - "trends.py"
Cohesion: 0.13
Nodes (14): detect_signals(), _surge(), DayPoint, entity_daily_series(), price_trend(), price_trend_from_closes(), PriceTrend, session_day() (+6 more)

### Community 181 - "test_screen_rating_screen_arg.py"
Cohesion: 0.24
Nodes (7): test_finalize_screen_adds_returns_for_compare_question(), fake_detail(), get_fund_detail(), test_rating_screen_uses_focus_question_not_full_compare_question(), test_rating_screen_uses_forced_category_spec(), fake_fetch(), test_validate_capability_args_keeps_rating_screen()

### Community 182 - "ask_plan.py"
Cohesion: 0.24
Nodes (9): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), test_ask_plan_keeps_rich_agent_fields(), test_cluster_prefers_larger_groups() (+1 more)

### Community 183 - "repo_root"
Cohesion: 0.20
Nodes (12): write_ask_market_snapshot(), FiiDiiSnapshot, _cache_dir(), write_snapshot(), fetch_fii_dii_snapshot(), fetch_fii_dii(), numeric_from_fii_dii_snapshot(), fetch_all() (+4 more)

### Community 184 - "test_ai_insight_mospi.py"
Cohesion: 0.25
Nodes (10): _client(), _sse(), test_400_is_not_retried(), test_gdp_yoy_uses_prior_fiscal_year(), handler(), test_retries_500_then_reads_cache(), handler(), test_snapshot_keeps_other_entities_when_one_fails() (+2 more)

### Community 185 - "insight_links.py"
Cohesion: 0.21
Nodes (11): normalize_holding_row(), normalize_sector_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows() (+3 more)

### Community 186 - "sources/google_news.py"
Cohesion: 0.04
Nodes (36): _backoff(), _consent_jar(), fetch_url(), _handle_google_response(), make_session(), post_url(), _proxy(), _retry_after_seconds() (+28 more)

### Community 187 - "compare_evidence.py"
Cohesion: 0.24
Nodes (8): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_maybe_run_compare_retries_after_failed_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 188 - "query_log.py"
Cohesion: 0.14
Nodes (12): ParsedQuery, attach_query_log_meta(), find_query_log_file(), new_fund_brief_logger(), new_query_logger(), query_log_page_href(), read_query_log(), main() (+4 more)

### Community 190 - "extract.py"
Cohesion: 0.36
Nodes (5): _authors(), _clean(), extract_article(), _meta(), _meta_fallback()

### Community 191 - "output_judge.py"
Cohesion: 0.31
Nodes (4): judge_answer(), JudgeResult, _scores_usable(), _thresholds()

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 193 - "node_compose"
Cohesion: 0.08
Nodes (29): asks_ideal_portfolio_shape(), balanced_portfolio_examples_spec(), question_asks_current_book_allocation(), _asks_ideal_portfolio_allocation(), maybe_install_balanced_portfolio_screen(), _plan_asks_investor_book_allocation(), _reroute_book_allocation_data_need(), apply_portfolio_intent() (+21 more)

### Community 195 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

### Community 197 - "QuestionBrief"
Cohesion: 0.08
Nodes (29): asks_random_fund_compare(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief(), _detect_direction(), _detect_funds(), _heuristic_brief() (+21 more)

### Community 198 - "283041/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 203 - "fund_brief.py"
Cohesion: 0.09
Nodes (34): PortfolioScope, qdrant_filter_names(), Settings, _article_entities(), build_events(), cluster_articles(), _cluster_entities(), compose_fund_insight() (+26 more)

### Community 206 - "test_ai_insight.py"
Cohesion: 0.18
Nodes (6): digest_filter(), _holding_mentioned(), matches_entity(), contains_phrase(), test_digest_filter_uses_stricter_scores(), test_sector_exclude_drops_nbfc_from_banks()

### Community 208 - "datetime"
Cohesion: 0.17
Nodes (16): week_index_movers(), _bars(), catalog_path(), fetch_ohlc(), IndexSpec, load_catalog(), OhlcBar, series_is_usable() (+8 more)

### Community 209 - "57e233/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 211 - "concept_asks.py"
Cohesion: 0.17
Nodes (17): fund_type_name_spec(), apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), apply_pure_concept_plan(), question_is_pure_general_concept() (+9 more)

### Community 212 - "c72b25/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 213 - "a45664/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 214 - "RunArtifacts"
Cohesion: 0.15
Nodes (10): current_artifacts(), _env_secrets(), log_external(), prune_logs(), _redact(), _redact_text(), _rmtree(), RunArtifacts (+2 more)

### Community 217 - "7859f0/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 218 - "_run_screen_funds_by_exposure"
Cohesion: 0.13
Nodes (12): _allocation_mix_spec(), asks_rating_list(), _cascade_labels_for_spec(), fetch_category_ratings(), _make_balanced_portfolio_spec(), _order(), rating_spec_for_forced_screen(), RatingScreenSpec (+4 more)

### Community 225 - "insights.js"
Cohesion: 0.24
Nodes (16): api(), arrow(), bars(), card(), chart(), diverging(), headers(), istTime() (+8 more)

### Community 227 - "insight_log.js"
Cohesion: 0.70
Nodes (4): api(), esc(), headers(), load()

### Community 230 - "fact_slots.py"
Cohesion: 0.33
Nodes (6): asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), test_aum_slot_renders_from_snapshot()

### Community 233 - "planner_catalog_knowledge.py"
Cohesion: 0.39
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 235 - "multi_fact.py"
Cohesion: 0.20
Nodes (9): screen_fact_names(), test_any_fund_screen_keeps_requested_aum(), _detail(), test_incomplete_return_column_is_omitted(), test_screen_can_ask_for_several_facts(), test_screen_manager_name_and_experience_are_separate_facts(), test_screen_table_includes_aum(), test_screen_table_includes_manager_name_and_experience() (+1 more)

### Community 240 - "run_insights_daily.sh"
Cohesion: 0.50
Nodes (4): note(), PYTHONPATH, PYTHONUNBUFFERED, run_insights_daily.sh script

## Knowledge Gaps
- **22 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+17 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1892 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **57 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `fund_rating_screen.py`, `node_compose`, `fields.py`, `clarify_plan_if_fund_unknown`, `fund_context.py`, `ensure_registry`, `test_fund_drawdown.py`, `test_fund_name_gate_and_hydrate.py`, `QueryLogger`, `macro_data.py`, `fund_display.py`, `plan_enforce.py`, `task_exec.py`, `test_portfolio_layer.py`, `pack_sanitize.py`, `test_fund_rating_screen.py`, `owned_holding_names`, `plan.py`, `portfolio_news_impact.py`, `gold_service.py`, `investor_subject.py`, `contracts.py`, `insight_links.py`, `compare_evidence.py`, `test_fund_risk.py`, `graph.py`, `node_compose`, `display_table_policy.py`, `fact_answer.py`, `concept_asks.py`, `test_compare_pair_category.py`, `test_portfolio_allocation.py`, `evidence_pack.py`, `build_evidence_pack`, `fact_slots.py`, `enrich_manager_payload`, `multi_fact.py`, `return_windows.py`, `EvidencePack`, `synthesize_tasks`, `memory/evidence.py`, `ToolCall`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `ExecutionPlan` (e.g. with `news_calls_for_book()` and `sector_book()`) actually correct?**
  _`ExecutionPlan` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _22 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.0992982456140351 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ToolCall` to `fund_rating_screen.py`, `update.py`, `fields.py`, `clarify_plan_if_fund_unknown`, `fund_context.py`, `ensure_registry`, `test_fund_drawdown.py`, `test_fund_name_gate_and_hydrate.py`, `macro_data.py`, `plan_enforce.py`, `task_exec.py`, `test_portfolio_layer.py`, `pack_sanitize.py`, `test_fund_rating_screen.py`, `fund_drawdown.py`, `owned_holding_names`, `plan.py`, `portfolio_news_impact.py`, `ExecutionPlan`, `gold_service.py`, `investor_subject.py`, `contracts.py`, `compare_evidence.py`, `executor.py`, `graph.py`, `test_fund_risk.py`, `node_compose`, `CapabilityCache`, `display_table_policy.py`, `concept_asks.py`, `test_compare_pair_category.py`, `test_portfolio_allocation.py`, `evidence_pack.py`, `build_evidence_pack`, `get_sector_fund_ranking_index`, `multi_fact.py`, `return_windows.py`, `memory/evidence.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ToolCall` (e.g. with `news_calls_for_book()` and `_apply_planner_request()`) actually correct?**
  _`ToolCall` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `NewsStore` be split into smaller, more focused modules?**
  _Cohesion score 0.07781649245063879 - nodes in this community are weakly interconnected._