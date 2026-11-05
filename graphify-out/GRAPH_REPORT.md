# Graph Report - db_design_with_qdrant_locally  (2026-11-05)

## Corpus Check
- 464 files · ~829,633 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 4884 nodes · 15525 edges · 190 communities (163 shown, 27 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 701 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b5146c09`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- AnswerMode
- fetch.py
- interpret.py
- portfolio/cache.py
- category_plan.py
- news_pipeline/config.py
- test_portfolio_layer.py
- Settings
- news_dates.py
- test_fund_drawdown.py
- gather.py
- embed_query
- compute.py
- QuestionBrief
- tools.py
- eval_basic_queries.py
- sector_exposure_tables.py
- QueryLogger
- news_reader.py
- _fund_performance_digest
- insight/portfolio_scope.py
- grounding.py
- affected_sectors.py
- tool_runners.py
- ._ensure_loaded
- sector_fund_ranking.py
- time
- article_quality.py
- fields.py
- fund_brief.py
- graph.py
- get_sector_fund_ranking_index
- ToolCall
- CapabilityCache
- market_pulse.py
- layer_tools.py
- plan_enforce.py
- fetch.py
- test_fund_rating_screen.py
- env
- executor.py
- call_json_llm
- sources/google_news.py
- macro_news_cache.py
- env
- json
- Any
- typing
- fund_display.py
- fund_context.py
- update.py
- env
- app.py
- fund_rupeestop_metrics.py
- test_call_json_llm.py
- graph.py
- scrape-worker/package.json
- nse_sector_indices.py
- _category_fund_name_spec
- embed.py
- fund_rating_screen.py
- portfolio/client.py
- re
- resolve_fund_for_query
- gold_service.py
- batch.ts
- portfolio_news_impact.py
- macro_impact_map.py
- http-fetch.ts
- investor_drawback.py
- fund_risk.py
- holdings_market.py
- get_settings
- with
- FundUniverseAgent
- fund_match.py
- fields.py
- execute_capability
- stock_fund_ranking.py
- return_windows.py
- concept_asks.py
- holding_attribution.py
- scrape-worker/src/index.ts
- planner_policy.py
- normalize.py
- test_fund_risk.py
- validate_capability_args
- resolve_display_table_policy
- enrich_manager_payload
- format_inr
- env
- universe.py
- steps
- evidence_pack.py
- lib/portfolio_scope.py
- v2_scoring.py
- fund_search.py
- extract_top_holdings
- plan.py
- re
- portfolio_bind.py
- run-daily-pipeline.sh
- env
- render_data_only_template
- test_two_wave_pipeline.py
- news_digest.py
- build_derived_views
- test_news_only_answer.py
- compare_evidence.py
- metals_spot_tables.py
- error_summary.py
- _run_screen_funds_by_exposure
- ExecutionPlan
- vitest
- fund_search.py
- test_greeting.py
- compilerOptions
- compilerOptions
- EntityFunnel
- data_pack.py
- backfill
- RunLogger
- sector_alignment.py
- test_portfolio_startup_cache.py
- run-pipeline
- nav_service.py
- multi_fact.py
- measured_facts_block
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
- infer_fund_news_layers
- trim_news_grouped
- run-backfill.sh
- qdrant
- sector_query_for_label
- aggregate_fund_holdings.py
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
- test_guardrails_domain.py
- rag-api.js
- install.sh
- apply_planner_post_hooks
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- test_macro_news_cache.py
- diagnose_lightsail_site.sh
- market_scope_entities
- retrieve_fund_articles
- execute_capability
- test_fund_payload_first.py
- table_source
- enforce_deictic_and_memory_primary_fund
- rank_funds_by_sector_exposure
- asks_rating_concept
- test_screen_rating_screen_arg.py
- compare_ask_speed.py
- contains_phrase
- json_util.py
- argparse
- _resolve_path

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 450 edges
2. `ToolCall` - 273 edges
3. `AnswerMode` - 141 edges
4. `get_settings()` - 137 edges
5. `QueryLogger` - 100 edges
6. `QuestionBrief` - 88 edges
7. `slot_route()` - 84 edges
8. `apply_planner_post_hooks()` - 84 edges
9. `Settings` - 83 edges
10. `node_compose()` - 81 edges

## Surprising Connections (you probably didn't know these)
- `test_colloquial_bluechip_aliases()` --calls--> `lookup_extracted_fund()`  [EXTRACTED]
  tests/test_fund_lookup.py → news_rag/fund_search.py
- `test_fund_index_has_amc_on_search_hit()` --calls--> `get_fund_index()`  [EXTRACTED]
  tests/test_fund_lookup.py → news_rag/fund_search.py
- `_offline_plan()` --uses--> `AnswerMode`  [INFERRED]
  scripts/eval_basic_queries.py → news_rag/insight/contracts.py
- `test_holdings_breakdown_keeps_planner_news()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_category_plan.py → news_rag/insight/contracts.py
- `test_render_fund_concentration_from_portfolio_data()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_fund_concentration.py → news_rag/insight/contracts.py

## Import Cycles
- None detected.

## Communities (190 total, 27 thin omitted)

### Community 0 - "logging"
Cohesion: 0.08
Nodes (46): get_encoder(), get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match() (+38 more)

### Community 1 - "AnswerMode"
Cohesion: 0.05
Nodes (57): rating_list_plan(), rating_concept_plan(), asks_fund_category_average(), QueryClass, Wave2Policy, glossary_execution_plan(), normalize_portfolio_plan_from_question(), _portfolio_call() (+49 more)

### Community 2 - "fetch.py"
Cohesion: 0.07
Nodes (21): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), article_id_from_url(), _batchexecute(), cached_resolve() (+13 more)

### Community 3 - "interpret.py"
Cohesion: 0.07
Nodes (62): Findings, FundFinding, SectorFinding, EvidenceSet, mentions_publication_date(), publication_date_keys(), strip_media_attribution(), _assemble() (+54 more)

### Community 4 - "portfolio/cache.py"
Cohesion: 0.18
Nodes (14): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), get_normalized_portfolio(), peek_derived(), peek_portfolio(), _run() (+6 more)

### Community 5 - "category_plan.py"
Cohesion: 0.05
Nodes (51): CategoryMatch, explanation_brief(), match_all_scheme_categories(), match_scheme_category(), _names_a_type(), _phrase_in(), _spaced_category_words(), taxonomy_reply() (+43 more)

### Community 6 - "news_pipeline/config.py"
Cohesion: 0.07
Nodes (13): _to_article(), EntityScore, StoredArticle, merge_stored_article(), payload_to_stored(), _datetime_range(), NewsStore, point_id_for_url() (+5 more)

### Community 7 - "test_portfolio_layer.py"
Cohesion: 0.14
Nodes (10): project_concentration(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore, test_concentration_keeps_cash() (+2 more)

### Community 8 - "Settings"
Cohesion: 0.06
Nodes (41): Publisher, SectorQuery, Settings, _merge_publisher_error_reasons(), write_day_report(), _atomic_write(), day_failure_slices_for_run(), ensure_loaded() (+33 more)

### Community 9 - "news_dates.py"
Cohesion: 0.06
Nodes (38): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), repo_root(), article_in_fetch_window(), google_time_query(), has_news_date_range() (+30 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (57): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+49 more)

### Community 11 - "gather.py"
Cohesion: 0.07
Nodes (48): _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext, LedgerEntry (+40 more)

### Community 12 - "embed_query"
Cohesion: 0.05
Nodes (34): _pack_row(), _retrieve_bullion_for_entities(), _trim_snippet(), embed_query(), corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news() (+26 more)

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (44): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+36 more)

### Community 14 - "QuestionBrief"
Cohesion: 0.05
Nodes (49): lookup_extracted_fund(), analyst_should_run(), asks_market_briefing(), asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), _brief_system() (+41 more)

### Community 15 - "tools.py"
Cohesion: 0.07
Nodes (46): retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), DataNeed, _active_sector_equity(), _args_from_question(), _articles_for_affected_question(), _as_date(), asks_equity_funds() (+38 more)

### Community 16 - "eval_basic_queries.py"
Cohesion: 0.09
Nodes (22): ensure_fund_concentration_plan(), node_route(), ensure_planner_fund_fact_modules(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question() (+14 more)

### Community 17 - "sector_exposure_tables.py"
Cohesion: 0.23
Nodes (14): owned_holding_names(), _all_holdings_metric_spec(), _fund_data_from_results(), _investor_holdings_rating_rows(), _metric_cell(), render_all_holdings_metric_table(), render_all_holdings_return_table(), render_all_holdings_sector_table() (+6 more)

### Community 18 - "QueryLogger"
Cohesion: 0.09
Nodes (9): slots_from_plan(), ParsedQuery, clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest(), test_finish_writes_json_sidecar() (+1 more)

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (40): _article_context_for_interpret(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority(), _clean_claims() (+32 more)

### Community 20 - "_fund_performance_digest"
Cohesion: 0.38
Nodes (4): _fund_performance_digest(), prefers_planner_over_slot(), test_fund_news_does_not_force_planner(), test_performance_digest_from_snapshot()

### Community 21 - "insight/portfolio_scope.py"
Cohesion: 0.17
Nodes (16): attach_drawback_digest(), build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), _pretty_category(), question_asks_portfolio_level_drawdown() (+8 more)

### Community 22 - "grounding.py"
Cohesion: 0.10
Nodes (30): widen_portfolio_args(), _holding_weight_pct(), _sector_weight_pct(), cores_for_float(), cores_in_text(), derived_cores(), finalize_text_fields(), fund_portfolio_cores() (+22 more)

### Community 23 - "affected_sectors.py"
Cohesion: 0.19
Nodes (11): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+3 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.12
Nodes (42): build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+34 more)

### Community 25 - "._ensure_loaded"
Cohesion: 0.13
Nodes (11): AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix(), get_amc_catalog(), install_amc_catalog(), _prefixes_for_amc_header(), _amc_hints_from_tokens() (+3 more)

### Community 26 - "sector_fund_ranking.py"
Cohesion: 0.13
Nodes (13): classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path(), sector_ranking_data_available() (+5 more)

### Community 27 - "time"
Cohesion: 0.10
Nodes (38): _take_conversation_slice(), _store_turn_memory(), clear_conversation(), drain_cache_events(), note_cache(), recall_slice(), recall_wider_portfolio(), remember_slice() (+30 more)

### Community 28 - "article_quality.py"
Cohesion: 0.11
Nodes (23): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+15 more)

### Community 29 - "fields.py"
Cohesion: 0.11
Nodes (40): _age(), _asks_portfolio_rs_ratings(), _book_line(), _comparison_rows(), _composition_line(), field_answer_needs_composer(), _fund_line(), _fund_name() (+32 more)

### Community 30 - "fund_brief.py"
Cohesion: 0.13
Nodes (20): qdrant_filter_names(), cluster_articles(), compose_fund_insight(), _day_key(), _empty_brief(), _fallback_bullets_from_events(), _fallback_summary(), _format_event_block() (+12 more)

### Community 31 - "graph.py"
Cohesion: 0.17
Nodes (13): RequestTelemetry, stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed(), event_phase_started(), event_quality_check(), event_request_failed() (+5 more)

### Community 32 - "get_sector_fund_ranking_index"
Cohesion: 0.08
Nodes (32): execute_wave(), get_sector_fund_ranking_index(), _clean_stock_capture(), phrase_is_mutual_fund_scheme(), phrase_looks_like_sector_reference(), return_window_days(), screen_hints_from_question(), stock_name_from_question() (+24 more)

### Community 33 - "ToolCall"
Cohesion: 0.06
Nodes (57): _ensure_pillar_rating_plan(), ensure_risk_tools(), _ensure_risk_trend_plan(), _use_rating_concept(), AnswerMode, ToolCall, ensure_multi_fact_tools(), align_planned_news_execution() (+49 more)

### Community 34 - "CapabilityCache"
Cohesion: 0.19
Nodes (5): CapabilityCache, _Entry, test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner()

### Community 35 - "market_pulse.py"
Cohesion: 0.08
Nodes (33): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), _one(), _fetch_macro_query(), _query_variants(), run_macro_news_enhanced() (+25 more)

### Community 36 - "layer_tools.py"
Cohesion: 0.10
Nodes (28): nifty50_ticker(), aggregate_sectors_from_holdings(), extract_top_sectors(), normalize_sector_row(), _run_get_market_snapshot(), _price_holdings(), benchmark_return_for_scheme(), _cache_path() (+20 more)

### Community 37 - "plan_enforce.py"
Cohesion: 0.09
Nodes (37): _categories_equivalent(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan(), ensure_deictic_fund_period_return_plan(), ensure_my_category_fund_investor_plan(), ensure_my_holding_fund_scope() (+29 more)

### Community 38 - "fetch.py"
Cohesion: 0.08
Nodes (19): _backoff(), _consent_jar(), fetch_url(), _handle_google_response(), make_session(), post_url(), _proxy(), _retry_after_seconds() (+11 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.09
Nodes (42): asks_taxonomy(), ensure_rating_screen(), _keep_asked_return(), _looks_like_fund_list(), parse_rating_screen(), _return_direction(), run_rating_list(), _payload() (+34 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "executor.py"
Cohesion: 0.06
Nodes (41): _amc_matches(), get_fund_index(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _capability_cache_key(), _conversation_id(), _conversation_turn() (+33 more)

### Community 42 - "call_json_llm"
Cohesion: 0.09
Nodes (27): _blocks_to_parts(), call_json_llm(), _composer_partial_usable(), _summarize_parsed_for_log(), extract_anthropic_text(), extract_assistant_text(), extract_gemini_text(), _json_balance() (+19 more)

### Community 43 - "sources/google_news.py"
Cohesion: 0.10
Nodes (26): _entity_refs(), _log_scrape_record(), _scrape(), scrape_bodies(), _drop(), clip_log_text(), finish_run_logger(), fetch_entity_items() (+18 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.21
Nodes (10): _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), _search_macro_parameters() (+2 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "json"
Cohesion: 0.13
Nodes (17): main(), main(), main(), fetch_fund(), load_done_isins(), load_isins(), main(), _pct() (+9 more)

### Community 48 - "typing"
Cohesion: 0.10
Nodes (15): run_ask_engine(), stream_ask_engine(), asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), run_insight_pipeline() (+7 more)

### Community 49 - "fund_display.py"
Cohesion: 0.05
Nodes (61): append_news_section(), _as_float(), assemble_fund_overview_answer(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), complete_sentences() (+53 more)

### Community 50 - "fund_context.py"
Cohesion: 0.10
Nodes (27): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), _resolve_funds(), resolve_deictic_fund_name(), asks_these_equity_funds(), comparison_fund_names(), _filter(), _frame_subjects() (+19 more)

### Community 51 - "update.py"
Cohesion: 0.14
Nodes (20): drop_old_turns(), compare_payload_matches_funds(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), empty_frame(), empty_state(), expire_stale_entities() (+12 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "app.py"
Cohesion: 0.07
Nodes (33): ask_memory(), ask_sources(), backfill_page(), backfill_start(), backfill_status(), backfill_stop(), BackfillRequest, _check_token() (+25 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.13
Nodes (18): build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns(), normalize_vs_benchmark_payload() (+10 more)

### Community 55 - "test_call_json_llm.py"
Cohesion: 0.24
Nodes (9): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), test_ask_plan_keeps_rich_agent_fields(), test_cluster_prefers_larger_groups() (+1 more)

### Community 56 - "graph.py"
Cohesion: 0.07
Nodes (31): asks_fund_risk(), asks_hidden_rating(), asks_sebi_riskometer(), blocked_reply(), _attach_conversation(), build_result(), _conversation_id(), _drop_scheme_is_the_whole_book() (+23 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "nse_sector_indices.py"
Cohesion: 0.18
Nodes (11): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _clear_index_cache(), test_by_sector_keys_match_sector_queries_exactly(), test_every_sector_has_verified_ticker_field() (+3 more)

### Community 59 - "_category_fund_name_spec"
Cohesion: 0.40
Nodes (4): _category_fund_name_spec(), _label_in(), _return_window(), _suggestion_spec()

### Community 60 - "embed.py"
Cohesion: 0.15
Nodes (7): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, _build_encoder(), main()

### Community 61 - "fund_rating_screen.py"
Cohesion: 0.08
Nodes (36): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), _amc_outside_label() (+28 more)

### Community 62 - "portfolio/client.py"
Cohesion: 0.19
Nodes (9): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), rupeestop_admin_request_headers(), rupeestop_bearer_token(), test_admin_headers_include_bearer(), test_bearer_prefers_auth_token_over_admin_token() (+1 more)

### Community 63 - "re"
Cohesion: 0.14
Nodes (16): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+8 more)

### Community 64 - "resolve_fund_for_query"
Cohesion: 0.13
Nodes (17): is_macro_metals_question(), is_market_fund_discovery_question(), resolve_fund_for_query(), resolve_fund_from_question(), _resolved_scheme_for_portfolio_ask(), test_absl_and_ppfas_shorthand(), test_absl_conservative_hybrid_active_fof(), test_absl_large_cap_is_not_frontline_or_the_trigger_plan() (+9 more)

### Community 65 - "gold_service.py"
Cohesion: 0.09
Nodes (21): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+13 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "portfolio_news_impact.py"
Cohesion: 0.23
Nodes (10): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), fetch_top_holdings() (+2 more)

### Community 68 - "macro_impact_map.py"
Cohesion: 0.23
Nodes (12): _rule_sector_picks(), canonical_direction_for_driver(), _document(), _driver_row(), list_macro_drivers(), macro_impact_entry(), macro_series_for_driver(), normalize_direction() (+4 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "investor_drawback.py"
Cohesion: 0.12
Nodes (20): question_asks_all_schemes_in_answer(), _display_holding_row(), _enrich_investor_computed_fields(), _internal_contribution_row(), investor_holdings_for_display(), merge_holding_pp_into_performance(), _num(), _rollup_investor_summary() (+12 more)

### Community 71 - "fund_risk.py"
Cohesion: 0.14
Nodes (13): asks_private_system(), asks_risk_trend_comparison(), asks_score_only(), exposure_from_detail(), fetch_public_rating(), include_drawdown_with_risk(), load_fund_risk(), normalize_rating() (+5 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "get_settings"
Cohesion: 0.07
Nodes (45): ask(), ask_stream(), AskRequest, _attach_llm_meta(), fund_brief(), health(), get_settings(), Settings (+37 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "FundUniverseAgent"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 77 - "fund_match.py"
Cohesion: 0.12
Nodes (13): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+5 more)

### Community 78 - "fields.py"
Cohesion: 0.11
Nodes (22): periods_requested_in_question(), _asks_book(), bind_fields_to_tools(), _book_fields(), canonicalize_field(), field_need(), FieldNeed, fields_from_question() (+14 more)

### Community 79 - "execute_capability"
Cohesion: 0.29
Nodes (6): _compare_cache_label(), _compare_payload_matches_funds(), test_compare_conversation_cache_does_not_reuse_different_pair(), fake_compare(), test_compare_conversation_cache_hits_same_pair(), test_compare_payload_matches_funds()

### Community 80 - "stock_fund_ranking.py"
Cohesion: 0.20
Nodes (14): extract_top_holdings(), _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file() (+6 more)

### Community 81 - "return_windows.py"
Cohesion: 0.20
Nodes (13): _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows(), window_label() (+5 more)

### Community 82 - "concept_asks.py"
Cohesion: 0.15
Nodes (17): apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), ScopeKind, apply_pure_concept_plan(), question_is_pure_general_concept() (+9 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "planner_policy.py"
Cohesion: 0.13
Nodes (14): apply_now_window(), _ensure_sector_overview(), finalize_planner_plan(), question_uses_now_window(), planner_supplement_for_question(), asks_sector_overview(), test_finalize_planner_plan_fills_funds_from_question(), test_named_period_is_not_replaced_by_right_now() (+6 more)

### Community 86 - "normalize.py"
Cohesion: 0.25
Nodes (14): _allocation_block(), _apply_holding_values(), _first(), _holding_from_scheme(), normalize_workspace(), _num(), _pnl_summary_row(), _prefer_xirr() (+6 more)

### Community 87 - "test_fund_risk.py"
Cohesion: 0.16
Nodes (17): asks_pillar_mark(), pillar_focus(), rating_lead(), render_pillar_marks_table(), render_risk_lines(), _public_summary(), test_fund_manager_name_ask_is_not_fund_manager_pillar(), test_fund_quality_question_maps_to_portfolio_quality_pillar() (+9 more)

### Community 88 - "validate_capability_args"
Cohesion: 0.22
Nodes (8): _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_vs_benchmark_module_is_not_replaced_by_snapshot(), test_validate_capability_requires_modules(), test_a_risk_read_does_not_point_at_a_missing_returns_table(), test_any_period_code_is_kept(), test_validate_capability_args_keeps_rating_screen()

### Community 89 - "resolve_display_table_policy"
Cohesion: 0.08
Nodes (26): resolve_display_periods(), DisplayTablePolicy, fact_values_already_stated(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark() (+18 more)

### Community 90 - "enrich_manager_payload"
Cohesion: 0.20
Nodes (11): asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score(), test_default_manager_answer_drops_former_managers() (+3 more)

### Community 91 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "universe.py"
Cohesion: 0.15
Nodes (19): _clean_holding_tokens(), instrument_to_qdrant_names(), match_holding_to_corpus_entity(), load_portfolio_universe(), _aliases_for(), build_holding_entities(), canonical_key(), _display_name() (+11 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.09
Nodes (42): append_investor_portfolio_overview_tables(), _attach_rs_ratings_to_screen(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_cell(), _compare_header(), _complete_fund_row(), _complete_shown_funds() (+34 more)

### Community 96 - "lib/portfolio_scope.py"
Cohesion: 0.19
Nodes (14): build_portfolio_scope(), FundRef, _holding_equity_allowed(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest(), load_portfolio_funds() (+6 more)

### Community 97 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 98 - "fund_search.py"
Cohesion: 0.17
Nodes (12): _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question(), _is_bullion_phrase_not_scheme() (+4 more)

### Community 99 - "extract_top_holdings"
Cohesion: 0.17
Nodes (13): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings() (+5 more)

### Community 100 - "plan.py"
Cohesion: 0.09
Nodes (25): field_prompt_table(), _apply_planner_request(), _example_part(), _invalidate_plan_system_cache(), _label_for_days(), make_plan(), parse_plan(), _pick_enum() (+17 more)

### Community 101 - "re"
Cohesion: 0.08
Nodes (22): _short_benchmark_label(), strip_context_disclaimer(), strip_grounding_holes(), strip_missing_data_caveats(), strip_private_leaks(), asks_precise_definition(), direct_glossary_reply(), extract_glossary_term() (+14 more)

### Community 102 - "portfolio_bind.py"
Cohesion: 0.24
Nodes (8): question_asks_category_book_share(), bind_cached_portfolio(), ensure_tools_for_data_question(), finish_portfolio_plan_bind(), _investor_args(), _merge_fund(), question_mentions_own_book(), find_cached_holdings()

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "render_data_only_template"
Cohesion: 0.07
Nodes (31): EvidencePack, EvidenceRow, build_evidence_pack(), extra_part_brief(), _holding_label(), _portfolio_markdown(), _portfolio_sections_from_plan(), _portfolio_top_n() (+23 more)

### Community 106 - "test_two_wave_pipeline.py"
Cohesion: 0.13
Nodes (9): evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), test_bridge_skips_wave2_for_data_only(), test_bridge_skips_when_return_positive(), test_bridge_triggers_on_negative_return(), test_fund_manager_data_only_template_includes_context_and_bio(), test_portfolio_data_only_template_uses_percentage_fields() (+1 more)

### Community 107 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 108 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 109 - "test_news_only_answer.py"
Cohesion: 0.22
Nodes (7): _news_subject(), _run_get_macro_news(), clean_news_insight(), is_article_only_news(), strip_publisher(), test_news_about_hdfc_bank_is_not_a_market_pulse(), test_news_insight_drops_publisher_clips_and_unrelated_articles()

### Community 110 - "compare_evidence.py"
Cohesion: 0.27
Nodes (7): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 111 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 112 - "error_summary.py"
Cohesion: 0.42
Nodes (5): _bucket(), _entity_names(), summarize_errors(), write_error_summary(), test_google_and_jev_errors_are_split_with_entities_and_dates()

### Community 113 - "_run_screen_funds_by_exposure"
Cohesion: 0.14
Nodes (20): categories_for(), _add_category_comparison(), _best_label(), _execute_rating_list(), _higher_pillars(), _install_suggestion_screen(), _keep(), _keep_followup_plan() (+12 more)

### Community 114 - "ExecutionPlan"
Cohesion: 0.08
Nodes (44): ExecutionPlan, node_resolve(), plan_targets_single_fund_measured_return(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings(), _ensure_portfolio_data_for_compare(), _ensure_portfolio_data_for_holdings() (+36 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "fund_search.py"
Cohesion: 0.10
Nodes (25): build_holding_overlap(), _clean_company_name(), detail_has_live_facts(), _entry_matches_amc(), _entry_matches_query_scheme(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers() (+17 more)

### Community 117 - "test_greeting.py"
Cohesion: 0.27
Nodes (7): greeting_reply(), identity_reply(), _mirror_greeting(), test_fund_question_is_not_greeting_or_identity(), test_hello_mirrors_greeting(), test_main_memory_in_prompt_view(), test_who_are_you_identity()

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 121 - "data_pack.py"
Cohesion: 0.32
Nodes (4): build_data_pack(), build(), _compact(), test_data_pack_groups_by_fund_and_hides_internal_fields()

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 124 - "sector_alignment.py"
Cohesion: 0.17
Nodes (13): clear_macro_impact_cache(), analyze_sector_block(), canonical_sector_for_holding(), holding_return_pct(), holdings_in_sector(), index_return_pct(), return_sign(), run_sector_holding_alignment() (+5 more)

### Community 125 - "test_portfolio_startup_cache.py"
Cohesion: 0.17
Nodes (15): clear_cache_for_tests(), seed_portfolio_cache_for_tests(), PortfolioError, PortfolioUnavailable, PortfolioUpstreamError, _doc(), test_compare_binds_cached_large_cap(), test_concept_question_keeps_an_empty_tool_list() (+7 more)

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "nav_service.py"
Cohesion: 0.21
Nodes (11): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+3 more)

### Community 128 - "multi_fact.py"
Cohesion: 0.14
Nodes (11): _followup_modules(), ensure_compare_template(), ensure_screen_facts(), top_n_from_question(), test_highest_rating_plus_returns_and_risk_keeps_the_fund_lookup(), test_compare_and_risk_stay_on_the_first_wave(), test_screen_plan_drops_the_unrelated_fund_lookup(), test_top_five_sectors() (+3 more)

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
Cohesion: 0.25
Nodes (5): build_composer_prompt(), build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 135 - "test_composer_table_summaries.py"
Cohesion: 0.24
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections(), test_summarize_tables_for_composer_extracts_mix_and_holdings()

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

### Community 141 - "infer_fund_news_layers"
Cohesion: 0.33
Nodes (5): infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only()

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

### Community 145 - "sector_query_for_label"
Cohesion: 0.13
Nodes (4): normalize_sector_label(), sector_query_for_label(), _sector_label_in_text(), SectorFundRankingIndex

### Community 146 - "aggregate_fund_holdings.py"
Cohesion: 0.20
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

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

### Community 157 - "test_guardrails_domain.py"
Cohesion: 0.20
Nodes (11): question_in_finance_scope(), check_guardrails(), financial_keyword_signal(), GuardrailResult, test_crude_why_not_misrouted_to_random_fund(), test_fund_question_still_passes(), test_hdfc_bank_passes_guardrails(), test_hdfc_bank_short_happening_passes() (+3 more)

### Community 163 - "apply_planner_post_hooks"
Cohesion: 0.06
Nodes (39): merge_planner_asked_facts(), tag_answer_parts(), ensure_catalog_tools_for_fund_news(), apply_category_scoped_compare_funds(), apply_deictic_equity_compare_funds(), apply_planner_post_hooks(), _compare_against_portfolio_holding(), _compare_category_slug() (+31 more)

### Community 170 - "test_macro_news_cache.py"
Cohesion: 0.16
Nodes (13): select_macro_for_question(), _digest(), test_banking_and_banks_are_one_search(), test_cache_keeps_the_article_body_not_only_the_title(), test_cache_searches_named_macro_parameters(), test_clusters_are_ordered_by_how_many_articles_are_in_the_db(), test_failed_refresh_keeps_the_previous_cache(), test_macro_news_is_reused_for_two_hours_then_overwritten() (+5 more)

### Community 175 - "retrieve_fund_articles"
Cohesion: 0.24
Nodes (11): PortfolioScope, _article_entities(), build_events(), _cluster_entities(), _exposure_for_holding(), _exposure_for_sector(), _fund_by_isin(), fund_search_query() (+3 more)

### Community 177 - "execute_capability"
Cohesion: 0.17
Nodes (5): get_capability_cache(), _capabilities_for_planner(), capability_catalog_text(), execute_capability(), test_capabilities_cache_stores_and_retrieves()

### Community 178 - "test_fund_payload_first.py"
Cohesion: 0.20
Nodes (8): headline_rating(), rating_for_request(), rating_needs_pillars(), test_default_windows_are_one_three_and_five_years(), test_headline_helper_drops_computed_at(), test_headline_rating_has_no_date_and_skips_admin(), test_named_window_is_not_expanded(), test_snapshot_uses_payload_returns_and_history_only_for_gaps()

### Community 179 - "table_source"
Cohesion: 0.15
Nodes (9): _add_category_comparison(), _compare_brief_line(), _row_bits(), table_source(), test_a_rating_row_is_filled_with_returns_riskometer_and_category_average(), test_fund_insights_category_average_reaches_the_composer_row(), test_table_source_includes_sebi_riskometer_from_risk_module(), test_table_source_keeps_pillar_marks_and_the_fetched_return() (+1 more)

### Community 180 - "enforce_deictic_and_memory_primary_fund"
Cohesion: 0.27
Nodes (7): enforce_deictic_and_memory_primary_fund(), reconcile_deictic_planner_fund(), resolve_user_named_fund_in_memory(), user_explicitly_named_scheme(), deictic_fund_context_active(), test_deictic_inactive_after_no_fund_gist_strips_planner_fund(), test_deictic_uses_recent_fund_focus_not_planner_hallucination()

### Community 181 - "rank_funds_by_sector_exposure"
Cohesion: 0.29
Nodes (6): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), rank_funds_by_sector_exposure()

### Community 182 - "asks_rating_concept"
Cohesion: 0.25
Nodes (5): asks_about_score_bands(), asks_pillar_structure(), asks_rating_concept(), _is_band_definition(), test_general_pillar_max_question_uses_concept_brief()

### Community 183 - "test_screen_rating_screen_arg.py"
Cohesion: 0.28
Nodes (6): test_finalize_screen_adds_returns_for_compare_question(), fake_detail(), get_fund_detail(), test_rating_screen_uses_focus_question_not_full_compare_question(), test_rating_screen_uses_forced_category_spec(), fake_fetch()

### Community 184 - "compare_ask_speed.py"
Cohesion: 0.53
Nodes (4): compare(), _load(), main(), _numbers()

### Community 185 - "contains_phrase"
Cohesion: 0.70
Nodes (3): _holding_mentioned(), matches_entity(), contains_phrase()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1423 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `multi_fact.py`, `AnswerMode`, `category_plan.py`, `test_composer_table_summaries.py`, `test_fund_drawdown.py`, `gather.py`, `eval_basic_queries.py`, `sector_exposure_tables.py`, `QueryLogger`, `insight/portfolio_scope.py`, `time`, `fields.py`, `ToolCall`, `apply_planner_post_hooks`, `plan_enforce.py`, `test_fund_rating_screen.py`, `typing`, `fund_context.py`, `enforce_deictic_and_memory_primary_fund`, `app.py`, `asks_rating_concept`, `graph.py`, `fund_rating_screen.py`, `gold_service.py`, `portfolio_news_impact.py`, `investor_drawback.py`, `fund_risk.py`, `fields.py`, `concept_asks.py`, `planner_policy.py`, `test_fund_risk.py`, `resolve_display_table_policy`, `evidence_pack.py`, `plan.py`, `re`, `portfolio_bind.py`, `render_data_only_template`, `test_two_wave_pipeline.py`, `test_news_only_answer.py`, `compare_evidence.py`, `test_portfolio_startup_cache.py`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 72 inferred relationships involving `ExecutionPlan` (e.g. with `evaluate_wave2()` and `resolve_compare_fund_pair()`) actually correct?**
  _`ExecutionPlan` has 72 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.08002866698518872 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ToolCall` to `multi_fact.py`, `AnswerMode`, `category_plan.py`, `test_fund_drawdown.py`, `gather.py`, `eval_basic_queries.py`, `sector_exposure_tables.py`, `insight/portfolio_scope.py`, `grounding.py`, `time`, `get_sector_fund_ranking_index`, `CapabilityCache`, `apply_planner_post_hooks`, `plan_enforce.py`, `test_fund_rating_screen.py`, `executor.py`, `execute_capability`, `fund_context.py`, `update.py`, `enforce_deictic_and_memory_primary_fund`, `app.py`, `graph.py`, `fund_rating_screen.py`, `gold_service.py`, `portfolio_news_impact.py`, `fund_risk.py`, `fields.py`, `execute_capability`, `concept_asks.py`, `planner_policy.py`, `test_fund_risk.py`, `resolve_display_table_policy`, `plan.py`, `portfolio_bind.py`, `render_data_only_template`, `test_two_wave_pipeline.py`, `test_news_only_answer.py`, `compare_evidence.py`, `_run_screen_funds_by_exposure`, `ExecutionPlan`, `test_portfolio_startup_cache.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ToolCall` (e.g. with `_apply_planner_request()` and `_portfolio_call()`) actually correct?**
  _`ToolCall` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `AnswerMode` be split into smaller, more focused modules?**
  _Cohesion score 0.050042955326460484 - nodes in this community are weakly interconnected._