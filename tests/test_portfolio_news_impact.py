from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.portfolio_news_impact import (
    _merge_sector_picks,
    _strip_book_concentration_tables,
    build_portfolio_news_impact_dossier,
    ensure_portfolio_news_impact_plan,
    question_is_portfolio_news_impact,
    render_portfolio_news_impact_markdown,
)


def test_detects_portfolio_crude_impact_question():
    plan = ExecutionPlan(
        portfolio_scope="investor",
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={"modules": ["summary"]}, wave=1),
            ToolCall(tool="search_financial_news", arguments={"scope": "macro"}, wave=2),
        ],
    )
    q = "if there is news related to the crude price increasing how would that affect my portfolio"
    assert question_is_portfolio_news_impact(q, plan)


def test_ensure_plan_adds_concentration_and_news_topics():
    plan = ExecutionPlan(
        portfolio_scope="investor",
        tool_calls=[
            ToolCall(
                tool="get_investor_portfolio",
                arguments={"modules": ["summary", "holdings"]},
                wave=1,
            ),
            ToolCall(tool="search_financial_news", arguments={"scope": "macro", "topics": []}, wave=2),
        ],
    )
    plan = ensure_portfolio_news_impact_plan(
        plan,
        "crude oil news impact on my portfolio",
    )
    assert all(c.tool != "screen_funds_by_exposure" for c in plan.tool_calls)
    inv = next(c for c in plan.tool_calls if c.tool == "get_investor_portfolio")
    assert "concentration" in (inv.arguments or {}).get("modules", [])
    news = next(c for c in plan.tool_calls if c.tool == "search_financial_news")
    assert (news.arguments or {}).get("topics")


def test_merge_sector_picks_prefers_news_over_rules():
    news = [{"name": "Banks", "direction": "negative", "reason": "margin pressure", "source": "news"}]
    rules = [{"name": "Banks", "direction": "negative", "reason": "rule", "source": "rule_table"}]
    merged = _merge_sector_picks(news, rules, "any")
    assert len(merged) == 1
    assert merged[0]["reason"] == "margin pressure"


def test_build_dossier_joins_portfolio_weights(monkeypatch):
    class _Idx:
        sector_names = ["Banks"]

        def resolve_sector_keys(self, labels):
            return ["Banks"] if "bank" in labels[0].lower() else labels

        def top_funds_for_sectors(self, keys, **kwargs):
            allow = kwargs.get("isin_allowlist") or set()
            if "INF111" in allow:
                return [("INF111", 8.5, {"Banks": 8.5})]
            return []

    monkeypatch.setattr(
        "news_rag.sector_fund_ranking.get_sector_fund_ranking_index",
        lambda: _Idx(),
    )
    monkeypatch.setattr(
        "news_rag.portfolio.concentration.fetch_top_holdings",
        lambda crn: {
            "sector_allocation": [{"sector": "Banks", "percentage": 12.7}],
        },
    )
    monkeypatch.setattr(
        "news_rag.sector_fund_ranking.candidate_sector_names",
        lambda articles, extra, cap=50: ["Banks"],
    )
    monkeypatch.setattr(
        "news_rag.affected_sectors.pick_affected_sectors",
        lambda **kwargs: [{"name": "Banks", "direction": "negative", "reason": "NIM squeeze", "source": "news"}],
    )
    monkeypatch.setattr(
        "news_rag.config.get_settings",
        lambda: type("S", (), {"client_ref_no": "CRN-test", "insight_sector_candidate_cap": 50})(),
    )

    plan = ExecutionPlan(goal="Crude impact on portfolio")
    pack = {
        "investor_portfolio": {
            "summary": {"aum_inr": 65000},
            "holdings": [
                {
                    "scheme_name": "Test Fund",
                    "isin": "INF111",
                    "aum_inr": 65000,
                },
            ],
        },
    }
    news = {
        "macro": [
            {
                "title": "Crude rises",
                "summary": "Oil prices increased pressuring margins for banks",
            },
        ],
    }
    dossier = build_portfolio_news_impact_dossier(
        question="how would crude news affect my portfolio",
        plan=plan,
        data_pack=pack,
        news_grouped=news,
    )
    assert dossier is not None
    assert dossier["sector_impact_analysis"][0]["portfolio_weight_pct"] == 12.7
    assert dossier["sector_impact_analysis"][0]["linkage"] == "direct"
    assert dossier["fund_sector_exposure"][0]["scheme_name"] == "Test Fund"


def test_strip_concentration_tail():
    text = "## Title\n\nBody\n\n### Top holdings\n\n| x |"
    assert "### Top holdings" not in _strip_book_concentration_tables(text)


def test_render_impact_markdown():
    md = render_portfolio_news_impact_markdown(
        {
            "sector_impact_analysis": [
                {
                    "sector": "Banks",
                    "direction": "negative",
                    "portfolio_weight_pct": 12.7,
                    "linkage": "direct",
                    "reason": "Higher rates",
                },
            ],
            "fund_sector_exposure": [
                {
                    "scheme_name": "Kotak Contra Fund",
                    "sector": "Banks",
                    "sector_weight_in_fund_pct": 20.9,
                    "scheme_portfolio_weight_pct": 18.7,
                    "impact_direction": "negative",
                    "sector_reason": "NIM pressure",
                },
            ],
        }
    )
    assert "### Sectors affected by the news" in md
    assert "### Your funds affected" in md
    assert "Kotak Contra" in md
    assert "|" not in md
