# Graph Report - db_design_with_qdrant_locally  (2026-11-13)

## Corpus Check
- 510 files · ~882,899 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 5676 nodes · 18211 edges · 211 communities (179 shown, 32 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 652 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8c4c6f18`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- NewsStore
- fund_rating_screen.py
- interpret.py
- fields.py
- article_quality.py
- lib/portfolio_scope.py
- time
- test_ask_speed.py
- Settings
- test_fund_drawdown.py
- test_pick_shown_fund.py
- get_sector_fund_ranking_index
- compute.py
- _attach_screen_facts
- tools.py
- fund_display.py
- update.py
- QueryLogger
- news_reader.py
- lib/portfolio_scope.py
- fact_slots.py
- Settings
- failure_ledger.py
- tool_runners.py
- category_plan.py
- test_fund_display_tables.py
- ensure_registry
- resolve_fund_for_query
- fund_name_gate.py
- sector_alignment.py
- pipeline.py
- executor.py
- task_exec.py
- llm_client.py
- book_news_map.py
- fund_search.py
- normalize.py
- investor_drawback.py
- test_fund_rating_screen.py
- env
- investor_subject.py
- contracts.py
- test_call_json_llm.py
- macro_news_cache.py
- env
- affected_sectors.py
- rupeestop_auth.py
- sources/google_news.py
- fund_scheme_match.py
- get_settings
- gold_service.py
- env
- insight/portfolio_scope.py
- fund_rupeestop_metrics.py
- slot_router.py
- test_portfolio_intents.py
- scrape-worker/package.json
- _normalize_fund_text
- question_intent.py
- test_fund_risk.py
- graph.py
- scoped_retrieve.py
- re
- nav_service.py
- test_investor_grounding.py
- batch.ts
- validate_capability_args
- insight/guardrails.py
- http-fetch.ts
- embed.py
- portfolio/cache.py
- retrieve_scoped_news
- graph.py
- with
- stock_fund_ranking.py
- ExecutionPlan
- stock_fund_ranking.py
- test_holding_overlap.py
- display_table_policy.py
- test_portfolio_layer.py
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- news_rag/config.py
- test_rupeestop_auth.py
- test_portfolio_layer.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- nse_sector_indices.py
- compare_evidence.py
- env
- plan_system_prompt
- steps
- evidence_pack.py
- portfolio/client.py
- concept_asks.py
- test_fund_payload_first.py
- evidence.py
- pathlib
- test_two_wave_pipeline.py
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- macro_impact_map.py
- market_pulse.py
- fund_rating_categories.py
- plan_enforce.py
- test_fact_answer.py
- aggregate_fund_holdings.py
- test_macro_news_cache.py
- news_digest.py
- ._ensure_loaded
- vitest
- format_inr
- test_macro_scope.py
- compilerOptions
- compilerOptions
- test_news_only_answer.py
- argparse
- backfill
- lib/google_news.py
- test_composer_table_summaries.py
- _return_slice_covers
- run-pipeline
- test_metal_fund_rating.py
- get_stock_profile
- index_series.py
- worker/src/index.ts
- steps
- steps
- with
- planner_catalog_knowledge.py
- top_n_from_question
- insights.py
- inputs
- with
- inputs
- json
- prompts.py
- append_investor_portfolio_overview_tables
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
- relationships.py
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_catalog.py
- diagnose_lightsail_site.sh
- RunLogger
- re
- EntityFunnel
- _run_screen_funds_by_exposure
- test_answer_precision.py
- build_derived_views
- market_scope_entities
- csv
- extract_top_holdings
- entity_candidates.py
- strip_missing_data_caveats
- typing
- strip_news_roundup
- _category_fund_name_spec
- metals_spot_tables.py
- planner_policy.py
- node_route
- Path
- QuestionBrief
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- compare_ask_speed.py
- json_util.py
- fund_brief.py
- _amc_outside_label
- contains_phrase
- datetime
- portfolio_news_impact.py
- ToolCall

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 605 edges
2. `ToolCall` - 367 edges
3. `get_settings()` - 141 edges
4. `apply_planner_post_hooks()` - 123 edges
5. `AnswerMode` - 109 edges
6. `QueryLogger` - 100 edges
7. `node_compose()` - 100 edges
8. `QuestionBrief` - 88 edges
9. `slot_route()` - 84 edges
10. `Settings` - 83 edges

## Surprising Connections (you probably didn't know these)
- `test_allocation_drops_dust_and_matches_book_aum()` --calls--> `normalize_workspace()`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/portfolio/normalize.py
- `test_book_schemes_are_the_open_holdings()` --calls--> `normalize_workspace()`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/portfolio/normalize.py
- `test_current_value_and_nonzero_xirr()` --calls--> `normalize_workspace()`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/portfolio/normalize.py
- `test_normalize_allocation_from_live_books_total()` --calls--> `normalize_workspace()`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/portfolio/normalize.py
- `test_project_pnl_scheme_without_filter_returns_schemes()` --calls--> `project_modules()`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/portfolio/project.py

## Import Cycles
- None detected.

## Communities (211 total, 32 thin omitted)

### Community 0 - "logging"
Cohesion: 0.08
Nodes (39): get_entity_funnel(), build_graph(), dedupe_and_alias(), drop_old_points(), embed_and_upsert(), _compact_fetch_errors(), fetch_google_news(), jev_article_scores() (+31 more)

### Community 1 - "NewsStore"
Cohesion: 0.05
Nodes (23): _to_article(), EntityScore, StoredArticle, is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), scrape_article_url() (+15 more)

### Community 2 - "fund_rating_screen.py"
Cohesion: 0.06
Nodes (46): categories_for(), metal_scheme_categories(), pickable_categories(), _add_category_comparison(), _allocation_mix_spec(), _amc_matches(), _apply_category_difference(), asks_balanced_long_horizon_fund_menu() (+38 more)

### Community 3 - "interpret.py"
Cohesion: 0.06
Nodes (70): asks_random_fund_compare(), Findings, FundFinding, SectorFinding, mentions_publication_date(), publication_date_keys(), _assemble(), _caveat() (+62 more)

### Community 4 - "fields.py"
Cohesion: 0.09
Nodes (32): _asks_book(), bind_fields_to_tools(), _book_fields(), field_need(), FieldNeed, fields_from_question(), _find_term(), _fund_fields() (+24 more)

### Community 5 - "article_quality.py"
Cohesion: 0.13
Nodes (18): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+10 more)

### Community 6 - "lib/portfolio_scope.py"
Cohesion: 0.16
Nodes (18): instrument_to_qdrant_names(), match_holding_to_corpus_entity(), load_portfolio_universe(), _aliases_for(), build_holding_entities(), canonical_key(), _display_name(), _holding_query() (+10 more)

### Community 7 - "time"
Cohesion: 0.11
Nodes (34): _conversation_id(), _load_planner_memory(), _store_turn_memory(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), chat_history_view(), _chat_turn_rows(), format_chat_history_block() (+26 more)

### Community 8 - "test_ask_speed.py"
Cohesion: 0.10
Nodes (25): collect_evidence_calendar_dates(), add_article(), cores_for_float(), cores_in_text(), derived_cores(), finalize_text_fields(), format_user_calendar_date(), number_is_grounded() (+17 more)

### Community 9 - "Settings"
Cohesion: 0.06
Nodes (44): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), repo_root(), _bucket(), _entity_names(), fetch_window_fields() (+36 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (58): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+50 more)

### Community 11 - "test_pick_shown_fund.py"
Cohesion: 0.10
Nodes (19): _metal_fund_categories(), fund_picked_from_prior_answer(), funds_from_shown_list(), _list_count(), _list_question(), merge_fund_isins_map(), question_picks_one_shown_fund(), question_refers_to_shown_list() (+11 more)

### Community 12 - "get_sector_fund_ranking_index"
Cohesion: 0.08
Nodes (34): execute_wave(), get_sector_fund_ranking_index(), asks_fund_portfolio_holdings(), asks_funds_holding_stock(), asks_funds_with_sector_exposure(), _clean_stock_capture(), _resolved_scheme_for_portfolio_ask(), screen_hints_from_question() (+26 more)

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (46): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+38 more)

### Community 14 - "_attach_screen_facts"
Cohesion: 0.12
Nodes (22): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), infer_anchor_label_from_excludes() (+14 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (49): rank_funds_by_sector_exposure(), _active_sector_equity(), _articles_for_affected_question(), _as_date(), asks_equity_funds(), _broad_working_well_keys(), _catalog_candidates(), _drop_stale_nav() (+41 more)

### Community 16 - "fund_display.py"
Cohesion: 0.12
Nodes (27): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+19 more)

### Community 17 - "update.py"
Cohesion: 0.14
Nodes (19): drop_old_turns(), add_gist(), empty_frame(), empty_state(), expire_stale_entities(), push_fund(), stack_entry(), _subject() (+11 more)

### Community 18 - "QueryLogger"
Cohesion: 0.08
Nodes (15): compose_fund_insight(), _empty_brief(), generate_fund_brief(), format_insight_display(), ParsedQuery, clip_log_text(), find_query_log_file(), _kv() (+7 more)

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (38): _article_context_for_interpret(), measured_facts_block(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority() (+30 more)

### Community 20 - "lib/portfolio_scope.py"
Cohesion: 0.17
Nodes (16): build_portfolio_scope(), FundRef, _holding_equity_allowed(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest(), load_portfolio_funds() (+8 more)

### Community 21 - "fact_slots.py"
Cohesion: 0.15
Nodes (14): asked_slots(), merge_planner_asked_facts(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), slots_from_plan(), tag_answer_parts() (+6 more)

### Community 22 - "Settings"
Cohesion: 0.10
Nodes (16): Publisher, SectorQuery, Settings, apply_fresh_start(), _clear_run_json_summaries(), clear_scrape_workspace(), remove_scrape_artifacts(), remove_scrape_artifacts_many() (+8 more)

### Community 23 - "failure_ledger.py"
Cohesion: 0.08
Nodes (32): _merge_publisher_error_reasons(), write_day_report(), _atomic_write(), day_failure_slices_for_run(), ensure_loaded(), _failures_dir(), flush(), is_google_exhausted() (+24 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.10
Nodes (47): build_holding_overlap(), build_default_registry(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+39 more)

### Community 25 - "category_plan.py"
Cohesion: 0.05
Nodes (54): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), fund_type_name_spec(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), asks_cross_category_compare() (+46 more)

### Community 26 - "test_fund_display_tables.py"
Cohesion: 0.07
Nodes (31): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers() (+23 more)

### Community 27 - "ensure_registry"
Cohesion: 0.07
Nodes (51): _brief_system(), canonical_facet(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence() (+43 more)

### Community 28 - "resolve_fund_for_query"
Cohesion: 0.14
Nodes (19): lookup_extracted_fund(), _lookup_fund_scan_question(), resolve_fund_for_query(), test_absl_and_ppfas_shorthand(), test_absl_conservative_hybrid_active_fof(), test_absl_gold_etf_is_the_etf_not_a_gold_fund_list(), test_absl_large_cap_is_not_frontline_or_the_trigger_plan(), test_absl_nifty_50_etf_not_momentum_200() (+11 more)

### Community 29 - "fund_name_gate.py"
Cohesion: 0.15
Nodes (13): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), question_wants_gold_table(), scrub_unknown_fund_mentions(), test_gold_price_still_wants_a_draft_table(), test_invested_in_gold_is_not_a_spot_price_ask() (+5 more)

### Community 30 - "sector_alignment.py"
Cohesion: 0.17
Nodes (12): clear_macro_impact_cache(), analyze_sector_block(), canonical_sector_for_holding(), holding_return_pct(), holdings_in_sector(), index_return_pct(), return_sign(), _sector_news() (+4 more)

### Community 31 - "pipeline.py"
Cohesion: 0.24
Nodes (3): run_insight_pipeline(), stream_insight_pipeline(), test_streaming_sse_order()

### Community 32 - "executor.py"
Cohesion: 0.06
Nodes (46): fetch_vs_benchmark(), get_fund_index(), get_capability_cache(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _compare_payload_matches_funds(), _conversation_id() (+38 more)

### Community 33 - "task_exec.py"
Cohesion: 0.05
Nodes (65): explanation_brief(), canonicalize_field(), field_prompt_table(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), _label_for_days() (+57 more)

### Community 34 - "llm_client.py"
Cohesion: 0.07
Nodes (57): ask(), ask_stream(), AskRequest, _attach_llm_meta(), fund_brief(), health(), get_settings(), Settings (+49 more)

### Community 35 - "book_news_map.py"
Cohesion: 0.21
Nodes (14): _clean_holding_tokens(), book_wide_sectors(), _display_name(), _has_named_stock(), news_calls_for_book(), _news_name(), _pct(), resolve_book_sector() (+6 more)

### Community 36 - "fund_search.py"
Cohesion: 0.10
Nodes (23): aggregate_sectors_from_holdings(), _clean_company_name(), detail_has_live_facts(), _entry_matches_query_scheme(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers(), _fund_text() (+15 more)

### Community 37 - "normalize.py"
Cohesion: 0.15
Nodes (21): aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values(), _book_has_market_value(), _fill_missing_from_live(), _first() (+13 more)

### Community 38 - "investor_drawback.py"
Cohesion: 0.12
Nodes (21): _fund_performance_digest(), attach_drawback_digest(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer(), _display_holding_row(), _enrich_investor_computed_fields(), _internal_contribution_row() (+13 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.09
Nodes (45): asks_taxonomy(), match_all_fund_types(), parse_rating_screen(), _return_direction(), run_rating_list(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap() (+37 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "investor_subject.py"
Cohesion: 0.03
Nodes (108): plan_wants_single_scheme_risk(), pick_best_matching_scheme(), resolve_fund_from_question(), _amc_token_set(), _bound_fund_name(), _compare_sides_resolvable(), _known_names_in_text(), question_refers_deictic_fund_safe() (+100 more)

### Community 42 - "contracts.py"
Cohesion: 0.04
Nodes (58): _followup_modules(), AnswerMode, EvidenceRow, build_evidence_pack(), ensure_fund_concentration_plan(), ensure_compare_template(), ensure_multi_fact_tools(), ensure_planner_fund_fact_modules() (+50 more)

### Community 43 - "test_call_json_llm.py"
Cohesion: 0.14
Nodes (19): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), _layered_news_topics(), _client() (+11 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.21
Nodes (10): _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), _search_macro_parameters() (+2 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "affected_sectors.py"
Cohesion: 0.16
Nodes (12): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+4 more)

### Community 47 - "rupeestop_auth.py"
Cohesion: 0.24
Nodes (11): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url(), _looks_like_jwt() (+3 more)

### Community 48 - "sources/google_news.py"
Cohesion: 0.15
Nodes (15): _absorb_into_candidate(), _dedupe_candidates(), _find_story_match(), _is_duplicate(), fetch_entity_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url() (+7 more)

### Community 49 - "fund_scheme_match.py"
Cohesion: 0.15
Nodes (17): is_quant_amc_entry(), is_quantum_amc_entry(), amc_token_in_question(), _category_phrases_in_question(), _constraint_in_scheme_name(), _distinctive_constraints(), question_amc_hints(), scheme_match_score() (+9 more)

### Community 50 - "get_settings"
Cohesion: 0.09
Nodes (35): ask_memory(), ask_query_log(), ask_sources(), _attach_portfolio_to_ask(), backfill_page(), backfill_start(), backfill_status(), backfill_stop() (+27 more)

### Community 51 - "gold_service.py"
Cohesion: 0.13
Nodes (17): _fetch(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date(), _point_on_or_before() (+9 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "insight/portfolio_scope.py"
Cohesion: 0.06
Nodes (50): plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), _category_slug_from_question(), plan_targets_single_fund_measured_return(), question_asks_category_book_share(), question_asks_category_money(), question_asks_holding_metric_and_glossary(), bind_cached_portfolio() (+42 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.11
Nodes (20): build_comparison_periods(), expense_ratio_for_question(), _f(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns(), normalize_vs_benchmark_payload(), _optional_number() (+12 more)

### Community 55 - "slot_router.py"
Cohesion: 0.06
Nodes (35): rating_list_plan(), rating_concept_plan(), QueryClass, ScopeKind, Wave2Policy, _slot_fallback(), normalize_portfolio_plan_from_question(), _asks_catalog_fund_performance() (+27 more)

### Community 56 - "test_portfolio_intents.py"
Cohesion: 0.15
Nodes (17): apply_portfolio_intent(), data_need_for(), _keep_book_news(), modules_for(), normalize_portfolio_intent(), portfolio_intent_from_question(), shape_for(), should_attach_news() (+9 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "_normalize_fund_text"
Cohesion: 0.15
Nodes (13): _attach_trailing_product(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question() (+5 more)

### Community 59 - "question_intent.py"
Cohesion: 0.11
Nodes (19): infer_fund_news_layers(), plan_matches_intent(), prefers_planner_over_slot(), QuestionIntent, resolve_question_intent(), _top_n_from_question(), asks_fund_related_news(), test_asks_fund_related_news() (+11 more)

### Community 60 - "test_fund_risk.py"
Cohesion: 0.06
Nodes (48): asks_about_score_bands(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison(), asks_score_only(), _ensure_pillar_rating_plan() (+40 more)

### Community 61 - "graph.py"
Cohesion: 0.12
Nodes (16): LLMUsageRecord, PhaseRecord, RequestTelemetry, ToolRecord, stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed() (+8 more)

### Community 62 - "scoped_retrieve.py"
Cohesion: 0.05
Nodes (37): _warmup_embeddings_background(), _run(), _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), embed_query() (+29 more)

### Community 63 - "re"
Cohesion: 0.08
Nodes (28): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+20 more)

### Community 64 - "nav_service.py"
Cohesion: 0.17
Nodes (12): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+4 more)

### Community 65 - "test_investor_grounding.py"
Cohesion: 0.19
Nodes (13): repair_investor_insight_prose(), strip_grounding_holes(), investor_book_cores(), sanitize_data_pack_for_composer(), _sample_book(), test_grounding_keeps_category_weight_in_prose(), test_investor_book_cores_includes_pnl_term_gains(), test_investor_book_cores_includes_rounded_allocation_pct() (+5 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "validate_capability_args"
Cohesion: 0.12
Nodes (15): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded() (+7 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.13
Nodes (15): asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), memory_shows_investor_book(), mentions_advice(), _tokens() (+7 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "embed.py"
Cohesion: 0.14
Nodes (9): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), embeddings_ready() (+1 more)

### Community 71 - "portfolio/cache.py"
Cohesion: 0.13
Nodes (20): _run_get_investor_portfolio(), _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), get_active_crn(), get_normalized_portfolio(), peek_derived() (+12 more)

### Community 72 - "retrieve_scoped_news"
Cohesion: 0.08
Nodes (28): _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news(), _sector_entities() (+20 more)

### Community 73 - "graph.py"
Cohesion: 0.05
Nodes (55): asks_fund_risk(), asks_hidden_rating(), asks_sebi_riskometer(), blocked_reply(), EvidencePack, question_wants_concentration_tables(), render_investor_concentration_answer(), facts_only_compose_allowed() (+47 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "stock_fund_ranking.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 77 - "ExecutionPlan"
Cohesion: 0.07
Nodes (47): ExecutionPlan, _attach_rs_ratings_to_screen(), owned_holding_names(), owned_holding_rows(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings(), _ensure_portfolio_data_for_compare() (+39 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 79 - "test_holding_overlap.py"
Cohesion: 0.10
Nodes (17): _add_category_comparison(), _compare_brief_line(), extra_part_brief(), table_source(), _compare_return_windows(), _detail(), test_a_comparison_keeps_one_three_and_five_years_plus_benchmark_and_rating(), test_compare_table_includes_risk_for_both_funds() (+9 more)

### Community 80 - "display_table_policy.py"
Cohesion: 0.10
Nodes (19): DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark() (+11 more)

### Community 81 - "test_portfolio_layer.py"
Cohesion: 0.15
Nodes (9): fetch_top_holdings(), project_concentration(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore (+1 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.13
Nodes (36): _age(), _allocation_bucket_rows(), _as_of(), _book_line(), _category_amount_map(), _comparison_rows(), _composition_line(), _float_or_none() (+28 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "news_rag/config.py"
Cohesion: 0.08
Nodes (15): classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path(), _sector_label_in_text() (+7 more)

### Community 86 - "test_rupeestop_auth.py"
Cohesion: 0.12
Nodes (8): rupeestop_admin_request_headers(), _jwt(), test_admin_headers_include_bearer(), test_admin_headers_use_token_from_login(), test_bearer_prefers_auth_token_over_admin_token(), test_failed_login_keeps_previous_token(), test_non_admin_url_has_no_authorization(), test_valid_jwt_does_not_call_login()

### Community 87 - "test_portfolio_layer.py"
Cohesion: 0.11
Nodes (13): _drop_sold(), normalized_doc(), test_allocation_drops_dust_and_matches_book_aum(), test_book_schemes_are_the_open_holdings(), test_current_value_and_nonzero_xirr(), test_holdings_table_uses_exact_value(), test_normalize_allocation_from_live_books_total(), test_portfolio_concentration_report_format() (+5 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.14
Nodes (19): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+11 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 90 - "nse_sector_indices.py"
Cohesion: 0.20
Nodes (11): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _clear_index_cache(), test_by_sector_keys_match_sector_queries_exactly(), test_every_sector_has_verified_ticker_field() (+3 more)

### Community 91 - "compare_evidence.py"
Cohesion: 0.24
Nodes (8): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_maybe_run_compare_retries_after_failed_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "plan_system_prompt"
Cohesion: 0.23
Nodes (8): plan_system_prompt(), build_anthropic_messages_body(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), _body(), test_planner_and_composer_share_the_first_system_block(), test_tools_stay_available_when_there_is_no_shared_prefix()

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.08
Nodes (49): _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_cell(), _compare_header(), _complete_fund_row(), _complete_shown_funds(), _concentration_markdown(), _drawdown_body() (+41 more)

### Community 96 - "portfolio/client.py"
Cohesion: 0.15
Nodes (15): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), InvalidCRN, PortfolioError, PortfolioNotConfigured, PortfolioUnavailable (+7 more)

### Community 97 - "concept_asks.py"
Cohesion: 0.31
Nodes (10): apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), asks_fof_funds(), test_concept_example_plan_screen_fof(), test_fof_name_one_detected() (+2 more)

### Community 98 - "test_fund_payload_first.py"
Cohesion: 0.15
Nodes (11): fetch_public_rating(), headline_rating(), pending_rating_line(), rating_api_data_is_null(), rating_for_request(), rating_needs_pillars(), _one(), test_headline_helper_drops_computed_at() (+3 more)

### Community 99 - "evidence.py"
Cohesion: 0.15
Nodes (15): _compare_cache_label(), clear_conversation(), drain_cache_events(), recall_slice(), recall_wider_portfolio(), remember_slice(), slice_key(), slice_slot() (+7 more)

### Community 100 - "pathlib"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 102 - "test_two_wave_pipeline.py"
Cohesion: 0.09
Nodes (13): ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), test_bridge_skips_wave2_for_data_only(), test_bridge_skips_when_return_positive(), test_bridge_triggers_on_negative_return() (+5 more)

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.20
Nodes (11): asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score(), test_default_manager_answer_drops_former_managers() (+3 more)

### Community 106 - "macro_impact_map.py"
Cohesion: 0.23
Nodes (12): _rule_sector_picks(), canonical_direction_for_driver(), _document(), _driver_row(), list_macro_drivers(), macro_impact_entry(), macro_series_for_driver(), normalize_direction() (+4 more)

### Community 107 - "market_pulse.py"
Cohesion: 0.10
Nodes (27): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), _one(), _fetch_macro_query(), _query_variants(), run_macro_news_enhanced() (+19 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.15
Nodes (15): CategoryMatch, _close(), fund_type_for_category(), _metal_category(), _metal_flags(), _names_a_type(), _phrase_score(), rating_scope_pairs() (+7 more)

### Community 109 - "plan_enforce.py"
Cohesion: 0.07
Nodes (32): asks_ideal_portfolio_shape(), ensure_rating_screen(), question_signals_investor_book(), question_asks_current_book_allocation(), apply_category_scoped_compare_funds(), _asks_ideal_portfolio_allocation(), _compare_category_slug(), drop_misclassified_category_composition() (+24 more)

### Community 110 - "test_fact_answer.py"
Cohesion: 0.16
Nodes (19): _asks_portfolio_rs_ratings(), field_answer_needs_composer(), is_pure_field_answer(), render_benchmark_comparison_table(), render_fact_answer(), render_investor_rs_ratings_table(), wants_comparison_table(), _plan() (+11 more)

### Community 111 - "aggregate_fund_holdings.py"
Cohesion: 0.23
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 112 - "test_macro_news_cache.py"
Cohesion: 0.16
Nodes (13): select_macro_for_question(), _digest(), test_banking_and_banks_are_one_search(), test_cache_keeps_the_article_body_not_only_the_title(), test_cache_searches_named_macro_parameters(), test_clusters_are_ordered_by_how_many_articles_are_in_the_db(), test_failed_refresh_keeps_the_previous_cache(), test_macro_news_is_reused_for_two_hours_then_overwritten() (+5 more)

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 114 - "._ensure_loaded"
Cohesion: 0.18
Nodes (3): FundIndex, _infer_category_and_type(), _sync_amc_prefix_from_catalog()

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 117 - "test_macro_scope.py"
Cohesion: 0.16
Nodes (11): question_is_standalone_macro(), ensure_catalog_tools_for_fund_news(), apply_standalone_macro_scope(), _macro_news_topics(), test_fund_news_adds_catalog_tools(), test_how_its_affecting_rupee_is_not_deictic_fund_title(), test_macro_scope_injects_news_when_planner_sent_no_tools(), test_macro_scope_strips_fund_tools() (+3 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "test_news_only_answer.py"
Cohesion: 0.19
Nodes (9): _news_subject(), clean_news_insight(), complete_sentences(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words(), test_news_about_hdfc_bank_is_not_a_market_pulse() (+1 more)

### Community 121 - "argparse"
Cohesion: 0.24
Nodes (4): check(), main(), run_case(), _Usage

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "lib/google_news.py"
Cohesion: 0.04
Nodes (37): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+29 more)

### Community 124 - "test_composer_table_summaries.py"
Cohesion: 0.19
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections()

### Community 125 - "_return_slice_covers"
Cohesion: 0.10
Nodes (16): CapabilityCache, _Entry, _return_slice_covers(), _trim_cached_to_ask(), test_missing_window_is_not_covered(), test_wider_cached_fund_payload_covers_and_trims_to_the_ask(), _wide(), test_return_slice_requires_pillars_when_requested() (+8 more)

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "test_metal_fund_rating.py"
Cohesion: 0.13
Nodes (13): ensure_quality_fund_list(), fetch_category_ratings(), _payload(), _rating(), test_category_rating_request_uses_admin_header(), test_gold_etf_only_stays_on_the_etf_category(), test_gold_fund_list_uses_only_gold_scheme_categories(), test_gold_list_spreads_etf_and_fund_of_funds() (+5 more)

### Community 128 - "get_stock_profile"
Cohesion: 0.25
Nodes (4): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker()

### Community 129 - "index_series.py"
Cohesion: 0.09
Nodes (30): get_gold_snapshot(), nifty50_ticker(), extract_top_holdings(), extract_top_sectors(), _run_get_market_snapshot(), _run_get_portfolio_data(), _price_holdings(), benchmark_return_for_scheme() (+22 more)

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

### Community 134 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 135 - "top_n_from_question"
Cohesion: 0.36
Nodes (5): top_n_from_question(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

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
Cohesion: 0.14
Nodes (15): main(), fetch_fund(), load_done_isins(), load_isins(), main(), _pct(), run(), write_final() (+7 more)

### Community 141 - "prompts.py"
Cohesion: 0.25
Nodes (5): build_brief_prompt(), build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 142 - "append_investor_portfolio_overview_tables"
Cohesion: 0.25
Nodes (5): append_investor_portfolio_overview_tables(), strip_unasked_scheme_names(), question_asks_all_schemes_in_answer(), question_wants_scheme_names(), test_portfolio_overview_omits_scheme_names()

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

### Community 159 - "relationships.py"
Cohesion: 0.42
Nodes (5): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships()

### Community 163 - "fund_match.py"
Cohesion: 0.11
Nodes (14): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+6 more)

### Community 170 - "fund_catalog.py"
Cohesion: 0.16
Nodes (16): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+8 more)

### Community 174 - "RunLogger"
Cohesion: 0.25
Nodes (5): finish_run_logger(), RunLogger, start_run_logger(), main(), _run_test()

### Community 178 - "re"
Cohesion: 0.10
Nodes (22): question_needs_affected_sectors(), question_mentions_fund_scheme(), _looks_like_fund_list(), asks_category_performance(), asks_fund_category_average(), asks_precise_definition(), direct_glossary_reply(), extract_glossary_term() (+14 more)

### Community 180 - "_run_screen_funds_by_exposure"
Cohesion: 0.13
Nodes (11): asks_rating_list(), fund_naming_clause(), rating_screen_question(), _run_screen_funds_by_exposure(), _named_scheme_category(), pick_random_scheme_category_for_compare(), test_debt_type_picks_a_debt_scheme_category(), test_debt_fund_type_not_confused_by_equity_education_clause() (+3 more)

### Community 181 - "test_answer_precision.py"
Cohesion: 0.17
Nodes (9): fact_values_already_stated(), question_wants_fact_table(), strip_meta_opening_heading(), _strip_unasked_closers(), test_fact_table_only_for_compare_or_an_explicit_list(), test_fact_table_skipped_when_prose_has_the_figure(), test_next_steps_and_summary_are_removed(), test_specific_lookup_has_no_default_table() (+1 more)

### Community 182 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 183 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

### Community 185 - "extract_top_holdings"
Cohesion: 0.17
Nodes (13): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings() (+5 more)

### Community 186 - "entity_candidates.py"
Cohesion: 0.26
Nodes (7): candidates_block(), entity_candidates(), _holding_candidates(), _sector_candidates(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

### Community 187 - "strip_missing_data_caveats"
Cohesion: 0.25
Nodes (6): strip_missing_data_caveats(), strip_private_leaks(), test_a_rating_pick_does_not_apologise_for_returns_or_pillars(), test_missing_apology_and_private_leak_are_removed(), test_strip_removes_risk_trend_apology(), test_a_gap_apology_is_removed_and_a_real_point_stays()

### Community 188 - "typing"
Cohesion: 0.07
Nodes (13): _events(), run_ask_engine(), stream_ask_engine(), trim_news_grouped(), attach_query_log_meta(), new_fund_brief_logger(), new_query_logger(), query_log_page_href() (+5 more)

### Community 190 - "strip_news_roundup"
Cohesion: 0.33
Nodes (6): append_news_section(), _insert_before_disclaimer(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 191 - "_category_fund_name_spec"
Cohesion: 0.40
Nodes (4): _category_fund_name_spec(), _label_in(), _return_window(), _suggestion_spec()

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 193 - "planner_policy.py"
Cohesion: 0.09
Nodes (22): sector_focus_from_market(), _invalidate_plan_system_cache(), apply_now_window(), drop_unasked_fund_modules(), _ensure_sector_overview(), finalize_planner_plan(), question_uses_now_window(), trim_named_fund_overview() (+14 more)

### Community 194 - "node_route"
Cohesion: 0.12
Nodes (12): asks_computed_illustration(), GraphUnavailable, node_route(), greeting_reply(), identity_reply(), _mirror_greeting(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator() (+4 more)

### Community 195 - "Path"
Cohesion: 0.40
Nodes (4): _env_files_for_token(), persist_rupeestop_auth_token(), _rewrite_env_token(), test_persist_sets_process_env()

### Community 197 - "QuestionBrief"
Cohesion: 0.06
Nodes (39): analyst_should_run(), asks_market_briefing(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), build_question_brief(), _detect_direction(), _detect_funds() (+31 more)

### Community 199 - "compare_ask_speed.py"
Cohesion: 0.53
Nodes (4): compare(), _load(), main(), _numbers()

### Community 203 - "fund_brief.py"
Cohesion: 0.11
Nodes (27): PortfolioScope, qdrant_filter_names(), _article_entities(), build_events(), cluster_articles(), _cluster_entities(), _day_key(), _exposure_for_holding() (+19 more)

### Community 206 - "contains_phrase"
Cohesion: 0.70
Nodes (3): _holding_mentioned(), matches_entity(), contains_phrase()

### Community 209 - "datetime"
Cohesion: 0.15
Nodes (16): _capability_cache_key(), _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows() (+8 more)

### Community 210 - "portfolio_news_impact.py"
Cohesion: 0.18
Nodes (11): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _tag_holding_news() (+3 more)

### Community 212 - "ToolCall"
Cohesion: 0.04
Nodes (70): reroute_single_fund_risk_plan(), finalize_unnamed_catalog_compare(), _split_count(), ToolCall, clarify_plan_if_fund_unknown(), _plan_uses_fund_scoped_tools(), enforce_user_authorized_funds_only(), apply_pure_concept_plan() (+62 more)

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1639 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `fund_rating_screen.py`, `fields.py`, `time`, `test_fund_drawdown.py`, `test_pick_shown_fund.py`, `append_investor_portfolio_overview_tables`, `update.py`, `fact_slots.py`, `category_plan.py`, `ensure_registry`, `fund_name_gate.py`, `task_exec.py`, `llm_client.py`, `book_news_map.py`, `investor_drawback.py`, `test_fund_rating_screen.py`, `investor_subject.py`, `contracts.py`, `re`, `gold_service.py`, `test_answer_precision.py`, `insight/portfolio_scope.py`, `slot_router.py`, `test_portfolio_intents.py`, `question_intent.py`, `test_fund_risk.py`, `graph.py`, `planner_policy.py`, `graph.py`, `test_holding_overlap.py`, `display_table_policy.py`, `datetime`, `fact_answer.py`, `portfolio_news_impact.py`, `ToolCall`, `test_portfolio_layer.py`, `test_portfolio_allocation.py`, `compare_evidence.py`, `evidence_pack.py`, `concept_asks.py`, `test_two_wave_pipeline.py`, `plan_enforce.py`, `test_fact_answer.py`, `test_macro_scope.py`, `test_news_only_answer.py`, `test_composer_table_summaries.py`, `test_metal_fund_rating.py`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Are the 49 inferred relationships involving `ExecutionPlan` (e.g. with `news_calls_for_book()` and `sector_book()`) actually correct?**
  _`ExecutionPlan` has 49 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.08281086729362591 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `llm_client.py` to `interpret.py`, `get_sector_fund_ranking_index`, `compute.py`, `tools.py`, `QueryLogger`, `news_reader.py`, `ensure_registry`, `executor.py`, `task_exec.py`, `fund_match.py`, `fund_search.py`, `investor_subject.py`, `affected_sectors.py`, `rupeestop_auth.py`, `get_settings`, `gold_service.py`, `insight/portfolio_scope.py`, `slot_router.py`, `typing`, `scoped_retrieve.py`, `node_route`, `validate_capability_args`, `insight/guardrails.py`, `QuestionBrief`, `embed.py`, `portfolio/cache.py`, `retrieve_scoped_news`, `graph.py`, `fund_brief.py`, `stock_fund_ranking.py`, `test_portfolio_layer.py`, `portfolio_news_impact.py`, `news_rag/config.py`, `test_rupeestop_auth.py`, `test_portfolio_layer.py`, `plan_system_prompt`, `portfolio/client.py`, `market_pulse.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ToolCall` (e.g. with `news_calls_for_book()` and `_apply_planner_request()`) actually correct?**
  _`ToolCall` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `NewsStore` be split into smaller, more focused modules?**
  _Cohesion score 0.04995004995004995 - nodes in this community are weakly interconnected._