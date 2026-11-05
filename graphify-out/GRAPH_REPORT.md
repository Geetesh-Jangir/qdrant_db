# Graph Report - db_design_with_qdrant_locally  (2026-11-05)

## Corpus Check
- 489 files · ~845,469 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 5070 nodes · 16217 edges · 193 communities (162 shown, 31 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 640 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a4d15efb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- re
- fund_context.py
- interpret.py
- portfolio/cache.py
- Settings
- NewsStore
- test_portfolio_layer.py
- parse.py
- news_dates.py
- test_fund_drawdown.py
- gather.py
- query_plan.py
- compute.py
- test_holding_overlap.py
- tools.py
- build_fund_display_tables
- normalize_rs_label
- QueryLogger
- news_reader.py
- resolve_display_table_policy
- universe.py
- test_ask_speed.py
- .lookup_extracted_fund
- tool_runners.py
- category_plan.py
- get_sector_fund_ranking_index
- test_conversation_memory.py
- fund_search.py
- fields.py
- fund_brief.py
- graph.py
- investor_subject.py
- owned_holding_names
- execute_capability
- planner_policy.py
- layer_tools.py
- executor.py
- lib/google_news.py
- test_fund_rating_screen.py
- env
- plan_enforce.py
- brief.py
- test_fund_display_tables.py
- macro_news_cache.py
- env
- json
- portfolio_plan.py
- primary_fund_name
- lib/portfolio_scope.py
- app.py
- contracts.py
- env
- test_return_windows.py
- fund_rupeestop_metrics.py
- fact_answer.py
- _run_get_fund_data
- scrape-worker/package.json
- test_call_json_llm.py
- re
- embed.py
- aggregate_fund_holdings.py
- glossary.py
- re
- get_fund_index
- gold_service.py
- batch.ts
- test_portfolio_startup_cache.py
- insight/guardrails.py
- http-fetch.ts
- investor_drawback.py
- ExecutionPlan
- sector_alignment.py
- run_ask_engine
- with
- FundUniverseAgent
- fund_match.py
- market_pulse.py
- plan.py
- stock_fund_ranking.py
- portfolio_bind.py
- nav_service.py
- holding_attribution.py
- scrape-worker/src/index.ts
- sector_fund_ranking.py
- normalize.py
- question_is_bullion_metal_price_question
- _normalize_fund_text
- test_composer_table_summaries.py
- enrich_manager_payload
- validate_capability_args
- env
- _strip_book_concentration_tables
- steps
- evidence_pack.py
- SectorFundRankingIndex
- test_macro_scope.py
- graph.py
- sector_alignment.py
- v2_scoring.py
- strip_missing_data_caveats
- make_plan
- run-daily-pipeline.sh
- env
- plan.py
- infer_fund_news_layers
- news_digest.py
- build_derived_views
- test_two_wave_pipeline.py
- node_compose
- metals_spot_tables.py
- test_insight_graph.py
- test_fact_answer.py
- EntityFunnel
- vitest
- fetch_google_news.py
- prompt.py
- compilerOptions
- compilerOptions
- Settings
- workspace.py
- backfill
- portfolio/client.py
- fund_name_policy.py
- validate_plan_tools
- run-pipeline
- get_settings
- format_inr
- dataclasses
- worker/src/index.ts
- steps
- steps
- with
- RunLogger
- ToolCall
- inputs
- with
- inputs
- _fund_performance_digest
- update.py
- match_scheme_category
- run-backfill.sh
- qdrant
- entity_candidates
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
- test_fund_risk.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_catalog.py
- diagnose_lightsail_site.sh
- compare_evidence.py
- test_compare_funds_cache.py
- market_scope_entities
- evidence.py
- PublisherStats
- unittest_mock
- measured_facts_block
- node_route
- compare_ask_speed.py
- fact_slots.py
- fund_type_name_spec
- csv
- fund_rating_screen.py
- test_rating_screen_uses_focus_question_not_full_compare_question
- _unhandled_exception_handler
- trim_news_grouped

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 486 edges
2. `ToolCall` - 295 edges
3. `get_settings()` - 137 edges
4. `AnswerMode` - 129 edges
5. `QueryLogger` - 100 edges
6. `apply_planner_post_hooks()` - 99 edges
7. `QuestionBrief` - 88 edges
8. `slot_route()` - 84 edges
9. `Settings` - 83 edges
10. `node_compose()` - 82 edges

## Surprising Connections (you probably didn't know these)
- `test_fund_index_has_amc_on_search_hit()` --calls--> `get_fund_index()`  [EXTRACTED]
  tests/test_fund_lookup.py → news_rag/fund_search.py
- `test_is_it_a_bad_fund_is_not_deictic_fund_pronoun()` --calls--> `question_refers_deictic_fund()`  [EXTRACTED]
  tests/test_investor_subject.py → news_rag/insight/investor_subject.py
- `test_user_explicitly_named_scheme_requires_amc_or_two_tokens()` --calls--> `user_explicitly_named_scheme()`  [EXTRACTED]
  tests/test_investor_subject.py → news_rag/insight/investor_subject.py
- `_offline_plan()` --uses--> `AnswerMode`  [INFERRED]
  scripts/eval_basic_queries.py → news_rag/insight/contracts.py
- `test_holdings_breakdown_keeps_planner_news()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_category_plan.py → news_rag/insight/contracts.py

## Import Cycles
- None detected.

## Communities (193 total, 31 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (47): get_encoder(), get_entity_funnel(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate() (+39 more)

### Community 1 - "re"
Cohesion: 0.04
Nodes (81): question_needs_affected_sectors(), asks_macro_explanation(), question_mentions_fund_scheme(), _question_targets_stock_not_fund(), _looks_like_fund_list(), rating_list_plan(), rating_concept_plan(), asks_fund_category_average() (+73 more)

### Community 2 - "fund_context.py"
Cohesion: 0.11
Nodes (26): _resolve_funds(), _canonical_chat_fund_name(), _chat_fund_mention_recency(), _compare_pair_from_chat_turns(), compare_side_in_chat(), comparison_fund_names(), _filter(), _frame_subjects() (+18 more)

### Community 3 - "interpret.py"
Cohesion: 0.07
Nodes (62): asks_random_fund_compare(), Findings, FundFinding, mentions_publication_date(), _assemble(), _caveat(), check_composer_guardrails(), _claim_for_sector() (+54 more)

### Community 4 - "portfolio/cache.py"
Cohesion: 0.15
Nodes (16): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), find_cached_holdings(), get_normalized_portfolio(), peek_derived(), peek_portfolio() (+8 more)

### Community 5 - "Settings"
Cohesion: 0.07
Nodes (30): article_id_from_url(), _batchexecute(), cached_resolve(), is_google_news_article_url(), _parse_garturlres(), resolve_google_news_url(), _connection(), _db_path() (+22 more)

### Community 6 - "NewsStore"
Cohesion: 0.06
Nodes (21): Publisher, SectorQuery, is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), finish_run_logger(), sector_query_gaps() (+13 more)

### Community 7 - "test_portfolio_layer.py"
Cohesion: 0.10
Nodes (17): fetch_top_holdings(), project_concentration(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore (+9 more)

### Community 8 - "parse.py"
Cohesion: 0.06
Nodes (33): _warmup_embeddings_background(), _run(), _pack_row(), _retrieve_bullion_for_entities(), _trim_snippet(), embed_query(), warmup_query_vectors(), corpus_entity_names() (+25 more)

### Community 9 - "news_dates.py"
Cohesion: 0.08
Nodes (33): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), repo_root(), article_in_fetch_window(), google_time_query(), has_news_date_range() (+25 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (58): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+50 more)

### Community 11 - "gather.py"
Cohesion: 0.07
Nodes (46): canonical_facet(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext (+38 more)

### Community 13 - "compute.py"
Cohesion: 0.08
Nodes (47): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+39 more)

### Community 14 - "test_holding_overlap.py"
Cohesion: 0.12
Nodes (13): _add_category_comparison(), _compare_brief_line(), extra_part_brief(), _row_bits(), table_source(), _detail(), test_compare_table_includes_risk_for_both_funds(), test_extra_part_brief_names_both_funds() (+5 more)

### Community 15 - "tools.py"
Cohesion: 0.08
Nodes (47): extract_top_sectors(), fetch_fund_managers_for_isin(), DataNeed, funds_holding_stock(), _active_sector_equity(), _articles_for_affected_question(), _as_date(), asks_equity_funds() (+39 more)

### Community 16 - "build_fund_display_tables"
Cohesion: 0.09
Nodes (32): append_news_section(), _as_float(), _assess_table_quality(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+24 more)

### Community 17 - "normalize_rs_label"
Cohesion: 0.10
Nodes (28): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), fetch_category_ratings() (+20 more)

### Community 18 - "QueryLogger"
Cohesion: 0.09
Nodes (9): slots_from_plan(), ParsedQuery, clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest(), test_finish_writes_json_sidecar() (+1 more)

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (40): _article_context_for_interpret(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority(), _clean_claims() (+32 more)

### Community 20 - "resolve_display_table_policy"
Cohesion: 0.09
Nodes (22): DisplayTablePolicy, fact_values_already_stated(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark(), question_wants_concentration_tables() (+14 more)

### Community 21 - "universe.py"
Cohesion: 0.14
Nodes (21): _clean_holding_tokens(), instrument_to_qdrant_names(), match_holding_to_corpus_entity(), _holding_mentioned(), matches_entity(), _aliases_for(), build_holding_entities(), canonical_key() (+13 more)

### Community 22 - "test_ask_speed.py"
Cohesion: 0.09
Nodes (31): strip_grounding_holes(), collect_evidence_calendar_dates(), add_article(), cores_for_float(), cores_in_text(), derived_cores(), finalize_text_fields(), format_user_calendar_date() (+23 more)

### Community 23 - ".lookup_extracted_fund"
Cohesion: 0.14
Nodes (5): _expand_query_token(), FundIndex, _infer_category_and_type(), resolve_canonical_isin(), _sync_amc_prefix_from_catalog()

### Community 24 - "tool_runners.py"
Cohesion: 0.12
Nodes (42): build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+34 more)

### Community 25 - "category_plan.py"
Cohesion: 0.06
Nodes (42): match_all_scheme_categories(), asks_category_performance(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), asks_cross_category_compare(), asks_fund_holdings_followup(), _category_for_alternate_plan() (+34 more)

### Community 26 - "get_sector_fund_ranking_index"
Cohesion: 0.07
Nodes (32): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+24 more)

### Community 27 - "test_conversation_memory.py"
Cohesion: 0.15
Nodes (27): _load_planner_memory(), _store_turn_memory(), hydrate_memory_from_prior_turns(), _infer_fund_focus_from_chat(), normalize_prior_turns(), append_chat_turn(), _fresh(), get_memory() (+19 more)

### Community 28 - "fund_search.py"
Cohesion: 0.12
Nodes (22): build_holding_overlap(), _clean_company_name(), detail_has_live_facts(), _entry_matches_amc(), _entry_matches_query_scheme(), fetch_fund_managers_for_query(), _fund_context_for_managers(), _fund_text() (+14 more)

### Community 29 - "fields.py"
Cohesion: 0.09
Nodes (32): _asks_book(), bind_fields_to_tools(), _book_fields(), canonicalize_field(), field_need(), FieldNeed, fields_from_question(), _find_term() (+24 more)

### Community 30 - "fund_brief.py"
Cohesion: 0.10
Nodes (33): PortfolioScope, qdrant_filter_names(), _article_entities(), build_events(), cluster_articles(), _cluster_entities(), compose_fund_insight(), _day_key() (+25 more)

### Community 31 - "graph.py"
Cohesion: 0.12
Nodes (17): LLMUsageRecord, PhaseRecord, RequestTelemetry, ToolRecord, _answer_stream_chunks(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta() (+9 more)

### Community 32 - "investor_subject.py"
Cohesion: 0.10
Nodes (36): _amc_token_set(), _categories_equivalent(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan(), ensure_deictic_fund_period_return_plan() (+28 more)

### Community 33 - "owned_holding_names"
Cohesion: 0.22
Nodes (15): owned_holding_names(), _all_holdings_metric_spec(), _fund_data_from_results(), _investor_holdings_rating_rows(), _metric_cell(), render_all_holdings_metric_table(), render_all_holdings_return_table(), render_all_holdings_sector_table() (+7 more)

### Community 34 - "execute_capability"
Cohesion: 0.09
Nodes (17): CapabilityCache, _Entry, _return_slice_covers(), _trim_cached_to_ask(), slice_slot(), test_missing_window_is_not_covered(), test_wider_cached_fund_payload_covers_and_trims_to_the_ask(), _wide() (+9 more)

### Community 35 - "planner_policy.py"
Cohesion: 0.10
Nodes (18): sector_focus_from_market(), align_planned_news_execution(), apply_now_window(), _ensure_sector_overview(), finalize_planner_plan(), question_uses_now_window(), asks_sector_overview(), test_data_only_drops_news() (+10 more)

### Community 36 - "layer_tools.py"
Cohesion: 0.08
Nodes (29): aggregate_sectors_from_holdings(), extract_top_holdings(), normalize_holding_row(), normalize_sector_row(), _price_holdings(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector() (+21 more)

### Community 37 - "executor.py"
Cohesion: 0.09
Nodes (29): retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _conversation_id(), _conversation_turn(), _fill_returns_from_catalog() (+21 more)

### Community 38 - "lib/google_news.py"
Cohesion: 0.05
Nodes (31): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+23 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.11
Nodes (40): asks_taxonomy(), asks_rating_list(), ensure_rating_screen(), _keep_asked_return(), parse_rating_screen(), run_rating_list(), _payload(), _rating() (+32 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "plan_enforce.py"
Cohesion: 0.11
Nodes (18): asks_these_equity_funds(), question_asks_compare_both_in_chat(), apply_category_scoped_compare_funds(), apply_deictic_equity_compare_funds(), _compare_against_portfolio_holding(), _compare_category_slug(), ensure_compare_fund_pair(), finalize_fund_compare_plan() (+10 more)

### Community 42 - "brief.py"
Cohesion: 0.07
Nodes (41): analyst_should_run(), asks_market_briefing(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief(), _detect_direction() (+33 more)

### Community 43 - "test_fund_display_tables.py"
Cohesion: 0.10
Nodes (26): build_fund_display_tables(), ensure_markdown_table_spacing(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_markdown_tables_from_prose(), strip_news_roundup(), _comparison_pack() (+18 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.10
Nodes (24): _run_get_macro_news(), complete_sentences(), _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log() (+16 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "json"
Cohesion: 0.14
Nodes (15): main(), fetch_fund(), load_done_isins(), load_isins(), main(), _pct(), run(), write_final() (+7 more)

### Community 47 - "portfolio_plan.py"
Cohesion: 0.24
Nodes (7): _portfolio_call(), portfolio_sections_from_plan(), top_n_from_question(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

### Community 48 - "primary_fund_name"
Cohesion: 0.15
Nodes (17): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), _bound_fund_name(), enforce_deictic_and_memory_primary_fund(), question_refers_deictic_fund(), reconcile_deictic_planner_fund(), reconcile_planner_invented_fund_name(), resolve_deictic_fund_name() (+9 more)

### Community 49 - "lib/portfolio_scope.py"
Cohesion: 0.16
Nodes (15): build_portfolio_scope(), FundRef, _holding_equity_allowed(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest(), load_portfolio_funds() (+7 more)

### Community 50 - "app.py"
Cohesion: 0.08
Nodes (40): ask(), ask_memory(), ask_sources(), ask_stream(), AskRequest, _attach_llm_meta(), backfill_page(), backfill_start() (+32 more)

### Community 51 - "contracts.py"
Cohesion: 0.14
Nodes (18): apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), EvidenceRow, ScopeKind, apply_pure_concept_plan() (+10 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "test_return_windows.py"
Cohesion: 0.20
Nodes (13): _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows(), window_label() (+5 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.11
Nodes (20): build_comparison_periods(), expense_ratio_for_question(), _f(), fund_returns_from_detail(), normalize_category_average_returns(), normalize_vs_benchmark_payload(), _optional_number(), parse_fund_costs() (+12 more)

### Community 55 - "fact_answer.py"
Cohesion: 0.21
Nodes (21): _age(), _asks_portfolio_rs_ratings(), _book_line(), _comparison_rows(), _composition_line(), field_answer_needs_composer(), _fund_line(), _fund_name() (+13 more)

### Community 56 - "_run_get_fund_data"
Cohesion: 0.13
Nodes (13): fetch_vs_benchmark(), merge_fund_insight_metrics(), _detail_for_fund_tool(), _fund_payload_matches_fund(), _isin_for_fund_name(), refetch_partial_fund_tools(), _repair_incomplete_fund_data(), _run_get_fund_data() (+5 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "test_call_json_llm.py"
Cohesion: 0.13
Nodes (20): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), _layered_news_topics(), _client() (+12 more)

### Community 59 - "re"
Cohesion: 0.14
Nodes (17): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+9 more)

### Community 60 - "embed.py"
Cohesion: 0.15
Nodes (7): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, _build_encoder(), main()

### Community 61 - "aggregate_fund_holdings.py"
Cohesion: 0.23
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 62 - "glossary.py"
Cohesion: 0.14
Nodes (14): asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), glossary_execution_plan(), has_second_part(), meaning_reply(), _normalize_term(), _wants_end_summary() (+6 more)

### Community 63 - "re"
Cohesion: 0.10
Nodes (24): asks_financial_news(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+16 more)

### Community 64 - "get_fund_index"
Cohesion: 0.12
Nodes (21): is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), resolve_fund_for_query(), resolve_fund_from_question(), _resolved_scheme_for_portfolio_ask(), test_absl_and_ppfas_shorthand() (+13 more)

### Community 65 - "gold_service.py"
Cohesion: 0.13
Nodes (18): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+10 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "test_portfolio_startup_cache.py"
Cohesion: 0.14
Nodes (18): clear_cache_for_tests(), seed_portfolio_cache_for_tests(), PortfolioError, PortfolioUnavailable, balance_verdicts(), test_executor_uses_workspace_sample_without_token(), test_executor_with_fixture(), _doc() (+10 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.16
Nodes (13): _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), _tokens(), unknown_fund_phrase() (+5 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "investor_drawback.py"
Cohesion: 0.12
Nodes (21): attach_drawback_digest(), question_asks_all_schemes_in_answer(), _display_holding_row(), _enrich_investor_computed_fields(), _internal_contribution_row(), investor_holdings_for_display(), merge_holding_pp_into_performance(), _num() (+13 more)

### Community 71 - "ExecutionPlan"
Cohesion: 0.06
Nodes (67): ExecutionPlan, merge_planner_asked_facts(), tag_answer_parts(), clarify_plan_if_fund_unknown(), _plan_uses_fund_scoped_tools(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings() (+59 more)

### Community 72 - "sector_alignment.py"
Cohesion: 0.10
Nodes (19): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker(), _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases() (+11 more)

### Community 73 - "run_ask_engine"
Cohesion: 0.23
Nodes (6): run_ask_engine(), stream_ask_engine(), run_insight_pipeline(), stream_insight_pipeline(), main(), test_ask_engine_delegates_to_insight_pipeline()

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "FundUniverseAgent"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 77 - "fund_match.py"
Cohesion: 0.11
Nodes (13): embed_query(), _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme() (+5 more)

### Community 78 - "market_pulse.py"
Cohesion: 0.08
Nodes (33): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), _one(), _fetch_macro_query(), _query_variants(), run_macro_news_enhanced() (+25 more)

### Community 79 - "plan.py"
Cohesion: 0.14
Nodes (14): _apply_planner_request(), _example_part(), _label_for_days(), parse_plan(), _pick_enum(), _planner_fields(), _str_list(), test_parse_plan_reads_the_memory_pointers() (+6 more)

### Community 80 - "stock_fund_ranking.py"
Cohesion: 0.11
Nodes (14): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials(), _match_aggregated() (+6 more)

### Community 81 - "portfolio_bind.py"
Cohesion: 0.23
Nodes (9): question_asks_category_book_share(), bind_cached_portfolio(), _catalog_fund_holdings_question(), ensure_tools_for_data_question(), finish_portfolio_plan_bind(), _investor_args(), _merge_fund(), question_mentions_own_book() (+1 more)

### Community 82 - "nav_service.py"
Cohesion: 0.15
Nodes (16): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+8 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "sector_fund_ranking.py"
Cohesion: 0.10
Nodes (19): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors() (+11 more)

### Community 86 - "normalize.py"
Cohesion: 0.27
Nodes (13): _allocation_block(), _apply_holding_values(), _first(), _holding_from_scheme(), normalize_workspace(), _num(), _pnl_summary_row(), _prefer_xirr() (+5 more)

### Community 87 - "question_is_bullion_metal_price_question"
Cohesion: 0.33
Nodes (6): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), test_bullion_plan_clears_memory_gold_etf(), test_bullion_vs_gold_etf_detection()

### Community 88 - "_normalize_fund_text"
Cohesion: 0.16
Nodes (13): _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question(), _is_bullion_phrase_not_scheme() (+5 more)

### Community 89 - "test_composer_table_summaries.py"
Cohesion: 0.12
Nodes (13): assemble_fund_overview_answer(), filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), strip_empty_table_pointers(), _strip_overview_prose_block(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table() (+5 more)

### Community 90 - "enrich_manager_payload"
Cohesion: 0.17
Nodes (12): _capability_cache_key(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score(), test_default_manager_answer_drops_former_managers() (+4 more)

### Community 91 - "validate_capability_args"
Cohesion: 0.18
Nodes (11): validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded(), test_vs_benchmark_module_is_not_replaced_by_snapshot(), test_validate_capability_requires_modules(), test_any_period_code_is_kept(), test_finalize_screen_adds_returns_for_compare_question() (+3 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.06
Nodes (61): EvidencePack, append_investor_portfolio_overview_tables(), _attach_rs_ratings_to_screen(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_cell(), _compare_header(), _complete_fund_row() (+53 more)

### Community 96 - "SectorFundRankingIndex"
Cohesion: 0.15
Nodes (3): normalize_sector_label(), _sector_label_in_text(), SectorFundRankingIndex

### Community 97 - "test_macro_scope.py"
Cohesion: 0.17
Nodes (10): question_is_standalone_macro(), ensure_catalog_tools_for_fund_news(), apply_standalone_macro_scope(), _macro_news_topics(), test_fund_news_adds_catalog_tools(), test_how_its_affecting_rupee_is_not_deictic_fund_title(), test_macro_scope_injects_news_when_planner_sent_no_tools(), test_macro_scope_strips_fund_tools() (+2 more)

### Community 98 - "graph.py"
Cohesion: 0.10
Nodes (26): execute_capability(), _attach_conversation(), build_result(), _compose_hints(), _conversation_id(), _ensure_portfolio_for_fund_news(), GraphState, _maybe_compare_funds_after_multi_screen() (+18 more)

### Community 99 - "sector_alignment.py"
Cohesion: 0.07
Nodes (35): benchmark_entry(), clear_sector_index_cache(), _document(), nifty50_ticker(), sector_index_entry(), sector_yfinance_ticker(), sector_query_for_label(), clear_macro_impact_cache() (+27 more)

### Community 100 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 101 - "strip_missing_data_caveats"
Cohesion: 0.12
Nodes (18): strip_missing_data_caveats(), strip_private_leaks(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows() (+10 more)

### Community 102 - "make_plan"
Cohesion: 0.24
Nodes (4): check(), main(), run_case(), _Usage

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "plan.py"
Cohesion: 0.08
Nodes (21): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), field_prompt_table(), mentions_advice(), _invalidate_plan_system_cache(), make_plan() (+13 more)

### Community 106 - "infer_fund_news_layers"
Cohesion: 0.33
Nodes (5): infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only()

### Community 107 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 108 - "build_derived_views"
Cohesion: 0.38
Nodes (6): asset_bucket(), _aum(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation()

### Community 109 - "test_two_wave_pipeline.py"
Cohesion: 0.13
Nodes (9): evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), test_bridge_skips_wave2_for_data_only(), test_bridge_skips_when_return_positive(), test_bridge_triggers_on_negative_return(), test_fund_manager_data_only_template_includes_context_and_bio(), test_portfolio_data_only_template_uses_percentage_fields() (+1 more)

### Community 110 - "node_compose"
Cohesion: 0.11
Nodes (28): build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), _pretty_category(), question_signals_investor_book(), render_portfolio_drawback_answer() (+20 more)

### Community 111 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 112 - "test_insight_graph.py"
Cohesion: 0.17
Nodes (5): build_data_pack(), build(), _compact(), plan_to_brief(), test_a_nav_lookup_plans_no_news_facets()

### Community 113 - "test_fact_answer.py"
Cohesion: 0.21
Nodes (16): is_pure_field_answer(), render_benchmark_comparison_table(), render_fact_answer(), wants_comparison_table(), _plan(), test_all_holdings_rs_uses_composer_not_field_template(), test_aum_and_expense_both_appear(), test_benchmark_return_uses_vs_benchmark_period() (+8 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "fetch_google_news.py"
Cohesion: 0.24
Nodes (11): _bucket(), _entity_names(), fetch_window_fields(), summarize_errors(), write_error_summary(), _compact_fetch_errors(), fetch_google_news(), covered_calendar_days() (+3 more)

### Community 117 - "prompt.py"
Cohesion: 0.15
Nodes (13): greeting_reply(), identity_reply(), _mirror_greeting(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens() (+5 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "Settings"
Cohesion: 0.11
Nodes (26): _merge_publisher_error_reasons(), write_day_report(), _atomic_write(), day_failure_slices_for_run(), ensure_loaded(), _failures_dir(), flush(), is_source_exhausted() (+18 more)

### Community 121 - "workspace.py"
Cohesion: 0.19
Nodes (7): apply_fresh_start(), _clear_run_json_summaries(), clear_scrape_workspace(), remove_scrape_artifacts(), remove_scrape_artifacts_many(), url_artifact_stem(), workspace_dir()

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "portfolio/client.py"
Cohesion: 0.17
Nodes (11): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), PortfolioNotConfigured, PortfolioUpstreamError, rupeestop_admin_request_headers(), rupeestop_bearer_token() (+3 more)

### Community 124 - "fund_name_policy.py"
Cohesion: 0.27
Nodes (8): plan_wants_random_same_category_pair_compare(), enforce_user_authorized_funds_only(), fund_authorized_for_question(), plan_allows_server_fund_pick(), plan_wants_better_rated_in_category(), test_invented_funds_stripped_when_not_in_chat(), test_random_compare_allows_server_pick(), test_user_named_fund_kept()

### Community 125 - "validate_plan_tools"
Cohesion: 0.24
Nodes (8): _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question(), validate_plan_tools(), test_silver_price_tool_becomes_news(), test_validate_adds_risk_when_planner_only_portfolio_holdings()

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "get_settings"
Cohesion: 0.07
Nodes (41): Settings, anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts(), build_anthropic_messages_body(), _call_anthropic(), _call_deepseek(), _call_gemini() (+33 more)

### Community 128 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 129 - "dataclasses"
Cohesion: 0.12
Nodes (13): _detect_funds(), _infer_window_days(), SubAsk, SectorFinding, _dedupe_parenthetical_cites(), test_dedupe_repeated_citations(), test_market_sector_lists_in_display_without_funds(), test_named_fund_why_uses_sector_drag_not_macro() (+5 more)

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

### Community 135 - "ToolCall"
Cohesion: 0.05
Nodes (62): _followup_modules(), AnswerMode, ToolCall, build_evidence_pack(), ensure_fund_concentration_plan(), clean_news_insight(), is_article_only_news(), strip_publisher() (+54 more)

### Community 137 - "inputs"
Cohesion: 0.29
Nodes (7): default, description, required, type, holdings_limit, workflow_dispatch, inputs

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "_fund_performance_digest"
Cohesion: 0.38
Nodes (4): _fund_performance_digest(), prefers_planner_over_slot(), test_fund_news_does_not_force_planner(), test_performance_digest_from_snapshot()

### Community 141 - "update.py"
Cohesion: 0.15
Nodes (19): drop_old_turns(), fund_name_mentioned_in_memory(), add_gist(), empty_frame(), empty_state(), expire_stale_entities(), push_fund(), stack_entry() (+11 more)

### Community 142 - "match_scheme_category"
Cohesion: 0.14
Nodes (12): CategoryMatch, explanation_brief(), match_scheme_category(), _names_a_type(), _phrase_in(), _spaced_category_words(), taxonomy_reply(), _category_fund_name_spec() (+4 more)

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

### Community 145 - "entity_candidates"
Cohesion: 0.30
Nodes (6): candidates_block(), entity_candidates(), _holding_candidates(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

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

### Community 163 - "test_fund_risk.py"
Cohesion: 0.06
Nodes (52): asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison() (+44 more)

### Community 170 - "fund_catalog.py"
Cohesion: 0.17
Nodes (18): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+10 more)

### Community 174 - "compare_evidence.py"
Cohesion: 0.27
Nodes (7): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 175 - "test_compare_funds_cache.py"
Cohesion: 0.21
Nodes (7): _compare_cache_label(), _compare_payload_matches_funds(), compare_payload_matches_funds(), test_compare_conversation_cache_does_not_reuse_different_pair(), fake_compare(), test_compare_conversation_cache_hits_same_pair(), test_compare_payload_matches_funds()

### Community 177 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

### Community 178 - "evidence.py"
Cohesion: 0.18
Nodes (14): _take_conversation_slice(), widen_portfolio_args(), clear_conversation(), drain_cache_events(), note_cache(), recall_slice(), recall_wider_portfolio(), remember_slice() (+6 more)

### Community 182 - "node_route"
Cohesion: 0.13
Nodes (9): asks_computed_illustration(), strip_context_disclaimer(), _clean_answer(), GraphUnavailable, node_route(), strip_meta_opening_heading(), test_strip_meta_opening_heading_keeps_summary_prose(), test_fire_sip_plan_is_a_computed_illustration() (+1 more)

### Community 183 - "compare_ask_speed.py"
Cohesion: 0.25
Nodes (6): _json_default(), safe_json_dumps(), compare(), _load(), main(), _numbers()

### Community 185 - "fact_slots.py"
Cohesion: 0.33
Nodes (6): asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), test_aum_slot_renders_from_snapshot()

### Community 186 - "fund_type_name_spec"
Cohesion: 0.32
Nodes (4): _fund_type_in_name_clause(), fund_type_name_spec(), test_name_me_debt_fund_gets_rating_spec(), test_random_debt_not_equity_when_also_asks_debt_vs_equity()

### Community 188 - "fund_rating_screen.py"
Cohesion: 0.10
Nodes (27): categories_for(), _add_category_comparison(), _amc_matches(), _amc_outside_label(), _amc_token(), _apply_category_difference(), _best_label(), _cascade_labels_for_spec() (+19 more)

### Community 190 - "test_rating_screen_uses_focus_question_not_full_compare_question"
Cohesion: 0.40
Nodes (3): test_rating_screen_uses_focus_question_not_full_compare_question(), test_rating_screen_uses_forced_category_spec(), fake_fetch()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1472 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `re`, `fund_context.py`, `ToolCall`, `test_portfolio_layer.py`, `test_fund_drawdown.py`, `update.py`, `test_holding_overlap.py`, `build_fund_display_tables`, `QueryLogger`, `resolve_display_table_policy`, `category_plan.py`, `get_sector_fund_ranking_index`, `test_conversation_memory.py`, `fields.py`, `investor_subject.py`, `owned_holding_names`, `test_fund_risk.py`, `planner_policy.py`, `test_fund_rating_screen.py`, `plan_enforce.py`, `compare_evidence.py`, `portfolio_plan.py`, `primary_fund_name`, `app.py`, `contracts.py`, `fact_answer.py`, `fact_slots.py`, `fund_rating_screen.py`, `glossary.py`, `gold_service.py`, `test_portfolio_startup_cache.py`, `investor_drawback.py`, `plan.py`, `portfolio_bind.py`, `question_is_bullion_metal_price_question`, `test_composer_table_summaries.py`, `evidence_pack.py`, `test_macro_scope.py`, `graph.py`, `plan.py`, `test_two_wave_pipeline.py`, `node_compose`, `test_insight_graph.py`, `test_fact_answer.py`, `fund_name_policy.py`, `validate_plan_tools`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `ExecutionPlan` (e.g. with `evaluate_wave2()` and `apply_concept_example_to_plan()`) actually correct?**
  _`ExecutionPlan` has 33 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.07174416158215864 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `app.py` to `re`, `interpret.py`, `portfolio/cache.py`, `test_portfolio_layer.py`, `parse.py`, `gather.py`, `compute.py`, `news_reader.py`, `.lookup_extracted_fund`, `tool_runners.py`, `get_sector_fund_ranking_index`, `fund_search.py`, `fund_brief.py`, `investor_subject.py`, `executor.py`, `brief.py`, `node_route`, `embed.py`, `gold_service.py`, `test_portfolio_startup_cache.py`, `fund_match.py`, `market_pulse.py`, `stock_fund_ranking.py`, `portfolio_bind.py`, `sector_fund_ranking.py`, `evidence_pack.py`, `graph.py`, `plan.py`, `node_compose`, `portfolio/client.py`, `get_settings`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Should `re` be split into smaller, more focused modules?**
  _Cohesion score 0.03827751196172249 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ToolCall` to `re`, `test_portfolio_layer.py`, `test_fund_drawdown.py`, `update.py`, `test_holding_overlap.py`, `resolve_display_table_policy`, `category_plan.py`, `get_sector_fund_ranking_index`, `test_conversation_memory.py`, `fields.py`, `investor_subject.py`, `owned_holding_names`, `execute_capability`, `test_fund_risk.py`, `planner_policy.py`, `executor.py`, `test_fund_rating_screen.py`, `plan_enforce.py`, `compare_evidence.py`, `portfolio_plan.py`, `primary_fund_name`, `test_compare_funds_cache.py`, `app.py`, `contracts.py`, `fund_rating_screen.py`, `gold_service.py`, `test_portfolio_startup_cache.py`, `ExecutionPlan`, `plan.py`, `portfolio_bind.py`, `question_is_bullion_metal_price_question`, `test_macro_scope.py`, `graph.py`, `plan.py`, `test_two_wave_pipeline.py`, `node_compose`, `test_insight_graph.py`, `fund_name_policy.py`, `validate_plan_tools`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._