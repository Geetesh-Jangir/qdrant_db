from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.evidence_pack import build_evidence_pack, render_data_only_template
from news_rag.insight.multi_fact import ensure_multi_fact_tools, requested_fund_facts


def test_named_facts_cover_nav_manager_sectors_returns_and_exit_load():
    q = "tell me nav, fund_manager, top 5 sectors, historical performance and exit load of hdfc large cap fund?"
    facts = requested_fund_facts(q)
    assert facts >= {"nav", "managers", "sectors", "returns", "exit_load"}


def test_multi_fact_plan_adds_snapshot_managers_and_sectors():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["managers"]}, wave=1)],
    )
    q = "tell me the aum and fund manager details about the hdfc large cap fund?"
    ensure_multi_fact_tools(q, plan)
    modules = plan.tool_calls[0].arguments["modules"]
    assert "snapshot" in modules
    assert "managers" in modules


def test_multi_fact_answer_keeps_aum_and_managers():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot", "managers"]}, wave=1),
        ],
    )
    pack = build_evidence_pack(
        plan,
        [
            {
                "tool": "get_fund_data",
                "ok": True,
                "fund": "HDFC Large Cap Fund",
                "data": {
                    "snapshot": {
                        "fund_name": "HDFC Large Cap Fund",
                        "nav": 100.5,
                        "aum": 37293.95,
                        "aum_as_on_date": "2026-09-30",
                        "exit_load_summary": "This fund has no exit load.",
                    },
                    "managers": {
                        "fund_name": "HDFC Large Cap Fund",
                        "current": [{"name": "Rahul Baijal", "designation": "Fund Manager"}],
                        "past": [],
                    },
                },
            }
        ],
        [],
    )
    text = render_data_only_template(pack, plan)
    assert text is not None
    assert "37,293.95" in text
    assert "Rahul Baijal" in text
    assert "no exit load" in text
