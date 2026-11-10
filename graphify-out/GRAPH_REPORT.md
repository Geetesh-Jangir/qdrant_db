# Graph Report - db_design_with_qdrant_locally  (2026-11-06)

## Corpus Check
- 492 files · ~851,303 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 5165 nodes · 16501 edges · 199 communities (164 shown, 35 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 637 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a395fe8d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- ToolCall
- market_pulse.py
- interpret.py
- portfolio/cache.py
- Settings
- NewsStore
- test_portfolio_layer.py
- bullion_retrieve.py
- news_dates.py
- test_fund_drawdown.py
- gather.py
- retrieve_scoped_news
- compute.py
- llm_client.py
- tools.py
- fund_display.py
- normalize_rs_label
- QueryLogger
- news_reader.py
- slot_route
- resolve_display_table_policy
- grounding.py
- typing
- tool_runners.py
- category_plan.py
- build_fund_display_tables
- investor_drawback.py
- resolve_fund_for_query
- fact_answer.py
- fund_brief.py
- node_compose
- investor_subject.py
- ask_plan.py
- execute_capability
- update.py
- layer_tools.py
- executor.py
- investor_subject.py
- test_fund_rating_screen.py
- env
- ensure_risk_tools
- QuestionBrief
- get_sector_fund_ranking_index
- macro_news_cache.py
- env
- json
- contracts.py
- fund_rating_screen.py
- universe.py
- app.py
- gold_service.py
- env
- test_return_windows.py
- fund_rupeestop_metrics.py
- parse_plan
- question_intent.py
- scrape-worker/package.json
- macro_news.py
- article_quality.py
- embed.py
- RequestTelemetry
- insight/portfolio_scope.py
- re
- top_n_from_question
- validate_plan_tools
- batch.ts
- fund_universe_agent.py
- insight/guardrails.py
- http-fetch.ts
- evidence.py
- test_holding_overlap.py
- holdings_market.py
- node_route
- with
- FundUniverseAgent
- fund_search.py
- fund_risk.py
- lib/portfolio_scope.py
- stock_fund_ranking.py
- format_inr
- nav_service.py
- holding_attribution.py
- scrape-worker/src/index.ts
- sector_fund_ranking.py
- normalize.py
- shared_system_prefix
- glossary.py
- fund_match.py
- enrich_manager_payload
- validate_capability_args
- env
- ToolCall
- steps
- evidence_pack.py
- fund_search.py
- infer_fund_news_layers
- investor_drawback.py
- question_is_bullion_metal_price_question
- v2_scoring.py
- insight_links.py
- rank_funds_by_sector_exposure
- run-daily-pipeline.sh
- env
- nse_sector_indices.py
- portfolio_news_impact.py
- test_guardrails_domain.py
- build_derived_views
- SectorFundRankingIndex
- test_answer_precision.py
- metals_spot_tables.py
- get_stock_profile
- news_digest.py
- EntityFunnel
- vitest
- entity_candidates.py
- test_fund_risk.py
- compilerOptions
- compilerOptions
- EvidencePack
- RunLogger
- backfill
- portfolio/client.py
- test_composer_table_summaries.py
- fact_slots.py
- run-pipeline
- prompts.py
- PortfolioError
- query_log.py
- worker/src/index.ts
- steps
- steps
- with
- query_plan.py
- GoogleCircuitBreaker
- inputs
- with
- inputs
- build_evidence_pack
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
- install.sh
- asks_sebi_riskometer
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_catalog.py
- diagnose_lightsail_site.sh
- compare_evidence.py
- GraphUnavailable
- fetch_category_ratings
- normalize_user_facing_text
- ExecutionPlan
- asks_computed_illustration
- contains_phrase
- test_news_only_answer.py
- json_util.py
- run_graph
- _apply_category_difference
- test_portfolio_layer.py
- explicit_fund_count
- contracts.py
- _fund_type_in_name_clause
- planner_catalog_knowledge.py
- test_snapshot_uses_payload_returns_and_history_only_for_gaps
- slot_router.py
- _return_direction

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 498 edges
2. `ToolCall` - 307 edges
3. `get_settings()` - 136 edges
4. `AnswerMode` - 118 edges
5. `apply_planner_post_hooks()` - 106 edges
6. `QueryLogger` - 100 edges
7. `QuestionBrief` - 88 edges
8. `node_compose()` - 85 edges
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
- `test_investor_holdings_cache_does_not_cover_pnl_summary_request()` --calls--> `_return_slice_covers()`  [EXTRACTED]
  tests/test_tool_cache_covers.py → news_rag/insight/capabilities/executor.py

## Import Cycles
- None detected.

## Communities (199 total, 35 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (50): get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate() (+42 more)

### Community 1 - "ToolCall"
Cohesion: 0.05
Nodes (56): rating_list_plan(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), AnswerMode, Wave2Policy, sector_focus_from_market(), ensure_compare_template() (+48 more)

### Community 2 - "market_pulse.py"
Cohesion: 0.06
Nodes (48): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), embed_query(), _body(), grouped_news(), NewsTarget (+40 more)

### Community 3 - "interpret.py"
Cohesion: 0.06
Nodes (71): Findings, FundFinding, SectorFinding, _assemble(), _caveat(), check_composer_guardrails(), _claim_for_sector(), _claim_map() (+63 more)

### Community 4 - "portfolio/cache.py"
Cohesion: 0.17
Nodes (16): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), get_normalized_portfolio(), peek_derived(), peek_portfolio(), preload_configured_portfolio() (+8 more)

### Community 5 - "Settings"
Cohesion: 0.04
Nodes (47): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+39 more)

### Community 6 - "NewsStore"
Cohesion: 0.06
Nodes (26): _entity_refs(), _log_scrape_record(), _scrape(), scrape_bodies(), _drop(), is_qdrant_cloud(), qdrant_host(), qdrant_summary() (+18 more)

### Community 7 - "test_portfolio_layer.py"
Cohesion: 0.14
Nodes (7): trim_news_grouped(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore

### Community 8 - "bullion_retrieve.py"
Cohesion: 0.11
Nodes (9): _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), corpus_entity_names(), describe_filters_for_log(), _point_row() (+1 more)

### Community 9 - "news_dates.py"
Cohesion: 0.05
Nodes (38): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), Publisher, repo_root(), SectorQuery, article_in_fetch_window() (+30 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (57): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+49 more)

### Community 11 - "gather.py"
Cohesion: 0.12
Nodes (26): _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext, LedgerEntry (+18 more)

### Community 12 - "retrieve_scoped_news"
Cohesion: 0.20
Nodes (11): _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news(), _sector_entities() (+3 more)

### Community 13 - "compute.py"
Cohesion: 0.08
Nodes (46): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+38 more)

### Community 14 - "llm_client.py"
Cohesion: 0.07
Nodes (43): ask(), ask_stream(), AskRequest, health(), _warmup_embeddings_background(), _run(), get_settings(), Settings (+35 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (53): extract_top_holdings(), extract_top_sectors(), DataNeed, rank_funds_by_sector_exposure(), _active_sector_equity(), _articles_for_affected_question(), _as_date(), asks_equity_funds() (+45 more)

### Community 16 - "fund_display.py"
Cohesion: 0.10
Nodes (28): append_news_section(), _as_float(), _assess_table_quality(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+20 more)

### Community 17 - "normalize_rs_label"
Cohesion: 0.14
Nodes (16): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), pick_funds_by_label_cascade(), pick_rows_by_label_cascade() (+8 more)

### Community 18 - "QueryLogger"
Cohesion: 0.08
Nodes (23): slots_from_plan(), _blocks_to_parts(), _call_anthropic(), _call_deepseek(), _call_gemini(), _call_insight_llm_body(), call_json_llm(), _invoke() (+15 more)

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (38): _article_context_for_interpret(), measured_facts_block(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority() (+30 more)

### Community 20 - "slot_route"
Cohesion: 0.16
Nodes (17): execute_wave(), slot_route(), asks_funds_holding_stock(), _clean_stock_capture(), stock_name_from_question(), test_crude_increase_compound_question_screens_negatively_affected_funds(), test_driver_exposure_screen_no_longer_needs_sector_picks_first(), test_fund_manager_isin_in_question_routes_data_only() (+9 more)

### Community 21 - "resolve_display_table_policy"
Cohesion: 0.12
Nodes (17): DisplayTablePolicy, filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark(), question_wants_concentration_tables(), question_wants_gold_table() (+9 more)

### Community 22 - "grounding.py"
Cohesion: 0.07
Nodes (33): analyst_should_run(), asks_market_briefing(), add_article(), cores_in_text(), finalize_text_fields(), format_user_calendar_date(), mentions_publication_date(), number_is_grounded() (+25 more)

### Community 23 - "typing"
Cohesion: 0.06
Nodes (42): Settings, _merge_publisher_error_reasons(), write_day_report(), _bucket(), _entity_names(), summarize_errors(), write_error_summary(), _atomic_write() (+34 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.07
Nodes (57): aggregate_sectors_from_holdings(), build_holding_overlap(), normalize_sector_row(), _window_pct_from_nav_payload(), _price_holdings(), _detail(), register_layer_tools(), run_fund_attribution_tool() (+49 more)

### Community 25 - "category_plan.py"
Cohesion: 0.06
Nodes (49): categories_for(), CategoryMatch, explanation_brief(), match_all_scheme_categories(), match_scheme_category(), _names_a_type(), _phrase_in(), _spaced_category_words() (+41 more)

### Community 26 - "build_fund_display_tables"
Cohesion: 0.09
Nodes (27): assemble_fund_overview_answer(), build_fund_display_tables(), format_display_tables_markdown(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers(), strip_markdown_tables_from_prose(), strip_news_roundup() (+19 more)

### Community 27 - "investor_drawback.py"
Cohesion: 0.18
Nodes (16): attach_drawback_digest(), build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), _pretty_category(), question_asks_portfolio_level_drawdown() (+8 more)

### Community 28 - "resolve_fund_for_query"
Cohesion: 0.10
Nodes (24): is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), resolve_fund_for_query(), resolve_fund_from_question(), planner_supplement_for_question(), test_absl_and_ppfas_shorthand() (+16 more)

### Community 29 - "fact_answer.py"
Cohesion: 0.06
Nodes (60): periods_requested_in_question(), _age(), _asks_portfolio_rs_ratings(), _book_line(), _comparison_rows(), _composition_line(), field_answer_needs_composer(), _fund_line() (+52 more)

### Community 30 - "fund_brief.py"
Cohesion: 0.10
Nodes (31): _article_entities(), build_events(), cluster_articles(), _cluster_entities(), compose_fund_insight(), _day_key(), _empty_brief(), _exposure_for_holding() (+23 more)

### Community 31 - "node_compose"
Cohesion: 0.08
Nodes (24): append_investor_portfolio_overview_tables(), _fmt_inr(), render_investor_concentration_answer(), repair_investor_insight_prose(), strip_grounding_holes(), _compose_hints(), _drop_scheme_is_the_whole_book(), node_compose() (+16 more)

### Community 32 - "investor_subject.py"
Cohesion: 0.07
Nodes (42): _categories_equivalent(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_investor_holding_subject(), ensure_my_category_fund_investor_plan(), ensure_my_holding_fund_scope(), holdings_rows_from_investor_tool_results(), investor_holding_for_category() (+34 more)

### Community 33 - "ask_plan.py"
Cohesion: 0.16
Nodes (17): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), _client(), _gemini_response() (+9 more)

### Community 34 - "execute_capability"
Cohesion: 0.08
Nodes (18): CapabilityCache, _Entry, get_capability_cache(), _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), test_compare_conversation_cache_does_not_reuse_different_pair(), fake_compare() (+10 more)

### Community 35 - "update.py"
Cohesion: 0.14
Nodes (19): drop_old_turns(), compare_payload_matches_funds(), add_gist(), empty_frame(), empty_state(), expire_stale_entities(), push_fund(), stack_entry() (+11 more)

### Community 36 - "layer_tools.py"
Cohesion: 0.20
Nodes (12): nifty50_ticker(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns(), _read_cache(), scheme_benchmark_metadata(), _write_cache() (+4 more)

### Community 37 - "executor.py"
Cohesion: 0.05
Nodes (47): _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _capability_cache_key(), _conversation_id(), _conversation_turn(), _detail_for_fund_tool(), _one_fund() (+39 more)

### Community 38 - "investor_subject.py"
Cohesion: 0.06
Nodes (50): _amc_token_set(), _bound_fund_name(), _resolve_funds(), enforce_deictic_and_memory_primary_fund(), ensure_deictic_fund_period_return_plan(), question_asks_catalog_fund_list(), question_asks_fund_measured_return(), question_refers_deictic_fund() (+42 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.11
Nodes (39): asks_taxonomy(), parse_rating_screen(), run_rating_list(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap(), fetch(), test_a_one_month_performer_is_shown_beside_the_same_category_rating() (+31 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "ensure_risk_tools"
Cohesion: 0.09
Nodes (21): asks_about_score_bands(), asks_pillar_mark(), asks_pillar_structure(), asks_rating_concept(), asks_risk_trend_comparison(), ensure_risk_tools(), _ensure_risk_trend_plan(), _is_band_definition() (+13 more)

### Community 42 - "QuestionBrief"
Cohesion: 0.05
Nodes (57): asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief(), _detect_direction(), _detect_funds() (+49 more)

### Community 43 - "get_sector_fund_ranking_index"
Cohesion: 0.08
Nodes (29): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+21 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.10
Nodes (23): _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), _search_macro_parameters() (+15 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "json"
Cohesion: 0.05
Nodes (39): portfolio_health_snapshot(), _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding() (+31 more)

### Community 47 - "contracts.py"
Cohesion: 0.09
Nodes (21): LLMUsageRecord, PhaseRecord, ToolRecord, ensure_fund_concentration_plan(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), _holdings_breakdown_question() (+13 more)

### Community 48 - "fund_rating_screen.py"
Cohesion: 0.10
Nodes (35): _add_category_comparison(), _alternate_row_excluded(), _amc_matches(), _amc_outside_label(), _amc_token(), asks_rating_list(), _best_label(), _cascade_labels_for_spec() (+27 more)

### Community 49 - "universe.py"
Cohesion: 0.16
Nodes (17): resolve_allisin_holdings_path(), load_portfolio_universe(), _aliases_for(), build_holding_entities(), canonical_key(), _display_name(), _holding_query(), _industry_search_hint() (+9 more)

### Community 50 - "app.py"
Cohesion: 0.14
Nodes (25): ask_memory(), ask_query_log(), ask_sources(), _attach_llm_meta(), backfill_page(), backfill_start(), backfill_status(), backfill_stop() (+17 more)

### Community 51 - "gold_service.py"
Cohesion: 0.09
Nodes (24): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+16 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "test_return_windows.py"
Cohesion: 0.18
Nodes (14): _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows(), window_label() (+6 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (21): asks_fund_category_average(), build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns() (+13 more)

### Community 55 - "parse_plan"
Cohesion: 0.15
Nodes (13): _apply_planner_request(), _example_part(), _label_for_days(), parse_plan(), _pick_enum(), _planner_fields(), _str_list(), test_parse_plan_reads_the_memory_pointers() (+5 more)

### Community 56 - "question_intent.py"
Cohesion: 0.11
Nodes (17): prefers_planner_over_slot(), QuestionIntent, resolve_question_intent(), _top_n_from_question(), _asks_catalog_fund_performance(), _asks_fund_manager(), _extract_fund_names(), asks_fund_related_news() (+9 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "macro_news.py"
Cohesion: 0.50
Nodes (3): fetch_macro_items(), is_macro_match(), macro_fetch_entities()

### Community 59 - "article_quality.py"
Cohesion: 0.11
Nodes (17): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+9 more)

### Community 60 - "embed.py"
Cohesion: 0.14
Nodes (9): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), embeddings_ready() (+1 more)

### Community 61 - "RequestTelemetry"
Cohesion: 0.16
Nodes (14): RequestTelemetry, _answer_stream_chunks(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed(), event_phase_started(), event_quality_check() (+6 more)

### Community 62 - "insight/portfolio_scope.py"
Cohesion: 0.10
Nodes (24): plan_targets_single_fund_measured_return(), question_asks_holding_metric_and_glossary(), ensure_portfolio_news_impact_plan(), question_is_portfolio_news_impact(), _data_need_is_investor(), enforce_portfolio_scope(), ensure_investor_portfolio_tool(), _has_investor_tool() (+16 more)

### Community 63 - "re"
Cohesion: 0.13
Nodes (16): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+8 more)

### Community 64 - "top_n_from_question"
Cohesion: 0.36
Nodes (5): top_n_from_question(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

### Community 65 - "validate_plan_tools"
Cohesion: 0.11
Nodes (24): funds_from_shown_list(), merge_fund_isins_map(), owned_holding_names(), bind_shown_list_followup(), windows_named_in_question(), _add(), _all_holdings_metric_spec(), _fund_data_from_results() (+16 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "fund_universe_agent.py"
Cohesion: 0.15
Nodes (4): FundEntry, FundUniverseCatalog, _enrich(), match_fund_category()

### Community 68 - "insight/guardrails.py"
Cohesion: 0.13
Nodes (16): _amc_hints_from_tokens(), _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), mentions_advice() (+8 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "evidence.py"
Cohesion: 0.18
Nodes (14): _take_conversation_slice(), widen_portfolio_args(), clear_conversation(), note_cache(), recall_slice(), recall_wider_portfolio(), remember_slice(), slice_key() (+6 more)

### Community 71 - "test_holding_overlap.py"
Cohesion: 0.12
Nodes (13): _compare_brief_line(), extra_part_brief(), table_source(), _detail(), test_compare_table_includes_risk_for_both_funds(), test_extra_part_brief_names_both_funds(), test_no_overlap_message_and_overlap_table(), test_overlap_uses_full_stock_list_and_skips_cash() (+5 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "node_route"
Cohesion: 0.26
Nodes (8): greeting_reply(), identity_reply(), _mirror_greeting(), prompt_view(), test_fund_question_is_not_greeting_or_identity(), test_hello_mirrors_greeting(), test_main_memory_in_prompt_view(), test_who_are_you_identity()

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "FundUniverseAgent"
Cohesion: 0.18
Nodes (8): FundUniverseAgent, get_fund_universe_catalog(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question(), test_agent_query_gold_etfs(), test_catalog_loads_funds(), test_query_by_amc_and_category(), test_query_large_cap_funds()

### Community 77 - "fund_search.py"
Cohesion: 0.13
Nodes (17): _attach_trailing_product(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _entry_matches_query_scheme(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase() (+9 more)

### Community 78 - "fund_risk.py"
Cohesion: 0.14
Nodes (17): asks_fund_risk(), exposure_from_detail(), fetch_public_rating(), headline_rating(), load_fund_risk(), pending_rating_line(), _pillar_maximum(), plan_wants_single_scheme_risk() (+9 more)

### Community 79 - "lib/portfolio_scope.py"
Cohesion: 0.15
Nodes (18): build_portfolio_scope(), _clean_holding_tokens(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc() (+10 more)

### Community 80 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 81 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 82 - "nav_service.py"
Cohesion: 0.20
Nodes (12): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+4 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "sector_fund_ranking.py"
Cohesion: 0.13
Nodes (13): classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path(), sector_ranking_data_available() (+5 more)

### Community 86 - "normalize.py"
Cohesion: 0.33
Nodes (12): _allocation_block(), _apply_holding_values(), _first(), _holding_from_scheme(), normalize_workspace(), _num(), _pnl_summary_row(), _prefer_xirr() (+4 more)

### Community 87 - "shared_system_prefix"
Cohesion: 0.18
Nodes (9): anthropic_cache_control(), anthropic_system_blocks(), build_anthropic_messages_body(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), _body(), test_planner_and_composer_share_the_first_system_block() (+1 more)

### Community 88 - "glossary.py"
Cohesion: 0.21
Nodes (11): asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), glossary_execution_plan(), has_second_part(), meaning_reply(), _normalize_term(), test_fund_nav_not_glossary() (+3 more)

### Community 89 - "fund_match.py"
Cohesion: 0.11
Nodes (14): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+6 more)

### Community 90 - "enrich_manager_payload"
Cohesion: 0.18
Nodes (12): _rating_lead_for_pack(), asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score() (+4 more)

### Community 91 - "validate_capability_args"
Cohesion: 0.11
Nodes (17): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded() (+9 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "ToolCall"
Cohesion: 0.06
Nodes (48): ensure_rating_screen(), _followup_modules(), _install_suggestion_screen(), _keep_followup_plan(), _ensure_pillar_rating_plan(), ToolCall, ensure_screen_facts(), _bind_fund_list() (+40 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.08
Nodes (48): _add_category_comparison(), _attach_rs_ratings_to_screen(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_cell(), _compare_header(), _complete_fund_row(), _complete_shown_funds() (+40 more)

### Community 96 - "fund_search.py"
Cohesion: 0.09
Nodes (19): _clean_company_name(), detail_has_live_facts(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers(), _fund_text(), FundIndex, get_fund_benchmark() (+11 more)

### Community 97 - "infer_fund_news_layers"
Cohesion: 0.29
Nodes (5): infer_fund_news_layers(), _plan_fund_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only()

### Community 98 - "investor_drawback.py"
Cohesion: 0.13
Nodes (17): _fund_performance_digest(), _render_investor_holdings_table(), question_asks_all_schemes_in_answer(), _display_holding_row(), _enrich_investor_computed_fields(), _internal_contribution_row(), investor_holdings_for_display(), merge_holding_pp_into_performance() (+9 more)

### Community 99 - "question_is_bullion_metal_price_question"
Cohesion: 0.29
Nodes (7): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), node_resolve(), test_bullion_plan_clears_memory_gold_etf(), test_bullion_vs_gold_etf_detection()

### Community 100 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 101 - "insight_links.py"
Cohesion: 0.17
Nodes (13): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings() (+5 more)

### Community 102 - "rank_funds_by_sector_exposure"
Cohesion: 0.42
Nodes (5): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships()

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "nse_sector_indices.py"
Cohesion: 0.10
Nodes (25): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), clear_macro_impact_cache(), analyze_sector_block(), canonical_sector_for_holding() (+17 more)

### Community 106 - "portfolio_news_impact.py"
Cohesion: 0.09
Nodes (27): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _rule_sector_picks() (+19 more)

### Community 107 - "test_guardrails_domain.py"
Cohesion: 0.20
Nodes (11): question_in_finance_scope(), check_guardrails(), financial_keyword_signal(), GuardrailResult, test_crude_why_not_misrouted_to_random_fund(), test_fund_question_still_passes(), test_hdfc_bank_passes_guardrails(), test_hdfc_bank_short_happening_passes() (+3 more)

### Community 108 - "build_derived_views"
Cohesion: 0.14
Nodes (16): _catalog_fund_holdings_question(), ensure_tools_for_data_question(), question_mentions_own_book(), asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views() (+8 more)

### Community 109 - "SectorFundRankingIndex"
Cohesion: 0.15
Nodes (4): normalize_sector_label(), sector_query_for_label(), _sector_label_in_text(), SectorFundRankingIndex

### Community 110 - "test_answer_precision.py"
Cohesion: 0.17
Nodes (9): fact_values_already_stated(), question_wants_fact_table(), strip_meta_opening_heading(), _strip_unasked_closers(), test_fact_table_only_for_compare_or_an_explicit_list(), test_fact_table_skipped_when_prose_has_the_figure(), test_next_steps_and_summary_are_removed(), test_specific_lookup_has_no_default_table() (+1 more)

### Community 111 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 112 - "get_stock_profile"
Cohesion: 0.26
Nodes (4): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker()

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "entity_candidates.py"
Cohesion: 0.30
Nodes (6): candidates_block(), entity_candidates(), _holding_candidates(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

### Community 117 - "test_fund_risk.py"
Cohesion: 0.11
Nodes (24): asks_private_system(), blocked_reply(), normalize_rating(), render_pillar_marks_table(), render_risk_lines(), strip_missing_data_caveats(), strip_private_leaks(), test_a_rating_pick_does_not_apologise_for_returns_or_pillars() (+16 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "EvidencePack"
Cohesion: 0.20
Nodes (8): EvidencePack, test_compare_table_shows_the_drawdown_row(), test_screen_table_shows_the_drawdown_column(), test_expense_ratio_meaning_and_judgment_uses_composer(), test_render_drawback_includes_underperformers(), test_compact_strips_contribution_from_data_attribution(), test_sanitize_data_pack_moves_pp_to_internal(), test_returns_table_for_investor_pnl()

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "portfolio/client.py"
Cohesion: 0.20
Nodes (9): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), rupeestop_admin_request_headers(), rupeestop_bearer_token(), test_admin_headers_include_bearer(), test_bearer_prefers_auth_token_over_admin_token() (+1 more)

### Community 124 - "test_composer_table_summaries.py"
Cohesion: 0.18
Nodes (9): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections() (+1 more)

### Community 125 - "fact_slots.py"
Cohesion: 0.33
Nodes (6): asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), test_aum_slot_renders_from_snapshot()

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "prompts.py"
Cohesion: 0.29
Nodes (4): build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 128 - "PortfolioError"
Cohesion: 0.24
Nodes (8): PortfolioError, PortfolioNotConfigured, PortfolioUnavailable, PortfolioUpstreamError, test_preload_failure_returns_false(), boom(), test_stale_snapshot_does_not_wait_on_fetch(), slow()

### Community 129 - "query_log.py"
Cohesion: 0.08
Nodes (18): run_ask_engine(), stream_ask_engine(), run_graph_pipeline(), run_insight_pipeline(), stream_insight_pipeline(), ParsedQuery, attach_query_log_meta(), find_query_log_file() (+10 more)

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

### Community 137 - "inputs"
Cohesion: 0.29
Nodes (7): default, description, required, type, holdings_limit, workflow_dispatch, inputs

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "build_evidence_pack"
Cohesion: 0.10
Nodes (17): EvidenceRow, build_evidence_pack(), screen_fact_names(), test_good_choice_list_uses_the_funds_table(), test_any_fund_screen_keeps_requested_aum(), _detail(), test_incomplete_return_column_is_omitted(), test_screen_can_ask_for_several_facts() (+9 more)

### Community 141 - "test_conversation_memory.py"
Cohesion: 0.09
Nodes (46): _attach_conversation(), build_result(), _conversation_id(), _ensure_portfolio_for_fund_news(), GraphState, _load_planner_memory(), _maybe_compare_funds_after_multi_screen(), _maybe_enrich_picked_fund_from_screen() (+38 more)

### Community 142 - "test_metal_fund_rating.py"
Cohesion: 0.29
Nodes (7): ensure_quality_fund_list(), _payload(), _rating(), test_gold_list_spreads_etf_and_fund_of_funds(), fetch(), test_named_gold_etf_is_not_a_category_list(), test_planner_gold_sector_screen_becomes_rating_list()

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

### Community 163 - "asks_sebi_riskometer"
Cohesion: 0.25
Nodes (5): asks_hidden_rating(), asks_score_only(), asks_sebi_riskometer(), include_drawdown_with_risk(), test_sebi_risk_score_question_is_detected()

### Community 170 - "fund_catalog.py"
Cohesion: 0.14
Nodes (21): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+13 more)

### Community 174 - "compare_evidence.py"
Cohesion: 0.27
Nodes (7): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 179 - "normalize_user_facing_text"
Cohesion: 0.22
Nodes (6): ensure_markdown_table_spacing(), normalize_user_facing_text(), strip_context_disclaimer(), _clean_answer(), test_normalize_inserts_blank_line_before_markdown_table(), test_normalize_na_to_hyphen()

### Community 180 - "ExecutionPlan"
Cohesion: 0.05
Nodes (69): reroute_single_fund_risk_plan(), ensure_name_fund_type_plan(), ensure_rating_list_funds(), ExecutionPlan, merge_planner_asked_facts(), tag_answer_parts(), clarify_plan_if_fund_unknown(), _plan_uses_fund_scoped_tools() (+61 more)

### Community 181 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

### Community 182 - "contains_phrase"
Cohesion: 0.70
Nodes (3): _holding_mentioned(), matches_entity(), contains_phrase()

### Community 183 - "test_news_only_answer.py"
Cohesion: 0.22
Nodes (9): _news_subject(), clean_news_insight(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words(), test_news_about_hdfc_bank_is_not_a_market_pulse(), test_news_insight_drops_publisher_clips_and_unrelated_articles() (+1 more)

### Community 185 - "run_graph"
Cohesion: 0.67
Nodes (4): run_graph(), _state(), test_out_of_scope_question_ends_after_the_planner(), test_unmatched_fund_replies_without_calling_tools()

### Community 186 - "_apply_category_difference"
Cohesion: 0.50
Nodes (3): _apply_category_difference(), _difference_brief(), _user_named_funds()

### Community 187 - "test_portfolio_layer.py"
Cohesion: 0.14
Nodes (12): clear_cache_for_tests(), project_concentration(), normalized_doc(), test_concentration_keeps_cash(), test_current_value_and_nonzero_xirr(), test_executor_uses_workspace_sample_without_token(), test_executor_with_fixture(), test_holdings_table_uses_exact_value() (+4 more)

### Community 188 - "explicit_fund_count"
Cohesion: 0.08
Nodes (17): metal_scheme_categories(), _category_fund_name_spec(), _label_in(), _looks_like_fund_list(), _metal_fund_categories(), _metal_fund_spec(), _question_names_amc_scheme(), _return_window() (+9 more)

### Community 190 - "contracts.py"
Cohesion: 0.09
Nodes (28): fund_type_name_spec(), question_is_standalone_macro(), apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), apply_pure_concept_plan() (+20 more)

### Community 192 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 194 - "slot_router.py"
Cohesion: 0.06
Nodes (22): rating_concept_plan(), QueryClass, ScopeKind, _asks_driver_sector_or_fund_impact(), _extract_drivers(), _extract_fund_targets_for_manager(), _extract_stocks(), _get_top_n() (+14 more)

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1503 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `ToolCall`, `test_fund_drawdown.py`, `build_evidence_pack`, `test_conversation_memory.py`, `llm_client.py`, `test_metal_fund_rating.py`, `QueryLogger`, `slot_route`, `resolve_display_table_policy`, `category_plan.py`, `investor_drawback.py`, `fact_answer.py`, `node_compose`, `investor_subject.py`, `investor_subject.py`, `test_fund_rating_screen.py`, `ensure_risk_tools`, `QuestionBrief`, `compare_evidence.py`, `contracts.py`, `fund_rating_screen.py`, `gold_service.py`, `test_return_windows.py`, `parse_plan`, `question_intent.py`, `test_news_only_answer.py`, `article_quality.py`, `test_portfolio_layer.py`, `contracts.py`, `insight/portfolio_scope.py`, `validate_plan_tools`, `slot_router.py`, `test_holding_overlap.py`, `fund_risk.py`, `glossary.py`, `ToolCall`, `evidence_pack.py`, `infer_fund_news_layers`, `investor_drawback.py`, `question_is_bullion_metal_price_question`, `portfolio_news_impact.py`, `build_derived_views`, `test_answer_precision.py`, `test_fund_risk.py`, `EvidencePack`, `test_composer_table_summaries.py`, `fact_slots.py`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `ExecutionPlan` (e.g. with `evaluate_wave2()` and `apply_concept_example_to_plan()`) actually correct?**
  _`ExecutionPlan` has 42 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.07188118811881188 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ToolCall` to `ToolCall`, `test_fund_drawdown.py`, `build_evidence_pack`, `test_conversation_memory.py`, `test_metal_fund_rating.py`, `slot_route`, `resolve_display_table_policy`, `category_plan.py`, `investor_drawback.py`, `fact_answer.py`, `investor_subject.py`, `execute_capability`, `update.py`, `executor.py`, `investor_subject.py`, `test_fund_rating_screen.py`, `ensure_risk_tools`, `QuestionBrief`, `compare_evidence.py`, `contracts.py`, `fund_rating_screen.py`, `gold_service.py`, `ExecutionPlan`, `test_return_windows.py`, `parse_plan`, `test_news_only_answer.py`, `run_graph`, `article_quality.py`, `test_portfolio_layer.py`, `contracts.py`, `insight/portfolio_scope.py`, `validate_plan_tools`, `slot_router.py`, `test_holding_overlap.py`, `fund_risk.py`, `infer_fund_news_layers`, `question_is_bullion_metal_price_question`, `portfolio_news_impact.py`, `build_derived_views`, `test_fund_risk.py`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Should `ToolCall` be split into smaller, more focused modules?**
  _Cohesion score 0.04519918283963228 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `llm_client.py` to `query_log.py`, `market_pulse.py`, `interpret.py`, `portfolio/cache.py`, `test_portfolio_layer.py`, `bullion_retrieve.py`, `gather.py`, `compute.py`, `test_conversation_memory.py`, `tools.py`, `QueryLogger`, `news_reader.py`, `slot_route`, `fund_brief.py`, `node_compose`, `investor_subject.py`, `execute_capability`, `executor.py`, `investor_subject.py`, `QuestionBrief`, `get_sector_fund_ranking_index`, `json`, `app.py`, `gold_service.py`, `ExecutionPlan`, `embed.py`, `insight/portfolio_scope.py`, `slot_router.py`, `fund_search.py`, `stock_fund_ranking.py`, `sector_fund_ranking.py`, `fund_match.py`, `validate_capability_args`, `portfolio_news_impact.py`, `build_derived_views`, `portfolio/client.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._