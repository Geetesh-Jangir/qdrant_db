# Graph Report - db_design_with_qdrant_locally  (2026-11-12)

## Corpus Check
- 505 files · ~873,917 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 5529 nodes · 17701 edges · 217 communities (182 shown, 35 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 663 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d781a383`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- investor_drawback.py
- retrieve_scoped_news
- interpret.py
- test_portfolio_layer.py
- article_quality.py
- main.py
- affected_sectors.py
- grounding.py
- Settings
- test_fund_drawdown.py
- get_settings
- re
- compute.py
- plan.py
- tools.py
- fund_display.py
- fund_rating_screen.py
- QueryLogger
- news_reader.py
- ToolCall
- investor_subject.py
- ExecutionPlan
- failure_ledger.py
- tool_runners.py
- category_plan.py
- test_fund_display_tables.py
- ensure_registry
- resolve_fund_for_query
- fields.py
- fund_brief.py
- execute_capability
- executor.py
- task_exec.py
- llm_client.py
- update.py
- fund_search.py
- fund_context.py
- fund_type_name_spec
- test_fund_rating_screen.py
- env
- glossary.py
- lib/portfolio_scope.py
- QuestionBrief
- macro_news_cache.py
- env
- sources/google_news.py
- rupeestop_auth.py
- build_evidence_pack
- fund_name_policy.py
- app.py
- gold_service.py
- env
- nav_service.py
- fund_rupeestop_metrics.py
- AnswerMode
- test_portfolio_intents.py
- scrape-worker/package.json
- test_macro_scope.py
- render_data_only_template
- test_fund_risk.py
- RequestTelemetry
- normalize_rs_label
- re
- bullion_retrieve.py
- _strip_book_concentration_tables
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
- fund_risk.py
- test_rating_screen_uses_focus_question_not_full_compare_question
- test_portfolio_allocation.py
- normalize_answer_markdown
- get_sector_fund_ranking_index
- _return_slice_covers
- env
- memory/__init__.py
- steps
- evidence_pack.py
- test_conversation_memory.py
- test_fund_payload_first.py
- sector_query_for_label
- market_pulse.py
- pathlib
- metals_spot_tables.py
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- enforce_planner_catalog_plan
- ask_plan.py
- fund_rating_categories.py
- portfolio_news_impact.py
- test_portfolio_layer.py
- macro_news_enhanced.py
- strip_news_roundup
- news_digest.py
- .lookup_extracted_fund
- vitest
- format_inr
- strip_missing_data_caveats
- compilerOptions
- compilerOptions
- test_ask_query_log.py
- ._ensure_loaded
- backfill
- lib/google_news.py
- test_composer_table_summaries.py
- typing
- run-pipeline
- portfolio/client.py
- sector_alignment.py
- index_series.py
- worker/src/index.ts
- steps
- steps
- with
- test_conversation_memory.py
- test_screen_facts.py
- insights.py
- inputs
- with
- inputs
- json
- concept_asks.py
- GraphState
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
- entity_candidates.py
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_catalog.py
- diagnose_lightsail_site.sh
- compare_evidence.py
- test_metal_fund_rating.py
- EntityFunnel
- plan_system_prompt
- asks_computed_illustration
- build_derived_views
- planner_catalog_knowledge.py
- query_log.py
- test_call_json_llm.py
- insight/portfolio_scope.py
- test_investor_grounding.py
- get_stock_profile
- asks_fund_related_news
- plan_enforce.py
- PublisherStats
- article_dedupe_key
- strip_missing_data_caveats
- top_n_from_question
- test_smart_fund_why.py
- question_is_bullion_metal_price_question
- news_insight_articles
- data_pack.py
- query_plan.py
- relationships.py
- test_google_rss.py
- normalize_rating
- _public_summary
- market_scope_entities
- Any
- test_one_rated_fund_per_category_does_not_fill_with_gold
- prompts.py
- csv
- fetch_category_ratings
- contains_phrase
- _resolve_path

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 577 edges
2. `ToolCall` - 346 edges
3. `get_settings()` - 139 edges
4. `apply_planner_post_hooks()` - 121 edges
5. `AnswerMode` - 108 edges
6. `QueryLogger` - 100 edges
7. `node_compose()` - 92 edges
8. `QuestionBrief` - 88 edges
9. `slot_route()` - 84 edges
10. `Settings` - 83 edges

## Surprising Connections (you probably didn't know these)
- `test_parse_plan_drops_unknown_tools_and_clamps_values()` --calls--> `parse_plan()`  [EXTRACTED]
  tests/test_insight_graph.py → news_rag/insight/plan.py
- `test_current_value_and_nonzero_xirr()` --calls--> `normalize_workspace()`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/portfolio/normalize.py
- `test_active_crn_reaches_a_worker_thread()` --indirect_call--> `get_active_crn()`  [INFERRED]
  tests/test_portfolio_layer.py → news_rag/portfolio/cache.py
- `fetch_google_news()` --uses--> `GoogleBlockedError`  [INFERRED]
  news_pipeline/graph/nodes/fetch_google_news.py → lib/google_guard.py
- `TestGoogleNewsFetch` --uses--> `Settings`  [INFERRED]
  tests/test_google_news_fetch.py → news_pipeline/config.py

## Import Cycles
- None detected.

## Communities (217 total, 35 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (52): get_entity_funnel(), _bucket(), _entity_names(), fetch_window_fields(), summarize_errors(), write_error_summary(), build_graph(), _absorb_into_candidate() (+44 more)

### Community 1 - "investor_drawback.py"
Cohesion: 0.09
Nodes (31): attach_drawback_digest(), build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), _pretty_category(), render_portfolio_drawback_answer() (+23 more)

### Community 2 - "retrieve_scoped_news"
Cohesion: 0.24
Nodes (12): _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news(), _sector_entities() (+4 more)

### Community 3 - "interpret.py"
Cohesion: 0.07
Nodes (71): asks_market_briefing(), asks_random_fund_compare(), Findings, FundFinding, SectorFinding, EvidenceSet, mentions_publication_date(), _article_context_for_interpret() (+63 more)

### Community 4 - "test_portfolio_layer.py"
Cohesion: 0.12
Nodes (13): _run_get_investor_portfolio(), project_concentration(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore (+5 more)

### Community 5 - "article_quality.py"
Cohesion: 0.13
Nodes (18): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+10 more)

### Community 6 - "main.py"
Cohesion: 0.07
Nodes (17): _to_article(), EntityScore, StoredArticle, is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), merge_stored_article() (+9 more)

### Community 7 - "affected_sectors.py"
Cohesion: 0.24
Nodes (9): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+1 more)

### Community 8 - "grounding.py"
Cohesion: 0.08
Nodes (28): collect_evidence_calendar_dates(), add_article(), cores_in_text(), derived_cores(), finalize_text_fields(), format_user_calendar_date(), number_is_grounded(), numeric_core() (+20 more)

### Community 9 - "Settings"
Cohesion: 0.08
Nodes (34): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), Publisher, repo_root(), SectorQuery, article_in_fetch_window() (+26 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (55): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+47 more)

### Community 11 - "get_settings"
Cohesion: 0.09
Nodes (26): ask(), ask_stream(), AskRequest, _attach_llm_meta(), fund_brief(), health(), get_settings(), make_plan() (+18 more)

### Community 12 - "re"
Cohesion: 0.09
Nodes (19): question_needs_affected_sectors(), _looks_like_fund_list(), _metal_fund_categories(), _metal_fund_spec(), _question_names_amc_scheme(), asks_category_performance(), _list_question(), question_picks_one_shown_fund() (+11 more)

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (45): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+37 more)

### Community 14 - "plan.py"
Cohesion: 0.13
Nodes (19): explanation_brief(), canonicalize_field(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), _label_for_days(), parse_plan() (+11 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (53): get_fund_nav_history(), run_driver_affected_funds_adapter(), DataNeed, _active_sector_equity(), _as_date(), asks_equity_funds(), _broad_working_well_keys(), _drop_stale_nav() (+45 more)

### Community 16 - "fund_display.py"
Cohesion: 0.13
Nodes (26): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+18 more)

### Community 17 - "fund_rating_screen.py"
Cohesion: 0.08
Nodes (38): categories_for(), metal_scheme_categories(), _add_category_comparison(), _allocation_mix_spec(), _amc_matches(), _amc_outside_label(), _amc_token(), _apply_category_difference() (+30 more)

### Community 18 - "QueryLogger"
Cohesion: 0.12
Nodes (5): clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest()

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (37): measured_facts_block(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority(), _clean_claims() (+29 more)

### Community 20 - "ToolCall"
Cohesion: 0.04
Nodes (70): ensure_rating_screen(), _install_suggestion_screen(), _keep_followup_plan(), _ensure_pillar_rating_plan(), ensure_fund_holdings_followup_plan(), ScopeKind, ToolCall, _set_fund_call() (+62 more)

### Community 21 - "investor_subject.py"
Cohesion: 0.05
Nodes (66): _amc_token_set(), _categories_equivalent(), question_asks_portfolio_level_drawdown(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_deictic_and_memory_primary_fund(), enforce_investor_holding_subject() (+58 more)

### Community 22 - "ExecutionPlan"
Cohesion: 0.04
Nodes (67): _followup_modules(), ExecutionPlan, _portfolio_sections_from_plan(), _portfolio_top_n(), render_fund_concentration_answer(), asked_slots(), merge_planner_asked_facts(), slots_from_plan() (+59 more)

### Community 23 - "failure_ledger.py"
Cohesion: 0.07
Nodes (36): Settings, _merge_publisher_error_reasons(), write_day_report(), _atomic_write(), day_failure_slices_for_run(), ensure_loaded(), _failures_dir(), flush() (+28 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.10
Nodes (45): build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+37 more)

### Community 25 - "category_plan.py"
Cohesion: 0.07
Nodes (42): match_all_scheme_categories(), match_scheme_category(), _named_scheme_category(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), asks_cross_category_compare(), asks_fund_holdings_followup() (+34 more)

### Community 26 - "test_fund_display_tables.py"
Cohesion: 0.07
Nodes (32): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers() (+24 more)

### Community 27 - "ensure_registry"
Cohesion: 0.06
Nodes (53): _brief_system(), canonical_facet(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence() (+45 more)

### Community 28 - "resolve_fund_for_query"
Cohesion: 0.08
Nodes (30): collect_fund_phrase_candidates(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question(), extract_top_sectors(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _phrase_specificity_score() (+22 more)

### Community 29 - "fields.py"
Cohesion: 0.12
Nodes (19): _asks_book(), bind_fields_to_tools(), _book_fields(), field_prompt_table(), FieldNeed, fields_from_question(), _fund_fields(), _legacy_facts() (+11 more)

### Community 30 - "fund_brief.py"
Cohesion: 0.11
Nodes (28): _article_entities(), build_events(), cluster_articles(), _cluster_entities(), compose_fund_insight(), _day_key(), _empty_brief(), _exposure_for_holding() (+20 more)

### Community 31 - "execute_capability"
Cohesion: 0.14
Nodes (14): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), execute_wave(), test_crude_increase_compound_question_screens_negatively_affected_funds(), test_driver_exposure_screen_no_longer_needs_sector_picks_first(), test_fund_manager_query_uses_rupeestop_api(), test_random_five_positive_1y_funds_screen() (+6 more)

### Community 32 - "executor.py"
Cohesion: 0.08
Nodes (30): get_fund_index(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _conversation_turn(), _detail_for_fund_tool(), _fill_returns_from_catalog(), _filter_excluded_screen_rows() (+22 more)

### Community 33 - "task_exec.py"
Cohesion: 0.13
Nodes (27): bind_subjects(), _book_total_line(), _canon_fact(), _category_in_planner_text(), _cell(), coverage_line(), _fact_label(), _facts_from_plan() (+19 more)

### Community 34 - "llm_client.py"
Cohesion: 0.11
Nodes (28): Settings, anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts(), _call_anthropic(), _call_deepseek(), _call_gemini(), call_insight_llm() (+20 more)

### Community 35 - "update.py"
Cohesion: 0.14
Nodes (19): drop_old_turns(), compare_payload_matches_funds(), add_gist(), empty_frame(), empty_state(), expire_stale_entities(), push_fund(), stack_entry() (+11 more)

### Community 36 - "fund_search.py"
Cohesion: 0.11
Nodes (21): aggregate_sectors_from_holdings(), _attach_trailing_product(), build_holding_overlap(), _clean_company_name(), detail_has_live_facts(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers() (+13 more)

### Community 37 - "fund_context.py"
Cohesion: 0.06
Nodes (44): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), _needles_for_amc_hint(), _bound_fund_name(), _compare_sides_resolvable(), _amc_token_in_question(), ensure_deictic_fund_period_return_plan(), question_asks_fund_measured_return() (+36 more)

### Community 38 - "fund_type_name_spec"
Cohesion: 0.14
Nodes (11): _category_fund_name_spec(), fund_naming_clause(), _fund_type_in_name_clause(), fund_type_name_spec(), _label_in(), rating_screen_question(), _return_window(), _suggestion_spec() (+3 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.09
Nodes (45): asks_taxonomy(), match_all_fund_types(), parse_rating_screen(), _return_direction(), run_rating_list(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap() (+37 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "glossary.py"
Cohesion: 0.26
Nodes (10): asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), glossary_execution_plan(), meaning_reply(), _normalize_term(), test_fund_nav_not_glossary(), test_nav_full_form_direct_reply() (+2 more)

### Community 42 - "lib/portfolio_scope.py"
Cohesion: 0.14
Nodes (19): build_portfolio_scope(), _clean_holding_tokens(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc() (+11 more)

### Community 43 - "QuestionBrief"
Cohesion: 0.08
Nodes (32): analyst_should_run(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), build_question_brief(), _detect_direction(), _heuristic_brief(), _log_brief() (+24 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.12
Nodes (21): _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), select_macro_for_question() (+13 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "sources/google_news.py"
Cohesion: 0.11
Nodes (21): finish_run_logger(), fetch_entity_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url(), fetch_macro_items(), is_macro_match(), macro_fetch_entities() (+13 more)

### Community 47 - "rupeestop_auth.py"
Cohesion: 0.07
Nodes (24): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+16 more)

### Community 48 - "build_evidence_pack"
Cohesion: 0.08
Nodes (27): EvidenceRow, build_evidence_pack(), _fund_performance_digest(), _row_bits(), table_source(), has_second_part(), _wants_end_summary(), asks_one_figure() (+19 more)

### Community 49 - "fund_name_policy.py"
Cohesion: 0.15
Nodes (15): enforce_user_authorized_funds_only(), fund_authorized_for_question(), _named_in_chat_turns(), plan_allows_server_fund_pick(), normalize_fund_pick_from_planner(), plan_wants_alternate_in_category(), plan_wants_better_rated_in_category(), test_compare_both_still_rebinds_after_strip() (+7 more)

### Community 50 - "app.py"
Cohesion: 0.09
Nodes (35): ask_memory(), ask_query_log(), ask_sources(), _attach_portfolio_to_ask(), backfill_page(), backfill_start(), backfill_status(), backfill_stop() (+27 more)

### Community 51 - "gold_service.py"
Cohesion: 0.15
Nodes (16): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+8 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "nav_service.py"
Cohesion: 0.15
Nodes (12): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), monthly_returns_from_records(), _read_cache() (+4 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.11
Nodes (22): build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns(), normalize_vs_benchmark_payload() (+14 more)

### Community 55 - "AnswerMode"
Cohesion: 0.06
Nodes (45): rating_list_plan(), rating_concept_plan(), asks_fund_category_average(), AnswerMode, QueryClass, Wave2Policy, normalize_portfolio_plan_from_question(), plan_matches_intent() (+37 more)

### Community 56 - "test_portfolio_intents.py"
Cohesion: 0.09
Nodes (27): _as_of(), render_portfolio_fact(), _table(), _leave_tools_alone(), _set_investor_call(), wants_comparison_table(), _drop_scheme_is_the_whole_book(), GraphUnavailable (+19 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "test_macro_scope.py"
Cohesion: 0.15
Nodes (12): question_is_standalone_macro(), ensure_catalog_tools_for_fund_news(), reconcile_planner_invented_fund_name(), apply_standalone_macro_scope(), _macro_news_topics(), test_fund_news_adds_catalog_tools(), test_how_its_affecting_rupee_is_not_deictic_fund_title(), test_macro_scope_injects_news_when_planner_sent_no_tools() (+4 more)

### Community 59 - "render_data_only_template"
Cohesion: 0.05
Nodes (33): ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), EvidencePack, _holding_label(), _holding_weight_pct() (+25 more)

### Community 60 - "test_fund_risk.py"
Cohesion: 0.12
Nodes (25): asks_pillar_mark(), asks_pillar_structure(), asks_rating_concept(), asks_risk_trend_comparison(), ensure_risk_tools(), pillar_focus(), rating_lead(), strip_private_leaks() (+17 more)

### Community 61 - "RequestTelemetry"
Cohesion: 0.12
Nodes (20): refetch_partial_fund_tools(), PhaseRecord, RequestTelemetry, ToolRecord, _answer_stream_chunks(), Node, node_evidence_gate(), stream_graph_pipeline() (+12 more)

### Community 62 - "normalize_rs_label"
Cohesion: 0.12
Nodes (23): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), asks_rating_list() (+15 more)

### Community 63 - "re"
Cohesion: 0.09
Nodes (26): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+18 more)

### Community 64 - "bullion_retrieve.py"
Cohesion: 0.09
Nodes (18): _warmup_embeddings_background(), _run(), _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), embed_query() (+10 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "datetime"
Cohesion: 0.16
Nodes (11): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_vs_benchmark_module_is_not_replaced_by_snapshot(), test_market_snapshot_accepts_gold_windows() (+3 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.14
Nodes (15): asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), memory_shows_investor_book(), mentions_advice(), _tokens() (+7 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "embed.py"
Cohesion: 0.14
Nodes (9): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), embeddings_ready() (+1 more)

### Community 71 - "portfolio/cache.py"
Cohesion: 0.18
Nodes (14): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), get_normalized_portfolio(), peek_derived(), preload_configured_portfolio(), _run() (+6 more)

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
Nodes (13): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), _catalog_candidates(), test_agent_answer_elss_question() (+5 more)

### Community 77 - "universe.py"
Cohesion: 0.16
Nodes (17): resolve_allisin_holdings_path(), load_portfolio_universe(), _aliases_for(), build_holding_entities(), canonical_key(), _display_name(), _holding_query(), _industry_search_hint() (+9 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.20
Nodes (14): extract_top_holdings(), _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file() (+6 more)

### Community 79 - "datetime"
Cohesion: 0.15
Nodes (17): _capability_cache_key(), _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows() (+9 more)

### Community 80 - "resolve_display_table_policy"
Cohesion: 0.08
Nodes (26): DisplayTablePolicy, fact_values_already_stated(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark(), question_wants_concentration_tables() (+18 more)

### Community 81 - "normalize.py"
Cohesion: 0.26
Nodes (14): aggregate_term_gains(), _allocation_block(), _apply_holding_values(), _drop_sold(), _first(), _holding_from_scheme(), normalize_workspace(), _num() (+6 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.15
Nodes (27): pending_rating_line(), _age(), _allocation_bucket_rows(), _book_line(), _comparison_rows(), _composition_line(), _float_or_none(), _fund_line() (+19 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "sector_fund_ranking.py"
Cohesion: 0.09
Nodes (17): candidate_sector_names(), classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), rank_funds_by_sector_exposure() (+9 more)

### Community 86 - "fund_risk.py"
Cohesion: 0.12
Nodes (13): asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_private_system(), asks_score_only(), asks_sebi_riskometer(), blocked_reply(), _ensure_risk_trend_plan() (+5 more)

### Community 87 - "test_rating_screen_uses_focus_question_not_full_compare_question"
Cohesion: 0.28
Nodes (6): test_finalize_screen_adds_returns_for_compare_question(), fake_detail(), get_fund_detail(), test_rating_screen_uses_focus_question_not_full_compare_question(), test_rating_screen_uses_forced_category_spec(), fake_fetch()

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.17
Nodes (16): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+8 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.22
Nodes (9): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), strip_context_disclaimer(), _clean_answer(), test_pads_short_row() (+1 more)

### Community 90 - "get_sector_fund_ranking_index"
Cohesion: 0.10
Nodes (28): get_sector_fund_ranking_index(), primary_sector_for_question(), asks_funds_holding_stock(), asks_funds_with_sector_exposure(), _clean_stock_capture(), return_window_days(), screen_hints_from_question(), stock_name_from_question() (+20 more)

### Community 91 - "_return_slice_covers"
Cohesion: 0.08
Nodes (20): CapabilityCache, _Entry, get_capability_cache(), _one_fund(), _positive_ms(), _return_slice_covers(), _trim_cached_to_ask(), slice_slot() (+12 more)

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
Cohesion: 0.05
Nodes (60): fetch_public_rating(), render_pillar_marks_table(), _add_category_comparison(), append_investor_portfolio_overview_tables(), _attach_rs_ratings_to_screen(), _one(), _benchmark_lines_from_pack(), _category_rows_from_investor() (+52 more)

### Community 96 - "test_conversation_memory.py"
Cohesion: 0.12
Nodes (26): _conversation_id(), _keep_conversation_slice(), _take_conversation_slice(), widen_portfolio_args(), beside_keys(), clear_conversation(), note_cache(), recall_slice() (+18 more)

### Community 97 - "test_fund_payload_first.py"
Cohesion: 0.18
Nodes (12): exposure_from_detail(), headline_rating(), load_fund_risk(), rating_api_data_is_null(), rating_for_request(), rating_needs_pillars(), _weights(), test_default_windows_are_one_three_and_five_years() (+4 more)

### Community 98 - "sector_query_for_label"
Cohesion: 0.15
Nodes (4): normalize_sector_label(), sector_query_for_label(), _sector_label_in_text(), SectorFundRankingIndex

### Community 99 - "market_pulse.py"
Cohesion: 0.15
Nodes (17): cluster_articles_by_theme(), _cluster_label(), clustered_macro_data_from_bundle(), _collect_pulse_pool(), _collect_pulse_pool_batched(), _fetch_one_macro_query(), MacroThemeCluster, market_pulse_representatives_from_clusters() (+9 more)

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
Cohesion: 0.18
Nodes (12): _rating_lead_for_pack(), asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score() (+4 more)

### Community 106 - "enforce_planner_catalog_plan"
Cohesion: 0.06
Nodes (48): _resolve_funds(), isin_for_owned_holding(), merge_fund_isins_map(), owned_holding_names(), owned_holding_rows(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings() (+40 more)

### Community 107 - "ask_plan.py"
Cohesion: 0.24
Nodes (9): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), test_ask_plan_keeps_rich_agent_fields(), test_cluster_prefers_larger_groups() (+1 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.21
Nodes (7): CategoryMatch, fund_type_for_category(), _names_a_type(), _phrase_in(), rating_scope_pairs(), _spaced_category_words(), taxonomy_reply()

### Community 109 - "portfolio_news_impact.py"
Cohesion: 0.09
Nodes (26): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _rule_sector_picks() (+18 more)

### Community 110 - "test_portfolio_layer.py"
Cohesion: 0.14
Nodes (16): peek_portfolio(), set_active_crn(), InvalidCRN, normalized_doc(), test_active_crn_reaches_a_worker_thread(), test_concentration_question_loads_stock_and_sector_data(), test_current_value_and_nonzero_xirr(), test_enforce_portfolio_scope_strips_tool() (+8 more)

### Community 111 - "macro_news_enhanced.py"
Cohesion: 0.18
Nodes (10): _fetch_macro_query(), _query_variants(), run_macro_news_enhanced(), _collect(), infer_window_days_from_question(), parse_date_field(), parse_time_window(), split_multi_questions() (+2 more)

### Community 112 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 114 - ".lookup_extracted_fund"
Cohesion: 0.13
Nodes (13): _clean_fund_phrase(), add(), _compose_amc_scheme_phrase(), _entry_matches_amc(), _entry_matches_query_scheme(), _expand_query_token(), _extend_amc_phrase_tail(), _hint_matches_amc_entry() (+5 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 117 - "strip_missing_data_caveats"
Cohesion: 0.25
Nodes (9): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings() (+1 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "test_ask_query_log.py"
Cohesion: 0.19
Nodes (9): ParsedQuery, attach_query_log_meta(), find_query_log_file(), query_log_page_href(), read_query_log(), test_attach_query_log_meta_adds_page_link(), test_finish_writes_json_sidecar(), test_log_parsed_includes_intent_and_fund() (+1 more)

### Community 121 - "._ensure_loaded"
Cohesion: 0.16
Nodes (4): FundIndex, _infer_category_and_type(), resolve_canonical_isin(), _sync_amc_prefix_from_catalog()

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "lib/google_news.py"
Cohesion: 0.04
Nodes (42): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+34 more)

### Community 124 - "test_composer_table_summaries.py"
Cohesion: 0.19
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections()

### Community 125 - "typing"
Cohesion: 0.09
Nodes (14): embed_query(), _body(), grouped_news(), NewsTarget, search_targets(), trim_news_grouped(), build_filter(), describe_filters_for_log() (+6 more)

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "portfolio/client.py"
Cohesion: 0.17
Nodes (11): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), PortfolioError, PortfolioNotConfigured, PortfolioUnavailable, PortfolioUpstreamError (+3 more)

### Community 128 - "sector_alignment.py"
Cohesion: 0.10
Nodes (23): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), clear_macro_impact_cache(), analyze_sector_block(), canonical_sector_for_holding() (+15 more)

### Community 129 - "index_series.py"
Cohesion: 0.10
Nodes (26): nifty50_ticker(), normalize_sector_row(), _price_holdings(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns(), _read_cache() (+18 more)

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
Cohesion: 0.18
Nodes (15): _store_turn_memory(), drain_cache_events(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), append_chat_turn(), _fresh(), get_memory(), get_or_create() (+7 more)

### Community 135 - "test_screen_facts.py"
Cohesion: 0.20
Nodes (9): screen_fact_names(), test_any_fund_screen_keeps_requested_aum(), _detail(), test_incomplete_return_column_is_omitted(), test_screen_can_ask_for_several_facts(), test_screen_manager_name_and_experience_are_separate_facts(), test_screen_table_includes_aum(), test_screen_table_includes_manager_name_and_experience() (+1 more)

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
Nodes (48): ScrapeArticleError, _json_default(), safe_json_dumps(), _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers() (+40 more)

### Community 141 - "concept_asks.py"
Cohesion: 0.31
Nodes (10): apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), asks_fof_funds(), test_concept_example_plan_screen_fof(), test_fof_name_one_detected() (+2 more)

### Community 142 - "GraphState"
Cohesion: 0.11
Nodes (24): _attach_conversation(), build_result(), _catalog_fanout_fund_names(), _conversation_id(), _ensure_portfolio_for_fund_news(), GraphState, _insight_headline_narrative(), _load_planner_memory() (+16 more)

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

### Community 159 - "entity_candidates.py"
Cohesion: 0.26
Nodes (7): candidates_block(), entity_candidates(), _holding_candidates(), _sector_candidates(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

### Community 163 - "fund_match.py"
Cohesion: 0.13
Nodes (11): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+3 more)

### Community 170 - "fund_catalog.py"
Cohesion: 0.17
Nodes (17): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+9 more)

### Community 174 - "compare_evidence.py"
Cohesion: 0.27
Nodes (7): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 178 - "test_metal_fund_rating.py"
Cohesion: 0.29
Nodes (7): ensure_quality_fund_list(), _payload(), _rating(), test_gold_list_spreads_etf_and_fund_of_funds(), fetch(), test_named_gold_etf_is_not_a_category_list(), test_planner_gold_sector_screen_becomes_rating_list()

### Community 180 - "plan_system_prompt"
Cohesion: 0.23
Nodes (8): plan_system_prompt(), build_anthropic_messages_body(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), _body(), test_planner_and_composer_share_the_first_system_block(), test_tools_stay_available_when_there_is_no_shared_prefix()

### Community 181 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

### Community 182 - "build_derived_views"
Cohesion: 0.18
Nodes (15): clear_cache_for_tests(), seed_portfolio_cache_for_tests(), asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct() (+7 more)

### Community 183 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 184 - "query_log.py"
Cohesion: 0.10
Nodes (15): _events(), run_ask_engine(), stream_ask_engine(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), run_graph_pipeline() (+7 more)

### Community 185 - "test_call_json_llm.py"
Cohesion: 0.19
Nodes (16): call_json_llm(), _model_for(), _json_balance(), salvage_truncated_json(), _loads_closed(), _layered_news_topics(), _client(), _gemini_response() (+8 more)

### Community 186 - "insight/portfolio_scope.py"
Cohesion: 0.21
Nodes (15): plan_targets_single_fund_measured_return(), question_asks_holding_metric_and_glossary(), _data_need_is_investor(), enforce_portfolio_scope(), ensure_investor_portfolio_tool(), _has_investor_tool(), _investor_tool_args(), investor_uses_holdings_table() (+7 more)

### Community 187 - "test_investor_grounding.py"
Cohesion: 0.26
Nodes (9): strip_grounding_holes(), cores_for_float(), investor_book_cores(), _sample_book(), test_grounding_keeps_category_weight_in_prose(), test_investor_book_cores_includes_pnl_term_gains(), test_investor_book_cores_includes_rounded_allocation_pct(), test_repair_fills_hollow_allocation_and_holding_bullets() (+1 more)

### Community 188 - "get_stock_profile"
Cohesion: 0.26
Nodes (4): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker()

### Community 190 - "asks_fund_related_news"
Cohesion: 0.26
Nodes (7): infer_fund_news_layers(), asks_fund_related_news(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only(), test_overview_news_is_holdings_and_sectors()

### Community 191 - "plan_enforce.py"
Cohesion: 0.06
Nodes (40): asks_balanced_long_horizon_fund_menu(), asks_ideal_portfolio_shape(), balanced_portfolio_examples_spec(), category_composition_plan_applies(), question_signals_investor_book(), question_asks_current_book_allocation(), asks_these_equity_funds(), compare_side_in_chat() (+32 more)

### Community 193 - "article_dedupe_key"
Cohesion: 0.50
Nodes (5): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), test_collect_bundle_articles_from_tool_results()

### Community 194 - "strip_missing_data_caveats"
Cohesion: 0.22
Nodes (7): strip_missing_data_caveats(), test_a_rating_pick_does_not_apologise_for_returns_or_pillars(), test_strip_removes_risk_trend_apology(), test_a_top_five_apology_is_removed(), test_each_holding_keeps_the_article_text_not_only_one_headline(), test_overview_fund_facts_are_a_short_table(), test_a_gap_apology_is_removed_and_a_real_point_stays()

### Community 195 - "top_n_from_question"
Cohesion: 0.36
Nodes (5): top_n_from_question(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

### Community 197 - "test_smart_fund_why.py"
Cohesion: 0.24
Nodes (5): _detect_funds(), _infer_window_days(), test_composer_guardrails(), test_fuzzy_fund_why_detection(), test_streaming_sse_order()

### Community 198 - "question_is_bullion_metal_price_question"
Cohesion: 0.33
Nodes (6): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), test_bullion_plan_clears_memory_gold_etf(), test_bullion_vs_gold_etf_detection()

### Community 199 - "news_insight_articles"
Cohesion: 0.16
Nodes (11): _news_subject(), _run_get_macro_news(), clean_news_insight(), complete_sentences(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words() (+3 more)

### Community 200 - "data_pack.py"
Cohesion: 0.32
Nodes (4): build_data_pack(), build(), _compact(), test_data_pack_groups_by_fund_and_hides_internal_fields()

### Community 204 - "relationships.py"
Cohesion: 0.42
Nodes (5): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships()

### Community 206 - "normalize_rating"
Cohesion: 0.25
Nodes (5): normalize_rating(), _pillar_maximum(), _public_pillars(), test_api_label_is_kept_as_sent(), test_debt_pillar_max_uses_api_max_score_field()

### Community 207 - "_public_summary"
Cohesion: 0.32
Nodes (7): render_risk_lines(), _public_summary(), test_mixed_question_adds_risk_lines_to_the_note(), test_public_summary_keeps_pillar_marks_and_drops_inputs(), test_risk_answer_keeps_exposure_and_drops_sharpe(), test_score_question_names_the_pillars_without_their_numbers(), test_why_good_choice_uses_the_api_label_and_explains_the_ranges()

### Community 208 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

### Community 210 - "test_one_rated_fund_per_category_does_not_fill_with_gold"
Cohesion: 1.00
Nodes (3): test_one_rated_fund_per_category_does_not_fill_with_gold(), fetch(), _row()

### Community 212 - "prompts.py"
Cohesion: 0.25
Nodes (5): build_brief_prompt(), build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 215 - "contains_phrase"
Cohesion: 0.70
Nodes (3): _holding_mentioned(), matches_entity(), contains_phrase()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1602 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `investor_drawback.py`, `test_conversation_memory.py`, `test_screen_facts.py`, `test_fund_drawdown.py`, `get_settings`, `json`, `concept_asks.py`, `GraphState`, `plan.py`, `fund_rating_screen.py`, `ToolCall`, `investor_subject.py`, `category_plan.py`, `ensure_registry`, `fields.py`, `task_exec.py`, `fund_context.py`, `test_fund_rating_screen.py`, `glossary.py`, `compare_evidence.py`, `build_evidence_pack`, `fund_name_policy.py`, `app.py`, `test_metal_fund_rating.py`, `build_derived_views`, `AnswerMode`, `test_portfolio_intents.py`, `test_macro_scope.py`, `render_data_only_template`, `test_fund_risk.py`, `RequestTelemetry`, `insight/portfolio_scope.py`, `plan_enforce.py`, `question_is_bullion_metal_price_question`, `news_insight_articles`, `test_fact_answer.py`, `datetime`, `resolve_display_table_policy`, `Any`, `fact_answer.py`, `fund_risk.py`, `test_portfolio_allocation.py`, `evidence_pack.py`, `test_conversation_memory.py`, `enforce_planner_catalog_plan`, `portfolio_news_impact.py`, `test_portfolio_layer.py`, `test_composer_table_summaries.py`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Are the 62 inferred relationships involving `ExecutionPlan` (e.g. with `apply_concept_example_to_plan()` and `append_investor_portfolio_overview_tables()`) actually correct?**
  _`ExecutionPlan` has 62 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.06948410432134018 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ToolCall` to `investor_drawback.py`, `test_conversation_memory.py`, `test_screen_facts.py`, `test_fund_drawdown.py`, `concept_asks.py`, `GraphState`, `plan.py`, `fund_rating_screen.py`, `investor_subject.py`, `ExecutionPlan`, `category_plan.py`, `ensure_registry`, `fields.py`, `execute_capability`, `executor.py`, `task_exec.py`, `update.py`, `fund_context.py`, `test_fund_rating_screen.py`, `compare_evidence.py`, `build_evidence_pack`, `fund_name_policy.py`, `test_metal_fund_rating.py`, `app.py`, `build_derived_views`, `AnswerMode`, `test_portfolio_intents.py`, `test_macro_scope.py`, `render_data_only_template`, `test_fund_risk.py`, `RequestTelemetry`, `insight/portfolio_scope.py`, `plan_enforce.py`, `question_is_bullion_metal_price_question`, `news_insight_articles`, `datetime`, `resolve_display_table_policy`, `Any`, `fund_risk.py`, `test_portfolio_allocation.py`, `_return_slice_covers`, `evidence_pack.py`, `test_conversation_memory.py`, `enforce_planner_catalog_plan`, `portfolio_news_impact.py`, `test_portfolio_layer.py`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ToolCall` (e.g. with `execute_capability()` and `execute_wave()`) actually correct?**
  _`ToolCall` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `investor_drawback.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09019607843137255 - nodes in this community are weakly interconnected._