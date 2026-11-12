# Graph Report - db_design_with_qdrant_locally  (2026-11-12)

## Corpus Check
- 506 files · ~876,090 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 5566 nodes · 17831 edges · 211 communities (177 shown, 34 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 632 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9453c225`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- insight/portfolio_scope.py
- get_sector_fund_ranking_index
- interpret.py
- test_portfolio_layer.py
- article_quality.py
- main.py
- executor.py
- grounding.py
- Settings
- test_fund_drawdown.py
- test_portfolio_layer.py
- _return_slice_covers
- compute.py
- plan.py
- tools.py
- fund_display.py
- fund_rating_screen.py
- QueryLogger
- news_reader.py
- ToolCall
- investor_subject.py
- test_macro_scope.py
- failure_ledger.py
- tool_runners.py
- category_plan.py
- test_fund_display_tables.py
- ensure_registry
- resolve_fund_for_query
- fields.py
- lib/portfolio_scope.py
- query_log.py
- Any
- task_exec.py
- llm_client.py
- update.py
- fund_search.py
- fund_context.py
- pack_sanitize.py
- test_fund_rating_screen.py
- env
- test_portfolio_startup_cache.py
- test_insight_graph.py
- nse_sector_indices.py
- macro_news_cache.py
- env
- textutil.py
- rupeestop_auth.py
- test_investor_grounding.py
- test_answer_precision.py
- app.py
- gold_service.py
- env
- nav_service.py
- fund_rupeestop_metrics.py
- contracts.py
- test_portfolio_intents.py
- scrape-worker/package.json
- test_answer_quality_logs.py
- render_data_only_template
- test_fund_risk.py
- RequestTelemetry
- normalize_rs_label
- re
- bullion_retrieve.py
- test_rupeestop_auth.py
- batch.ts
- datetime
- insight/guardrails.py
- http-fetch.ts
- embed.py
- portfolio/cache.py
- holdings_market.py
- test_fact_answer.py
- with
- stock_fund_ranking.py
- universe.py
- stock_fund_ranking.py
- datetime
- resolve_display_table_policy
- normalize.py
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- sector_fund_ranking.py
- SectorFundRankingIndex
- market_pulse.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- affected_sectors.py
- CapabilityCache
- env
- memory/__init__.py
- steps
- evidence_pack.py
- _run_get_fund_data
- EvidencePack
- test_macro_news_cache.py
- retrieve_scoped_news
- pathlib
- metals_spot_tables.py
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- enforce_planner_catalog_plan
- ask_plan.py
- fund_rating_categories.py
- insight/portfolio_scope.py
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- explicit_fund_count
- strip_news_roundup
- news_digest.py
- .lookup_extracted_fund
- vitest
- format_inr
- get_stock_profile
- compilerOptions
- compilerOptions
- execute_capability
- ._ensure_loaded
- backfill
- lib/google_news.py
- test_composer_table_summaries.py
- compare_evidence.py
- run-pipeline
- portfolio/client.py
- macro_impact_map.py
- index_series.py
- worker/src/index.ts
- steps
- steps
- with
- test_conversation_memory.py
- sector_alignment.py
- insights.py
- inputs
- with
- inputs
- json
- concept_asks.py
- graph.py
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
- fetch_public_rating
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_catalog.py
- diagnose_lightsail_site.sh
- RunLogger
- test_metal_fund_rating.py
- EntityFunnel
- shared_system_prefix
- asks_computed_illustration
- build_derived_views
- planner_catalog_knowledge.py
- query_plan.py
- extract_top_holdings
- entity_candidates.py
- relationships.py
- Path
- asks_fund_related_news
- plan_enforce.py
- fact_slots.py
- contains_phrase
- test_rating_screen_uses_focus_question_not_full_compare_question
- top_n_from_question
- QuestionBrief
- news_pipeline/config.py
- news_insight_articles
- data_pack.py
- fund_brief.py
- test_snapshot_uses_payload_returns_and_history_only_for_gaps
- test_holding_overlap.py
- market_scope_entities
- unittest_mock
- prompts.py

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 585 edges
2. `ToolCall` - 352 edges
3. `get_settings()` - 139 edges
4. `apply_planner_post_hooks()` - 121 edges
5. `AnswerMode` - 104 edges
6. `QueryLogger` - 100 edges
7. `node_compose()` - 98 edges
8. `QuestionBrief` - 88 edges
9. `slot_route()` - 84 edges
10. `Settings` - 83 edges

## Surprising Connections (you probably didn't know these)
- `test_rs_label_glossary_does_not_resolve_category_field()` --calls--> `fields_from_question()`  [EXTRACTED]
  tests/test_fund_risk.py → news_rag/insight/fields.py
- `test_return_slice_requires_pillars_when_requested()` --calls--> `_return_slice_covers()`  [EXTRACTED]
  tests/test_fund_risk.py → news_rag/insight/capabilities/executor.py
- `TestGoogleNewsFetch` --uses--> `Settings`  [INFERRED]
  tests/test_google_news_fetch.py → news_pipeline/config.py
- `test_market_sector_lists_in_display_without_funds()` --uses--> `QuestionBrief`  [INFERRED]
  tests/test_insight_interpret.py → news_rag/insight/brief.py
- `test_named_fund_why_uses_sector_drag_not_macro()` --uses--> `QuestionBrief`  [INFERRED]
  tests/test_insight_interpret.py → news_rag/insight/brief.py

## Import Cycles
- None detected.

## Communities (211 total, 34 thin omitted)

### Community 0 - "logging"
Cohesion: 0.06
Nodes (60): get_entity_funnel(), _bucket(), _entity_names(), fetch_window_fields(), summarize_errors(), write_error_summary(), reset_run_buffers(), build_graph() (+52 more)

### Community 1 - "insight/portfolio_scope.py"
Cohesion: 0.11
Nodes (29): attach_drawback_digest(), build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), _pretty_category(), render_portfolio_drawback_answer() (+21 more)

### Community 2 - "get_sector_fund_ranking_index"
Cohesion: 0.07
Nodes (35): execute_wave(), get_sector_fund_ranking_index(), _args_from_question(), _clean_stock_capture(), _exposure_ask(), _heavy_and_return(), phrase_is_mutual_fund_scheme(), phrase_looks_like_sector_reference() (+27 more)

### Community 3 - "interpret.py"
Cohesion: 0.07
Nodes (67): asks_market_briefing(), Findings, FundFinding, SectorFinding, mentions_publication_date(), _assemble(), _caveat(), check_composer_guardrails() (+59 more)

### Community 4 - "test_portfolio_layer.py"
Cohesion: 0.14
Nodes (10): fetch_top_holdings(), project_concentration(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore (+2 more)

### Community 5 - "article_quality.py"
Cohesion: 0.13
Nodes (18): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+10 more)

### Community 6 - "main.py"
Cohesion: 0.08
Nodes (12): is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), _datetime_range(), NewsStore, point_id_for_url(), build_filter() (+4 more)

### Community 7 - "executor.py"
Cohesion: 0.14
Nodes (20): _conversation_id(), _conversation_turn(), _keep_conversation_slice(), _run_get_macro_news(), _take_conversation_slice(), widen_portfolio_args(), complete_sentences(), beside_keys() (+12 more)

### Community 8 - "grounding.py"
Cohesion: 0.06
Nodes (37): analyst_should_run(), collect_evidence_calendar_dates(), add_article(), cores_in_text(), finalize_text_fields(), format_user_calendar_date(), number_is_grounded(), numeric_core() (+29 more)

### Community 9 - "Settings"
Cohesion: 0.07
Nodes (35): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), article_in_fetch_window(), google_time_query(), has_news_date_range(), iter_inclusive_days() (+27 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (58): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+50 more)

### Community 11 - "test_portfolio_layer.py"
Cohesion: 0.11
Nodes (23): clear_cache_for_tests(), get_active_crn(), set_active_crn(), InvalidCRN, normalized_doc(), test_active_crn_reaches_a_worker_thread(), test_concentration_question_loads_stock_and_sector_data(), test_current_value_and_nonzero_xirr() (+15 more)

### Community 12 - "_return_slice_covers"
Cohesion: 0.13
Nodes (16): _capability_cache_key(), _one_fund(), _positive_ms(), _return_slice_covers(), _trim_cached_to_ask(), slice_slot(), test_missing_window_is_not_covered(), test_wider_cached_fund_payload_covers_and_trims_to_the_ask() (+8 more)

### Community 13 - "compute.py"
Cohesion: 0.08
Nodes (43): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+35 more)

### Community 14 - "plan.py"
Cohesion: 0.09
Nodes (26): explanation_brief(), canonicalize_field(), field_prompt_table(), mentions_advice(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years() (+18 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (53): get_fund_nav_history(), get_fund_index(), run_driver_affected_funds_adapter(), DataNeed, rank_funds_by_sector_exposure(), _active_sector_equity(), _articles_for_affected_question(), _as_date() (+45 more)

### Community 16 - "fund_display.py"
Cohesion: 0.11
Nodes (28): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+20 more)

### Community 17 - "fund_rating_screen.py"
Cohesion: 0.06
Nodes (40): categories_for(), metal_scheme_categories(), _add_category_comparison(), _allocation_mix_spec(), _amc_matches(), _amc_outside_label(), _amc_token(), _apply_category_difference() (+32 more)

### Community 18 - "QueryLogger"
Cohesion: 0.10
Nodes (7): slots_from_plan(), clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest(), test_finish_writes_json_sidecar()

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (37): _article_context_for_interpret(), measured_facts_block(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority() (+29 more)

### Community 20 - "ToolCall"
Cohesion: 0.06
Nodes (45): _followup_modules(), ToolCall, build_evidence_pack(), ensure_fund_concentration_plan(), has_second_part(), asks_one_figure(), ensure_compare_template(), ensure_multi_fact_tools() (+37 more)

### Community 21 - "investor_subject.py"
Cohesion: 0.05
Nodes (76): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), _needles_for_amc_hint(), _amc_token_set(), _categories_equivalent(), _bound_fund_name(), _compare_sides_resolvable(), _known_names_in_text() (+68 more)

### Community 22 - "test_macro_scope.py"
Cohesion: 0.18
Nodes (10): question_is_standalone_macro(), ensure_catalog_tools_for_fund_news(), apply_standalone_macro_scope(), _macro_news_topics(), test_fund_news_adds_catalog_tools(), test_macro_scope_injects_news_when_planner_sent_no_tools(), test_macro_scope_strips_fund_tools(), test_market_overview_does_not_invent_rupee_search() (+2 more)

### Community 23 - "failure_ledger.py"
Cohesion: 0.07
Nodes (32): Settings, _merge_publisher_error_reasons(), write_day_report(), _atomic_write(), day_failure_slices_for_run(), ensure_loaded(), _failures_dir(), flush() (+24 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.11
Nodes (44): build_holding_overlap(), build_default_registry(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+36 more)

### Community 25 - "category_plan.py"
Cohesion: 0.05
Nodes (56): match_all_scheme_categories(), asks_category_performance(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), asks_cross_category_compare(), asks_fund_holdings_followup(), _category_for_alternate_plan() (+48 more)

### Community 26 - "test_fund_display_tables.py"
Cohesion: 0.07
Nodes (32): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers() (+24 more)

### Community 27 - "ensure_registry"
Cohesion: 0.06
Nodes (53): canonical_facet(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), EvidenceItem, _extract_funds_from_result(), gather_evidence() (+45 more)

### Community 28 - "resolve_fund_for_query"
Cohesion: 0.10
Nodes (25): fetch_fund_managers_for_query(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), prefer_resolved_fund_name(), resolve_fund_for_query(), resolve_fund_from_question() (+17 more)

### Community 29 - "fields.py"
Cohesion: 0.11
Nodes (25): periods_requested_in_question(), _asks_book(), bind_fields_to_tools(), _book_fields(), field_need(), FieldNeed, fields_from_question(), _find_term() (+17 more)

### Community 30 - "lib/portfolio_scope.py"
Cohesion: 0.14
Nodes (19): build_portfolio_scope(), FundRef, _holding_equity_allowed(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest(), load_portfolio_funds() (+11 more)

### Community 31 - "query_log.py"
Cohesion: 0.10
Nodes (15): ask_query_log(), run_ask_engine(), stream_ask_engine(), ParsedQuery, attach_query_log_meta(), find_query_log_file(), new_fund_brief_logger(), new_query_logger() (+7 more)

### Community 32 - "Any"
Cohesion: 0.09
Nodes (22): retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), embed_query(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _fill_returns_from_catalog(), _filter_excluded_screen_rows() (+14 more)

### Community 33 - "task_exec.py"
Cohesion: 0.09
Nodes (42): apply_task_layer(), bind_subjects(), _book_total_line(), _canon_fact(), _category_in_planner_text(), _cell(), coverage_line(), _fact_label() (+34 more)

### Community 34 - "llm_client.py"
Cohesion: 0.07
Nodes (46): get_settings(), Settings, anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts(), _call_anthropic(), _call_deepseek(), _call_gemini() (+38 more)

### Community 35 - "update.py"
Cohesion: 0.12
Nodes (22): drop_old_turns(), compare_payload_matches_funds(), push_recent_fund_focus(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), empty_frame(), empty_state() (+14 more)

### Community 36 - "fund_search.py"
Cohesion: 0.11
Nodes (22): headline_rating(), _clean_company_name(), detail_has_live_facts(), _entry_matches_amc(), _entry_matches_query_scheme(), _expand_query_token(), fetch_fund_managers_for_isin(), _fund_context_for_managers() (+14 more)

### Community 37 - "fund_context.py"
Cohesion: 0.07
Nodes (39): match_scheme_category(), _resolve_funds(), _canonical_chat_fund_name(), _chat_fund_mention_recency(), _compare_pair_from_chat_turns(), compare_side_in_chat(), comparison_fund_names(), _filter() (+31 more)

### Community 38 - "pack_sanitize.py"
Cohesion: 0.09
Nodes (25): append_investor_portfolio_overview_tables(), _fund_performance_digest(), strip_unasked_scheme_names(), question_asks_all_schemes_in_answer(), question_wants_scheme_names(), _display_holding_row(), _enrich_investor_computed_fields(), _internal_contribution_row() (+17 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.08
Nodes (49): asks_taxonomy(), ensure_rating_screen(), parse_rating_screen(), rating_is_stronger(), run_rating_list(), test_ensure_rating_screen_does_not_rewrite_from_question_text(), _payload(), _rating() (+41 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "test_portfolio_startup_cache.py"
Cohesion: 0.17
Nodes (14): question_asks_category_book_share(), bind_cached_portfolio(), _catalog_fund_holdings_question(), ensure_tools_for_data_question(), finish_portfolio_plan_bind(), _investor_args(), _merge_fund(), question_mentions_own_book() (+6 more)

### Community 42 - "test_insight_graph.py"
Cohesion: 0.11
Nodes (13): _insight_headline_narrative(), run_graph(), run_graph_pipeline(), run_insight_pipeline(), stream_insight_pipeline(), plan_to_brief(), _state(), test_a_nav_lookup_plans_no_news_facets() (+5 more)

### Community 43 - "nse_sector_indices.py"
Cohesion: 0.19
Nodes (11): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _clear_index_cache(), test_by_sector_keys_match_sector_queries_exactly(), test_every_sector_has_verified_ticker_field() (+3 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.21
Nodes (10): _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), _search_macro_parameters() (+2 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "textutil.py"
Cohesion: 0.10
Nodes (25): _entity_refs(), _log_scrape_record(), _scrape(), scrape_bodies(), _drop(), clip_log_text(), fetch_entity_items(), _match_publisher() (+17 more)

### Community 47 - "rupeestop_auth.py"
Cohesion: 0.24
Nodes (11): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url(), _looks_like_jwt() (+3 more)

### Community 48 - "test_investor_grounding.py"
Cohesion: 0.18
Nodes (12): repair_investor_insight_prose(), strip_grounding_holes(), cores_for_float(), derived_cores(), investor_book_cores(), _sample_book(), test_grounding_keeps_category_weight_in_prose(), test_investor_book_cores_includes_pnl_term_gains() (+4 more)

### Community 49 - "test_answer_precision.py"
Cohesion: 0.17
Nodes (9): fact_values_already_stated(), question_wants_fact_table(), strip_meta_opening_heading(), _strip_unasked_closers(), test_fact_table_only_for_compare_or_an_explicit_list(), test_fact_table_skipped_when_prose_has_the_figure(), test_next_steps_and_summary_are_removed(), test_specific_lookup_has_no_default_table() (+1 more)

### Community 50 - "app.py"
Cohesion: 0.07
Nodes (47): ask(), ask_memory(), ask_sources(), ask_stream(), _events(), AskRequest, _attach_llm_meta(), _attach_portfolio_to_ask() (+39 more)

### Community 51 - "gold_service.py"
Cohesion: 0.13
Nodes (19): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+11 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "nav_service.py"
Cohesion: 0.22
Nodes (10): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), monthly_returns_from_records(), _read_cache() (+2 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (18): build_comparison_periods(), expense_ratio_for_question(), _f(), fund_returns_from_detail(), normalize_category_average_returns(), normalize_vs_benchmark_payload(), _optional_number(), parse_fund_costs() (+10 more)

### Community 55 - "contracts.py"
Cohesion: 0.03
Nodes (97): asks_macro_explanation(), question_mentions_fund_scheme(), rating_list_plan(), rating_concept_plan(), asks_fund_category_average(), AnswerMode, EvidenceRow, LLMUsageRecord (+89 more)

### Community 56 - "test_portfolio_intents.py"
Cohesion: 0.14
Nodes (19): render_portfolio_fact(), _set_investor_call(), plan_targets_catalog_on_holdings(), apply_portfolio_intent(), data_need_for(), modules_for(), normalize_portfolio_intent(), portfolio_intent_from_question() (+11 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "test_answer_quality_logs.py"
Cohesion: 0.14
Nodes (16): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), question_wants_gold_table(), clarify_plan_if_fund_unknown(), _plan_uses_fund_scoped_tools(), scrub_unknown_fund_mentions() (+8 more)

### Community 59 - "render_data_only_template"
Cohesion: 0.08
Nodes (17): question_needs_affected_sectors(), ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), test_bridge_runs_planned_wave2_when_trigger_is_none(), test_bridge_skips_wave2_for_data_only() (+9 more)

### Community 60 - "test_fund_risk.py"
Cohesion: 0.05
Nodes (64): asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison() (+56 more)

### Community 61 - "RequestTelemetry"
Cohesion: 0.16
Nodes (13): RequestTelemetry, stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed(), event_phase_started(), event_quality_check(), event_request_failed() (+5 more)

### Community 62 - "normalize_rs_label"
Cohesion: 0.08
Nodes (32): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), asks_rating_list() (+24 more)

### Community 63 - "re"
Cohesion: 0.10
Nodes (25): asks_financial_news(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+17 more)

### Community 64 - "bullion_retrieve.py"
Cohesion: 0.11
Nodes (7): _pack_row(), _retrieve_bullion_for_entities(), _trim_snippet(), describe_filters_for_log(), filter_spec(), _point_row(), QdrantReader

### Community 65 - "test_rupeestop_auth.py"
Cohesion: 0.12
Nodes (8): rupeestop_admin_request_headers(), _jwt(), test_admin_headers_include_bearer(), test_admin_headers_use_token_from_login(), test_bearer_prefers_auth_token_over_admin_token(), test_failed_login_keeps_previous_token(), test_non_admin_url_has_no_authorization(), test_valid_jwt_does_not_call_login()

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "datetime"
Cohesion: 0.14
Nodes (13): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_named_window_is_not_expanded(), test_vs_benchmark_module_is_not_replaced_by_snapshot() (+5 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.15
Nodes (14): asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), memory_shows_investor_book(), _tokens(), unknown_fund_phrase() (+6 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "embed.py"
Cohesion: 0.15
Nodes (9): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), embeddings_ready() (+1 more)

### Community 71 - "portfolio/cache.py"
Cohesion: 0.16
Nodes (17): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), find_cached_holdings(), get_normalized_portfolio(), peek_derived(), peek_portfolio() (+9 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "test_fact_answer.py"
Cohesion: 0.17
Nodes (19): _asks_portfolio_rs_ratings(), field_answer_needs_composer(), _investor_holdings_rows(), is_pure_field_answer(), render_benchmark_comparison_table(), render_fact_answer(), render_investor_rs_ratings_table(), _plan() (+11 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "stock_fund_ranking.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 77 - "universe.py"
Cohesion: 0.17
Nodes (18): _clean_holding_tokens(), instrument_to_qdrant_names(), match_holding_to_corpus_entity(), _aliases_for(), build_holding_entities(), canonical_key(), _display_name(), _holding_query() (+10 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 79 - "datetime"
Cohesion: 0.17
Nodes (16): run_fund_snapshot(), _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows() (+8 more)

### Community 80 - "resolve_display_table_policy"
Cohesion: 0.10
Nodes (20): DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark() (+12 more)

### Community 81 - "normalize.py"
Cohesion: 0.26
Nodes (14): aggregate_term_gains(), _allocation_block(), _apply_holding_values(), _drop_sold(), _first(), _holding_from_scheme(), normalize_workspace(), _num() (+6 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.14
Nodes (33): pending_rating_line(), _age(), _allocation_bucket_rows(), _as_of(), _book_line(), _category_amount_map(), _comparison_rows(), _composition_line() (+25 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "sector_fund_ranking.py"
Cohesion: 0.13
Nodes (13): classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path(), sector_ranking_data_available() (+5 more)

### Community 86 - "SectorFundRankingIndex"
Cohesion: 0.15
Nodes (3): normalize_sector_label(), _sector_label_in_text(), SectorFundRankingIndex

### Community 87 - "market_pulse.py"
Cohesion: 0.07
Nodes (38): _warmup_embeddings_background(), _run(), article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), embed_query(), warmup_query_vectors() (+30 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.14
Nodes (19): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+11 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 90 - "affected_sectors.py"
Cohesion: 0.24
Nodes (9): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+1 more)

### Community 91 - "CapabilityCache"
Cohesion: 0.15
Nodes (7): CapabilityCache, _Entry, get_capability_cache(), test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner(), test_capabilities_cache_stores_and_retrieves()

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "memory/__init__.py"
Cohesion: 0.15
Nodes (13): greeting_reply(), identity_reply(), _mirror_greeting(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens() (+5 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.07
Nodes (53): _add_category_comparison(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line(), _compare_cell(), _compare_header(), _complete_fund_row(), _complete_shown_funds() (+45 more)

### Community 96 - "_run_get_fund_data"
Cohesion: 0.11
Nodes (17): load_fund_risk(), rating_for_request(), rating_needs_pillars(), fetch_vs_benchmark(), merge_fund_insight_metrics(), _detail_for_fund_tool(), _fund_payload_matches_fund(), _isin_for_fund_name() (+9 more)

### Community 97 - "EvidencePack"
Cohesion: 0.16
Nodes (8): EvidencePack, test_compare_table_shows_the_drawdown_row(), test_screen_table_shows_the_drawdown_column(), test_expense_ratio_meaning_and_judgment_uses_composer(), test_compact_strips_contribution_from_data_attribution(), test_sanitize_data_pack_moves_pp_to_internal(), test_compose_always_uses_composer_for_largest_holding(), test_returns_table_for_investor_pnl()

### Community 98 - "test_macro_news_cache.py"
Cohesion: 0.16
Nodes (13): select_macro_for_question(), _digest(), test_banking_and_banks_are_one_search(), test_cache_keeps_the_article_body_not_only_the_title(), test_cache_searches_named_macro_parameters(), test_clusters_are_ordered_by_how_many_articles_are_in_the_db(), test_failed_refresh_keeps_the_previous_cache(), test_macro_news_is_reused_for_two_hours_then_overwritten() (+5 more)

### Community 99 - "retrieve_scoped_news"
Cohesion: 0.13
Nodes (20): corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news() (+12 more)

### Community 100 - "pathlib"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 102 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.24
Nodes (9): build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_default_manager_answer_drops_former_managers(), test_enrich_filters_past_only(), test_infer_roster_focus_current_vs_past() (+1 more)

### Community 106 - "enforce_planner_catalog_plan"
Cohesion: 0.08
Nodes (43): owned_holding_names(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings(), _ensure_portfolio_data_for_compare(), _ensure_portfolio_data_for_holdings(), ensure_whole_book_catalog_scope(), _funds_from_entities() (+35 more)

### Community 107 - "ask_plan.py"
Cohesion: 0.13
Nodes (20): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), _layered_news_topics(), _client() (+12 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.17
Nodes (9): CategoryMatch, fund_type_for_category(), match_all_fund_types(), _names_a_type(), _phrase_in(), rating_scope_pairs(), _spaced_category_words(), taxonomy_reply() (+1 more)

### Community 109 - "insight/portfolio_scope.py"
Cohesion: 0.14
Nodes (15): _articles_from_pack(), build_portfolio_news_impact_dossier(), ensure_portfolio_news_impact_plan(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown() (+7 more)

### Community 111 - "explicit_fund_count"
Cohesion: 0.15
Nodes (10): _category_fund_name_spec(), fund_naming_clause(), _label_in(), _looks_like_fund_list(), rating_screen_question(), _return_window(), _suggestion_spec(), explicit_fund_count() (+2 more)

### Community 112 - "strip_news_roundup"
Cohesion: 0.33
Nodes (6): append_news_section(), _insert_before_disclaimer(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 114 - ".lookup_extracted_fund"
Cohesion: 0.14
Nodes (14): _attach_trailing_product(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question() (+6 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 117 - "get_stock_profile"
Cohesion: 0.23
Nodes (5): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker(), holding_return_pct()

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "execute_capability"
Cohesion: 0.26
Nodes (7): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), test_compare_conversation_cache_does_not_reuse_different_pair(), fake_compare(), test_compare_conversation_cache_hits_same_pair(), test_compare_payload_matches_funds()

### Community 121 - "._ensure_loaded"
Cohesion: 0.15
Nodes (4): FundIndex, _infer_category_and_type(), resolve_canonical_isin(), _sync_amc_prefix_from_catalog()

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "lib/google_news.py"
Cohesion: 0.04
Nodes (40): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+32 more)

### Community 124 - "test_composer_table_summaries.py"
Cohesion: 0.24
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections()

### Community 125 - "compare_evidence.py"
Cohesion: 0.27
Nodes (7): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "portfolio/client.py"
Cohesion: 0.17
Nodes (12): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), PortfolioError, PortfolioNotConfigured, PortfolioUnavailable, PortfolioUpstreamError (+4 more)

### Community 128 - "macro_impact_map.py"
Cohesion: 0.14
Nodes (17): repo_root(), _rule_sector_picks(), canonical_direction_for_driver(), clear_macro_impact_cache(), _document(), _driver_row(), list_macro_drivers(), macro_impact_entry() (+9 more)

### Community 129 - "index_series.py"
Cohesion: 0.08
Nodes (31): nifty50_ticker(), aggregate_sectors_from_holdings(), extract_top_holdings(), extract_top_sectors(), normalize_holding_row(), normalize_sector_row(), _run_get_market_snapshot(), _price_holdings() (+23 more)

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

### Community 134 - "test_conversation_memory.py"
Cohesion: 0.12
Nodes (33): build_result(), _load_planner_memory(), _store_turn_memory(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), append_chat_turn(), _fresh(), get_memory() (+25 more)

### Community 135 - "sector_alignment.py"
Cohesion: 0.29
Nodes (9): analyze_sector_block(), canonical_sector_for_holding(), holdings_in_sector(), index_return_pct(), return_sign(), run_sector_holding_alignment(), _sector_news(), signs_opposite() (+1 more)

### Community 136 - "insights.py"
Cohesion: 0.30
Nodes (10): build_insights(), _equity_pct(), Insight, insight_lines(), insights_for_brief(), _num(), _style_band(), _book() (+2 more)

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
Cohesion: 0.04
Nodes (48): _json_default(), safe_json_dumps(), _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins() (+40 more)

### Community 141 - "concept_asks.py"
Cohesion: 0.17
Nodes (17): fund_type_name_spec(), apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), apply_pure_concept_plan(), question_is_pure_general_concept() (+9 more)

### Community 142 - "graph.py"
Cohesion: 0.08
Nodes (27): facts_only_compose_allowed(), strip_context_disclaimer(), _answer_stream_chunks(), _attach_conversation(), _catalog_fanout_fund_names(), _clean_answer(), _conversation_id(), _drop_scheme_is_the_whole_book() (+19 more)

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

### Community 159 - "fetch_public_rating"
Cohesion: 0.22
Nodes (6): fetch_public_rating(), rating_api_data_is_null(), _attach_rs_ratings_to_screen(), _one(), test_null_rating_data_is_a_pending_rating(), test_screen_rows_get_ratings_by_default()

### Community 163 - "fund_match.py"
Cohesion: 0.13
Nodes (11): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+3 more)

### Community 170 - "fund_catalog.py"
Cohesion: 0.17
Nodes (17): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+9 more)

### Community 178 - "test_metal_fund_rating.py"
Cohesion: 0.13
Nodes (13): ensure_quality_fund_list(), fetch_category_ratings(), _payload(), _rating(), test_category_rating_request_uses_admin_header(), test_gold_etf_only_stays_on_the_etf_category(), test_gold_fund_list_uses_only_gold_scheme_categories(), test_gold_list_spreads_etf_and_fund_of_funds() (+5 more)

### Community 180 - "shared_system_prefix"
Cohesion: 0.24
Nodes (7): build_anthropic_messages_body(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), _body(), test_planner_and_composer_share_the_first_system_block(), test_tools_stay_available_when_there_is_no_shared_prefix()

### Community 181 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

### Community 182 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 183 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 185 - "extract_top_holdings"
Cohesion: 0.19
Nodes (12): build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings(), test_a_holding_outside_the_top_five_still_gets_weight_and_sector() (+4 more)

### Community 186 - "entity_candidates.py"
Cohesion: 0.26
Nodes (7): candidates_block(), entity_candidates(), _holding_candidates(), _sector_candidates(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

### Community 187 - "relationships.py"
Cohesion: 0.42
Nodes (5): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships()

### Community 188 - "Path"
Cohesion: 0.40
Nodes (4): _env_files_for_token(), persist_rupeestop_auth_token(), _rewrite_env_token(), test_persist_sets_process_env()

### Community 190 - "asks_fund_related_news"
Cohesion: 0.24
Nodes (7): infer_fund_news_layers(), layers_to_retrieval_keys(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only(), test_overview_news_is_holdings_and_sectors()

### Community 191 - "plan_enforce.py"
Cohesion: 0.05
Nodes (71): asks_ideal_portfolio_shape(), category_composition_plan_applies(), ensure_name_fund_type_plan(), ensure_rating_list_funds(), ensure_unnamed_category_pair_compare_plan(), ExecutionPlan, merge_planner_asked_facts(), tag_answer_parts() (+63 more)

### Community 192 - "fact_slots.py"
Cohesion: 0.39
Nodes (5): asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value()

### Community 193 - "contains_phrase"
Cohesion: 0.70
Nodes (3): _holding_mentioned(), matches_entity(), contains_phrase()

### Community 194 - "test_rating_screen_uses_focus_question_not_full_compare_question"
Cohesion: 0.40
Nodes (3): test_rating_screen_uses_focus_question_not_full_compare_question(), test_rating_screen_uses_forced_category_spec(), fake_fetch()

### Community 195 - "top_n_from_question"
Cohesion: 0.36
Nodes (5): top_n_from_question(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

### Community 197 - "QuestionBrief"
Cohesion: 0.08
Nodes (32): asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief(), _detect_direction(), _detect_funds() (+24 more)

### Community 199 - "news_insight_articles"
Cohesion: 0.22
Nodes (7): _news_subject(), clean_news_insight(), news_insight_articles(), strip_publisher(), _subject_words(), test_news_about_hdfc_bank_is_not_a_market_pulse(), test_news_insight_drops_publisher_clips_and_unrelated_articles()

### Community 200 - "data_pack.py"
Cohesion: 0.32
Nodes (4): build_data_pack(), build(), _compact(), test_data_pack_groups_by_fund_and_hides_internal_fields()

### Community 203 - "fund_brief.py"
Cohesion: 0.10
Nodes (30): qdrant_filter_names(), _article_entities(), build_events(), cluster_articles(), _cluster_entities(), compose_fund_insight(), _day_key(), _empty_brief() (+22 more)

### Community 206 - "test_holding_overlap.py"
Cohesion: 0.13
Nodes (14): extra_part_brief(), table_source(), _compare_return_windows(), _detail(), test_a_comparison_keeps_one_three_and_five_years_plus_benchmark_and_rating(), test_compare_table_includes_risk_for_both_funds(), test_extra_part_brief_names_both_funds(), test_no_overlap_message_and_overlap_table() (+6 more)

### Community 207 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

### Community 212 - "prompts.py"
Cohesion: 0.29
Nodes (4): build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1614 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `plan_enforce.py` to `insight/portfolio_scope.py`, `index_series.py`, `test_conversation_memory.py`, `test_fund_drawdown.py`, `test_portfolio_layer.py`, `json`, `concept_asks.py`, `graph.py`, `plan.py`, `fund_rating_screen.py`, `QueryLogger`, `ToolCall`, `investor_subject.py`, `test_macro_scope.py`, `category_plan.py`, `fields.py`, `fetch_public_rating`, `task_exec.py`, `update.py`, `fund_context.py`, `pack_sanitize.py`, `test_fund_rating_screen.py`, `test_portfolio_startup_cache.py`, `test_insight_graph.py`, `test_answer_precision.py`, `test_metal_fund_rating.py`, `gold_service.py`, `contracts.py`, `test_portfolio_intents.py`, `test_answer_quality_logs.py`, `render_data_only_template`, `test_fund_risk.py`, `RequestTelemetry`, `fact_slots.py`, `news_insight_articles`, `test_fact_answer.py`, `test_holding_overlap.py`, `datetime`, `resolve_display_table_policy`, `fact_answer.py`, `test_portfolio_allocation.py`, `evidence_pack.py`, `EvidencePack`, `enforce_planner_catalog_plan`, `insight/portfolio_scope.py`, `test_composer_table_summaries.py`, `compare_evidence.py`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Are the 38 inferred relationships involving `ExecutionPlan` (e.g. with `apply_concept_example_to_plan()` and `append_investor_portfolio_overview_tables()`) actually correct?**
  _`ExecutionPlan` has 38 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.057161290322580646 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `llm_client.py` to `insight/portfolio_scope.py`, `get_sector_fund_ranking_index`, `interpret.py`, `test_portfolio_layer.py`, `executor.py`, `test_portfolio_layer.py`, `compute.py`, `graph.py`, `plan.py`, `tools.py`, `news_reader.py`, `investor_subject.py`, `ensure_registry`, `query_log.py`, `Any`, `fund_match.py`, `fund_search.py`, `test_portfolio_startup_cache.py`, `rupeestop_auth.py`, `app.py`, `gold_service.py`, `contracts.py`, `test_fund_risk.py`, `bullion_retrieve.py`, `test_rupeestop_auth.py`, `datetime`, `insight/guardrails.py`, `QuestionBrief`, `embed.py`, `portfolio/cache.py`, `fund_brief.py`, `stock_fund_ranking.py`, `sector_fund_ranking.py`, `market_pulse.py`, `affected_sectors.py`, `CapabilityCache`, `retrieve_scoped_news`, `insight/portfolio_scope.py`, `execute_capability`, `._ensure_loaded`, `lib/google_news.py`, `portfolio/client.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ToolCall` (e.g. with `execute_capability()` and `execute_wave()`) actually correct?**
  _`ToolCall` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `insight/portfolio_scope.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11074197120708748 - nodes in this community are weakly interconnected._