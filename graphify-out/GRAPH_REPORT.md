# Graph Report - db_design_with_qdrant_locally  (2026-11-14)

## Corpus Check
- 526 files · ~890,300 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .example 6, (none) 4, .mdc 2)

## Summary
- 5817 nodes · 18639 edges · 218 communities (182 shown, 36 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 660 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7c7f0faf`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- Settings
- fund_rating_screen.py
- interpret.py
- fields.py
- article_quality.py
- node_compose
- time
- test_ask_speed.py
- Settings
- fund_drawdown.py
- node_compose
- concept_asks.py
- compute.py
- _attach_screen_facts
- tools.py
- fund_display.py
- update.py
- QueryLogger
- news_reader.py
- macro_data.py
- test_portfolio_startup_cache.py
- AnswerMode
- failure_ledger.py
- tool_runners.py
- category_plan.py
- test_fund_display_tables.py
- ensure_registry
- resolve_fund_for_query
- fund_name_gate.py
- nse_fii_dii.py
- bridge.py
- _run_get_fund_data
- task_exec.py
- llm_client.py
- book_news_map.py
- fund_search.py
- normalize.py
- pack_sanitize.py
- test_fund_rating_screen.py
- env
- plan_enforce.py
- build_evidence_pack
- plan.py
- macro_news_cache.py
- env
- affected_sectors.py
- validate_plan_tools
- test_fund_drawdown.py
- fund_scheme_match.py
- get_settings
- gold_service.py
- env
- insight/portfolio_scope.py
- fund_rupeestop_metrics.py
- slot_router.py
- test_portfolio_intents.py
- scrape-worker/package.json
- _normalize_fund_text
- test_fund_payload_first.py
- test_fund_risk.py
- graph.py
- retrieve_scoped_news
- re
- nav_service.py
- fund_universe_agent.py
- batch.ts
- CapabilityCache
- insight/guardrails.py
- http-fetch.ts
- embed.py
- portfolio/cache.py
- holdings_market.py
- test_insight_graph.py
- with
- ensure_registry
- ExecutionPlan
- stock_fund_ranking.py
- rupeestop_auth.py
- display_table_policy.py
- test_portfolio_layer.py
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- get_fund_index
- test_rupeestop_auth.py
- screen_hints_from_question
- test_portfolio_allocation.py
- normalize_answer_markdown
- nse_sector_indices.py
- compare_evidence.py
- env
- prompts.py
- steps
- evidence_pack.py
- portfolio/client.py
- NumericRecord
- validate_capability_args
- fund_display.py
- pathlib
- MospiClient
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- macro_impact_map.py
- market_pulse.py
- fund_rating_categories.py
- call_json_llm
- output_judge.py
- test_portfolio_layer.py
- execute_capability
- news_digest.py
- planner_policy.py
- vitest
- format_inr
- test_guardrails_domain.py
- compilerOptions
- compilerOptions
- test_ai_insight_mospi.py
- run_ask_engine
- backfill
- lib/google_news.py
- test_composer_table_summaries.py
- evidence.py
- run-pipeline
- enforce_planner_catalog_plan
- ask_market_bridge.py
- index_series.py
- worker/src/index.ts
- steps
- steps
- with
- executor.py
- glossary.py
- insights.py
- inputs
- with
- inputs
- json
- build_data_pack
- node_wave1
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
- repo_root
- install.sh
- fund_match.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- fund_catalog.py
- diagnose_lightsail_site.sh
- RunLogger
- node_compose
- EntityFunnel
- test_metal_fund_rating.py
- test_answer_precision.py
- build_derived_views
- market_scope_entities
- planner_catalog_knowledge.py
- extract_top_holdings
- entity_candidates.py
- pack_trim.py
- query_log.py
- test_holding_overlap.py
- fund_type_name_spec
- metals_spot_tables.py
- httpx
- memory/__init__.py
- maybe_install_balanced_portfolio_screen
- QuestionBrief
- news_fanout.py
- fund_brief.py
- test_ai_insight.py
- top_n_from_question
- test_return_windows.py
- portfolio_news_impact.py
- eval_basic_queries.py
- pick_compare_pair_with_fallback
- render_asked_facts
- prompts.py
- measured_facts_block
- _unhandled_exception_handler
- test_risk_analysis_without_periods_still_loads_one_three_and_five_year

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 607 edges
2. `ToolCall` - 367 edges
3. `get_settings()` - 141 edges
4. `apply_planner_post_hooks()` - 123 edges
5. `AnswerMode` - 108 edges
6. `node_compose()` - 102 edges
7. `QueryLogger` - 100 edges
8. `QuestionBrief` - 88 edges
9. `Settings` - 84 edges
10. `slot_route()` - 84 edges

## Surprising Connections (you probably didn't know these)
- `test_400_is_not_retried()` --uses--> `MospiError`  [INFERRED]
  tests/test_ai_insight_mospi.py → ai_insight/data/macro_data.py
- `fetch_google_news()` --uses--> `GoogleBlockedError`  [INFERRED]
  news_pipeline/graph/nodes/fetch_google_news.py → lib/google_guard.py
- `test_market_sector_lists_in_display_without_funds()` --uses--> `SubAsk`  [INFERRED]
  tests/test_insight_interpret.py → news_rag/insight/brief.py
- `test_structured_compose_orders_sub_asks_and_bold()` --uses--> `SubAsk`  [INFERRED]
  tests/test_insight_interpret.py → news_rag/insight/brief.py
- `retrieve_fund_articles()` --uses--> `PortfolioScope`  [INFERRED]
  news_rag/fund_brief.py → lib/portfolio_scope.py

## Import Cycles
- None detected.

## Communities (218 total, 36 thin omitted)

### Community 0 - "logging"
Cohesion: 0.06
Nodes (58): get_entity_funnel(), fetch_window_fields(), is_source_exhausted(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match() (+50 more)

### Community 1 - "Settings"
Cohesion: 0.03
Nodes (47): Publisher, SectorQuery, Settings, is_google_exhausted(), is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings() (+39 more)

### Community 2 - "fund_rating_screen.py"
Cohesion: 0.08
Nodes (42): _add_category_comparison(), _alternate_row_excluded(), _amc_matches(), _apply_category_difference(), balanced_portfolio_examples_spec(), _best_label(), _best_rated_row(), _cascade_labels_for_spec() (+34 more)

### Community 3 - "interpret.py"
Cohesion: 0.06
Nodes (67): asks_random_fund_compare(), Findings, FundFinding, SectorFinding, mentions_publication_date(), _assemble(), _caveat(), check_composer_guardrails() (+59 more)

### Community 4 - "fields.py"
Cohesion: 0.11
Nodes (22): periods_requested_in_question(), _asks_book(), bind_fields_to_tools(), _book_fields(), canonicalize_field(), field_need(), FieldNeed, fields_from_question() (+14 more)

### Community 5 - "article_quality.py"
Cohesion: 0.13
Nodes (18): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+10 more)

### Community 6 - "node_compose"
Cohesion: 0.16
Nodes (20): _asks_portfolio_rs_ratings(), field_answer_needs_composer(), _investor_holdings_rows(), is_pure_field_answer(), render_benchmark_comparison_table(), render_fact_answer(), render_investor_rs_ratings_table(), wants_comparison_table() (+12 more)

### Community 7 - "time"
Cohesion: 0.14
Nodes (29): _conversation_id(), GraphState, _load_planner_memory(), node_reply(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), append_chat_turn(), _fresh() (+21 more)

### Community 8 - "test_ask_speed.py"
Cohesion: 0.06
Nodes (36): analyst_should_run(), asks_market_briefing(), collect_evidence_calendar_dates(), add_article(), cores_for_float(), cores_in_text(), finalize_text_fields(), format_user_calendar_date() (+28 more)

### Community 9 - "Settings"
Cohesion: 0.08
Nodes (32): _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), article_in_fetch_window(), google_time_query(), has_news_date_range(), iter_inclusive_days() (+24 more)

### Community 10 - "fund_drawdown.py"
Cohesion: 0.15
Nodes (27): _add_drawdown_call(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), fetch_drawdown_periods(), fetch_trailing_drawdown(), investment_amount() (+19 more)

### Community 11 - "node_compose"
Cohesion: 0.05
Nodes (70): question_is_standalone_macro(), _categories_equivalent(), node_evidence_gate(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan() (+62 more)

### Community 12 - "concept_asks.py"
Cohesion: 0.31
Nodes (10): apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), asks_fof_funds(), test_concept_example_plan_screen_fof(), test_fof_name_one_detected() (+2 more)

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (48): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+40 more)

### Community 14 - "_attach_screen_facts"
Cohesion: 0.13
Nodes (18): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), pick_funds_by_label_cascade(), pick_rows_by_label_cascade() (+10 more)

### Community 15 - "tools.py"
Cohesion: 0.06
Nodes (57): question_needs_affected_sectors(), fetch_fund_managers_for_isin(), _finalize_screen_payload(), run_driver_affected_funds_adapter(), DataNeed, get_sector_fund_ranking_index(), _active_sector_equity(), _articles_for_affected_question() (+49 more)

### Community 16 - "fund_display.py"
Cohesion: 0.15
Nodes (21): _as_float(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_pct(), _fmt_pp(), _fmt_weight() (+13 more)

### Community 17 - "update.py"
Cohesion: 0.16
Nodes (18): drop_old_turns(), add_gist(), empty_frame(), empty_state(), expire_stale_entities(), push_fund(), stack_entry(), _subject() (+10 more)

### Community 18 - "QueryLogger"
Cohesion: 0.10
Nodes (7): _pillar_maximum(), _public_pillars(), clip_log_text(), _kv(), QueryLogger, _shrink_for_log(), _tool_digest()

### Community 19 - "news_reader.py"
Cohesion: 0.10
Nodes (37): _article_context_for_interpret(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority(), _clean_claims() (+29 more)

### Community 20 - "macro_data.py"
Cohesion: 0.14
Nodes (26): BondYieldResult, _client(), _codes(), walk(), CPIRecord, fetch_bond_yields(), fetch_cpi(), fetch_gdp() (+18 more)

### Community 21 - "test_portfolio_startup_cache.py"
Cohesion: 0.14
Nodes (17): question_asks_category_book_share(), question_asks_category_money(), bind_cached_portfolio(), _catalog_fund_holdings_question(), ensure_tools_for_data_question(), finish_portfolio_plan_bind(), _investor_args(), _merge_fund() (+9 more)

### Community 22 - "AnswerMode"
Cohesion: 0.12
Nodes (20): AnswerMode, normalize_portfolio_plan_from_question(), plan_matches_intent(), QuestionIntent, resolve_question_intent(), _top_n_from_question(), _asks_catalog_fund_performance(), _extract_fund_names() (+12 more)

### Community 23 - "failure_ledger.py"
Cohesion: 0.06
Nodes (39): _merge_publisher_error_reasons(), write_day_report(), _bucket(), _entity_names(), summarize_errors(), write_error_summary(), _atomic_write(), day_failure_slices_for_run() (+31 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.07
Nodes (58): aggregate_sectors_from_holdings(), extract_top_sectors(), _price_holdings(), _detail(), register_layer_tools(), run_fund_attribution_tool(), run_fund_portfolio(), run_fund_snapshot() (+50 more)

### Community 25 - "category_plan.py"
Cohesion: 0.05
Nodes (62): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), fund_type_name_spec(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), asks_cross_category_compare() (+54 more)

### Community 26 - "test_fund_display_tables.py"
Cohesion: 0.08
Nodes (29): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers(), _compose_hints() (+21 more)

### Community 27 - "ensure_registry"
Cohesion: 0.11
Nodes (26): _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext, LedgerEntry (+18 more)

### Community 28 - "resolve_fund_for_query"
Cohesion: 0.10
Nodes (25): fetch_fund_managers_for_query(), is_macro_metals_question(), is_market_fund_discovery_question(), lookup_extracted_fund(), _lookup_fund_scan_question(), prefer_resolved_fund_name(), resolve_fund_for_query(), resolve_fund_from_question() (+17 more)

### Community 29 - "fund_name_gate.py"
Cohesion: 0.08
Nodes (21): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), question_wants_gold_table(), asked_slots(), facts_only_compose_allowed(), merge_planner_asked_facts() (+13 more)

### Community 30 - "nse_fii_dii.py"
Cohesion: 0.29
Nodes (8): FlowLeg, _bucket(), fetch_fii_dii_snapshot(), _leg(), _nse_json(), _num(), test_bucket_fii_dii(), test_leg_parses_nse_row()

### Community 31 - "bridge.py"
Cohesion: 0.09
Nodes (15): evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), infer_fund_news_layers(), prefers_planner_over_slot(), asks_fund_related_news(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified() (+7 more)

### Community 32 - "_run_get_fund_data"
Cohesion: 0.12
Nodes (14): fetch_vs_benchmark(), merge_fund_insight_metrics(), _detail_for_fund_tool(), _fund_payload_matches_fund(), _isin_for_fund_name(), refetch_partial_fund_tools(), _repair_incomplete_fund_data(), _run_get_fund_data() (+6 more)

### Community 33 - "task_exec.py"
Cohesion: 0.13
Nodes (28): bind_subjects(), _book_total_line(), _canon_fact(), _category_in_planner_text(), _cell(), _compare_subject_kind(), coverage_line(), _fact_label() (+20 more)

### Community 34 - "llm_client.py"
Cohesion: 0.09
Nodes (37): health(), get_settings(), Settings, make_plan(), _slot_fallback(), anthropic_cache_control(), anthropic_system_blocks(), _call_anthropic() (+29 more)

### Community 35 - "book_news_map.py"
Cohesion: 0.21
Nodes (14): _clean_holding_tokens(), book_wide_sectors(), _display_name(), _has_named_stock(), news_calls_for_book(), _news_name(), _pct(), resolve_book_sector() (+6 more)

### Community 36 - "fund_search.py"
Cohesion: 0.09
Nodes (19): _clean_company_name(), detail_has_live_facts(), _entry_matches_amc(), _expand_query_token(), _fund_context_for_managers(), _fund_text(), FundIndex, get_fund_benchmark() (+11 more)

### Community 37 - "normalize.py"
Cohesion: 0.18
Nodes (21): aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values(), _book_has_market_value(), _fill_missing_from_live(), _first() (+13 more)

### Community 38 - "pack_sanitize.py"
Cohesion: 0.08
Nodes (30): append_investor_portfolio_overview_tables(), _fund_performance_digest(), strip_unasked_scheme_names(), attach_drawback_digest(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer(), question_asks_all_schemes_in_answer() (+22 more)

### Community 39 - "test_fund_rating_screen.py"
Cohesion: 0.08
Nodes (46): asks_taxonomy(), parse_rating_screen(), _return_direction(), run_rating_list(), _payload(), _rating(), test_a_named_large_cap_positive_year_stays_in_large_cap(), fetch() (+38 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "plan_enforce.py"
Cohesion: 0.04
Nodes (77): pick_best_matching_scheme(), _bound_fund_name(), _compare_sides_resolvable(), _known_names_in_text(), question_refers_deictic_fund_safe(), single_fund_for_deictic(), fund_authorized_for_question(), _resolve_funds() (+69 more)

### Community 42 - "build_evidence_pack"
Cohesion: 0.05
Nodes (50): normalize_sector_row(), ensure_affected_fund_screen(), market_affected_fund_calls(), EvidencePack, EvidenceRow, build_evidence_pack(), render_data_only_template(), table_source() (+42 more)

### Community 43 - "plan.py"
Cohesion: 0.11
Nodes (21): mentions_advice(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), _label_for_days(), _news_mode(), parse_plan() (+13 more)

### Community 44 - "macro_news_cache.py"
Cohesion: 0.10
Nodes (23): _run_get_macro_news(), _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read() (+15 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "affected_sectors.py"
Cohesion: 0.16
Nodes (12): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+4 more)

### Community 47 - "validate_plan_tools"
Cohesion: 0.12
Nodes (23): owned_holding_names(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question(), validate_plan_tools(), _all_holdings_metric_spec() (+15 more)

### Community 48 - "test_fund_drawdown.py"
Cohesion: 0.15
Nodes (27): asks_category_drawdown(), drawdown_words(), ensure_drawdown_tools(), is_drawdown_definition(), _named_standard_periods(), periods_for_question(), _question_needs_drawdown(), _plan() (+19 more)

### Community 49 - "fund_scheme_match.py"
Cohesion: 0.16
Nodes (14): amc_token_in_question(), _category_phrases_in_question(), _constraint_in_scheme_name(), _distinctive_constraints(), question_amc_hints(), scheme_match_score(), _scheme_name_tokens(), _scheme_vocab_tokens() (+6 more)

### Community 50 - "get_settings"
Cohesion: 0.07
Nodes (45): ask(), ask_memory(), ask_query_log(), ask_sources(), ask_stream(), AskRequest, _attach_llm_meta(), _attach_portfolio_to_ask() (+37 more)

### Community 51 - "gold_service.py"
Cohesion: 0.10
Nodes (24): _fetch(), get_gold_snapshot(), get_silver_snapshot(), _load_payload(), _merged_series(), add(), _normalize_windows(), _parse_date() (+16 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "insight/portfolio_scope.py"
Cohesion: 0.08
Nodes (37): build_drawdown_wave2_calls(), plan_wants_investor_drawdown_fetch(), plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), question_asks_portfolio_level_drawdown(), question_signals_investor_book(), plan_targets_single_fund_measured_return(), question_asks_current_book_allocation() (+29 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.12
Nodes (19): asks_category_performance(), asks_fund_category_average(), build_comparison_periods(), expense_ratio_for_question(), _f(), fund_returns_from_detail(), normalize_category_average_returns(), normalize_vs_benchmark_payload() (+11 more)

### Community 55 - "slot_router.py"
Cohesion: 0.06
Nodes (43): asks_rating_list(), rating_list_plan(), rating_concept_plan(), execute_wave(), QueryClass, ScopeKind, Wave2Policy, _asks_driver_sector_or_fund_impact() (+35 more)

### Community 56 - "test_portfolio_intents.py"
Cohesion: 0.14
Nodes (19): _as_of(), render_portfolio_fact(), apply_portfolio_intent(), data_need_for(), _keep_book_news(), modules_for(), normalize_portfolio_intent(), portfolio_intent_from_question() (+11 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "_normalize_fund_text"
Cohesion: 0.12
Nodes (18): labels_name_the_same_scheme(), _attach_trailing_product(), build_holding_overlap(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _entry_matches_query_scheme() (+10 more)

### Community 59 - "test_fund_payload_first.py"
Cohesion: 0.17
Nodes (9): fetch_public_rating(), headline_rating(), rating_for_request(), rating_needs_pillars(), _attach_rs_ratings_to_screen(), _one(), test_headline_helper_drops_computed_at(), test_headline_rating_has_no_date_and_skips_admin() (+1 more)

### Community 60 - "test_fund_risk.py"
Cohesion: 0.06
Nodes (56): asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison() (+48 more)

### Community 61 - "graph.py"
Cohesion: 0.15
Nodes (16): RequestTelemetry, _answer_stream_chunks(), Node, _plan_fetches_manager_roster(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta(), event_phase_completed() (+8 more)

### Community 62 - "retrieve_scoped_news"
Cohesion: 0.10
Nodes (21): _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank(), _macro_queries_for_sectors(), _merge_articles(), retrieve_layered_fund_news(), _sector_entities() (+13 more)

### Community 63 - "re"
Cohesion: 0.12
Nodes (20): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+12 more)

### Community 64 - "nav_service.py"
Cohesion: 0.12
Nodes (19): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+11 more)

### Community 65 - "fund_universe_agent.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "CapabilityCache"
Cohesion: 0.14
Nodes (7): CapabilityCache, _Entry, get_capability_cache(), test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner(), test_capabilities_cache_stores_and_retrieves()

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
Cohesion: 0.22
Nodes (14): _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), get_normalized_portfolio(), peek_derived(), preload_configured_portfolio(), _run() (+6 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.07
Nodes (30): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker(), sector_query_for_label(), _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news() (+22 more)

### Community 73 - "test_insight_graph.py"
Cohesion: 0.16
Nodes (12): build_result(), _insight_headline_narrative(), node_resolve(), run_graph(), run_graph_pipeline(), _store_turn_memory(), drain_cache_events(), _state() (+4 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "ensure_registry"
Cohesion: 0.13
Nodes (22): plan_to_brief(), tools_to_facets(), all_tools(), _eligible(), ensure_registry(), pick_tool_for_facet(), registry_prompt_block(), tools_providing() (+14 more)

### Community 77 - "ExecutionPlan"
Cohesion: 0.03
Nodes (129): ensure_rating_screen(), _followup_modules(), category_composition_plan_applies(), _compare_fund_count(), finalize_unnamed_catalog_compare(), _split_count(), ExecutionPlan, ToolCall (+121 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.21
Nodes (13): extract_top_holdings(), _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), _holdings_file(), _initials() (+5 more)

### Community 79 - "rupeestop_auth.py"
Cohesion: 0.15
Nodes (19): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+11 more)

### Community 80 - "display_table_policy.py"
Cohesion: 0.10
Nodes (20): resolve_display_periods(), DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), filter_display_tables(), _limit_tables(), _named_fund_overview(), _news_primary() (+12 more)

### Community 81 - "test_portfolio_layer.py"
Cohesion: 0.12
Nodes (13): _run_get_investor_portfolio(), node_bridge(), get_active_crn(), fetch_top_holdings(), project_concentration(), match_scheme_filter(), _attach_ratings(), _pick_row() (+5 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.14
Nodes (33): _age(), _allocation_bucket_rows(), _book_line(), _category_amount_map(), _comparison_rows(), _composition_line(), _float_or_none(), _fund_line() (+25 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "get_fund_index"
Cohesion: 0.06
Nodes (22): normalize_sector_label(), _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), classify_sector_fund_purity(), _damerau() (+14 more)

### Community 86 - "test_rupeestop_auth.py"
Cohesion: 0.09
Nodes (5): _jwt(), test_admin_headers_use_token_from_login(), test_expired_jwt_logs_in_once_and_reuses_fresh_token(), test_failed_login_keeps_previous_token(), test_valid_jwt_does_not_call_login()

### Community 87 - "screen_hints_from_question"
Cohesion: 0.14
Nodes (17): _clean_stock_capture(), screen_hints_from_question(), stock_name_from_question(), test_defence_fund_screen_uses_defense_category(), test_fof_fund_screen_returns_fof_schemes(), test_funds_invested_in_hdfc_bank_not_hdfc_amc_catalog(), test_banking_and_defence_funds_are_categories_not_sectors(), test_category_beats_a_shorter_cap_phrase() (+9 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.14
Nodes (19): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+11 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 90 - "nse_sector_indices.py"
Cohesion: 0.20
Nodes (11): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _clear_index_cache(), test_by_sector_keys_match_sector_queries_exactly(), test_every_sector_has_verified_ticker_field() (+3 more)

### Community 91 - "compare_evidence.py"
Cohesion: 0.24
Nodes (8): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_maybe_run_compare_retries_after_failed_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 93 - "prompts.py"
Cohesion: 0.16
Nodes (11): field_prompt_table(), _invalidate_plan_system_cache(), plan_system_prompt(), build_anthropic_messages_body(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), test_plan_system_prompt_planner_authority() (+3 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.07
Nodes (52): _add_category_comparison(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line(), _compare_cell(), _compare_header(), _complete_fund_row(), _complete_shown_funds() (+44 more)

### Community 96 - "portfolio/client.py"
Cohesion: 0.14
Nodes (16): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), InvalidCRN, PortfolioError, PortfolioNotConfigured, PortfolioUnavailable (+8 more)

### Community 97 - "NumericRecord"
Cohesion: 0.18
Nodes (17): NumericRecord, unavailable(), fetch_cpi_record(), pick(), fetch_fii_dii(), fetch_gdp_record(), fetch_gsec(), fetch_gst() (+9 more)

### Community 98 - "validate_capability_args"
Cohesion: 0.10
Nodes (17): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), test_default_windows_are_one_three_and_five_years(), test_named_window_is_not_expanded() (+9 more)

### Community 99 - "fund_display.py"
Cohesion: 0.07
Nodes (20): append_news_section(), _assess_table_quality(), clean_news_insight(), complete_sentences(), ensure_markdown_table_spacing(), _insert_before_disclaimer(), is_article_only_news(), news_insight_articles() (+12 more)

### Community 100 - "pathlib"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 102 - "MospiClient"
Cohesion: 0.23
Nodes (4): MospiError, _payload(), _sse_json(), GraphUnavailable

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.14
Nodes (14): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_WINDOW_HOURS, note() (+6 more)

### Community 104 - "env"
Cohesion: 0.13
Nodes (15): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE (+7 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.22
Nodes (10): build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score(), test_default_manager_answer_drops_former_managers(), test_enrich_filters_past_only() (+2 more)

### Community 106 - "macro_impact_map.py"
Cohesion: 0.15
Nodes (16): _rule_sector_picks(), canonical_direction_for_driver(), clear_macro_impact_cache(), _document(), _driver_row(), list_macro_drivers(), macro_impact_entry(), macro_series_for_driver() (+8 more)

### Community 107 - "market_pulse.py"
Cohesion: 0.04
Nodes (54): _warmup_embeddings_background(), _run(), article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), AskPlan, EntityMention (+46 more)

### Community 108 - "fund_rating_categories.py"
Cohesion: 0.09
Nodes (24): categories_for(), CategoryMatch, _close(), explanation_brief(), fund_type_for_category(), match_all_fund_types(), _metal_category(), _metal_flags() (+16 more)

### Community 109 - "call_json_llm"
Cohesion: 0.21
Nodes (16): _blocks_to_parts(), call_json_llm(), _model_for(), _composer_partial_usable(), _summarize_parsed_for_log(), _layered_news_topics(), _client(), _gemini_response() (+8 more)

### Community 110 - "output_judge.py"
Cohesion: 0.13
Nodes (10): extract_assistant_text(), _json_balance(), parse_json_from_text(), _plain_answer_from_reasoning(), salvage_truncated_json(), _loads_closed(), judge_answer(), JudgeResult (+2 more)

### Community 111 - "test_portfolio_layer.py"
Cohesion: 0.10
Nodes (14): question_wants_invested_value_table(), _drop_sold(), normalized_doc(), test_allocation_drops_dust_and_matches_book_aum(), test_book_schemes_are_the_open_holdings(), test_current_value_and_nonzero_xirr(), test_holdings_table_uses_exact_value(), test_invested_value_table_for_each_holding() (+6 more)

### Community 112 - "execute_capability"
Cohesion: 0.15
Nodes (10): _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), widen_portfolio_args(), compare_payload_matches_funds(), test_compare_conversation_cache_does_not_reuse_different_pair(), fake_compare(), test_compare_conversation_cache_hits_same_pair() (+2 more)

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 114 - "planner_policy.py"
Cohesion: 0.14
Nodes (10): sector_focus_from_market(), drop_unasked_fund_modules(), _ensure_sector_overview(), question_uses_now_window(), trim_named_fund_overview(), _asks_fund_manager(), asks_sector_overview(), test_banking_sector_question_is_an_overview_not_a_fund_list() (+2 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "format_inr"
Cohesion: 0.21
Nodes (11): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), _fmt_inr(), test_format_indian_amount_lakh() (+3 more)

### Community 117 - "test_guardrails_domain.py"
Cohesion: 0.20
Nodes (11): question_in_finance_scope(), check_guardrails(), financial_keyword_signal(), GuardrailResult, test_crude_why_not_misrouted_to_random_fund(), test_fund_question_still_passes(), test_hdfc_bank_passes_guardrails(), test_hdfc_bank_short_happening_passes() (+3 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "test_ai_insight_mospi.py"
Cohesion: 0.27
Nodes (9): _client(), _sse(), test_400_is_not_retried(), test_gdp_yoy_uses_prior_fiscal_year(), handler(), test_retries_500_then_reads_cache(), handler(), test_wpi_yoy_is_derived() (+1 more)

### Community 121 - "run_ask_engine"
Cohesion: 0.19
Nodes (7): _events(), run_ask_engine(), stream_ask_engine(), run_insight_pipeline(), stream_insight_pipeline(), test_ask_engine_delegates_to_insight_pipeline(), test_streaming_sse_order()

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "lib/google_news.py"
Cohesion: 0.04
Nodes (38): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), fetch_url() (+30 more)

### Community 124 - "test_composer_table_summaries.py"
Cohesion: 0.24
Nodes (8): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_filter_display_tables_by_decision(), test_holdings_question_data_only_skips_returns_table(), test_parse_tables_append_directive(), test_strip_empty_bold_sections(), test_summarize_tables_for_composer_extracts_mix_and_holdings()

### Community 125 - "evidence.py"
Cohesion: 0.28
Nodes (9): clear_conversation(), recall_slice(), recall_wider_portfolio(), remember_slice(), slice_key(), slice_slot(), test_holdings_then_sectors_keep_both_slices(), test_period_change_does_not_reuse_the_other_window() (+1 more)

### Community 126 - "run-pipeline"
Cohesion: 0.22
Nodes (8): jobs, run-pipeline, name, on, schedule, runs-on, timeout-minutes, cron

### Community 127 - "enforce_planner_catalog_plan"
Cohesion: 0.12
Nodes (28): _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings(), _ensure_portfolio_data_for_compare(), _ensure_portfolio_data_for_holdings(), ensure_whole_book_catalog_scope(), _funds_from_entities(), _holding_scope() (+20 more)

### Community 128 - "ask_market_bridge.py"
Cohesion: 0.22
Nodes (7): fetch_ask_market_records(), fetch_gold_record(), get_ask_market_snapshot(), write_ask_market_snapshot(), test_fetch_ask_market_records_includes_extras(), test_fetch_gold_record_ok(), test_get_ask_market_snapshot_shape()

### Community 129 - "index_series.py"
Cohesion: 0.22
Nodes (11): nifty50_ticker(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns(), _read_cache(), scheme_benchmark_metadata(), worst_sector_by_return() (+3 more)

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

### Community 134 - "executor.py"
Cohesion: 0.11
Nodes (24): _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _conversation_id(), _conversation_turn(), _one_fund(), _fill_returns_from_catalog(), _filter_excluded_screen_rows() (+16 more)

### Community 135 - "glossary.py"
Cohesion: 0.26
Nodes (10): asks_precise_definition(), direct_glossary_reply(), extract_glossary_term(), glossary_execution_plan(), meaning_reply(), _normalize_term(), test_fund_nav_not_glossary(), test_nav_full_form_direct_reply() (+2 more)

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
Cohesion: 0.05
Nodes (38): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+30 more)

### Community 141 - "build_data_pack"
Cohesion: 0.38
Nodes (3): build_data_pack(), build(), _compact()

### Community 142 - "node_wave1"
Cohesion: 0.18
Nodes (8): _attach_conversation(), _catalog_fanout_fund_names(), _ensure_portfolio_for_fund_news(), _maybe_compare_funds_after_multi_screen(), _maybe_enrich_picked_fund_from_screen(), node_wave1(), node_wave2(), repair_compare_with_screen_peer()

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

### Community 159 - "repo_root"
Cohesion: 0.26
Nodes (7): FiiDiiSnapshot, _cache_dir(), write_snapshot(), main(), write_fii_dii(), write_latest(), repo_root()

### Community 163 - "fund_match.py"
Cohesion: 0.15
Nodes (10): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), load_fund_embedding_cache(), _normalize_fund_text() (+2 more)

### Community 170 - "fund_catalog.py"
Cohesion: 0.13
Nodes (22): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+14 more)

### Community 178 - "node_compose"
Cohesion: 0.06
Nodes (33): rating_lead(), asks_computed_illustration(), strip_grounding_holes(), strip_missing_data_caveats(), strip_private_leaks(), _drop_scheme_is_the_whole_book(), node_compose(), _rating_lead_for_pack() (+25 more)

### Community 180 - "test_metal_fund_rating.py"
Cohesion: 0.27
Nodes (8): ensure_quality_fund_list(), _payload(), _rating(), test_gold_list_spreads_etf_and_fund_of_funds(), fetch(), test_my_gold_fund_does_not_add_category_screen(), test_named_gold_etf_is_not_a_category_list(), test_planner_gold_sector_screen_becomes_rating_list()

### Community 181 - "test_answer_precision.py"
Cohesion: 0.14
Nodes (11): fact_values_already_stated(), question_wants_fact_table(), strip_context_disclaimer(), _clean_answer(), strip_meta_opening_heading(), _strip_unasked_closers(), test_fact_table_only_for_compare_or_an_explicit_list(), test_fact_table_skipped_when_prose_has_the_figure() (+3 more)

### Community 182 - "build_derived_views"
Cohesion: 0.22
Nodes (10): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), _doc() (+2 more)

### Community 183 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

### Community 184 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 185 - "extract_top_holdings"
Cohesion: 0.17
Nodes (13): normalize_holding_row(), _group_layered_articles(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows() (+5 more)

### Community 186 - "entity_candidates.py"
Cohesion: 0.30
Nodes (6): candidates_block(), entity_candidates(), _holding_candidates(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

### Community 188 - "query_log.py"
Cohesion: 0.19
Nodes (9): ParsedQuery, attach_query_log_meta(), find_query_log_file(), query_log_page_href(), read_query_log(), test_attach_query_log_meta_adds_page_link(), test_finish_writes_json_sidecar(), test_log_parsed_includes_intent_and_fund() (+1 more)

### Community 190 - "test_holding_overlap.py"
Cohesion: 0.24
Nodes (8): _compare_return_windows(), _detail(), test_a_comparison_keeps_one_three_and_five_years_plus_benchmark_and_rating(), test_compare_table_includes_risk_for_both_funds(), test_extra_part_brief_names_both_funds(), test_no_overlap_message_and_overlap_table(), test_overlap_uses_full_stock_list_and_skips_cash(), test_unnamed_catalog_periods_are_measured_together()

### Community 191 - "fund_type_name_spec"
Cohesion: 0.11
Nodes (13): _category_fund_name_spec(), fund_naming_clause(), _label_in(), _looks_like_fund_list(), _metal_fund_categories(), _metal_fund_spec(), _question_names_amc_scheme(), rating_screen_question() (+5 more)

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 193 - "httpx"
Cohesion: 0.18
Nodes (4): fetch_category_ratings(), main(), main(), test_category_rating_request_uses_admin_header()

### Community 194 - "memory/__init__.py"
Cohesion: 0.15
Nodes (13): greeting_reply(), identity_reply(), _mirror_greeting(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens() (+5 more)

### Community 195 - "maybe_install_balanced_portfolio_screen"
Cohesion: 0.36
Nodes (8): asks_balanced_long_horizon_fund_menu(), asks_ideal_portfolio_shape(), _asks_ideal_portfolio_allocation(), maybe_install_balanced_portfolio_screen(), test_ideal_portfolio_without_planner_allocation_does_not_install_a_screen(), test_long_horizon_fund_names_uses_seven_sleeves(), test_misclassified_allocation_with_investor_tool_never_clears_tools(), test_portfolio_allocation_without_screen_signals_does_not_clarify_horizon()

### Community 197 - "QuestionBrief"
Cohesion: 0.09
Nodes (31): asks_sector_lists(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief(), _detect_direction(), _detect_funds(), _heuristic_brief() (+23 more)

### Community 198 - "news_fanout.py"
Cohesion: 0.33
Nodes (5): embed_query(), _body(), grouped_news(), NewsTarget, search_targets()

### Community 203 - "fund_brief.py"
Cohesion: 0.06
Nodes (61): build_portfolio_scope(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest() (+53 more)

### Community 206 - "test_ai_insight.py"
Cohesion: 0.18
Nodes (6): digest_filter(), _holding_mentioned(), matches_entity(), contains_phrase(), test_digest_filter_uses_stricter_scores(), test_sector_exclude_drops_nbfc_from_banks()

### Community 208 - "top_n_from_question"
Cohesion: 0.36
Nodes (5): top_n_from_question(), test_top_five_sectors(), test_top_sector_singular(), test_top_sectors_default_three(), test_top_six_word()

### Community 209 - "test_return_windows.py"
Cohesion: 0.11
Nodes (19): _capability_cache_key(), _positive_ms(), _return_slice_covers(), _trim_cached_to_ask(), test_missing_window_is_not_covered(), test_wider_cached_fund_payload_covers_and_trims_to_the_ask(), _wide(), test_return_slice_requires_pillars_when_requested() (+11 more)

### Community 210 - "portfolio_news_impact.py"
Cohesion: 0.15
Nodes (13): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), render_portfolio_news_impact_markdown(), _strip_book_concentration_tables() (+5 more)

### Community 211 - "eval_basic_queries.py"
Cohesion: 0.39
Nodes (7): _cases(), _check_plan(), _expects(), main(), _modules(), _offline_plan(), _turns()

### Community 212 - "pick_compare_pair_with_fallback"
Cohesion: 0.21
Nodes (4): _amc_outside_label(), _amc_token(), pick_compare_pair_with_fallback(), test_short_category_moves_to_another_with_two_funds()

### Community 213 - "render_asked_facts"
Cohesion: 0.48
Nodes (5): missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), test_aum_slot_renders_from_snapshot()

### Community 214 - "prompts.py"
Cohesion: 0.29
Nodes (4): build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

## Knowledge Gaps
- **20 isolated node(s):** `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT`, `MACRO_NEWS_ENABLED` (+15 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1676 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `fund_rating_screen.py`, `fields.py`, `node_compose`, `glossary.py`, `time`, `node_compose`, `concept_asks.py`, `node_wave1`, `fund_display.py`, `update.py`, `macro_data.py`, `test_portfolio_startup_cache.py`, `AnswerMode`, `category_plan.py`, `fund_name_gate.py`, `bridge.py`, `task_exec.py`, `llm_client.py`, `book_news_map.py`, `pack_sanitize.py`, `test_fund_rating_screen.py`, `plan_enforce.py`, `build_evidence_pack`, `plan.py`, `validate_plan_tools`, `test_fund_drawdown.py`, `node_compose`, `gold_service.py`, `test_metal_fund_rating.py`, `test_answer_precision.py`, `insight/portfolio_scope.py`, `slot_router.py`, `test_portfolio_intents.py`, `test_fund_payload_first.py`, `test_fund_risk.py`, `graph.py`, `test_holding_overlap.py`, `maybe_install_balanced_portfolio_screen`, `test_insight_graph.py`, `ensure_registry`, `display_table_policy.py`, `test_return_windows.py`, `fact_answer.py`, `portfolio_news_impact.py`, `eval_basic_queries.py`, `test_portfolio_allocation.py`, `compare_evidence.py`, `evidence_pack.py`, `test_portfolio_layer.py`, `planner_policy.py`, `test_composer_table_summaries.py`, `enforce_planner_catalog_plan`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `ExecutionPlan` (e.g. with `news_calls_for_book()` and `sector_book()`) actually correct?**
  _`ExecutionPlan` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN` to the rest of the system?**
  _20 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.06221889055472264 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ExecutionPlan` to `fund_rating_screen.py`, `fields.py`, `executor.py`, `time`, `fund_drawdown.py`, `node_compose`, `concept_asks.py`, `node_wave1`, `update.py`, `macro_data.py`, `test_portfolio_startup_cache.py`, `AnswerMode`, `category_plan.py`, `fund_name_gate.py`, `bridge.py`, `task_exec.py`, `book_news_map.py`, `pack_sanitize.py`, `test_fund_rating_screen.py`, `plan_enforce.py`, `build_evidence_pack`, `plan.py`, `validate_plan_tools`, `test_fund_drawdown.py`, `gold_service.py`, `test_metal_fund_rating.py`, `insight/portfolio_scope.py`, `slot_router.py`, `test_portfolio_intents.py`, `test_fund_risk.py`, `graph.py`, `test_holding_overlap.py`, `maybe_install_balanced_portfolio_screen`, `CapabilityCache`, `test_insight_graph.py`, `ensure_registry`, `display_table_policy.py`, `test_return_windows.py`, `portfolio_news_impact.py`, `test_portfolio_allocation.py`, `compare_evidence.py`, `test_portfolio_layer.py`, `execute_capability`, `planner_policy.py`, `enforce_planner_catalog_plan`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ToolCall` (e.g. with `news_calls_for_book()` and `_apply_planner_request()`) actually correct?**
  _`ToolCall` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `Settings` be split into smaller, more focused modules?**
  _Cohesion score 0.03377284293314828 - nodes in this community are weakly interconnected._