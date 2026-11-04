# Graph Report - db_design_with_qdrant_locally  (2026-11-04)

## Corpus Check
- 464 files · ~829,209 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 4877 nodes · 15475 edges · 175 communities (149 shown, 26 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 738 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8672a174`
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
- question_intent.py
- insight/portfolio_scope.py
- grounding.py
- affected_sectors.py
- tool_runners.py
- Any
- sector_fund_ranking.py
- time
- article_quality.py
- fields.py
- fund_brief.py
- graph.py
- get_sector_fund_ranking_index
- AnswerMode
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
- Any
- typing
- build_fund_display_tables
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
- normalize_rs_label
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
- slots_from_plan
- execute_capability
- stock_fund_ranking.py
- nav_service.py
- concept_asks.py
- holding_attribution.py
- scrape-worker/src/index.ts
- node_compose
- normalize.py
- get_stock_profile
- validate_capability_args
- resolve_display_table_policy
- enrich_manager_payload
- format_inr
- env
- universe.py
- steps
- evidence_pack.py
- PublisherStats
- v2_scoring.py
- fund_search.py
- extract_top_holdings
- plan.py
- test_investor_grounding.py
- portfolio_bind.py
- run-daily-pipeline.sh
- env
- _attach_screen_facts
- strip_news_roundup
- news_digest.py
- build_derived_views
- test_news_only_answer.py
- ToolCall
- metals_spot_tables.py
- error_summary.py
- _run_screen_funds_by_exposure
- ExecutionPlan
- vitest
- Any
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
- fund_catalog.py
- test_market_sector_fund_pipeline.py
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
- _amc_outside_label
- build_holding_overlap
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
- _return_direction
- rag-api.js
- install.sh
- apply_planner_post_hooks
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- diagnose_lightsail_site.sh
- market_scope_entities

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 449 edges
2. `ToolCall` - 273 edges
3. `AnswerMode` - 137 edges
4. `get_settings()` - 137 edges
5. `QueryLogger` - 100 edges
6. `QuestionBrief` - 88 edges
7. `slot_route()` - 84 edges
8. `apply_planner_post_hooks()` - 84 edges
9. `Settings` - 83 edges
10. `node_compose()` - 80 edges

## Surprising Connections (you probably didn't know these)
- `test_category_avg_question_detected()` --calls--> `asks_fund_category_average()`  [EXTRACTED]
  tests/test_fund_rupeestop_metrics.py → news_rag/fund_rupeestop_metrics.py
- `test_a_question_does_not_keep_unasked_windows()` --calls--> `build_fund_display_tables()`  [EXTRACTED]
  tests/test_fund_display_tables.py → news_rag/insight/fund_display.py
- `test_holdings_table_column_order()` --calls--> `build_fund_display_tables()`  [EXTRACTED]
  tests/test_fund_display_tables.py → news_rag/insight/fund_display.py
- `test_short_comparison_requires_category_average()` --calls--> `build_fund_display_tables()`  [EXTRACTED]
  tests/test_fund_display_tables.py → news_rag/insight/fund_display.py
- `test_snapshot_shows_regular_expense_exit_load_and_aum()` --calls--> `build_fund_display_tables()`  [EXTRACTED]
  tests/test_fund_display_tables.py → news_rag/insight/fund_display.py

## Import Cycles
- None detected.

## Communities (175 total, 26 thin omitted)

### Community 0 - "logging"
Cohesion: 0.08
Nodes (49): get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate() (+41 more)

### Community 1 - "AnswerMode"
Cohesion: 0.03
Nodes (65): rating_list_plan(), rating_concept_plan(), _use_rating_concept(), EvidenceRow, LLMUsageRecord, PhaseRecord, QueryClass, ToolRecord (+57 more)

### Community 2 - "fetch.py"
Cohesion: 0.04
Nodes (38): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+30 more)

### Community 3 - "interpret.py"
Cohesion: 0.06
Nodes (68): Findings, FundFinding, SectorFinding, mentions_publication_date(), publication_date_keys(), _assemble(), _caveat(), check_composer_guardrails() (+60 more)

### Community 4 - "portfolio/cache.py"
Cohesion: 0.16
Nodes (15): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), get_normalized_portfolio(), peek_derived(), peek_portfolio(), preload_configured_portfolio() (+7 more)

### Community 5 - "category_plan.py"
Cohesion: 0.07
Nodes (44): CategoryMatch, match_all_scheme_categories(), match_scheme_category(), _names_a_type(), _phrase_in(), _spaced_category_words(), taxonomy_reply(), _anchor_rating_for_category() (+36 more)

### Community 6 - "news_pipeline/config.py"
Cohesion: 0.06
Nodes (19): Publisher, SectorQuery, _to_article(), EntityScore, StoredArticle, is_qdrant_cloud(), qdrant_host(), qdrant_summary() (+11 more)

### Community 7 - "test_portfolio_layer.py"
Cohesion: 0.10
Nodes (17): fetch_top_holdings(), project_concentration(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore (+9 more)

### Community 8 - "Settings"
Cohesion: 0.08
Nodes (34): Settings, _merge_publisher_error_reasons(), write_day_report(), _atomic_write(), day_failure_slices_for_run(), ensure_loaded(), _failures_dir(), flush() (+26 more)

### Community 9 - "news_dates.py"
Cohesion: 0.07
Nodes (36): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), repo_root(), article_in_fetch_window(), covered_calendar_days(), google_time_query() (+28 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (58): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+50 more)

### Community 11 - "gather.py"
Cohesion: 0.08
Nodes (48): _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext, LedgerEntry (+40 more)

### Community 12 - "embed_query"
Cohesion: 0.07
Nodes (21): _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news() (+13 more)

### Community 13 - "compute.py"
Cohesion: 0.08
Nodes (44): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+36 more)

### Community 14 - "QuestionBrief"
Cohesion: 0.06
Nodes (45): analyst_should_run(), asks_market_briefing(), asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief() (+37 more)

### Community 15 - "tools.py"
Cohesion: 0.09
Nodes (41): DataNeed, _active_sector_equity(), _articles_for_affected_question(), _as_date(), asks_equity_funds(), asks_fof_funds(), _broad_working_well_keys(), _catalog_candidates() (+33 more)

### Community 16 - "eval_basic_queries.py"
Cohesion: 0.18
Nodes (12): ensure_fund_concentration_plan(), _cases(), _check_plan(), _expects(), _live_plan(), main(), _modules(), _offline_plan() (+4 more)

### Community 17 - "sector_exposure_tables.py"
Cohesion: 0.22
Nodes (14): owned_holding_names(), _all_holdings_metric_spec(), _fund_data_from_results(), _investor_holdings_rating_rows(), _metric_cell(), render_all_holdings_metric_table(), render_all_holdings_return_table(), render_all_holdings_sector_table() (+6 more)

### Community 18 - "QueryLogger"
Cohesion: 0.09
Nodes (9): jev_filter_events(), ParsedQuery, clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest(), test_finish_writes_json_sidecar() (+1 more)

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (37): _article_context_for_interpret(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority(), _clean_claims() (+29 more)

### Community 20 - "question_intent.py"
Cohesion: 0.09
Nodes (24): asks_category_performance(), asks_fund_category_average(), plan_matches_intent(), prefers_planner_over_slot(), QuestionIntent, resolve_question_intent(), _top_n_from_question(), _asks_catalog_fund_performance() (+16 more)

### Community 21 - "insight/portfolio_scope.py"
Cohesion: 0.12
Nodes (28): attach_drawback_digest(), build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), _pretty_category(), question_signals_investor_book() (+20 more)

### Community 22 - "grounding.py"
Cohesion: 0.15
Nodes (20): cores_in_text(), derived_cores(), finalize_text_fields(), number_is_grounded(), numeric_core(), strip_media_attribution(), strip_ungrounded_numbers(), drop_decimal() (+12 more)

### Community 23 - "affected_sectors.py"
Cohesion: 0.15
Nodes (14): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+6 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.12
Nodes (42): _window_pct_from_nav_payload(), build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has() (+34 more)

### Community 25 - "Any"
Cohesion: 0.12
Nodes (5): detail_has_live_facts(), FundIndex, get_fund_benchmark(), _infer_category_and_type(), resolve_canonical_isin()

### Community 26 - "sector_fund_ranking.py"
Cohesion: 0.06
Nodes (21): normalize_sector_label(), _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), classify_sector_fund_purity(), _damerau() (+13 more)

### Community 27 - "time"
Cohesion: 0.11
Nodes (23): _take_conversation_slice(), widen_portfolio_args(), clear_conversation(), note_cache(), recall_slice(), recall_wider_portfolio(), remember_slice(), slice_key() (+15 more)

### Community 28 - "article_quality.py"
Cohesion: 0.12
Nodes (19): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+11 more)

### Community 29 - "fields.py"
Cohesion: 0.06
Nodes (60): _age(), _asks_portfolio_rs_ratings(), _book_line(), _comparison_rows(), _composition_line(), field_answer_needs_composer(), _fund_line(), _fund_name() (+52 more)

### Community 30 - "fund_brief.py"
Cohesion: 0.07
Nodes (51): build_portfolio_scope(), _clean_holding_tokens(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc() (+43 more)

### Community 31 - "graph.py"
Cohesion: 0.17
Nodes (14): RequestTelemetry, _answer_stream_chunks(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed(), event_phase_started(), event_quality_check() (+6 more)

### Community 32 - "get_sector_fund_ranking_index"
Cohesion: 0.08
Nodes (31): execute_wave(), get_sector_fund_ranking_index(), _clean_stock_capture(), phrase_is_mutual_fund_scheme(), phrase_looks_like_sector_reference(), screen_hints_from_question(), stock_name_from_question(), test_crude_increase_compound_question_screens_negatively_affected_funds() (+23 more)

### Community 33 - "AnswerMode"
Cohesion: 0.05
Nodes (60): asks_about_score_bands(), asks_pillar_mark(), asks_pillar_structure(), asks_rating_concept(), asks_risk_trend_comparison(), _ensure_pillar_rating_plan(), ensure_risk_tools(), _ensure_risk_trend_plan() (+52 more)

### Community 34 - "CapabilityCache"
Cohesion: 0.19
Nodes (5): CapabilityCache, _Entry, test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner()

### Community 35 - "market_pulse.py"
Cohesion: 0.06
Nodes (49): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), embed_query(), warmup_query_vectors(), _body(), grouped_news() (+41 more)

### Community 36 - "layer_tools.py"
Cohesion: 0.08
Nodes (31): nifty50_ticker(), aggregate_sectors_from_holdings(), extract_top_holdings(), extract_top_sectors(), normalize_sector_row(), _run_get_market_snapshot(), _run_get_portfolio_data(), _price_holdings() (+23 more)

### Community 37 - "plan_enforce.py"
Cohesion: 0.07
Nodes (49): _categories_equivalent(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_deictic_and_memory_primary_fund(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan(), ensure_deictic_fund_period_return_plan(), ensure_my_category_fund_investor_plan() (+41 more)

### Community 38 - "fund_rating_screen.py"
Cohesion: 0.13
Nodes (23): categories_for(), _alternate_row_excluded(), _apply_category_difference(), _best_label(), _catalog_name(), _difference_brief(), fetch_category_ratings(), _higher_pillars() (+15 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.12
Nodes (36): asks_taxonomy(), _keep_asked_return(), parse_rating_screen(), run_rating_list(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap(), fetch() (+28 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "executor.py"
Cohesion: 0.06
Nodes (44): merge_fund_insight_metrics(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _capability_cache_key(), _conversation_id(), _conversation_turn(), _detail_for_fund_tool() (+36 more)

### Community 42 - "fund_display.py"
Cohesion: 0.12
Nodes (28): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+20 more)

### Community 43 - "sources/google_news.py"
Cohesion: 0.11
Nodes (22): finish_run_logger(), fetch_entity_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url(), fetch_macro_items(), is_macro_match(), macro_fetch_entities() (+14 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.12
Nodes (20): _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), select_macro_for_question(), _slim_clusters() (+12 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "json"
Cohesion: 0.06
Nodes (35): _json_default(), safe_json_dumps(), _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins() (+27 more)

### Community 48 - "typing"
Cohesion: 0.07
Nodes (12): run_ask_engine(), stream_ask_engine(), embeddings_ready(), get_capability_cache(), run_insight_pipeline(), stream_insight_pipeline(), new_fund_brief_logger(), new_query_logger() (+4 more)

### Community 49 - "build_fund_display_tables"
Cohesion: 0.08
Nodes (28): assemble_fund_overview_answer(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers(), strip_markdown_tables_from_prose() (+20 more)

### Community 50 - "fund_context.py"
Cohesion: 0.14
Nodes (20): _resolve_funds(), resolve_deictic_fund_name(), compare_payload_matches_funds(), _frame_subjects(), fund_name_mentioned_in_memory(), isin_for_owned_holding(), last_fund_name_from_gists(), list_cursor_fund_name() (+12 more)

### Community 51 - "update.py"
Cohesion: 0.24
Nodes (11): add_gist(), empty_frame(), empty_state(), expire_stale_entities(), push_fund(), stack_entry(), _subject(), test_repeated_fund_mention_refreshes_entity_ttl() (+3 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "app.py"
Cohesion: 0.10
Nodes (30): ask_memory(), ask_sources(), _attach_llm_meta(), backfill_page(), backfill_start(), backfill_status(), backfill_stop(), BackfillRequest (+22 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (20): build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), normalize_category_average_returns(), normalize_vs_benchmark_payload(), _optional_number() (+12 more)

### Community 55 - "test_call_json_llm.py"
Cohesion: 0.13
Nodes (20): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), _layered_news_topics(), _client() (+12 more)

### Community 56 - "graph.py"
Cohesion: 0.07
Nodes (37): refetch_partial_fund_tools(), strip_context_disclaimer(), _attach_conversation(), build_result(), _clean_answer(), _conversation_id(), _ensure_portfolio_for_fund_news(), GraphState (+29 more)

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
Nodes (8): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), main()

### Community 61 - "normalize_rs_label"
Cohesion: 0.14
Nodes (16): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), pick_funds_by_label_cascade(), pick_rows_by_label_cascade() (+8 more)

### Community 62 - "portfolio/client.py"
Cohesion: 0.17
Nodes (11): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), PortfolioNotConfigured, PortfolioUpstreamError, rupeestop_admin_request_headers(), rupeestop_bearer_token() (+3 more)

### Community 63 - "re"
Cohesion: 0.07
Nodes (32): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+24 more)

### Community 64 - "resolve_fund_for_query"
Cohesion: 0.09
Nodes (26): fetch_fund_managers_for_query(), get_fund_index(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), prefer_resolved_fund_name(), resolve_fund_for_query() (+18 more)

### Community 65 - "gold_service.py"
Cohesion: 0.16
Nodes (16): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+8 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "portfolio_news_impact.py"
Cohesion: 0.15
Nodes (12): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _strip_book_concentration_tables() (+4 more)

### Community 68 - "macro_impact_map.py"
Cohesion: 0.21
Nodes (13): _rule_sector_picks(), _rule_sector_picks(), canonical_direction_for_driver(), _document(), _driver_row(), list_macro_drivers(), macro_impact_entry(), macro_series_for_driver() (+5 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "investor_drawback.py"
Cohesion: 0.11
Nodes (21): _fund_performance_digest(), question_asks_all_schemes_in_answer(), _display_holding_row(), _enrich_investor_computed_fields(), _internal_contribution_row(), investor_holdings_for_display(), merge_holding_pp_into_performance(), _num() (+13 more)

### Community 71 - "fund_risk.py"
Cohesion: 0.07
Nodes (33): asks_fund_risk(), asks_hidden_rating(), asks_private_system(), asks_score_only(), asks_sebi_riskometer(), blocked_reply(), exposure_from_detail(), fetch_public_rating() (+25 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "get_settings"
Cohesion: 0.06
Nodes (61): ask(), ask_stream(), AskRequest, health(), get_settings(), Settings, make_plan(), plan_system_prompt() (+53 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "FundUniverseAgent"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 77 - "fund_match.py"
Cohesion: 0.14
Nodes (10): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), _normalize_fund_text() (+2 more)

### Community 78 - "slots_from_plan"
Cohesion: 0.20
Nodes (11): asked_slots(), merge_planner_asked_facts(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), slots_from_plan(), _book() (+3 more)

### Community 79 - "execute_capability"
Cohesion: 0.29
Nodes (7): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), test_compare_conversation_cache_does_not_reuse_different_pair(), fake_compare(), test_compare_conversation_cache_hits_same_pair(), test_compare_payload_matches_funds()

### Community 80 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 81 - "nav_service.py"
Cohesion: 0.10
Nodes (25): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+17 more)

### Community 82 - "concept_asks.py"
Cohesion: 0.19
Nodes (15): apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), apply_pure_concept_plan(), question_is_pure_general_concept(), test_concept_example_plan_screen_fof() (+7 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "node_compose"
Cohesion: 0.11
Nodes (22): append_investor_portfolio_overview_tables(), _category_rows_from_investor(), _concentration_markdown(), _fmt_inr(), _fmt_pct(), _fmt_table_inr(), _pct_of_total(), _portfolio_concentration_report() (+14 more)

### Community 86 - "normalize.py"
Cohesion: 0.27
Nodes (13): _allocation_block(), _apply_holding_values(), _first(), _holding_from_scheme(), normalize_workspace(), _num(), _pnl_summary_row(), _prefer_xirr() (+5 more)

### Community 87 - "get_stock_profile"
Cohesion: 0.25
Nodes (4): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker()

### Community 88 - "validate_capability_args"
Cohesion: 0.10
Nodes (17): _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded(), test_vs_benchmark_module_is_not_replaced_by_snapshot() (+9 more)

### Community 89 - "resolve_display_table_policy"
Cohesion: 0.09
Nodes (21): DisplayTablePolicy, fact_values_already_stated(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark(), question_wants_concentration_tables() (+13 more)

### Community 90 - "enrich_manager_payload"
Cohesion: 0.18
Nodes (12): _rating_lead_for_pack(), asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score() (+4 more)

### Community 91 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "universe.py"
Cohesion: 0.10
Nodes (20): _holding_mentioned(), matches_entity(), load_portfolio_universe(), _aliases_for(), build_holding_entities(), _display_name(), _holding_query(), _industry_search_hint() (+12 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.07
Nodes (47): render_pillar_marks_table(), _add_category_comparison(), _attach_rs_ratings_to_screen(), _benchmark_lines_from_pack(), _compare_brief_line(), _compare_cell(), _compare_header(), _complete_fund_row() (+39 more)

### Community 97 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 98 - "fund_search.py"
Cohesion: 0.13
Nodes (21): get_amc_catalog(), load_fund_embedding_cache(), _amc_hints_from_tokens(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _entry_matches_amc() (+13 more)

### Community 99 - "extract_top_holdings"
Cohesion: 0.11
Nodes (18): normalize_holding_row(), strip_missing_data_caveats(), strip_private_leaks(), build_insight_links(), _fact(), _key(), _match(), _pct() (+10 more)

### Community 100 - "plan.py"
Cohesion: 0.07
Nodes (31): explanation_brief(), ScopeKind, asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), glossary_execution_plan(), meaning_reply(), _normalize_term() (+23 more)

### Community 101 - "test_investor_grounding.py"
Cohesion: 0.20
Nodes (9): strip_grounding_holes(), cores_for_float(), fund_portfolio_cores(), investor_book_cores(), _sample_book(), test_grounding_keeps_category_weight_in_prose(), test_investor_book_cores_includes_rounded_allocation_pct(), test_repair_fills_hollow_allocation_and_holding_bullets() (+1 more)

### Community 102 - "portfolio_bind.py"
Cohesion: 0.24
Nodes (8): question_asks_category_book_share(), bind_cached_portfolio(), ensure_tools_for_data_question(), finish_portfolio_plan_bind(), _investor_args(), _merge_fund(), question_mentions_own_book(), find_cached_holdings()

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "_attach_screen_facts"
Cohesion: 0.21
Nodes (9): screen_fact_names(), _attach_screen_facts(), test_any_fund_screen_keeps_requested_aum(), _detail(), test_screen_can_ask_for_several_facts(), test_screen_manager_name_and_experience_are_separate_facts(), test_screen_table_includes_aum(), test_screen_table_includes_manager_name_and_experience() (+1 more)

### Community 106 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 107 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 108 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 109 - "test_news_only_answer.py"
Cohesion: 0.31
Nodes (6): clean_news_insight(), is_article_only_news(), news_insight_articles(), strip_publisher(), test_news_insight_drops_publisher_clips_and_unrelated_articles(), test_news_plus_a_market_snapshot_stays_with_the_composer()

### Community 110 - "ToolCall"
Cohesion: 0.05
Nodes (39): ensure_rating_screen(), reroute_single_fund_risk_plan(), maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), ToolCall (+31 more)

### Community 111 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 112 - "error_summary.py"
Cohesion: 0.42
Nodes (5): _bucket(), _entity_names(), summarize_errors(), write_error_summary(), test_google_and_jev_errors_are_split_with_entities_and_dates()

### Community 113 - "_run_screen_funds_by_exposure"
Cohesion: 0.16
Nodes (15): _add_category_comparison(), _amc_matches(), asks_rating_list(), _cascade_labels_for_spec(), _execute_rating_list(), _install_suggestion_screen(), _keep(), _keep_followup_plan() (+7 more)

### Community 114 - "ExecutionPlan"
Cohesion: 0.11
Nodes (30): ExecutionPlan, _wants_end_summary(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings(), _ensure_portfolio_data_for_compare(), _ensure_portfolio_data_for_holdings(), ensure_whole_book_catalog_scope() (+22 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "Any"
Cohesion: 0.22
Nodes (12): _clean_company_name(), fetch_fund_managers_for_isin(), _fund_context_for_managers(), _fund_text(), _named_weights(), _normalize_manager_record(), _optional_number(), parse_fund_managers_from_api_payload() (+4 more)

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
Cohesion: 0.38
Nodes (3): build_data_pack(), build(), _compact()

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 124 - "sector_alignment.py"
Cohesion: 0.16
Nodes (14): sector_query_for_label(), clear_macro_impact_cache(), analyze_sector_block(), canonical_sector_for_holding(), holding_return_pct(), holdings_in_sector(), index_return_pct(), return_sign() (+6 more)

### Community 125 - "test_portfolio_startup_cache.py"
Cohesion: 0.17
Nodes (16): clear_cache_for_tests(), seed_portfolio_cache_for_tests(), PortfolioError, PortfolioUnavailable, test_executor_uses_workspace_sample_without_token(), test_executor_with_fixture(), _doc(), test_compare_binds_cached_large_cap() (+8 more)

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "fund_catalog.py"
Cohesion: 0.39
Nodes (6): AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix(), install_amc_catalog(), _prefixes_for_amc_header()

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
Cohesion: 0.27
Nodes (7): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_parse_tables_append_directive(), test_strip_empty_bold_sections()

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
Cohesion: 0.27
Nodes (6): infer_fund_news_layers(), asks_fund_related_news(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only()

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

### Community 146 - "build_holding_overlap"
Cohesion: 0.40
Nodes (4): build_holding_overlap(), _holding_overlap_key(), _detail(), test_overlap_uses_full_stock_list_and_skips_cash()

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

### Community 163 - "apply_planner_post_hooks"
Cohesion: 0.05
Nodes (52): _followup_modules(), tag_answer_parts(), has_second_part(), asks_these_equity_funds(), comparison_fund_names(), _filter(), fund_name_matches_category(), memory_funds_for_category() (+44 more)

### Community 174 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1422 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `AnswerMode`, `category_plan.py`, `test_composer_table_summaries.py`, `test_portfolio_layer.py`, `test_fund_drawdown.py`, `eval_basic_queries.py`, `sector_exposure_tables.py`, `question_intent.py`, `insight/portfolio_scope.py`, `time`, `fields.py`, `AnswerMode`, `apply_planner_post_hooks`, `plan_enforce.py`, `fund_rating_screen.py`, `test_fund_rating_screen.py`, `fund_display.py`, `fund_context.py`, `update.py`, `graph.py`, `gold_service.py`, `portfolio_news_impact.py`, `investor_drawback.py`, `fund_risk.py`, `get_settings`, `slots_from_plan`, `concept_asks.py`, `node_compose`, `resolve_display_table_policy`, `evidence_pack.py`, `plan.py`, `portfolio_bind.py`, `_attach_screen_facts`, `test_news_only_answer.py`, `ToolCall`, `test_portfolio_startup_cache.py`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `ExecutionPlan` (e.g. with `evaluate_wave2()` and `resolve_compare_fund_pair()`) actually correct?**
  _`ExecutionPlan` has 53 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.07544836116264687 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `get_settings` to `AnswerMode`, `interpret.py`, `portfolio/cache.py`, `test_portfolio_layer.py`, `gather.py`, `embed_query`, `compute.py`, `QuestionBrief`, `news_reader.py`, `insight/portfolio_scope.py`, `affected_sectors.py`, `tool_runners.py`, `sector_fund_ranking.py`, `fund_brief.py`, `get_sector_fund_ranking_index`, `market_pulse.py`, `plan_enforce.py`, `executor.py`, `json`, `typing`, `app.py`, `graph.py`, `embed.py`, `portfolio/client.py`, `gold_service.py`, `portfolio_news_impact.py`, `fund_match.py`, `execute_capability`, `stock_fund_ranking.py`, `node_compose`, `validate_capability_args`, `fund_search.py`, `plan.py`, `portfolio_bind.py`, `test_portfolio_startup_cache.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ToolCall` (e.g. with `_apply_planner_request()` and `_portfolio_call()`) actually correct?**
  _`ToolCall` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `AnswerMode` be split into smaller, more focused modules?**
  _Cohesion score 0.03415977961432507 - nodes in this community are weakly interconnected._