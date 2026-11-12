# Graph Report - db_design_with_qdrant_locally  (2026-11-12)

## Corpus Check
- 506 files · ~876,571 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 5572 nodes · 17847 edges · 204 communities (169 shown, 35 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 632 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7ed5eb54`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- insight/portfolio_scope.py
- get_sector_fund_ranking_index
- interpret.py
- test_portfolio_layer.py
- article_quality.py
- main.py
- execute_capability
- grounding.py
- Settings
- test_fund_drawdown.py
- planner_policy.py
- _return_slice_covers
- compute.py
- plan.py
- tools.py
- fund_display.py
- fund_rating_screen.py
- QueryLogger
- news_reader.py
- build_evidence_pack
- investor_subject.py
- get_settings
- failure_ledger.py
- tool_runners.py
- category_plan.py
- test_fund_display_tables.py
- ensure_registry
- resolve_fund_for_query
- fields.py
- lib/google_news.py
- run_ask_engine
- executor.py
- task_exec.py
- llm_client.py
- update.py
- fund_search.py
- sector_exposure_tables.py
- pack_sanitize.py
- test_fund_rating_screen.py
- env
- test_portfolio_startup_cache.py
- node_route
- test_call_json_llm.py
- macro_news_cache.py
- env
- textutil.py
- rupeestop_auth.py
- test_investor_grounding.py
- fetch_google_news.py
- app.py
- gold_service.py
- env
- nav_service.py
- fund_rupeestop_metrics.py
- contracts.py
- test_portfolio_intents.py
- scrape-worker/package.json
- contracts.py
- test_investor_drawback_routing.py
- test_fund_risk.py
- RequestTelemetry
- normalize_rs_label
- re
- aggregate_fund_holdings.py
- test_rupeestop_auth.py
- batch.ts
- datetime
- insight/guardrails.py
- http-fetch.ts
- embed.py
- portfolio/cache.py
- holdings_market.py
- test_fact_answer.py
- with
- stock_fund_ranking.py
- lib/portfolio_scope.py
- stock_fund_ranking.py
- datetime
- resolve_display_table_policy
- normalize.py
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- sector_fund_ranking.py
- SectorFundRankingIndex
- market_pulse.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- affected_sectors.py
- CapabilityCache
- env
- memory/__init__.py
- steps
- evidence_pack.py
- _run_get_fund_data
- EvidencePack
- test_macro_news_cache.py
- retrieve_scoped_news
- pathlib
- metals_spot_tables.py
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- ExecutionPlan
- ask_plan.py
- fund_rating_categories.py
- insight/portfolio_scope.py
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- test_fund_rating_screen.py
- strip_news_roundup
- news_digest.py
- _compose_amc_scheme_phrase
- vitest
- format_inr
- test_ask_query_log.py
- compilerOptions
- compilerOptions
- PublisherStats
- ._ensure_loaded
- backfill
- lib/google_news.py
- test_composer_table_summaries.py
- compare_evidence.py
- run-pipeline
- portfolio/client.py
- sector_alignment.py
- index_series.py
- worker/src/index.ts
- steps
- steps
- with
- test_conversation_memory.py
- get_fund_index
- insights.py
- inputs
- with
- inputs
- json
- concept_asks.py
- GraphState
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
- eval_planner.py
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_catalog.py
- diagnose_lightsail_site.sh
- RunLogger
- test_metal_fund_rating.py
- EntityFunnel
- shared_system_prefix
- asks_computed_illustration
- build_derived_views
- httpx
- query_plan.py
- extract_top_holdings
- entity_candidates.py
- csv
- _fund_performance_digest
- asks_fund_related_news
- plan_enforce.py
- pack_trim.py
- QuestionBrief
- news_insight_articles
- data_pack.py
- fund_brief.py
- market_scope_entities
- prompts.py

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 585 edges
2. `ToolCall` - 352 edges
3. `get_settings()` - 139 edges
4. `apply_planner_post_hooks()` - 121 edges
5. `AnswerMode` - 104 edges
6. `QueryLogger` - 100 edges
7. `node_compose()` - 98 edges
8. `QuestionBrief` - 88 edges
9. `slot_route()` - 84 edges
10. `Settings` - 83 edges

## Surprising Connections (you probably didn't know these)
- `test_allocation_fact_uses_category_share_list()` --calls--> `render_portfolio_fact()`  [EXTRACTED]
  tests/test_portfolio_intents.py → news_rag/insight/fact_answer.py
- `test_next_sip_uses_normalized_next_due_date()` --calls--> `render_portfolio_fact()`  [EXTRACTED]
  tests/test_portfolio_intents.py → news_rag/insight/fact_answer.py
- `test_st_vs_lt_gains_from_pnl_summary()` --calls--> `render_portfolio_fact()`  [EXTRACTED]
  tests/test_portfolio_intents.py → news_rag/insight/fact_answer.py
- `test_xirr_fact_reads_xirr_module_slice()` --calls--> `render_portfolio_fact()`  [EXTRACTED]
  tests/test_portfolio_intents.py → news_rag/insight/fact_answer.py
- `test_current_value_and_nonzero_xirr()` --calls--> `normalize_workspace()`  [EXTRACTED]
  tests/test_portfolio_layer.py → news_rag/portfolio/normalize.py

## Import Cycles
- None detected.

## Communities (204 total, 35 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (46): get_entity_funnel(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate(), drop_old_points() (+38 more)

### Community 1 - "insight/portfolio_scope.py"
Cohesion: 0.15
Nodes (20): plan_targets_single_fund_measured_return(), _data_need_is_investor(), enforce_portfolio_scope(), ensure_investor_portfolio_tool(), _has_investor_tool(), _investor_tool_args(), _modules_for_investor_plan(), _plan_wants_investor_book() (+12 more)

### Community 2 - "get_sector_fund_ranking_index"
Cohesion: 0.08
Nodes (31): execute_wave(), get_sector_fund_ranking_index(), _clean_stock_capture(), phrase_is_mutual_fund_scheme(), phrase_looks_like_sector_reference(), screen_hints_from_question(), stock_name_from_question(), test_crude_increase_compound_question_screens_negatively_affected_funds() (+23 more)

### Community 3 - "interpret.py"
Cohesion: 0.07
Nodes (63): asks_random_fund_compare(), Findings, FundFinding, SectorFinding, EvidenceSet, mentions_publication_date(), _assemble(), _caveat() (+55 more)

### Community 4 - "test_portfolio_layer.py"
Cohesion: 0.08
Nodes (20): get_active_crn(), project_concentration(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match(), PortfolioStore (+12 more)

### Community 5 - "article_quality.py"
Cohesion: 0.20
Nodes (12): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+4 more)

### Community 6 - "main.py"
Cohesion: 0.07
Nodes (16): is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), _datetime_range(), NewsStore, point_id_for_url(), to_iso() (+8 more)

### Community 7 - "execute_capability"
Cohesion: 0.10
Nodes (21): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), _positive_ms(), widen_portfolio_args(), beside_keys(), recall_slice(), recall_wider_portfolio() (+13 more)

### Community 8 - "grounding.py"
Cohesion: 0.06
Nodes (37): analyst_should_run(), asks_market_briefing(), question_is_standalone_macro(), collect_evidence_calendar_dates(), add_article(), cores_in_text(), finalize_text_fields(), format_user_calendar_date() (+29 more)

### Community 9 - "Settings"
Cohesion: 0.07
Nodes (35): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), Publisher, repo_root(), SectorQuery, article_in_fetch_window() (+27 more)

### Community 10 - "test_fund_drawdown.py"
Cohesion: 0.05
Nodes (68): _add_drawdown_call(), asks_category_drawdown(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), drawdown_words(), ensure_drawdown_tools() (+60 more)

### Community 11 - "planner_policy.py"
Cohesion: 0.07
Nodes (29): _invalidate_plan_system_cache(), align_planned_news_execution(), apply_now_window(), drop_unasked_fund_modules(), _ensure_sector_overview(), finalize_planner_plan(), narrow_deictic_follow_up(), question_uses_now_window() (+21 more)

### Community 12 - "_return_slice_covers"
Cohesion: 0.23
Nodes (8): _return_slice_covers(), _ensure_portfolio_for_fund_news(), test_missing_window_is_not_covered(), test_wider_cached_fund_payload_covers_and_trims_to_the_ask(), _wide(), test_a_narrow_cache_does_not_stand_in_for_a_wider_request(), test_investor_holdings_cache_does_not_cover_pnl_summary_request(), test_market_snapshot_cache_does_not_cover_different_window()

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (44): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+36 more)

### Community 14 - "plan.py"
Cohesion: 0.11
Nodes (20): explanation_brief(), field_prompt_table(), mentions_advice(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), _label_for_days() (+12 more)

### Community 15 - "tools.py"
Cohesion: 0.05
Nodes (61): extract_top_holdings(), extract_top_sectors(), run_driver_affected_funds_adapter(), DataNeed, _active_sector_equity(), _args_from_question(), _articles_for_affected_question(), _as_date() (+53 more)

### Community 16 - "fund_display.py"
Cohesion: 0.11
Nodes (29): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+21 more)

### Community 17 - "fund_rating_screen.py"
Cohesion: 0.07
Nodes (37): _add_category_comparison(), _amc_matches(), _amc_outside_label(), _amc_token(), _apply_category_difference(), asks_balanced_long_horizon_fund_menu(), balanced_portfolio_examples_spec(), _best_label() (+29 more)

### Community 18 - "QueryLogger"
Cohesion: 0.10
Nodes (7): _retrieve_bullion_for_entities(), retrieve_fund_articles(), clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest()

### Community 19 - "news_reader.py"
Cohesion: 0.07
Nodes (48): _article_context_for_interpret(), _clean_market_claims(), _sector_lists_block(), _lines(), measured_facts_block(), _allowed_sector_names(), _article_char_limit(), _body() (+40 more)

### Community 20 - "build_evidence_pack"
Cohesion: 0.09
Nodes (20): fetch_public_rating(), EvidenceRow, _attach_rs_ratings_to_screen(), _one(), build_evidence_pack(), _refresh_fund_blocks_ratings(), sector_focus_from_market(), screen_fact_names() (+12 more)

### Community 21 - "investor_subject.py"
Cohesion: 0.04
Nodes (101): _metal_fund_categories(), plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), _needles_for_amc_hint(), _amc_token_set(), _bound_fund_name(), _compare_sides_resolvable(), _known_names_in_text() (+93 more)

### Community 22 - "get_settings"
Cohesion: 0.09
Nodes (24): ask(), ask_stream(), AskRequest, _attach_llm_meta(), fund_brief(), FundBriefRequest, health(), get_settings() (+16 more)

### Community 23 - "failure_ledger.py"
Cohesion: 0.07
Nodes (37): Settings, _merge_publisher_error_reasons(), write_day_report(), _atomic_write(), day_failure_slices_for_run(), ensure_loaded(), _failures_dir(), flush() (+29 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.10
Nodes (44): build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+36 more)

### Community 25 - "category_plan.py"
Cohesion: 0.05
Nodes (55): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), asks_category_performance(), _named_scheme_category(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition() (+47 more)

### Community 26 - "test_fund_display_tables.py"
Cohesion: 0.07
Nodes (30): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_markdown_tables_from_prose() (+22 more)

### Community 27 - "ensure_registry"
Cohesion: 0.07
Nodes (48): _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext, LedgerEntry (+40 more)

### Community 28 - "resolve_fund_for_query"
Cohesion: 0.10
Nodes (27): _attach_trailing_product(), collect_fund_phrase_candidates(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _phrase_specificity_score() (+19 more)

### Community 29 - "fields.py"
Cohesion: 0.11
Nodes (23): periods_requested_in_question(), _asks_book(), bind_fields_to_tools(), _book_fields(), canonicalize_field(), FieldNeed, fields_from_question(), _fund_fields() (+15 more)

### Community 30 - "lib/google_news.py"
Cohesion: 0.09
Nodes (15): article_id_from_url(), _batchexecute(), cached_resolve(), is_google_news_article_url(), _parse_garturlres(), resolve_google_news_url(), _connection(), _db_path() (+7 more)

### Community 31 - "run_ask_engine"
Cohesion: 0.13
Nodes (10): _events(), run_ask_engine(), stream_ask_engine(), run_insight_pipeline(), stream_insight_pipeline(), new_fund_brief_logger(), new_query_logger(), main() (+2 more)

### Community 32 - "executor.py"
Cohesion: 0.07
Nodes (36): retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), asks_rating_list(), pick_compare_pair_in_category(), rating_spec_for_forced_screen(), _rows_from_payload(), _attach_rs_rating_to_screen_rows(), _bullion_articles() (+28 more)

### Community 33 - "task_exec.py"
Cohesion: 0.09
Nodes (41): apply_task_layer(), bind_subjects(), _book_total_line(), _canon_fact(), _category_in_planner_text(), _cell(), coverage_line(), _fact_label() (+33 more)

### Community 34 - "llm_client.py"
Cohesion: 0.11
Nodes (33): Settings, make_plan(), anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts(), _call_anthropic(), _call_deepseek(), _call_gemini() (+25 more)

### Community 35 - "update.py"
Cohesion: 0.10
Nodes (28): _store_turn_memory(), drain_cache_events(), drop_old_turns(), compare_payload_matches_funds(), push_recent_fund_focus(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist() (+20 more)

### Community 36 - "fund_search.py"
Cohesion: 0.12
Nodes (22): build_holding_overlap(), _clean_company_name(), detail_has_live_facts(), _entry_matches_amc(), fetch_fund_managers_for_isin(), fetch_fund_managers_for_query(), _fund_context_for_managers(), _fund_text() (+14 more)

### Community 37 - "sector_exposure_tables.py"
Cohesion: 0.14
Nodes (19): merge_fund_isins_map(), bind_shown_list_followup(), windows_named_in_question(), _all_holdings_metric_spec(), _fund_data_from_results(), _investor_holdings_rating_rows(), _metric_cell(), render_all_holdings_metric_table() (+11 more)

### Community 38 - "pack_sanitize.py"
Cohesion: 0.10
Nodes (25): append_investor_portfolio_overview_tables(), strip_unasked_scheme_names(), attach_drawback_digest(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer(), question_asks_all_schemes_in_answer(), question_wants_scheme_names() (+17 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.14
Nodes (27): run_rating_list(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap(), fetch(), test_a_one_month_performer_is_shown_beside_the_same_category_rating(), fetch(), test_a_positive_one_month_return_is_paired_with_best_in_category() (+19 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "test_portfolio_startup_cache.py"
Cohesion: 0.16
Nodes (14): _category_slug_from_question(), question_asks_category_book_share(), question_asks_category_money(), bind_cached_portfolio(), _catalog_fund_holdings_question(), ensure_tools_for_data_question(), finish_portfolio_plan_bind(), _investor_args() (+6 more)

### Community 42 - "node_route"
Cohesion: 0.12
Nodes (18): node_route(), ensure_planner_fund_fact_modules(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question(), validate_plan_tools() (+10 more)

### Community 43 - "test_call_json_llm.py"
Cohesion: 0.17
Nodes (14): _json_balance(), _plain_answer_from_reasoning(), salvage_truncated_json(), _loads_closed(), _client(), _gemini_response(), _settings(), test_agent_keeps_truncated_tools_without_repair() (+6 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.18
Nodes (11): _run_get_macro_news(), _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read() (+3 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "textutil.py"
Cohesion: 0.13
Nodes (16): fetch_entity_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url(), fetch_macro_items(), is_macro_match(), macro_fetch_entities(), canonical_url() (+8 more)

### Community 47 - "rupeestop_auth.py"
Cohesion: 0.16
Nodes (19): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+11 more)

### Community 48 - "test_investor_grounding.py"
Cohesion: 0.10
Nodes (19): render_pillar_marks_table(), investor_fact_brief(), repair_investor_insight_prose(), _risk_body(), strip_grounding_holes(), _drop_scheme_is_the_whole_book(), GraphUnavailable, node_compose() (+11 more)

### Community 49 - "fetch_google_news.py"
Cohesion: 0.24
Nodes (11): _bucket(), _entity_names(), fetch_window_fields(), summarize_errors(), write_error_summary(), _compact_fetch_errors(), fetch_google_news(), covered_calendar_days() (+3 more)

### Community 50 - "app.py"
Cohesion: 0.09
Nodes (34): ask_memory(), ask_query_log(), ask_sources(), _attach_portfolio_to_ask(), backfill_page(), backfill_start(), backfill_status(), backfill_stop() (+26 more)

### Community 51 - "gold_service.py"
Cohesion: 0.15
Nodes (16): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+8 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "nav_service.py"
Cohesion: 0.20
Nodes (12): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+4 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (19): build_comparison_periods(), expense_ratio_for_question(), _f(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns(), normalize_vs_benchmark_payload(), _optional_number() (+11 more)

### Community 55 - "contracts.py"
Cohesion: 0.03
Nodes (81): question_needs_affected_sectors(), question_mentions_fund_scheme(), rating_list_plan(), rating_concept_plan(), asks_fund_category_average(), ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results() (+73 more)

### Community 56 - "test_portfolio_intents.py"
Cohesion: 0.14
Nodes (19): _leave_tools_alone(), _set_investor_call(), plan_targets_catalog_on_holdings(), apply_portfolio_intent(), data_need_for(), modules_for(), normalize_portfolio_intent(), portfolio_intent_from_question() (+11 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "contracts.py"
Cohesion: 0.06
Nodes (29): question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), LLMUsageRecord, PhaseRecord, ToolRecord, question_wants_gold_table(), asked_slots() (+21 more)

### Community 59 - "test_investor_drawback_routing.py"
Cohesion: 0.21
Nodes (13): render_investor_concentration_answer(), node_bridge(), build_drawdown_wave2_calls(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), question_asks_portfolio_level_drawdown(), question_signals_investor_book() (+5 more)

### Community 60 - "test_fund_risk.py"
Cohesion: 0.05
Nodes (60): asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison() (+52 more)

### Community 61 - "RequestTelemetry"
Cohesion: 0.13
Nodes (18): RequestTelemetry, _answer_stream_chunks(), Node, _plan_fetches_manager_roster(), run_graph_pipeline(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta() (+10 more)

### Community 62 - "normalize_rs_label"
Cohesion: 0.12
Nodes (23): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), infer_anchor_label_from_excludes() (+15 more)

### Community 63 - "re"
Cohesion: 0.08
Nodes (29): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+21 more)

### Community 64 - "aggregate_fund_holdings.py"
Cohesion: 0.23
Nodes (11): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+3 more)

### Community 65 - "test_rupeestop_auth.py"
Cohesion: 0.13
Nodes (4): _jwt(), test_admin_headers_use_token_from_login(), test_failed_login_keeps_previous_token(), test_valid_jwt_does_not_call_login()

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "datetime"
Cohesion: 0.09
Nodes (18): headline_rating(), _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years() (+10 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.14
Nodes (15): _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), memory_shows_investor_book(), _tokens() (+7 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "embed.py"
Cohesion: 0.15
Nodes (8): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), main()

### Community 71 - "portfolio/cache.py"
Cohesion: 0.11
Nodes (27): _BreakerState, _CacheEntry, clear_cache_for_tests(), crn_log_id(), _fetch_and_store(), get_normalized_portfolio(), peek_derived(), peek_portfolio() (+19 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.10
Nodes (19): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker(), _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases() (+11 more)

### Community 73 - "test_fact_answer.py"
Cohesion: 0.16
Nodes (20): _asks_portfolio_rs_ratings(), field_answer_needs_composer(), _investor_holdings_rows(), is_pure_field_answer(), render_benchmark_comparison_table(), render_fact_answer(), render_investor_rs_ratings_table(), wants_comparison_table() (+12 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "stock_fund_ranking.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 77 - "lib/portfolio_scope.py"
Cohesion: 0.09
Nodes (32): build_portfolio_scope(), _clean_holding_tokens(), _holding_equity_allowed(), instrument_to_qdrant_names(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest(), load_portfolio_funds() (+24 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 79 - "datetime"
Cohesion: 0.11
Nodes (22): _capability_cache_key(), _run_get_investor_portfolio(), strip_empty_table_pointers(), ensure_all_holdings_metrics_plan(), run_fund_snapshot(), _age_phrase(), align_plan_windows(), normalize_window_code() (+14 more)

### Community 80 - "resolve_display_table_policy"
Cohesion: 0.07
Nodes (27): DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), fact_values_already_stated(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary() (+19 more)

### Community 81 - "normalize.py"
Cohesion: 0.19
Nodes (17): aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values(), _drop_sold(), _first(), _holding_from_scheme() (+9 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.13
Nodes (37): _age(), _allocation_bucket_rows(), _as_of(), _book_line(), _category_amount_map(), _comparison_rows(), _composition_line(), _float_or_none() (+29 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "sector_fund_ranking.py"
Cohesion: 0.08
Nodes (22): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), candidate_sector_names(), classify_sector_fund_purity(), _damerau() (+14 more)

### Community 86 - "SectorFundRankingIndex"
Cohesion: 0.15
Nodes (4): normalize_sector_label(), sector_query_for_label(), _sector_label_in_text(), SectorFundRankingIndex

### Community 87 - "market_pulse.py"
Cohesion: 0.05
Nodes (51): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), _pack_row(), _trim_snippet(), embed_query(), _body() (+43 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.14
Nodes (19): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+11 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.22
Nodes (9): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), strip_context_disclaimer(), _clean_answer(), test_pads_short_row() (+1 more)

### Community 90 - "affected_sectors.py"
Cohesion: 0.24
Nodes (9): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+1 more)

### Community 91 - "CapabilityCache"
Cohesion: 0.14
Nodes (7): CapabilityCache, _Entry, get_capability_cache(), test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner(), test_capabilities_cache_stores_and_retrieves()

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "memory/__init__.py"
Cohesion: 0.15
Nodes (13): greeting_reply(), identity_reply(), _mirror_greeting(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens() (+5 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.06
Nodes (59): labels_name_the_same_scheme(), _add_category_comparison(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line(), _compare_cell(), _compare_header(), _complete_fund_row() (+51 more)

### Community 96 - "_run_get_fund_data"
Cohesion: 0.17
Nodes (12): load_fund_risk(), rating_for_request(), rating_needs_pillars(), fetch_vs_benchmark(), _detail_for_fund_tool(), _isin_for_fund_name(), _repair_incomplete_fund_data(), _run_get_fund_data() (+4 more)

### Community 97 - "EvidencePack"
Cohesion: 0.16
Nodes (10): EvidencePack, test_evidence_pack_compact_includes_table_summaries(), test_compare_table_shows_the_drawdown_row(), test_screen_table_shows_the_drawdown_column(), test_risk_only_template_shows_the_public_lines(), test_expense_ratio_meaning_and_judgment_uses_composer(), test_render_drawback_includes_underperformers(), test_compact_strips_contribution_from_data_attribution() (+2 more)

### Community 98 - "test_macro_news_cache.py"
Cohesion: 0.16
Nodes (13): select_macro_for_question(), _digest(), test_banking_and_banks_are_one_search(), test_cache_keeps_the_article_body_not_only_the_title(), test_cache_searches_named_macro_parameters(), test_clusters_are_ordered_by_how_many_articles_are_in_the_db(), test_failed_refresh_keeps_the_previous_cache(), test_macro_news_is_reused_for_two_hours_then_overwritten() (+5 more)

### Community 99 - "retrieve_scoped_news"
Cohesion: 0.12
Nodes (13): corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news() (+5 more)

### Community 100 - "pathlib"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 102 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.17
Nodes (13): _rating_lead_for_pack(), asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score() (+5 more)

### Community 106 - "ExecutionPlan"
Cohesion: 0.04
Nodes (109): _ensure_pillar_rating_plan(), ExecutionPlan, ToolCall, ensure_fund_concentration_plan(), is_article_only_news(), clarify_plan_if_fund_unknown(), _plan_uses_fund_scoped_tools(), question_refers_deictic_fund_safe() (+101 more)

### Community 107 - "ask_plan.py"
Cohesion: 0.24
Nodes (9): AskPlan, EntityMention, _int_list(), PlannedTool, common_market_news_from_plan(), market_pulse_from_plan(), test_ask_plan_keeps_rich_agent_fields(), test_cluster_prefers_larger_groups() (+1 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.16
Nodes (9): categories_for(), CategoryMatch, fund_type_for_category(), metal_scheme_categories(), _names_a_type(), rating_scope_pairs(), _spaced_category_words(), taxonomy_reply() (+1 more)

### Community 109 - "insight/portfolio_scope.py"
Cohesion: 0.12
Nodes (17): _articles_from_pack(), build_portfolio_news_impact_dossier(), ensure_portfolio_news_impact_plan(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), question_is_portfolio_news_impact() (+9 more)

### Community 111 - "test_fund_rating_screen.py"
Cohesion: 0.08
Nodes (37): asks_taxonomy(), match_all_fund_types(), _category_fund_name_spec(), ensure_rating_screen(), fund_naming_clause(), fund_type_name_spec(), _label_in(), _looks_like_fund_list() (+29 more)

### Community 112 - "strip_news_roundup"
Cohesion: 0.33
Nodes (6): append_news_section(), _insert_before_disclaimer(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 114 - "_compose_amc_scheme_phrase"
Cohesion: 0.33
Nodes (3): _compose_amc_scheme_phrase(), _extend_amc_phrase_tail(), _slurp_scheme_tail_from_question()

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 117 - "test_ask_query_log.py"
Cohesion: 0.19
Nodes (9): ParsedQuery, attach_query_log_meta(), find_query_log_file(), query_log_page_href(), read_query_log(), test_attach_query_log_meta_adds_page_link(), test_finish_writes_json_sidecar(), test_log_parsed_includes_intent_and_fund() (+1 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 121 - "._ensure_loaded"
Cohesion: 0.12
Nodes (10): _clean_fund_phrase(), add(), _entry_matches_query_scheme(), _expand_query_token(), FundIndex, _infer_category_and_type(), _is_bullion_phrase_not_scheme(), _is_plausible_scheme_phrase() (+2 more)

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "lib/google_news.py"
Cohesion: 0.06
Nodes (30): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+22 more)

### Community 124 - "test_composer_table_summaries.py"
Cohesion: 0.27
Nodes (7): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections()

### Community 125 - "compare_evidence.py"
Cohesion: 0.27
Nodes (7): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "portfolio/client.py"
Cohesion: 0.20
Nodes (11): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), InvalidCRN, PortfolioNotConfigured, PortfolioUpstreamError, test_switch_evicts_the_previous_crn() (+3 more)

### Community 128 - "sector_alignment.py"
Cohesion: 0.07
Nodes (36): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _rule_sector_picks(), canonical_direction_for_driver(), clear_macro_impact_cache() (+28 more)

### Community 129 - "index_series.py"
Cohesion: 0.10
Nodes (28): nifty50_ticker(), aggregate_sectors_from_holdings(), normalize_sector_row(), _run_get_market_snapshot(), _run_get_portfolio_data(), _price_holdings(), benchmark_return_for_scheme(), _cache_path() (+20 more)

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

### Community 134 - "test_conversation_memory.py"
Cohesion: 0.15
Nodes (25): _load_planner_memory(), clear_conversation(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), append_chat_turn(), get_memory(), reset_memory(), save_state() (+17 more)

### Community 135 - "get_fund_index"
Cohesion: 0.33
Nodes (7): _warmup_embeddings_background(), _run(), embed_query(), warmup_query_vectors(), get_fund_index(), _prewarm_tool_modules(), main()

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
Cohesion: 0.11
Nodes (20): _json_default(), safe_json_dumps(), fetch_fund(), load_done_isins(), load_isins(), main(), _pct(), run() (+12 more)

### Community 141 - "concept_asks.py"
Cohesion: 0.18
Nodes (16): apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), apply_pure_concept_plan(), question_is_pure_general_concept(), asks_fof_funds() (+8 more)

### Community 142 - "GraphState"
Cohesion: 0.11
Nodes (20): _attach_conversation(), build_result(), _catalog_fanout_fund_names(), _conversation_id(), GraphState, _insight_headline_narrative(), _maybe_compare_funds_after_multi_screen(), _maybe_enrich_picked_fund_from_screen() (+12 more)

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

### Community 159 - "eval_planner.py"
Cohesion: 0.24
Nodes (4): check(), main(), run_case(), _Usage

### Community 163 - "fund_match.py"
Cohesion: 0.15
Nodes (10): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), load_fund_embedding_cache(), _normalize_fund_text() (+2 more)

### Community 170 - "fund_catalog.py"
Cohesion: 0.10
Nodes (24): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+16 more)

### Community 178 - "test_metal_fund_rating.py"
Cohesion: 0.27
Nodes (8): ensure_quality_fund_list(), _payload(), _rating(), test_gold_list_spreads_etf_and_fund_of_funds(), fetch(), test_my_gold_fund_does_not_add_category_screen(), test_named_gold_etf_is_not_a_category_list(), test_planner_gold_sector_screen_becomes_rating_list()

### Community 180 - "shared_system_prefix"
Cohesion: 0.23
Nodes (8): plan_system_prompt(), build_anthropic_messages_body(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), _body(), test_planner_and_composer_share_the_first_system_block(), test_tools_stay_available_when_there_is_no_shared_prefix()

### Community 181 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

### Community 182 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 183 - "httpx"
Cohesion: 0.22
Nodes (3): fetch_category_ratings(), main(), test_category_rating_request_uses_admin_header()

### Community 185 - "extract_top_holdings"
Cohesion: 0.17
Nodes (13): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings() (+5 more)

### Community 186 - "entity_candidates.py"
Cohesion: 0.30
Nodes (6): candidates_block(), entity_candidates(), _holding_candidates(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

### Community 188 - "_fund_performance_digest"
Cohesion: 0.38
Nodes (4): _fund_performance_digest(), prefers_planner_over_slot(), test_fund_news_does_not_force_planner(), test_performance_digest_from_snapshot()

### Community 190 - "asks_fund_related_news"
Cohesion: 0.31
Nodes (6): infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only(), test_overview_news_is_holdings_and_sectors()

### Community 191 - "plan_enforce.py"
Cohesion: 0.06
Nodes (38): asks_ideal_portfolio_shape(), question_asks_current_book_allocation(), asks_these_equity_funds(), comparison_fund_names(), _filter(), fund_name_matches_category(), implicit_compare_pair_from_chat(), memory_funds_for_category() (+30 more)

### Community 197 - "QuestionBrief"
Cohesion: 0.07
Nodes (35): asks_sector_lists(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief(), _detect_direction(), _detect_funds(), _heuristic_brief() (+27 more)

### Community 199 - "news_insight_articles"
Cohesion: 0.22
Nodes (5): clean_news_insight(), complete_sentences(), news_insight_articles(), strip_publisher(), _subject_words()

### Community 200 - "data_pack.py"
Cohesion: 0.38
Nodes (3): build_data_pack(), build(), _compact()

### Community 203 - "fund_brief.py"
Cohesion: 0.09
Nodes (36): FundRef, is_blocked_sector(), PortfolioScope, ScopedHolding, ScopedSector, _article_entities(), build_events(), cluster_articles() (+28 more)

### Community 212 - "prompts.py"
Cohesion: 0.25
Nodes (5): build_composer_prompt(), build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1615 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `insight/portfolio_scope.py`, `test_portfolio_layer.py`, `test_conversation_memory.py`, `test_fund_drawdown.py`, `planner_policy.py`, `concept_asks.py`, `GraphState`, `plan.py`, `fund_display.py`, `fund_rating_screen.py`, `build_evidence_pack`, `investor_subject.py`, `category_plan.py`, `fields.py`, `task_exec.py`, `llm_client.py`, `sector_exposure_tables.py`, `pack_sanitize.py`, `test_portfolio_startup_cache.py`, `node_route`, `test_metal_fund_rating.py`, `gold_service.py`, `contracts.py`, `test_portfolio_intents.py`, `contracts.py`, `test_investor_drawback_routing.py`, `test_fund_risk.py`, `RequestTelemetry`, `plan_enforce.py`, `QuestionBrief`, `portfolio/cache.py`, `test_fact_answer.py`, `datetime`, `resolve_display_table_policy`, `fact_answer.py`, `test_portfolio_allocation.py`, `evidence_pack.py`, `EvidencePack`, `enrich_manager_payload`, `insight/portfolio_scope.py`, `test_fund_rating_screen.py`, `test_composer_table_summaries.py`, `compare_evidence.py`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Are the 38 inferred relationships involving `ExecutionPlan` (e.g. with `apply_concept_example_to_plan()` and `append_investor_portfolio_overview_tables()`) actually correct?**
  _`ExecutionPlan` has 38 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.07259450171821306 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ExecutionPlan` to `insight/portfolio_scope.py`, `get_sector_fund_ranking_index`, `test_portfolio_layer.py`, `test_conversation_memory.py`, `execute_capability`, `test_fund_drawdown.py`, `planner_policy.py`, `_return_slice_covers`, `concept_asks.py`, `GraphState`, `plan.py`, `fund_rating_screen.py`, `build_evidence_pack`, `investor_subject.py`, `category_plan.py`, `fields.py`, `executor.py`, `task_exec.py`, `update.py`, `sector_exposure_tables.py`, `pack_sanitize.py`, `test_portfolio_startup_cache.py`, `node_route`, `test_metal_fund_rating.py`, `gold_service.py`, `contracts.py`, `test_portfolio_intents.py`, `contracts.py`, `test_investor_drawback_routing.py`, `test_fund_risk.py`, `RequestTelemetry`, `plan_enforce.py`, `QuestionBrief`, `portfolio/cache.py`, `datetime`, `resolve_display_table_policy`, `test_portfolio_allocation.py`, `CapabilityCache`, `evidence_pack.py`, `insight/portfolio_scope.py`, `test_fund_rating_screen.py`, `compare_evidence.py`, `portfolio/client.py`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ToolCall` (e.g. with `execute_capability()` and `execute_wave()`) actually correct?**
  _`ToolCall` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `get_sector_fund_ranking_index` be split into smaller, more focused modules?**
  _Cohesion score 0.07948717948717948 - nodes in this community are weakly interconnected._