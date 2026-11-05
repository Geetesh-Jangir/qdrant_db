"""Conversation pointers, per-chat slices, and the sources link."""

import json

from news_rag.insight.contracts import EvidencePack, ExecutionPlan, ToolCall
from news_rag.insight.graph import GraphState, _load_planner_memory, build_result
from news_rag.insight.memory.evidence import (
    clear_conversation,
    recall_slice,
    remember_slice,
)
from news_rag.insight.memory.prompt import chat_history_view, memory_json_tokens, prompt_view
from news_rag.insight.memory.state import MAX_CHAT_TURNS, append_chat_turn
from news_rag.insight.memory.store import get_memory, reset_memory, save_state, sources_for, turn_record
from news_rag.insight.memory.update import apply_planner_refs, commit_turn
from news_rag.insight.plan import parse_plan


class _Log:
    def __init__(self, query_id: str):
        self.query_id = query_id
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        self.lines.append(message)


def _fund_plan(name: str, *, window: str, windows: list[str], relation: str = "") -> ExecutionPlan:
    return ExecutionPlan(
        funds=[name],
        intent="lookup",
        window_label=window,
        turn_relation=relation,
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": windows},
            )
        ],
    )


def _ok(name: str) -> list[dict]:
    return [{
        "ok": True,
        "tool": "get_fund_data",
        "fund": name,
        "data": {"snapshot": {"fund_name": name}},
    }]


def test_period_change_does_not_reuse_the_other_window():
    clear_conversation("conv-period")
    month = {"modules": ["snapshot"], "windows": ["1M"]}
    year = {"modules": ["snapshot"], "windows": ["1Y"]}
    remember_slice("conv-period", "HDFC Large Cap", "get_fund_data", month, {"return_pct": 1.1}, turn=1)
    remember_slice("conv-period", "HDFC Large Cap", "get_fund_data", year, {"return_pct": 12.4}, turn=2)
    assert recall_slice("conv-period", "HDFC Large Cap", "get_fund_data", month)["return_pct"] == 1.1
    assert recall_slice("conv-period", "HDFC Large Cap", "get_fund_data", year)["return_pct"] == 12.4


def test_holdings_then_sectors_keep_both_slices():
    clear_conversation("conv-parts")
    holdings = {"sections": ["holdings"], "top_n": 5}
    sectors = {"sections": ["sectors"], "top_n": 5}
    remember_slice("conv-parts", "HDFC Large Cap", "get_portfolio_data", holdings, {"rows": ["stock"]}, turn=1)
    remember_slice("conv-parts", "HDFC Large Cap", "get_portfolio_data", sectors, {"rows": ["bank"]}, turn=2)
    assert recall_slice("conv-parts", "HDFC Large Cap", "get_portfolio_data", holdings)["rows"] == ["stock"]
    assert recall_slice("conv-parts", "HDFC Large Cap", "get_portfolio_data", sectors)["rows"] == ["bank"]


def test_failed_lookup_does_not_keep_the_old_fund():
    reset_memory("conv-fail")
    commit_turn("conv-fail", _fund_plan("HDFC Large Cap", window="1 month", windows=["1M"]), _ok("HDFC Large Cap"))
    failed = ExecutionPlan(
        funds=["Missing Scheme"],
        intent="lookup",
        turn_relation="continue",
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]})],
    )
    commit_turn("conv-fail", failed, [{"ok": False, "tool": "get_fund_data", "fund": "", "data": {}}])
    frame = get_memory("conv-fail")["frame"]
    assert frame["subjects"] == []
    assert frame["subject_kind"] == "none"


def test_two_stack_entries_can_be_named_together():
    reset_memory("conv-stack")
    commit_turn("conv-stack", _fund_plan("HDFC Large Cap", window="1 month", windows=["1M"]), _ok("HDFC Large Cap"))
    commit_turn(
        "conv-stack",
        _fund_plan("ICICI Prudential Bluechip", window="1 year", windows=["1Y"], relation="reset"),
        _ok("ICICI Prudential Bluechip"),
    )
    follow = ExecutionPlan(funds=[], stack_refs=[1, 2], turn_relation="partial_keep")
    apply_planner_refs(get_memory("conv-stack"), follow)
    assert follow.funds == ["ICICI Prudential Bluechip", "HDFC Large Cap"]


def test_news_less_answer_has_no_sources_link_and_news_keeps_its_own():
    plain = GraphState(question="What is NAV?", conversation_id="conv-plain")
    plain.answer = "NAV is the price of one unit."
    plain.plan = ExecutionPlan(intent="lookup")
    plain.query_log = _Log("q-plain")
    plain_result = build_result(plain)
    assert plain_result["sources_href"] == ""
    assert plain_result["used_news"] is False

    news = GraphState(question="Why did it move?", conversation_id="conv-news")
    news.answer = "The RBI move showed up in the banking weight."
    news.plan = ExecutionPlan(intent="explain_cause", funds=["HDFC Large Cap"])
    news.query_log = _Log("q-news")
    news.evidence_pack = EvidencePack(
        news_grouped={"fund": [{"title": "RBI rate", "url": "https://example.com/rbi", "source": "Mint"}]}
    )
    news_result = build_result(news)
    assert news_result["sources_href"] == "sources?query_id=q-news"
    assert sources_for("q-news")[0]["title"] == "RBI rate"
    assert sources_for("q-plain") == []

    later = GraphState(question="What about the next story?", conversation_id="conv-news")
    later.answer = "A later story."
    later.plan = ExecutionPlan(intent="explain_cause")
    later.query_log = _Log("q-later")
    later.evidence_pack = EvidencePack(
        news_grouped={"fund": [{"title": "Later story", "url": "https://example.com/later"}]}
    )
    build_result(later)
    assert sources_for("q-news")[0]["title"] == "RBI rate"
    assert sources_for("q-later")[0]["title"] == "Later story"


def test_prompt_view_has_pointers_not_cached_numbers_and_logs_chat_history():
    reset_memory("conv-view")
    clear_conversation("conv-view")
    remember_slice(
        "conv-view",
        "HDFC Large Cap",
        "get_fund_data",
        {"modules": ["snapshot"], "windows": ["1M"]},
        {"return_pct": 1.25},
        turn=1,
    )
    commit_turn("conv-view", _fund_plan("HDFC Large Cap", window="1 month", windows=["1M"]), _ok("HDFC Large Cap"))
    view = prompt_view(get_memory("conv-view"))
    assert view["frame"]["subjects"][0]["name"] == "HDFC Large Cap"
    assert "1.25" not in json.dumps(view)

    mem = get_memory("conv-view")
    append_chat_turn(
        mem,
        user="What is the 1 month return?",
        assistant="HDFC Large Cap returned 1.1% over 1 month.",
        turn=1,
    )
    save_state(mem)

    state = GraphState(question="and the 1 year?", conversation_id="")
    state.prior_context = {"conversation_id": "conv-view"}
    state.query_log = _Log("q-view")
    passed = _load_planner_memory(state)
    assert passed["memory"]["turns"][0]["user"] == "What is the 1 month return?"
    assert "frame" not in passed["memory"]
    assert any(line.startswith("MEMORY_PASSED") for line in state.query_log.lines)

    stored = GraphState(question="and the 1 year?", conversation_id="conv-view")
    stored.plan = _fund_plan("HDFC Large Cap", window="1 year", windows=["1Y"], relation="partial_keep")
    stored.answer = "The 1 year figure is in the slice."
    stored.query_log = _Log("q-store")
    stored.wave1_results = _ok("HDFC Large Cap")
    stored.memory_passed_view = chat_history_view(get_memory("conv-view"))
    from news_rag.insight.memory.evidence import note_cache

    note_cache("conv-view", "stored", "hdfc large cap|fund|snapshot|w=1Y|p=", beside="hdfc large cap|fund|snapshot|w=1M|p=")
    build_result(stored)
    text = "\n".join(stored.query_log.lines)
    assert "MEMORY_STORED" in text
    assert "CACHE status=stored" in text
    assert "1.25" not in text
    record = turn_record("q-store")
    assert len(record["stored"]["memory"]["turns"]) == 2


def test_memory_pages_keep_what_was_sent_and_what_python_stored():
    assert memory_json_tokens({}) == 0
    assert memory_json_tokens({"turns": [{"user": "hi", "assistant": "hello"}]}) > 0

    reset_memory("conv-pages")
    first = GraphState(question="What is the NAV?", conversation_id="conv-pages")
    first.answer = "The NAV is on the fact sheet."
    first.plan = _fund_plan("HDFC Large Cap", window="1 month", windows=["1M"])
    first.query_log = _Log("q-first-page")
    first.wave1_results = _ok("HDFC Large Cap")
    first.memory_passed_view = {"turns": []}
    first_result = build_result(first)
    assert first_result["memory_tokens"] == {"planner": 0, "composer": 0}
    assert first_result["memory_passed_href"] == "memory-passed?query_id=q-first-page"
    assert first_result["memory_stored_href"] == "memory-stored?query_id=q-first-page"
    first_record = turn_record("q-first-page")
    assert first_record["passed"]["memory"] == {"turns": []}
    assert first_record["stored"]["updated_by"] == "python"
    assert first_record["stored"]["memory"]["turns"][0]["user"] == "What is the NAV?"
    assert get_memory("conv-pages")["frame"]["subjects"][0]["name"] == "HDFC Large Cap"

    second = GraphState(question="What about 1 year?", conversation_id="conv-pages")
    second.answer = "Here is the 1 year figure."
    second.plan = _fund_plan("HDFC Large Cap", window="1 year", windows=["1Y"], relation="partial_keep")
    second.query_log = _Log("q-second-page")
    second.wave1_results = _ok("HDFC Large Cap")
    second.memory = get_memory("conv-pages")
    second.memory_passed_view = chat_history_view(second.memory)
    second.memory_sent_composer = True
    second_result = build_result(second)
    assert second_result["memory_tokens"]["planner"] > 0
    assert second_result["memory_tokens"]["composer"] == second_result["memory_tokens"]["planner"]
    passed = turn_record("q-second-page")["passed"]
    assert passed["sent_to"] == ["planner", "composer"]
    assert passed["memory"]["turns"][0]["user"] == "What is the NAV?"
    assert len(turn_record("q-second-page")["stored"]["memory"]["turns"]) == 2


def test_chat_history_keeps_at_most_eight_turns():
    reset_memory("conv-eight")
    from news_rag.insight.memory.store import get_or_create

    state = get_or_create("conv-eight")
    for index in range(MAX_CHAT_TURNS + 2):
        append_chat_turn(
            state,
            user=f"question {index}",
            assistant=f"answer {index}",
            turn=index + 1,
        )
    save_state(state)
    turns = chat_history_view(get_memory("conv-eight"))["turns"]
    assert len(turns) == MAX_CHAT_TURNS
    assert turns[0]["user"] == "question 2"
    assert turns[-1]["user"] == f"question {MAX_CHAT_TURNS + 1}"


def test_parse_plan_reads_the_memory_pointers():
    plan = parse_plan(
        {
            "scope": {"kind": "in_scope"},
            "understanding": {"goal": "compare the last two", "intent": "compare", "answer_mode": "DATA_ONLY"},
            "request": {"count": 0, "portfolio_slice": "none", "reading": "two earlier funds"},
            "tool_calls": [],
            "memory": {
                "turn_relation": "partial_keep",
                "stack_refs": [1, 2],
                "list_ordinals": [3],
                "depth": "more",
                "refers_to_turn": 2,
            },
        }
    )
    assert plan.turn_relation == "partial_keep"
    assert plan.stack_refs == [1, 2]
    assert plan.list_ordinals == [3]
    assert plan.answer_depth == "more"
    assert plan.refers_to_turn == 2
