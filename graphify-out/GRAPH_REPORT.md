# Graph Report - db_design_with_qdrant_locally  (2026-11-18)

## Corpus Check
- 717 files · ~1,103,123 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 31 file(s) not represented in the graph (top: .example 6, .log 5, (none) 4)

## Summary
- 7248 nodes · 23455 edges · 263 communities (199 shown, 64 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 752 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `62f19442`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging
- time
- fund_rating_screen.py
- interpret.py
- build_evidence_pack
- market_driver_digest/run.py
- affected_sectors.py
- format_inr
- test_two_wave_pipeline.py
- Settings
- sector_leaderboard/run.py
- memory/state.py
- display_table_policy.py
- compute.py
- v2_scoring.py
- tools.py
- embed_query
- test_conversation_memory.py
- QueryLogger
- news_reader.py
- macro_data.py
- runner.py
- api.py
- main.py
- tool_runners.py
- scrape_bodies.py
- fund_display.py
- gather.py
- pack_sanitize.py
- enforce_planner_catalog_plan
- _normalize_fund_text
- trends.py
- sources/google_news.py
- task_exec.py
- llm_client.py
- sector_query_for_label
- fund_search.py
- normalize.py
- test_portfolio_layer.py
- plan.py
- env
- workspace.py
- article_quality.py
- ToolCall
- dataclasses
- env
- time_ist.py
- book_news_map.py
- logging.py
- fund_catalog.py
- app.py
- gold_service.py
- env
- investor_subject.py
- fund_rupeestop_metrics.py
- ToolCall
- test_sector_leaderboard_run.py
- scrape-worker/package.json
- resolve_fund_for_query
- executor.py
- node_compose
- graph.py
- market_pulse.py
- re
- test_portfolio_intents.py
- fund_universe_agent.py
- batch.ts
- screen_hints_from_question
- insight/guardrails.py
- http-fetch.ts
- embed.py
- portfolio/cache.py
- holdings_market.py
- httpx
- with
- insight/portfolio_scope.py
- sector_fund_ranking.py
- stock_fund_ranking.py
- rupeestop_auth.py
- main.py
- memory/store.py
- fact_answer.py
- holding_attribution.py
- scrape-worker/src/index.ts
- RunLogger
- fact_slots.py
- sector_indices.py
- test_portfolio_allocation.py
- normalize_answer_markdown
- lib/portfolio_scope.py
- test_metal_fund_rating.py
- env
- steps
- evidence_pack.py
- validate_capability_args
- official.py
- fields.py
- nav_service.py
- NumericRecord
- portfolio/client.py
- run-daily-pipeline.sh
- env
- enrich_manager_payload
- portfolio_news_impact.py
- retrieve_scoped_news
- test_fact_answer.py
- layer_tools.py
- fund_match.py
- ExecutionPlan
- typing
- news_digest.py
- insights.py
- vitest
- NewsStore
- fund_rating_categories.py
- compilerOptions
- compilerOptions
- macro_news_cache.py
- test_ai_insight_mospi.py
- backfill
- stitch_display_tables_into_answer
- sector_alignment.py
- normalize_rs_label
- run-pipeline
- test_call_json_llm.py
- query_log.py
- test_pick_shown_fund.py
- worker/src/index.ts
- steps
- steps
- with
- concurrent_futures
- fund_drawdown.py
- assemble_fund_overview_answer
- inputs
- with
- inputs
- fund_type_name_spec
- macro_impact_map.py
- test_fund_drawdown.py
- run-backfill.sh
- qdrant
- plan_system_prompt
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
- time
- install.sh
- memory/evidence.py
- install-backfill.sh
- install-daily-cron.sh
- server-bootstrap.sh
- sync_repo_branch.sh
- nse_fii_dii.py
- graph.py
- diagnose_lightsail_site.sh
- entity_candidates.py
- strip_missing_data_caveats
- EntityFunnel
- project_modules
- test_fund_rating_screen.py
- portfolio_insights.js
- enrich_rankings_with_nav
- update.py
- insight_links.py
- test_daily_cron_settings.py
- build_top100_holdings.py
- test_ai_insight_quality.py
- pack_trim.py
- build_derived_views
- metals_spot_tables.py
- infer_fund_news_layers
- sources/universe.py
- planner_catalog_knowledge.py
- QuestionBrief
- 283041/manifest.json
- fund_brief.py
- test_ai_insight.py
- Envelope
- 57e233/manifest.json
- DisplayTablePolicy
- c72b25/manifest.json
- a45664/manifest.json
- test_composer_table_summaries.py
- 7859f0/manifest.json
- market_scope_entities
- re
- prompts.py
- test_news_only_answer.py
- _fund_performance_digest
- MospiError
- insights.js
- holding_insights.js
- insight_log.js
- fix-daily-ingest.sh
- normalize_user_facing_text
- test_expired_jwt_logs_in_once_and_reuses_fresh_token
- test_greeting.py
- test_admin_headers_use_token_from_login
- sector_alignment.py
- measured_facts_block
- holding_insights/llm.py
- _unhandled_exception_handler
- _detail_for_fund_tool
- run_insights_daily.sh
- test_snapshot_uses_payload_returns_and_history_only_for_gaps
- install-insights-cron.sh
- test_stocks_service.py
- test_insight_graph.py
- holding_insights_stock_log.js
- strip_news_roundup

## God Nodes (most connected - your core abstractions)
1. `ExecutionPlan` - 607 edges
2. `ToolCall` - 367 edges
3. `get_settings()` - 147 edges
4. `apply_planner_post_hooks()` - 123 edges
5. `AnswerMode` - 108 edges
6. `load_config()` - 104 edges
7. `node_compose()` - 102 edges
8. `QueryLogger` - 100 edges
9. `Settings` - 95 edges
10. `QuestionBrief` - 88 edges

## Surprising Connections (you probably didn't know these)
- `_call()` --calls--> `call_json_llm()`  [EXTRACTED]
  ai_insight/holding_insights/llm.py → news_rag/llm_client.py
- `_check_plan()` --uses--> `ExecutionPlan`  [INFERRED]
  scripts/eval_basic_queries.py → news_rag/insight/contracts.py
- `_live_plan()` --uses--> `ExecutionPlan`  [INFERRED]
  scripts/eval_basic_queries.py → news_rag/insight/contracts.py
- `_modules()` --uses--> `ExecutionPlan`  [INFERRED]
  scripts/eval_basic_queries.py → news_rag/insight/contracts.py
- `test_market_sector_lists_in_display_without_funds()` --uses--> `SubAsk`  [INFERRED]
  tests/test_insight_interpret.py → news_rag/insight/brief.py

## Import Cycles
- 2-file cycle: `ai_insight/common/entity_retrieval.py -> ai_insight/common/retrieval_plan.py -> ai_insight/common/entity_retrieval.py`

## Communities (263 total, 64 thin omitted)

### Community 0 - "logging"
Cohesion: 0.08
Nodes (47): get_encoder(), get_entity_funnel(), fetch_window_fields(), build_graph(), _absorb_into_candidate(), dedupe_and_alias(), _dedupe_candidates(), _find_story_match() (+39 more)

### Community 1 - "time"
Cohesion: 0.10
Nodes (13): CapabilityCache, _Entry, get_capability_cache(), _compare_cache_label(), _compare_payload_matches_funds(), execute_capability(), test_compare_conversation_cache_does_not_reuse_different_pair(), fake_compare() (+5 more)

### Community 2 - "fund_rating_screen.py"
Cohesion: 0.07
Nodes (43): _add_category_comparison(), _amc_matches(), _amc_outside_label(), _amc_token(), _apply_category_difference(), asks_balanced_long_horizon_fund_menu(), balanced_portfolio_examples_spec(), _best_label() (+35 more)

### Community 3 - "interpret.py"
Cohesion: 0.07
Nodes (69): asks_sector_lists(), QuestionBrief, _success_criteria(), Findings, FundFinding, SectorFinding, mentions_publication_date(), strip_media_attribution() (+61 more)

### Community 4 - "build_evidence_pack"
Cohesion: 0.06
Nodes (41): EvidencePack, EvidenceRow, build_evidence_pack(), extra_part_brief(), _holding_label(), _holding_weight_pct(), _portfolio_markdown(), _portfolio_sections_from_plan() (+33 more)

### Community 5 - "market_driver_digest/run.py"
Cohesion: 0.04
Nodes (75): CommonConfig, editorial_context(), market_numbers(), fmt_inr_crore(), ordinal(), cumulative(), FlowDay, history_path() (+67 more)

### Community 6 - "affected_sectors.py"
Cohesion: 0.14
Nodes (14): accepted_sectors(), _article_char_limit(), _article_lines(), build_picker_prompt(), _flatten_sector_buckets(), pick_affected_companies(), pick_affected_sectors(), picker_direction_line() (+6 more)

### Community 7 - "format_inr"
Cohesion: 0.23
Nodes (10): format_indian_amount(), format_indian_integer_digits(), format_inr(), format_rs(), normalize_rupee_commas_in_text(), repl(), test_format_indian_amount_lakh(), test_format_inr_symbol() (+2 more)

### Community 8 - "test_two_wave_pipeline.py"
Cohesion: 0.06
Nodes (38): strip_grounding_holes(), collect_evidence_calendar_dates(), add_article(), cores_for_float(), cores_in_text(), derived_cores(), finalize_text_fields(), format_user_calendar_date() (+30 more)

### Community 9 - "Settings"
Cohesion: 0.07
Nodes (35): _subprocess(), _checkpoint_path(), _load_checkpoint(), main(), _save_checkpoint(), Publisher, repo_root(), SectorQuery (+27 more)

### Community 10 - "sector_leaderboard/run.py"
Cohesion: 0.05
Nodes (83): sector_label(), sector_names_for_pulse(), scrub_refusal_prose(), split_sentences(), SectorFetch, _block(), build_user(), _abs_scores() (+75 more)

### Community 11 - "memory/state.py"
Cohesion: 0.25
Nodes (10): empty_frame(), empty_state(), expire_stale_entities(), push_fund(), stack_entry(), _subject(), test_repeated_fund_mention_refreshes_entity_ttl(), test_catalog_subjects_expire_investor_subjects_kept() (+2 more)

### Community 12 - "display_table_policy.py"
Cohesion: 0.07
Nodes (31): primary_metal_in_question(), question_is_bullion_metal_price_question(), question_mentions_gold_etf_or_fund(), apply_bullion_metal_scope(), _drop_sparse_in_table(), drop_sparse_table_columns(), _limit_tables(), _named_fund_overview() (+23 more)

### Community 13 - "compute.py"
Cohesion: 0.07
Nodes (48): _alignment(), _benchmark(), _build_evidence_text(), _claims_for_findings(), compute_findings(), _drags_for(), _driver_row_tilt(), _fmt_date() (+40 more)

### Community 14 - "v2_scoring.py"
Cohesion: 0.26
Nodes (10): _blob(), load_cases_v2(), score_answer(), score_brief(), score_case(), score_findings(), score_ledger(), main() (+2 more)

### Community 15 - "tools.py"
Cohesion: 0.07
Nodes (53): retrieve_bullion_macro_news(), retrieve_bullion_metal_news(), run_driver_affected_funds_adapter(), DataNeed, _active_sector_equity(), _articles_for_affected_question(), _as_date(), asks_equity_funds() (+45 more)

### Community 16 - "embed_query"
Cohesion: 0.06
Nodes (22): _pack_row(), _retrieve_bullion_for_entities(), _trim_snippet(), embed_query(), _body(), grouped_news(), NewsTarget, search_targets() (+14 more)

### Community 17 - "test_conversation_memory.py"
Cohesion: 0.21
Nodes (19): build_result(), clear_conversation(), note_cache(), get_memory(), reset_memory(), sources_for(), turn_record(), _fund_plan() (+11 more)

### Community 18 - "QueryLogger"
Cohesion: 0.07
Nodes (13): _events(), run_ask_engine(), stream_ask_engine(), run_graph_pipeline(), run_insight_pipeline(), stream_insight_pipeline(), clip_log_text(), _kv() (+5 more)

### Community 19 - "news_reader.py"
Cohesion: 0.08
Nodes (45): _article_context_for_interpret(), _clean_market_claims(), _format_claim_bullet(), _allowed_sector_names(), _article_char_limit(), _body(), _build_user_prompt(), _canonical_sector() (+37 more)

### Community 20 - "macro_data.py"
Cohesion: 0.21
Nodes (22): PortfolioComposeRequest, BondYieldResult, _client(), _codes(), walk(), CPIRecord, fetch_bond_yields(), fetch_cpi() (+14 more)

### Community 21 - "runner.py"
Cohesion: 0.09
Nodes (39): _append(), _clock(), RunLog, _write(), _bound_llm(), bundle_cli_main(), cli_main(), _failed() (+31 more)

### Community 22 - "api.py"
Cohesion: 0.04
Nodes (84): _all_dates(), _bundle_is_live(), create_router(), daily(), dates(), generate(), health(), holding_insights_job_latest() (+76 more)

### Community 23 - "main.py"
Cohesion: 0.08
Nodes (28): Settings, _merge_publisher_error_reasons(), write_day_report(), _atomic_write(), day_failure_slices_for_run(), ensure_loaded(), _failures_dir(), flush() (+20 more)

### Community 24 - "tool_runners.py"
Cohesion: 0.10
Nodes (45): build_default_registry(), _compare_return_windows(), _driver_without_sector(), _enrich_compare_brief(), _fail(), _fund_compare_brief(), _has(), _has_sector() (+37 more)

### Community 25 - "scrape_bodies.py"
Cohesion: 0.07
Nodes (26): _backoff(), _consent_jar(), _fetch_http_get(), fetch_publisher_url(), _handle_google_response(), make_session(), post_url(), _proxy() (+18 more)

### Community 26 - "fund_display.py"
Cohesion: 0.11
Nodes (26): _as_float(), _assess_table_quality(), _cell(), _comparison_pair_ok(), _composition_table_markdown(), _fmt_inr(), _fmt_pct(), _fmt_pp() (+18 more)

### Community 27 - "gather.py"
Cohesion: 0.07
Nodes (47): _article_key(), _base_ctx(), _close_dependencies(), _collect_articles(), _extract_funds_from_result(), gather_evidence(), GatherContext, LedgerEntry (+39 more)

### Community 28 - "pack_sanitize.py"
Cohesion: 0.10
Nodes (24): attach_drawback_digest(), _fmt_inr(), _pretty_category(), render_portfolio_drawback_answer(), question_asks_all_schemes_in_answer(), _display_holding_row(), _enrich_investor_computed_fields(), _internal_contribution_row() (+16 more)

### Community 29 - "enforce_planner_catalog_plan"
Cohesion: 0.08
Nodes (43): owned_holding_names(), _bind_fund_list(), enforce_planner_catalog_plan(), _ensure_get_fund_data_for_holdings(), _ensure_portfolio_data_for_compare(), _ensure_portfolio_data_for_holdings(), ensure_whole_book_catalog_scope(), _funds_from_entities() (+35 more)

### Community 30 - "_normalize_fund_text"
Cohesion: 0.10
Nodes (11): _clean_fund_phrase(), add(), _expand_query_token(), _extend_amc_phrase_tail(), FundIndex, _infer_category_and_type(), _is_bullion_phrase_not_scheme(), _is_plausible_scheme_phrase() (+3 more)

### Community 31 - "trends.py"
Cohesion: 0.09
Nodes (19): detect_signals(), _surge(), notify_failure(), DayPoint, entity_daily_series(), price_trend(), price_trend_from_closes(), PriceTrend (+11 more)

### Community 32 - "sources/google_news.py"
Cohesion: 0.12
Nodes (19): fetch_entity_items(), _fetch_query_items(), _match_publisher(), _parse_rss(), _resolve_publisher_url(), fetch_macro_items(), is_macro_match(), macro_fetch_entities() (+11 more)

### Community 33 - "task_exec.py"
Cohesion: 0.13
Nodes (29): bind_subjects(), _book_total_line(), _canon_fact(), _category_in_planner_text(), _cell(), _compare_subject_kind(), coverage_line(), _fact_label() (+21 more)

### Community 34 - "llm_client.py"
Cohesion: 0.08
Nodes (49): get_settings(), make_plan(), _slot_fallback(), anthropic_cache_control(), anthropic_system_blocks(), _blocks_to_parts(), _call_anthropic(), _call_deepseek() (+41 more)

### Community 35 - "sector_query_for_label"
Cohesion: 0.11
Nodes (22): _default_phrase(), sector_headline_phrase(), append_personal_tail(), _display_fund_name(), _fetch_fund_short_name(), format_fund_tail(), fund_isins_from_row(), _headline_ends_with_your() (+14 more)

### Community 36 - "fund_search.py"
Cohesion: 0.09
Nodes (27): headline_rating(), aggregate_sectors_from_holdings(), build_holding_overlap(), _clean_company_name(), detail_has_live_facts(), _entry_matches_amc(), _entry_matches_query_scheme(), extract_top_holdings() (+19 more)

### Community 37 - "normalize.py"
Cohesion: 0.18
Nodes (21): aggregate_term_gains(), _allocation_block(), _allocation_raw_from_workspace(), _allocation_raw_has_payload(), _apply_holding_values(), _book_has_market_value(), _fill_missing_from_live(), _first() (+13 more)

### Community 38 - "test_portfolio_layer.py"
Cohesion: 0.11
Nodes (13): _drop_sold(), normalized_doc(), test_allocation_drops_dust_and_matches_book_aum(), test_book_schemes_are_the_open_holdings(), test_current_value_and_nonzero_xirr(), test_holdings_table_uses_exact_value(), test_normalize_allocation_from_live_books_total(), test_portfolio_concentration_report_format() (+5 more)

### Community 39 - "plan.py"
Cohesion: 0.09
Nodes (26): explanation_brief(), canonicalize_field(), field_prompt_table(), _apply_planner_request(), _compare_sides(), _example_part(), _horizon_years(), _invalidate_plan_system_cache() (+18 more)

### Community 40 - "env"
Cohesion: 0.05
Nodes (39): APP_TOKEN, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, EMBEDDING_CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, PYTHONPATH (+31 more)

### Community 41 - "workspace.py"
Cohesion: 0.19
Nodes (7): apply_fresh_start(), _clear_run_json_summaries(), clear_scrape_workspace(), remove_scrape_artifacts(), remove_scrape_artifacts_many(), url_artifact_stem(), workspace_dir()

### Community 42 - "article_quality.py"
Cohesion: 0.22
Nodes (12): _article_blob(), _body_len(), claim_matches_label(), filter_quality_articles(), _has_movers(), _impact(), _quality_score(), relevance_terms() (+4 more)

### Community 43 - "ToolCall"
Cohesion: 0.03
Nodes (97): match_all_scheme_categories(), match_scheme_category(), asks_ideal_portfolio_shape(), _anchor_rating_for_category(), _apply_same_category_pair_screen_plan(), asks_category_composition(), asks_cross_category_compare(), asks_fund_holdings_followup() (+89 more)

### Community 44 - "dataclasses"
Cohesion: 0.03
Nodes (79): _write(), latest_quote(), atomic_write_json(), holding_data_dir(), _daily_path(), load_daily(), save_daily(), _articles() (+71 more)

### Community 45 - "env"
Cohesion: 0.05
Nodes (38): FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PYTHONPATH, QDRANT_API_KEY (+30 more)

### Community 46 - "time_ist.py"
Cohesion: 0.12
Nodes (26): fmt_ist(), _resolve_end(), rolling_window(), session_window(), to_ist(), week_window(), _closed_dates(), is_trading_day() (+18 more)

### Community 47 - "book_news_map.py"
Cohesion: 0.21
Nodes (14): _clean_holding_tokens(), book_wide_sectors(), _display_name(), _has_named_stock(), news_calls_for_book(), _news_name(), _pct(), resolve_book_sector() (+6 more)

### Community 48 - "logging.py"
Cohesion: 0.20
Nodes (8): _env_secrets(), prune_logs(), _redact(), _redact_text(), _rmtree(), RunArtifacts, _usage(), test_artifacts_redact_and_prune()

### Community 49 - "fund_catalog.py"
Cohesion: 0.08
Nodes (36): all_amc_bare_names(), amc_headers_for_hint(), amc_hint_token_set(), amc_planner_lines(), AmcCatalogIndex, bare_amc_name(), build_amc_catalog(), add_prefix() (+28 more)

### Community 50 - "app.py"
Cohesion: 0.06
Nodes (51): holding_insights_page(), holding_insights_stock_log_page(), portfolio_insights_page(), ask(), ask_memory(), ask_query_log(), ask_sources(), ask_stream() (+43 more)

### Community 51 - "gold_service.py"
Cohesion: 0.14
Nodes (18): _fetch(), get_gold_snapshot(), get_silver_snapshot(), gold_horizon_code(), gold_macro_series_row(), _load_payload(), _merged_series(), add() (+10 more)

### Community 52 - "env"
Cohesion: 0.06
Nodes (33): ALLISIN_SECTORS_HOLDINGS_JSON, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL, NEWS_CORPUS_MODE, PORTFOLIO_JSON (+25 more)

### Community 53 - "investor_subject.py"
Cohesion: 0.04
Nodes (107): plan_wants_single_scheme_risk(), reroute_single_fund_risk_plan(), pick_best_matching_scheme(), _bound_fund_name(), _compare_sides_resolvable(), _known_names_in_text(), question_refers_deictic_fund_safe(), single_fund_for_deictic() (+99 more)

### Community 54 - "fund_rupeestop_metrics.py"
Cohesion: 0.10
Nodes (20): build_comparison_periods(), expense_ratio_for_question(), _f(), fetch_vs_benchmark(), fund_returns_from_detail(), normalize_category_average_returns(), normalize_vs_benchmark_payload(), _optional_number() (+12 more)

### Community 55 - "ToolCall"
Cohesion: 0.03
Nodes (98): _followup_modules(), apply_concept_example_to_plan(), asks_concept_with_catalog_example(), asks_wants_named_example(), build_concept_example_plan(), concept_brief_for_question(), AnswerMode, QueryClass (+90 more)

### Community 56 - "test_sector_leaderboard_run.py"
Cohesion: 0.08
Nodes (46): _add_usage(), _default_call(), format_articles_block(), generate_json(), _invoke_with_retry(), LlmJsonResult, LlmSchemaError, LlmUnavailable (+38 more)

### Community 57 - "scrape-worker/package.json"
Cohesion: 0.08
Nodes (27): devDependencies, @cloudflare/workers-types@^5.20261019.1, typescript@^5.6.3, vitest@^3.2.4, wrangler@^4.151.0, @cloudflare/workers-types, typescript, wrangler (+19 more)

### Community 58 - "resolve_fund_for_query"
Cohesion: 0.07
Nodes (34): _detect_funds(), _attach_trailing_product(), collect_fund_phrase_candidates(), _compose_amc_scheme_phrase(), _extract_amc_scheme_phrase(), extract_fund_phrase_from_question(), extract_top_sectors(), is_macro_metals_question() (+26 more)

### Community 59 - "executor.py"
Cohesion: 0.05
Nodes (49): rating_for_request(), rating_needs_pillars(), merge_fund_insight_metrics(), _attach_rs_rating_to_screen_rows(), _bullion_articles(), _bullion_topics(), _capability_cache_key(), _conversation_id() (+41 more)

### Community 60 - "node_compose"
Cohesion: 0.05
Nodes (55): asks_about_score_bands(), asks_hidden_rating(), asks_pillar_mark(), asks_pillar_structure(), asks_private_system(), asks_rating_concept(), asks_risk_trend_comparison(), asks_score_only() (+47 more)

### Community 61 - "graph.py"
Cohesion: 0.12
Nodes (17): LLMUsageRecord, PhaseRecord, RequestTelemetry, ToolRecord, _answer_stream_chunks(), stream_graph_pipeline(), event_answer_completed(), event_answer_delta() (+9 more)

### Community 62 - "market_pulse.py"
Cohesion: 0.08
Nodes (32): _lifespan(), _warmup_embeddings_background(), _run(), AskPlan, EntityMention, _int_list(), PlannedTool, embed_query() (+24 more)

### Community 63 - "re"
Cohesion: 0.08
Nodes (27): asks_financial_news(), asks_macro_explanation(), _detect_drivers(), _detect_sectors(), _detect_stocks(), DomainScan, enrich_news_search_topic(), extract_news_topics() (+19 more)

### Community 64 - "test_portfolio_intents.py"
Cohesion: 0.15
Nodes (18): render_portfolio_fact(), apply_portfolio_intent(), data_need_for(), _keep_book_news(), modules_for(), normalize_portfolio_intent(), portfolio_intent_from_question(), shape_for() (+10 more)

### Community 65 - "fund_universe_agent.py"
Cohesion: 0.09
Nodes (12): FundEntry, FundUniverseAgent, FundUniverseCatalog, _enrich(), get_fund_universe_catalog(), match_fund_category(), test_agent_answer_elss_question(), test_agent_answer_large_cap_question() (+4 more)

### Community 66 - "batch.ts"
Cohesion: 0.15
Nodes (22): bumpPublisher(), emptyRunSummary(), failedSourceFromErrorRow(), logScrapeEvent(), publisherKey(), recordOutcome(), ScrapeBatchResult, scrapeItems() (+14 more)

### Community 67 - "screen_hints_from_question"
Cohesion: 0.09
Nodes (28): execute_wave(), get_sector_fund_ranking_index(), phrase_looks_like_sector_reference(), screen_hints_from_question(), test_crude_increase_compound_question_screens_negatively_affected_funds(), test_defence_fund_screen_uses_defense_category(), test_driver_exposure_screen_no_longer_needs_sector_picks_first(), test_fof_fund_screen_returns_fof_schemes() (+20 more)

### Community 68 - "insight/guardrails.py"
Cohesion: 0.12
Nodes (16): _sector_candidates(), asks_advice_only(), asks_internals(), _close_to_known(), guard_reply(), looks_like_gibberish(), memory_shows_investor_book(), mentions_advice() (+8 more)

### Community 69 - "http-fetch.ts"
Cohesion: 0.20
Nodes (17): ScraperConfig, buildErrorRecord(), describeHttpStatus(), fetchHtmlWithPolicy(), FetchOk, hostFromUrl(), sanitizeExcerpt(), SleepFn (+9 more)

### Community 70 - "embed.py"
Cohesion: 0.16
Nodes (7): model_snapshot_exists(), prepare_embedding_cache(), configure_huggingface_token(), huggingface_model_kwargs(), Encoder, _build_encoder(), main()

### Community 71 - "portfolio/cache.py"
Cohesion: 0.14
Nodes (19): _run_get_investor_portfolio(), _BreakerState, _CacheEntry, crn_log_id(), _fetch_and_store(), find_cached_holdings(), get_active_crn(), get_normalized_portfolio() (+11 more)

### Community 72 - "holdings_market.py"
Cohesion: 0.10
Nodes (19): format_holdings_stock_context(), format_single_stock_context(), get_stock_profile(), resolve_stock_ticker(), _article_mentions_holding(), build_holdings_market_snapshots(), fetch_dedicated_holding_news(), _holding_match_aliases() (+11 more)

### Community 73 - "httpx"
Cohesion: 0.27
Nodes (3): main(), main(), main()

### Community 74 - "with"
Cohesion: 0.08
Nodes (23): default, description, required, type, runs-on, steps, timeout-minutes, branch (+15 more)

### Community 75 - "insight/portfolio_scope.py"
Cohesion: 0.07
Nodes (45): plan_wants_portfolio_drawback(), plan_wants_pure_concentration(), plan_targets_single_fund_measured_return(), question_asks_category_book_share(), question_asks_category_money(), question_asks_holding_metric_and_glossary(), bind_cached_portfolio(), _catalog_fund_holdings_question() (+37 more)

### Community 77 - "sector_fund_ranking.py"
Cohesion: 0.06
Nodes (21): _article_blob(), _matches(), _names_on_article(), _norm(), trace_relationships(), classify_sector_fund_purity(), _damerau(), _fuzzy_pipeline_sectors() (+13 more)

### Community 78 - "stock_fund_ranking.py"
Cohesion: 0.22
Nodes (13): _aggregated_map(), default_holder_candidates(), _funds_from_holdings_file(), funds_holding_stock(), holder_candidates_for_stock(), holdings_archive_available(), _holdings_file(), _initials() (+5 more)

### Community 79 - "rupeestop_auth.py"
Cohesion: 0.11
Nodes (22): ensure_fresh_rupeestop_bearer(), _cfg(), _current(), _env_files_for_token(), _fetch_admin_login_token(), _jwt_exp_epoch(), _login_credentials(), _login_url() (+14 more)

### Community 80 - "main.py"
Cohesion: 0.11
Nodes (19): _bucket(), _entity_names(), summarize_errors(), write_error_summary(), reset_run_buffers(), main(), _write_summary(), covered_calendar_days() (+11 more)

### Community 81 - "memory/store.py"
Cohesion: 0.16
Nodes (13): _load_planner_memory(), _store_turn_memory(), drain_cache_events(), hydrate_memory_from_prior_turns(), normalize_prior_turns(), append_chat_turn(), _fresh(), get_or_create() (+5 more)

### Community 82 - "fact_answer.py"
Cohesion: 0.13
Nodes (35): pending_rating_line(), _age(), _allocation_bucket_rows(), _as_of(), _book_line(), _category_amount_map(), _comparison_rows(), _composition_line() (+27 more)

### Community 83 - "holding_attribution.py"
Cohesion: 0.22
Nodes (14): arithmetic_ok(), attribute_rows(), company_news_line(), contribution_pct(), _format_holding_move_line(), _holding_move_stats(), _join_holding_moves(), _name_tokens() (+6 more)

### Community 84 - "scrape-worker/src/index.ts"
Cohesion: 0.30
Nodes (18): buildErrorsFile(), buildScrapedFile(), checkAuth(), fetch(), handleRun(), json(), newRunId(), parseBatchSize() (+10 more)

### Community 85 - "RunLogger"
Cohesion: 0.21
Nodes (7): finish_run_logger(), RunLogger, start_run_logger(), load_macro_entities(), load_universe(), main(), _run_test()

### Community 86 - "fact_slots.py"
Cohesion: 0.12
Nodes (15): asked_slots(), missing_slots(), render_asked_facts(), _slot_label(), _slot_value(), slots_from_plan(), ensure_fund_concentration_plan(), plan_wants_fund_concentration() (+7 more)

### Community 87 - "sector_indices.py"
Cohesion: 0.12
Nodes (22): week_index_movers(), _bars(), catalog_path(), fetch_ohlc(), IndexSpec, load_catalog(), news_sectors_for_index(), OhlcBar (+14 more)

### Community 88 - "test_portfolio_allocation.py"
Cohesion: 0.14
Nodes (19): allocate(), Allocation, AllocationCategory, bucket_for_years(), _categories(), _split(), test_balanced_equity_by_bucket(), test_debt_more_on_ten_years_keeps_equity_floor() (+11 more)

### Community 89 - "normalize_answer_markdown"
Cohesion: 0.31
Nodes (7): _balance_bold(), _is_rule(), _is_table_line(), normalize_answer_markdown(), _split_cells(), test_pads_short_row(), test_separator_and_bold_and_blank_line()

### Community 90 - "lib/portfolio_scope.py"
Cohesion: 0.13
Nodes (21): build_portfolio_scope(), FundRef, _holding_equity_allowed(), instrument_to_qdrant_names(), is_blocked_sector(), load_aggregated_equity_keys(), load_allisin_doc(), load_manifest() (+13 more)

### Community 91 - "test_metal_fund_rating.py"
Cohesion: 0.16
Nodes (9): fetch_category_ratings(), _payload(), _rating(), test_category_rating_request_uses_admin_header(), test_gold_etf_only_stays_on_the_etf_category(), test_gold_fund_list_uses_only_gold_scheme_categories(), test_gold_list_spreads_etf_and_fund_of_funds(), fetch() (+1 more)

### Community 92 - "env"
Cohesion: 0.11
Nodes (18): env, BACKFILL_END, BACKFILL_PAUSE_SEC, BACKFILL_START, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, HOLDINGS_LIMIT, JEV_API_KEY (+10 more)

### Community 94 - "steps"
Cohesion: 0.12
Nodes (16): jobs, verify, name, on, pull_request, push, paths, branches (+8 more)

### Community 95 - "evidence_pack.py"
Cohesion: 0.06
Nodes (54): fetch_public_rating(), _add_category_comparison(), append_investor_portfolio_overview_tables(), _attach_rs_ratings_to_screen(), _one(), _benchmark_lines_from_pack(), _category_rows_from_investor(), _compare_brief_line() (+46 more)

### Community 96 - "validate_capability_args"
Cohesion: 0.12
Nodes (15): _arg_text(), _capabilities_for_planner(), capability_catalog_text(), _clamp(), validate_capability_args(), test_validate_capability_args_keeps_compare_pair(), _history(), test_a_narrow_cache_does_not_stand_in_for_a_wider_request() (+7 more)

### Community 97 - "official.py"
Cohesion: 0.13
Nodes (25): write_ask_market_snapshot(), FiiDiiSnapshot, NumericRecord, unavailable(), write_snapshot(), fetch_fii_dii_snapshot(), fetch_cpi_record(), pick() (+17 more)

### Community 98 - "fields.py"
Cohesion: 0.10
Nodes (28): _asks_book(), bind_fields_to_tools(), _book_fields(), field_need(), FieldNeed, fields_from_question(), _find_term(), _fund_fields() (+20 more)

### Community 99 - "nav_service.py"
Cohesion: 0.15
Nodes (16): _cache_path(), _calculate_window_stats(), _ensure_cache_dir(), fetch_raw_nav_history(), format_nav_context_for_rag(), fund_return_series(), get_fund_nav_history(), monthly_returns_from_records() (+8 more)

### Community 100 - "NumericRecord"
Cohesion: 0.23
Nodes (6): fetch_ask_market_records(), fetch_gold_record(), get_ask_market_snapshot(), test_fetch_ask_market_records_includes_extras(), test_fetch_gold_record_ok(), test_get_ask_market_snapshot_shape()

### Community 102 - "portfolio/client.py"
Cohesion: 0.14
Nodes (17): fetch_workspace_raw(), _load_json_file(), _resolve_fixture_path(), _workspace_url(), InvalidCRN, PortfolioError, PortfolioNotConfigured, PortfolioUnavailable (+9 more)

### Community 103 - "run-daily-pipeline.sh"
Cohesion: 0.11
Nodes (18): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, MACRO_NEWS_ENABLED, NEWS_CORPUS_MODE, NEWS_PIPELINE_DAILY (+10 more)

### Community 104 - "env"
Cohesion: 0.11
Nodes (18): FETCH_WORKERS, FRESH_START_CLEAR_QDRANT, FRESH_START_EACH_RUN, GOOGLE_NEWS_WHEN, HOLDINGS_LIMIT, JEV_API_KEY, JEV_BASE_URL, JEV_MODEL (+10 more)

### Community 105 - "enrich_manager_payload"
Cohesion: 0.17
Nodes (13): _rating_lead_for_pack(), asks_manager_roster(), build_roster_note(), _earliest_on_scheme_dates(), enrich_manager_payload(), infer_manager_roster_focus(), _parse_iso_date(), test_asks_manager_roster_not_pillar_score() (+5 more)

### Community 106 - "portfolio_news_impact.py"
Cohesion: 0.19
Nodes (12): _articles_from_pack(), build_portfolio_news_impact_dossier(), _infer_direction(), _linkage(), _merge_sector_picks(), _portfolio_sector_weights(), _rule_sector_picks(), _tag_holding_news() (+4 more)

### Community 107 - "retrieve_scoped_news"
Cohesion: 0.07
Nodes (32): article_dedupe_key(), collect_bundle_articles(), merge_article(), sources_from_articles(), corpus_entity_names(), _fetch_holding_news(), _fetch_macro_news(), _fetch_sector_news() (+24 more)

### Community 108 - "test_fact_answer.py"
Cohesion: 0.17
Nodes (19): _asks_portfolio_rs_ratings(), field_answer_needs_composer(), _investor_holdings_rows(), is_pure_field_answer(), render_benchmark_comparison_table(), render_fact_answer(), render_investor_rs_ratings_table(), _plan() (+11 more)

### Community 109 - "layer_tools.py"
Cohesion: 0.09
Nodes (29): nifty50_ticker(), normalize_sector_row(), _run_get_market_snapshot(), _price_holdings(), benchmark_return_for_scheme(), _cache_path(), index_return_for_sector(), nifty50_reference_returns() (+21 more)

### Community 110 - "fund_match.py"
Cohesion: 0.13
Nodes (11): _cap_structure_adjustment(), _catalog_name_extra_token_penalty(), catalog_name_for_match(), _distinctive_token_adjustment(), embedding_best_match(), fold_fund_spelling(), labels_name_the_same_scheme(), load_fund_embedding_cache() (+3 more)

### Community 111 - "ExecutionPlan"
Cohesion: 0.04
Nodes (64): ensure_quality_fund_list(), ensure_rating_screen(), _install_suggestion_screen(), _keep_followup_plan(), maybe_run_compare_funds_for_parties(), resolve_compare_fund_pair(), _screen_anchor_name(), _screen_ranking_names() (+56 more)

### Community 112 - "typing"
Cohesion: 0.05
Nodes (82): _adapter(), Cluster, cluster_rows(), cluster_score(), _collapse(), _dedupe(), find(), union() (+74 more)

### Community 113 - "news_digest.py"
Cohesion: 0.25
Nodes (9): _best_excerpt(), _clean_body(), _dedupe_key(), digest_articles(), executive_sector_summary(), _extract_numbers(), test_digest_articles_uses_snippet_and_impact(), test_digest_strips_boilerplate_and_dedupes() (+1 more)

### Community 114 - "insights.py"
Cohesion: 0.30
Nodes (10): build_insights(), _equity_pct(), Insight, insight_lines(), insights_for_brief(), _num(), _style_band(), _book() (+2 more)

### Community 115 - "vitest"
Cohesion: 0.18
Nodes (4): DomainPacer, NowFn, SleepFn, vitest

### Community 116 - "NewsStore"
Cohesion: 0.09
Nodes (8): _to_article(), EntityScore, StoredArticle, merge_stored_article(), payload_to_stored(), _datetime_range(), NewsStore, point_id_for_url()

### Community 117 - "fund_rating_categories.py"
Cohesion: 0.07
Nodes (31): categories_for(), CategoryMatch, _close(), fund_type_for_category(), _metal_category(), _metal_flags(), metal_scheme_categories(), _names_a_type() (+23 more)

### Community 118 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 119 - "compilerOptions"
Cohesion: 0.18
Nodes (10): compilerOptions, lib, module, moduleResolution, noEmit, skipLibCheck, strict, target (+2 more)

### Community 120 - "macro_news_cache.py"
Cohesion: 0.10
Nodes (23): _run_get_macro_news(), _article_text(), _cache_has_article_text(), compute_macro_news(), _fresh(), get_macro_news(), _log(), _read() (+15 more)

### Community 121 - "test_ai_insight_mospi.py"
Cohesion: 0.25
Nodes (10): _client(), _sse(), test_400_is_not_retried(), test_gdp_yoy_uses_prior_fiscal_year(), handler(), test_retries_500_then_reads_cache(), handler(), test_snapshot_keeps_other_entities_when_one_fails() (+2 more)

### Community 122 - "backfill"
Cohesion: 0.20
Nodes (9): runs-on, timeout-minutes, jobs, backfill, name, on, permissions, actions (+1 more)

### Community 123 - "stitch_display_tables_into_answer"
Cohesion: 0.17
Nodes (19): build_fund_display_tables(), format_display_tables_markdown(), stitch_display_tables_into_answer(), _compose_hints(), _comparison_pack(), test_a_question_does_not_keep_unasked_windows(), test_caveats_about_missing_comparison_are_removed(), test_comparison_keeps_only_benchmark_when_category_missing() (+11 more)

### Community 124 - "sector_alignment.py"
Cohesion: 0.17
Nodes (13): clear_macro_impact_cache(), analyze_sector_block(), canonical_sector_for_holding(), holding_return_pct(), holdings_in_sector(), index_return_pct(), return_sign(), run_sector_holding_alignment() (+5 more)

### Community 125 - "normalize_rs_label"
Cohesion: 0.10
Nodes (27): is_higher_rated_than(), is_lower_tier_than(), label_tiers_from(), label_tiers_up_to(), normalize_rs_label(), tier_rank(), _alternate_row_excluded(), asks_rating_list() (+19 more)

### Community 126 - "run-pipeline"
Cohesion: 0.29
Nodes (6): jobs, run-pipeline, name, on, runs-on, timeout-minutes

### Community 127 - "test_call_json_llm.py"
Cohesion: 0.40
Nodes (9): _client(), _gemini_response(), _settings(), test_agent_keeps_truncated_tools_without_repair(), test_composer_keeps_truncated_answer_without_a_second_call(), test_gemini_request_includes_response_schema(), test_judge_truncated_json_does_not_repair(), test_salvage_closes_a_cut_off_composer_object() (+1 more)

### Community 128 - "query_log.py"
Cohesion: 0.15
Nodes (11): ParsedQuery, attach_query_log_meta(), find_query_log_file(), new_fund_brief_logger(), new_query_logger(), query_log_page_href(), read_query_log(), main() (+3 more)

### Community 129 - "test_pick_shown_fund.py"
Cohesion: 0.14
Nodes (14): fund_picked_from_prior_answer(), funds_from_shown_list(), _list_count(), _list_question(), question_picks_one_shown_fund(), question_refers_to_shown_list(), _scheme_names_in_prose(), shown_list_names() (+6 more)

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

### Community 134 - "concurrent_futures"
Cohesion: 0.07
Nodes (28): _canonical_industry(), clean_display_name(), clean_industry(), fetch_fund(), _has_markers(), load_isins(), normalize_holding(), normalize_sector() (+20 more)

### Community 135 - "fund_drawdown.py"
Cohesion: 0.13
Nodes (30): _add_drawdown_call(), attach_screen_drawdown(), average_peer_drawdown(), collapse_episodes(), compare_drawdown_rows(), fetch_drawdown_periods(), fetch_trailing_drawdown(), investment_amount() (+22 more)

### Community 136 - "assemble_fund_overview_answer"
Cohesion: 0.12
Nodes (10): assemble_fund_overview_answer(), _drop_repeated_fund_heading(), strip_composer_display_sections(), strip_empty_table_pointers(), strip_markdown_tables_from_prose(), _strip_overview_prose_block(), test_overview_drops_repeated_title_and_nav_paragraph(), test_overview_puts_rating_and_tables_before_news() (+2 more)

### Community 137 - "inputs"
Cohesion: 0.40
Nodes (5): default, description, required, type, holdings_limit

### Community 138 - "with"
Cohesion: 0.29
Nodes (7): with, cache, if-no-files-found, key, name, path, python-version

### Community 139 - "inputs"
Cohesion: 0.29
Nodes (7): sectors_limit, workflow_dispatch, default, description, required, type, inputs

### Community 140 - "fund_type_name_spec"
Cohesion: 0.09
Nodes (21): _fund_type_in_name_clause(), fund_type_name_spec(), question_is_standalone_macro(), asks_computed_illustration(), apply_pure_concept_plan(), question_is_pure_general_concept(), ensure_catalog_tools_for_fund_news(), apply_standalone_macro_scope() (+13 more)

### Community 141 - "macro_impact_map.py"
Cohesion: 0.24
Nodes (10): canonical_direction_for_driver(), _document(), _driver_row(), list_macro_drivers(), macro_impact_entry(), macro_series_for_driver(), normalize_direction(), run_macro_sector_impact() (+2 more)

### Community 142 - "test_fund_drawdown.py"
Cohesion: 0.16
Nodes (24): asks_category_drawdown(), ensure_drawdown_tools(), is_drawdown_definition(), _named_standard_periods(), periods_for_question(), _plan(), test_category_drawdown_asks_for_the_peer_average(), test_comparison_keeps_compare_funds_and_drops_ten_year() (+16 more)

### Community 143 - "run-backfill.sh"
Cohesion: 0.33
Nodes (5): FRESH_START_EACH_RUN, NEWS_CORPUS_MODE, PYTHONPATH, RETENTION_DAYS, run-backfill.sh script

### Community 144 - "qdrant"
Cohesion: 0.33
Nodes (5): image, ports, volumes, services, qdrant

### Community 146 - "plan_system_prompt"
Cohesion: 0.23
Nodes (8): plan_system_prompt(), build_anthropic_messages_body(), shared_system_prefix(), test_composer_and_prefix_carry_the_product_rules(), test_rupee_grouping_lives_in_the_shared_prefix(), _body(), test_planner_and_composer_share_the_first_system_block(), test_tools_stay_available_when_there_is_no_shared_prefix()

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

### Community 159 - "time"
Cohesion: 0.07
Nodes (22): _authors(), _clean(), extract_article(), _meta(), _meta_fallback(), fetch_url(), article_id_from_url(), _batchexecute() (+14 more)

### Community 163 - "memory/evidence.py"
Cohesion: 0.24
Nodes (9): _take_conversation_slice(), recall_slice(), recall_wider_portfolio(), remember_slice(), slice_key(), slice_slot(), stored_fund_slices(), test_period_change_does_not_reuse_the_other_window() (+1 more)

### Community 169 - "nse_fii_dii.py"
Cohesion: 0.18
Nodes (12): current_artifacts(), log_external(), FlowLeg, _bucket(), _httpx_json(), _impit_json(), _leg(), _log_external() (+4 more)

### Community 170 - "graph.py"
Cohesion: 0.03
Nodes (69): drawdown_words(), asks_fund_risk(), ensure_affected_fund_screen(), evaluate_wave2(), _extract_returns_from_results(), _extract_top_entities_from_results(), market_affected_fund_calls(), fact_values_already_stated() (+61 more)

### Community 174 - "entity_candidates.py"
Cohesion: 0.30
Nodes (6): candidates_block(), entity_candidates(), _holding_candidates(), test_no_candidates_for_plain_text(), test_quant_question_includes_amc_catalog_note(), test_sector_and_holding_candidates()

### Community 178 - "strip_missing_data_caveats"
Cohesion: 0.18
Nodes (8): strip_missing_data_caveats(), test_a_rating_pick_does_not_apologise_for_returns_or_pillars(), test_strip_removes_risk_trend_apology(), test_a_holding_outside_the_top_five_still_gets_weight_and_sector(), test_a_top_five_apology_is_removed(), test_each_holding_keeps_the_article_text_not_only_one_headline(), test_overview_fund_facts_are_a_short_table(), test_a_gap_apology_is_removed_and_a_real_point_stays()

### Community 180 - "project_modules"
Cohesion: 0.12
Nodes (10): fetch_top_holdings(), project_concentration(), row_fund_isins(), match_scheme_filter(), _attach_ratings(), _pick_row(), project_modules(), _scheme_match() (+2 more)

### Community 181 - "test_fund_rating_screen.py"
Cohesion: 0.08
Nodes (48): asks_taxonomy(), match_all_fund_types(), fund_naming_clause(), parse_rating_screen(), rating_screen_question(), _return_direction(), run_rating_list(), _payload() (+40 more)

### Community 182 - "portfolio_insights.js"
Cohesion: 0.42
Nodes (9): api(), card(), chipHtml(), esc(), headers(), loadReady(), renderCompose(), renderReady() (+1 more)

### Community 183 - "enrich_rankings_with_nav"
Cohesion: 0.23
Nodes (6): enrich_rankings_with_nav(), _fetch_nav_one(), _performance_sort_key(), _sort_ranked_by_performance(), test_enrich_rankings_with_nav_any(), test_enrich_rankings_with_nav_positive()

### Community 184 - "update.py"
Cohesion: 0.21
Nodes (11): drop_old_turns(), compare_payload_matches_funds(), subjects_from_fund_names(), touch_fund_entity_ttl(), add_gist(), apply_planner_refs(), _changed(), commit_turn() (+3 more)

### Community 185 - "insight_links.py"
Cohesion: 0.31
Nodes (8): normalize_holding_row(), build_insight_links(), _fact(), _key(), _match(), _pct(), _portfolio_rows(), _wider_holdings()

### Community 187 - "build_top100_holdings.py"
Cohesion: 0.38
Nodes (7): check_yfinance(), load_master_index(), lookup_master(), main(), normalize_name(), pick_best_master(), resolve_yf_ticker()

### Community 188 - "test_ai_insight_quality.py"
Cohesion: 0.05
Nodes (49): bellwether_holdings(), evidence_from_clusters(), merge_evidence(), _qdrant_holding_names(), slug(), enforce_prompt_budget(), EvidenceArticle, _float() (+41 more)

### Community 191 - "build_derived_views"
Cohesion: 0.26
Nodes (8): asset_bucket(), _aum(), balance_verdicts(), balance_verdicts_for_payload(), build_derived_views(), _pct(), _split_from_allocation(), test_equity_only_and_concentration_verdicts()

### Community 192 - "metals_spot_tables.py"
Cohesion: 0.26
Nodes (7): _fmt_inr_whole(), _metals_spot_from_results(), render_gold_returns_table(), _short_date(), strip_gold_window_table(), test_render_gold_returns_table_shows_then_and_now(), test_strip_gold_window_table()

### Community 193 - "infer_fund_news_layers"
Cohesion: 0.31
Nodes (6): infer_fund_news_layers(), test_asks_fund_related_news(), test_infer_all_layers_when_unspecified(), test_infer_macro_only(), test_infer_sector_only(), test_overview_news_is_holdings_and_sectors()

### Community 194 - "sources/universe.py"
Cohesion: 0.09
Nodes (27): _resolve_bellwether(), rank(), resolve_allisin_holdings_path(), load_portfolio_universe(), _fund_stats_from_csv(), load_holdings_rows_from_xlsx(), multi_query_for(), _strip_legal_suffix() (+19 more)

### Community 195 - "planner_catalog_knowledge.py"
Cohesion: 0.33
Nodes (5): _catalog_block(), planner_catalog_knowledge(), _read(), _repo_root(), _scheme_categories_block()

### Community 197 - "QuestionBrief"
Cohesion: 0.06
Nodes (39): analyst_should_run(), asks_market_briefing(), asks_random_fund_compare(), asks_share_price(), asks_weak_sector(), _brief_system(), build_question_brief(), _detect_direction() (+31 more)

### Community 198 - "283041/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

### Community 203 - "fund_brief.py"
Cohesion: 0.11
Nodes (27): Settings, _article_entities(), build_events(), cluster_articles(), _cluster_entities(), compose_fund_insight(), _day_key(), _exposure_for_holding() (+19 more)

### Community 206 - "test_ai_insight.py"
Cohesion: 0.18
Nodes (6): digest_filter(), _holding_mentioned(), matches_entity(), contains_phrase(), test_digest_filter_uses_stricter_scores(), test_sector_exclude_drops_nbfc_from_banks()

### Community 208 - "Envelope"
Cohesion: 0.04
Nodes (86): build(), compose(), _cards(), main(), _build(), _user(), Signal, news_map_block() (+78 more)

### Community 209 - "57e233/manifest.json"
Cohesion: 0.25
Nodes (7): dry_run, insight_id, job_id, live, run_dir, run_id, trading_date

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

### Community 218 - "market_scope_entities"
Cohesion: 0.32
Nodes (3): market_query_for_topic(), market_scope_entities(), pulse_theme_entities()

### Community 219 - "re"
Cohesion: 0.04
Nodes (68): question_mentions_fund_scheme(), _difference_brief(), _looks_like_fund_list(), _metal_fund_categories(), _metal_fund_spec(), _question_names_amc_scheme(), rating_list_plan(), _suggestion_spec() (+60 more)

### Community 221 - "prompts.py"
Cohesion: 0.29
Nodes (4): build_interpret_hybrid_prompt(), build_judge_prompt(), build_named_fund_composer_prompt(), build_news_reader_prompt()

### Community 222 - "test_news_only_answer.py"
Cohesion: 0.18
Nodes (10): _news_subject(), clean_news_insight(), complete_sentences(), is_article_only_news(), news_insight_articles(), strip_publisher(), _subject_words(), test_news_about_hdfc_bank_is_not_a_market_pulse() (+2 more)

### Community 223 - "_fund_performance_digest"
Cohesion: 0.38
Nodes (4): _fund_performance_digest(), prefers_planner_over_slot(), test_fund_news_does_not_force_planner(), test_performance_digest_from_snapshot()

### Community 224 - "MospiError"
Cohesion: 0.23
Nodes (5): _cache_dir(), MospiClient, MospiError, _payload(), _sse_json()

### Community 225 - "insights.js"
Cohesion: 0.22
Nodes (18): api(), arrow(), bars(), card(), chart(), diverging(), esc(), headers() (+10 more)

### Community 226 - "holding_insights.js"
Cohesion: 0.35
Nodes (14): api(), clearError(), escapeHtml(), headers(), instrumentMeta(), loadSaved(), logLink(), poll() (+6 more)

### Community 227 - "insight_log.js"
Cohesion: 0.70
Nodes (4): api(), esc(), headers(), load()

### Community 229 - "normalize_user_facing_text"
Cohesion: 0.33
Nodes (4): ensure_markdown_table_spacing(), normalize_user_facing_text(), test_normalize_inserts_blank_line_before_markdown_table(), test_normalize_na_to_hyphen()

### Community 231 - "test_greeting.py"
Cohesion: 0.16
Nodes (13): greeting_reply(), identity_reply(), _mirror_greeting(), chat_history_view(), _chat_turn_rows(), format_chat_history_block(), format_chat_history_from_view(), memory_json_tokens() (+5 more)

### Community 233 - "sector_alignment.py"
Cohesion: 0.20
Nodes (11): benchmark_entry(), clear_sector_index_cache(), _document(), sector_index_entry(), sector_yfinance_ticker(), _clear_index_cache(), test_by_sector_keys_match_sector_queries_exactly(), test_every_sector_has_verified_ticker_field() (+3 more)

### Community 237 - "holding_insights/llm.py"
Cohesion: 0.13
Nodes (23): llm_allow_fallback(), _as_paragraph(), call_holding_llm(), _call(), _headline_week_matches(), _normalize_response(), parse_insight_lines(), _pct_in_text() (+15 more)

### Community 240 - "run_insights_daily.sh"
Cohesion: 0.50
Nodes (4): note(), PYTHONPATH, PYTHONUNBUFFERED, run_insights_daily.sh script

### Community 259 - "test_insight_graph.py"
Cohesion: 0.17
Nodes (6): build_data_pack(), build(), _compact(), plan_to_brief(), tools_to_facets(), test_a_nav_lookup_plans_no_news_facets()

### Community 260 - "holding_insights_stock_log.js"
Cohesion: 0.60
Nodes (5): api(), escapeHtml(), headers(), load(), render()

### Community 264 - "strip_news_roundup"
Cohesion: 0.25
Nodes (7): append_news_section(), _insert_before_disclaimer(), render_news_section(), _strip_heading_sections(), strip_news_roundup(), test_portfolio_tables_and_news_section(), test_examples_heading_is_removed()

## Knowledge Gaps
- **26 isolated node(s):** `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN`, `GOOGLE_NEWS_WHEN`, `HOLDINGS_LIMIT` (+21 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 2002 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **64 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ExecutionPlan` connect `ExecutionPlan` to `test_pick_shown_fund.py`, `fund_rating_screen.py`, `test_insight_graph.py`, `build_evidence_pack`, `test_two_wave_pipeline.py`, `display_table_policy.py`, `fund_type_name_spec`, `test_fund_drawdown.py`, `test_conversation_memory.py`, `macro_data.py`, `fund_display.py`, `pack_sanitize.py`, `enforce_planner_catalog_plan`, `task_exec.py`, `llm_client.py`, `test_portfolio_layer.py`, `plan.py`, `graph.py`, `ToolCall`, `book_news_map.py`, `gold_service.py`, `investor_subject.py`, `test_fund_rating_screen.py`, `ToolCall`, `node_compose`, `test_portfolio_intents.py`, `insight/portfolio_scope.py`, `memory/store.py`, `fact_answer.py`, `fact_slots.py`, `test_composer_table_summaries.py`, `test_portfolio_allocation.py`, `re`, `test_metal_fund_rating.py`, `test_news_only_answer.py`, `evidence_pack.py`, `validate_capability_args`, `fields.py`, `enrich_manager_payload`, `portfolio_news_impact.py`, `test_fact_answer.py`, `fund_rating_categories.py`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `ExecutionPlan` (e.g. with `news_calls_for_book()` and `sector_book()`) actually correct?**
  _`ExecutionPlan` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FETCH_WORKERS`, `FRESH_START_CLEAR_QDRANT`, `FRESH_START_EACH_RUN` to the rest of the system?**
  _26 weakly-connected nodes found - possible missing edges._
- **Should `logging` be split into smaller, more focused modules?**
  _Cohesion score 0.07609649122807018 - nodes in this community are weakly interconnected._
- **Why does `ToolCall` connect `ToolCall` to `time`, `fund_rating_screen.py`, `test_pick_shown_fund.py`, `build_evidence_pack`, `test_insight_graph.py`, `fund_drawdown.py`, `test_two_wave_pipeline.py`, `display_table_policy.py`, `fund_type_name_spec`, `test_fund_drawdown.py`, `test_conversation_memory.py`, `macro_data.py`, `pack_sanitize.py`, `enforce_planner_catalog_plan`, `task_exec.py`, `test_portfolio_layer.py`, `plan.py`, `graph.py`, `ToolCall`, `book_news_map.py`, `gold_service.py`, `investor_subject.py`, `test_fund_rating_screen.py`, `update.py`, `executor.py`, `node_compose`, `test_portfolio_intents.py`, `screen_hints_from_question`, `insight/portfolio_scope.py`, `memory/store.py`, `fact_slots.py`, `test_portfolio_allocation.py`, `re`, `test_metal_fund_rating.py`, `test_news_only_answer.py`, `validate_capability_args`, `fields.py`, `portfolio/client.py`, `portfolio_news_impact.py`, `ExecutionPlan`, `fund_rating_categories.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ToolCall` (e.g. with `news_calls_for_book()` and `_apply_planner_request()`) actually correct?**
  _`ToolCall` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `time` be split into smaller, more focused modules?**
  _Cohesion score 0.1028225806451613 - nodes in this community are weakly interconnected._