# Graph Report - db_design_with_qdrant_locally  (2026-11-20)

## Corpus Check
- 746 files · ~1,121,251 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 31 file(s) not represented in the graph (top: .example 6, .log 5, (none) 4)

## Summary
- 7565 nodes · 24575 edges · 272 communities (214 shown, 58 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 744 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `920b5444`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- execute_capability
- plan_enforce.py
- interpret.py
- ToolCall
- market_data.py
- fii_dii_flow_narrative/run.py
- format_inr
- test_two_wave_pipeline.py
- Settings
- sector_leaderboard/run.py
- QuestionBrief
- display_table_policy.py
- compute.py
- insight_links.py
- tools.py
- retrieve_scoped_news
- json
- QueryLogger
- news_reader.py
- macro_data.py
- datetime
- match.py
- Settings
- tool_runners.py
- test_equity_fund_week.py
- test_fund_display_tables.py
- gather.py
- investor_drawback.py
- ExecutionPlan
- logging.py
- trends.py
- sources/google_news.py
- task_exec.py
- llm_client.py
- sector_query_for_label
- fund_display.py
- normalize.py
- project_modules
- plan.py
- env
- run_daily.py
- article_quality.py
- plan_enforce.py
- test_portfolio_startup_cache.py
- env
- screen_hints_from_question
- portfolio_news_impact.py
- entity_retrieval.py
- fund_scheme_match.py
- app.py
- gold_service.py
- env
- investor_subject.py
- fund_rupeestop_metrics.py
- typing
- test_sector_leaderboard_run.py
- scrape-worker/package.json
- resolve_fund_for_query
- executor.py
- node_compose
- test_insight_news_link.py
- test_ai_insight_common_qdrant_access.py
- re
- pytest
- fund_universe_agent.py
- batch.ts
- twelve_data_brent.py
- insight/guardrails.py
- http-fetch.ts
- embed.py
- portfolio/cache.py
- holdings_market.py
- RatingScreenSpec
- with
- fields.py
- sector_fund_ranking.py
- stock_fund_ranking.py
- rupeestop_auth.py
- Cluster
- time
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- scrape_bodies.py
- fii_dii_flow_narrative/prompt.py
- sector_indices.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- official.py
- news_filter.py
- env
- steps
- evidence_pack.py
- affected_sectors.py
- NumericRecord
- EvidencePack
- qdrant_access.py
- sector_exposure_tables.py
- portfolio/client.py
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- portfolio_news_impact.py
- market_pulse.py
- _normalize_fund_text
- fund_drawdown.py
- fund_match.py
- Settings
- explicit_fund_count
- fund_rating_categories.py
- insights.py
- vitest
- entity_candidates.py
- test_insight_interpret.py
- compilerOptions
- compilerOptions
- macro_news_cache.py
- stock_explain.py
- backfill
- relationships.py
- news_digest.py
- normalize_rs_label
- run-pipeline
- update.py
- common/store.py
- market_scope_entities
- worker/src/index.ts
- steps
- steps
- with
- json
- test_fund_drawdown.py
- _fund_performance_digest
- inputs
- with
- inputs
- asks_computed_illustration
- price.py
- test_news_only_answer.py
- run-backfill.sh
- qdrant
- node_compose
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
- threading
- install.sh
- test_sector_leaderboard_score.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- nse_fii_dii.py
- GraphState
- diagnose_lightsail_site.sh
- fund_search.py
- graph.py
- EntityFunnel
- news.py
- test_metal_fund_rating.py
- portfolio_insights.js
- fund_catalog.py
- v2_scoring.py
- prompts.py
- nav_service.py
- ._ensure_loaded
- narrative.py
- security_master.py
- build_derived_views
- metals_spot_tables.py
- infer_fund_news_layers
- measured_facts_block
- test_rating_screen_uses_focus_question_not_full_compare_question
- brief.py
- 283041/manifest.json
- _amc_outside_label
- fund_brief.py
- test_ai_insight.py
- Envelope
- 57e233/manifest.json
- test_return_windows.py
- c72b25/manifest.json
- a45664/manifest.json
- compare_evidence.py
- 7859f0/manifest.json
- test_greeting.py
- contracts.py
- layer_tools.py
- Cluster
- insights.js
- holding_insights.js
- insight_log.js
- fix-daily-ingest.sh
- news_pipeline/config.py
- test_admin_headers_use_token_from_login
- data_pack.py
- router.py
- holding_insights/llm.py
- app.js
- run_insights_daily.sh
- sys
- install-insights-cron.sh
- test_ai_insight_mospi.py
- test_composer_table_summaries.py
- test_fund_rating_screen.py
- eval_planner.py
- EvidenceArticle
- holding_insights_stock_log.js
- planner_catalog_knowledge.py
- load_config
- strip_news_roundup
- MospiError
- test_equity_fund_week.py
- load_equity_holdings
- fund_type_name_spec
- compose_llm.py
- yf_week.py

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 607 edges
2. `ToolCall` - 367 edges
3. `get_settings()` - 147 edges
4. `apply_planner_post_hooks()` - 123 edges
5. `load_config()` - 115 edges
6. `AnswerMode` - 108 edges
7. `node_compose()` - 102 edges
8. `QueryLogger` - 100 edges
9. `Settings` - 95 edges
10. `QuestionBrief` - 88 edges

## Surprising Connections (you probably didn't know these)
- `test_stock_entries_splits_by_move()` --calls--> `_stock_entries()`  [EXTRACTED]
  tests/test_equity_fund_week.py → new/compose_llm.py
- `test_compose_structured_narrative()` --calls--> `compose_fund_narrative()`  [EXTRACTED]
  tests/test_equity_fund_week.py → new/compose_llm.py
- `test_equity_week_defaults_to_haiku()` --calls--> `equity_week_llm_kwargs()`  [EXTRACTED]
  tests/test_equity_fund_week.py → new/equity_week_llm.py
- `test_select_drivers_sign()` --calls--> `select_drivers()`  [EXTRACTED]
  tests/test_equity_fund_week.py → new/fund_context.py
- `test_clamp_why_keeps_full_sentences()` --calls--> `clamp_why_paragraph()`  [EXTRACTED]
  tests/test_equity_fund_week.py → new/stock_explain.py

## Import Cycles
- 2-file cycle: `ai_insight/common/entity_retrieval.py -> ai_insight/common/retrieval_plan.py -> ai_insight/common/entity_retrieval.py`

## Communities (272 total, 58 thin omitted)

### Community 0 - "logging"
Cohesion: 0.07
Nodes (47): get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match(), _is_duplicate() (+39 more)

### Community 1 - "execute_capability"
Cohesion: 0.13
Nodes (7): CapabilityCache, _Entry, get_capability_cache(), test_complete_payload_is_stored_in_capability_cache(), test_partial_fund_payload_is_not_stored_in_capability_cache(), stub_runner(), test_capabilities_cache_stores_and_retrieves()

### Community 2 - "plan_enforce.py"
Cohesion: 0.04
Nodes (83): asks_ideal_portfolio_shape(), _metal_fund_categories(), _question_names_amc_scheme(), plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), _bound_fund_name(), _compare_sides_resolvable(), _known_names_in_text() (+75 more)

### Community 3 - "interpret.py"
Cohesion: 0.08
Nodes (59): asks_market_briefing(), asks_sector_lists(), Findings, FundFinding, mentions_publication_date(), _assemble(), _caveat(), check_composer_guardrails() (+51 more)

### Community 4 - "ToolCall"
Cohesion: 0.03
Nodes (93): ensure_rating_screen(), _followup_modules(), finalize_unnamed_catalog_compare(), _split_count(), EvidenceRow, ToolCall, build_evidence_pack(), merge_planner_asked_facts() (+85 more)

### Community 5 - "market_data.py"
Cohesion: 0.13
Nodes (23): editorial_context(), market_numbers(), build_aligned_table(), _done(), _flow_data(), _from_history(), get_fii_dii_today(), get_index_history() (+15 more)

### Community 6 - "fii_dii_flow_narrative/run.py"
Cohesion: 0.04
Nodes (77): fmt_inr_crore(), ordinal(), cumulative(), FlowDay, history_path(), load_flow_history(), _num(), MarketDriverFactsBase (+69 more)

### Community 7 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 8 - "test_two_wave_pipeline.py"
Cohesion: 0.10
Nodes (25): collect_evidence_calendar_dates(), add_article(), cores_in_text(), finalize_text_fields(), format_user_calendar_date(), number_is_grounded(), numeric_core(), _ordinal_day() (+17 more)

### Community 9 - "Settings"
Cohesion: 0.09
Nodes (32): _subprocess(), _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), article_in_fetch_window(), google_time_query(), has_news_date_range() (+24 more)

### Community 10 - "sector_leaderboard/run.py"
Cohesion: 0.13
Nodes (37): build_narrative_user(), _abs_scores(), backtest(), build(), _cell(), _chips(), compose_body(), _context() (+29 more)

### Community 11 - "QuestionBrief"
Cohesion: 0.08
Nodes (26): analyst_should_run(), _topic_sector_label(), _log_brief(), nearest_return_window(), question_tier(), QuestionBrief, _success_criteria(), validate_brief_plan() (+18 more)

### Community 12 - "display_table_policy.py"
Cohesion: 0.04
Nodes (55): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), DisplayTablePolicy, _drop_sparse_in_table(), drop_sparse_table_columns(), fact_values_already_stated() (+47 more)

### Community 13 - "compute.py"
Cohesion: 0.10
Nodes (30): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+22 more)

### Community 14 - "insight_links.py"
Cohesion: 0.17
Nodes (13): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings() (+5 more)

### Community 15 - "tools.py"
Cohesion: 0.05
Nodes (66): question_needs_affected_sectors(), extract_top_sectors(), fetch_fund_managers_for_isin(), _finalize_screen_payload(), run_driver_affected_funds_adapter(), DataNeed, get_sector_fund_ranking_index(), rank_funds_by_sector_exposure() (+58 more)

### Community 16 - "retrieve_scoped_news"
Cohesion: 0.05
Nodes (34): _pack_row(), _trim_snippet(), embed_query(), corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news(), _layer_rank() (+26 more)

### Community 17 - "json"
Cohesion: 0.04
Nodes (41): JobProgress, _write(), atomic_write_json(), holding_data_dir(), HoldingInsightsJobManager, on_progress(), HoldingJobBusy, HoldingJobView (+33 more)

### Community 18 - "QueryLogger"
Cohesion: 0.07
Nodes (16): _retrieve_bullion_for_entities(), slots_from_plan(), ParsedQuery, attach_query_log_meta(), clip_log_text(), find_query_log_file(), _kv(), query_log_page_href() (+8 more)

### Community 19 - "news_reader.py"
Cohesion: 0.13
Nodes (30): _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector(), _claim_priority(), _clean_claims(), _clean_sector_calls() (+22 more)

### Community 20 - "macro_data.py"
Cohesion: 0.14
Nodes (26): PortfolioComposeRequest, BondYieldResult, _client(), _codes(), walk(), CPIRecord, fetch_bond_yields(), fetch_cpi() (+18 more)

### Community 21 - "datetime"
Cohesion: 0.07
Nodes (54): CommonConfig, _append(), _clock(), RunLog, _write(), _bound_llm(), bundle_cli_main(), cli_main() (+46 more)

### Community 22 - "match.py"
Cohesion: 0.06
Nodes (49): _articles(), build_market_daily_snapshot(), _daily_path(), load_market_daily(), _newer_bundle(), save_market_daily(), _sector_names(), _usage() (+41 more)

### Community 23 - "Settings"
Cohesion: 0.05
Nodes (41): _merge_publisher_error_reasons(), write_day_report(), _bucket(), _entity_names(), summarize_errors(), write_error_summary(), _atomic_write(), day_failure_slices_for_run() (+33 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.09
Nodes (48): headline_rating(), build_holding_overlap(), _lazy_register(), register(), ToolSpec, build_default_registry(), _driver_without_sector(), _enrich_compare_brief() (+40 more)

### Community 25 - "test_equity_fund_week.py"
Cohesion: 0.18
Nodes (20): _attach_daily_bars(), attribution_summary(), build_fund_facts(), cushion_funds(), _daily_prices_for_holding(), _equity_holdings_from_detail(), _fmt_signed_pct(), _fund_return_1w_api() (+12 more)

### Community 26 - "test_fund_display_tables.py"
Cohesion: 0.08
Nodes (27): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), ensure_markdown_table_spacing(), format_display_tables_markdown(), normalize_user_facing_text(), stitch_display_tables_into_answer(), strip_composer_display_sections(), strip_empty_table_pointers() (+19 more)

### Community 27 - "gather.py"
Cohesion: 0.10
Nodes (30): _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), EvidenceItem, _extract_funds_from_result(), gather_evidence(), GatherContext (+22 more)

### Community 28 - "investor_drawback.py"
Cohesion: 0.08
Nodes (34): is_drawdown_definition(), node_bridge(), attach_drawback_digest(), build_drawdown_wave2_calls(), _fmt_inr(), plan_wants_investor_drawdown_fetch(), plan_wants_pure_concentration(), _pretty_category() (+26 more)

### Community 29 - "ExecutionPlan"
Cohesion: 0.04
Nodes (90): ExecutionPlan, _attach_rs_ratings_to_screen(), tag_answer_parts(), _wants_end_summary(), plan_wants_portfolio_drawback(), plan_targets_single_fund_measured_return(), question_asks_holding_metric_and_glossary(), _bind_fund_list() (+82 more)

### Community 30 - "logging.py"
Cohesion: 0.15
Nodes (8): _env_secrets(), prune_logs(), _redact(), _redact_text(), _rmtree(), RunArtifacts, _usage(), test_artifacts_redact_and_prune()

### Community 31 - "trends.py"
Cohesion: 0.13
Nodes (15): detect_signals(), _surge(), DayPoint, entity_daily_series(), price_trend(), price_trend_from_closes(), PriceTrend, session_day() (+7 more)

### Community 32 - "sources/google_news.py"
Cohesion: 0.14
Nodes (15): fetch_entity_items(), _fetch_query_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url(), fetch_macro_items(), is_macro_match(), macro_fetch_entities() (+7 more)

### Community 33 - "task_exec.py"
Cohesion: 0.10
Nodes (34): _spaced_category_words(), bind_subjects(), _book_total_line(), _canon_fact(), _category_in_planner_text(), _cell(), _compare_subject_kind(), coverage_line() (+26 more)

### Community 34 - "llm_client.py"
Cohesion: 0.05
Nodes (68): ask(), ask_stream(), AskRequest, _attach_llm_meta(), fund_brief(), health(), get_settings(), anthropic_cache_control() (+60 more)

### Community 35 - "sector_query_for_label"
Cohesion: 0.09
Nodes (28): _default_phrase(), primary_sector_headline_phrase(), sector_headline_phrase(), match_sectors(), _sector_index_from_daily(), append_personal_tail(), _display_fund_name(), _fetch_fund_short_name() (+20 more)

### Community 36 - "fund_display.py"
Cohesion: 0.10
Nodes (32): _as_float(), _assess_table_quality(), build_fund_display_tables(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct() (+24 more)

### Community 37 - "normalize.py"
Cohesion: 0.18
Nodes (21): aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values(), _book_has_market_value(), _fill_missing_from_live(), _first() (+13 more)

### Community 38 - "project_modules"
Cohesion: 0.08
Nodes (23): fetch_public_rating(), _one(), project_concentration(), _drop_sold(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules() (+15 more)

### Community 39 - "plan.py"
Cohesion: 0.07
Nodes (34): capability_catalog_text(), field_prompt_table(), mentions_advice(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), _invalidate_plan_system_cache() (+26 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "run_daily.py"
Cohesion: 0.27
Nodes (4): notify_failure(), ingest_ready(), main(), run_daily()

### Community 42 - "article_quality.py"
Cohesion: 0.12
Nodes (19): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+11 more)

### Community 43 - "plan_enforce.py"
Cohesion: 0.05
Nodes (56): match_all_scheme_categories(), match_scheme_category(), _phrase_in(), _difference_brief(), asks_category_performance(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition() (+48 more)

### Community 44 - "test_portfolio_startup_cache.py"
Cohesion: 0.14
Nodes (21): bind_cached_portfolio(), ensure_tools_for_data_question(), _investor_args(), _merge_fund(), question_mentions_own_book(), clear_cache_for_tests(), seed_portfolio_cache_for_tests(), set_active_crn() (+13 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "screen_hints_from_question"
Cohesion: 0.08
Nodes (29): execute_wave(), _clean_stock_capture(), phrase_is_mutual_fund_scheme(), screen_hints_from_question(), stock_name_from_question(), test_crude_increase_compound_question_screens_negatively_affected_funds(), test_defence_fund_screen_uses_defense_category(), test_driver_exposure_screen_no_longer_needs_sector_picks_first() (+21 more)

### Community 47 - "portfolio_news_impact.py"
Cohesion: 0.09
Nodes (28): _clean_holding_tokens(), book_wide_sectors(), _display_name(), _has_named_stock(), news_calls_for_book(), _news_name(), _pct(), resolve_book_sector() (+20 more)

### Community 48 - "entity_retrieval.py"
Cohesion: 0.15
Nodes (25): EntityPack, evidence_from_clusters(), fetch_entity_pack(), fetch_fii_dii(), fetch_macro_packs(), work(), fetch_market_driver(), fetch_sector_index() (+17 more)

### Community 49 - "fund_scheme_match.py"
Cohesion: 0.17
Nodes (13): amc_token_in_question(), _category_phrases_in_question(), _constraint_in_scheme_name(), _distinctive_constraints(), question_amc_hints(), scheme_match_score(), _scheme_name_tokens(), _scheme_vocab_tokens() (+5 more)

### Community 50 - "app.py"
Cohesion: 0.10
Nodes (40): ask_memory(), ask_query_log(), ask_sources(), _attach_portfolio_to_ask(), backfill_page(), backfill_start(), backfill_status(), backfill_stop() (+32 more)

### Community 51 - "gold_service.py"
Cohesion: 0.13
Nodes (18): _fetch(), get_gold_snapshot(), gold_horizon_code(), gold_macro_series_row(), _load_payload(), _merged_series(), add(), _normalize_windows() (+10 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "investor_subject.py"
Cohesion: 0.05
Nodes (64): pick_best_matching_scheme(), resolve_fund_from_question(), apply_investor_category_fund_to_plan(), _category_slug_from_question(), enforce_catalog_fund_list_scope(), enforce_deictic_and_memory_primary_fund(), enforce_investor_holding_subject(), ensure_all_holdings_metrics_plan() (+56 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.11
Nodes (22): asks_fund_category_average(), build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), merge_fund_insight_metrics(), normalize_category_average_returns() (+14 more)

### Community 55 - "typing"
Cohesion: 0.13
Nodes (8): _events(), run_ask_engine(), stream_ask_engine(), run_insight_pipeline(), stream_insight_pipeline(), main(), test_ask_engine_delegates_to_insight_pipeline(), test_streaming_sse_order()

### Community 56 - "test_sector_leaderboard_run.py"
Cohesion: 0.10
Nodes (33): LlmJsonResult, LlmUsage, call(), DryRunHalt, _block(), build_user(), main(), _theme_problem() (+25 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "resolve_fund_for_query"
Cohesion: 0.15
Nodes (19): lookup_extracted_fund(), resolve_fund_for_query(), _resolved_scheme_for_portfolio_ask(), test_absl_and_ppfas_shorthand(), test_absl_conservative_hybrid_active_fof(), test_absl_gold_etf_is_the_etf_not_a_gold_fund_list(), test_absl_large_cap_is_not_frontline_or_the_trigger_plan(), test_absl_nifty_50_etf_not_momentum_200() (+11 more)

### Community 59 - "executor.py"
Cohesion: 0.04
Nodes (68): rating_for_request(), rating_needs_pillars(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _capability_cache_key(), _compare_cache_label(), _compare_payload_matches_funds() (+60 more)

### Community 60 - "node_compose"
Cohesion: 0.05
Nodes (61): asks_about_score_bands(), asks_fund_risk(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison() (+53 more)

### Community 61 - "test_insight_news_link.py"
Cohesion: 0.14
Nodes (19): NewsClaim, NewsRead, _same_sector(), SectorCall, _brief(), _compose(), _evidence(), _llm() (+11 more)

### Community 62 - "test_ai_insight_common_qdrant_access.py"
Cohesion: 0.21
Nodes (12): is_stale(), newest_scraped_at(), _freshness_warning(), _article(), FakeQdrant, _point(), test_freshness_stale_when_missing_or_old(), test_holding_without_names_raises() (+4 more)

### Community 63 - "re"
Cohesion: 0.09
Nodes (25): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_funds(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic() (+17 more)

### Community 64 - "pytest"
Cohesion: 0.14
Nodes (21): _add_usage(), _default_call(), format_articles_block(), generate_json(), _invoke_with_retry(), LlmSchemaError, LlmUnavailable, _run_bounded() (+13 more)

### Community 65 - "fund_universe_agent.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "twelve_data_brent.py"
Cohesion: 0.14
Nodes (22): _api_key(), BrentSyncResult, _call_time_series(), fetch_day(), fetch_days(), history_path(), main(), _merge_rows() (+14 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.14
Nodes (15): asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), memory_shows_investor_book(), _tokens(), unknown_fund_phrase() (+7 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "embed.py"
Cohesion: 0.15
Nodes (8): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, get_encoder(), _build_encoder(), main()

### Community 71 - "portfolio/cache.py"
Cohesion: 0.13
Nodes (19): _run_get_investor_portfolio(), _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), find_cached_holdings(), get_active_crn(), get_normalized_portfolio() (+11 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.16
Nodes (15): _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases(), _linked_articles_from_pool(), _news_stats_for_holding(), question_wants_holdings_performance(), should_fetch_holdings_market() (+7 more)

### Community 73 - "RatingScreenSpec"
Cohesion: 0.10
Nodes (21): _add_category_comparison(), _amc_matches(), asks_balanced_long_horizon_fund_menu(), balanced_portfolio_examples_spec(), _best_rated_row(), _cascade_labels_for_spec(), _execute_rating_list(), _install_suggestion_screen() (+13 more)

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "fields.py"
Cohesion: 0.10
Nodes (31): _asks_book(), bind_fields_to_tools(), _book_fields(), canonicalize_field(), fields_from_question(), _fund_fields(), _leave_tools_alone(), _legacy_facts() (+23 more)

### Community 77 - "sector_fund_ranking.py"
Cohesion: 0.08
Nodes (15): classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors(), is_passive_fund_name(), load_regular_growth_isins(), _pipeline_sector_targets(), _repo_path(), _sector_label_in_text() (+7 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.20
Nodes (14): extract_top_holdings(), _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file() (+6 more)

### Community 79 - "rupeestop_auth.py"
Cohesion: 0.14
Nodes (20): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+12 more)

### Community 80 - "Cluster"
Cohesion: 0.26
Nodes (14): Cluster, cluster_score(), rank_clusters(), Drivers, is_index_recap(), move_phrase(), move_size(), _names() (+6 more)

### Community 81 - "time"
Cohesion: 0.16
Nodes (22): hydrate_memory_from_prior_turns(), normalize_prior_turns(), append_chat_turn(), _fresh(), get_memory(), get_or_create(), reset_memory(), save_state() (+14 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.08
Nodes (57): _benchmark_lines_from_pack(), _age(), _allocation_bucket_rows(), _as_of(), _asks_portfolio_rs_ratings(), _book_line(), _category_amount_map(), _comparison_rows() (+49 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "scrape_bodies.py"
Cohesion: 0.13
Nodes (13): is_source_exhausted(), _entity_refs(), _log_scrape_record(), _scrape(), scrape_bodies(), clip_log_text(), finish_run_logger(), RunLogger (+5 more)

### Community 86 - "fii_dii_flow_narrative/prompt.py"
Cohesion: 0.19
Nodes (12): assemble_fii_body(), _clean_paragraph(), compact_flow_facts(), _legacy_paragraph(), normalize_fii_draft(), test_assemble_strips_markup_in_paragraph(), test_compact_flow_facts_excludes_gross_and_bars(), test_compact_flow_facts_includes_datasets() (+4 more)

### Community 87 - "sector_indices.py"
Cohesion: 0.09
Nodes (36): _bars(), catalog_path(), fetch_ohlc(), IndexSpec, load_catalog(), news_sectors_for_index(), OhlcBar, series_is_usable() (+28 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.13
Nodes (21): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_category_allocation_without_planner_tools_still_fetches_the_book() (+13 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 90 - "official.py"
Cohesion: 0.22
Nodes (11): fetch_cpi_record(), pick(), fetch_fii_dii(), fetch_gdp_record(), fetch_gsec(), fetch_gst(), fetch_iip_record(), fetch_official() (+3 more)

### Community 91 - "news_filter.py"
Cohesion: 0.27
Nodes (12): filter_usable_articles(), _is_low_quality_article(), merge_article_pool(), rank_and_pick_articles(), score_article(), _stock_terms(), _title_mentions_stock(), _vector_strength() (+4 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.05
Nodes (68): labels_name_the_same_scheme(), _add_category_comparison(), append_investor_portfolio_overview_tables(), _category_rows_from_investor(), _compare_brief_line(), _compare_cell(), _compare_header(), _complete_fund_row() (+60 more)

### Community 96 - "affected_sectors.py"
Cohesion: 0.24
Nodes (9): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+1 more)

### Community 97 - "NumericRecord"
Cohesion: 0.14
Nodes (19): fetch_ask_market_records(), fetch_gold_record(), get_ask_market_snapshot(), write_ask_market_snapshot(), FiiDiiSnapshot, NumericRecord, unavailable(), fetch_fii_dii_snapshot() (+11 more)

### Community 98 - "EvidencePack"
Cohesion: 0.16
Nodes (10): EvidencePack, test_evidence_pack_compact_includes_table_summaries(), test_expense_ratio_meaning_and_judgment_uses_composer(), test_render_drawback_includes_underperformers(), test_compact_strips_contribution_from_data_attribution(), test_sanitize_data_pack_moves_pp_to_internal(), test_allocation_with_book_data_still_calls_composer(), test_compose_always_uses_composer_for_largest_holding() (+2 more)

### Community 99 - "qdrant_access.py"
Cohesion: 0.17
Nodes (19): _as_dict(), _client(), _drop(), _entity_view(), EntityRowsResult, _explode(), fetch_entity_rows(), _filter() (+11 more)

### Community 100 - "sector_exposure_tables.py"
Cohesion: 0.11
Nodes (24): owned_holding_names(), _block_deictic_all_holdings_fanout(), _ensure_all_holdings_tool_order(), _ensure_metric_modules(), ensure_silver_news_only(), _holdings_breakdown_question(), validate_plan_tools(), _all_holdings_metric_spec() (+16 more)

### Community 102 - "portfolio/client.py"
Cohesion: 0.17
Nodes (13): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), InvalidCRN, PortfolioError, PortfolioNotConfigured, PortfolioUnavailable (+5 more)

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.11
Nodes (18): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_PIPELINE_DAILY (+10 more)

### Community 104 - "env"
Cohesion: 0.11
Nodes (18): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL (+10 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.18
Nodes (12): _rating_lead_for_pack(), asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score() (+4 more)

### Community 106 - "portfolio_news_impact.py"
Cohesion: 0.06
Nodes (41): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), _rule_sector_picks() (+33 more)

### Community 107 - "market_pulse.py"
Cohesion: 0.06
Nodes (46): _warmup_embeddings_background(), _run(), article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), AskPlan, EntityMention (+38 more)

### Community 108 - "_normalize_fund_text"
Cohesion: 0.15
Nodes (13): _attach_trailing_product(), _clean_fund_phrase(), collect_fund_phrase_candidates(), add(), _compose_amc_scheme_phrase(), _extend_amc_phrase_tail(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question() (+5 more)

### Community 109 - "fund_drawdown.py"
Cohesion: 0.13
Nodes (28): _add_drawdown_call(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), fetch_drawdown_periods(), fetch_trailing_drawdown(), investment_amount() (+20 more)

### Community 110 - "fund_match.py"
Cohesion: 0.13
Nodes (12): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), load_fund_embedding_cache(), _normalize_fund_text() (+4 more)

### Community 111 - "Settings"
Cohesion: 0.06
Nodes (34): resolve_allisin_holdings_path(), Publisher, SectorQuery, Settings, load_portfolio_universe(), _fund_stats_from_csv(), load_holdings_rows_from_xlsx(), multi_query_for() (+26 more)

### Community 112 - "explicit_fund_count"
Cohesion: 0.15
Nodes (10): _category_fund_name_spec(), fund_naming_clause(), _label_in(), _looks_like_fund_list(), _metal_fund_spec(), rating_screen_question(), _return_window(), _suggestion_spec() (+2 more)

### Community 113 - "fund_rating_categories.py"
Cohesion: 0.12
Nodes (18): categories_for(), CategoryMatch, _close(), explanation_brief(), _metal_category(), _metal_flags(), metal_scheme_categories(), _names_a_type() (+10 more)

### Community 114 - "insights.py"
Cohesion: 0.30
Nodes (10): build_insights(), _equity_pct(), Insight, insight_lines(), insights_for_brief(), _num(), _style_band(), _book() (+2 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "entity_candidates.py"
Cohesion: 0.26
Nodes (7): candidates_block(), entity_candidates(), _holding_candidates(), _sector_candidates(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

### Community 117 - "test_insight_interpret.py"
Cohesion: 0.24
Nodes (7): SectorFinding, _dedupe_parenthetical_cites(), test_dedupe_repeated_citations(), test_market_sector_lists_in_display_without_funds(), test_named_fund_why_uses_sector_drag_not_macro(), test_render_citations_strips_outlets(), test_structured_compose_orders_sub_asks_and_bold()

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "macro_news_cache.py"
Cohesion: 0.11
Nodes (23): _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read(), _search_macro_parameters() (+15 more)

### Community 121 - "stock_explain.py"
Cohesion: 0.26
Nodes (11): equity_week_llm_kwargs(), attach_stock_whys(), explain_one_block(), _fmt_movers_daily(), _fmt_nav_daily(), _fmt_stock_daily(), polish_why(), scrub_number_heavy_sentences() (+3 more)

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "relationships.py"
Cohesion: 0.42
Nodes (5): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships()

### Community 124 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 125 - "normalize_rs_label"
Cohesion: 0.07
Nodes (43): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), _apply_category_difference() (+35 more)

### Community 126 - "run-pipeline"
Cohesion: 0.29
Nodes (6): jobs, run-pipeline, name, on, runs-on, timeout-minutes

### Community 127 - "update.py"
Cohesion: 0.14
Nodes (19): drop_old_turns(), compare_payload_matches_funds(), add_gist(), empty_frame(), empty_state(), expire_stale_entities(), push_fund(), stack_entry() (+11 more)

### Community 128 - "common/store.py"
Cohesion: 0.10
Nodes (37): bundle_exists(), _check_id(), _dump(), exists(), _file(), _is_date(), latest(), list_dates() (+29 more)

### Community 129 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

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
Cohesion: 0.10
Nodes (24): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+16 more)

### Community 135 - "test_fund_drawdown.py"
Cohesion: 0.14
Nodes (28): asks_category_drawdown(), drawdown_words(), ensure_drawdown_tools(), _named_standard_periods(), periods_for_question(), _question_needs_drawdown(), requested_fund_facts(), _plan() (+20 more)

### Community 136 - "_fund_performance_digest"
Cohesion: 0.38
Nodes (4): _fund_performance_digest(), prefers_planner_over_slot(), test_fund_news_does_not_force_planner(), test_performance_digest_from_snapshot()

### Community 137 - "inputs"
Cohesion: 0.40
Nodes (5): default, description, required, type, holdings_limit

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "asks_computed_illustration"
Cohesion: 0.43
Nodes (3): asks_computed_illustration(), test_fire_sip_plan_is_a_computed_illustration(), test_sip_definition_is_not_a_calculator()

### Community 141 - "price.py"
Cohesion: 0.17
Nodes (6): history_closes(), latest_quote(), _consecutive_down_days(), DayBar, get_price_snapshot(), test_consecutive_down_days()

### Community 142 - "test_news_only_answer.py"
Cohesion: 0.17
Nodes (10): _news_subject(), _run_get_macro_news(), clean_news_insight(), complete_sentences(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words() (+2 more)

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

### Community 146 - "node_compose"
Cohesion: 0.08
Nodes (24): repair_investor_insight_prose(), asked_slots(), facts_only_compose_allowed(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), strip_grounding_holes() (+16 more)

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

### Community 159 - "threading"
Cohesion: 0.04
Nodes (43): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), _backoff(), _consent_jar(), _fetch_http_get() (+35 more)

### Community 163 - "test_sector_leaderboard_score.py"
Cohesion: 0.08
Nodes (36): sector_label(), compose_headline(), _degraded_body(), _placeholder_sector(), llm_schema(), SectorScore, build_pulse_drivers(), _driver_row() (+28 more)

### Community 169 - "nse_fii_dii.py"
Cohesion: 0.18
Nodes (12): current_artifacts(), log_external(), FlowLeg, _bucket(), _httpx_json(), _impit_json(), _leg(), _log_external() (+4 more)

### Community 170 - "GraphState"
Cohesion: 0.09
Nodes (28): _attach_conversation(), build_result(), _catalog_fanout_fund_names(), _conversation_id(), _ensure_portfolio_for_fund_news(), GraphState, _insight_headline_narrative(), _load_planner_memory() (+20 more)

### Community 174 - "fund_search.py"
Cohesion: 0.08
Nodes (24): _clean_company_name(), detail_has_live_facts(), _entry_matches_amc(), _entry_matches_query_scheme(), fetch_fund_managers_for_query(), _fund_context_for_managers(), _fund_text(), get_fund_benchmark() (+16 more)

### Community 178 - "graph.py"
Cohesion: 0.14
Nodes (17): execute_capability(), RequestTelemetry, _answer_stream_chunks(), Node, _plan_fetches_manager_roster(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta() (+9 more)

### Community 180 - "news.py"
Cohesion: 0.17
Nodes (14): _fetch_rows(), get_top_news(), news_window(), NewsBundle, _published_in_window(), _rows_to_articles(), sort_key(), fetch_stock_news() (+6 more)

### Community 181 - "test_metal_fund_rating.py"
Cohesion: 0.14
Nodes (12): ensure_quality_fund_list(), _payload(), _rating(), test_category_rating_request_uses_admin_header(), test_gold_etf_only_stays_on_the_etf_category(), test_gold_fund_list_uses_only_gold_scheme_categories(), test_gold_list_spreads_etf_and_fund_of_funds(), fetch() (+4 more)

### Community 182 - "portfolio_insights.js"
Cohesion: 0.42
Nodes (9): api(), card(), chipHtml(), esc(), headers(), loadReady(), renderCompose(), renderReady() (+1 more)

### Community 183 - "fund_catalog.py"
Cohesion: 0.12
Nodes (23): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+15 more)

### Community 184 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 185 - "prompts.py"
Cohesion: 0.29
Nodes (4): build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 186 - "nav_service.py"
Cohesion: 0.10
Nodes (17): get_silver_snapshot(), _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history() (+9 more)

### Community 187 - "._ensure_loaded"
Cohesion: 0.21
Nodes (3): FundIndex, _infer_category_and_type(), _sync_amc_prefix_from_catalog()

### Community 188 - "narrative.py"
Cohesion: 0.12
Nodes (20): assemble_body(), beats_from_draft(), compact_facts(), _compact_news_map(), enrich_flow_gross(), narrative_limits(), narrative_limits_text(), _num() (+12 more)

### Community 190 - "security_master.py"
Cohesion: 0.35
Nodes (8): _load_index(), load_master_index(), lookup_instrument(), lookup_master(), normalize_name(), _pick_best_master(), resolve_yf_ticker(), test_master_lookup()

### Community 191 - "build_derived_views"
Cohesion: 0.24
Nodes (9): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_derived_views_split_assets_and_categories() (+1 more)

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 193 - "infer_fund_news_layers"
Cohesion: 0.31
Nodes (6): infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only(), test_overview_news_is_holdings_and_sectors()

### Community 195 - "test_rating_screen_uses_focus_question_not_full_compare_question"
Cohesion: 0.40
Nodes (3): test_rating_screen_uses_focus_question_not_full_compare_question(), test_rating_screen_uses_forced_category_spec(), fake_fetch()

### Community 197 - "brief.py"
Cohesion: 0.09
Nodes (36): asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief(), _detect_direction(), _detect_funds(), _detect_sector(), _heuristic_brief() (+28 more)

### Community 198 - "283041/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 203 - "fund_brief.py"
Cohesion: 0.07
Nodes (48): build_portfolio_scope(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest() (+40 more)

### Community 206 - "test_ai_insight.py"
Cohesion: 0.18
Nodes (6): digest_filter(), _holding_mentioned(), matches_entity(), contains_phrase(), test_digest_filter_uses_stricter_scores(), test_sector_exclude_drops_nbfc_from_banks()

### Community 208 - "Envelope"
Cohesion: 0.05
Nodes (88): build(), compose(), _cards(), main(), _build(), _user(), Signal, news_map_block() (+80 more)

### Community 209 - "57e233/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 211 - "test_return_windows.py"
Cohesion: 0.08
Nodes (28): _arg_text(), _capabilities_for_planner(), _clamp(), validate_capability_args(), _age_phrase(), align_plan_windows(), normalize_window_code(), _parse_date() (+20 more)

### Community 212 - "c72b25/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 213 - "a45664/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 214 - "compare_evidence.py"
Cohesion: 0.24
Nodes (8): maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names(), _screen_wants_pair_compare(), test_maybe_run_compare_retries_after_failed_compare(), test_resolve_pair_anchor_plus_screen_pick(), test_resolve_pair_two_screen_rankings()

### Community 217 - "7859f0/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 218 - "test_greeting.py"
Cohesion: 0.13
Nodes (15): _store_turn_memory(), greeting_reply(), identity_reply(), _mirror_greeting(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view() (+7 more)

### Community 219 - "contracts.py"
Cohesion: 0.02
Nodes (121): question_mentions_fund_scheme(), rating_list_plan(), rating_concept_plan(), ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls() (+113 more)

### Community 222 - "layer_tools.py"
Cohesion: 0.10
Nodes (26): nifty50_ticker(), aggregate_sectors_from_holdings(), normalize_sector_row(), _run_get_market_snapshot(), _run_get_portfolio_data(), _price_holdings(), benchmark_return_for_scheme(), _cache_path() (+18 more)

### Community 224 - "Cluster"
Cohesion: 0.16
Nodes (18): _adapter(), cluster_rows(), _collapse(), _dedupe(), find(), union(), _group_of(), _keys() (+10 more)

### Community 225 - "insights.js"
Cohesion: 0.22
Nodes (18): api(), arrow(), bars(), card(), chart(), diverging(), esc(), headers() (+10 more)

### Community 226 - "holding_insights.js"
Cohesion: 0.35
Nodes (14): api(), clearError(), escapeHtml(), headers(), instrumentMeta(), loadSaved(), logLink(), poll() (+6 more)

### Community 227 - "insight_log.js"
Cohesion: 0.70
Nodes (4): api(), esc(), headers(), load()

### Community 229 - "news_pipeline/config.py"
Cohesion: 0.06
Nodes (20): _to_article(), EntityScore, StoredArticle, is_qdrant_cloud(), qdrant_host(), qdrant_summary(), validate_qdrant_settings(), merge_stored_article() (+12 more)

### Community 230 - "test_admin_headers_use_token_from_login"
Cohesion: 0.10
Nodes (4): _jwt(), test_admin_headers_use_token_from_login(), test_expired_jwt_logs_in_once_and_reuses_fresh_token(), test_failed_login_keeps_previous_token()

### Community 232 - "data_pack.py"
Cohesion: 0.32
Nodes (4): build_data_pack(), build(), _compact(), test_data_pack_groups_by_fund_and_hides_internal_fields()

### Community 233 - "router.py"
Cohesion: 0.11
Nodes (8): holding_insights_page(), holding_insights_stock_log_page(), portfolio_insights_page(), equity_fund_week_page(), create_equity_fund_week_router(), page(), run_endpoint(), EquityFundWeekRequest

### Community 237 - "holding_insights/llm.py"
Cohesion: 0.13
Nodes (23): llm_allow_fallback(), _as_paragraph(), call_holding_llm(), _call(), _headline_week_matches(), _normalize_response(), parse_insight_lines(), _pct_in_text() (+15 more)

### Community 238 - "app.js"
Cohesion: 0.57
Nodes (6): esc(), fundCard(), paragraphSection(), pctFmt(), structuredInsight(), summaryBlock()

### Community 240 - "run_insights_daily.sh"
Cohesion: 0.50
Nodes (4): note(), PYTHONPATH, PYTHONUNBUFFERED, run_insights_daily.sh script

### Community 241 - "sys"
Cohesion: 0.14
Nodes (11): check_yfinance(), load_master_index(), lookup_master(), main(), normalize_name(), pick_best_master(), resolve_yf_ticker(), compare() (+3 more)

### Community 252 - "test_ai_insight_mospi.py"
Cohesion: 0.25
Nodes (10): _client(), _sse(), test_400_is_not_retried(), test_gdp_yoy_uses_prior_fiscal_year(), handler(), test_retries_500_then_reads_cache(), handler(), test_snapshot_keeps_other_entities_when_one_fails() (+2 more)

### Community 253 - "test_composer_table_summaries.py"
Cohesion: 0.27
Nodes (7): filter_display_tables_by_decision(), parse_tables_append_directive(), strip_empty_bold_sections(), test_filter_display_tables_by_decision(), test_parse_tables_append_directive(), test_strip_empty_bold_sections(), test_summarize_tables_for_composer_extracts_mix_and_holdings()

### Community 254 - "test_fund_rating_screen.py"
Cohesion: 0.08
Nodes (47): asks_taxonomy(), match_all_fund_types(), _keep_asked_return(), parse_rating_screen(), _return_direction(), run_rating_list(), _payload(), _rating() (+39 more)

### Community 255 - "eval_planner.py"
Cohesion: 0.24
Nodes (4): check(), main(), run_case(), _Usage

### Community 257 - "EvidenceArticle"
Cohesion: 0.07
Nodes (27): bellwether_holdings(), merge_evidence(), _qdrant_holding_names(), _resolve_bellwether(), rank(), enforce_prompt_budget(), EvidenceArticle, _float() (+19 more)

### Community 260 - "holding_insights_stock_log.js"
Cohesion: 0.60
Nodes (5): api(), escapeHtml(), headers(), load(), render()

### Community 261 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 268 - "load_config"
Cohesion: 0.05
Nodes (60): _all_dates(), _bundle_is_live(), create_router(), daily(), dates(), generate(), health(), holding_insights_job_latest() (+52 more)

### Community 270 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

### Community 273 - "MospiError"
Cohesion: 0.15
Nodes (7): _cache_dir(), MospiClient, MospiError, _payload(), _sse_json(), _unhandled_exception_handler(), GraphUnavailable

### Community 276 - "test_equity_fund_week.py"
Cohesion: 0.23
Nodes (10): nav_change_1w_settled(), nav_daily_week_settled(), settled_nav_records(), test_clamp_why_keeps_full_sentences(), test_compose_structured_narrative(), test_equity_week_defaults_to_haiku(), test_nav_daily_week_from_records(), test_select_drivers_sign() (+2 more)

### Community 277 - "load_equity_holdings"
Cohesion: 0.33
Nodes (4): _is_equity(), load_equity_holdings(), fund_type_for_category(), test_equity_filter_from_workspace()

### Community 278 - "fund_type_name_spec"
Cohesion: 0.06
Nodes (33): _fund_type_in_name_clause(), fund_type_name_spec(), asks_random_fund_compare(), question_is_standalone_macro(), random_fund_count(), _compare_fund_count(), enforce_user_authorized_funds_only(), fund_authorized_for_question() (+25 more)

### Community 279 - "compose_llm.py"
Cohesion: 0.19
Nodes (21): scrub_refusal_prose(), split_sentences(), _clean_summary_sentence(), compose_fund_narrative(), _compose_user_message(), _ensure_fund_summary(), _facts_payload(), _fund_display_name() (+13 more)

### Community 281 - "yf_week.py"
Cohesion: 0.44
Nodes (4): _bars_before_today(), _history_settled_bars(), stock_change_1w_settled(), stock_daily_week_settled()

## Knowledge Gaps
- **26 isolated node(s):** `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT` (+21 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2049 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **58 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `plan_enforce.py`, `ToolCall`, `test_fund_drawdown.py`, `display_table_policy.py`, `test_news_only_answer.py`, `node_compose`, `QueryLogger`, `macro_data.py`, `fund_type_name_spec`, `investor_drawback.py`, `task_exec.py`, `fund_display.py`, `project_modules`, `plan.py`, `GraphState`, `plan_enforce.py`, `test_portfolio_startup_cache.py`, `portfolio_news_impact.py`, `graph.py`, `gold_service.py`, `investor_subject.py`, `test_metal_fund_rating.py`, `node_compose`, `fields.py`, `time`, `fact_answer.py`, `test_return_windows.py`, `compare_evidence.py`, `test_portfolio_allocation.py`, `contracts.py`, `evidence_pack.py`, `EvidencePack`, `sector_exposure_tables.py`, `test_composer_table_summaries.py`, `normalize_rs_label`, `test_fund_rating_screen.py`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `ExecutionPlan` (e.g. with `news_calls_for_book()` and `sector_book()`) actually correct?**
  _`ExecutionPlan` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN` to the rest of the system?**
  _26 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.07474226804123711 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ToolCall` to `execute_capability`, `plan_enforce.py`, `test_fund_drawdown.py`, `display_table_policy.py`, `test_news_only_answer.py`, `macro_data.py`, `fund_type_name_spec`, `investor_drawback.py`, `ExecutionPlan`, `task_exec.py`, `project_modules`, `plan.py`, `GraphState`, `plan_enforce.py`, `test_portfolio_startup_cache.py`, `screen_hints_from_question`, `portfolio_news_impact.py`, `graph.py`, `gold_service.py`, `test_metal_fund_rating.py`, `investor_subject.py`, `executor.py`, `node_compose`, `RatingScreenSpec`, `fields.py`, `time`, `test_return_windows.py`, `compare_evidence.py`, `test_portfolio_allocation.py`, `contracts.py`, `evidence_pack.py`, `sector_exposure_tables.py`, `portfolio/client.py`, `fund_drawdown.py`, `normalize_rs_label`, `test_fund_rating_screen.py`, `update.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ToolCall` (e.g. with `news_calls_for_book()` and `_apply_planner_request()`) actually correct?**
  _`ToolCall` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `execute_capability` be split into smaller, more focused modules?**
  _Cohesion score 0.13043478260869565 - nodes in this community are weakly interconnected._