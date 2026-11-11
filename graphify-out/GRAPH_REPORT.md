# Graph Report - db_design_with_qdrant_locally  (2026-11-11)

## Corpus Check
- 503 files · ~865,732 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 5414 nodes · 17292 edges · 217 communities (185 shown, 32 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 678 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d9c9891c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- main.py
- market_pulse.py
- interpret.py
- test_portfolio_layer.py
- article_quality.py
- NewsStore
- normalize_rs_label
- affected_sectors.py
- news_dates.py
- test_fund_drawdown.py
- query_log.py
- ExecutionPlan
- compute.py
- plan.py
- tools.py
- fund_display.py
- fund_rating_screen.py
- QueryLogger
- news_reader.py
- time
- investor_subject.py
- test_call_json_llm.py
- scrape_bodies.py
- tool_runners.py
- category_plan.py
- test_fund_display_tables.py
- ensure_registry
- resolve_fund_for_query
- fields.py
- fund_brief.py
- node_compose
- executor.py
- get_settings
- get_sector_fund_ranking_index
- update.py
- test_fund_payload_first.py
- fund_context.py
- fund_type_name_spec
- test_fund_rating_screen.py
- env
- sector_alignment.py
- test_portfolio_startup_cache.py
- QuestionBrief
- get_macro_news
- env
- pack_sanitize.py
- portfolio_news_impact.py
- portfolio/cache.py
- GraphState
- app.py
- gold_service.py
- env
- nav_service.py
- fund_rupeestop_metrics.py
- contracts.py
- build_evidence_pack
- scrape-worker/package.json
- contracts.py
- sector_query_for_label
- embed.py
- RequestTelemetry
- test_rupeestop_auth.py
- domain_intake.py
- bullion_retrieve.py
- owned_holding_names
- batch.ts
- validate_capability_args
- insight/guardrails.py
- http-fetch.ts
- universe.py
- retrieve_scoped_news
- holdings_market.py
- node_route
- with
- stock_fund_ranking.py
- lib/portfolio_scope.py
- stock_fund_ranking.py
- CapabilityCache
- resolve_display_table_policy
- normalize.py
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- sector_fund_ranking.py
- test_fund_risk.py
- test_fact_answer.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- enrich_manager_payload
- Any
- env
- test_conversation_memory.py
- steps
- evidence_pack.py
- datetime
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- fund_risk.py
- format_inr
- layer_tools.py
- metals_spot_tables.py
- run-daily-pipeline.sh
- env
- _fund_performance_digest
- sources/google_news.py
- _normalize_fund_text
- re
- sector_alignment.py
- rupeestop_auth.py
- .lookup_extracted_fund
- index_series.py
- news_digest.py
- EntityFunnel
- vitest
- top_n_from_question
- strip_missing_data_caveats
- compilerOptions
- compilerOptions
- aggregate_fund_holdings.py
- investor_drawback.py
- backfill
- test_guardrails_domain.py
- test_composer_table_summaries.py
- v2_scoring.py
- run-pipeline
- test_portfolio_intents.py
- test_multi_fact_fund.py
- test_portfolio_layer.py
- worker/src/index.ts
- steps
- steps
- with
- get_stock_profile
- macro_impact_map.py
- insights.py
- inputs
- with
- inputs
- json
- test_answer_precision.py
- _run_screen_funds_by_exposure
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
- _return_slice_covers
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_catalog.py
- diagnose_lightsail_site.sh
- compare_evidence.py
- get_fund_index
- entity_candidates.py
- test_glossary.py
- test_call_json_llm.py
- build_derived_views
- memory/__init__.py
- test_holding_overlap.py
- test_macro_news_cache.py
- insight/portfolio_scope.py
- validate_plan_tools
- contains_phrase
- test_smart_fund_why.py
- question_is_bullion_metal_price_question
- plan_system_prompt
- test_one_rated_fund_per_category_does_not_fill_with_gold
- strip_missing_data_caveats
- test_metal_fund_rating.py
- infer_fund_news_layers
- rank_funds_by_sector_exposure
- news_insight_articles
- rating_lead
- _return_slice_covers
- extract.py
- RunLogger
- planner_catalog_knowledge.py
- normalize_rating
- _public_summary
- strip_news_roundup
- data_pack.py
- collect_evidence_calendar_dates
- market_scope_entities
- GoogleCircuitBreaker
- _attach_rs_ratings_to_screen
- test_market_sector_fund_pipeline.py
- json_util.py

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 534 edges
2. `ToolCall` - 324 edges
3. `get_settings()` - 137 edges
4. `apply_planner_post_hooks()` - 117 edges
5. `AnswerMode` - 110 edges
6. `QueryLogger` - 100 edges
7. `QuestionBrief` - 88 edges
8. `node_compose()` - 87 edges
9. `slot_route()` - 84 edges
10. `Settings` - 83 edges

## Surprising Connections (you probably didn't know these)
- `test_aum_slot_renders_from_snapshot()` --calls--> `render_asked_facts()`  [EXTRACTED]
  tests/test_fact_slots.py → news_rag/insight/fact_slots.py
- `build_events()` --uses--> `PortfolioScope`  [INFERRED]
  news_rag/fund_brief.py → lib/portfolio_scope.py
- `_exposure_for_holding()` --uses--> `PortfolioScope`  [INFERRED]
  news_rag/fund_brief.py → lib/portfolio_scope.py
- `_exposure_for_sector()` --uses--> `PortfolioScope`  [INFERRED]
  news_rag/fund_brief.py → lib/portfolio_scope.py
- `_fund_by_isin()` --uses--> `PortfolioScope`  [INFERRED]
  news_rag/fund_brief.py → lib/portfolio_scope.py

## Import Cycles
- None detected.

## Communities (217 total, 32 thin omitted)

### Community 0 - "logging"
Cohesion: 0.08
Nodes (45): get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate() (+37 more)

### Community 1 - "main.py"
Cohesion: 0.10
Nodes (24): _bucket(), _entity_names(), summarize_errors(), write_error_summary(), reset_run_buffers(), main(), _write_summary(), covered_calendar_days() (+16 more)

### Community 2 - "market_pulse.py"
Cohesion: 0.08
Nodes (32): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), _one(), _fetch_macro_query(), _query_variants(), run_macro_news_enhanced() (+24 more)

### Community 3 - "interpret.py"
Cohesion: 0.06
Nodes (71): Findings, FundFinding, SectorFinding, EvidenceSet, mentions_publication_date(), publication_date_keys(), strip_media_attribution(), _assemble() (+63 more)

### Community 4 - "test_portfolio_layer.py"
Cohesion: 0.16
Nodes (9): fetch_top_holdings(), project_concentration(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore (+1 more)

### Community 5 - "article_quality.py"
Cohesion: 0.24
Nodes (11): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+3 more)

### Community 6 - "NewsStore"
Cohesion: 0.10
Nodes (8): _to_article(), EntityScore, StoredArticle, merge_stored_article(), payload_to_stored(), _datetime_range(), NewsStore, point_id_for_url()

### Community 7 - "normalize_rs_label"
Cohesion: 0.13
Nodes (21): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), infer_anchor_label_from_excludes() (+13 more)

### Community 8 - "affected_sectors.py"
Cohesion: 0.08
Nodes (21): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+13 more)

### Community 9 - "news_dates.py"
Cohesion: 0.06
Nodes (38): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), repo_root(), article_in_fetch_window(), google_time_query(), has_news_date_range() (+30 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.09
Nodes (45): _add_drawdown_call(), asks_category_drawdown(), average_peer_drawdown(), collapse_episodes(), ensure_drawdown_tools(), investment_amount(), is_drawdown_definition(), _money() (+37 more)

### Community 11 - "query_log.py"
Cohesion: 0.07
Nodes (21): _events(), run_ask_engine(), stream_ask_engine(), asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value() (+13 more)

### Community 12 - "ExecutionPlan"
Cohesion: 0.04
Nodes (97): ensure_rating_screen(), _ensure_pillar_rating_plan(), _use_rating_concept(), ExecutionPlan, ToolCall, _portfolio_sections_from_plan(), merge_planner_asked_facts(), tag_answer_parts() (+89 more)

### Community 13 - "compute.py"
Cohesion: 0.08
Nodes (41): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+33 more)

### Community 14 - "plan.py"
Cohesion: 0.11
Nodes (19): _apply_planner_request(), _example_part(), _horizon_years(), _label_for_days(), parse_plan(), _pick_enum(), plan_to_brief(), _planner_fields() (+11 more)

### Community 15 - "tools.py"
Cohesion: 0.07
Nodes (51): run_driver_affected_funds_adapter(), DataNeed, _active_sector_equity(), _articles_for_affected_question(), _as_date(), asks_equity_funds(), _broad_working_well_keys(), _catalog_candidates() (+43 more)

### Community 16 - "fund_display.py"
Cohesion: 0.09
Nodes (33): _news_subject(), _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr() (+25 more)

### Community 17 - "fund_rating_screen.py"
Cohesion: 0.06
Nodes (47): categories_for(), metal_scheme_categories(), _add_category_comparison(), _allocation_mix_spec(), _amc_matches(), _amc_outside_label(), _amc_token(), _apply_category_difference() (+39 more)

### Community 18 - "QueryLogger"
Cohesion: 0.09
Nodes (11): compose_fund_insight(), _fallback_summary(), _format_event_block(), _sources_from_events(), slots_from_plan(), clip_log_text(), _kv(), QueryLogger (+3 more)

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (39): _article_context_for_interpret(), measured_facts_block(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority() (+31 more)

### Community 20 - "time"
Cohesion: 0.04
Nodes (39): _backoff(), _consent_jar(), fetch_url(), _handle_google_response(), make_session(), post_url(), _proxy(), _retry_after_seconds() (+31 more)

### Community 21 - "investor_subject.py"
Cohesion: 0.05
Nodes (64): _amc_token_set(), question_is_standalone_macro(), _categories_equivalent(), _amc_token_in_question(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_deictic_and_memory_primary_fund() (+56 more)

### Community 22 - "test_call_json_llm.py"
Cohesion: 0.15
Nodes (17): extract_anthropic_text(), extract_assistant_text(), extract_gemini_text(), _json_balance(), parse_json_from_text(), _plain_answer_from_reasoning(), salvage_truncated_json(), _loads_closed() (+9 more)

### Community 23 - "scrape_bodies.py"
Cohesion: 0.07
Nodes (33): Publisher, SectorQuery, Settings, _merge_publisher_error_reasons(), write_day_report(), _atomic_write(), day_failure_slices_for_run(), ensure_loaded() (+25 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.11
Nodes (43): build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+35 more)

### Community 25 - "category_plan.py"
Cohesion: 0.06
Nodes (43): asks_category_performance(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), asks_cross_category_compare(), asks_fund_holdings_followup(), _category_for_alternate_plan(), _category_from_memory_cursor() (+35 more)

### Community 26 - "test_fund_display_tables.py"
Cohesion: 0.09
Nodes (25): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_markdown_tables_from_prose() (+17 more)

### Community 27 - "ensure_registry"
Cohesion: 0.07
Nodes (51): _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), EvidenceItem, _extract_funds_from_result(), gather_evidence(), GatherContext (+43 more)

### Community 28 - "resolve_fund_for_query"
Cohesion: 0.11
Nodes (24): is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), prefer_resolved_fund_name(), resolve_fund_for_query(), resolve_fund_from_question(), _resolved_scheme_for_portfolio_ask() (+16 more)

### Community 29 - "fields.py"
Cohesion: 0.12
Nodes (21): _asks_book(), bind_fields_to_tools(), _book_fields(), canonicalize_field(), field_need(), field_prompt_table(), FieldNeed, fields_from_question() (+13 more)

### Community 30 - "fund_brief.py"
Cohesion: 0.11
Nodes (27): _article_entities(), build_events(), cluster_articles(), _cluster_entities(), _day_key(), _empty_brief(), _exposure_for_holding(), _exposure_for_sector() (+19 more)

### Community 31 - "node_compose"
Cohesion: 0.10
Nodes (30): strip_grounding_holes(), _drop_scheme_is_the_whole_book(), node_compose(), cores_for_float(), cores_in_text(), derived_cores(), finalize_text_fields(), investor_book_cores() (+22 more)

### Community 32 - "executor.py"
Cohesion: 0.08
Nodes (34): detail_has_live_facts(), fetch_fund_managers_for_query(), _bullion_articles(), _bullion_topics(), _capability_cache_key(), _compare_cache_label(), _conversation_id(), _conversation_turn() (+26 more)

### Community 33 - "get_settings"
Cohesion: 0.08
Nodes (50): ask(), ask_stream(), AskRequest, _attach_llm_meta(), _crn_for_ask(), fund_brief(), health(), get_settings() (+42 more)

### Community 34 - "get_sector_fund_ranking_index"
Cohesion: 0.06
Nodes (40): question_needs_affected_sectors(), execute_wave(), get_sector_fund_ranking_index(), _args_from_question(), asks_funds_with_sector_exposure(), _clean_stock_capture(), _exposure_ask(), _heavy_and_return() (+32 more)

### Community 35 - "update.py"
Cohesion: 0.13
Nodes (20): drop_old_turns(), compare_payload_matches_funds(), add_gist(), empty_frame(), empty_state(), expire_stale_entities(), push_fund(), stack_entry() (+12 more)

### Community 36 - "test_fund_payload_first.py"
Cohesion: 0.15
Nodes (14): exposure_from_detail(), fetch_public_rating(), headline_rating(), load_fund_risk(), pending_rating_line(), plan_wants_single_scheme_risk(), rating_api_data_is_null(), rating_for_request() (+6 more)

### Community 37 - "fund_context.py"
Cohesion: 0.04
Nodes (70): category_composition_plan_applies(), _bound_fund_name(), _resolve_funds(), resolve_deictic_fund_name(), resolve_user_named_fund_in_memory(), asks_these_equity_funds(), _canonical_chat_fund_name(), _chat_fund_mention_recency() (+62 more)

### Community 38 - "fund_type_name_spec"
Cohesion: 0.12
Nodes (14): _category_fund_name_spec(), fund_naming_clause(), _fund_type_in_name_clause(), fund_type_name_spec(), _label_in(), _looks_like_fund_list(), rating_screen_question(), _return_window() (+6 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.09
Nodes (44): asks_taxonomy(), parse_rating_screen(), _return_direction(), run_rating_list(), explicit_return_window(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap() (+36 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "sector_alignment.py"
Cohesion: 0.19
Nodes (11): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _clear_index_cache(), test_by_sector_keys_match_sector_queries_exactly(), test_every_sector_has_verified_ticker_field() (+3 more)

### Community 42 - "test_portfolio_startup_cache.py"
Cohesion: 0.14
Nodes (20): question_asks_category_book_share(), bind_cached_portfolio(), _catalog_fund_holdings_question(), ensure_tools_for_data_question(), finish_portfolio_plan_bind(), _investor_args(), _merge_fund(), question_mentions_own_book() (+12 more)

### Community 43 - "QuestionBrief"
Cohesion: 0.06
Nodes (41): analyst_should_run(), asks_market_briefing(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief(), _detect_direction() (+33 more)

### Community 44 - "get_macro_news"
Cohesion: 0.16
Nodes (13): _run_get_macro_news(), _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read() (+5 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "pack_sanitize.py"
Cohesion: 0.12
Nodes (19): append_investor_portfolio_overview_tables(), strip_unasked_scheme_names(), question_asks_all_schemes_in_answer(), question_wants_scheme_names(), _display_holding_row(), _enrich_investor_computed_fields(), _internal_contribution_row(), investor_holdings_for_display() (+11 more)

### Community 47 - "portfolio_news_impact.py"
Cohesion: 0.14
Nodes (16): _articles_from_pack(), build_portfolio_news_impact_dossier(), ensure_portfolio_news_impact_plan(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), question_is_portfolio_news_impact() (+8 more)

### Community 48 - "portfolio/cache.py"
Cohesion: 0.09
Nodes (26): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), find_cached_holdings(), get_normalized_portfolio(), peek_derived(), peek_portfolio() (+18 more)

### Community 49 - "GraphState"
Cohesion: 0.11
Nodes (23): _attach_conversation(), build_result(), _catalog_fanout_fund_names(), _conversation_id(), _ensure_portfolio_for_fund_news(), GraphState, _insight_headline_narrative(), _maybe_compare_funds_after_multi_screen() (+15 more)

### Community 50 - "app.py"
Cohesion: 0.09
Nodes (32): ask_memory(), ask_query_log(), ask_sources(), backfill_page(), backfill_start(), backfill_status(), backfill_stop(), BackfillRequest (+24 more)

### Community 51 - "gold_service.py"
Cohesion: 0.14
Nodes (17): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+9 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "nav_service.py"
Cohesion: 0.21
Nodes (11): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+3 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.11
Nodes (21): build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns(), normalize_vs_benchmark_payload() (+13 more)

### Community 55 - "contracts.py"
Cohesion: 0.04
Nodes (92): question_mentions_fund_scheme(), rating_list_plan(), rating_concept_plan(), asks_fund_category_average(), apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan() (+84 more)

### Community 56 - "build_evidence_pack"
Cohesion: 0.04
Nodes (46): ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), EvidencePack, EvidenceRow, LLMUsageRecord (+38 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "contracts.py"
Cohesion: 0.22
Nodes (11): asks_random_fund_compare(), enforce_user_authorized_funds_only(), fund_authorized_for_question(), _named_in_chat_turns(), plan_allows_server_fund_pick(), test_compare_both_still_rebinds_after_strip(), test_compare_these_two_funds_binds_chat_pair(), test_invented_funds_stripped_when_not_in_chat() (+3 more)

### Community 59 - "sector_query_for_label"
Cohesion: 0.13
Nodes (4): normalize_sector_label(), sector_query_for_label(), _sector_label_in_text(), SectorFundRankingIndex

### Community 60 - "embed.py"
Cohesion: 0.14
Nodes (9): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), embeddings_ready() (+1 more)

### Community 61 - "RequestTelemetry"
Cohesion: 0.13
Nodes (18): RequestTelemetry, strip_context_disclaimer(), _answer_stream_chunks(), _clean_answer(), Node, _plan_fetches_manager_roster(), stream_graph_pipeline(), event_answer_completed() (+10 more)

### Community 62 - "test_rupeestop_auth.py"
Cohesion: 0.12
Nodes (8): rupeestop_admin_request_headers(), _jwt(), test_admin_headers_include_bearer(), test_admin_headers_use_token_from_login(), test_bearer_prefers_auth_token_over_admin_token(), test_failed_login_keeps_previous_token(), test_non_admin_url_has_no_authorization(), test_valid_jwt_does_not_call_login()

### Community 63 - "domain_intake.py"
Cohesion: 0.15
Nodes (15): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+7 more)

### Community 64 - "bullion_retrieve.py"
Cohesion: 0.06
Nodes (21): _warmup_embeddings_background(), _run(), _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), embed_query() (+13 more)

### Community 65 - "owned_holding_names"
Cohesion: 0.17
Nodes (16): merge_fund_isins_map(), _all_holdings_metric_spec(), _fund_data_from_results(), _investor_holdings_rating_rows(), _metric_cell(), render_all_holdings_metric_table(), render_all_holdings_return_table(), render_all_holdings_sector_table() (+8 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "validate_capability_args"
Cohesion: 0.15
Nodes (12): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded() (+4 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.15
Nodes (14): _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), mentions_advice(), _tokens() (+6 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "universe.py"
Cohesion: 0.16
Nodes (17): resolve_allisin_holdings_path(), load_portfolio_universe(), _aliases_for(), build_holding_entities(), canonical_key(), _display_name(), _holding_query(), _industry_search_hint() (+9 more)

### Community 71 - "retrieve_scoped_news"
Cohesion: 0.09
Nodes (21): _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news(), _sector_entities() (+13 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.15
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "node_route"
Cohesion: 0.12
Nodes (13): blocked_reply(), asks_computed_illustration(), GraphUnavailable, node_route(), greeting_reply(), identity_reply(), _mirror_greeting(), test_fire_sip_plan_is_a_computed_illustration() (+5 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "stock_fund_ranking.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 77 - "lib/portfolio_scope.py"
Cohesion: 0.16
Nodes (18): build_portfolio_scope(), _clean_holding_tokens(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc() (+10 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 79 - "CapabilityCache"
Cohesion: 0.15
Nodes (4): CapabilityCache, _Entry, get_capability_cache(), test_capabilities_cache_stores_and_retrieves()

### Community 80 - "resolve_display_table_policy"
Cohesion: 0.12
Nodes (17): DisplayTablePolicy, filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark(), question_wants_concentration_tables(), question_wants_gold_table() (+9 more)

### Community 81 - "normalize.py"
Cohesion: 0.29
Nodes (13): aggregate_term_gains(), _allocation_block(), _apply_holding_values(), _first(), _holding_from_scheme(), normalize_workspace(), _num(), _pnl_summary_row() (+5 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.22
Nodes (22): _age(), _as_of(), _book_line(), _comparison_rows(), _composition_line(), _fund_line(), _fund_name(), _holding_row_for_plan() (+14 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "sector_fund_ranking.py"
Cohesion: 0.13
Nodes (13): classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path(), sector_ranking_data_available() (+5 more)

### Community 86 - "test_fund_risk.py"
Cohesion: 0.16
Nodes (20): asks_pillar_mark(), asks_pillar_structure(), asks_rating_concept(), asks_risk_trend_comparison(), ensure_risk_tools(), test_category_question_explains_the_ranges_without_a_tool_call(), test_fund_quality_question_maps_to_portfolio_quality_pillar(), test_general_pillar_max_question_uses_concept_brief() (+12 more)

### Community 87 - "test_fact_answer.py"
Cohesion: 0.16
Nodes (20): _asks_portfolio_rs_ratings(), field_answer_needs_composer(), _investor_holdings_rows(), is_pure_field_answer(), render_benchmark_comparison_table(), render_fact_answer(), render_investor_rs_ratings_table(), wants_comparison_table() (+12 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.17
Nodes (16): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+8 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 90 - "enrich_manager_payload"
Cohesion: 0.24
Nodes (9): build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_default_manager_answer_drops_former_managers(), test_enrich_filters_past_only(), test_infer_roster_focus_current_vs_past() (+1 more)

### Community 91 - "Any"
Cohesion: 0.12
Nodes (21): build_holding_overlap(), _clean_company_name(), _entry_matches_amc(), _entry_matches_query_scheme(), _expand_query_token(), _fund_context_for_managers(), _fund_text(), get_fund_benchmark() (+13 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "test_conversation_memory.py"
Cohesion: 0.16
Nodes (25): _load_planner_memory(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), append_chat_turn(), _fresh(), get_memory(), get_or_create(), reset_memory() (+17 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.07
Nodes (53): render_pillar_marks_table(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_cell(), _compare_header(), _complete_fund_row(), _complete_shown_funds(), _concentration_markdown() (+45 more)

### Community 96 - "datetime"
Cohesion: 0.15
Nodes (17): strip_empty_table_pointers(), _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows() (+9 more)

### Community 98 - "fund_risk.py"
Cohesion: 0.14
Nodes (9): asks_about_score_bands(), asks_hidden_rating(), asks_private_system(), asks_score_only(), asks_sebi_riskometer(), _ensure_risk_trend_plan(), include_drawdown_with_risk(), _is_band_definition() (+1 more)

### Community 99 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 100 - "layer_tools.py"
Cohesion: 0.15
Nodes (17): aggregate_sectors_from_holdings(), normalize_sector_row(), _run_get_market_snapshot(), _price_holdings(), _detail(), register_layer_tools(), run_fund_attribution_tool(), run_fund_portfolio() (+9 more)

### Community 102 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "_fund_performance_digest"
Cohesion: 0.38
Nodes (4): _fund_performance_digest(), prefers_planner_over_slot(), test_fund_news_does_not_force_planner(), test_performance_digest_from_snapshot()

### Community 106 - "sources/google_news.py"
Cohesion: 0.15
Nodes (15): fetch_entity_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url(), fetch_macro_items(), is_macro_match(), macro_fetch_entities(), canonical_url() (+7 more)

### Community 107 - "_normalize_fund_text"
Cohesion: 0.14
Nodes (14): _attach_trailing_product(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question() (+6 more)

### Community 108 - "re"
Cohesion: 0.15
Nodes (12): CategoryMatch, explanation_brief(), fund_type_for_category(), match_all_fund_types(), match_all_scheme_categories(), match_scheme_category(), _names_a_type(), _phrase_in() (+4 more)

### Community 109 - "sector_alignment.py"
Cohesion: 0.17
Nodes (13): clear_macro_impact_cache(), analyze_sector_block(), canonical_sector_for_holding(), holding_return_pct(), holdings_in_sector(), index_return_pct(), return_sign(), run_sector_holding_alignment() (+5 more)

### Community 110 - "rupeestop_auth.py"
Cohesion: 0.18
Nodes (15): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+7 more)

### Community 111 - ".lookup_extracted_fund"
Cohesion: 0.15
Nodes (4): FundIndex, _infer_category_and_type(), resolve_canonical_isin(), _sync_amc_prefix_from_catalog()

### Community 112 - "index_series.py"
Cohesion: 0.21
Nodes (10): nifty50_ticker(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns(), _read_cache(), scheme_benchmark_metadata(), worst_sector_by_return() (+2 more)

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "top_n_from_question"
Cohesion: 0.36
Nodes (5): top_n_from_question(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

### Community 117 - "strip_missing_data_caveats"
Cohesion: 0.17
Nodes (13): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings() (+5 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "aggregate_fund_holdings.py"
Cohesion: 0.20
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 121 - "investor_drawback.py"
Cohesion: 0.17
Nodes (16): attach_drawback_digest(), build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), _pretty_category(), question_asks_portfolio_level_drawdown() (+8 more)

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "test_guardrails_domain.py"
Cohesion: 0.20
Nodes (11): question_in_finance_scope(), check_guardrails(), financial_keyword_signal(), GuardrailResult, test_crude_why_not_misrouted_to_random_fund(), test_fund_question_still_passes(), test_hdfc_bank_passes_guardrails(), test_hdfc_bank_short_happening_passes() (+3 more)

### Community 124 - "test_composer_table_summaries.py"
Cohesion: 0.21
Nodes (9): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections() (+1 more)

### Community 125 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "test_portfolio_intents.py"
Cohesion: 0.15
Nodes (18): render_portfolio_fact(), _table(), _leave_tools_alone(), _set_investor_call(), plan_targets_catalog_on_holdings(), apply_portfolio_intent(), data_need_for(), modules_for() (+10 more)

### Community 128 - "test_multi_fact_fund.py"
Cohesion: 0.09
Nodes (23): drawdown_words(), _question_needs_drawdown(), _followup_modules(), asks_fund_risk(), has_second_part(), _wants_end_summary(), asks_one_figure(), ensure_multi_fact_tools() (+15 more)

### Community 129 - "test_portfolio_layer.py"
Cohesion: 0.09
Nodes (24): enforce_portfolio_scope(), get_active_crn(), set_active_crn(), portfolio_health_snapshot(), test_enforce_drawback_strips_catalog_and_adds_modules(), normalized_doc(), test_active_crn_reaches_a_worker_thread(), test_concentration_question_loads_stock_and_sector_data() (+16 more)

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

### Community 134 - "get_stock_profile"
Cohesion: 0.26
Nodes (4): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker()

### Community 135 - "macro_impact_map.py"
Cohesion: 0.23
Nodes (12): _rule_sector_picks(), canonical_direction_for_driver(), _document(), _driver_row(), list_macro_drivers(), macro_impact_entry(), macro_series_for_driver(), normalize_direction() (+4 more)

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
Cohesion: 0.06
Nodes (28): main(), main(), main(), fetch_fund(), load_done_isins(), load_isins(), main(), _pct() (+20 more)

### Community 141 - "test_answer_precision.py"
Cohesion: 0.17
Nodes (9): fact_values_already_stated(), question_wants_fact_table(), strip_meta_opening_heading(), _strip_unasked_closers(), test_fact_table_only_for_compare_or_an_explicit_list(), test_fact_table_skipped_when_prose_has_the_figure(), test_next_steps_and_summary_are_removed(), test_specific_lookup_has_no_default_table() (+1 more)

### Community 142 - "_run_screen_funds_by_exposure"
Cohesion: 0.11
Nodes (13): asks_rating_list(), fetch_category_ratings(), _attach_rs_rating_to_screen_rows(), _finalize_screen_payload(), _run_screen_funds_by_exposure(), _named_scheme_category(), test_category_rating_request_uses_admin_header(), test_finalize_screen_adds_returns_for_compare_question() (+5 more)

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

### Community 159 - "_return_slice_covers"
Cohesion: 0.10
Nodes (27): _compare_payload_matches_funds(), execute_capability(), _positive_ms(), _take_conversation_slice(), widen_portfolio_args(), clear_conversation(), note_cache(), recall_slice() (+19 more)

### Community 163 - "fund_match.py"
Cohesion: 0.13
Nodes (11): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+3 more)

### Community 170 - "fund_catalog.py"
Cohesion: 0.17
Nodes (17): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+9 more)

### Community 174 - "compare_evidence.py"
Cohesion: 0.27
Nodes (7): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 175 - "get_fund_index"
Cohesion: 0.15
Nodes (16): attach_screen_drawdown(), compare_drawdown_rows(), fetch_drawdown_periods(), fetch_trailing_drawdown(), load_fund_drawdown(), normalize_drawdown_payload(), _peer_average_for_period(), screen_drawdown_cell() (+8 more)

### Community 178 - "entity_candidates.py"
Cohesion: 0.25
Nodes (7): candidates_block(), entity_candidates(), _holding_candidates(), question_asks_compare_both_in_chat(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

### Community 179 - "test_glossary.py"
Cohesion: 0.16
Nodes (15): apply_pure_concept_plan(), question_is_pure_general_concept(), asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), meaning_reply(), _normalize_term(), test_all_holdings_metrics_adds_investor_tool() (+7 more)

### Community 180 - "test_call_json_llm.py"
Cohesion: 0.24
Nodes (9): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), test_ask_plan_keeps_rich_agent_fields(), test_cluster_prefers_larger_groups() (+1 more)

### Community 182 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 183 - "memory/__init__.py"
Cohesion: 0.22
Nodes (9): _store_turn_memory(), drain_cache_events(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens(), prompt_view() (+1 more)

### Community 184 - "test_holding_overlap.py"
Cohesion: 0.18
Nodes (8): _add_category_comparison(), _compare_brief_line(), _row_bits(), table_source(), test_fund_insights_category_average_reaches_the_composer_row(), test_table_source_includes_sebi_riskometer_from_risk_module(), test_table_source_keeps_pillar_marks_and_the_fetched_return(), test_table_source_lists_the_screen_rows()

### Community 185 - "test_macro_news_cache.py"
Cohesion: 0.19
Nodes (11): select_macro_for_question(), _digest(), test_banking_and_banks_are_one_search(), test_cache_searches_named_macro_parameters(), test_failed_refresh_keeps_the_previous_cache(), test_macro_news_is_reused_for_two_hours_then_overwritten(), fetch(), test_question_gets_two_articles_from_each_leading_section() (+3 more)

### Community 186 - "insight/portfolio_scope.py"
Cohesion: 0.24
Nodes (11): plan_targets_single_fund_measured_return(), _data_need_is_investor(), ensure_investor_portfolio_tool(), _has_investor_tool(), _investor_tool_args(), _modules_for_investor_plan(), _plan_wants_investor_book(), _planner_text() (+3 more)

### Community 187 - "validate_plan_tools"
Cohesion: 0.24
Nodes (8): _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question(), validate_plan_tools(), test_silver_price_tool_becomes_news(), test_validate_adds_risk_when_planner_only_portfolio_holdings()

### Community 188 - "contains_phrase"
Cohesion: 0.70
Nodes (3): _holding_mentioned(), matches_entity(), contains_phrase()

### Community 190 - "test_smart_fund_why.py"
Cohesion: 0.21
Nodes (4): canonical_facet(), test_composer_guardrails(), test_facet_alias_fund_facts_holdings(), test_streaming_sse_order()

### Community 191 - "question_is_bullion_metal_price_question"
Cohesion: 0.33
Nodes (6): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), test_bullion_plan_clears_memory_gold_etf(), test_bullion_vs_gold_etf_detection()

### Community 192 - "plan_system_prompt"
Cohesion: 0.23
Nodes (8): plan_system_prompt(), build_anthropic_messages_body(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), _body(), test_planner_and_composer_share_the_first_system_block(), test_tools_stay_available_when_there_is_no_shared_prefix()

### Community 193 - "test_one_rated_fund_per_category_does_not_fill_with_gold"
Cohesion: 1.00
Nodes (3): test_one_rated_fund_per_category_does_not_fill_with_gold(), fetch(), _row()

### Community 194 - "strip_missing_data_caveats"
Cohesion: 0.25
Nodes (6): strip_missing_data_caveats(), strip_private_leaks(), test_a_rating_pick_does_not_apologise_for_returns_or_pillars(), test_missing_apology_and_private_leak_are_removed(), test_strip_removes_risk_trend_apology(), test_a_gap_apology_is_removed_and_a_real_point_stays()

### Community 195 - "test_metal_fund_rating.py"
Cohesion: 0.29
Nodes (7): ensure_quality_fund_list(), _payload(), _rating(), test_gold_list_spreads_etf_and_fund_of_funds(), fetch(), test_named_gold_etf_is_not_a_category_list(), test_planner_gold_sector_screen_becomes_rating_list()

### Community 197 - "infer_fund_news_layers"
Cohesion: 0.31
Nodes (6): infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only(), test_overview_news_is_holdings_and_sectors()

### Community 198 - "rank_funds_by_sector_exposure"
Cohesion: 0.29
Nodes (6): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), rank_funds_by_sector_exposure()

### Community 199 - "news_insight_articles"
Cohesion: 0.22
Nodes (6): clean_news_insight(), complete_sentences(), is_article_only_news(), news_insight_articles(), strip_publisher(), test_news_insight_drops_publisher_clips_and_unrelated_articles()

### Community 200 - "rating_lead"
Cohesion: 0.27
Nodes (7): pillar_focus(), rating_lead(), _rating_lead_for_pack(), asks_manager_roster(), test_fund_manager_name_ask_is_not_fund_manager_pillar(), test_rating_lead_lists_every_mark_for_a_fund_question(), test_asks_manager_roster_not_pillar_score()

### Community 203 - "_return_slice_covers"
Cohesion: 0.29
Nodes (7): _return_slice_covers(), test_missing_window_is_not_covered(), test_wider_cached_fund_payload_covers_and_trims_to_the_ask(), _wide(), test_return_slice_requires_pillars_when_requested(), test_investor_holdings_cache_does_not_cover_pnl_summary_request(), test_market_snapshot_cache_does_not_cover_different_window()

### Community 204 - "extract.py"
Cohesion: 0.36
Nodes (5): _authors(), _clean(), extract_article(), _meta(), _meta_fallback()

### Community 206 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 207 - "normalize_rating"
Cohesion: 0.25
Nodes (5): normalize_rating(), _pillar_maximum(), _public_pillars(), test_api_label_is_kept_as_sent(), test_debt_pillar_max_uses_api_max_score_field()

### Community 208 - "_public_summary"
Cohesion: 0.32
Nodes (7): render_risk_lines(), _public_summary(), test_mixed_question_adds_risk_lines_to_the_note(), test_public_summary_keeps_pillar_marks_and_drops_inputs(), test_risk_answer_keeps_exposure_and_drops_sharpe(), test_score_question_names_the_pillars_without_their_numbers(), test_why_good_choice_uses_the_api_label_and_explains_the_ranges()

### Community 209 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 210 - "data_pack.py"
Cohesion: 0.32
Nodes (4): build_data_pack(), build(), _compact(), test_data_pack_groups_by_fund_and_hides_internal_fields()

### Community 211 - "collect_evidence_calendar_dates"
Cohesion: 0.29
Nodes (5): collect_evidence_calendar_dates(), add_article(), format_user_calendar_date(), _ordinal_day(), test_format_user_calendar_date_and_news_collection()

### Community 212 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1574 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `test_multi_fact_fund.py`, `test_portfolio_layer.py`, `test_fund_drawdown.py`, `query_log.py`, `test_answer_precision.py`, `plan.py`, `fund_rating_screen.py`, `QueryLogger`, `investor_subject.py`, `category_plan.py`, `fields.py`, `get_settings`, `update.py`, `test_fund_payload_first.py`, `fund_context.py`, `test_fund_rating_screen.py`, `test_portfolio_startup_cache.py`, `compare_evidence.py`, `pack_sanitize.py`, `portfolio_news_impact.py`, `GraphState`, `test_glossary.py`, `gold_service.py`, `contracts.py`, `build_evidence_pack`, `contracts.py`, `insight/portfolio_scope.py`, `validate_plan_tools`, `RequestTelemetry`, `question_is_bullion_metal_price_question`, `owned_holding_names`, `test_metal_fund_rating.py`, `news_insight_articles`, `resolve_display_table_policy`, `fact_answer.py`, `test_fund_risk.py`, `_attach_rs_ratings_to_screen`, `test_fact_answer.py`, `test_portfolio_allocation.py`, `test_conversation_memory.py`, `evidence_pack.py`, `datetime`, `fund_risk.py`, `investor_drawback.py`, `test_composer_table_summaries.py`, `test_portfolio_intents.py`?**
  _High betweenness centrality (0.111) - this node is a cross-community bridge._
- **Are the 72 inferred relationships involving `ExecutionPlan` (e.g. with `apply_concept_example_to_plan()` and `append_investor_portfolio_overview_tables()`) actually correct?**
  _`ExecutionPlan` has 72 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.08107448107448108 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ExecutionPlan` to `test_multi_fact_fund.py`, `test_portfolio_layer.py`, `test_fund_drawdown.py`, `plan.py`, `fund_rating_screen.py`, `investor_subject.py`, `category_plan.py`, `fields.py`, `_return_slice_covers`, `executor.py`, `get_sector_fund_ranking_index`, `update.py`, `test_fund_payload_first.py`, `fund_context.py`, `test_fund_rating_screen.py`, `test_portfolio_startup_cache.py`, `compare_evidence.py`, `portfolio_news_impact.py`, `GraphState`, `test_glossary.py`, `gold_service.py`, `contracts.py`, `build_evidence_pack`, `insight/portfolio_scope.py`, `validate_plan_tools`, `contracts.py`, `RequestTelemetry`, `question_is_bullion_metal_price_question`, `owned_holding_names`, `test_metal_fund_rating.py`, `news_insight_articles`, `resolve_display_table_policy`, `test_fund_risk.py`, `test_conversation_memory.py`, `datetime`, `fund_risk.py`, `investor_drawback.py`, `test_portfolio_intents.py`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `ToolCall` (e.g. with `execute_capability()` and `execute_wave()`) actually correct?**
  _`ToolCall` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09574468085106383 - nodes in this community are weakly interconnected._