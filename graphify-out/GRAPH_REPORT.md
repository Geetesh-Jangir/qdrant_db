# Graph Report - db_design_with_qdrant_locally  (2026-11-17)

## Corpus Check
- 692 files · ~1,092,863 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 31 file(s) not represented in the graph (top: .example 6, .log 5, (none) 4)

## Summary
- 7049 nodes · 22762 edges · 261 communities (204 shown, 57 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 753 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1357b104`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- Envelope
- fund_rating_screen.py
- interpret.py
- CommonConfig
- time_ist.py
- get_sector_fund_ranking_index
- typing
- grounding.py
- Settings
- GraphState
- update.py
- Envelope
- compute.py
- v2_scoring.py
- tools.py
- news_rag/config.py
- test_fund_name_gate_and_hydrate.py
- QueryLogger
- news_reader.py
- macro_data.py
- runner.py
- project_modules
- main.py
- tool_runners.py
- sector_leaderboard/run.py
- fund_display.py
- gather.py
- pack_sanitize.py
- plan_enforce.py
- nse_fii_dii.py
- fund_context.py
- NewsStore
- task_exec.py
- llm_client.py
- api.py
- fund_search.py
- normalize.py
- test_portfolio_layer.py
- plan.py
- env
- normalize_rs_label
- article_quality.py
- category_plan.py
- holding_insights/run.py
- env
- _run_screen_funds_by_exposure
- book_news_map.py
- ToolCall
- fund_catalog.py
- app.py
- gold_service.py
- env
- investor_subject.py
- fund_rupeestop_metrics.py
- re
- test_sector_leaderboard_run.py
- scrape-worker/package.json
- resolve_fund_for_query
- executor.py
- test_fund_risk.py
- graph.py
- typing
- re
- nav_service.py
- fund_universe_agent.py
- batch.ts
- slot_route
- insight/guardrails.py
- http-fetch.ts
- embed.py
- portfolio/cache.py
- holdings_market.py
- parse.py
- with
- node_route
- sector_fund_ranking.py
- stock_fund_ranking.py
- get_settings
- job.py
- validate.py
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- fetch_google_news.py
- test_ai_insight_quality.py
- ExecutionPlan
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
- clustering.py
- price.py
- portfolio/client.py
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- portfolio_news_impact.py
- parse_rating_screen
- fund_rating_categories.py
- test_guardrails_domain.py
- test_call_json_llm.py
- test_portfolio_intents.py
- qdrant_access.py
- news_digest.py
- insights.py
- vitest
- format_inr
- compare_evidence.py
- compilerOptions
- compilerOptions
- macro_news_cache.py
- test_ai_insight_mospi.py
- backfill
- stitch_display_tables_into_answer
- glossary.py
- execute_capability
- run-pipeline
- bridge.py
- query_log.py
- layer_tools.py
- worker/src/index.ts
- steps
- steps
- with
- json
- test_greeting.py
- node_compose
- inputs
- with
- inputs
- test_investor_grounding.py
- fund_type_name_spec
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
- RunLogger
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_scheme_match.py
- generate_json
- diagnose_lightsail_site.sh
- stock_log.py
- PublisherStats
- EntityFunnel
- test_sector_leaderboard_score.py
- test_metal_fund_rating.py
- assemble_fund_overview_answer
- ai_insight/jobs.py
- eval_planner.py
- insight_links.py
- lib/google_news.py
- test_answer_quality_logs.py
- entity_retrieval.py
- news.py
- build_derived_views
- metals_spot_tables.py
- _normalize_fund_text
- Settings
- httpx
- QuestionBrief
- 283041/manifest.json
- fund_brief.py
- test_ai_insight.py
- load_config
- 57e233/manifest.json
- test_macro_scope.py
- c72b25/manifest.json
- a45664/manifest.json
- test_composer_table_summaries.py
- 7859f0/manifest.json
- sources/google_news.py
- asks_computed_illustration
- strip_news_roundup
- repo_root
- test_holding_overlap.py
- MospiError
- insights.js
- holding_insights.js
- insight_log.js
- market_scope_entities
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- aggregate_fund_holdings.py
- json_util.py
- get_macro_news
- planner_catalog_knowledge.py
- _apply_category_difference
- holding_insights/llm.py
- test_answer_precision.py
- build_top100_holdings.py
- run_insights_daily.sh
- data_pack.py
- install-insights-cron.sh
- _public_pillars
- test_rupeestop_auth.py
- test_short_category_moves_to_another_with_two_funds
- holding_insights_stock_log.js
- test_snapshot_uses_payload_returns_and_history_only_for_gaps

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 607 edges
2. `ToolCall` - 367 edges
3. `get_settings()` - 143 edges
4. `apply_planner_post_hooks()` - 123 edges
5. `AnswerMode` - 108 edges
6. `node_compose()` - 102 edges
7. `QueryLogger` - 100 edges
8. `load_config()` - 94 edges
9. `Settings` - 93 edges
10. `QuestionBrief` - 88 edges

## Surprising Connections (you probably didn't know these)
- `_call()` --calls--> `call_json_llm()`  [EXTRACTED]
  ai_insight/holding_insights/llm.py → news_rag/llm_client.py
- `boom()` --calls--> `PortfolioError`  [EXTRACTED]
  tests/test_portfolio_startup_cache.py → news_rag/portfolio/errors.py
- `slow()` --calls--> `PortfolioError`  [EXTRACTED]
  tests/test_portfolio_startup_cache.py → news_rag/portfolio/errors.py
- `test_gate_boundaries()` --uses--> `GateConfig`  [INFERRED]
  tests/test_ai_insight_common_qdrant_access.py → ai_insight/common/qdrant_access.py
- `fetch_google_news()` --uses--> `GoogleBlockedError`  [INFERRED]
  news_pipeline/graph/nodes/fetch_google_news.py → lib/google_guard.py

## Import Cycles
- 2-file cycle: `ai_insight/common/entity_retrieval.py -> ai_insight/common/retrieval_plan.py -> ai_insight/common/entity_retrieval.py`

## Communities (261 total, 57 thin omitted)

### Community 0 - "logging"
Cohesion: 0.08
Nodes (43): get_encoder(), get_entity_funnel(), build_graph(), dedupe_and_alias(), drop_old_points(), embed_and_upsert(), _to_article(), jev_article_scores() (+35 more)

### Community 1 - "Envelope"
Cohesion: 0.07
Nodes (47): build(), compose(), _cards(), main(), _build(), _user(), Signal, news_map_block() (+39 more)

### Community 2 - "fund_rating_screen.py"
Cohesion: 0.07
Nodes (45): categories_for(), metal_scheme_categories(), pickable_categories(), _add_category_comparison(), _allocation_mix_spec(), _amc_matches(), _amc_outside_label(), _amc_token() (+37 more)

### Community 3 - "interpret.py"
Cohesion: 0.06
Nodes (61): Findings, FundFinding, SectorFinding, _assemble(), _caveat(), check_composer_guardrails(), _claim_for_sector(), _claim_map() (+53 more)

### Community 4 - "CommonConfig"
Cohesion: 0.16
Nodes (22): CommonConfig, build_aligned_table(), _done(), _flow_data(), _from_history(), get_fii_dii_today(), get_index_history(), get_nifty() (+14 more)

### Community 5 - "time_ist.py"
Cohesion: 0.10
Nodes (28): MarketDriverFactsBase, fmt_ist(), _resolve_end(), rolling_window(), session_window(), to_ist(), week_window(), _closed_dates() (+20 more)

### Community 6 - "get_sector_fund_ranking_index"
Cohesion: 0.08
Nodes (28): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+20 more)

### Community 7 - "typing"
Cohesion: 0.05
Nodes (52): editorial_context(), market_numbers(), fmt_inr_crore(), ordinal(), cumulative(), FlowDay, history_path(), load_flow_history() (+44 more)

### Community 8 - "grounding.py"
Cohesion: 0.07
Nodes (35): analyst_should_run(), asks_market_briefing(), collect_evidence_calendar_dates(), add_article(), cores_in_text(), finalize_text_fields(), format_user_calendar_date(), mentions_publication_date() (+27 more)

### Community 9 - "Settings"
Cohesion: 0.07
Nodes (33): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), article_in_fetch_window(), google_time_query(), has_news_date_range(), iter_inclusive_days() (+25 more)

### Community 10 - "GraphState"
Cohesion: 0.08
Nodes (33): _answer_stream_chunks(), _attach_conversation(), build_result(), _catalog_fanout_fund_names(), _conversation_id(), _ensure_portfolio_for_fund_news(), GraphState, _insight_headline_narrative() (+25 more)

### Community 11 - "update.py"
Cohesion: 0.14
Nodes (21): drop_old_turns(), compare_payload_matches_funds(), push_recent_fund_focus(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), empty_frame(), empty_state() (+13 more)

### Community 12 - "Envelope"
Cohesion: 0.10
Nodes (38): bundle_exists(), _check_id(), _dump(), exists(), _file(), _is_date(), latest(), list_dates() (+30 more)

### Community 13 - "compute.py"
Cohesion: 0.08
Nodes (48): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+40 more)

### Community 14 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (61): extract_top_sectors(), get_fund_index(), run_driver_affected_funds_adapter(), DataNeed, get_sector_fund_ranking_index(), rank_funds_by_sector_exposure(), _active_sector_equity(), _args_from_question() (+53 more)

### Community 16 - "news_rag/config.py"
Cohesion: 0.06
Nodes (34): _warmup_embeddings_background(), _run(), embed_query(), warmup_query_vectors(), corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news() (+26 more)

### Community 17 - "test_fund_name_gate_and_hydrate.py"
Cohesion: 0.13
Nodes (29): _load_planner_memory(), _store_turn_memory(), drain_cache_events(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), chat_history_view(), append_chat_turn(), _fresh() (+21 more)

### Community 18 - "QueryLogger"
Cohesion: 0.08
Nodes (13): run_market_pulse(), ParsedQuery, attach_query_log_meta(), clip_log_text(), find_query_log_file(), _kv(), QueryLogger, _shrink_for_log() (+5 more)

### Community 19 - "news_reader.py"
Cohesion: 0.09
Nodes (38): _article_context_for_interpret(), measured_facts_block(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority() (+30 more)

### Community 20 - "macro_data.py"
Cohesion: 0.16
Nodes (25): BondYieldResult, _client(), _codes(), walk(), CPIRecord, fetch_bond_yields(), fetch_cpi(), fetch_gdp() (+17 more)

### Community 21 - "runner.py"
Cohesion: 0.13
Nodes (29): _append(), _clock(), RunLog, _write(), _bound_llm(), bundle_cli_main(), cli_main(), _failed() (+21 more)

### Community 22 - "project_modules"
Cohesion: 0.16
Nodes (8): match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore, test_project_holdings_fields(), test_project_pnl_scheme_without_filter_returns_schemes()

### Community 23 - "main.py"
Cohesion: 0.07
Nodes (27): _merge_publisher_error_reasons(), write_day_report(), _atomic_write(), day_failure_slices_for_run(), ensure_loaded(), _failures_dir(), flush(), _load_file() (+19 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.12
Nodes (40): headline_rating(), build_default_registry(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+32 more)

### Community 25 - "sector_leaderboard/run.py"
Cohesion: 0.08
Nodes (55): split_sentences(), _block(), build_user(), _abs_scores(), backtest(), _cell(), _chips(), compose_body() (+47 more)

### Community 26 - "fund_display.py"
Cohesion: 0.12
Nodes (27): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+19 more)

### Community 27 - "gather.py"
Cohesion: 0.07
Nodes (50): _brief_system(), canonical_facet(), _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence() (+42 more)

### Community 28 - "pack_sanitize.py"
Cohesion: 0.08
Nodes (29): append_investor_portfolio_overview_tables(), _fund_performance_digest(), render_investor_invested_value_table(), strip_unasked_scheme_names(), attach_drawback_digest(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer() (+21 more)

### Community 29 - "plan_enforce.py"
Cohesion: 0.04
Nodes (75): asks_ideal_portfolio_shape(), category_composition_plan_applies(), tag_answer_parts(), enforce_user_authorized_funds_only(), fund_authorized_for_question(), _named_in_chat_turns(), plan_allows_server_fund_pick(), question_asks_current_book_allocation() (+67 more)

### Community 30 - "nse_fii_dii.py"
Cohesion: 0.20
Nodes (11): current_artifacts(), log_external(), _bucket(), _httpx_json(), _impit_json(), _leg(), _log_external(), _nse_json() (+3 more)

### Community 31 - "fund_context.py"
Cohesion: 0.05
Nodes (58): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), _bound_fund_name(), clarify_plan_if_fund_unknown(), _compare_sides_resolvable(), _known_names_in_text(), _plan_uses_fund_scoped_tools(), scrub_unknown_fund_mentions() (+50 more)

### Community 32 - "NewsStore"
Cohesion: 0.09
Nodes (14): is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), _datetime_range(), NewsStore, point_id_for_url(), to_iso() (+6 more)

### Community 33 - "task_exec.py"
Cohesion: 0.08
Nodes (46): _spaced_category_words(), apply_task_layer(), bind_subjects(), _book_total_line(), _canon_fact(), _category_in_planner_text(), _cell(), _compare_subject_kind() (+38 more)

### Community 34 - "llm_client.py"
Cohesion: 0.07
Nodes (55): ask(), ask_stream(), AskRequest, _attach_llm_meta(), fund_brief(), health(), get_settings(), anthropic_cache_control() (+47 more)

### Community 35 - "api.py"
Cohesion: 0.09
Nodes (41): _all_dates(), _bundle_is_live(), create_router(), daily(), dates(), generate(), health(), holding_insights_job_latest() (+33 more)

### Community 36 - "fund_search.py"
Cohesion: 0.10
Nodes (23): aggregate_sectors_from_holdings(), build_holding_overlap(), _clean_company_name(), detail_has_live_facts(), _entry_matches_amc(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers() (+15 more)

### Community 37 - "normalize.py"
Cohesion: 0.18
Nodes (21): aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values(), _book_has_market_value(), _fill_missing_from_live(), _first() (+13 more)

### Community 38 - "test_portfolio_layer.py"
Cohesion: 0.09
Nodes (15): question_wants_invested_value_table(), project_concentration(), _drop_sold(), normalized_doc(), test_allocation_drops_dust_and_matches_book_aum(), test_book_schemes_are_the_open_holdings(), test_concentration_keeps_cash(), test_current_value_and_nonzero_xirr() (+7 more)

### Community 39 - "plan.py"
Cohesion: 0.06
Nodes (36): explanation_brief(), field_prompt_table(), mentions_advice(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), _invalidate_plan_system_cache() (+28 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "normalize_rs_label"
Cohesion: 0.13
Nodes (21): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), infer_anchor_label_from_excludes() (+13 more)

### Community 42 - "article_quality.py"
Cohesion: 0.11
Nodes (23): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+15 more)

### Community 43 - "category_plan.py"
Cohesion: 0.05
Nodes (53): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), asks_category_performance(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), asks_cross_category_compare() (+45 more)

### Community 44 - "holding_insights/run.py"
Cohesion: 0.18
Nodes (9): main(), _process_stock(), run_batch(), _write_stock_log(), log_page_path(), load_top_stocks(), StockRow, test_no_news_skips_llm() (+1 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "_run_screen_funds_by_exposure"
Cohesion: 0.06
Nodes (43): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _run_screen_funds_by_exposure(), _named_scheme_category(), _rule_sector_picks() (+35 more)

### Community 47 - "book_news_map.py"
Cohesion: 0.21
Nodes (14): _clean_holding_tokens(), book_wide_sectors(), _display_name(), _has_named_stock(), news_calls_for_book(), _news_name(), _pct(), resolve_book_sector() (+6 more)

### Community 48 - "ToolCall"
Cohesion: 0.03
Nodes (86): ensure_rating_screen(), _followup_modules(), asks_fund_risk(), asks_hidden_rating(), asks_private_system(), asks_risk_trend_comparison(), asks_score_only(), blocked_reply() (+78 more)

### Community 49 - "fund_catalog.py"
Cohesion: 0.15
Nodes (19): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+11 more)

### Community 50 - "app.py"
Cohesion: 0.07
Nodes (42): holding_insights_page(), holding_insights_stock_log_page(), ask_memory(), ask_query_log(), ask_sources(), _attach_portfolio_to_ask(), backfill_page(), backfill_start() (+34 more)

### Community 51 - "gold_service.py"
Cohesion: 0.09
Nodes (22): _fetch(), get_gold_snapshot(), get_silver_snapshot(), gold_horizon_code(), gold_macro_series_row(), _load_payload(), _merged_series(), add() (+14 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "investor_subject.py"
Cohesion: 0.05
Nodes (70): pick_best_matching_scheme(), question_refers_deictic_fund_safe(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_deictic_and_memory_primary_fund(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan() (+62 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (21): asks_fund_category_average(), build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns() (+13 more)

### Community 55 - "re"
Cohesion: 0.04
Nodes (75): rating_list_plan(), rating_concept_plan(), apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), AnswerMode (+67 more)

### Community 56 - "test_sector_leaderboard_run.py"
Cohesion: 0.14
Nodes (30): LlmJsonResult, LlmUsage, call(), DryRunHalt, build(), compose_headline(), main(), _both_sides() (+22 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "resolve_fund_for_query"
Cohesion: 0.08
Nodes (30): _detect_funds(), _attach_trailing_product(), collect_fund_phrase_candidates(), _compose_amc_scheme_phrase(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question(), is_macro_metals_question(), is_market_fund_discovery_question() (+22 more)

### Community 59 - "executor.py"
Cohesion: 0.05
Nodes (64): asks_rating_list(), load_fund_risk(), rating_for_request(), rating_needs_pillars(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _capability_cache_key() (+56 more)

### Community 60 - "test_fund_risk.py"
Cohesion: 0.07
Nodes (39): asks_about_score_bands(), asks_pillar_mark(), asks_pillar_structure(), asks_rating_concept(), asks_sebi_riskometer(), exposure_from_detail(), normalize_rating(), pillar_focus() (+31 more)

### Community 61 - "graph.py"
Cohesion: 0.17
Nodes (13): RequestTelemetry, stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed(), event_phase_started(), event_quality_check(), event_request_failed() (+5 more)

### Community 62 - "typing"
Cohesion: 0.07
Nodes (34): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), AskPlan, EntityMention, _int_list(), PlannedTool (+26 more)

### Community 63 - "re"
Cohesion: 0.09
Nodes (21): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+13 more)

### Community 64 - "nav_service.py"
Cohesion: 0.10
Nodes (24): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+16 more)

### Community 65 - "fund_universe_agent.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "slot_route"
Cohesion: 0.08
Nodes (36): execute_wave(), plan_matches_intent(), QuestionIntent, resolve_question_intent(), _top_n_from_question(), _asks_catalog_fund_performance(), _extract_fund_names(), _extract_fund_targets_for_manager() (+28 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.10
Nodes (23): _amc_hints_from_tokens(), candidates_block(), entity_candidates(), _holding_candidates(), _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known() (+15 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "embed.py"
Cohesion: 0.15
Nodes (8): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, _build_encoder(), embeddings_ready(), main()

### Community 71 - "portfolio/cache.py"
Cohesion: 0.10
Nodes (19): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), find_cached_holdings(), get_active_crn(), get_normalized_portfolio(), peek_derived() (+11 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "parse.py"
Cohesion: 0.10
Nodes (15): _pack_row(), _retrieve_bullion_for_entities(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _trim_snippet(), embed_query(), retrieve_fund_articles(), infer_window_days_from_question() (+7 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "node_route"
Cohesion: 0.12
Nodes (19): node_route(), ensure_planner_fund_fact_modules(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question(), validate_plan_tools() (+11 more)

### Community 77 - "sector_fund_ranking.py"
Cohesion: 0.06
Nodes (20): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors() (+12 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 79 - "get_settings"
Cohesion: 0.18
Nodes (15): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+7 more)

### Community 80 - "job.py"
Cohesion: 0.17
Nodes (6): HoldingInsightsJobManager, on_progress(), HoldingJobBusy, HoldingJobView, _write(), report()

### Community 81 - "validate.py"
Cohesion: 0.13
Nodes (20): Envelope, numeric_leaves(), walk(), _allowed_numbers(), _banned(), _blob(), walk(), _body() (+12 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.11
Nodes (40): pending_rating_line(), periods_requested_in_question(), _age(), _allocation_bucket_rows(), _as_of(), _book_line(), _category_amount_map(), _comparison_rows() (+32 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "fetch_google_news.py"
Cohesion: 0.16
Nodes (15): _bucket(), _entity_names(), fetch_window_fields(), summarize_errors(), write_error_summary(), _compact_fetch_errors(), fetch_google_news(), covered_calendar_days() (+7 more)

### Community 86 - "test_ai_insight_quality.py"
Cohesion: 0.09
Nodes (16): EvidenceArticle, _float(), format_evidence_block(), _int(), pick_evidence(), story_weight(), scrub_refusal_prose(), build_user() (+8 more)

### Community 87 - "ExecutionPlan"
Cohesion: 0.05
Nodes (61): ExecutionPlan, _named_fund_overview(), _plan_fetches_vs_benchmark(), resolve_display_table_policy(), asked_slots(), merge_planner_asked_facts(), slots_from_plan(), bind_fields_to_tools() (+53 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.14
Nodes (19): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+11 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 91 - "logging.py"
Cohesion: 0.15
Nodes (8): _env_secrets(), prune_logs(), _redact(), _redact_text(), _rmtree(), RunArtifacts, _usage(), test_artifacts_redact_and_prune()

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.07
Nodes (56): fetch_public_rating(), _add_category_comparison(), _attach_rs_ratings_to_screen(), _one(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line(), _compare_cell() (+48 more)

### Community 96 - "test_news_only_answer.py"
Cohesion: 0.19
Nodes (9): _news_subject(), clean_news_insight(), complete_sentences(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words(), test_news_about_hdfc_bank_is_not_a_market_pulse() (+1 more)

### Community 97 - "NumericRecord"
Cohesion: 0.10
Nodes (30): fetch_ask_market_records(), fetch_gold_record(), get_ask_market_snapshot(), write_ask_market_snapshot(), FiiDiiSnapshot, NumericRecord, unavailable(), fetch_fii_dii_snapshot() (+22 more)

### Community 98 - "fields.py"
Cohesion: 0.17
Nodes (12): _asks_book(), _book_fields(), canonicalize_field(), FieldNeed, fields_from_question(), _fund_fields(), planner_field_names(), resolve_asked_fields() (+4 more)

### Community 99 - "clustering.py"
Cohesion: 0.10
Nodes (31): _adapter(), Cluster, cluster_rows(), cluster_score(), _collapse(), _dedupe(), find(), union() (+23 more)

### Community 100 - "price.py"
Cohesion: 0.17
Nodes (6): history_closes(), latest_quote(), _consecutive_down_days(), DayBar, get_price_snapshot(), test_consecutive_down_days()

### Community 102 - "portfolio/client.py"
Cohesion: 0.17
Nodes (13): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), InvalidCRN, PortfolioError, PortfolioNotConfigured, PortfolioUnavailable (+5 more)

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.12
Nodes (17): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS (+9 more)

### Community 104 - "env"
Cohesion: 0.11
Nodes (18): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL (+10 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.20
Nodes (11): asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score(), test_default_manager_answer_drops_former_managers() (+3 more)

### Community 106 - "portfolio_news_impact.py"
Cohesion: 0.12
Nodes (18): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _strip_book_concentration_tables() (+10 more)

### Community 107 - "parse_rating_screen"
Cohesion: 0.09
Nodes (46): asks_taxonomy(), match_all_fund_types(), parse_rating_screen(), _return_direction(), run_rating_list(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap() (+38 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.16
Nodes (14): CategoryMatch, _close(), fund_type_for_category(), _metal_category(), _metal_flags(), _names_a_type(), _phrase_score(), rating_scope_pairs() (+6 more)

### Community 109 - "test_guardrails_domain.py"
Cohesion: 0.20
Nodes (11): question_in_finance_scope(), check_guardrails(), financial_keyword_signal(), GuardrailResult, test_crude_why_not_misrouted_to_random_fund(), test_fund_question_still_passes(), test_hdfc_bank_passes_guardrails(), test_hdfc_bank_short_happening_passes() (+3 more)

### Community 110 - "test_call_json_llm.py"
Cohesion: 0.32
Nodes (10): _layered_news_topics(), _client(), _gemini_response(), _settings(), test_agent_keeps_truncated_tools_without_repair(), test_composer_keeps_truncated_answer_without_a_second_call(), test_gemini_request_includes_response_schema(), test_judge_truncated_json_does_not_repair() (+2 more)

### Community 111 - "test_portfolio_intents.py"
Cohesion: 0.05
Nodes (60): _leave_tools_alone(), owned_holding_names(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings(), _ensure_portfolio_data_for_compare(), _ensure_portfolio_data_for_holdings(), ensure_whole_book_catalog_scope() (+52 more)

### Community 112 - "qdrant_access.py"
Cohesion: 0.10
Nodes (30): is_stale(), newest_scraped_at(), _as_dict(), _client(), _drop(), _entity_view(), EntityRowsResult, _explode() (+22 more)

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 114 - "insights.py"
Cohesion: 0.30
Nodes (10): build_insights(), _equity_pct(), Insight, insight_lines(), insights_for_brief(), _num(), _style_band(), _book() (+2 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

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
Cohesion: 0.17
Nodes (12): _run_get_macro_news(), _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read() (+4 more)

### Community 121 - "test_ai_insight_mospi.py"
Cohesion: 0.25
Nodes (10): _client(), _sse(), test_400_is_not_retried(), test_gdp_yoy_uses_prior_fiscal_year(), handler(), test_retries_500_then_reads_cache(), handler(), test_snapshot_keeps_other_entities_when_one_fails() (+2 more)

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "stitch_display_tables_into_answer"
Cohesion: 0.08
Nodes (27): ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_context_disclaimer(), strip_markdown_tables_from_prose(), _clean_answer() (+19 more)

### Community 124 - "glossary.py"
Cohesion: 0.25
Nodes (9): asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), meaning_reply(), _normalize_term(), test_fund_nav_not_glossary(), test_nav_full_form_direct_reply(), test_rs_rating_question_is_a_composer_concept_not_a_tool_call() (+1 more)

### Community 125 - "execute_capability"
Cohesion: 0.06
Nodes (28): CapabilityCache, _Entry, get_capability_cache(), _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args() (+20 more)

### Community 126 - "run-pipeline"
Cohesion: 0.29
Nodes (6): jobs, run-pipeline, name, on, runs-on, timeout-minutes

### Community 127 - "bridge.py"
Cohesion: 0.10
Nodes (15): ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), infer_fund_news_layers(), prefers_planner_over_slot(), asks_fund_related_news() (+7 more)

### Community 128 - "query_log.py"
Cohesion: 0.09
Nodes (16): _events(), run_ask_engine(), stream_ask_engine(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), run_insight_pipeline() (+8 more)

### Community 129 - "layer_tools.py"
Cohesion: 0.09
Nodes (29): nifty50_ticker(), extract_top_holdings(), _run_get_investor_portfolio(), _run_get_market_snapshot(), _run_get_portfolio_data(), _price_holdings(), benchmark_return_for_scheme(), _cache_path() (+21 more)

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
Cohesion: 0.15
Nodes (17): fetch_fund(), load_done_isins(), load_isins(), main(), _pct(), run(), write_final(), load_portfolio_isins() (+9 more)

### Community 135 - "test_greeting.py"
Cohesion: 0.16
Nodes (12): greeting_reply(), identity_reply(), _mirror_greeting(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens(), prompt_view() (+4 more)

### Community 136 - "node_compose"
Cohesion: 0.08
Nodes (33): EvidencePack, _asks_portfolio_rs_ratings(), field_answer_needs_composer(), is_pure_field_answer(), render_benchmark_comparison_table(), render_fact_answer(), render_investor_rs_ratings_table(), wants_comparison_table() (+25 more)

### Community 137 - "inputs"
Cohesion: 0.40
Nodes (5): default, description, required, type, holdings_limit

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "test_investor_grounding.py"
Cohesion: 0.18
Nodes (12): repair_investor_insight_prose(), strip_grounding_holes(), cores_for_float(), derived_cores(), investor_book_cores(), _sample_book(), test_grounding_keeps_category_weight_in_prose(), test_investor_book_cores_includes_pnl_term_gains() (+4 more)

### Community 141 - "fund_type_name_spec"
Cohesion: 0.12
Nodes (14): _category_fund_name_spec(), fund_naming_clause(), _fund_type_in_name_clause(), fund_type_name_spec(), _label_in(), _looks_like_fund_list(), rating_screen_question(), _return_window() (+6 more)

### Community 142 - "test_fund_drawdown.py"
Cohesion: 0.08
Nodes (57): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+49 more)

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

### Community 146 - "trends.py"
Cohesion: 0.13
Nodes (15): detect_signals(), _surge(), DayPoint, entity_daily_series(), price_trend(), price_trend_from_closes(), PriceTrend, session_day() (+7 more)

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

### Community 159 - "RunLogger"
Cohesion: 0.25
Nodes (5): finish_run_logger(), RunLogger, start_run_logger(), main(), _run_test()

### Community 163 - "fund_match.py"
Cohesion: 0.13
Nodes (11): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+3 more)

### Community 169 - "fund_scheme_match.py"
Cohesion: 0.17
Nodes (13): amc_token_in_question(), _category_phrases_in_question(), _constraint_in_scheme_name(), _distinctive_constraints(), question_amc_hints(), scheme_match_score(), _scheme_name_tokens(), _scheme_vocab_tokens() (+5 more)

### Community 170 - "generate_json"
Cohesion: 0.14
Nodes (21): _add_usage(), _default_call(), format_articles_block(), generate_json(), _invoke_with_retry(), LlmSchemaError, LlmUnavailable, _run_bounded() (+13 more)

### Community 174 - "stock_log.py"
Cohesion: 0.36
Nodes (8): holding_data_dir(), build_log_document(), load_stock_log(), _price_summary(), render_markdown(), save_stock_log(), stock_logs_dir(), test_save_and_load_stock_log()

### Community 180 - "test_sector_leaderboard_score.py"
Cohesion: 0.15
Nodes (19): sector_label(), llm_schema(), prominence(), rank(), score_sector(), score_stories(), trim_text(), _cluster() (+11 more)

### Community 181 - "test_metal_fund_rating.py"
Cohesion: 0.27
Nodes (8): ensure_quality_fund_list(), _payload(), _rating(), test_gold_list_spreads_etf_and_fund_of_funds(), fetch(), test_my_gold_fund_does_not_add_category_screen(), test_named_gold_etf_is_not_a_category_list(), test_planner_gold_sector_screen_becomes_rating_list()

### Community 182 - "assemble_fund_overview_answer"
Cohesion: 0.18
Nodes (7): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), strip_empty_table_pointers(), _strip_overview_prose_block(), test_overview_drops_repeated_title_and_nav_paragraph(), test_overview_puts_rating_and_tables_before_news(), test_a_risk_read_does_not_point_at_a_missing_returns_table()

### Community 183 - "ai_insight/jobs.py"
Cohesion: 0.12
Nodes (8): JobProgress, _write(), JobBusy, JobManager, JobView, _subprocess(), _write(), test_job_isolates_one_failure()

### Community 184 - "eval_planner.py"
Cohesion: 0.24
Nodes (4): check(), main(), run_case(), _Usage

### Community 185 - "insight_links.py"
Cohesion: 0.17
Nodes (13): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings() (+5 more)

### Community 186 - "lib/google_news.py"
Cohesion: 0.04
Nodes (44): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+36 more)

### Community 187 - "test_answer_quality_logs.py"
Cohesion: 0.08
Nodes (22): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), filter_display_tables() (+14 more)

### Community 188 - "entity_retrieval.py"
Cohesion: 0.11
Nodes (34): rank_clusters(), bellwether_holdings(), EntityPack, evidence_from_clusters(), fetch_entity_pack(), fetch_fii_dii(), fetch_macro_packs(), work() (+26 more)

### Community 190 - "news.py"
Cohesion: 0.19
Nodes (10): get_top_news(), sort_key(), news_window(), NewsArticle, NewsBundle, _published_in_window(), _bar_line(), build_user_prompt() (+2 more)

### Community 191 - "build_derived_views"
Cohesion: 0.15
Nodes (18): clear_cache_for_tests(), seed_portfolio_cache_for_tests(), asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct() (+10 more)

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 193 - "_normalize_fund_text"
Cohesion: 0.11
Nodes (12): _clean_fund_phrase(), add(), _entry_matches_query_scheme(), _expand_query_token(), _extend_amc_phrase_tail(), FundIndex, _infer_category_and_type(), _is_bullion_phrase_not_scheme() (+4 more)

### Community 194 - "Settings"
Cohesion: 0.07
Nodes (36): Publisher, SectorQuery, Settings, load_portfolio_universe(), _fund_stats_from_csv(), load_holdings_rows_from_xlsx(), multi_query_for(), _strip_legal_suffix() (+28 more)

### Community 195 - "httpx"
Cohesion: 0.27
Nodes (3): main(), main(), main()

### Community 197 - "QuestionBrief"
Cohesion: 0.08
Nodes (35): asks_random_fund_compare(), asks_sector_lists(), asks_share_price(), asks_weak_sector(), build_question_brief(), _detect_direction(), _detect_funds(), _heuristic_brief() (+27 more)

### Community 198 - "283041/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 203 - "fund_brief.py"
Cohesion: 0.06
Nodes (51): build_portfolio_scope(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest() (+43 more)

### Community 206 - "test_ai_insight.py"
Cohesion: 0.18
Nodes (6): digest_filter(), _holding_mentioned(), matches_entity(), contains_phrase(), test_digest_filter_uses_stricter_scores(), test_sector_exclude_drops_nbfc_from_banks()

### Community 208 - "load_config"
Cohesion: 0.06
Nodes (45): _bool(), _float(), _freshness_flag(), _int(), load_config(), notify_failure(), _bars(), catalog_path() (+37 more)

### Community 209 - "57e233/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 211 - "test_macro_scope.py"
Cohesion: 0.13
Nodes (16): question_is_standalone_macro(), apply_pure_concept_plan(), question_is_pure_general_concept(), ensure_catalog_tools_for_fund_news(), apply_standalone_macro_scope(), _macro_news_topics(), test_all_holdings_metrics_adds_investor_tool(), test_large_cap_vs_mid_cap_is_pure_concept() (+8 more)

### Community 212 - "c72b25/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 213 - "a45664/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 214 - "test_composer_table_summaries.py"
Cohesion: 0.24
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_evidence_pack_compact_includes_table_summaries(), test_filter_display_tables_by_decision(), test_parse_tables_append_directive(), test_strip_empty_bold_sections(), test_summarize_tables_for_composer_extracts_mix_and_holdings()

### Community 217 - "7859f0/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 218 - "sources/google_news.py"
Cohesion: 0.12
Nodes (22): is_google_exhausted(), _merge_entities(), _now_iso(), record_google_failure(), record_source_failure(), _absorb_into_candidate(), _dedupe_candidates(), _find_story_match() (+14 more)

### Community 219 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

### Community 221 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 222 - "repo_root"
Cohesion: 0.28
Nodes (4): _cache_dir(), repo_root(), main(), test_macro_map_sectors_are_valid_labels()

### Community 223 - "test_holding_overlap.py"
Cohesion: 0.09
Nodes (17): table_source(), has_second_part(), _wants_end_summary(), asks_one_figure(), _compare_return_windows(), _detail(), test_a_comparison_keeps_one_three_and_five_years_plus_benchmark_and_rating(), test_compare_table_includes_risk_for_both_funds() (+9 more)

### Community 224 - "MospiError"
Cohesion: 0.23
Nodes (4): MospiError, _payload(), _sse_json(), GraphUnavailable

### Community 225 - "insights.js"
Cohesion: 0.22
Nodes (18): api(), arrow(), bars(), card(), chart(), diverging(), esc(), headers() (+10 more)

### Community 226 - "holding_insights.js"
Cohesion: 0.40
Nodes (10): api(), clearError(), escapeHtml(), headers(), logLink(), poll(), renderResult(), run() (+2 more)

### Community 227 - "insight_log.js"
Cohesion: 0.70
Nodes (4): api(), esc(), headers(), load()

### Community 228 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

### Community 230 - "aggregate_fund_holdings.py"
Cohesion: 0.23
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 232 - "get_macro_news"
Cohesion: 0.16
Nodes (13): select_macro_for_question(), _digest(), test_banking_and_banks_are_one_search(), test_cache_keeps_the_article_body_not_only_the_title(), test_cache_searches_named_macro_parameters(), test_clusters_are_ordered_by_how_many_articles_are_in_the_db(), test_failed_refresh_keeps_the_previous_cache(), test_macro_news_is_reused_for_two_hours_then_overwritten() (+5 more)

### Community 233 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 236 - "_apply_category_difference"
Cohesion: 0.50
Nodes (3): _apply_category_difference(), _difference_brief(), _user_named_funds()

### Community 237 - "holding_insights/llm.py"
Cohesion: 0.17
Nodes (14): llm_allow_fallback(), call_holding_llm(), _call(), _normalize_response(), parse_insight_lines(), _shrink_to_budget(), _usage_from_result(), _word_count() (+6 more)

### Community 238 - "test_answer_precision.py"
Cohesion: 0.17
Nodes (9): fact_values_already_stated(), question_wants_fact_table(), strip_meta_opening_heading(), _strip_unasked_closers(), test_fact_table_only_for_compare_or_an_explicit_list(), test_fact_table_skipped_when_prose_has_the_figure(), test_next_steps_and_summary_are_removed(), test_specific_lookup_has_no_default_table() (+1 more)

### Community 239 - "build_top100_holdings.py"
Cohesion: 0.38
Nodes (7): check_yfinance(), load_master_index(), lookup_master(), main(), normalize_name(), pick_best_master(), resolve_yf_ticker()

### Community 240 - "run_insights_daily.sh"
Cohesion: 0.50
Nodes (4): note(), PYTHONPATH, PYTHONUNBUFFERED, run_insights_daily.sh script

### Community 241 - "data_pack.py"
Cohesion: 0.38
Nodes (3): build_data_pack(), build(), _compact()

### Community 253 - "test_rupeestop_auth.py"
Cohesion: 0.12
Nodes (8): rupeestop_admin_request_headers(), _jwt(), test_admin_headers_include_bearer(), test_admin_headers_use_token_from_login(), test_bearer_prefers_auth_token_over_admin_token(), test_failed_login_keeps_previous_token(), test_non_admin_url_has_no_authorization(), test_valid_jwt_does_not_call_login()

### Community 260 - "holding_insights_stock_log.js"
Cohesion: 0.60
Nodes (5): api(), escapeHtml(), headers(), load(), render()

## Knowledge Gaps
- **25 isolated node(s):** `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT` (+20 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1954 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **57 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `fund_rating_screen.py`, `node_compose`, `GraphState`, `test_fund_drawdown.py`, `test_fund_name_gate_and_hydrate.py`, `macro_data.py`, `fund_display.py`, `pack_sanitize.py`, `plan_enforce.py`, `fund_context.py`, `task_exec.py`, `test_portfolio_layer.py`, `plan.py`, `category_plan.py`, `book_news_map.py`, `ToolCall`, `gold_service.py`, `investor_subject.py`, `test_metal_fund_rating.py`, `re`, `test_answer_quality_logs.py`, `test_fund_risk.py`, `build_derived_views`, `slot_route`, `QuestionBrief`, `node_route`, `fact_answer.py`, `test_macro_scope.py`, `test_composer_table_summaries.py`, `test_portfolio_allocation.py`, `evidence_pack.py`, `test_holding_overlap.py`, `test_news_only_answer.py`, `fields.py`, `portfolio_news_impact.py`, `parse_rating_screen`, `test_answer_precision.py`, `test_portfolio_intents.py`, `compare_evidence.py`, `glossary.py`, `bridge.py`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `ExecutionPlan` (e.g. with `news_calls_for_book()` and `sector_book()`) actually correct?**
  _`ExecutionPlan` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN` to the rest of the system?**
  _25 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.07863247863247863 - nodes in this community are weakly interconnected._
- **Why does `get_settings()` connect `llm_client.py` to `query_log.py`, `layer_tools.py`, `interpret.py`, `get_sector_fund_ranking_index`, `node_compose`, `GraphState`, `compute.py`, `tools.py`, `news_rag/config.py`, `QueryLogger`, `news_reader.py`, `gather.py`, `task_exec.py`, `fund_match.py`, `fund_search.py`, `test_portfolio_layer.py`, `plan.py`, `app.py`, `gold_service.py`, `investor_subject.py`, `re`, `executor.py`, `typing`, `_normalize_fund_text`, `slot_route`, `httpx`, `QuestionBrief`, `embed.py`, `portfolio/cache.py`, `insight/guardrails.py`, `parse.py`, `fund_brief.py`, `node_route`, `sector_fund_ranking.py`, `stock_fund_ranking.py`, `get_settings`, `ExecutionPlan`, `portfolio/client.py`, `portfolio_news_impact.py`, `qdrant_access.py`, `test_rupeestop_auth.py`, `execute_capability`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ToolCall` (e.g. with `news_calls_for_book()` and `_apply_planner_request()`) actually correct?**
  _`ToolCall` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `Envelope` be split into smaller, more focused modules?**
  _Cohesion score 0.07042253521126761 - nodes in this community are weakly interconnected._