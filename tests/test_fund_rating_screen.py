"""Category RS-rating lists. Payloads are fake. No live HTTP."""

from news_rag.fund_rating_screen import parse_rating_screen, run_rating_list
from news_rag.insight.slot_router import slot_route


def _rating(isin: str, *, label: str, score: float, trail: float, category: str = "large cap") -> dict:
    return {
        "isin": isin,
        "fundName": isin.lower(),
        "schemeCategory": category,
        "finalScore": score,
        "label": label,
        "benchmark": "Nifty 100",
        "asOnDate": "2026-09-30",
        "inputs": {"trailing1Y": trail, "sharpe": 1.4, "beta": 0.9},
        "pillars": {"performance": {"score": 10}, "risk": {"score": 8}},
    }


def _payload(*rows: dict) -> dict:
    return {"data": {"ratings": list(rows)}}


def test_equity_categories_are_explained_by_the_composer():
    from news_rag.insight.plan import parse_plan

    plan = slot_route("What categories come under equity?")
    assert plan is None or not (plan.direct_reply or "").strip()
    explained = parse_plan(
        {
            "scope": {"kind": "in_scope", "direct_reply": "Equity categories: large cap."},
            "understanding": {
                "goal": "List equity categories",
                "intent": "lookup",
                "answer_mode": "DATA_ONLY",
                "query_class": "simple",
                "task": "explain",
            },
            "request": {"count": 0, "portfolio_slice": "none", "reading": "Categories under equity"},
            "tool_calls": [
                {"tool": "screen_funds_by_exposure", "arguments": {"top_n": 1}, "wave": 1}
            ],
            "wave_2_policy": {"trigger": "none"},
            "presentation": {"response_shape": "short_answer", "max_words": 40},
        }
    )
    assert explained.tool_calls == []
    assert explained.direct_reply == ""
    assert explained.requires_compose is True
    assert "large cap" in explained.concept_brief.lower()
    assert "multi cap" in explained.concept_brief.lower()


def test_explain_plus_a_fund_name_keeps_one_screen():
    from news_rag.insight.plan import parse_plan

    explained = parse_plan(
        {
            "scope": {"kind": "in_scope"},
            "understanding": {
                "goal": "Explain multi cap, compare it with flexi cap, and name one multi cap fund",
                "intent": "explain_cause",
                "answer_mode": "DATA_ONLY",
                "query_class": "simple",
                "task": "explain",
            },
            "request": {"count": 1, "portfolio_slice": "none", "reading": "Explain and name one multi cap fund"},
            "tool_calls": [],
            "wave_2_policy": {"trigger": "none"},
            "presentation": {
                "response_shape": "sections",
                "max_words": 180,
                "sub_queries": [
                    {"text": "What is a multi cap fund?"},
                    {"text": "How does multi cap differ from flexi cap?"},
                    {"text": "Name one multi cap fund"},
                ],
            },
        }
    )
    assert explained.requires_compose is True
    assert len(explained.tool_calls) == 1
    call = explained.tool_calls[0]
    assert call.tool == "screen_funds_by_exposure"
    assert call.arguments["top_n"] == 1
    assert call.arguments["focus_question"] == "Name one multi cap fund"
    assert "name exactly one fund" in explained.presentation_notes.lower()


def test_good_choice_list_uses_the_funds_table():
    from news_rag.fund_risk import ensure_risk_tools
    from news_rag.fund_rating_screen import ensure_rating_screen
    from news_rag.insight.contracts import ExecutionPlan
    from news_rag.insight.evidence_pack import build_evidence_pack, render_data_only_template

    question = "tell me 5 random large cap funds which are in good choice category"
    plan = ExecutionPlan()
    ensure_risk_tools(question, plan)
    ensure_rating_screen(question, plan)
    assert plan.requires_compose is False
    assert not (plan.concept_brief or "").strip()
    pack = build_evidence_pack(
        plan,
        [
            {
                "tool": "screen_funds_by_exposure",
                "ok": True,
                "data": {
                    "rankings": [
                        {
                            "fund_name": "HDFC Large Cap Fund - Growth",
                            "category": "large cap",
                            "rs_label": "Good Choice",
                            "final_score": 64.55,
                        }
                    ]
                },
            }
        ],
        [],
    )
    template = render_data_only_template(pack, plan)
    assert template is not None
    assert "table below" in template.lower()
    assert "good choice" in template.lower()
    assert "| Fund |" not in template
    assert "HDFC Large Cap" not in template


def test_locked_large_cap_does_not_request_mid_cap():
    plan = slot_route("5 large cap funds that are Best in category")
    assert plan is not None
    assert plan.tool_calls[0].tool == "screen_funds_by_exposure"
    assert plan.tool_calls[0].arguments.get("rating_screen") is True
    assert not (plan.concept_brief or "").strip()
    called: list[str] = []

    def fetch(fund_type: str, category: str) -> dict:
        called.append(category)
        if category == "large cap":
            return _payload(_rating("INF1", label="Best in category", score=79.85, trail=12))
        return _payload(_rating("INF2", label="Best in category", score=90, trail=20, category=category))

    result = run_rating_list(
        "5 large cap funds that are Best in category",
        fetch=fetch,
    )
    assert called == ["large cap"]
    assert [row["isin"] for row in result["rankings"]] == ["INF1"]
    assert "no more" in result["ranking_note"].lower()
    stored = result["rankings"][0]
    assert "pillars" not in stored
    assert "sharpe" not in stored
    assert stored["rs_label"] == "Best in category"


def test_equity_best_in_category_walks_until_five():
    called: list[str] = []

    def fetch(fund_type: str, category: str) -> dict:
        called.append(category)
        if category == "large cap":
            return _payload(_rating("INF1", label="Best in category", score=79, trail=8))
        if category == "mid cap":
            return _payload(
                *[
                    _rating(f"INFM{i}", label="Best in category", score=80, trail=9, category="mid cap")
                    for i in range(4)
                ]
            )
        return _payload(_rating("INFSMALL", label="Best in category", score=81, trail=10, category=category))

    result = run_rating_list("5 equity funds that are Best in category", fetch=fetch)
    assert called == ["large cap", "mid cap"]
    assert len(result["rankings"]) == 5
    assert "INFSMALL" not in {row["isin"] for row in result["rankings"]}


def test_highest_rating_is_the_rs_score_not_a_one_month_return():
    spec = parse_rating_screen("name the highest rating large cap fund?")
    assert spec is not None
    assert spec.category == "large cap"
    assert spec.locked is True
    assert spec.highest_score is True
    assert spec.count == 1
    assert spec.return_window == ""

    def fetch(fund_type: str, category: str) -> dict:
        assert category == "large cap"
        return _payload(
            _rating("INFLOW", label="Good Choice", score=60, trail=40),
            _rating("INFHIGH", label="Best in category", score=79.85, trail=1),
        )

    result = run_rating_list("name the highest rating largecap fund?", fetch=fetch)
    assert result["rankings"][0]["isin"] == "INFHIGH"
    assert result["categories_called"] == ["large cap"]
    spec = parse_rating_screen("tell me 5 random large cap funds which are in good choice category")
    assert spec is not None
    assert spec.amc == ""
    assert spec.label == "Good Choice"
    assert spec.category == "large cap"
    assert spec.random_sample is True
    assert spec.count == 5
    assert parse_rating_screen("what makes equity different from the debt funds?") is None


def test_hdfc_only_does_not_call_the_rating_url():
    called: list[str] = []

    def fetch(fund_type: str, category: str) -> dict:
        called.append(category)
        return _payload()

    result = run_rating_list("tell me 5 HDFC funds", fetch=fetch)
    assert parse_rating_screen("tell me 5 HDFC funds") is None
    assert called == []
    assert result["rankings"] == []


def test_hdfc_large_cap_label_uses_rating_rows(monkeypatch):
    monkeypatch.setattr(
        "news_rag.fund_rating_screen._amc_matches",
        lambda isin, amc: isin == "INFHDFC" and "hdfc" in amc.lower(),
    )
    called: list[str] = []

    def fetch(fund_type: str, category: str) -> dict:
        called.append(category)
        return _payload(
            _rating("INFHDFC", label="Best in category", score=70, trail=5),
            _rating("INFOTHER", label="Best in category", score=90, trail=9),
        )

    spec = parse_rating_screen("5 HDFC large cap funds that are Best in category")
    assert spec is not None
    assert spec.amc
    result = run_rating_list(
        "5 HDFC large cap funds that are Best in category",
        fetch=fetch,
    )
    assert called == ["large cap"]
    assert [row["isin"] for row in result["rankings"]] == ["INFHDFC"]


def test_best_one_year_prices_the_trailing_shortlist_and_sorts_by_real_return():
    priced: list[str] = []
    rows = [
        _rating(f"INF{i:02d}", label="Good Choice", score=60, trail=100 - i)
        for i in range(12)
    ]

    def fetch(fund_type: str, category: str) -> dict:
        assert category == "large cap"
        return _payload(*rows)

    def price(short: list[dict], window: str) -> list[dict]:
        assert window == "1Y"
        priced.extend(row["isin"] for row in short)
        out = []
        for index, row in enumerate(short):
            copied = dict(row)
            copied["_return"] = float(index)
            out.append(copied)
        return out

    result = run_rating_list(
        "which large cap fund gave the best 1 year return",
        fetch=fetch,
        price=price,
    )
    assert priced == [f"INF{i:02d}" for i in range(10)]
    assert result["rankings"][0]["isin"] == "INF09"
    assert "sharpe" not in result["rankings"][0]
    assert "_return" not in result["rankings"][0]


def test_best_in_category_list_shows_one_year_against_the_category_average():
    question = (
        "name any 5 equity funds which are best in category and also their risk factor "
        "and 1 year return and also their category averages and also compare them"
    )
    spec = parse_rating_screen(question)
    assert spec is not None
    assert spec.label == "Best in category"
    assert spec.return_window == "1Y"
    assert spec.return_direction == ""
    assert spec.compare_category is True
    called = []
    priced = []

    def fetch(fund_type, category):
        called.append(category)
        if category == "large cap":
            row = _rating("INF1", label="Best in category", score=80, trail=5)
            row["inputs"]["categoryAvg1Y"] = 4.0
            return _payload(row)
        if category == "mid cap":
            rows = []
            for index in range(4):
                row = _rating(f"INFM{index}", label="Best in category", score=81, trail=3, category="mid cap")
                row["inputs"]["categoryAvg1Y"] = 2.0
                rows.append(row)
            return _payload(*rows)
        return _payload()

    def price(rows, window):
        assert window == "1Y"
        priced.extend(row["isin"] for row in rows)
        out = []
        for row in rows:
            copied = dict(row)
            copied["return_1y_pct"] = 6.0
            copied["_return"] = 6.0
            out.append(copied)
        return out

    result = run_rating_list(question, fetch=fetch, price=price)
    assert called == ["large cap", "mid cap"]
    assert priced == [row["isin"] for row in result["rankings"]]
    large = next(row for row in result["rankings"] if row["isin"] == "INF1")
    assert large["return_1y_pct"] == 6.0
    assert large["category_avg_1y_pct"] == 4.0
    assert large["vs_category_1y_pct"] == 2.0
    assert "return_1m_pct" not in large
    assert "category avg" in result["ranking_note"].lower()


def test_highest_rating_plus_returns_and_risk_keeps_the_fund_lookup():
    from news_rag.fund_rating_screen import ensure_rating_screen
    from news_rag.insight.contracts import ExecutionPlan, ToolCall
    from news_rag.insight.multi_fact import ensure_screen_facts

    question = (
        "tell me the highest rating equity fund? and also historical returns "
        "and also do the risk analysis of the fund"
    )
    plan = ExecutionPlan(
        routed_by="planner",
        tool_calls=[
            ToolCall(tool="screen_funds_by_exposure", arguments={"top_n": 1}),
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=2),
            ToolCall(tool="search_financial_news", arguments={}, wave=1),
        ],
        sub_queries=[
            {"text": "highest rating equity fund"},
            {"text": "historical returns"},
            {"text": "risk analysis"},
        ],
    )
    ensure_screen_facts(question, plan)
    ensure_rating_screen(question, plan)
    assert [call.tool for call in plan.tool_calls] == ["screen_funds_by_exposure", "get_fund_data"]
    assert plan.tool_calls[1].wave == 1
    modules = plan.tool_calls[1].arguments["modules"]
    assert "return_series" in modules
    assert "risk" in modules
    assert "drawdown" in modules
    assert plan.tool_calls[0].arguments["rating_screen"] is True
    assert plan.tool_calls[0].arguments["top_n"] == 1
    assert plan.requires_compose is True


def test_one_month_return_keeps_only_that_column():
    from news_rag.fund_rating_screen import _keep_asked_return
    from news_rag.tools import explicit_return_window

    question = "recommend me any 5 debt funds and show me their one months returns"
    assert explicit_return_window(question) == "1M"
    assert explicit_return_window("recommend me any 5 debt funds") == ""
    spec = parse_rating_screen(question)
    assert spec is not None
    assert spec.return_window == "1M"
    assert spec.return_direction == ""
    row = {
        "fund_name": "Axis Liquid Fund",
        "return_1w_pct": 3.7,
        "return_1m_pct": 5.32,
        "return_3m_pct": 5.9,
        "return_1y_pct": 6.42,
    }
    _keep_asked_return([row], spec.return_window)
    assert row["return_1m_pct"] == 5.32
    assert "return_1w_pct" not in row
    assert "return_1y_pct" not in row
    untouched = {"return_1m_pct": 1.0, "return_1y_pct": 2.0}
    _keep_asked_return([untouched], "")
    assert untouched["return_1y_pct"] == 2.0


def test_elss_list_drops_an_invented_fund_and_keeps_the_difference():
    from news_rag.fund_rating_screen import ensure_rating_screen
    from news_rag.insight.contracts import ExecutionPlan, ToolCall

    question = "can you show me any 2 elss funds and also tell me how they are different from other funds"
    plan = ExecutionPlan(
        routed_by="planner",
        funds=["Aditya Birla Sun Life ELSS Tax Saver Fund - Growth"],
        tool_calls=[ToolCall(tool="screen_funds_by_exposure", arguments={"top_n": 2}, wave=1)],
        sub_queries=[{"text": "show 2 elss funds"}, {"text": "how they are different"}],
    )
    ensure_rating_screen(question, plan)
    assert plan.funds == []
    assert any(call.tool == "screen_funds_by_exposure" for call in plan.tool_calls)
    assert plan.requires_compose is True
    assert "3 years" in plan.concept_brief
    assert "80C" in plan.concept_brief
