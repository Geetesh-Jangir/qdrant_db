# Graph Report - db_design_with_qdrant_locally  (2026-11-04)

## Corpus Check
- 460 files · ~825,427 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 4802 nodes · 15242 edges · 171 communities (148 shown, 23 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 743 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b7fa1824`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- AnswerMode
- fetch.py
- interpret.py
- fetch.py
- category_plan.py
- news_pipeline/config.py
- portfolio/cache.py
- Settings
- news_dates.py
- test_fund_drawdown.py
- gather.py
- embed_query
- compute.py
- QuestionBrief
- tools.py
- fields.py
- sector_exposure_tables.py
- QueryLogger
- news_reader.py
- question_intent.py
- ExecutionPlan
- node_compose
- get_sector_fund_ranking_index
- tool_runners.py
- Any
- sector_fund_ranking.py
- test_conversation_memory.py
- article_quality.py
- fields.py
- fund_brief.py
- graph.py
- slot_route
- test_fund_risk.py
- CapabilityCache
- market_pulse.py
- layer_tools.py
- plan_enforce.py
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
- typing
- build_fund_display_tables
- planner_policy.py
- update.py
- env
- app.py
- fund_rupeestop_metrics.py
- test_call_json_llm.py
- graph.py
- scrape-worker/package.json
- nav_service.py
- parse_rating_screen
- embed.py
- normalize_rs_label
- portfolio_plan.py
- re
- resolve_fund_for_query
- gold_service.py
- batch.ts
- execute_capability
- lib/portfolio_scope.py
- http-fetch.ts
- investor_drawback.py
- aggregate_fund_holdings.py
- holdings_market.py
- get_settings
- with
- FundUniverseAgent
- fund_match.py
- fund_search.py
- execute_capability
- stock_fund_ranking.py
- validate_capability_args
- contracts.py
- holding_attribution.py
- scrape-worker/src/index.ts
- portfolio_news_impact.py
- get_stock_profile
- glossary.py
- validate_capability_args
- DisplayTablePolicy
- enrich_manager_payload
- env
- universe.py
- steps
- evidence_pack.py
- generate_fund_brief
- v2_scoring.py
- fund_search.py
- extract_top_holdings
- plan.py
- PublisherStats
- concept_asks.py
- run-daily-pipeline.sh
- env
- render_data_only_template
- strip_news_roundup
- news_digest.py
- validate_plan_tools
- fund_display.py
- compare_evidence.py
- metals_spot_tables.py
- SectorFundRankingIndex
- data_pack.py
- enforce_planner_catalog_plan
- vitest
- slots_from_plan
- test_greeting.py
- compilerOptions
- compilerOptions
- EntityFunnel
- plan_system_prompt
- backfill
- RunLogger
- sector_alignment.py
- test_portfolio_layer.py
- run-pipeline
- fund_catalog.py
- contains_phrase
- evaluate_wave2
- worker/src/index.ts
- steps
- steps
- with
- prompts.py
- test_composer_table_summaries.py
- inputs
- with
- inputs
- asks_computed_illustration
- measured_facts_block
- run-backfill.sh
- qdrant
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
- install.sh
- ToolCall
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- relationships.py
- diagnose_lightsail_site.sh
- market_scope_entities

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 434 edges
2. `ToolCall` - 267 edges
3. `AnswerMode` - 143 edges
4. `get_settings()` - 127 edges
5. `QueryLogger` - 100 edges
6. `QuestionBrief` - 88 edges
7. `slot_route()` - 84 edges
8. `apply_planner_post_hooks()` - 83 edges
9. `Settings` - 83 edges
10. `node_compose()` - 75 edges

## Surprising Connections (you probably didn't know these)
- `test_grouped_news_keeps_the_article_body()` --calls--> `_group_layered_articles()`  [EXTRACTED]
  tests/test_insight_links.py → news_rag/insight/capabilities/executor.py
- `test_banking_and_banks_are_one_search()` --calls--> `_news_search_targets()`  [EXTRACTED]
  tests/test_macro_news_cache.py → news_rag/insight/capabilities/executor.py
- `test_performance_digest_from_snapshot()` --calls--> `_fund_performance_digest()`  [EXTRACTED]
  tests/test_fund_performance_digest.py → news_rag/insight/evidence_pack.py
- `test_sector_focus_states_the_gap_versus_the_index()` --calls--> `sector_focus_from_market()`  [EXTRACTED]
  tests/test_sector_overview.py → news_rag/insight/evidence_pack.py
- `test_compare_table_includes_risk_for_both_funds()` --calls--> `_render_fund_compare_markdown()`  [EXTRACTED]
  tests/test_holding_overlap.py → news_rag/insight/evidence_pack.py

## Import Cycles
- None detected.

## Communities (171 total, 23 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (50): get_encoder(), get_entity_funnel(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate() (+42 more)

### Community 1 - "AnswerMode"
Cohesion: 0.09
Nodes (27): rating_list_plan(), rating_concept_plan(), AnswerMode, QueryClass, ScopeKind, Wave2Policy, _macro_series_for_driver(), _plan_driver_impact() (+19 more)

### Community 2 - "fetch.py"
Cohesion: 0.07
Nodes (21): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), article_id_from_url(), _batchexecute(), cached_resolve() (+13 more)

### Community 3 - "interpret.py"
Cohesion: 0.06
Nodes (71): asks_random_fund_compare(), Findings, FundFinding, SectorFinding, mentions_publication_date(), publication_date_keys(), strip_media_attribution(), _assemble() (+63 more)

### Community 4 - "fetch.py"
Cohesion: 0.08
Nodes (19): _backoff(), _consent_jar(), fetch_url(), _handle_google_response(), make_session(), post_url(), _proxy(), _retry_after_seconds() (+11 more)

### Community 5 - "category_plan.py"
Cohesion: 0.05
Nodes (52): CategoryMatch, explanation_brief(), match_all_scheme_categories(), match_scheme_category(), _names_a_type(), _phrase_in(), _spaced_category_words(), taxonomy_reply() (+44 more)

### Community 6 - "news_pipeline/config.py"
Cohesion: 0.08
Nodes (11): is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), _datetime_range(), NewsStore, point_id_for_url(), inspect_qdrant() (+3 more)

### Community 7 - "portfolio/cache.py"
Cohesion: 0.05
Nodes (39): _BreakerState, _CacheEntry, crn_log_id(), get_normalized_portfolio(), fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url() (+31 more)

### Community 8 - "Settings"
Cohesion: 0.06
Nodes (44): Settings, _merge_publisher_error_reasons(), write_day_report(), _bucket(), _entity_names(), fetch_window_fields(), summarize_errors(), write_error_summary() (+36 more)

### Community 9 - "news_dates.py"
Cohesion: 0.07
Nodes (35): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), Publisher, repo_root(), SectorQuery, article_in_fetch_window() (+27 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (56): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+48 more)

### Community 11 - "gather.py"
Cohesion: 0.07
Nodes (49): _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext, LedgerEntry (+41 more)

### Community 12 - "embed_query"
Cohesion: 0.07
Nodes (20): _warmup_embeddings_background(), _run(), _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), embed_query() (+12 more)

### Community 13 - "compute.py"
Cohesion: 0.08
Nodes (45): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+37 more)

### Community 14 - "QuestionBrief"
Cohesion: 0.06
Nodes (44): analyst_should_run(), asks_market_briefing(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief(), _detect_direction() (+36 more)

### Community 15 - "tools.py"
Cohesion: 0.07
Nodes (51): extract_top_sectors(), DataNeed, _active_sector_equity(), _args_from_question(), _articles_for_affected_question(), _as_date(), asks_equity_funds(), _attach_screen_facts() (+43 more)

### Community 16 - "fields.py"
Cohesion: 0.09
Nodes (32): periods_requested_in_question(), _asks_book(), bind_fields_to_tools(), _book_fields(), canonicalize_field(), field_need(), FieldNeed, fields_from_question() (+24 more)

### Community 17 - "sector_exposure_tables.py"
Cohesion: 0.17
Nodes (16): merge_fund_isins_map(), owned_holding_names(), owned_holding_rows(), _all_holdings_metric_spec(), _fund_data_from_results(), _investor_holdings_rating_rows(), _metric_cell(), render_all_holdings_metric_table() (+8 more)

### Community 18 - "QueryLogger"
Cohesion: 0.09
Nodes (8): ParsedQuery, clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest(), test_finish_writes_json_sidecar(), test_log_parsed_includes_intent_and_fund()

### Community 19 - "news_reader.py"
Cohesion: 0.10
Nodes (37): _article_context_for_interpret(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority(), _clean_claims() (+29 more)

### Community 20 - "question_intent.py"
Cohesion: 0.13
Nodes (15): asks_fund_category_average(), plan_matches_intent(), prefers_planner_over_slot(), QuestionIntent, resolve_question_intent(), _top_n_from_question(), _asks_catalog_fund_performance(), _asks_fund_manager() (+7 more)

### Community 21 - "ExecutionPlan"
Cohesion: 0.06
Nodes (47): _ensure_pillar_rating_plan(), ExecutionPlan, _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark(), resolve_display_table_policy(), build_drawdown_wave2_calls(), plan_wants_fund_concentration() (+39 more)

### Community 22 - "node_compose"
Cohesion: 0.09
Nodes (31): repair_investor_insight_prose(), _sector_weight_pct(), strip_grounding_holes(), _drop_scheme_is_the_whole_book(), node_compose(), cores_for_float(), cores_in_text(), derived_cores() (+23 more)

### Community 23 - "get_sector_fund_ranking_index"
Cohesion: 0.07
Nodes (31): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+23 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.11
Nodes (44): get_fund_index(), _add(), build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief() (+36 more)

### Community 25 - "Any"
Cohesion: 0.10
Nodes (16): _clean_company_name(), detail_has_live_facts(), fetch_fund_managers_for_isin(), _fund_context_for_managers(), _fund_text(), FundIndex, get_fund_benchmark(), _named_weights() (+8 more)

### Community 26 - "sector_fund_ranking.py"
Cohesion: 0.14
Nodes (12): classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path(), sector_ranking_index_path() (+4 more)

### Community 27 - "test_conversation_memory.py"
Cohesion: 0.19
Nodes (18): build_result(), _fresh(), get_memory(), get_or_create(), reset_memory(), save_sources(), save_state(), save_turn_record() (+10 more)

### Community 28 - "article_quality.py"
Cohesion: 0.13
Nodes (18): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+10 more)

### Community 29 - "fields.py"
Cohesion: 0.08
Nodes (48): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), _age(), _asks_portfolio_rs_ratings() (+40 more)

### Community 30 - "fund_brief.py"
Cohesion: 0.13
Nodes (21): _article_entities(), cluster_articles(), _cluster_entities(), compose_fund_insight(), _day_key(), _fallback_bullets_from_events(), _fallback_summary(), _format_event_block() (+13 more)

### Community 31 - "graph.py"
Cohesion: 0.17
Nodes (14): RequestTelemetry, _answer_stream_chunks(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed(), event_phase_started(), event_quality_check() (+6 more)

### Community 32 - "slot_route"
Cohesion: 0.09
Nodes (27): random_fund_count(), execute_wave(), _asks_driver_sector_or_fund_impact(), _extract_drivers(), _extract_stocks(), _infer_window_days(), slot_route(), primary_sector_for_question() (+19 more)

### Community 33 - "test_fund_risk.py"
Cohesion: 0.05
Nodes (58): asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison() (+50 more)

### Community 34 - "CapabilityCache"
Cohesion: 0.11
Nodes (12): CapabilityCache, _Entry, get_capability_cache(), _return_slice_covers(), test_return_slice_requires_pillars_when_requested(), test_a_narrow_cache_does_not_stand_in_for_a_wider_request(), test_complete_payload_is_stored_in_capability_cache(), test_investor_holdings_cache_does_not_cover_pnl_summary_request() (+4 more)

### Community 35 - "market_pulse.py"
Cohesion: 0.08
Nodes (32): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), _fetch_macro_query(), _query_variants(), run_macro_news_enhanced(), _collect() (+24 more)

### Community 36 - "layer_tools.py"
Cohesion: 0.13
Nodes (22): nifty50_ticker(), _run_get_market_snapshot(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns(), _read_cache(), scheme_benchmark_metadata() (+14 more)

### Community 37 - "plan_enforce.py"
Cohesion: 0.04
Nodes (80): reroute_single_fund_risk_plan(), _resolve_funds(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_deictic_and_memory_primary_fund(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan(), ensure_deictic_fund_period_return_plan() (+72 more)

### Community 38 - "fund_rating_screen.py"
Cohesion: 0.12
Nodes (28): categories_for(), _add_category_comparison(), _amc_matches(), _apply_category_difference(), _best_label(), _cascade_labels_for_spec(), _catalog_name(), _difference_brief() (+20 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.15
Nodes (28): run_rating_list(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap(), fetch(), test_a_one_month_performer_is_shown_beside_the_same_category_rating(), fetch(), test_a_positive_one_month_return_is_paired_with_best_in_category() (+20 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "executor.py"
Cohesion: 0.07
Nodes (37): fetch_public_rating(), merge_fund_insight_metrics(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _conversation_id(), _conversation_turn(), _detail_for_fund_tool() (+29 more)

### Community 42 - "fund_display.py"
Cohesion: 0.12
Nodes (26): _as_float(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct(), _fmt_pp() (+18 more)

### Community 43 - "sources/google_news.py"
Cohesion: 0.10
Nodes (25): _entity_refs(), _log_scrape_record(), _scrape(), scrape_bodies(), _drop(), clip_log_text(), fetch_entity_items(), _match_publisher() (+17 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.11
Nodes (22): _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), select_macro_for_question() (+14 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "json"
Cohesion: 0.06
Nodes (28): _json_default(), safe_json_dumps(), main(), main(), main(), fetch_fund(), load_done_isins(), load_isins() (+20 more)

### Community 47 - "retrieve_scoped_news"
Cohesion: 0.09
Nodes (23): corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news() (+15 more)

### Community 48 - "typing"
Cohesion: 0.21
Nodes (5): run_ask_engine(), stream_ask_engine(), run_insight_pipeline(), stream_insight_pipeline(), test_ask_engine_delegates_to_insight_pipeline()

### Community 49 - "build_fund_display_tables"
Cohesion: 0.09
Nodes (23): assemble_fund_overview_answer(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers(), strip_markdown_tables_from_prose() (+15 more)

### Community 50 - "planner_policy.py"
Cohesion: 0.11
Nodes (17): _invalidate_plan_system_cache(), apply_now_window(), _ensure_sector_overview(), finalize_planner_plan(), question_uses_now_window(), normalize_portfolio_plan_from_question(), planner_supplement_for_question(), asks_sector_overview() (+9 more)

### Community 51 - "update.py"
Cohesion: 0.14
Nodes (21): drop_old_turns(), push_recent_fund_focus(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), empty_frame(), empty_state(), expire_stale_entities() (+13 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "app.py"
Cohesion: 0.10
Nodes (31): ask(), ask_memory(), ask_sources(), ask_stream(), AskRequest, _attach_llm_meta(), backfill_page(), backfill_start() (+23 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (19): build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), normalize_category_average_returns(), normalize_vs_benchmark_payload(), _optional_number() (+11 more)

### Community 55 - "test_call_json_llm.py"
Cohesion: 0.13
Nodes (20): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), _layered_news_topics(), _client() (+12 more)

### Community 56 - "graph.py"
Cohesion: 0.10
Nodes (24): strip_context_disclaimer(), _attach_conversation(), _clean_answer(), _conversation_id(), _ensure_portfolio_for_fund_news(), GraphState, GraphUnavailable, _load_planner_memory() (+16 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "nav_service.py"
Cohesion: 0.21
Nodes (11): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+3 more)

### Community 59 - "parse_rating_screen"
Cohesion: 0.12
Nodes (15): asks_taxonomy(), _amc_outside_label(), _amc_token(), asks_rating_list(), _category_fund_name_spec(), _label_in(), parse_rating_screen(), rating_spec_for_forced_screen() (+7 more)

### Community 60 - "embed.py"
Cohesion: 0.09
Nodes (9): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, _build_encoder(), embeddings_ready(), main() (+1 more)

### Community 61 - "normalize_rs_label"
Cohesion: 0.11
Nodes (25): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), infer_anchor_label_from_excludes() (+17 more)

### Community 62 - "portfolio_plan.py"
Cohesion: 0.15
Nodes (10): _looks_like_fund_list(), _get_top_n(), _plan_fund_performance_screen(), top_n_from_question(), explicit_fund_count(), _return_direction_in_question(), test_top_five_sectors(), test_top_sector_singular() (+2 more)

### Community 63 - "re"
Cohesion: 0.09
Nodes (27): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+19 more)

### Community 64 - "resolve_fund_for_query"
Cohesion: 0.12
Nodes (18): fetch_fund_managers_for_query(), is_macro_metals_question(), is_market_fund_discovery_question(), _lookup_fund_scan_question(), prefer_resolved_fund_name(), resolve_fund_for_query(), resolve_fund_from_question(), _resolved_scheme_for_portfolio_ask() (+10 more)

### Community 65 - "gold_service.py"
Cohesion: 0.15
Nodes (17): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+9 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "execute_capability"
Cohesion: 0.22
Nodes (11): widen_portfolio_args(), clear_conversation(), recall_slice(), recall_wider_portfolio(), remember_slice(), slice_key(), slice_slot(), test_holdings_then_sectors_keep_both_slices() (+3 more)

### Community 68 - "lib/portfolio_scope.py"
Cohesion: 0.14
Nodes (17): build_portfolio_scope(), _clean_holding_tokens(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc() (+9 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "investor_drawback.py"
Cohesion: 0.10
Nodes (25): _fund_performance_digest(), attach_drawback_digest(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer(), question_asks_all_schemes_in_answer(), _display_holding_row(), _enrich_investor_computed_fields() (+17 more)

### Community 71 - "aggregate_fund_holdings.py"
Cohesion: 0.20
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "get_settings"
Cohesion: 0.07
Nodes (51): health(), get_settings(), Settings, make_plan(), anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts(), _call_anthropic() (+43 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "FundUniverseAgent"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 77 - "fund_match.py"
Cohesion: 0.12
Nodes (13): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+5 more)

### Community 78 - "fund_search.py"
Cohesion: 0.15
Nodes (11): get_amc_catalog(), aggregate_sectors_from_holdings(), _amc_hints_from_tokens(), build_holding_overlap(), _entry_matches_amc(), _holding_overlap_key(), _infer_category_and_type(), _needles_for_amc_hint() (+3 more)

### Community 79 - "execute_capability"
Cohesion: 0.21
Nodes (8): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), compare_payload_matches_funds(), test_compare_conversation_cache_does_not_reuse_different_pair(), fake_compare(), test_compare_conversation_cache_hits_same_pair(), test_compare_payload_matches_funds()

### Community 80 - "stock_fund_ranking.py"
Cohesion: 0.15
Nodes (17): extract_top_holdings(), lookup_extracted_fund(), _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available() (+9 more)

### Community 81 - "validate_capability_args"
Cohesion: 0.15
Nodes (17): _capability_cache_key(), run_fund_snapshot(), _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return() (+9 more)

### Community 82 - "contracts.py"
Cohesion: 0.11
Nodes (15): LLMUsageRecord, PhaseRecord, ToolRecord, apply_pure_concept_plan(), question_is_pure_general_concept(), normalize_fund_pick_from_planner(), plan_wants_alternate_in_category(), reconcile_planner_intent() (+7 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "portfolio_news_impact.py"
Cohesion: 0.18
Nodes (12): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _strip_book_concentration_tables() (+4 more)

### Community 86 - "get_stock_profile"
Cohesion: 0.18
Nodes (5): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker(), _price_holdings()

### Community 87 - "glossary.py"
Cohesion: 0.26
Nodes (10): asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), glossary_execution_plan(), meaning_reply(), _normalize_term(), test_fund_nav_not_glossary(), test_nav_full_form_direct_reply() (+2 more)

### Community 88 - "validate_capability_args"
Cohesion: 0.08
Nodes (21): headline_rating(), rating_for_request(), rating_needs_pillars(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair() (+13 more)

### Community 90 - "enrich_manager_payload"
Cohesion: 0.24
Nodes (9): build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_default_manager_answer_drops_former_managers(), test_enrich_filters_past_only(), test_infer_roster_focus_current_vs_past() (+1 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "universe.py"
Cohesion: 0.16
Nodes (17): resolve_allisin_holdings_path(), load_portfolio_universe(), _aliases_for(), build_holding_entities(), canonical_key(), _display_name(), _holding_query(), _industry_search_hint() (+9 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.06
Nodes (58): render_pillar_marks_table(), _add_category_comparison(), append_investor_portfolio_overview_tables(), _attach_rs_ratings_to_screen(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line(), _compare_cell() (+50 more)

### Community 96 - "generate_fund_brief"
Cohesion: 0.20
Nodes (13): PortfolioScope, ScopedHolding, ScopedSector, build_events(), _empty_brief(), _exposure_for_holding(), _exposure_for_sector(), _fund_by_isin() (+5 more)

### Community 97 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 98 - "fund_search.py"
Cohesion: 0.16
Nodes (13): _detect_funds(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _entry_matches_query_scheme(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase() (+5 more)

### Community 99 - "extract_top_holdings"
Cohesion: 0.13
Nodes (17): normalize_holding_row(), strip_missing_data_caveats(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows() (+9 more)

### Community 100 - "plan.py"
Cohesion: 0.15
Nodes (14): _apply_planner_request(), _example_part(), _label_for_days(), parse_plan(), _pick_enum(), _planner_fields(), _slot_fallback(), _str_list() (+6 more)

### Community 102 - "concept_asks.py"
Cohesion: 0.31
Nodes (10): apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), asks_fof_funds(), test_concept_example_plan_screen_fof(), test_fof_name_one_detected() (+2 more)

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "render_data_only_template"
Cohesion: 0.05
Nodes (48): EvidencePack, EvidenceRow, build_evidence_pack(), _refresh_fund_blocks_ratings(), render_data_only_template(), _row_bits(), table_source(), has_second_part() (+40 more)

### Community 106 - "strip_news_roundup"
Cohesion: 0.22
Nodes (8): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed(), test_sector_focus_states_the_gap_versus_the_index()

### Community 107 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 108 - "validate_plan_tools"
Cohesion: 0.22
Nodes (9): _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question(), validate_plan_tools(), test_silver_price_tool_becomes_news(), test_deictic_exit_load_swaps_limits_for_snapshot() (+1 more)

### Community 109 - "fund_display.py"
Cohesion: 0.13
Nodes (14): _news_subject(), _assess_table_quality(), clean_news_insight(), is_article_only_news(), news_insight_articles(), news_only_answer(), render_news_answer(), _short_benchmark_label() (+6 more)

### Community 110 - "compare_evidence.py"
Cohesion: 0.27
Nodes (7): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 111 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 113 - "data_pack.py"
Cohesion: 0.18
Nodes (10): build_data_pack(), build(), _compact(), run_graph(), _state(), test_data_pack_groups_by_fund_and_hides_internal_fields(), test_lookup_route_skips_news_and_sends_no_identifiers_to_the_writer(), test_out_of_scope_question_ends_after_the_planner() (+2 more)

### Community 114 - "enforce_planner_catalog_plan"
Cohesion: 0.13
Nodes (26): _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings(), _ensure_portfolio_data_for_compare(), _ensure_portfolio_data_for_holdings(), ensure_whole_book_catalog_scope(), _funds_from_entities(), _holding_scope() (+18 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "slots_from_plan"
Cohesion: 0.26
Nodes (7): asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), slots_from_plan(), test_aum_slot_renders_from_snapshot()

### Community 117 - "test_greeting.py"
Cohesion: 0.18
Nodes (9): greeting_reply(), identity_reply(), _mirror_greeting(), memory_json_tokens(), prompt_view(), test_fund_question_is_not_greeting_or_identity(), test_hello_mirrors_greeting(), test_main_memory_in_prompt_view() (+1 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 121 - "plan_system_prompt"
Cohesion: 0.26
Nodes (7): field_prompt_table(), plan_system_prompt(), build_anthropic_messages_body(), shared_system_prefix(), _body(), test_planner_and_composer_share_the_first_system_block(), test_tools_stay_available_when_there_is_no_shared_prefix()

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 124 - "sector_alignment.py"
Cohesion: 0.07
Nodes (36): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _rule_sector_picks(), canonical_direction_for_driver(), clear_macro_impact_cache() (+28 more)

### Community 125 - "test_portfolio_layer.py"
Cohesion: 0.24
Nodes (8): clear_cache_for_tests(), test_current_value_and_nonzero_xirr(), test_executor_uses_workspace_sample_without_token(), test_executor_with_fixture(), test_normalize_strips_pii(), test_project_holdings_fields(), test_project_summary_minimal(), test_validate_capability_requires_modules()

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "fund_catalog.py"
Cohesion: 0.39
Nodes (6): AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix(), install_amc_catalog(), _prefixes_for_amc_header()

### Community 128 - "contains_phrase"
Cohesion: 0.70
Nodes (3): _holding_mentioned(), matches_entity(), contains_phrase()

### Community 129 - "evaluate_wave2"
Cohesion: 0.16
Nodes (9): evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), infer_fund_news_layers(), asks_fund_related_news(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only() (+1 more)

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

### Community 134 - "prompts.py"
Cohesion: 0.29
Nodes (4): build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 135 - "test_composer_table_summaries.py"
Cohesion: 0.14
Nodes (9): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), trim_news_grouped(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_parse_tables_append_directive(), test_strip_empty_bold_sections() (+1 more)

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

### Community 163 - "ToolCall"
Cohesion: 0.06
Nodes (45): ensure_rating_screen(), _followup_modules(), ToolCall, merge_planner_asked_facts(), tag_answer_parts(), ensure_fund_concentration_plan(), ensure_catalog_tools_for_fund_news(), ensure_compare_template() (+37 more)

### Community 170 - "relationships.py"
Cohesion: 0.29
Nodes (6): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), rank_funds_by_sector_exposure()

### Community 174 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1403 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `AnswerMode`, `evaluate_wave2`, `category_plan.py`, `test_composer_table_summaries.py`, `test_fund_drawdown.py`, `QuestionBrief`, `fields.py`, `sector_exposure_tables.py`, `question_intent.py`, `test_conversation_memory.py`, `fields.py`, `slot_route`, `test_fund_risk.py`, `ToolCall`, `plan_enforce.py`, `fund_rating_screen.py`, `test_fund_rating_screen.py`, `fund_display.py`, `planner_policy.py`, `update.py`, `graph.py`, `portfolio_plan.py`, `gold_service.py`, `investor_drawback.py`, `get_settings`, `validate_capability_args`, `contracts.py`, `portfolio_news_impact.py`, `glossary.py`, `evidence_pack.py`, `plan.py`, `concept_asks.py`, `render_data_only_template`, `strip_news_roundup`, `validate_plan_tools`, `fund_display.py`, `compare_evidence.py`, `data_pack.py`, `enforce_planner_catalog_plan`, `slots_from_plan`, `test_portfolio_layer.py`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `ExecutionPlan` (e.g. with `evaluate_wave2()` and `resolve_compare_fund_pair()`) actually correct?**
  _`ExecutionPlan` has 56 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.0687245195107746 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `get_settings` to `AnswerMode`, `interpret.py`, `portfolio/cache.py`, `gather.py`, `embed_query`, `compute.py`, `QuestionBrief`, `news_reader.py`, `ExecutionPlan`, `node_compose`, `get_sector_fund_ranking_index`, `tool_runners.py`, `sector_fund_ranking.py`, `fund_brief.py`, `slot_route`, `CapabilityCache`, `market_pulse.py`, `plan_enforce.py`, `executor.py`, `relationships.py`, `json`, `retrieve_scoped_news`, `app.py`, `graph.py`, `embed.py`, `gold_service.py`, `fund_match.py`, `fund_search.py`, `execute_capability`, `stock_fund_ranking.py`, `portfolio_news_impact.py`, `validate_capability_args`, `generate_fund_brief`, `plan.py`, `plan_system_prompt`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ToolCall` (e.g. with `_apply_planner_request()` and `_portfolio_call()`) actually correct?**
  _`ToolCall` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `AnswerMode` be split into smaller, more focused modules?**
  _Cohesion score 0.08672699849170437 - nodes in this community are weakly interconnected._