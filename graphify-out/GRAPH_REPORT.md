# Graph Report - db_design_with_qdrant_locally  (2026-11-17)

## Corpus Check
- 694 files · ~1,094,847 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 31 file(s) not represented in the graph (top: .example 6, .log 5, (none) 4)

## Summary
- 7085 nodes · 22866 edges · 273 communities (212 shown, 61 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 754 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3e3057a5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- Envelope
- fund_rating_screen.py
- interpret.py
- execute_capability
- time_ist.py
- affected_sectors.py
- typing
- grounding.py
- Settings
- graph.py
- update.py
- common/store.py
- compute.py
- v2_scoring.py
- tools.py
- news_rag/config.py
- test_fund_name_gate_and_hydrate.py
- QueryLogger
- news_reader.py
- macro_data.py
- runner.py
- api.py
- main.py
- tool_runners.py
- sector_leaderboard/run.py
- fund_display.py
- gather.py
- pack_sanitize.py
- plan_enforce.py
- nse_fii_dii.py
- investor_subject.py
- NewsStore
- task_exec.py
- llm_client.py
- fund_search.py
- normalize.py
- test_portfolio_layer.py
- plan.py
- env
- test_two_wave_pipeline.py
- article_quality.py
- category_plan.py
- holding_insights/run.py
- env
- _run_screen_funds_by_exposure
- book_news_map.py
- build_evidence_pack
- fund_catalog.py
- app.py
- gold_service.py
- env
- investor_subject.py
- fund_rupeestop_metrics.py
- AnswerMode
- test_sector_leaderboard_run.py
- scrape-worker/package.json
- resolve_fund_for_query
- executor.py
- fund_risk.py
- graph.py
- typing
- re
- validate_capability_args
- fund_universe_agent.py
- batch.ts
- slot_router.py
- insight/guardrails.py
- http-fetch.ts
- embed.py
- portfolio/cache.py
- holdings_market.py
- bullion_retrieve.py
- with
- validate_plan_tools
- sector_fund_ranking.py
- stock_fund_ranking.py
- get_settings
- job.py
- screen_hints_from_question
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- fetch_google_news.py
- lib/portfolio_scope.py
- test_portfolio_startup_cache.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- fetch_category_ratings
- logging.py
- env
- steps
- evidence_pack.py
- test_news_only_answer.py
- NumericRecord
- fields.py
- nav_service.py
- ask_market_bridge.py
- portfolio/client.py
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- ExecutionPlan
- parse_rating_screen
- fund_rating_categories.py
- test_sector_leaderboard_score.py
- test_call_json_llm.py
- insight/portfolio_scope.py
- qdrant_access.py
- news_digest.py
- insights.py
- vitest
- _run_screen_funds_by_exposure
- compare_evidence.py
- compilerOptions
- compilerOptions
- macro_news_cache.py
- test_ai_insight_mospi.py
- backfill
- stitch_display_tables_into_answer
- glossary.py
- CapabilityCache
- run-pipeline
- Settings
- query_log.py
- render_data_only_template
- worker/src/index.ts
- steps
- steps
- with
- json
- test_greeting.py
- generate_json
- inputs
- with
- inputs
- test_daily_cron_settings.py
- fund_scheme_match.py
- test_fund_drawdown.py
- run-backfill.sh
- qdrant
- trends.py
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
- lib/google_news.py
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- top_n_from_question
- display_table_policy.py
- diagnose_lightsail_site.sh
- stock_log.py
- prompts.py
- EntityFunnel
- dataclasses
- parse_rating_screen
- clustering.py
- ai_insight/jobs.py
- validate.py
- insight_links.py
- lib/google_news.py
- test_answer_quality_logs.py
- entity_retrieval.py
- news.py
- build_derived_views
- metals_spot_tables.py
- canonical_key
- Settings
- typing
- QuestionBrief
- 283041/manifest.json
- fund_brief.py
- test_ai_insight.py
- datetime
- 57e233/manifest.json
- test_macro_scope.py
- c72b25/manifest.json
- a45664/manifest.json
- test_composer_table_summaries.py
- 7859f0/manifest.json
- sources/google_news.py
- asks_computed_illustration
- _normalize_fund_text
- repo_root
- Cluster
- MospiError
- insights.js
- holding_insights.js
- insight_log.js
- fix-daily-ingest.sh
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- aggregate_fund_holdings.py
- get_macro_news
- portfolio_news_impact.py
- price.py
- holding_insights/llm.py
- get_stock_profile
- build_top100_holdings.py
- run_insights_daily.sh
- data_pack.py
- install-insights-cron.sh
- plan_system_prompt
- test_rupeestop_auth.py
- fund_name_policy.py
- SectorFundRankingIndex
- ._ensure_loaded
- concept_asks.py
- test_smart_fund_why.py
- holding_insights_stock_log.js
- RunLogger
- planner_catalog_knowledge.py
- strip_news_roundup
- relationships.py
- market_scope_entities
- rating_screen_question
- _unhandled_exception_handler
- _public_pillars

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 607 edges
2. `ToolCall` - 367 edges
3. `get_settings()` - 143 edges
4. `apply_planner_post_hooks()` - 123 edges
5. `AnswerMode` - 108 edges
6. `node_compose()` - 102 edges
7. `QueryLogger` - 100 edges
8. `Settings` - 95 edges
9. `load_config()` - 94 edges
10. `QuestionBrief` - 88 edges

## Surprising Connections (you probably didn't know these)
- `_call()` --calls--> `call_json_llm()`  [EXTRACTED]
  ai_insight/holding_insights/llm.py → news_rag/llm_client.py
- `_qdrant_holding_names()` --uses--> `Settings`  [INFERRED]
  ai_insight/common/entity_retrieval.py → news_pipeline/config.py
- `jev_filter_events()` --uses--> `JevError`  [INFERRED]
  news_rag/fund_brief.py → news_pipeline/jev/client.py
- `fake()` --calls--> `InvalidCRN`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/portfolio/errors.py
- `reject()` --calls--> `InvalidCRN`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/portfolio/errors.py

## Import Cycles
- 2-file cycle: `ai_insight/common/entity_retrieval.py -> ai_insight/common/retrieval_plan.py -> ai_insight/common/entity_retrieval.py`

## Communities (273 total, 61 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (46): get_entity_funnel(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate(), drop_old_points() (+38 more)

### Community 1 - "Envelope"
Cohesion: 0.07
Nodes (52): build(), compose(), _cards(), main(), _build(), _user(), Signal, news_map_block() (+44 more)

### Community 2 - "fund_rating_screen.py"
Cohesion: 0.06
Nodes (49): categories_for(), metal_scheme_categories(), pickable_categories(), _add_category_comparison(), _allocation_mix_spec(), _amc_matches(), _apply_category_difference(), asks_balanced_long_horizon_fund_menu() (+41 more)

### Community 3 - "interpret.py"
Cohesion: 0.08
Nodes (61): Findings, FundFinding, SectorFinding, EvidenceSet, mentions_publication_date(), _assemble(), _caveat(), check_composer_guardrails() (+53 more)

### Community 4 - "execute_capability"
Cohesion: 0.07
Nodes (39): _compare_cache_label(), _compare_payload_matches_funds(), _conversation_id(), execute_capability(), _one_fund(), _keep_conversation_slice(), _positive_ms(), _return_slice_covers() (+31 more)

### Community 5 - "time_ist.py"
Cohesion: 0.07
Nodes (41): _bool(), _float(), _freshness_flag(), _int(), load_config(), ordinal(), notify_failure(), MarketDriverFactsBase (+33 more)

### Community 6 - "affected_sectors.py"
Cohesion: 0.19
Nodes (11): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+3 more)

### Community 7 - "typing"
Cohesion: 0.04
Nodes (72): editorial_context(), market_numbers(), fmt_inr_crore(), cumulative(), FlowDay, history_path(), load_flow_history(), _num() (+64 more)

### Community 8 - "grounding.py"
Cohesion: 0.08
Nodes (35): repair_investor_insight_prose(), strip_grounding_holes(), collect_evidence_calendar_dates(), add_article(), cores_for_float(), cores_in_text(), derived_cores(), finalize_text_fields() (+27 more)

### Community 9 - "Settings"
Cohesion: 0.10
Nodes (26): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), article_in_fetch_window(), has_news_date_range(), iter_inclusive_days(), NewsDateRangeError (+18 more)

### Community 10 - "graph.py"
Cohesion: 0.05
Nodes (45): fact_values_already_stated(), question_wants_concentration_tables(), question_wants_fact_table(), strip_context_disclaimer(), _attach_conversation(), _clean_answer(), _compose_hints(), _conversation_id() (+37 more)

### Community 11 - "update.py"
Cohesion: 0.13
Nodes (22): drop_old_turns(), compare_payload_matches_funds(), push_recent_fund_focus(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), empty_frame(), empty_state() (+14 more)

### Community 12 - "common/store.py"
Cohesion: 0.09
Nodes (38): bundle_exists(), _check_id(), _dump(), exists(), _file(), _is_date(), latest(), list_dates() (+30 more)

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (44): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+36 more)

### Community 14 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 15 - "tools.py"
Cohesion: 0.07
Nodes (54): get_fund_index(), run_driver_affected_funds_adapter(), DataNeed, get_sector_fund_ranking_index(), rank_funds_by_sector_exposure(), _active_sector_equity(), _articles_for_affected_question(), _as_date() (+46 more)

### Community 16 - "news_rag/config.py"
Cohesion: 0.07
Nodes (31): _warmup_embeddings_background(), _run(), embed_query(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors() (+23 more)

### Community 17 - "test_fund_name_gate_and_hydrate.py"
Cohesion: 0.11
Nodes (34): build_result(), _load_planner_memory(), _store_turn_memory(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), chat_history_view(), _chat_turn_rows(), format_chat_history_block() (+26 more)

### Community 18 - "QueryLogger"
Cohesion: 0.08
Nodes (14): jev_filter_events(), ParsedQuery, attach_query_log_meta(), clip_log_text(), find_query_log_file(), _kv(), QueryLogger, read_query_log() (+6 more)

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (38): _article_context_for_interpret(), measured_facts_block(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority() (+30 more)

### Community 20 - "macro_data.py"
Cohesion: 0.17
Nodes (23): BondYieldResult, _client(), _codes(), walk(), CPIRecord, fetch_bond_yields(), fetch_cpi(), fetch_gdp() (+15 more)

### Community 21 - "runner.py"
Cohesion: 0.12
Nodes (30): CommonConfig, _append(), _clock(), RunLog, _write(), _bound_llm(), bundle_cli_main(), cli_main() (+22 more)

### Community 22 - "api.py"
Cohesion: 0.10
Nodes (38): _all_dates(), _bundle_is_live(), create_router(), daily(), dates(), generate(), health(), holding_insights_job_latest() (+30 more)

### Community 23 - "main.py"
Cohesion: 0.08
Nodes (25): _merge_publisher_error_reasons(), write_day_report(), _atomic_write(), day_failure_slices_for_run(), ensure_loaded(), _failures_dir(), flush(), _load_file() (+17 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.11
Nodes (43): build_default_registry(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector(), _infer_driver_direction() (+35 more)

### Community 25 - "sector_leaderboard/run.py"
Cohesion: 0.07
Nodes (58): scrub_refusal_prose(), split_sentences(), SectorLeaderboardFactsBase, _block(), build_user(), _abs_scores(), backtest(), _cell() (+50 more)

### Community 26 - "fund_display.py"
Cohesion: 0.13
Nodes (26): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+18 more)

### Community 27 - "gather.py"
Cohesion: 0.07
Nodes (52): _brief_system(), _run_catalog_screen_fallback(), canonical_facet(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result() (+44 more)

### Community 28 - "pack_sanitize.py"
Cohesion: 0.13
Nodes (19): _fund_performance_digest(), _display_holding_row(), _enrich_investor_computed_fields(), _internal_contribution_row(), investor_holdings_for_display(), merge_holding_pp_into_performance(), _num(), _rollup_investor_summary() (+11 more)

### Community 29 - "plan_enforce.py"
Cohesion: 0.05
Nodes (46): asks_ideal_portfolio_shape(), category_composition_plan_applies(), tag_answer_parts(), ensure_fund_concentration_plan(), node_route(), question_asks_current_book_allocation(), ensure_planner_fund_fact_modules(), apply_category_scoped_compare_funds() (+38 more)

### Community 30 - "nse_fii_dii.py"
Cohesion: 0.23
Nodes (9): _bucket(), _httpx_json(), _impit_json(), _leg(), _log_external(), _nse_json(), _num(), test_bucket_fii_dii() (+1 more)

### Community 31 - "investor_subject.py"
Cohesion: 0.04
Nodes (70): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), _bound_fund_name(), _compare_sides_resolvable(), _known_names_in_text(), question_refers_deictic_fund_safe(), single_fund_for_deictic(), _resolve_funds() (+62 more)

### Community 32 - "NewsStore"
Cohesion: 0.05
Nodes (22): Publisher, SectorQuery, is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), finish_run_logger(), _datetime_range() (+14 more)

### Community 33 - "task_exec.py"
Cohesion: 0.08
Nodes (47): _spaced_category_words(), apply_task_layer(), bind_subjects(), _book_total_line(), _canon_fact(), _category_in_planner_text(), _cell(), _compare_subject_kind() (+39 more)

### Community 34 - "llm_client.py"
Cohesion: 0.08
Nodes (42): anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts(), _call_anthropic(), _call_deepseek(), _call_gemini(), call_insight_llm(), _call_insight_llm_body() (+34 more)

### Community 36 - "fund_search.py"
Cohesion: 0.10
Nodes (22): headline_rating(), build_holding_overlap(), _clean_company_name(), detail_has_live_facts(), _entry_matches_query_scheme(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers() (+14 more)

### Community 37 - "normalize.py"
Cohesion: 0.18
Nodes (21): aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values(), _book_has_market_value(), _fill_missing_from_live(), _first() (+13 more)

### Community 38 - "test_portfolio_layer.py"
Cohesion: 0.07
Nodes (25): _run_get_investor_portfolio(), question_wants_invested_value_table(), get_active_crn(), project_concentration(), _drop_sold(), match_scheme_filter(), _attach_ratings(), _pick_row() (+17 more)

### Community 39 - "plan.py"
Cohesion: 0.10
Nodes (25): explanation_brief(), canonicalize_field(), mentions_advice(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), _label_for_days() (+17 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "test_two_wave_pipeline.py"
Cohesion: 0.09
Nodes (15): ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified() (+7 more)

### Community 42 - "article_quality.py"
Cohesion: 0.11
Nodes (23): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+15 more)

### Community 43 - "category_plan.py"
Cohesion: 0.05
Nodes (53): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), asks_category_performance(), _named_scheme_category(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition() (+45 more)

### Community 44 - "holding_insights/run.py"
Cohesion: 0.17
Nodes (14): _articles_for_log(), _build_batch_outcome(), main(), _news_summary_block(), _persist_run_snapshot(), _process_stock(), run_batch(), _week_change_pct() (+6 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "_run_screen_funds_by_exposure"
Cohesion: 0.07
Nodes (36): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), canonical_direction_for_driver(), clear_macro_impact_cache(), _document() (+28 more)

### Community 47 - "book_news_map.py"
Cohesion: 0.21
Nodes (14): _clean_holding_tokens(), book_wide_sectors(), _display_name(), _has_named_stock(), news_calls_for_book(), _news_name(), _pct(), resolve_book_sector() (+6 more)

### Community 48 - "build_evidence_pack"
Cohesion: 0.06
Nodes (37): EvidenceRow, build_evidence_pack(), _row_bits(), table_source(), has_second_part(), asks_one_figure(), ensure_multi_fact_tools(), screen_fact_names() (+29 more)

### Community 49 - "fund_catalog.py"
Cohesion: 0.19
Nodes (15): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+7 more)

### Community 50 - "app.py"
Cohesion: 0.07
Nodes (53): holding_insights_page(), holding_insights_stock_log_page(), ask(), ask_memory(), ask_query_log(), ask_sources(), ask_stream(), AskRequest (+45 more)

### Community 51 - "gold_service.py"
Cohesion: 0.17
Nodes (16): _fetch(), get_gold_snapshot(), gold_horizon_code(), gold_macro_series_row(), _load_payload(), _merged_series(), add(), _normalize_windows() (+8 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "investor_subject.py"
Cohesion: 0.05
Nodes (60): _catalog_fanout_fund_names(), node_evidence_gate(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan(), ensure_manager_fund_scope() (+52 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.11
Nodes (21): build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns(), normalize_vs_benchmark_payload() (+13 more)

### Community 55 - "AnswerMode"
Cohesion: 0.06
Nodes (47): AnswerMode, QueryClass, ScopeKind, Wave2Policy, sector_focus_from_market(), _invalidate_plan_system_cache(), align_planned_news_execution(), apply_now_window() (+39 more)

### Community 56 - "test_sector_leaderboard_run.py"
Cohesion: 0.14
Nodes (30): LlmJsonResult, LlmUsage, call(), DryRunHalt, build(), compose_headline(), main(), _both_sides() (+22 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "resolve_fund_for_query"
Cohesion: 0.09
Nodes (22): is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), prefer_resolved_fund_name(), resolve_fund_from_question(), test_absl_and_ppfas_shorthand(), test_absl_conservative_hybrid_active_fof() (+14 more)

### Community 59 - "executor.py"
Cohesion: 0.05
Nodes (57): nifty50_ticker(), aggregate_sectors_from_holdings(), extract_top_holdings(), extract_top_sectors(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _conversation_turn() (+49 more)

### Community 60 - "fund_risk.py"
Cohesion: 0.05
Nodes (61): asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison() (+53 more)

### Community 61 - "graph.py"
Cohesion: 0.17
Nodes (14): RequestTelemetry, _answer_stream_chunks(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed(), event_phase_started(), event_quality_check() (+6 more)

### Community 62 - "typing"
Cohesion: 0.08
Nodes (33): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), embed_query(), warmup_query_vectors(), _query_variants(), run_macro_news_enhanced() (+25 more)

### Community 63 - "re"
Cohesion: 0.09
Nodes (28): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+20 more)

### Community 64 - "validate_capability_args"
Cohesion: 0.08
Nodes (31): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), _capability_cache_key(), _age_phrase(), align_plan_windows() (+23 more)

### Community 65 - "fund_universe_agent.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "slot_router.py"
Cohesion: 0.06
Nodes (45): _detect_funds(), question_mentions_fund_scheme(), rating_list_plan(), rating_concept_plan(), asks_fund_category_average(), collect_fund_phrase_candidates(), resolve_fund_for_query(), plan_matches_intent() (+37 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.10
Nodes (21): candidates_block(), entity_candidates(), _holding_candidates(), _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known(), guard_reply() (+13 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "embed.py"
Cohesion: 0.15
Nodes (9): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), embeddings_ready() (+1 more)

### Community 71 - "portfolio/cache.py"
Cohesion: 0.18
Nodes (14): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), get_normalized_portfolio(), peek_derived(), preload_configured_portfolio(), _run() (+6 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "bullion_retrieve.py"
Cohesion: 0.08
Nodes (14): _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), corpus_entity_names(), build_filter(), describe_filters_for_log() (+6 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "validate_plan_tools"
Cohesion: 0.10
Nodes (23): _attach_rs_ratings_to_screen(), owned_holding_names(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), _holdings_breakdown_question(), validate_plan_tools(), _all_holdings_metric_spec() (+15 more)

### Community 77 - "sector_fund_ranking.py"
Cohesion: 0.13
Nodes (13): classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path(), sector_ranking_data_available() (+5 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 79 - "get_settings"
Cohesion: 0.18
Nodes (15): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+7 more)

### Community 80 - "job.py"
Cohesion: 0.19
Nodes (6): HoldingInsightsJobManager, on_progress(), HoldingJobBusy, HoldingJobView, _write(), report()

### Community 81 - "screen_hints_from_question"
Cohesion: 0.09
Nodes (26): execute_wave(), screen_hints_from_question(), test_crude_increase_compound_question_screens_negatively_affected_funds(), test_defence_fund_screen_uses_defense_category(), test_driver_exposure_screen_no_longer_needs_sector_picks_first(), test_fof_fund_screen_returns_fof_schemes(), test_fund_manager_isin_in_question_routes_data_only(), test_fund_manager_query_uses_rupeestop_api() (+18 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.05
Nodes (72): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), _age(), _allocation_bucket_rows() (+64 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "fetch_google_news.py"
Cohesion: 0.13
Nodes (16): _bucket(), _entity_names(), fetch_window_fields(), summarize_errors(), write_error_summary(), _compact_fetch_errors(), fetch_google_news(), covered_calendar_days() (+8 more)

### Community 86 - "lib/portfolio_scope.py"
Cohesion: 0.19
Nodes (15): build_portfolio_scope(), FundRef, _holding_equity_allowed(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest(), load_portfolio_funds() (+7 more)

### Community 87 - "test_portfolio_startup_cache.py"
Cohesion: 0.17
Nodes (17): clear_cache_for_tests(), seed_portfolio_cache_for_tests(), set_active_crn(), test_concentration_question_loads_stock_and_sector_data(), test_executor_with_fixture(), test_repair_empty_investor_tool_calls(), test_switch_evicts_the_previous_crn(), fake() (+9 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.14
Nodes (19): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+11 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 91 - "logging.py"
Cohesion: 0.14
Nodes (10): current_artifacts(), _env_secrets(), log_external(), prune_logs(), _redact(), _redact_text(), _rmtree(), RunArtifacts (+2 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.07
Nodes (49): _add_category_comparison(), append_investor_portfolio_overview_tables(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line(), _compare_cell(), _compare_header(), _complete_fund_row() (+41 more)

### Community 96 - "test_news_only_answer.py"
Cohesion: 0.18
Nodes (10): _news_subject(), clean_news_insight(), complete_sentences(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words(), test_news_about_hdfc_bank_is_not_a_market_pulse() (+2 more)

### Community 97 - "NumericRecord"
Cohesion: 0.17
Nodes (17): NumericRecord, unavailable(), fetch_cpi_record(), pick(), fetch_fii_dii(), fetch_gdp_record(), fetch_gsec(), fetch_gst() (+9 more)

### Community 98 - "fields.py"
Cohesion: 0.09
Nodes (31): _asks_book(), bind_fields_to_tools(), _book_fields(), fields_from_question(), _find_term(), _fund_fields(), _leave_tools_alone(), _legacy_facts() (+23 more)

### Community 99 - "nav_service.py"
Cohesion: 0.13
Nodes (15): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+7 more)

### Community 100 - "ask_market_bridge.py"
Cohesion: 0.23
Nodes (6): fetch_ask_market_records(), fetch_gold_record(), get_ask_market_snapshot(), test_fetch_ask_market_records_includes_extras(), test_fetch_gold_record_ok(), test_get_ask_market_snapshot_shape()

### Community 102 - "portfolio/client.py"
Cohesion: 0.18
Nodes (12): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), InvalidCRN, PortfolioError, PortfolioNotConfigured, PortfolioUnavailable (+4 more)

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.11
Nodes (18): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_PIPELINE_DAILY (+10 more)

### Community 104 - "env"
Cohesion: 0.11
Nodes (18): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL (+10 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.18
Nodes (12): asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score(), test_default_manager_answer_drops_former_managers() (+4 more)

### Community 106 - "ExecutionPlan"
Cohesion: 0.04
Nodes (94): ensure_rating_screen(), _compare_fund_count(), finalize_unnamed_catalog_compare(), _split_count(), ExecutionPlan, LLMUsageRecord, ToolCall, asked_slots() (+86 more)

### Community 107 - "parse_rating_screen"
Cohesion: 0.12
Nodes (32): run_rating_list(), explicit_return_window(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap(), fetch(), test_a_one_month_performer_is_shown_beside_the_same_category_rating(), fetch() (+24 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.12
Nodes (18): CategoryMatch, _close(), fund_type_for_category(), match_all_fund_types(), _metal_category(), _metal_flags(), _names_a_type(), _phrase_score() (+10 more)

### Community 109 - "test_sector_leaderboard_score.py"
Cohesion: 0.10
Nodes (26): sector_label(), _float(), _int(), pick_evidence(), story_weight(), llm_schema(), prominence(), rank() (+18 more)

### Community 110 - "test_call_json_llm.py"
Cohesion: 0.13
Nodes (20): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), _layered_news_topics(), _client() (+12 more)

### Community 111 - "insight/portfolio_scope.py"
Cohesion: 0.07
Nodes (46): attach_drawback_digest(), build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), _pretty_category(), question_asks_portfolio_level_drawdown() (+38 more)

### Community 112 - "qdrant_access.py"
Cohesion: 0.09
Nodes (31): is_stale(), newest_scraped_at(), _as_dict(), _client(), _drop(), _entity_view(), EntityRowsResult, _explode() (+23 more)

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 114 - "insights.py"
Cohesion: 0.30
Nodes (10): build_insights(), _equity_pct(), Insight, insight_lines(), insights_for_brief(), _num(), _style_band(), _book() (+2 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "_run_screen_funds_by_exposure"
Cohesion: 0.11
Nodes (25): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), infer_anchor_label_from_excludes() (+17 more)

### Community 117 - "compare_evidence.py"
Cohesion: 0.24
Nodes (8): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_maybe_run_compare_retries_after_failed_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "macro_news_cache.py"
Cohesion: 0.15
Nodes (13): _run_get_macro_news(), _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read() (+5 more)

### Community 121 - "test_ai_insight_mospi.py"
Cohesion: 0.25
Nodes (10): _client(), _sse(), test_400_is_not_retried(), test_gdp_yoy_uses_prior_fiscal_year(), handler(), test_retries_500_then_reads_cache(), handler(), test_snapshot_keeps_other_entities_when_one_fails() (+2 more)

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "stitch_display_tables_into_answer"
Cohesion: 0.07
Nodes (31): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers() (+23 more)

### Community 124 - "glossary.py"
Cohesion: 0.26
Nodes (10): asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), glossary_execution_plan(), meaning_reply(), _normalize_term(), test_fund_nav_not_glossary(), test_nav_full_form_direct_reply() (+2 more)

### Community 125 - "CapabilityCache"
Cohesion: 0.15
Nodes (6): CapabilityCache, _Entry, get_capability_cache(), test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner()

### Community 126 - "run-pipeline"
Cohesion: 0.29
Nodes (6): jobs, run-pipeline, name, on, runs-on, timeout-minutes

### Community 127 - "Settings"
Cohesion: 0.10
Nodes (16): Settings, apply_fresh_start(), _clear_run_json_summaries(), google_time_query(), clear_scrape_workspace(), remove_scrape_artifacts(), remove_scrape_artifacts_many(), url_artifact_stem() (+8 more)

### Community 128 - "query_log.py"
Cohesion: 0.10
Nodes (15): _events(), run_ask_engine(), stream_ask_engine(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), run_insight_pipeline() (+7 more)

### Community 129 - "render_data_only_template"
Cohesion: 0.08
Nodes (25): normalize_holding_row(), normalize_sector_row(), EvidencePack, _holding_label(), _holding_weight_pct(), _portfolio_markdown(), _portfolio_top_n(), render_data_only_template() (+17 more)

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

### Community 134 - "json"
Cohesion: 0.05
Nodes (35): explain(), main(), _short(), main(), prune_insight_logs(), _json_default(), safe_json_dumps(), main() (+27 more)

### Community 135 - "test_greeting.py"
Cohesion: 0.27
Nodes (7): greeting_reply(), identity_reply(), _mirror_greeting(), test_fund_question_is_not_greeting_or_identity(), test_hello_mirrors_greeting(), test_main_memory_in_prompt_view(), test_who_are_you_identity()

### Community 136 - "generate_json"
Cohesion: 0.14
Nodes (21): _add_usage(), _default_call(), format_articles_block(), generate_json(), _invoke_with_retry(), LlmSchemaError, LlmUnavailable, _run_bounded() (+13 more)

### Community 137 - "inputs"
Cohesion: 0.40
Nodes (5): default, description, required, type, holdings_limit

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 141 - "fund_scheme_match.py"
Cohesion: 0.13
Nodes (21): is_quant_amc_entry(), is_quantum_amc_entry(), amc_token_in_question(), _category_phrases_in_question(), _constraint_in_scheme_name(), _distinctive_constraints(), pick_best_matching_scheme(), question_amc_hints() (+13 more)

### Community 142 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (55): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+47 more)

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

### Community 146 - "trends.py"
Cohesion: 0.13
Nodes (14): detect_signals(), _surge(), DayPoint, entity_daily_series(), price_trend(), price_trend_from_closes(), PriceTrend, session_day() (+6 more)

### Community 147 - "extract.ts"
Cohesion: 0.80
Nodes (4): decodeHtmlEntities(), extractFromHtml(), metaContent(), stripTags()

### Community 148 - "sync-news-runs-to-r2.sh"
Cohesion: 0.40
Nodes (4): AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION, AWS_SECRET_ACCESS_KEY, sync-news-runs-to-r2.sh script

### Community 149 - "date_range"
Cohesion: 0.29
Nodes (7): default, description, required, type, date_range, workflow_dispatch, inputs

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

### Community 159 - "lib/google_news.py"
Cohesion: 0.07
Nodes (21): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), article_id_from_url(), _batchexecute(), cached_resolve() (+13 more)

### Community 163 - "fund_match.py"
Cohesion: 0.11
Nodes (14): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+6 more)

### Community 169 - "top_n_from_question"
Cohesion: 0.29
Nodes (5): top_n_from_question(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

### Community 170 - "display_table_policy.py"
Cohesion: 0.11
Nodes (18): DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary(), _plan_fetches_vs_benchmark() (+10 more)

### Community 174 - "stock_log.py"
Cohesion: 0.32
Nodes (8): holding_data_dir(), build_log_document(), load_stock_log(), _price_summary(), render_markdown(), save_stock_log(), stock_logs_dir(), test_save_and_load_stock_log()

### Community 178 - "prompts.py"
Cohesion: 0.25
Nodes (5): build_brief_prompt(), build_composer_prompt(), build_interpret_hybrid_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 180 - "dataclasses"
Cohesion: 0.10
Nodes (14): analyst_should_run(), publication_date_keys(), _drop_pipeline_voice(), _attribution_judge(), _grounding_blob(), verify_answer(), VerifyResult, candidate_sector_names() (+6 more)

### Community 181 - "parse_rating_screen"
Cohesion: 0.06
Nodes (33): asks_taxonomy(), _amc_outside_label(), _amc_token(), asks_rating_list(), ensure_quality_fund_list(), _fund_type_in_name_clause(), fund_type_name_spec(), _looks_like_fund_list() (+25 more)

### Community 182 - "clustering.py"
Cohesion: 0.16
Nodes (18): _adapter(), cluster_rows(), _collapse(), _dedupe(), find(), union(), _group_of(), _keys() (+10 more)

### Community 183 - "ai_insight/jobs.py"
Cohesion: 0.13
Nodes (7): JobProgress, _write(), JobBusy, JobManager, JobView, _write(), test_job_isolates_one_failure()

### Community 184 - "validate.py"
Cohesion: 0.19
Nodes (19): numeric_leaves(), walk(), _allowed_numbers(), _banned(), _blob(), walk(), _body(), CheckResult (+11 more)

### Community 185 - "insight_links.py"
Cohesion: 0.11
Nodes (19): _group_layered_articles(), strip_missing_data_caveats(), strip_private_leaks(), build_insight_links(), _fact(), _key(), _match(), _pct() (+11 more)

### Community 186 - "lib/google_news.py"
Cohesion: 0.06
Nodes (27): _backoff(), _consent_jar(), _fetch_http_get(), fetch_publisher_url(), fetch_url(), _handle_google_response(), make_session(), post_url() (+19 more)

### Community 187 - "test_answer_quality_logs.py"
Cohesion: 0.12
Nodes (17): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), question_wants_gold_table(), facts_only_compose_allowed(), scrub_unknown_fund_mentions(), node_resolve() (+9 more)

### Community 188 - "entity_retrieval.py"
Cohesion: 0.13
Nodes (30): bellwether_holdings(), EntityPack, evidence_from_clusters(), fetch_entity_pack(), fetch_fii_dii(), fetch_macro_packs(), work(), fetch_market_driver() (+22 more)

### Community 190 - "news.py"
Cohesion: 0.17
Nodes (13): llm_allow_fallback(), _fetch_rows(), get_top_news(), news_window(), NewsArticle, NewsBundle, _published_in_window(), _rows_to_articles() (+5 more)

### Community 191 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 193 - "canonical_key"
Cohesion: 0.19
Nodes (12): _resolve_bellwether(), rank(), match_holding_to_corpus_entity(), _fund_stats_from_csv(), load_holdings_rows_from_xlsx(), multi_query_for(), _strip_legal_suffix(), canonical_key() (+4 more)

### Community 194 - "Settings"
Cohesion: 0.14
Nodes (17): resolve_allisin_holdings_path(), load_portfolio_universe(), _aliases_for(), build_holding_entities(), _display_name(), _holding_query(), _industry_search_hint(), _is_exchange_label() (+9 more)

### Community 195 - "typing"
Cohesion: 0.08
Nodes (18): enforce_prompt_budget(), EvidenceArticle, format_evidence_block(), _data(), _dump(), LoopResult, _problems(), run_quality_loop() (+10 more)

### Community 197 - "QuestionBrief"
Cohesion: 0.10
Nodes (27): asks_market_briefing(), asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), build_question_brief(), _detect_direction(), _heuristic_brief() (+19 more)

### Community 198 - "283041/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 203 - "fund_brief.py"
Cohesion: 0.09
Nodes (35): instrument_to_qdrant_names(), PortfolioScope, qdrant_filter_names(), Settings, _article_entities(), build_events(), cluster_articles(), _cluster_entities() (+27 more)

### Community 206 - "test_ai_insight.py"
Cohesion: 0.18
Nodes (6): digest_filter(), _holding_mentioned(), matches_entity(), contains_phrase(), test_digest_filter_uses_stricter_scores(), test_sector_exclude_drops_nbfc_from_banks()

### Community 208 - "datetime"
Cohesion: 0.16
Nodes (18): _bars(), catalog_path(), fetch_ohlc(), IndexSpec, load_catalog(), news_sectors_for_index(), OhlcBar, series_is_usable() (+10 more)

### Community 209 - "57e233/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 211 - "test_macro_scope.py"
Cohesion: 0.12
Nodes (17): question_is_standalone_macro(), apply_pure_concept_plan(), question_is_pure_general_concept(), ensure_catalog_tools_for_fund_news(), apply_standalone_macro_scope(), _macro_news_topics(), test_all_holdings_metrics_adds_investor_tool(), test_large_cap_vs_mid_cap_is_pure_concept() (+9 more)

### Community 212 - "c72b25/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 213 - "a45664/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 214 - "test_composer_table_summaries.py"
Cohesion: 0.27
Nodes (7): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections()

### Community 217 - "7859f0/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 218 - "sources/google_news.py"
Cohesion: 0.18
Nodes (13): is_google_exhausted(), _fetch_query_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url(), canonical_url(), host_matches(), host_of() (+5 more)

### Community 219 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

### Community 221 - "_normalize_fund_text"
Cohesion: 0.15
Nodes (12): _attach_trailing_product(), _clean_fund_phrase(), add(), _compose_amc_scheme_phrase(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question(), _is_bullion_phrase_not_scheme() (+4 more)

### Community 222 - "repo_root"
Cohesion: 0.37
Nodes (9): write_ask_market_snapshot(), FiiDiiSnapshot, write_snapshot(), fetch_fii_dii_snapshot(), fetch_all(), main(), write_fii_dii(), write_latest() (+1 more)

### Community 223 - "Cluster"
Cohesion: 0.26
Nodes (14): Cluster, cluster_score(), rank_clusters(), Drivers, is_index_recap(), move_phrase(), move_size(), _names() (+6 more)

### Community 224 - "MospiError"
Cohesion: 0.25
Nodes (5): _cache_dir(), MospiClient, MospiError, _payload(), _sse_json()

### Community 225 - "insights.js"
Cohesion: 0.22
Nodes (18): api(), arrow(), bars(), card(), chart(), diverging(), esc(), headers() (+10 more)

### Community 226 - "holding_insights.js"
Cohesion: 0.36
Nodes (13): api(), clearError(), escapeHtml(), headers(), loadSaved(), logLink(), poll(), rememberJob() (+5 more)

### Community 227 - "insight_log.js"
Cohesion: 0.70
Nodes (4): api(), esc(), headers(), load()

### Community 230 - "aggregate_fund_holdings.py"
Cohesion: 0.20
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 232 - "get_macro_news"
Cohesion: 0.21
Nodes (10): select_macro_for_question(), _digest(), test_cache_searches_named_macro_parameters(), test_failed_refresh_keeps_the_previous_cache(), test_macro_news_is_reused_for_two_hours_then_overwritten(), fetch(), test_question_gets_two_articles_from_each_leading_section(), test_seven_day_question_uses_the_seven_day_cache() (+2 more)

### Community 233 - "portfolio_news_impact.py"
Cohesion: 0.18
Nodes (12): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _rule_sector_picks() (+4 more)

### Community 236 - "price.py"
Cohesion: 0.17
Nodes (6): history_closes(), latest_quote(), _consecutive_down_days(), DayBar, get_price_snapshot(), test_consecutive_down_days()

### Community 237 - "holding_insights/llm.py"
Cohesion: 0.14
Nodes (21): _as_paragraph(), call_holding_llm(), _call(), _headline_week_matches(), _normalize_response(), parse_insight_lines(), _pct_in_text(), _pct_matches_week_change() (+13 more)

### Community 238 - "get_stock_profile"
Cohesion: 0.19
Nodes (6): get_silver_snapshot(), format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker(), test_silver_stub_is_news_only()

### Community 239 - "build_top100_holdings.py"
Cohesion: 0.38
Nodes (7): check_yfinance(), load_master_index(), lookup_master(), main(), normalize_name(), pick_best_master(), resolve_yf_ticker()

### Community 240 - "run_insights_daily.sh"
Cohesion: 0.50
Nodes (4): note(), PYTHONPATH, PYTHONUNBUFFERED, run_insights_daily.sh script

### Community 241 - "data_pack.py"
Cohesion: 0.22
Nodes (6): build_data_pack(), build(), _compact(), plan_to_brief(), test_a_nav_lookup_plans_no_news_facets(), test_data_pack_groups_by_fund_and_hides_internal_fields()

### Community 252 - "plan_system_prompt"
Cohesion: 0.19
Nodes (9): field_prompt_table(), plan_system_prompt(), build_anthropic_messages_body(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), _body(), test_planner_and_composer_share_the_first_system_block() (+1 more)

### Community 253 - "test_rupeestop_auth.py"
Cohesion: 0.12
Nodes (8): rupeestop_admin_request_headers(), _jwt(), test_admin_headers_include_bearer(), test_admin_headers_use_token_from_login(), test_bearer_prefers_auth_token_over_admin_token(), test_failed_login_keeps_previous_token(), test_non_admin_url_has_no_authorization(), test_valid_jwt_does_not_call_login()

### Community 254 - "fund_name_policy.py"
Cohesion: 0.24
Nodes (11): enforce_user_authorized_funds_only(), fund_authorized_for_question(), _named_in_chat_turns(), plan_allows_server_fund_pick(), test_compare_both_still_rebinds_after_strip(), test_compare_these_two_funds_binds_chat_pair(), test_invented_funds_stripped_when_not_in_chat(), test_prior_answer_names_are_authorized() (+3 more)

### Community 256 - "._ensure_loaded"
Cohesion: 0.18
Nodes (3): FundIndex, _infer_category_and_type(), _sync_amc_prefix_from_catalog()

### Community 257 - "concept_asks.py"
Cohesion: 0.31
Nodes (10): apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), asks_fof_funds(), test_concept_example_plan_screen_fof(), test_fof_name_one_detected() (+2 more)

### Community 259 - "test_smart_fund_why.py"
Cohesion: 0.24
Nodes (5): _detect_funds(), _infer_window_days(), test_composer_guardrails(), test_fuzzy_fund_why_detection(), test_streaming_sse_order()

### Community 260 - "holding_insights_stock_log.js"
Cohesion: 0.60
Nodes (5): api(), escapeHtml(), headers(), load(), render()

### Community 263 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 264 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 266 - "relationships.py"
Cohesion: 0.42
Nodes (5): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships()

### Community 267 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

### Community 268 - "rating_screen_question"
Cohesion: 0.50
Nodes (3): fund_naming_clause(), rating_screen_question(), test_debt_fund_type_not_confused_by_equity_education_clause()

## Knowledge Gaps
- **26 isolated node(s):** `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT` (+21 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1963 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **61 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `concept_asks.py`, `fund_rating_screen.py`, `render_data_only_template`, `graph.py`, `test_fund_drawdown.py`, `test_fund_name_gate_and_hydrate.py`, `macro_data.py`, `plan_enforce.py`, `investor_subject.py`, `task_exec.py`, `test_portfolio_layer.py`, `plan.py`, `test_two_wave_pipeline.py`, `display_table_policy.py`, `category_plan.py`, `top_n_from_question`, `book_news_map.py`, `build_evidence_pack`, `gold_service.py`, `investor_subject.py`, `parse_rating_screen`, `AnswerMode`, `test_answer_quality_logs.py`, `fund_risk.py`, `validate_capability_args`, `slot_router.py`, `validate_plan_tools`, `fact_answer.py`, `test_macro_scope.py`, `test_composer_table_summaries.py`, `test_portfolio_startup_cache.py`, `test_portfolio_allocation.py`, `evidence_pack.py`, `test_news_only_answer.py`, `fields.py`, `portfolio_news_impact.py`, `enrich_manager_payload`, `parse_rating_screen`, `insight/portfolio_scope.py`, `data_pack.py`, `compare_evidence.py`, `glossary.py`, `fund_name_policy.py`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `ExecutionPlan` (e.g. with `news_calls_for_book()` and `sector_book()`) actually correct?**
  _`ExecutionPlan` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN` to the rest of the system?**
  _26 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.07346024636058231 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ExecutionPlan` to `concept_asks.py`, `fund_rating_screen.py`, `render_data_only_template`, `execute_capability`, `graph.py`, `update.py`, `test_fund_drawdown.py`, `test_fund_name_gate_and_hydrate.py`, `macro_data.py`, `plan_enforce.py`, `investor_subject.py`, `task_exec.py`, `test_portfolio_layer.py`, `plan.py`, `test_two_wave_pipeline.py`, `top_n_from_question`, `category_plan.py`, `display_table_policy.py`, `book_news_map.py`, `build_evidence_pack`, `gold_service.py`, `parse_rating_screen`, `investor_subject.py`, `AnswerMode`, `executor.py`, `test_answer_quality_logs.py`, `fund_risk.py`, `validate_capability_args`, `slot_router.py`, `validate_plan_tools`, `screen_hints_from_question`, `test_macro_scope.py`, `test_portfolio_startup_cache.py`, `test_portfolio_allocation.py`, `test_news_only_answer.py`, `fields.py`, `portfolio_news_impact.py`, `parse_rating_screen`, `insight/portfolio_scope.py`, `data_pack.py`, `compare_evidence.py`, `CapabilityCache`, `fund_name_policy.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ToolCall` (e.g. with `news_calls_for_book()` and `_apply_planner_request()`) actually correct?**
  _`ToolCall` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `Envelope` be split into smaller, more focused modules?**
  _Cohesion score 0.0708548479632817 - nodes in this community are weakly interconnected._