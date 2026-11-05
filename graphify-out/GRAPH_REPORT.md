# Graph Report - db_design_with_qdrant_locally  (2026-11-05)

## Corpus Check
- 486 files · ~842,253 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 5028 nodes · 16008 edges · 192 communities (165 shown, 27 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 644 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5a6d3de3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- ToolCall
- investor_subject.py
- interpret.py
- portfolio/cache.py
- apply_planner_post_hooks
- NewsStore
- test_portfolio_layer.py
- pathlib
- news_dates.py
- test_fund_drawdown.py
- gather.py
- _unhandled_exception_handler
- compute.py
- QuestionBrief
- tools.py
- build_fund_display_tables
- eval_basic_queries.py
- QueryLogger
- news_reader.py
- resolve_display_table_policy
- lib/portfolio_scope.py
- node_compose
- ._ensure_loaded
- tool_runners.py
- category_plan.py
- news_reader.py
- test_conversation_memory.py
- Any
- fact_answer.py
- fund_brief.py
- graph.py
- article_url.py
- fund_context.py
- execute_capability
- screen_hints_from_question
- layer_tools.py
- _run_get_fund_data
- lib/google_news.py
- test_fund_rating_screen.py
- env
- test_screen_rating_screen_arg.py
- brief.py
- test_fund_display_tables.py
- macro_news_cache.py
- env
- json
- build_evidence_pack
- validate_capability_args
- scrape_bodies.py
- get_settings
- question_is_pure_general_concept
- env
- test_return_windows.py
- fund_rupeestop_metrics.py
- test_news_only_answer.py
- trim_news_grouped
- scrape-worker/package.json
- llm_client.py
- re
- embed.py
- test_fund_risk.py
- test_smart_fund_why.py
- re
- get_fund_index
- gold_service.py
- batch.ts
- test_portfolio_layer.py
- insight/guardrails.py
- http-fetch.ts
- investor_drawback.py
- ExecutionPlan
- sector_alignment.py
- typing
- with
- FundUniverseAgent
- fund_match.py
- market_pulse.py
- parse_plan
- stock_fund_ranking.py
- test_portfolio_startup_cache.py
- nav_service.py
- holding_attribution.py
- scrape-worker/src/index.ts
- Settings
- normalize.py
- question_is_bullion_metal_price_question
- _normalize_fund_text
- test_composer_table_summaries.py
- enrich_manager_payload
- aggregate_fund_holdings.py
- env
- portfolio_news_impact.py
- steps
- evidence_pack.py
- sector_query_for_label
- sector_alignment.py
- graph.py
- macro_impact_map.py
- index_series.py
- strip_missing_data_caveats
- ask_plan.py
- run-daily-pipeline.sh
- env
- plan.py
- infer_fund_news_layers
- news_digest.py
- build_derived_views
- test_guardrails_domain.py
- node_compose
- metals_spot_tables.py
- test_insight_graph.py
- fund_rating_screen.py
- FundUniverseCatalog
- vitest
- nse_sector_indices.py
- prompt.py
- compilerOptions
- compilerOptions
- main.py
- test_answer_precision.py
- backfill
- PortfolioError
- get_stock_profile
- fetch_workspace_raw
- run-pipeline
- news_pipeline/config.py
- format_inr
- test_holding_overlap.py
- worker/src/index.ts
- steps
- steps
- with
- RunLogger
- primary_sector_for_question
- inputs
- with
- inputs
- slots_from_plan
- update.py
- explicit_fund_count
- run-backfill.sh
- qdrant
- glossary.py
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
- fund_risk.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_catalog.py
- diagnose_lightsail_site.sh
- compare_evidence.py
- rank_funds_by_sector_exposure
- collect_evidence_calendar_dates
- evidence.py
- test_screen_facts.py
- enrich_rankings_with_nav
- extract_top_holdings
- asks_computed_illustration
- normalize_user_facing_text
- top_n_from_question
- article_pool.py
- contains_phrase
- _apply_category_difference
- _amc_outside_label
- test_snapshot_uses_payload_returns_and_history_only_for_gaps

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 472 edges
2. `ToolCall` - 287 edges
3. `get_settings()` - 137 edges
4. `AnswerMode` - 130 edges
5. `QueryLogger` - 100 edges
6. `apply_planner_post_hooks()` - 89 edges
7. `QuestionBrief` - 88 edges
8. `slot_route()` - 84 edges
9. `Settings` - 83 edges
10. `node_compose()` - 82 edges

## Surprising Connections (you probably didn't know these)
- `_offline_plan()` --uses--> `AnswerMode`  [INFERRED]
  scripts/eval_basic_queries.py → news_rag/insight/contracts.py
- `test_holdings_breakdown_keeps_planner_news()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_category_plan.py → news_rag/insight/contracts.py
- `test_render_fund_concentration_from_portfolio_data()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_fund_concentration.py → news_rag/insight/contracts.py
- `_plan()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_fund_drawdown.py → news_rag/insight/contracts.py
- `test_compare_table_shows_the_drawdown_row()` --uses--> `AnswerMode`  [INFERRED]
  tests/test_fund_drawdown.py → news_rag/insight/contracts.py

## Import Cycles
- None detected.

## Communities (192 total, 27 thin omitted)

### Community 0 - "logging"
Cohesion: 0.08
Nodes (43): fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate(), drop_old_points() (+35 more)

### Community 1 - "ToolCall"
Cohesion: 0.03
Nodes (97): rating_list_plan(), _ensure_pillar_rating_plan(), rating_concept_plan(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), apply_concept_example_to_plan(), asks_concept_with_catalog_example() (+89 more)

### Community 2 - "investor_subject.py"
Cohesion: 0.07
Nodes (46): question_is_standalone_macro(), node_evidence_gate(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan(), ensure_catalog_tools_for_fund_news() (+38 more)

### Community 3 - "interpret.py"
Cohesion: 0.08
Nodes (63): asks_random_fund_compare(), Findings, FundFinding, SectorFinding, EvidenceSet, _article_context_for_interpret(), _assemble(), _caveat() (+55 more)

### Community 4 - "portfolio/cache.py"
Cohesion: 0.15
Nodes (18): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), find_cached_holdings(), get_normalized_portfolio(), peek_derived(), peek_portfolio() (+10 more)

### Community 5 - "apply_planner_post_hooks"
Cohesion: 0.06
Nodes (42): _amc_token_set(), _detect_funds(), tag_answer_parts(), asks_these_equity_funds(), apply_category_scoped_compare_funds(), apply_deictic_equity_compare_funds(), apply_planner_post_hooks(), _compare_against_portfolio_holding() (+34 more)

### Community 6 - "NewsStore"
Cohesion: 0.06
Nodes (21): Encoder, get_encoder(), embed_and_upsert(), _to_article(), EntityScore, StoredArticle, is_qdrant_cloud(), qdrant_host() (+13 more)

### Community 7 - "test_portfolio_layer.py"
Cohesion: 0.18
Nodes (7): _run_get_investor_portfolio(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore

### Community 8 - "pathlib"
Cohesion: 0.10
Nodes (23): Settings, _atomic_write(), ensure_loaded(), _failures_dir(), flush(), is_google_exhausted(), is_source_exhausted(), _load_file() (+15 more)

### Community 9 - "news_dates.py"
Cohesion: 0.09
Nodes (21): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), iter_inclusive_days(), NewsDateRangeError, parse_one_date(), single_day_news_date_range() (+13 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.07
Nodes (62): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+54 more)

### Community 11 - "gather.py"
Cohesion: 0.07
Nodes (47): _brief_system(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext (+39 more)

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (46): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+38 more)

### Community 14 - "QuestionBrief"
Cohesion: 0.09
Nodes (26): analyst_should_run(), asks_market_briefing(), asks_sector_lists(), nearest_return_window(), question_tier(), QuestionBrief, random_fund_count(), _success_criteria() (+18 more)

### Community 15 - "tools.py"
Cohesion: 0.09
Nodes (39): DataNeed, _active_sector_equity(), _articles_for_affected_question(), _as_date(), asks_equity_funds(), _broad_working_well_keys(), _catalog_candidates(), _drop_stale_nav() (+31 more)

### Community 16 - "build_fund_display_tables"
Cohesion: 0.11
Nodes (25): _as_float(), _assess_table_quality(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct(), _fmt_pp() (+17 more)

### Community 17 - "eval_basic_queries.py"
Cohesion: 0.09
Nodes (22): ensure_fund_concentration_plan(), node_route(), ensure_planner_fund_fact_modules(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question() (+14 more)

### Community 18 - "QueryLogger"
Cohesion: 0.08
Nodes (13): _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), ParsedQuery, clip_log_text(), _kv() (+5 more)

### Community 19 - "news_reader.py"
Cohesion: 0.10
Nodes (27): _body(), _build_user_prompt(), _canonical_sector(), _clean_claims(), _clean_sector_calls(), _date(), _direction_to_sentiment(), _first_fact() (+19 more)

### Community 20 - "resolve_display_table_policy"
Cohesion: 0.12
Nodes (17): DisplayTablePolicy, filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark(), question_wants_concentration_tables(), question_wants_gold_table() (+9 more)

### Community 21 - "lib/portfolio_scope.py"
Cohesion: 0.08
Nodes (33): build_portfolio_scope(), _clean_holding_tokens(), FundRef, _holding_equity_allowed(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest() (+25 more)

### Community 22 - "node_compose"
Cohesion: 0.10
Nodes (29): strip_grounding_holes(), cores_for_float(), cores_in_text(), derived_cores(), finalize_text_fields(), fund_portfolio_cores(), investor_book_cores(), number_is_grounded() (+21 more)

### Community 23 - "._ensure_loaded"
Cohesion: 0.17
Nodes (5): amc_hint_token_set(), get_amc_catalog(), FundIndex, _infer_category_and_type(), _sync_amc_prefix_from_catalog()

### Community 24 - "tool_runners.py"
Cohesion: 0.13
Nodes (40): build_default_registry(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector(), _infer_driver_direction() (+32 more)

### Community 25 - "category_plan.py"
Cohesion: 0.05
Nodes (53): CategoryMatch, explanation_brief(), match_all_scheme_categories(), match_scheme_category(), _names_a_type(), _phrase_in(), _spaced_category_words(), taxonomy_reply() (+45 more)

### Community 26 - "news_reader.py"
Cohesion: 0.06
Nodes (32): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+24 more)

### Community 27 - "test_conversation_memory.py"
Cohesion: 0.13
Nodes (28): _load_planner_memory(), push_recent_fund_focus(), hydrate_memory_from_prior_turns(), _infer_fund_focus_from_chat(), normalize_prior_turns(), append_chat_turn(), get_memory(), get_or_create() (+20 more)

### Community 28 - "Any"
Cohesion: 0.11
Nodes (23): build_holding_overlap(), _clean_company_name(), detail_has_live_facts(), _entry_matches_amc(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers(), _fund_text() (+15 more)

### Community 29 - "fact_answer.py"
Cohesion: 0.07
Nodes (59): periods_requested_in_question(), _age(), _asks_portfolio_rs_ratings(), _book_line(), _comparison_rows(), _composition_line(), field_answer_needs_composer(), _fund_line() (+51 more)

### Community 30 - "fund_brief.py"
Cohesion: 0.06
Nodes (40): instrument_to_qdrant_names(), PortfolioScope, qdrant_filter_names(), ScopedHolding, ScopedSector, _article_entities(), build_events(), cluster_articles() (+32 more)

### Community 31 - "graph.py"
Cohesion: 0.15
Nodes (14): RequestTelemetry, _answer_stream_chunks(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed(), event_phase_started(), event_quality_check() (+6 more)

### Community 32 - "article_url.py"
Cohesion: 0.26
Nodes (3): scrape_article_url(), ScrapeArticleError, main()

### Community 33 - "fund_context.py"
Cohesion: 0.06
Nodes (50): _bound_fund_name(), clarify_plan_if_fund_unknown(), _plan_uses_fund_scoped_tools(), _resolve_funds(), enforce_deictic_and_memory_primary_fund(), reconcile_deictic_planner_fund(), resolve_deictic_fund_name(), resolve_user_named_fund_in_memory() (+42 more)

### Community 34 - "execute_capability"
Cohesion: 0.10
Nodes (14): CapabilityCache, _Entry, get_capability_cache(), _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), test_compare_conversation_cache_does_not_reuse_different_pair(), fake_compare() (+6 more)

### Community 35 - "screen_hints_from_question"
Cohesion: 0.06
Nodes (39): question_needs_affected_sectors(), execute_wave(), _args_from_question(), asks_funds_holding_stock(), asks_funds_with_sector_exposure(), _clean_stock_capture(), _exposure_ask(), _heavy_and_return() (+31 more)

### Community 36 - "layer_tools.py"
Cohesion: 0.17
Nodes (15): _run_get_market_snapshot(), _price_holdings(), _detail(), register_layer_tools(), run_fund_attribution_tool(), run_fund_snapshot(), run_index_return_tool(), run_macro_series_tool() (+7 more)

### Community 37 - "_run_get_fund_data"
Cohesion: 0.06
Nodes (42): asks_rating_list(), fetch_public_rating(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _capability_cache_key(), _conversation_id(), _conversation_turn() (+34 more)

### Community 38 - "lib/google_news.py"
Cohesion: 0.05
Nodes (36): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+28 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.09
Nodes (42): asks_taxonomy(), ensure_rating_screen(), _followup_modules(), parse_rating_screen(), _return_direction(), run_rating_list(), ensure_screen_facts(), _payload() (+34 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "test_screen_rating_screen_arg.py"
Cohesion: 0.28
Nodes (6): test_finalize_screen_adds_returns_for_compare_question(), fake_detail(), get_fund_detail(), test_rating_screen_uses_focus_question_not_full_compare_question(), test_rating_screen_uses_forced_category_spec(), fake_fetch()

### Community 42 - "brief.py"
Cohesion: 0.11
Nodes (19): asks_share_price(), asks_weak_sector(), build_question_brief(), _detect_direction(), _heuristic_brief(), _infer_window_days(), _log_brief(), plan_evidence() (+11 more)

### Community 43 - "test_fund_display_tables.py"
Cohesion: 0.09
Nodes (31): append_news_section(), assemble_fund_overview_answer(), build_fund_display_tables(), format_display_tables_markdown(), _insert_before_disclaimer(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers() (+23 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.07
Nodes (28): _news_search_targets(), _run_get_macro_news(), market_query_for_topic(), market_scope_entities(), pulse_theme_entities(), _article_text(), _cache_has_article_text(), compute_macro_news() (+20 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "json"
Cohesion: 0.05
Nodes (37): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), _json_default() (+29 more)

### Community 47 - "build_evidence_pack"
Cohesion: 0.08
Nodes (25): EvidenceRow, _add_category_comparison(), build_evidence_pack(), _compare_brief_line(), table_source(), asks_one_figure(), test_render_fund_concentration_from_portfolio_data(), test_good_choice_list_uses_the_funds_table() (+17 more)

### Community 48 - "validate_capability_args"
Cohesion: 0.12
Nodes (18): exposure_from_detail(), headline_rating(), load_fund_risk(), _pillar_maximum(), _public_pillars(), rating_for_request(), rating_needs_pillars(), _weights() (+10 more)

### Community 49 - "scrape_bodies.py"
Cohesion: 0.11
Nodes (20): _entity_refs(), _log_scrape_record(), _scrape(), scrape_bodies(), _drop(), article_in_fetch_window(), google_time_query(), has_news_date_range() (+12 more)

### Community 50 - "get_settings"
Cohesion: 0.07
Nodes (49): ask(), ask_memory(), ask_sources(), ask_stream(), AskRequest, _attach_llm_meta(), backfill_page(), backfill_start() (+41 more)

### Community 51 - "question_is_pure_general_concept"
Cohesion: 0.44
Nodes (6): apply_pure_concept_plan(), question_is_pure_general_concept(), test_all_holdings_metrics_adds_investor_tool(), test_large_cap_vs_mid_cap_is_pure_concept(), test_my_funds_is_not_pure_concept(), test_named_large_cap_scheme_keeps_tools()

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "test_return_windows.py"
Cohesion: 0.20
Nodes (13): _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date(), _pretty_date(), published_return(), returns_for_windows(), window_label() (+5 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (21): asks_fund_category_average(), build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns() (+13 more)

### Community 55 - "test_news_only_answer.py"
Cohesion: 0.17
Nodes (11): _news_subject(), clean_news_insight(), complete_sentences(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words(), test_get_macro_news_clusters_reach_composer_news() (+3 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "llm_client.py"
Cohesion: 0.08
Nodes (36): anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts(), build_anthropic_messages_body(), _call_anthropic(), _call_deepseek(), _call_gemini(), call_insight_llm() (+28 more)

### Community 59 - "re"
Cohesion: 0.13
Nodes (17): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+9 more)

### Community 60 - "embed.py"
Cohesion: 0.11
Nodes (8): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), _build_encoder(), embed_query(), main(), main()

### Community 61 - "test_fund_risk.py"
Cohesion: 0.10
Nodes (27): asks_sebi_riskometer(), blocked_reply(), normalize_rating(), render_risk_lines(), strip_missing_data_caveats(), strip_private_leaks(), ensure_multi_fact_tools(), test_a_rating_pick_does_not_apologise_for_returns_or_pillars() (+19 more)

### Community 62 - "test_smart_fund_why.py"
Cohesion: 0.10
Nodes (11): canonical_facet(), mentions_publication_date(), publication_date_keys(), check_composer_guardrails(), grounding_cores(), scrub_composer_text(), test_publication_date_flags_paren_cites_not_prose_anchors(), test_composer_guardrails() (+3 more)

### Community 63 - "re"
Cohesion: 0.12
Nodes (17): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+9 more)

### Community 64 - "get_fund_index"
Cohesion: 0.11
Nodes (22): extract_fund_phrase_from_question(), extract_top_sectors(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), resolve_fund_for_query(), resolve_fund_from_question() (+14 more)

### Community 65 - "gold_service.py"
Cohesion: 0.16
Nodes (16): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+8 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "test_portfolio_layer.py"
Cohesion: 0.12
Nodes (15): clear_cache_for_tests(), project_concentration(), normalized_doc(), test_concentration_keeps_cash(), test_concentration_question_loads_stock_and_sector_data(), test_current_value_and_nonzero_xirr(), test_enforce_portfolio_scope_strips_tool(), test_executor_uses_workspace_sample_without_token() (+7 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.12
Nodes (18): candidates_block(), entity_candidates(), _holding_candidates(), _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known(), guard_reply() (+10 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "investor_drawback.py"
Cohesion: 0.07
Nodes (32): EvidencePack, _fund_performance_digest(), attach_drawback_digest(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer(), question_asks_all_schemes_in_answer(), _display_holding_row() (+24 more)

### Community 71 - "ExecutionPlan"
Cohesion: 0.07
Nodes (57): ExecutionPlan, build_drawdown_wave2_calls(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), question_asks_portfolio_level_drawdown(), question_signals_investor_book(), plan_targets_single_fund_measured_return(), _bind_fund_list() (+49 more)

### Community 72 - "sector_alignment.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "typing"
Cohesion: 0.12
Nodes (6): run_ask_engine(), stream_ask_engine(), run_insight_pipeline(), stream_insight_pipeline(), attach_query_log_meta(), main()

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "FundUniverseAgent"
Cohesion: 0.18
Nodes (8): FundUniverseAgent, get_fund_universe_catalog(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question(), test_agent_query_gold_etfs(), test_catalog_loads_funds(), test_query_by_amc_and_category(), test_query_large_cap_funds()

### Community 77 - "fund_match.py"
Cohesion: 0.09
Nodes (20): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+12 more)

### Community 78 - "market_pulse.py"
Cohesion: 0.05
Nodes (56): article_dedupe_key(), corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles() (+48 more)

### Community 79 - "parse_plan"
Cohesion: 0.13
Nodes (14): _apply_planner_request(), _example_part(), _label_for_days(), parse_plan(), _pick_enum(), _planner_fields(), _str_list(), test_parse_plan_reads_the_memory_pointers() (+6 more)

### Community 80 - "stock_fund_ranking.py"
Cohesion: 0.31
Nodes (7): default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), _initials(), _match_aggregated(), _norm()

### Community 81 - "test_portfolio_startup_cache.py"
Cohesion: 0.16
Nodes (15): question_asks_category_book_share(), bind_cached_portfolio(), _catalog_fund_holdings_question(), ensure_tools_for_data_question(), finish_portfolio_plan_bind(), _investor_args(), _merge_fund(), question_mentions_own_book() (+7 more)

### Community 82 - "nav_service.py"
Cohesion: 0.21
Nodes (11): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+3 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "Settings"
Cohesion: 0.13
Nodes (19): finish_run_logger(), fetch_entity_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url(), fetch_macro_items(), is_macro_match(), macro_fetch_entities() (+11 more)

### Community 86 - "normalize.py"
Cohesion: 0.33
Nodes (12): _allocation_block(), _apply_holding_values(), _first(), _holding_from_scheme(), normalize_workspace(), _num(), _pnl_summary_row(), _prefer_xirr() (+4 more)

### Community 87 - "question_is_bullion_metal_price_question"
Cohesion: 0.29
Nodes (7): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), node_resolve(), test_bullion_plan_clears_memory_gold_etf(), test_bullion_vs_gold_etf_detection()

### Community 88 - "_normalize_fund_text"
Cohesion: 0.20
Nodes (7): _detect_funds(), collect_fund_phrase_candidates(), _compose_amc_scheme_phrase(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase(), _phrase_specificity_score(), _slurp_scheme_tail_from_question()

### Community 89 - "test_composer_table_summaries.py"
Cohesion: 0.21
Nodes (9): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections() (+1 more)

### Community 90 - "enrich_manager_payload"
Cohesion: 0.22
Nodes (10): build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score(), test_default_manager_answer_drops_former_managers(), test_enrich_filters_past_only() (+2 more)

### Community 91 - "aggregate_fund_holdings.py"
Cohesion: 0.23
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "portfolio_news_impact.py"
Cohesion: 0.14
Nodes (13): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _strip_book_concentration_tables() (+5 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.08
Nodes (52): append_investor_portfolio_overview_tables(), _attach_rs_ratings_to_screen(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_cell(), _compare_header(), _complete_fund_row(), _complete_shown_funds() (+44 more)

### Community 97 - "sector_alignment.py"
Cohesion: 0.17
Nodes (13): clear_macro_impact_cache(), analyze_sector_block(), canonical_sector_for_holding(), holding_return_pct(), holdings_in_sector(), index_return_pct(), return_sign(), run_sector_holding_alignment() (+5 more)

### Community 98 - "graph.py"
Cohesion: 0.11
Nodes (24): _attach_conversation(), build_result(), _compose_hints(), _conversation_id(), _drop_scheme_is_the_whole_book(), _ensure_portfolio_for_fund_news(), GraphState, GraphUnavailable (+16 more)

### Community 99 - "macro_impact_map.py"
Cohesion: 0.23
Nodes (12): _rule_sector_picks(), canonical_direction_for_driver(), _document(), _driver_row(), list_macro_drivers(), macro_impact_entry(), macro_series_for_driver(), normalize_direction() (+4 more)

### Community 100 - "index_series.py"
Cohesion: 0.24
Nodes (9): nifty50_ticker(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns(), _read_cache(), scheme_benchmark_metadata(), _write_cache() (+1 more)

### Community 101 - "strip_missing_data_caveats"
Cohesion: 0.16
Nodes (14): normalize_holding_row(), _group_layered_articles(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows() (+6 more)

### Community 102 - "ask_plan.py"
Cohesion: 0.13
Nodes (20): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), _layered_news_topics(), _client() (+12 more)

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "plan.py"
Cohesion: 0.08
Nodes (22): _warmup_embeddings_background(), _run(), embed_query(), warmup_query_vectors(), _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp() (+14 more)

### Community 106 - "infer_fund_news_layers"
Cohesion: 0.33
Nodes (5): infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only()

### Community 107 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 108 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 109 - "test_guardrails_domain.py"
Cohesion: 0.20
Nodes (11): question_in_finance_scope(), check_guardrails(), financial_keyword_signal(), GuardrailResult, test_crude_why_not_misrouted_to_random_fund(), test_fund_question_still_passes(), test_hdfc_bank_passes_guardrails(), test_hdfc_bank_short_happening_passes() (+3 more)

### Community 110 - "node_compose"
Cohesion: 0.18
Nodes (12): asks_pillar_mark(), pillar_focus(), rating_lead(), render_pillar_marks_table(), node_compose(), _plan_fetches_manager_roster(), _rating_lead_for_pack(), asks_manager_roster() (+4 more)

### Community 111 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 112 - "test_insight_graph.py"
Cohesion: 0.19
Nodes (6): build_data_pack(), build(), _compact(), plan_to_brief(), test_a_nav_lookup_plans_no_news_facets(), test_parse_plan_drops_unknown_tools_and_clamps_values()

### Community 113 - "fund_rating_screen.py"
Cohesion: 0.07
Nodes (52): categories_for(), is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _add_category_comparison() (+44 more)

### Community 114 - "FundUniverseCatalog"
Cohesion: 0.16
Nodes (4): FundEntry, FundUniverseCatalog, _enrich(), match_fund_category()

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "nse_sector_indices.py"
Cohesion: 0.18
Nodes (11): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _clear_index_cache(), test_by_sector_keys_match_sector_queries_exactly(), test_every_sector_has_verified_ticker_field() (+3 more)

### Community 117 - "prompt.py"
Cohesion: 0.15
Nodes (13): greeting_reply(), identity_reply(), _mirror_greeting(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens() (+5 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "main.py"
Cohesion: 0.08
Nodes (21): _merge_publisher_error_reasons(), write_day_report(), _empty_row(), EntityFunnel, get_entity_funnel(), _bucket(), _entity_names(), summarize_errors() (+13 more)

### Community 121 - "test_answer_precision.py"
Cohesion: 0.17
Nodes (9): fact_values_already_stated(), question_wants_fact_table(), strip_meta_opening_heading(), _strip_unasked_closers(), test_fact_table_only_for_compare_or_an_explicit_list(), test_fact_table_skipped_when_prose_has_the_figure(), test_next_steps_and_summary_are_removed(), test_specific_lookup_has_no_default_table() (+1 more)

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "PortfolioError"
Cohesion: 0.25
Nodes (7): PortfolioError, PortfolioUnavailable, PortfolioUpstreamError, test_preload_failure_returns_false(), boom(), test_stale_snapshot_does_not_wait_on_fetch(), slow()

### Community 124 - "get_stock_profile"
Cohesion: 0.26
Nodes (4): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker()

### Community 125 - "fetch_workspace_raw"
Cohesion: 0.43
Nodes (4): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url()

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "news_pipeline/config.py"
Cohesion: 0.21
Nodes (5): Publisher, repo_root(), SectorQuery, main(), test_macro_map_sectors_are_valid_labels()

### Community 128 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 129 - "test_holding_overlap.py"
Cohesion: 0.24
Nodes (8): extra_part_brief(), _compare_return_windows(), _detail(), test_a_comparison_keeps_one_three_and_five_years_plus_benchmark_and_rating(), test_compare_table_includes_risk_for_both_funds(), test_extra_part_brief_names_both_funds(), test_no_overlap_message_and_overlap_table(), test_overlap_uses_full_stock_list_and_skips_cash()

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

### Community 135 - "primary_sector_for_question"
Cohesion: 0.29
Nodes (5): sector_focus_from_market(), primary_sector_for_question(), asks_sector_overview(), test_banking_sector_question_is_an_overview_not_a_fund_list(), test_sector_focus_states_the_gap_versus_the_index()

### Community 137 - "inputs"
Cohesion: 0.29
Nodes (7): default, description, required, type, holdings_limit, workflow_dispatch, inputs

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "slots_from_plan"
Cohesion: 0.17
Nodes (13): asked_slots(), merge_planner_asked_facts(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), slots_from_plan(), plan_wants_fund_concentration() (+5 more)

### Community 141 - "update.py"
Cohesion: 0.11
Nodes (23): drop_old_turns(), compare_payload_matches_funds(), fund_name_mentioned_in_memory(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), empty_frame(), empty_state() (+15 more)

### Community 142 - "explicit_fund_count"
Cohesion: 0.20
Nodes (7): _category_fund_name_spec(), _label_in(), _looks_like_fund_list(), _return_window(), _suggestion_spec(), explicit_fund_count(), explicit_return_window()

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

### Community 145 - "glossary.py"
Cohesion: 0.21
Nodes (10): asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), has_second_part(), meaning_reply(), _normalize_term(), test_fund_nav_not_glossary(), test_nav_full_form_direct_reply() (+2 more)

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

### Community 163 - "fund_risk.py"
Cohesion: 0.09
Nodes (24): asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison(), asks_score_only() (+16 more)

### Community 170 - "fund_catalog.py"
Cohesion: 0.20
Nodes (14): amc_headers_for_hint(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix(), install_amc_catalog(), is_quant_amc_entry() (+6 more)

### Community 174 - "compare_evidence.py"
Cohesion: 0.27
Nodes (7): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 175 - "rank_funds_by_sector_exposure"
Cohesion: 0.16
Nodes (11): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), classify_sector_fund_purity(), is_passive_fund_name(), rank_funds_by_sector_exposure() (+3 more)

### Community 177 - "collect_evidence_calendar_dates"
Cohesion: 0.29
Nodes (5): collect_evidence_calendar_dates(), add_article(), format_user_calendar_date(), _ordinal_day(), test_format_user_calendar_date_and_news_collection()

### Community 178 - "evidence.py"
Cohesion: 0.22
Nodes (12): _take_conversation_slice(), clear_conversation(), note_cache(), recall_slice(), recall_wider_portfolio(), remember_slice(), slice_key(), slice_slot() (+4 more)

### Community 179 - "test_screen_facts.py"
Cohesion: 0.20
Nodes (9): screen_fact_names(), test_any_fund_screen_keeps_requested_aum(), _detail(), test_incomplete_return_column_is_omitted(), test_screen_can_ask_for_several_facts(), test_screen_manager_name_and_experience_are_separate_facts(), test_screen_table_includes_aum(), test_screen_table_includes_manager_name_and_experience() (+1 more)

### Community 180 - "enrich_rankings_with_nav"
Cohesion: 0.19
Nodes (5): enrich_rankings_with_nav(), _fetch_nav_one(), test_ask_engine_delegates_to_insight_pipeline(), test_enrich_rankings_with_nav_any(), test_enrich_rankings_with_nav_positive()

### Community 181 - "extract_top_holdings"
Cohesion: 0.25
Nodes (6): aggregate_sectors_from_holdings(), extract_top_holdings(), normalize_sector_row(), run_fund_portfolio(), scan_schemes_holding_stock(), _one()

### Community 182 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

### Community 183 - "normalize_user_facing_text"
Cohesion: 0.22
Nodes (6): ensure_markdown_table_spacing(), normalize_user_facing_text(), strip_context_disclaimer(), _clean_answer(), test_normalize_inserts_blank_line_before_markdown_table(), test_normalize_na_to_hyphen()

### Community 185 - "top_n_from_question"
Cohesion: 0.36
Nodes (5): top_n_from_question(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

### Community 186 - "article_pool.py"
Cohesion: 0.50
Nodes (4): collect_bundle_articles(), merge_article(), sources_from_articles(), test_collect_bundle_articles_from_tool_results()

### Community 187 - "contains_phrase"
Cohesion: 0.70
Nodes (3): _holding_mentioned(), matches_entity(), contains_phrase()

### Community 188 - "_apply_category_difference"
Cohesion: 0.50
Nodes (3): _apply_category_difference(), _difference_brief(), _user_named_funds()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1462 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `ToolCall`, `investor_subject.py`, `test_holding_overlap.py`, `apply_planner_post_hooks`, `test_fund_drawdown.py`, `slots_from_plan`, `update.py`, `eval_basic_queries.py`, `glossary.py`, `resolve_display_table_policy`, `category_plan.py`, `test_conversation_memory.py`, `fact_answer.py`, `graph.py`, `fund_context.py`, `fund_risk.py`, `test_fund_rating_screen.py`, `compare_evidence.py`, `build_evidence_pack`, `question_is_pure_general_concept`, `test_screen_facts.py`, `test_news_only_answer.py`, `test_fund_risk.py`, `re`, `gold_service.py`, `test_portfolio_layer.py`, `investor_drawback.py`, `parse_plan`, `test_portfolio_startup_cache.py`, `question_is_bullion_metal_price_question`, `test_composer_table_summaries.py`, `portfolio_news_impact.py`, `evidence_pack.py`, `graph.py`, `plan.py`, `node_compose`, `test_insight_graph.py`, `fund_rating_screen.py`, `test_answer_precision.py`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Are the 36 inferred relationships involving `ExecutionPlan` (e.g. with `evaluate_wave2()` and `resolve_compare_fund_pair()`) actually correct?**
  _`ExecutionPlan` has 36 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.0809943865276664 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `get_settings` to `ToolCall`, `investor_subject.py`, `interpret.py`, `portfolio/cache.py`, `test_portfolio_layer.py`, `test_fund_drawdown.py`, `gather.py`, `compute.py`, `QuestionBrief`, `eval_basic_queries.py`, `QueryLogger`, `tool_runners.py`, `news_reader.py`, `Any`, `fund_brief.py`, `execute_capability`, `screen_hints_from_question`, `_run_get_fund_data`, `brief.py`, `json`, `rank_funds_by_sector_exposure`, `llm_client.py`, `embed.py`, `gold_service.py`, `ExecutionPlan`, `typing`, `fund_match.py`, `market_pulse.py`, `test_portfolio_startup_cache.py`, `portfolio_news_impact.py`, `graph.py`, `plan.py`, `node_compose`, `fetch_workspace_raw`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 81 inferred relationships involving `AnswerMode` (e.g. with `evaluate_wave2()` and `build_concept_example_plan()`) actually correct?**
  _`AnswerMode` has 81 INFERRED edges - model-reasoned connections that need verification._
- **Should `ToolCall` be split into smaller, more focused modules?**
  _Cohesion score 0.03269218561543833 - nodes in this community are weakly interconnected._