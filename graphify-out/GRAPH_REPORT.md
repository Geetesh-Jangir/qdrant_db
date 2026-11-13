# Graph Report - db_design_with_qdrant_locally  (2026-11-13)

## Corpus Check
- 508 files · ~880,778 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 5643 nodes · 18089 edges · 203 communities (169 shown, 34 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 631 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0b20e41f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- sector_alignment.py
- fund_rating_screen.py
- interpret.py
- test_fund_drawdown.py
- article_quality.py
- scrape_bodies.py
- test_conversation_memory.py
- grounding.py
- Settings
- fund_drawdown.py
- ExecutionPlan
- question_intent.py
- compute.py
- plan.py
- tools.py
- fund_display.py
- fund_rating_screen.py
- QueryLogger
- news_reader.py
- top_n_from_question
- reroute_single_fund_risk_plan
- query_plan.py
- failure_ledger.py
- tool_runners.py
- category_plan.py
- test_fund_display_tables.py
- ensure_registry
- resolve_fund_for_query
- test_answer_quality_logs.py
- nse_sector_indices.py
- query_log.py
- executor.py
- task_exec.py
- llm_client.py
- update.py
- fund_search.py
- macro_news_enhanced.py
- investor_drawback.py
- test_fund_rating_screen.py
- env
- investor_subject.py
- eval_basic_queries.py
- test_call_json_llm.py
- macro_news_cache.py
- env
- get_sector_fund_ranking_index
- rupeestop_auth.py
- sources/google_news.py
- fund_scheme_match.py
- get_settings
- gold_service.py
- env
- insight/portfolio_scope.py
- fund_rupeestop_metrics.py
- slot_router.py
- insight/portfolio_scope.py
- scrape-worker/package.json
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- slot_route
- ensure_risk_tools
- graph.py
- bullion_retrieve.py
- re
- nav_service.py
- memory/store.py
- batch.ts
- validate_capability_args
- insight/guardrails.py
- http-fetch.ts
- NewsStore
- portfolio/cache.py
- retrieve_scoped_news
- apply_task_layer
- with
- stock_fund_ranking.py
- _run_screen_funds_by_exposure
- stock_fund_ranking.py
- table_source
- display_table_policy.py
- test_portfolio_layer.py
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- news_rag/config.py
- dataclasses
- scoped_retrieve.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- parse_rating_screen
- portfolio_bind.py
- env
- memory/__init__.py
- steps
- evidence_pack.py
- relationships.py
- concept_asks.py
- fund_risk.py
- evidence.py
- pathlib
- contracts.py
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- execute_capability
- market_pulse.py
- fund_rating_categories.py
- append_investor_portfolio_overview_tables
- test_smart_fund_why.py
- test_answer_precision.py
- glossary.py
- news_digest.py
- fund_search.py
- vitest
- format_inr
- question_is_pure_general_concept
- compilerOptions
- compilerOptions
- _metal_fund_categories
- ._ensure_loaded
- backfill
- lib/google_news.py
- test_composer_table_summaries.py
- _return_slice_covers
- run-pipeline
- test_greeting.py
- pillar_focus
- index_series.py
- worker/src/index.ts
- steps
- steps
- with
- assemble_fund_overview_answer
- synthesize_tasks
- collect_evidence_calendar_dates
- inputs
- with
- inputs
- json
- prompts.py
- test_insight_graph.py
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
- compare_evidence.py
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_catalog.py
- diagnose_lightsail_site.sh
- RunLogger
- render_data_only_template
- EntityFunnel
- embed_query
- test_market_sector_fund_pipeline.py
- build_derived_views
- test_fund_risk.py
- PublisherStats
- extract_top_holdings
- entity_candidates.py
- strip_news_roundup
- pack_trim.py
- asks_fund_related_news
- planner_supplement_for_question
- metals_spot_tables.py
- test_risk_analysis_without_periods_still_loads_one_three_and_five_year
- QuestionBrief
- fund_brief.py
- universe.py
- datetime
- ExecutionPlan

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 599 edges
2. `ToolCall` - 361 edges
3. `get_settings()` - 141 edges
4. `apply_planner_post_hooks()` - 123 edges
5. `AnswerMode` - 104 edges
6. `QueryLogger` - 100 edges
7. `node_compose()` - 99 edges
8. `QuestionBrief` - 88 edges
9. `slot_route()` - 84 edges
10. `Settings` - 83 edges

## Surprising Connections (you probably didn't know these)
- `test_random_debt_not_equity_when_also_asks_debt_vs_equity()` --calls--> `fund_type_name_spec()`  [EXTRACTED]
  tests/test_fund_type_name_spec.py → news_rag/fund_rating_screen.py
- `test_pick_one_silver_from_above_is_not_an_unnamed_list()` --calls--> `parse_rating_screen()`  [EXTRACTED]
  tests/test_pick_shown_fund.py → news_rag/fund_rating_screen.py
- `test_grouped_news_keeps_the_article_body()` --calls--> `_group_layered_articles()`  [EXTRACTED]
  tests/test_insight_links.py → news_rag/insight/capabilities/executor.py
- `test_banking_and_banks_are_one_search()` --calls--> `_news_search_targets()`  [EXTRACTED]
  tests/test_macro_news_cache.py → news_rag/insight/capabilities/executor.py
- `test_parallel_wave_does_not_reuse_one_context()` --calls--> `execute_wave()`  [INFERRED]
  tests/test_two_wave_pipeline.py → news_rag/insight/capabilities/executor.py

## Import Cycles
- None detected.

## Communities (203 total, 34 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (51): get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate() (+43 more)

### Community 1 - "sector_alignment.py"
Cohesion: 0.17
Nodes (13): clear_macro_impact_cache(), analyze_sector_block(), canonical_sector_for_holding(), holding_return_pct(), holdings_in_sector(), index_return_pct(), return_sign(), run_sector_holding_alignment() (+5 more)

### Community 2 - "fund_rating_screen.py"
Cohesion: 0.09
Nodes (27): _add_category_comparison(), _amc_matches(), _amc_outside_label(), _amc_token(), _apply_category_difference(), _best_rated_row(), _cascade_labels_for_spec(), _difference_brief() (+19 more)

### Community 3 - "interpret.py"
Cohesion: 0.06
Nodes (73): SubAsk, Findings, FundFinding, SectorFinding, EvidenceSet, mentions_publication_date(), publication_date_keys(), strip_media_attribution() (+65 more)

### Community 4 - "test_fund_drawdown.py"
Cohesion: 0.16
Nodes (26): asks_category_drawdown(), drawdown_words(), ensure_drawdown_tools(), is_drawdown_definition(), _named_standard_periods(), periods_for_question(), _question_needs_drawdown(), _plan() (+18 more)

### Community 5 - "article_quality.py"
Cohesion: 0.14
Nodes (17): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+9 more)

### Community 6 - "scrape_bodies.py"
Cohesion: 0.14
Nodes (13): thread_session(), is_source_exhausted(), _entity_refs(), _log_scrape_record(), _scrape(), scrape_bodies(), _drop(), clip_log_text() (+5 more)

### Community 7 - "test_conversation_memory.py"
Cohesion: 0.19
Nodes (18): build_result(), _insight_headline_narrative(), _load_planner_memory(), get_memory(), reset_memory(), turn_record(), _fund_plan(), _Log (+10 more)

### Community 8 - "grounding.py"
Cohesion: 0.11
Nodes (27): repair_investor_insight_prose(), strip_grounding_holes(), cores_for_float(), cores_in_text(), derived_cores(), finalize_text_fields(), investor_book_cores(), number_is_grounded() (+19 more)

### Community 9 - "Settings"
Cohesion: 0.08
Nodes (33): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), repo_root(), article_in_fetch_window(), google_time_query(), has_news_date_range() (+25 more)

### Community 10 - "fund_drawdown.py"
Cohesion: 0.14
Nodes (28): _add_drawdown_call(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), fetch_drawdown_periods(), fetch_trailing_drawdown(), investment_amount() (+20 more)

### Community 11 - "ExecutionPlan"
Cohesion: 0.04
Nodes (72): asks_balanced_long_horizon_fund_menu(), asks_ideal_portfolio_shape(), balanced_portfolio_examples_spec(), category_composition_plan_applies(), ensure_cross_category_compare_plan(), ensure_rating_list_funds(), tag_answer_parts(), node_route() (+64 more)

### Community 12 - "question_intent.py"
Cohesion: 0.08
Nodes (26): question_mentions_fund_scheme(), asks_category_performance(), asks_fund_category_average(), plan_matches_intent(), prefers_planner_over_slot(), QuestionIntent, resolve_question_intent(), _top_n_from_question() (+18 more)

### Community 13 - "compute.py"
Cohesion: 0.08
Nodes (40): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+32 more)

### Community 14 - "plan.py"
Cohesion: 0.11
Nodes (21): explanation_brief(), canonicalize_field(), field_prompt_table(), mentions_advice(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years() (+13 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (59): get_fund_index(), _finalize_screen_payload(), DataNeed, rank_funds_by_sector_exposure(), _active_sector_equity(), _articles_for_affected_question(), _as_date(), asks_equity_funds() (+51 more)

### Community 16 - "fund_display.py"
Cohesion: 0.09
Nodes (29): _as_float(), _assess_table_quality(), _cell(), clean_news_insight(), _comparison_pair_ok(), complete_sentences(), _composition_table_markdown(), _fmt_inr() (+21 more)

### Community 17 - "fund_rating_screen.py"
Cohesion: 0.09
Nodes (33): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), _best_label() (+25 more)

### Community 18 - "QueryLogger"
Cohesion: 0.10
Nodes (9): _collect_pulse_pool(), run_market_pulse(), clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest(), test_finish_writes_json_sidecar() (+1 more)

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (39): _article_context_for_interpret(), measured_facts_block(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority() (+31 more)

### Community 20 - "top_n_from_question"
Cohesion: 0.36
Nodes (5): top_n_from_question(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

### Community 21 - "reroute_single_fund_risk_plan"
Cohesion: 0.14
Nodes (9): asks_fund_risk(), asks_hidden_rating(), asks_private_system(), asks_sebi_riskometer(), blocked_reply(), plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), test_reroute_investor_risk_to_fund_data_for_deictic_risk() (+1 more)

### Community 23 - "failure_ledger.py"
Cohesion: 0.07
Nodes (36): _merge_publisher_error_reasons(), write_day_report(), _bucket(), _entity_names(), summarize_errors(), write_error_summary(), _atomic_write(), day_failure_slices_for_run() (+28 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.09
Nodes (47): fetch_vs_benchmark(), build_holding_overlap(), build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief() (+39 more)

### Community 25 - "category_plan.py"
Cohesion: 0.07
Nodes (42): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), _spaced_category_words(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), asks_cross_category_compare() (+34 more)

### Community 26 - "test_fund_display_tables.py"
Cohesion: 0.10
Nodes (26): build_fund_display_tables(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_markdown_tables_from_prose(), _compose_hints() (+18 more)

### Community 27 - "ensure_registry"
Cohesion: 0.07
Nodes (49): canonical_facet(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext (+41 more)

### Community 28 - "resolve_fund_for_query"
Cohesion: 0.11
Nodes (23): is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), prefer_resolved_fund_name(), resolve_fund_for_query(), resolve_fund_from_question(), _resolved_scheme_for_portfolio_ask(), test_absl_and_ppfas_shorthand() (+15 more)

### Community 29 - "test_answer_quality_logs.py"
Cohesion: 0.13
Nodes (15): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), question_wants_gold_table(), facts_only_compose_allowed(), scrub_unknown_fund_mentions(), test_facts_only_skipped_when_slots_missing_or_market_tools_present() (+7 more)

### Community 30 - "nse_sector_indices.py"
Cohesion: 0.12
Nodes (20): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _document(), _driver_row(), list_macro_drivers() (+12 more)

### Community 31 - "query_log.py"
Cohesion: 0.09
Nodes (20): _events(), run_ask_engine(), stream_ask_engine(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), run_insight_pipeline() (+12 more)

### Community 32 - "executor.py"
Cohesion: 0.06
Nodes (36): _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _conversation_id(), _conversation_turn(), _detail_for_fund_tool(), _fill_returns_from_catalog(), _filter_excluded_screen_rows() (+28 more)

### Community 33 - "task_exec.py"
Cohesion: 0.20
Nodes (20): bind_subjects(), _book_total_line(), _cell(), coverage_line(), _fact_label(), _fmt(), _funds_from_pack(), _holding_for_category() (+12 more)

### Community 34 - "llm_client.py"
Cohesion: 0.07
Nodes (51): get_settings(), Settings, make_plan(), _slot_fallback(), anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts(), build_anthropic_messages_body() (+43 more)

### Community 35 - "update.py"
Cohesion: 0.13
Nodes (22): drop_old_turns(), compare_payload_matches_funds(), push_recent_fund_focus(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), empty_frame(), empty_state() (+14 more)

### Community 36 - "fund_search.py"
Cohesion: 0.13
Nodes (21): _clean_company_name(), detail_has_live_facts(), _entry_matches_amc(), _entry_matches_query_scheme(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers(), _fund_text() (+13 more)

### Community 37 - "macro_news_enhanced.py"
Cohesion: 0.12
Nodes (18): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), _one(), _fetch_macro_query(), _query_variants(), run_macro_news_enhanced() (+10 more)

### Community 38 - "investor_drawback.py"
Cohesion: 0.10
Nodes (25): _fund_performance_digest(), attach_drawback_digest(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer(), question_asks_all_schemes_in_answer(), _display_holding_row(), _enrich_investor_computed_fields() (+17 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.13
Nodes (30): rating_is_stronger(), run_rating_list(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap(), fetch(), test_a_one_month_performer_is_shown_beside_the_same_category_rating(), fetch() (+22 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "investor_subject.py"
Cohesion: 0.03
Nodes (110): fund_type_name_spec(), question_is_standalone_macro(), _bound_fund_name(), clarify_plan_if_fund_unknown(), _compare_sides_resolvable(), _known_names_in_text(), _plan_uses_fund_scoped_tools(), question_refers_deictic_fund_safe() (+102 more)

### Community 42 - "eval_basic_queries.py"
Cohesion: 0.16
Nodes (15): ensure_planner_fund_fact_modules(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), _holdings_breakdown_question(), validate_plan_tools(), _cases(), _check_plan() (+7 more)

### Community 43 - "test_call_json_llm.py"
Cohesion: 0.40
Nodes (9): _client(), _gemini_response(), _settings(), test_agent_keeps_truncated_tools_without_repair(), test_composer_keeps_truncated_answer_without_a_second_call(), test_gemini_request_includes_response_schema(), test_judge_truncated_json_does_not_repair(), test_salvage_closes_a_cut_off_composer_object() (+1 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.10
Nodes (24): _run_get_macro_news(), _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read() (+16 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "get_sector_fund_ranking_index"
Cohesion: 0.07
Nodes (31): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+23 more)

### Community 47 - "rupeestop_auth.py"
Cohesion: 0.12
Nodes (21): fetch_category_ratings(), ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials() (+13 more)

### Community 48 - "sources/google_news.py"
Cohesion: 0.08
Nodes (30): Publisher, SectorQuery, Settings, is_google_exhausted(), is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings() (+22 more)

### Community 49 - "fund_scheme_match.py"
Cohesion: 0.14
Nodes (17): amc_token_in_question(), _category_phrases_in_question(), _constraint_in_scheme_name(), _distinctive_constraints(), pick_best_matching_scheme(), question_amc_hints(), scheme_match_score(), _scheme_name_tokens() (+9 more)

### Community 50 - "get_settings"
Cohesion: 0.07
Nodes (44): ask(), ask_memory(), ask_query_log(), ask_sources(), ask_stream(), AskRequest, _attach_llm_meta(), _attach_portfolio_to_ask() (+36 more)

### Community 51 - "gold_service.py"
Cohesion: 0.10
Nodes (21): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+13 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "insight/portfolio_scope.py"
Cohesion: 0.12
Nodes (27): build_drawdown_wave2_calls(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), plan_targets_single_fund_measured_return(), question_asks_holding_metric_and_glossary(), _data_need_is_investor(), enforce_portfolio_scope() (+19 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (19): build_comparison_periods(), expense_ratio_for_question(), _f(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns(), normalize_vs_benchmark_payload(), _optional_number() (+11 more)

### Community 55 - "slot_router.py"
Cohesion: 0.10
Nodes (21): rating_list_plan(), rating_concept_plan(), QueryClass, Wave2Policy, normalize_portfolio_plan_from_question(), _macro_series_for_driver(), _plan_driver_impact(), _plan_fund_category_average() (+13 more)

### Community 56 - "insight/portfolio_scope.py"
Cohesion: 0.09
Nodes (30): render_portfolio_fact(), _leave_tools_alone(), _set_investor_call(), _bind_fund_list(), _ensure_portfolio_data_for_holdings(), ensure_whole_book_catalog_scope(), _funds_from_entities(), _holding_scope() (+22 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "test_expired_jwt_logs_in_once_and_reuses_fresh_token"
Cohesion: 0.09
Nodes (5): _jwt(), test_admin_headers_use_token_from_login(), test_expired_jwt_logs_in_once_and_reuses_fresh_token(), test_failed_login_keeps_previous_token(), test_valid_jwt_does_not_call_login()

### Community 59 - "slot_route"
Cohesion: 0.08
Nodes (27): random_fund_count(), execute_wave(), _asks_driver_sector_or_fund_impact(), _extract_drivers(), _extract_stocks(), _get_top_n(), _infer_window_days(), _plan_fund_performance_screen() (+19 more)

### Community 60 - "ensure_risk_tools"
Cohesion: 0.10
Nodes (19): asks_about_score_bands(), asks_pillar_structure(), asks_rating_concept(), asks_risk_trend_comparison(), asks_score_only(), ensure_risk_tools(), _ensure_risk_trend_plan(), include_drawdown_with_risk() (+11 more)

### Community 61 - "graph.py"
Cohesion: 0.03
Nodes (76): LLMUsageRecord, PhaseRecord, RequestTelemetry, ToolRecord, question_wants_concentration_tables(), render_investor_concentration_answer(), strip_context_disclaimer(), _answer_stream_chunks() (+68 more)

### Community 62 - "bullion_retrieve.py"
Cohesion: 0.10
Nodes (14): _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), embed_query(), retrieve_fund_articles(), build_filter() (+6 more)

### Community 63 - "re"
Cohesion: 0.11
Nodes (21): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+13 more)

### Community 64 - "nav_service.py"
Cohesion: 0.11
Nodes (21): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+13 more)

### Community 65 - "memory/store.py"
Cohesion: 0.20
Nodes (12): _store_turn_memory(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), append_chat_turn(), _fresh(), get_or_create(), save_sources(), save_state() (+4 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "validate_capability_args"
Cohesion: 0.12
Nodes (15): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded() (+7 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.14
Nodes (15): _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), memory_shows_investor_book(), _tokens() (+7 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "NewsStore"
Cohesion: 0.06
Nodes (11): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _datetime_range(), NewsStore (+3 more)

### Community 71 - "portfolio/cache.py"
Cohesion: 0.08
Nodes (39): _BreakerState, _CacheEntry, clear_cache_for_tests(), crn_log_id(), _fetch_and_store(), get_normalized_portfolio(), peek_derived(), preload_configured_portfolio() (+31 more)

### Community 72 - "retrieve_scoped_news"
Cohesion: 0.09
Nodes (31): corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news() (+23 more)

### Community 73 - "apply_task_layer"
Cohesion: 0.16
Nodes (17): apply_task_layer(), _has_peer_screen(), _modules_for(), parse_task_list(), test_aum_without_a_named_fund_is_the_book_total(), test_category_filter_does_not_bind_every_holding(), test_compare_pair_screen_does_not_add_a_peer_screen(), test_compare_reading_adds_large_cap_peer_screen() (+9 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "stock_fund_ranking.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 77 - "_run_screen_funds_by_exposure"
Cohesion: 0.12
Nodes (11): asks_rating_list(), fund_naming_clause(), pick_compare_pair_with_fallback(), rating_screen_question(), _run_screen_funds_by_exposure(), _named_scheme_category(), test_short_category_moves_to_another_with_two_funds(), test_debt_fund_type_not_confused_by_equity_education_clause() (+3 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.20
Nodes (14): extract_top_holdings(), _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file() (+6 more)

### Community 79 - "table_source"
Cohesion: 0.18
Nodes (8): _add_category_comparison(), _compare_brief_line(), _row_bits(), table_source(), test_fund_insights_category_average_reaches_the_composer_row(), test_table_source_includes_sebi_riskometer_from_risk_module(), test_table_source_keeps_pillar_marks_and_the_fetched_return(), test_table_source_lists_the_screen_rows()

### Community 80 - "display_table_policy.py"
Cohesion: 0.10
Nodes (19): DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark() (+11 more)

### Community 81 - "test_portfolio_layer.py"
Cohesion: 0.06
Nodes (46): fetch_public_rating(), _run_get_investor_portfolio(), _one(), get_active_crn(), peek_portfolio(), project_concentration(), aggregate_term_gains(), _allocation_block() (+38 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.05
Nodes (77): periods_requested_in_question(), _age(), _allocation_bucket_rows(), _as_of(), _asks_portfolio_rs_ratings(), _book_line(), _category_amount_map(), _comparison_rows() (+69 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "news_rag/config.py"
Cohesion: 0.06
Nodes (16): classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path(), _sector_label_in_text() (+8 more)

### Community 86 - "dataclasses"
Cohesion: 0.24
Nodes (9): check_guardrails(), GuardrailResult, test_crude_why_not_misrouted_to_random_fund(), test_fund_question_still_passes(), test_hdfc_bank_passes_guardrails(), test_hdfc_bank_short_happening_passes(), test_jio_ipo_news_passes_guardrails_and_routes(), test_non_financial_still_refused() (+1 more)

### Community 87 - "scoped_retrieve.py"
Cohesion: 0.18
Nodes (10): embed_query(), _body(), grouped_news(), NewsTarget, search_targets(), get_qdrant_reader(), _topic_match(), _topic_tokens() (+2 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.14
Nodes (19): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+11 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 90 - "parse_rating_screen"
Cohesion: 0.08
Nodes (24): asks_taxonomy(), match_all_fund_types(), _category_fund_name_spec(), _label_in(), _looks_like_fund_list(), parse_rating_screen(), _return_direction(), _return_window() (+16 more)

### Community 91 - "portfolio_bind.py"
Cohesion: 0.09
Nodes (23): question_asks_category_book_share(), question_asks_category_money(), fund_picked_from_prior_answer(), funds_from_shown_list(), _scheme_names_in_prose(), shown_list_names(), bind_shown_list_followup(), bind_cached_portfolio() (+15 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "memory/__init__.py"
Cohesion: 0.31
Nodes (6): chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens(), prompt_view()

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.08
Nodes (42): _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_cell(), _compare_header(), _complete_fund_row(), _complete_shown_funds(), _concentration_markdown(), _drawdown_body() (+34 more)

### Community 96 - "relationships.py"
Cohesion: 0.42
Nodes (5): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships()

### Community 97 - "concept_asks.py"
Cohesion: 0.31
Nodes (10): apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), asks_fof_funds(), test_concept_example_plan_screen_fof(), test_fof_name_one_detected() (+2 more)

### Community 98 - "fund_risk.py"
Cohesion: 0.16
Nodes (12): exposure_from_detail(), headline_rating(), load_fund_risk(), pending_rating_line(), _pillar_maximum(), rating_api_data_is_null(), rating_for_request(), rating_needs_pillars() (+4 more)

### Community 99 - "evidence.py"
Cohesion: 0.20
Nodes (13): _take_conversation_slice(), clear_conversation(), drain_cache_events(), note_cache(), recall_slice(), recall_wider_portfolio(), remember_slice(), slice_key() (+5 more)

### Community 100 - "pathlib"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 102 - "contracts.py"
Cohesion: 0.04
Nodes (65): _followup_modules(), ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), AnswerMode, EvidencePack (+57 more)

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.20
Nodes (11): asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score(), test_default_manager_answer_drops_former_managers() (+3 more)

### Community 106 - "execute_capability"
Cohesion: 0.19
Nodes (9): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), widen_portfolio_args(), test_compare_conversation_cache_does_not_reuse_different_pair(), fake_compare(), test_compare_conversation_cache_hits_same_pair(), test_compare_payload_matches_funds() (+1 more)

### Community 107 - "market_pulse.py"
Cohesion: 0.11
Nodes (22): AskPlan, EntityMention, _int_list(), PlannedTool, cluster_articles_by_theme(), _cluster_label(), clustered_macro_data_from_bundle(), _collect_pulse_pool_batched() (+14 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.11
Nodes (20): categories_for(), CategoryMatch, _close(), fund_type_for_category(), _metal_category(), _metal_flags(), metal_scheme_categories(), _names_a_type() (+12 more)

### Community 109 - "append_investor_portfolio_overview_tables"
Cohesion: 0.33
Nodes (4): append_investor_portfolio_overview_tables(), strip_unasked_scheme_names(), question_wants_scheme_names(), test_portfolio_overview_omits_scheme_names()

### Community 110 - "test_smart_fund_why.py"
Cohesion: 0.16
Nodes (5): _detect_funds(), _infer_window_days(), test_composer_guardrails(), test_fuzzy_fund_why_detection(), test_streaming_sse_order()

### Community 111 - "test_answer_precision.py"
Cohesion: 0.17
Nodes (9): fact_values_already_stated(), question_wants_fact_table(), strip_meta_opening_heading(), _strip_unasked_closers(), test_fact_table_only_for_compare_or_an_explicit_list(), test_fact_table_skipped_when_prose_has_the_figure(), test_next_steps_and_summary_are_removed(), test_specific_lookup_has_no_default_table() (+1 more)

### Community 112 - "glossary.py"
Cohesion: 0.26
Nodes (10): asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), glossary_execution_plan(), meaning_reply(), _normalize_term(), test_fund_nav_not_glossary(), test_nav_full_form_direct_reply() (+2 more)

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 114 - "fund_search.py"
Cohesion: 0.14
Nodes (14): _attach_trailing_product(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question() (+6 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 117 - "question_is_pure_general_concept"
Cohesion: 0.23
Nodes (9): asks_computed_illustration(), apply_pure_concept_plan(), question_is_pure_general_concept(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator(), test_all_holdings_metrics_adds_investor_tool(), test_large_cap_vs_mid_cap_is_pure_concept(), test_my_funds_is_not_pure_concept() (+1 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "_metal_fund_categories"
Cohesion: 0.20
Nodes (7): _metal_fund_categories(), _question_names_amc_scheme(), _list_count(), _list_question(), question_picks_one_shown_fund(), question_refers_to_shown_list(), _slice_shown_names()

### Community 121 - "._ensure_loaded"
Cohesion: 0.16
Nodes (3): _expand_query_token(), FundIndex, _infer_category_and_type()

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "lib/google_news.py"
Cohesion: 0.05
Nodes (33): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+25 more)

### Community 124 - "test_composer_table_summaries.py"
Cohesion: 0.18
Nodes (9): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections() (+1 more)

### Community 125 - "_return_slice_covers"
Cohesion: 0.07
Nodes (23): CapabilityCache, _Entry, get_capability_cache(), _capability_cache_key(), _one_fund(), _positive_ms(), _return_slice_covers(), _trim_cached_to_ask() (+15 more)

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "test_greeting.py"
Cohesion: 0.27
Nodes (7): greeting_reply(), identity_reply(), _mirror_greeting(), test_fund_question_is_not_greeting_or_identity(), test_hello_mirrors_greeting(), test_main_memory_in_prompt_view(), test_who_are_you_identity()

### Community 128 - "pillar_focus"
Cohesion: 0.20
Nodes (7): asks_pillar_mark(), _ensure_pillar_rating_plan(), pillar_focus(), render_pillar_marks_table(), test_fund_quality_question_maps_to_portfolio_quality_pillar(), test_pillars_data_question_matches_pillar_mark(), test_pillars_in_rating_with_fund_adds_rating_tool()

### Community 129 - "index_series.py"
Cohesion: 0.09
Nodes (30): nifty50_ticker(), aggregate_sectors_from_holdings(), extract_top_sectors(), normalize_sector_row(), _price_holdings(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector() (+22 more)

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

### Community 134 - "assemble_fund_overview_answer"
Cohesion: 0.18
Nodes (7): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), strip_empty_table_pointers(), _strip_overview_prose_block(), test_overview_drops_repeated_title_and_nav_paragraph(), test_overview_puts_rating_and_tables_before_news(), test_a_risk_read_does_not_point_at_a_missing_returns_table()

### Community 135 - "synthesize_tasks"
Cohesion: 0.25
Nodes (7): _canon_fact(), _category_in_planner_text(), _compare_subject_kind(), _facts_from_plan(), _owned_fund_names(), synthesize_tasks(), _window_code()

### Community 136 - "collect_evidence_calendar_dates"
Cohesion: 0.29
Nodes (5): collect_evidence_calendar_dates(), add_article(), format_user_calendar_date(), _ordinal_day(), test_format_user_calendar_date_and_news_collection()

### Community 137 - "inputs"
Cohesion: 0.29
Nodes (7): default, description, required, type, holdings_limit, workflow_dispatch, inputs

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "json"
Cohesion: 0.05
Nodes (38): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+30 more)

### Community 141 - "prompts.py"
Cohesion: 0.25
Nodes (5): build_composer_prompt(), build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 142 - "test_insight_graph.py"
Cohesion: 0.14
Nodes (10): build_data_pack(), build(), _compact(), EvidenceItem, plan_to_brief(), _sample_evidence(), test_compute_findings_other_sectors_and_divergence(), test_a_nav_lookup_plans_no_news_facets() (+2 more)

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

### Community 159 - "compare_evidence.py"
Cohesion: 0.24
Nodes (8): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_maybe_run_compare_retries_after_failed_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 163 - "fund_match.py"
Cohesion: 0.13
Nodes (11): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+3 more)

### Community 170 - "fund_catalog.py"
Cohesion: 0.11
Nodes (24): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+16 more)

### Community 178 - "render_data_only_template"
Cohesion: 0.24
Nodes (10): _holding_label(), _holding_weight_pct(), _portfolio_markdown(), _portfolio_sections_from_plan(), _portfolio_top_n(), render_fund_concentration_answer(), _sector_label(), _sector_weight_pct() (+2 more)

### Community 180 - "embed_query"
Cohesion: 0.18
Nodes (11): _warmup_embeddings_background(), _run(), warmup_query_vectors(), _prewarm_tool_modules(), plan_system_prompt(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix() (+3 more)

### Community 182 - "build_derived_views"
Cohesion: 0.14
Nodes (19): build_insights(), _equity_pct(), Insight, insight_lines(), insights_for_brief(), _num(), _style_band(), asset_bucket() (+11 more)

### Community 183 - "test_fund_risk.py"
Cohesion: 0.13
Nodes (22): normalize_rating(), rating_lead(), render_risk_lines(), strip_missing_data_caveats(), strip_private_leaks(), test_a_rating_pick_does_not_apologise_for_returns_or_pillars(), _public_summary(), test_api_label_is_kept_as_sent() (+14 more)

### Community 185 - "extract_top_holdings"
Cohesion: 0.17
Nodes (13): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings() (+5 more)

### Community 186 - "entity_candidates.py"
Cohesion: 0.30
Nodes (6): candidates_block(), entity_candidates(), _holding_candidates(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

### Community 187 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 190 - "asks_fund_related_news"
Cohesion: 0.31
Nodes (6): infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only(), test_overview_news_is_holdings_and_sectors()

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 197 - "QuestionBrief"
Cohesion: 0.07
Nodes (34): analyst_should_run(), asks_market_briefing(), asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief() (+26 more)

### Community 203 - "fund_brief.py"
Cohesion: 0.07
Nodes (49): build_portfolio_scope(), _clean_holding_tokens(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc() (+41 more)

### Community 206 - "universe.py"
Cohesion: 0.09
Nodes (25): resolve_allisin_holdings_path(), write_manifest(), _holding_mentioned(), matches_entity(), load_portfolio_universe(), _aliases_for(), build_holding_entities(), canonical_key() (+17 more)

### Community 209 - "datetime"
Cohesion: 0.13
Nodes (17): ensure_all_holdings_metrics_plan(), _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows() (+9 more)

### Community 212 - "ExecutionPlan"
Cohesion: 0.03
Nodes (101): ensure_quality_fund_list(), ensure_rating_screen(), _compare_fund_count(), finalize_unnamed_catalog_compare(), _split_count(), ExecutionPlan, ToolCall, asked_slots() (+93 more)

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1630 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `pillar_focus`, `fund_rating_screen.py`, `test_fund_drawdown.py`, `synthesize_tasks`, `test_conversation_memory.py`, `ExecutionPlan`, `question_intent.py`, `plan.py`, `test_insight_graph.py`, `reroute_single_fund_risk_plan`, `category_plan.py`, `test_answer_quality_logs.py`, `compare_evidence.py`, `task_exec.py`, `llm_client.py`, `update.py`, `investor_drawback.py`, `test_fund_rating_screen.py`, `investor_subject.py`, `eval_basic_queries.py`, `get_sector_fund_ranking_index`, `get_settings`, `render_data_only_template`, `gold_service.py`, `insight/portfolio_scope.py`, `slot_router.py`, `insight/portfolio_scope.py`, `test_fund_risk.py`, `slot_route`, `ensure_risk_tools`, `graph.py`, `portfolio/cache.py`, `apply_task_layer`, `display_table_policy.py`, `datetime`, `fact_answer.py`, `test_portfolio_layer.py`, `test_portfolio_allocation.py`, `portfolio_bind.py`, `evidence_pack.py`, `concept_asks.py`, `fund_risk.py`, `contracts.py`, `append_investor_portfolio_overview_tables`, `test_answer_precision.py`, `glossary.py`, `question_is_pure_general_concept`, `test_composer_table_summaries.py`?**
  _High betweenness centrality (0.120) - this node is a cross-community bridge._
- **Are the 38 inferred relationships involving `ExecutionPlan` (e.g. with `apply_concept_example_to_plan()` and `append_investor_portfolio_overview_tables()`) actually correct?**
  _`ExecutionPlan` has 38 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.07066589011842361 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ExecutionPlan` to `pillar_focus`, `fund_rating_screen.py`, `test_fund_drawdown.py`, `test_conversation_memory.py`, `fund_drawdown.py`, `ExecutionPlan`, `question_intent.py`, `plan.py`, `test_insight_graph.py`, `reroute_single_fund_risk_plan`, `category_plan.py`, `test_answer_quality_logs.py`, `compare_evidence.py`, `executor.py`, `task_exec.py`, `update.py`, `investor_drawback.py`, `test_fund_rating_screen.py`, `investor_subject.py`, `eval_basic_queries.py`, `get_sector_fund_ranking_index`, `get_settings`, `gold_service.py`, `insight/portfolio_scope.py`, `slot_router.py`, `insight/portfolio_scope.py`, `test_fund_risk.py`, `slot_route`, `ensure_risk_tools`, `graph.py`, `portfolio/cache.py`, `apply_task_layer`, `display_table_policy.py`, `datetime`, `fact_answer.py`, `test_portfolio_layer.py`, `test_portfolio_allocation.py`, `portfolio_bind.py`, `concept_asks.py`, `fund_risk.py`, `contracts.py`, `execute_capability`, `question_is_pure_general_concept`, `_return_slice_covers`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Should `fund_rating_screen.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08658536585365853 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `llm_client.py` to `interpret.py`, `ExecutionPlan`, `json`, `compute.py`, `plan.py`, `tools.py`, `news_reader.py`, `ensure_registry`, `query_log.py`, `executor.py`, `task_exec.py`, `fund_match.py`, `fund_search.py`, `investor_subject.py`, `get_sector_fund_ranking_index`, `rupeestop_auth.py`, `get_settings`, `gold_service.py`, `embed_query`, `insight/portfolio_scope.py`, `slot_router.py`, `slot_route`, `graph.py`, `bullion_retrieve.py`, `validate_capability_args`, `insight/guardrails.py`, `QuestionBrief`, `NewsStore`, `portfolio/cache.py`, `retrieve_scoped_news`, `apply_task_layer`, `fund_brief.py`, `stock_fund_ranking.py`, `test_portfolio_layer.py`, `datetime`, `news_rag/config.py`, `scoped_retrieve.py`, `portfolio_bind.py`, `execute_capability`, `market_pulse.py`, `._ensure_loaded`, `_return_slice_covers`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._