# Graph Report - db_design_with_qdrant_locally  (2026-11-04)

## Corpus Check
- 457 files · ~821,930 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 4747 nodes · 15054 edges · 177 communities (147 shown, 30 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 788 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8587ec86`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- AnswerMode
- fetch.py
- interpret.py
- multi_fact.py
- ToolCall
- news_pipeline/config.py
- portfolio/cache.py
- Settings
- news_dates.py
- test_fund_drawdown.py
- gather.py
- qdrant_reader.py
- compute.py
- QuestionBrief
- tools.py
- fund_context.py
- sector_exposure_tables.py
- QueryLogger
- re
- output_judge.py
- ExecutionPlan
- grounding.py
- screen_hints_from_question
- tool_runners.py
- Any
- sector_fund_ranking.py
- test_conversation_memory.py
- macro_news_enhanced.py
- fields.py
- fund_brief.py
- graph.py
- apply_planner_post_hooks
- ensure_catalog_tools_for_fund_news
- CapabilityCache
- market_pulse.py
- layer_tools.py
- investor_subject.py
- fund_rating_screen.py
- test_fund_rating_screen.py
- env
- executor.py
- fund_display.py
- sources/google_news.py
- macro_news_cache.py
- env
- json
- retrieve_scoped_news
- httpx
- build_fund_display_tables
- plan.py
- update.py
- env
- app.py
- fund_rupeestop_metrics.py
- call_json_llm
- graph.py
- scrape-worker/package.json
- nav_service.py
- run_ask_engine
- embed.py
- normalize_rs_label
- embed_query
- domain_intake.py
- resolve_fund_for_query
- gold_service.py
- batch.ts
- parse.py
- test_guardrails_domain.py
- http-fetch.ts
- pack_sanitize.py
- fund_rating_categories.py
- holdings_market.py
- llm_client.py
- with
- FundUniverseAgent
- fund_match.py
- portfolio_news_impact.py
- test_fund_risk.py
- stock_fund_ranking.py
- validate_capability_args
- eval_basic_queries.py
- holding_attribution.py
- scrape-worker/src/index.ts
- portfolio_news_impact.py
- aggregate_fund_holdings.py
- macro_impact_map.py
- sector_alignment.py
- typing
- enrich_manager_payload
- env
- lib/portfolio_scope.py
- steps
- evidence_pack.py
- nse_sector_indices.py
- v2_scoring.py
- fund_search.py
- extract_top_holdings
- plan_intent.py
- PublisherStats
- question_mentions_fund_scheme
- run-daily-pipeline.sh
- env
- ToolCall
- strip_news_roundup
- news_digest.py
- test_call_json_llm.py
- news_insight_articles
- test_insight_graph.py
- metals_spot_tables.py
- resolve_display_table_policy
- data_pack.py
- plan_catalog_bind.py
- vitest
- test_composer_table_summaries.py
- test_greeting.py
- compilerOptions
- compilerOptions
- EntityFunnel
- test_prompt_cache_prefix.py
- backfill
- RunLogger
- collections
- fact_slots.py
- run-pipeline
- fund_catalog.py
- contains_phrase
- infer_fund_news_layers
- worker/src/index.ts
- steps
- steps
- with
- _category_fund_name_spec
- prompts.py
- compare_ask_speed.py
- inputs
- with
- inputs
- asks_computed_illustration
- _resolve_path
- measured_facts_block
- run-backfill.sh
- qdrant
- json_util.py
- _unhandled_exception_handler
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
- _apply_category_difference
- rag-api.js
- _amc_outside_label
- install.sh
- nearest_return_window
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- plan_to_brief
- _return_direction
- diagnose_lightsail_site.sh
- _strip_overview_prose_block
- test_pick_compare_pair_walks_tiers

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 418 edges
2. `ToolCall` - 262 edges
3. `AnswerMode` - 146 edges
4. `get_settings()` - 127 edges
5. `QueryLogger` - 100 edges
6. `QuestionBrief` - 88 edges
7. `slot_route()` - 84 edges
8. `Settings` - 83 edges
9. `apply_planner_post_hooks()` - 81 edges
10. `node_compose()` - 71 edges

## Surprising Connections (you probably didn't know these)
- `test_is_it_a_bad_fund_is_not_deictic_fund_pronoun()` --calls--> `question_refers_deictic_fund()`  [EXTRACTED]
  tests/test_investor_subject.py → news_rag/insight/investor_subject.py
- `test_user_explicitly_named_scheme_requires_amc_or_two_tokens()` --calls--> `user_explicitly_named_scheme()`  [EXTRACTED]
  tests/test_investor_subject.py → news_rag/insight/investor_subject.py
- `_offline_plan()` --uses--> `AnswerMode`  [INFERRED]
  scripts/eval_basic_queries.py → news_rag/insight/contracts.py
- `test_holdings_breakdown_keeps_planner_news()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_category_plan.py → news_rag/insight/contracts.py
- `test_benchmark_performance_data_only_uses_vs_table()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_display_table_policy.py → news_rag/insight/contracts.py

## Import Cycles
- None detected.

## Communities (177 total, 30 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (50): get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate() (+42 more)

### Community 1 - "AnswerMode"
Cohesion: 0.04
Nodes (77): rating_list_plan(), rating_concept_plan(), asks_fund_category_average(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), apply_concept_example_to_plan(), asks_concept_with_catalog_example() (+69 more)

### Community 2 - "fetch.py"
Cohesion: 0.04
Nodes (40): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+32 more)

### Community 3 - "interpret.py"
Cohesion: 0.06
Nodes (70): QuestionBrief, _success_criteria(), Findings, FundFinding, SectorFinding, mentions_publication_date(), publication_date_keys(), strip_media_attribution() (+62 more)

### Community 4 - "multi_fact.py"
Cohesion: 0.08
Nodes (22): _followup_modules(), has_second_part(), ensure_compare_template(), ensure_screen_facts(), screen_fact_names(), planner_owns(), top_n_from_question(), test_highest_rating_plus_returns_and_risk_keeps_the_fund_lookup() (+14 more)

### Community 5 - "ToolCall"
Cohesion: 0.10
Nodes (26): match_scheme_category(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), _categories_equivalent(), _category_for_alternate_plan(), _category_from_memory_cursor(), ensure_alternate_category_fund_plan() (+18 more)

### Community 6 - "news_pipeline/config.py"
Cohesion: 0.08
Nodes (12): is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), _datetime_range(), NewsStore, point_id_for_url(), inspect_qdrant() (+4 more)

### Community 7 - "portfolio/cache.py"
Cohesion: 0.05
Nodes (39): _BreakerState, _CacheEntry, crn_log_id(), get_normalized_portfolio(), fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url() (+31 more)

### Community 8 - "Settings"
Cohesion: 0.06
Nodes (42): Settings, _merge_publisher_error_reasons(), write_day_report(), _bucket(), _entity_names(), summarize_errors(), write_error_summary(), _atomic_write() (+34 more)

### Community 9 - "news_dates.py"
Cohesion: 0.07
Nodes (34): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), Publisher, repo_root(), SectorQuery, article_in_fetch_window() (+26 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (57): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+49 more)

### Community 11 - "gather.py"
Cohesion: 0.07
Nodes (49): _brief_system(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext (+41 more)

### Community 12 - "qdrant_reader.py"
Cohesion: 0.10
Nodes (6): corpus_entity_names(), _normalize_key(), describe_filters_for_log(), filter_spec(), _point_row(), QdrantReader

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (48): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+40 more)

### Community 14 - "QuestionBrief"
Cohesion: 0.06
Nodes (42): _looks_like_fund_list(), analyst_should_run(), asks_market_briefing(), asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), build_question_brief() (+34 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (53): extract_top_holdings(), extract_top_sectors(), fetch_fund_managers_for_isin(), DataNeed, get_sector_fund_ranking_index(), rank_funds_by_sector_exposure(), _active_sector_equity(), _articles_for_affected_question() (+45 more)

### Community 16 - "fund_context.py"
Cohesion: 0.12
Nodes (24): _resolve_funds(), comparison_fund_names(), _filter(), _frame_subjects(), fund_name_matches_category(), fund_name_mentioned_in_memory(), isin_for_owned_holding(), last_fund_name_from_gists() (+16 more)

### Community 17 - "sector_exposure_tables.py"
Cohesion: 0.30
Nodes (11): _all_holdings_metric_spec(), _fund_data_from_results(), _metric_cell(), render_all_holdings_metric_table(), render_all_holdings_return_table(), render_all_holdings_sector_table(), _sector_needle(), _sector_weight_pct() (+3 more)

### Community 18 - "QueryLogger"
Cohesion: 0.09
Nodes (9): slots_from_plan(), ParsedQuery, clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest(), test_finish_writes_json_sidecar() (+1 more)

### Community 19 - "re"
Cohesion: 0.05
Nodes (61): get_settings(), _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score() (+53 more)

### Community 20 - "output_judge.py"
Cohesion: 0.13
Nodes (11): contract_model(), _json_balance(), parse_json_from_text(), _plain_answer_from_reasoning(), salvage_truncated_json(), _loads_closed(), judge_answer(), JudgeResult (+3 more)

### Community 21 - "ExecutionPlan"
Cohesion: 0.05
Nodes (75): ExecutionPlan, _leave_tools_alone(), attach_drawback_digest(), build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_fund_concentration(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration() (+67 more)

### Community 22 - "grounding.py"
Cohesion: 0.10
Nodes (30): strip_grounding_holes(), cores_for_float(), cores_in_text(), derived_cores(), finalize_text_fields(), fund_portfolio_cores(), investor_book_cores(), number_is_grounded() (+22 more)

### Community 23 - "screen_hints_from_question"
Cohesion: 0.07
Nodes (36): question_needs_affected_sectors(), execute_wave(), _args_from_question(), asks_funds_holding_stock(), asks_funds_with_sector_exposure(), _clean_stock_capture(), _exposure_ask(), _heavy_and_return() (+28 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.11
Nodes (44): headline_rating(), build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has() (+36 more)

### Community 25 - "Any"
Cohesion: 0.09
Nodes (15): _clean_company_name(), _fund_text(), FundIndex, get_fund_benchmark(), _infer_category_and_type(), _named_weights(), _normalize_manager_record(), _optional_number() (+7 more)

### Community 26 - "sector_fund_ranking.py"
Cohesion: 0.06
Nodes (20): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors() (+12 more)

### Community 27 - "test_conversation_memory.py"
Cohesion: 0.10
Nodes (31): _store_turn_memory(), clear_conversation(), drain_cache_events(), note_cache(), recall_slice(), recall_wider_portfolio(), remember_slice(), slice_key() (+23 more)

### Community 28 - "macro_news_enhanced.py"
Cohesion: 0.18
Nodes (11): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), _one(), _fetch_macro_query(), _query_variants(), run_macro_news_enhanced() (+3 more)

### Community 29 - "fields.py"
Cohesion: 0.08
Nodes (46): periods_requested_in_question(), _age(), _book_line(), _comparison_rows(), _composition_line(), _fund_line(), _fund_name(), _identity() (+38 more)

### Community 30 - "fund_brief.py"
Cohesion: 0.10
Nodes (31): PortfolioScope, qdrant_filter_names(), _article_entities(), build_events(), cluster_articles(), _cluster_entities(), compose_fund_insight(), _day_key() (+23 more)

### Community 31 - "graph.py"
Cohesion: 0.16
Nodes (14): RequestTelemetry, _answer_stream_chunks(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed(), event_phase_started(), event_quality_check() (+6 more)

### Community 32 - "apply_planner_post_hooks"
Cohesion: 0.09
Nodes (28): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), merge_planner_asked_facts(), tag_answer_parts(), enforce_deictic_and_memory_primary_fund(), question_refers_deictic_fund(), reconcile_deictic_planner_fund(), resolve_deictic_fund_name() (+20 more)

### Community 34 - "CapabilityCache"
Cohesion: 0.19
Nodes (5): CapabilityCache, _Entry, test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner()

### Community 35 - "market_pulse.py"
Cohesion: 0.16
Nodes (16): cluster_articles_by_theme(), _cluster_label(), clustered_macro_data_from_bundle(), _collect_pulse_pool(), _collect_pulse_pool_batched(), _fetch_one_macro_query(), MacroThemeCluster, market_pulse_representatives_from_clusters() (+8 more)

### Community 36 - "layer_tools.py"
Cohesion: 0.11
Nodes (26): nifty50_ticker(), aggregate_sectors_from_holdings(), normalize_sector_row(), _price_holdings(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns() (+18 more)

### Community 37 - "investor_subject.py"
Cohesion: 0.10
Nodes (33): apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan(), ensure_deictic_fund_period_return_plan(), ensure_my_category_fund_investor_plan(), ensure_my_holding_fund_scope(), holdings_rows_from_investor_tool_results() (+25 more)

### Community 38 - "fund_rating_screen.py"
Cohesion: 0.15
Nodes (26): categories_for(), _add_category_comparison(), _amc_matches(), _best_label(), _cascade_labels_for_spec(), _catalog_name(), _execute_rating_list(), _higher_pillars() (+18 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.12
Nodes (37): asks_taxonomy(), ensure_rating_screen(), parse_rating_screen(), run_rating_list(), _payload(), _rating(), test_a_good_fund_request_uses_best_in_category_and_drops_an_unnamed_sector(), test_a_named_large_cap_positive_year_stays_in_large_cap() (+29 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "executor.py"
Cohesion: 0.03
Nodes (72): asks_rating_list(), fetch_category_ratings(), rating_spec_for_forced_screen(), rating_for_request(), rating_needs_pillars(), fetch_vs_benchmark(), merge_fund_insight_metrics(), detail_has_live_facts() (+64 more)

### Community 42 - "fund_display.py"
Cohesion: 0.11
Nodes (28): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+20 more)

### Community 43 - "sources/google_news.py"
Cohesion: 0.09
Nodes (27): _entity_refs(), _log_scrape_record(), _scrape(), scrape_bodies(), _drop(), clip_log_text(), finish_run_logger(), fetch_entity_items() (+19 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.11
Nodes (23): _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), _search_macro_parameters() (+15 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "json"
Cohesion: 0.16
Nodes (14): fetch_fund(), load_done_isins(), load_isins(), main(), _pct(), run(), write_final(), load_portfolio_isins() (+6 more)

### Community 47 - "retrieve_scoped_news"
Cohesion: 0.18
Nodes (16): _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news(), _sector_entities() (+8 more)

### Community 48 - "httpx"
Cohesion: 0.27
Nodes (3): main(), main(), main()

### Community 49 - "build_fund_display_tables"
Cohesion: 0.10
Nodes (23): ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_markdown_tables_from_prose(), _comparison_pack(), test_caveats_about_missing_comparison_are_removed() (+15 more)

### Community 50 - "plan.py"
Cohesion: 0.07
Nodes (34): sector_focus_from_market(), field_prompt_table(), _apply_planner_request(), _example_part(), _invalidate_plan_system_cache(), _label_for_days(), make_plan(), parse_plan() (+26 more)

### Community 51 - "update.py"
Cohesion: 0.14
Nodes (19): drop_old_turns(), compare_payload_matches_funds(), add_gist(), empty_frame(), empty_state(), expire_stale_entities(), push_fund(), stack_entry() (+11 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "app.py"
Cohesion: 0.12
Nodes (32): ask(), ask_memory(), ask_sources(), ask_stream(), AskRequest, _attach_llm_meta(), backfill_page(), backfill_start() (+24 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (18): build_comparison_periods(), expense_ratio_for_question(), _f(), fund_returns_from_detail(), normalize_category_average_returns(), normalize_vs_benchmark_payload(), _optional_number(), parse_fund_costs() (+10 more)

### Community 55 - "call_json_llm"
Cohesion: 0.23
Nodes (15): _blocks_to_parts(), call_json_llm(), _model_for(), _composer_partial_usable(), _summarize_parsed_for_log(), _layered_news_topics(), _client(), _gemini_response() (+7 more)

### Community 56 - "graph.py"
Cohesion: 0.05
Nodes (51): asks_fund_risk(), asks_hidden_rating(), asks_private_system(), asks_sebi_riskometer(), blocked_reply(), rating_lead(), assemble_fund_overview_answer(), strip_context_disclaimer() (+43 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "nav_service.py"
Cohesion: 0.21
Nodes (11): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+3 more)

### Community 59 - "run_ask_engine"
Cohesion: 0.17
Nodes (7): run_ask_engine(), stream_ask_engine(), stream_insight_pipeline(), new_fund_brief_logger(), new_query_logger(), main(), test_ask_engine_delegates_to_insight_pipeline()

### Community 60 - "embed.py"
Cohesion: 0.14
Nodes (8): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), main()

### Community 61 - "normalize_rs_label"
Cohesion: 0.13
Nodes (21): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), infer_anchor_label_from_excludes() (+13 more)

### Community 62 - "embed_query"
Cohesion: 0.17
Nodes (12): _warmup_embeddings_background(), _run(), embed_query(), warmup_query_vectors(), _prewarm_tool_modules(), _body(), grouped_news(), NewsTarget (+4 more)

### Community 63 - "domain_intake.py"
Cohesion: 0.15
Nodes (15): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+7 more)

### Community 64 - "resolve_fund_for_query"
Cohesion: 0.10
Nodes (24): fetch_fund_managers_for_query(), get_fund_index(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), prefer_resolved_fund_name(), resolve_fund_for_query() (+16 more)

### Community 65 - "gold_service.py"
Cohesion: 0.11
Nodes (19): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+11 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "parse.py"
Cohesion: 0.17
Nodes (11): _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), infer_window_days_from_question(), parse_date_field(), parse_time_window() (+3 more)

### Community 68 - "test_guardrails_domain.py"
Cohesion: 0.20
Nodes (11): question_in_finance_scope(), check_guardrails(), financial_keyword_signal(), GuardrailResult, test_crude_why_not_misrouted_to_random_fund(), test_fund_question_still_passes(), test_hdfc_bank_passes_guardrails(), test_hdfc_bank_short_happening_passes() (+3 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "pack_sanitize.py"
Cohesion: 0.18
Nodes (9): _display_holding_row(), _enrich_investor_computed_fields(), _internal_contribution_row(), merge_holding_pp_into_performance(), _num(), _rollup_investor_summary(), split_attribution_for_composer(), test_compact_strips_contribution_from_data_attribution() (+1 more)

### Community 71 - "fund_rating_categories.py"
Cohesion: 0.18
Nodes (10): CategoryMatch, explanation_brief(), match_all_scheme_categories(), _names_a_type(), _phrase_in(), _spaced_category_words(), taxonomy_reply(), asks_cross_category_compare() (+2 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "llm_client.py"
Cohesion: 0.11
Nodes (26): Settings, anthropic_cache_control(), anthropic_system_blocks(), _call_anthropic(), _call_deepseek(), _call_gemini(), call_insight_llm(), _call_insight_llm_body() (+18 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "FundUniverseAgent"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 77 - "fund_match.py"
Cohesion: 0.12
Nodes (13): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+5 more)

### Community 78 - "portfolio_news_impact.py"
Cohesion: 0.16
Nodes (12): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+4 more)

### Community 79 - "test_fund_risk.py"
Cohesion: 0.07
Nodes (47): asks_about_score_bands(), asks_pillar_mark(), asks_pillar_structure(), asks_rating_concept(), asks_risk_trend_comparison(), asks_score_only(), _ensure_pillar_rating_plan(), ensure_risk_tools() (+39 more)

### Community 80 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 81 - "validate_capability_args"
Cohesion: 0.09
Nodes (27): _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), strip_empty_table_pointers(), _age_phrase(), align_plan_windows(), normalize_window_code() (+19 more)

### Community 82 - "eval_basic_queries.py"
Cohesion: 0.14
Nodes (14): ensure_fund_concentration_plan(), ensure_planner_fund_fact_modules(), _cases(), _check_plan(), _expects(), _live_plan(), main(), _modules() (+6 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "portfolio_news_impact.py"
Cohesion: 0.18
Nodes (12): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _strip_book_concentration_tables() (+4 more)

### Community 86 - "aggregate_fund_holdings.py"
Cohesion: 0.23
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 87 - "macro_impact_map.py"
Cohesion: 0.15
Nodes (16): _rule_sector_picks(), canonical_direction_for_driver(), clear_macro_impact_cache(), _document(), _driver_row(), list_macro_drivers(), macro_impact_entry(), macro_series_for_driver() (+8 more)

### Community 88 - "sector_alignment.py"
Cohesion: 0.27
Nodes (11): sector_yfinance_ticker(), analyze_sector_block(), canonical_sector_for_holding(), holding_return_pct(), holdings_in_sector(), index_return_pct(), return_sign(), run_sector_holding_alignment() (+3 more)

### Community 89 - "typing"
Cohesion: 0.18
Nodes (3): trim_news_grouped(), QueryPlan, SubQuery

### Community 90 - "enrich_manager_payload"
Cohesion: 0.22
Nodes (10): build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score(), test_default_manager_answer_drops_former_managers(), test_enrich_filters_past_only() (+2 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "lib/portfolio_scope.py"
Cohesion: 0.09
Nodes (35): build_portfolio_scope(), _clean_holding_tokens(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc() (+27 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.04
Nodes (93): EvidencePack, _add_category_comparison(), append_investor_portfolio_overview_tables(), _attach_rs_ratings_to_screen(), _benchmark_lines_from_pack(), build_evidence_pack(), _category_rows_from_investor(), _compare_brief_line() (+85 more)

### Community 96 - "nse_sector_indices.py"
Cohesion: 0.18
Nodes (10): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), _clear_index_cache(), test_by_sector_keys_match_sector_queries_exactly(), test_every_sector_has_verified_ticker_field(), test_nifty_50_benchmark_present() (+2 more)

### Community 97 - "v2_scoring.py"
Cohesion: 0.22
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 98 - "fund_search.py"
Cohesion: 0.12
Nodes (21): get_amc_catalog(), _amc_hints_from_tokens(), build_holding_overlap(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _entry_matches_amc() (+13 more)

### Community 99 - "extract_top_holdings"
Cohesion: 0.17
Nodes (13): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings() (+5 more)

### Community 100 - "plan_intent.py"
Cohesion: 0.30
Nodes (6): normalize_fund_pick_from_planner(), plan_wants_alternate_in_category(), reconcile_planner_intent(), test_compare_categories_not_replaced_by_composition(), test_normalize_fund_pick_from_planner_reading(), test_pick_alternate_tool_arg_counts()

### Community 102 - "question_mentions_fund_scheme"
Cohesion: 0.35
Nodes (7): question_mentions_fund_scheme(), apply_pure_concept_plan(), question_is_pure_general_concept(), test_all_holdings_metrics_adds_investor_tool(), test_large_cap_vs_mid_cap_is_pure_concept(), test_my_funds_is_not_pure_concept(), test_named_large_cap_scheme_keeps_tools()

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "ToolCall"
Cohesion: 0.05
Nodes (53): asks_category_performance(), asks_fund_holdings_followup(), ensure_category_performance_plan(), ensure_fund_holdings_followup_plan(), ensure_rating_list_funds(), maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name() (+45 more)

### Community 106 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 107 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 108 - "test_call_json_llm.py"
Cohesion: 0.24
Nodes (9): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), test_ask_plan_keeps_rich_agent_fields(), test_cluster_prefers_larger_groups() (+1 more)

### Community 109 - "news_insight_articles"
Cohesion: 0.29
Nodes (4): clean_news_insight(), news_insight_articles(), strip_publisher(), _subject_words()

### Community 110 - "test_insight_graph.py"
Cohesion: 0.16
Nodes (9): build_result(), run_graph(), run_graph_pipeline(), run_insight_pipeline(), _state(), test_lookup_route_skips_news_and_sends_no_identifiers_to_the_writer(), test_out_of_scope_question_ends_after_the_planner(), test_unmatched_fund_replies_without_calling_tools() (+1 more)

### Community 111 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 112 - "resolve_display_table_policy"
Cohesion: 0.16
Nodes (13): DisplayTablePolicy, filter_display_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark(), resolve_display_table_policy(), test_holdings_question_data_only_skips_returns_table(), test_benchmark_performance_data_only_uses_vs_table() (+5 more)

### Community 113 - "data_pack.py"
Cohesion: 0.38
Nodes (3): build_data_pack(), build(), _compact()

### Community 114 - "plan_catalog_bind.py"
Cohesion: 0.33
Nodes (6): _bind_fund_list(), _ensure_get_fund_data_for_holdings(), ensure_whole_book_catalog_scope(), _funds_from_entities(), _holding_scope(), _window_codes_from_plan()

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "test_composer_table_summaries.py"
Cohesion: 0.24
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_parse_tables_append_directive(), test_strip_empty_bold_sections(), test_summarize_tables_for_composer_extracts_mix_and_holdings()

### Community 117 - "test_greeting.py"
Cohesion: 0.27
Nodes (7): greeting_reply(), identity_reply(), _mirror_greeting(), test_fund_question_is_not_greeting_or_identity(), test_hello_mirrors_greeting(), test_main_memory_in_prompt_view(), test_who_are_you_identity()

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 121 - "test_prompt_cache_prefix.py"
Cohesion: 0.36
Nodes (5): build_anthropic_messages_body(), shared_system_prefix(), _body(), test_planner_and_composer_share_the_first_system_block(), test_tools_stay_available_when_there_is_no_shared_prefix()

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 125 - "fact_slots.py"
Cohesion: 0.33
Nodes (6): asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), test_aum_slot_renders_from_snapshot()

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "fund_catalog.py"
Cohesion: 0.39
Nodes (6): AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix(), install_amc_catalog(), _prefixes_for_amc_header()

### Community 128 - "contains_phrase"
Cohesion: 0.70
Nodes (3): _holding_mentioned(), matches_entity(), contains_phrase()

### Community 129 - "infer_fund_news_layers"
Cohesion: 0.33
Nodes (5): infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only()

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

### Community 134 - "_category_fund_name_spec"
Cohesion: 0.40
Nodes (4): _category_fund_name_spec(), _label_in(), _return_window(), _suggestion_spec()

### Community 135 - "prompts.py"
Cohesion: 0.22
Nodes (6): build_brief_prompt(), build_composer_prompt(), build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 136 - "compare_ask_speed.py"
Cohesion: 0.53
Nodes (4): compare(), _load(), main(), _numbers()

### Community 137 - "inputs"
Cohesion: 0.29
Nodes (7): default, description, required, type, holdings_limit, workflow_dispatch, inputs

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

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

### Community 157 - "_apply_category_difference"
Cohesion: 0.50
Nodes (3): _apply_category_difference(), _difference_brief(), _user_named_funds()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1389 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `AnswerMode`, `multi_fact.py`, `ToolCall`, `test_fund_drawdown.py`, `fund_context.py`, `sector_exposure_tables.py`, `QueryLogger`, `test_conversation_memory.py`, `fields.py`, `apply_planner_post_hooks`, `ensure_catalog_tools_for_fund_news`, `investor_subject.py`, `fund_rating_screen.py`, `test_fund_rating_screen.py`, `plan_to_brief`, `fund_display.py`, `plan.py`, `graph.py`, `gold_service.py`, `fund_rating_categories.py`, `test_fund_risk.py`, `validate_capability_args`, `eval_basic_queries.py`, `portfolio_news_impact.py`, `evidence_pack.py`, `plan_intent.py`, `question_mentions_fund_scheme`, `ToolCall`, `test_insight_graph.py`, `resolve_display_table_policy`, `plan_catalog_bind.py`, `test_composer_table_summaries.py`, `fact_slots.py`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 97 inferred relationships involving `ExecutionPlan` (e.g. with `evaluate_wave2()` and `resolve_compare_fund_pair()`) actually correct?**
  _`ExecutionPlan` has 97 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.07188118811881188 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `re` to `AnswerMode`, `interpret.py`, `portfolio/cache.py`, `gather.py`, `qdrant_reader.py`, `compute.py`, `QuestionBrief`, `tools.py`, `output_judge.py`, `ExecutionPlan`, `screen_hints_from_question`, `tool_runners.py`, `sector_fund_ranking.py`, `fund_brief.py`, `market_pulse.py`, `investor_subject.py`, `executor.py`, `retrieve_scoped_news`, `httpx`, `plan.py`, `app.py`, `call_json_llm`, `graph.py`, `run_ask_engine`, `embed.py`, `embed_query`, `gold_service.py`, `parse.py`, `llm_client.py`, `fund_match.py`, `portfolio_news_impact.py`, `stock_fund_ranking.py`, `validate_capability_args`, `portfolio_news_impact.py`, `fund_search.py`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ToolCall` (e.g. with `_apply_planner_request()` and `_portfolio_call()`) actually correct?**
  _`ToolCall` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `AnswerMode` be split into smaller, more focused modules?**
  _Cohesion score 0.03779128672745694 - nodes in this community are weakly interconnected._