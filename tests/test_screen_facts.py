from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.evidence_pack import build_evidence_pack, render_data_only_template
from news_rag.insight.multi_fact import ensure_screen_facts, screen_fact_names
from news_rag.tools import _attach_screen_facts, run_screen_funds


def test_sector_screen_aum_does_not_mean_top_sectors():
    q = "tell me any 5 funds that are heavily invested in fmgc sector and also their aum"
    assert screen_fact_names(q) == ["aum"]


def test_screen_manager_name_and_experience_are_separate_facts():
    both = "5 fmcg funds and the name and experience of the fund manager"
    assert "manager_name" in screen_fact_names(both)
    assert "manager_experience" in screen_fact_names(both)
    only_name = "5 fmcg funds and the name of the fund manager"
    assert screen_fact_names(only_name) == ["manager_name"]
    only_exp = "5 fmcg funds and the experience of the fund manager"
    assert screen_fact_names(only_exp) == ["manager_experience"]


def test_screen_can_ask_for_several_facts():
    q = "5 funds in petroleum sector with nav, aum, expense ratio and exit load"
    assert screen_fact_names(q) == ["nav", "aum", "expense", "exit_load"]


def test_any_fund_screen_keeps_requested_aum(monkeypatch):
    rows = [
        {"isin": "INF1", "fund_name": "Kotak Nifty PSU Bank ETF", "category": "Banking", "return_1m_pct": -2.2},
        {"isin": "INF2", "fund_name": "DSP Nifty PSU Bank ETF", "category": "Banking", "return_1m_pct": -2.4},
    ]
    monkeypatch.setattr("news_rag.tools._catalog_candidates", lambda **_kwargs: rows)
    monkeypatch.setattr("news_rag.tools._sector_candidates", lambda *_args, **_kwargs: [])

    def _select(rankings, **kwargs):
        return list(rankings)[: kwargs.get("top_n") or 2], False, "note"

    monkeypatch.setattr("news_rag.tools.select_funds_by_nav", _select)

    def _detail(isin: str):
        return {"aum": 500.0 if isin == "INF1" else 800.0, "expense_ratio": {}, "returns": {}}

    monkeypatch.setattr(
        "news_rag.fund_search.get_fund_index",
        lambda: type("I", (), {"get_fund_detail": staticmethod(_detail)})(),
    )
    out = run_screen_funds(
        question="compare two random banking sectors related funds and also tell me their aum",
        top_n=2,
        category="Banking & Financial Services",
    )
    ranked = (out.get("data") or {}).get("rankings") or []
    assert [row.get("aum") for row in ranked] == [500.0, 800.0]


def test_incomplete_return_column_is_omitted():
    plan = ExecutionPlan(intent="rank", answer_mode=AnswerMode.DATA_ONLY)
    rows = [
        {"fund_name": "Fund A", "sector_weight_pct": 10, "aum": 1, "category": "Equity", "return_1m_pct": -1.2},
        {"fund_name": "Fund B", "sector_weight_pct": 8, "aum": 2, "category": "Equity"},
    ]
    pack = build_evidence_pack(
        plan,
        [{"tool": "screen_funds_by_exposure", "ok": True, "data": {"rankings": rows, "return_window": "1M"}}],
        [],
    )
    text = render_data_only_template(pack, plan) or ""
    assert "1M return" not in text
    assert "Fund A" in text
    assert "Fund B" in text


def test_screen_plan_drops_the_unrelated_fund_lookup():
    plan = ExecutionPlan(
        intent="rank",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["Aditya Birla Sun Life Transportation and Logistics Fund - Regular Plan - Growth"],
        tool_calls=[
            ToolCall(tool="screen_funds_by_exposure", arguments={"sector": "FMCG", "top_n": 5}, wave=1),
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(tool="get_portfolio_data", arguments={"sections": ["sectors"]}, wave=1),
        ],
    )
    q = "tell me any 5 funds that are heavily invested in fmgc sector and also their aum"
    ensure_screen_facts(q, plan)
    assert [call.tool for call in plan.tool_calls] == ["screen_funds_by_exposure"]
    assert plan.funds == []


def test_screen_table_includes_aum(monkeypatch):
    def _detail(isin: str):
        return {"nav": 100, "aum": 1234.5, "expense_ratio": {"regular": 1.2}, "returns": {}}

    monkeypatch.setattr("news_rag.fund_search.get_fund_index", lambda: type("I", (), {"get_fund_detail": staticmethod(_detail)})())
    rows = [{"isin": "INF000000001", "fund_name": "ICICI Prudential FMCG Fund", "sector_weight_pct": 34.87, "category": "Other Equity"}]
    _attach_screen_facts(rows, "funds in fmcg sector and also their aum")
    assert rows[0]["aum"] == 1234.5
    plan = ExecutionPlan(intent="rank", answer_mode=AnswerMode.DATA_ONLY)
    pack = build_evidence_pack(
        plan,
        [{"tool": "screen_funds_by_exposure", "ok": True, "data": {"rankings": rows, "ranking_note": "Ranked by sector weight."}}],
        [],
    )
    text = render_data_only_template(pack, plan)
    assert text is not None
    assert "1,234.50" in text
    assert "34.87%" in text


def test_screen_table_includes_manager_name_and_experience(monkeypatch):
    def _detail(_isin: str):
        return {
            "managers": {
                "current": [{"name": "Rahul Baijal", "total_experience_years": 18, "managing_since": "2022-01-01"}],
                "past": [],
            }
        }

    monkeypatch.setattr(
        "news_rag.fund_search.get_fund_index",
        lambda: type("I", (), {"get_fund_detail": staticmethod(_detail)})(),
    )
    rows = [{"isin": "INF000000001", "fund_name": "ICICI Prudential FMCG Fund", "sector_weight_pct": 34.87}]
    _attach_screen_facts(rows, "fmcg funds and the name and experience of the fund manager")
    assert rows[0]["manager_name"] == "Rahul Baijal"
    assert "18 yrs" in rows[0]["manager_experience"]
    assert "2022-01-01" in rows[0]["manager_experience"]

    plan = ExecutionPlan(intent="rank", answer_mode=AnswerMode.DATA_ONLY)
    pack = build_evidence_pack(
        plan,
        [{"tool": "screen_funds_by_exposure", "ok": True, "data": {"rankings": rows, "ranking_note": "Ranked by sector weight."}}],
        [],
    )
    text = render_data_only_template(pack, plan)
    assert text is not None
    assert "Rahul Baijal" in text
    assert "18 yrs since 2022-01-01" in text
