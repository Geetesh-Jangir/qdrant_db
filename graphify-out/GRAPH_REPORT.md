# Graph Report - db_design_with_qdrant_locally  (2026-11-10)

## Corpus Check
- 493 files · ~856,455 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 5278 nodes · 16838 edges · 194 communities (159 shown, 35 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 616 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `44c5c8b4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- AnswerMode
- typing
- interpret.py
- portfolio/cache.py
- Settings
- news_pipeline/config.py
- normalize.py
- slot_route
- news_dates.py
- test_fund_drawdown.py
- gather.py
- enforce_planner_catalog_plan
- compute.py
- plan.py
- tools.py
- fund_display.py
- fund_rating_screen.py
- QueryLogger
- news_reader.py
- plan_enforce.py
- dataclasses
- question_refers_deictic_fund
- scrape_bodies.py
- tool_runners.py
- category_plan.py
- build_fund_display_tables
- QuestionBrief
- resolve_fund_for_query
- fact_answer.py
- fund_brief.py
- test_ask_speed.py
- fund_context.py
- test_macro_scope.py
- test_tool_cache_covers.py
- update.py
- layer_tools.py
- executor.py
- investor_subject.py
- test_fund_rating_screen.py
- env
- slots_from_plan
- strip_news_roundup
- resolve_display_table_policy
- macro_news_cache.py
- env
- json
- affected_sectors.py
- ask_plan.py
- graph.py
- app.py
- gold_service.py
- env
- test_return_windows.py
- fund_rupeestop_metrics.py
- .lookup_extracted_fund
- macro_news_enhanced.py
- scrape-worker/package.json
- test_call_json_llm.py
- article_quality.py
- embed.py
- RequestTelemetry
- entity_candidates.py
- re
- qdrant_reader.py
- owned_holding_names
- batch.ts
- validate_capability_args
- insight/guardrails.py
- http-fetch.ts
- fields.py
- question_is_bullion_metal_price_question
- holdings_market.py
- memory/__init__.py
- with
- FundUniverseAgent
- fund_search.py
- test_pick_shown_fund.py
- lib/portfolio_scope.py
- stock_fund_ranking.py
- parse.py
- nav_service.py
- holding_attribution.py
- scrape-worker/src/index.ts
- sector_fund_ranking.py
- planner_catalog_knowledge.py
- contracts.py
- retrieve_scoped_news
- fund_match.py
- enrich_manager_payload
- fund_risk.py
- env
- contracts.py
- steps
- evidence_pack.py
- fund_search.py
- aggregate_fund_holdings.py
- investor_drawback.py
- macro_impact_map.py
- time
- news_fanout.py
- run-daily-pipeline.sh
- env
- test_two_wave_pipeline.py
- fund_type_name_spec
- csv
- fund_rating_categories.py
- llm_client.py
- rupeestop_auth.py
- metals_spot_tables.py
- news_rag/config.py
- news_digest.py
- EntityFunnel
- vitest
- test_news_only_answer.py
- strip_missing_data_caveats
- compilerOptions
- compilerOptions
- query_log.py
- RunLogger
- backfill
- pack_trim.py
- test_composer_table_summaries.py
- v2_scoring.py
- run-pipeline
- argparse
- portfolio_bind.py
- worker/src/index.ts
- steps
- steps
- with
- sector_alignment.py
- render_data_only_template
- inputs
- with
- inputs
- test_conversation_memory.py
- test_metal_fund_rating.py
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
- universe.py
- install.sh
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_catalog.py
- diagnose_lightsail_site.sh
- node_compose
- test_insight_graph.py
- strip_missing_data_caveats
- GraphUnavailable
- build_derived_views
- query_plan.py
- compare_ask_speed.py
- prompts.py
- data_pack.py
- ExecutionPlan
- unittest_mock
- textutil.py
- contains_phrase
- _amc_outside_label
- test_screen_rating_screen_arg.py

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 503 edges
2. `ToolCall` - 311 edges
3. `get_settings()` - 137 edges
4. `apply_planner_post_hooks()` - 106 edges
5. `AnswerMode` - 103 edges
6. `QueryLogger` - 100 edges
7. `QuestionBrief` - 88 edges
8. `node_compose()` - 84 edges
9. `slot_route()` - 84 edges
10. `Settings` - 83 edges

## Surprising Connections (you probably didn't know these)
- `test_parallel_wave_does_not_reuse_one_context()` --calls--> `execute_wave()`  [INFERRED]
  tests/test_two_wave_pipeline.py → news_rag/insight/capabilities/executor.py
- `_offline_plan()` --uses--> `AnswerMode`  [INFERRED]
  scripts/eval_basic_queries.py → news_rag/insight/contracts.py
- `test_holdings_breakdown_keeps_planner_news()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_category_plan.py → news_rag/insight/contracts.py
- `test_book_value_uses_investor_summary_only()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_fact_fields.py → news_rag/insight/contracts.py
- `test_compare_plan_is_not_pruned()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_fact_fields.py → news_rag/insight/contracts.py

## Import Cycles
- None detected.

## Communities (194 total, 35 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (52): get_encoder(), get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match() (+44 more)

### Community 1 - "AnswerMode"
Cohesion: 0.04
Nodes (76): question_mentions_fund_scheme(), rating_list_plan(), rating_concept_plan(), asks_fund_category_average(), AnswerMode, QueryClass, Wave2Policy, sector_focus_from_market() (+68 more)

### Community 2 - "typing"
Cohesion: 0.12
Nodes (20): cluster_articles_by_theme(), _cluster_label(), clustered_macro_data_from_bundle(), _collect_pulse_pool(), _collect_pulse_pool_batched(), _fetch_one_macro_query(), MacroThemeCluster, market_pulse_representatives_from_clusters() (+12 more)

### Community 3 - "interpret.py"
Cohesion: 0.07
Nodes (61): Findings, FundFinding, mentions_publication_date(), publication_date_keys(), _assemble(), _caveat(), check_composer_guardrails(), _claim_for_sector() (+53 more)

### Community 4 - "portfolio/cache.py"
Cohesion: 0.06
Nodes (55): portfolio_select(), PortfolioSelectRequest, _release_session(), _run_get_investor_portfolio(), enforce_portfolio_scope(), bind_session(), _BreakerState, _CacheEntry (+47 more)

### Community 5 - "Settings"
Cohesion: 0.04
Nodes (42): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+34 more)

### Community 6 - "news_pipeline/config.py"
Cohesion: 0.08
Nodes (12): is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), _datetime_range(), NewsStore, point_id_for_url(), to_iso() (+4 more)

### Community 7 - "normalize.py"
Cohesion: 0.11
Nodes (22): _allocation_block(), _apply_holding_values(), _first(), _holding_from_scheme(), match_scheme_filter(), normalize_workspace(), _num(), _pnl_summary_row() (+14 more)

### Community 8 - "slot_route"
Cohesion: 0.09
Nodes (28): execute_wave(), get_sector_fund_ranking_index(), phrase_looks_like_sector_reference(), screen_hints_from_question(), test_crude_increase_compound_question_screens_negatively_affected_funds(), test_defence_fund_screen_uses_defense_category(), test_driver_exposure_screen_no_longer_needs_sector_picks_first(), test_fof_fund_screen_returns_fof_schemes() (+20 more)

### Community 9 - "news_dates.py"
Cohesion: 0.05
Nodes (39): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), Publisher, repo_root(), SectorQuery, article_in_fetch_window() (+31 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (57): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+49 more)

### Community 11 - "gather.py"
Cohesion: 0.07
Nodes (51): _brief_system(), canonical_facet(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence() (+43 more)

### Community 12 - "enforce_planner_catalog_plan"
Cohesion: 0.08
Nodes (42): plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), plan_targets_single_fund_measured_return(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings(), _ensure_portfolio_data_for_compare(), _ensure_portfolio_data_for_holdings() (+34 more)

### Community 13 - "compute.py"
Cohesion: 0.08
Nodes (46): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+38 more)

### Community 14 - "plan.py"
Cohesion: 0.07
Nodes (33): _warmup_embeddings_background(), _run(), embed_query(), warmup_query_vectors(), explanation_brief(), canonicalize_field(), field_prompt_table(), _prewarm_tool_modules() (+25 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (57): get_fund_nav_history(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), run_driver_affected_funds_adapter(), DataNeed, _active_sector_equity(), _args_from_question(), _articles_for_affected_question() (+49 more)

### Community 16 - "fund_display.py"
Cohesion: 0.12
Nodes (27): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+19 more)

### Community 17 - "fund_rating_screen.py"
Cohesion: 0.07
Nodes (52): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _add_category_comparison(), _alternate_row_excluded() (+44 more)

### Community 18 - "QueryLogger"
Cohesion: 0.09
Nodes (9): _pack_row(), _retrieve_bullion_for_entities(), _trim_snippet(), clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), test_finish_writes_json_sidecar() (+1 more)

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (40): _article_context_for_interpret(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority(), _clean_claims() (+32 more)

### Community 20 - "plan_enforce.py"
Cohesion: 0.11
Nodes (21): asks_these_equity_funds(), compare_side_in_chat(), comparison_fund_names(), _filter(), fund_name_matches_category(), implicit_compare_pair_from_chat(), memory_funds_for_category(), recent_equity_fund_pair_in_chat() (+13 more)

### Community 21 - "dataclasses"
Cohesion: 0.10
Nodes (15): _detect_funds(), _infer_window_days(), SubAsk, SectorFinding, strip_media_attribution(), _dedupe_parenthetical_cites(), _render_citations(), test_strip_media_attribution_removes_outlet_cites() (+7 more)

### Community 22 - "question_refers_deictic_fund"
Cohesion: 0.11
Nodes (21): _needles_for_amc_hint(), _amc_token_set(), _bound_fund_name(), _amc_token_in_question(), enforce_deictic_and_memory_primary_fund(), question_refers_deictic_fund(), reconcile_deictic_planner_fund(), resolve_deictic_fund_name() (+13 more)

### Community 23 - "scrape_bodies.py"
Cohesion: 0.06
Nodes (39): Settings, _merge_publisher_error_reasons(), write_day_report(), _bucket(), _entity_names(), summarize_errors(), write_error_summary(), _atomic_write() (+31 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.09
Nodes (49): periods_requested_in_question(), build_holding_overlap(), _holding_overlap_key(), _window_pct_from_nav_payload(), build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief() (+41 more)

### Community 25 - "category_plan.py"
Cohesion: 0.05
Nodes (56): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), asks_category_performance(), _named_scheme_category(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition() (+48 more)

### Community 26 - "build_fund_display_tables"
Cohesion: 0.08
Nodes (28): assemble_fund_overview_answer(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers(), strip_markdown_tables_from_prose() (+20 more)

### Community 27 - "QuestionBrief"
Cohesion: 0.08
Nodes (35): analyst_should_run(), asks_market_briefing(), asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), build_question_brief(), _detect_direction() (+27 more)

### Community 28 - "resolve_fund_for_query"
Cohesion: 0.08
Nodes (30): _detect_funds(), extract_top_holdings(), extract_top_sectors(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), resolve_fund_for_query() (+22 more)

### Community 29 - "fact_answer.py"
Cohesion: 0.07
Nodes (50): pending_rating_line(), format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), _age() (+42 more)

### Community 30 - "fund_brief.py"
Cohesion: 0.10
Nodes (33): PortfolioScope, qdrant_filter_names(), _article_entities(), build_events(), cluster_articles(), _cluster_entities(), compose_fund_insight(), _day_key() (+25 more)

### Community 31 - "test_ask_speed.py"
Cohesion: 0.09
Nodes (31): strip_grounding_holes(), collect_evidence_calendar_dates(), add_article(), cores_for_float(), cores_in_text(), derived_cores(), finalize_text_fields(), format_user_calendar_date() (+23 more)

### Community 32 - "fund_context.py"
Cohesion: 0.16
Nodes (21): _resolve_funds(), _canonical_chat_fund_name(), _chat_fund_mention_recency(), _compare_pair_from_chat_turns(), _frame_subjects(), _fund_name_from_user_text(), isin_for_owned_holding(), last_fund_name_from_gists() (+13 more)

### Community 33 - "test_macro_scope.py"
Cohesion: 0.16
Nodes (11): question_is_standalone_macro(), ensure_catalog_tools_for_fund_news(), reconcile_planner_invented_fund_name(), apply_standalone_macro_scope(), _macro_news_topics(), test_fund_news_adds_catalog_tools(), test_macro_scope_injects_news_when_planner_sent_no_tools(), test_macro_scope_strips_fund_tools() (+3 more)

### Community 34 - "test_tool_cache_covers.py"
Cohesion: 0.14
Nodes (7): CapabilityCache, _Entry, get_capability_cache(), test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner(), test_capabilities_cache_stores_and_retrieves()

### Community 35 - "update.py"
Cohesion: 0.13
Nodes (21): drop_old_turns(), compare_payload_matches_funds(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), empty_frame(), empty_state(), expire_stale_entities() (+13 more)

### Community 36 - "layer_tools.py"
Cohesion: 0.10
Nodes (25): nifty50_ticker(), _run_get_market_snapshot(), _price_holdings(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns(), _read_cache() (+17 more)

### Community 37 - "executor.py"
Cohesion: 0.05
Nodes (45): _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _capability_cache_key(), _conversation_id(), _conversation_turn(), _detail_for_fund_tool(), _one_fund() (+37 more)

### Community 38 - "investor_subject.py"
Cohesion: 0.11
Nodes (31): apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_investor_holding_subject(), ensure_my_category_fund_investor_plan(), ensure_my_holding_fund_scope(), holdings_rows_from_investor_tool_results(), investor_holding_for_category() (+23 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.07
Nodes (52): asks_taxonomy(), _apply_category_difference(), _difference_brief(), ensure_rating_screen(), _install_suggestion_screen(), _keep_asked_return(), _keep_followup_plan(), parse_rating_screen() (+44 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "slots_from_plan"
Cohesion: 0.19
Nodes (12): asked_slots(), merge_planner_asked_facts(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), slots_from_plan(), _book() (+4 more)

### Community 42 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 43 - "resolve_display_table_policy"
Cohesion: 0.08
Nodes (25): DisplayTablePolicy, fact_values_already_stated(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark(), question_wants_concentration_tables() (+17 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.11
Nodes (22): _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), select_macro_for_question() (+14 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "json"
Cohesion: 0.13
Nodes (16): _json_default(), safe_json_dumps(), main(), fetch_fund(), load_done_isins(), load_isins(), main(), _pct() (+8 more)

### Community 47 - "affected_sectors.py"
Cohesion: 0.19
Nodes (11): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+3 more)

### Community 48 - "ask_plan.py"
Cohesion: 0.24
Nodes (9): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), test_ask_plan_keeps_rich_agent_fields(), test_cluster_prefers_larger_groups() (+1 more)

### Community 49 - "graph.py"
Cohesion: 0.15
Nodes (17): _attach_conversation(), _compose_hints(), _conversation_id(), _drop_scheme_is_the_whole_book(), _ensure_portfolio_for_fund_news(), GraphState, _maybe_compare_funds_after_multi_screen(), _maybe_enrich_picked_fund_from_screen() (+9 more)

### Community 50 - "app.py"
Cohesion: 0.10
Nodes (40): ask(), ask_memory(), ask_query_log(), ask_sources(), ask_stream(), AskRequest, _attach_llm_meta(), backfill_page() (+32 more)

### Community 51 - "gold_service.py"
Cohesion: 0.09
Nodes (21): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+13 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "test_return_windows.py"
Cohesion: 0.15
Nodes (16): ensure_all_holdings_metrics_plan(), ensure_deictic_fund_period_return_plan(), _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return() (+8 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (20): build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns(), normalize_vs_benchmark_payload() (+12 more)

### Community 55 - ".lookup_extracted_fund"
Cohesion: 0.11
Nodes (8): detail_has_live_facts(), _entry_matches_amc(), _expand_query_token(), FundIndex, get_fund_benchmark(), _infer_category_and_type(), resolve_canonical_isin(), _sync_amc_prefix_from_catalog()

### Community 56 - "macro_news_enhanced.py"
Cohesion: 0.26
Nodes (9): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), _fetch_macro_query(), _query_variants(), run_macro_news_enhanced(), _collect() (+1 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "test_call_json_llm.py"
Cohesion: 0.40
Nodes (9): _client(), _gemini_response(), _settings(), test_agent_keeps_truncated_tools_without_repair(), test_composer_keeps_truncated_answer_without_a_second_call(), test_gemini_request_includes_response_schema(), test_judge_truncated_json_does_not_repair(), test_salvage_closes_a_cut_off_composer_object() (+1 more)

### Community 59 - "article_quality.py"
Cohesion: 0.12
Nodes (18): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+10 more)

### Community 60 - "embed.py"
Cohesion: 0.14
Nodes (8): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, _build_encoder(), embeddings_ready(), main()

### Community 61 - "RequestTelemetry"
Cohesion: 0.16
Nodes (14): RequestTelemetry, _answer_stream_chunks(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed(), event_phase_started(), event_quality_check() (+6 more)

### Community 62 - "entity_candidates.py"
Cohesion: 0.25
Nodes (7): candidates_block(), entity_candidates(), _holding_candidates(), question_asks_compare_both_in_chat(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

### Community 63 - "re"
Cohesion: 0.08
Nodes (29): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+21 more)

### Community 64 - "qdrant_reader.py"
Cohesion: 0.10
Nodes (8): corpus_entity_names(), _normalize_key(), resolve_corpus_entities(), resolve_corpus_entity(), describe_filters_for_log(), filter_spec(), _point_row(), QdrantReader

### Community 65 - "owned_holding_names"
Cohesion: 0.18
Nodes (15): merge_fund_isins_map(), _all_holdings_metric_spec(), _fund_data_from_results(), _investor_holdings_rating_rows(), _metric_cell(), render_all_holdings_metric_table(), render_all_holdings_return_table(), render_all_holdings_sector_table() (+7 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "validate_capability_args"
Cohesion: 0.18
Nodes (9): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_vs_benchmark_module_is_not_replaced_by_snapshot(), test_validate_capability_requires_modules() (+1 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.17
Nodes (13): _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), _tokens(), unknown_fund_phrase() (+5 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "fields.py"
Cohesion: 0.08
Nodes (34): _asks_book(), bind_fields_to_tools(), _book_fields(), fields_from_question(), _find_term(), _fund_fields(), _leave_tools_alone(), _legacy_facts() (+26 more)

### Community 71 - "question_is_bullion_metal_price_question"
Cohesion: 0.33
Nodes (6): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), test_bullion_plan_clears_memory_gold_etf(), test_bullion_vs_gold_etf_detection()

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "memory/__init__.py"
Cohesion: 0.15
Nodes (13): greeting_reply(), identity_reply(), _mirror_greeting(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens() (+5 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "FundUniverseAgent"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 77 - "fund_search.py"
Cohesion: 0.14
Nodes (16): labels_name_the_same_scheme(), _attach_trailing_product(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _entry_matches_query_scheme(), _extend_amc_phrase_tail() (+8 more)

### Community 78 - "test_pick_shown_fund.py"
Cohesion: 0.16
Nodes (13): fund_picked_from_prior_answer(), funds_from_shown_list(), _list_count(), _list_question(), question_refers_to_shown_list(), _slice_shown_names(), bind_shown_list_followup(), windows_named_in_question() (+5 more)

### Community 79 - "lib/portfolio_scope.py"
Cohesion: 0.16
Nodes (15): build_portfolio_scope(), FundRef, _holding_equity_allowed(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest(), load_portfolio_funds() (+7 more)

### Community 80 - "stock_fund_ranking.py"
Cohesion: 0.14
Nodes (17): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), rank_funds_by_sector_exposure(), _aggregated_map(), default_holder_candidates() (+9 more)

### Community 81 - "parse.py"
Cohesion: 0.33
Nodes (5): parse_date_field(), parse_time_window(), split_multi_questions(), to_iso(), utc_now()

### Community 82 - "nav_service.py"
Cohesion: 0.22
Nodes (10): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), monthly_returns_from_records(), _read_cache() (+2 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "sector_fund_ranking.py"
Cohesion: 0.07
Nodes (16): normalize_sector_label(), classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path() (+8 more)

### Community 86 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 87 - "contracts.py"
Cohesion: 0.06
Nodes (35): asks_computed_illustration(), apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), EvidenceRow, LLMUsageRecord (+27 more)

### Community 88 - "retrieve_scoped_news"
Cohesion: 0.16
Nodes (17): _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news(), _sector_entities() (+9 more)

### Community 89 - "fund_match.py"
Cohesion: 0.15
Nodes (10): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), load_fund_embedding_cache(), _normalize_fund_text() (+2 more)

### Community 90 - "enrich_manager_payload"
Cohesion: 0.24
Nodes (9): build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_default_manager_answer_drops_former_managers(), test_enrich_filters_past_only(), test_infer_roster_focus_current_vs_past() (+1 more)

### Community 91 - "fund_risk.py"
Cohesion: 0.09
Nodes (24): asks_fund_risk(), asks_hidden_rating(), asks_private_system(), asks_score_only(), blocked_reply(), exposure_from_detail(), fetch_public_rating(), headline_rating() (+16 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "contracts.py"
Cohesion: 0.08
Nodes (21): _followup_modules(), has_second_part(), _wants_end_summary(), asks_one_figure(), ensure_screen_facts(), screen_fact_names(), top_n_from_question(), test_highest_rating_plus_returns_and_risk_keeps_the_fund_lookup() (+13 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.07
Nodes (50): _add_category_comparison(), append_investor_portfolio_overview_tables(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line(), _compare_cell(), _compare_header(), _complete_fund_row() (+42 more)

### Community 96 - "fund_search.py"
Cohesion: 0.14
Nodes (17): aggregate_sectors_from_holdings(), _clean_company_name(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers(), _fund_text(), _named_weights(), _normalize_manager_record() (+9 more)

### Community 97 - "aggregate_fund_holdings.py"
Cohesion: 0.23
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 98 - "investor_drawback.py"
Cohesion: 0.08
Nodes (31): _fund_performance_digest(), attach_drawback_digest(), build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_investor_drawdown_fetch(), _pretty_category(), question_asks_portfolio_level_drawdown(), question_signals_investor_book() (+23 more)

### Community 99 - "macro_impact_map.py"
Cohesion: 0.09
Nodes (28): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _rule_sector_picks() (+20 more)

### Community 100 - "time"
Cohesion: 0.11
Nodes (20): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), _take_conversation_slice(), widen_portfolio_args(), note_cache(), recall_slice(), recall_wider_portfolio() (+12 more)

### Community 102 - "news_fanout.py"
Cohesion: 0.33
Nodes (5): embed_query(), _body(), grouped_news(), NewsTarget, search_targets()

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "test_two_wave_pipeline.py"
Cohesion: 0.06
Nodes (22): ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified() (+14 more)

### Community 106 - "fund_type_name_spec"
Cohesion: 0.09
Nodes (18): _category_fund_name_spec(), fund_naming_clause(), _fund_type_in_name_clause(), fund_type_name_spec(), _label_in(), _looks_like_fund_list(), _metal_fund_categories(), _metal_fund_spec() (+10 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.14
Nodes (11): categories_for(), CategoryMatch, fund_type_for_category(), match_all_fund_types(), metal_scheme_categories(), _names_a_type(), rating_scope_pairs(), _spaced_category_words() (+3 more)

### Community 109 - "llm_client.py"
Cohesion: 0.07
Nodes (43): Settings, anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts(), build_anthropic_messages_body(), _call_anthropic(), _call_deepseek(), _call_gemini() (+35 more)

### Community 110 - "rupeestop_auth.py"
Cohesion: 0.07
Nodes (24): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+16 more)

### Community 111 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 112 - "news_rag/config.py"
Cohesion: 0.12
Nodes (9): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), project_concentration(), PortfolioUpstreamError, main(), main() (+1 more)

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "test_news_only_answer.py"
Cohesion: 0.23
Nodes (8): _news_subject(), clean_news_insight(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words(), test_news_about_hdfc_bank_is_not_a_market_pulse(), test_news_insight_drops_publisher_clips_and_unrelated_articles()

### Community 117 - "strip_missing_data_caveats"
Cohesion: 0.31
Nodes (8): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings()

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "query_log.py"
Cohesion: 0.07
Nodes (20): _events(), run_ask_engine(), stream_ask_engine(), run_graph_pipeline(), run_insight_pipeline(), stream_insight_pipeline(), ParsedQuery, attach_query_log_meta() (+12 more)

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 124 - "test_composer_table_summaries.py"
Cohesion: 0.19
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_parse_tables_append_directive(), test_strip_empty_bold_sections(), test_summarize_tables_for_composer_extracts_mix_and_holdings()

### Community 125 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "argparse"
Cohesion: 0.17
Nodes (6): check(), main(), run_case(), _Usage, main(), main()

### Community 129 - "portfolio_bind.py"
Cohesion: 0.20
Nodes (10): question_asks_category_book_share(), bind_cached_portfolio(), _catalog_fund_holdings_question(), ensure_tools_for_data_question(), finish_portfolio_plan_bind(), _investor_args(), _merge_fund(), question_mentions_own_book() (+2 more)

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

### Community 135 - "sector_alignment.py"
Cohesion: 0.12
Nodes (19): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), sector_query_for_label(), analyze_sector_block(), canonical_sector_for_holding() (+11 more)

### Community 136 - "render_data_only_template"
Cohesion: 0.14
Nodes (18): EvidencePack, _holding_label(), _holding_weight_pct(), _portfolio_markdown(), _portfolio_sections_from_plan(), _portfolio_top_n(), render_data_only_template(), render_fund_concentration_answer() (+10 more)

### Community 137 - "inputs"
Cohesion: 0.29
Nodes (7): default, description, required, type, holdings_limit, workflow_dispatch, inputs

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 141 - "test_conversation_memory.py"
Cohesion: 0.12
Nodes (32): build_result(), _load_planner_memory(), _store_turn_memory(), clear_conversation(), drain_cache_events(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), append_chat_turn() (+24 more)

### Community 142 - "test_metal_fund_rating.py"
Cohesion: 0.15
Nodes (11): ensure_quality_fund_list(), _payload(), _rating(), test_category_rating_request_uses_admin_header(), test_gold_etf_only_stays_on_the_etf_category(), test_gold_fund_list_uses_only_gold_scheme_categories(), test_gold_list_spreads_etf_and_fund_of_funds(), fetch() (+3 more)

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

### Community 159 - "universe.py"
Cohesion: 0.17
Nodes (18): _clean_holding_tokens(), instrument_to_qdrant_names(), match_holding_to_corpus_entity(), _aliases_for(), build_holding_entities(), canonical_key(), _display_name(), _holding_query() (+10 more)

### Community 170 - "fund_catalog.py"
Cohesion: 0.14
Nodes (20): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+12 more)

### Community 178 - "node_compose"
Cohesion: 0.08
Nodes (34): asks_about_score_bands(), asks_pillar_mark(), asks_pillar_structure(), asks_rating_concept(), asks_sebi_riskometer(), normalize_rating(), pillar_focus(), rating_lead() (+26 more)

### Community 179 - "test_insight_graph.py"
Cohesion: 0.26
Nodes (8): run_graph(), plan_to_brief(), _state(), test_a_nav_lookup_plans_no_news_facets(), test_lookup_route_skips_news_and_sends_no_identifiers_to_the_writer(), test_out_of_scope_question_ends_after_the_planner(), test_parse_plan_drops_unknown_tools_and_clamps_values(), test_unmatched_fund_replies_without_calling_tools()

### Community 180 - "strip_missing_data_caveats"
Cohesion: 0.17
Nodes (9): strip_missing_data_caveats(), test_a_rating_pick_does_not_apologise_for_returns_or_pillars(), test_strip_removes_risk_trend_apology(), test_a_holding_outside_the_top_five_still_gets_weight_and_sector(), test_a_top_five_apology_is_removed(), test_each_holding_keeps_the_article_text_not_only_one_headline(), test_grouped_news_keeps_the_article_body(), test_overview_fund_facts_are_a_short_table() (+1 more)

### Community 182 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 190 - "compare_ask_speed.py"
Cohesion: 0.53
Nodes (4): compare(), _load(), main(), _numbers()

### Community 191 - "prompts.py"
Cohesion: 0.25
Nodes (5): build_brief_prompt(), build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 192 - "data_pack.py"
Cohesion: 0.38
Nodes (3): build_data_pack(), build(), _compact()

### Community 195 - "ExecutionPlan"
Cohesion: 0.04
Nodes (104): asks_risk_trend_comparison(), _ensure_pillar_rating_plan(), ensure_risk_tools(), _ensure_risk_trend_plan(), _is_band_definition(), _use_rating_concept(), maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair() (+96 more)

### Community 204 - "textutil.py"
Cohesion: 0.10
Nodes (24): _entity_refs(), _log_scrape_record(), _scrape(), scrape_bodies(), _drop(), clip_log_text(), finish_run_logger(), fetch_entity_items() (+16 more)

### Community 205 - "contains_phrase"
Cohesion: 0.70
Nodes (3): _holding_mentioned(), matches_entity(), contains_phrase()

### Community 210 - "test_screen_rating_screen_arg.py"
Cohesion: 0.28
Nodes (6): test_finalize_screen_adds_returns_for_compare_question(), fake_detail(), get_fund_detail(), test_rating_screen_uses_focus_question_not_full_compare_question(), test_rating_screen_uses_forced_category_spec(), fake_fetch()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1545 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `AnswerMode`, `portfolio_bind.py`, `portfolio/cache.py`, `render_data_only_template`, `test_fund_drawdown.py`, `enforce_planner_catalog_plan`, `test_conversation_memory.py`, `plan.py`, `test_metal_fund_rating.py`, `fund_display.py`, `fund_rating_screen.py`, `plan_enforce.py`, `question_refers_deictic_fund`, `tool_runners.py`, `category_plan.py`, `fact_answer.py`, `fund_context.py`, `test_macro_scope.py`, `update.py`, `investor_subject.py`, `test_fund_rating_screen.py`, `slots_from_plan`, `resolve_display_table_policy`, `graph.py`, `node_compose`, `test_insight_graph.py`, `gold_service.py`, `test_return_windows.py`, `owned_holding_names`, `fields.py`, `question_is_bullion_metal_price_question`, `test_pick_shown_fund.py`, `contracts.py`, `fund_risk.py`, `contracts.py`, `evidence_pack.py`, `investor_drawback.py`, `macro_impact_map.py`, `test_two_wave_pipeline.py`, `test_news_only_answer.py`, `test_composer_table_summaries.py`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `ExecutionPlan` (e.g. with `apply_concept_example_to_plan()` and `merge_planner_asked_facts()`) actually correct?**
  _`ExecutionPlan` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.0684981684981685 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `app.py` to `portfolio_bind.py`, `AnswerMode`, `interpret.py`, `portfolio/cache.py`, `typing`, `slot_route`, `gather.py`, `enforce_planner_catalog_plan`, `compute.py`, `plan.py`, `QueryLogger`, `news_reader.py`, `QuestionBrief`, `fund_brief.py`, `test_tool_cache_covers.py`, `executor.py`, `investor_subject.py`, `affected_sectors.py`, `graph.py`, `node_compose`, `gold_service.py`, `test_return_windows.py`, `.lookup_extracted_fund`, `embed.py`, `qdrant_reader.py`, `validate_capability_args`, `fields.py`, `fund_search.py`, `stock_fund_ranking.py`, `sector_fund_ranking.py`, `retrieve_scoped_news`, `fund_match.py`, `macro_impact_map.py`, `time`, `llm_client.py`, `rupeestop_auth.py`, `news_rag/config.py`, `query_log.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Should `AnswerMode` be split into smaller, more focused modules?**
  _Cohesion score 0.04016441573693482 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ExecutionPlan` to `AnswerMode`, `portfolio_bind.py`, `portfolio/cache.py`, `slot_route`, `test_fund_drawdown.py`, `enforce_planner_catalog_plan`, `test_conversation_memory.py`, `test_metal_fund_rating.py`, `plan.py`, `fund_rating_screen.py`, `plan_enforce.py`, `question_refers_deictic_fund`, `tool_runners.py`, `category_plan.py`, `test_ask_speed.py`, `test_macro_scope.py`, `test_tool_cache_covers.py`, `update.py`, `executor.py`, `investor_subject.py`, `test_fund_rating_screen.py`, `slots_from_plan`, `resolve_display_table_policy`, `graph.py`, `node_compose`, `gold_service.py`, `test_insight_graph.py`, `test_return_windows.py`, `owned_holding_names`, `fields.py`, `question_is_bullion_metal_price_question`, `test_pick_shown_fund.py`, `contracts.py`, `fund_risk.py`, `contracts.py`, `investor_drawback.py`, `macro_impact_map.py`, `time`, `test_two_wave_pipeline.py`, `test_news_only_answer.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._